"""Connection diagnostics honor configured generation time, without inference."""
from contextlib import nullcontext

import pytest

from app.services import ai_client, ai_routing


@pytest.mark.parametrize('using_fallback', [False, True])
@pytest.mark.parametrize('configured, expected', [(1, 1), (60, 60), (120, 120), (300, 300), (None, 15)])
def test_diagnostic_transport_uses_setting_without_changing_lease_or_prompt(monkeypatch, using_fallback, configured, expected):
    calls, reservations, confirmed = [], [], []
    cfg = {'enabled':True, 'provider':'openai_compatible', 'base_url':'http://127.0.0.1:1234',
           'model':'fictional-model', 'using_fallback':using_fallback}
    if configured is not None:
        cfg['timeout_s'] = configured

    def local(configuration):
        reservations.append(configuration)
        return nullcontext()

    def post(url, payload, headers, timeout):
        calls.append((url, payload, headers, timeout))
        return {'choices':[{'message':{'content':'OK'}}]}

    monkeypatch.setattr(ai_client, '_post_json', post)
    monkeypatch.setattr(ai_routing, 'local_generation', local)
    monkeypatch.setattr(ai_routing, 'primary_epoch', lambda value:7)
    monkeypatch.setattr(ai_routing, 'primary_succeeded', lambda value, epoch:confirmed.append((value,epoch)))
    assert ai_client.check_connection(cfg)['ok'] is True
    assert len(calls) == 1 and calls[0][3] == expected
    assert calls[0][1] == {'model':'fictional-model', 'messages':[{'role':'user','content':'Réponds uniquement OK.'}],
                          'max_tokens':32, 'reasoning_effort':'none', 'chat_template_kwargs':{'enable_thinking':False}}
    assert reservations == ([cfg] if using_fallback else [])
    assert confirmed == [(cfg,7)]


def test_configured_timeout_does_not_turn_transport_failure_into_success(monkeypatch):
    def timeout(*args, **kwargs):
        assert kwargs['timeout'] == 120
        raise TimeoutError('fictional timeout')

    monkeypatch.setattr(ai_client, '_post_json', timeout)
    monkeypatch.setattr(ai_routing, 'primary_succeeded', lambda *args:pytest.fail('Failure cannot release the fallback'))
    result = ai_client.check_connection({'enabled':True,'provider':'openai_compatible',
        'base_url':'http://fictional.invalid','model':'fictional','timeout_s':120})
    assert result['ok'] is False and result['reason'].startswith('TimeoutError:')
