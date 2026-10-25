"""French streaming speech for Max, independent of the Low server service."""
import json
from pathlib import Path
import time
import numpy as np


class PhononVoice:
    def __init__(self,root):
        import ptts
        folder=Path(root)/'tts'
        self.spec=json.loads((folder/'phonon-model.json').read_text(encoding='utf-8'))
        if ptts.__version__!=self.spec['runtime'] or self.spec['language']!='fr':
            raise ValueError('La voix française Max doit être mise à jour.')
        ptts.set_num_threads(4)
        self.model=ptts.TTS(str(folder),lang='fr',device='cpu',quant=self.spec['quant'],voice='default',voice_catalog=str(folder))
        self.model.add_voice(self.spec['voice'],str(folder/self.spec['voice_file']))
        if self.model.sample_rate!=24000:raise ValueError('Le format de la voix Max est incompatible.')

    def stream(self,text,cancelled):
        started=time.perf_counter();first=None;samples=0
        with self.model.stream(text,voice=self.spec['voice']) as audio:
            for chunk in audio:
                if cancelled.is_set():break
                values=np.asarray(chunk,dtype=np.float32).reshape(-1)
                if not np.isfinite(values).all():raise ValueError('Le son Max est invalide. Réessayez.')
                samples+=len(values)
                if samples>90*24000:raise ValueError('La réponse vocale Max est trop longue.')
                if first is None:first=(time.perf_counter()-started)*1000
                raw=(np.clip(values,-1,1)*32767).astype('<i2').tobytes()
                for offset in range(0,len(raw),9600):
                    if cancelled.is_set():break
                    yield {'rate':24000,'raw_pcm':raw[offset:offset+9600]}
        if samples and not cancelled.is_set():
            elapsed=time.perf_counter()-started
            yield {'metrics':{'first_audio_ms':first,'elapsed_ms':elapsed*1000,'rtf':elapsed/(samples/24000)}}

    def close(self):self.model=None
