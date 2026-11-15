"""Liaison authentifiée, doublons/écartés et brouillons sans envoi."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Source, ThunderbirdJob
from app.services.mail_identity import fingerprint
from scripts.install_thunderbird import install_policy, package


def test_presence_tolerates_short_delay_but_expires():
    from app.services.thunderbird import presence_connected
    now = datetime.now(timezone.utc)
    assert presence_connected((now - timedelta(seconds=120)).isoformat())
    assert not presence_connected((now - timedelta(seconds=181)).isoformat())
    assert not presence_connected((now + timedelta(seconds=30)).isoformat())
    assert not presence_connected(None)
    assert not presence_connected('invalid')


@pytest.fixture
def bridge(monkeypatch):
    monkeypatch.setenv("PB_THUNDERBIRD_TOKEN", "test-thunderbird-secret")
    return TestClient(app), {"X-Agent-Thunderbird-Token": "test-thunderbird-secret", "Origin": "moz-extension://test-bridge"}


def mail():
    return (f"From: client@example.com\r\nTo: agent@example.com\r\nSubject: Bonjour {uuid.uuid4()}\r\n"
            f"Message-ID: <{uuid.uuid4()}@example.com>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nEnvoyer le devis.\r\n").encode()


def test_bridge_auth_is_scoped_and_handles_preflight(bridge):
    c, headers = bridge
    assert c.post("/v1/thunderbird/bridge/jobs/claim").status_code == 403
    assert c.post("/v1/thunderbird/bridge/jobs/claim", headers={**headers, "X-Agent-Thunderbird-Token": "wrong"}).status_code == 403
    assert c.post("/v1/thunderbird/bridge/jobs/claim", headers={**headers, "Origin": "https://evil.example"}).status_code == 403
    assert c.post("/v1/projects", json={"code": "NO", "name": "NO"}, headers=headers).status_code == 403
    response = c.options("/v1/thunderbird/bridge/import", headers={"Origin": headers["Origin"]})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == headers["Origin"]


def test_thunderbird_import_deduplicates_and_honors_discard(bridge):
    c, headers = bridge
    raw = mail()
    existing = c.post("/v1/sources/upload-eml", files={"file": ("old.eml", raw)}).json()
    transformed = b"X-Mozilla-Status: 0001\r\nX-Mozilla-Keys: tag1\r\n" + raw
    assert fingerprint(raw) == fingerprint(transformed)
    result = c.post("/v1/thunderbird/bridge/import", headers=headers, files={"file": ("new.eml", transformed)}).json()
    assert result["status"] == "duplicate" and result["source_id"] == existing["source_id"]
    assert c.post(f"/v1/sources/{existing['source_id']}/discard").status_code == 200
    result = c.post("/v1/thunderbird/bridge/import", headers=headers, files={"file": ("new.eml", transformed)}).json()
    assert result["status"] == "duplicate"
    with SessionLocal() as db:
        assert db.get(Source, result["source_id"]).status == "discarded"


def test_thunderbird_import_defers_analysis_and_auto_attachment(bridge, monkeypatch):
    c, headers = bridge
    def unexpected(*args, **kwargs):
        raise AssertionError("L’import ne doit pas appeler le modèle")
    monkeypatch.setattr("app.services.ai_client.classify_email", unexpected)
    monkeypatch.setattr("app.services.mail_ingest.resolve_project", lambda *args: {
        "auto": True, "candidates": [{"project_id": "does-not-exist", "code": "P", "score": 1}]})
    response = c.post("/v1/thunderbird/bridge/import", headers=headers, files={"file": ("new.eml", mail())})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "resolution_pending" and response.json()["project_id"] is None


def test_draft_commands_are_durable_claimed_once_and_clear_content(bridge):
    c, headers = bridge
    response = c.post("/v1/thunderbird/drafts", json={"to": ["client@example.com"], "subject": "Devis",
        "body": "Bonjour", "identity_id": "id1"})
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]
    claimed = c.post("/v1/thunderbird/bridge/jobs/claim", headers=headers).json()["job"]
    assert claimed["id"] == job_id and claimed["kind"] == "draft"
    assert c.post("/v1/thunderbird/bridge/jobs/claim", headers=headers).json()["job"] is None
    assert c.post(f"/v1/thunderbird/bridge/jobs/{job_id}/result", headers=headers,
        json={"status": "done", "result": {"draft_ids": [42]}}).status_code == 200
    with SessionLocal() as db:
        job = db.get(ThunderbirdJob, job_id)
        assert job.status == "done" and job.payload == {}
    assert c.post("/v1/thunderbird/send", json={}).status_code == 404


def test_install_preserves_existing_policies_and_packages_local_config(tmp_path):
    import json
    import zipfile
    from pathlib import Path
    app_dir = tmp_path / "Thunderbird"
    (app_dir / "distribution").mkdir(parents=True)
    policy = app_dir / "distribution" / "policies.json"
    policy.write_text(json.dumps({"policies": {"DisableTelemetry": True,
        "ExtensionSettings": {"other@example.com": {"installation_mode": "allowed"}}}}))
    output = tmp_path / "agent.xpi"
    package(Path("extensions/thunderbird-agent"), output, "local-secret")
    with zipfile.ZipFile(output) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert "messages.send" not in manifest["permissions"] and "compose.send" not in manifest["permissions"]
        assert json.loads(archive.read("pairing.json"))["token"] == "local-secret"
    install_policy(app_dir, output)
    policies = json.loads(policy.read_text())["policies"]
    assert policies["DisableTelemetry"]
    assert "other@example.com" in policies["ExtensionSettings"]
    assert policies["ExtensionSettings"]["agent-bridge@agent.local"]["install_url"].startswith("file:///")
    assert list(policy.parent.glob("policies-before-agent-*.json"))
