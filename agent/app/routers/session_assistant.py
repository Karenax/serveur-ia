"""Closed scope requests and human decisions on versioned suggestions."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, StrictBool
from sqlalchemy.orm import Session

from app.db import get_db
from app.meeting_session_schemas import Closed
from app.schemas import ChatHistoryMessage
from app.services import meeting_sessions as sessions, scoped_assistant as assistant
from app.services import session_enhancements as enhancements
from app.services import assistant_feedback as feedback
from app.services import session_proactive

router = APIRouter(prefix='/api/v1/meeting-sessions', tags=['session-assistant'])


class Question(Closed):
    query: str = Field(min_length=2, max_length=2000)
    scope: Literal['session', 'project', 'sources', 'global'] = 'session'
    source_ids: list[str] = Field(default_factory=list, max_length=100)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=12)
    expected_revision: int | None = Field(default=None, ge=1)


class Revision(Closed):
    expected_revision: int = Field(ge=1)


class Decision(Revision):
    decision: Literal['accept', 'reject']


class Pin(Closed):
    pinned: bool


class Feedback(Closed):
    useful: StrictBool | None


def context(db, sid, expected=None, write=False):
    sessions.require_enabled(db)
    row = sessions.get_session(db, sid, write=write)
    if expected is not None and row.revision != expected:
        raise HTTPException(409, 'La séance a évolué ; actualiser avant cette action')
    return row


@router.post('/{sid}/ask')
async def ask(sid: str, body: Question, db: Session = Depends(get_db)):
    if sum(len(m.content) for m in body.history) > 12000:
        raise HTTPException(422, 'Historique limité à 12 000 caractères')
    result = await assistant.answer(db, context(db, sid, body.expected_revision), **body.model_dump(exclude={'expected_revision', 'history'}), history=body.history)
    return feedback.annotate(db, sid, 'ask', [result])[0]


@router.get('/{sid}/ask')
def answer_history(sid: str, scope: Literal['session', 'project', 'sources', 'global'] = 'session',
                   source_ids: list[str] = Query(default=[], max_length=100), db: Session = Depends(get_db)):
    result = assistant.stored_answers(db, context(db, sid), 'assistant.answer', scope=scope, source_ids=source_ids)
    return {'items': feedback.annotate(db, sid, 'ask', result['items'])}


@router.get('/{sid}/live-answers')
def live_answers(sid: str, db: Session = Depends(get_db)):
    row = context(db, sid)
    result = assistant.stored_answers(db, row, 'assistant.live-answer')
    return {'items': feedback.annotate(db, sid, 'live', result['items']),
            'automatic': session_proactive.question_progress(db, row)}


@router.put('/{sid}/answers/{answer_kind}/{answer_id}/feedback')
def rate_answer(sid: str, answer_kind: Literal['ask', 'live'], answer_id: str,
                body: Feedback, db: Session = Depends(get_db)):
    return feedback.set_feedback(db, context(db, sid, write=True), answer_kind, answer_id, body.useful)


@router.put('/{sid}/live-answers/{answer_id}/pin')
def pin_answer(sid: str, answer_id: str, body: Pin, db: Session = Depends(get_db)):
    return assistant.pin_live_answer(db, context(db, sid, write=True), answer_id, body.pinned)


@router.post('/{sid}/live-answers')
async def live_answer(sid: str, body: Question, db: Session = Depends(get_db)):
    result = await assistant.answer(db, context(db, sid, body.expected_revision), query=body.query,
                                    scope=body.scope, source_ids=body.source_ids, live=True)
    return feedback.annotate(db, sid, 'live', [result])[0]


@router.get('/{sid}/enhancements')
def proposals(sid: str, db: Session = Depends(get_db)):
    return enhancements.list_proposals(db, context(db, sid))


@router.post('/{sid}/enhancements')
async def enhance(sid: str, body: Revision, db: Session = Depends(get_db)):
    return await enhancements.propose(db, context(db, sid, body.expected_revision, True))


@router.post('/{sid}/enhancements/{proposal_id}/decision')
def decide(sid: str, proposal_id: str, body: Decision, db: Session = Depends(get_db)):
    return enhancements.decide(db, context(db, sid, write=True), proposal_id, body.decision, body.expected_revision)
