"""Three meanings of dates, evidence, incremental scan and source isolation."""
from datetime import datetime
import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.db import SessionLocal as Brain
from app.models import Project as BrainProject, Source, SourceArtifact
from backend.app.db import SessionLocal as Erp
from backend.app.models import BrainLink, MilestoneCandidate, MilestoneScanJob, NetworkLink
from backend.app.services import milestones, milestone_scan

client = TestClient(app)


@pytest.fixture
def project():
    p = client.post("/api/v1/projects", json={"code": uuid.uuid4().hex, "title": "Jalons fictifs"}).json()
    with Brain() as brain, Erp() as erp:
        bp = BrainProject(code=uuid.uuid4().hex, name="Jalons fictifs")
        brain.add(bp)
        brain.commit()
        erp.add(BrainLink(project_id=p["id"], brain_project_id=bp.id, brain_code=bp.code))
        erp.commit()
        p["brain_id"] = bp.id
    return p


def mail(project, body):
    with Brain() as db:
        source = Source(project_id=project["brain_id"], status="resolved", source_type="email",
                        original_uri="test://mail", sha256=uuid.uuid4().hex * 2,
                        source_metadata={"subject": "Dates du projet"})
        db.add(source)
        db.flush()
        artifact = SourceArtifact(source_id=source.id, kind="body_text", content_text=body)
        db.add(artifact)
        db.commit()
        return source.id, artifact.id


def scan(project, monkeypatch, cfg=None):
    monkeypatch.setattr("backend.app.routers.cdc.brain_ai_settings", lambda: cfg or {"enabled": False})
    with Erp() as db:
        job = milestone_scan.enqueue(db, project["id"])
        row = db.get(MilestoneScanJob, job["id"])
        row.status = "running"
        db.commit()
    milestone_scan.scan(job["id"])
    return client.get(f"/api/v1/projects/{project['id']}/milestones/review").json()


def test_three_dates_and_completed_milestones_not_overdue(project):
    detail = client.get(f"/api/v1/projects/{project['id']}").json()
    assert len(detail["milestones"]) == 8
    fat = next(x for x in detail["milestones"] if x["title"] == "FAT")
    assert not any(fat[field] for field in milestones.DATE_FIELDS)
    url = f"/api/v1/projects/{project['id']}/milestones/{fat['id']}"
    out = client.patch(url, json={"contractual_date": "2026-10-01", "forecast_date": "2026-10-03", "actual_date": "2026-10-04"}).json()
    assert out["due_date"] == "2026-10-03" and out["variance_days"] == 3 and out["state"] == "completed"
    assert out["date_sources"]["actual_date"]["kind"] == "manual"
    history = client.get(url + "/history").json()
    assert len(history) == 3
    planning = client.get(f"/api/v1/projects/{project['id']}/planning").json()
    fat_entry = next(x for x in planning["entries"] if x["id"] == fat["id"])
    assert fat_entry["status"] == "done" and not fat_entry["overdue"]
    assert client.patch(url, json={"contractual_date": "2026-02-30"}).status_code == 422
    assert client.patch(url, json={"title": " "}).status_code == 422
    legacy = client.patch(url, json={"due_date": "2026-10-06"}).json()
    assert legacy["forecast_date"] == "2026-10-06" and legacy["contractual_date"] == "2026-10-01"


