"""Canonical rich notes and immutable versions. Callers commit/rollback commands.

No DDL, file/Office/network calls, seeding or implicit imports. Attachments and
transport are integrated separately; a captured historical nonce cannot execute.
"""
from copy import deepcopy
import unicodedata
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.sqlite import insert

from app.db_support import utc_iso
from app.services.deliverable_manifest import freeze
from ..project_note_models import ProjectNote, NoteVersion, NoteAttachment, NoteSourceImport
from ..project_note_schemas import ImageBlock, NoteContent, NoteCreate, NoteSave, NoteRestore, content_text
from ..project_identity_models import now, uid
from .project_identity import _project
from .project_note_schema import validate_note_schema
from .project_note_history import version_value
from .project_operator import current_operator


def _error(message='La note a changé ; comparez les versions avant de réessayer'):
    raise HTTPException(409, message)


def _ready(db, *, write=False):
    try:
        plan = validate_note_schema(db.connection())
    except ValueError as exc:
        _error(str(exc))
    available = not plan['created_tables'] and not plan['created_triggers']
    if write and not available:
        _error('Installation protégée des notes requise')
    return available


def _lock(db):
    db.execute(text('UPDATE project_notes SET revision=revision WHERE 0'))
    db.expire_all()


def _actor():
    value = current_operator().id
    if not isinstance(value, str) or not 1 <= len(value) <= 120:
        raise HTTPException(422, 'Identifiant opérateur incompatible avec les notes')
    return value


def _head(db, project_id, note_id):
    head = db.get(ProjectNote, note_id)
    if head is None or head.project_id != project_id:
        raise HTTPException(404, 'Note introuvable')
    return head


