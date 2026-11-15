"""Real v9 ERP/Brain round-trips, file closure and failure preservation."""

import base64
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path

from fastapi import HTTPException
from PIL import Image
import pytest
from sqlalchemy import event, select, text

from app.db_support import backup_sqlite
from app.services.deliverable_manifest import freeze
from backend.app.models import BrainLink, Project
from backend.app.project_note_models import (
    ProjectNote,
    NoteVersion,
    NoteAttachment,
)
from backend.app.project_note_schemas import NoteCreate, NoteSave, NoteRestore
from backend.app.services import project_archive as archive, project_notes as notes
from backend.app.services import (
    project_note_files as managed,
    project_note_imports as imports,
)
from backend.app.services import project_note_archive_store as note_store
from backend.app.services.project_note_schema import install_note_schema
from backend.app.services.project_operator import Operator, operator_context
from backend.app.services.migration_guard import capture_baseline, compare_baseline
from tests.test_project_document_archive import paired, restore
from tests.test_project_document_job_archive import batch_archive
from tests.test_project_note_imports import command
from tests.test_project_note_source_preview import sources
from tests import test_project_notes_core as core

__all__ = ["paired", "batch_archive"]


def switch(monkeypatch, store):
    import app.db
    import backend.app.db

    monkeypatch.setattr(app.db, "SessionLocal", store["brain"])
    monkeypatch.setattr(backend.app.db, "APP_DIR", store["home"])
    monkeypatch.setattr(managed, "APP_DIR", store["home"])


def install(stores):
    for store in stores.values():
        install_note_schema(
            store["erp"].kw["bind"],
            backup=lambda s=store: backup_sqlite(
                s["erp_path"], s["home"] / "before-v9-notes.db"
            ),
        )


def populate(source):
    pid = source["pid"]
    files = sources()
    image = BytesIO()
    Image.new("RGB", (8, 8), "red").save(image, format="PNG")
    files["content.html"] = (
        b'<p>Actuel</p><img src="data:image/png;base64,'
        + base64.b64encode(image.getvalue())
        + b'">'
    )
    with source["erp"]() as db:
        result = imports.import_selected(
            db, pid, command(files), acquire=lambda _: files
        )
        note_id = result["note"]["id"]
        db.commit()
        notes.save_note(
            db,
            pid,
            note_id,
            NoteSave(
                command_id=core.command(),
                expected_revision=2,
                title="Correction Agent",
                attachment_ids=result["note"]["attachment_ids"],
                content=core.rich(),
            ),
        )
        notes.restore_note(
            db,
            pid,
            note_id,
            NoteRestore(
                command_id=core.command(),
                expected_revision=3,
                version_id=result["source_versions"][1]["note_version_id"],
            ),
        )
        created = notes.create_note(
            db,
            pid,
            NoteCreate(
                command_id=core.command(), title="Note manuelle", content=core.rich()
            ),
        )
        managed.upload(
            db,
            pid,
            created["note"]["id"],
            command_id=core.command(),
            filename="Non encore liée.txt",
            stream=BytesIO(b"Unreferenced attachment must survive"),
        )
        db.commit()


@pytest.fixture
def note_archive(paired, monkeypatch):
    _, stores = paired
    install(stores)
    source, target = stores["source"], stores["target"]
    switch(monkeypatch, source)
    populate(source)
    from app.models import Project as BrainProject

    with source["brain"]() as brain:
        brain_id = brain.scalar(select(BrainProject.id))
    with source["erp"]() as db:
        db.add(BrainLink(project_id=source["pid"], brain_project_id=brain_id))
        db.commit()
        data = archive.export_archive(db, source["pid"])
    assert data["version"] == 9 and len(data["tables"]["project_notes"]) == 2
    assert len([entry for entry in data["files"] if entry["area"] == "note-file"]) == 3
    switch(monkeypatch, target)
    yield data, stores


