import json

from fastapi.testclient import TestClient

from app.main import app
from app.services import connection_health as health


def test_llm_checks_configured_model_not_just_server(monkeypatch):
    monkeypatch.setattr(health, 'http_json', lambda *args, **kwargs: {'models': [{'name': 'other:latest'}]})
    cfg={'enabled':True,'provider':'ollama','model':'wanted','base_url':'http://local'}
    assert health.llm_check(cfg)['state']=='warning'
    monkeypatch.setattr(health, 'http_json', lambda *args, **kwargs: {'models': [{'name': 'wanted:latest'}]})
    assert health.llm_check(cfg)['state']=='ok'
    assert health.llm_check({**cfg,'enabled':False})['state']=='disabled'


def test_embedding_requires_real_finite_vector(monkeypatch):
    memory={'embedding_provider':'ollama','embedding_model':'embed','embedding_endpoint':'http://local'}
    monkeypatch.setattr(health,'http_json',lambda *args, **kwargs:{'data':[{'embedding':[1.0] * 768}]})
    assert health.embedding_check({},memory)['state']=='ok'
    monkeypatch.setattr(health,'http_json',lambda *args, **kwargs:{'data':[{'embedding':[float('nan')] * 768}]})
    assert health.embedding_check({},memory)['state']=='error'
    monkeypatch.setattr(health,'http_json',lambda *args, **kwargs:{'data':[]})
    assert health.embedding_check({},memory)['state']=='error'


def test_memory_simulation_is_never_green(monkeypatch):
    monkeypatch.setattr('app.services.memory_factory.resolve_engine',lambda *args:'fake')
    assert health.memory_check({})['state']=='disabled'


def test_missing_memory_storage_is_not_created_or_marked_connected(monkeypatch,tmp_path):
    monkeypatch.setattr('app.services.memory_factory.resolve_engine',lambda *args:'eg2')
    result=health.memory_check({'index_path':str(tmp_path/'absent'/'index.db')})
    assert result['state']=='warning'
    assert not (tmp_path/'absent').exists()


