"""Complete graph pages and measured statistics without models or production data."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from sqlalchemy import func, select
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.meeting_session_models import MeetingAudioChunk, MeetingSessionEvent
from app.models import KnowledgeItem, Project, ProvenanceLink, Source, SourceArtifact
from app.services import fusion_insights, fusion_index_metrics
from app.services.eg2_memory import EG2MemoryAdapter
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create
from tests.test_session_assistant import source
from tests.test_unified_search import Channel

stores=stores_fixture


def no_runtime(monkeypatch):
    monkeypatch.setattr('app.services.live_speech.runtime_status',lambda: {'ready':False})


def test_graph_pages_cover_every_source_and_all_its_provenance(stores):
    brain, _, pid, bid=stores
    with brain() as db:
        sources=[source(db,bid) for _ in range(5)]
        first=min(sources,key=lambda s:s.id)
        for i in range(6):
            knowledge=KnowledgeItem(project_id=bid,kind='technical',subject=f'Constat {i}',value='350 lux',status='validated')
            db.add(knowledge)
            db.flush()
            db.add(ProvenanceLink(knowledge_item_id=knowledge.id,source_id=first.id))
        other=Project(code='OTHER',name='Other project')
        db.add(other)
        db.flush()
        foreign=source(db,other.id)
        crossed=KnowledgeItem(project_id=other.id,kind='technical',subject='Hidden',value='Hidden',status='validated')
        db.add(crossed)
        db.flush()
        db.add(ProvenanceLink(knowledge_item_id=crossed.id,source_id=first.id))
        db.commit()
        before=[db.scalar(select(func.count()).select_from(t)) for t in (Source,KnowledgeItem,ProvenanceLink)]
        with operator_context(Operator('local','editor',frozenset([pid]))):
            pages=[fusion_insights.graph(db,bid,limit=2,offset=offset) for offset in (0,2,4)]
        assert [p['has_next'] for p in pages]==[True,True,False]
        assert all(p['total']==5 and p['page_provenance_complete'] for p in pages)
        seen=[n['source_id'] for p in pages for n in p['nodes'] if n['kind']=='source']
        assert len(seen)==len(set(seen))==5 and foreign.id not in seen
        assert sum(e['kind']=='cites' for e in pages[0]['edges'])==6
        assert all(not e['inferred'] for p in pages for e in p['edges'])
        assert not any(n['label']=='Hidden' for p in pages for n in p['nodes'])
        assert before==[db.scalar(select(func.count()).select_from(t)) for t in (Source,KnowledgeItem,ProvenanceLink)]


def test_graph_http_window_validation_and_continuation(stores):
    from app.db import get_db
    from app.routers.fusion_insights import router
    brain, _, pid, bid=stores
    with brain() as db:
        for _ in range(3):
            source(db,bid)
    app=FastAPI()
    app.include_router(router)
    def private_db():
        with brain() as db:
            yield db
    app.dependency_overrides[get_db]=private_db
    with operator_context(Operator('local','editor',frozenset([pid]))), TestClient(app) as client:
        url='/api/v1/workspace/source-graph'
        response=client.get(url,params={'project_id':bid,'limit':1,'offset':1})
        assert response.status_code==200
        data=response.json()
        assert data['total']==3 and data['offset']==1 and data['limit']==1 and data['has_next']
        assert len([n for n in data['nodes'] if n['kind']=='source'])==1
        assert client.get(url,params={'offset':-1}).status_code==422
        assert client.get(url,params={'limit':0}).status_code==422


def test_stats_two_tracks_pending_age_and_latency_are_measured_separately(stores,monkeypatch):
    brain, _, pid, bid=stores
    no_runtime(monkeypatch)
    monkeypatch.setattr(fusion_index_metrics,'measured_indexes',lambda *args:{'indexed_sources':0,
        'text_passages':0,'profiles':[],'size_bytes':0})
    monkeypatch.setattr('app.services.scoped_assistant.context_current',lambda *args:True)
    created=datetime.now(timezone.utc)-timedelta(seconds=120)
    with brain() as db:
        session=create(db,project_id=pid)
        for i,(track,start,status) in enumerate((('mic',0,'pending'),('system',0,'running'),('mic',5000,'completed'))):
            db.add(MeetingAudioChunk(id=f'chunk-{i}',session_id=session['id'],track=track,sequence=i,
                filename=f'{track}-{i}.wav',mime_type='audio/wav',storage_path=str(Path('private')/f'{i}.wav'),
                sha256=str(i)*64,size_bytes=12+i,start_ms=start,duration_ms=5000,
                speech_status=status,created_at=created))
        for value in (2.5,-1,True,float('nan'),'invalid'):
            db.add(MeetingSessionEvent(session_id=session['id'],kind='assistant.answer',
                revision=1,data={'elapsed_seconds':value}))
        db.commit()
        with operator_context(Operator('local','editor',frozenset([pid]))):
            result=fusion_insights.stats(db,bid)
        assert result['sessions']['duration_seconds']==10
        assert result['sessions']['audio_bytes']==39
        assert result['sessions']['chunks_by_track']=={'mic':2,'system':1}
        assert result['transcription']['pending_chunks']==2
        assert result['transcription']['pending_audio_seconds']==10
        assert 120<=result['transcription']['oldest_pending_seconds']<130
        assert result['assistant']['answers']==5
        assert result['assistant']['measured_latency_samples']==1
        assert result['assistant']['p50_seconds']==result['assistant']['p95_seconds']==2.5
        assert result['assistant']['useful_answers'] == 0 and result['assistant']['evaluated_answers'] == 0
        assert result['assistant']['tokens'] is None
        json.dumps(result,allow_nan=False)
