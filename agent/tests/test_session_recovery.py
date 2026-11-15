"""Capture exports and restored copies retain bytes, versions and original data."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import zipfile

import pytest

from app.db_support import backup_sqlite
from app.meeting_session_models import MeetingSession
from app.services import meeting_session_backup as recovery, session_export
from tests.test_meeting_sessions import stores, create, chunk, command, content

__all__ = ['stores']


def test_review_export_preserves_original_chunks_and_both_note_histories(stores):
    brain, _, pid, _ = stores
    with brain() as db:
        session = create(db)
        command(db, session['id'], 'notes', session['revision'], title='Décision', content=content('Ne pas supprimer les réserves'))
        row = db.get(MeetingSession, session['id'])
        command(db, row.id, 'assign-project', row.revision, project_id=pid)
        db.refresh(row)
        command(db, row.id, 'resume', row.revision)
        chunk(db, row.id)
        path = session_export.export(db, row.id)
        with zipfile.ZipFile(path) as bundle:
            manifest = json.loads(bundle.read('session.json'))
            assert manifest['staged_note_versions'][0]['plain_text'] == 'Ne pas supprimer les réserves'
            assert len(manifest['note_versions']) == 1
            assert manifest['session']['note']['version_id'] == manifest['note_versions'][0]['id']
            for name, binding in manifest['files'].items():
                assert hashlib.sha256(bundle.read(name)).hexdigest() == binding['sha256']


def test_offline_capture_manifest_relocates_and_stops_capture_only_in_new_copy(stores, tmp_path):
    from app.config import settings
    from app.services.settings_service import save_section
    brain, _, _, _ = stores
    with brain() as db:
        session = create(db)
        command(db, session['id'], 'resume', session['revision'])
        chunk(db, session['id'])
        save_section(db, 'foresight', {'enabled': True, 'proactive_enabled': True,
                                      'auto_enhancement_enabled': True, 'live_transcription_enabled': True})
        database = Path(db.get_bind().url.database)
    bindings = recovery.collect(database, settings.storage_dir)
    output = tmp_path / 'restored'
    output.mkdir()
    copied_database = output / 'brain.db'
    backup_sqlite(database, copied_database)
    files = {}
    for binding in bindings.values():
        target = output / binding['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(settings.storage_dir) / Path(binding['path']).relative_to('storage'), target)
        files[binding['path']] = binding['sha256']
    manifest = {'files': files, 'meeting_session_files': bindings}
    recovery.validate(copied_database, output, manifest)
    recovery.relocate(copied_database, output, bindings)
    with sqlite3.connect(copied_database) as db:
        assert db.execute('SELECT state FROM meeting_sessions').fetchone()[0] == 'interrupted'
        assert db.execute('SELECT storage_path FROM meeting_session_chunks').fetchone()[0].startswith(str(output))
        restored_settings = json.loads(db.execute("SELECT value FROM app_settings WHERE key='foresight'").fetchone()[0])
        assert all(restored_settings[key] is False for key in
                   ('enabled', 'proactive_enabled', 'auto_enhancement_enabled', 'live_transcription_enabled'))
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT state FROM meeting_sessions').fetchone()[0] == 'recording'
    (output / next(iter(bindings.values()))['path']).write_bytes(b'truncated')
    with pytest.raises(ValueError, match='tronqué'):
        recovery.validate(copied_database, output, manifest)


def test_global_chat_flags_changed_source_after_generation(stores):
    from app.models import Source, SourceArtifact
    from app.services.chat_freshness import freeze, finalize
    brain, _, _, bid = stores
    with brain() as db:
        source = Source(project_id=bid, source_type='document', status='resolved', original_uri='fixture.txt', sha256='9' * 64)
        db.add(source)
        db.flush()
        artifact = SourceArtifact(source_id=source.id, kind='text', content_text='Diamètre 50 mm', content_json={'physical_page': 3})
        db.add(artifact)
        db.commit()
        metadata = freeze(db, {'citations': [{'source_id': source.id, 'excerpt': 'Diamètre 50 mm'}], 'warnings': []})
        assert metadata['citations'][0]['locator']['physical_page'] == 3
        artifact.content_text = 'Diamètre 80 mm'
        db.commit()
        assert finalize(db, metadata)['stale']