def _identity(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError('Identifiant historique non canonique')
    return value


def _value(version):
    try:
        return version_value({column.name: getattr(version, column.name) for column in NoteVersion.__table__.c})
    except (ValueError, TypeError, KeyError, ValidationError):
        _error('Intégrité de la version de note invalide')


def _detail(db, head):
    version = db.get(NoteVersion, head.current_version_id)
    if version is None or (version.project_id, version.note_id, version.revision) != (head.project_id, head.id, head.revision):
        _error('Historique de note incomplet')
    value = _value(version)
    if value['title'] != head.title or value['plain_text'] != head.plain_text:
        _error('La note diffère de sa version enregistrée')
    content, attachments = _bound_content(version, value)
    _attachments(db, head.project_id, head.id, content, attachments)
    origin = db.scalar(select(NoteSourceImport).where(NoteSourceImport.note_id == head.id,
                                                    NoteSourceImport.project_id == head.project_id))
    return {'id': head.id, 'project_id': head.project_id, 'title': head.title, 'revision': head.revision,
            'version_id': version.id, 'sha256': version.sha256, 'content': content.model_dump(mode='json'),
            'captured_content': value['content'], 'attachment_bindings': version.attachment_bindings,
            'plain_text': value['plain_text'], 'attachment_ids': attachments,
            'actor_id': version.actor_id, 'created_at': utc_iso(head.created_at), 'updated_at': utc_iso(head.updated_at),
            'source_kind': origin.source_kind if origin else None, 'read_only': bool(origin and origin.source_kind == 'external_office')}


def read_note(db, project_id, note_id):
    _project(db, project_id)
    if not _ready(db):
        raise HTTPException(404, 'Notes non installées')
    return _detail(db, _head(db, project_id, note_id))


def _page(limit, offset):
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or not 0 <= offset <= 10000:
        raise HTTPException(422, 'Pagination bornée requise')


def fold_query(query):
    return ''.join(char for char in unicodedata.normalize('NFKD', query.strip().casefold())
                   if not unicodedata.combining(char))


def list_notes(db, project_id, *, query='', limit=30, offset=0):
    _project(db, project_id)
    _page(limit, offset)
    if not isinstance(query, str) or len(query) > 200:
        raise HTTPException(422, 'Recherche limitée à 200 caractères')
    if not _ready(db):
        return {'available': False, 'items': [], 'total': 0, 'limit': limit, 'offset': offset}
    folded = fold_query(query)
    conditions = [ProjectNote.project_id == project_id]
    if folded:
        conditions.append(func.agent_fold(ProjectNote.title + '\n' + ProjectNote.plain_text).contains(folded, autoescape=True))
    total = db.scalar(select(func.count()).select_from(ProjectNote).where(*conditions))
    items = []
    for head in db.scalars(select(ProjectNote).where(*conditions).order_by(ProjectNote.updated_at.desc(), ProjectNote.id).limit(limit).offset(offset)):
        value = _detail(db, head)
        items.append({key: value[key] for key in ('id', 'project_id', 'title', 'revision', 'version_id', 'updated_at', 'actor_id')}
                     | {'excerpt': value['plain_text'][:240]})
    operator = current_operator()
    return {'available': True, 'items': items, 'total': total, 'limit': limit, 'offset': offset,
            'can_edit': operator.role != 'reader', 'operator_id': operator.id}


def history(db, project_id, note_id, *, limit=30, offset=0):
    _project(db, project_id)
    _page(limit, offset)
    if not _ready(db):
        raise HTTPException(404, 'Notes non installées')
    _detail(db, _head(db, project_id, note_id))
    conditions = (NoteVersion.project_id == project_id, NoteVersion.note_id == note_id)
    total = db.scalar(select(func.count()).select_from(NoteVersion).where(*conditions))
    rows = db.scalars(select(NoteVersion).where(*conditions).order_by(NoteVersion.revision.desc()).limit(limit).offset(offset))
    items = []
    for row in rows:
        value = _value(row)
        items.append({'id': row.id, 'revision': row.revision, 'sha256': row.sha256,
            'actor_id': row.actor_id, 'created_at': utc_iso(row.created_at), 'title': value['title'],
            'operation': value['operation'], 'restored_from': value['restored_from'],
            'restored_version_id': row.restored_version_id})
    return {'total': total, 'items': items, 'limit': limit, 'offset': offset}


def read_version(db, project_id, note_id, version_id):
    _project(db, project_id)
    if not _ready(db):
        raise HTTPException(404, 'Notes non installées')
    _detail(db, _head(db, project_id, note_id))
    row = db.get(NoteVersion, version_id)
    if row is None or (row.project_id, row.note_id) != (project_id, note_id):
        raise HTTPException(404, 'Version de note introuvable')
    return {'id': row.id, 'project_id': project_id, 'note_id': note_id, 'revision': row.revision,
            'sha256': row.sha256, 'actor_id': row.actor_id, 'created_at': utc_iso(row.created_at),
            'value': _value(row), 'attachment_bindings': row.attachment_bindings, 'restored_version_id': row.restored_version_id}


def _command_digest(project_id, note_id, operation, payload, actor):
    return freeze({'project_id': project_id, 'note_id': note_id, 'operation': operation,
                   'payload': payload.model_dump(mode='json'), 'actor_id': actor})[1]


def _response(db, version, *, replayed):
    _value(version)
    return {'note': _detail(db, _head(db, version.project_id, version.note_id)),
            'command_id': version.command_id, 'command_revision': version.revision,
            'command_version_id': version.id, 'command_sha256': version.sha256, 'replayed': replayed}


def _replay(db, project_id, command_id, digest, actor):
    if db.scalar(select(NoteSourceImport.id).where(NoteSourceImport.project_id == project_id,
                                                 NoteSourceImport.command_id == command_id)):
        _error('Cette commande appartient à un import ; utiliser son parcours de reprise')
    previous = db.scalar(select(NoteVersion).where(NoteVersion.project_id == project_id, NoteVersion.command_id == command_id))
    if previous is None:
        return None
    if previous.execution_blocked or previous.command_sha256 != digest or previous.actor_id != actor:
        _error('Commande déjà utilisée ou historique importé ; conserver la saisie et créer une nouvelle commande')
    return _response(db, previous, replayed=True)


def _attachments(db, project_id, note_id, content, ids):
    images = {block.attachment_id for block in content.blocks if isinstance(block, ImageBlock)}
    if not images.issubset(ids):
        raise HTTPException(422, 'Chaque image doit référencer une pièce jointe de la note')
    for attachment_id in ids:
        row = db.get(NoteAttachment, attachment_id)
        if row is None or (row.project_id, row.note_id) != (project_id, note_id):
            raise HTTPException(422, 'Pièce jointe absente de cette note')
        if attachment_id in images and row.content_type not in {'image/png', 'image/jpeg', 'image/webp'}:
            raise HTTPException(422, 'Image gérée PNG, JPEG ou WebP requise')


def _bound_content(version, value):
    content = deepcopy(value['content'])
    for block in content['blocks']:
        if block['type'] == 'image':
            block['attachment_id'] = version.attachment_bindings[block['attachment_id']]
    return NoteContent.model_validate(content), [version.attachment_bindings[key] for key in value['attachment_ids']]


def _append(db, project_id, note_id, *, title, content, attachment_ids, revision, command_id,
            command_digest, actor, operation, restored_from=None, head=None):
    _attachments(db, project_id, note_id, content, attachment_ids)
    plain = content_text(content)
    snapshot, digest = freeze({'format': 'agent-project-note', 'version': 1, 'project_id': project_id,
        'note_id': note_id, 'title': title, 'content': content.model_dump(mode='json'), 'plain_text': plain,
        'attachment_ids': attachment_ids, 'revision': revision, 'actor_id': actor,
        'command_id': command_id, 'operation': operation, 'restored_from': restored_from})
    version_id, timestamp = uid(), now()
    db.execute(insert(NoteVersion).values(id=version_id, project_id=project_id, note_id=note_id, revision=revision,
        snapshot=snapshot, sha256=digest, command_id=command_id, command_sha256=command_digest, actor_id=actor,
        attachment_bindings={key: key for key in attachment_ids}, restored_version_id=restored_from, created_at=timestamp))
    values = {'title': title, 'plain_text': plain, 'revision': revision, 'current_version_id': version_id, 'updated_at': timestamp}
    if head is None:
        db.execute(insert(ProjectNote).values(id=note_id, project_id=project_id, created_at=timestamp, **values))
    else:
        result = db.execute(update(ProjectNote).where(ProjectNote.id == note_id, ProjectNote.project_id == project_id,
                             ProjectNote.revision == revision-1).values(**values))
        if result.rowcount != 1:
            _error()
    db.expire_all()
    from .note_evidence_outbox import enqueue_note_version
    enqueue_note_version(db, version_id)
    return _response(db, db.get(NoteVersion, version_id), replayed=False)


def create_note(db, project_id, payload: NoteCreate):
    _project(db, project_id, write=True)
    payload = NoteCreate.model_validate(payload.model_dump(mode='json'))
    actor = _actor()
    _ready(db, write=True)
    _lock(db)
    digest = _command_digest(project_id, None, 'create', payload, actor)
    replay = _replay(db, project_id, payload.command_id, digest, actor)
    if replay:
        return replay
    return _append(db, project_id, uid(), title=payload.title, content=payload.content, attachment_ids=[],
                   revision=1, command_id=payload.command_id, command_digest=digest, actor=actor, operation='create')


def save_note(db, project_id, note_id, payload: NoteSave):
    _project(db, project_id, write=True)
    payload = NoteSave.model_validate(payload.model_dump(mode='json'))
    actor = _actor()
    _ready(db, write=True)
    _lock(db)
    digest = _command_digest(project_id, note_id, 'save', payload, actor)
    replay = _replay(db, project_id, payload.command_id, digest, actor)
    if replay:
        return replay
    head = _head(db, project_id, note_id)
    if _detail(db, head)['read_only']:
        raise HTTPException(409, 'Le document Office original reste en consultation')
    if head.revision != payload.expected_revision:
        _error()
    return _append(db, project_id, note_id, title=payload.title, content=payload.content,
                   attachment_ids=payload.attachment_ids, revision=head.revision+1, command_id=payload.command_id,
                   command_digest=digest, actor=actor, operation='save', head=head)


def restore_note(db, project_id, note_id, payload: NoteRestore):
    _project(db, project_id, write=True)
    payload = NoteRestore.model_validate(payload.model_dump(mode='json'))
    actor = _actor()
    _ready(db, write=True)
    _lock(db)
    digest = _command_digest(project_id, note_id, 'restore', payload, actor)
    replay = _replay(db, project_id, payload.command_id, digest, actor)
    if replay:
        return replay
    head = _head(db, project_id, note_id)
    if _detail(db, head)['read_only']:
        raise HTTPException(409, 'Le document Office original reste en consultation')
    if head.revision != payload.expected_revision:
        _error()
    version = db.get(NoteVersion, payload.version_id)
    if version is None or (version.project_id, version.note_id) != (project_id, note_id):
        raise HTTPException(404, 'Version de note introuvable')
    value = _value(version)
    content, attachment_ids = _bound_content(version, value)
    return _append(db, project_id, note_id, title=value['title'], content=content,
                   attachment_ids=attachment_ids, revision=head.revision+1, command_id=payload.command_id,
                   command_digest=digest, actor=actor, operation='restore', restored_from=version.id, head=head)
