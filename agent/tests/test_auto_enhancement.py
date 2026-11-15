"""Saved snapshots stabilize before one opt-in, cited, human-reviewed proposal."""
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import timedelta
from threading import Barrier, Event, get_ident

from fastapi import HTTPException
import pytest
from sqlalchemy import func, select, text

from app.meeting_session_models import LiveTranscriptSegment, MeetingSessionEvent
from app.services import meeting_sessions as sessions, session_enhancements as enhancements, session_proactive as worker
from app.services import scoped_assistant as assistant, inference_scheduler as scheduler
from app.services.settings_service import save_section
from backend.app.project_note_models import NoteVersion
from backend.app.services.project_operator import Operator, operator_context
from tests.test_session_assistant import stores as stores_fixture, enable, note_session, model
from tests.test_session_assistant import enhancement_session, enhancement_reply, enhancement_model
from tests.test_meeting_sessions import command, content, key, create

stores = stores_fixture


@pytest.fixture(autouse=True)
def stopped_worker():
    worker._stop.clear()
    yield
    worker._stop.clear()


def seed(stores, *, enabled=True, questions=False, project=True):
    brain, _, pid, _ = stores
    with brain() as db:
        enable(db)
        save_section(db, 'foresight', {'auto_enhancement_enabled': enabled, 'proactive_enabled': questions})
        session_fixture = enhancement_session if enabled else note_session
        row, _ = session_fixture(db, pid if project else None)
        return row.id


def settle(brain, sid, age=9):
    with brain() as db:
        observed = db.scalar(select(MeetingSessionEvent).where(MeetingSessionEvent.session_id == sid,
                MeetingSessionEvent.kind == 'enhancement.auto-observed').order_by(MeetingSessionEvent.id.desc()))
        assert observed is not None
        observed.created_at = sessions.now() - timedelta(seconds=age)
        db.commit()


def events(brain, kind):
    with brain() as db:
        return [dict(row.data) for row in db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == kind))]


def test_opt_in_defaults_off_even_with_questions_enabled(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores, enabled=False, questions=True)
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('opt-in required'))
    worker.tick()
    assert not events(brain, 'enhancement.auto-observed')
    with brain() as db:
        status = enhancements.list_proposals(db, sessions.get_session(db, sid))['automatic']
        assert not status['enabled'] and status['state'] == 'disabled'
    from app.routers.fusion_insights import Controls
    assert Controls(enabled=True).auto_enhancement_enabled is False


def test_stability_eight_seconds_saved_version_and_restart_no_duplicate(stores, monkeypatch):
    brain, erp, pid, _ = stores
    sid = seed(stores)
    calls = []
    def generate(cfg, messages, **kwargs):
        calls.append(kwargs)
        assert kwargs['timeout'] == 600 and kwargs['raise_errors'] is True
        assert kwargs['retry_empty'] is False and cfg['fallback_enabled'] is False and cfg['fallback_autostart'] is False
        assert scheduler.waiting_policy() == (900, worker._stop)
        assert 'Réserve humaine de 50 euros.' in messages[-1]['content']
        return enhancement_reply(messages)
    model(monkeypatch, generate)
    worker.tick()
    settle(brain, sid, 7)
    worker.tick()
    assert not calls
    settle(brain, sid, 9)
    worker.tick()
    worker.tick()  # A new DB context simulates the next worker/restart tick.
    assert len(calls) == 1 and len(events(brain, 'enhancement.auto-attempt')) == 1
    with brain() as db:
        row = sessions.get_session(db, sid)
        proposal = enhancements.list_proposals(db, row)
        assert proposal['automatic']['state'] == 'completed'
        assert proposal['items'][0]['status'] == 'pending'
        assert sessions.session_note(db, row)['content']['blocks'] == content('Réserve humaine de 50 euros.').model_dump()['blocks']
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion).where(NoteVersion.project_id == pid)) == 1


