"""Managed note attachments. Caller commits; failed copies are retained.

No file path comes from a command. Uploads never overwrite an existing blob,
and a committed retry returns the original attachment without another copy.
Downloads freeze verified bytes before the response; only decoded images may
be rendered inline. Office and other attachments remain downloads.
"""
import hashlib
import os
import stat
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select

from ..db import APP_DIR
from ..project_identity_models import now, uid
from ..project_note_models import NoteAttachment
from . import project_notes as notes
from .deliverable_files import _filename
from .project_identity import _project
from .project_note_binary import MAX_BYTES, IMAGE_TYPES, image, content_type
from .project_note_binary import MAX_PIXELS as MAX_PIXELS, DOWNLOAD_TYPES as DOWNLOAD_TYPES

MAX_TOTAL_BYTES = MAX_BYTES


def _command_id(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(422, 'Identifiant de commande UUID canonique requis') from exc
    return value


def _bounded_bytes(stream):
    chunks, total = [], 0
    while chunk := stream.read(min(64 * 1024, MAX_BYTES + 1 - total)):
        if not isinstance(chunk, bytes):
            raise HTTPException(422, 'Contenu binaire requis')
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_BYTES:
            raise HTTPException(413, 'Cette pièce jointe dépasse le quota total de la note (25 Mio)')
    if not total:
        raise HTTPException(422, 'La pièce jointe est vide')
    return b''.join(chunks)


def _image(data, expected_format):
    try:
        return image(data, expected_format)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _content_type(filename, data):
    try:
        return content_type(filename, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _path(storage_id, *, create=False):
    # Generated UUIDs, rather than filenames or command IDs, identify blobs.
    _command_id(storage_id)
    try:
        base = APP_DIR.resolve()
        root = base / 'note-files'
        folder = root / storage_id
        path = folder / 'blob'
        for component in (root, folder, path):
            if component.is_symlink() or (component.exists() and component.is_junction()):
                raise HTTPException(409, 'Stockage de notes redirigé ; rétablir la copie gérée')
        if not path.resolve().is_relative_to(base):
            raise HTTPException(409, 'Stockage de notes hors de la base Agent')
        if create:
            root.mkdir(exist_ok=True)
            folder.mkdir(exist_ok=False)
        return path
    except (OSError, ValueError) as exc:
        raise HTTPException(409, 'Stockage des pièces jointes indisponible') from exc


def _metadata(row):
    return {'id': row.id, 'project_id': row.project_id, 'note_id': row.note_id,
            'filename': row.filename, 'content_type': row.content_type,
            'size_bytes': row.size_bytes, 'sha256': row.sha256,
            'actor_id': row.actor_id, 'created_at': notes.utc_iso(row.created_at)}


def upload(db, project_id, note_id, *, command_id, filename, stream):
    _project(db, project_id, write=True)
    notes._ready(db, write=True)
    notes._head(db, project_id, note_id)
    actor = notes._actor()
    command_id, filename = _command_id(command_id), _filename(filename)
    data = _bounded_bytes(stream)
    mime, digest = _content_type(filename, data), hashlib.sha256(data).hexdigest()
    notes._lock(db)
    notes._detail(db, notes._head(db, project_id, note_id))
    previous = db.scalar(select(NoteAttachment).where(NoteAttachment.note_id == note_id,
                                                      NoteAttachment.command_id == command_id))
    if previous is not None:
        if (previous.project_id, previous.actor_id, previous.filename, previous.content_type,
                previous.size_bytes, previous.sha256) != (project_id, actor, filename, mime, len(data), digest):
            raise HTTPException(409, 'Commande de pièce jointe déjà utilisée avec un autre contenu')
        # Do not acknowledge a stored attachment whose actual blob is missing.
        download(db, project_id, note_id, previous.id)
        return {'attachment': _metadata(previous), 'replayed': True}
    count, size = db.execute(select(func.count(), func.coalesce(func.sum(NoteAttachment.size_bytes), 0))
                            .where(NoteAttachment.note_id == note_id)).one()
    if count >= 20 or size + len(data) > MAX_TOTAL_BYTES:
        raise HTTPException(413, 'Limite de 20 pièces jointes et 25 Mio par note atteinte')
    row = NoteAttachment(id=uid(), project_id=project_id, note_id=note_id, storage_id=uid(),
                         filename=filename, content_type=mime, size_bytes=len(data), sha256=digest,
                         command_id=command_id, actor_id=actor, created_at=now())
    path = _path(row.storage_id, create=True)
    try:
        with path.open('xb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except OSError as exc:
        raise HTTPException(409, 'Copie de pièce jointe impossible ; aucun ajout enregistré') from exc
    db.add(row)
    db.flush()
    return {'attachment': _metadata(row), 'replayed': False}


def listing(db, project_id, note_id):
    _project(db, project_id)
    notes._ready(db, write=True)
    notes._detail(db, notes._head(db, project_id, note_id))
    rows = db.scalars(select(NoteAttachment).where(NoteAttachment.project_id == project_id,
                      NoteAttachment.note_id == note_id).order_by(NoteAttachment.created_at, NoteAttachment.id))
    return {'items': [_metadata(row) for row in rows]}


def download(db, project_id, note_id, attachment_id, *, inline=False):
    _project(db, project_id)
    notes._ready(db, write=True)
    notes._head(db, project_id, note_id)
    row = db.get(NoteAttachment, attachment_id)
    if row is None or (row.project_id, row.note_id) != (project_id, note_id):
        raise HTTPException(404, 'Pièce jointe introuvable dans cette note')
    filename = _filename(row.filename)
    if inline and row.content_type not in {value[1] for value in IMAGE_TYPES.values()}:
        raise HTTPException(422, 'Seules les images gérées peuvent être affichées dans la note')
    path = _path(row.storage_id)
    try:
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
                raise HTTPException(409, 'Fichier de pièce jointe non valide')
            data = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        if ((before.st_size, before.st_mtime_ns, before.st_ino) !=
                (after.st_size, after.st_mtime_ns, after.st_ino)
                or len(data) != row.size_bytes or hashlib.sha256(data).hexdigest() != row.sha256
                or _content_type(filename, data) != row.content_type):
            raise HTTPException(409, 'Pièce jointe modifiée ; rétablir la copie originale')
    except OSError as exc:
        raise HTTPException(409, 'Pièce jointe indisponible ; conserver son historique et rétablir la copie') from exc
    return data, _metadata(row)
