"""A prolonged Brain outage must not permanently strand saved ERP notes."""
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
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


def test_confirmed_note_follows_project_links_without_a_new_version(stores):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact
    from app.services.current_evidence import current_contents, is_current_evidence

    brain, erp, pid, original_brain_id = stores
    with erp() as db:
        note = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('Texte conservé')))
        db.commit()
        version_id = note['note']['version_id']
        version = db.get(NoteVersion, version_id)
        canonical = (version.sha256, version.snapshot)
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        original = db.scalar(select(Source))
        original_id = original.id
        artifact = db.scalar(select(SourceArtifact))
        original_artifact = (artifact.id, artifact.content_text, dict(artifact.content_json))
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        db.commit()
    result = bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)
    assert result['visited'] == result['relinked'] == 1 and result['failed'] == 0
    with brain() as db:
        binding = db.scalar(select(NoteEvidenceBinding))
        new_source = db.get(Source, binding.source_id)
        assert new_source.id != original_id and new_source.project_id == other_id
        assert is_current_evidence(new_source, erp_factory=erp)
        assert not is_current_evidence(db.get(Source, original_id), erp_factory=erp)
        assert 'Texte conservé' in current_contents(db, [other_id])[new_source.id]
        artifact = db.get(SourceArtifact, original_artifact[0])
        assert (artifact.id, artifact.content_text, artifact.content_json) == original_artifact
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 1
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['relinked'] == 0
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = original_brain_id
        db.commit()
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['relinked'] == 1
    with brain() as db:
        assert db.scalar(select(NoteEvidenceBinding)).source_id == original_id
        assert db.scalar(select(func.count()).select_from(Source)) == 2
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 2
        assert is_current_evidence(db.get(Source, original_id), erp_factory=erp)
    with erp() as db:
        version = db.get(NoteVersion, version_id)
        assert (version.sha256, version.snapshot) == canonical
        assert db.scalar(select(func.count()).select_from(NoteEvidenceOutbox)) == 1
        assert db.scalar(select(NoteEvidenceOutbox)).status == 'received'


def test_confirmed_note_link_scan_retries_after_interrupted_commit(stores, monkeypatch):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact

    brain, erp, pid, _ = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('Texte')))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        db.commit()
    apply = bridge._apply
    def after_commit(*args, **kwargs):
        result = apply(*args, **kwargs)
        if kwargs.get('reconcile'):
            raise OSError('Interruption après validation')
        return result
    monkeypatch.setattr(bridge, '_apply', after_commit)
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['failed'] == 1
    monkeypatch.setattr(bridge, '_apply', apply)
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['failed'] == 0
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 2
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 2
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 1
        assert db.scalar(select(NoteEvidenceBinding)).brain_project_id == other_id


def test_confirmed_note_link_scan_recovers_from_a_concurrent_link_change(stores, monkeypatch):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact
    from app.services.current_evidence import is_current_evidence
    from backend.app.services import note_projection_port

    brain, erp, pid, original_brain_id = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('Texte')))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        db.commit()
    read = note_projection_port.read_projection
    def change_after_read(packet, factory):
        projection = read(packet, factory)
        with erp() as db:
            db.get(BrainLink, pid).brain_project_id = original_brain_id
            db.commit()
        return projection
    monkeypatch.setattr(note_projection_port, 'read_projection', change_after_read)
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['relinked'] == 1
    with brain() as db:
        binding = db.scalar(select(NoteEvidenceBinding))
        assert binding.brain_project_id == other_id
        assert not is_current_evidence(db.get(Source, binding.source_id), erp_factory=erp)
    monkeypatch.setattr(note_projection_port, 'read_projection', read)
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['relinked'] == 1
    with brain() as db:
        binding = db.scalar(select(NoteEvidenceBinding))
        assert binding.brain_project_id == original_brain_id
        assert is_current_evidence(db.get(Source, binding.source_id), erp_factory=erp)
        assert db.scalar(select(func.count()).select_from(Source)) == 2
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 2


