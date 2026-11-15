"""Tests domaine: idempotence, projet requis, provenance, versionnement."""
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db

init_db()
c = TestClient(app)


def test_project_and_eml_idempotence():
    r = c.post("/v1/projects", json={"code": "P26-0148", "name": "Test"})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    eml = b"From: client@ex.com\r\nTo: moi@boite.fr\r\nSubject: [P26-0148] Report FAT\r\nMessage-ID: <1@x>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nOn valide le report au 18/12. TODO envoyer le PV."
    r1 = c.post("/v1/sources/upload-eml", files={"file": ("mail.eml", eml, "message/rfc822")})
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "resolved"
    c.post(f"/v1/resolution/{r1.json()['source_id']}/confirm", json={"project_id": pid})
    assert c.get(f"/v1/sources/{r1.json()['source_id']}").json()["project_id"] == pid
    r2 = c.post("/v1/sources/upload-eml", files={"file": ("mail.eml", eml, "message/rfc822")})
    assert r2.json()["status"] == "duplicate"
    # Source résolue : informations utilisables sans validation manuelle.
    know = c.get(f"/v1/projects/{pid}/knowledge").json()
    assert len(know) >= 1
    assert any(k["validation_mode"] == "default" for k in know)
    # recall truth
    rec = c.post(f"/v1/projects/{pid}/memory/recall", json={"query": "", "scopes": ["truth"]}).json()
    assert len(rec["results"]) >= 1


def test_pending_when_no_code():
    eml = b"From: inconnu@x.fr\r\nSubject: Bonjour\r\nContent-Type: text/plain\r\n\r\nSimple bonjour sans projet."
    r = c.post("/v1/sources/upload-eml", files={"file": ("x.eml", eml, "message/rfc822")})
    assert r.json()["status"] == "resolution_pending"
    pend = c.get("/v1/resolution/pending").json()
    assert any(x["source_id"] == r.json()["source_id"] for x in pend)