def test_note_outbox_stays_local_and_old_partial_graph_is_rejected(note_archive):
    from datetime import datetime
    from backend.app.db import Base
    from backend.app.note_evidence_models import NoteEvidenceOutbox
    data, stores = note_archive
    source = stores['source']
    before = capture_baseline(source['erp_path'])
    with source['erp']() as db:
        rows = [dict(row) for row in db.execute(select(NoteEvidenceOutbox.__table__)).mappings()]
    assert rows and 'note_evidence_outbox' not in data['tables']
    # This is the former generic graph: note parents live in the v9 typed
    # section, while an outbox row was accidentally exported as an ordinary row.
    serialized = [{key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in row.items()} for row in rows]
    with pytest.raises(HTTPException) as caught:
        archive._validate_tables(Base.metadata, {
            'projects': data['tables']['projects'], 'note_evidence_outbox': serialized})
    assert caught.value.status_code == 400 and 'Relation sortant du projet' in caught.value.detail
    assert capture_baseline(source['erp_path']) == before


def test_project_archive_keeps_both_original_and_ocr_source_files(note_archive, monkeypatch):
    from reportlab.pdfgen.canvas import Canvas
    from app import config
    from app.models import Source
    from app.routers.sources import raw_source
    from app.services import library_ocr, settings_service, source_library

    initial, stores = note_archive
    source, target = stores['source'], stores['target']
    output = BytesIO()
    document = Canvas(output)
    document.showPage()
    document.save()
    original = output.getvalue()
    source_raw = source['home'] / 'source-raw'
    target_raw = target['home'] / 'raw'
    switch(monkeypatch, source)
    monkeypatch.setattr(config, 'RAW_DIR', source_raw)
    monkeypatch.setattr(library_ocr, 'profile', lambda: {'language': 'fr-FR'})
    monkeypatch.setattr(library_ocr, 'recognize_page', lambda *args: {
        'text': 'Pression nominale 318 kPa', 'lines': [], 'width': 1200, 'height': 420})
    source_library.init_library_db(source['brain'].kw['bind'])
    with source['brain']() as db:
        settings_service.save_section(db, 'foresight', {'enabled': True, 'mode': 'network'})
        imported = source_library.import_bytes(db, project_id=initial['brain']['projects'][0]['id'],
            provider='file', provider_key='scan.pdf', filename='scan.pdf', data=original, mime_type='application/pdf')
        recognized = library_ocr.recognize_source(db, imported['source_id'])

    with source['erp']() as db:
        bundle = archive.export_archive(db, source['pid'])
    assert any('catalogue' in warning for warning in bundle['warnings'])
    pieces = {piece['owner']: piece for piece in bundle['files'] if piece['area'] == 'raw'}
    assert set(pieces) == {imported['source_id'], recognized['source_id']}
    assert all(base64.b64decode(piece['data']) == original for piece in pieces.values())

    switch(monkeypatch, target)
    monkeypatch.setattr(config, 'RAW_DIR', target_raw)
    damaged = deepcopy(bundle)
    piece = next(piece for piece in damaged['files'] if piece['owner'] == recognized['source_id'])
    piece.update(data=base64.b64encode(b'wrong PDF').decode(), sha256=hashlib.sha256(b'wrong PDF').hexdigest())
    with pytest.raises(HTTPException, match='empreinte Brain'):
        restore(target, damaged)
    restored = restore(target, bundle)
    with target['erp']() as db:
        brain_id = db.get(BrainLink, restored['id']).brain_project_id
    with target['brain']() as db:
        sources = list(db.scalars(select(Source).where(Source.project_id == brain_id)))
        assert len(sources) == 2
        assert len({source.original_uri for source in sources}) == 1
        assert {source.source_metadata['extraction_status'] for source in sources} == {'ocr_required', 'ocr_extracted'}
        assert all(Path(raw_source(source.id, db).path).read_bytes() == original for source in sources)
        extracted = next(source for source in sources if source.source_metadata['extraction_status'] == 'ocr_extracted')
        assert [(artifact.content_json['physical_page'], artifact.content_text) for artifact in extracted.artifacts] == [
            (1, 'Pression nominale 318 kPa')]