@pytest.mark.parametrize('damage', ['missing_receipt', 'different_bound_source'])
def test_confirmed_note_link_scan_refuses_inconsistent_recovery(stores, damage):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact

    brain, erp, pid, original_brain_id = stores
    with erp() as db:
        note = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('Conservé')))
        db.commit()
        version_id = note['note']['version_id']
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.flush()
        other_id = other.id
        if damage == 'missing_receipt':
            db.delete(db.scalar(select(NoteEvidenceReceipt)))
        else:
            source = db.scalar(select(Source))
            source.source_metadata = {**source.source_metadata, 'note_version_id': 'incohérent'}
        db.commit()
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        db.commit()
    result = bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)
    assert result['relinked'] == 0 and result['failed'] == 1
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 1
        assert db.scalar(select(NoteEvidenceBinding)).brain_project_id == original_brain_id
        if damage == 'different_bound_source':
            assert db.scalar(select(Source)).source_metadata['note_version_id'] == 'incohérent'
    with erp() as db:
        assert db.get(NoteVersion, version_id) is not None
        assert db.scalar(select(NoteEvidenceOutbox)).status == 'received'


def test_confirmed_note_link_scan_pages_and_resumes(stores):
    from app.models import Project as BrainProject, SourceArtifact

    brain, erp, pid, _ = stores
    with erp() as db:
        for label in ('A', 'B', 'C'):
            notes.create_note(db, pid, NoteCreate(command_id=key(), title=label, content=content(label)))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 3
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        db.commit()
    cursor = ''
    visited = []
    while True:
        page = bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain, after_id=cursor, limit=1)
        assert page['failed'] == 0
        if page['visited']:
            visited.append(page['after_id'])
            assert page['relinked'] == 1
        if not page['has_more']:
            break
        cursor = page['after_id']
    assert len(visited) == len(set(visited)) == 3 and visited == sorted(visited)
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 6
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 6
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 3


def test_confirmed_note_link_scan_refuses_damaged_original_receipt_source(stores):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact

    brain, erp, pid, _ = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('Texte')))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        original_id = db.scalar(select(Source)).id
        projects = [BrainProject(code=code, name=code) for code in ('OTHER1', 'OTHER2')]
        db.add_all(projects)
        db.commit()
        first_id, second_id = [project.id for project in projects]
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = first_id
        db.commit()
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['relinked'] == 1
    with brain() as db:
        original = db.get(Source, original_id)
        original.source_metadata = {**original.source_metadata, 'origin_kind': 'document'}
        db.commit()
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = second_id
        db.commit()
    result = bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)
    assert result['failed'] == 1 and result['relinked'] == 0
    with brain() as db:
        assert db.get(Source, original_id).source_metadata['origin_kind'] == 'document'
        assert db.scalar(select(NoteEvidenceBinding)).brain_project_id == first_id
        assert db.scalar(select(func.count()).select_from(Source)) == 2
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 2


@pytest.mark.parametrize('damage', ['artifact', 'newer_revision', 'newer_artifact'])
def test_confirmed_note_link_scan_preserves_a_modified_target(stores, damage):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact

    brain, erp, pid, original_brain_id = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('Texte')))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        db.commit()
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['relinked'] == 1
    with brain() as db:
        other_source = db.scalar(select(NoteEvidenceBinding)).source_id
        artifact = db.scalar(select(SourceArtifact).where(SourceArtifact.source_id == other_source))
        artifact_id = artifact.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = original_brain_id
        db.commit()
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['relinked'] == 1
    with brain() as db:
        if damage == 'artifact':
            db.get(SourceArtifact, artifact_id).content_text = 'Contenu modifié à conserver'
        elif damage == 'newer_revision':
            source = db.get(Source, other_source)
            source.source_metadata = {**source.source_metadata, 'note_revision': 2,
                                      'note_version_id': 'version-plus-recente', 'note_sha256': 'c' * 64}
        else:
            artifact = db.get(SourceArtifact, artifact_id)
            artifact.content_json = {**artifact.content_json, 'note_revision': 2,
                                     'note_version_id': 'version-plus-recente', 'note_sha256': 'c' * 64}
        db.commit()
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        db.commit()
    result = bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)
    assert result['failed'] == 1 and result['relinked'] == 0
    with brain() as db:
        if damage == 'artifact':
            assert db.get(SourceArtifact, artifact_id).content_text == 'Contenu modifié à conserver'
        elif damage == 'newer_revision':
            assert db.get(Source, other_source).source_metadata['note_version_id'] == 'version-plus-recente'
        else:
            assert db.get(SourceArtifact, artifact_id).content_json['note_version_id'] == 'version-plus-recente'
        assert db.scalar(select(NoteEvidenceBinding)).brain_project_id == original_brain_id
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 2


