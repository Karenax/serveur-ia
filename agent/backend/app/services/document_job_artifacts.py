"""Owned artifact bytes only. No network publication or untrusted output path."""
from app.operational_limits import DOCUMENT_IMPORT_BYTES
import hashlib
import os
from pathlib import Path
import stat
from uuid import UUID

from fastapi import HTTPException

MAX_BYTES = DOCUMENT_IMPORT_BYTES


def _directory(root):
    root = Path(root).absolute()
    for part in (root, *root.parents):
        if part.exists() and (part.is_symlink() or part.is_junction()):
            raise HTTPException(409, 'Le stockage documentaire ne doit pas suivre un lien')
    root.mkdir(parents=True, exist_ok=True)
    if root.resolve() != root:
        raise HTTPException(409, 'Stockage documentaire incohérent')
    return root


def _key(key):
    try:
        if str(UUID(key)) != key:
            raise ValueError
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(409, 'Identifiant de fichier documentaire invalide') from exc
    return key


def write_artifact(root, key, content):
    if not isinstance(content, bytes) or not 1 <= len(content) <= MAX_BYTES:
        raise HTTPException(413, 'Copie documentaire bornée à 50 Mio')
    directory = _directory(root)
    key = _key(key)
    temporary, destination = directory / (key + '.pending'), directory / key
    # Exclusive temporary creation + hard link finalize never replaces an old
    # file. An uncommitted candidate stays retained for explicit reconciliation.
    with temporary.open('xb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, destination)
    temporary.unlink()
    return {'storage_key': key, 'sha256': hashlib.sha256(content).hexdigest(), 'size_bytes': len(content)}


def read_artifact(root, artifact):
    path = Path(root).absolute() / _key(artifact.storage_key)
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise HTTPException(409, 'Lien dans le stockage documentaire refusé')
    try:
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size != artifact.size_bytes or not 1 <= before.st_size <= MAX_BYTES:
                raise HTTPException(409, 'Taille de copie documentaire modifiée')
            data = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or hashlib.sha256(data).hexdigest() != artifact.sha256):
            raise HTTPException(409, 'Empreinte de copie documentaire modifiée')
        return data
    except OSError as exc:
        raise HTTPException(409, 'Copie documentaire indisponible') from exc
