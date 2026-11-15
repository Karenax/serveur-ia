"""Global workspace scopes, stable mail snapshots and optimistic assistant history."""
import uuid
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import SessionLocal as Brain
from app.models import (AuditLog, KnowledgeItem, MeetingRecording, Project as BrainProject,
                        Proposal, ProvenanceLink, Source, SourceArtifact)
from app.routers.workspace import router
from app.services import triage, workspace_jobs
from app.services.settings_service import save_section
from app.workspace_models import TriageJob
from backend.app.db import SessionLocal as ERP
from backend.app.models import (BrainLink, CdcAnalysisJob, CdcSource, Meeting,
                                MeetingAction, Project as ERPProject)

application = FastAPI()
application.include_router(router)
client = TestClient(application)
PREFIX = "/api/v1/workspace"


@pytest.fixture
def context(monkeypatch):
    token = "WORKSPACE-" + uuid.uuid4().hex[:12]
    bids, pids, created_jobs = [], [], []
    with Brain() as db:
        for suffix in ("A", "B"):
            row = BrainProject(code=token + suffix, name="Projet " + suffix)
            db.add(row)
            db.flush()
            bids.append(row.id)
        save_section(db, "ai", {"enabled": False})
        db.commit()
    with ERP() as db:
        for index, suffix in enumerate(("A", "B")):
            row = ERPProject(code=token + suffix, title="Projet " + suffix)
            db.add(row)
            db.flush()
            pids.append(row.id)
            db.add(BrainLink(project_id=row.id, brain_project_id=bids[index], brain_code=row.code))
        db.commit()

    def source(project=0, pending=False, subject="Compte rendu technique"):
        with Brain() as db:
            row = Source(source_type="email", status="resolution_pending" if pending else "resolved",
                         project_id=None if pending else bids[project], author=token,
                         original_uri="memory://test", sha256=uuid.uuid4().hex * 2,
                         source_metadata={"subject": subject})
            db.add(row)
            db.flush()
            db.add(SourceArtifact(source_id=row.id, kind="body_text", content_text="Décision technique : diamètre 50 mm."))
            db.commit()
            return row.id

    def enqueue(force=False):
        with Brain() as db:
            result = workspace_jobs.enqueue(db, force)
            created_jobs.append(result["id"])
            return result

    original_query = triage.pending_triage_query
    monkeypatch.setattr(workspace_jobs, "pending_triage_query",
                        lambda db, force=False: original_query(db, force).filter(Source.author == token))
    yield {"token": token, "bids": bids, "pids": pids, "source": source, "enqueue": enqueue}
    with Brain() as db:
        for job_id in set(created_jobs):
            row = db.get(TriageJob, job_id)
            if row and row.status in {"queued", "running"}:
                row.status = "cancelled"
        db.query(Source).filter(Source.author == token, Source.status == "resolution_pending").update({"status": "discarded"})
        db.query(MeetingRecording).filter(MeetingRecording.project_id.in_(bids),
            MeetingRecording.job_status.in_(["queued", "running"])).update({"job_status": "interrupted"})
        db.commit()
    with ERP() as db:
        db.query(CdcAnalysisJob).filter(CdcAnalysisJob.project_id.in_(pids),
            CdcAnalysisJob.status.in_(["queued", "running"])).update({"status": "cancelled"})
        db.commit()