def test_extraction_keeps_three_meanings_and_refuses_unsupported_claims(project):
    body = "FAT contractuelle le 01/10/2026.\nFAT prévue le 03/10/2026.\nFAT réalisée le 04/10/2026."
    with Erp() as db:
        evidence = {"kind": "test", "label": "Fictif"}
        n = milestones.store_candidates(db, project["id"], body, milestones.fallback(body), evidence)
        db.commit()
        assert n == 3
        fields = {x.date_type for x in db.query(MilestoneCandidate).filter_by(project_id=project["id"])}
        assert fields == set(milestones.DATE_FIELDS)
        for text_value in ["FAT le 4 octobre 2026", "FAT prévue le 04/10", "FAT n'a pas été réalisée le 04/10/2026",
                           "FAT contractuelle le 01/10/2026 et prévue le 03/10/2026"]:
            assert not milestones.fallback(text_value)
        fake = [{"title": "FAT", "date_type": "actual_date", "date": "2099-10-04", "quote": "FAT réalisée le 04/10/2099"}]
        assert milestones.store_candidates(db, project["id"], fake[0]["quote"], fake, evidence) == 0
        fake[0].update(date="2026-10-04", quote="Texte inventé")
        assert milestones.store_candidates(db, project["id"], body, fake, evidence) == 0
    assert milestones.dates_in("prévue le 4 octobre 2026") == {"2026-10-04"}


def test_assigned_mail_to_proposal_validation_and_history(project, monkeypatch):
    mail(project, "FAT prévue le 03/10/2026.")
    review = scan(project, monkeypatch)
    assert review["job"]["status"] == "completed" and len(review["candidates"]) == 1
    candidate = review["candidates"][0]
    assert candidate["evidence"]["source_id"]
    url = f"/api/v1/projects/{project['id']}/milestones/candidates/{candidate['id']}/decision"
    result = client.post(url, json={"decision": "accept"}).json()
    assert result["forecast_date"] == "2026-10-03" and not result["contractual_date"]
    assert client.post(url, json={"decision": "accept"}).status_code == 409
    mail(project, "FAT reportée au 04/10/2026.")
    review = scan(project, monkeypatch)
    next_candidate = review["candidates"][0]
    assert next_candidate["conflict"] and next_candidate["current_value"] == "2026-10-03"
    url = f"/api/v1/projects/{project['id']}/milestones/candidates/{next_candidate['id']}/decision"
    assert client.post(url, json={"decision": "accept", "expected_value": ""}).status_code == 409
    assert client.post(url, json={"decision": "accept", "expected_value": "2026-10-03"}).status_code == 200
    changes = client.get(f"/api/v1/projects/{project['id']}/milestones/{result['id']}/history").json()
    assert changes[0]["previous"] == "2026-10-03" and changes[0]["evidence"]["quote"]


def test_reclassified_mail_cannot_populate_former_project(project, monkeypatch):
    source_id, _ = mail(project, "Livraison prévue le 2026-10-22.")
    candidate = scan(project, monkeypatch)["candidates"][0]
    with Brain() as db:
        db.get(Source, source_id).status = "resolution_pending"
        db.commit()
    url = f"/api/v1/projects/{project['id']}/milestones/candidates/{candidate['id']}/decision"
    assert client.post(url, json={"decision": "accept"}).status_code == 409
    with Erp() as db:
        assert not milestones.matching(db, project["id"], "Livraison").forecast_date


def test_scan_incremental_and_failed_ai_is_retried(project, monkeypatch):
    _, artifact_id = mail(project, "SAT prévue le 2026-10-23.")
    from unittest.mock import Mock
    inference = Mock(return_value=None)
    monkeypatch.setattr("app.services.ai_client.chat_json", inference)
    cfg = {"enabled": True, "provider": "ollama", "model": "test", "timeout_s": 1}
    result = scan(project, monkeypatch, cfg)
    assert result["job"]["status"] == "failed" and len(result["candidates"]) == 1
    inference.return_value = '{"items": []}'
    scan(project, monkeypatch, cfg)
    assert inference.call_count == 2
    result = scan(project, monkeypatch, cfg)
    assert inference.call_count == 2 and result["job"]["total"] == 0
    with Brain() as db:
        db.get(SourceArtifact, artifact_id).content_text = "SAT prévue le 2026-10-24."
        db.commit()
    scan(project, monkeypatch, cfg)
    assert inference.call_count == 3


