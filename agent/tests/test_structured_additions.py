import asyncio
from copy import deepcopy
from contextlib import contextmanager
import json
import socket
import subprocess
from types import SimpleNamespace
import urllib.error
import urllib.request
import http.client

from fastapi import HTTPException
import pytest

from app.services import ai_client as AI, session_enhancements as SERVICE
REAL_CHAT_TEXT = AI.chat_text

CFG = {'enabled': True, 'provider': 'openai_compatible', 'model': 'fictitious-model',
       'base_url': 'http://192.0.2.1:1234', 'fallback_enabled': True, 'fallback_autostart': True}
SID = '00000000-0000-0000-0000-000000000001'
NOTE = {'reference': 'C1', 'title': 'Note FICTIVE', 'level': 'working',
        'excerpt': 'La réception du banc QA reste à confirmer.',
        'locator': {'session_id': SID, 'note_version_id': 'note-fictitious-v1', 'block': 0}}
TRANSCRIPT = {'reference': 'C2', 'title': 'Transcription FICTIVE', 'level': 'working',
              'excerpt': 'La réception du banc QA reste à confirmer. Le contrôle sera mardi.',
              'locator': {'session_id': SID, 'segment_id': 'segment-fictitious-v1'}}


@pytest.fixture(autouse=True)
def no_real_network_or_process(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError('No real network or process in candidate unit tests')
    monkeypatch.setattr(socket, 'create_connection', refused)
    monkeypatch.setattr(urllib.request, 'urlopen', refused)
    monkeypatch.setattr(http.client.HTTPConnection, 'request', refused)
    monkeypatch.setattr(subprocess, 'Popen', refused)
    monkeypatch.setattr(AI.ai_routing, 'resolve', lambda cfg: cfg)
    monkeypatch.setattr(AI.ai_routing, 'primary_epoch', lambda cfg: 0)
    monkeypatch.setattr(AI.ai_routing, 'primary_succeeded', lambda *args: None)
    @contextmanager
    def no_model(*args, **kwargs):
        raise AssertionError('No real model management in unit tests')
        yield
    monkeypatch.setattr(AI.ai_routing, 'local_generation', no_model)
    monkeypatch.setattr(AI.ai_routing, 'unavailable', lambda *args: None)


class Response:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self):
        return json.dumps(self.payload).encode()


def transport(monkeypatch, contents, provider='openai_compatible'):
    calls = []
    def fake(request, **kwargs):
        calls.append(json.loads(request.data))
        content = contents[len(calls) - 1]
        if isinstance(content, Exception):
            raise content
        payload = {'message': {'content': content}} if provider == 'ollama' else {'choices': [{'message': {'content': content}}]}
        return Response(payload)
    monkeypatch.setattr(urllib.request, 'urlopen', fake)
    return calls


def fake_session(monkeypatch, citations=(NOTE, TRANSCRIPT), reply=None):
    class DB:
        def __init__(self):
            self.events, self.commits = [], 0
        def refresh(self, row):
            pass
        def expire_all(self):
            pass
        def get(self, model, key):
            return None
        def execute(self, statement):
            pass
        def commit(self):
            self.commits += 1
    db = DB()
    row = SimpleNamespace(id=SID, revision=1)
    note = {'revision': 1, 'version_id': 'note-fictitious-v1',
            'content': {'blocks': [{'type': 'paragraph', 'runs': [{'text': NOTE['excerpt']}]}]}}
    initial = deepcopy(note)
    metadata = {'scope': 'session', 'session_stamp': 'fictitious-stamp', 'citations': list(citations), 'warnings': []}
    async def prepare(*args, **kwargs):
        return deepcopy(CFG), [{'role': 'system', 'content': 'Consigne FICTIVE.'}, {'role': 'user', 'content': 'Extraits.'}], deepcopy(metadata)
    calls = []
    def generate(cfg, messages, **options):
        calls.append((deepcopy(cfg), deepcopy(messages), deepcopy(options)))
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setattr(SERVICE.assistant, 'prepare', prepare)
    monkeypatch.setattr(SERVICE.assistant, 'session_snapshot', lambda *args: ('fictitious-stamp', note, []))
    monkeypatch.setattr(SERVICE.assistant, 'context_current', lambda *args: True)
    monkeypatch.setattr(SERVICE.assistant, 'answer_visible', lambda *args: True)
    monkeypatch.setattr(SERVICE.sessions, 'require_enabled', lambda *args: None)
    monkeypatch.setattr(SERVICE.sessions, 'get_session', lambda *args, **kwargs: row)
    monkeypatch.setattr(SERVICE.sessions, 'append_event', lambda db, row, kind, data: db.events.append((kind, deepcopy(data))))
    monkeypatch.setattr(SERVICE, '_find', lambda *args: None)
    monkeypatch.setattr(AI, 'chat_text', generate)
    return db, row, note, initial, calls


