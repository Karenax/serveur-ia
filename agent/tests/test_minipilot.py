import json

from fastapi.testclient import TestClient

from backend.app.db import Base, engine, init_db
from app.main import app


def setup_function(_):
    Base.metadata.drop_all(bind=engine)
    init_db()


def test_health():
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_projects_crud_and_cdc():
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "PRJ-001", "title": "Machine test"}).json()
    assert p["id"]
    t = c.post(f"/api/v1/projects/{p['id']}/tasks", json={"title": "Plans BE"}).json()
    assert t["id"]
    bad = c.post(f"/api/v1/projects/{p['id']}/cdc/items", json={
        "kind": "nope", "title": "x", "source_quote": "y", "physical_page": 1})
    assert bad.status_code == 400
    ok = c.post(f"/api/v1/projects/{p['id']}/cdc/items", json={
        "kind": "function", "title": "Assemblage", "source_quote": "la machine assemble", "physical_page": 2})
    assert ok.status_code == 201


def test_transfer_be():
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "PRJ-TR", "title": "Transfert"}).json()
    empty = c.post(f"/api/v1/projects/{p['id']}/cdc/transfer")
    assert empty.status_code == 400
    c.post(f"/api/v1/projects/{p['id']}/cdc/items", json={
        "kind": "constraint", "title": "Cadence", "source_quote": "cadence 100/h", "physical_page": 1})
    assert c.post(f"/api/v1/projects/{p['id']}/cdc/transfer").status_code == 409
    tr = c.post(f"/api/v1/projects/{p['id']}/cdc/transfer?draft=true").json()
    assert tr["items"] == 1
    assert "Réponse technique du BE" in tr["markdown"]


def test_portfolio_and_sources():
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "PRJ-PF", "title": "Portfolio"}).json()
    pf = c.get("/api/v1/portfolio").json()
    row = [r for r in pf if r["id"] == p["id"]][0]
    assert row["taches"] == "0/0"
    assert row["corrections"] == 0
    assert row["jalon_en_cours"] == "Lancement du projet"
    assert row["jalon_echeance"] == ""
    c.post(f"/api/v1/projects/{p['id']}/milestones",
           json={"title": "J1", "due_date": "2026-10-01"})
    row2 = [r for r in c.get("/api/v1/portfolio").json() if r["id"] == p["id"]][0]
    assert row2["jalon_en_cours"] == "J1"
    assert row2["jalon_echeance"] == "2026-10-01"
    # upload d'un mini PDF -> source enregistrée
    from pypdf import PdfWriter
    import io

    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(200, 200)
    w.write(buf)
    buf.seek(0)
    up = c.post(f"/api/v1/projects/{p['id']}/cdc/sources/upload",
                files={"file": ("cdc.pdf", buf.read(), "application/pdf")}).json()
    assert up["status"] in ("ready", "review_required")
    srcs = c.get(f"/api/v1/projects/{p['id']}/cdc/sources").json()
    assert len(srcs) == 1
    assert srcs[0]["revision"] == "R1"


def test_network_links():
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "PRJ-NET", "title": "Réseau"}).json()
    links = c.get(f"/api/v1/projects/{p['id']}/network-links").json()
    assert [link["code"] for link in links] == ["offre", "dernier_tdao", "dernier_tdsp"]
    assert all(link["required"] for link in links)
    # chemin UNC sur le lien offre
    payload = [{"code": link["code"], "libelle": link["libelle"],
                "chemin": "\\\\srv\\affaires\\PRJ-NET\\offre" if link["code"] == "offre" else link["chemin"]}
               for link in links]
    saved = c.put(f"/api/v1/projects/{p['id']}/network-links", json={"liens": payload}).json()
    assert [link for link in saved if link["code"] == "offre"][0]["chemin"] == "\\\\srv\\affaires\\PRJ-NET\\offre"
    assert {link['code']: link['id'] for link in saved if link['code'] != 'offre'} == {
        link['code']: link['id'] for link in links if link['code'] != 'offre'
    }
    # doublon -> 409
    dup = c.put(f"/api/v1/projects/{p['id']}/network-links",
                json={"liens": payload + [{"code": "offre", "libelle": "bis", "chemin": None}]})
    assert dup.status_code == 409
    # lien obligatoire supprimé -> 400
    missing = c.put(f"/api/v1/projects/{p['id']}/network-links",
                    json={"liens": [link for link in payload if link["code"] != "offre"]})
    assert missing.status_code == 400
    # ouverture : chemin vide -> 422 (validation, aucun appel OS)
    assert c.post("/api/v1/open-path", json={"path": ""}).status_code == 422