def test_note_worker_runs_link_reconciliation(stores, monkeypatch):
    from threading import Event
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject

    brain, erp, pid, _ = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('Texte')))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        db.commit()
    done = Event()
    outcomes = []
    reconcile = bridge.reconcile_project_links
    def observed_scan(**kwargs):
        result = reconcile(**kwargs)
        outcomes.append(result)
        done.set()
        return result
    monkeypatch.setenv('AGENT_TESTING', '0')
    monkeypatch.setattr(bridge, '_stop', Event())
    monkeypatch.setattr(bridge, '_thread', None)
    monkeypatch.setattr(bridge, 'reconcile_project_links', observed_scan)
    try:
        bridge.start_worker()
        assert done.wait(timeout=15), 'Le traitement de fond ne lance pas la reprise des liens'
        assert outcomes[0]['relinked'] == 1 and outcomes[0]['failed'] == 0
    finally:
        bridge.stop_worker()
    assert not bridge._thread.is_alive()
    with brain() as db:
        assert db.scalar(select(NoteEvidenceBinding)).brain_project_id == other_id


def test_new_note_version_projects_after_the_existing_version_was_relinked(stores):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact
    from app.services.current_evidence import is_current_evidence

    brain, erp, pid, _ = stores
    with erp() as db:
        note = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('V1')))
        db.commit()
        note_id = note['note']['id']
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        db.commit()
    assert bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain)['relinked'] == 1
    with erp() as db:
        notes.save_note(db, pid, note_id, NoteSave(command_id=key(), expected_revision=1,
                                                   title='Note', content=content('V2')))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        source = db.get(Source, db.scalar(select(NoteEvidenceBinding)).source_id)
        artifacts = list(db.scalars(select(SourceArtifact).where(SourceArtifact.source_id == source.id)))
        assert source.project_id == other_id and is_current_evidence(source, erp_factory=erp)
        assert len(artifacts) == 2
        assert sum(not artifact.content_json['superseded'] for artifact in artifacts) == 1
        assert any('V2' in artifact.content_text and not artifact.content_json['superseded'] for artifact in artifacts)


def test_note_link_scan_reports_busy_without_advancing_cursor(stores):
    brain, erp, _, _ = stores
    assert bridge._processing.acquire(blocking=False)
    try:
        result = bridge.reconcile_project_links(erp_factory=erp, brain_factory=brain, after_id='cursor')
    finally:
        bridge._processing.release()
    assert result['busy'] and result['after_id'] == 'cursor' and result['visited'] == 0


@pytest.mark.parametrize('unlink', [False, True])
def test_note_evidence_stops_being_current_when_project_link_changes(stores, unlink):
    from app.models import Project as BrainProject, SourceArtifact
    from app.services.current_evidence import current_contents, is_current_evidence

    brain, erp, pid, original_brain_id = stores
    with erp() as db:
        created = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note conservée',
                                                        content=content('Texte fictif')))
        db.commit()
        version_id = created['note']['version_id']
        version = db.get(NoteVersion, version_id)
        canonical = (version.sha256, version.snapshot)
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
        source = db.scalar(select(Source))
        source_id = source.id
        assert is_current_evidence(source, erp_factory=erp)
        assert 'Texte fictif' in current_contents(db, [original_brain_id])[source_id]
    with erp() as db:
        link = db.get(BrainLink, pid)
        if unlink:
            db.delete(link)
        else:
            link.brain_project_id = other_id
        db.commit()
    with brain() as db:
        source = db.get(Source, source_id)
        assert not is_current_evidence(source, erp_factory=erp)
        assert source_id not in current_contents(db, [original_brain_id])
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 1
    with erp() as db:
        version = db.get(NoteVersion, version_id)
        assert (version.sha256, version.snapshot) == canonical
        link = db.get(BrainLink, pid)
        if link is None:
            db.add(BrainLink(project_id=pid, brain_project_id=original_brain_id))
        else:
            link.brain_project_id = original_brain_id
        db.commit()
    with brain() as db:
        assert is_current_evidence(db.get(Source, source_id), erp_factory=erp)
        assert 'Texte fictif' in current_contents(db, [original_brain_id])[source_id]


