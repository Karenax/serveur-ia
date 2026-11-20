"""Explicit saved forms and search preferences, separate from file approval.

No network/Office access and no implicit installation, seeding or commits.
Callers commit one successful command and roll back any rejected command.
Old captured JSON is immutable; restoring always appends a new version.
"""
import json

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, inspect, select, text, update
from sqlalchemy.dialects.sqlite import insert

from app.services.deliverable_manifest import freeze
from app.db_support import utc_iso

from ..models import NetworkLink
from ..personal_document_models import PersonalDocumentSearchVersion
from ..project_document_form_schemas import DocumentDraftSave
from ..project_document_models import (
    DOCUMENT_FORM_TABLES, DocumentDraftVersion, DocumentSearchState,
    DocumentSearchVersion, ProjectDocumentDraft,
)
from ..project_identity_models import now, uid
from .document_paths import _relative
from .document_preferences import default_preferences, _items  # re-export compatibility
from .document_project_values import project_values
from .document_template_catalogue import catalogue, document_spec
from .project_document_migration import validate_document_schema
from .project_identity import _project
from .project_operator import can_manage_references, current_operator, require_reference_write


def _conflict(message='Le formulaire a changé ; rechargez sa version avant de réessayer'):
    raise HTTPException(409, message)


def _available(db, *, write=False):
    connection = db.connection()
    present = set(inspect(connection).get_table_names()) & {table.name for table in DOCUMENT_FORM_TABLES}
    try:
        plan = validate_document_schema(connection)
    except ValueError as exc:
        _conflict(str(exc))
    complete = not plan['created_tables'] and not plan['created_triggers']
    if not complete:
        populated = any(connection.exec_driver_sql(f'SELECT 1 FROM {name} LIMIT 1').first() for name in present)
        if write or populated:
            _conflict('Installation documentaire protégée requise')
    return complete


def _lock(db):
    # A no-op SQLite write acquires the writer lock before final reads. The
    # predicate never selects a row and therefore never invokes an UPDATE
    # trigger. This also works when no preference/draft head exists yet.
    db.execute(text('UPDATE project_document_search_states SET revision=revision WHERE 0'))
    db.expire_all()


def _actor(operator):
    if not isinstance(operator.id, str) or not 1 <= len(operator.id) <= 120:
        raise HTTPException(422, 'Identifiant opérateur incompatible avec le journal documentaire')
    return operator.id


def _revision(value):
    if type(value) is not int or value < 0:
        raise HTTPException(422, 'Révision documentaire entière positive ou nulle requise')


def _snapshot(version, *, format_name):
    try:
        value = json.loads(version.snapshot)
        canonical, digest = freeze(value)
    except (ValueError, TypeError):
        _conflict('Version documentaire illisible')
    if (canonical != version.snapshot or digest != version.sha256 or not isinstance(value, dict)
            or value.get('format') != format_name or type(value.get('version')) is not int or value['version'] != 1
            or type(value.get('revision')) is not int or value['revision'] != version.revision
            or value.get('actor_id') != version.actor_id):
        _conflict('Intégrité de la version documentaire invalide')
    return value


def _preferences(db):
    available = _available(db)
    head = db.get(DocumentSearchState, 'common') if available else None
    if head is None:
        return {'available': available, 'revision': 0, 'version_id': None, 'items': _items(default_preferences())}
    version = db.get(DocumentSearchVersion, head.current_version_id)
    if version is None or version.revision != head.revision:
        _conflict('Historique des préférences incomplet')
    value = _snapshot(version, format_name='agent-document-search-preferences')
    if value.get('catalogue_sha256') != freeze(catalogue())[1]:
        _conflict('Catalogue documentaire modifié ; réconciliation explicite requise')
    return {'available': True, 'revision': head.revision, 'version_id': version.id,
            'items': _items(value.get('items'))}


def search_preferences(db):
    return {**_preferences(db), 'can_edit': can_manage_references(current_operator())}


def effective_preferences(db, project_id):
    _project(db, project_id)
    row = _personal_head(db)
    if row is None:
        return _preferences(db)
    return {**_personal_preferences(row), 'available': _available(db)}


_PERSONAL_FORMAT = 'agent-personal-document-search-preferences'


def _personal_versions(actor):
    return select(PersonalDocumentSearchVersion).where(PersonalDocumentSearchVersion.actor_id == actor)


def _personal_installed(db):
    return inspect(db.connection()).has_table(PersonalDocumentSearchVersion.__tablename__)


