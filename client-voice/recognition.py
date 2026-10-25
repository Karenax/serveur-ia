"""Parakeet v3, Silero VAD and Smart Turn on CPU, with asynchronous decoding."""
from collections import deque
from pathlib import Path
import threading
import time
import numpy as np
import onnxruntime as ort
import sherpa_onnx
from turn_features import features

RATE = 16000
MAX_TURN = 28 * RATE
CONVERSATION_SILENCE = .65
CONVERSATION_MAX_SILENCE = 1.6


class Recognizer:
    minimum_silence=CONVERSATION_SILENCE
    maximum_silence=CONVERSATION_MAX_SILENCE
    turn_threshold=.65
    def __init__(self, models, mode='conversation', transcribe=None):
        models = Path(models); self.mode = mode
        self.transcribe = transcribe
        self.asr = None if transcribe else sherpa_onnx.OfflineRecognizer.from_transducer(
            tokens=str(models/'tokens.txt'), encoder=str(models/'encoder.int8.onnx'),
            decoder=str(models/'decoder.int8.onnx'), joiner=str(models/'joiner.int8.onnx'),
            model_type='nemo_transducer', num_threads=4, provider='cpu')
        config = sherpa_onnx.VadModelConfig()
        config.sample_rate = RATE; config.num_threads = 1
        config.silero_vad.model = str(models/'silero-vad.onnx')
        config.silero_vad.threshold = .6; config.silero_vad.min_silence_duration = .2
        config.silero_vad.min_speech_duration = .25; config.silero_vad.max_speech_duration = 30
        self.vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=35)
        options = ort.SessionOptions(); options.intra_op_num_threads = 2; options.inter_op_num_threads = 1
        self.turn = ort.InferenceSession(str(models/'smart-turn.onnx'), options, providers=['CPUExecutionProvider'])
        self.input_name = self.turn.get_inputs()[0].name
        self.samples = 0; self.last_voice = 0; self.next_check = 0; self.last_preview = 0
        self.speech = False; self.was_speech = False; self.speech_id = 0; self.turn_id = 0
        # Silero can confirm a quiet onset late. Retain the beginning of the
        # utterance even when its first word precedes the VAD decision by >1 s.
        self.audio = []; self.preroll = deque(maxlen=20); self.audio_samples = 0
        self.partial = ''; self.partial_speech_id = 0; self.committed = ''; self.turns = deque()
        self.last_probability = None; self.compute = 0.; self.failure = None
        self.guard = threading.Condition(); self.finals = deque(); self.preview = None
        self.processing = False; self.closed = False; self.finalized = 0
        self.capture_epoch = 0
        self.worker = threading.Thread(target=self._decode, daemon=True); self.worker.start()

    def accept(self, audio):
        if self.failure:
            raise ValueError('La reconnaissance vocale a échoué. Raccrochez puis réessayez.') from self.failure
        audio = np.asarray(audio, dtype=np.float32)
        for offset in range(0, len(audio), 1600):
            self._frame(audio[offset:offset+1600].copy())

    def _frame(self, audio):
        self.samples += len(audio); self.vad.accept_waveform(audio)
        speech = self.vad.is_speech_detected()
        while not self.vad.empty():
            self.vad.pop()
        if speech:
            self.last_voice = self.samples
            if not self.speech:
                self.speech_id += 1; self.speech = True
                self.audio = list(self.preroll); self.audio_samples = sum(len(frame) for frame in self.audio)
                self.preroll.clear(); self.last_preview = 0
                with self.guard:
                    self.partial = ''; self.partial_speech_id = self.speech_id
        self.was_speech = speech
        if not self.speech:
            self.preroll.append(audio); return
        self.audio.append(audio); self.audio_samples += len(audio)
        if self.audio_samples >= MAX_TURN:
            self.finish(); return
        silence = (self.samples - self.last_voice) / RATE
        if not speech and silence >= (self.minimum_silence if self.mode == 'conversation' else 1.5) and self.samples >= self.next_check:
            self.next_check = self.samples + 4000
            window = np.concatenate(self.audio)[-128000:]
            self.last_probability = float(np.asarray(self.turn.run(None, {self.input_name: features(window)})[0]).reshape(-1)[0])
            if self.mode == 'dictation' or self.last_probability > self.turn_threshold or silence >= self.maximum_silence:
                self.finish(); return
        if self.audio_samples >= RATE and self.audio_samples - self.last_preview >= RATE:
            self.last_preview = self.audio_samples
            with self.guard:
                self.preview = (self.speech_id, np.concatenate(self.audio), False)
                self.guard.notify_all()

    def finish(self):
        if not self.speech:
            return
        with self.guard:
            if len(self.finals) + len(self.turns) >= 8:
                raise ValueError('Trop de demandes vocales en attente. Raccrochez puis recommencez.')
            # Endpoint detection needs silence, but the ASR final should see
            # the spoken phrase with a short tail, not seconds of empty audio.
            tail=max(0,self.samples-self.last_voice-int(.15*RATE))
            audio=np.concatenate(self.audio)
            if tail:audio=audio[:max(RATE//4,len(audio)-tail)]
            self.finals.append((self.speech_id, audio, True))
            self.preview = None; self.guard.notify_all()
        self.speech = False; self.was_speech = False
        self.audio = []; self.audio_samples = 0; self.next_check = 0; self.preroll.clear()

    def _decode(self):
        try:
            while True:
                with self.guard:
                    self.guard.wait_for(lambda: self.closed or self.finals or self.preview)
                    if self.closed:
                        return
                    if self.finals:
                        identifier, audio, final = self.finals.popleft()
                    else:
                        identifier, audio, final = self.preview; self.preview = None
                    self.processing = True
                    epoch = self.capture_epoch
                started = time.perf_counter()
                if self.transcribe:
                    text = self.transcribe(audio).strip()[:6000]
                else:
                    stream = self.asr.create_stream(); stream.accept_waveform(RATE, audio)
                    self.asr.decode_stream(stream); text = stream.result.text.strip()[:6000]
                with self.guard:
                    self.compute += time.perf_counter() - started
                    if self.closed:
                        return
                    if epoch != self.capture_epoch:
                        self.processing = False; self.guard.notify_all(); continue
                    if final:
                        self.finalized = identifier
                        if text:
                            if self.mode == 'dictation':
                                self.committed = (self.committed + ' ' + text).strip()[:32000]
                            else:
                                self.turn_id += 1
                                self.turns.append({'id': self.turn_id, 'text': text, 'speech_id': identifier})
                        if self.partial_speech_id <= identifier:
                            self.partial = ''
                    elif identifier > self.finalized and identifier == self.speech_id:
                        self.partial = text; self.partial_speech_id = identifier
                    self.processing = False; self.guard.notify_all()
        except Exception as error:
            with self.guard:
                self.failure = error; self.processing = False; self.guard.notify_all()

    def drain(self, stop=None):
        deadline = time.monotonic() + 90
        with self.guard:
            while (self.processing or self.finals) and not self.failure and not (stop and stop.is_set()):
                if time.monotonic() >= deadline:
                    raise TimeoutError('La transcription prend trop de temps. Réessayez avec des phrases plus courtes.')
                self.guard.wait(.1)
            if self.failure:
                raise ValueError('La transcription a échoué. Réessayez.') from self.failure

    def ack(self, identifier):
        with self.guard:
            while self.turns and self.turns[0]['id'] <= identifier:
                self.turns.popleft()

    def reset_capture(self):
        """Discard an unfinished utterance and late decodes when muting."""
        with self.guard:
            self.capture_epoch += 1; self.finals.clear(); self.preview = None
            self.partial = ''; self.partial_speech_id = self.speech_id
            self.finalized = self.speech_id; self.guard.notify_all()
        self.speech = False; self.was_speech = False
        self.audio.clear(); self.preroll.clear(); self.audio_samples = 0
        self.next_check = 0; self.last_preview = 0; self.last_probability = None
        self.vad.reset()

    def status(self):
        with self.guard:
            if self.failure:
                raise ValueError('La transcription a échoué. Réessayez.') from self.failure
            return {'partial': self.partial, 'partial_speech_id': self.partial_speech_id,
                    'text': (self.committed + ' ' + self.partial).strip(), 'turns': list(self.turns),
                    'speech_id': self.speech_id, 'speaking': self.was_speech,
                    'turn_probability': self.last_probability, 'processing': self.processing or bool(self.finals),
                    'compute_seconds': round(self.compute, 4), 'model': 'Voxtral Realtime' if self.transcribe else 'Parakeet v3'}

    def close(self):
        with self.guard:
            self.closed = True; self.finals.clear(); self.preview = None; self.guard.notify_all()
        self.worker.join(timeout=3)
        self.audio.clear(); self.preroll.clear()
