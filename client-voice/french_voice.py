"""One pinned French reference shared by the native and Python Max engines."""
import array
import hashlib
import json
from pathlib import Path
import sys
import wave


def reference(root):
    folder=Path(root)/'voices/fr-fr'
    try:
        spec=json.loads((folder/'reference.json').read_text(encoding='utf-8'))
        text=spec['text']
        if spec['locale']!='fr-FR' or not isinstance(text,str) or not 1<=len(text)<=1000:
            raise ValueError('Invalid French reference')
        if hashlib.sha256((folder/'reference.wav').read_bytes()).hexdigest()!=spec.get('audio_sha256'):
            raise ValueError('Corrupted French reference')
        with wave.open(str(folder/'reference.wav'),'rb') as source:
            count=source.getnframes()
            if (source.getnchannels()!=1 or source.getsampwidth()!=2 or source.getframerate()!=24000
                    or source.getcomptype()!='NONE' or not 3*24000<=count<=12*24000):
                raise ValueError('Invalid French reference audio')
            raw=source.readframes(count)
        if len(raw)!=count*2:raise ValueError('Truncated French reference')
        samples=array.array('h');samples.frombytes(raw)
        if sys.byteorder!='little':samples.byteswap()
        if max(abs(value) for value in samples)<100:raise ValueError('Silent French reference')
        return folder/'reference.wav',text,[value/32768 for value in samples]
    except (OSError,ValueError,KeyError,TypeError,wave.Error) as error:
        raise ValueError('La référence française de Max est absente ou invalide. Mettez le complément Max à jour.') from error
