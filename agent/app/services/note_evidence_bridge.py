"""Recoverable ERP -> Brain evidence bridge. No inference during note saving."""
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import threading
import time
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select, text

_stop = threading.Event()
_thread = None
_processing = threading.Lock()


def current_source_version(source_metadata, *, erp_factory=None, brain_project_id=None):
    """Read canonical note head, using an injectable factory and no eager DB import."""
    metadata = source_metadata or {}
    if metadata.get('origin_kind') != 'erp_note':
        return {'eligible': True, 'current_version_id': None, 'reason': 'not_note'}
    if erp_factory is None:
        from backend.app.db import SessionLocal
        erp_factory = SessionLocal
    try:
        from backend.app.services.note_projection_port import current_head
        row = current_head(metadata, erp_factory)
        if row is None:
            return {'eligible': False, 'current_version_id': None, 'reason': 'missing'}
        if brain_project_id is not None and row[3] != brain_project_id:
            return {'eligible': False, 'current_version_id': row[0], 'reason': 'project_link_changed'}
        valid = (row[0] == metadata.get('note_version_id') and row[1] == metadata.get('note_revision')
                 and row[2] == metadata.get('note_sha256'))
        return {'eligible': valid, 'current_version_id': row[0], 'reason': 'current' if valid else 'superseded'}
    except Exception:
        return {'eligible': False, 'current_version_id': None, 'reason': 'canonical_unavailable'}


def is_current_note_source(source_metadata, *, erp_factory=None):
    return current_source_version(source_metadata, erp_factory=erp_factory)['eligible']


def _factories(erp_factory, brain_factory):
    if erp_factory is None:
        from backend.app.db import SessionLocal
        erp_factory = SessionLocal
    if brain_factory is None:
        from app.db import SessionLocal
        brain_factory = SessionLocal
    return erp_factory, brain_factory


