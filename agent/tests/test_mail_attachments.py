"""Mail-only attachment facts, persistent vectors and classification safety."""
import asyncio
from email.message import EmailMessage
import hashlib
from io import BytesIO
from pathlib import Path
import uuid
from zipfile import ZipFile

import pytest

from app.config import settings
from app.db import SessionLocal
from app.models import MemoryDatasetMapping, MemoryProjection, Project, Source, SourceArtifact
from app.services import mail_attachments
from app.services.eg2_memory import EG2MemoryAdapter
from app.services.mail_attachment_extraction import _extract_local, extract_attachment
from app.services.projections import enqueue, process


class Channel:
    profile = 'attachments-test'
    model = 'test'
    dimensions = 2

    def __init__(self):
        self.documents = []

    async def embed(self, texts, query=False):
        if not query:
            self.documents.extend(texts)
        return [[1.0, 0.0] if '7439' in text else [0.0, 1.0] for text in texts]


def seed(*, filename='devis.txt', content=b'Prix exclusif en piece jointe : 7439 euros', status='resolved'):
    msg = EmailMessage()
    msg['From'] = 'supplier@example.com'
    msg['Subject'] = 'Le document est joint'
    msg.set_content('Consulter le devis joint.')
    msg.add_attachment(content, maintype='application', subtype='octet-stream', filename=filename)
    raw = msg.as_bytes()
    digest = hashlib.sha256(raw + uuid.uuid4().bytes).hexdigest()
    # Make each message distinct, and keep the exact original hash.
    msg['Message-ID'] = f'<{digest}@test>'
    raw = msg.as_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    (Path(settings.storage_dir) / 'raw' / (digest + '.eml')).write_bytes(raw)
    with SessionLocal() as db:
        projects = [Project(code=uuid.uuid4().hex, name=name) for name in ('A', 'B')]
        db.add_all(projects)
        db.flush()
        source = Source(project_id=projects[0].id, source_type='email', status=status,
            original_uri='old://path-is-irrelevant', sha256=digest,
            source_metadata={'subject': str(msg['Subject']), 'attachments': [{'filename': filename}]})
        db.add(source)
        db.flush()
        db.add(SourceArtifact(source_id=source.id, kind='body_text', content_text='Consulter le devis joint.'))
        db.commit()
        return source.id, [p.id for p in projects], raw


def test_attachment_only_fact_is_embedded_in_parent_project_and_replay_is_idempotent(tmp_path):
    async def run():
        sid, projects, raw = seed()
        channel = Channel()
        adapter = EG2MemoryAdapter(SessionLocal, channel=channel, path=tmp_path / 'index.db')
        with SessionLocal() as db:
            enqueue(db, projects[0], 'evidence', source_id=sid)
            db.query(MemoryDatasetMapping).filter_by(project_id=projects[0]).update({'engine': 'eg2'})
            db.commit()
            assert (await process(db, adapter, projection_ids=[db.query(MemoryProjection).filter_by(source_id=sid).one().id]))['indexed'] == 1
            attachment = db.query(SourceArtifact).filter_by(source_id=sid, kind='attachment_text').one()
            assert '7439' in attachment.content_text
            assert attachment.content_json['filename'] == 'devis.txt'
            assert attachment.content_json['attachment_index'] == 0
            assert not await mail_attachments.prepare(db, db.get(Source, sid))
            assert db.query(SourceArtifact).filter_by(source_id=sid).count() == 2
            source = db.get(Source, sid)
            assert (Path(settings.storage_dir) / 'raw' / (source.sha256 + '.eml')).read_bytes() == raw
        assert any('7439' in text for text in channel.documents)
        assert not await adapter.recall(projects[1], '7439 euros', ['evidence'])
        assert any('7439' in hit['text'] for hit in await adapter.recall(projects[0], '7439 euros', ['evidence']))
    asyncio.run(run())


def test_reclassification_during_extraction_cannot_publish_to_old_project(monkeypatch):
    sid, projects, _ = seed()
    original_scan = mail_attachments._scan

    def changed(*args):
        records = original_scan(*args)
        with SessionLocal() as other:
            other.get(Source, sid).project_id = projects[1]
            other.commit()
        return records

    monkeypatch.setattr(mail_attachments, '_scan', changed)
    with SessionLocal() as db:
        assert not asyncio.run(mail_attachments.prepare(db, db.get(Source, sid)))
        assert not db.query(SourceArtifact).filter_by(source_id=sid, kind='attachment_text').count()
        assert db.get(Source, sid).project_id == projects[1]


def test_missing_original_fails_with_classification_and_body_preserved():
    sid, projects, _ = seed()
    with SessionLocal() as db:
        source = db.get(Source, sid)
        (Path(settings.storage_dir) / 'raw' / (source.sha256 + '.eml')).unlink()
        with pytest.raises(ValueError, match='indisponible'):
            asyncio.run(mail_attachments.prepare(db, source))
        assert source.status == 'resolved' and source.project_id == projects[0]
        assert db.query(SourceArtifact).filter_by(source_id=sid, kind='body_text').one().content_text


