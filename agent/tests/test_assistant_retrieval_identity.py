"""Exercise real EG2 -> project/session context without external inference."""
import asyncio

import pytest

from app.models import KnowledgeItem
from app.services import scoped_assistant as assistant
from app.services.eg2_memory import EG2MemoryAdapter
from app.services.settings_service import save_section
from backend.app.models import Milestone
from tests.test_meeting_sessions import stores as stores_fixture, create
from tests.test_session_assistant import enable, source

stores = stores_fixture


class DeterministicChannel:
    profile = 'identity-regression-only'

    async def embed(self, texts, query=False):
        return [[1.0, 0.0] for _ in texts]


@pytest.mark.parametrize('scope', ['project', 'global'])
def test_real_eg2_passage_is_cited_as_source_and_not_knowledge(stores, tmp_path, monkeypatch, scope):
    brain, _, pid, bid = stores
    adapter = EG2MemoryAdapter(brain, channel=DeterministicChannel(), path=tmp_path / 'eg2.db')
    monkeypatch.setattr('app.routers.core.get_memory_adapter', lambda *args: adapter)
    with brain() as db:
        enable(db)
        save_section(db, 'foresight', {'mode': 'remote'})
        text = 'QA-ASSIST : puissance proposée de 1250 W, réception fournisseur à confirmer.'
        src = source(db, bid, text)
        asyncio.run(adapter.remember_evidence(bid, text, {'source_id': src.id}))
        row = assistant.sessions.get_session(db, create(db, project_id=pid)['id'])
        _, messages, metadata = asyncio.run(assistant.prepare(db, row, query='puissance QA-ASSIST', scope=scope))
        citation, = metadata['citations']
        assert citation['source_id'] == src.id
        assert citation['knowledge_id'] is None
        assert citation['source_project_id'] == bid and citation['stamp']
        assert citation['locator']['artifact_id']
        assert text in messages[-1]['content']
        assert assistant.context_current(db, row, metadata)
        # Removing the fictitious source must still invalidate the context.
        src.status = 'discarded'
        db.commit()
        assert not assistant.context_current(db, row, metadata)


def test_canonical_truth_keeps_its_knowledge_identity_and_version_guard(stores, tmp_path, monkeypatch):
    brain, _, pid, bid = stores
    adapter = EG2MemoryAdapter(brain, channel=DeterministicChannel(), path=tmp_path / 'eg2.db')
    monkeypatch.setattr('app.routers.core.get_memory_adapter', lambda *args: adapter)
    with brain() as db:
        enable(db)
        save_section(db, 'foresight', {'mode': 'remote'})
        fact = KnowledgeItem(project_id=bid, status='validated', kind='requirement',
                             subject='Puissance', value='1250 W', validated_by='human')
        db.add(fact)
        db.commit()
        row = assistant.sessions.get_session(db, create(db, project_id=pid)['id'])
        _, _, metadata = asyncio.run(assistant.prepare(db, row, query='puissance', scope='project'))
        citation, = metadata['citations']
        assert citation['knowledge_id'] == fact.id
        assert citation['knowledge_version'] == fact.version and citation['knowledge_stamp']
        assert citation['knowledge_project_id'] == bid
        fact.version += 1
        db.commit()
        assert not assistant.context_current(db, row, metadata)


def test_erp_milestone_identity_is_not_a_knowledge_identity(stores, monkeypatch):
    brain, erp, pid, _ = stores
    class EmptyAdapter:
        async def recall(self, *args):
            return []
    monkeypatch.setattr('app.routers.core.get_memory_adapter', lambda *args: EmptyAdapter())
    with erp() as db:
        db.add(Milestone(project_id=pid, title='FAT', contractual_date='2026-11-03'))
        db.commit()
    with brain() as db:
        enable(db)
        save_section(db, 'foresight', {'mode': 'remote'})
        row = assistant.sessions.get_session(db, create(db, project_id=pid)['id'])
        _, messages, metadata = asyncio.run(assistant.prepare(db, row, query='date FAT', scope='project'))
        citation, = metadata['citations']
        assert citation['scope'] == 'erp_dates' and citation['knowledge_id'] is None
        assert '2026-11-03' in messages[-1]['content']