def test_memory_health_warns_when_restored_vectors_use_old_endpoint(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import closing
    monkeypatch.setattr('app.services.memory_factory.resolve_engine', lambda *args: 'eg2')
    path = tmp_path / 'index.db'
    old = health.EmbeddingChannel('http://127.0.0.1:17841', 'google/embeddinggemma-2')
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('CREATE TABLE passages (profile TEXT)')
        db.execute('INSERT INTO passages VALUES (?)', (old.profile,))
    result = health.memory_check({'index_path': str(path), 'embedding_endpoint': 'http://127.0.0.1:8766',
                                  'embedding_model': old.model})
    assert result['state'] == 'warning'
    assert 'Reconstruisez' in result['detail']


def test_restored_memory_uses_relocated_managed_index(monkeypatch, tmp_path):
    from app.config import settings

    storage = tmp_path / 'storage'
    local = storage / 'eg2/profile/index.db'
    local.parent.mkdir(parents=True)
    local.touch()
    monkeypatch.setattr(settings, 'storage_dir', str(storage))
    stale = tmp_path / 'previous/storage/eg2/profile/index.db'
    assert health.index_path({'index_path': str(stale)}) == local
    stale.parent.mkdir(parents=True)
    stale.touch()
    assert health.index_path({'index_path': str(stale)}) == stale


def test_errors_do_not_expose_keys_or_endpoint():
    def fail():
        raise RuntimeError('secret-key on http://private')
    out=health.guarded(fail)
    assert out['state']=='error'
    assert 'secret' not in json.dumps(out)
    assert 'private' not in json.dumps(out)


def test_status_cache_does_not_start_duplicate_probe_and_invalidates_settings(monkeypatch):
    started=[]
    class Thread:
        def __init__(self, **kwargs):
            started.append(kwargs)
        def start(self):
            pass
    monkeypatch.setattr(health.threading,'Thread',Thread)
    monkeypatch.setattr(health,'_cache',{})
    first=health.connection_status({'api_key':'secret'}, {})
    health.connection_status({'api_key':'secret'}, {})
    assert len(started)==1
    assert first['services']['embedding']['state']=='checking'
    assert 'secret' not in json.dumps(first)
    health.connection_status({'api_key':'secret','model':'new'}, {})
    assert len(started)==2


def test_route_exposes_no_settings_secrets(monkeypatch):
    monkeypatch.setattr(health,'connection_status',lambda ai,memory:{'services':{},'refreshing':False})
    response=TestClient(app).get('/api/v1/connections/status')
    assert response.status_code==200
    assert response.json()=={'services':{},'refreshing':False}


def test_manual_test_overrides_old_probe_but_expires_and_is_scoped(monkeypatch):
    monkeypatch.setattr(health, '_cache', {})
    monkeypatch.setattr(health, '_last_llm_test', {})
    clock = [100.0]
    monkeypatch.setattr(health.time, 'monotonic', lambda: clock[0])
    cfg = {'enabled': True, 'provider': 'openai_compatible', 'model': 'wanted'}
    monkeypatch.setattr(health, 'llm_check', lambda ai: health.result('error', 'Old probe'))
    monkeypatch.setattr(health, 'embedding_check', lambda *args: health.result('ok', 'Vector'))
    monkeypatch.setattr(health, 'memory_check', lambda *args: health.result('warning', 'Memory'))
    # Simulate a background probe completing after the manual test.
    health.record_llm_test(cfg, {'ok': True, 'reply': 'OK'})
    key = health._settings_key([cfg, {}])
    health._cache.update(key=key, values={}, running=True)
    health._refresh(key, cfg, {})
    current = health.connection_status(cfg, {})['services']
    assert current['llm']['state'] == 'ok'
    assert 'réponse du modèle' in current['llm']['detail']
    assert current['memory']['state'] == 'warning'
    clock[0] += health.TTL
    health._cache['expires'] = clock[0] + 1
    assert health.connection_status(cfg, {})['services']['llm']['state'] == 'error'
    health.record_llm_test({**cfg, 'model': 'other'}, {'ok': True})
    assert health.connection_status(cfg, {})['services']['llm']['state'] == 'error'


def test_ai_test_route_publishes_success_failure_and_disabled_without_secrets(monkeypatch):
    from app.routers import settings
    cfg = {'enabled': True, 'provider': 'openai_compatible', 'model': 'local'}
    monkeypatch.setattr(settings.svc, 'get_section', lambda *args: dict(cfg))
    monkeypatch.setattr(health, '_last_llm_test', {})
    client = TestClient(app)
    for outcome, expected in [({'ok': True}, 'ok'),
                              ({'ok': False, 'reason': 'secret-key at private-url'}, 'error')]:
        monkeypatch.setattr(settings.ai, 'check_connection', lambda *args: outcome)
        assert client.post('/v1/settings/ai/test').json() == outcome
        assert health._last_llm_test['value']['state'] == expected
        assert 'secret-key' not in json.dumps(health._last_llm_test)
        assert 'private-url' not in json.dumps(health._last_llm_test)
    cfg['enabled'] = False
    client.post('/v1/settings/ai/test')
    assert health._last_llm_test['value']['state'] == 'disabled'


def test_background_failure_requires_confirmation_and_recovers(monkeypatch):
    cfg = {'enabled': True, 'provider': 'ollama', 'model': 'wanted'}
    key = health._settings_key([cfg, {}])
    original = health.result('ok', 'Previously confirmed')
    monkeypatch.setattr(health, '_cache', {'key': key, 'values': {'llm': original}, 'running': True})
    monkeypatch.setattr(health, 'llm_check', lambda *args: health.result('error', 'Timeout'))
    monkeypatch.setattr(health, 'embedding_check', lambda *args: health.result('ok', 'Vector'))
    monkeypatch.setattr(health, 'memory_check', lambda *args: health.result('ok', 'Memory'))
    health._refresh(key, cfg, {})
    assert health._cache['values']['llm'] == original
    health._refresh(key, cfg, {})
    assert health._cache['values']['llm']['state'] == 'error'
    monkeypatch.setattr(health, 'llm_check', lambda *args: health.result('ok', 'Recovered'))
    health._refresh(key, cfg, {})
    assert health._cache['failures']['llm'] == 0
    assert health._cache['values']['llm']['state'] == 'ok'


def test_background_embedding_probe_has_short_bounded_budget(monkeypatch):
    calls = []

    def respond(*args, **kwargs):
        calls.append(kwargs['timeout_s'])
        return {'data': [{'embedding': [1.0] * 768}]}

    monkeypatch.setattr(health, 'http_json', respond)
    health.embedding_check({}, {'timeout_s': 600})
    health.embedding_check({}, {'timeout_s': 8})
    assert calls == [20, 8]
