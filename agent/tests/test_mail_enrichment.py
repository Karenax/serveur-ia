"""Classification commits before slow AI/memory; durable jobs reject stale results."""
import asyncio
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import MemoryProjection, Project, Proposal, Source, SourceArtifact
from app.services import mail_enrichment, triage
from app.services.memory_port import FakeMemoryAdapter
from app.services.settings_service import save_section
from app.workspace_models import MailEnrichmentJob

client = TestClient(app)


@pytest.fixture
def context():
    with SessionLocal() as db:
        projects = [Project(code=uuid.uuid4().hex, name=name) for name in ("A", "B")]
        db.add_all(projects)
        db.flush()
        source = Source(source_type="email", status="resolution_pending", original_uri="test://mail",
                        sha256=uuid.uuid4().hex * 2, source_metadata={"subject": "Mail fictif"})
        db.add(source)
        db.flush()
        db.add(SourceArtifact(source_id=source.id, kind="body_text", content_text="Le diamètre est de 50 mm."))
        proposal = Proposal(source_id=source.id, project_id=projects[0].id, kind="project_attach",
                            subject="Projet", value=projects[0].id)
        db.add(proposal)
        save_section(db, "ai", {"enabled": True})
        db.commit()
        return source.id, [p.id for p in projects], proposal.id


def assign(context, target=0):
    sid, projects, proposal = context
    response = client.post(f"/api/v1/brain/triage/{proposal}/assign", json={"project_id": projects[target]})
    assert response.status_code == 200, response.text
    return response.json()


