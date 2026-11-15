"""Reserve operational headroom before creating managed files; never delete."""
from pathlib import Path
import shutil

from fastapi import HTTPException

RESERVE_BYTES = 2 * 1024**3
WARNING_BYTES = 10 * 1024**3


def capacity(path, requested_bytes=0):
    target = Path(path).resolve()
    while not target.exists() and target != target.parent:
        target = target.parent
    free = shutil.disk_usage(target).free
    required = RESERVE_BYTES + max(0, requested_bytes)
    return {'free_bytes': free, 'reserve_bytes': RESERVE_BYTES, 'requested_bytes': requested_bytes,
            'required_bytes': required, 'sufficient': free >= required, 'warning': free < WARNING_BYTES}


def require_capacity(path, requested_bytes=0):
    state = capacity(path, requested_bytes)
    if not state['sufficient']:
        raise HTTPException(507, 'Espace disque insuffisant pour conserver ce fichier et la réserve de travail')
    return state