def test_v9_roundtrip_twice_keeps_captures_authors_restore_bindings_and_all_files(
    note_archive,
):
    data, stores = note_archive
    source, target = stores["source"], stores["target"]
    original = deepcopy(data)
    source_before = (
        capture_baseline(source["erp_path"]),
        capture_baseline(source["brain_path"]),
    )
    before = (
        capture_baseline(target["erp_path"]),
        capture_baseline(target["brain_path"]),
    )
    first = restore(target, data)
    originals = sorted(
        data["tables"]["project_note_versions"],
        key=lambda row: (json.loads(row["snapshot"])["note_id"], row["revision"]),
    )
    with target["erp"]() as db:
        heads = list(
            db.scalars(select(ProjectNote).where(ProjectNote.project_id == first["id"]))
        )
        assert sorted(head.revision for head in heads) == [1, 4]
        imported = next(head for head in heads if head.revision == 4)
        state = notes._detail(db, imported)
        assert any(block["type"] == "image" for block in state["content"]["blocks"])
        receipt = imports.read_import(db, first["id"], imported.id)
        assert receipt["source_versions"][0]["source_actor"] is None
        assets = list(
            db.scalars(
                select(NoteAttachment).where(NoteAttachment.project_id == first["id"])
            )
        )
        assert len(assets) == 3
        for asset in assets:
            content, _ = managed.download(db, first["id"], asset.note_id, asset.id)
            assert hashlib.sha256(content).hexdigest() == asset.sha256
        assert imports.original_file(db, first["id"], imported.id, "content.html")[
            0
        ].startswith(b"<p>Actuel")
        second_data = archive.export_archive(db, first["id"])
        for row in second_data["tables"]["project_note_versions"]:
            snapshot = json.loads(row["snapshot"])
            old = next(
                item for item in originals if item["snapshot"] == row["snapshot"]
            )
            assert (
                row["sha256"],
                row["command_sha256"],
                row["actor_id"],
                row["command_id"],
            ) == (
                old["sha256"],
                old["command_sha256"],
                old["actor_id"],
                old["command_id"],
            )
            assert row["id"] != old["id"] and row["execution_blocked"] is True
            if snapshot["operation"] == "restore":
                assert row["restored_version_id"] != snapshot["restored_from"]
        assert not db.execute(text("PRAGMA foreign_key_check")).all()
    second = restore(target, second_data, "IMPORTED-SECOND")
    with target["erp"]() as db:
        third = archive.export_archive(db, second["id"])
        assert sorted(
            row["snapshot"] for row in third["tables"]["project_note_versions"]
        ) == sorted(row["snapshot"] for row in originals)
        assert sorted(
            row["snapshot"] for row in third["tables"]["project_note_imports"]
        ) == sorted(row["snapshot"] for row in data["tables"]["project_note_imports"])
        head = db.scalar(
            select(ProjectNote).where(
                ProjectNote.project_id == second["id"], ProjectNote.revision == 4
            )
        )
        prior = db.scalar(
            select(NoteVersion).where(
                NoteVersion.note_id == head.id, NoteVersion.revision == 1
            )
        )
        notes.restore_note(
            db,
            second["id"],
            head.id,
            NoteRestore(
                command_id=core.command(), expected_revision=4, version_id=prior.id
            ),
        )
        db.commit()
        assert head.revision == 5
        assert not db.execute(text("PRAGMA foreign_key_check")).all()
    assert data == original and source_before == (
        capture_baseline(source["erp_path"]),
        capture_baseline(source["brain_path"]),
    )
    assert compare_baseline(before[0], capture_baseline(target["erp_path"]))[
        "preserved"
    ]
    assert compare_baseline(before[1], capture_baseline(target["brain_path"]))[
        "preserved"
    ]


