"""A prolonged Brain outage must not permanently strand saved ERP notes."""
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.meeting_session_models import NoteEvidenceReceipt
from app.models import Source
from app.services import note_evidence_bridge as bridge
from backend.app.note_evidence_models import NoteEvidenceOutbox
from backend.app.project_note_models import NoteVersion
from backend.app.models import BrainLink, Project
from backend.app.project_note_schemas import NoteCreate, NoteRestore, NoteSave
from backend.app.services import project_notes as notes
from tests.test_meeting_sessions import stores as stores_fixture, key, content

stores = stores_fixture


def test_twentieth_failure_remains_retryable_and_new_note_version_saves_during_outage(stores, monkeypatch):
    brain, erp, pid, _ = stores
    with erp() as db:
        first = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note durable', content=content('V1 à conserver')))
        db.commit()
        version = db.get(NoteVersion, first['note']['version_id'])
        original = (version.sha256, version.snapshot)
        event = db.scalar(select(NoteEvidenceOutbox))
        event.attempts = 19
        db.commit()
    apply = bridge._apply
    monkeypatch.setattr(bridge, '_apply', lambda *args: (_ for _ in ()).throw(OSError('Brain indisponible')))
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['failed'] == 1
    with erp() as db:
        event = db.scalar(select(NoteEvidenceOutbox))
        assert event.attempts == 20 and event.status == 'failed'
        assert event.retry_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
        second = notes.save_note(db, pid, first['note']['id'], NoteSave(command_id=key(), expected_revision=1,
            title='Note durable', content=content('V2 enregistrée malgré la panne')))
        db.commit()
        # The old version remains intact, and both saves have durable outbox rows.
        version = db.get(NoteVersion, first['note']['version_id'])
        assert (version.sha256, version.snapshot) == original
        assert db.scalar(select(func.count()).select_from(NoteEvidenceOutbox)) == 2
        event.retry_at = None  # Advance the retry eligibility on this private fixture only.
        db.commit()
    monkeypatch.setattr(bridge, '_apply', apply)
    result = bridge.process_pending(erp_factory=erp, brain_factory=brain)
    assert result == {'received':1, 'obsolete':1, 'waiting_project':0, 'failed':0}
    with brain() as db:
        source = db.scalar(select(Source))
        assert source.source_metadata['note_version_id'] == second['note']['version_id']
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 2


def test_legacy_exhausted_note_resumes_without_new_event_or_duplicate_source(stores):
    brain, erp, pid, _ = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Reprise ancienne', content=content()))
        db.commit()
        event = db.scalar(select(NoteEvidenceOutbox))
        event_id = event.id
        event.status, event.attempts, event.retry_at = 'exhausted', 20, None
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain) == {'received':0,'obsolete':0,'waiting_project':0,'failed':0}
    with erp() as db:
        event = db.get(NoteEvidenceOutbox, event_id)
        assert event.status == 'received' and event.attempts == 20
        assert db.scalar(select(func.count()).select_from(NoteEvidenceOutbox)) == 1
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 1


def test_unlinked_restored_note_keeps_history_and_projects_only_current_version_after_link(stores):
    brain, erp, _, bid = stores
    with erp() as db:
        project = Project(code='NO-BRAIN-YET', title='Projet sans liaison')
        db.add(project)
        db.flush()
        pid = project.id
        first = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Historique', content=content('Texte initial')))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['waiting_project'] == 1
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 0
    with erp() as db:
        notes.save_note(db, pid, first['note']['id'], NoteSave(command_id=key(), expected_revision=1,
            title='Historique', content=content('Texte modifié')))
        db.commit()
        before = {v.id:(v.snapshot,v.sha256) for v in db.scalars(select(NoteVersion))}
        restored = notes.restore_note(db, pid, first['note']['id'], NoteRestore(command_id=key(),
            expected_revision=2, version_id=first['note']['version_id']))
        assert restored['note']['revision'] == 3
        assert restored['note']['content'] == first['note']['content']
        db.add(BrainLink(project_id=pid, brain_project_id=bid))
        for event in db.scalars(select(NoteEvidenceOutbox)):
            event.retry_at = None
        db.commit()
        assert all((db.get(NoteVersion,vid).snapshot,db.get(NoteVersion,vid).sha256)==value for vid,value in before.items())
    result = bridge.process_pending(erp_factory=erp, brain_factory=brain)
    assert result == {'received':1,'obsolete':2,'waiting_project':0,'failed':0}
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        source = db.scalar(select(Source))
        assert source.source_metadata['note_version_id'] == restored['note']['version_id']
        assert source.source_metadata['note_revision'] == 3