def _personal_value(row):
    value = _snapshot(row, format_name=_PERSONAL_FORMAT)
    if value.get('catalogue_sha256') != freeze(catalogue())[1]:
        _conflict('Catalogue documentaire modifié ; réconciliation explicite requise')
    return value


def _personal_head(db):
    if not _personal_installed(db):
        return None
    return db.scalar(_personal_versions(_actor(current_operator())).order_by(
        PersonalDocumentSearchVersion.revision.desc()).limit(1))


def _personal_preferences(row):
    return {'available': True, 'revision': row.revision,
            'version_id': row.id, 'items': _items(_personal_value(row)['items'])}


def personal_search_preferences(db):
    available = _personal_installed(db)
    row = _personal_head(db) if available else None
    return {**(_personal_preferences(row) if row else {
        'available': available, 'revision': 0, 'version_id': None, 'items': _preferences(db)['items']
    }), 'can_edit': True}


def save_personal_search_preferences(db, *, expected_revision, items, restored_from=None):
    actor = _actor(current_operator())
    _revision(expected_revision)
    values = _items(items)
    if not _personal_installed(db):
        _conflict('Installation des réglages personnels requise')
    # Reserve the SQLite writer before comparing the per-owner revision.
    db.execute(text('UPDATE personal_document_search_versions SET revision=revision WHERE 0'))
    db.expire_all()
    head = _personal_head(db)
    if (head.revision if head else 0) != expected_revision:
        _conflict()
    revision = expected_revision + 1
    snapshot, digest = freeze({'format': _PERSONAL_FORMAT, 'version': 1, 'actor_id': actor,
                              'revision': revision, 'catalogue_sha256': freeze(catalogue())[1],
                              'items': values, 'restored_from': restored_from})
    row = PersonalDocumentSearchVersion(revision=revision, snapshot=snapshot, sha256=digest, actor_id=actor)
    db.add(row)
    db.flush()
    return {'available': True, 'can_edit': True, 'revision': revision, 'version_id': row.id, 'items': values}


def restore_personal_search_preferences(db, *, expected_revision, version_id):
    if not _personal_installed(db):
        _conflict('Installation des réglages personnels requise')
    row = db.scalar(_personal_versions(_actor(current_operator())).where(PersonalDocumentSearchVersion.id == version_id))
    if row is None:
        raise HTTPException(404, 'Version de préférences introuvable')
    return save_personal_search_preferences(db, expected_revision=expected_revision,
        items=_personal_value(row)['items'], restored_from=version_id)


def save_search_preferences(db, *, expected_revision, items, restored_from=None):
    actor = _actor(require_reference_write())
    _revision(expected_revision)
    values = _items(items)
    _available(db, write=True)
    _lock(db)
    current = _preferences(db)
    if current['revision'] != expected_revision:
        _conflict()
    revision = expected_revision + 1
    snapshot, digest = freeze({'format': 'agent-document-search-preferences', 'version': 1,
                              'revision': revision, 'actor_id': actor, 'catalogue_sha256': freeze(catalogue())[1],
                              'items': values, 'restored_from': restored_from})
    version_id = uid()
    db.execute(insert(DocumentSearchVersion).values(id=version_id, revision=revision, snapshot=snapshot,
                                                   sha256=digest, actor_id=actor, created_at=now()))
    if expected_revision == 0:
        result = db.execute(insert(DocumentSearchState).values(id='common', revision=revision,
                    current_version_id=version_id, updated_at=now()).on_conflict_do_nothing())
    else:
        result = db.execute(update(DocumentSearchState).where(DocumentSearchState.id == 'common',
                    DocumentSearchState.revision == expected_revision).values(revision=revision,
                    current_version_id=version_id, updated_at=now()))
    if result.rowcount != 1:
        _conflict()
    db.expire_all()
    return _preferences(db)


def search_history(db):
    require_reference_write()
    if not _available(db):
        return []
    _preferences(db)
    return [{'id': row.id, 'revision': row.revision, 'sha256': row.sha256,
             'created_at': utc_iso(row.created_at), 'value': _snapshot(row, format_name='agent-document-search-preferences')}
            for row in db.scalars(select(DocumentSearchVersion).order_by(DocumentSearchVersion.revision.desc()))]