def test_periodic_retry_does_not_overtake_a_queued_project(project, monkeypatch):
    other = client.post('/api/v1/projects', json={'code': uuid.uuid4().hex, 'title': 'Projet en attente'}).json()
    with Erp() as db:
        older = MilestoneScanJob(project_id=project['id'], status='completed', total=30,
                                created_at=datetime(2020, 1, 1), updated_at=datetime(2020, 1, 2))
        waiting = MilestoneScanJob(project_id=other['id'], status='queued', total=30,
                                  created_at=datetime(2020, 2, 1), updated_at=datetime(2020, 2, 1))
        db.add_all([older, waiting])
        db.commit()
        waiting_id = waiting.id
        milestone_scan.enqueue(db, project['id'])

    def check_claim(job_id, should_stop):
        assert job_id == waiting_id
        with Erp() as db:
            job = db.get(MilestoneScanJob, job_id)
            assert job.status == 'running' and job.total == 0
            assert job.updated_at > datetime(2020, 2, 1)
            job.status = 'completed'
            db.commit()

    monkeypatch.setattr(milestone_scan, 'scan', check_claim)
    assert milestone_scan.process_next()
    with Erp() as db:
        assert db.get(MilestoneScanJob, waiting_id).status == 'completed'


def test_result_from_source_changed_during_inference_is_ignored(project, monkeypatch):
    source_id, _ = mail(project, "FAT prévue le 2026-10-23.")
    def changing(*args, **kwargs):
        with Brain() as db:
            db.get(Source, source_id).status = "discarded"
            db.commit()
        return '{"items":[{"title":"FAT","date_type":"forecast_date","date":"2026-10-23","quote":"FAT prévue le 2026-10-23.","confidence":0.9}]}'
    monkeypatch.setattr("app.services.ai_client.chat_json", changing)
    result = scan(project, monkeypatch, {"enabled": True, "provider": "ollama"})
    assert not result["candidates"] and result["job"]["status"] == "failed"


def test_network_scan_bound_to_project_and_documents_must_stay_unchanged(project, tmp_path, monkeypatch):
    folder = tmp_path / "project"
    folder.mkdir()
    path = folder / "planning.txt"
    path.write_text("Livraison contractuelle le 30/10/2026.", encoding="utf-8")
    (tmp_path / "other.txt").write_text("SAT prévue le 01/11/2026.", encoding="utf-8")
    (folder / "copie.txt").write_text("AIRB23LTH3146-A\nFAT prévue le 01/11/2026.", encoding="utf-8")
    with Erp() as db:
        db.add(NetworkLink(project_id=project["id"], code="affaire", libelle="Dossier", chemin=str(folder)))
        db.commit()
    result = scan(project, monkeypatch)
    assert len(result["candidates"]) == 1
    assert "autre numéro" in " ".join(result["job"]["warnings"])
    assert result["candidates"][0]["evidence"]["path"] == str(path.resolve())
    path.write_text("Livraison contractuelle le 31/10/2026.", encoding="utf-8")
    candidate = result["candidates"][0]
    url = f"/api/v1/projects/{project['id']}/milestones/candidates/{candidate['id']}/decision"
    assert client.post(url, json={"decision": "accept"}).status_code == 409


