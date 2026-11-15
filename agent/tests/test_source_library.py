"""Imports retain bytes/versions, isolate projects, and preserve canonical state."""
import io
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from openpyxl import Workbook
from sqlalchemy import event

from app.db import SessionLocal, engine
from app.models import MemoryProjection, Project, Source, SourceArtifact
from app.services.source_library import init_library_db, import_bytes, catalog, update_labels, actual_file_format
from app.services.library_extraction import extract
from app.services.source_connectors import public_url, calendar_preview


@pytest.fixture
def library(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENT_OPERATOR_PROJECT_IDS", raising=False)
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "owner")
    init_library_db(engine)
    with SessionLocal() as db:
        projects = [Project(code="LIB-" + uuid.uuid4().hex, name="Selected imports") for _ in range(2)]
        db.add_all(projects)
        db.commit()
        ids = [p.id for p in projects]
    return ids, tmp_path / "raw"


def add(db, library, data=b"Reserve initiale 350 lux", project=0):
    return import_bytes(db, project_id=library[0][project], provider="file", provider_key="fichier.txt",
                        filename="fichier.txt", data=data, storage=library[1])


def test_same_text_in_different_projects_and_replayed_old_revision(library):
    with SessionLocal() as db:
        first = add(db, library)
        other = add(db, library, project=1)
        assert first["source_id"] != other["source_id"]
        changed = add(db, library, b"Reserve modifiee 400 lux")
        replay = add(db, library)
        assert replay["replayed"] and not replay["current"]
        current = catalog(db, project_id=library[0][0])
        assert [item["source_id"] for item in current["items"]] == [changed["source_id"]]
        assert db.get(Source, first["source_id"]).source_metadata["superseded"]
        assert len(list(library[1].glob("*.txt"))) == 3


def test_labels_survive_new_import_and_do_not_expand_scope(library, monkeypatch):
    with SessionLocal() as db:
        first = add(db, library)
        update_labels(db, first["source_id"], ["Site A", "Site A"])
        changed = add(db, library, b"Version deux")
        assert catalog(db, project_id=library[0][0], label="Site A")["items"][0]["source_id"] == changed["source_id"]
        monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", "[]")
        assert not catalog(db)["items"]
        with pytest.raises(HTTPException) as denied:
            update_labels(db, changed["source_id"], ["Public"])
        assert denied.value.status_code == 404


def test_partial_import_failure_keeps_original_visible(library):
    with SessionLocal() as db:
        result = import_bytes(db, project_id=library[0][0], provider="file", provider_key="bad.pdf",
                              filename="bad.pdf", data=b"not a pdf", storage=library[1])
        assert result["extraction_status"] == "failed"
        assert catalog(db, project_id=library[0][0])["items"][0]["extraction_status"] == "failed"
        assert next(library[1].glob("*.pdf")).read_bytes() == b"not a pdf"


@pytest.mark.parametrize("mime,filename,kind,origin,expected", [
    ("application/pdf", "wrong.png", "document", None, "pdf"),
    ("image/png", "wrong.pdf", "document", None, "png"),
    ("IMAGE/JPEG; charset=binary", "photo.jpg", "document", None, "jpeg"),
    ("text/plain", "fiche.txt", "document", None, "txt"),
    ("text/plain", "fiche.csv", "document", None, "csv"),
    ("text/plain", "fiche.md", "document", None, "md"),
    ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "devis", "document", None, "docx"),
    ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "devis", "document", None, "xlsx"),
    ("application/vnd.ms-excel.sheet.macroenabled.12", "devis.xlsm", "document", None, "xlsm"),
    ("application/vnd.ms-excel", "devis", "document", None, "xls"),
    ("text/csv", "devis", "document", None, "csv"),
    ("audio/wav", "reunion", "meeting", None, "wav"),
    ("audio/mpeg", "reunion", "meeting", None, "mp3"),
    ("audio/mp4", "reunion", "document", None, "m4a"),
    ("application/octet-stream", "PLAN.PDF", "document", None, "pdf"),
    (None, "plan.png", "document", None, "png"),
    ("application/x-custom", "plan.pdf", "document", None, None),
    (None, "plan.bin", "document", None, None),
    (None, None, "document", None, None),
    ("application/pdf", "titre.pdf", "document", "erp_note", None),
    (None, "titre.pdf", "document", "published_erp_note", None),
    ("application/vnd.agent.note+json", "titre.pdf", "document", None, None),
    ("application/pdf", "titre.pdf", "note", None, None),
    (None, "transcription.pdf", "meeting", None, None),
    (None, "audio.WAV", "meeting", None, "wav"),
    ("text/plain", "titre.pdf", "meeting", None, None),
    (None, "piece.pdf", "email", None, None),
    ("message/rfc822", "mail", "email", None, "eml"),
])
def test_actual_format_uses_mime_then_only_compatible_filename(mime, filename, kind, origin, expected):
    assert actual_file_format(kind, {"filename": filename, "origin_kind": origin}, mime) == expected


