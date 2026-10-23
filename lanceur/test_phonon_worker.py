"""PCM compatibility, native stream cleanup, cancellation/recovery and pinned files."""
import base64
import hashlib
import json
from pathlib import Path
import queue
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np
import phonon_model
from phonon_worker import serve


class Input:
    def __init__(self):
        self.lines = queue.Queue()

    def readline(self, limit):
        return self.lines.get(timeout=8)

    def command(self, action, identifier='a' * 32, **extra):
        self.lines.put(json.dumps({'action': action, 'id': identifier, **extra}) + '\n')


class Model:
    sample_rate = 24000

    def __init__(self, samples=None):
        self.samples = samples if samples is not None else np.linspace(-2, 2, 24000, dtype=np.float32)
        self.closed = 0
        self.calls = []

    def stream(self, text, *, voice):
        model = self
        self.calls.append((text, voice))

        class Stream:
            def __enter__(self): return self
            def __exit__(self, *args): model.closed += 1
            def __iter__(self):
                for _ in range(2): yield model.samples

        return Stream()


class PhononWorkerTests(unittest.TestCase):
    def start(self, model=None):
        self.model = model or Model()
        self.source = Input()
        self.output = queue.Queue()
        self.runner = threading.Thread(target=serve, args=(self.model, self.source, self.output.put), daemon=True)
        self.runner.start()
        self.addCleanup(self.shutdown)

    def shutdown(self):
        self.source.lines.put('')
        self.runner.join(3)
        self.assertFalse(self.runner.is_alive())

    def frames(self):
        frames = []
        while True:
            frame = self.output.get(timeout=5)
            frames.append(frame)
            if frame.get('done') or frame.get('error'): return frames

    def test_pcm_is_mono_little_endian_clipped_and_bounded(self):
        self.start()
        self.source.command('speak', text='Bonjour Fred.')
        frames = self.frames()
        audio = [base64.b64decode(f['pcm']) for f in frames if 'pcm' in f]
        self.assertTrue(all(len(chunk) <= 16000 and len(chunk) % 2 == 0 for chunk in audio))
        samples = np.frombuffer(b''.join(audio), dtype='<i2')
        self.assertEqual(48000, samples.size)
        self.assertEqual((-32767, 32767), (int(samples.min()), int(samples.max())))
        self.assertTrue(all(f['rate'] == 24000 for f in frames if 'pcm' in f))
        self.assertEqual({'id': 'a' * 32, 'done': True, 'cancelled': False}, frames[-1])
        self.assertEqual(1, self.model.closed)

    def test_cancel_closes_generation_and_next_request_works(self):
        waiting = threading.Event()
        release = threading.Event()
        model = Model()
        original = model.stream

        def slow_stream(*args, **kwargs):
            original_stream = original(*args, **kwargs)

            class Stream:
                def __enter__(self): return self
                def __exit__(self, *args): original_stream.__exit__(*args)
                def __iter__(self):
                    yield model.samples[:240]
                    waiting.set()
                    release.wait(5)
                    yield model.samples[:240]

            return Stream()

        model.stream = slow_stream
        self.start(model)
        self.source.command('speak', text='Une longue phrase.')
        first = self.output.get(timeout=5)
        self.assertIn('pcm', first)
        self.assertTrue(waiting.wait(2))
        # Acknowledged cancellation must be observed before the iterator resumes.
        self.source.command('cancel')
        # A queue barrier: reader handles the cancellation before queuing this request.
        self.source.command('speak', 'b' * 32, text='Suite.')
        deadline = time.monotonic() + 2
        while not self.source.lines.empty() and time.monotonic() < deadline:
            threading.Event().wait(.005)
        self.assertTrue(self.source.lines.empty())
        release.set()
        frames = self.frames()
        self.assertEqual([{'id': 'a' * 32, 'done': True, 'cancelled': True}], frames)
        self.assertEqual('b' * 32, self.frames()[-1]['id'])
        self.assertEqual(2, model.closed)

    def test_cancel_before_request_never_starts_synthesis(self):
        self.start()
        self.source.command('cancel')
        self.source.command('speak', text='Ignorer cette phrase.')
        self.assertTrue(self.frames()[-1]['cancelled'])
        self.assertEqual([], self.model.calls)

    def test_invalid_text_does_not_poison_next_turn(self):
        self.start()
        self.source.command('speak', text=' ' * 601)
        self.assertIn('error', self.frames()[-1])
        self.source.command('speak', 'b' * 32, text='Bonjour.')
        self.assertTrue(self.frames()[-1]['done'])

    def test_invalid_samples_close_native_stream(self):
        self.start(Model(np.array([float('nan')], dtype=np.float32)))
        self.source.command('speak', text='Bonjour.')
        self.assertIn('error', self.frames()[-1])
        self.assertEqual(1, self.model.closed)

    def test_duration_limit_closes_native_stream(self):
        self.start(Model(np.zeros(24000 * 91, dtype=np.float32)))
        self.source.command('speak', text='Bonjour.')
        frames = self.frames()
        self.assertNotIn('pcm', frames[0])
        self.assertIn('error', frames[-1])
        self.assertEqual(1, self.model.closed)

    def test_corrupt_same_size_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.q8.gguf'
            path.write_bytes(b'good')
            spec = {'files': {path.name: {'size': 4, 'sha256': hashlib.sha256(b'good').hexdigest()}}}
            with patch.object(phonon_model, 'SPEC', spec):
                self.assertEqual(Path(folder), phonon_model.verify(folder))
                path.write_bytes(b'evil')
                with self.assertRaisesRegex(ValueError, 'Empreinte'): phonon_model.verify(folder)


if __name__ == '__main__':
    unittest.main(verbosity=2)
