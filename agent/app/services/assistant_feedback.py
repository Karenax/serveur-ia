"""Explicit, reversible human usefulness opinions, separate from model output."""
from fastapi import HTTPException
from sqlalchemy import select, text

from ..meeting_session_models import MeetingSessionEvent
from . import meeting_sessions as sessions

KINDS = {'ask': 'assistant.answer', 'live': 'assistant.live-answer'}
EVENT = 'assistant.answer-feedback'


def annotate(db, sid, kind, items):
    ids = {item['id'] for item in items if item.get('id')}
    latest = {}
    if ids:
        events = db.scalars(select(MeetingSessionEvent).where(
            MeetingSessionEvent.session_id == sid, MeetingSessionEvent.kind == EVENT,
            MeetingSessionEvent.data['answer_kind'].as_string() == kind,
            MeetingSessionEvent.data['answer_id'].as_string().in_(ids))
            .order_by(MeetingSessionEvent.id.desc()))
        for event in events:
            identity = event.data['answer_id']
            value = event.data.get('useful')
            if identity not in latest and (value is None or type(value) is bool):
                latest[identity] = value
    return [{**item, 'useful': latest.get(item.get('id'))} for item in items]


def set_feedback(db, row, kind, answer_id, useful):
    from .scoped_assistant import answer_visible
    from backend.app.services.project_operator import current_operator
    if kind not in KINDS or (useful is not None and type(useful) is not bool):
        raise HTTPException(422, 'Avis attendu : utile, pas utile ou avis retiré')
    with sessions._lock:
        db.execute(text('UPDATE meeting_sessions SET revision=revision WHERE 0'))
        sessions.get_session(db, row.id, write=True)
        answer = db.scalar(select(MeetingSessionEvent).where(
            MeetingSessionEvent.session_id == row.id, MeetingSessionEvent.kind == KINDS[kind],
            MeetingSessionEvent.data['id'].as_string() == answer_id).order_by(MeetingSessionEvent.id).limit(1))
        if answer is None or not answer_visible(db, answer.data):
            raise HTTPException(404, 'Réponse introuvable dans votre périmètre')
        previous = db.scalar(select(MeetingSessionEvent).where(
            MeetingSessionEvent.session_id == row.id, MeetingSessionEvent.kind == EVENT,
            MeetingSessionEvent.data['answer_kind'].as_string() == kind,
            MeetingSessionEvent.data['answer_id'].as_string() == answer_id)
            .order_by(MeetingSessionEvent.id.desc()).limit(1))
        if (previous.data.get('useful') if previous else None) is not useful:
            sessions.append_event(db, row, EVENT, {'answer_id': answer_id, 'answer_kind': kind,
                'answer_event_id': answer.id, 'useful': useful, 'operator_id': current_operator().id})
        db.commit()
    return {'id': answer_id, 'kind': kind, 'useful': useful}


def summary(events, allowed):
    """Count the last explicit opinion for each visible answer, never infer it."""
    latest = {}
    for event in sorted(events, key=lambda item: item.id, reverse=True):
        if event.kind != EVENT:
            continue
        data = event.data
        key = (event.session_id, KINDS.get(data.get('answer_kind')), data.get('answer_id'))
        if key not in allowed or key in latest:
            continue
        value = data.get('useful')
        if value is None or type(value) is bool:
            latest[key] = value
    return {'useful_answers': sum(value is True for value in latest.values()),
            'unhelpful_answers': sum(value is False for value in latest.values()),
            'evaluated_answers': sum(value is not None for value in latest.values())}
