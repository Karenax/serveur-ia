"""Moteur CDC repris de XPilot : extraction, citations obligatoires, contrôles."""
import json
import os
import sys
import tempfile
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MINIPILOT_HOME", tempfile.mkdtemp(prefix="agent-cdc-test-"))

from fastapi.testclient import TestClient  # noqa: E402

import backend.app.services.cdc_generation as cdc_gen  # noqa: E402
from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from backend.app.db import Base, engine, SessionLocal, init_db as init_erp  # noqa: E402

CDC_TEXT = (
    "Le support doit supporter une charge de 250 kg sans deformation.\n"
    "Une tolerance de 0,2 mm est acceptable sur le perçage.\n"
    "La machine doit démarrer automatiquement à 7h.\n"
    "L'interface automate doit exposer un mode maintenance (préférence).\n"
    "Le plan de maintenance est fourni en annexe (information).\n"
)


def _fake_chat_json(cfg, payload, json_schema=None, timeout=None):
    body = payload["messages"][1]["content"]
    page = int(body.split("[[PAGE ")[1].split("]]")[0]) if "[[PAGE " in body else 1
    rev = body.split("[[SOURCE_REVISION ")[1].split("]]")[0]
    return json.dumps({"items": [
        {"kind": "function", "title": "Support structure", "normalized_wording": "supporte 250 kg",
         "source_revision_id": rev, "physical_page": page,
         "source_quote": "doit supporter une charge de 250 kg", "modality": "mandatory",
         "priority": "p1", "confidence": "très haute", "unit": "kg"},
        {"kind": "constraint", "title": "Tolerance perçage",
         "normalized_wording": "tolerance 0,2 mm", "source_revision_id": rev,
         "physical_page": page, "source_quote": "Une tolerance de 0,2 mm",
         "modality": "mandatory", "priority": "p2", "confidence": 0.8},
        {"kind": "requirement", "title": "Demarrage auto", "normalized_wording": "demarrage 7h",
         "source_revision_id": rev, "physical_page": page,
         "source_quote": "La machine doit démarrer", "modality": "mandatory",
         "priority": "p2", "confidence": "90 %"},
        {"kind": "interface", "title": "Mode maintenance", "normalized_wording": "mode maintenance",
         "source_revision_id": rev, "physical_page": page,
         "source_quote": "exposer un mode maintenance", "modality": "preference",
         "priority": "p3", "confidence": 0.4},
        {"kind": "open_point", "title": "Plan maintenance", "normalized_wording": "plan annexe",
         "source_revision_id": rev, "physical_page": page,
         "source_quote": "Le plan de maintenance est fourni", "modality": "information",
         "priority": "unclassified", "confidence": 0.3},
        # citation absente du texte source : doit être rejetée
        {"kind": "requirement", "title": "Invente", "normalized_wording": "resistance 900 MPa",
         "source_revision_id": rev, "physical_page": page,
         "source_quote": "resistance 900 MPa", "modality": "mandatory",
         "priority": "p1", "confidence": 0.9},
    ]})


def setup_function(_):
    Base.metadata.drop_all(bind=engine)
    init_erp()
    init_db()


@pytest.fixture(autouse=True)
def fake_cdc_chat(monkeypatch):
    monkeypatch.setattr(cdc_gen, "chat_json", _fake_chat_json)


def _upload(c, pid, name="cdc.txt", data=None, mime="text/plain"):
    return c.post(f"/api/v1/projects/{pid}/cdc/sources/upload",
                  files={"file": (name, data if data is not None else CDC_TEXT.encode("utf-8"), mime)})


def test_confidence_normalisation():
    base = {"kind": "function", "title": "t", "normalized_wording": "n", "source_revision_id": "r",
            "physical_page": 1, "source_quote": "q", "modality": "information", "priority": "p1"}
    assert cdc_gen.GeneratedCdcItem.model_validate({**base, "confidence": "très haute"}).confidence == 0.98
    assert cdc_gen.GeneratedCdcItem.model_validate({**base, "confidence": "90 %"}).confidence == 0.9
    # kind invalide rejeté par le schéma
    try:
        cdc_gen.GeneratedCdcItem.model_validate({**base, "kind": "nope", "confidence": 0.5})
        assert False, "kind invalide accepté"
    except Exception:
        pass


def test_parse_batch_strips_think_and_fence():
    raw = "<think>réfléchir</think>\n```json\n{\"items\": []}\n```"
    assert cdc_gen.parse_batch(raw).items == []
    try:
        cdc_gen.parse_batch("pas de json")
        assert False, "réponse non JSON acceptée"
    except cdc_gen.CdcGenerationError:
        pass


