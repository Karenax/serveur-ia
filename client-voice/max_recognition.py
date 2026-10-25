"""Max-only progressive ingress and cancellable end-of-turn preparation.

The Low Recognizer is deliberately unchanged. Smart Turn still controls the
endpoint; Max holds an unanswered final briefly to join a resumed phrase.
"""
import secrets
import time
from recognition import Recognizer, RATE


class MaxRecognizer(Recognizer):
    minimum_silence=.85
    maximum_silence=2.4
    turn_threshold=.8

    def __init__(self, models, transcribe, model_name='Parakeet v3 · progressif'):
        self.max_transcribe = transcribe
        self.pending_final = None
        self.prefix = ''
        self.last_speech_end = None
        self.speech_ends={}
        self.model_name=model_name
        self.ingress_key = None
        self.ingress_offset = 0
        self.ingress_id = None
        super().__init__(models, transcribe=self._progressive)

    def _progressive(self, audio):
        # The decoder thread alone owns the incremental cursor. If previews
        # are superseded, send the entire new delta, never drop captured audio.
        identifier = self.decoding_id
        if identifier != self.ingress_id:
            self.ingress_id = identifier
            self.ingress_key = secrets.token_hex(16)
            self.ingress_offset = 0
        offset = min(self.ingress_offset, max(0, len(audio)-1))
        text = self.max_transcribe(audio[offset:], utterance=self.ingress_key,
                                   offset=offset, final=self.decoding_final)
        self.ingress_offset = len(audio)
        return text

    def _frame(self, audio):
        super()._frame(audio)
        if self.was_speech:
            self.last_speech_end = time.time()
            self.speech_ends[self.speech_id]=(self.last_speech_end,time.monotonic())
            while len(self.speech_ends)>16:self.speech_ends.pop(next(iter(self.speech_ends)))
        self._release()

    def _release(self):
        with self.guard:
            candidate = self.pending_final
            if not candidate:
                return
            # A continuation can already be captured and waiting for ASR after
            # its VAD segment ended. Do not release the earlier half meanwhile.
            if self.speech_id > candidate['speech_id']:
                self.prefix = (self.prefix+' '+candidate['text']).strip()[:6000]
                self.pending_final = None
            elif time.monotonic() >= candidate['release_at']:
                self.turn_id += 1
                self.turns.append({'id': self.turn_id, 'text': (self.prefix+' '+candidate['text']).strip()[:6000],
                                   'speech_id': candidate['speech_id'], 'latency': candidate['latency']})
                self.prefix = ''; self.pending_final = None

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
                    self.decoding_id = identifier; self.decoding_final = final
                    speech_end,end_clock = self.speech_ends.get(identifier,(self.last_speech_end,None))
                started = time.perf_counter()
                text = self.transcribe(audio).strip()[:6000]
                elapsed = time.perf_counter()-started
                with self.guard:
                    self.compute += elapsed
                    if self.closed:
                        return
                    if epoch != self.capture_epoch:
                        self.processing = False; self.guard.notify_all(); continue
                    if final:
                        self.finalized = identifier
                        if text or self.prefix:
                            # Speculation is restricted to ASR. No dialogue,
                            # external tool, history write or audio is released
                            # before the turn has settled.
                            if self.pending_final:
                                self.prefix = (self.prefix+' '+self.pending_final['text']).strip()[:6000]
                            self.pending_final = {'text': text, 'speech_id': identifier,
                                'release_at': max(time.monotonic(),(end_clock or time.monotonic())+1.05),
                                'latency': {'speech_end_unix_ms': speech_end*1000 if speech_end else None,
                                            'stt_final_ms': elapsed*1000, 'transcript_unix_ms': time.time()*1000}}
                        if self.partial_speech_id <= identifier:
                            self.partial = ''
                    elif identifier > self.finalized and identifier == self.speech_id:
                        self.partial = (self.prefix+' '+text).strip(); self.partial_speech_id = identifier
                    self.processing = False; self.guard.notify_all()
        except Exception as error:
            with self.guard:
                self.failure = error; self.processing = False; self.guard.notify_all()

    def reset_capture(self):
        super().reset_capture()
        with self.guard:
            self.pending_final = None; self.prefix = ''; self.last_speech_end = None
            self.speech_ends.clear()
        # Force a fresh owner key for the next decoder request. Old requests
        # remain filtered by the capture epoch in the decoder thread.
        self.ingress_id = None

    def status(self):
        self._release()
        value = super().status()
        value['model'] = self.model_name
        value['processing'] = value['processing'] or self.pending_final is not None
        return value

    def drain(self, stop=None):
        super().drain(stop)
        deadline = time.monotonic()+.4
        while self.pending_final and time.monotonic() < deadline and not (stop and stop.is_set()):
            self._release(); time.sleep(.01)
