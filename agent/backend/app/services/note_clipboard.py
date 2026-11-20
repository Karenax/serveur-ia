"""Validate pasted images and save them together with the note revision."""
from hashlib import sha256
from io import BytesIO
from uuid import uuid5, NAMESPACE_URL

from fastapi import HTTPException
from sqlalchemy import select

from ..project_identity_models import uid
from ..project_note_models import NoteAttachment, NoteVersion
from ..project_note_schemas import ImageBlock, NoteContent, NoteCreate, NoteSave, Paragraph
from . import project_note_files as files, project_notes as notes
from .project_identity import _project


def read_image(filename, stream):
    filename = files._filename(filename)
    data = files._bounded_bytes(stream)
    mime = files._content_type(filename, data)
    if mime not in {value[1] for value in files.IMAGE_TYPES.values()}:
        raise HTTPException(422, 'Collez une image PNG, JPEG ou WebP')
    return filename, mime, sha256(data).hexdigest(), data


def with_image(payload, attachment_id):
    blocks = list(payload.content.blocks)
    blocks.insert(payload.insert_at, ImageBlock(type='image', attachment_id=attachment_id, caption=''))
    if payload.insert_at == len(blocks)-1 and len(blocks) < 500:
        blocks.append(Paragraph(type='paragraph'))
    return NoteContent(background=payload.content.background, blocks=blocks)


def attachment_command(command_id, index=0):
    return str(uuid5(NAMESPACE_URL, f'kiara-note-attachment:{command_id}:{index}'))


def paste_project(db, project_id, note_id, payload, image):
    _project(db, project_id, write=True)
    notes._ready(db, write=True)
    filename, _, _, data = image
    if note_id is None and (payload.expected_revision != 0 or payload.attachment_ids):
        raise HTTPException(422, 'La nouvelle note doit recevoir ses propres pièces jointes')
    if len(payload.attachment_ids) >= 20:
        raise HTTPException(413, 'La note contient déjà 20 pièces jointes')
    with_image(payload, uid())  # Validate the size before creating a file.
    notes._lock(db)
    revision = payload.expected_revision
    if note_id is None:
        created = notes.create_note(db, project_id, NoteCreate(command_id=attachment_command(payload.command_id, -1),
                                    title=payload.title, content=payload.content))
        note_id, revision = created['note']['id'], 1
    head = notes._head(db, project_id, note_id)
    previous = db.scalar(select(NoteVersion).where(NoteVersion.project_id == project_id,
                         NoteVersion.command_id == payload.command_id))
    if previous is None and head.revision != revision:
        notes._error()
    upload_id = attachment_command(payload.command_id)
    if previous is not None and (previous.note_id != note_id or not db.scalar(select(NoteAttachment.id).where(
            NoteAttachment.note_id == note_id, NoteAttachment.command_id == upload_id))):
        notes._error('Commande déjà utilisée pour une autre saisie')
    if notes._detail(db, head)['read_only']:
        raise HTTPException(409, 'Le document Office original reste en consultation')
    notes._attachments(db, project_id, note_id, payload.content, payload.attachment_ids)
    uploaded = files.upload(db, project_id, note_id, command_id=upload_id,
                            filename=filename, stream=BytesIO(data))
    attachment_id = uploaded['attachment']['id']
    return notes.save_note(db, project_id, note_id, NoteSave(
        command_id=payload.command_id, expected_revision=revision, title=payload.title,
        content=with_image(payload, attachment_id), attachment_ids=[*payload.attachment_ids, attachment_id]))
