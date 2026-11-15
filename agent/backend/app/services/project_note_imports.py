"""Explicit selected-source import, immutable provenance and committed retries.

Callers own commit/rollback. Acquisition is a trusted bounded adapter invoked
only after authorization, schema checks and replay lookup. No source scan, DDL,
XPilot database read or network access is implemented here.
"""
import hashlib
from pathlib import PurePosixPath
from uuid import UUID, uuid5

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.services.deliverable_manifest import freeze
from ..project_identity_models import uid, now
from ..project_note_models import ProjectNote, NoteVersion, NoteAttachment, NoteSourceImport
from ..project_note_import_schemas import NoteImportCommand, NoteImportCapture
from ..project_note_schemas import NoteCreate, NoteSave, NoteContent
from . import project_notes as notes, project_note_files as attachments, project_note_import_files as storage
from .project_identity import _project
from .project_note_source_content import _derived, _asset_capture, validate_source_capture
from .project_note_source_preview import preview_source
from .project_note_source_bundle import prepare_bundle


def command_digest(project_id, payload, actor):
    return notes._command_digest(project_id, payload.planned_note_id, 'import', payload, actor)


def _capture(row):
    try:
        from .project_note_history import import_value
        return import_value({column.name: getattr(row, column.name) for column in NoteSourceImport.__table__.c})
    except (ValueError, TypeError, KeyError, ValidationError) as exc:
        raise HTTPException(409, 'Intégrité du reçu d’import invalide') from exc


def _verified(db, row):
    capture = _capture(row)
    bundle, files = storage.read_originals(row, capture)
    try:
        preview = validate_source_capture(capture, files)
        for revision, source in enumerate(capture.versions, start=1):
            version = db.get(NoteVersion, row.version_bindings[source.note_version_id])
            if version is None or (version.project_id, version.note_id, version.revision) != (row.project_id, row.note_id, revision):
                raise ValueError('Liaison de version source manquante')
            value = notes._value(version)
            if (value['title'] != preview['title'] or freeze(value['content'])[1] != source.content_sha256
                    or (value['project_id'], value['note_id'], value['actor_id']) !=
                       (capture.project_id, capture.note_id, capture.actor_id)
                    or not version.execution_blocked
                    or value['attachment_ids'] != [item.id for item in capture.attachments]
                    or version.attachment_bindings != row.attachment_bindings):
                raise ValueError('Contenu historique différent de la conversion capturée')
        for source in capture.attachments:
            data, item = attachments.download(db, row.project_id, row.note_id, row.attachment_bindings[source.id])
            if any(item[field] != getattr(source, field) for field in ('filename', 'content_type', 'size_bytes', 'sha256')):
                raise ValueError('Pièce différente de la capture source')
            if hashlib.sha256(data).hexdigest() != source.sha256:
                raise ValueError('Octets de pièce incompatibles')
    except ValueError as exc:
        raise HTTPException(409, 'Historique d’import incomplet ou modifié') from exc
    return capture, bundle, files


def _response(db, row, *, replayed):
    capture, _, _ = _verified(db, row)
    return {'note': notes._detail(db, notes._head(db, row.project_id, row.note_id)),
            'import_id': row.id, 'command_id': row.command_id, 'replayed': replayed,
            'source_kind': row.source_kind, 'originals_sha256': row.sha256,
            'source_metadata': capture.source_metadata,
            'source_descriptor': capture.command.source.model_dump(mode='json'),
            'source_files': capture.files,
            'source_versions': [item.model_dump(mode='json') | {'current_version_id': row.version_bindings[item.note_version_id]}
                                for item in capture.versions]}


