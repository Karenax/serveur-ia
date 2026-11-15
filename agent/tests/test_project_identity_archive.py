"""Selective v3 project archives and legacy v2 restoration, on isolated stores."""
from copy import deepcopy
from pathlib import Path
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db_support import configure_sqlite
from backend.app.db import Base
from backend.app.models import CdcSource, Project
from backend.app.project_identity_models import ProjectIdentityChange, ProjectMember, ProjectPerson, ProjectProfile, ProjectReference
from backend.app.project_identity_schemas import IdentityPatch, MemberCreate, PersonCreate, ReferenceCreate, ReferencePatch
from backend.app.services import project_identity as identity
from backend.app.services import project_archive as archive


@pytest.fixture
def stores(tmp_path):
    engines = [create_engine(f"sqlite:///{tmp_path / (name + '.db')}") for name in ("source", "target")]
    factories = []
    for engine in engines:
        configure_sqlite(engine)
        Base.metadata.create_all(engine)
        factories.append(sessionmaker(bind=engine, autoflush=False))
    yield factories
    for engine in engines:
        engine.dispose()


def make_archive(factory):
    with factory() as db:
        p = Project(code="AIRB26LTH0205-A", title="LED 2026", client_name="Valeur héritée", hourly_rate=91.5)
        other = Project(code="OTHER-" + uuid.uuid4().hex, title="Projet étranger")
        db.add_all([p, other])
        db.flush()
        client = identity.create_reference(db, ReferenceCreate(kind="client", code="AIRBUS", label="Airbus"))
        historical_client = identity.create_reference(db, ReferenceCreate(kind="client", code="OLD", label="Ancien client"))
        agency = identity.create_reference(db, ReferenceCreate(kind="agency", code="NTE", label="Nantes"))
        lead = identity.create_person(db, PersonCreate(first_name="Élodie", last_name="Durand",
                                                     email="lead@example.test", agency_id=agency["id"]))
        previous = identity.create_person(db, PersonCreate(first_name="Marc", last_name="Martin", trigram="MMA"))
        secret_client = identity.create_reference(db, ReferenceCreate(kind="client", code="SECRET", label="Autre client"))
        secret_person = identity.create_person(db, PersonCreate(first_name="Autre", last_name="Personne"))
        identity.patch_identity(db, p.id, IdentityPatch(expected_revision=0, client_id=historical_client["id"],
                                                       responsible_id=previous["id"]))
        identity.patch_identity(db, p.id, IdentityPatch(expected_revision=1, client_id=client["id"],
                                                       responsible_id=lead["id"], start_date="2026-10-05",
                                                       planned_end_date="2027-01-15", description="LED"))
        identity.add_member(db, p.id, MemberCreate(expected_revision=2, person_id=lead["id"], role="qualite"))
        identity.patch_identity(db, other.id, IdentityPatch(expected_revision=0, client_id=secret_client["id"],
                                                           responsible_id=secret_person["id"]))
        db.commit()
        exported = archive.export_archive(db, p.id)
        return exported, {"project": p.id, "client": client, "agency": agency, "historical_client": historical_client,
                          "lead": lead, "previous": previous, "secret_client": secret_client, "secret_person": secret_person}


def restore(factory, exported, code="RESTORED-0205"):
    with factory() as db:
        try:
            return archive.import_archive(db, exported, code=code)
        except Exception:
            db.rollback()
            raise


def test_v3_exports_only_current_and_historical_dependencies(stores):
    source, _ = stores
    exported, objects = make_archive(source)
    assert exported["version"] == 3
    references = exported["references"]
    assert {row["id"] for row in references["project_references"]} == {
        objects[key]["id"] for key in ("client", "agency", "historical_client")}
    assert {row["id"] for row in references["project_people"]} == {objects[key]["id"] for key in ("lead", "previous")}
    assert all(name not in exported["tables"] for name in ("project_references", "project_people", "project_reference_changes"))
    assert any(not row["active"] for row in exported["tables"]["project_members"])
    assert objects["secret_client"]["id"] not in str(exported)
    assert objects["secret_person"]["id"] not in str(exported)


