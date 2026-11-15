"""Provider counters, failed-attempt coverage and async answer persistence."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier
import urllib.error

import pytest

from app.services import ai_client, ai_routing, llm_usage, scoped_assistant
from app.meeting_session_models import MeetingSessionEvent
from sqlalchemy import select
from tests.test_meeting_sessions import stores as stores_fixture
from tests.test_session_assistant import note_session

stores = stores_fixture


@pytest.mark.parametrize('value', [None, True, False, -1, '12', 1.5, {}, []])
def test_invalid_counts_are_unavailable_not_estimated(value):
    result = llm_usage.normalize('openai_compatible', {'usage': {'total_tokens': value}})
    assert result['total_tokens'] is None


def test_reported_totals_and_only_reported_components_are_counted():
    assert llm_usage.normalize('openai_compatible', {'usage': {'total_tokens': 0}})['total_tokens'] == 0
    assert llm_usage.normalize('openai_compatible', {'usage': {'total_tokens': 30}})['total_tokens'] == 30
    partial = llm_usage.normalize('openai_compatible', {'usage': {'prompt_tokens': 20}})
    assert partial['total_tokens'] is None
    derived = llm_usage.normalize('ollama', {'prompt_eval_count': 20, 'eval_count': 10})
    assert derived['total_tokens'] == 30 and derived['total_formula'] == 'reported_prompt_plus_completion'
    bad = llm_usage.normalize('openai_compatible', {'usage': {'prompt_tokens': 20, 'completion_tokens': 10, 'total_tokens': 99}})
    assert bad['inconsistent'] and bad['total_tokens'] is None


def configure(monkeypatch):
    monkeypatch.setattr(ai_routing, 'resolve', lambda cfg: cfg)
    monkeypatch.setattr(ai_routing, 'primary_succeeded', lambda *args: None)
    return {'enabled': True, 'provider': 'openai_compatible', 'base_url': 'http://127.0.0.1:9',
            'model': 'fictif', 'fallback_enabled': False}


def test_empty_retry_keeps_both_reported_token_costs_without_changing_payload(monkeypatch):
    cfg = configure(monkeypatch)
    responses = iter([{'choices': [{'message': {'content': ''}}], 'usage': {'total_tokens': 30}},
                      {'choices': [{'message': {'content': 'Réponse'}}], 'usage': {'total_tokens': 10}}])
    calls = []
    def post(url, payload, **kwargs):
        calls.append(payload)
        return next(responses)
    monkeypatch.setattr(ai_client, '_post_json', post)
    with llm_usage.collect() as attempts:
        assert ai_client.chat_text(cfg, [], max_tokens=12) == 'Réponse'
    result = llm_usage.summarize(attempts)
    assert result['complete'] and result['measured_tokens'] == 40
    assert result['total_attempts'] == 2
    assert [row['max_tokens'] for row in calls] == [12, 24]
    assert all(row['reasoning_effort'] == 'none' and row['chat_template_kwargs'] == {'enable_thinking': False} for row in calls)


def test_failed_attempt_and_missing_usage_stay_unknown_and_do_not_store_sensitive_text(monkeypatch):
    cfg = configure(monkeypatch)
    def post(*args, **kwargs):
        raise urllib.error.URLError('PRIVATE-ERROR-AND-CREDENTIAL')
    monkeypatch.setattr(ai_client, '_post_json', post)
    with llm_usage.collect() as attempts:
        assert ai_client.chat_text(cfg, [{'role': 'user', 'content': 'PRIVATE-PROMPT'}]) is None
    result = llm_usage.summarize(attempts)
    assert not result['complete'] and result['measured_tokens'] is None
    assert attempts[0]['error_type'] == 'URLError'
    assert 'PRIVATE' not in json.dumps(result)
    monkeypatch.setattr(ai_client, '_post_json', lambda *args, **kwargs: {'choices': [{'message': {'content': 'Réponse'}}]})
    with llm_usage.collect() as unmeasured:
        assert ai_client.chat_text(cfg, []) == 'Réponse'
    assert llm_usage.summarize(unmeasured)['measured_tokens'] is None


def test_primary_failure_and_local_fallback_preserve_unknown_coverage_and_actual_provider(monkeypatch):
    from contextlib import nullcontext
    cfg = configure(monkeypatch)
    cfg.update(fallback_enabled=True)
    monkeypatch.setattr(ai_routing, 'local_config', lambda cfg: {'provider': 'openai_compatible', 'base_url': 'http://127.0.0.1:10', 'model': 'rescue'})
    monkeypatch.setattr(ai_routing, 'local_generation', lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(ai_routing, 'unavailable', lambda *args: None)
    def post(url, *args, **kwargs):
        if ':9/' in url:
            raise urllib.error.URLError('offline')
        return {'choices': [{'message': {'content': 'Secours'}}], 'usage': {'total_tokens': 8}}
    monkeypatch.setattr(ai_client, '_post_json', post)
    with llm_usage.collect() as attempts:
        assert ai_client.chat_text(cfg, []) == 'Secours'
    result = llm_usage.summarize(attempts)
    assert result['measured_tokens'] == 8 and not result['complete']
    assert [row['model'] for row in attempts] == ['fictif', 'rescue']


def test_collectors_are_isolated_between_threads_and_restore_outer_collection():
    barrier = Barrier(2)
    def measured(value):
        with llm_usage.collect() as attempts:
            barrier.wait()
            with llm_usage.observe_request('openai_compatible', 'fictif') as received:
                received({'usage': {'total_tokens': value}})
            return llm_usage.summarize(attempts)['measured_tokens']
    with ThreadPoolExecutor(2) as executor:
        left, right = executor.submit(measured, 5), executor.submit(measured, 9)
        assert (left.result(), right.result()) == (5, 9)
    with llm_usage.collect() as outer:
        with llm_usage.collect() as inner:
            with llm_usage.observe_request('ollama', 'fictif') as received:
                received({'prompt_eval_count': 2, 'eval_count': 3})
        assert len(inner) == 1 and not outer
        with llm_usage.observe_request('openai_compatible', 'fictif') as received:
            received({'usage': {'total_tokens': 7}})
        assert llm_usage.summarize(outer)['measured_tokens'] == 7


def test_partial_history_aggregation_does_not_turn_missing_usage_into_zero():
    result = llm_usage.aggregate([{'usage': {'measured_tokens': 12, 'complete': True}},
        {'usage': {'measured_tokens': 5, 'complete': False}}, {}, {'usage': None}])
    assert result == {'tokens': 17, 'token_complete_answers': 1, 'token_partial_answers': 1,
                      'token_unmeasured_answers': 2, 'token_total_answers': 4}
    assert llm_usage.aggregate([{}, {'usage': None}])['tokens'] is None


def test_async_answer_persists_measured_usage_and_replay_does_not_call_model(stores, monkeypatch):
    brain, _, pid, _ = stores
    cfg = configure(monkeypatch)
    calls = []
    monkeypatch.setattr(ai_client, '_post_json', lambda *args, **kwargs: calls.append(args) or {
        'choices': [{'message': {'content': 'La réserve reste ouverte [C1].'}}],
        'usage': {'prompt_tokens': 42, 'completion_tokens': 8, 'total_tokens': 50}})
    with brain() as db:
        row, _ = note_session(db, pid)
        stamp = scoped_assistant.session_snapshot(db, row)[0]
        conversation = scoped_assistant.conversation_context(row, 'session')
        metadata = {'session_stamp': stamp, 'revision': row.revision, 'scope': 'session',
            'conversation': conversation, 'conversation_key': scoped_assistant.conversation_key(conversation),
            'citations': [{'reference': 'C1', 'excerpt': 'Réserve humaine'}], 'warnings': []}
        async def prepare(*args, **kwargs):
            return cfg, [{'role': 'user', 'content': 'Contexte fictif'}], metadata
        monkeypatch.setattr(scoped_assistant, 'prepare', prepare)
        first = asyncio.run(scoped_assistant.answer(db, row, query='Quelle réserve ?'))
        second = asyncio.run(scoped_assistant.answer(db, row, query='Quelle réserve ?'))
        assert first['usage']['measured_tokens'] == second['usage']['measured_tokens'] == 50
        assert first['usage']['complete'] and len(calls) == 1
        events = db.scalars(select(MeetingSessionEvent).where(MeetingSessionEvent.kind == 'assistant.answer')).all()
        assert len(events) == 1 and events[0].data['usage']['measured_tokens'] == 50
