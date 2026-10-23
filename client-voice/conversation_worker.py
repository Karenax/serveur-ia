"""One local Windows ASR for dictation and conversation; PCM stays in memory."""
import argparse
from collections import deque
import json
import sys
import threading
import time
import wave
import numpy as np
from aec_capture import EchoMicrophone
from recognition import Recognizer


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--mode', choices=('conversation', 'dictation'), default='conversation')
    parser.add_argument('--fixture')
    args = parser.parse_args()
    stop = threading.Event(); finish = threading.Event(); muted = threading.Event(); acks = deque()

    def commands():
        try:
            for line in sys.stdin:
                if len(line) > 1024:
                    raise ValueError('Command too large')
                value = json.loads(line)
                if value.get('action') == 'stop':
                    stop.set(); break
                if value.get('action') == 'finish':
                    finish.set()
                if value.get('action') == 'ack' and type(value.get('turn')) is int:
                    acks.append(value['turn'])
                if value.get('action') == 'mute' and type(value.get('muted')) is bool and args.mode=='conversation':
                    muted.set() if value['muted'] else muted.clear()
        finally:
            stop.set()

    if not args.fixture:
        threading.Thread(target=commands, daemon=True).start()
    started = time.monotonic()
    recognizer = Recognizer(args.models, mode=args.mode)
    microphone = None
    try:
        if args.fixture:
            import math
            with wave.open(args.fixture) as source:
                assert source.getnchannels() == 1 and source.getsampwidth() == 2
                rate = source.getframerate()
                audio = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32) / 32768
            divisor = math.gcd(rate, 16000)
            if rate != 16000:
                from scipy.signal import resample_poly
                audio = resample_poly(audio, 16000 // divisor, rate // divisor).astype(np.float32)
            for offset in range(0, len(audio) + 32000, 1600):
                recognizer.accept(audio[offset:offset+1600] if offset < len(audio) else np.zeros(1600, np.float32))
            recognizer.finish(); recognizer.drain()
            result = recognizer.status()
            emit({'phase': 'test_done', 'passed': bool(result['turns'] or result['text']),
                  'audio_seconds': len(audio) / 16000, **result})
            return
        if stop.is_set():
            return
        if finish.is_set():
            emit({'phase': 'ready', 'microphone_closed': True, 'text': '', 'partial': '', 'turns': [],
                  'message': 'Texte prêt. Corrigez-le puis envoyez votre message.'})
            return
        last_audio = time.monotonic(); last_emit = 0; captured = 0; listening = False
        was_muted = False
        limit = 120 if args.mode == 'dictation' else 15 * 60
        while not stop.is_set() and not finish.is_set() and captured < limit * 16000:
            while acks:
                recognizer.ack(acks.popleft())
            if muted.is_set():
                if microphone:
                    microphone.close(); microphone = None
                if not was_muted:
                    recognizer.reset_capture(); was_muted = True
                if not listening or time.monotonic()-last_emit>=.1:
                    emit({'phase':'listening','muted':True,'microphone_closed':True,'aec':True,
                          'captured_samples':captured,'seconds':captured//16000,
                          'message':'Microphone coupé',**recognizer.status()})
                    listening = True; last_emit = time.monotonic()
                stop.wait(.05); continue
            if microphone is None:
                microphone = EchoMicrophone(args.resources)
                was_muted = False; listening = False; last_audio = time.monotonic()
            pcm = microphone.read()
            if muted.is_set():continue
            if not pcm:
                if time.monotonic() - last_audio > 5:
                    raise OSError('Le microphone ne fournit aucun son. Vérifiez les périphériques Windows par défaut.')
                continue
            last_audio = time.monotonic(); captured += len(pcm) // 2
            audio = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768
            recognizer.accept(audio)
            if not listening or time.monotonic() - last_emit >= .1:
                emit({'phase': 'listening', 'aec': True, 'muted':False, 'microphone_closed':False, 'loading_seconds': time.monotonic()-started,
                      'message': 'Dictée locale · français' if args.mode=='dictation' else 'Conversation locale · français',
                      'captured_samples': captured, 'seconds': captured // 16000,
                      'audio_level': round(float(np.sqrt(np.mean(audio*audio))), 5), **recognizer.status()})
                listening = True; last_emit = time.monotonic()
        if microphone:microphone.close(); microphone = None
        if args.mode == 'dictation' and not stop.is_set():
            emit({'phase': 'finishing', 'microphone_closed': True, **recognizer.status()})
            recognizer.finish(); recognizer.drain(stop)
            if stop.is_set():
                emit({'phase': 'stopped', 'partial': '', 'text': '', 'turns': [], 'microphone_closed': True})
            else:
                emit({'phase': 'ready', 'microphone_closed': True, 'seconds': captured // 16000,
                      'message': 'Texte prêt. Corrigez-le puis envoyez votre message.', **recognizer.status()})
        else:
            emit({'phase': 'stopped', 'partial': '', 'text': '', 'turns': [], 'microphone_closed': True})
    finally:
        if microphone:
            microphone.close()
        recognizer.close()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
    try:
        main()
    except Exception as error:
        emit({'phase': 'error', 'message': str(error) if isinstance(error, (ValueError, OSError)) else 'La reconnaissance vocale a échoué. Réessayez.', 'microphone_closed': True})
        raise