def test_project_creation_provisions_its_private_client_directory(tmp_path, monkeypatch):
    root = tmp_path / "clients"
    monkeypatch.setenv("AGENT_DOCUMENT_PROJECT_ROOT", json.dumps(str(root)))
    client = TestClient(app)
    payload = {"code": "PRJ-CLIENT", "title": "Dossier client"}

    assert client.post("/api/v1/projects", json=payload).status_code == 503
    assert not client.get("/api/v1/project-catalogue").json()
    root.mkdir()
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201
    project_id = response.json()["id"]

    folder = root / project_id
    (link,) = [row for row in client.get(f"/api/v1/projects/{project_id}/network-links").json()
               if row["code"] == "dossier_client_kiara"]
    assert folder.is_dir()
    assert link["chemin"] == str(folder)


def test_financial_endpoints_are_removed_but_hours_remain():
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "PRJ-OF", "title": "Technique"}).json()
    item = c.post(f"/api/v1/projects/{p['id']}/cdc/items", json={
        "kind": "function", "title": "Montage", "source_quote": "montage sur site"}).json()
    assert c.patch(f"/api/v1/projects/{p['id']}/cdc/items/{item['id']}", json={"estimated_hours": 10}).status_code == 200
    assert c.post(f"/api/v1/projects/{p['id']}/offer", json={}).status_code == 404
    assert c.patch(f"/api/v1/projects/{p['id']}", json={"hourly_rate": 100}).status_code == 422
    assert c.get(f"/api/v1/projects/{p['id']}/cdc/items").json()[0]["estimated_hours"] == 10


def _make_tdao(path):
    from openpyxl import Workbook

    wb = Workbook()
    accueil = wb.active
    accueil.title = "Accueil"
    accueil["E6"] = "OFF-001"
    accueil["E8"] = "AIRB26LTx0000-A"
    accueil["E10"] = "Machine de test"
    accueil["K6"] = "Airbus"
    heures = wb.create_sheet("Budget")
    heures["J135"] = "TOTAL HEURES PREVUES"
    heures["J138"] = 100
    heures["K138"] = 24
    heures["N123"] = 47772
    wb.save(path)


def test_scan_and_import(tmp_path, monkeypatch):
    root = tmp_path / "clients"
    root.mkdir()
    monkeypatch.setenv("AGENT_DOCUMENT_PROJECT_ROOT", json.dumps(str(root)))
    c = TestClient(app)
    folder = tmp_path / "00 - AIRB26LTx0000-A - Machine de test"
    folder.mkdir()
    _make_tdao(str(folder / "AIRB26LTx0000-A-TDAO-001-A.xlsm"))
    preview = c.post("/api/v1/projects/scan", json={"folder": str(folder)}).json()
    assert preview["code"] == "AIRB26LTx0000-A"
    assert preview["client_name"] == "Airbus"
    assert preview["budget_h"] == 124
    assert "prix_vente" not in preview
    assert preview["tdao_file"] is not None
    created = c.post("/api/v1/projects/import", json={"folder": str(folder)}).json()
    assert created["code"] == "AIRB26LTx0000-A"
    links = c.get(f"/api/v1/projects/{created['id']}/network-links").json()
    codes = [link["code"] for link in links]
    assert "affaire" in codes and "dernier_tdao" in codes
    (client_link,) = [link for link in links if link["code"] == "dossier_client_kiara"]
    assert client_link["chemin"] == str(root / created["id"])
    assert (root / created["id"]).is_dir()
    # doublon -> 409
    dup = c.post("/api/v1/projects/import", json={"folder": str(folder)})
    assert dup.status_code == 409
    # dossier inexistant -> 400
    bad = c.post("/api/v1/projects/scan", json={"folder": str(tmp_path / "nope")})
    assert bad.status_code == 400
    # lignes budgétaires créées à l'import (J138=100, K138=24)
    items = c.get(f"/api/v1/projects/{created['id']}/cdc/items").json()
    by_title = {item["title"]: item for item in items}
    assert by_title["Budget TDAO – Chiffrage BE"]["estimated_hours"] == 100
    # idempotent : second appel -> 400 (déjà chargées)
    again = c.post(f"/api/v1/projects/{created['id']}/budgets-from-tdao")
    assert again.status_code == 400