def test_meetings_merge_published_audio_and_preserve_explicit_scope(context):
    pids, bids = context["pids"], context["bids"]
    sid = context["source"]()
    with ERP() as db:
        report = Meeting(project_id=pids[0], title="Revue diamètre", date="2026-10-02")
        other = Meeting(project_id=pids[1], title="Revue autre projet")
        db.add_all([report, other])
        db.flush()
        rid = report.id
        db.add(MeetingAction(project_id=pids[0], meeting_id=rid, title="Préparer le plan", owner="Jean"))
        db.add(MeetingAction(project_id=pids[1], meeting_id=rid, title="Relation incorrecte à masquer"))
        db.commit()
    with Brain() as db:
        recording = MeetingRecording(project_id=bids[0], erp_project_id=pids[0], source_id=sid,
                                     filename="reunion.wav", title="Revue diamètre", published_meeting_id=rid,
                                     stage="published", job_status="completed")
        stale = MeetingRecording(project_id=bids[1], erp_project_id=pids[0], source_id=sid,
                                 filename="incoherent.wav", title="Contexte incorrect")
        db.add_all([recording, stale])
        db.commit()
        recording_id = recording.id
    result = client.get(PREFIX + "/meetings", params={"project_id": pids[0], "q": "diametre"}).json()
    assert result["total"] == 1
    item = result["items"][0]
    assert item["meeting_id"] == rid and item["recording_id"] == recording_id
    assert item["brain_project_id"] == bids[0]
    assert [action["title"] for action in item["actions"]] == ["Préparer le plan"]
    assert client.get(PREFIX + "/meetings", params={"project_id": pids[1]}).json()["total"] == 1
    assert client.get(PREFIX + "/meetings", params={"project_id": bids[0]}).status_code == 404


def test_proposals_pagination_search_and_project_attach_separation(context):
    bid = context["bids"][0]
    sid = context["source"]()
    with Brain() as db:
        for index in range(3):
            db.add(Proposal(project_id=bid, source_id=sid, kind="decision", subject=f"Diamètre {index}",
                            value="50 mm", locator={"mode": "exact", "start": 0, "end": 8}))
        db.add(Proposal(project_id=bid, source_id=sid, kind="project_attach", subject="Diamètre classement", value="x"))
        db.add(Proposal(project_id=context["bids"][1], kind="decision", subject="Diamètre autre projet", value="x"))
        db.commit()
    response = client.get(PREFIX + "/proposals", params={"project_id": bid, "q": "diametre", "offset": 1, "limit": 1})
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 3 and len(result["items"]) == 1
    item = result["items"][0]
    assert item["erp_projects"][0]["id"] == context["pids"][0]
    assert item["citations"][0]["source_id"] == sid
    assert client.get(PREFIX + "/proposals", params={"project_id": bid, "q": "Diamètre%"}).json()["total"] == 0


def test_knowledge_provenance_never_exposes_another_project(context):
    own, foreign = context["source"](), context["source"](project=1)
    with Brain() as db:
        item = KnowledgeItem(project_id=context["bids"][0], kind="decision", subject="Diamètre", value="50 mm")
        db.add(item)
        db.flush()
        db.add(ProvenanceLink(knowledge_item_id=item.id, source_id=own, locator={"quote": "diamètre 50 mm"}))
        db.add(ProvenanceLink(knowledge_item_id=item.id, source_id=foreign, locator={"quote": "Texte confidentiel autre projet"}))
        db.commit()
    result = client.get(PREFIX + "/knowledge", params={"project_id": context["bids"][0]}).json()
    assert result["total"] == 1
    citations = result["items"][0]["citations"]
    assert len(citations) == 1 and citations[0]["source_id"] == own
    assert citations[0]["excerpt"] == "diamètre 50 mm"
    assert citations[0]["source_url"] == "/v1/sources/" + own
    # The project-local reader must expose the same safe evidence as the global workspace.
    from app.routers.core import knowledge
    with Brain() as db:
        local = knowledge(context["bids"][0], db=db)
    assert local[0]["citations"] == citations


