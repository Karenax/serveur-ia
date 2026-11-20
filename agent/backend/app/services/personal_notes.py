"""Notes owned by the authenticated operator, with the shared rich-note format."""
from hashlib import sha256
from io import BytesIO
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import func, select, text

from ..models import Project
from ..personal_note_models import PersonalNote, PersonalNoteImage, PersonalNoteVersion
from ..project_identity_models import now, uid
from ..project_note_schemas import ImageBlock, NoteContent, NoteCreate, NoteSave, content_text
from . import note_clipboard, project_note_files, project_notes
from .project_operator import current_operator, require_project_access

SCOPE = 'personal'


def _head(db, note_id, *, include_deleted=False):
    item = db.get(PersonalNote, note_id)
    if item is None or item.owner_id != current_operator().id:
        raise HTTPException(404, 'Note personnelle introuvable')
    if not include_deleted and _version(db, item, item.current_version_id).operation == 'delete':
        raise HTTPException(404, 'Note personnelle introuvable')
    return item


def _version(db, head, version_id):
    row = db.get(PersonalNoteVersion, version_id)
    if row is None or (row.note_id, row.owner_id) != (head.id, head.owner_id):
        raise HTTPException(404, 'Version de note introuvable')
    return row


def _summary(head):
    return {'id': head.id, 'project_id': SCOPE, 'title': head.title, 'revision': head.revision,
            'version_id': head.current_version_id, 'updated_at': project_notes.utc_iso(head.updated_at),
            'actor_id': head.owner_id}


def _detail(db, head):
    row = _version(db, head, head.current_version_id)
    return {**_summary(head), 'content': row.content, 'plain_text': head.plain_text, 'attachment_ids': row.attachment_ids,
            'read_only': False, 'source_kind': None}


def read(db, note_id):
    return _detail(db, _head(db, note_id))


def listing(db, query, limit, offset):
    operator = current_operator()
    current = PersonalNote.current_version_id == PersonalNoteVersion.id
    terms = [PersonalNote.owner_id == operator.id, PersonalNoteVersion.operation != 'delete']
    folded = project_notes.fold_query(query)
    if folded:
        terms.append(func.agent_fold(PersonalNote.title + '\n' + PersonalNote.plain_text).contains(folded, autoescape=True))
    count = db.scalar(select(func.count()).select_from(PersonalNote).join(PersonalNoteVersion, current).where(*terms))
    rows = db.execute(select(PersonalNote, func.json_extract(PersonalNoteVersion.content, '$.background'))
                      .join(PersonalNoteVersion, current).where(*terms)
                      .order_by(PersonalNote.updated_at.desc(), PersonalNote.id).limit(limit).offset(offset))
    return {'available': True, 'can_edit': operator.role != 'reader', 'operator_id': operator.id,
            'total': count, 'limit': limit, 'offset': offset,
            'items': [{**_summary(row), 'excerpt': row.plain_text[:240], 'background': background} for row, background in rows]}


def _history_item(row):
    return {'id': row.id, 'revision': row.revision, 'actor_id': row.owner_id,
            'created_at': project_notes.utc_iso(row.created_at), 'title': row.title, 'operation': row.operation}


def history(db, note_id, limit, offset):
    head = _head(db, note_id)
    condition = PersonalNoteVersion.note_id == head.id
    count = db.scalar(select(func.count()).select_from(PersonalNoteVersion).where(condition))
    rows = db.scalars(select(PersonalNoteVersion).where(condition).order_by(PersonalNoteVersion.revision.desc())
                      .limit(limit).offset(offset))
    return {'total': count, 'limit': limit, 'offset': offset, 'items': [_history_item(row) for row in rows]}


def version(db, note_id, version_id):
    row = _version(db, _head(db, note_id), version_id)
    return {**_history_item(row), 'project_id': SCOPE, 'note_id': note_id,
            'attachment_bindings': {key: key for key in row.attachment_ids},
            'value': {'title': row.title, 'content': row.content}}


def _image(db, head, attachment_id):
    row = db.get(PersonalNoteImage, attachment_id)
    if row is None or row.note_id != head.id:
        raise HTTPException(404, 'Image introuvable dans cette note')
    return row


def read_image(db, note_id, attachment_id):
    row = _image(db, _head(db, note_id), attachment_id)
    data = row.data
    if len(data) != row.size_bytes or sha256(data).hexdigest() != row.sha256:
        raise HTTPException(409, 'Image endommagée')
    return data, {'filename': row.filename, 'content_type': row.content_type, 'sha256': row.sha256}


def _result(db, row, *, replayed):
    return {'note': read(db, row.note_id), 'command_id': row.command_id,
            'command_revision': row.revision, 'replayed': replayed}