def test_schema_is_closed_bounded_and_uses_remaining_references():
    schema = SERVICE._addition_response_format([TRANSCRIPT])['json_schema']
    assert schema['strict'] is True
    root = schema['schema']
    assert root['additionalProperties'] is False and root['required'] == ['additions']
    additions = root['properties']['additions']
    assert additions['maxItems'] == 12
    item = additions['items']
    assert item['additionalProperties'] is False and set(item['required']) == {'text', 'reference', 'quote'}
    assert item['properties']['reference']['enum'] == ['C2']


def test_structured_api_payload_forces_single_transport(monkeypatch):
    calls = transport(monkeypatch, ['{"additions":[]}'])
    seen = []
    monkeypatch.setattr(AI.ai_routing, 'resolve', lambda cfg: seen.append(dict(cfg)) or cfg)
    response_format = SERVICE._addition_response_format([TRANSCRIPT])
    assert AI.chat_text(CFG, [], response_format=response_format, raise_errors=True) == '{"additions":[]}'
    assert len(calls) == 1 and calls[0]['response_format'] == response_format
    assert calls[0]['reasoning_effort'] == 'none' and calls[0]['chat_template_kwargs'] == {'enable_thinking': False}
    assert all(cfg['fallback_enabled'] and cfg['fallback_autostart'] for cfg in seen)


def test_structured_empty_reply_is_not_retried(monkeypatch):
    calls = transport(monkeypatch, [''])
    assert AI.chat_text(CFG, [], response_format=SERVICE._addition_response_format([TRANSCRIPT]), raise_errors=True) is None
    assert len(calls) == 1


@pytest.mark.parametrize('code', [400, 404, 422, 503])
def test_structured_http_refusal_has_one_call_no_fallback(monkeypatch, code):
    failure = urllib.error.HTTPError('http://192.0.2.1:1234', code, 'fictitious refusal', {}, None)
    calls = transport(monkeypatch, [failure])
    # This case exercises disabled rescue; manual enabled rescue is covered in
    # test_ai_routing, including a transport503 after the primary probe.
    cfg = {**CFG, 'fallback_enabled': False, 'fallback_autostart': False}
    with pytest.raises(urllib.error.HTTPError):
        AI.chat_text(cfg, [], response_format=SERVICE._addition_response_format([TRANSCRIPT]), raise_errors=True)
    assert len(calls) == 1


def test_default_empty_retry_is_preserved_without_response_format(monkeypatch):
    calls = transport(monkeypatch, ['', 'Réponse FICTIVE.'])
    assert AI.chat_text({**CFG, 'fallback_enabled': False}, [], max_tokens=100) == 'Réponse FICTIVE.'
    assert len(calls) == 2 and calls[1]['max_tokens'] == 200
    assert all('response_format' not in payload for payload in calls)


def test_ollama_default_contract_is_preserved(monkeypatch):
    calls = transport(monkeypatch, ['Réponse FICTIVE.'], provider='ollama')
    assert AI.chat_text({**CFG, 'provider': 'ollama', 'fallback_enabled': False}, []) == 'Réponse FICTIVE.'
    assert len(calls) == 1 and calls[0]['format'] == 'json' and calls[0]['think'] is False
    assert 'response_format' not in calls[0]