def test_unsupported_and_corrupt_files_have_status_without_false_text(tmp_path):
    assert extract_attachment(b'video', 'film.mp4', 'video/mp4', tmp_path)[0]['status'] == 'unsupported'
    sid, _, _ = seed(filename='bad.pdf', content=b'not a pdf')
    with SessionLocal() as db:
        asyncio.run(mail_attachments.prepare(db, db.get(Source, sid)))
        artifact = db.query(SourceArtifact).filter_by(source_id=sid, kind='attachment_status').one()
        assert artifact.content_json['extraction_status'] == 'failed'
        assert not artifact.content_text
        assert not db.get(Source, sid).source_metadata['attachment_extraction']['complete']


def test_pending_and_discarded_mails_are_never_scanned(monkeypatch):
    monkeypatch.setattr(mail_attachments, '_scan', lambda *a: pytest.fail('unclassified content scanned'))
    for status in ('resolution_pending', 'discarded'):
        sid, _, _ = seed(status=status)
        with SessionLocal() as db:
            assert not asyncio.run(mail_attachments.prepare(db, db.get(Source, sid)))


def test_office_and_archive_provenance_and_zip_limits(tmp_path):
    from openpyxl import Workbook
    workbook = Workbook()
    workbook.active.title = 'Prix'
    workbook.active.append(['Référence', 'Montant'])
    workbook.active.append(['RE-12', 7439])
    workbook.active.append([None, 'Première cellule vide'])
    stream = BytesIO()
    workbook.save(stream)
    items = extract_attachment(stream.getvalue(), 'devis.xlsx', 'application/octet-stream', tmp_path)
    assert items[0]['locator'] == {'sheet': 'Prix', 'range': 'A1:B3'}
    assert 'B2=7439' in items[0]['text']
    stream = BytesIO()
    with ZipFile(stream, 'w') as archive:
        archive.writestr('../../outside.txt', 'Archive only fact 7439')
        archive.writestr('binary.exe', b'not executable')
    items = extract_attachment(stream.getvalue(), 'pieces.zip', 'application/zip', tmp_path)
    assert items[0]['locator']['archive_member'] == '../../outside.txt'
    assert '7439' in items[0]['text']
    assert items[1]['status'] == 'unsupported'
    assert not (tmp_path.parent / 'outside.txt').exists()
    stream = BytesIO()
    with ZipFile(stream, 'w') as archive:
        for index in range(201):
            archive.writestr(f'{index}.txt', 'small')
    path = tmp_path / 'many.zip'
    path.write_bytes(stream.getvalue())
    with pytest.raises(ValueError, match='volumineuse'):
        _extract_local(path, path.name)


def test_ocr_text_is_indexable_and_empty_image_is_explicit(tmp_path, monkeypatch):
    from app.services import library_ocr
    from app.services.mail_attachment_extraction import _recognize
    monkeypatch.setattr(library_ocr, 'profile', lambda: {'engine': 'windows-ocr', 'language': 'fr-FR'})
    monkeypatch.setattr(library_ocr, 'powershell', lambda *a: {'text': 'Cote technique 7439 mm'})
    path = tmp_path / 'image.png'
    from PIL import Image
    Image.new('RGB', (100, 100)).save(path)
    items = [{'text': '', 'status': 'ocr_required', 'locator': {'image': True}}]
    _recognize(items, path, tmp_path)
    assert items[0]['status'] == 'extracted' and '7439' in items[0]['text']
    assert items[0]['locator']['ocr']['engine'] == 'windows-ocr'


def test_appending_evidence_reuses_body_vectors_but_profile_change_does_not(tmp_path):
    async def run():
        channel = Channel()
        adapter = EG2MemoryAdapter(channel=channel, path=tmp_path / 'index.db')
        await adapter.remember_evidence('p', 'Body unchanged', {'source_id': 's'})
        channel.documents.clear()
        await adapter.remember_evidence('p', 'Body unchanged\n\nAttachment only 7439', {'source_id': 's'})
        assert channel.documents == ['Attachment only 7439']
        channel.documents.clear()
        channel.profile = 'different-profile'
        await adapter.remember_evidence('p', 'Body unchanged\n\nAttachment only 7439', {'source_id': 's'})
        assert channel.documents == ['Body unchanged', 'Attachment only 7439']
    asyncio.run(run())


def test_partial_embedding_failure_reuses_completed_batches_on_retry(tmp_path):
    class Unreliable(Channel):
        batch_size = 1
        fail = True

        async def embed(self, texts, query=False):
            if self.fail and texts == ['Final attachment']:
                raise RuntimeError('remote unavailable')
            return await super().embed(texts, query=query)

    async def run():
        channel = Unreliable()
        adapter = EG2MemoryAdapter(channel=channel, path=tmp_path / 'index.db')
        with pytest.raises(RuntimeError):
            await adapter.remember_evidence('a', 'First attachment\n\nFinal attachment', {'source_id': 's'})
        assert (await adapter.health())['passages'] == 0
        channel.fail = False
        channel.documents.clear()
        await adapter.remember_evidence('a', 'First attachment\n\nFinal attachment', {'source_id': 's'})
        assert channel.documents == ['Final attachment']
        channel.documents.clear()
        await adapter.remember_evidence('b', 'First attachment\n\nFinal attachment', {'source_id': 'other'})
        assert not channel.documents
    asyncio.run(run())


