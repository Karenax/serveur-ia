import json
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def sage_exports(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENT_OPERATOR_PROJECT_IDS", raising=False)
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "owner")
    client = TestClient(app)

    def create_project(suffix):
        code = f"SAGE-{tmp_path.name}-{suffix}"
        response = client.post("/api/v1/projects", json={"code": code, "title": code})
        assert response.status_code == 201, response.text
        return code, response.json()["id"]

    code, project_id = create_project("principal")
    _, other_id = create_project("autre")
    achats = tmp_path / "Achats"
    pointages = tmp_path / "Pointages"
    achats.mkdir()
    pointages.mkdir()
    old_purchase = achats / "archive.csv"
    old_purchase.write_text(f"Affaire;Fournisseur\n{code};Ancien\n", encoding="utf-8")
    os.utime(old_purchase, (1_600_000_000, 1_600_000_000))
    purchases = achats / "achats.csv"
    purchases.write_text(f"Affaire;Fournisseur;Designation\n{code};Société;Pompe\n", encoding="utf-8-sig")
    times = pointages / "pointages.csv"
    times.write_text(f" affaire ;Nom;Heures\n {code.upper()} ;André;7,25\n", encoding="cp1252")
    response = client.put("/api/v1/sage/config", json={"root_path": str(tmp_path)})
    assert response.status_code == 200, response.text
    return client, code, project_id, other_id, purchases, times


def test_latest_sage_exports_are_available_in_the_correct_project(sage_exports, monkeypatch):
    client, _, project_id, other_id, _, _ = sage_exports
    response = client.post("/api/v1/sage/run")
    assert response.status_code == 200, response.text
    assert response.json()["total_rows"] == 2
    assert [source["file_name"] for source in response.json()["sources"]] == ["achats.csv", "pointages.csv"]

    purchases = client.get(f"/api/v1/projects/{project_id}/purchases").json()
    assert purchases["count"] == 1
    assert purchases["rows"][0]["supplier"] == "Société"
    times = client.get(f"/api/v1/projects/{project_id}/time-tracking").json()
    assert times["total_hours"] == 7.25
    assert times["entries"][0]["person"] == "André"
    assert client.get(f"/api/v1/projects/{other_id}/purchases").json()["rows"] == []
    assert client.get(f"/api/v1/projects/{other_id}/time-tracking").json()["entries"] == []

    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "editor")
    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", json.dumps([project_id]))
    response = client.get(f"/api/v1/projects/{project_id}/purchases")
    assert response.status_code == 200, response.text
    assert client.get(f"/api/v1/projects/{other_id}/purchases").status_code == 404
    assert client.get(f"/api/v1/projects/{other_id}/time-tracking").status_code == 404
    assert client.post("/api/v1/sage/run").status_code == 403


@pytest.mark.parametrize(("invalid_export", "message"), [
    ("Affaire,Nom,Heures\n{code},André,7\n", "ligne 1 : colonne Affaire manquante"),
    ("Affaire;Nom;Nom;Heures\n{code};André;André;7\n", "ligne 1 : noms de colonnes en double"),
    ('Affaire;Nom;Heures\n{code};"André\nTest";7\n{code};"inachevé\n', "ligne 4 : format CSV invalide"),
    ("Affaire;Nom;Heures\n{code};André\n", "ligne 2 : 2 colonnes au lieu de 3"),
])
def test_invalid_sage_export_preserves_the_previous_batch(sage_exports, invalid_export, message):
    client, code, project_id, _, purchases, times = sage_exports
    assert client.post("/api/v1/sage/run").status_code == 200
    purchases.write_text(f"Affaire;Fournisseur\n{code};Nouveau\n", encoding="utf-8")
    times.write_text(invalid_export.format(code=code), encoding="utf-8")

    response = client.post("/api/v1/sage/run")
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail.startswith(f"pointages.csv, {message}")
    batch = client.get("/api/v1/sage/status").json()["batch"]
    assert batch["status"] == "failed"
    assert batch["finished_at"]
    assert batch["error_message"] == detail
    assert client.get(f"/api/v1/projects/{project_id}/purchases").json()["rows"][0]["supplier"] == "Société"
    assert client.get(f"/api/v1/projects/{project_id}/time-tracking").json()["total_hours"] == 7.25
