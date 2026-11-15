"""Qualification counts and restored derived storage cannot widen authority."""
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import create_engine

from app.db import SessionLocal
from app.models import SourceArtifact
from app.services import fusion_index_metrics, meeting_session_backup, source_library


def test_incompatible_library_schema_fails_without_migration_writes(tmp_path):
    path = tmp_path / 'broken.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE foresight_library_items (id TEXT PRIMARY KEY)')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    engine = create_engine('sqlite:///' + path.as_posix())
    with pytest.raises(ValueError, match='incompatible'):
        source_library.init_library_db(engine)
    engine.dispose()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_restored_derived_jobs_and_native_journals_use_only_new_copy(tmp_path):
    output = tmp_path / 'restored'
    storage = output / 'storage'
    directory = storage / 'meeting-sessions' / 'native' / 'session'
    directory.mkdir(parents=True)
    chunk = directory / 'system-0.wav'
    chunk.write_bytes(b'audio preserved')
    journal = directory / 'system-0.json'
    journal.write_text(json.dumps({'kind': 'chunk', 'path': 'C:/old/meeting-sessions/native/session/system-0.wav',
        'sha256': hashlib.sha256(chunk.read_bytes()).hexdigest()}), encoding='utf-8')
    meeting_session_backup.relocate_derived_storage(output)
    assert Path(json.loads(journal.read_text(encoding='utf-8'))['path']) == chunk
    assert chunk.read_bytes() == b'audio preserved'
