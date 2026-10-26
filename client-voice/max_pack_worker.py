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


from worker_protocol import CommandInbox


def serve(configuration, engine, selection=None):
    verify(configuration,engine)
    with redirect_stdout(sys.stderr):
        loaded = WhisperRecognition(configuration['root'],selection or 'auto',configuration.get('native_device') if selection is None else None) if engine=='asr' else PhononVoice(configuration['root'])
    inbox=CommandInbox(engine)
    commands,stop,closed=inbox.commands,inbox.stop,inbox.closed

    inbox.start()
    emit({'ready': True, 'device':getattr(loaded,'device_info',{})})
    try:
        while not closed.is_set():
            command = commands.get()
            if command is None:
                break
            identifier = command['id']
            inbox.begin(identifier)
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
                inbox.finish()
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
