"""User-visible correctness: hours, whole-folder mail search, durable jobs and delivery history."""
import hashlib
import io
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import event

from app.main import app
from app.db import SessionLocal as BrainSession
from app.models import Project as BrainProject, Source, SourceArtifact, Proposal
from backend.app.db import SessionLocal as ERP, engine
from backend.app.models import Project, CdcItem, TimeEntry, SagePointage, CdcAnalysisJob, CdcSourcePage, CdcSource

c = TestClient(app)


def project():
    return c.post("/api/v1/projects", json={"code": "IMPROVE-" + uuid.uuid4().hex[:8], "title": "Technique"}).json()["id"]


def test_hours_and_financial_history_preserved():
    pid = project()
    with ERP() as db:
        p = db.get(Project, pid)
        p.hourly_rate, p.margin_pct, p.tdao_prix_vente = 127, 13, 999
        db.add(CdcItem(project_id=pid, kind="function", title="Étude", source_quote="preuve", estimated_hours=10, unit_price=500))
        db.add(TimeEntry(project_id=pid, person="Ingénieur", hours=4))
        db.add(SagePointage(affaire=p.code, batch_id="test", payload=json.dumps({"Heures": "1,5"})))
        db.commit()
    row = next(r for r in c.get("/api/v1/portfolio").json() if r["id"] == pid)
    assert (row["initial_hours"], row["consumed_hours"], row["raf"]) == (10, 5.5, 4.5)
    assert "prix_vente" not in row
    assert c.patch(f"/api/v1/projects/{pid}", json={"remaining_hours": 7.25}).status_code == 200
    row = next(r for r in c.get("/api/v1/portfolio").json() if r["id"] == pid)
    assert row["raf"] == 7.25 and row["remaining_mode"] == "reestimated"
    planning = c.get(f"/api/v1/projects/{pid}/planning").json()
    assert planning["remaining_hours"] == 7.25 and planning["consumed_hours"] == 5.5
    assert c.patch(f"/api/v1/projects/{pid}", json={"remaining_hours": None}).status_code == 200
    archive = c.get(f"/api/v1/projects/{pid}/export").json()
    assert archive["tables"]["projects"][0]["hourly_rate"] == 127
    assert archive["tables"]["cdc_items"][0]["unit_price"] == 500
    assert "hourly_rate" not in c.get(f"/api/v1/projects/{pid}").json()


def test_portfolio_query_count_is_independent_of_project_count():
    statements = []
    def count(*args):
        statements.append(args[2])
    event.listen(engine, "before_cursor_execute", count)
    try:
        c.get("/api/v1/portfolio")
        first = len(statements)
        for _ in range(5):
            project()
        statements.clear()
        c.get("/api/v1/portfolio")
        assert len(statements) == first
    finally:
        event.remove(engine, "before_cursor_execute", count)


def _mail_sources(scope):
    with BrainSession() as db:
        p = BrainProject(code="MAIL-" + uuid.uuid4().hex, name="Dossier test")
        db.add(p)
        db.flush()
        ids = []
        for index in range(3):
            s = Source(source_type="email", status="resolved" if scope == "resolved" else "resolution_pending",
                       project_id=p.id if scope == "resolved" else None, original_uri="test", author="client@test",
                       sha256=uuid.uuid4().hex, received_at=datetime.now(timezone.utc) + timedelta(days=index),
                       source_metadata={"subject": f"Mail {index}"})
            db.add(s)
            db.flush()
            db.add(SourceArtifact(source_id=s.id, kind="body_text", content_text="x" * 800 + " Tolérance vérifiée à 100%"))
            if scope == "pending":
                db.add(Proposal(source_id=s.id, project_id=p.id, kind="project_attach", subject="Classement", value=p.code))
            ids.append(s.id)
        db.commit()
        return p.id, ids


def test_mail_search_full_body_before_paging_and_stable_sort():
    for scope in ("resolved", "pending"):
        pid, ids = _mail_sources(scope)
        args = {"scope": scope, "project_id": pid, "q": "tolerance", "limit": 1, "sort": "oldest"}
        first = c.get("/v1/mail/page", params=args).json()
        assert first["total"] == 3 and first["rows"][0]["source_id"] == ids[0] and first["has_next"]
        second = c.get("/v1/mail/page", params={**args, "offset": 1}).json()
        assert second["rows"][0]["source_id"] == ids[1]
        last = c.get("/v1/mail/page", params={**args, "offset": 2}).json()
        assert not last["has_next"]
        assert c.get("/v1/mail/page", params={**args, "sort": "newest"}).json()["rows"][0]["source_id"] == ids[2]
        assert c.get("/v1/mail/page", params={**args, "q": "100%"}).json()["total"] == 3
        assert c.get("/v1/mail/page", params={**args, "q": "%other"}).json()["total"] == 0
    assert c.get("/v1/mail/page", params={"sort": "invalid"}).status_code == 422


