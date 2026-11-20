"""Diagnostics cannot confuse inventory, loaded models, successful replies or scopes."""
import json
import urllib.error

import pytest
from fastapi import HTTPException

from app.db import SessionLocal
from app.services import fusion_readiness as readiness
from app.services.settings_service import save_section


@pytest.fixture
def configured(tmp_path, monkeypatch):
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS', raising=False)
    monkeypatch.setattr(readiness, 'directory', lambda key:tmp_path/key)
    monkeypatch.setattr(readiness, 'snapshot', lambda db:{'generation':readiness.generation_snapshot(db)})
    with SessionLocal() as db:
        save_section(db, 'foresight', {'enabled':True, 'mode':'network'})
        save_section(db, 'ai', {'enabled':True, 'provider':'openai_compatible', 'base_url':'http://llm.test:1234',
            'model':'target', 'api_key':'secret-readiness-test', 'fallback_enabled':True, 'fallback_autostart':True})
    return tmp_path


@pytest.mark.parametrize('loaded', [[], [{'id':'target-instance'}], None])
def test_inventory_never_proves_generation(configured, monkeypatch, loaded):
    requests = []
    monkeypatch.setattr(readiness, 'fetch', lambda cfg,path:requests.append(path) or
        {'models':[{'key':'target','loaded_instances':loaded}]})
    monkeypatch.setattr('app.services.ai_client.chat_text', lambda *args,**kwargs:pytest.fail('Inventory launched generation'))
    with SessionLocal() as db:
        state = readiness.probe_generation(db)['generation']
    assert requests == ['/api/v1/models']
    assert state['inventory']['installed'] is True
    assert state['inventory']['loaded'] == (None if loaded is None else bool(loaded))
    assert state['test'] is None and state['placement'] == 'network'


def test_openai_inventory_cannot_invent_loaded_state(configured, monkeypatch):
    def fetch(cfg,path):
        if path == '/api/v1/models':
            raise urllib.error.HTTPError('http://llm.test',404,'not supported',None,None)
        return {'data':[{'id':'target'}]}
    monkeypatch.setattr(readiness, 'fetch', fetch)
    with SessionLocal() as db:
        state = readiness.probe_generation(db)['generation']['inventory']
    assert state['reachable'] and state['announced']
    assert state['installed'] is None and state['loaded'] is None


@pytest.mark.parametrize('reply', ['OK', ''])
def test_reply_targets_exact_configuration_without_fallback(configured, monkeypatch, reply):
    calls = []
    monkeypatch.setattr('app.services.ai_client.chat_text', lambda cfg,messages,**kwargs:calls.append((cfg,messages,kwargs)) or reply)
    monkeypatch.setattr('app.services.ai_routing.primary_succeeded', lambda *args:None)
    with SessionLocal() as db:
        result = readiness.test_generation(db)['generation']
    assert result['test']['ok'] == result['test']['reply_received'] == bool(reply)
    cfg, messages, options = calls[0]
    assert cfg['base_url'] == 'http://llm.test:1234' and cfg['model'] == 'target'
    assert not cfg['fallback_enabled'] and not cfg['fallback_autostart']
    assert messages == [{'role':'user','content':'Réponds uniquement OK.'}]
    assert not options['retry_empty']
    assert 'secret-readiness-test' not in json.dumps(result)


def test_inventory_failure_preserves_successful_reply_and_sanitizes_errors(configured, monkeypatch):
    monkeypatch.setattr('app.services.ai_client.chat_text', lambda *args,**kwargs:'OK')
    monkeypatch.setattr('app.services.ai_routing.primary_succeeded', lambda *args:None)
    with SessionLocal() as db:
        assert readiness.test_generation(db)['generation']['test']['ok']
        monkeypatch.setattr(readiness, 'fetch', lambda *args:(_ for _ in ()).throw(OSError('secret-readiness-test')))
        result = readiness.probe_generation(db)['generation']
    assert result['test']['ok'] and not result['inventory']['reachable']
    assert 'secret-readiness-test' not in json.dumps(result)
    assert len(list(configured.glob('*/generation-*.json'))) == 1


def test_settings_changed_during_test_cannot_inherit_the_previous_reply(configured, monkeypatch):
    with SessionLocal() as db:
        def respond(*args, **kwargs):
            save_section(db, 'ai', {'model':'different-model'})
            return 'OK'
        monkeypatch.setattr('app.services.ai_client.chat_text', respond)
        monkeypatch.setattr('app.services.ai_routing.primary_succeeded', lambda *args:None)
        result = readiness.test_generation(db)['generation']
    assert result['model'] == 'different-model' and result['test'] is None
    assert len(list(configured.glob('*/generation-*.json'))) == 1