def test_scan_ignores_placeholders(tmp_path):
    from openpyxl import Workbook

    from backend.app.routers.scan import _clean_identity, parse_folder_name

    assert _clean_identity({"project_code": "-", "client_name": "Airbus"}) == {"client_name": "Airbus"}
    assert _clean_identity({"project_code": "A remplir obligatoirement"}) == {}
    assert parse_folder_name("00 - AIRB26LTx0000-A - Machine de test") == ("AIRB26LTx0000-A", "Machine de test")
    # TDAO vierge : le code du dossier prime
    c = TestClient(app)
    folder = tmp_path / "00 - AIRB26LTx0000-A - Vierge"
    folder.mkdir()
    wb = Workbook()
    accueil = wb.active
    accueil.title = "Accueil"
    accueil["E8"] = "A remplir obligatoirement"
    wb.save(str(folder / "x-TDAO-y.xlsm"))
    preview = c.post("/api/v1/projects/scan", json={"folder": str(folder)}).json()
    assert preview["code"] == "AIRB26LTx0000-A"


def test_scan_folder_identity_wins_over_old_tdao_and_tdsp(tmp_path):
    from openpyxl import Workbook
    folder = tmp_path / "AIRB26LTH0205-A - LED 2026"
    folder.mkdir()
    for kind, cell in (("TDAO", "E8"), ("TDSP", "E6")):
        wb = Workbook()
        ws = wb.active
        ws.title = "Accueil" if kind == "TDAO" else "Page d'Accueil"
        ws[cell] = "AIRB23LTH3146-A"
        ws["E10" if kind == "TDAO" else "E8"] = "Catalogue éclairage"
        ws["K6"] = "Ancien client"
        hours = wb.create_sheet("Budget")
        hours["J135"] = "TOTAL HEURES PREVUES"
        hours["J138"] = 100
        wb.save(folder / f"ancien-{kind}.xlsx")
        wb.close()
    c = TestClient(app)
    preview = c.post("/api/v1/projects/scan", json={"folder": str(folder)}).json()
    assert (preview["code"], preview["title"]) == ("AIRB26LTH0205-A", "LED 2026")
    assert len(preview["warnings"]) == 2
    assert preview["budget_h"] == 0 and not preview["client_name"]
    created = c.post("/api/v1/projects/import", json={"folder": str(folder)})
    assert created.status_code == 201, created.text
    result = created.json()
    assert result["code"] == "AIRB26LTH0205-A" and result["title"] == "LED 2026"
    assert result["budget_lines"] == 0
    assert c.get(f"/api/v1/projects/{result['id']}/cdc/items").json() == []