@pytest.mark.parametrize(
    "damage",
    [
        "missing_file",
        "missing_original",
        "duplicate_file",
        "extra_file_field",
        "wrong_file_name",
        "wrong_bytes",
        "oversize_encoded",
        "missing_version",
        "wrong_restore",
        "wrong_actor",
        "wrong_section",
        "extra_envelope",
        "bad_original_rehashed",
    ],
)
def test_v9_damaged_archive_refused_before_any_file_or_sql_write(note_archive, damage):
    data, stores = note_archive
    target = stores["target"]
    value = deepcopy(data)
    piece = next(entry for entry in value["files"] if entry["area"] == "note-file")
    original = next(
        entry for entry in value["files"] if entry["area"] == "note-original"
    )
    if damage == "missing_file":
        value["files"].remove(piece)
    elif damage == "missing_original":
        value["files"].remove(original)
    elif damage == "duplicate_file":
        value["files"].append(piece)
    elif damage == "extra_file_field":
        piece["server_path"] = "C:/not-allowed"
    elif damage == "wrong_file_name":
        piece["name"] = "../blob"
    elif damage == "wrong_bytes":
        piece["data"] = base64.b64encode(b"Changed").decode("ascii")
    elif damage == "oversize_encoded":
        piece["data"] += "AAAA"
    elif damage == "missing_version":
        value["tables"]["project_note_versions"].pop()
    elif damage == "wrong_restore":
        next(
            row
            for row in value["tables"]["project_note_versions"]
            if row["restored_version_id"]
        )["restored_version_id"] = core.command()
    elif damage == "wrong_actor":
        value["tables"]["project_note_versions"][0]["actor_id"] = "Fake actor"
    elif damage == "wrong_section":
        value["note_references"]["version"] = True
    elif damage == "extra_envelope":
        value["not_allowed"] = True
    else:
        content = b"Corrupt original ZIP"
        digest = hashlib.sha256(content).hexdigest()
        row = value["tables"]["project_note_imports"][0]
        capture = json.loads(row["snapshot"])
        capture.update(bundle_sha256=digest, bundle_size_bytes=len(content))
        row.update(sha256=digest, size_bytes=len(content))
        row["snapshot"], row["snapshot_sha256"] = freeze(capture)
        original.update(sha256=digest, data=base64.b64encode(content).decode("ascii"))
    before = (
        capture_baseline(target["erp_path"]),
        capture_baseline(target["brain_path"]),
    )
    files = {
        str(p.relative_to(target["home"])): p.read_bytes()
        for p in target["home"].rglob("*")
        if p.is_file()
        and p.suffix not in {".db", ".db-wal", ".db-shm"}
        and "-wal" not in p.name
        and "-shm" not in p.name
    }
    with pytest.raises(HTTPException) as caught:
        restore(target, value)
    assert caught.value.status_code in {400, 409}
    assert before == (
        capture_baseline(target["erp_path"]),
        capture_baseline(target["brain_path"]),
    )
    assert files == {
        str(p.relative_to(target["home"])): p.read_bytes()
        for p in target["home"].rglob("*")
        if p.is_file()
        and p.suffix not in {".db", ".db-wal", ".db-shm"}
        and "-wal" not in p.name
        and "-shm" not in p.name
    }


@pytest.mark.parametrize("version", [2, 3, 4, 5, 6, 7, 8])
def test_old_versions_cannot_smuggle_note_tables_or_sections(note_archive, version):
    data, stores = note_archive
    value = deepcopy(data)
    value["version"] = version
    before = capture_baseline(stores["target"]["erp_path"])
    with pytest.raises(HTTPException):
        restore(stores["target"], value)
    assert capture_baseline(stores["target"]["erp_path"]) == before


