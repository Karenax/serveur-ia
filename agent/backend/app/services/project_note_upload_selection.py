"""Bounded multipart selection, preserving relative names without disk extraction."""
from pathlib import PurePosixPath

from fastapi import HTTPException

from .project_note_source_preview import MAX_IMPORT_BYTES, MAX_IMPORT_FILES, MAX_TEXT_BYTES, OFFICE, LEGACY_TEXT, _path, _filename


def acquire_uploads(uploads, paths):
    if (not isinstance(paths, list) or not 1 <= len(paths) <= MAX_IMPORT_FILES
            or len(paths) != len(uploads) or any(not isinstance(name, str) for name in paths)
            or len({name.casefold() for name in paths}) != len(paths)):
        raise HTTPException(422, 'Sélection complète avec noms relatifs uniques requise (200 fichiers maximum)')
    limits = []
    try:
        for name in paths:
            suffix = PurePosixPath(name).suffix.casefold()
            if len(paths) == 1 and suffix in OFFICE | LEGACY_TEXT:
                _filename(name)
                maximum = MAX_IMPORT_BYTES if suffix in OFFICE | {'.html', '.htm'} else MAX_TEXT_BYTES
            else:
                kind = _path(name)
                maximum = 5 * 1024 * 1024 if kind == 'attachment' else MAX_IMPORT_BYTES if name.endswith('content.html') else MAX_TEXT_BYTES
            limits.append(maximum)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    files, total = {}, 0
    for name, upload, maximum in zip(paths, uploads, limits, strict=True):
        chunks, size = [], 0
        maximum = min(maximum, MAX_IMPORT_BYTES - total)
        while chunk := upload.file.read(min(64 * 1024, maximum + 1 - size)):
            if not isinstance(chunk, bytes):
                raise HTTPException(422, 'Octets de fichier requis')
            size += len(chunk)
            if size > maximum:
                raise HTTPException(413, 'Sélection dépassant les limites du contenu ou 50 Mio au total')
            chunks.append(chunk)
        files[name] = b''.join(chunks)
        total += size
    return files
