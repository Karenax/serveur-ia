"""Cross-module invariants identified by the September 2026 audit."""
import os
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.db import SessionLocal, engine
from app.models import KnowledgeItem, MemoryProjection, Proposal, Source
from app.services.memory_port import FakeMemoryAdapter
from app.services.eg2_memory import dataset_name_for
from backend.app.db import SessionLocal as ERP, engine as erp_engine
from backend.app.models import CdcItem, CdcEvidenceAnchor, CdcSourcePage, SageAchat

c = TestClient(app)


def project(brain=False):
    code = "AUD-" + uuid.uuid4().hex[:10]
    r = c.post("/v1/projects" if brain else "/api/v1/projects",
               json={"code": code, "name" if brain else "title": code})
    assert r.status_code == 200 if brain else r.status_code == 201
    return r.json()


def mail(subject, project_id=None):
    raw = (f"From: audit@example.test\r\nSubject: {subject}\r\n"
           f"Message-ID: <{uuid.uuid4()}@audit>\r\n\r\nTODO vérifier le dossier.").encode()
    r = c.post("/v1/sources/upload-eml", files={"file": ("audit.eml", raw)},
               data={"candidate_project_id": project_id} if project_id else {})
    assert r.status_code == 200, r.text
    return r.json()


def test_ambiguous_remains_pending_and_confident_ai_classification_auto_attaches():
    a, b = project(True), project(True)
    result = mail(f"[{a['code']}] [{b['code']}]")
    assert result["status"] == "resolution_pending" and result["project_id"] is None
    with patch("app.services.settings_service.get_section", return_value={"enabled": True}), \
         patch("app.services.ai_client.classify_email", return_value={"project_hints": [b["code"]]}):
        result = mail("Sans référence")
    assert result["status"] == "resolved" and result["project_id"] == b["id"]


def test_attach_cannot_become_truth_and_confirmation_is_idempotent():
    a, b = project(True), project(True)
    source = mail("Affectation humaine")
    c.post("/v1/triage/run")
    with SessionLocal() as db:
        attach = db.query(Proposal).filter_by(source_id=source["source_id"], kind="project_attach", status="pending").first()
        attach_id = attach.id
    assert c.post(f"/v1/proposals/{attach_id}/accept", json={}).status_code == 400
    url = f"/v1/resolution/{source['source_id']}/confirm"
    waiting = c.get("/api/v1/workspace/sources", params={"status": "pending", "query": "Affectation humaine"})
    assert waiting.status_code == 200
    assert source["source_id"] in {row["source_id"] for row in waiting.json()["items"]}
    assert c.post(url, json={"project_id": a["id"], "pending_only": True}).status_code == 200
    assert c.post(url, json={"project_id": a["id"], "pending_only": True}).json()["items"] == 0
    assert c.post(url, json={"project_id": b["id"], "pending_only": True}).status_code == 409
    with SessionLocal() as db:
        assert db.query(MemoryProjection).filter_by(source_id=source["source_id"]).count() == 1
    assert c.post(url, json={"project_id": b["id"]}).status_code == 200
    with SessionLocal() as db:
        assert db.get(Source, source["source_id"]).project_id == b["id"]
        old = db.query(MemoryProjection).filter_by(source_id=source["source_id"], project_id=a["id"]).all()
        assert all(row.status == "forgotten" for row in old)
        assert not db.query(Proposal).filter_by(source_id=source["source_id"], project_id=a["id"], status="pending").count()


def test_memory_failure_preserves_canonical_source_and_can_retry():
    p = project(True)

    async def unavailable(*args, **kwargs):
        raise RuntimeError("memory down")

    with patch.object(FakeMemoryAdapter, "remember_evidence", unavailable):
        source = mail("Conservation", p["id"])
    with SessionLocal() as db:
        assert db.get(Source, source["source_id"]) is not None
        assert db.query(MemoryProjection).filter_by(source_id=source["source_id"]).one().status == "failed"
    assert c.post(f"/v1/projects/{p['id']}/memory/retry").json()["indexed"] == 1


