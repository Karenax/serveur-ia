"""L10 publication -> project/global -> explicit task -> read-only PDF export."""
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import func, select

from app.db import get_db as get_brain
from app.models import MeetingRecording, KnowledgeItem, ProvenanceLink
from app.routers.meeting_notes_publication import router as publication_router
from app.routers.workspace import router as workspace_router, get_erp_db
from backend.app.db import get_db as get_erp
from backend.app.models import Meeting, MeetingAction, Task
from backend.app.routers.meetings import router as meeting_router
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, publication

stores = stores_fixture


def client_for(brain, erp):
    app = FastAPI()
    for router in (publication_router, meeting_router, workspace_router):
        app.include_router(router)
    def brain_db():
        with brain() as db:
            yield db
    def erp_db():
        with erp() as db:
            yield db
    app.dependency_overrides[get_brain] = brain_db
    app.dependency_overrides[get_erp] = erp_db
    app.dependency_overrides[get_erp_db] = erp_db
    return TestClient(app)


def test_notes_report_replay_global_project_task_and_pdf_keep_one_publication(stores):
    brain, erp, pid, _ = stores
    with brain() as db:
        session, saved, payload = publication(db, pid)
        sid = session['id']
    with client_for(brain, erp) as client:
        published = client.post(f'/api/v1/meeting-sessions/{sid}/publish-notes', json=payload.model_dump(mode='json'))
        assert published.status_code == 200, published.text
        mid = published.json()['meeting_id']
        replay = client.post(f'/api/v1/meeting-sessions/{sid}/publish-notes', json=payload.model_dump(mode='json'))
        assert replay.status_code == 200 and replay.json()['meeting_id'] == mid and replay.json()['replayed']
        for params in ({}, {'project_id':pid}):
            rows = client.get('/api/v1/workspace/meetings', params=params).json()['items']
            assert len(rows) == 1 and rows[0]['meeting_id'] == mid and rows[0]['session_id'] == sid
        rows = client.get(f'/api/v1/projects/{pid}/meetings').json()
        assert len(rows) == 1 and len(rows[0]['actions']) == 1
        aid = rows[0]['actions'][0]['id']
        assert rows[0]['actions'][0]['task_id'] is None
        with erp() as db:
            before = (db.get(Meeting,mid).decisions, db.scalar(select(func.count()).select_from(Task)))
        pdf = client.get(f'/api/v1/projects/{pid}/meetings/{mid}/pdf')
        assert pdf.status_code == 200 and pdf.headers['content-type'] == 'application/pdf'
        assert pdf.headers['cache-control'] == 'private, no-store' and pdf.content.startswith(b'%PDF-')
        text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
        assert 'Compte rendu de réunion' in text and 'Le devis doit être vérifié.' in text
        assert 'Vérifier le devis' in text and 'BE' in text and '2026-10-12' in text
        with erp() as db:
            assert (db.get(Meeting,mid).decisions, db.scalar(select(func.count()).select_from(Task))) == before
        task_url = f'/api/v1/projects/{pid}/meetings/{mid}/actions/{aid}/to-task'
        converted = client.post(task_url)
        assert converted.status_code == 201, converted.text
        assert client.post(task_url).status_code == 409
        after_pdf = client.get(f'/api/v1/projects/{pid}/meetings/{mid}/pdf')
        after_text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(after_pdf.content)).pages)
        assert 'Transférée en tâche' in after_text
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(Meeting)) == 1
        assert db.scalar(select(func.count()).select_from(MeetingAction)) == 1
        assert db.scalar(select(func.count()).select_from(Task)) == 1
        assert db.get(Meeting,mid).decisions == before[0]
    with brain() as db:
        assert db.scalar(select(func.count()).select_from(MeetingRecording)) == 0
        assert db.scalar(select(func.count()).select_from(KnowledgeItem)) == 2
        assert db.scalar(select(func.count()).select_from(ProvenanceLink)) == 2


def test_pdf_rights_foreign_project_missing_report_and_markup_are_readonly(stores):
    brain, erp, pid, _ = stores
    with erp() as db:
        row = Meeting(project_id=pid, title='Export <privé>', date='2026-10-16',
            decisions='Conserver <b>1250 W</b> & ±0,2 mm ; aucune validation automatique.')
        db.add(row)
        db.commit()
        mid = row.id
    with client_for(brain, erp) as client:
        url = f'/api/v1/projects/{pid}/meetings/{mid}/pdf'
        with operator_context(Operator('reader','reader',frozenset([pid]))):
            result = client.get(url)
            assert result.status_code == 200
        text = ''.join(page.extract_text() for page in PdfReader(BytesIO(result.content)).pages)
        assert '<b>1250 W</b>' in text and '±0,2 mm' in text
        with operator_context(Operator('other','reader',frozenset())):
            assert client.get(url).status_code == 404
        assert client.get(f'/api/v1/projects/{pid}/meetings/absent/pdf').status_code == 404
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(Meeting)) == 1
        assert db.scalar(select(func.count()).select_from(Task)) == 0


def test_pdf_paginates_long_decisions_and_long_actions_without_losing_last_text():
    from backend.app.services.meeting_report_pdf import build_pdf
    raw = build_pdf({'code':'PDF-FICTIF', 'title':'Projet de recette'},
        {'title':'Compte rendu long', 'date':'2026-10-16','participants':'BE',
         'decisions':'\n'.join(f'Point {i} : conserver la réserve industrielle.' for i in range(180))},
        [{'title':('Action détaillée à conserver. '*120)+'DERNIERE-ACTION', 'owner':'BE', 'due_date':'2026-10-20','task_id':None}])
    pages = PdfReader(BytesIO(raw)).pages
    assert len(pages) > 2
    text = '\n'.join(page.extract_text() for page in pages)
    assert 'Point 179' in text and 'DERNIERE-ACTION' in text
    assert all(f'Page {index}' in page.extract_text() for index,page in enumerate(pages,1))
