"""A spoken question cannot prove itself; factual excerpts remain canonical."""
import asyncio

from app.meeting_session_models import LiveTranscriptSegment
from app.services import meeting_sessions as sessions, scoped_assistant as assistant
from tests.test_meeting_sessions import stores as stores_fixture, create, key
from tests.test_session_assistant import enable

stores = stores_fixture


def segment(db, row, text, start):
    value = LiveTranscriptSegment(id=key(),session_id=row.id,track='mic',
        start_ms=start,end_ms=start+1000,speaker='MIC',text=text)
    db.add(value)
    db.commit()
    return value


def test_spoken_question_is_not_evidence_and_facts_precede_query(stores):
    brain,_,_,_ = stores
    with brain() as db:
        enable(db)
        row=sessions.get_session(db,create(db,kind='meeting')['id'])
        fact=segment(db,row,'Le budget n’est pas approuvé ; aucun achat n’est autorisé.',0)
        question=segment(db,row,'  Le budget est-il approuvé ? ',1000)
        query='Le budget est-il approuvé ?'
        _,messages,metadata=asyncio.run(assistant.prepare(db,row,query=query,scope='session'))
        assert [c['excerpt'] for c in metadata['citations']]==[fact.text]
        assert metadata['citations'][0]['locator']['segment_id']==fact.id
        assert metadata['citations'][0]['locator']['segment_revision']==fact.revision
        assert messages[-1]['content'].startswith('Extraits :\n[C1]')
        assert messages[-1]['content'].endswith('\n\nQuestion : '+query)
        db.refresh(question)
        assert question.text=='  Le budget est-il approuvé ? '


def test_question_without_evidence_does_not_cite_itself(stores):
    brain,_,_,_=stores
    with brain() as db:
        enable(db)
        row=sessions.get_session(db,create(db,kind='meeting')['id'])
        segment(db,row,'Quel budget est approuvé ?',0)
        _,_,metadata=asyncio.run(assistant.prepare(db,row,query='Quel budget est approuvé ?',scope='session'))
        assert metadata['citations']==[]


def test_literal_fact_remains_evidence_for_identical_short_query(stores):
    brain,_,_,_=stores
    with brain() as db:
        enable(db)
        row=sessions.get_session(db,create(db,kind='meeting')['id'])
        fact=segment(db,row,'230 volts',0)
        _,_,metadata=asyncio.run(assistant.prepare(db,row,query='230 volts',scope='session'))
        assert [c['excerpt'] for c in metadata['citations']]==[fact.text]
