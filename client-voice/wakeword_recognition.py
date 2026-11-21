"""Tiny local keyword spotter. No speech transcription and no network transport."""
from pathlib import Path
import json
import hashlib
import time
import sherpa_onnx

WAKEWORD_FILES = frozenset({'tokens.txt', 'encoder.onnx', 'decoder.onnx', 'joiner.onnx', 'keywords.txt'})


class WakeWordRecognizer:
    def __init__(self,models):
        root=Path(models).resolve(strict=True)
        manifest = root / 'manifest.json'
        if manifest.resolve(strict=True) != manifest:
            raise ValueError('Emplacement de l’inventaire vocal invalide.')
        spec=json.loads(manifest.read_text(encoding='utf-8'))
        entries = spec.get('files') if isinstance(spec, dict) else None
        if (not isinstance(entries, list) or len(entries) != len(WAKEWORD_FILES)
                or any(not isinstance(entry, dict) or not isinstance(entry.get('name'), str) for entry in entries)
                or {entry['name'] for entry in entries} != WAKEWORD_FILES):
            raise ValueError('Inventaire du modèle d’activation vocale invalide. Réinstallez le client.')
        for entry in entries:
            path = root / entry['name']
            if path.resolve(strict=True) != path or not path.is_file():
                raise ValueError('Emplacement du modèle d’activation vocale invalide.')
            with path.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=entry.get('sha256'):
                    raise ValueError('Modèle d’activation vocale corrompu. Réinstallez le client.')
        self.spotter=sherpa_onnx.KeywordSpotter(tokens=str(root/'tokens.txt'),encoder=str(root/'encoder.onnx'),
            decoder=str(root/'decoder.onnx'),joiner=str(root/'joiner.onnx'),keywords_file=str(root/'keywords.txt'),
            num_threads=1,keywords_threshold=.4,keywords_score=1.5)
        self.stream=self.spotter.create_stream();self.turns=[];self.sequence=0;self.last=0

    def accept(self,audio):
        self.stream.accept_waveform(16000,audio)
        while self.spotter.is_ready(self.stream):
            self.spotter.decode_stream(self.stream)
            if self.spotter.get_result(self.stream):
                if time.monotonic()-self.last>2:
                    self.sequence+=1;self.turns.append({'id':self.sequence,'speech_id':self.sequence,'text':'Kiara'})
                    self.turns=self.turns[-4:];self.last=time.monotonic()
                self.spotter.reset_stream(self.stream)

    def status(self):return {'partial':'','text':'','turns':list(self.turns),'speech_id':self.sequence,'wakeword':True}
    def reset_capture(self):self.spotter.reset_stream(self.stream)
    def ack(self,sequence):self.turns=[t for t in self.turns if t['id']>sequence]
    def finish(self):self.stream.input_finished()
    def drain(self,*args):pass
    def close(self):self.stream=None;self.spotter=None