def import_selected(db, project_id, payload: NoteImportCommand, *, acquire):
    _project(db, project_id, write=True)
    payload = NoteImportCommand.model_validate(payload.model_dump(mode='json'))
    actor = notes._actor()
    notes._ready(db, write=True)
    notes._lock(db)
    digest = command_digest(project_id, payload, actor)
    previous = db.scalar(select(NoteSourceImport).where(NoteSourceImport.project_id == project_id,
                                                       NoteSourceImport.command_id == payload.command_id))
    if previous is not None:
        if previous.execution_blocked or previous.command_sha256 != digest or previous.actor_id != actor:
            raise HTTPException(409, 'Commande d’import déjà utilisée ou historique restauré')
        return _response(db, previous, replayed=True)
    if (db.get(ProjectNote, payload.planned_note_id) is not None
            or db.scalar(select(NoteVersion.id).where(NoteVersion.project_id == project_id, NoteVersion.command_id == payload.command_id))):
        raise HTTPException(409, 'Identité de note ou de commande déjà utilisée')
    try:
        # Acquire exactly the explicit selection; never infer a folder/DB here.
        files = acquire(payload.source)
        bundle, origin = prepare_bundle(files, planned_note_id=payload.planned_note_id,
                                        expected_preview_sha256=payload.expected_preview_sha256, mode=payload.mode)
        preview = preview_source(files, planned_note_id=payload.planned_note_id, mode=payload.mode)
        versions, assets = _derived(files, preview, payload.mode)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    row = NoteSourceImport(id=uid(), project_id=project_id, note_id=payload.planned_note_id,
        actor_id=actor, command_id=payload.command_id, command_sha256=digest, source_kind=preview['kind'],
        storage_id=uid(), sha256=origin['sha256'], size_bytes=len(bundle), created_at=now())
    # Validate every derived asset before the first persistent write.
    attachment_rows = []
    for item in assets:
        attachment_rows.append(NoteAttachment(id=item['id'], project_id=project_id, note_id=row.note_id,
            filename=item['filename'], content_type=item['content_type'], size_bytes=item['size_bytes'],
            sha256=item['sha256'], storage_id=uid(), command_id=uid(), actor_id=actor, created_at=now()))
    storage.write_originals(row.storage_id, bundle)
    for item, attachment in zip(assets, attachment_rows, strict=True):
        storage.write_attachment(attachment.storage_id, item['data'])
    db.add_all(attachment_rows)
    db.flush()
    captured_versions = []
    ids = [item['id'] for item in assets]
    for revision, source in enumerate(versions, start=1):
        command_id = str(uuid5(UUID(payload.command_id), 'version:' + source['source_key']))
        content = NoteContent.model_validate(source['content'])
        operation = 'create' if revision == 1 else 'save'
        command = NoteCreate(command_id=command_id, title=preview['title'], content=content) if revision == 1 else NoteSave(
            command_id=command_id, title=preview['title'], content=content, expected_revision=revision-1, attachment_ids=ids)
        result = notes._append(db, project_id, row.note_id, title=command.title, content=content,
            attachment_ids=ids, revision=revision, command_id=command_id, actor=actor, operation=operation,
            command_digest=notes._command_digest(project_id, None if revision == 1 else row.note_id, operation, command, actor),
            head=None if revision == 1 else notes._head(db, project_id, row.note_id))
        version = db.get(NoteVersion, result['command_version_id'])
        version.execution_blocked = True
        db.flush()
        captured_versions.append({'source_key': source['source_key'], 'source_actor': source['source_actor'],
            'note_version_id': version.id, 'content_sha256': freeze(source['content'])[1], 'conversion_mode': source['conversion_mode']})
    capture = NoteImportCapture(id=row.id, project_id=project_id, note_id=row.note_id, actor_id=actor,
        command_id=payload.command_id, command=payload, source_kind=row.source_kind,
        bundle_sha256=row.sha256, bundle_size_bytes=row.size_bytes, source_sha256=preview['source_sha256'],
        source_metadata=preview.get('source_metadata', {}), files=preview['files'], versions=captured_versions,
        attachments=[_asset_capture(item) for item in assets])
    row.snapshot, row.snapshot_sha256 = freeze(capture.model_dump(mode='json'))
    row.version_bindings = {item.note_version_id: item.note_version_id for item in capture.versions}
    row.attachment_bindings = {item.id: item.id for item in capture.attachments}
    db.add(row)
    db.flush()
    return _response(db, row, replayed=False)


def read_import(db, project_id, note_id):
    _project(db, project_id)
    notes._ready(db, write=True)
    notes._head(db, project_id, note_id)
    row = db.scalar(select(NoteSourceImport).where(NoteSourceImport.project_id == project_id, NoteSourceImport.note_id == note_id))
    if row is None:
        raise HTTPException(404, 'Aucun original importé pour cette note')
    return _response(db, row, replayed=False)


def replay_import(db, project_id, payload: NoteImportCommand):
    """Confirm an exact previous command without ever acquiring source files."""
    def unavailable(_):
        raise HTTPException(404, 'Import non confirmé ; sélectionner à nouveau les mêmes sources pour le reprendre')
    return import_selected(db, project_id, payload, acquire=unavailable)


def original_file(db, project_id, note_id, relative_path):
    _project(db, project_id)
    notes._ready(db, write=True)
    notes._head(db, project_id, note_id)
    row = db.scalar(select(NoteSourceImport).where(NoteSourceImport.project_id == project_id, NoteSourceImport.note_id == note_id))
    if row is None:
        raise HTTPException(404, 'Aucun original importé pour cette note')
    capture, _, files = _verified(db, row)
    if not isinstance(relative_path, str) or relative_path not in files:
        raise HTTPException(404, 'Fichier absent des originaux conservés')
    item = next(item for item in capture.files if item['relative_path'] == relative_path)
    return files[relative_path], {'filename': PurePosixPath(relative_path).name, 'relative_path': relative_path,
                                 'sha256': item['sha256'], 'content_type': 'application/octet-stream'}
