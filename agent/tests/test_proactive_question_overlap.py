"""One live question carried by overlapping audio tracks must not run twice."""
import pytest
from sqlalchemy import select

from app.meeting_session_models import LiveTranscriptSegment, MeetingSession, MeetingSessionEvent
from app.services import session_proactive as worker, scoped_assistant as assistant
from app.services.settings_service import save_section
from tests.test_meeting_sessions import stores as stores_fixture, create, command, key

stores = stores_fixture


@pytest.mark.parametrize('start,end,repeated,expected',[
    (1000,4000,'FAUT-IL vérifier la puissance 1250 W ?',1),
    (0,3000,'Faut-il  vérifier la puissance 1250 W?',1),
    (4000,6000,'Faut-il vérifier la puissance 1250 W ?',2),
    (1000,4000,'Faut-il vérifier la puissance 2250 W ?',2),
])
def test_overlap_echo_is_one_attempt_but_later_or_different_number_is_new(stores,monkeypatch,start,end,repeated,expected):
    brain,_,pid,_=stores
    worker._stop.clear()
    with brain() as db:
        save_section(db,'foresight',{'proactive_enabled':True,'auto_enhancement_enabled':False})
        session=create(db,project_id=pid)
        command(db,session['id'],'resume',1)
        original=LiveTranscriptSegment(id=key(),session_id=session['id'],track='mic',start_ms=0,end_ms=3000,
            speaker='MIC',text='Faut-il vérifier la puissance 1250 W ?')
        echo=LiveTranscriptSegment(id=key(),session_id=session['id'],track='system',start_ms=start,end_ms=end,
            speaker='SYSTEM',text=repeated)
        db.add_all([original,echo])
        db.commit()
    calls=[]
    async def answer(db,row,**kwargs):
        calls.append(kwargs['query'])
    monkeypatch.setattr(assistant,'answer',answer)
    for _ in range(4):
        worker.tick()
    assert len(calls)==expected
    with brain() as db:
        events=list(db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id==session['id'])))
        attempts=[row for row in events if row.kind=='assistant.proactive-attempt']
        duplicates=[row for row in events if row.kind=='assistant.proactive-duplicate']
        assert len(attempts)==expected and len(duplicates)==2-expected
        assert len(list(db.scalars(select(LiveTranscriptSegment))))==2
        if duplicates:
            assert duplicates[0].data['duplicate_of']==attempts[0].data['question_token']


def test_same_question_in_another_session_and_corrected_number_are_not_suppressed(stores,monkeypatch):
    brain,_,pid,_=stores
    worker._stop.clear()
    ids=[]
    calls=[]
    async def answer(db,row,**kwargs):
        calls.append((row.id,kwargs['query']))
    monkeypatch.setattr(assistant,'answer',answer)
    with brain() as db:
        save_section(db,'foresight',{'proactive_enabled':True,'auto_enhancement_enabled':False})
    for _ in range(2):
        with brain() as db:
            session=create(db,project_id=pid)
            command(db,session['id'],'resume',1)
            segment=LiveTranscriptSegment(id=key(),session_id=session['id'],track='mic',start_ms=0,end_ms=3000,
                speaker='MIC',text='Faut-il vérifier la puissance 1250 W ?')
            db.add(segment)
            db.flush()
            ids.append((session['id'],segment.id))
            db.commit()
        worker.tick()
        if len(ids)==1:
            with brain() as db:
                command(db,ids[0][0],'finalize',2)
    assert {sid for sid,_ in calls}=={sid for sid,_ in ids} and len(calls)==2
    with brain() as db:
        segment=db.get(LiveTranscriptSegment,ids[1][1])
        segment.text='Faut-il vérifier la puissance 2250 W ?'
        segment.revision+=1
        db.commit()
    worker.tick()
    assert len(calls)==3 and calls[-1]==(ids[1][0],'Faut-il vérifier la puissance 2250 W ?')


@pytest.mark.parametrize('first,second',[
    ('Faut-il contrôler AIRB25LTH0806-A ?','Faut-il contrôler AIRB25LTH0806/A ?'),
    ('Valeur 1,5 W à vérifier ?','Valeur 1/5 W à vérifier ?'),
])
def test_reference_separators_and_decimal_fraction_are_distinct(stores,first,second):
    brain,_,_,_=stores
    with brain() as db:
        session=create(db)
        a=LiveTranscriptSegment(id=key(),session_id=session['id'],track='mic',start_ms=0,end_ms=3000,speaker='MIC',text=first)
        b=LiveTranscriptSegment(id=key(),session_id=session['id'],track='system',start_ms=0,end_ms=3000,speaker='SYSTEM',text=second)
        db.add_all([a,b])
        db.flush()
        db.add(MeetingSessionEvent(session_id=session['id'],kind='assistant.proactive-attempt',revision=1,
            data={'question_token':f'{a.id}:{a.revision}','query':first}))
        db.commit()
        assert worker._overlapping_question_attempt(db,db.get(MeetingSession,session['id']),b) is None
