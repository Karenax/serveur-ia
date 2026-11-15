"""L1 service/HTTP rules and additive startup, isolated from production data."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import sqlite3
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from backend.app.db import Base, get_db
from backend.app.models import BrainLink, Project
from backend.app.project_identity_models import (
    IDENTITY_TABLES, ProjectIdentityChange, ProjectPerson, ProjectProfile,
)
from backend.app.project_identity_schemas import (
    IdentityPatch, MemberCreate, MemberPatch, PersonCreate, PersonPatch, ReferenceCreate, ReferencePatch, RevisionCommand,
)
from backend.app.routers.project_identity import router
from backend.app.services import project_identity as identity
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from backend.app.services.project_identity_migration import install_identity_schema
from backend.app.services.project_operator import Operator, configured_operator, current_operator, operator_context


@pytest.fixture
def store(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'identity.db'}", connect_args={"check_same_thread": False})
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[Project.__table__, BrainLink.__table__, *IDENTITY_TABLES])
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as db:
        projects = [Project(code=f"AIRB26LTH020{i}-A", title=f"Projet {i}", client_name="Client hérité",
                            hourly_rate=91.5, margin_pct=12.75) for i in (5, 6)]
        db.add_all(projects)
        db.flush()
        db.add(BrainLink(project_id=projects[0].id, brain_project_id=str(uuid.uuid4()), brain_code=projects[0].code))
        db.commit()
        ids = [row.id for row in projects]
    yield factory, ids
    engine.dispose()


@contextmanager
def transaction(factory):
    with factory() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def reference(factory, kind, code="TEST", label="Référence"):
    with transaction(factory) as db:
        return identity.create_reference(db, ReferenceCreate(kind=kind, code=code, label=label))


def person(factory, first_name="Élodie", last_name="Durand", **values):
    with transaction(factory) as db:
        return identity.create_person(db, PersonCreate(first_name=first_name, last_name=last_name, **values))


def patch(factory, project_id, **values):
    with transaction(factory) as db:
        return identity.patch_identity(db, project_id, IdentityPatch(**values))


def test_legacy_identity_read_is_neutral_and_never_writes(store):
    factory, ids = store
    with factory() as db:
        row = identity.read_identity(db, ids[0])
        assert row["revision"] == 0 and row["members"] == []
        assert row["client_id"] is None and row["legacy_client_name"] == "Client hérité"
        assert row["actual_closure_date"] == "" and row["standby"] is False
        assert db.query(ProjectProfile).count() == 0
        assert set(identity.ROLE_LABELS) == {x["code"] for x in row["roles"]}
        assert "hourly_rate" not in row and "margin_pct" not in row


def test_complete_identity_and_responsible_preserve_existing_project_and_link(store):
    factory, ids = store
    references = {kind: reference(factory, kind) for kind in identity.REFERENCE_FIELDS.values()}
    lead = person(factory, agency_id=references["agency"]["id"])
    values = {field: references[kind]["id"] for field, kind in identity.REFERENCE_FIELDS.items()}
    out = patch(factory, ids[0], expected_revision=0, **values, responsible_id=lead["id"],
                description="Outillage LED", equipment_number="LED-26", client_reference="Commande 123",
                client_site="Nantes", client_contact="Contact client", quantity=2,
                start_date="2026-10-05", planned_end_date="2027-01-15", standby=True)
    assert out["revision"] == 1 and out["responsible"]["id"] == lead["id"]
    assert len(out["references"]) == 5 and out["quantity"] == 2
    assert out["members"][0]["role"] == "responsable_projet"
    with factory() as db:
        project = db.get(Project, ids[0])
        assert project.code == "AIRB26LTH0205-A" and project.client_name == "Client hérité"
        assert project.hourly_rate == 91.5 and project.margin_pct == 12.75
        assert db.query(BrainLink).filter_by(project_id=ids[0]).one().brain_code == project.code
        assert db.query(ProjectIdentityChange).filter_by(project_id=ids[0]).count() == 2


def test_invalid_merged_dates_and_reference_kind_roll_back_everything(store):
    factory, ids = store
    patch(factory, ids[0], expected_revision=0, planned_end_date="2026-10-06")
    with pytest.raises(HTTPException) as error:
        patch(factory, ids[0], expected_revision=1, start_date="2026-10-07")
    assert error.value.status_code == 422
    wrong = reference(factory, "agency")
    with pytest.raises(HTTPException):
        patch(factory, ids[0], expected_revision=1, client_id=wrong["id"])
    with factory() as db:
        out = identity.read_identity(db, ids[0])
        assert out["revision"] == 1 and out["start_date"] == ""
        assert db.query(ProjectIdentityChange).count() == 1


def test_responsible_replacement_archives_assignment_and_keeps_both_people(store):
    factory, ids = store
    first, second = person(factory), person(factory, first_name="Marc")
    out = patch(factory, ids[0], expected_revision=0, responsible_id=first["id"])
    original_id = out["members"][0]["id"]
    out = patch(factory, ids[0], expected_revision=1, responsible_id=second["id"])
    assert len(out["members"]) == 2
    old = next(member for member in out["members"] if member["id"] == original_id)
    assert old["active"] is False and old["archived_at"]
    assert out["responsible_id"] == second["id"]
    out = patch(factory, ids[0], expected_revision=2, responsible_id=None)
    assert out["responsible_id"] is None and all(not member["active"] for member in out["members"])
    with factory() as db:
        assert db.query(ProjectPerson).count() == 2
        events = identity.identity_history(db, ids[0])
        assert any(event["action"] == "member_archived" for event in events["items"])


def test_member_lifecycle_scope_and_responsible_synchronization(store):
    factory, ids = store
    lead = person(factory)
    with transaction(factory) as db:
        out = identity.add_member(db, ids[0], MemberCreate(expected_revision=0, person_id=lead["id"],
                                                        role="responsable_projet", start_date="2026-10-05"))
    member_id = out["members"][0]["id"]
    assert out["responsible_id"] == lead["id"]
    with pytest.raises(HTTPException) as error, transaction(factory) as db:
        identity.patch_member(db, ids[1], member_id, MemberPatch(expected_revision=0, role="calcul"))
    assert error.value.status_code == 404
    with transaction(factory) as db:
        out = identity.patch_member(db, ids[0], member_id, MemberPatch(expected_revision=1, role="calcul"))
        assert out["responsible_id"] is None
    with pytest.raises(HTTPException) as error, transaction(factory) as db:
        identity.add_member(db, ids[0], MemberCreate(expected_revision=2, person_id=lead["id"], role="calcul"))
    assert error.value.status_code == 409
    with transaction(factory) as db:
        out = identity.archive_member(db, ids[0], member_id, RevisionCommand(expected_revision=2))
        assert out["members"][0]["active"] is False
    with transaction(factory) as db:
        out = identity.add_member(db, ids[0], MemberCreate(expected_revision=3, person_id=lead["id"], role="calcul"))
        assert len(out["members"]) == 2 and out["revision"] == 4
    with factory() as db:
        assert db.get(ProjectProfile, ids[1]) is None


def test_reader_scope_applies_to_services_and_business_role_cannot_grant_access(store):
    factory, ids = store
    allowed = person(factory)
    person(factory, first_name="Autre", email="autre@example.test")
    with transaction(factory) as db:
        identity.add_member(db, ids[0], MemberCreate(expected_revision=0, person_id=allowed["id"], role="lecteur_projet"))
    with operator_context(Operator("reader-test", "reader", frozenset([ids[0]]))), factory() as db:
        assert identity.read_identity(db, ids[0])["can_edit"] is False
        assert [row["id"] for row in identity.list_people(db)["items"]] == [allowed["id"]]
        with pytest.raises(HTTPException) as error:
            identity.read_identity(db, ids[1])
        assert error.value.status_code == 404
        with pytest.raises(HTTPException) as error:
            identity.patch_identity(db, ids[0], IdentityPatch(expected_revision=1, description="Interdit"))
        assert error.value.status_code == 403
        with pytest.raises(HTTPException):
            identity.create_person(db, PersonCreate(first_name="Interdit", last_name="Test"))
    assert current_operator().role == "owner"
    # Business membership alone does not downgrade or elevate the trusted operator.
    patch(factory, ids[0], expected_revision=1, description="Opérateur propriétaire autorisé")


def test_reference_search_archive_duplicates_and_optimistic_updates(store):
    factory, ids = store
    ref = reference(factory, "client", "AIRBUS", "Aéronautique")
    with factory() as db:
        assert identity.list_references(db, search="aeronautique")["total"] == 1
        assert identity.list_references(db, search="%")["total"] == 0
        assert identity.list_references(db, limit=1)["items"][0]["id"] == ref["id"]
    patch(factory, ids[0], expected_revision=0, client_id=ref["id"])
    with transaction(factory) as db:
        row = identity.patch_reference(db, ref["id"], ReferencePatch(expected_revision=1, active=False))
        assert row["revision"] == 2
    with pytest.raises(HTTPException), transaction(factory) as db:
        identity.patch_reference(db, ref["id"], ReferencePatch(expected_revision=1, label="Écrasement"))
    with pytest.raises(HTTPException):
        reference(factory, "client", "airbus", "Doublon")
    with pytest.raises(HTTPException):
        patch(factory, ids[1], expected_revision=0, client_id=ref["id"])
    out = patch(factory, ids[0], expected_revision=1, description="Garder la référence historique")
    assert out["client_id"] == ref["id"] and out["references"][ref["id"]]["active"] is False
    with factory() as db:
        assert identity.list_references(db)["total"] == 0
        assert identity.list_references(db, include_inactive=True)["total"] == 1


def test_people_unique_identifiers_allow_namesakes_and_retained_inactive_assignment(store):
    factory, ids = store
    first = person(factory, email="Elodie@example.test", trigram="ELD")
    person(factory)  # Same name alone is not enough to merge two people.
    with pytest.raises(HTTPException):
        person(factory, email="elodie@example.test")
    with pytest.raises(HTTPException):
        person(factory, trigram="eld")
    with pytest.raises(HTTPException):
        person(factory, email="bad-email")
    patch(factory, ids[0], expected_revision=0, responsible_id=first["id"])
    with transaction(factory) as db:
        identity.patch_person(db, first["id"], PersonPatch(expected_revision=1, active=False))
    with pytest.raises(HTTPException):
        patch(factory, ids[1], expected_revision=0, responsible_id=first["id"])
    assert patch(factory, ids[0], expected_revision=1, description="Historique conservé")["responsible_id"] == first["id"]
    with factory() as db:
        assert identity.list_people(db, search="elodie", include_inactive=True)["total"] == 2


def test_concurrent_identity_edits_have_exactly_one_winner(store):
    factory, ids = store

    def edit(value):
        try:
            patch(factory, ids[0], expected_revision=0, description=value)
            return 200
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(edit, ["Décision A", "Décision B"]))
    assert sorted(result) == [200, 409]
    with factory() as db:
        assert identity.read_identity(db, ids[0])["revision"] == 1
        assert db.query(ProjectIdentityChange).count() == 1


def test_merged_validation_refreshes_profile_after_acquiring_write_lock(store):
    factory, ids = store
    patch(factory, ids[0], expected_revision=0, start_date="2026-10-05")
    with factory() as stale:
        cached_profile = stale.get(ProjectProfile, ids[0])
        assert cached_profile.planned_end_date == ""
        patch(factory, ids[0], expected_revision=1, planned_end_date="2026-10-06")
        with pytest.raises(HTTPException) as error:
            identity.patch_identity(stale, ids[0], IdentityPatch(expected_revision=2, start_date="2026-10-07"))
        assert error.value.status_code == 422
        stale.rollback()
    with factory() as db:
        out = identity.read_identity(db, ids[0])
        assert out["revision"] == 2 and out["start_date"] == "2026-10-05"


def test_person_patch_refreshes_cached_row_before_rebuilding_unique_keys(store):
    factory, _ = store
    first = person(factory, email="before@example.test")
    with factory() as stale:
        cached_person = stale.get(ProjectPerson, first["id"])
        assert cached_person.email == "before@example.test"
        with transaction(factory) as db:
            identity.patch_person(db, first["id"], PersonPatch(expected_revision=1, email="after@example.test"))
        identity.patch_person(stale, first["id"], PersonPatch(expected_revision=2, phone="0102030405"))
        stale.commit()
    with factory() as db:
        out = db.get(ProjectPerson, first["id"])
        assert out.normalized_email == "after@example.test" and out.email == "after@example.test"


def test_inactive_person_cannot_be_assigned_a_new_role_but_dates_remain_correctable(store):
    factory, ids = store
    lead = person(factory)
    with transaction(factory) as db:
        out = identity.add_member(db, ids[0], MemberCreate(expected_revision=0, person_id=lead["id"], role="calcul"))
        member_id = out["members"][0]["id"]
    with transaction(factory) as db:
        identity.patch_person(db, lead["id"], PersonPatch(expected_revision=1, active=False))
    with pytest.raises(HTTPException) as error, transaction(factory) as db:
        identity.patch_member(db, ids[0], member_id, MemberPatch(expected_revision=1, role="qualite"))
    assert error.value.status_code == 409
    with transaction(factory) as db:
        out = identity.patch_member(db, ids[0], member_id, MemberPatch(expected_revision=1, end_date="2026-12-31"))
        assert out["revision"] == 2 and out["members"][0]["role"] == "calcul"


def test_duplicate_responsible_is_refused_and_business_roles_allow_multiple_assignments(store):
    factory, ids = store
    first, second = person(factory), person(factory, first_name="Marc")
    patch(factory, ids[0], expected_revision=0, responsible_id=first["id"])
    with pytest.raises(HTTPException) as error, transaction(factory) as db:
        identity.add_member(db, ids[0], MemberCreate(expected_revision=1, person_id=second["id"], role="responsable_projet"))
    assert error.value.status_code == 409
    with transaction(factory) as db:
        out = identity.add_member(db, ids[0], MemberCreate(expected_revision=1, person_id=first["id"], role="qualite"))
        assert out["responsible_id"] == first["id"] and len(out["members"]) == 2
    with pytest.raises(HTTPException) as error, transaction(factory) as db:
        identity.patch_member(db, ids[0], out["members"][1]["id"], MemberPatch(
            expected_revision=2, start_date="2026-10-07", end_date="2026-10-06"))
    assert error.value.status_code == 422


def test_new_http_contract_validation_and_failed_command_transaction(store, monkeypatch):
    factory, ids = store
    app = FastAPI()
    app.include_router(router)

    def session():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = session
    client = TestClient(app)
    path = f"/api/v1/projects/{ids[0]}/identity"
    assert client.patch(path, json={"description": "Sans révision"}).status_code == 422
    assert client.patch(path, json={"expected_revision": 0, "actual_closure_date": "2026-10-05"}).status_code == 422
    assert client.patch(path, json={"expected_revision": 0, "hourly_rate": 12}).status_code == 422
    out = client.patch(path, json={"expected_revision": 0, "start_date": "2026-10-05"})
    assert out.status_code == 200
    assert client.patch(path, json={"expected_revision": 0, "description": "Périmé"}).status_code == 409
    assert client.get("/api/v1/project-people?limit=201").status_code == 422
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "reader")
    assert client.patch(path, json={"expected_revision": 1, "description": "Élévation", "actor_id": "owner"}).status_code == 422
    assert client.patch(path, json={"expected_revision": 1, "description": "Interdit"},
                        headers={"x-operator-role": "owner"}).status_code == 403
    assert client.get(path).json()["revision"] == 1


@pytest.mark.parametrize("schema,values", [
    (IdentityPatch, {"expected_revision": 0, "start_date": "2026-02-30"}),
    (IdentityPatch, {"expected_revision": 0, "description": None}),
    (IdentityPatch, {"expected_revision": 0, "quantity": 0}),
    (MemberCreate, {"expected_revision": 0, "person_id": "fake", "role": "administrateur"}),
    (MemberPatch, {"expected_revision": 0, "role": None}),
    (ReferenceCreate, {"kind": "client", "code": "  ", "label": "Test"}),
    (ReferencePatch, {"expected_revision": 0, "active": None}),
    (PersonPatch, {"expected_revision": 0, "first_name": None}),
    (PersonPatch, {"expected_revision": 0, "label": "Inconnu"}),
])
def test_reject_invalid_identity_commands(schema, values):
    with pytest.raises(ValidationError):
        schema(**values)


def test_operator_scope_is_server_configured_and_context_resets(monkeypatch):
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "reader")
    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", "[]")
    assert configured_operator().project_ids == frozenset()
    with operator_context(Operator("trusted-worker", "owner")):
        assert current_operator().id == "trusted-worker"
    assert current_operator().role == "reader"
    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", "all")
    with pytest.raises(ValueError):
        configured_operator()
    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", "[123]")
    with pytest.raises(ValueError):
        configured_operator()
    with pytest.raises(ValueError):
        Operator("fake", "administrator")


def test_additive_install_keeps_financial_cells_and_links_and_backup_precedes_ddl(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("CREATE TABLE projects(id TEXT PRIMARY KEY,code TEXT,hourly_rate REAL,margin_pct REAL);"
                                 "INSERT INTO projects VALUES('old-project','AIRB26LTH0205-A',91.5,12.75);"
                                 "CREATE TABLE brain_links(id TEXT PRIMARY KEY,project_id TEXT,brain_project_id TEXT);"
                                 "INSERT INTO brain_links VALUES('link','old-project','old-brain');")
    baseline = capture_baseline(path)
    engine = create_engine(f"sqlite:///{path}")
    configure_sqlite(engine)
    calls = []

    def backup():
        calls.append("backup")
        backup_sqlite(path, tmp_path / "before.db")

    result = install_identity_schema(engine, backup=backup)
    assert len(result["created_tables"]) == 6 and calls == ["backup"]
    assert compare_baseline(baseline, capture_baseline(path))["preserved"]
    assert compare_baseline(baseline, capture_baseline(tmp_path / "before.db"))["preserved"]
    assert install_identity_schema(engine, backup=backup) == {"created_tables": []}
    assert calls == ["backup"]
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    engine.dispose()


def test_failed_backup_prevents_identity_install(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects(id TEXT PRIMARY KEY)"))

    def failed_backup():
        raise OSError("Backup unavailable")

    with pytest.raises(OSError):
        install_identity_schema(engine, backup=failed_backup)
    with engine.connect() as connection:
        assert not connection.scalar(select(text("name")).select_from(text("sqlite_master"))
                                     .where(text("name='project_profiles'")))
    engine.dispose()


def test_missing_team_uniqueness_index_is_rejected_before_other_ddl(store):
    factory, _ = store
    engine = factory.kw["bind"]
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX uq_active_project_responsible"))
    with pytest.raises(ValueError, match="Contraintes d'identité incomplètes"):
        install_identity_schema(engine, backup=lambda: pytest.fail("Unsafe schema must be rejected before backup"))


def test_index_with_same_name_but_wrong_uniqueness_is_rejected(store):
    factory, _ = store
    engine = factory.kw["bind"]
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX uq_active_project_responsible"))
        connection.execute(text("CREATE INDEX uq_active_project_responsible ON project_members(project_id)"))
    with pytest.raises(ValueError, match="Contraintes d'identité incomplètes"):
        install_identity_schema(engine, backup=lambda: pytest.fail("Unsafe index cannot be accepted"))


def test_startup_installs_identity_after_backup_and_preserves_existing_project(tmp_path, monkeypatch):
    from backend.app import db as erp
    from sqlalchemy import inspect
    path = tmp_path / "startup.db"
    engine = create_engine(f"sqlite:///{path}")
    configure_sqlite(engine)
    # A genuine pre-L1 schema, with all historical fields including finances.
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables
                                            if table not in IDENTITY_TABLES])
    with sessionmaker(bind=engine)() as db:
        db.add(Project(id="legacy", code="OLD", title="Conservé", hourly_rate=91.5, margin_pct=12.75))
        db.commit()
    before = capture_baseline(path)
    backups = []

    def backup():
        assert not set(table.name for table in IDENTITY_TABLES).intersection(inspect(engine).get_table_names())
        backup_sqlite(path, tmp_path / "before-startup.db")
        backups.append(True)

    monkeypatch.setattr(erp, "engine", engine)
    monkeypatch.setattr(erp, "_backup", backup)
    erp.init_db()
    assert backups == [True]
    assert compare_baseline(before, capture_baseline(path))["preserved"]
    assert compare_baseline(before, capture_baseline(tmp_path / "before-startup.db"))["preserved"]
    erp.init_db()
    assert backups == [True]
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    engine.dispose()


def test_startup_refuses_invalid_identity_schema_before_other_ddl(store, monkeypatch):
    from backend.app import db as erp
    factory, _ = store
    engine = factory.kw["bind"]
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX uq_active_project_responsible"))
    monkeypatch.setattr(erp, "engine", engine)
    with pytest.raises(ValueError, match="Contraintes d'identité incomplètes"):
        erp.init_db()


def test_registered_monoserver_identity_team_and_reader_scope(store, monkeypatch):
    from app.main import app
    factory, ids = store

    def isolated_erp():
        with factory() as db:
            yield db

    original = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = isolated_erp
    try:
        client = TestClient(app, base_url="http://127.0.0.1:8001")
        path = f"/api/v1/projects/{ids[0]}/identity"
        assert client.get(path).json()["revision"] == 0
        reference = client.post("/api/v1/project-references", json={"kind": "client", "code": "TEST-HTTP",
                                                                 "label": "Client HTTP"})
        person_response = client.post("/api/v1/project-people", json={"first_name": "Alice", "last_name": "Martin"})
        assert reference.status_code == person_response.status_code == 201
        ref_id, person_id = reference.json()["id"], person_response.json()["id"]
        result = client.patch(path, json={"expected_revision": 0, "client_id": ref_id,
                                         "description": "Parcours réel", "responsible_id": person_id})
        assert result.status_code == 200
        assert result.json()["references"][ref_id]["label"] == "Client HTTP"
        member = result.json()["members"][0]
        result = client.patch(f"/api/v1/projects/{ids[0]}/members/{member['id']}",
                              json={"expected_revision": 1, "end_date": "2026-12-01"})
        assert result.status_code == 200 and result.json()["revision"] == 2
        history = client.get(path + "/history").json()
        assert {item["action"] for item in history["items"]} >= {"identity_updated", "member_added", "member_updated"}
        assert {item["actor_id"] for item in history["items"]} == {current_operator().id}
        monkeypatch.setenv("AGENT_OPERATOR_ROLE", "reader")
        monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", f'["{ids[0]}"]')
        assert client.get(path).json()["can_edit"] is False
        assert client.get(f"/api/v1/projects/{ids[1]}/identity").status_code == 404
        assert client.patch(path, json={"expected_revision": 2, "description": "Interdit"}).status_code == 403
        assert client.get("/api/v1/project-references").json()["total"] == 1
        assert client.get("/api/v1/project-people").json()["total"] == 1
        assert client.get(path).json()["description"] == "Parcours réel"
    finally:
        if original is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = original