def test_new_note_versions_follow_a_project_relink_without_moving_previous_sources(stores):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact
    from app.services.current_evidence import is_current_evidence

    brain, erp, pid, original_brain_id = stores
    with erp() as db:
        created = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('V1')))
        db.commit()
        note_id = created['note']['id']
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
        old_source_id = db.scalar(select(Source)).id
        old_artifact = db.scalar(select(SourceArtifact))
        old_artifact_id, old_content = old_artifact.id, old_artifact.content_text
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        saved = notes.save_note(db, pid, note_id, NoteSave(command_id=key(), expected_revision=1,
                                                          title='Note', content=content('V2')))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        old_source = db.get(Source, old_source_id)
        binding = db.scalar(select(NoteEvidenceBinding))
        new_source = db.get(Source, binding.source_id)
        assert old_source.project_id == original_brain_id and not is_current_evidence(old_source, erp_factory=erp)
        assert new_source.id != old_source_id and new_source.project_id == other_id
        assert is_current_evidence(new_source, erp_factory=erp)
        assert db.get(SourceArtifact, old_artifact_id).content_text == old_content
        assert binding.brain_project_id == other_id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = original_brain_id
        third = notes.save_note(db, pid, note_id, NoteSave(command_id=key(), expected_revision=2,
                                                          title='Note', content=content('V3')))
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        artifacts = list(db.scalars(select(SourceArtifact)))
        binding = db.scalar(select(NoteEvidenceBinding))
        assert len(artifacts) == 3 and db.scalar(select(func.count()).select_from(Source)) == 2
        assert binding.source_id == old_source_id and binding.brain_project_id == original_brain_id
        assert db.get(SourceArtifact, old_artifact_id).content_text == old_content
        assert any('V2' in artifact.content_text for artifact in artifacts)
        assert any('V3' in artifact.content_text and not artifact.content_json['superseded'] for artifact in artifacts)
        assert is_current_evidence(db.get(Source, old_source_id), erp_factory=erp)
    with erp() as db:
        assert db.get(NoteVersion, saved['note']['version_id']) is not None
        assert db.get(NoteVersion, third['note']['version_id']) is not None


def test_relinked_note_retries_after_brain_commit_without_duplicate_sources(stores):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact

    brain, erp, pid, _ = stores
    with erp() as db:
        created = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('V1')))
        db.commit()
        note_id = created['note']['id']
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        saved = notes.save_note(db, pid, note_id, NoteSave(command_id=key(), expected_revision=1,
                                                          title='Note', content=content('V2')))
        db.commit()
        version_id = saved['note']['version_id']
    def crash(_packet):
        raise OSError('Acquittement interrompu')
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain, after_brain_commit=crash)['failed'] == 1
    with erp() as db:
        event = db.scalar(select(NoteEvidenceOutbox).where(NoteEvidenceOutbox.version_id == version_id))
        event.retry_at = None
        db.commit()
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 0
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 2
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 2
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 2
        assert db.scalar(select(NoteEvidenceBinding)).brain_project_id == other_id