def test_chat_context_balanced_and_relevant():
    from app.services.chat_selection import select_context
    hits = [{"project_code": "A", "id": str(n), "value": "Information générale"} for n in range(12)]
    hits += [{"project_code": "Z", "id": "target", "value": "Échéance FAT client"}]
    selected = select_context(hits, "échéance FAT")
    assert selected[0]["id"] == "target"
    assert {h["project_code"] for h in selected} == {"A", "Z"}


def _job_source(pid):
    with ERP() as db:
        source = CdcSource(project_id=pid, filename="durable.txt", pages=2)
        db.add(source)
        db.flush()
        for page in (1, 2):
            db.add(CdcSourcePage(source_id=source.id, physical_page=page, extracted_text=f"Exigence page {page} vérifiée", extraction_quality=1))
        db.commit()
        return source.id


def _llm_response(payload):
    text = payload["messages"][1]["content"]
    page = int(text.split("[[PAGE ")[1].split("]]")[0])
    source = text.split("[[SOURCE_REVISION ")[1].split("]]")[0]
    return json.dumps({"items": [{"kind": "requirement", "title": f"Exigence {page}", "normalized_wording": f"Page {page}",
        "source_revision_id": source, "physical_page": page, "source_quote": f"Exigence page {page} vérifiée",
        "modality": "mandatory", "priority": "p1", "confidence": 1}]})


def test_job_resume_skips_committed_batches_and_keeps_counters(monkeypatch):
    import backend.app.services.cdc_generation as generation
    from backend.app.services.cdc_jobs import process_next
    pid = project()
    sid = _job_source(pid)
    created = c.post(f"/api/v1/projects/{pid}/cdc/jobs", json={"source_id": sid, "pages_per_batch": 1})
    assert created.status_code == 202
    job_id = created.json()["id"]
    assert created.json()["created_at"].endswith("+00:00")
    assert c.post(f"/api/v1/projects/{pid}/cdc/jobs", json={"source_id": sid}).json()["id"] == job_id
    calls = []
    def interrupted(cfg, payload, **kwargs):
        calls.append(payload)
        if len(calls) == 2:
            raise generation.CdcGenerationError("Interruption simulée")
        return _llm_response(payload)
    monkeypatch.setattr(generation, "chat_json", interrupted)
    assert process_next()
    job = c.get(f"/api/v1/projects/{pid}/cdc/jobs").json()[0]
    assert job["status"] == "failed" and job["completed_batches"] == 1
    assert len(c.get(f"/api/v1/projects/{pid}/cdc/items").json()) == 1
    monkeypatch.setattr(generation, "chat_json", lambda cfg, payload, **kw: (calls.append(payload), _llm_response(payload))[1])
    assert c.post(f"/api/v1/projects/{pid}/cdc/jobs/{job_id}/retry").status_code == 200
    assert process_next()
    job = c.get(f"/api/v1/projects/{pid}/cdc/jobs").json()[0]
    assert job["status"] == "completed" and job["progress"] == 100
    assert job["result"]["created"] == 2 and len(calls) == 3
    assert "[[PAGE 2]]" in calls[-1]["messages"][1]["content"]
    archive = c.get(f"/api/v1/projects/{pid}/export").json()
    restored = c.post("/api/v1/projects/import-json", json={"data": archive, "code": "JOB-" + uuid.uuid4().hex}).json()
    restored_job = c.get(f"/api/v1/projects/{restored['id']}/cdc/jobs").json()[0]
    from backend.app.models import CdcLlmRun
    with ERP() as db:
        copied = db.get(CdcAnalysisJob, restored_job["id"])
        original = db.get(CdcAnalysisJob, job_id)
        assert copied.run_id != original.run_id
        assert db.get(CdcLlmRun, copied.run_id).project_id == restored["id"]
        assert copied.completed_batches == 2


def test_job_cancellation_at_batch_boundary(monkeypatch):
    import backend.app.services.cdc_generation as generation
    from backend.app.services.cdc_jobs import process_next
    pid = project()
    sid = _job_source(pid)
    job = c.post(f"/api/v1/projects/{pid}/cdc/jobs", json={"source_id": sid, "pages_per_batch": 1}).json()
    def cancel_during_request(cfg, payload, **kw):
        assert c.post(f"/api/v1/projects/{pid}/cdc/jobs/{job['id']}/cancel").status_code == 200
        return _llm_response(payload)
    monkeypatch.setattr(generation, "chat_json", cancel_during_request)
    assert process_next()
    state = c.get(f"/api/v1/projects/{pid}/cdc/jobs").json()[0]
    assert state["status"] == "cancelled" and state["completed_batches"] == 1
    assert len(c.get(f"/api/v1/projects/{pid}/cdc/items").json()) == 1


