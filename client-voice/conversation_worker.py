"""One local Windows ASR for dictation and conversation; PCM stays in memory."""
import argparse
import base64
from collections import deque
import json
import sys
import threading
import time
import wave
import secrets
import urllib.request
import numpy as np
from aec_capture import EchoMicrophone
from recognition import Recognizer


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--mode', choices=('conversation', 'dictation', 'wakeword'), default='conversation')
    parser.add_argument('--fixture')
    parser.add_argument('--quality', choices=('low', 'max'), default='low')
    args = parser.parse_args()
    bridge = None
    if args.quality == 'max':
        # Fixed loopback address and ephemeral token come from the owning client,
        # never from a user-controlled URL or process command line.
        bridge = json.loads(sys.stdin.readline(4096))
        if type(bridge.get('port')) is not int or not 1 <= bridge['port'] <= 65535:
            raise ValueError('Connexion locale du mode Max invalide.')
    stop = threading.Event(); finish = threading.Event(); muted = threading.Event(); paused=threading.Event();acks = deque()

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
                if value.get('action')=='playback' and args.quality=='max' and args.mode=='conversation' and type(value.get('playing')) is bool and type(value.get('interruptions')) is bool:
                    paused.set() if value['playing'] and not value['interruptions'] else paused.clear()
        finally:
            stop.set()

    if not args.fixture:
        threading.Thread(target=commands, daemon=True).start()
    started = time.monotonic()
    def transcribe(audio, **progressive):
        body = {'pcm': base64.b64encode((np.clip(audio, -1, 1)*32767).astype('<i2').tobytes()).decode(),
                'rate': 16000, 'session': bridge['session'], 'request_id': secrets.token_hex(16), **progressive}
        request = urllib.request.Request('http://127.0.0.1:'+str(bridge['port'])+'/client/voice/max/transcribe',
            data=json.dumps(body).encode(), headers={'Authorization': 'Bearer '+bridge['token'], 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=35) as response:
            value = json.loads(response.read(65536))
        return value['text']
    if args.mode=='wakeword':
        from wakeword_recognition import WakeWordRecognizer
        recognizer=WakeWordRecognizer(args.models)
    elif bridge and bridge.get('progressive'):
        from max_recognition import MaxRecognizer
        recognizer = MaxRecognizer(args.models, transcribe,bridge.get('recognizer','Parakeet v3 · progressif'))
    else:
        recognizer = Recognizer(args.models, mode=args.mode, **({'transcribe': transcribe} if bridge else {}))
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
        was_muted = False;was_paused=False
        limit = 120 if args.mode == 'dictation' else 15 * 60
        while not stop.is_set() and not finish.is_set() and captured < limit * 16000 and (args.mode!='conversation' or time.monotonic()-started<limit):
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
            capture_paused=paused.is_set()
            if capture_paused!=was_paused:
                recognizer.reset_capture();was_paused=capture_paused
            if not capture_paused:recognizer.accept(audio)
            if not listening or time.monotonic() - last_emit >= .1:
                emit({'phase': 'listening', 'aec': True, 'muted':False, 'microphone_closed':False, 'loading_seconds': time.monotonic()-started,
                      'message': 'Dictée locale · français' if args.mode=='dictation' else 'Conversation locale · français',
                      'captured_samples': captured, 'seconds': captured // 16000,'capture_paused':capture_paused,
                      'audio_level': round(float(np.sqrt(np.mean(audio*audio))), 5), 'audio_level_at':time.time(), **recognizer.status()})
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
