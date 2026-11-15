import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from backend.app.db import SessionLocal
from backend.app.models import BomLine


@pytest.fixture
def workshop():
    client = TestClient(app)
    prefix = f"/api/v1/projects"
    projects = []
    for _ in range(2):
        created = client.post(prefix, json={"code": f"BOM-{uuid4().hex[:10]}", "title": "Atelier de recette"})
        assert created.status_code == 201, created.text
        projects.append(created.json()["id"])
    return client, projects[0], f"{prefix}/{projects[0]}/bom", f"{prefix}/{projects[1]}/bom"


def upload(client, url, content):
    return client.post(f"{url}/import", files={"file": ("atelier.csv", content, "text/csv")})


def test_import_preserves_french_headers_and_targets_only_the_selected_project(workshop, monkeypatch):
    client, project, url, other = workshop
    initial = client.post(url, json={"reference": "A", "designation": "Ligne existante"})
    assert initial.status_code == 201, initial.text
    csv_content = ('Référence;Désignation;Quantité;Fournisseur\r\n'
                   'B;"Tôle; pliée";2,50;Société\r\nC;Câble;0;Atelier\r\n').encode("cp1252")

    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", json.dumps([project]))
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "reader")
    assert upload(client, url, csv_content).status_code == 403
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "editor")
    assert upload(client, other, csv_content).status_code == 404
    response = upload(client, url, csv_content)
    assert response.status_code == 200, response.text
    assert response.json() == {"created": 2}
    lines = client.get(url).json()["lines"]
    assert [line["reference"] for line in lines] == ["A", "B", "C"]
    assert (lines[1]["designation"], lines[1]["quantity"], lines[1]["supplier"]) == ("Tôle; pliée", 2.5, "Société")
    assert lines[2]["quantity"] == 0

    exported = client.get(url.removesuffix("/bom") + "/export")
    assert exported.status_code == 200, exported.text
    assert {row["reference"]: row["quantity"] for row in exported.json()["tables"]["bom_lines"]} == {
        "A": 1, "B": 2.5, "C": 0
    }
    monkeypatch.delenv("AGENT_OPERATOR_PROJECT_IDS")
    assert client.get(other).json()["count"] == 0


@pytest.mark.parametrize(("content", "message"), [
    ("Référence,Désignation,Quantité\nA,Pièce,3\n", "Colonnes ambiguës à la ligne 1"),
    ("Référence;Total\nA;2\n", "Colonne Désignation manquante à la ligne 1"),
    ("Référence;Désignation;Designation;Quantité\nA;Pièce;Disque;2\n", "Noms de colonnes en double à la ligne 1"),
    ("Référence;Désignation;Quantité\nA;Pièce;2\nB;;1\n", "Désignation manquante à la ligne 3"),
    ('Référence;Désignation;Quantité\nA;"Pièce\nsur deux lignes";2\nB;Disque\n', "2 colonnes à la ligne 4"),
    ('Référence;Désignation;Quantité\nA;Pièce;2\nB;"Disque\n', "Format CSV invalide à la ligne 3"),
])
def test_bad_csv_leaves_existing_bom_intact(workshop, content, message):
    client, _, url, _ = workshop
    assert client.post(url, json={"designation": "Existante"}).status_code == 201
    result = upload(client, url, content.encode("utf-8-sig"))
    assert result.status_code == 422, result.text
    assert message in result.json()["detail"]
    assert [line["designation"] for line in client.get(url).json()["lines"]] == ["Existante"]


def test_two_imports_and_a_manual_line_append_without_position_collisions(workshop):
    client, project, url, _ = workshop
    with SessionLocal() as db:
        db.add(BomLine(project_id=project, reference="OLD", designation="Existante", position=8))
        db.commit()

    start = Barrier(3)

    def submit(prefix):
        start.wait(timeout=5)
        if prefix == "MAN":
            return client.post(url, json={"reference": prefix, "designation": "Saisie"})
        return upload(client, url, f"Ref;Article;Qty\n{prefix}1;Pompe;2\n{prefix}2;Vanne;3\n".encode("ascii"))

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(submit, ("CSV-A", "CSV-B", "MAN")))
    assert [result.status_code for result in results] == [200, 200, 201]
    with SessionLocal() as db:
        lines = db.query(BomLine).filter_by(project_id=project).order_by(BomLine.position).all()
        assert [line.position for line in lines] == list(range(8, 14))
        references = [line.reference for line in lines]
    assert references[0] == "OLD"
    assert set(references[1:]) == {"CSV-A1", "CSV-A2", "CSV-B1", "CSV-B2", "MAN"}
    for prefix in ("CSV-A", "CSV-B"):
        assert references.index(prefix + "2") == references.index(prefix + "1") + 1
