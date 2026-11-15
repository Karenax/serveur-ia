"""New ERP projects are usable for classification without deleting any source."""
import json
import uuid
from email.message import EmailMessage

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.services import projections
from app.workspace_models import MailEnrichmentJob

client = TestClient(app)


def _erp(code):
    response = client.post("/api/v1/projects", json={"code": code, "title": "Cible de classement"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_new_project_attachment_is_idempotent_and_preserves_classified_mail():
    code = "NEW-" + uuid.uuid4().hex[:8]
    erp = _erp(code)
    result = client.post(f"/api/v1/projects/{erp}/brain/ensure")
    assert result.status_code == 200, result.text
    target = result.json()["brain_project_id"]
    again = client.post(f"/api/v1/projects/{erp}/brain/ensure")
    assert again.json()["brain_project_id"] == target
    assert len([p for p in client.get("/v1/projects").json() if p["code"] == code]) == 1

    subject = "Classement explicite " + uuid.uuid4().hex
    eml = (f"From: client@example.com\r\nSubject: {subject}\r\nMessage-ID: <{uuid.uuid4()}@test>\r\n"
           "Content-Type: text/plain; charset=utf-8\r\n\r\nTexte conservé.")
    uploaded = client.post("/v1/sources/upload-eml", files={"file": ("test.eml", eml.encode(), "message/rfc822")})
    assert uploaded.status_code == 200, uploaded.text
    source = uploaded.json()["source_id"]
    client.post("/v1/triage/run?limit=1000")
    before = client.get("/v1/mail/page", params={"scope": "pending", "q": subject}).json()
    assert before["total"] == 1
    proposal = before["rows"][0]["proposal_id"]
    assigned = client.post(f"/api/v1/brain/triage/{proposal}/assign", json={"project_id": target})
    assert assigned.status_code == 200, assigned.text
    assert client.get("/v1/mail/page", params={"scope": "pending", "q": subject}).json()["total"] == 0
    after = client.get("/v1/mail/page", params={"scope": "resolved", "project_id": target, "q": subject}).json()
    assert after["total"] == 1
    assert after["rows"][0]["source_id"] == source
    detail = client.get(f"/v1/sources/{source}").json()
    assert any("Texte conservé" in (a.get("text") or "") for a in detail["artifacts"])


def test_attachment_reuses_matching_code_without_merging_unrelated_projects():
    code = "SAME-" + uuid.uuid4().hex[:8]
    existing = client.post("/v1/projects", json={"code": code.lower(), "name": "Existant"}).json()["id"]
    erp = _erp(code)
    result = client.post(f"/api/v1/projects/{erp}/brain/ensure")
    assert result.status_code == 200, result.text
    assert result.json()["brain_project_id"] == existing


def test_attachment_ambiguity_requires_explicit_mapping():
    code = "AMB-" + uuid.uuid4().hex[:8]
    for variant in (code.upper(), code.lower()):
        assert client.post("/v1/projects", json={"code": variant, "name": "Ambigu"}).status_code == 200
    erp = _erp(code)
    assert client.post(f"/api/v1/projects/{erp}/brain/ensure").status_code == 409
    assert not client.get(f"/api/v1/projects/{erp}/brain").json()["linked"]


def test_project_without_code_gets_stable_knowledge_target():
    erp = _erp("")
    result = client.post(f"/api/v1/projects/{erp}/brain/ensure")
    assert result.status_code == 200, result.text
    assert result.json()["brain_code"] == f"ERP-{erp}"
    assert client.post(f"/api/v1/projects/{erp}/brain/ensure").json() == result.json()


def test_project_eml_upload_is_scoped_and_preserves_the_attachment(monkeypatch):
    code = "EML-" + uuid.uuid4().hex[:8]
    project = _erp(code)
    target = client.post(f"/api/v1/projects/{project}/brain/ensure").json()["brain_project_id"]
    other = _erp(code + "-EXT")
    hidden = client.post(f"/api/v1/projects/{other}/brain/ensure").json()["brain_project_id"]

    message = EmailMessage()
    message["From"] = "client@example.test"
    message["To"] = "atelier@example.test"
    message["Subject"] = f"[{code}-EXT] Plan de recette"
    message["Message-ID"] = f"<{uuid.uuid4()}@example.test>"
    message.set_content("Texte du mail de recette.")
    attachment = b"Piece jointe de recette"
    message.add_attachment(attachment, maintype="text", subtype="plain", filename="plan.txt")
    files = {"file": ("courrier.eml", message.as_bytes(), "message/rfc822")}
    url = f"/v1/projects/{target}/import-eml"

    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", json.dumps([project]))
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "reader")
    assert client.post(url, files=files).status_code == 403
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "editor")
    assert client.post(f"/v1/projects/{hidden}/import-eml", files=files).status_code == 404
    bad = client.post(url, files={"file": ("invalide.eml", b"texte sans en-tete", "message/rfc822")})
    assert bad.status_code == 422, bad.text
    async def reject_inline_projection(*args, **kwargs):
        raise AssertionError("L’import doit répondre avant l’indexation EG2")

    monkeypatch.setattr(projections, "process", reject_inline_projection)
    sent = client.post(url, files=files)
    assert sent.status_code == 200, sent.text
    assert sent.json() == {"status": "resolved"}
    assert client.post(url, files=files).json() == {"status": "duplicate"}

    result = client.get("/v1/mail/page", params={"scope": "resolved", "project_id": target, "q": message["Subject"]})
    assert result.status_code == 200, result.text
    page = result.json()
    assert page["total"] == 1
    source_id = page["rows"][0]["source_id"]
    with SessionLocal() as db:
        job = db.query(MailEnrichmentJob).filter_by(source_id=source_id).one()
        assert job.project_id == target
        assert (job.status, job.stage) == ("queued", "memory")
        assert job.projection_ids
    detail = client.get(f"/v1/sources/{source_id}").json()
    assert detail["project_id"] == target
    assert any("Texte du mail de recette." in a["text"] for a in detail["artifacts"])
    downloaded = client.get(f"/v1/sources/{source_id}/attachments/0?download=true")
    assert downloaded.content == attachment
    assert "plan.txt" in downloaded.headers["Content-Disposition"]

    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", json.dumps([other]))
    assert client.get(f"/v1/sources/{source_id}/attachments/0").status_code == 404
    assert client.post(f"/v1/projects/{hidden}/import-eml", files=files).json() == {"status": "duplicate"}