def test_explicit_structured_request_on_other_provider_is_refused_before_io(monkeypatch):
    with pytest.raises(ValueError, match='compatible OpenAI'):
        AI.chat_text({**CFG, 'provider': 'ollama'}, [], response_format={}, raise_errors=True)


def test_only_current_note_returns_empty_locally_and_preserves_note(monkeypatch):
    db, row, note, initial, calls = fake_session(monkeypatch, citations=[NOTE])
    result = asyncio.run(SERVICE.propose(db, row))
    assert calls == [] and result['text'] == '' and result['content']['blocks'] == [] and result['citations'] == []
    assert note == initial


def test_valid_addition_uses_transcript_and_keeps_note_as_uncitable_context(monkeypatch):
    reply = json.dumps({'additions': [{'text': 'Le contrôle sera mardi.', 'reference': 'C2', 'quote': 'Le contrôle sera mardi.'}]})
    db, row, note, initial, calls = fake_session(monkeypatch, reply=reply)
    result = asyncio.run(SERVICE.propose(db, row, automatic=True))
    assert len(calls) == 1 and note == initial
    cfg, messages, options = calls[0]
    assert cfg['fallback_enabled'] is False and options['retry_empty'] is False and options['timeout'] == 600
    assert options['response_format']['json_schema']['schema']['properties']['additions']['items']['properties']['reference']['enum'] == ['C2']
    assert NOTE['excerpt'] in messages[-1]['content'] and '[C1]' not in messages[-1]['content']
    assert result['citations'][0]['reference'] == 'C2' and result['status'] == 'pending'


def test_duplicate_note_fact_is_rejected_even_when_transcript_citation_is_valid(monkeypatch):
    reply = json.dumps({'additions': [{'text': NOTE['excerpt'].upper(), 'reference': 'C2', 'quote': NOTE['excerpt']}]})
    db, row, note, initial, calls = fake_session(monkeypatch, reply=reply)
    with pytest.raises(HTTPException, match='déjà présent') as caught:
        asyncio.run(SERVICE.propose(db, row))
    assert caught.value.status_code == 502 and len(calls) == 1
    assert db.events == [] and db.commits == 0 and note == initial


@pytest.mark.parametrize('item', [
    {'text': 'Le contrôle sera mardi.', 'reference': 'C1', 'quote': NOTE['excerpt']},
    {'text': 'Le contrôle sera mardi.', 'reference': 'C2', 'quote': 'Le contrôle sera Mardi.'},
    {'text': 'Le contrôle sera mardi.', 'reference': 'C2', 'quote': 'Le contrôle sera mardi.', 'extra': 'refused'},
    {'text': 14, 'reference': 'C2', 'quote': 'Le contrôle sera mardi.'},
])
def test_invalid_reference_quote_keys_or_type_are_rejected_locally(monkeypatch, item):
    db, row, note, initial, calls = fake_session(monkeypatch, reply=json.dumps({'additions': [item]}))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(SERVICE.propose(db, row))
    assert caught.value.status_code == 502 and db.events == [] and note == initial and len(calls) == 1


def test_fourteen_additions_are_refused_without_trimming(monkeypatch):
    item = {'text': 'Le contrôle sera mardi.', 'reference': 'C2', 'quote': 'Le contrôle sera mardi.'}
    db, row, note, initial, calls = fake_session(monkeypatch, reply=json.dumps({'additions': [item] * 14}))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(SERVICE.propose(db, row))
    assert caught.value.status_code == 502 and '12' in str(caught.value.__cause__)
    assert len(calls) == 1 and db.events == [] and note == initial


def test_server_format_refusal_has_clear_message_and_no_second_generation(monkeypatch):
    failure = urllib.error.HTTPError('http://192.0.2.1:1234', 400, 'fictitious refusal', {}, None)
    db, row, note, initial, calls = fake_session(monkeypatch, reply=failure)
    with pytest.raises(HTTPException, match='refusé le format') as caught:
        asyncio.run(SERVICE.propose(db, row))
    assert caught.value.status_code == 502 and len(calls) == 1 and db.events == [] and note == initial