def test_assignment_does_not_call_ai_or_memory_and_leaves_durable_work(context, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Slow enrichment must not run inside classification")
    monkeypatch.setattr("app.services.ai_client.classify_email", forbidden)
    monkeypatch.setattr("app.services.projections.process", forbidden)
    assign(context)
    sid, projects, _ = context
    with SessionLocal() as db:
        assert db.get(Source, sid).project_id == projects[0]
        job = db.query(MailEnrichmentJob).filter_by(source_id=sid).one()
        assert (job.status, job.stage) == ("queued", "extraction")
        assert job.projection_ids
    assert not any(row["source_id"] == sid for row in client.get("/v1/mail/page?scope=pending").json()["rows"])
    assert client.get("/v1/mail/page", params={"scope": "resolved", "project_id": projects[0]}).json()["total"] == 1


def test_worker_completion_and_memory_retry_do_not_repeat_ai(context, monkeypatch):
    from unittest.mock import Mock
    inference = Mock(return_value=([{"kind": "decision", "subject": "Diamètre", "value": "50 mm"}], "IA"))
    monkeypatch.setattr(triage, "extract_mail_candidates", inference)
    adapter = FakeMemoryAdapter(SessionLocal)
    monkeypatch.setattr("app.services.memory_factory.get_memory_adapter", lambda factory: adapter)
    original = adapter.remember_evidence

    async def failing(*args):
        raise RuntimeError("Temporary memory outage")
    adapter.remember_evidence = failing
    assign(context)
    sid, projects, _ = context
    assert mail_enrichment.process_next(sid)
    with SessionLocal() as db:
        job = db.query(MailEnrichmentJob).filter_by(source_id=sid).one()
        assert job.status == "failed" and job.stage == "memory"
        assert db.get(Source, sid).project_id == projects[0]
        assert db.query(Proposal).filter_by(source_id=sid, kind="decision", status="accepted").count() == 1
        job_id = job.id
    assert client.post(f"/api/v1/workspace/mail-enrichments/{job_id}/retry").status_code == 200
    adapter.remember_evidence = original
    assert mail_enrichment.process_next(sid)
    with SessionLocal() as db:
        assert db.get(MailEnrichmentJob, job_id).status == "completed"
        assert db.query(MemoryProjection).filter_by(source_id=sid, status="indexed").count() == 1
    assert inference.call_count == 1
    assert client.post(f"/api/v1/workspace/mail-enrichments/{job_id}/retry").status_code == 409


@pytest.mark.parametrize("action", ["reclassify", "discard"])
def test_change_while_ai_waits_commits_and_ignores_stale_candidates(context, monkeypatch, action):
    started, release = threading.Event(), threading.Event()

    def delayed(*args, **kwargs):
        started.set()
        assert release.wait(5)
        return ([{"kind": "decision", "subject": "Ancien", "value": "Résultat périmé"}], "IA")
    monkeypatch.setattr(triage, "extract_mail_candidates", delayed)
    monkeypatch.setattr("app.services.memory_factory.get_memory_adapter", lambda factory: FakeMemoryAdapter(factory))
    assign(context)
    sid, projects, _ = context
    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(mail_enrichment.process_next, sid)
        assert started.wait(5)
        try:
            if action == "reclassify":
                response = client.post(f"/api/v1/brain/sources/{sid}/reassign", json={"project_id": projects[1]})
                assert response.status_code == 200, response.text
            else:
                response = client.post(f"/v1/sources/{sid}/discard")
                assert response.status_code == 200, response.text
        finally:
            release.set()
        assert work.result(timeout=5)
    with SessionLocal() as db:
        assert not db.query(Proposal).filter_by(source_id=sid, value="Résultat périmé").count()
        source = db.get(Source, sid)
        job = db.query(MailEnrichmentJob).filter_by(source_id=sid).first()
        if action == "reclassify":
            assert source.project_id == projects[1]
            assert job.revision == 2 and job.status == "queued"
        else:
            assert source.status == "discarded" and job is None
            assert not db.query(SourceArtifact).filter_by(source_id=sid).count()


def test_running_job_is_recovered_after_restart(context):
    assign(context)
    with SessionLocal() as db:
        job = db.query(MailEnrichmentJob).filter_by(source_id=context[0]).one()
        job.status = "running"
        db.commit()
        mail_enrichment.recover_interrupted(db)
        assert job.status == "queued"


def test_unusable_llm_response_remains_retryable_in_extraction(context, monkeypatch):
    sid = context[0]
    assign(context)
    monkeypatch.setattr("app.services.ai_client.classify_email", lambda *args, **kwargs: None)
    assert mail_enrichment.process_next(sid, worker_stage="extraction")
    with SessionLocal() as db:
        job = db.query(MailEnrichmentJob).filter_by(source_id=sid).one()
        assert (job.status, job.stage) == ("failed", "extraction")
        assert db.get(Source, sid).status == "resolved"
        assert not db.query(Proposal).filter_by(source_id=sid, kind="fact").count()
        job_id = job.id
    assert client.post(f"/api/v1/workspace/mail-enrichments/{job_id}/retry").status_code == 200
    monkeypatch.setattr("app.services.ai_client.classify_email", lambda *args, **kwargs:
                        {"items": [{"kind": "fact", "value": "Extraction reprise"}]})
    assert mail_enrichment.process_next(sid, worker_stage="extraction")
    with SessionLocal() as db:
        job = db.get(MailEnrichmentJob, job_id)
        assert (job.status, job.stage) == ("queued", "memory")
        assert db.query(Proposal).filter_by(source_id=sid, value="Extraction reprise").count() == 1


def test_slow_memory_does_not_block_next_mail_extraction(context, monkeypatch):
    from app.services.projections import enqueue as project_projection
    sid, projects, _ = context
    assign(context)
    extracted = []

    def extract(*args, **kwargs):
        extracted.append(args[0])
        return [{"kind": "fact", "subject": "Dimension", "value": "50 mm"}], "IA"

    monkeypatch.setattr(triage, "extract_mail_candidates", extract)
    started, release = threading.Event(), threading.Event()

    async def slow_memory(*args, **kwargs):
        started.set()
        await asyncio.to_thread(release.wait, 5)
        return {"indexed": 1, "failed": 0, "forgotten": 0}

    monkeypatch.setattr("app.services.projections.process", slow_memory)
    assert mail_enrichment.process_next(sid, worker_stage="extraction")
    with SessionLocal() as db:
        first = db.query(MailEnrichmentJob).filter_by(source_id=sid).one()
        assert (first.status, first.stage) == ("queued", "memory")
        source = Source(source_type="email", status="resolved", project_id=projects[0],
                        original_uri="test://second", sha256=uuid.uuid4().hex * 2,
                        source_metadata={"subject": "Second mail"})
        db.add(source)
        db.flush()
        db.add(SourceArtifact(source_id=source.id, kind="body_text", content_text="Dimension 50 mm"))
        project_projection(db, projects[0], "evidence", source_id=source.id)
        mail_enrichment.enqueue(db, source, db.get(Project, projects[0]), True)
        second = source.id
        db.commit()
    with ThreadPoolExecutor(max_workers=1) as pool:
        indexing = pool.submit(mail_enrichment.process_next, sid, "memory")
        assert started.wait(5)
        try:
            assert mail_enrichment.process_next(second, worker_stage="extraction")
            assert extracted[-1] == "Second mail"
            assert not indexing.done()
            with SessionLocal() as db:
                job = db.query(MailEnrichmentJob).filter_by(source_id=second).one()
                assert (job.status, job.stage) == ("queued", "memory")
        finally:
            release.set()
        assert indexing.result(timeout=5)


def test_job_is_visible_only_in_its_linked_erp_project(context):
    from backend.app.db import SessionLocal as ERP
    from backend.app.models import BrainLink, Project as ERPProject
    assign(context)
    with ERP() as db:
        project = ERPProject(code=uuid.uuid4().hex, title="Projet lié")
        other = ERPProject(code=uuid.uuid4().hex, title="Autre projet")
        db.add_all([project, other])
        db.flush()
        db.add(BrainLink(project_id=project.id, brain_project_id=context[1][0], brain_code=project.code))
        db.commit()
        own_id, other_id = project.id, other.id
    jobs = client.get("/api/v1/workspace/jobs", params={"project_id": own_id}).json()
    assert jobs["total"] == 1
    row = jobs["items"][0]
    assert row["engine"] == "mail" and row["source_id"] == context[0]
    assert row["unit"] == "steps" and row["status"] == "queued"
    assert not row["can_cancel"]
    assert client.get("/api/v1/workspace/jobs", params={"project_id": other_id}).json()["total"] == 0


def test_restored_jobs_wait_for_explicit_retry(context, tmp_path):
    import sqlite3
    from pathlib import Path
    from app.config import STORAGE_DIR, settings
    from app.services.backup import create_backup, restore_backup
    from backend.app.db import APP_DIR
    from sqlalchemy.engine import make_url
    assign(context)
    with SessionLocal() as db:
        job_id = db.query(MailEnrichmentJob).filter_by(source_id=context[0]).one().id
    backup, destination = tmp_path / "backup", tmp_path / "restore"
    create_backup(backup, Path(make_url(settings.database_url).database), APP_DIR, STORAGE_DIR)
    restore_backup(backup, destination)
    with sqlite3.connect(destination / "brain/project_brain.db") as db:
        row = db.execute("SELECT status, stage FROM mail_enrichment_jobs WHERE id=?", (job_id,)).fetchone()
        assert row == ("failed", "extraction")
        assert db.execute("SELECT status FROM sources WHERE id=?", (context[0],)).fetchone()[0] == "resolved"


def test_evidence_is_not_restored_if_classification_changes_during_indexing(context):
    from app.services.projections import process
    assign(context)
    sid, projects, _ = context

    class ReclassifyingMemory(FakeMemoryAdapter):
        async def remember_evidence(self, project_id, content, metadata):
            with SessionLocal() as other:
                triage.resolve_source(other, None, other.get(Source, sid), other.get(Project, projects[1]),
                                      {"enabled": True}, "test", defer_enrichment=True)
            return await super().remember_evidence(project_id, content, metadata)

    with SessionLocal() as db:
        projection = db.query(MemoryProjection).filter_by(source_id=sid, project_id=projects[0]).one()
        pid = projection.id
        result = asyncio.run(process(db, ReclassifyingMemory(SessionLocal), projection_ids=[pid]))
        assert result["indexed"] == 0
        db.expire_all()
        assert db.get(MemoryProjection, pid).status == "forgotten"
        assert db.get(Source, sid).project_id == projects[1]
