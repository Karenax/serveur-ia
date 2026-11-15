"""Retain one explicitly selected ICS event as bounded, versioned context."""
import hashlib

from fastapi import HTTPException
from pydantic import ValidationError

from ..meeting_session_schemas import Command
from . import meeting_sessions as sessions
from .source_connectors import calendar_preview


def attach_context(db, sid, raw, uid, command_id, expected_revision):
    sessions.require_enabled(db)
    row = sessions.get_session(db, sid, write=True)
    try:
        Command(command_id=command_id, expected_revision=expected_revision)
    except ValidationError as exc:
        raise HTTPException(422, 'UUID de commande et révision valide requis') from exc
    preview = calendar_preview(raw)
    matches = [event for event in preview['events'] if event['uid'] == uid]
    if len(matches) != 1:
        raise HTTPException(422, 'Choisir un UID unique dans le calendrier importé')
    value = {'command_id': command_id, 'expected_revision': expected_revision, 'uid': uid,
             'sha256': hashlib.sha256(raw).hexdigest()}
    with sessions._lock:
        command = sessions._begin(db, row, 'calendar-context', value, server_data={'calendar': matches[0]})
        if command.status == 'completed':
            return command.result
        event = command.body['calendar']
        sessions.append_event(db, row, 'calendar.context', {**event, 'origin': 'human_selected_ics',
                              'sha256': value['sha256'], 'context_only': True})
        return sessions._finish(db, row, command, 'session.calendar-attached', {'uid': uid})
