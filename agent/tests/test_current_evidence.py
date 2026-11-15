"""Race checks: an embedding finishing after a save cannot revive old evidence."""
import asyncio
import hashlib
import uuid
from types import SimpleNamespace

from app.db import SessionLocal
from app.models import Project, Source, SourceArtifact
from app.services.current_evidence import is_current_evidence
from app.services.eg2_memory import EG2MemoryAdapter
from app.services.projections import _remembered, enqueue


def seed():
    with SessionLocal() as db:
        project = Project(code="FRESH-" + uuid.uuid4().hex, name="Version test")
        db.add(project)
        db.flush()
        source = Source(project_id=project.id, status="resolved", source_type="document",
                        sha256=uuid.uuid4().hex, original_uri="test://freshness")
        db.add(source)
        db.flush()
        artifact = SourceArtifact(source_id=source.id, kind="body_text", content_text="Ancienne réserve 350 lux")
        db.add(artifact)
        db.commit()
        return project.id, source.id, artifact.id


def test_old_import_version_is_not_eligible_even_when_resolved():
    source = SimpleNamespace(status="resolved", project_id="p", source_metadata={"superseded": True})
    assert not is_current_evidence(source)
    source.source_metadata = {}
    assert is_current_evidence(source)
    source.status = "resolution_pending"
    assert not is_current_evidence(source)


def test_save_during_query_embedding_excludes_the_previous_text(tmp_path):
    pid, sid, aid = seed()

    class Channel:
        profile = "freshness"

        async def embed(self, texts, query=False):
            if query:
                with SessionLocal() as db:
                    db.get(SourceArtifact, aid).content_text = "Nouvelle réserve 400 lux"
                    db.commit()
            return [[1.0, 0.0] for _ in texts]

    async def run():
        adapter = EG2MemoryAdapter(SessionLocal, channel=Channel(), path=tmp_path / "index.db")
        await adapter.remember_evidence(pid, "Ancienne réserve 350 lux", {"source_id": sid})
        assert not await adapter.recall(pid, "350 lux", ["evidence"])

    asyncio.run(run())


def test_projection_completion_after_content_save_preserves_cleanup():
    pid, sid, aid = seed()

    class Memory:
        forgotten = []

        async def forget_projection(self, project, ref):
            self.forgotten.append((project, ref))
            return True

    memory = Memory()
    with SessionLocal() as db:
        projection = enqueue(db, pid, "evidence", source_id=sid)
        db.flush()
        projection_id = projection.id
        db.commit()
        db.get(SourceArtifact, aid).content_text = "La réserve a changé"
        db.commit()
        result = asyncio.run(_remembered(db, memory, projection_id, pid, "old-ref", "evidence", sid,
                             content_hash=hashlib.sha256("Ancienne réserve 350 lux".encode()).hexdigest()))
        assert result is None
        db.refresh(projection)
        assert projection.status == "forgotten"
        assert memory.forgotten == [(pid, "old-ref")]