def test_file_format_is_independent_of_source_kind_and_filtered_before_page_and_rights(library, monkeypatch):
    with SessionLocal() as db:
        ids = []
        for project, filename, mime in [(0, "plan.pdf", "application/pdf"), (0, "plan.png", "image/png"),
                (0, "plan.txt", "text/plain"), (1, "secret.pdf", "application/pdf")]:
            source = Source(project_id=library[0][project], source_type="document", status="resolved",
                original_uri="unused", sha256=uuid.uuid4().hex * 2, mime_type=mime,
                source_metadata={"filename": filename})
            db.add(source)
            db.flush()
            ids.append(source.id)
        db.commit()
        legacy = catalog(db, project_id=library[0][0], source_type="document")
        assert legacy["total"] == 3 and {v["file_format"] for v in legacy["items"]} == {"pdf", "png", "txt"}
        pdf = catalog(db, project_id=library[0][0], source_type="document", file_format="pdf", limit=1)
        assert pdf["total"] == 1 and pdf["items"][0]["source_id"] == ids[0] and not pdf["has_next"]
        next_page = catalog(db, project_id=library[0][0], file_format="pdf", offset=1, limit=1)
        assert next_page["total"] == 1 and next_page["items"] == []
        monkeypatch.setattr("app.services.project_access.brain_ids", lambda: frozenset({library[0][0]}))
        accessible = catalog(db, file_format="pdf")
        assert accessible["total"] == 1 and accessible["items"][0]["source_id"] == ids[0]
        with pytest.raises(HTTPException) as denied:
            catalog(db, project_id=library[0][1], file_format="pdf")
        assert denied.value.status_code == 404


def test_format_route_rejects_unknown_value_and_keeps_legacy_type_protocol(library):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.db import get_db
    from app.routers.source_library import router
    app = FastAPI()
    app.include_router(router)

    def isolated_database():
        with SessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = isolated_database
    with SessionLocal() as db:
        result = add(db, library)
    with TestClient(app) as client:
        url = "/api/v1/workspace/sources"
        invalid = client.get(url, params={"file_format": "not-a-format"})
        assert invalid.status_code == 422
        assert any(v["loc"] == ["query", "file_format"] for v in invalid.json()["detail"])
        legacy = client.get(url, params={"project_id": library[0][0], "source_type": "document"})
        assert legacy.status_code == 200 and legacy.json()["items"][0]["source_id"] == result["source_id"]
        text = client.get(url, params={"project_id": library[0][0], "source_type": "document", "file_format": "txt"})
        assert text.status_code == 200 and text.json()["total"] == 1
        assert text.json()["items"][0]["file_format"] == "txt"
        assert client.get(url, params={"project_id": library[0][0], "file_format": "pdf"}).json()["total"] == 0


