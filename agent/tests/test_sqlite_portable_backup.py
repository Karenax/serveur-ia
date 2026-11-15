"""Real WAL snapshots, GC-independent standalone files and round-trip restore."""
from contextlib import closing
import gc
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from app.db_support import backup_sqlite
from app.services.backup import create_backup, restore_backup
from tests.test_project_note_archive_store import note_archive
from tests.test_project_document_archive import paired

__all__ = ['note_archive', 'paired']


@pytest.mark.parametrize('journal', ['wal', 'delete'])
def test_snapshot_has_no_sidecar_dependency_and_keeps_source_mode(tmp_path, journal):
    source, copied = tmp_path / 'source.sqlite', tmp_path / 'copy.sqlite'
    with closing(sqlite3.connect(source)) as writer:
        assert writer.execute('PRAGMA journal_mode=' + journal).fetchone()[0] == journal
        writer.execute('PRAGMA wal_autocheckpoint=0')
        writer.execute('CREATE TABLE retained(id INTEGER PRIMARY KEY, body BLOB)')
        writer.execute('INSERT INTO retained VALUES(1,?)', (b'Committed uncheckpointed value' * 300,))
        writer.commit()
        wal = Path(str(source) + '-wal')
        original_wal = hashlib.sha256(wal.read_bytes()).hexdigest() if wal.exists() else None
        enabled = gc.isenabled()
        gc.disable()
        try:
            backup_sqlite(source, copied)
            assert not Path(str(copied) + '-wal').exists()
            assert not Path(str(copied) + '-shm').exists()
            with closing(sqlite3.connect(copied.as_uri() + '?mode=ro&immutable=1', uri=True)) as reader:
                assert reader.execute('PRAGMA journal_mode').fetchone()[0] == 'delete'
                assert reader.execute('SELECT body FROM retained').fetchone()[0] == b'Committed uncheckpointed value' * 300
                assert reader.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert writer.execute('PRAGMA journal_mode').fetchone()[0] == journal
            assert original_wal == (hashlib.sha256(wal.read_bytes()).hexdigest() if wal.exists() else None)
        finally:
            if enabled:
                gc.enable()
            gc.collect()


def test_preexisting_destination_is_not_overwritten(tmp_path):
    source, copied = tmp_path / 'source.sqlite', tmp_path / 'copy.sqlite'
    source.write_bytes(b'Not opened')
    copied.write_bytes(b'Preserved existing destination')
    with pytest.raises(FileExistsError):
        backup_sqlite(source, copied)
    assert copied.read_bytes() == b'Preserved existing destination'


def test_source_and_destination_handles_close_on_backup_error(tmp_path, monkeypatch):
    original_connect = sqlite3.connect
    connections = []
    class Tracked(sqlite3.Connection):
        explicitly_closed = False
        def backup(self, target, *args, **kwargs):
            raise RuntimeError('Injected backup failure before any copied data')
        def close(self):
            self.explicitly_closed = True
            return super().close()
    def connect(*args, **kwargs):
        instance = original_connect(*args, factory=Tracked, **kwargs)
        connections.append(instance)
        return instance
    monkeypatch.setattr(sqlite3, 'connect', connect)
    with pytest.raises(RuntimeError, match='Injected backup failure'):
        backup_sqlite(tmp_path / 'source.sqlite', tmp_path / 'copy.sqlite')
    assert len(connections) == 2 and all(item.explicitly_closed for item in connections)


def test_coordinated_backup_of_live_WAL_indexes_remains_restorable_after_GC(note_archive, tmp_path):
    _, stores = note_archive
    source = stores['source']
    storage = tmp_path / 'storage'
    holders = []
    enabled = gc.isenabled()
    gc.disable()
    try:
        for name in ['eg2', 'MultiModal']:
            file = storage / name / 'index.db'
            file.parent.mkdir(parents=True)
            db = sqlite3.connect(file)
            holders.append(db)
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA wal_autocheckpoint=0')
            db.execute('CREATE TABLE retained(id INTEGER PRIMARY KEY, body TEXT)')
            db.execute('INSERT INTO retained VALUES(1,?)', (name + ' retained snapshot',))
            db.commit()
        output = tmp_path / 'backup'
        manifest = create_backup(output, source['brain_path'], source['home'], storage)
        assert not any(name.endswith(('-wal', '-shm')) for name in manifest['files'])
        assert not any(name.casefold().startswith('storage/multimodal/') for name in manifest['files'])
        # Simulate an older valid archive that still listed the retired index.
        old_index = output / 'storage/MultiModal/index.db'
        old_index.parent.mkdir()
        old_index.write_bytes(b'legacy index')
        manifest['files']['storage/MultiModal/index.db'] = hashlib.sha256(old_index.read_bytes()).hexdigest()
        (output / 'backup.json').write_text(json.dumps(manifest), encoding='utf-8')
    finally:
        for holder in holders:
            holder.close()
        if enabled:
            gc.enable()
        gc.collect()
    restored = tmp_path / 'restored'
    restore_backup(output, restored)
    assert not (restored / 'storage/MultiModal').exists()
    assert old_index.read_bytes() == b'legacy index'
    for name in ['eg2']:
        with closing(sqlite3.connect(restored / 'storage' / name / 'index.db')) as db:
            assert db.execute('SELECT body FROM retained').fetchone()[0] == name + ' retained snapshot'