def test_interrupted_job_recovered_without_resetting_checkpoint():
    from backend.app.services.cdc_jobs import recover_interrupted
    pid = project()
    sid = _job_source(pid)
    with ERP() as db:
        job = CdcAnalysisJob(project_id=pid, source_id=sid, status="running", completed_batches=1, total_batches=2)
        db.add(job)
        db.commit()
        recover_interrupted(db)
        db.refresh(job)
        assert job.status == "queued" and job.completed_batches == 1
        # Prevent this synthetic recovery fixture from entering another test's worker.
        job.status = "cancelled"
        db.commit()


def test_deliveries_are_immutable_and_portable():
    pid = project()
    item = c.post(f"/api/v1/projects/{pid}/cdc/items", json={"kind": "function", "title": "Version une", "source_quote": "preuve"}).json()
    first = c.post(f"/api/v1/projects/{pid}/cdc/transfer?draft=true").json()
    original = Path(first["file"]).read_bytes()
    assert c.patch(f"/api/v1/projects/{pid}/cdc/items/{item['id']}", json={"title": "Version deux"}).status_code == 200
    second = c.post(f"/api/v1/projects/{pid}/cdc/transfer?draft=true").json()
    assert second["version"] == first["version"] + 1 and first["file"] != second["file"]
    assert Path(first["file"]).read_bytes() == original
    read = c.get(f"/api/v1/projects/{pid}/cdc/deliveries/{first['version_id']}").json()
    assert read["snapshot"]["items"][0]["title"] == "Version une"
    archive = c.get(f"/api/v1/projects/{pid}/export").json()
    restored = c.post("/api/v1/projects/import-json", json={"data": archive, "code": "REST-" + uuid.uuid4().hex}).json()
    versions = c.get(f"/api/v1/projects/{restored['id']}/cdc/deliveries").json()
    assert len(versions) == 2
    assert versions[0]["created_at"].endswith("+00:00")
    assert c.get(f"/api/v1/projects/{restored['id']}/cdc/deliveries/{versions[0]['id']}").status_code == 200


def test_pdf_cdc_review_exports_the_version_with_traceable_evidence(monkeypatch):
    from reportlab.pdfgen.canvas import Canvas
    from backend.app.services import cdc_generation, cdc_jobs

    pid, other_id = project(), project()
    base = f"/api/v1/projects/{pid}/cdc"
    blob = io.BytesIO()
    pdf = Canvas(blob)
    for page in (1, 2):
        pdf.drawString(50, 730, f"Exigence page {page} vérifiée dans le cahier des charges fictif.")
        pdf.showPage()
    pdf.save()

    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "editor")
    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", json.dumps([pid]))
    uploaded = c.post(f"{base}/sources/upload", files={"file": ("cdc-recette.pdf", blob.getvalue(), "application/pdf")})
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["status"] == "ready"
    source_id = uploaded.json()["source_id"]
    pages = c.get(f"{base}/sources/{source_id}/pages").json()
    assert [page["physical_page"] for page in pages] == [1, 2]
    assert "Exigence page 2 vérifiée" in pages[1]["text"]

    queued = c.post(f"{base}/jobs", json={"source_id": source_id, "pages_per_batch": 1})
    assert queued.status_code == 202, queued.text
    job_id = queued.json()["id"]
    calls = []

    def fake_chat(cfg, payload, **kwargs):
        calls.append(payload["messages"][1]["content"])
        if len(calls) == 2:
            raise cdc_generation.CdcGenerationError("Interruption de recette")
        return _llm_response(payload)

    monkeypatch.setattr(cdc_generation, "chat_json", fake_chat)
    assert cdc_jobs.process_next()
    failed = c.get(f"{base}/jobs").json()[0]
    assert failed["completed_batches"] == 1 and failed["status"] == "failed"
    assert c.post(f"{base}/jobs/{job_id}/retry").status_code == 200
    assert cdc_jobs.process_next()
    assert c.get(f"{base}/jobs").json()[0]["status"] == "completed"
    assert len(calls) == 3 and "[[PAGE 2]]" in calls[-1]

    items = c.get(f"{base}/items").json()
    assert {item["evidence"][0]["page"] for item in items} == {1, 2}
    assert all(item["evidence"][0]["source_id"] == source_id for item in items)
    assert c.post(f"{base}/transfer").status_code == 409
    for item in items:
        reviewed = c.patch(f"{base}/items/{item['id']}", json={"knowledge_status": "confirmed", "actor": "Recette"})
        assert reviewed.status_code == 200, reviewed.text
    assert len(c.get(f"{base}/decisions").json()) == 2

    generated = c.post(f"{base}/transfer")
    assert generated.status_code == 200, generated.text
    result = generated.json()
    url = f"{base}/deliveries/{result['version_id']}"
    detail = c.get(url).json()
    assert detail["snapshot"]["sources"] == [
        {"id": source_id, "filename": "cdc-recette.pdf", "revision": "R1",
         "sha256": hashlib.sha256(blob.getvalue()).hexdigest()}
    ]
    download = c.get(f"{url}/download")
    assert download.status_code == 200, download.text
    assert download.headers["content-disposition"].startswith("attachment")
    assert download.content == detail["markdown"].encode("utf-8") == result["markdown"].encode("utf-8")
    assert hashlib.sha256(download.content).hexdigest() == result["sha256"]
    for page in (1, 2):
        assert f"cdc-recette.pdf, révision R1, page {page} — « Exigence page {page} vérifiée »" in download.text

    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", json.dumps([other_id]))
    assert c.get(f"{url}/download").status_code == 404
    assert c.get(f"/api/v1/projects/{other_id}/cdc/deliveries/{result['version_id']}/download").status_code == 404
    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", json.dumps([pid]))
    Path(result["file"]).write_bytes(b"fichier corrompu de recette")
    assert c.get(f"{url}/download").status_code == 409


