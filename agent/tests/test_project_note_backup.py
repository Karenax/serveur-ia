"""Offline global restore, retained original bytes and no source reacquisition."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db_support import configure_sqlite
from app.services.backup import create_backup, restore_backup
from app.services.note_backup import collect_files, validate_history
from backend.app.project_note_models import NoteVersion, ProjectNote, NoteSourceImport
from backend.app.project_note_schemas import NoteSave
from backend.app.services import project_notes as notes, project_note_imports as imports
from backend.app.services import project_note_files as managed
from backend.app.services.project_note_schema_rules import (
    validate_schema,
    specification,
)
from backend.app.services.project_operator import Operator, operator_context
from backend.app.services.migration_guard import capture_baseline
from tests.test_project_note_archive_store import note_archive, switch
from tests.test_project_document_archive import paired
from tests import test_project_notes_core as core

__all__ = ["note_archive", "paired"]


@pytest.fixture
def backup(note_archive, tmp_path, monkeypatch):
    _, stores = note_archive
    source = stores["source"]
    switch(monkeypatch, source)
    storage = tmp_path / "brain-storage"
    storage.mkdir()
    (storage / "retained.txt").write_bytes(b"Existing stored data")
    output = tmp_path / "coordinated-notes-backup"
    before = (
        capture_baseline(source["erp_path"]),
        capture_baseline(source["brain_path"]),
    )
    manifest = create_backup(output, source["brain_path"], source["home"], storage)
    assert len(manifest["note_files"]) == 4
    assert before == (
        capture_baseline(source["erp_path"]),
        capture_baseline(source["brain_path"]),
    )
    yield output, source, storage, manifest


def test_backup_snapshots_nested_eg2_wal_and_relocates_configured_index(backup, tmp_path):
    _, source, storage, _ = backup
    index = storage / 'eg2' / 'profile' / 'index.db'
    index.parent.mkdir(parents=True)
    with sqlite3.connect(source['brain_path']) as db:
        db.execute("INSERT OR REPLACE INTO app_settings (key,value,updated_at) VALUES ('memory',?,CURRENT_TIMESTAMP)",
                   (json.dumps({'index_path': r'F:\Agent\storage\eg2\profile\index.db'}),))
    db.close()
    writer = sqlite3.connect(index)
    try:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('PRAGMA wal_autocheckpoint=0')
        writer.execute('CREATE TABLE passages (profile TEXT)')
        writer.execute("INSERT INTO passages VALUES ('restored')")
        writer.commit()
        snapshot = tmp_path / 'with-index'
        create_backup(snapshot, source['brain_path'], source['home'], storage)
        restored = tmp_path / 'restored-index'
        restore_backup(snapshot, restored)
    finally:
        writer.close()
    expected = restored / 'storage/eg2/profile/index.db'
    with sqlite3.connect(restored / 'brain/project_brain.db') as db:
        memory = json.loads(db.execute("SELECT value FROM app_settings WHERE key='memory'").fetchone()[0])
        assert Path(memory['index_path']) == expected
    db.close()
    with sqlite3.connect(expected) as db:
        assert db.execute('SELECT profile FROM passages').fetchall() == [('restored',)]
    db.close()


def test_offline_restore_keeps_notes_originals_and_freezes_only_historical_commands(
    backup, tmp_path, monkeypatch
):
    source, original, _, manifest = backup
    original_db = capture_baseline(original["erp_path"])
    archive_hashes = {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in manifest["files"]
    }
    target = tmp_path / "independent-restoration"
    result = restore_backup(source, target)
    assert (
        result["files"] == len(manifest["files"])
        and validate_history(target / "erp/minipilot.db") == 2
    )
    assert len(collect_files(target / "erp/minipilot.db", target / "erp")) == 4
    engine = create_engine("sqlite:///" + (target / "erp/minipilot.db").as_posix())
    configure_sqlite(engine)
    monkeypatch.setattr(managed, "APP_DIR", target / "erp")
    factory = sessionmaker(bind=engine)
    with factory() as db:
        assert all(
            version.execution_blocked for version in db.scalars(select(NoteVersion))
        )
        source_note = db.scalar(select(NoteSourceImport))
        receipt = imports.read_import(db, source_note.project_id, source_note.note_id)
        assert len(receipt["source_versions"]) == 2 and source_note.execution_blocked
        assert imports.original_file(
            db, source_note.project_id, source_note.note_id, "content.html"
        )[0].startswith(b"<p>Actuel")
        head = db.get(ProjectNote, source_note.note_id)
        notes.save_note(
            db,
            head.project_id,
            head.id,
            NoteSave(
                command_id=core.command(),
                expected_revision=head.revision,
                title="Edition après restauration",
                content=core.rich(),
                attachment_ids=notes._detail(db, head)["attachment_ids"],
            ),
        )
        db.commit()
        assert head.revision == 5
        assert not next(
            db.execute(__import__("sqlalchemy").text("PRAGMA foreign_key_check")), None
        )
    engine.dispose()
    assert capture_baseline(original["erp_path"]) == original_db
    assert archive_hashes == {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in manifest["files"]
    }
    with (
        sqlite3.connect(source / "erp/minipilot.db") as before,
        sqlite3.connect(target / "erp/minipilot.db") as after,
    ):
        for row in before.execute(
            "SELECT id,snapshot,sha256,command_sha256,actor_id,attachment_bindings,restored_version_id FROM project_note_versions"
        ):
            assert (
                after.execute(
                    "SELECT id,snapshot,sha256,command_sha256,actor_id,attachment_bindings,restored_version_id FROM project_note_versions WHERE id=?",
                    (row[0],),
                ).fetchone()
                == row
            )


@pytest.mark.parametrize(
    "damage",
    [
        "missing_note_inventory",
        "missing_original",
        "wrong_note_path",
        "modified_piece",
        "unprotected_schema",
        "forged_capture",
        "incomplete_versions",
        "wrong_restore_binding",
    ],
)
def test_restore_refuses_rehashed_corrupt_notes_before_creating_destination(
    backup, tmp_path, damage
):
    source, _, _, manifest = backup
    manifest = deepcopy(manifest)
    dbpath = source / "erp/minipilot.db"
    if damage == "missing_note_inventory":
        manifest.pop("note_files")
    elif damage == "missing_original":
        path = next(
            name for name in manifest["files"] if name.startswith("erp/note-originals/")
        )
        manifest["files"].pop(path)
    elif damage == "wrong_note_path":
        manifest["note_files"][0]["storage_id"] = core.command()
    elif damage == "modified_piece":
        name = next(
            name for name in manifest["files"] if name.startswith("erp/note-files/")
        )
        (source / name).write_bytes(b"Changed but rehashed container")
        manifest["files"][name] = hashlib.sha256(
            (source / name).read_bytes()
        ).hexdigest()
    else:
        with sqlite3.connect(dbpath) as db:
            if damage == "unprotected_schema":
                db.execute("DROP TRIGGER trg_project_note_versions_sequence")
            elif damage == "forged_capture":
                db.execute("DROP TRIGGER trg_project_note_versions_update_immutable")
                db.execute(
                    "UPDATE project_note_versions SET actor_id='Forged operator' WHERE revision=1"
                )
                db.execute(
                    specification()["triggers"][
                        "trg_project_note_versions_update_immutable"
                    ]
                )
            elif damage == "incomplete_versions":
                db.execute("DROP TRIGGER trg_project_note_versions_delete_immutable")
                db.execute("DELETE FROM project_note_versions WHERE revision=1")
                db.execute(
                    specification()["triggers"][
                        "trg_project_note_versions_delete_immutable"
                    ]
                )
            else:
                db.execute("DROP TRIGGER trg_project_note_versions_update_immutable")
                db.execute(
                    "UPDATE project_note_versions SET restored_version_id=? WHERE restored_version_id IS NOT NULL",
                    (core.command(),),
                )
                db.execute(
                    specification()["triggers"][
                        "trg_project_note_versions_update_immutable"
                    ]
                )
        manifest["files"]["erp/minipilot.db"] = hashlib.sha256(
            dbpath.read_bytes()
        ).hexdigest()
    (source / "backup.json").write_text(json.dumps(manifest), encoding="utf-8")
    target = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        restore_backup(source, target)
    assert not target.exists()


def test_create_backup_refuses_missing_managed_piece_before_creating_output(
    note_archive, tmp_path, monkeypatch
):
    _, stores = note_archive
    source = stores["source"]
    switch(monkeypatch, source)
    # Move only a fictional recipe blob to preserve it while simulating absence.
    item = next((source["home"] / "note-files").rglob("blob"))
    item.rename(item.with_name("preserved-missing-blob"))
    output = tmp_path / "missing-piece-backup"
    with pytest.raises(ValueError):
        create_backup(
            output, source["brain_path"], source["home"], tmp_path / "storage"
        )
    assert not output.exists() and item.with_name("preserved-missing-blob").is_file()


def test_import_nonce_cannot_reacquire_network_after_global_restore(
    backup, tmp_path, monkeypatch
):
    source, _, _, _ = backup
    target = tmp_path / "blocked-source-replay"
    restore_backup(source, target)
    engine = create_engine("sqlite:///" + (target / "erp/minipilot.db").as_posix())
    configure_sqlite(engine)
    monkeypatch.setattr(managed, "APP_DIR", target / "erp")
    with sessionmaker(bind=engine)() as db:
        row = db.scalar(select(NoteSourceImport))
        capture = imports._capture(row)
        with (
            operator_context(Operator(capture.actor_id, "owner")),
            pytest.raises(HTTPException) as caught,
        ):
            imports.import_selected(
                db,
                row.project_id,
                capture.command,
                acquire=lambda *_: pytest.fail("No reacquisition"),
            )
        assert caught.value.status_code == 409
    engine.dispose()


def test_complete_schema_matches_model_protections_and_absent_schema_creates_nothing(
    backup, tmp_path
):
    source, _, _, _ = backup
    with sqlite3.connect(source / "erp/minipilot.db") as db:
        assert validate_schema(db)
    empty = tmp_path / "empty.db"
    with sqlite3.connect(empty) as db:
        assert not validate_schema(db)
        assert not db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()


def test_offline_note_backup_import_has_no_application_or_sqlalchemy_side_effects():
    code = """
import builtins
original = builtins.__import__
def guarded(name,*args,**kwargs):
    if name=='sqlalchemy' or name.startswith('sqlalchemy.') or name in {'app.db','app.config','backend.app.db','backend.app.models'}:
        raise RuntimeError('Runtime import: '+name)
    return original(name,*args,**kwargs)
builtins.__import__=guarded
from app.services.note_backup import validate_history, collect_files
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "field", ["version", "bundle_size_bytes", "attachment_size_bytes"]
)
def test_original_capture_rejects_boolean_integer_fields(backup, field):
    source, _, _, _ = backup
    with sqlite3.connect(source / "erp/minipilot.db") as db:
        value = json.loads(
            db.execute("SELECT snapshot FROM project_note_imports").fetchone()[0]
        )
    if field == "attachment_size_bytes":
        value["attachments"][0]["size_bytes"] = True
    else:
        value[field] = True
    from backend.app.project_note_import_schemas import NoteImportCapture

    with pytest.raises(ValueError):
        NoteImportCapture.model_validate(value)