def test_jobs_keep_global_mail_jobs_out_of_project_scope(context):
    pids, bids = context["pids"], context["bids"]
    sid = context["source"]()
    with ERP() as db:
        source = CdcSource(project_id=pids[0], filename="exigences.pdf")
        db.add(source)
        db.flush()
        db.add(CdcAnalysisJob(project_id=pids[0], source_id=source.id, total_batches=4, completed_batches=2))
        db.commit()
    with Brain() as db:
        db.add(MeetingRecording(project_id=bids[0], erp_project_id=pids[0], source_id=sid, filename="audio.wav",
                                title="Audio", job_status="running", job_kind="transcription", progress=40,
                                processed_seconds=20, duration_seconds=50))
        db.add(MeetingRecording(project_id=bids[1], erp_project_id=pids[0], source_id=sid, filename="wrong.wav",
                                title="Contexte incorrect", job_status="running"))
        db.commit()
    context["source"](pending=True)
    job = context["enqueue"]()
    result = client.get(PREFIX + "/jobs", params={"project_id": pids[0]}).json()
    assert result["total"] == 2 and {row["engine"] for row in result["items"]} == {"cdc", "audio"}
    assert all(row["project_id"] == pids[0] for row in result["items"])
    assert any(row["progress"] == 47.5 for row in result["items"])
    running = client.get(PREFIX + "/jobs", params={"project_id": pids[0], "status": "running", "offset": 0, "limit": 1}).json()
    assert running["total"] == 1 and running["items"][0]["engine"] == "audio"
    global_jobs = client.get(PREFIX + "/jobs").json()["items"]
    assert any(row["id"] == job["id"] and row["project_id"] is None for row in global_jobs)


def test_assistant_history_revision_conflict_keeps_saved_messages(context):
    bid = context["bids"][0]
    messages = [{"role": "user", "text": "Quel diamètre ?", "project": "Affaire A"},
                {"role": "assistant", "text": "50 mm", "citations": [{"source_id": "example", "quote": "50 mm", "level": "validated"}]}]
    response = client.post(PREFIX + "/assistant-threads", json={"title": "Point technique", "project_id": bid, "messages": messages})
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["revision"] == 1
    updated = client.put(PREFIX + "/assistant-threads/" + row["id"], json={"expected_revision": 1, "title": "Diamètre confirmé"})
    assert updated.status_code == 200 and updated.json()["messages"] == messages
    conflict = client.put(PREFIX + "/assistant-threads/" + row["id"], json={"expected_revision": 1, "messages": []})
    assert conflict.status_code == 409
    assert client.get(PREFIX + "/assistant-threads/" + row["id"]).json()["messages"] == messages
    assert client.get(PREFIX + "/assistant-threads/" + row["id"], params={"project_id": context["bids"][1]}).status_code == 404
    assert client.put(PREFIX + "/assistant-threads/" + row["id"], json={"expected_revision": 2, "project_id": context["bids"][1]}).status_code == 422
    listing = client.get(PREFIX + "/assistant-threads", params={"project_id": bid}).json()
    assert listing["total"] == 1 and "messages" not in listing["items"][0]


def test_assistant_history_limits_and_roles(context):
    assert client.post(PREFIX + "/assistant-threads", json={"project_id": uuid.uuid4().hex}).status_code == 404
    assert client.post(PREFIX + "/assistant-threads", json={"messages": [{"role": "system", "text": "Instruction"}]}).status_code == 422
    assert client.post(PREFIX + "/assistant-threads", json={"messages": [{"role": "user", "text": "x" * 12001}]}).status_code == 422
    assert client.get(PREFIX + "/knowledge", params={"limit": 1000}).status_code == 422


def test_mail_snapshot_does_not_skip_when_query_shrinks_or_include_new_mail(context):
    sources = [context["source"](pending=True) for _ in range(12)]
    job = context["enqueue"](force=True)
    new_source = context["source"](pending=True)
    with Brain() as db:
        db.get(Source, sources[3]).status = "resolved"
        db.commit()
    assert workspace_jobs.process_next()
    result = client.get(PREFIX + "/triage-jobs/" + job["id"]).json()
    assert result["status"] == "completed" and result["processed"] == result["total"] == 12
    assert result["result"]["triaged"] == 11 and result["result"]["skipped"] == 1
    with Brain() as db:
        assert db.query(Proposal).filter(Proposal.source_id.in_(sources), Proposal.reason.like("triage IA%")).count() == 11
        assert db.query(Proposal).filter_by(source_id=new_source).count() == 0