def restore_search_preferences(db, *, expected_revision, version_id):
    require_reference_write()
    _available(db, write=True)
    version = db.get(DocumentSearchVersion, version_id)
    if version is None:
        raise HTTPException(404, 'Version de préférences introuvable')
    value = _snapshot(version, format_name='agent-document-search-preferences')
    if value.get('catalogue_sha256') != freeze(catalogue())[1]:
        _conflict('Catalogue historique incompatible')
    return save_search_preferences(db, expected_revision=expected_revision, items=value.get('items'), restored_from=version_id)


def _head(db, project_id, document_id):
    return db.scalar(select(ProjectDocumentDraft).where(ProjectDocumentDraft.project_id == project_id,
                                                      ProjectDocumentDraft.document_id == document_id))


def _draft_value(version, head):
    value = _snapshot(version, format_name='agent-project-document-draft')
    bindings = version.bindings
    if (not isinstance(bindings, dict) or set(bindings) != {'project_id', 'draft_id', 'link_id'}
            or bindings['project_id'] != head.project_id or bindings['draft_id'] != head.id
            or value.get('document_id') != head.document_id or version.project_id != head.project_id
            or version.draft_id != head.id or version.document_id != head.document_id
            or not isinstance(value.get('choice'), dict)):
        _conflict('Relations de l’historique documentaire invalides')
    return value


def draft(db, project_id, document_id):
    _project(db, project_id)
    document_spec(document_id)
    available = _available(db)
    head = _head(db, project_id, document_id) if available else None
    if head is None:
        return {'available': available, 'revision': 0, 'version_id': None,
                'link_id': None, 'selected_link': None, 'relative_path': '', 'overrides': {}, 'warnings': []}
    version = db.scalar(select(DocumentDraftVersion).where(DocumentDraftVersion.draft_id == head.id,
                                                          DocumentDraftVersion.revision == head.revision))
    if version is None:
        _conflict('Historique du formulaire incomplet')
    value = _draft_value(version, head)
    choice = value['choice']
    if (version.bindings['link_id'] != head.link_id or choice.get('relative_path') != head.relative_path
            or choice.get('overrides') != head.overrides):
        _conflict('Le formulaire ne correspond plus à sa version conservée')
    link = db.scalar(select(NetworkLink).where(NetworkLink.id == head.link_id, NetworkLink.project_id == project_id))
    return {'available': True, 'revision': head.revision, 'version_id': version.id, 'link_id': head.link_id,
            'selected_link': {'id': link.id, 'code': link.code, 'label': link.libelle,
                              'path': link.chemin, 'order': link.ordre} if link else None,
            'relative_path': head.relative_path, 'overrides': dict(head.overrides),
            'warnings': ['selected_link_missing'] if head.link_id and link is None else []}


def save_draft(db, project_id, document_id, *, expected_revision, link_id=None, relative_path='', overrides=None,
               restored_from=None):
    actor = _actor(_project(db, project_id, write=True))
    document_spec(document_id)
    try:
        command = DocumentDraftSave(expected_revision=expected_revision, link_id=link_id,
                                    relative_path=relative_path, overrides={} if overrides is None else overrides)
    except ValidationError as exc:
        raise HTTPException(422, 'Formulaire documentaire invalide') from exc
    path = _relative(command.relative_path)
    if command.link_id is None and path:
        raise HTTPException(422, 'Le chemin relatif requiert un lien du projet')
    project_values(db, project_id, overrides=command.overrides)
    _available(db, write=True)
    _lock(db)
    _project(db, project_id, write=True)
    if command.link_id is not None and db.scalar(select(NetworkLink.id).where(
            NetworkLink.id == command.link_id, NetworkLink.project_id == project_id)) is None:
        raise HTTPException(404, 'Lien du projet introuvable')
    current = draft(db, project_id, document_id)
    if current['revision'] != command.expected_revision:
        _conflict()
    head = _head(db, project_id, document_id)
    draft_id = head.id if head else uid()
    revision = command.expected_revision + 1
    changes = {'revision': revision, 'link_id': command.link_id, 'relative_path': path,
               'overrides': command.overrides, 'updated_at': now()}
    if head is None:
        result = db.execute(insert(ProjectDocumentDraft).values(id=draft_id, project_id=project_id,
                        document_id=document_id, **changes).on_conflict_do_nothing())
    else:
        result = db.execute(update(ProjectDocumentDraft).where(ProjectDocumentDraft.id == draft_id,
                        ProjectDocumentDraft.revision == command.expected_revision).values(**changes))
    if result.rowcount != 1:
        _conflict()
    snapshot, digest = freeze({'format': 'agent-project-document-draft', 'version': 1, 'project_id': project_id,
                'draft_id': draft_id, 'document_id': document_id, 'revision': revision, 'actor_id': actor,
                'choice': {'link_id': command.link_id, 'relative_path': path, 'overrides': command.overrides},
                'restored_from': restored_from})
    db.execute(insert(DocumentDraftVersion).values(id=uid(), project_id=project_id, draft_id=draft_id,
                document_id=document_id, revision=revision, snapshot=snapshot, sha256=digest, actor_id=actor,
                bindings={'project_id': project_id, 'draft_id': draft_id, 'link_id': command.link_id}, created_at=now()))
    db.expire_all()
    return draft(db, project_id, document_id)


