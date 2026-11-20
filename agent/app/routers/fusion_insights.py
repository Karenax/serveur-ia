"""Preparation controls, measured statistics and explicit source links."""
import os
from threading import RLock
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from ..db import get_db
from ..meeting_session_schemas import Closed
from ..services import fusion_insights as insights, meeting_sessions as sessions
from ..services.settings_service import get_section, save_section
from backend.app.services.project_operator import can_manage_references, current_operator, require_reference_write

router = APIRouter(prefix='/api/v1/workspace', tags=['fusion-insights'])
_configuration_lock = RLock()


class Controls(Closed):
    enabled: bool
    live_transcription_enabled: bool = False
    proactive_enabled: bool = False
    auto_enhancement_enabled: bool = False
    mode: Literal['network', 'local'] = 'network'
    onboarding_complete: bool = False
    live_speech_device: Literal['cpu', 'cuda'] | None = None


class Backfill(Closed):
    limit: int = Field(default=100, ge=1, le=500)
    after_id: str = Field(default='', max_length=36)


class PersonalControls(Closed):
    live_transcription_enabled: bool
    proactive_enabled: bool
    auto_enhancement_enabled: bool
    mode: Literal['network', 'local']


@router.get('/fusion-settings/personal')
def personal_settings(db: Session = Depends(get_db)):
    from ..services import meeting_preferences
    return meeting_preferences.preferences(db, current_operator().id)


@router.put('/fusion-settings/personal')
def save_personal_settings(body: PersonalControls, db: Session = Depends(get_db)):
    from ..services import meeting_preferences
    values = body.model_dump()
    meeting_preferences.save(db, current_operator().id, values)
    if sessions.feature_enabled(db) and os.environ.get('AGENT_TESTING') != '1':
        if body.live_transcription_enabled:
            from ..services.live_speech import start_worker
            start_worker()
        if body.proactive_enabled or body.auto_enhancement_enabled:
            from ..services.session_proactive import start_worker
            start_worker()
    return values


def controls(db):
    value = get_section(db, 'foresight')
    from ..services.speech_acceleration import describe
    acceleration = describe(db)
    return {**{k: value.get(k, default) for k, default in {'proactive_enabled': False, 'auto_enhancement_enabled': False, 'mode': 'network', 'onboarding_complete': False}.items()},
            'live_transcription_enabled': value.get('live_transcription_enabled') is True,
            'live_speech_device': acceleration['selected'] or 'cpu', 'speech_acceleration': acceleration,
            'enabled': sessions.feature_enabled(db), 'capabilities': sessions.capabilities(db),
            'can_edit': can_manage_references(current_operator())}


@router.get('/fusion-settings')
def settings(db: Session = Depends(get_db)):
    return controls(db)


@router.put('/fusion-settings')
def configure(body: Controls, db: Session = Depends(get_db)):
    require_reference_write()
    with _configuration_lock:
        return _configure(body, db)


def _configure(body, db):
    from ..services import speech_acceleration, live_speech
    try:
        current_device = speech_acceleration.configured_device(db)
    except ValueError as exc:
        raise HTTPException(409, 'Corriger la configuration du calcul audio du service avant son réglage.') from exc
    changing_device = body.live_speech_device is not None and body.live_speech_device != current_device
    if changing_device:
        if 'PB_SPEECH_DEVICE' in os.environ:
            raise HTTPException(409, 'Le calcul audio est imposé par la configuration du service.')
        if body.live_speech_device == 'cuda':
            from pathlib import Path
            try:
                speech_acceleration.cuda_profile(Path(live_speech.ROOT) / '.models' / 'audio-medium')
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise HTTPException(422, 'Installation GPU de transcription indisponible ou incomplète.') from exc
        from ..services.audio_cpu_coordinator import _running_batch
        if _running_batch(db):
            raise HTTPException(409, 'Terminez la transcription complète avant de changer le calcul du direct.')
    if not body.enabled:
        from uuid import uuid4
        from .native_capture import perform
        from ..meeting_session_schemas import Command
        from ..services import native_audio
        for item in native_audio.status().get('active', []):
            row = sessions.get_session(db, item['session_id'], write=True)
            perform(db, row.id, 'stop', Command(command_id=str(uuid4()), expected_revision=row.revision))
    if changing_device:
        # Cancel and fence only direct ASR after other preconditions pass.
        live_speech.stop_worker()
    values = body.model_dump()
    if values['live_speech_device'] is None:
        values.pop('live_speech_device')  # Older clients preserve the explicit choice.
    save_section(db, 'foresight', values)
    # JSON equality considers 1 == True (and 0 == False). An imported old
    # non-boolean flag must still become the explicitly requested bool in SQL.
    from ..models import AppSetting
    saved = db.query(AppSetting).filter_by(key='foresight').one()
    if type(saved.value.get('live_transcription_enabled')) is not bool:
        saved.value = {**saved.value, 'live_transcription_enabled': body.live_transcription_enabled}
        flag_modified(saved, 'value')
        db.commit()
    try:
        from ..services.live_speech import start_worker as start_speech, stop_worker as stop_speech
        if sessions.live_transcription_enabled(db) and os.environ.get('AGENT_TESTING') != '1':
            start_speech()
        else:
            stop_speech()
        if body.enabled and os.environ.get('AGENT_TESTING') != '1':
            from ..services.note_evidence_bridge import start_worker
            from ..services.session_proactive import start_worker as start_proactive
            start_worker()
            start_proactive()
        elif not body.enabled:
            from ..services.session_proactive import stop_worker as stop_proactive
            stop_proactive()
    finally:
        if not body.enabled:
            from ..services.session_batch_transcription import cancel_current
            cancel_current(reason='workspace_disabled')
    return controls(db)


@router.get('/fusion-settings/readiness')
def readiness(db: Session = Depends(get_db)):
    require_reference_write()
    from ..services.fusion_readiness import snapshot
    return snapshot(db)


@router.post('/fusion-settings/readiness/probe')
def probe_readiness(db: Session = Depends(get_db)):
    require_reference_write()
    from ..services.fusion_readiness import probe_generation
    try:
        return probe_generation(db)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post('/fusion-settings/readiness/generation-test')
def test_readiness_generation(db: Session = Depends(get_db)):
    require_reference_write()
    from ..services.fusion_readiness import test_generation
    try:
        return test_generation(db)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get('/source-graph')
def graph(project_id: str | None = None, limit: int = Query(300, ge=1, le=500),
          offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return insights.graph(db, project_id, limit, offset)


@router.get('/fusion-stats')
def stats(project_id: str | None = None, db: Session = Depends(get_db)):
    return insights.stats(db, project_id)


@router.post('/fusion-settings/note-backfill')
def backfill(body: Backfill, db: Session = Depends(get_db)):
    require_reference_write()
    sessions.require_enabled(db)
    from backend.app.db import SessionLocal
    from backend.app.services.note_evidence_outbox import backfill as backfill_notes
    with SessionLocal() as erp:
        result = backfill_notes(erp, limit=body.limit, after_id=body.after_id)
        erp.commit()
    return result


@router.get('/indexing')
def indexing(project_id: str | None = None, db: Session = Depends(get_db)):
    from ..services.project_indexing import snapshot
    return snapshot(db, project_id)