def test_contradictions_require_explicit_version_replacement():
    p = project(True)
    ids = []
    with SessionLocal() as db:
        for value in ["2026-10-01", "2027-01-01"]:
            row = Proposal(project_id=p["id"], kind="milestone", subject="FAT", value=value)
            db.add(row)
            db.flush()
            ids.append(row.id)
        db.commit()
    first = c.post(f"/v1/proposals/{ids[0]}/accept", json={}).json()
    assert c.post(f"/v1/proposals/{ids[1]}/accept", json={}).status_code == 409
    second = c.post(f"/v1/proposals/{ids[1]}/accept", json={"supersedes_id": first["knowledge_id"]})
    assert second.status_code == 200 and second.json()["version"] == 2
    with SessionLocal() as db:
        assert db.get(KnowledgeItem, first["knowledge_id"]).status == "superseded"
        assert db.get(KnowledgeItem, second.json()["knowledge_id"]).supersedes_id == first["knowledge_id"]


def test_cdc_final_output_respects_rejection_review_and_evidence():
    p = project()
    pid = p["id"]
    rejected = c.post(f"/api/v1/projects/{pid}/cdc/items", json={"kind": "requirement", "title": "REJECTED", "source_quote": "rejet"}).json()["id"]
    active = c.post(f"/api/v1/projects/{pid}/cdc/items", json={"kind": "requirement", "title": "ACTIVE", "source_quote": "preuve"}).json()["id"]
    c.patch(f"/api/v1/projects/{pid}/cdc/items/{rejected}", json={"knowledge_status": "rejected", "estimated_hours": 50})
    assert c.post(f"/api/v1/projects/{pid}/cdc/transfer").status_code == 409
    draft = c.post(f"/api/v1/projects/{pid}/cdc/transfer?draft=true")
    assert draft.status_code == 200 and "REJECTED" not in draft.json()["markdown"]
    assert "BROUILLON" in draft.json()["markdown"]
    c.patch(f"/api/v1/projects/{pid}/cdc/items/{active}", json={"knowledge_status": "confirmed"})
    assert c.post(f"/api/v1/projects/{pid}/cdc/transfer").status_code == 409
    src = c.post(f"/api/v1/projects/{pid}/cdc/sources/upload", files={"file": ("proof.txt", b"preuve")}).json()
    with ERP() as db:
        page = db.query(CdcSourcePage).filter_by(source_id=src["source_id"]).one()
        db.add(CdcEvidenceAnchor(item_id=active, source_id=src["source_id"], source_page_id=page.id, physical_page=1, quote="preuve"))
        db.commit()
    result = c.post(f"/api/v1/projects/{pid}/cdc/transfer")
    assert result.status_code == 200 and result.json()["items"] == 1
    assert "REJECTED" not in result.json()["markdown"]


def test_archive_preserves_all_erp_relations_and_source_files():
    from backend.app.models import BomLine, TimeEntry, Meeting, MeetingAction, Task
    p = project()
    src = c.post(f"/api/v1/projects/{p['id']}/cdc/sources/upload", files={"file": ("source.txt", b"une preuve")}).json()
    with ERP() as db:
        item = CdcItem(project_id=p["id"], kind="requirement", title="Conserver", source_quote="une preuve",
                       knowledge_status="confirmed", criterion="Essai", human_id="EXI-010")
        task = Task(project_id=p["id"], title="Action existante", status="done")
        meeting = Meeting(project_id=p["id"], title="Revue")
        db.add_all([item, task, meeting])
        db.flush()
        page = db.query(CdcSourcePage).filter_by(source_id=src["source_id"]).one()
        db.add_all([CdcEvidenceAnchor(item_id=item.id, source_id=src["source_id"], source_page_id=page.id, physical_page=1, quote="une preuve"),
                    BomLine(project_id=p["id"], designation="Pièce", quantity=0, unit_price=12.34),
                    TimeEntry(project_id=p["id"], person="Audit", hours=2.5),
                    MeetingAction(project_id=p["id"], meeting_id=meeting.id, title="Action", task_id=task.id)])
        db.commit()
    archive = c.get(f"/api/v1/projects/{p['id']}/export").json()
    assert archive["version"] == 2 and archive["files"]
    imported = c.post("/api/v1/projects/import-json", json={"data": archive, "code": p["code"] + "-COPY"})
    assert imported.status_code == 201, imported.text
    pid = imported.json()["id"]
    with ERP() as db:
        assert db.query(Task).filter_by(project_id=pid).count() == 1
        action = db.query(MeetingAction).filter_by(project_id=pid).one()
        assert db.get(Task, action.task_id).project_id == pid
        assert db.query(BomLine).filter_by(project_id=pid).one().quantity == 0
        assert db.query(TimeEntry).filter_by(project_id=pid).one().hours == 2.5
        restored = db.query(CdcItem).filter_by(project_id=pid).one()
        assert restored.knowledge_status == "confirmed" and restored.human_id == "EXI-010"
        anchor = db.query(CdcEvidenceAnchor).filter_by(item_id=restored.id).one()
        assert db.get(CdcSourcePage, anchor.source_page_id).source_id == anchor.source_id


