"""Pinned local Phonon checkpoint; runtime loading never contacts the Hub."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'lanceur/phonon-model.json').read_text(encoding='utf-8'))
MODEL = ROOT / 'toolchain/phonon-models' / ('phonon-40m-fr-' + SPEC['revision'])


def verify(folder=MODEL):
    folder = Path(folder)
    for name, expected in SPEC['files'].items():
        path = folder / name
        if not path.is_file() or path.stat().st_size != expected['size']:
            raise ValueError('Fichier Phonon manquant ou incomplet : ' + name)
        data = path.read_bytes()
        if 'sha256' in expected:
            actual = hashlib.sha256(data).hexdigest()
            wanted = expected['sha256']
        else:
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            wanted = expected['git_sha1']
        if actual != wanted:
            raise ValueError('Empreinte Phonon incorrecte : ' + name)
    return folder


def load():
    import ptts
    if ptts.__version__ != SPEC['runtime']:
        raise ValueError('Version Phonon incorrecte.')
    folder = verify()
    ptts.set_num_threads(SPEC['threads'])
    model = ptts.TTS(str(folder), lang=SPEC['language'], device='cpu',
                     quant=SPEC['quant'], voice=SPEC['voice'], voice_catalog=str(folder))
    if model.device != 'cpu' or model.sample_rate != 24000 or 'fr' not in model.languages:
        raise ValueError('Configuration Phonon française CPU incorrecte.')
    return model