@pytest.mark.parametrize("source_count", [1, 80])
def test_catalog_query_count_is_bounded_and_never_loads_artifact_contents(library, source_count):
    project_id = library[0][0]
    with SessionLocal() as db:
        ids = []
        for ordinal in range(source_count):
            source = Source(project_id=project_id, source_type="document", status="resolved",
                original_uri="unused", sha256=uuid.uuid4().hex * 2,
                source_metadata={"filename": f"Document {ordinal:03}", "labels": [f"Label {ordinal % 2}"]})
            db.add(source)
            db.flush()
            ids.append(source.id)
            if ordinal % 2 == 0:
                db.add(SourceArtifact(source_id=source.id, kind="body_text", content_text="heavy text " * 10000,
                    content_json={"large": "heavy JSON " * 10000}))
        offset = max(0, source_count - 3)
        db.add(MemoryProjection(project_id=project_id, source_id=ids[offset], purpose="evidence",
            content_hash="a" * 64, status="pending", last_error="heavy error " * 10000))
        db.commit()
        db.expunge_all()
        statements = []

        def capture(connection, cursor, statement, parameters, context, many):
            statements.append(statement.lower())

        event.listen(engine, "before_cursor_execute", capture)
        try:
            result = catalog(db, project_id=project_id, sort="title_asc", offset=offset, limit=2)
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert result["total"] == source_count
        assert [row["source_id"] for row in result["items"]] == ids[offset:offset + 2]
        assert result["has_next"] == (offset + 2 < source_count)
        assert result["labels"] == (["Label 0"] if source_count == 1 else ["Label 0", "Label 1"])
        assert result["items"][0]["index_status"] == "pending"
        for ordinal, row in enumerate(result["items"], start=offset):
            assert row["extraction_status"] == ("extracted" if ordinal % 2 == 0 else "pending")
        assert len(statements) <= 3
        assert sum("source_artifacts" in statement for statement in statements) == 1
        assert not any("source_artifacts.content_text" in statement or "source_artifacts.content_json" in statement
                       or "memory_projections.last_error" in statement for statement in statements)


def test_catalog_keeps_canonical_note_head_fresh_and_projection_pending_unique(library):
    from backend.app.db import SessionLocal as ERP
    from backend.app.models import BrainLink, Project as ERPProject
    from backend.app.project_note_models import NoteVersion
    from backend.app.project_note_schemas import NoteCreate, NoteSave
    from backend.app.services import project_notes

    project_id = library[0][0]
    with ERP() as erp:
        project = ERPProject(code="LIB-NOTE-" + uuid.uuid4().hex, title="Canonical catalogue note")
        erp.add(project)
        erp.flush()
        erp.add(BrainLink(project_id=project.id, brain_project_id=project_id))
        first = project_notes.create_note(erp, project.id,
            NoteCreate(command_id=str(uuid.uuid4()), title="Version initiale"))["note"]
        erp.commit()
        erp_project_id = project.id
        first_sha = erp.get(NoteVersion, first["version_id"]).sha256
    with SessionLocal() as db:
        source = Source(project_id=project_id, source_type="document", status="resolved",
            original_uri="agent-note://test", sha256=uuid.uuid4().hex * 2,
            source_metadata={"origin_kind": "erp_note", "erp_project_id": erp_project_id, "note_id": first["id"],
                "note_version_id": first["version_id"], "note_revision": first["revision"], "note_sha256": first_sha,
                "subject": first["title"], "labels": ["Note suivie"]})
        db.add(source)
        db.commit()
        source_id = source.id
        result = catalog(db, project_id=project_id)
        assert result["total"] == 1 and result["items"][0]["source_id"] == source_id
        assert result["items"][0]["file_format"] is None
        assert catalog(db, project_id=project_id, source_type="note", file_format="unknown")["total"] == 1
        assert catalog(db, project_id=project_id, file_format="pdf")["total"] == 0
        with ERP() as erp:
            changed = project_notes.save_note(erp, erp_project_id, first["id"],
                NoteSave(command_id=str(uuid.uuid4()), expected_revision=1, title="Version récente"))["note"]
            erp.commit()
            changed_sha = erp.get(NoteVersion, changed["version_id"]).sha256
        pending = catalog(db, project_id=project_id)
        assert pending["total"] == 1
        assert pending["items"][0]["source_id"] is None
        assert pending["items"][0]["version_id"] == changed["version_id"]
        assert pending["items"][0]["title"] == "Version récente"
        assert pending["items"][0]["status"] == "projection_pending"
        assert pending["items"][0]["file_format"] is None
        assert catalog(db, project_id=project_id, source_type="note", file_format="unknown")["total"] == 1
        assert catalog(db, project_id=project_id, file_format="pdf")["total"] == 0
        assert not catalog(db, project_id=project_id, label="Note suivie")["items"]
        source.source_metadata = {**source.source_metadata, "subject": changed["title"],
            "note_version_id": changed["version_id"], "note_revision": changed["revision"], "note_sha256": changed_sha}
        db.commit()
        fresh = catalog(db, project_id=project_id, label="Note suivie")
        assert fresh["total"] == 1 and fresh["items"][0]["source_id"] == source_id
        assert fresh["items"][0]["version_id"] == changed["version_id"]
        assert catalog(db, project_id=project_id)["total"] == 1