def test_relinked_note_rolls_back_partial_brain_write_and_retries(stores, monkeypatch):
    from app.meeting_session_models import NoteEvidenceBinding
    from app.models import Project as BrainProject, SourceArtifact
    from app.services import projections

    brain, erp, pid, original_brain_id = stores
    with erp() as db:
        created = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('V1')))
        db.commit()
        note_id = created['note']['id']
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.commit()
        other_id = other.id
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        saved = notes.save_note(db, pid, note_id, NoteSave(command_id=key(), expected_revision=1,
                                                          title='Note', content=content('V2')))
        db.commit()
        version_id = saved['note']['version_id']
    enqueue = projections.enqueue
    def interrupted(*_args, **_kwargs):
        raise OSError('Interruption avant validation Brain')
    monkeypatch.setattr(projections, 'enqueue', interrupted)
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['failed'] == 1
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 1
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 1
        assert db.scalar(select(NoteEvidenceBinding)).brain_project_id == original_brain_id
    with erp() as db:
        event = db.scalar(select(NoteEvidenceOutbox).where(NoteEvidenceOutbox.version_id == version_id))
        event.retry_at = None
        assert db.get(NoteVersion, version_id) is not None
        db.commit()
    monkeypatch.setattr(projections, 'enqueue', enqueue)
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 2
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 2
        assert db.scalar(select(NoteEvidenceBinding)).brain_project_id == other_id


def test_relinked_note_refuses_a_conflicting_target_source_without_overwrite(stores):
    from uuid import NAMESPACE_URL, uuid5
    from app.models import Project as BrainProject, SourceArtifact

    brain, erp, pid, _ = stores
    with erp() as db:
        created = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note', content=content('V1')))
        db.commit()
        note_id = created['note']['id']
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['received'] == 1
    with brain() as db:
        other = BrainProject(code='OTHER', name='Autre projet')
        db.add(other)
        db.flush()
        other_id = other.id
        conflicting_id = str(uuid5(NAMESPACE_URL, 'agent:note-source-project:' + pid + ':' + note_id + ':' + other_id))
        db.add(Source(id=conflicting_id, project_id=other_id, source_type='document', status='resolved',
                      original_uri='test://autre', sha256='b' * 64, source_metadata={'origin_kind': 'document'}))
        db.commit()
    with erp() as db:
        db.get(BrainLink, pid).brain_project_id = other_id
        saved = notes.save_note(db, pid, note_id, NoteSave(command_id=key(), expected_revision=1,
                                                          title='Note', content=content('V2')))
        db.commit()
        version_id = saved['note']['version_id']
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain)['failed'] == 1
    with brain() as db:
        assert db.get(Source, conflicting_id).source_metadata == {'origin_kind': 'document'}
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) == 1
    with erp() as db:
        assert db.get(NoteVersion, version_id) is not None
        event = db.scalar(select(NoteEvidenceOutbox).where(NoteEvidenceOutbox.version_id == version_id))
        assert event.status == 'failed'


@pytest.mark.parametrize('terminal', ['received', 'obsolete'])
def test_late_outcomes_cannot_reverse_a_confirmed_event(stores, terminal):
    from backend.app.services.note_projection_port import record_failure, record_result

    _, erp, pid, _ = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note conservée', content=content('Texte fictif')))
        db.commit()
        event_id = db.scalar(select(NoteEvidenceOutbox)).id
    instant = datetime.now(timezone.utc)
    record_result(erp, event_id, terminal, instant)
    assert record_failure(erp, event_id, 'OSError', instant + timedelta(seconds=1)) == terminal
    assert record_result(erp, event_id, 'waiting_project', instant + timedelta(seconds=2)) == terminal
    assert record_result(erp, event_id, 'obsolete' if terminal == 'received' else 'received', instant + timedelta(seconds=3)) == terminal
    with erp() as db:
        event = db.get(NoteEvidenceOutbox, event_id)
        assert event.status == terminal and event.attempts == 0 and event.error is None and event.retry_at is None
        assert event.received_at.replace(tzinfo=timezone.utc) == instant


