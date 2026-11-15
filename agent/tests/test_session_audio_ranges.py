"""Real HTTP partial audio, scoped and byte-exact, with no devices or models."""
import hashlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.db import get_db
from app.meeting_session_models import MeetingAudioChunk
from app.routers.meeting_sessions import router
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, key, wav

stores=stores_fixture


@pytest.fixture
def audio(stores):
    brain, _, pid, _=stores
    raw=wav(samples=16000)
    with operator_context(Operator('audio-qa','owner')), brain() as db:
        row=create(db,project_id=pid,kind='import')
        path=Path(settings.storage_dir)/'meeting-sessions'/row['id']/'silence.wav'
        path.parent.mkdir(parents=True)
        path.write_bytes(raw)
        db.add(MeetingAudioChunk(id=key(),session_id=row['id'],track='mic',sequence=0,filename=path.name,
            mime_type='audio/wav',storage_path=str(path),sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw),
            start_ms=0,duration_ms=1000,speech_status='completed'))
        db.commit()
    app=FastAPI()
    app.include_router(router)
    def private_db():
        with brain() as db:
            yield db
    app.dependency_overrides[get_db]=private_db
    with operator_context(Operator('audio-qa','owner')), TestClient(app) as client:
        yield client,f"/api/v1/meeting-sessions/{row['id']}/audio?track=mic",raw,path


@pytest.mark.parametrize('header,start,end', [('bytes=0-0',0,0),('bytes=2-13',2,13),
    ('bytes=14-',14,None),('bytes=-11',-11,None),('bytes=0-999999999999999999999',0,None)])
def test_partial_bytes_match_retained_original(audio,header,start,end):
    client,url,raw,path=audio
    response=client.get(url,headers={'Range':header})
    assert response.status_code==206
    expected=raw[start:] if end is None else raw[start:end+1]
    assert response.content==expected
    actual_start=start if start>=0 else len(raw)+start
    actual_end=len(raw)-1 if end is None else end
    assert response.headers['content-range']==f'bytes {actual_start}-{actual_end}/{len(raw)}'
    assert response.headers['content-length']==str(len(expected))
    assert response.headers['accept-ranges']=='bytes'
    assert response.headers['cache-control']=='private, no-store'
    assert path.read_bytes()==raw


@pytest.mark.parametrize('header',['bytes=99999999999999999-','bytes=-0','bytes='+('9'*5000)+'-'],
    ids=['past-end','zero-suffix','very-large-decimal'])
def test_unsatisfiable_and_huge_ranges_are_controlled(audio,header):
    client,url,raw,_=audio
    response=client.get(url,headers={'Range':header})
    assert response.status_code==416
    assert response.headers['content-range']==f'bytes */{len(raw)}'
    assert response.headers['cache-control']=='private, no-store'


@pytest.mark.parametrize('header',[None,'items=0-1','bytes=abc','bytes=0-1,4-5','bytes=5-2'])
def test_full_get_and_ignored_ranges_keep_original(audio,header):
    client,url,raw,_=audio
    response=client.get(url,headers={'Range':header} if header else {})
    assert response.status_code==200 and response.content==raw
    assert response.headers['accept-ranges']=='bytes'
    assert 'content-range' not in response.headers


def test_if_range_without_validator_falls_back_to_full_representation(audio):
    client,url,raw,_=audio
    response=client.get(url,headers={'Range':'bytes=0-1','If-Range':'"unknown"'})
    assert response.status_code==200 and response.content==raw


def test_partial_request_cannot_bypass_integrity_or_project_rights(audio):
    client,url,raw,path=audio
    with operator_context(Operator('blocked','reader',frozenset())):
        denied=client.get(url,headers={'Range':'bytes=0-0'})
    assert denied.status_code in (403,404) and 'content-range' not in denied.headers
    path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
    altered=client.get(url,headers={'Range':'bytes=0-0'})
    assert altered.status_code==409 and 'content-range' not in altered.headers
