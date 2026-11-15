"""Default truth remains source-backed, reversible and respectful of human decisions."""
import asyncio
import uuid

import pytest
from fastapi import HTTPException
from app.db import SessionLocal
from app.models import Project, Source, Proposal, KnowledgeItem, ProvenanceLink, ValidationDecision, MemoryProjection
from app.services.knowledge_defaults import accept_by_default, change_status
from app.services.memory_port import FakeMemoryAdapter


def seed(db, status='pending', kind='fact', resolved=True):
    token = uuid.uuid4().hex
    project = Project(code=token, name='Test')
    db.add(project)
    db.flush()
    source = Source(project_id=project.id, source_type='email', status='resolved' if resolved else 'resolution_pending',
                    original_uri='test://mail', sha256=token)
    db.add(source)
    db.flush()
    proposal = Proposal(project_id=project.id, source_id=source.id, kind=kind, subject='Diamètre',
                        value='50 mm', status=status, confidence=.8)
    db.add(proposal)
    db.flush()
    return project, source, proposal


def test_default_information_is_immediate_with_provenance_and_no_llm_job():
    with SessionLocal() as db:
        project, source, proposal = seed(db)
        assert accept_by_default(db, proposal)
        db.commit()
        item = db.query(KnowledgeItem).filter_by(project_id=project.id).one()
        assert item.validated_by == 'auto-default'
        assert db.query(ProvenanceLink).filter_by(knowledge_item_id=item.id, source_id=source.id).count() == 1
        assert db.query(ValidationDecision).filter_by(proposal_id=proposal.id, actor='auto-default').count() == 1
        assert not db.query(MemoryProjection).filter_by(knowledge_item_id=item.id).count()
        hits = asyncio.run(FakeMemoryAdapter(SessionLocal).recall(project.id, '', ['truth']))
        assert any(h['value'] == '50 mm' and h['validation_mode'] == 'default' and h['source_id'] == source.id for h in hits)
        assert not accept_by_default(db, proposal)


@pytest.mark.parametrize('status,kind,resolved', [
    ('rejected', 'fact', True), ('deferred', 'fact', True),
    ('pending', 'project_attach', True), ('pending', 'fact', False)])
def test_human_exceptions_and_unresolved_sources_remain_untouched(status, kind, resolved):
    with SessionLocal() as db:
        project, _, proposal = seed(db, status, kind, resolved)
        assert not accept_by_default(db, proposal)
        assert proposal.status == status
        assert not db.query(KnowledgeItem).filter_by(project_id=project.id).count()


def test_demotion_restore_and_reextraction_cannot_resurrect_information():
    with SessionLocal() as db:
        project, source, proposal = seed(db)
        assert accept_by_default(db, proposal)
        db.commit()
        item = db.query(KnowledgeItem).filter_by(project_id=project.id).one()
        assert change_status(db, project.id, item.id, 'invalidate', 'test')['status'] == 'invalidated'
        assert proposal.status == 'rejected'
        assert not asyncio.run(FakeMemoryAdapter(SessionLocal).recall(project.id, '', ['truth']))
        again = Proposal(project_id=project.id, source_id=source.id, kind='fact', subject='Diamètre', value='50 mm')
        db.add(again)
        db.flush()
        assert not accept_by_default(db, again)
        assert db.get(Source, source.id) is not None
        assert change_status(db, project.id, item.id, 'restore', 'test')['status'] == 'validated'
        assert proposal.status == 'accepted'
        assert asyncio.run(FakeMemoryAdapter(SessionLocal).recall(project.id, '', ['truth']))
        with pytest.raises(HTTPException) as error:
            change_status(db, 'other-project', item.id, 'invalidate', 'test')
        assert error.value.status_code == 404