def draft_history(db, project_id, document_id):
    draft(db, project_id, document_id)
    head = _head(db, project_id, document_id) if _available(db) else None
    if head is None:
        return []
    return [{'id': row.id, 'revision': row.revision, 'sha256': row.sha256, 'bindings': dict(row.bindings),
             'created_at': utc_iso(row.created_at), 'value': _draft_value(row, head)}
            for row in db.scalars(select(DocumentDraftVersion).where(DocumentDraftVersion.draft_id == head.id)
                                  .order_by(DocumentDraftVersion.revision.desc()))]


def restore_draft(db, project_id, document_id, *, expected_revision, version_id):
    _project(db, project_id, write=True)
    _available(db, write=True)
    draft(db, project_id, document_id)
    head = _head(db, project_id, document_id)
    row = db.scalar(select(DocumentDraftVersion).where(DocumentDraftVersion.id == version_id,
            DocumentDraftVersion.project_id == project_id, DocumentDraftVersion.document_id == document_id)) if head else None
    if row is None:
        raise HTTPException(404, 'Version du formulaire introuvable')
    value = _draft_value(row, head)
    return save_draft(db, project_id, document_id, expected_revision=expected_revision,
                      link_id=row.bindings['link_id'], relative_path=value['choice']['relative_path'],
                      overrides=value['choice']['overrides'], restored_from=version_id)


def _pagination(offset, limit):
    if type(offset) is not int or type(limit) is not int or not 0 <= offset <= 1000000 or not 1 <= limit <= 200:
        raise HTTPException(422, 'Pagination documentaire invalide')


def search_history_page(db, *, offset=0, limit=50):
    require_reference_write()
    _pagination(offset, limit)
    _preferences(db)
    available = _available(db)
    total = db.scalar(select(func.count()).select_from(DocumentSearchVersion)) if available else 0
    rows = db.scalars(select(DocumentSearchVersion).order_by(DocumentSearchVersion.revision.desc())
                      .offset(offset).limit(limit)) if available else []
    return {'items': [{'id': row.id, 'revision': row.revision, 'sha256': row.sha256,
             'created_at': utc_iso(row.created_at), 'value': _snapshot(row, format_name='agent-document-search-preferences')}
            for row in rows], 'total': total, 'offset': offset, 'limit': limit}


def personal_search_history_page(db, *, offset=0, limit=50):
    _pagination(offset, limit)
    query = _personal_versions(_actor(current_operator()))
    available = _personal_installed(db)
    total = db.scalar(select(func.count()).select_from(query.subquery())) if available else 0
    rows = db.scalars(query.order_by(PersonalDocumentSearchVersion.revision.desc())
                      .offset(offset).limit(limit)) if available else []
    return {'items': [{'id': row.id, 'revision': row.revision, 'sha256': row.sha256,
            'created_at': utc_iso(row.created_at), 'value': _snapshot(row, format_name=_PERSONAL_FORMAT)}
            for row in rows], 'total': total, 'offset': offset, 'limit': limit}


def draft_history_page(db, project_id, document_id, *, offset=0, limit=50):
    draft(db, project_id, document_id)
    _pagination(offset, limit)
    head = _head(db, project_id, document_id) if _available(db) else None
    query = select(DocumentDraftVersion).where(DocumentDraftVersion.draft_id == head.id) if head else None
    total = db.scalar(select(func.count()).select_from(query.subquery())) if query is not None else 0
    rows = db.scalars(query.order_by(DocumentDraftVersion.revision.desc()).offset(offset).limit(limit)) if query is not None else []
    return {'items': [{'id': row.id, 'revision': row.revision, 'sha256': row.sha256, 'bindings': dict(row.bindings),
             'created_at': utc_iso(row.created_at), 'value': _draft_value(row, head)} for row in rows],
            'total': total, 'offset': offset, 'limit': limit}