def test_empty_generation_is_explicit_failure_without_note_change(monkeypatch):
    db, row, note, initial, calls = fake_session(monkeypatch, reply=None)
    with pytest.raises(HTTPException, match='aucune proposition') as caught:
        asyncio.run(SERVICE.propose(db, row))
    assert caught.value.status_code == 502 and len(calls) == 1 and db.events == [] and note == initial


def test_preselected_manual_fallback_keeps_configured_preparation_and_one_post(monkeypatch):
    prepared = []
    @contextmanager
    def local(cfg, **kwargs):
        prepared.append(dict(cfg))
        yield
    monkeypatch.setattr(AI.ai_routing, 'local_generation', local)
    selected = {**CFG, 'using_fallback': True, 'base_url': 'http://127.0.0.1:1234', 'model': 'local-fictitious'}
    calls = transport(monkeypatch, ['{"additions":[]}'])
    assert AI.chat_text(selected, [], response_format=SERVICE._addition_response_format([TRANSCRIPT]), raise_errors=True) == '{"additions":[]}'
    assert len(calls) == len(prepared) == 1 and prepared[0]['fallback_autostart'] is True
    assert calls[0]['model'] == 'local-fictitious'


def test_pure_builder_is_reusable_without_mutating_frozen_input_or_duplicating_prompt():
    messages = [{'role': 'system', 'content': 'Consigne FICTIVE.'}, {'role': 'user', 'content': 'Extraits.'}]
    context = {'citations': [NOTE, TRANSCRIPT], 'session_stamp': 'fictitious-stamp'}
    before = deepcopy((messages, context))
    prepared, filtered, note_text, schema = SERVICE._prepare_addition_request(messages, context, SID)
    again, _, _, _ = SERVICE._prepare_addition_request(prepared, context, SID)
    assert (messages, context) == before and prepared == again
    assert [c['reference'] for c in filtered['citations']] == ['C2'] and NOTE['excerpt'] in note_text
    assert prepared[0]['content'].count('Maximum 12 ajouts.') == 1
    assert schema['json_schema']['schema']['properties']['additions']['maxItems'] == 12


def test_pure_validator_returns_verified_blocks_without_sql_or_events():
    reply = json.dumps({'additions': [{'text': 'Le contrôle sera mardi.', 'reference': 'C2', 'quote': 'Le contrôle sera mardi.'}]})
    additions, blocks, used = SERVICE._validate_addition_reply(reply, {'citations': [TRANSCRIPT]}, NOTE['excerpt'])
    assert len(additions) == len(blocks) == len(used) == 1
    assert blocks[0]['runs'][0]['text'].endswith('[C2]') and used[0]['quote'] == 'Le contrôle sera mardi.'


def test_accepting_empty_proposal_is_refused_before_note_write(monkeypatch):
    db, row, note, initial, calls = fake_session(monkeypatch, citations=[NOTE])
    result = asyncio.run(SERVICE.propose(db, row))
    monkeypatch.setattr(SERVICE, '_find', lambda db, row, kind, identity:
                        SimpleNamespace(data=result) if kind == 'enhancement.proposed' else None)
    with pytest.raises(HTTPException, match='Aucun ajout utile') as caught:
        SERVICE.decide(db, row, result['id'], 'accept', 1)
    assert caught.value.status_code == 409 and note == initial and calls == [] and db.commits == 1


def test_cached_empty_result_does_not_repeat_generation_or_note_write(monkeypatch):
    db, row, note, initial, calls = fake_session(monkeypatch, citations=[NOTE])
    result = asyncio.run(SERVICE.propose(db, row))
    monkeypatch.setattr(SERVICE, '_find', lambda *args: SimpleNamespace(data=result))
    monkeypatch.setattr(SERVICE, 'list_proposals', lambda *args: {'items': [result]})
    assert asyncio.run(SERVICE.propose(db, row)) == result
    assert len(db.events) == 1 and db.commits == 1 and calls == [] and note == initial