def test_late_worker_failure_reports_already_confirmed_projection(stores):
    from backend.app.services.note_projection_port import record_result

    brain, erp, pid, _ = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Projection', content=content('Texte fictif')))
        db.commit()
    def other_worker_completed(packet):
        record_result(erp, packet['id'], 'received', datetime.now(timezone.utc))
        raise OSError('Échec tardif fictif')
    assert bridge.process_pending(erp_factory=erp, brain_factory=brain, after_brain_commit=other_worker_completed) == {
        'received': 1, 'obsolete': 0, 'waiting_project': 0, 'failed': 0}
    with erp() as db:
        event = db.scalar(select(NoteEvidenceOutbox))
        assert event.status == 'received' and event.attempts == 0
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        assert db.scalar(select(func.count()).select_from(NoteEvidenceReceipt)) == 1


@pytest.mark.parametrize('include_confirmation', [False, True])
def test_concurrent_outcomes_preserve_confirmation_or_all_retry_counts(stores, include_confirmation):
    from backend.app.services.note_projection_port import record_failure, record_result

    _, erp, pid, _ = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Concurrence', content=content('Texte fictif')))
        db.commit()
        event_id = db.scalar(select(NoteEvidenceOutbox)).id
    instant = datetime.now(timezone.utc)
    barrier = Barrier(6)
    def worker(index):
        barrier.wait(timeout=10)
        if include_confirmation and index == 0:
            return record_result(erp, event_id, 'received', instant)
        return record_failure(erp, event_id, 'OSError', instant)
    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(worker, range(6)))
    with erp() as db:
        event = db.get(NoteEvidenceOutbox, event_id)
        if include_confirmation:
            assert event.status == 'received' and event.error is None and event.retry_at is None
            assert 'received' in outcomes and event.received_at.replace(tzinfo=timezone.utc) == instant
        else:
            assert outcomes == ['failed'] * 6
            assert event.status == 'failed' and event.attempts == 6
            assert event.retry_at.replace(tzinfo=timezone.utc) == instant + timedelta(seconds=1920)


def test_erp_outbox_contract_bounds_events_and_keeps_delivery_timing(stores):
    from backend.app.services.note_projection_port import pending_events, record_result

    _, erp, pid, _ = stores
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Première note', content=content('Texte privé A')))
        notes.create_note(db, pid, NoteCreate(command_id=key(), title='Seconde note', content=content('Texte privé B')))
        db.commit()
    instant = datetime.now(timezone.utc)
    first = pending_events(erp, instant, 1)
    assert len(first) == 1
    assert set(first[0]) == {'id', 'project_id', 'note_id', 'version_id', 'revision', 'digest'}
    assert 'Texte privé' not in str(first)
    with pytest.raises(ValueError, match='Invalid note projection result'):
        record_result(erp, first[0]['id'], 'unexpected', instant)
    assert first[0] in pending_events(erp, instant, 100)
    record_result(erp, first[0]['id'], 'waiting_project', instant)
    assert first[0] not in pending_events(erp, instant, 100)
    assert first[0] in pending_events(erp, instant + timedelta(seconds=31), 100)


def test_erp_projection_contract_rejects_mismatches_and_identifies_an_old_version(stores):
    from backend.app.services.note_projection_port import read_projection

    _, erp, pid, _ = stores
    with erp() as db:
        first = notes.create_note(db, pid, NoteCreate(command_id=key(), title='Note canonique', content=content('Version 1')))
        db.commit()
        event = db.scalar(select(NoteEvidenceOutbox))
        packet = {name: getattr(event, name) for name in ('id', 'project_id', 'note_id', 'version_id', 'revision', 'digest')}
    projection = read_projection(packet, erp)
    assert projection.current and projection.value['title'] == 'Note canonique'
    with pytest.raises(ValueError, match='Canonical note event mismatch'):
        read_projection({**packet, 'digest': '0' * 64}, erp)
    with pytest.raises(ValueError, match='Canonical note event mismatch'):
        read_projection({**packet, 'revision': packet['revision'] + 1}, erp)
    with erp() as db:
        notes.save_note(db, pid, first['note']['id'], NoteSave(command_id=key(), expected_revision=1,
            title='Note canonique', content=content('Version 2')))
        db.commit()
    assert not read_projection(packet, erp).current


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
