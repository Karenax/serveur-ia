"""Recoverable ERP -> Brain evidence bridge. No inference during note saving."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import threading
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import inspect, or_, select, text

_stop = threading.Event()
_thread = None
_processing = threading.Lock()


def current_source_version(source_metadata, *, erp_factory=None):
    """Read canonical note head, using an injectable factory and no eager DB import."""
    metadata = source_metadata or {}
    if metadata.get('origin_kind') != 'erp_note':
        return {'eligible': True, 'current_version_id': None, 'reason': 'not_note'}
    if erp_factory is None:
        from backend.app.db import SessionLocal
        erp_factory = SessionLocal
    try:
        with erp_factory() as db:
            row = db.execute(text('SELECT n.current_version_id,n.revision,v.sha256 '
                'FROM project_notes n JOIN project_note_versions v ON v.id=n.current_version_id '
                'WHERE n.id=:nid AND n.project_id=:pid'),
                {'nid': metadata.get('note_id'), 'pid': metadata.get('erp_project_id')}).first()
        if row is None:
            return {'eligible': False, 'current_version_id': None, 'reason': 'missing'}
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


def _apply(packet, erp_factory, brain_factory):
    from backend.app.models import BrainLink
    from backend.app.project_note_models import NoteVersion, ProjectNote
    from backend.app.services.project_notes import _value
    from app.meeting_session_models import NoteEvidenceBinding, NoteEvidenceReceipt
    from app.models import Project, Source, SourceArtifact
    from .projections import enqueue

    with brain_factory() as brain:
        receipt = brain.get(NoteEvidenceReceipt, packet['id'])
        if receipt:
            if receipt.digest != packet['digest']:
                raise ValueError('Outbox receipt differs')
            return receipt.status
    with erp_factory() as erp:
        version = erp.get(NoteVersion, packet['version_id'])
        head = erp.get(ProjectNote, packet['note_id'])
        if (version is None or head is None or version.project_id != packet['project_id']
                or version.note_id != packet['note_id'] or version.sha256 != packet['digest']):
            raise ValueError('Canonical note event mismatch')
        value = _value(version)
        link = erp.get(BrainLink, packet['project_id'])
        current = head.current_version_id == version.id
        brain_id = link.brain_project_id if link else None
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
            return receipt.status
        if not current:
            brain.add(NoteEvidenceReceipt(id=packet['id'], digest=packet['digest'], status='obsolete'))
            brain.commit()
            return 'obsolete'
        binding = brain.scalar(select(NoteEvidenceBinding).where(
            NoteEvidenceBinding.erp_project_id == packet['project_id'], NoteEvidenceBinding.note_id == packet['note_id']))
        if binding and binding.brain_project_id != brain_id:
            raise ValueError('Note project binding changed')
        if binding and binding.revision > packet['revision']:
            brain.add(NoteEvidenceReceipt(id=packet['id'], digest=packet['digest'], status='obsolete'))
            brain.commit()
            return 'obsolete'
        source = brain.get(Source, binding.source_id) if binding else None
        if source is None:
            capsule = json.dumps({'format': 'agent-note-source', 'erp_project_id': packet['project_id'],
                'note_id': packet['note_id'], 'initial_version_id': packet['version_id'], 'sha256': packet['digest']},
                sort_keys=True, separators=(',', ':'))
            source = Source(id=str(uuid5(NAMESPACE_URL, 'agent:note-source:' + packet['project_id'] + ':' + packet['note_id'])),
                project_id=brain_id, source_type='document', status='resolved', author=version.actor_id,
                original_uri=f"agent-note://{packet['project_id']}/{packet['note_id']}",
                sha256=hashlib.sha256(capsule.encode()).hexdigest(), mime_type='application/vnd.agent.note+json')
            brain.add(source)
            brain.flush()
        metadata = {**(source.source_metadata or {}), 'origin_kind': 'erp_note', 'erp_project_id': packet['project_id'], 'note_id': packet['note_id'],
            'note_version_id': packet['version_id'], 'note_revision': packet['revision'], 'note_sha256': packet['digest'],
            'subject': value['title'], 'note_url': f"/app/projects/{packet['project_id']}/documents",
            'evidence_state': 'assessed', 'truth_eligible': False, 'superseded': False}
        source.source_metadata = metadata
        for old in brain.scalars(select(SourceArtifact).where(SourceArtifact.source_id == source.id, SourceArtifact.kind == 'note_text')):
            old.content_json = {**old.content_json, 'superseded': True}
        brain.add(SourceArtifact(id=str(uuid5(NAMESPACE_URL, 'agent:note-artifact:' + packet['version_id'])),
            source_id=source.id, kind='note_text', content_text=value['title'] + '\n' + value['plain_text'],
            content_json={**metadata, 'content': value['content'], 'superseded': False}))
        if binding is None:
            binding = NoteEvidenceBinding(erp_project_id=packet['project_id'], note_id=packet['note_id'],
                brain_project_id=brain_id, source_id=source.id, version_id=packet['version_id'], revision=packet['revision'])
            brain.add(binding)
        else:
            binding.version_id, binding.revision = packet['version_id'], packet['revision']
        enqueue(brain, brain_id, 'evidence', source_id=source.id).status = 'pending'
        brain.add(NoteEvidenceReceipt(id=packet['id'], digest=packet['digest'], source_id=source.id, status='received'))
        brain.commit()
    return 'received'


def process_pending(*, erp_factory=None, brain_factory=None, limit=100, after_brain_commit=None):
    """Bounded recovery; optional hook exercises the inter-store crash boundary."""
    from backend.app.note_evidence_models import NoteEvidenceOutbox
    erp_factory, brain_factory = _factories(erp_factory, brain_factory)
    result = {'received': 0, 'obsolete': 0, 'waiting_project': 0, 'failed': 0}
    if not _processing.acquire(blocking=False):
        return result
    try:
        instant = datetime.now(timezone.utc)
        with erp_factory() as erp:
            if not inspect(erp.connection()).has_table('note_evidence_outbox'):
                return result
            rows = erp.scalars(select(NoteEvidenceOutbox).where(
                NoteEvidenceOutbox.status.in_(['pending', 'failed', 'waiting_project', 'exhausted']),
                or_(NoteEvidenceOutbox.retry_at.is_(None), NoteEvidenceOutbox.retry_at <= instant))
                .order_by(NoteEvidenceOutbox.created_at, NoteEvidenceOutbox.id).limit(limit))
            packets = [{key: getattr(row, key) for key in ('id', 'project_id', 'note_id', 'version_id', 'revision', 'digest')}
                       for row in rows]
        for packet in packets:
            try:
                status = _apply(packet, erp_factory, brain_factory)
                if after_brain_commit:
                    after_brain_commit(packet)
                with erp_factory() as erp:
                    row = erp.get(NoteEvidenceOutbox, packet['id'])
                    row.status, row.error = status, None
                    row.received_at = instant if status in {'received', 'obsolete'} else None
                    row.retry_at = instant + timedelta(seconds=30) if status == 'waiting_project' else None
                    erp.commit()
                result[status] += 1
            except Exception as exc:
                with erp_factory() as erp:
                    row = erp.get(NoteEvidenceOutbox, packet['id'])
                    row.attempts += 1
                    # An outage can outlast any fixed retry count. Keep durable
                    # events retryable, including legacy exhausted rows, while
                    # the existing backoff bounds repeated work.
                    row.status = 'failed'
                    row.error = type(exc).__name__ + ' : projection de note à reprendre'
                    row.retry_at = instant + timedelta(seconds=min(3600, 60 * 2 ** min(row.attempts - 1, 6)))
                    erp.commit()
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
        while not _stop.is_set():
            try:
                if feature_enabled():
                    process_pending()
            except Exception:
                pass  # no note content or connection secrets in general logs
            _stop.wait(5)
    _thread = threading.Thread(target=loop, name='note-evidence-bridge', daemon=True)
    _thread.start()


def stop_worker():
    _stop.set()
    if _thread:
        _thread.join(timeout=5)