def test_snapshot_change_resets_stability_and_old_result_is_obsolete(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    def generate(cfg, messages, **kwargs):
        with brain() as other:
            row = sessions.get_session(other, sid)
            note = sessions.session_note(other, row)
            command(other, sid, 'notes', row.revision, title='Modification humaine', content=content('Ne pas publier : 250 W provisoires.'),
                    expected_note_revision=note['revision'], expected_note_version_id=note['version_id'])
        return enhancement_reply(messages, 'Ancien contexte.')
    model(monkeypatch, generate)
    worker.tick()
    with brain() as db:
        proposals = enhancements.list_proposals(db, sessions.get_session(db, sid))
        assert proposals['items'][0]['status'] == 'obsolete' and proposals['automatic']['state'] == 'waiting'
    worker.tick()
    assert len(events(brain, 'enhancement.auto-observed')) == 2
    assert len(events(brain, 'enhancement.auto-attempt')) == 1


def test_question_priority_across_sessions_one_total_ai_action(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores, questions=True)
    with brain() as db:
        other = create(db)
        command(db, other['id'], 'resume', 1)
        db.add(LiveTranscriptSegment(id=key(), session_id=other['id'], track='mic', start_ms=0, end_ms=1000,
            speaker='MIC', text='Qui relit le devis ?'))
        db.commit()
    # Establish an old stable candidate without generating before the question.
    with brain() as db:
        stamp = assistant.session_snapshot(db, sessions.get_session(db, sid))[0]
        db.add(MeetingSessionEvent(session_id=sid, kind='enhancement.auto-observed', revision=2,
            data={'stamp': stamp}, created_at=sessions.now() - timedelta(seconds=9)))
        db.commit()
    calls = []
    async def answer(db, row, **kwargs):
        calls.append(('question', row.id))
    async def propose(db, row, **kwargs):
        calls.append(('enhancement', row.id))
        return {'id':'proposal', 'status':'pending'}
    monkeypatch.setattr(assistant, 'answer', answer)
    monkeypatch.setattr(enhancements, 'propose', propose)
    worker.tick()
    assert calls == [('question', other['id'])]
    worker.tick()
    assert calls == [('question', other['id']), ('enhancement', sid)]


def test_concurrent_ticks_reserve_once_and_do_not_queue_duplicate_work(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    entered, release = Event(), Event()
    calls = []
    async def propose(db, row, **kwargs):
        calls.append(row.id)
        entered.set()
        assert release.wait(3)
        return {'id':'proposal', 'status':'pending'}
    monkeypatch.setattr(enhancements, 'propose', propose)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(worker.tick)
        assert entered.wait(2)
        pool.submit(worker.tick).result(timeout=2)
        release.set()
        first.result(timeout=3)
    worker.tick()
    assert calls == [sid] and len(events(brain, 'enhancement.auto-attempt')) == 1


def test_failure_visible_no_automatic_loop_manual_retry(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    model(monkeypatch, lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('Transport indisponible')))
    worker.tick()
    worker.tick()
    assert len(events(brain, 'enhancement.auto-attempt')) == 1
    with brain() as db:
        row = sessions.get_session(db, sid)
        state = enhancements.list_proposals(db, row)['automatic']
        assert state['state'] == 'failed' and 'Transport indisponible' in state['error']
        model(monkeypatch, '{"additions":[]}')
        asyncio.run(enhancements.propose(db, row))  # Deliberate retry, no human note mutation.
        assert enhancements.list_proposals(db, row)['automatic']['state'] == 'completed'


@pytest.mark.parametrize('admission', ['engine', 'background'])
def test_queue_refusal_waits_then_recovers_same_saved_snapshot(stores, monkeypatch, admission):
    from app.services.llm_activity import Deferred
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    refusal = scheduler.InferenceBusy('Moteur occupé') if admission == 'engine' else Deferred('Activité de fond occupée')
    model(monkeypatch, lambda *args, **kwargs: (_ for _ in ()).throw(refusal))
    worker.tick()
    worker.tick()
    assert len(events(brain, 'enhancement.auto-attempt')) == 1
    with brain() as db:
        row = sessions.get_session(db, sid)
        state = enhancements.list_proposals(db, row)['automatic']
        assert state['state'] == 'waiting' and state['error'] is None
        assert state['retry_after_seconds'] > 0
        failure = worker._event(db, sid, 'enhancement.auto-error')
        assert failure.data['retryable'] is True
        failure.created_at = sessions.now() - timedelta(seconds=worker.ADMISSION_RETRY_SECONDS + 1)
        db.commit()
    model(monkeypatch, '{"additions":[]}')
    worker.tick()
    worker.tick()
    attempts = events(brain, 'enhancement.auto-attempt')
    assert len(attempts) == 2 and attempts[1]['admission_retries'] == 1
    assert attempts[0]['attempt_id'] != attempts[1]['attempt_id']
    with brain() as db:
        row = sessions.get_session(db, sid)
        assert enhancements.list_proposals(db, row)['automatic']['state'] == 'completed'
        assert sessions.session_note(db, row)['plain_text'] == 'Réserve humaine de 50 euros.'


def test_legacy_queue_only_error_is_recoverable_without_changing_audit(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    with brain() as db:
        row = sessions.get_session(db, sid)
        stamp, attempt = worker._observe(db, row)
        data = {'stamp': stamp, 'attempt_id': attempt,
                'error': 'Activité IA de fond occupée ; délai d’attente dépassé'}
        failure = sessions.append_event(db, row, 'enhancement.auto-error', data)
        failure.created_at = sessions.now() - timedelta(seconds=16)
        db.commit()
        failure_id = failure.id
        assert enhancements.list_proposals(db, row)['automatic']['state'] == 'waiting'
    model(monkeypatch, '{"additions":[]}')
    worker.tick()
    with brain() as db:
        assert db.get(MeetingSessionEvent, failure_id).data == data
        assert enhancements.list_proposals(db, sessions.get_session(db, sid))['automatic']['state'] == 'completed'


def test_new_admission_attempt_does_not_report_previous_failure_or_repeat_after_crash(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    with brain() as db:
        row = sessions.get_session(db, sid)
        stamp, attempt = worker._observe(db, row)
        failure = sessions.append_event(db, row, 'enhancement.auto-error', {
            'stamp': stamp, 'attempt_id': attempt, 'error': 'File occupée', 'retryable': True})
        failure.created_at = sessions.now() - timedelta(seconds=16)
        db.commit()
        assert worker._observe(db, row) is not None
        assert enhancements.list_proposals(db, row)['automatic']['state'] == 'running'
        latest = worker._event(db, sid, 'enhancement.auto-attempt', stamp=stamp)
        latest.created_at = sessions.now() - timedelta(seconds=3600)
        db.commit()
        assert enhancements.list_proposals(db, row)['automatic']['state'] == 'failed'
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('Unconfirmed generation must not repeat'))
    worker.tick()
    assert len(events(brain, 'enhancement.auto-attempt')) == 2


@pytest.mark.parametrize('response', ['busy', 'empty'])
def test_manual_enhancement_has_foreground_priority_and_clear_recoverable_error(stores, monkeypatch, response):
    brain, _, _, _ = stores
    sid = seed(stores)
    def generate(*args, **kwargs):
        assert scheduler.current_priority() == scheduler.PRIORITIES['manual']
        assert scheduler.waiting_policy() == (900, None)
        assert kwargs['raise_errors'] is True
        if response == 'busy':
            raise scheduler.InferenceBusy('File occupée')
        return None
    model(monkeypatch, generate)
    with brain() as db:
        row = sessions.get_session(db, sid)
        note_version = sessions.session_note(db, row)['version_id']
        with pytest.raises(HTTPException) as caught:
            asyncio.run(enhancements.propose(db, row))
        assert caught.value.status_code == (503 if response == 'busy' else 502)
        assert 'notes sont conservées' in caught.value.detail
        assert sessions.session_note(db, row)['version_id'] == note_version
        assert enhancements.list_proposals(db, row)['items'] == []
    assert scheduler.waiting_policy() == (None, None)


@pytest.mark.parametrize('operator', [Operator('local','reader'), Operator('local','editor',frozenset())])
def test_reader_and_out_of_scope_cannot_reserve_or_generate(stores, monkeypatch, operator):
    brain, _, _, _ = stores
    seed(stores)
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('unauthorized generation'))
    with operator_context(operator):
        worker.tick()
    assert not events(brain, 'enhancement.auto-observed')


def test_stop_while_waiting_removes_reservation_waiter_without_generation(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    entered = Event()
    resource = 'test-auto-' + key()
    def generate(*args, **kwargs):
        entered.set()
        with scheduler.lease(resource):
            pytest.fail('cancelled generation admitted')
    model(monkeypatch, generate)
    with scheduler.lease(resource), ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker.tick)
        assert entered.wait(2)
        worker.stop_worker()
        future.result(timeout=3)
    assert scheduler.status()['waiting'] == 0
    assert 'annulée' in events(brain, 'enhancement.auto-error')[0]['error']
    with brain() as db:
        assert enhancements.list_proposals(db, sessions.get_session(db, sid))['automatic']['state'] == 'stopped'


def test_saved_staging_is_stable_and_revised_segments_require_new_observation(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores, project=False)
    worker.tick()
    settle(brain, sid)
    with brain() as db:
        db.add(LiveTranscriptSegment(id=key(),session_id=sid,track='mic',start_ms=0,end_ms=2000,speaker='MIC',text='Ne pas confirmer IP65.'))
        db.commit()
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('new segment not stable'))
    worker.tick()
    assert len(events(brain,'enhancement.auto-observed')) == 2
    assert not events(brain,'enhancement.auto-attempt')


def test_stale_reservation_before_generation_is_refused_and_crash_is_not_replayed(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    with brain() as db:
        row = sessions.get_session(db,sid)
        stamp, attempt = worker._observe(db,row)
        event = worker._event(db,sid,'enhancement.auto-attempt',stamp=stamp)
        event.created_at = sessions.now() - timedelta(seconds=(
            worker.GENERATION_TIMEOUT_SECONDS + worker.QUEUE_WAIT_SECONDS + worker.TICK_SECONDS + 1))
        db.commit()
        status = enhancements.list_proposals(db,row)['automatic']
        assert status['state'] == 'failed' and status['attempt_id'] == attempt
        with pytest.raises(HTTPException,match='contexte enregistré a changé'):
            asyncio.run(enhancements.propose(db,row,automatic=True,expected_stamp='outdated-stamp'))
    model(monkeypatch,lambda *args,**kwargs:pytest.fail('reserved crash must not repeat'))
    worker.tick()
    assert len(events(brain,'enhancement.auto-attempt')) == 1


def test_sql_writer_lock_dedupes_two_independent_session_reservations(stores):
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    barrier = Barrier(2)
    def reserve():
        with brain() as db:
            row = sessions.get_session(db, sid)
            barrier.wait(timeout=5)
            return worker._observe(db, row)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert len(events(brain, 'enhancement.auto-attempt')) == 1


def test_stop_start_during_live_tick_rearms_same_worker_without_overlap(monkeypatch):
    monkeypatch.delenv('AGENT_TESTING')
    monkeypatch.setattr(worker, 'TICK_SECONDS', .01)
    entered, release, continued = Event(), Event(), Event()
    ids = []
    def tick():
        ids.append(get_ident())
        if len(ids) == 1:
            entered.set()
            assert release.wait(5)
        else:
            continued.set()
    monkeypatch.setattr(worker, 'tick', tick)
    worker.start_worker()
    thread = worker._thread
    try:
        assert entered.wait(3)
        worker.stop_worker()
        worker.start_worker()
        assert worker._thread is thread and not worker._stop.is_set()
        release.set()
        assert continued.wait(3)
        assert len(set(ids)) == 1
    finally:
        release.set()
        worker.stop_worker()
        thread.join(timeout=3)
    assert not thread.is_alive() and not worker.status()['worker_running']


def test_actual_text_client_keeps_legacy_blank_retry_but_automatic_is_one_call(monkeypatch):
    from app.services import ai_client
    cfg = {'enabled': True, 'provider': 'openai_compatible', 'base_url': 'http://127.0.0.1:1234', 'model': 'fictif', 'fallback_enabled': False}
    calls = []
    monkeypatch.setattr(ai_client.ai_routing, 'resolve', lambda value: value)
    def transport(config, url, payload, headers, *, timeout):
        calls.append((payload['max_tokens'], timeout))
        return {'choices': [{'message': {'content': '' if len(calls) == 1 else 'Réponse héritée.'}}]}
    monkeypatch.setattr(ai_client, '_post_llm', transport)
    assert ai_client.chat_text(cfg, [], max_tokens=1800, timeout=45) == 'Réponse héritée.'
    assert calls == [(1800,45),(3600,45)]
    calls.clear()
    assert ai_client.chat_text(cfg, [], max_tokens=1800, timeout=45, raise_errors=True, retry_empty=False) is None
    assert calls == [(1800,45)]


def test_transport_age_is_not_misreported_as_crash_while_attempt_is_active(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    with brain() as db:
        row = sessions.get_session(db, sid)
        stamp, attempt = worker._observe(db, row)
        event = worker._event(db, sid, 'enhancement.auto-attempt', stamp=stamp)
        event.created_at = sessions.now() - timedelta(seconds=3600)
        db.commit()
        monkeypatch.setattr(worker, '_active_attempt', attempt)
        assert enhancements.list_proposals(db, row)['automatic']['state'] == 'running'
        monkeypatch.setattr(worker, '_active_attempt', None)
        assert enhancements.list_proposals(db, row)['automatic']['state'] == 'failed'


def move_out_of_scope(brain, sid):
    with brain() as other:
        other.execute(text('UPDATE meeting_sessions SET project_id=:project, brain_project_id=NULL, revision=revision+1 WHERE id=:sid'),
                      {'project': 'private-other-project', 'sid': sid})
        other.commit()


def test_observation_rechecks_write_scope_on_refreshed_session(stores):
    brain, _, pid, _ = stores
    sid = seed(stores)
    with operator_context(Operator('local', 'editor', frozenset([pid]))), brain() as db:
        cached = sessions.get_session(db, sid, write=True)
        move_out_of_scope(brain, sid)
        with pytest.raises(HTTPException) as caught:
            worker._observe(db, cached)
        assert caught.value.status_code == 404
        db.rollback()
    assert not events(brain, 'enhancement.auto-observed')


@pytest.mark.parametrize('change', ['scope', 'completed', 'finalizing', 'pending', 'question_corrected'])
def test_question_reservation_uses_current_rights_state_and_text(stores, monkeypatch, change):
    brain, _, pid, _ = stores
    sid = seed(stores, enabled=False, questions=True)
    segment_id = key()
    with brain() as db:
        command(db, sid, 'resume', sessions.get_session(db, sid).revision)
        db.add(LiveTranscriptSegment(id=segment_id, session_id=sid, track='mic', start_ms=0, end_ms=1000,
                                    speaker='MIC', text='Faut-il publier 250 W ?'))
        db.commit()
    changed = False
    def worker_session():
        db = brain()
        original_execute = db.execute
        def execute(statement, *args, **kwargs):
            nonlocal changed
            # Simulate another connection committing after the listing and
            # question read, but before this worker obtains SQLite's writer.
            if not changed and str(statement) == 'UPDATE meeting_sessions SET revision=revision WHERE 0':
                changed = True
                with brain() as other:
                    if change == 'scope':
                        other.execute(text('UPDATE meeting_sessions SET project_id=:project, brain_project_id=NULL, revision=revision+1 WHERE id=:sid'),
                                      {'project': 'private-other-project', 'sid': sid})
                    elif change == 'pending':
                        other.execute(text('UPDATE meeting_sessions SET pending_command_id=:command, revision=revision+1 WHERE id=:sid'),
                                      {'command': key(), 'sid': sid})
                    elif change == 'question_corrected':
                        other.execute(text('UPDATE meeting_live_segments SET text=:value, revision=revision+1 WHERE id=:id'),
                                      {'value': 'Ne pas publier 250 W.', 'id': segment_id})
                    else:
                        other.execute(text('UPDATE meeting_sessions SET state=:state, revision=revision+1 WHERE id=:sid'),
                                      {'state': change, 'sid': sid})
                    other.commit()
            return original_execute(statement, *args, **kwargs)
        db.execute = execute
        return db
    async def forbidden(*args, **kwargs):
        pytest.fail('question changed before reservation must not reach inference')
    monkeypatch.setattr('app.db.SessionLocal', worker_session)
    monkeypatch.setattr(assistant, 'answer', forbidden)
    with operator_context(Operator('local', 'editor', frozenset([pid]))):
        worker.tick()
    assert changed and not events(brain, 'assistant.proactive-attempt')
    assert not events(brain, 'assistant.proactive-error')


@pytest.mark.parametrize('result', ['success', 'failure'])
def test_generation_cannot_record_proposal_or_outcome_after_scope_revocation(stores, monkeypatch, result):
    brain, _, pid, _ = stores
    sid = seed(stores)
    worker.tick()
    settle(brain, sid)
    def generate(cfg, messages, **kwargs):
        move_out_of_scope(brain, sid)
        if result == 'failure':
            raise RuntimeError('Transport failed after the project changed')
        return enhancement_reply(messages, 'Ancien contexte.')
    model(monkeypatch, generate)
    with operator_context(Operator('local', 'editor', frozenset([pid]))):
        worker.tick()
    # The authorized reservation remains a receipt; no unauthorized terminal
    # event or proposal is written on the now-private session.
    assert len(events(brain, 'enhancement.auto-attempt')) == 1
    assert not events(brain, 'enhancement.proposed')
    assert not events(brain, 'enhancement.auto-finished')
    assert not events(brain, 'enhancement.auto-error')


def test_enhancement_rechecks_cached_session_before_generation(stores, monkeypatch):
    brain, _, pid, _ = stores
    sid = seed(stores)
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('cached rights must not permit inference'))
    with operator_context(Operator('local', 'editor', frozenset([pid]))), brain() as db:
        row = sessions.get_session(db, sid, write=True)
        move_out_of_scope(brain, sid)
        with pytest.raises(HTTPException) as caught:
            asyncio.run(enhancements.propose(db, row, automatic=True))
        assert caught.value.status_code == 404
    assert not events(brain, 'enhancement.proposed')


def segment_proposal(stores, monkeypatch):
    brain, _, pid, _ = stores
    model(monkeypatch, lambda cfg, messages, **kwargs:
          enhancement_reply(messages, 'Réserve à conserver.', evidence='Ne pas publier', quote='Ne pas publier'))
    with brain() as db:
        enable(db)
        sid = create(db, project_id=pid)['id']
        db.add(LiveTranscriptSegment(id=key(), session_id=sid, track='mic', start_ms=0, end_ms=1000,
                                    speaker='MIC', text='Ne pas publier 250 W.'))
        db.commit()
        asyncio.run(enhancements.propose(db, sessions.get_session(db, sid)))
    return sid


def test_proposal_listing_rechecks_scope_after_snapshot_refresh(stores, monkeypatch):
    brain, _, pid, _ = stores
    sid = segment_proposal(stores, monkeypatch)
    original_current = assistant.context_current
    moved = False
    def context_current(db, row, metadata):
        nonlocal moved
        if not moved:
            moved = True
            move_out_of_scope(brain, sid)
        return original_current(db, row, metadata)
    monkeypatch.setattr(assistant, 'context_current', context_current)
    with operator_context(Operator('local', 'editor', frozenset([pid]))), brain() as db:
        row = sessions.get_session(db, sid)
        with pytest.raises(HTTPException) as caught:
            enhancements.list_proposals(db, row)
        assert moved and caught.value.status_code == 404


def test_proposal_replay_cannot_return_old_excerpt_after_scope_revocation(stores, monkeypatch):
    brain, _, pid, _ = stores
    sid = segment_proposal(stores, monkeypatch)
    model(monkeypatch, lambda *args, **kwargs: pytest.fail('cached replay must not generate'))
    original_list = enhancements.list_proposals
    def list_after_move(db, row):
        move_out_of_scope(brain, sid)
        return original_list(db, row)
    monkeypatch.setattr(enhancements, 'list_proposals', list_after_move)
    with operator_context(Operator('local', 'editor', frozenset([pid]))), brain() as db:
        row = sessions.get_session(db, sid)
        with pytest.raises(HTTPException) as caught:
            asyncio.run(enhancements.propose(db, row))
        assert caught.value.status_code == 404
    assert len(events(brain, 'enhancement.proposed')) == 1


def test_proposal_from_original_project_is_hidden_from_new_scope(stores, monkeypatch):
    brain, _, _, _ = stores
    sid = segment_proposal(stores, monkeypatch)
    move_out_of_scope(brain, sid)
    with operator_context(Operator('local', 'editor', frozenset(['private-other-project']))), brain() as db:
        row = sessions.get_session(db, sid)
        assert enhancements.list_proposals(db, row)['items'] == []


@pytest.mark.parametrize('change, status', [('scope', 404), ('revision', 409)])
def test_reject_rechecks_rights_and_revision_at_writer(stores, monkeypatch, change, status):
    brain, _, pid, _ = stores
    sid = segment_proposal(stores, monkeypatch)
    original_find = enhancements._find
    changed = False
    def find_then_change(db, row, kind, identity):
        nonlocal changed
        found = original_find(db, row, kind, identity)
        if kind == 'enhancement.proposed' and not changed:
            changed = True
            if change == 'scope':
                move_out_of_scope(brain, sid)
            else:
                with brain() as other:
                    other.execute(text('UPDATE meeting_sessions SET revision=revision+1 WHERE id=:sid'), {'sid': sid})
                    other.commit()
        return found
    monkeypatch.setattr(enhancements, '_find', find_then_change)
    proposal = events(brain, 'enhancement.proposed')[0]
    with operator_context(Operator('local', 'editor', frozenset([pid]))), brain() as db:
        row = sessions.get_session(db, sid)
        with pytest.raises(HTTPException) as caught:
            enhancements.decide(db, row, proposal['id'], 'reject', row.revision)
        assert changed and caught.value.status_code == status
        db.rollback()
    assert not events(brain, 'enhancement.decision')


def test_reject_replay_rechecks_scope_before_return(stores, monkeypatch):
    brain, _, pid, _ = stores
    sid = segment_proposal(stores, monkeypatch)
    proposal = events(brain, 'enhancement.proposed')[0]
    with brain() as db:
        row = sessions.get_session(db, sid)
        enhancements.decide(db, row, proposal['id'], 'reject', row.revision)
    original_find = enhancements._find
    def find_then_move(db, row, kind, identity):
        found = original_find(db, row, kind, identity)
        if kind == 'enhancement.decision':
            move_out_of_scope(brain, sid)
        return found
    monkeypatch.setattr(enhancements, '_find', find_then_move)
    with operator_context(Operator('local', 'editor', frozenset([pid]))), brain() as db:
        row = sessions.get_session(db, sid)
        with pytest.raises(HTTPException) as caught:
            enhancements.decide(db, row, proposal['id'], 'reject', row.revision)
        assert caught.value.status_code == 404
    assert len(events(brain, 'enhancement.decision')) == 1


@pytest.mark.parametrize('first_decision', ['accept', 'reject'])
def test_accept_and_reject_are_serialized_before_any_note_mutation(stores, monkeypatch, first_decision):
    brain, erp, pid, _ = stores
    sid = seed(stores)
    enhancement_model(monkeypatch, 'Ajout relu.')
    with brain() as db:
        row = sessions.get_session(db, sid)
        proposal = asyncio.run(enhancements.propose(db, row))
        revision = row.revision
    original_find = enhancements._find
    entered, release, second_started = Event(), Event(), Event()
    held = False
    def hold_first_lookup(db, row, kind, identity):
        nonlocal held
        found = original_find(db, row, kind, identity)
        if kind == 'enhancement.proposed' and not held:
            held = True
            entered.set()
            assert release.wait(5)
        return found
    monkeypatch.setattr(enhancements, '_find', hold_first_lookup)
    def decide(decision, second=False):
        with brain() as db:
            row = sessions.get_session(db, sid)
            if second:
                second_started.set()
            try:
                enhancements.decide(db, row, proposal['id'], decision, revision)
                return 'saved'
            except HTTPException as exc:
                return exc.status_code
    second_decision = 'reject' if first_decision == 'accept' else 'accept'
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(decide, first_decision)
        assert entered.wait(3)
        second = pool.submit(decide, second_decision, True)
        assert second_started.wait(3)
        try:
            with pytest.raises(FutureTimeout):
                second.result(timeout=.1)
            assert not events(brain, 'enhancement.decision')
            with erp() as db:
                assert db.scalar(select(func.count()).select_from(NoteVersion).where(NoteVersion.project_id == pid)) == 1
        finally:
            release.set()
        assert first.result(timeout=5) == 'saved'
        assert second.result(timeout=5) == 409
    decision = events(brain, 'enhancement.decision')
    assert len(decision) == 1 and decision[0]['decision'] == ('accepted' if first_decision == 'accept' else 'rejected')
    with erp() as db:
        assert db.scalar(select(func.count()).select_from(NoteVersion).where(NoteVersion.project_id == pid)) == (2 if first_decision == 'accept' else 1)
    with brain() as db:
        note = sessions.session_note(db, sessions.get_session(db, sid))
        assert note['content']['blocks'][0] == content('Réserve humaine de 50 euros.').model_dump()['blocks'][0]
        assert len(note['content']['blocks']) == (2 if first_decision == 'accept' else 1)