def _apply(packet, erp_factory, brain_factory, *, reconcile=False):
    from backend.app.services.note_projection_port import read_projection
    from app.meeting_session_models import NoteEvidenceBinding, NoteEvidenceReceipt
    from app.models import Project, Source, SourceArtifact
    from .projections import enqueue

    with brain_factory() as brain:
        receipt = brain.get(NoteEvidenceReceipt, packet['id'])
        if receipt:
            if receipt.digest != packet['digest']:
                raise ValueError('Outbox receipt differs')
            if not reconcile:
                return receipt.status
        if reconcile and (receipt is None or receipt.status != 'received'):
            raise ValueError('Confirmed note receipt unavailable')
    projection = read_projection(packet, erp_factory)
    value, current, brain_id = projection.value, projection.current, projection.brain_project_id
    if not brain_id:
        return 'waiting_project'
    with brain_factory() as brain:
        if brain.get(Project, brain_id) is None:
            return 'waiting_project'
        # Serialise immutable receipt/source writes in SQLite before checking
        # again. A retry after Brain commit must only acknowledge the event.
        brain.execute(text('UPDATE note_evidence_receipts SET status=status WHERE 0'))
        receipt = brain.get(NoteEvidenceReceipt, packet['id'])
        if receipt:
            if receipt.digest != packet['digest']:
                raise ValueError('Outbox receipt differs')
            if not reconcile:
                return receipt.status
        if reconcile and (receipt is None or receipt.status != 'received'):
            raise ValueError('Confirmed note receipt unavailable')
        if reconcile:
            receipt_source = brain.get(Source, receipt.source_id) if receipt.source_id else None
            receipt_metadata = (receipt_source.source_metadata or {}) if receipt_source else {}
            if (receipt_source is None or receipt_source.status != 'resolved'
                    or receipt_metadata.get('origin_kind') != 'erp_note'
                    or receipt_metadata.get('erp_project_id') != packet['project_id']
                    or receipt_metadata.get('note_id') != packet['note_id']):
                raise ValueError('Confirmed note receipt source unavailable')
        if not current:
            if reconcile:
                return 'unchanged'
            brain.add(NoteEvidenceReceipt(id=packet['id'], digest=packet['digest'], status='obsolete'))
            brain.commit()
            return 'obsolete'
        binding = brain.scalar(select(NoteEvidenceBinding).where(
            NoteEvidenceBinding.erp_project_id == packet['project_id'], NoteEvidenceBinding.note_id == packet['note_id']))
        if reconcile and (binding is None or binding.revision != packet['revision']
                          or binding.version_id != packet['version_id']):
            raise ValueError('Confirmed note binding differs')
        if reconcile and binding.brain_project_id == brain_id:
            return 'unchanged'
        if binding and binding.revision > packet['revision']:
            brain.add(NoteEvidenceReceipt(id=packet['id'], digest=packet['digest'], status='obsolete'))
            brain.commit()
            return 'obsolete'
        legacy_source_id = str(uuid5(NAMESPACE_URL, 'agent:note-source:' + packet['project_id'] + ':' + packet['note_id']))
        project_source_id = str(uuid5(NAMESPACE_URL, 'agent:note-source-project:' + packet['project_id'] + ':'
                                      + packet['note_id'] + ':' + brain_id))
        if binding:
            bound_source = brain.get(Source, binding.source_id)
            bound_metadata = (bound_source.source_metadata or {}) if bound_source else {}
            if (bound_source is None or bound_source.project_id != binding.brain_project_id
                    or bound_source.status != 'resolved' or bound_metadata.get('origin_kind') != 'erp_note'
                    or bound_metadata.get('erp_project_id') != packet['project_id']
                    or bound_metadata.get('note_id') != packet['note_id']
                    or bound_metadata.get('note_version_id') != binding.version_id
                    or bound_metadata.get('note_revision') != binding.revision
                    or (reconcile and bound_metadata.get('note_sha256') != packet['digest'])):
                raise ValueError('Bound note source identity differs')
        if binding and binding.brain_project_id == brain_id:
            source = bound_source
        elif binding:
            source = brain.get(Source, project_source_id)
            if source is None:
                legacy = brain.get(Source, legacy_source_id)
                source = legacy if legacy and legacy.project_id == brain_id else None
        else:
            source = brain.get(Source, legacy_source_id)
            if source is not None:
                # A source without its binding can indicate a partial restore.
                # Do not silently take ownership of it.
                raise ValueError('Unbound note source already exists')
        if source is not None:
            source_metadata = source.source_metadata or {}
            if (source.project_id != brain_id or source_metadata.get('origin_kind') != 'erp_note'
                    or source_metadata.get('erp_project_id') != packet['project_id']
                    or source_metadata.get('note_id') != packet['note_id'] or source.status != 'resolved'):
                raise ValueError('Note source identity differs')
            source_revision = source_metadata.get('note_revision')
            if (type(source_revision) is not int or source_revision < 1 or source_revision > packet['revision']
                    or (source_revision == packet['revision'] and
                        (source_metadata.get('note_version_id') != packet['version_id']
                         or source_metadata.get('note_sha256') != packet['digest']))):
                raise ValueError('Note source revision differs')
        if source is None:
            capsule = json.dumps({'format': 'agent-note-source', 'erp_project_id': packet['project_id'],
                'note_id': packet['note_id'], 'initial_version_id': packet['version_id'], 'sha256': packet['digest'],
                **({'brain_project_id': brain_id} if binding else {})},
                sort_keys=True, separators=(',', ':'))
            source = Source(id=project_source_id if binding else legacy_source_id,
                project_id=brain_id, source_type='document', status='resolved', author=projection.actor_id,
                original_uri=f"agent-note://{packet['project_id']}/{packet['note_id']}",
                sha256=hashlib.sha256(capsule.encode()).hexdigest(), mime_type='application/vnd.agent.note+json')
            brain.add(source)
            brain.flush()
        metadata = {**(source.source_metadata or {}), 'origin_kind': 'erp_note', 'erp_project_id': packet['project_id'], 'note_id': packet['note_id'],
            'note_version_id': packet['version_id'], 'note_revision': packet['revision'], 'note_sha256': packet['digest'],
            'subject': value['title'], 'note_url': f"/app/projets/{packet['project_id']}/documents",
            'evidence_state': 'assessed', 'truth_eligible': False, 'superseded': False}
        source.source_metadata = metadata
        artifacts = list(brain.scalars(select(SourceArtifact).where(SourceArtifact.source_id == source.id, SourceArtifact.kind == 'note_text')))
        for artifact in artifacts:
            details = artifact.content_json or {}
            revision = details.get('note_revision')
            if (details.get('origin_kind') != 'erp_note' or details.get('erp_project_id') != packet['project_id']
                    or details.get('note_id') != packet['note_id'] or type(revision) is not int
                    or revision < 1 or revision > packet['revision']):
                raise ValueError('Note artifact identity or revision differs')
        matches = [artifact for artifact in artifacts if (artifact.content_json or {}).get('note_version_id') == packet['version_id']]
        if len(matches) > 1:
            raise ValueError('Duplicate note artifacts')
        existing = matches[0] if matches else None
        content_text = value['title'] + '\n' + value['plain_text']
        if existing and (existing.content_text != content_text or (existing.content_json or {}).get('note_sha256') != packet['digest']
                         or (existing.content_json or {}).get('content') != value['content']):
            raise ValueError('Existing note artifact differs')
        for old in artifacts:
            old.content_json = {**old.content_json, 'superseded': old is not existing}
        if existing is None:
            artifact_name = ('agent:note-artifact-project:' + source.id + ':' + packet['version_id']
                             if reconcile else 'agent:note-artifact:' + packet['version_id'])
            brain.add(SourceArtifact(id=str(uuid5(NAMESPACE_URL, artifact_name)), source_id=source.id,
                kind='note_text', content_text=content_text,
                content_json={**metadata, 'content': value['content'], 'superseded': False}))
        if binding is None:
            binding = NoteEvidenceBinding(erp_project_id=packet['project_id'], note_id=packet['note_id'],
                brain_project_id=brain_id, source_id=source.id, version_id=packet['version_id'], revision=packet['revision'])
            brain.add(binding)
        else:
            binding.brain_project_id, binding.source_id = brain_id, source.id
            binding.version_id, binding.revision = packet['version_id'], packet['revision']
        enqueue(brain, brain_id, 'evidence', source_id=source.id).status = 'pending'
        if not reconcile:
            brain.add(NoteEvidenceReceipt(id=packet['id'], digest=packet['digest'], source_id=source.id, status='received'))
        brain.commit()
    return 'received'


