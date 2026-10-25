"""Optional downloadable worker; dependencies never enter the base client EXE."""
import argparse
import base64
from collections import OrderedDict
from contextlib import redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time
from max_asr import WhisperRecognition, available_devices
from max_phonon import PhononVoice
from max_gpu import gpu_candidates, select_gpu


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def verify(configuration,engine=None):
    root = Path(configuration['root']).resolve()
    for name, item in configuration['manifest'].items():
        if engine=='asr' and name.startswith('tts/') or engine=='tts' and name.startswith('asr/'):
            continue
        path = (root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size != item['bytes']:
            raise ValueError('Complément Max incomplet. Réinstallez-le depuis Vocal.')
        with path.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != item['sha256']:
                raise ValueError('Complément Max corrompu. Réinstallez-le depuis Vocal.')


def serve(configuration, engine, selection=None):
    verify(configuration,engine)
    with redirect_stdout(sys.stderr):
        loaded = WhisperRecognition(configuration['root'],selection or 'auto',configuration.get('native_device') if selection is None else None) if engine=='asr' else PhononVoice(configuration['root'])
    commands = queue.Queue(maxsize=1)
    cancelled_ids = OrderedDict()
    stop = threading.Event()
    closed = threading.Event()
    guard = threading.Lock()
    current = {'id': None}

    def read():
        try:
            while line := sys.stdin.readline(1300002):
                if len(line) > 1300000:
                    raise ValueError('Commande Max trop volumineuse.')
                value = json.loads(line)
                identifier = value.get('id')
                if not isinstance(identifier, str) or not re.fullmatch('[a-f0-9]{32}', identifier):
                    raise ValueError('Identifiant Max invalide.')
                if value.get('action') == 'cancel':
                    with guard:
                        cancelled_ids[identifier] = True
                        while len(cancelled_ids) > 64:
                            cancelled_ids.popitem(last=False)
                        if current['id'] == identifier:
                            stop.set()
                elif value.get('action') == ('transcribe' if engine == 'asr' else 'speak'):
                    commands.put_nowait(value)
                else:
                    raise ValueError('Commande Max invalide.')
        except Exception:
            if os.environ.get('KIARA_MAX_DIAGNOSTICS')=='1':
                import traceback
                traceback.print_exc(file=sys.stderr)
        finally:
            closed.set(); stop.set()
            try:
                commands.put_nowait(None)
            except queue.Full:
                pass

    threading.Thread(target=read, daemon=True).start()
    emit({'ready': True, 'device':getattr(loaded,'device_info',{})})
    try:
        while not closed.is_set():
            command = commands.get()
            if command is None:
                break
            identifier = command['id']
            with guard:
                current['id'] = identifier
                stop.clear()
                if identifier in cancelled_ids:
                    stop.set()
            try:
                if not stop.is_set():
                    started = time.perf_counter()
                    if engine == 'asr':
                        command['raw_pcm'] = base64.b64decode(command['pcm'], validate=True)
                        with redirect_stdout(sys.stderr):
                            text = loaded.transcribe(command,stop)
                        elapsed = time.perf_counter()-started
                        duration = (command.get('offset', 0)+len(command['raw_pcm'])/2)/16000
                        if not stop.is_set():
                            emit({'id': identifier, 'text': text, 'metrics': {'elapsed_ms': elapsed*1000, 'rtf': elapsed/max(.01, duration)}})
                    else:
                        iterator = loaded.stream(command['text'], stop)
                        try:
                            while True:
                                try:
                                    with redirect_stdout(sys.stderr):
                                        frame = next(iterator)
                                except StopIteration:
                                    break
                                if stop.is_set():
                                    break
                                if 'raw_pcm' in frame:
                                    frame['pcm'] = base64.b64encode(frame.pop('raw_pcm')).decode()
                                emit({'id': identifier, **frame})
                        finally:
                            iterator.close()
                emit({'id': identifier, 'done': True, 'cancelled': stop.is_set()})
            except Exception as error:
                emit({'id': identifier, 'error': str(error) if isinstance(error, ValueError) else 'Le traitement Max a échoué. Réessayez ou choisissez Low.'})
            finally:
                with guard:
                    current['id'] = None
    finally:
        loaded.close()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--engine', choices=('asr', 'tts'))
    parser.add_argument('--probe-gpus',action='store_true')
    parser.add_argument('--gpu')
    args = parser.parse_args()
    try:
        configuration=json.loads(Path(args.config).read_text(encoding='utf-8'))
        if args.probe_gpus:
            with redirect_stdout(sys.stderr):devices=gpu_candidates(available_devices(configuration['root']))
            recommended=select_gpu(devices)['id'] if devices else None
            emit({'devices':devices,'recommended':recommended})
        else:
            if not args.engine:raise ValueError('Choisissez le moteur vocal.')
            serve(configuration, args.engine,args.gpu)
    except Exception as error:
        import traceback
        traceback.print_exc(file=sys.stderr)
        emit({'error': str(error) if isinstance(error, ValueError) else 'Chargement Max impossible. Réinstallez le complément depuis Vocal.', 'code':getattr(error,'code','runtime_error')})