def test_scan_uses_document_identity_when_folder_has_no_project_code(tmp_path):
    folder = tmp_path / "Sans référence"
    folder.mkdir()
    _make_tdao(str(folder / "document-TDAO.xlsm"))
    preview = TestClient(app).post("/api/v1/projects/scan", json={"folder": str(folder)}).json()
    assert preview["code"] == "AIRB26LTx0000-A"
    assert preview["title"] == "Machine de test"
    assert preview["warnings"] == [] and preview["budget_h"] == 124


def test_meetings():
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "PRJ-CR", "title": "Réunions"}).json()
    m = c.post(f"/api/v1/projects/{p['id']}/meetings", json={
        "date": "2026-09-16", "title": "Point hebdo", "participants": "FLF, BE",
        "decisions": "On valide le plan"}).json()
    a = c.post(f"/api/v1/projects/{p['id']}/meetings/{m['id']}/actions", json={
        "title": "Mettre à jour le plan", "owner": "BE", "due_date": "2026-09-23"}).json()
    t = c.post(f"/api/v1/projects/{p['id']}/meetings/{m['id']}/actions/{a['id']}/to-task").json()
    assert t["title"] == "Mettre à jour le plan (BE)"
    # doublon -> 409
    dup = c.post(f"/api/v1/projects/{p['id']}/meetings/{m['id']}/actions/{a['id']}/to-task")
    assert dup.status_code == 409
    tasks = c.get(f"/api/v1/projects/{p['id']}").json()["tasks"]
    assert any(task["id"] == t["id"] for task in tasks)
    export = c.get(f"/api/v1/projects/{p['id']}/meetings/{m['id']}/export").json()
    assert "On valide le plan" in export["markdown"]
    assert "transférée en tâche" in export["markdown"]


def test_planning_search_export_import(tmp_path, monkeypatch):
    root = tmp_path / "clients"
    root.mkdir()
    monkeypatch.setenv("AGENT_DOCUMENT_PROJECT_ROOT", json.dumps(str(root)))
    c = TestClient(app)
    p = c.post("/api/v1/projects", json={"code": "PRJ-PLAN", "title": "Planning Airbus"}).json()
    t = c.post(f"/api/v1/projects/{p['id']}/tasks",
               json={"title": "Vieille tâche", "due_date": "2020-01-01"}).json()
    c.patch(f"/api/v1/projects/{p['id']}/tasks/{t['id']}", json={"status": "done"})
    got = c.get(f"/api/v1/projects/{p['id']}").json()
    assert [x for x in got["tasks"] if x["id"] == t["id"]][0]["status"] == "done"
    planning = c.get(f"/api/v1/projects/{p['id']}/planning").json()
    assert planning["overdue_count"] == 0  # tâche clôturée
    # recherche globale
    found = c.get("/api/v1/search", params={"q": "airbus"}).json()
    assert any(r["project_id"] == p["id"] for r in found)
    short = c.get("/api/v1/search", params={"q": "x"})
    assert short.status_code == 400
    # recherche restreinte au projet : pas de résultat "project", que les tâches/CDC/CR du projet
    scoped = c.get("/api/v1/search", params={"q": "Vieille", "project_id": p["id"]}).json()
    assert all(r["project_id"] == p["id"] for r in scoped)
    assert all(r["type"] != "project" for r in scoped)
    unknown = c.get("/api/v1/search", params={"q": "Vieille", "project_id": "00000000-0000-0000-0000-000000000000"})
    assert unknown.status_code == 404
    # export puis réimport sous un autre code
    dump = c.get(f"/api/v1/projects/{p['id']}/export").json()
    assert dump["format"] == "agent-project-archive"
    again = c.post("/api/v1/projects/import-json",
                   json={"data": dump, "code": "PRJ-PLAN2"})
    assert again.status_code == 201
    assert again.json()["code"] == "PRJ-PLAN2"
    imported_id = again.json()["id"]
    (link,) = [row for row in c.get(f"/api/v1/projects/{imported_id}/network-links").json()
               if row["code"] == "dossier_client_kiara"]
    assert link["chemin"] == str(root / imported_id)
    assert (root / imported_id).is_dir()
    assert (root / p["id"]).is_dir()
    with monkeypatch.context() as unavailable:
        unavailable.setenv("AGENT_DOCUMENT_PROJECT_ROOT", json.dumps(str(tmp_path / "missing")))
        failed = c.post("/api/v1/projects/import-json", json={"data": dump, "code": "PRJ-PLAN3"})
    assert failed.status_code == 503
    assert {row["code"] for row in c.get("/api/v1/project-catalogue").json()} == {"PRJ-PLAN", "PRJ-PLAN2"}
    dup = c.post("/api/v1/projects/import-json", json={"data": dump})
    assert dup.status_code == 409
    bad = c.post("/api/v1/projects/import-json", json={"data": {"format": "nope"}})
    assert bad.status_code == 400