def test_quote_guard():
    assert cdc_gen.quote_is_present("250 kg", "charge de 250 kg")
    assert not cdc_gen.quote_is_present("900 MPa", "charge de 250 kg")
    assert not cdc_gen.quote_is_present("a", "abc")  # < 4 caractères


def test_upload_analyze_and_checks():
    c = TestClient(app)
    # source héritée d'avant le moteur : ni fichier stocké ni texte
    legacy_src = c.post("/api/v1/projects", json={"code": "CDC-LEGACY",
                                                   "title": "Source legacy"}).json()
    from backend.app.models import CdcSource
    db = SessionLocal()
    try:
        db.add(CdcSource(project_id=legacy_src["id"], filename="ancien.pdf",
                         revision="R1", status="ready", pages=12, size_bytes=999,
                         storage_path=None))
        db.commit()
        legacy_id = db.query(CdcSource).filter_by(project_id=legacy_src["id"]).first().id
    finally:
        db.close()
    r = c.post(f"/api/v1/projects/{legacy_src['id']}/cdc/analyze", json={"source_id": legacy_id})
    assert r.status_code == 400, r.text
    assert "ré-importe" in r.json()["detail"]

    p = c.post("/api/v1/projects", json={"code": "CDC-1", "title": "Projet CDC"}).json()
    up = _upload(c, p["id"])
    assert up.status_code == 200, up.text
    body = up.json()
    assert body["status"] == "ready", body
    src = body["source_id"]

    # idempotence par empreinte
    dup = _upload(c, p["id"]).json()
    assert dup["status"] == "duplicate"

    # pages extraites et consultables
    pages = c.get(f"/api/v1/projects/{p['id']}/cdc/sources/{src}/pages").json()
    assert pages and pages[0]["chars"] > 0
    assert pages[0]["quality"] >= 0.5

    res = c.post(f"/api/v1/projects/{p['id']}/cdc/analyze", json={"source_id": src})
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["returned"] == 6
    assert out["created"] == 5          # la citation absente est rejetée
    assert out["rejected"] == 1

    items = c.get(f"/api/v1/projects/{p['id']}/cdc/items").json()
    kinds = {i["kind"] for i in items}
    assert kinds == {"function", "constraint", "requirement", "interface", "open_point"}
    # identifiants humains + preuve attachée
    assert any(i["human_id"] == "FCT-001" for i in items)
    assert all(i["evidence"] for i in items)
    # confidence normalisée
    assert any(i["confidence"] == 0.98 for i in items)
    assert any(i["confidence"] == 0.9 for i in items)
    # la citation retirée n'est jamais enregistrée
    assert not any("900 MPa" in i["source_quote"] for i in items)

    # A restored database can retain the digest and evidence without the PDF.
    with SessionLocal() as db:
        source = db.get(CdcSource, src)
        original = Path(source.storage_path)
        original.unlink()
        source.storage_path = str(original.parent / 'ancien-poste' / original.name)
        db.commit()
    missing = c.get(f"/api/v1/projects/{p['id']}/cdc/sources").json()[0]
    assert missing['analyzable'] and 'Réimportez' in missing['hint']
    original.write_bytes(b'un autre fichier')
    assert _upload(c, p['id']).status_code == 409
    assert original.read_bytes() == b'un autre fichier'
    original.unlink()
    recovered = _upload(c, p['id'], name='original-retrouve.txt')
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()['status'] == 'restored' and recovered.json()['source_id'] == src
    assert original.read_bytes() == CDC_TEXT.encode('utf-8')
    assert c.get(f"/api/v1/projects/{p['id']}/cdc/sources/{src}/pages").json() == pages
    assert c.get(f"/api/v1/projects/{p['id']}/cdc/items").json() == items
    assert c.get(f"/api/v1/projects/{p['id']}/cdc/sources").json()[0]['hint'] == ''
    assert _upload(c, p['id']).json()['status'] == 'duplicate'

    # contrôles déterministes
    checks = c.get(f"/api/v1/projects/{p['id']}/cdc/checks").json()
    assert all(ch["code"] for ch in checks)
    # trace d'appel IA
    runs = c.get(f"/api/v1/projects/{p['id']}/cdc/runs").json()
    assert runs and runs[0]["status"] == "completed"
    assert runs[0]["accepted"] == 5 and runs[0]["rejected"] == 1

    # transfert BE toujours produit avec la mention NC
    assert c.post(f"/api/v1/projects/{p['id']}/cdc/transfer").status_code == 409
    tr = c.post(f"/api/v1/projects/{p['id']}/cdc/transfer?draft=true")
    assert tr.status_code == 200 and "Réponse technique du BE" in tr.json()["markdown"]


