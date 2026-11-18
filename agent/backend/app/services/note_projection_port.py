"""ERP-owned contract for canonical note projections and delivery outcomes."""
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import inspect, or_, select, text, update

from ..models import BrainLink
from ..note_evidence_models import NoteEvidenceOutbox
from ..project_note_models import NoteVersion, ProjectNote
from .project_notes import _value


@dataclass(frozen=True)
class NoteProjection:
    brain_project_id: str | None
    current: bool
    actor_id: str
    value: dict


def pending_events(factory, instant, limit):
    """Return bounded event envelopes without exposing the ERP session or models."""
    with factory() as erp:
        if not inspect(erp.connection()).has_table('note_evidence_outbox'):
            return []
        rows = erp.scalars(select(NoteEvidenceOutbox).where(
            NoteEvidenceOutbox.status.in_(['pending', 'failed', 'waiting_project', 'exhausted']),
            or_(NoteEvidenceOutbox.retry_at.is_(None), NoteEvidenceOutbox.retry_at <= instant))
            .order_by(NoteEvidenceOutbox.created_at, NoteEvidenceOutbox.id).limit(limit))
        return [{key: getattr(row, key) for key in ('id', 'project_id', 'note_id', 'version_id', 'revision', 'digest')}
                for row in rows]


def confirmed_current_events(factory, *, after_id='', limit=100):
    """Page through confirmed current notes whose projects have a Brain link."""
    if not isinstance(after_id, str) or len(after_id) > 36 or type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('Invalid note projection scan')
    with factory() as erp:
        inspector = inspect(erp.connection())
        if not all(inspector.has_table(name) for name in ('note_evidence_outbox', 'project_notes', 'brain_links')):
            return []
        rows = erp.execute(select(NoteEvidenceOutbox, BrainLink.brain_project_id)
            .join(ProjectNote, ProjectNote.current_version_id == NoteEvidenceOutbox.version_id)
            .join(BrainLink, BrainLink.project_id == ProjectNote.project_id)
            .where(NoteEvidenceOutbox.status == 'received', ProjectNote.id > after_id)
            .order_by(ProjectNote.id).limit(limit))
        return [{**{key: getattr(event, key) for key in ('id', 'project_id', 'note_id', 'version_id', 'revision', 'digest')},
                 'brain_project_id': brain_id} for event, brain_id in rows]


def record_result(factory, event_id, status, instant):
    """Commit the delivery outcome without reversing a confirmed event."""
    if status not in {'received', 'obsolete', 'waiting_project'}:
        raise ValueError('Invalid note projection result')
    with factory() as erp:
        changed = erp.execute(update(NoteEvidenceOutbox).where(
            NoteEvidenceOutbox.id == event_id, NoteEvidenceOutbox.status.not_in(('received', 'obsolete'))
        ).values(status=status, error=None, received_at=instant if status in {'received', 'obsolete'} else None,
                 retry_at=instant + timedelta(seconds=30) if status == 'waiting_project' else None)
          .execution_options(synchronize_session=False))
        if changed.rowcount != 1:
            existing = erp.scalar(select(NoteEvidenceOutbox.status).where(NoteEvidenceOutbox.id == event_id))
            if existing in {'received', 'obsolete'}:
                return existing
            raise RuntimeError('Note projection event unavailable')
        erp.commit()
        return status


def record_failure(factory, event_id, error_type, instant):
    """Record a retryable failure unless another worker already confirmed it."""
    for _ in range(16):
        with factory() as erp:
            row = erp.execute(select(NoteEvidenceOutbox.status, NoteEvidenceOutbox.attempts)
                              .where(NoteEvidenceOutbox.id == event_id)).first()
        if row is None:
            raise RuntimeError('Note projection event unavailable')
        if row.status in {'received', 'obsolete'}:
            return row.status
        attempts = row.attempts
        # Compare the retry count atomically; a concurrent worker may have
        # confirmed the event or recorded another failure since our read.
        with factory() as erp:
            changed = erp.execute(update(NoteEvidenceOutbox).where(
                NoteEvidenceOutbox.id == event_id, NoteEvidenceOutbox.attempts == attempts,
                NoteEvidenceOutbox.status.not_in(('received', 'obsolete'))
            ).values(status='failed', attempts=attempts + 1,
                     error=error_type + ' : projection de note à reprendre',
                     retry_at=instant + timedelta(seconds=min(3600, 60 * 2 ** min(attempts, 6))))
              .execution_options(synchronize_session=False))
            if changed.rowcount == 1:
                erp.commit()
                return 'failed'
    raise RuntimeError('Note projection event changed repeatedly')


def current_head(metadata, factory):
    """Return the canonical head and its current Brain link, or None if absent."""
    with factory() as db:
        return db.execute(text('SELECT n.current_version_id,n.revision,v.sha256,l.brain_project_id '
            'FROM project_notes n JOIN project_note_versions v ON v.id=n.current_version_id '
            'LEFT JOIN brain_links l ON l.project_id=n.project_id '
            'WHERE n.id=:nid AND n.project_id=:pid'),
            {'nid': metadata.get('note_id'), 'pid': metadata.get('erp_project_id')}).first()


def read_projection(packet, factory):
    """Validate an outbox event against its owning ERP records before projection."""
    with factory() as erp:
        version = erp.get(NoteVersion, packet['version_id'])
        head = erp.get(ProjectNote, packet['note_id'])
        if (version is None or head is None or version.project_id != packet['project_id']
                or head.project_id != packet['project_id'] or version.note_id != packet['note_id']
                or version.revision != packet['revision'] or version.sha256 != packet['digest']):
            raise ValueError('Canonical note event mismatch')
        value = _value(version)
        link = erp.get(BrainLink, packet['project_id'])
        return NoteProjection(brain_project_id=link.brain_project_id if link else None,
                              current=head.current_version_id == version.id,
                              actor_id=version.actor_id, value=value)