def test_dashboard_orders_overdue_and_excludes_rejected():
    pid = project()
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    c.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Relance urgente", "due_date": yesterday})
    item = c.post(f"/api/v1/projects/{pid}/cdc/items", json={"kind": "open_point", "title": "Écart rejeté", "source_quote": "preuve"}).json()
    c.patch(f"/api/v1/projects/{pid}/cdc/items/{item['id']}", json={"knowledge_status": "rejected"})
    result = c.get("/api/v1/actions", params={"project_id": pid}).json()
    assert result["actions"][0]["kind"] == "overdue"
    assert not any(a["kind"] in {"open_point", "cdc_review"} for a in result["actions"])


def test_migrations_do_not_create_backups_at_every_start():
    from backend.app.db import APP_DIR, init_db
    before = set((APP_DIR / "backups").glob("*.db"))
    init_db()
    init_db()
    assert set((APP_DIR / "backups").glob("*.db")) == before


def test_backup_verification_detects_tampering_and_restores_versions(tmp_path):
    import sqlite3
    from sqlalchemy.engine import make_url
    from app.config import settings, STORAGE_DIR
    from backend.app.db import APP_DIR
    from app.services.backup import create_backup, restore_backup
    pid = project()
    sid = _job_source(pid)
    c.post(f"/api/v1/projects/{pid}/cdc/jobs", json={"source_id": sid})
    c.post(f"/api/v1/projects/{pid}/cdc/items", json={"kind": "function", "title": "Étude", "source_quote": "preuve"})
    response = c.post(f"/api/v1/projects/{pid}/cdc/transfer?draft=true")
    assert response.status_code == 200
    version = response.json()
    backup = tmp_path / "backup"
    create_backup(backup, Path(make_url(settings.database_url).database), APP_DIR, STORAGE_DIR)
    assert not (backup / "storage/backup-status.json").exists()
    assert c.post("/api/v1/operations/backup/verify").json()["status"] == "verified"
    restored = tmp_path / "restored"
    restore_backup(backup, restored)
    with sqlite3.connect(restored / "erp/minipilot.db") as db:
        path, = db.execute("SELECT path FROM delivery_versions WHERE id=?", (version["version_id"],)).fetchone()
        assert Path(path).is_relative_to(restored) and Path(path).is_file()
        status, = db.execute("SELECT status FROM cdc_analysis_jobs WHERE project_id=?", (pid,)).fetchone()
        assert status == "interrupted"
    # Clean this queued fixture before another worker test.
    job = c.get(f"/api/v1/projects/{pid}/cdc/jobs").json()[0]
    c.post(f"/api/v1/projects/{pid}/cdc/jobs/{job['id']}/cancel")
    (backup / "brain/project_brain.db").write_bytes(b"corruption")
    assert c.post("/api/v1/operations/backup/verify").status_code == 409
    assert c.get("/api/v1/operations/status").json()["backup"]["status"] == "verification_failed"