def test_v3_round_trip_preserves_profiles_roles_history_and_financial_legacy(stores):
    source, target = stores
    exported, objects = make_archive(source)
    original = deepcopy(exported)
    result = restore(target, exported)
    assert result["version"] == 3 and result["id"] != objects["project"]
    assert exported == original  # Import never rewrites the caller's archive.
    with target() as db:
        out = identity.read_identity(db, result["id"])
        assert out["revision"] == 3 and out["description"] == "LED"
        assert out["planned_end_date"] == "2027-01-15"
        assert out["responsible"]["email"] == "lead@example.test"
        assert len(out["members"]) == 3 and sum(row["active"] for row in out["members"]) == 2
        assert db.get(Project, result["id"]).hourly_rate == 91.5
        assert db.query(ProjectIdentityChange).count() == len(exported["tables"]["project_identity_changes"])
        changes = identity.identity_history(db, result["id"])["items"]
        assert all(row["previous"].get("client_id") != objects["client"]["id"] for row in changes)
        assert all(row.project_id == result["id"] for row in db.query(ProjectMember))
        assert db.execute(text("PRAGMA foreign_key_check")).all() == []
        second = archive.export_archive(db, result["id"])
        assert second["version"] == 3 and len(second["references"]["project_people"]) == 2


def test_same_store_reuses_exact_references_without_mutating_them(stores):
    source, _ = stores
    exported, objects = make_archive(source)
    with source() as db:
        people_before = [dict(row) for row in db.execute(select(ProjectPerson.__table__)).mappings()]
        refs_before = [dict(row) for row in db.execute(select(ProjectReference.__table__)).mappings()]
    restored = restore(source, exported)
    with source() as db:
        assert [dict(row) for row in db.execute(select(ProjectPerson.__table__)).mappings()] == people_before
        assert [dict(row) for row in db.execute(select(ProjectReference.__table__)).mappings()] == refs_before
        assert identity.read_identity(db, restored["id"])["responsible_id"] == objects["lead"]["id"]


def test_different_uuid_same_business_reference_and_person_are_reused(stores):
    source, target = stores
    exported, objects = make_archive(source)
    with target() as db:
        agency = identity.create_reference(db, ReferenceCreate(kind="agency", code="NTE", label="Nantes"))
        client = identity.create_reference(db, ReferenceCreate(kind="client", code="AIRBUS", label="Airbus"))
        lead = identity.create_person(db, PersonCreate(first_name="Élodie", last_name="Durand",
                                                      email="lead@example.test", agency_id=agency["id"]))
        db.commit()
    restored = restore(target, exported)
    with target() as db:
        out = identity.read_identity(db, restored["id"])
        assert out["client_id"] == client["id"] and out["agency_id"] is None
        assert out["responsible_id"] == lead["id"] and out["responsible"]["agency_id"] == agency["id"]
        assert db.query(ProjectReference).count() == 3
        assert db.query(ProjectPerson).count() == 2
        assert lead["id"] != objects["lead"]["id"]


def test_changed_reference_is_an_explicit_conflict_without_project_or_global_write(stores):
    source, target = stores
    exported, _ = make_archive(source)
    with target() as db:
        identity.create_reference(db, ReferenceCreate(kind="client", code="AIRBUS", label="Libellé local conservé"))
        db.commit()
    with pytest.raises(HTTPException) as error:
        restore(target, exported)
    assert error.value.status_code == 409 and error.value.detail["table"] == "project_references"
    with target() as db:
        assert db.query(Project).count() == 0 and db.query(ProjectPerson).count() == 0
        assert db.query(ProjectReference).one().label == "Libellé local conservé"


def test_changed_same_uuid_reference_conflicts_even_after_rename(stores):
    source, _ = stores
    exported, objects = make_archive(source)
    with source() as db:
        identity.patch_reference(db, objects["client"]["id"], ReferencePatch(expected_revision=1, label="Nouvelle identité"))
        db.commit()
        before = db.query(Project).count()
    with pytest.raises(HTTPException) as error:
        restore(source, exported)
    assert error.value.status_code == 409
    with source() as db:
        assert db.query(Project).count() == before
        assert db.get(ProjectReference, objects["client"]["id"]).label == "Nouvelle identité"