def test_full_note_fact_outside_selected_citations_is_rejected(monkeypatch):
    reply = json.dumps({'additions': [{'text': NOTE['excerpt'], 'reference': 'C2', 'quote': NOTE['excerpt']}]})
    db, row, note, initial, calls = fake_session(monkeypatch, citations=[TRANSCRIPT], reply=reply)
    with pytest.raises(HTTPException, match='déjà présent'):
        asyncio.run(SERVICE.propose(db, row))
    assert len(calls) == 1 and db.events == [] and note == initial


def test_full_note_suffix_outside_excerpt_is_rejected(monkeypatch):
    reply = json.dumps({'additions': [{'text': 'Le contrôle sera mardi.', 'reference': 'C2', 'quote': 'Le contrôle sera mardi.'}]})
    db, row, note, _, calls = fake_session(monkeypatch, reply=reply)
    note['content']['blocks'][0]['runs'][0]['text'] += ' Le contrôle sera mardi.'
    frozen_note = deepcopy(note)
    with pytest.raises(HTTPException, match='déjà présent'):
        asyncio.run(SERVICE.propose(db, row))
    assert len(calls) == 1 and db.events == [] and note == frozen_note


def test_changed_snapshot_stamp_refuses_generation_before_transport(monkeypatch):
    db, row, note, initial, calls = fake_session(monkeypatch, reply='{"additions":[]}')
    monkeypatch.setattr(SERVICE.assistant, 'session_snapshot', lambda *args: ('changed-stamp', note, []))
    with pytest.raises(HTTPException, match='a changé') as caught:
        asyncio.run(SERVICE.propose(db, row))
    assert caught.value.status_code == 409 and calls == [] and db.events == [] and note == initial


def test_manual_unavailable_primary_selects_local_before_single_generation(monkeypatch):
    selected = {**CFG, 'using_fallback': True, 'fallback_enabled': False,
                'base_url': 'http://127.0.0.1:1234', 'model': 'local-fictitious'}
    resolved, prepared = [], []
    monkeypatch.setattr(AI.ai_routing, 'resolve', lambda cfg: resolved.append(dict(cfg)) or selected)
    @contextmanager
    def local(cfg, **kwargs):
        prepared.append(dict(cfg))
        yield
    monkeypatch.setattr(AI.ai_routing, 'local_generation', local)
    calls = transport(monkeypatch, ['{"additions":[]}'])
    assert AI.chat_text(CFG, [], response_format=SERVICE._addition_response_format([TRANSCRIPT]), raise_errors=True) == '{"additions":[]}'
    assert len(resolved) == len(prepared) == len(calls) == 1
    assert resolved[0]['fallback_enabled'] is True and prepared[0]['fallback_autostart'] is True
    assert calls[0]['model'] == 'local-fictitious'


def test_explicit_local_mode_has_one_post_without_fallback_management(monkeypatch):
    calls = transport(monkeypatch, ['{"additions":[]}'])
    cfg = {**CFG, 'base_url': 'http://127.0.0.1:1234', 'model': 'explicit-local-fictitious',
           'fallback_enabled': False, 'fallback_autostart': False}
    assert AI.chat_text(cfg, [], response_format=SERVICE._addition_response_format([TRANSCRIPT]), raise_errors=True) == '{"additions":[]}'
    assert len(calls) == 1 and calls[0]['model'] == 'explicit-local-fictitious'