def test_unsupported_attachment_status_does_not_invalidate_existing_body_vectors(tmp_path):
    from app.services.current_evidence import current_contents

    async def run():
        sid, projects, _ = seed(filename='movie.mp4', content=b'unsupported video')
        adapter = EG2MemoryAdapter(SessionLocal, channel=Channel(), path=tmp_path / 'index.db')
        with SessionLocal() as db:
            before = current_contents(db, [projects[0]])[sid]
            await adapter.remember_evidence(projects[0], before, {'source_id': sid})
            assert not await mail_attachments.prepare(db, db.get(Source, sid))
            assert current_contents(db, [projects[0]])[sid] == before
        assert await adapter.recall(projects[0], 'devis', ['evidence'])
    asyncio.run(run())


def test_archive_image_receives_ocr_with_member_provenance(tmp_path, monkeypatch):
    from app.services import library_ocr
    from PIL import Image
    monkeypatch.setattr(library_ocr, 'profile', lambda: {'engine': 'windows-ocr', 'language': 'fr-FR'})
    monkeypatch.setattr(library_ocr, 'powershell', lambda *a: {'text': 'Archive image 7439'})
    picture = BytesIO()
    Image.new('RGB', (100, 100)).save(picture, format='PNG')
    stream = BytesIO()
    with ZipFile(stream, 'w') as archive:
        archive.writestr('scans/plan.png', picture.getvalue())
    items = extract_attachment(stream.getvalue(), 'scans.zip', 'application/zip', tmp_path)
    assert items[0]['status'] == 'extracted'
    assert items[0]['text'] == 'Archive image 7439'
    assert items[0]['locator']['archive_chain'] == ['scans/plan.png']


def test_complete_html_attachment_is_text_only_and_office_images_have_ocr_locators(tmp_path):
    html = b'<!DOCTYPE html><html><head><script>secret()</script></head><body><p>Fact 7439</p></body></html>'
    items = extract_attachment(html, 'guide.html', 'text/html', tmp_path)
    assert items[0]['text'] == 'Fact 7439'
    stream = BytesIO()
    with ZipFile(stream, 'w') as archive:
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
        archive.writestr('word/media/image1.png', b'picture')
    path = tmp_path / 'photo.docx'
    path.write_bytes(stream.getvalue())
    items = _extract_local(path, path.name)
    assert items[0]['status'] == 'empty'
    assert items[1]['status'] == 'ocr_required'
    assert items[1]['locator']['archive_chain'] == ['word/media/image1.png']


def test_sparse_sheet_formatting_does_not_count_as_extracted_data(tmp_path):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    workbook = Workbook()
    workbook.active['B2'] = 7439
    workbook.active['Z10000'].font = Font(bold=True)
    stream = BytesIO()
    workbook.save(stream)
    items = extract_attachment(stream.getvalue(), 'formatted.xlsx', 'application/octet-stream', tmp_path)
    assert 'B2=7439' in items[0]['text']


def test_pdf_parser_failure_uses_existing_isolated_renderer(tmp_path, monkeypatch):
    from app.services import document_sandbox, library_extraction, pdf_render
    path = tmp_path / 'restricted.pdf'
    path.write_bytes(b'fixture')
    python = tmp_path / 'python.exe'
    python.write_bytes(b'fixture')
    def unavailable(*args):
        raise ValueError('cryptography is required for AES')
    monkeypatch.setattr(library_extraction, '_extract_local', unavailable)
    monkeypatch.setattr(pdf_render, 'runtime_python', lambda: python)
    def fallback(original, filename, kind, **kwargs):
        assert original == path and kind == 'mail_pdfium' and kwargs['python'] == python
        return [{'text': 'Supplier PDF 7439', 'status': 'extracted',
                 'kind': 'document_page', 'locator': {'physical_page': 1, 'extractor': 'pypdfium2'}}]
    monkeypatch.setattr(document_sandbox, 'extract', fallback)
    assert '7439' in _extract_local(path, path.name)[0]['text']


def test_old_success_receipt_is_revisited_when_interpretation_improves():
    sid, _, _ = seed()
    with SessionLocal() as db:
        source = db.get(Source, sid)
        source.source_metadata = {**source.source_metadata, 'attachment_extraction': {
            'version': mail_attachments.VERSION, 'complete': True, 'revision': 1}}
        db.commit()
        assert asyncio.run(mail_attachments.prepare(db, source))
        assert db.get(Source, sid).source_metadata['attachment_extraction']['revision'] == 2