def test_readable_attachment_becomes_traced_candidate(project, monkeypatch):
    from email.message import EmailMessage
    from app.config import RAW_DIR
    message = EmailMessage()
    message.set_content("Planning joint")
    message.add_attachment(b"FAT forecast scheduled 2026-10-22.", maintype="text", subtype="plain", filename="planning.txt")
    raw = message.as_bytes()
    path = RAW_DIR / (uuid.uuid4().hex + ".eml")
    path.write_bytes(raw)
    with Brain() as db:
        src = Source(project_id=project["brain_id"], source_type="email", status="resolved", original_uri=str(path),
                     sha256=hashlib.sha256(raw).hexdigest(), source_metadata={"raw_path": str(path), "attachments": [{"filename": "planning.txt"}]})
        db.add(src)
        db.commit()
    result = scan(project, monkeypatch)
    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["evidence"]["kind"] == "attachment"
    assert client.post(f"/api/v1/projects/{project['id']}/milestones/candidates/{candidate['id']}/decision",
                       json={"decision": "accept"}).status_code == 200
    from backend.app.services import cdc_extraction
    extract = cdc_extraction.extract_document
    extracted = []

    def track_extraction(path, filename):
        extracted.append(filename)
        return extract(path, filename)

    monkeypatch.setattr(cdc_extraction, 'extract_document', track_extraction)
    assert scan(project, monkeypatch)['job']['status'] == 'completed'
    assert extracted == []

    message['Subject'] = 'Planning révisé'
    path.write_bytes(message.as_bytes())
    assert scan(project, monkeypatch)['job']['status'] == 'completed'
    assert extracted == ['planning.txt']


def test_non_destructive_migration_of_single_due_date(tmp_path, monkeypatch):
    import backend.app.db as database
    path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE milestones (id VARCHAR(36) PRIMARY KEY, project_id VARCHAR(36), title VARCHAR(255), due_date VARCHAR(32))"))
        conn.execute(text("INSERT INTO milestones VALUES ('old', 'p', 'FAT', '2026-10-22')"))
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "DB_PATH", path)
    monkeypatch.setattr(database, "APP_DIR", tmp_path)
    database.init_db()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT due_date, forecast_date, contractual_date, actual_date FROM milestones WHERE id='old'")).one()
        assert tuple(row) == ("2026-10-22", "2026-10-22", "", "")
    assert list((tmp_path / "backups").glob("*.db"))
    engine.dispose()


def test_meetings_transcripts_cdc_and_current_chat_table(project, monkeypatch):
    from backend.app.models import CdcSource, CdcSourcePage, Meeting
    mail(project, "FAT prévue le 2026-10-20.")
    with Erp() as db:
        db.add(Meeting(project_id=project["id"], title="Revue", decisions="SAT prévue le 2026-11-03."))
        src = CdcSource(project_id=project["id"], filename="Contrat fictif.txt")
        db.add(src)
        db.flush()
        db.add(CdcSourcePage(source_id=src.id, physical_page=1, extracted_text="Livraison contractuelle le 2026-11-01."))
        db.commit()
    result = scan(project, monkeypatch)
    assert {c["evidence"]["kind"] for c in result["candidates"]} == {"brain", "meeting", "cdc"}
    fat = next(c for c in result["candidates"] if c["title"] == "FAT")
    assert client.post(f"/api/v1/projects/{project['id']}/milestones/candidates/{fat['id']}/decision",
                       json={"decision": "accept"}).status_code == 200
    with Brain() as brain:
        hits = milestones.chat_hits([brain.get(BrainProject, project["brain_id"])], "dates FAT")
    hit = next(h for h in hits if h["subject"] == "FAT")
    assert hit["scope"] == "erp_dates" and hit["level"] == "validated"
    assert "prévisionnelle : 2026-10-20" in hit["value"] and "contractuelle : non renseignée" in hit["value"]
    assert any(j["engine"] == "milestones" for j in client.get("/api/v1/workspace/jobs", params={"project_id": project["id"]}).json()["items"])


def test_incremental_batches_do_not_starve_later_inputs(project, monkeypatch):
    for index in range(4):
        mail(project, f"FAT prévue le 2026-10-{20+index}.")
    monkeypatch.setattr(milestone_scan, "MAX_BATCH", 2)
    first = scan(project, monkeypatch)
    assert len(first["candidates"]) == 2 and first["job"]["processed"] == 2
    assert any("prochain passage" in w for w in first["job"]["warnings"])
    second = scan(project, monkeypatch)
    assert len(second["candidates"]) == 4 and second["job"]["processed"] == 2
    last = scan(project, monkeypatch)
    assert last["job"]["total"] == 0