def test_v9_sql_failure_keeps_both_stores_exact_and_prepared_files_for_inspection(
    note_archive,
):
    data, stores = note_archive
    target = stores["target"]
    before = (
        capture_baseline(target["erp_path"]),
        capture_baseline(target["brain_path"]),
    )
    engine = target["erp"].kw["bind"]

    def failure(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO project_note_versions"):
            raise RuntimeError("Injected late SQL failure")

    event.listen(engine, "before_cursor_execute", failure)
    try:
        with pytest.raises(HTTPException):
            restore(target, data)
    finally:
        event.remove(engine, "before_cursor_execute", failure)
    assert before == (
        capture_baseline(target["erp_path"]),
        capture_baseline(target["brain_path"]),
    )
    retained = {
        str(p): p.read_bytes()
        for root in ("note-files", "note-originals")
        for p in (target["home"] / root).rglob("*")
        if p.is_file()
    }
    assert len(retained) == 4
    restore(target, data)
    assert all(Path(name).read_bytes() == content for name, content in retained.items())
    assert (
        sum(
            p.is_file()
            for root in ("note-files", "note-originals")
            for p in (target["home"] / root).rglob("*")
        )
        == 8
    )


def test_v9_requires_protected_schema_and_owner_before_files(note_archive):
    data, stores = note_archive
    target = stores["target"]
    with (
        operator_context(Operator("reader", "reader")),
        pytest.raises(HTTPException) as caught,
    ):
        restore(target, data)
    assert caught.value.status_code == 403
    with target["erp"].kw["bind"].begin() as db:
        db.execute(text("DROP TRIGGER trg_project_note_versions_sequence"))
    before = capture_baseline(target["erp_path"])
    with pytest.raises(HTTPException) as caught:
        restore(target, data)
    assert caught.value.status_code == 409
    assert capture_baseline(target["erp_path"]) == before
    assert not (target["home"] / "note-files").exists()


def test_v9_without_document_or_job_rows_roundtrips(paired, monkeypatch):
    _, stores = paired
    install(stores)
    source, target = stores["source"], stores["target"]
    switch(monkeypatch, source)
    with source["erp"]() as db:
        project = Project(code="ONLY-NOTES", title="Notes uniquement")
        db.add(project)
        db.commit()
        notes.create_note(
            db,
            project.id,
            NoteCreate(command_id=core.command(), title="Sans formulaire"),
        )
        db.commit()
        value = archive.export_archive(db, project.id)
    assert (
        value["version"] == 9
        and "document_references" not in value
        and "document_job_references" not in value
    )
    switch(monkeypatch, target)
    first = restore(target, value)
    with target["erp"]() as db:
        assert notes.list_notes(db, first["id"])["total"] == 1
        assert archive.export_archive(db, first["id"])["version"] == 9


def test_v9_with_durable_document_jobs_preserves_jobs_and_notes(
    batch_archive, monkeypatch
):
    _, stores = batch_archive
    install(stores)
    source, target = stores["source"], stores["target"]
    switch(monkeypatch, source)
    populate(source)
    with source["erp"]() as db:
        value = archive.export_archive(db, source["pid"])
    assert value["version"] == 9 and "document_job_references" in value
    switch(monkeypatch, target)
    first = restore(target, value)
    with target["erp"]() as db:
        exported = archive.export_archive(db, first["id"])
        assert len(exported["tables"]["project_notes"]) == 2
        assert len(exported["tables"]["project_document_jobs"]) == 1
        assert exported["tables"]["project_document_jobs"][0]["execution_blocked"]
        assert not db.execute(text("PRAGMA foreign_key_check")).all()


def test_note_destination_never_adopts_existing_matching_bytes(tmp_path):
    row = {"storage_id": core.command()}
    target = note_store.destination(tmp_path, "note-file", row)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"Same abandoned bytes")
    with pytest.raises(HTTPException) as caught:
        note_store.destination(tmp_path, "note-file", row)
    assert (
        caught.value.status_code == 409
        and target.read_bytes() == b"Same abandoned bytes"
    )
