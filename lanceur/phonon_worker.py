"""Isolated CPU Phonon process. Same bounded JSON/PCM protocol as Kiara's gateway."""
import base64
from collections import OrderedDict
import json
import os
import queue
import sys
import threading
import time

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['HF_HUB_OFFLINE'] = '1'
import numpy as np
from phonon_model import load, SPEC


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def serve(model, source, send=emit):
    commands = queue.Queue(maxsize=1)
    stop = threading.Event()
    closed = threading.Event()
    guard = threading.Lock()
    current = {'id': ''}
    cancelled = OrderedDict()

    def reader():
        try:
            while True:
                line = source.readline(8194)
                if not line:
                    break
                if len(line) > 8192:
                    raise ValueError('Command too large')
                command = json.loads(line)
                if not isinstance(command, dict):
                    raise ValueError('Invalid command')
                identifier = command.get('id')
                if not isinstance(identifier, str) or len(identifier) != 32 or any(c not in '0123456789abcdef' for c in identifier):
                    raise ValueError('Invalid request ID')
                if command.get('action') == 'cancel':
                    with guard:
                        cancelled[identifier] = True
                        while len(cancelled) > 64:
                            cancelled.popitem(last=False)
                        if identifier == current['id']:
                            stop.set()
                elif command.get('action') == 'speak':
                    try:
                        commands.put_nowait(command)
                    except queue.Full:
                        send({'id': identifier, 'error': 'Le moteur vocal est occupé.'})
                else:
                    raise ValueError('Invalid action')
        finally:
            closed.set()
            stop.set()
            try:
                commands.put_nowait(None)
            except queue.Full:
                pass

    threading.Thread(target=reader, daemon=True).start()
    while True:
        command = commands.get()
        if command is None:
            break
        identifier = command['id']
        with guard:
            current['id'] = identifier
            stop.clear()
            if identifier in cancelled or closed.is_set():
                stop.set()
            cancelled.pop(identifier, None)
        try:
            text = command.get('text')
            if not isinstance(text, str) or not 1 <= len(text.strip()) <= 600:
                raise ValueError('Invalid speech text')
            duration = 0
            started = time.monotonic()
            if not stop.is_set():
                # Exiting this context also cancels and joins native generation workers.
                with model.stream(text, voice=SPEC['voice']) as audio:
                    for chunk in audio:
                        if stop.is_set():
                            break
                        samples = np.asarray(chunk, dtype=np.float32).reshape(-1)
                        if not np.isfinite(samples).all():
                            raise ValueError('Non-finite audio')
                        duration += samples.size / model.sample_rate
                        if duration > 90 or time.monotonic() - started > 90:
                            raise ValueError('Speech duration exceeded')
                        pcm = (np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes()
                        for offset in range(0, len(pcm), 16000):
                            if stop.is_set():
                                break
                            send({'id': identifier, 'pcm': base64.b64encode(pcm[offset:offset + 16000]).decode(),
                                  'rate': model.sample_rate})
            send({'id': identifier, 'done': True, 'cancelled': stop.is_set()})
        except Exception as error:
            print('Phonon synthesis error: ' + type(error).__name__, file=sys.stderr, flush=True)
            send({'id': identifier, 'error': 'La synthèse vocale a échoué.'})
        finally:
            with guard:
                current['id'] = ''
        if closed.is_set():
            break


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    started = time.monotonic()
    model = load()
    emit({'ready': True, 'rate': model.sample_rate, 'engine': 'Phonon 0.4.1',
          'language': 'fr', 'voice': SPEC['voice'], 'loading_seconds': time.monotonic() - started})
    serve(model, sys.stdin)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        emit({'error': 'Service Phonon indisponible : ' + type(error).__name__})
        raise