def test_restore_keeps_original_pdf_for_both_ocr_and_pre_ocr_citations(note_archive, tmp_path, monkeypatch):
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app import config
    from app.models import Project, Source
    from app.routers.sources import raw_source
    from app.services import library_ocr, settings_service, source_library

    _, stores = note_archive
    source = stores['source']
    storage = tmp_path / 'storage'
    output = BytesIO()
    page = Canvas(output)
    page.showPage()
    page.save()
    content = output.getvalue()
    monkeypatch.setattr(library_ocr, 'profile', lambda: {'language': 'fr-FR'})
    monkeypatch.setattr(library_ocr, 'recognize_page', lambda *args: {
        'text': 'Pression nominale 318 kPa', 'lines': [], 'width': 1200, 'height': 420})
    source_library.init_library_db(source['brain'].kw['bind'])
    with source['brain']() as db:
        settings_service.save_section(db, 'foresight', {'enabled': True, 'mode': 'network'})
        project_id = db.query(Project.id).first()[0]
        initial = source_library.import_bytes(db, project_id=project_id, provider='file', provider_key='scan.pdf',
            filename='scan.pdf', data=content, mime_type='application/pdf', storage=storage / 'raw')
        recognized = library_ocr.recognize_source(db, initial['source_id'], storage=storage / 'raw')
        assert recognized['source_id'] != initial['source_id']
        original = Path(db.get(Source, initial['source_id']).original_uri)

    snapshot, restored = tmp_path / 'backup', tmp_path / 'restored'
    create_backup(snapshot, source['brain_path'], source['home'], storage)
    restore_backup(snapshot, restored)
    raw = restored / 'storage' / 'raw'
    monkeypatch.setattr(config, 'RAW_DIR', raw)
    engine = create_engine(f"sqlite:///{(restored / 'brain' / 'project_brain.db').as_posix()}")
    try:
        with Session(engine) as db:
            for source_id in (initial['source_id'], recognized['source_id']):
                restored_source = db.get(Source, source_id)
                assert Path(restored_source.original_uri) == raw / original.name
                assert restored_source.source_metadata['raw_path'] == restored_source.original_uri
                assert Path(raw_source(source_id, db).path).read_bytes() == content
    finally:
        engine.dispose()


def test_managed_client_documents_follow_restored_project(note_archive, tmp_path):
    _, stores = note_archive
    source = stores['source']
    erp_path = source['home'] / 'minipilot.db'
    root = tmp_path / 'clients'
    with closing(sqlite3.connect(erp_path)) as db, db:
        project_id = db.execute('SELECT id FROM projects LIMIT 1').fetchone()[0]
        folder = root / project_id
        folder.mkdir(parents=True)
        outside = tmp_path / 'external'
        db.executemany('INSERT INTO network_links (id,project_id,code,libelle,chemin,ordre,created_at) '
                       'VALUES (?,?,?,?,?,0,CURRENT_TIMESTAMP)', [
            ('managed', project_id, 'dossier_client_kiara', 'Dossier client Kiara', str(folder)),
            ('external', project_id, 'external', 'External', str(outside)),
        ])
    (folder / 'contrat.txt').write_bytes(b'Document client fictif')
    snapshot, restored = tmp_path / 'snapshot', tmp_path / 'restored'
    create_backup(snapshot, source['brain_path'], source['home'], tmp_path / 'storage', client_root=root)
    restore_backup(snapshot, restored)
    recovered = restored / 'dossiers-clients' / project_id
    assert (recovered / 'contrat.txt').read_bytes() == (folder / 'contrat.txt').read_bytes()
    with closing(sqlite3.connect(restored / 'erp/minipilot.db')) as db:
        assert dict(db.execute("SELECT id,chemin FROM network_links WHERE id IN ('managed','external')")) == {
            'managed': str(recovered), 'external': str(outside),
        }