def test_local_mode_uses_loopback_and_does_not_inherit_network_receipt(configured, monkeypatch):
    monkeypatch.setattr('app.services.ai_client.chat_text', lambda *args,**kwargs:'OK')
    monkeypatch.setattr('app.services.ai_routing.primary_succeeded', lambda *args:None)
    with SessionLocal() as db:
        assert readiness.test_generation(db)['generation']['test']['ok']
        save_section(db, 'foresight', {'mode':'local'})
        result = readiness.generation_snapshot(db)
        selected, _, placement = readiness.selected_configuration(db)
    assert placement == result['placement'] == 'local'
    assert selected['base_url'] == 'http://127.0.0.1:1234'
    assert result['test'] is None


def test_editor_cannot_trigger_global_model_checks(configured, monkeypatch):
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'editor')
    with SessionLocal() as db:
        for operation in (readiness.probe_generation, readiness.test_generation):
            with pytest.raises(HTTPException) as denied:
                operation(db)
            assert denied.value.status_code == 403


def test_diagnostics_keep_immutable_attempts_and_refuse_invalid_pointer(configured):
    readiness.record('test-key','generation',{'ok':True})
    readiness.record('test-key','generation',{'ok':False})
    assert len(list((configured/'test-key').glob('generation-*.json'))) == 2
    assert readiness.saved('test-key','generation')['ok'] is False
    (configured/'test-key/generation.latest').write_text('../outside')
    assert readiness.saved('test-key','generation') is None


def test_readiness_HTTP_routes_keep_global_owner_guard(configured, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.db import get_db
    from app.routers.fusion_insights import router
    from app.security import local_guard
    app = FastAPI()
    app.middleware('http')(local_guard)
    app.include_router(router)
    def database():
        with SessionLocal() as db:
            yield db
    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(readiness, 'fetch', lambda *args:{'models':[{'key':'target','loaded_instances':[]}]})
    monkeypatch.setattr('app.services.ai_client.chat_text', lambda *args,**kwargs:'OK')
    monkeypatch.setattr('app.services.ai_routing.primary_succeeded', lambda *args:None)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        settings = '/api/v1/workspace/fusion-settings'
        root = settings + '/readiness'
        assert client.get(settings).json()['can_edit'] is True
        assert client.get(root).json()['generation']['test'] is None
        assert client.post(root+'/probe').json()['generation']['inventory']['loaded'] is False
        assert client.post(root+'/generation-test').json()['generation']['test']['reply_received']
        for role in ('reader', 'editor', 'owner'):
            monkeypatch.setenv('AGENT_OPERATOR_ROLE', role)
            monkeypatch.setenv('AGENT_OPERATOR_PROJECT_IDS', '[]')
            response = client.get(settings)
            assert response.status_code == 200 and response.json()['can_edit'] is False
            assert client.put(settings, json={'enabled': False}).status_code == 403
            monkeypatch.setenv('AGENT_OPERATOR_ID', role)
            personal = settings + '/personal'
            selection = client.get(personal).json()
            assert selection['live_transcription_enabled'] is False
            selection['live_transcription_enabled'] = True
            assert client.put(personal, json=selection).json() == selection
            assert client.get(personal).json() == selection
            assert client.get(settings).json()['live_transcription_enabled'] is False
            assert client.get(root).status_code == 403
            assert client.post(root+'/probe').status_code == 403
            assert client.post(root+'/generation-test').status_code == 403


def test_timeout_or_onboarding_change_keeps_the_same_model_reply(configured, monkeypatch):
    monkeypatch.setattr('app.services.ai_client.chat_text', lambda *args,**kwargs:'OK')
    monkeypatch.setattr('app.services.ai_routing.primary_succeeded', lambda *args:None)
    with SessionLocal() as db:
        assert readiness.test_generation(db)['generation']['test']['ok']
        save_section(db, 'ai', {'timeout_s':300, 'fallback_autostart':False})
        save_section(db, 'foresight', {'onboarding_complete':True})
        assert readiness.generation_snapshot(db)['test']['ok']


def test_LM_Studio_custom_instance_identifier_is_recognized(configured, monkeypatch):
    monkeypatch.setattr(readiness, 'fetch', lambda *args:{'models':[{'key':'publisher/model', 'loaded_instances':[{'id':'target'}]}]})
    with SessionLocal() as db:
        inventory = readiness.probe_generation(db)['generation']['inventory']
    assert inventory['installed'] and inventory['loaded']