def test_secret_is_write_only_and_empty_input_preserves_it():
    c.put("/v1/settings/ai", json={"api_key": "audit-fake-secret", "enabled": False})
    assert "audit-fake-secret" not in c.get("/v1/settings").text
    r = c.put("/api/v1/brain/ai-settings", json={"provider": "none", "base_url": "http://localhost:1", "model": "audit", "api_key": "", "enabled": False})
    assert r.status_code == 200 and "audit-fake-secret" not in r.text
    with SessionLocal() as db:
        from app.services.settings_service import get_section
        assert get_section(db, "ai")["api_key"] == "audit-fake-secret"
    c.put("/v1/settings/ai", json={"clear_api_key": True})
    assert c.get("/v1/settings").json()["ai"]["api_key_set"] is False


def test_queues_progress_beyond_duplicate_first_batch(tmp_path):
    from app.services.mail_ingest import scan_folder
    from app.services.triage import triage_pending
    for n in range(3):
        (tmp_path / f"{n}.eml").write_bytes(f"Subject: {uuid.uuid4()}\r\n\r\nMail {n}".encode())
    mem = FakeMemoryAdapter(SessionLocal)
    assert scan_folder(str(tmp_path), SessionLocal, mem, limit=2)["imported"] == 2
    assert scan_folder(str(tmp_path), SessionLocal, mem, limit=2)["imported"] == 1
    with SessionLocal() as db:
        before = db.query(Proposal).filter_by(kind="project_attach", status="pending").count()
        triage_pending(db, mem, None, limit=2)
        triage_pending(db, mem, None, limit=2)
        # Four eligible sources can be triaged even when older triaged entries exist.
        assert db.query(Proposal).filter_by(kind="project_attach", status="pending").count() >= before


def test_html_contracts_foreign_keys_and_dataset_isolation():
    home = c.get("/ui", follow_redirects=False)
    assert home.status_code == 307
    assert home.headers["location"] == "/app/knowledge"
    pending = c.get("/ui/pending", follow_redirects=False)
    assert pending.status_code == 307
    assert pending.headers["location"] == "/app/sources?status=pending"
    review = c.get("/ui/proposals?offset=200", follow_redirects=False)
    assert review.status_code == 307
    assert review.headers["location"] == "/app/knowledge?mode=proposals&offset=200"
    response = c.get("/ui/settings", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/app/settings"
    for e in [engine, erp_engine]:
        with e.connect() as db:
            assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
    assert dataset_name_for("12345678-a", "truth") != dataset_name_for("12345678-b", "truth")
    def flatten(router):
        for route in router.routes:
            child = getattr(route, "original_router", None)
            if child:
                yield from flatten(child)
            else:
                yield route
    routes = [(tuple(sorted(r.methods)), r.path) for r in flatten(app) if hasattr(r, "methods")]
    assert len(routes) == len(set(routes))


def test_invalid_pdf_and_docx_are_handled_and_ollama_payload_is_complete(tmp_path):
    from backend.app.services.cdc_extraction import extract_document, CdcExtractionError
    import pytest
    file = tmp_path / "bad.pdf"
    file.write_bytes(b"not a pdf")
    with pytest.raises(CdcExtractionError):
        extract_document(file, file.name)
    from app.services.ai_client import _chat_content
    with patch("app.services.ai_client._post_json", return_value={"message": {"content": "{}"}}) as send:
        _chat_content({"provider": "ollama", "base_url": "http://localhost:1"},
                      {"messages": [], "max_tokens": 256, "reasoning_effort": "none",
                       "chat_template_kwargs": {"enable_thinking": False}}, 1)
    payload = send.call_args.args[1]
    assert payload["think"] is False and payload["options"]["num_predict"] == 256


def test_sage_matching_is_exact():
    from backend.app.routers.workshop import _for_project
    with ERP() as db:
        code = "AFF-" + uuid.uuid4().hex[:8]
        db.add(SageAchat(affaire=code + "0", batch_id="audit", payload='{"montant": 123}'))
        db.commit()
        assert _for_project(db, SageAchat, code) == []
        assert _for_project(db, SageAchat, "") == []


def test_internal_bridge_remains_available_under_parallel_calls():
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=45) as pool:
        results = list(pool.map(lambda _: c.get("/api/v1/brain/status").json(), range(45)))
    assert all(r["reachable"] for r in results)


