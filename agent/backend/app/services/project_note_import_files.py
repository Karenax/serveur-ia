"""Managed immutable originals; no extraction, overwrite or orphan adoption."""
import hashlib
import os
import stat

from fastapi import HTTPException

from . import project_note_files as attachments
from .project_note_source_bundle import MAX_BUNDLE_BYTES, verify_bundle


def _path(storage_id, *, create=False):
    attachments._command_id(storage_id)
    try:
        base = attachments.APP_DIR.resolve()
        root = base / 'note-originals'
        folder = root / storage_id
        path = folder / 'blob.zip'
        for component in (root, folder, path):
            if component.is_symlink() or (component.exists() and component.is_junction()):
                raise HTTPException(409, 'Stockage des originaux redirigé')
        if not path.resolve().is_relative_to(base):
            raise HTTPException(409, 'Originaux hors du stockage Agent')
        if create:
            root.mkdir(exist_ok=True)
            folder.mkdir(exist_ok=False)
        return path
    except (OSError, ValueError) as exc:
        raise HTTPException(409, 'Stockage des originaux indisponible') from exc


def _write(path, data):
    try:
        with path.open('xb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except OSError as exc:
        # Preserve every partial copy. A retry allocates new storage IDs.
        raise HTTPException(409, 'Copie impossible ; aucun import validé en base') from exc


def write_originals(storage_id, data):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BUNDLE_BYTES:
        raise HTTPException(422, 'Conteneur original borné requis')
    _write(_path(storage_id, create=True), data)


def write_attachment(storage_id, data):
    _write(attachments._path(storage_id, create=True), data)


def read_originals(row, capture):
    try:
        with _path(row.storage_id).open('rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BUNDLE_BYTES:
                raise HTTPException(409, 'Conteneur original régulier borné requis')
            data = stream.read(MAX_BUNDLE_BYTES + 1)
            after = os.fstat(stream.fileno())
        if ((before.st_size, before.st_mtime_ns, before.st_ino) !=
                (after.st_size, after.st_mtime_ns, after.st_ino)
                or len(data) != row.size_bytes or hashlib.sha256(data).hexdigest() != row.sha256):
            raise HTTPException(409, 'Originaux modifiés ; rétablir leur copie exacte')
        return data, verify_bundle(data, capture.files)
    except (OSError, ValueError) as exc:
        raise HTTPException(409, 'Originaux absents ou invalides ; conserver leur historique') from exc