def test_tableur_has_sheet_and_cell_locators(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Devis"
    sheet.append(["Article", "Quantite"])
    sheet.append(["Tube 316L", 12])
    stream = io.BytesIO()
    workbook.save(stream)
    path = tmp_path / "devis.xlsx"
    path.write_bytes(stream.getvalue())
    passages = extract(path, path.name)
    assert passages[1]["locator"] == {"sheet": "Devis", "range": "A2:B2"}
    assert "A2=Tube 316L" in passages[1]["text"] and "B2=12" in passages[1]["text"]


def test_calendar_selected_context_preserves_timezone_and_unfolds():
    result = calendar_preview(b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:meeting-42\r\nSUMMARY:Revue de\r\n  conception\r\nDTSTART;TZID=Europe/Paris:20261011T140000\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    assert result["events"][0]["summary"] == "Revue de conception"
    assert result["events"][0]["dtstart_parameters"] == ["TZID=Europe/Paris"]
    assert result["context_only"]


def test_url_private_dns_and_credentials_refused(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 80))])
    for url in ("http://example.com", "https://user:secret@example.com", "file:///C:/Agent/project_brain.db"):
        with pytest.raises(HTTPException) as failure:
            public_url(url)
        assert failure.value.status_code == 422


def industrial_pdf():
    """Two physical pages with actual extractable text; no client document."""
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    for text in ('FICTIF IP65 page A-17', 'FICTIF Serrage 12 Nm page A-42'):
        page = writer.add_blank_page(width=400, height=400)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
            DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(f'BT /F1 12 Tf 40 300 Td ({text}) Tj ET'.encode())
        page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def selected_url(db, library, monkeypatch, data, mime, url='https://example.test/download', **extra):
    from app.routers import source_library as route
    monkeypatch.setattr(route, 'fetch_selected', lambda selected: (data, mime))
    monkeypatch.setattr(route.library, 'require_enabled', lambda db: None)
    monkeypatch.setattr('app.config.RAW_DIR', library[1])
    return route.import_url(route.URLImport(project_id=library[0][0], url=url, **extra), db)


def test_url_pdf_keeps_physical_pages_instead_of_treating_binary_as_html(library, monkeypatch):
    data = industrial_pdf()
    with SessionLocal() as db:
        result = selected_url(db, library, monkeypatch, data, 'application/pdf')
        source = db.get(Source, result['source_id'])
        artifacts = db.query(SourceArtifact).filter_by(source_id=source.id).all()
        assert source.source_metadata['filename'].endswith('.pdf')
        assert Path(source.original_uri).read_bytes() == data
        assert [a.content_json.get('physical_page') for a in artifacts] == [1, 2]
        assert 'IP65' in artifacts[0].content_text and '12 Nm' in artifacts[1].content_text
        assert result['extraction_status'] == 'extracted'


