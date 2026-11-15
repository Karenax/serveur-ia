"""Pont MiniPilot <-> Project Brain : mapping + proxy lecture, sans vraie connexion."""
from fastapi.testclient import TestClient

import backend.app.routers.brain as brain_router
from backend.app.db import Base, engine, init_db
from app.main import app


def setup_function(_):
    Base.metadata.drop_all(bind=engine)
    init_db()


BRAIN_PROJECTS = [
    {"id": "b1", "code": "AIRB23LTH0502-A", "name": "Outillages"},
    {"id": "b2", "code": "P26-0148", "name": "Test"},
]


def _fake_call(method, path, body=None, timeout=20):
    if path == "/health":
        return {"status": "ok", "service": "project-brain"}
    if path == "/v1/projects":
        return BRAIN_PROJECTS
    if path == "/v1/stats":
        return {"pending_count": 0, "proposals_count": 1}
    if path.startswith("/v1/projects/b1/knowledge"):
        return [{"id": "k1", "kind": "milestone", "subject": "FAT", "value": "18/12"}]
    if path == "/v1/projects/b1/open-actions":
        return [{"id": "a1", "subject": "Envoyer PV", "value": "TODO"}]
    if path == "/v1/projects/b1/risks":
        return []
    if path == "/v1/projects/b1/timeline":
        return {"knowledge": [], "sources": []}
    if path == "/v1/projects/b1/memory/status":
        return {"evidence_projections": 3, "truth_projections": 1}
    if path == "/v1/ingest/scan":
        return {"scanned": 5, "imported": 5}
    if path == "/v1/resolution/pending":
        return []
    if path == "/v1/proposals?status=pending":
        return [{"id": "pp1", "kind": "fact", "subject": "S", "value": "V"}]
    if path == "/v1/settings":
        return {"ai": {"provider": "ollama", "model": "llama3.1", "enabled": False},
                "mail": {"folder": "C:/mails", "auto_scan": True}, "memory": {"engine": "fake"}}
    if path == "/v1/settings/ai":
        assert method == "PUT"
        return body
    if path == "/v1/settings/ai/test":
        return {"ok": True, "provider": "ollama"}
    if path == "/v1/ingest/default-folder":
        return {"folder": "C:/mails", "exists": True, "eml_count": 12}
    if path == "/v1/settings/memory/engines":
        return {"configured": {"engine": "fake"},
                "active": {"engine": "FakeMemoryAdapter", "health": {"status": "ok"}}}
    if path in ("/v1/settings/mail", "/v1/settings/memory"):
        assert method == "PUT"
        return body
    if path == "/v1/triage/stats":
        return {"pending_sources": 3, "queued": 2, "divers_project_id": "d1", "divers_count": 1}
    if path == "/v1/triage/queue?offset=0&limit=200":
        return [{"proposal_id": "tp1", "source_id": "s1", "sender": "a@b.c",
                 "subject": "Devis", "received_at": None, "excerpt": "bonjour",
                 "target_project_id": "d1", "target_code": "DIVERS",
                 "target_name": "Divers", "confidence": 0.35, "reason": "triage IA"}]
    if path == "/v1/triage/run?limit=10&offset=0&force=false":
        assert method == "POST"
        return {"scanned": 3, "triaged": 2, "divers": 2, "skipped": 1, "errors": []}
    if path == "/v1/triage/run?limit=10&offset=5&force=true":
        assert method == "POST"
        return {"scanned": 5, "triaged": 5, "divers": 1, "skipped": 0, "errors": [],
                "force": True}
    if path == "/v1/ingest/auto-status":
        return {"enabled": True, "interval_minutes": 5, "last_run_at": "2026-10-01T10:00:00",
                "last_result": {"triage": {"triaged": 2}}, "last_error": None,
                "runs": 3, "folder": "C:/mails"}
    if path == "/v1/triage/tp1/accept":
        assert method == "POST"
        return {"status": "resolved", "validated_to": "DIVERS"}
    if path == "/v1/triage/tp1/assign":
        assert method == "POST"
        assert body["project_id"] == "b1"
        return {"status": "resolved", "validated_to": "AIRB23LTH0502-A"}
    if path == "/v1/projects/chat":
        assert method == "POST"
        assert body["query"] == "date FAT ?"
        assert body["project_id"] is None
        assert body["include_evidence"] is True
        return {"answer": "Au 18/12 [V].", "citations": [], "engine": "FakeMemoryAdapter",
                "projects_queried": ["P1"]}
    raise AssertionError(f"appel Brain inattendu : {method} {path}")


def _client(monkeypatch):
    monkeypatch.setattr(brain_router, "_call", _fake_call)
    return TestClient(app)


def test_brain_status_reachable(monkeypatch):
    c = _client(monkeypatch)
    r = c.get("/api/v1/brain/status").json()
    assert r["reachable"] is True


def test_brain_status_unreachable(monkeypatch):
    def boom(method, path, body=None, timeout=20):
        from fastapi import HTTPException
        raise HTTPException(502, "Project Brain injoignable")
    monkeypatch.setattr(brain_router, "_call", boom)
    c = TestClient(app)
    r = c.get("/api/v1/brain/status").json()
    assert r["reachable"] is False