def process_pending(*, erp_factory=None, brain_factory=None, limit=100, after_brain_commit=None):
    """Bounded recovery; optional hook exercises the inter-store crash boundary."""
    from backend.app.services.note_projection_port import pending_events, record_failure, record_result
    erp_factory, brain_factory = _factories(erp_factory, brain_factory)
    result = {'received': 0, 'obsolete': 0, 'waiting_project': 0, 'failed': 0}
    if not _processing.acquire(blocking=False):
        return result
    try:
        instant = datetime.now(timezone.utc)
        packets = pending_events(erp_factory, instant, limit)
        for packet in packets:
            try:
                status = _apply(packet, erp_factory, brain_factory)
                if after_brain_commit:
                    after_brain_commit(packet)
                outcome = record_result(erp_factory, packet['id'], status, instant)
                result[outcome] += 1
            except Exception as exc:
                outcome = record_failure(erp_factory, packet['id'], type(exc).__name__, instant)
                result[outcome] += 1
        return result
    finally:
        _processing.release()


def reconcile_project_links(*, erp_factory=None, brain_factory=None, after_id='', limit=100):
    """Bounded, restartable scan of confirmed notes after a project-link change."""
    from backend.app.services.note_projection_port import confirmed_current_events
    from app.meeting_session_models import NoteEvidenceBinding
    erp_factory, brain_factory = _factories(erp_factory, brain_factory)
    result = {'visited': 0, 'relinked': 0, 'failed': 0, 'waiting': 0, 'after_id': after_id,
              'has_more': False, 'busy': False}
    if not _processing.acquire(blocking=False):
        result['busy'] = True
        return result
    try:
        packets = confirmed_current_events(erp_factory, after_id=after_id, limit=limit)
        result.update(visited=len(packets), after_id=packets[-1]['note_id'] if packets else after_id,
                      has_more=len(packets) == limit)
        if not packets:
            return result
        with brain_factory() as brain:
            bindings = {(row.erp_project_id, row.note_id): row.brain_project_id
                        for row in brain.scalars(select(NoteEvidenceBinding).where(
                            NoteEvidenceBinding.note_id.in_([packet['note_id'] for packet in packets])))}
        for packet in packets:
            binding_project = bindings.get((packet['project_id'], packet['note_id']))
            if binding_project == packet['brain_project_id']:
                continue
            try:
                status = _apply(packet, erp_factory, brain_factory, reconcile=True)
                if status == 'received':
                    result['relinked'] += 1
                elif status == 'waiting_project':
                    result['waiting'] += 1
            except Exception:
                # The next scan retries; do not log note content or secrets.
                result['failed'] += 1
        return result
    finally:
        _processing.release()


def start_worker():
    global _thread
    if os.environ.get('AGENT_TESTING') == '1' or (_thread and _thread.is_alive()):
        return
    from .meeting_sessions import feature_enabled
    if not feature_enabled():
        return
    _stop.clear()
    def loop():
        cursor, next_scan = '', 0.0
        while not _stop.is_set():
            try:
                if feature_enabled():
                    process_pending()
                    if time.monotonic() >= next_scan:
                        result = reconcile_project_links(after_id=cursor)
                        if result['busy']:
                            next_scan = time.monotonic() + 5
                        else:
                            if result['failed']:
                                logging.getLogger(__name__).warning('Reprise de notes à vérifier : %d', result['failed'])
                            cursor = result['after_id'] if result['has_more'] else ''
                            next_scan = time.monotonic() + (5 if result['has_more'] else 60)
            except Exception:
                pass  # no note content or connection secrets in general logs
            _stop.wait(5)
    _thread = threading.Thread(target=loop, name='note-evidence-bridge', daemon=True)
    _thread.start()


def stop_worker():
    _stop.set()
    if _thread:
        _thread.join(timeout=5)