def test_url_xlsx_keeps_actual_sheet_cells_with_an_opaque_url(library, monkeypatch):
    workbook = Workbook()
    workbook.active.title = 'Devis'
    workbook.active.append(['Tube 316L', 12])
    output = io.BytesIO()
    workbook.save(output)
    data = output.getvalue()
    with SessionLocal() as db:
        result = selected_url(db, library, monkeypatch, data,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        source = db.get(Source, result['source_id'])
        artifact = db.query(SourceArtifact).filter_by(source_id=source.id).one()
        assert source.source_metadata['filename'].endswith('.xlsx')
        assert artifact.content_json['sheet'] == 'Devis' and artifact.content_json['range'] == 'A1:B1'
        assert 'A1=Tube 316L' in artifact.content_text and 'B1=12' in artifact.content_text
        assert Path(source.original_uri).read_bytes() == data


def test_url_image_has_no_extracted_text_and_never_fake_html(library, monkeypatch):
    # This transport/extractor contract checks byte retention, not image decoding quality.
    data = b'\x89PNG\r\n\x1a\nsynthetic-transport-fixture'
    with SessionLocal() as db:
        result = selected_url(db, library, monkeypatch, data, 'image/png', filename='page.html')
        source = db.get(Source, result['source_id'])
        artifact = db.query(SourceArtifact).filter_by(source_id=source.id).one()
        assert source.source_metadata['filename'].endswith('.png')
        assert artifact.kind == 'media' and artifact.content_text == ''
        assert result['extraction_status'] == 'empty'
        assert Path(source.original_uri).read_bytes() == data


@pytest.mark.parametrize('url,mime,requested,expected', [
    ('https://example.test/fiche%20atelier.PDF?download=1', 'application/octet-stream', None, 'fiche atelier.PDF'),
    ('https://example.test/donnees.pdf', 'text/html; charset=utf-8', None, 'donnees.html'),
    ('https://example.test/', 'text/html', None, 'source.html'),
    ('https://example.test/opaque', 'application/octet-stream', None, 'opaque.bin'),
    ('https://example.test/secret%2Fatelier.pdf', 'APPLICATION/PDF', None, 'secret_atelier.pdf'),
    ('https://example.test/opaque', 'image/jpeg', 'photo.jpeg', 'photo.jpeg'),
])
def test_url_format_uses_known_mime_and_safe_path_fallback(url, mime, requested, expected):
    from app.routers.source_library import url_filename
    assert url_filename(url, mime, requested) == expected
    with pytest.raises(HTTPException) as invalid:
        url_filename(url, mime, '../outside.pdf')
    assert invalid.value.status_code == 422


def test_url_repeat_change_and_unavailable_remote_keep_all_local_versions(library, monkeypatch):
    from app.routers import source_library as route
    from app.source_library_models import LibraryVersion
    with SessionLocal() as db:
        initial = selected_url(db, library, monkeypatch, b'Reserve fictive 350 lux', 'text/plain')
        update_labels(db, initial['source_id'], ['Qualification'])
        repeated = selected_url(db, library, monkeypatch, b'Reserve fictive 350 lux', 'text/plain')
        assert repeated['replayed'] and repeated['source_id'] == initial['source_id']
        changed = selected_url(db, library, monkeypatch, b'Reserve fictive 400 lux', 'text/plain')
        assert changed['item_id'] == initial['item_id'] and changed['version_id'] != initial['version_id']
        old = selected_url(db, library, monkeypatch, b'Reserve fictive 350 lux', 'text/plain')
        assert old['replayed'] and not old['current']

        def unavailable(url):
            raise HTTPException(502, 'Source distante : réponse HTTP 503')

        monkeypatch.setattr(route, 'fetch_selected', unavailable)
        with pytest.raises(HTTPException) as failure:
            route.import_url(route.URLImport(project_id=library[0][0], url='https://example.test/download'), db)
        assert failure.value.status_code == 502
        assert catalog(db, project_id=library[0][0], label='Qualification')['items'][0]['source_id'] == changed['source_id']
        assert db.query(LibraryVersion).filter_by(item_id=initial['item_id']).count() == 2
        assert Path(db.get(Source, initial['source_id']).original_uri).read_bytes() == b'Reserve fictive 350 lux'
        assert Path(db.get(Source, changed['source_id']).original_uri).read_bytes() == b'Reserve fictive 400 lux'


def test_explicit_url_reimport_reinterprets_legacy_html_without_erasing_old_evidence(library, monkeypatch):
    from app.source_library_models import LibraryVersion
    data = industrial_pdf()
    url = 'https://example.test/download'
    with SessionLocal() as db:
        legacy = import_bytes(db, project_id=library[0][0], provider='url', provider_key=url,
            filename='page.html', data=data, mime_type='application/pdf', storage=library[1])
        update_labels(db, legacy['source_id'], ['Qualification'])
        old = db.get(Source, legacy['source_id'])
        old_path = old.original_uri
        old_metadata = dict(old.source_metadata)
        old_artifacts = [(a.id, a.kind, a.content_text, a.content_json) for a in
            db.query(SourceArtifact).filter_by(source_id=old.id).all()]
        corrected = selected_url(db, library, monkeypatch, data, 'application/pdf', url=url)
        assert corrected['source_id'] != legacy['source_id']
        assert corrected['version_id'] == legacy['version_id']
        assert corrected['extraction_version_id'] != legacy['version_id']
        assert corrected['extraction_version_id'] == str(uuid.uuid5(uuid.UUID(legacy['version_id']), 'url-format-v1:.pdf'))
        source = db.get(Source, corrected['source_id'])
        assert source.source_metadata['reinterprets_source_id'] == legacy['source_id']
        assert source.source_metadata['filename'].endswith('.pdf')
        assert Path(source.original_uri).read_bytes() == data == Path(old_path).read_bytes()
        assert [(a.id, a.kind, a.content_text, a.content_json) for a in
            db.query(SourceArtifact).filter_by(source_id=old.id).all()] == old_artifacts
        db.refresh(old)
        assert old.original_uri == old_path and old.source_metadata['filename'] == 'page.html'
        assert old.source_metadata == {**old_metadata, 'superseded': True}
        assert db.get(LibraryVersion, legacy['version_id']).source_id == legacy['source_id']
        assert db.query(LibraryVersion).filter_by(item_id=legacy['item_id']).count() == 1
        artifacts = db.query(SourceArtifact).filter_by(source_id=source.id).all()
        assert [a.content_json.get('physical_page') for a in artifacts] == [1, 2]
        assert catalog(db, project_id=library[0][0], label='Qualification')['items'][0]['source_id'] == corrected['source_id']
        replay = selected_url(db, library, monkeypatch, data, 'application/pdf', url=url)
        assert replay['replayed'] and replay['source_id'] == corrected['source_id']
        assert replay['extraction_version_id'] == corrected['extraction_version_id']


@pytest.mark.parametrize('repair_before_change', [False, True])
def test_old_url_interpretation_replay_never_rolls_back_newer_bytes(library, monkeypatch, repair_before_change):
    from app.source_library_models import LibraryItem, LibraryVersion
    data = industrial_pdf()
    url = 'https://example.test/download'
    with SessionLocal() as db:
        legacy = import_bytes(db, project_id=library[0][0], provider='url', provider_key=url,
            filename='page.html', data=data, mime_type='application/pdf', storage=library[1])
        update_labels(db, legacy['source_id'], ['Qualification'])
        if repair_before_change:
            selected_url(db, library, monkeypatch, data, 'application/pdf', url=url)
        changed = selected_url(db, library, monkeypatch, data.replace(b'IP65', b'IP67'), 'application/pdf', url=url)
        old = selected_url(db, library, monkeypatch, data, 'application/pdf', url=url)
        repeated = selected_url(db, library, monkeypatch, data, 'application/pdf', url=url)
        assert not old['current'] and not repeated['current'] and repeated['replayed']
        assert old['source_id'] == repeated['source_id'] != changed['source_id']
        assert db.get(Source, old['source_id']).source_metadata['superseded']
        assert db.get(LibraryItem, legacy['item_id']).current_source_id == changed['source_id']
        assert db.query(LibraryVersion).filter_by(item_id=legacy['item_id']).count() == 2
        assert catalog(db, project_id=library[0][0], label='Qualification')['items'][0]['source_id'] == changed['source_id']
        assert Path(db.get(Source, legacy['source_id']).original_uri).read_bytes() == data


@pytest.mark.parametrize('damage_reinterpreted', [False, True])
def test_url_reinterpretation_refuses_corrupt_retained_bytes(library, monkeypatch, damage_reinterpreted):
    data = industrial_pdf()
    url = 'https://example.test/download'
    with SessionLocal() as db:
        legacy = import_bytes(db, project_id=library[0][0], provider='url', provider_key=url,
            filename='page.html', data=data, mime_type='application/pdf', storage=library[1])
        target = legacy['source_id']
        if damage_reinterpreted:
            target = selected_url(db, library, monkeypatch, data, 'application/pdf', url=url)['source_id']
        path = Path(db.get(Source, target).original_uri)
        path.write_bytes(b'corrupt fixture')
        count = db.query(Source).filter_by(project_id=library[0][0]).count()
        with pytest.raises(HTTPException) as failure:
            selected_url(db, library, monkeypatch, data, 'application/pdf', url=url)
        assert failure.value.status_code == 409
        assert db.query(Source).filter_by(project_id=library[0][0]).count() == count
        assert path.read_bytes() == b'corrupt fixture'


def test_unknown_mime_and_file_replay_do_not_trigger_legacy_url_reinterpretation(library, monkeypatch):
    data = industrial_pdf()
    url = 'https://example.test/fiche.pdf'
    with SessionLocal() as db:
        legacy = import_bytes(db, project_id=library[0][0], provider='url', provider_key=url,
            filename='page.html', data=data, mime_type='application/pdf', storage=library[1])
        unchanged = selected_url(db, library, monkeypatch, data, 'application/octet-stream', url=url)
        assert unchanged['source_id'] == legacy['source_id'] and not unchanged.get('reinterpreted')
        file = import_bytes(db, project_id=library[0][0], provider='file', provider_key='old.html',
            filename='old.html', data=data, storage=library[1])
        repeated = import_bytes(db, project_id=library[0][0], provider='file', provider_key='old.html',
            filename='old.pdf', data=data, storage=library[1], reinterpret_legacy_html=True)
        assert repeated['source_id'] == file['source_id'] and not repeated.get('reinterpreted')


@pytest.fixture
def isolated_drive_settings(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import AppSetting
    database = create_engine('sqlite:///' + str(tmp_path / 'drive-settings.sqlite'))
    AppSetting.__table__.create(database)
    factory = sessionmaker(bind=database)
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    try:
        with factory() as db:
            yield db
    finally:
        database.dispose()


@pytest.mark.parametrize('foresight', [{}, {'drive_enabled': False}, {'drive_enabled': 'false'}, {'drive_enabled': 1}])
def test_drive_default_off_retains_old_token_and_refuses_before_network_or_writes(isolated_drive_settings, monkeypatch, foresight):
    from app.models import AppSetting
    from app.routers import source_library as route
    from app.services.settings_service import get_section
    db = isolated_drive_settings
    if foresight:
        db.add(AppSetting(key='foresight', value=foresight))
    retained = {'access_token': 'opaque-fixture-token-retained', 'last_import': '2026-10-10T11:00:00Z'}
    db.add(AppSetting(key='foresight_drive', value=retained))
    db.commit()
    writes = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().split(' ', 1)[0].upper() in {'INSERT', 'UPDATE', 'DELETE'}:
            writes.append(statement)

    event.listen(db.get_bind(), 'before_cursor_execute', capture)

    def prohibited(*_args, **_kwargs):
        pytest.fail('Drive disabled: no remote fetch, secret transform or settings write is admitted')

    monkeypatch.setattr(route.library, 'require_enabled', lambda _db: None)
    monkeypatch.setattr(route, 'require_brain', lambda _project: None)
    monkeypatch.setattr(route, 'fetch_selected', prohibited)
    monkeypatch.setattr('app.services.secrets_store.reveal', prohibited)
    monkeypatch.setattr('app.services.secrets_store.protect', prohibited)
    monkeypatch.setattr('app.services.settings_service.save_section', prohibited)
    status = route.drive_status(db)
    assert status['enabled'] is False and status['configured'] is True
    assert status['last_import'] == retained['last_import']
    assert 'access_token' not in status
    for action in [lambda: route.configure_drive(route.DriveConnection(access_token='new-opaque-fixture-token'), db),
                   lambda: route.import_drive(route.DriveImport(project_id='fixture-project', file_id='chosen-file'), db)]:
        with pytest.raises(HTTPException) as failure:
            action()
        assert failure.value.status_code == 409
        assert 'désactivé' in failure.value.detail
    assert get_section(db, 'foresight_drive') == retained
    assert get_section(db, 'foresight') == foresight
    assert writes == []


def test_drive_off_preserves_write_and_project_rights(isolated_drive_settings, monkeypatch):
    from app.routers import source_library as route
    db = isolated_drive_settings
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    with pytest.raises(HTTPException) as failure:
        route.configure_drive(route.DriveConnection(access_token='opaque-fixture-access-token'), db)
    assert failure.value.status_code == 403
    monkeypatch.setattr(route.library, 'require_enabled', lambda _db: None)

    def denied(_project):
        raise HTTPException(404, 'Projet absent ou inaccessible')

    monkeypatch.setattr(route, 'require_brain', denied)
    with pytest.raises(HTTPException) as failure:
        route.import_drive(route.DriveImport(project_id='foreign-project', file_id='chosen-file'), db)
    assert failure.value.status_code == 404


def test_drive_selected_native_sheet_exports_real_xlsx_and_retains_provider_versions(library, monkeypatch):
    import json
    from app.routers import source_library as route
    from app.services.settings_service import save_section
    from app.source_library_models import LibraryVersion
    monkeypatch.setattr(route.library, 'require_enabled', lambda db: None)
    monkeypatch.setattr('app.services.secrets_store.reveal', lambda value: 'fixture-token-not-private')
    monkeypatch.setattr('app.config.RAW_DIR', library[1])
    remote = {'version': '1', 'quantity': 12, 'available': True}
    calls = []
    payloads = {}
    for quantity in (12, 18):
        workbook = Workbook()
        workbook.active.title = 'Devis'
        workbook.active.append(['Tube 316L', quantity])
        output = io.BytesIO()
        workbook.save(output)
        payloads[quantity] = output.getvalue()

    def fetch(url, *, bearer):
        assert bearer == 'fixture-token-not-private'
        calls.append(url)
        if not remote['available']:
            raise HTTPException(502, 'Source distante : réponse HTTP 503')
        if '?fields=' in url:
            return json.dumps({'id': 'chosen-file', 'name': 'Devis fictif',
                'mimeType': 'application/vnd.google-apps.spreadsheet', 'version': remote['version'],
                'modifiedTime': '2026-10-11T12:00:00Z'}).encode(), 'application/json'
        assert '/chosen-file/export?mimeType=' in url
        return payloads[remote['quantity']], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    monkeypatch.setattr(route, 'fetch_selected', fetch)
    with SessionLocal() as db:
        save_section(db, 'foresight', {'drive_enabled': True})
        save_section(db, 'foresight_drive', {'access_token': 'opaque-fixture-token'})
        body = route.DriveImport(project_id=library[0][0], file_id='chosen-file')
        first = route.import_drive(body, db)
        update_labels(db, first['source_id'], ['Achats'])
        repeat = route.import_drive(body, db)
        assert repeat['replayed'] and repeat['source_id'] == first['source_id']
        remote.update(version='2', quantity=18)
        changed = route.import_drive(body, db)
        assert changed['item_id'] == first['item_id'] and changed['source_id'] != first['source_id']
        artifact = db.query(SourceArtifact).filter_by(source_id=changed['source_id']).one()
        assert 'B1=18' in artifact.content_text and artifact.content_json['range'] == 'A1:B1'
        versions = db.query(LibraryVersion).filter_by(item_id=first['item_id']).all()
        assert {version.provider_version for version in versions} == {'1', '2'}
        assert all(version.provenance['drive_file_id'] == 'chosen-file' for version in versions)
        assert route.drive_status(db)['configured'] and route.drive_status(db)['enabled']
        remote['available'] = False
        with pytest.raises(HTTPException) as failure:
            route.import_drive(body, db)
        assert failure.value.status_code == 502
        assert all(Path(db.get(Source, version.source_id).original_uri).is_file() for version in versions)
        assert catalog(db, project_id=library[0][0], label='Achats')['items'][0]['source_id'] == changed['source_id']
    assert len(calls) == 7