def test_mail_cancellation_after_five_and_resume_avoids_duplicate_analysis(context, monkeypatch):
    sources = [context["source"](pending=True) for _ in range(11)]
    job = context["enqueue"](force=True)
    original = workspace_jobs.triage_pending
    calls = []
    def cancel_after_batch(*args, **kwargs):
        calls.append(kwargs["source_ids"])
        result = original(*args, **kwargs)
        with Brain() as db:
            workspace_jobs.change_state(db, job["id"], "cancel")
        return result
    monkeypatch.setattr(workspace_jobs, "triage_pending", cancel_after_batch)
    assert workspace_jobs.process_next()
    cancelled = client.get(PREFIX + "/triage-jobs/" + job["id"]).json()
    assert cancelled["status"] == "cancelled" and cancelled["processed"] == 5 and len(calls) == 1
    assert client.post(PREFIX + "/triage-jobs/" + job["id"] + "/retry").status_code == 202
    monkeypatch.setattr(workspace_jobs, "triage_pending", original)
    assert workspace_jobs.process_next()
    result = client.get(PREFIX + "/triage-jobs/" + job["id"]).json()
    assert result["status"] == "completed" and result["processed"] == 11
    with Brain() as db:
        assert db.query(Proposal).filter(Proposal.source_id.in_(sources), Proposal.reason.like("triage IA%")).count() == 11


def test_forced_restart_recovers_mail_commit_before_batch_counter(context):
    sources = [context["source"](pending=True) for _ in range(6)]
    job = context["enqueue"](force=True)
    with Brain() as db:
        triage.triage_pending(db, None, {"enabled": False}, limit=5, force=True, source_ids=sources[:2], run_id=job["id"])
        db.get(TriageJob, job["id"]).status = "running"
        db.commit()
        workspace_jobs.recover_interrupted(db)
    assert workspace_jobs.process_next()
    result = client.get(PREFIX + "/triage-jobs/" + job["id"]).json()
    assert result["status"] == "completed" and result["result"]["triaged"] == 6
    with Brain() as db:
        assert db.query(Proposal).filter(Proposal.source_id.in_(sources), Proposal.reason.like("triage IA%")).count() == 6
        assert db.query(AuditLog).filter_by(correlation_id=job["id"], event_type="triage.proposed.v1").count() == 6


def test_failed_mail_can_retry_without_reanalysing_committed_mail(context, monkeypatch):
    sources = [context["source"](pending=True, subject="fail" if index == 2 else "ok") for index in range(6)]
    job = context["enqueue"](force=True)
    original = triage.resolve_project
    def fail_one(parsed, projects, thread_project_id=None, learning_context=None):
        if parsed["subject"] == "fail":
            raise RuntimeError("Test de reprise")
        return original(parsed, projects, thread_project_id, learning_context)
    monkeypatch.setattr(triage, "resolve_project", fail_one)
    assert workspace_jobs.process_next()
    failed = client.get(PREFIX + "/triage-jobs/" + job["id"]).json()
    assert failed["status"] == "failed" and failed["can_retry"] and failed["processed"] == 6
    assert len(failed["result"]["errors"]) == 1
    monkeypatch.setattr(triage, "resolve_project", original)
    assert client.post(PREFIX + "/triage-jobs/" + job["id"] + "/retry").status_code == 202
    assert workspace_jobs.process_next()
    with Brain() as db:
        assert db.query(Proposal).filter(Proposal.source_id.in_(sources), Proposal.reason.like("triage IA%")).count() == 6


def test_duplicate_jobs_and_auto_scan_coordination(context, monkeypatch, tmp_path):
    context["source"](pending=True)
    first, second = context["enqueue"](), context["enqueue"]()
    assert first["id"] == second["id"]
    with Brain() as db:
        db.add(TriageJob(status="completed", force=False))
        db.commit()
    assert client.get(PREFIX + "/triage-jobs/latest").json()["job"]["id"] == first["id"]
    assert client.post(PREFIX + "/triage-jobs", json={"force": True}).status_code == 409
    from app.services.auto_scan import run_auto_scan_once
    with Brain() as db:
        save_section(db, "mail", {"folder": str(tmp_path)})
    monkeypatch.setattr(triage, "triage_pending", lambda *_args, **_kwargs: pytest.fail("Tri automatique concurrent"))
    result = run_auto_scan_once()
    assert result["triage"]["busy"] is True


