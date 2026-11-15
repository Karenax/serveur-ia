"""OCR adds immutable, project-scoped evidence without rewriting retained bytes."""
import io
from pathlib import Path
import uuid

import pytest
from fastapi import HTTPException
from reportlab.pdfgen.canvas import Canvas

from app.db import engine, SessionLocal
from app.models import Project, Source, MemoryProjection
from app.source_library_models import LibraryItem, LibraryVersion
from app.services import library_ocr as ocr
from app.services.source_library import init_library_db, import_bytes, catalog
from app.services.settings_service import save_section


@pytest.fixture
def scan(tmp_path, monkeypatch):
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS', raising=False)
    init_library_db(engine)
    output = io.BytesIO()
    canvas = Canvas(output)
    canvas.drawString(30, 700, 'Reserve native : ne pas receptionner.')
    canvas.showPage()
    canvas.showPage()
    canvas.save()
    with SessionLocal() as db:
        save_section(db, 'foresight', {'enabled':True, 'mode':'network'})
        project = Project(code='OCR-'+uuid.uuid4().hex, name='Scan fictif')
        db.add(project)
        db.commit()
        result = import_bytes(db, project_id=project.id, provider='file', provider_key='scan.pdf',
            filename='scan.pdf', data=output.getvalue(), mime_type='application/pdf', storage=tmp_path)
        result.update(project_id=project.id, storage=tmp_path, original=Path(db.get(Source, result['source_id']).original_uri),
                      data=output.getvalue())
    monkeypatch.setattr(ocr, 'profile', lambda:{'engine':'test-only', 'language':'fr-FR'})
    monkeypatch.setattr(ocr, 'recognize_page', lambda path, page, *args:{'text':'1250 W ; ne pas valider.',
        'lines':[{'text':'1250 W ; ne pas valider.', 'words':[]}], 'width':2048, 'height':1536})
    return result


def test_ocr_preserves_native_page_old_evidence_and_version_and_enqueues_current(scan):
    with SessionLocal() as db:
        old = db.get(Source, scan['source_id'])
        original_artifacts = [(a.id, a.content_text, a.content_json) for a in old.artifacts]
        result = ocr.recognize_source(db, old.id, storage=scan['storage'])
        assert result['recognized_pages'] == 1 and result['extraction_status'] == 'ocr_extracted'
        new = db.get(Source, result['source_id'])
        assert new.id != old.id and old.source_metadata['superseded']
        assert [(a.id, a.content_text, a.content_json) for a in old.artifacts] == original_artifacts
        assert new.artifacts[0].content_text == original_artifacts[0][1]
        recognized = next(a for a in new.artifacts if a.content_json['physical_page'] == 2)
        assert recognized.content_text == '1250 W ; ne pas valider.'
        assert recognized.content_json['text_is_OCR'] and recognized.content_json['visual_review_required']
        assert db.get(LibraryVersion, scan['version_id']).source_id == old.id
        assert db.get(LibraryItem, scan['item_id']).current_source_id == new.id
        assert catalog(db, project_id=scan['project_id'])['items'][0]['source_id'] == new.id
        assert db.query(MemoryProjection).filter_by(source_id=new.id).count() == 1
        assert scan['original'].read_bytes() == scan['data']
        assert ocr.recognize_source(db, new.id, storage=scan['storage'])['replayed']
        with pytest.raises(HTTPException) as stale:
            ocr.recognize_source(db, old.id, storage=scan['storage'])
        assert stale.value.status_code == 409


def test_citation_download_serves_original_after_ocr(scan, monkeypatch):
    from app import config
    from app.routers.sources import raw_source

    monkeypatch.setattr(config, 'RAW_DIR', scan['storage'])
    with SessionLocal() as db:
        result = ocr.recognize_source(db, scan['source_id'], storage=scan['storage'])
        response = raw_source(result['source_id'], db)
        assert response.filename == 'scan.pdf'
        assert response.media_type == 'application/pdf'
        assert Path(response.path).read_bytes() == scan['data']


def test_cancelled_ocr_never_publishes_partial_evidence_and_keeps_original(scan, monkeypatch):
    with SessionLocal() as db:
        original = db.get(Source, scan['source_id'])
        evidence_before = [(a.id, a.content_text) for a in original.artifacts]
        source_count = db.query(Source).count()

        def cancel_during_page(*args):
            assert ocr.cancel_source(db, original.id)['cancel_requested']
            return {'text': 'Texte incomplet à conserver en reprise', 'lines': [], 'width': 100, 'height': 100}

        monkeypatch.setattr(ocr, 'recognize_page', cancel_during_page)
        with pytest.raises(HTTPException) as stopped:
            ocr.recognize_source(db, original.id, storage=scan['storage'])
        assert stopped.value.status_code == 409 and 'annulée' in stopped.value.detail
        assert db.query(Source).count() == source_count
        assert db.get(LibraryItem, scan['item_id']).current_source_id == original.id
        assert [(a.id, a.content_text) for a in original.artifacts] == evidence_before
        assert scan['original'].read_bytes() == scan['data']
        assert not ocr.cancel_source(db, original.id)['cancel_requested']


