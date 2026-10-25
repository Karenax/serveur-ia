"""Authenticated distribution of a signed optional voice runtime, outside the base EXE."""
import hashlib
import json
from pathlib import Path
from core import ROOT
from signing import public
from max_installation import verify_catalogue

DIRECTORY = ROOT/'toolchain/voice-max-release'
_cache = {}


def package(home, directory=None):
    folder = Path(directory) if directory else DIRECTORY
    try:
        raw = (folder/'release.json').read_bytes()
        catalogue = verify_catalogue(json.loads(raw), public(home, create=False))
        source = folder/'runtime.zip'
        stat = source.stat()
        identity = (str(source), hashlib.sha256(raw).hexdigest(), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if identity not in _cache:
            if stat.st_size != catalogue['runtime']['bytes']:
                raise ValueError('Taille du complément différente du catalogue.')
            with source.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != catalogue['runtime']['sha256']:
                    raise ValueError('Complément vocal altéré.')
            _cache.clear(); _cache[identity] = True
        return catalogue, source
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError('Le complément Max n’est pas encore disponible sur ce serveur. Réessayez plus tard.') from error