def test_analyze_without_ai_returns_409():
    c = TestClient(app)
    cdc_gen.chat_json = lambda cfg, payload, json_schema=None, timeout=None: None
    p = c.post("/api/v1/projects", json={"code": "CDC-2", "title": "Sans IA"}).json()
    up = _upload(c, p["id"]).json()
    r = c.post(f"/api/v1/projects/{p['id']}/cdc/analyze", json={"source_id": up["source_id"]})
    assert r.status_code == 409
    assert "Réglages" in r.json()["detail"]


def test_upload_rejects_unsupported_format():
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "CDC-3", "title": "Format"}).json()
    r = c.post(f"/api/v1/projects/{p['id']}/cdc/sources/upload",
               files={"file": ("mauvais.zip", b"x", "application/zip")})
    assert r.status_code == 400
    assert "Format CDC" in r.json()["detail"]


def test_review_flow_validates_one_by_one():
    """Revue élément par élément : statuts, retouches, sélection multiple."""
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "CDC-REV", "title": "Revue"}).json()
    up = _upload(c, p["id"]).json()
    c.post(f"/api/v1/projects/{p['id']}/cdc/analyze", json={"source_id": up["source_id"]})
    items = c.get(f"/api/v1/projects/{p['id']}/cdc/items").json()
    assert len(items) == 5
    assert all(i["knowledge_status"] == "candidate" for i in items)

    stats = c.get(f"/api/v1/projects/{p['id']}/cdc/review").json()
    assert stats["total"] == 5 and stats["reviewed"] == 0 and stats["remaining"] == 5
    assert stats["by_status"]["candidate"] == 5

    first, second = items[0], items[1]
    # validation unitaire + retouche des champs de chiffrage
    r = c.patch(f"/api/v1/projects/{p['id']}/cdc/items/{first['id']}", json={
        "knowledge_status": "confirmed", "criterion": "charge admissible",
        "unit": "kg", "estimated_hours": 3.5})
    assert r.status_code == 200, r.text
    assert r.json()["knowledge_status"] == "confirmed"
    updated = [i for i in c.get(f"/api/v1/projects/{p['id']}/cdc/items").json()
               if i["id"] == first["id"]][0]
    assert updated["estimated_hours"] == 3.5 and updated["unit"] == "kg"
    assert updated["criterion"] == "charge admissible"

    # statut invalide refusé
    bad = c.patch(f"/api/v1/projects/{p['id']}/cdc/items/{first['id']}",
                  json={"knowledge_status": "inconnu"})
    assert bad.status_code == 400
    # élément inexistant / autre projet
    assert c.patch(f"/api/v1/projects/{p['id']}/cdc/items/nope",
                   json={"knowledge_status": "confirmed"}).status_code == 404

    # validation en série
    bulk = c.post(f"/api/v1/projects/{p['id']}/cdc/items/bulk-status", json={
        "ids": [second["id"], items[2]["id"]], "knowledge_status": "to_confirm"})
    assert bulk.status_code == 200 and bulk.json()["updated"] == 2
    assert c.post(f"/api/v1/projects/{p['id']}/cdc/items/bulk-status",
                  json={"ids": [second["id"]], "knowledge_status": "nope"}).status_code == 400
    assert c.post(f"/api/v1/projects/{p['id']}/cdc/items/bulk-status",
                  json={"ids": [], "knowledge_status": "confirmed"}).status_code == 400

    stats2 = c.get(f"/api/v1/projects/{p['id']}/cdc/review").json()
    assert stats2["reviewed"] == 3 and stats2["remaining"] == 2
    assert stats2["by_status"]["to_confirm"] == 2

    # rejet : l'élément ne doit plus être compté comme actif dans les contrôles
    c.patch(f"/api/v1/projects/{p['id']}/cdc/items/{items[2]['id']}",
            json={"knowledge_status": "rejected"})
    rejected = [i for i in c.get(f"/api/v1/projects/{p['id']}/cdc/items").json()
                if i["id"] == items[2]["id"]][0]
    assert rejected["knowledge_status"] == "rejected"


def test_unit_missing_check():
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "CDC-4", "title": "Unités"}).json()
    up = _upload(c, p["id"]).json()
    c.post(f"/api/v1/projects/{p['id']}/cdc/analyze", json={"source_id": up["source_id"]})
    from backend.app.models import CdcItem
    db = SessionLocal()
    try:
        item = db.query(CdcItem).filter_by(project_id=p["id"], kind="constraint").first()
        item.unit = None
        db.commit()
        checks = cdc_gen.run_deterministic_checks(db, p["id"])
        assert any(ch["code"] == "UNIT_MISSING" for ch in checks)
    finally:
        db.close()