def save(db, note_id, payload, *, restore=False, image=None):
    owner = current_operator()
    if owner.role == 'reader':
        raise HTTPException(403, 'Opérateur en lecture seule')
    # Serialize revision checks and command receipts before any read transaction.
    db.execute(text('UPDATE personal_notes SET revision=revision WHERE 0'))
    head = _head(db, note_id) if note_id is not None else None
    operation = 'restore' if restore else 'create' if head is None else 'save'
    image_key = image[:3] if image else None
    digest = project_notes.freeze([note_id, operation, payload.model_dump(mode='json'), image_key])[1]
    previous = db.scalar(select(PersonalNoteVersion).where(PersonalNoteVersion.owner_id == owner.id,
                         PersonalNoteVersion.command_id == payload.command_id))
    if previous:
        if previous.command_digest != digest:
            raise HTTPException(409, 'Commande déjà utilisée pour une autre saisie')
        return _result(db, previous, replayed=True)

    expected = getattr(payload, 'expected_revision', 0)
    revision = head.revision if head else 0
    if expected != revision:
        project_notes._error()
    if restore:
        previous_version = _version(db, head, payload.version_id)
        title, content = previous_version.title, NoteContent.model_validate(previous_version.content)
        attachment_ids = list(previous_version.attachment_ids)
    else:
        title, content = payload.title, payload.content
        attachment_ids = list(getattr(payload, 'attachment_ids', []))
    if (not head and attachment_ids) or any(isinstance(block, ImageBlock) and block.attachment_id not in attachment_ids
                                            for block in content.blocks):
        raise HTTPException(422, 'Chaque image doit appartenir à la note')
    for attachment_id in attachment_ids:
        _image(db, head, attachment_id)

    timestamp = now()
    version_id = uid()
    if head is None:
        head = PersonalNote(id=uid(), owner_id=owner.id)
    if image:
        filename, mime, checksum, data = image
        count, size = db.execute(select(func.count(), func.coalesce(func.sum(PersonalNoteImage.size_bytes), 0))
                                .where(PersonalNoteImage.note_id == head.id)).one()
        if count >= 20 or size + len(data) > project_note_files.MAX_TOTAL_BYTES:
            raise HTTPException(413, 'Limite de 20 pièces jointes et 25 Mio par note atteinte')
        attachment_id = uid()
        content = note_clipboard.with_image(payload, attachment_id)
        attachment_ids.append(attachment_id)

    head.title, head.plain_text, head.revision = title, content_text(content), revision+1
    head.current_version_id, head.updated_at = version_id, timestamp
    db.add(head)
    db.flush()
    if image:
        db.add(PersonalNoteImage(id=attachment_id, note_id=head.id, filename=filename,
                                 content_type=mime, size_bytes=len(data), sha256=checksum, data=data))
    row = PersonalNoteVersion(id=version_id, note_id=head.id, owner_id=owner.id, revision=head.revision,
                              command_id=payload.command_id, command_digest=digest, title=title,
                              content=content.model_dump(mode='json'), attachment_ids=attachment_ids,
                              operation=operation, created_at=timestamp)
    db.add(row)
    db.flush()
    return _result(db, row, replayed=False)


def delete(db, note_id, payload):
    owner = current_operator()
    if owner.role == 'reader':
        raise HTTPException(403, 'Opérateur en lecture seule')
    db.execute(text('UPDATE personal_notes SET revision=revision WHERE 0'))
    db.expire_all()
    head = _head(db, note_id, include_deleted=True)
    current = _version(db, head, head.current_version_id)
    digest = project_notes.freeze([note_id, 'delete', payload.model_dump(mode='json')])[1]
    if current.operation == 'delete':
        if current.command_id == payload.command_id and current.command_digest == digest:
            return {'deleted': True}
        raise HTTPException(404, 'Note personnelle introuvable')
    if head.revision != payload.expected_revision:
        project_notes._error()
    version_id, timestamp = uid(), now()
    head.current_version_id, head.updated_at, head.revision = version_id, timestamp, head.revision + 1
    db.add(PersonalNoteVersion(id=version_id, note_id=head.id, owner_id=owner.id, revision=head.revision,
                               command_id=payload.command_id, command_digest=digest, title=head.title,
                               content=current.content, attachment_ids=current.attachment_ids,
                               operation='delete', created_at=timestamp))
    db.flush()
    return {'deleted': True}


def copy_to_project(db, note_id, project_id, version_id):
    require_project_access(project_id, write=True)
    project_notes._ready(db, write=True)
    project_notes._lock(db)
    project = db.get(Project, project_id)
    if project is None or project.status != 'active':
        raise HTTPException(404, 'Projet actif introuvable')
    head = _head(db, note_id)
    row = _version(db, head, version_id)
    content = NoteContent.model_validate(row.content)
    # Keep the private original and let the project's canonical note/attachment APIs own the copy.
    base_content = NoteContent(background=content.background, blocks=[block for block in content.blocks if not isinstance(block, ImageBlock)])
    create_id = str(uuid5(NAMESPACE_URL, f'kiara-copy-note:{project_id}:{version_id}'))
    result = project_notes.create_note(db, project_id, NoteCreate(command_id=create_id, title=row.title,
                                                                 content=base_content))
    if not row.attachment_ids:
        return result['note']
    target_id = result['note']['id']
    bindings = {}
    for index, source_id in enumerate(row.attachment_ids):
        data, asset = read_image(db, note_id, source_id)
        uploaded = project_note_files.upload(db, project_id, target_id, command_id=note_clipboard.attachment_command(create_id, index),
                                             filename=asset['filename'], stream=BytesIO(data))
        bindings[source_id] = uploaded['attachment']['id']
    for block in content.blocks:
        if isinstance(block, ImageBlock):
            block.attachment_id = bindings[block.attachment_id]
    return project_notes.save_note(db, project_id, target_id, NoteSave(command_id=note_clipboard.attachment_command(create_id, -1),
        title=row.title, content=content, expected_revision=1, attachment_ids=list(bindings.values())))['note']
