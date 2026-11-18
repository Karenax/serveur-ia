"""Private notes and embedded images survive an isolated coordinated backup."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from PIL import Image
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db_support import configure_sqlite
from app.services.backup import create_backup, restore_backup, verify_backup
from backend.app.db import Base
from backend.app.personal_note_models import PersonalNote, PersonalNoteImage, PersonalNoteVersion
from backend.app.project_note_schemas import NotePaste
from backend.app.services import note_clipboard, personal_notes
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_notes_core as core
from tests.test_project_document_archive import paired
from tests.test_project_note_archive_store import note_archive, switch

__all__ = ['paired', 'note_archive']


@pytest.fixture
def private_note(note_archive, tmp_path, monkeypatch):
    _, stores = note_archive
    source = stores['source']
    switch(monkeypatch, source)
    engine = source['erp'].kw['bind']
    Base.metadata.create_all(engine, tables=[PersonalNote.__table__, PersonalNoteVersion.__table__, PersonalNoteImage.__table__])
    screenshot = BytesIO()
    Image.new('RGB', (6, 4), 'blue').save(screenshot, format='PNG')
    image = screenshot.getvalue()
    command = NotePaste(command_id=core.command(), title='Note privée fictive', expected_revision=0,
                        content=core.rich(), attachment_ids=[], insert_at=2)
    with source['erp']() as db, operator_context(Operator('fixture-owner', 'owner')):
        result = personal_notes.save(db, None, command, image=note_clipboard.read_image('capture.png', BytesIO(image)))
        db.commit()
    storage = tmp_path / 'brain-storage'
    storage.mkdir()
    return source, storage, result['note'], image


def test_restoration_preserves_private_note_versions_image_and_owner(private_note, tmp_path):
    source, storage, note, image = private_note
    snapshot, restored = tmp_path / 'snapshot', tmp_path / 'restored'
    create_backup(snapshot, source['brain_path'], source['home'], storage)
    assert verify_backup(snapshot)['status'] == 'verified'
    encrypted, extracted = tmp_path / 'notes.kiara-agent', tmp_path / 'extracted'
    extracted.mkdir()
    script = '''
import sys
sys.path[:0] = [sys.argv[4], sys.argv[5]]
from agent_archive import write_archive, extract_archive
write_archive(sys.argv[1], sys.argv[2], 'phrase fictive de recette 2026')
extract_archive(sys.argv[2], sys.argv[3], 'phrase fictive de recette 2026')
'''
    root = Path(__file__).resolve().parents[2]
    subprocess.run([sys.executable, '-c', script, str(snapshot), str(encrypted), str(extracted),
                    str(root / 'lanceur'), str(root / 'shared')],
                   check=True, capture_output=True, timeout=60)
    assert b'Note priv\xc3\xa9e fictive' not in encrypted.read_bytes()
    restore_backup(extracted, restored)
    engine = create_engine('sqlite:///' + (restored / 'erp/minipilot.db').as_posix())
    configure_sqlite(engine)
    try:
        with sessionmaker(bind=engine)() as db, operator_context(Operator('fixture-owner', 'owner')):
            saved = personal_notes.read(db, note['id'])
            assert saved == note
            restored_image, _ = personal_notes.read_image(db, note['id'], note['attachment_ids'][0])
            assert restored_image == image
        with sessionmaker(bind=engine)() as db, operator_context(Operator('different-owner', 'owner')):
            assert personal_notes.listing(db, '', 30, 0)['total'] == 0
    finally:
        engine.dispose()


def test_backup_refuses_corrupt_private_image_without_changing_source(private_note, tmp_path):
    source, storage, note, image = private_note
    corrupted = bytes([image[0] ^ 1]) + image[1:]
    with sqlite3.connect(source['erp_path']) as db:
        db.execute('UPDATE personal_note_images SET data=? WHERE id=?', (corrupted, note['attachment_ids'][0]))
    snapshot = tmp_path / 'must-not-be-verified'
    with pytest.raises(ValueError, match='[Nn]ote'):
        create_backup(snapshot, source['brain_path'], source['home'], storage)
    with sqlite3.connect(source['erp_path']) as db:
        assert db.execute('SELECT data FROM personal_note_images WHERE id=?', (note['attachment_ids'][0],)).fetchone()[0] == corrupted


def test_restore_refuses_rehashed_corrupt_private_image_before_destination(private_note, tmp_path):
    source, storage, note, image = private_note
    snapshot, restored = tmp_path / 'snapshot', tmp_path / 'must-not-restore'
    create_backup(snapshot, source['brain_path'], source['home'], storage)
    database = snapshot / 'erp/minipilot.db'
    with sqlite3.connect(database) as db:
        db.execute('UPDATE personal_note_images SET data=? WHERE id=?', (bytes([image[0] ^ 1]) + image[1:], note['attachment_ids'][0]))
    manifest_path = snapshot / 'backup.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['files']['erp/minipilot.db'] = sha256(database.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='[Nn]ote'):
        verify_backup(snapshot)
    with pytest.raises(ValueError, match='[Nn]ote'):
        restore_backup(snapshot, restored)
    assert not restored.exists()