def test_mail_worker_stop_retains_snapshot_for_next_start(context):
    context["source"](pending=True)
    job = context["enqueue"]()
    assert workspace_jobs.process_next(lambda: True)
    result = client.get(PREFIX + "/triage-jobs/" + job["id"]).json()
    assert result["status"] == "queued" and result["processed"] == 0 and result["total"] == 1


def test_application_deep_links_reload_without_swallowing_unknown_api():
    from app.main import app
    app_client = TestClient(app)
    home = app_client.get("/")
    assert home.status_code == 200 and "text/html" in home.headers["content-type"]
    for path in ("/app", "/app/projects/example/requirements", "/app/meetings", "/app/knowledge"):
        response = app_client.get(path)
        assert response.status_code == 200 and response.text == home.text
    for path in ("/api/v1/does-not-exist", "/v1/does-not-exist"):
        response = app_client.get(path)
        assert response.status_code == 404 and response.json() == {"detail": "Not Found"}
    assert app_client.get(PREFIX + "/triage-jobs").status_code == 200


def test_workspace_migration_preserves_backup_and_runs_once(monkeypatch, tmp_path):
    from sqlalchemy import create_engine, inspect
    path = tmp_path / "previous-brain.db"
    target = create_engine("sqlite:///" + path.as_posix())
    BrainProject.__table__.create(target)
    with target.begin() as connection:
        connection.execute(BrainProject.__table__.insert(), {"id": "preserved", "code": "MIGRATION", "name": "Projet existant"})
    monkeypatch.setattr(workspace_jobs, "engine", target)
    workspace_jobs.init_workspace_db()
    workspace_jobs.init_workspace_db()
    backups = list((tmp_path / "backups").glob("brain-workspace-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as db:
        assert db.execute("SELECT id FROM projects").fetchone()[0] == "preserved"
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='mail_triage_jobs'").fetchone()
    assert {"mail_triage_jobs", "assistant_threads"}.issubset(inspect(target).get_table_names())
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM schema_migrations WHERE domain='brain' AND version=6").fetchone()[0] == 1
        assert db.execute("SELECT id FROM projects").fetchone()[0] == "preserved"
    target.dispose()


def test_application_lifespan_connects_workspace_without_real_workers(monkeypatch):
    import app.main as main
    from app.services import auto_scan, meeting_audio
    from backend.app.services import cdc_jobs
    calls = []
    for service, label in ((auto_scan, "auto"), (meeting_audio, "audio"), (cdc_jobs, "cdc"), (workspace_jobs, "mail")):
        start_name = "start_auto_scan" if label == "auto" else "start_worker"
        stop_name = "stop_auto_scan" if label == "auto" else "stop_worker"
        monkeypatch.setattr(service, start_name, lambda name=label: calls.append("start-" + name))
        monkeypatch.setattr(service, stop_name, lambda name=label: calls.append("stop-" + name))
    monkeypatch.setattr(workspace_jobs, "init_workspace_db", lambda: calls.append("workspace-schema"))
    monkeypatch.setattr(main, "init_db", lambda: calls.append("brain-schema"))
    monkeypatch.setattr(main, "mp_init_db", lambda: calls.append("erp-schema"))
    with TestClient(main.app) as app_client:
        assert calls[:3] == ["workspace-schema", "brain-schema", "erp-schema"]
        assert app_client.get(PREFIX + "/assistant-threads").status_code == 200
    assert set(calls[3:]) == {"start-auto", "start-audio", "start-cdc", "start-mail",
                               "stop-auto", "stop-audio", "stop-cdc", "stop-mail"}


def test_testing_mode_never_starts_auto_scan_thread(monkeypatch):
    from app.services import auto_scan
    monkeypatch.setenv("AGENT_TESTING", "1")
    monkeypatch.setattr(auto_scan, "_thread", None)
    monkeypatch.setattr(auto_scan.threading, "Thread", lambda *_args, **_kwargs: pytest.fail(
        "Le mode test ne doit jamais démarrer le scan du dossier réel"))
    auto_scan.start_auto_scan()
    assert auto_scan._thread is None
