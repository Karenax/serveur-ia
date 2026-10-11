"""Verified Android packages published by Build-Android.ps1."""
import hashlib
import json
import re
import threading
from pathlib import Path
from core import ROOT

DIRECTORY = ROOT / 'client-android/dist'
_lock = threading.Lock()
_cache = {}


def status(directory=None):
    directory = Path(directory) if directory is not None else DIRECTORY
    source = directory / 'Acces-serveur-Fred-Android.apk'
    try:
        release = json.loads((directory / 'release.json').read_text(encoding='utf-8-sig'))
        if (release.get('package') != 'net.karenax.fred'
                or not isinstance(release.get('version'), str)
                or not re.fullmatch(r'\d+\.\d+\.\d+', release['version'])
                or type(release.get('version_code')) is not int or release['version_code'] < 1
                or type(release.get('bytes')) is not int or not 1 <= release['bytes'] <= 128*1024*1024
                or not isinstance(release.get('sha256'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', release['sha256'])):
            raise ValueError('Manifeste Android invalide.')
        stat = source.stat()
        key = (str(source), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, release['sha256'])
        with _lock:
            if key not in _cache:
                with source.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                _cache.clear()
                _cache[key] = digest == release['sha256'] and stat.st_size == release['bytes']
            if not _cache[key]:
                raise ValueError('APK Android altéré ou incomplet.')
        return release, source
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError('Mise à jour Android absente ou invalide.') from error
