"""A cached session cannot carry old project rights into a fresh snapshot."""
import asyncio

from fastapi import HTTPException
import pytest

from sqlalchemy import select, func

from app.meeting_session_models import MeetingSession, LiveTranscriptSegment, MeetingSessionEvent
from app.models import Source
from app.models import Project as BrainProject
from app.services import meeting_sessions as sessions, scoped_assistant as assistant
from backend.app.models import Project, BrainLink
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, create, key
from tests.test_session_assistant import enable, source, model

stores = stores_fixture


@pytest.mark.parametrize('scope', ['session', 'project', 'sources', 'global'])
def test_prepare_rechecks_project_after_another_connection_changes_cached_session(stores, scope):
    brain, erp, allowed_id, _ = stores
    with brain() as db, erp() as target:
        enable(db)
        hidden_brain = BrainProject(code='RIGHTS-B', name='Projet privé B')
        db.add(hidden_brain)
        db.commit()
        hidden = Project(code='RIGHTS-B', title='Projet privé B')
        target.add(hidden)
        target.flush()
        target.add(BrainLink(project_id=hidden.id, brain_project_id=hidden_brain.id))
        target.commit()
        sid = create(db, project_id=allowed_id)['id']
        db.add(LiveTranscriptSegment(id=key(), session_id=sid, track='mic', start_ms=0, end_ms=1000,
                                    text='Confidentiel : puissance 250 W.', speaker='MIC'))
        db.commit()
        cached = sessions.get_session(db, sid)
        assert cached.project_id == allowed_id
        with brain() as changed:
            row = changed.get(MeetingSession, sid)
            row.project_id, row.brain_project_id = hidden.id, hidden_brain.id
            row.revision += 1
            changed.commit()
        with operator_context(Operator('local', 'editor', frozenset([allowed_id]))):
            with pytest.raises(HTTPException) as failure:
                asyncio.run(assistant.prepare(db, cached, query='Quelle puissance ?', scope=scope))
            assert failure.value.status_code == 404


@pytest.mark.parametrize('moved_object', ['session', 'source'])
def test_move_during_generation_does_not_return_or_store_an_inaccessible_answer(stores, monkeypatch, moved_object):
    brain, erp, allowed_id, allowed_brain_id = stores
    with brain() as db, erp() as target:
        enable(db)
        hidden_brain = BrainProject(code='RIGHTS-GEN-B', name='Projet privé B')
        db.add(hidden_brain)
        db.commit()
        hidden = Project(code='RIGHTS-GEN-B', title='Projet privé B')
        target.add(hidden)
        target.flush()
        target.add(BrainLink(project_id=hidden.id, brain_project_id=hidden_brain.id))
        target.commit()
        hidden_id, hidden_brain_id = hidden.id, hidden_brain.id
        sid = create(db, project_id=allowed_id)['id']
        db.add(LiveTranscriptSegment(id=key(), session_id=sid, track='mic', start_ms=0, end_ms=1000,
                                    text='Puissance demandée : 250 W.', speaker='MIC'))
        db.commit()
        src = source(db, allowed_brain_id)
        source_id = src.id
        def generate(*args, **kwargs):
            with brain() as changed:
                if moved_object == 'session':
                    value = changed.get(MeetingSession, sid)
                    value.project_id, value.brain_project_id = hidden_id, hidden_brain_id
                    value.revision += 1
                else:
                    changed.get(Source, source_id).project_id = hidden_brain_id
                changed.commit()
            return 'Information de la source initiale [C1].'
        model(monkeypatch, generate)
        with operator_context(Operator('local', 'editor', frozenset([allowed_id]))):
            with pytest.raises(HTTPException) as failure:
                asyncio.run(assistant.answer(db, sessions.get_session(db, sid), query='Puissance réserve ?',
                    scope='sources' if moved_object == 'source' else 'session',
                    source_ids=[source_id] if moved_object == 'source' else []))
            assert failure.value.status_code == 404
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.kind == 'assistant.answer')) == 0
