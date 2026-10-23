"""Exercise the real isolated French worker before allowing the production switch."""
import base64
import hashlib
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import wave

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lanceur'))
from phonon_model import SPEC, verify


def source_hashes():
    names = ('phonon_worker.py', 'phonon_model.py', 'phonon-model.json', 'requirements-phonon.txt')
    return {name: hashlib.sha256((ROOT / 'lanceur' / name).read_bytes()).hexdigest() for name in names}


def main():
    verify()
    output = queue.Queue()
    with (OUT / 'native-stderr.txt').open('w', encoding='utf-8') as errors:
        started = time.monotonic()
        process = subprocess.Popen([sys.executable, '-X', 'utf8', str(ROOT / 'lanceur/phonon_worker.py')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True, encoding='utf-8',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

        def reader():
            for line in process.stdout:
                try: output.put(json.loads(line))
                except ValueError: output.put({'error': 'Non-JSON worker stdout'})
            output.put({'error': 'Worker stopped'})

        threading.Thread(target=reader, daemon=True).start()

        def command(action, identifier, **extra):
            process.stdin.write(json.dumps({'action': action, 'id': identifier, **extra}) + '\n')
            process.stdin.flush()

        def speech(identifier, text, cancel=False):
            start = time.monotonic()
            command('speak', identifier, text=text)
            first = None
            cancelled_at = None
            pcm = []
            deadline = start + 100
            while time.monotonic() < deadline:
                frame = output.get(timeout=10)
                assert not frame.get('error'), frame
                assert frame['id'] == identifier, 'Cross-request frame'
                if 'pcm' in frame:
                    if first is None:
                        first = time.monotonic() - start
                        if cancel:
                            cancelled_at = time.monotonic()
                            command('cancel', identifier)
                    audio = base64.b64decode(frame['pcm'], validate=True)
                    assert frame['rate'] == 24000 and len(audio) <= 16000 and len(audio) % 2 == 0
                    pcm.append(audio)
                if frame.get('done'):
                    assert first is not None and frame['cancelled'] == cancel
                    elapsed = time.monotonic() - start
                    samples = np.frombuffer(b''.join(pcm), dtype='<i2')
                    assert samples.size and np.max(np.abs(samples.astype(np.int32))) > 10
                    tree = [psutil.Process(process.pid)]
                    tree.extend(tree[0].children(recursive=True))
                    resident = sum(child.memory_info().rss for child in tree if child.is_running())
                    result = {'first_chunk_seconds': first, 'compute_seconds': elapsed,
                              'audio_seconds': samples.size / 24000,
                              'cancelled': cancel, 'rss_bytes': resident,
                              'memory_scope': 'worker process tree including Windows Python launcher'}
                    if cancel:
                        result['cancel_ack_seconds'] = time.monotonic() - cancelled_at
                        assert result['cancel_ack_seconds'] < 3, 'Slow native cancellation'
                    return result, b''.join(pcm)
            raise TimeoutError('Phonon did not complete')

        try:
            ready = output.get(timeout=60)
            assert ready.get('ready') and ready['language'] == 'fr' and ready['rate'] == 24000, ready
            loading = time.monotonic() - started
            first, audio = speech('a' * 32, 'Bonjour, je suis Fred. Nous pouvons maintenant discuter ensemble.')
            with wave.open(str(OUT / 'fred-phonon-francais.wav'), 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(audio)
            interrupted, _ = speech('b' * 32,
                'Je vais raconter une longue histoire pour vérifier que ma réponse s’arrête lorsque vous reprenez la parole. ' * 4,
                cancel=True)
            resumed, _ = speech('c' * 32, 'Oui, je vous écoute. La conversation peut continuer.')
            result = {'passed': True, 'engine': 'Phonon 0.4.1', 'device': 'cpu', 'language': 'fr',
                      'voice': 'default', 'revision': SPEC['revision'], 'source_sha256': source_hashes(),
                      'loading_seconds': loading, 'speech': first, 'interruption': interrupted, 'recovery': resumed,
                      'human_listening_validated': False}
            (OUT / 'native-validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(result, indent=2))
        finally:
            process.stdin.close()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=5)


if __name__ == '__main__':
    main()