def test_default_conflict_preserves_human_truth_and_restore_checks_source():
    with SessionLocal() as db:
        project, source, proposal = seed(db)
        human = KnowledgeItem(project_id=project.id, kind='fact', subject='Diamètre', value='52 mm',
                              status='validated', validated_by='human')
        db.add(human)
        db.flush()
        assert accept_by_default(db, proposal)
        db.commit()
        assert human.status == 'validated'
        assert db.query(KnowledgeItem).filter_by(project_id=project.id, status='validated').count() == 2
        item = db.query(KnowledgeItem).filter_by(project_id=project.id, validated_by='auto-default').one()
        change_status(db, project.id, item.id, 'invalidate', 'test')
        source.status = 'resolution_pending'
        db.commit()
        with pytest.raises(HTTPException) as error:
            change_status(db, project.id, item.id, 'restore', 'test')
        assert error.value.status_code == 409


def test_assistant_does_not_reintroduce_demoted_information_from_evidence(monkeypatch):
    from app.routers import core
    from app.schemas import ChatQuery
    from app.services.settings_service import save_section
    with SessionLocal() as db:
        project, _, proposal = seed(db)
        assert accept_by_default(db, proposal)
        db.commit()
        item = db.query(KnowledgeItem).filter_by(project_id=project.id).one()
        change_status(db, project.id, item.id, 'invalidate', 'test')
        save_section(db, 'ai', {'enabled': True})
        db.commit()
        class Adapter:
            async def recall(self, *args):
                return [{'scope': 'evidence', 'text': 'Le diamètre est de 50 mm.', 'source_id': 'source'}]
        monkeypatch.setattr(core, 'get_memory_adapter', lambda *_: Adapter())
        _, messages, metadata = asyncio.run(core.prepare_chat(
            ChatQuery(query='Diamètre ?', project_id=project.id, include_evidence=True), db))
        assert not metadata['citations']
        assert '50 mm' not in messages[-1]['content']


def test_large_project_finds_relevant_default_information_beyond_first_fifty_rows():
    from app.services.eg2_memory import EG2MemoryAdapter
    with SessionLocal() as db:
        project, _, proposal = seed(db)
        for index in range(60):
            db.add(KnowledgeItem(project_id=project.id, kind='fact', subject='Diamètre ancien',
                                 value=f'Autre équipement {index}'))
        db.flush()
        proposal.subject = 'Diamètre codeur ATEX'
        assert accept_by_default(db, proposal)
        db.commit()
        for adapter in [FakeMemoryAdapter(SessionLocal), EG2MemoryAdapter(db_factory=SessionLocal)]:
            hits = asyncio.run(adapter.recall(project.id, 'Diamètre codeur ATEX', ['truth']))
            assert hits[0]['subject'] == 'Diamètre codeur ATEX'
            assert hits[0]['validation_mode'] == 'default'


def test_demotion_does_not_hide_another_active_information_with_the_same_value(monkeypatch):
    from app.routers import core
    from app.schemas import ChatQuery
    from app.services.settings_service import save_section
    with SessionLocal() as db:
        project, _, proposal = seed(db)
        assert accept_by_default(db, proposal)
        db.commit()
        item = db.query(KnowledgeItem).filter_by(project_id=project.id).one()
        change_status(db, project.id, item.id, 'invalidate', 'test')
        other = KnowledgeItem(project_id=project.id, kind='fact', subject='Largeur', value='50 mm', validated_by='human')
        db.add(other)
        save_section(db, 'ai', {'enabled': True})
        db.commit()
        monkeypatch.setattr(core, 'get_memory_adapter', lambda *_: FakeMemoryAdapter(SessionLocal))
        _, messages, metadata = asyncio.run(core.prepare_chat(
            ChatQuery(query='Largeur ?', project_id=project.id, include_evidence=False), db))
        assert any(c['knowledge_id'] == other.id for c in metadata['citations'])
        assert all(c['knowledge_id'] != item.id for c in metadata['citations'])
        assert '50 mm' in messages[-1]['content']