def test_ai_status_and_unreachable():
    c = TestClient(app)
    status = c.get("/api/v1/ai/status").json()
    assert status["model"] == "llama3.1"
    assert status["reachable"] is False  # aucun serveur LLM sur ce poste
    p = c.post("/api/v1/projects", json={"code": "PRJ-AI", "title": "IA"}).json()
    failed = c.post(f"/api/v1/projects/{p['id']}/cdc/ai-generate",
                    json={"text": "x" * 100, "physical_page": 1})
    assert failed.status_code == 409
    assert "injoignable" in failed.json()["detail"]


def _sage_root(tmp_path):
    root = tmp_path / "sage"
    (root / "Achats").mkdir(parents=True)
    (root / "Pointages").mkdir()
    (root / "Achats" / "achats.csv").write_text(
        "Affaire;Fournisseur;Désignation;Montant;Statut\n"
        "PRJ-SAGE;Fourni SA;Tôles;1250,50;Commandé\n", encoding="utf-8")
    (root / "Pointages" / "pointages.csv").write_text(
        "Affaire;Nom;Date;Heures;Lot\n"
        "PRJ-SAGE;Dupont;2026-09-01;7,5;Montage\n", encoding="utf-8")
    return root


def test_sage_purchases_tracking_bom(tmp_path):
    c = TestClient(app)
    root = _sage_root(tmp_path)
    assert c.put("/api/v1/sage/config", json={"root_path": str(root)}).json()["root_path"]
    run = c.post("/api/v1/sage/run").json()
    assert run["status"] == "success"
    assert run["total_rows"] == 2
    status = c.get("/api/v1/sage/status").json()
    assert status["batch"]["status"] == "success"
    p = c.post("/api/v1/projects", json={"code": "PRJ-SAGE", "title": "Sage"}).json()
    purchases = c.get(f"/api/v1/projects/{p['id']}/purchases").json()
    assert purchases["count"] == 1
    assert "total_amount" not in purchases
    assert all("Montant" not in row["payload"] for row in purchases["rows"])
    tracking = c.get(f"/api/v1/projects/{p['id']}/time-tracking").json()
    assert tracking["total_hours"] == 7.5
    assert tracking["by_person"][0]["person"] == "Dupont"
    # saisie manuelle + BOM
    c.post(f"/api/v1/projects/{p['id']}/time-entries",
           json={"person": "FLF", "date": "2026-09-16", "hours": 2, "label": "Plans"})
    tracking = c.get(f"/api/v1/projects/{p['id']}/time-tracking").json()
    assert tracking["total_hours"] == 9.5
    line = c.post(f"/api/v1/projects/{p['id']}/bom", json={
        "reference": "T-001", "designation": "Tôle", "quantity": 4,
        "supplier": "Fourni SA"}).json()
    bom = c.get(f"/api/v1/projects/{p['id']}/bom").json()
    assert "total" not in bom and bom["lines"][0]["quantity"] == 4
    c.patch(f"/api/v1/projects/{p['id']}/bom/{line['id']}", json={"quantity": 5})
    assert c.get(f"/api/v1/projects/{p['id']}/bom").json()["lines"][0]["quantity"] == 5