def test_name_alone_never_merges_people(stores):
    source, target = stores
    exported, _ = make_archive(source)
    # Remove the old person's trigram from the archive consistently.
    person = next(row for row in exported["references"]["project_people"] if row["first_name"] == "Marc")
    person["trigram"] = ""
    person["normalized_trigram"] = None
    person["search_text"] = identity._person_values({key: person[key] for key in PersonCreate.model_fields})["search_text"]
    with target() as db:
        existing = identity.create_person(db, PersonCreate(first_name="Marc", last_name="Martin"))
        db.commit()
    restore(target, exported)
    with target() as db:
        assert db.query(ProjectPerson).count() == 3
        assert db.query(ProjectMember).filter_by(person_id=existing["id"]).count() == 0


def test_v2_project_remains_v2_and_can_be_restored(stores):
    source, target = stores
    with source() as db:
        row = Project(code="LEGACY-0205", title="Ancien", hourly_rate=91.5)
        db.add(row)
        db.commit()
        exported = archive.export_archive(db, row.id)
    assert exported["version"] == 2 and "references" not in exported
    assert "project_profiles" not in exported["tables"]
    restored = restore(target, exported)
    with target() as db:
        assert identity.read_identity(db, restored["id"])["revision"] == 0
        assert db.get(Project, restored["id"]).hourly_rate == 91.5


@pytest.mark.parametrize("change", [
    "foreign_reference", "missing_person", "missing_historical_reference", "wrong_reference_kind",
    "duplicate_row", "duplicate_reference_id", "global_table", "responsible_mismatch",
    "bad_date", "backward_dates", "bad_revision", "bad_actor", "future_history",
    "tampered_email_key", "bad_people_list", "v2_with_identity", "floating_version",
    "foreign_history_project", "foreign_history_member", "history_bad_date", "history_snapshot_list",
])
def test_invalid_archive_is_rejected_before_writing_anything(stores, change):
    source, target = stores
    exported, objects = make_archive(source)
    refs = exported["references"]
    profile = exported["tables"]["project_profiles"][0]
    if change == "foreign_reference":
        row = deepcopy(refs["project_references"][0])
        row.update(id=str(uuid.uuid4()), code="FOREIGN", normalized_code="foreign", search_text="foreign " + identity._normalized(row["label"]))
        refs["project_references"].append(row)
    elif change == "missing_person":
        refs["project_people"].pop()
    elif change == "missing_historical_reference":
        refs["project_references"] = [row for row in refs["project_references"] if row["id"] != objects["historical_client"]["id"]]
    elif change == "wrong_reference_kind":
        profile["client_id"] = objects["agency"]["id"]
    elif change == "duplicate_row":
        exported["tables"]["project_members"].append(deepcopy(exported["tables"]["project_members"][0]))
    elif change == "duplicate_reference_id":
        refs["project_people"][0]["id"] = refs["project_references"][0]["id"]
    elif change == "global_table":
        exported["tables"]["project_references"] = refs["project_references"]
    elif change == "responsible_mismatch":
        profile["responsible_id"] = None
    elif change == "bad_date":
        profile["start_date"] = "2026-02-30"
    elif change == "backward_dates":
        profile["start_date"] = "2030-01-01"
    elif change == "bad_revision":
        profile["revision"] = True
    elif change == "bad_actor":
        exported["tables"]["project_identity_changes"][0]["actor_id"] = 12
    elif change == "future_history":
        exported["tables"]["project_identity_changes"][0]["revision"] = 1000
    elif change == "tampered_email_key":
        refs["project_people"][0]["normalized_email"] = "forged@example.test"
    elif change == "bad_people_list":
        refs["project_people"] = "invalid"
    elif change == "v2_with_identity":
        exported["version"] = 2
    elif change == "floating_version":
        exported["version"] = 3.0
    elif change.startswith("foreign_history") or change.startswith("history_"):
        event = next(row for row in exported["tables"]["project_identity_changes"] if row["action"] == "member_added")
        if change == "foreign_history_project":
            event["value"]["project_id"] = str(uuid.uuid4())
        elif change == "foreign_history_member":
            event["value"]["id"] = str(uuid.uuid4())
        elif change == "history_bad_date":
            event["value"]["archived_at"] = "not-a-date"
        elif change == "history_snapshot_list":
            event["value"] = []
    with pytest.raises(HTTPException) as error:
        restore(target, exported)
    assert error.value.status_code == 400
    with target() as db:
        assert db.query(Project).count() == 0
        assert db.query(ProjectProfile).count() == 0
        assert db.query(ProjectReference).count() == 0
        assert db.query(ProjectPerson).count() == 0