@pytest.mark.parametrize('failure', [
    urllib.error.HTTPError('http://192.0.2.1:1234', 500, 'fictitious refusal', {}, None),
    urllib.error.URLError(ConnectionError('fictitious disconnection')),
])
def test_selected_primary_failure_has_no_second_post_or_local_preparation(monkeypatch, failure):
    resolved, down = [], []
    monkeypatch.setattr(AI.ai_routing, 'resolve', lambda cfg: resolved.append(dict(cfg)) or cfg)
    monkeypatch.setattr(AI.ai_routing, 'unavailable', lambda cfg: down.append(dict(cfg)))
    calls = transport(monkeypatch, [failure])
    cfg = {**CFG, 'fallback_enabled': False, 'fallback_autostart': False}
    with pytest.raises(type(failure)):
        AI.chat_text(cfg, [], response_format=SERVICE._addition_response_format([TRANSCRIPT]), raise_errors=True)
    assert len(calls) == len(resolved) == 1
    assert resolved[0]['fallback_enabled'] is False and resolved[0]['fallback_autostart'] is False


def test_structured_primary_success_retains_recovery_notification(monkeypatch):
    notified = []
    monkeypatch.setattr(AI.ai_routing, 'primary_epoch', lambda cfg: 71)
    monkeypatch.setattr(AI.ai_routing, 'primary_succeeded', lambda cfg, epoch: notified.append((dict(cfg), epoch)))
    calls = transport(monkeypatch, ['{"additions":[]}'])
    AI.chat_text(CFG, [], response_format=SERVICE._addition_response_format([TRANSCRIPT]), raise_errors=True)
    assert len(calls) == 1 and notified == [(CFG, 71)]


def test_automatic_suggestion_never_selects_or_prepares_fallback(monkeypatch):
    reply = json.dumps({'additions': [{'text': 'Le contrôle sera mardi.', 'reference': 'C2', 'quote': 'Le contrôle sera mardi.'}]})
    db, row, note, initial, _ = fake_session(monkeypatch, reply=reply)
    monkeypatch.setattr(AI, 'chat_text', REAL_CHAT_TEXT)
    resolved = []
    def choose(cfg):
        resolved.append(dict(cfg))
        assert cfg['fallback_enabled'] is False and cfg['fallback_autostart'] is False
        return cfg
    monkeypatch.setattr(AI.ai_routing, 'resolve', choose)
    calls = transport(monkeypatch, [reply])
    result = asyncio.run(SERVICE.propose(db, row, automatic=True))
    assert result['text'] == 'Le contrôle sera mardi.' and len(calls) == len(resolved) == 1 and note == initial


def test_identical_additions_inside_one_reply_are_rejected_without_suppression(monkeypatch):
    first = {'text': 'Le contrôle sera mardi.', 'reference': 'C2', 'quote': 'Le contrôle sera mardi.'}
    second = {**first, 'text': 'LE CONTRÔLE SERA MARDI !'}
    db, row, note, initial, calls = fake_session(monkeypatch, reply=json.dumps({'additions': [first, second]}))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(SERVICE.propose(db, row))
    assert caught.value.status_code == 502 and 'identiques' in str(caught.value.__cause__)
    assert len(calls) == 1 and db.events == [] and note == initial


@pytest.mark.parametrize('status', ['prepared', 'completed'])
def test_old_empty_acceptance_receipt_is_recovered_before_new_empty_guard(monkeypatch, status):
    db, row, note, initial, _ = fake_session(monkeypatch, citations=[NOTE])
    result = asyncio.run(SERVICE.propose(db, row))
    receipt = SimpleNamespace(status=status, body={}, id='old-fictitious-receipt')
    db.get = lambda *args: receipt
    monkeypatch.setattr(SERVICE, '_find', lambda db, row, kind, identity:
                        SimpleNamespace(data=result) if kind == 'enhancement.proposed' else None)
    replayed = []
    def finish(*args):
        replayed.append(args)
        receipt.status = 'completed'
    monkeypatch.setattr(SERVICE.sessions, 'execute_command', finish)
    monkeypatch.setattr(SERVICE.SessionNoteSave, 'model_validate', lambda body: 'old-fictitious-command')
    monkeypatch.setattr(SERVICE.sessions, 'serialize_session', lambda *args: {'id': SID, 'note': note})
    accepted = SERVICE.decide(db, row, result['id'], 'accept', 1)
    assert accepted['note'] == initial and len(replayed) == (1 if status == 'prepared' else 0)
    assert db.events[-1][1]['decision'] == 'accepted'
