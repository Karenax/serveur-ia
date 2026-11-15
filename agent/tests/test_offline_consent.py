import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient

from app.main import app
from app.services import ai_client, ai_routing, connection_health


@pytest.fixture
def outage(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(ai_routing, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(ai_routing, '_outages', {})
    monkeypatch.setattr(ai_routing, '_down_until', {})
    monkeypatch.setattr(ai_routing, '_failure_epochs', {})
    monkeypatch.setattr(ai_routing, '_routing_configured', False)
    monkeypatch.setattr(ai_routing, '_queue_release', lambda *a: None)
    cfg = {'enabled': True, 'provider': 'openai_compatible', 'base_url': 'http://remote.invalid:1234',
           'model': 'principal', 'fallback_enabled': True, 'fallback_autostart': True}
    return cfg, clock


def test_two_minutes_and_explicit_approval_are_both_required(outage, monkeypatch):
    cfg, clock = outage
    monkeypatch.setattr(ai_routing.subprocess, 'run', lambda *a, **k: pytest.fail('Unexpected model load'))
    monkeypatch.setattr(ai_routing.socket, 'create_connection', lambda *a, **k: (_ for _ in ()).throw(ConnectionRefusedError()))
    assert ai_routing.resolve(cfg) is cfg
    identifier = ai_routing.offline_status(cfg)['outage_id']
    fallback = ai_routing.local_config(cfg)
    clock[0] += 119
    assert not ai_routing.offline_status(cfg)['approval_required']
    with pytest.raises(ValueError):
        ai_routing.decide_offline(cfg, identifier, 'offline')
    with pytest.raises(RuntimeError):
        ai_routing.ensure_local(fallback)
    clock[0] += 1
    assert ai_routing.offline_status(cfg)['approval_required']
    with pytest.raises(RuntimeError):
        ai_routing.ensure_local(fallback)
    ai_routing.decide_offline(cfg, identifier, 'wait')
    clock[0] += 600
    assert not ai_routing.offline_status(cfg)['approval_required']
    assert ai_routing.resolve(cfg) is cfg
    with pytest.raises(RuntimeError):
        ai_routing.require_offline_consent(fallback)
    ai_routing.decide_offline(cfg, identifier, 'offline')
    ai_routing.require_offline_consent(fallback)
    assert ai_routing.resolve(cfg)['using_fallback']
    ai_routing.primary_succeeded(cfg, ai_routing.primary_epoch(cfg))
    assert ai_routing.offline_status(cfg)['outage_id'] is None
    with pytest.raises(RuntimeError):
        ai_routing.require_offline_consent(fallback)
    with pytest.raises(ValueError):
        ai_routing.decide_offline(cfg, identifier, 'offline')


def test_actual_transport_failure_cannot_call_or_load_local_model(outage, monkeypatch):
    cfg, clock = outage
    calls = []
    class Connected:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(ai_routing.socket, 'create_connection', lambda *a, **k: Connected())
    def post(url, *args, **kwargs):
        calls.append(url)
        assert 'remote.invalid' in url
        raise TimeoutError()
    monkeypatch.setattr(ai_client, '_post_json', post)
    for advance in (0, 120):
        clock[0] += advance
        with pytest.raises(RuntimeError, match='validation'):
            ai_client.chat_text(cfg, [], retry_empty=False, raise_errors=True)
    assert len(calls) == 2


def test_decision_route_rejects_stale_or_early_consent(outage, monkeypatch):
    from app.routers import settings
    cfg, clock = outage
    monkeypatch.setattr(settings.svc, 'get_section', lambda *a: cfg)
    ai_routing.unavailable(cfg)
    identifier = ai_routing.offline_status(cfg)['outage_id']
    client = TestClient(app)
    body = {'outage_id': identifier, 'decision': 'offline'}
    assert client.post('/v1/settings/ai/offline-decision', json=body).status_code == 409
    clock[0] += 120
    assert client.post('/v1/settings/ai/offline-decision', json=body).json()['using_fallback']
    assert client.post('/v1/settings/ai/offline-decision', json={**body, 'outage_id': 'old'}).status_code == 409
    assert not ai_routing.offline_status({**cfg, 'model': 'new'})['using_fallback']


def test_status_reads_never_probe_or_load(outage, monkeypatch):
    cfg, _ = outage
    monkeypatch.setattr(ai_routing.socket, 'create_connection', lambda *a, **k: pytest.fail('Status must be passive'))
    assert not ai_routing.status(cfg)['using_fallback']
    monkeypatch.setattr(connection_health, '_cache', {'key': connection_health._settings_key([cfg, {}]),
        'running': False, 'expires': 99999, 'values': {}})
    assert not connection_health.connection_status(cfg, {})['offline']['approval_required']


def test_stream_never_loads_without_consent(outage, monkeypatch):
    from app.services.ai_stream import ChatStream, ChatStreamError
    cfg, _ = outage
    ai_routing.unavailable(cfg)
    monkeypatch.setattr(ai_routing.subprocess, 'run', lambda *a, **k: pytest.fail('Unexpected local start'))
    def interrupted(self):
        assert not self.cfg.get('using_fallback')
        raise ChatStreamError('Serveur sans réponse') from TimeoutError()
        yield  # Keep the simulated transport a generator.
    monkeypatch.setattr(ChatStream, '_iterate', interrupted)
    with pytest.raises(ChatStreamError, match='validation'):
        list(ChatStream(cfg, []))
