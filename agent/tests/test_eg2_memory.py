"""Production EG2 contract: persistence, ownership, atomic failure and profile isolation."""
import asyncio
import uuid

import pytest

from app.db import SessionLocal
from app.models import Project, Source, SourceArtifact
from app.services.eg2_memory import EG2MemoryAdapter, eg2_passages, split_passages


class Channel:
    profile = "eg2-test"
    model = "text-embedding-embeddinggemma-2"

    async def embed(self, texts, query=False):
        return [[1.0, 0.0] if "316L" in t else [0.0, 1.0] for t in texts]


def seed():
    with SessionLocal() as db:
        p = Project(code="EG2-" + uuid.uuid4().hex, name="Isolation")
        db.add(p)
        db.flush()
        s = Source(project_id=p.id, status="resolved", source_type="email",
                   original_uri="test://eg2", sha256=uuid.uuid4().hex)
        db.add(s)
        db.flush()
        db.add(SourceArtifact(source_id=s.id, kind="body_text", content_text="Inox 316L"))
        db.commit()
        return p.id, s.id


def test_persistent_index_provenance_project_filter_and_canonical_invalidation(tmp_path):
    async def run():
        project, source = seed()
        path = tmp_path / "index.db"
        adapter = EG2MemoryAdapter(SessionLocal, channel=Channel(), path=path)
        ref = await adapter.remember_evidence(project, "Inox 316L", {"source_id": source})
        adapter = EG2MemoryAdapter(SessionLocal, channel=Channel(), path=path)
        assert not await adapter.recall("foreign", "316L", ["evidence"])
        hits = await adapter.recall(project, "316L", ["evidence"])
        assert hits[0]["source_id"] == source and hits[0]["level"] == "proposed"
        with SessionLocal() as db:
            db.get(Source, source).status = "discarded"
            db.commit()
        assert not await adapter.recall(project, "316L", ["evidence"])
        assert await adapter.forget_projection("foreign", ref)
        assert (await adapter.health())["passages"] == 1
        assert await adapter.forget_projection(project, ref)
        assert (await adapter.health())["passages"] == 0
    asyncio.run(run())


def test_failed_replacement_preserves_old_index_and_profile_change_fails_closed(tmp_path):
    async def run():
        project, source = seed()
        adapter = EG2MemoryAdapter(SessionLocal, channel=Channel(), path=tmp_path / "index.db")
        await adapter.remember_evidence(project, "Inox 316L", {"source_id": source})
        class Failing(Channel):
            async def embed(self, texts, query=False):
                raise RuntimeError("server unavailable")
        failing = EG2MemoryAdapter(SessionLocal, channel=Failing(), path=adapter.path)
        with pytest.raises(RuntimeError):
            await failing.remember_evidence(project, "Updated material", {"source_id": source})
        assert (await adapter.recall(project, "316L", ["evidence"]))[0]["text"] == "Inox 316L"
        class Different(Channel):
            profile = "new-profile"
        changed = EG2MemoryAdapter(SessionLocal, channel=Different(), path=adapter.path)
        with pytest.raises(ValueError, match="reconstruction"):
            await changed.recall(project, "316L", ["evidence"])
    asyncio.run(run())


def test_long_chunking_retains_every_word_including_final_decision():
    text = " ".join(f"word{i}" for i in range(2000)) + "\n\nDécision finale inox 316L."
    chunks = split_passages(text)
    assert len(chunks) > 10 and all(len(c.split()) <= 160 for c in chunks)
    assert set(text.split()) <= set(" ".join(chunks).split())
    assert chunks[-1] == "Décision finale inox 316L."


def test_recall_uses_only_migrated_sources_and_reports_partial_index(tmp_path):
    async def run():
        project, old_source = seed()
        _, ready_source = seed()
        with SessionLocal() as db:
            db.get(Source, ready_source).project_id = project
            db.commit()
        old = EG2MemoryAdapter(SessionLocal, channel=Channel(), path=tmp_path / 'index.db')
        await old.remember_evidence(project, 'Inox 316L', {'source_id': old_source})
        channel = Channel()
        channel.profile = 'new-profile'
        current = EG2MemoryAdapter(SessionLocal, channel=channel, path=old.path)
        await current.remember_evidence(project, 'Inox 316L', {'source_id': ready_source})
        results = await current.recall(project, '316L', ['evidence'])
        assert [item['source_id'] for item in results if 'source_id' in item] == [ready_source]
        assert any('reconstruction' in item.get('error', '') for item in results)

    asyncio.run(run())


def test_eg2_chunks_a_long_run_without_losing_characters():
    text = 'a1' * 21000 + ' fin'
    passages = eg2_passages(text)
    assert all(len(passage) <= 1536 for passage in passages)
    assert ''.join(passages) == text


def test_replaced_artifact_is_excluded_before_reindexing(tmp_path):
    async def run():
        project, source = seed()
        adapter = EG2MemoryAdapter(SessionLocal, channel=Channel(), path=tmp_path / "index.db")
        await adapter.remember_evidence(project, "Inox 316L", {"source_id": source})
        with SessionLocal() as db:
            db.query(SourceArtifact).filter_by(source_id=source).one().content_text = "Document remplacé"
            db.commit()
        assert not await adapter.recall(project, "316L", ["evidence"])
    asyncio.run(run())


def test_remote_failure_keeps_validated_truth_available(tmp_path):
    async def run():
        from app.models import KnowledgeItem
        project, source = seed()
        adapter = EG2MemoryAdapter(SessionLocal, channel=Channel(), path=tmp_path / "index.db")
        await adapter.remember_evidence(project, "Inox 316L", {"source_id": source})
        with SessionLocal() as db:
            db.add(KnowledgeItem(project_id=project, status="validated", kind="requirement",
                                 subject="Matière", value="Inox 316L", validated_by="human"))
            db.commit()
        class Failing(Channel):
            async def embed(self, texts, query=False):
                raise RuntimeError("remote unavailable")
        failed = EG2MemoryAdapter(SessionLocal, channel=Failing(), path=adapter.path)
        hits = await failed.recall(project, "316L", ["truth", "evidence"])
        assert hits[0]["value"] == "Inox 316L" and hits[0]["level"] == "validated"
        assert hits[-1]["error"]
    asyncio.run(run())


def test_memory_probe_never_contacts_server_in_fixture_mode(monkeypatch):
    from app.routers.settings import test_memory
    async def forbidden(self):
        raise AssertionError("External probe in isolated tests")
    monkeypatch.setattr(EG2MemoryAdapter, "probe", forbidden)
    with SessionLocal() as db:
        assert test_memory(db)["status"] == "skipped"