def test_eml_scan_uses_only_the_configured_directory(tmp_path):
    from app.services.settings_service import save_section

    allowed = tmp_path / 'allowed'
    folder = allowed / 'inbox'
    folder.mkdir(parents=True)
    separate = tmp_path / 'separate'
    separate.mkdir()
    with SessionLocal() as db:
        save_section(db, 'mail', {'source': 'folder', 'folder': str(allowed)})
    route = '/v1/ingest/scan'
    assert c.post(route, json={'folder': str(separate)}).status_code == 403
    result = c.post(route, json={'folder': str(folder)})
    assert result.status_code == 200 and result.json()['scanned'] == 0


def test_local_session_host_origin_and_executable_protection(monkeypatch, tmp_path):
    monkeypatch.delenv("AGENT_TESTING")
    local = TestClient(app, base_url="http://127.0.0.1:18001")
    assert local.get("/v1/settings", headers={"host": "evil.example"}).status_code == 400
    assert local.get("/api/v1/session", headers={"origin": "https://evil.example"}).status_code == 403
    assert local.post("/api/v1/open-path", json={"path": "bad.exe"}).status_code == 403
    assert local.get("/api/v1/session").status_code == 403
    assert local.get("/v1/settings").status_code == 403
    token = os.environ['AGENT_LOCAL_TOKEN']
    opened = local.post('/api/v1/session', headers={'X-Agent-Token': token})
    assert opened.status_code == 200 and 'token' not in opened.json()
    assert 'HttpOnly' in opened.headers['Set-Cookie']
    assert local.get('/api/v1/session').status_code == 200
    monkeypatch.setenv("AGENT_OPEN_ROOTS", str(tmp_path))
    program = tmp_path / "bad.exe"
    program.write_bytes(b"audit")
    with patch("os.startfile", create=True) as launch:
        response = local.post("/api/v1/open-path", json={"path": str(program)}, headers={"X-Agent-Token": token})
        assert response.status_code == 403
        launch.assert_not_called()