def test_restore_rejects_case_insensitive_duplicate_project_code(stores):
    source, target = stores
    exported, _ = make_archive(source)
    restore(target, exported, code="CASE-0205")
    with pytest.raises(HTTPException) as error:
        restore(target, exported, code="case-0205")
    assert error.value.status_code == 409


def test_business_text_that_looks_like_an_identifier_is_not_remapped(stores):
    source, target = stores
    _, objects = make_archive(source)
    with source() as db:
        identity.patch_identity(db, objects["project"], IdentityPatch(expected_revision=3, description=objects["lead"]["id"]))
        db.commit()
        exported = archive.export_archive(db, objects["project"])
    result = restore(target, exported)
    with target() as db:
        out = identity.read_identity(db, result["id"])
        assert out["description"] == objects["lead"]["id"]
        assert out["description"] != out["responsible_id"]
        events = identity.identity_history(db, result["id"])["items"]
        assert any(row["value"].get("description") == objects["lead"]["id"] for row in events)


@pytest.mark.parametrize("change", ["missing_piece", "unknown_area", "reference_owner", "duplicate_piece", "invalid_encoding"])
def test_invalid_file_bundle_is_rejected_before_any_file_is_copied(stores, tmp_path, monkeypatch, change):
    source, target = stores
    _, objects = make_archive(source)
    root = tmp_path / "cdc-storage"
    root.mkdir()
    original = root / "source.bin"
    original.write_bytes(b"Document CDC test")
    monkeypatch.setattr("backend.app.routers.cdc.cdc_storage_root", lambda: root)
    with source() as db:
        db.add(CdcSource(project_id=objects["project"], filename="source.bin", storage_path=str(original)))
        db.commit()
        exported = archive.export_archive(db, objects["project"])
    if change == "missing_piece":
        exported["files"] = []
    else:
        invalid = deepcopy(exported["files"][0])
        if change == "unknown_area":
            invalid["area"] = "unknown"
        elif change == "reference_owner":
            invalid["owner"] = objects["lead"]["id"]
        elif change == "invalid_encoding":
            invalid["data"] = 123
            exported["files"] = []
        exported["files"].append(invalid)
    with pytest.raises(HTTPException) as error:
        restore(target, exported)
    assert error.value.status_code == 400
    assert list(root.iterdir()) == [original]
    with target() as db:
        assert db.query(Project).count() == 0 and db.query(ProjectReference).count() == 0


def test_v3_cdc_piece_is_restored_under_new_project_uuid(stores, tmp_path, monkeypatch):
    source, target = stores
    _, objects = make_archive(source)
    root = tmp_path / "cdc-storage"
    root.mkdir()
    original = root / "source.bin"
    original.write_bytes(b"Document CDC portable")
    monkeypatch.setattr("backend.app.routers.cdc.cdc_storage_root", lambda: root)
    with source() as db:
        db.add(CdcSource(project_id=objects["project"], filename="source.bin", storage_path=str(original)))
        db.commit()
        exported = archive.export_archive(db, objects["project"])
    restored = restore(target, exported)
    with target() as db:
        row = db.query(CdcSource).filter_by(project_id=restored["id"]).one()
        path = Path(row.storage_path)
        assert path.is_relative_to(root / restored["id"])
        assert path.read_bytes() == original.read_bytes()
        assert exported["tables"]["cdc_sources"][0]["storage_path"] == str(original)


def test_v2_works_without_l1_schema_while_v3_requires_its_migration(stores, tmp_path):
    source, _ = stores
    exported, _ = make_archive(source)
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    configure_sqlite(engine)
    identity_tables = {"project_profiles", "project_members", "project_identity_changes",
                       "project_references", "project_people", "project_reference_changes"}
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.tables.values() if table.name not in identity_tables])
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as db:
        old = Project(code="OLD-0205", title="Ancien schéma")
        db.add(old)
        db.commit()
        old_export = archive.export_archive(db, old.id)
        assert old_export["version"] == 2
    assert restore(factory, old_export)["version"] == 2
    with pytest.raises(HTTPException) as error:
        restore(factory, exported, code="L1-0205")
    assert error.value.status_code == 409 and "migration" in error.value.detail
    engine.dispose()