def test_link_suggest_save_read_unlink(monkeypatch):
    c = _client(monkeypatch)
    p = c.post("/api/v1/projects", json={"code": "AIRB23LTH0502-A", "title": "Outillages"}).json()
    # Non relié : suggestion par code
    link = c.get(f"/api/v1/projects/{p['id']}/brain").json()
    assert link["linked"] is False
    assert link["suggested"]["id"] == "b1"
    # Lecture sans lien -> 409
    assert c.get(f"/api/v1/projects/{p['id']}/brain/knowledge").status_code == 409
    # Mauvais id Brain -> 404
    assert c.put(f"/api/v1/projects/{p['id']}/brain",
                 json={"brain_project_id": "nope"}).status_code == 404
    saved = c.put(f"/api/v1/projects/{p['id']}/brain",
                  json={"brain_project_id": "b1"}).json()
    assert saved == {"linked": True, "brain_project_id": "b1", "brain_code": "AIRB23LTH0502-A"}
    linked = c.get(f"/api/v1/projects/{p['id']}/brain").json()
    assert linked["linked"] is True
    assert linked["memory"]["truth_projections"] == 1
    assert c.get(f"/api/v1/projects/{p['id']}/brain/knowledge").json()[0]["subject"] == "FAT"
    assert c.get(f"/api/v1/projects/{p['id']}/brain/actions").json()[0]["id"] == "a1"
    assert c.get(f"/api/v1/projects/{p['id']}/brain/risks").json() == []
    assert c.post(f"/api/v1/projects/{p['id']}/brain/scan").json()["scanned"] == 5
    assert c.delete(f"/api/v1/projects/{p['id']}/brain").json() == {"linked": False}
    assert c.get("/api/v1/projects/inexistant/brain").status_code == 404


def test_brain_overview_proposals_scan_global(monkeypatch):
    c = _client(monkeypatch)
    ov = c.get("/api/v1/brain/overview").json()
    assert ov["ai"]["provider"] == "ollama"
    assert ov["mail"]["eml_count"] == 12
    assert ov["pending_count"] == 0
    assert ov["proposals_count"] == 1
    assert "api_key" not in ov["ai"]
    assert c.get("/api/v1/brain/proposals").json()[0]["id"] == "pp1"
    assert c.post("/api/v1/brain/scan").json()["imported"] == 5


def test_brain_ai_settings_roundtrip(monkeypatch):
    c = _client(monkeypatch)
    got = c.get("/api/v1/brain/ai-settings").json()
    assert got["provider"] == "ollama"
    assert got["api_key_set"] is False
    assert "api_key" not in got
    bad = c.put("/api/v1/brain/ai-settings",
                json={"provider": "nope", "base_url": "http://x", "model": "m"})
    assert bad.status_code == 400
    saved = c.put("/api/v1/brain/ai-settings",
                  json={"provider": "ollama", "base_url": "http://127.0.0.1:11434",
                        "model": "llama3.1", "enabled": True}).json()
    assert saved["enabled"] is True
    assert c.post("/api/v1/brain/ai-test").json() == {"ok": True, "provider": "ollama"}


def test_brain_mail_and_memory_settings(monkeypatch):
    c = _client(monkeypatch)
    mail = c.get("/api/v1/brain/mail-settings").json()
    assert mail["folder"] == "C:/mails"
    assert mail["eml_count"] == 12
    assert mail["auto_scan"] is True
    saved_mail = c.put("/api/v1/brain/mail-settings",
                       json={"folder": "C:/autre", "auto_scan": False}).json()
    assert saved_mail["folder"] == "C:/autre"
    assert c.put("/api/v1/brain/mail-settings", json={"folder": ""}).status_code == 422
    mem = c.get("/api/v1/brain/memory-settings").json()
    assert mem["active"]["health"]["status"] == "ok"
    assert c.put("/api/v1/brain/memory-settings",
                 json={"engine": "eg2"}).json()["engine"] == "eg2"
    assert c.put("/api/v1/brain/memory-settings",
                 json={"engine": "nope"}).status_code == 400


def test_brain_triage_proxies(monkeypatch):
    c = _client(monkeypatch)
    st = c.get("/api/v1/brain/triage/stats").json()
    assert st == {"pending_sources": 3, "queued": 2, "divers_project_id": "d1",
                  "divers_count": 1}
    q = c.get("/api/v1/brain/triage/queue").json()
    assert len(q) == 1 and q[0]["target_code"] == "DIVERS"
    run = c.post("/api/v1/brain/triage/run?limit=10").json()
    assert run["triaged"] == 2 and run["divers"] == 2
    run_f = c.post("/api/v1/brain/triage/run?limit=10&offset=5&force=true").json()
    assert run_f["triaged"] == 5 and run_f["force"] is True
    au = c.get("/api/v1/brain/ingest/auto-status").json()
    assert au["enabled"] is True and au["interval_minutes"] == 5 and au["runs"] == 3
    acc = c.post("/api/v1/brain/triage/tp1/accept", json={"actor": "test"}).json()
    assert acc["validated_to"] == "DIVERS"
    ass = c.post("/api/v1/brain/triage/tp1/assign",
                 json={"project_id": "b1", "actor": "test"}).json()
    assert ass["validated_to"] == "AIRB23LTH0502-A"


def test_brain_chat_proxy(monkeypatch):
    c = _client(monkeypatch)
    r = c.post("/api/v1/brain/chat", json={"query": "date FAT ?"}).json()
    assert r["answer"] == "Au 18/12 [V]."
    assert r["engine"] == "FakeMemoryAdapter"