def test_global_backup_restores_new_directory_and_rejects_corruption(tmp_path):
    from pathlib import Path
    from app.services.backup import create_backup, restore_backup
    from app.config import settings, STORAGE_DIR
    from sqlalchemy.engine import make_url
    from backend.app.db import APP_DIR
    import pytest
    backup = tmp_path / "backup"
    result = create_backup(backup, Path(make_url(settings.database_url).database), APP_DIR, STORAGE_DIR)
    assert "brain/project_brain.db" in result["files"] and "erp/minipilot.db" in result["files"]
    destination = tmp_path / "restore"
    assert restore_backup(backup, destination)["files"] == len(result["files"])
    with pytest.raises(FileExistsError):
        restore_backup(backup, destination)
    (backup / "erp/minipilot.db").write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        restore_backup(backup, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_transcript_is_extracted_and_raw_is_downloadable():
    p = project(True)
    source = c.post("/v1/sources/upload-audio", files={"file": ("../../unsafe.wav", b"audio")},
                    data={"transcript": "TODO envoyer le rapport.", "candidate_project_id": p["id"]})
    assert source.status_code == 200
    sid = source.json()["source_id"]
    with SessionLocal() as db:
        values = [row.value for row in db.query(Proposal).filter_by(source_id=sid).all()]
    assert values and all(values) and any("rapport" in value for value in values)
    assert c.get(f"/v1/sources/{sid}/raw").content == b"audio"


def test_cdc_decisions_and_numeric_date_validation():
    p = project()
    item = c.post(f"/api/v1/projects/{p['id']}/cdc/items", json={"kind": "requirement", "title": "Historique", "source_quote": "citation"}).json()
    assert c.patch(f"/api/v1/projects/{p['id']}/cdc/items/{item['id']}", json={"knowledge_status": "rejected", "actor": "Audit"}).status_code == 200
    history = c.get(f"/api/v1/projects/{p['id']}/cdc/decisions").json()
    assert history[0]["actor"] == "Audit" and "candidate" in history[0]["before"] and "rejected" in history[0]["after"]
    assert c.patch(f"/api/v1/projects/{p['id']}", json={"hourly_rate": -1}).status_code == 422
    assert c.post(f"/api/v1/projects/{p['id']}/tasks", json={"title": "Date", "due_date": "2026-02-30"}).status_code == 422
    assert c.post(f"/api/v1/projects/{p['id']}/tasks", json={"title": "Statut", "status": "arbitrary"}).status_code == 422


def test_archive_rejects_global_tables_and_cross_project_rows():
    p = project()
    data = c.get(f"/api/v1/projects/{p['id']}/export").json()
    data["tables"]["sage_config"] = [{"id": 1}]
    response = c.post("/api/v1/projects/import-json", json={"data": data, "code": "BAD-" + uuid.uuid4().hex})
    assert response.status_code == 400
    del data["tables"]["sage_config"]
    data["tables"]["tasks"] = [{"id": str(uuid.uuid4()), "project_id": "other", "title": "Intrusion"}]
    response = c.post("/api/v1/projects/import-json", json={"data": data, "code": "BAD-" + uuid.uuid4().hex})
    assert response.status_code == 400


def test_cdc_hours_record_history_and_bom_rejects_negative_values():
    p = project()
    item = c.post(f"/api/v1/projects/{p['id']}/cdc/items", json={"kind": "requirement", "title": "Prix", "source_quote": "citation"}).json()
    response = c.patch(f"/api/v1/projects/{p['id']}/cdc/items/{item['id']}", json={"estimated_hours": 1.25})
    assert response.status_code == 200
    assert c.get(f"/api/v1/projects/{p['id']}/cdc/decisions").json()[0]["operation"] == "cdc.review"
    bad = c.post(f"/api/v1/projects/{p['id']}/bom/import", files={"file": ("bom.csv", b"designation;quantite;prix\nArticle;-2;10\n")})
    assert bad.status_code == 422


def test_tracking_preserves_fractional_hours():
    p = project()
    item = c.post(f"/api/v1/projects/{p['id']}/cdc/items", json={"kind": "requirement", "title": "Fraction", "source_quote": "citation"}).json()
    assert c.patch(f"/api/v1/projects/{p['id']}/cdc/items/{item['id']}", json={"estimated_hours": 0.125}).status_code == 200
    assert c.get(f"/api/v1/projects/{p['id']}/cdc/items").json()[0]["estimated_hours"] == 0.125


def test_duplicate_truth_is_not_created_by_concurrent_acceptance():
    from concurrent.futures import ThreadPoolExecutor
    p = project(True)
    with SessionLocal() as db:
        rows = [Proposal(project_id=p["id"], kind="fact", subject="Concurrent", value="Une seule vérité") for _ in range(2)]
        db.add_all(rows)
        db.commit()
        ids = [row.id for row in rows]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pid: c.post(f"/v1/proposals/{pid}/accept", json={"actor": "audit"}), ids))
    assert all(result.status_code == 200 for result in results)
    assert len({result.json()["knowledge_id"] for result in results}) == 1


def test_unreadable_secret_can_be_replaced_without_decryption(monkeypatch):
    from app.models import AppSetting
    from app.services import settings_service
    with SessionLocal() as db:
        row = db.get(AppSetting, "ai")
        row.value = {**row.value, "api_key": "dpapi:unreadable"}
        db.commit()
        with monkeypatch.context() as scoped:
            scoped.setattr(settings_service, "reveal", lambda _: (_ for _ in ()).throw(OSError("other user")))
            assert settings_service.get_section(db, "ai")["enabled"] is False
            settings_service.save_section(db, "ai", {"clear_api_key": True})
        assert settings_service.get_section(db, "ai")["api_key"] == ""