@pytest.mark.parametrize('case', ['reader', 'scope', 'tampered', 'outside', 'unavailable', 'replaced'])
def test_ocr_refuses_before_canonical_changes(scan, monkeypatch, tmp_path, case):
    if case == 'reader':
        monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    if case == 'scope':
        monkeypatch.setattr(ocr, 'require_brain', lambda pid: (_ for _ in ()).throw(HTTPException(404)))
    if case == 'tampered':
        scan['original'].write_bytes(scan['data']+b'changed')
    if case == 'unavailable':
        monkeypatch.setattr(ocr, 'profile', lambda: (_ for _ in ()).throw(ValueError('OCR indisponible')))
    with SessionLocal() as db:
        if case == 'replaced':
            def replace(*args):
                db.get(LibraryItem, scan['item_id']).current_source_id = None
                db.commit()
                return {'text':'1250 W', 'lines':[], 'width':100, 'height':100}
            monkeypatch.setattr(ocr, 'recognize_page', replace)
        with pytest.raises(HTTPException) as denied:
            ocr.recognize_source(db, scan['source_id'], storage=tmp_path/'other' if case == 'outside' else scan['storage'])
        assert denied.value.status_code == (403 if case == 'reader' else 404 if case == 'scope' else 409)
        assert not db.get(Source, scan['source_id']).source_metadata.get('superseded')
        assert db.query(Source).filter_by(project_id=scan['project_id']).count() == 1


def test_unreadable_page_is_not_reported_as_extracted(scan, monkeypatch):
    monkeypatch.setattr(ocr, 'recognize_page', lambda *args:{'text':'', 'lines':[], 'width':2048, 'height':1536})
    with SessionLocal() as db:
        result = ocr.recognize_source(db, scan['source_id'], storage=scan['storage'])
        assert result['recognized_pages'] == 0 and result['empty_pages'] == 1
        assert result['extraction_status'] == 'partially_extracted'
        assert db.get(LibraryItem, scan['item_id']).current_source_id == scan['source_id']


def test_interruption_keeps_current_binding_and_original(scan, monkeypatch):
    calls = []
    def fail(*args):
        calls.append(True)
        raise OSError('worker interrompu')
    monkeypatch.setattr(ocr, 'recognize_page', fail)
    with SessionLocal() as db:
        with pytest.raises(HTTPException):
            ocr.recognize_source(db, scan['source_id'], storage=scan['storage'])
        assert db.get(LibraryItem, scan['item_id']).current_source_id == scan['source_id']
        assert scan['original'].read_bytes() == scan['data']
    assert len(calls) == 1


def test_windows_ocr_handles_localized_startup_errors(monkeypatch):
    from types import SimpleNamespace

    def run(command, **options):
        assert command == ['powershell.exe', '-NoProfile', '-NonInteractive',
                           '-ExecutionPolicy', 'RemoteSigned', '-File', str(ocr.SCRIPT), '-Status']
        assert options['capture_output']
        assert 'encoding' not in options
        return SimpleNamespace(returncode=1, stdout=b'', stderr=b'Acc\x8as refus\x82')

    monkeypatch.setattr(ocr, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(ocr, 'subprocess', SimpleNamespace(run=run, CREATE_NO_WINDOW=0, DEVNULL=-3))
    with pytest.raises(ValueError, match='OCR Windows indisponible'):
        ocr.powershell('-Status')


def test_page_checkpoint_reuses_recognition_and_detects_corruption(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    from app.services import pdf_render
    settings = {'engine':'test-only', 'language':'fr-FR'}
    monkeypatch.setattr(pdf_render, 'runtime_python', lambda: Path('not-executed.exe'))
    renders = []
    def render(command, **kwargs):
        assert kwargs['stdin'] == ocr.subprocess.DEVNULL
        renders.append(command)
        Path(command[command.index('--output')+1]).write_bytes(b'fake-render')
        return SimpleNamespace(returncode=0, stdout=json.dumps({'source_sha256':'abc', 'physical_page':7}))
    monkeypatch.setattr(ocr.subprocess, 'run', render)
    recognitions = []
    monkeypatch.setattr(ocr, 'powershell', lambda *args:recognitions.append(args) or
        {'text':'1250 W', 'language':'fr-FR', 'lines':[], 'width':2048, 'height':1536})
    first = ocr.recognize_page(tmp_path/'original.pdf', 7, tmp_path, 'abc', settings)
    assert ocr.recognize_page(tmp_path/'original.pdf', 7, tmp_path, 'abc', settings) == first
    assert len(renders) == len(recognitions) == 1
    receipt = next(tmp_path.glob('ocr/*/result.json'))
    saved = json.loads(receipt.read_text())
    saved['result']['text'] = '2250 W'
    receipt.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match='incompatible'):
        ocr.recognize_page(tmp_path/'original.pdf', 7, tmp_path, 'abc', settings)
    assert receipt.exists() and len(recognitions) == 1
