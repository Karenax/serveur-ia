"""Authoritative source selection gates both ingestion paths without touching mail data."""
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.services.settings_service import save_section

client = TestClient(app)


def test_defaults_and_legacy_folder_choice():
    assert client.get("/v1/settings").json()["mail"]["source"] == "thunderbird"
    response = client.put("/v1/settings/mail", json={"folder": "C:/eml", "auto_scan": False})
    assert response.json()["source"] == "folder"
    assert client.put("/v1/settings/mail", json={"source": "unknown"}).status_code == 422


def test_frontend_mail_settings_roundtrip_and_legacy_compatibility():
    body = {"source": "thunderbird", "folder": "", "auto_scan": False,
            "scan_interval_minutes": 11, "thunderbird_folder_ids": ["a://INBOX", "a://Sent"]}
    result = client.put("/api/v1/brain/mail-settings", json=body)
    assert result.status_code == 200, result.text
    actual = client.get("/api/v1/brain/mail-settings").json()
    assert all(actual[key] == value for key, value in body.items())
    assert client.put("/api/v1/brain/mail-settings", json={"source": "unknown"}).status_code == 422
    result = client.put("/api/v1/brain/mail-settings", json={"folder": "C:/previous-eml"})
    assert result.status_code == 200 and result.json()["source"] == "folder"
    assert result.json()["scan_interval_minutes"] == 11


def test_heartbeat_controls_source_interval_and_selected_folders(monkeypatch):
    monkeypatch.setenv("PB_THUNDERBIRD_TOKEN", "test-source")
    client.put("/v1/settings/mail", json={"source": "folder", "auto_scan": False,
        "thunderbird_folder_ids": ["a://INBOX"], "scan_interval_minutes": 9})
    result = client.post("/v1/thunderbird/bridge/heartbeat", headers={"X-Agent-Thunderbird-Token": "test-source"},
                         json={"version": "0.2.0", "accounts": [], "folders": []}).json()
    assert result["mail_config"] == {"source": "folder", "auto_scan": False,
                                     "folder_ids": ["a://INBOX"], "interval_minutes": 9}
    assert client.post("/v1/thunderbird/sync", json={"folder_ids": ["a://INBOX"]}).status_code == 409
    assert client.post("/v1/thunderbird/bridge/import", headers={"X-Agent-Thunderbird-Token": "test-source"},
                       files={"file": ("mail.eml", b"From: test@example.com\r\n\r\nTest")}).status_code == 409


def test_thunderbird_mode_never_scans_the_eml_folder(monkeypatch):
    from app.services.auto_scan import run_auto_scan_once
    monkeypatch.setattr("app.services.mail_ingest.scan_folder", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("EML scanner active during Thunderbird mode")))
    monkeypatch.setattr("app.services.triage.triage_pending", lambda *a, **k: {"triaged": 0})
    with SessionLocal() as db:
        save_section(db, "mail", {"source": "thunderbird"})
    assert run_auto_scan_once()["scan"]["source"] == "thunderbird"


def test_manual_sync_uses_saved_selection_when_automatic_is_disabled():
    client.put("/v1/settings/mail", json={"source": "thunderbird", "auto_scan": False,
        "thunderbird_folder_ids": ["a://INBOX"]})
    result = client.post("/v1/ingest/scan", json={})
    assert result.status_code == 200, result.text
    assert result.json()["source"] == "thunderbird" and result.json()["job_id"]
    assert client.get("/v1/settings").json()["mail"]["thunderbird_folder_ids"] == ["a://INBOX"]
    from app.models import ThunderbirdJob
    with SessionLocal() as db:
        db.get(ThunderbirdJob, result.json()["job_id"]).status = "done"
        db.commit()
