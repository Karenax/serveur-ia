"""Protocol recovery uses the real HTTP client, without any network or model."""
import io
import json
import urllib.error

import pytest

from app.services import ai_client, ai_routing, llm_usage


@pytest.fixture
def client(monkeypatch):
    cfg = {"enabled": True, "provider": "openai_compatible", "model": "configured-model",
           "base_url": "http://remote.invalid:1234", "api_key": "test-only"}
    monkeypatch.setattr(ai_routing, "resolve", lambda value: value)
    monkeypatch.setattr(ai_routing, "primary_succeeded", lambda *args: None)
    monkeypatch.setattr(ai_routing, "local_config", lambda *args: pytest.fail("Unexpected local fallback"))
    calls, replies = [], []

    def request(req, timeout):
        calls.append((req.full_url, json.loads(req.data), dict(req.headers), timeout))
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return io.BytesIO(json.dumps(reply).encode())

    monkeypatch.setattr(ai_client.urllib.request, "urlopen", request)
    return cfg, calls, replies


def rejection(body=b'{"error":"Model is unloaded."}', code=400):
    return urllib.error.HTTPError("http://remote.invalid:1234/v1/chat/completions", code,
                                  "rejected", {}, io.BytesIO(body))


def success(content="Texte fictif"):
    return {"choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}}


def call(cfg, **kwargs):
    return ai_client.chat_text(cfg, [{"role": "user", "content": "Fictif"}],
                               max_tokens=1200, timeout=30, retry_empty=False,
                               raise_errors=True, **kwargs)


def test_exact_rejection_retries_same_request_and_accounts_both_attempts(client):
    cfg, calls, replies = client
    replies.extend([rejection(), success()])
    with llm_usage.collect() as usage:
        assert call(cfg) == "Texte fictif"
    assert len(calls) == 2
    assert calls[0][:3] == calls[1][:3]
    assert calls[0][1]["max_tokens"] == 1200
    assert calls[0][2]["Authorization"] == "Bearer test-only"
    assert 0 < calls[1][3] <= calls[0][3] == 30
    assert usage[0]["error_type"] == "ModelUnloadedError"
    assert usage[0]["total_tokens"] is None
    assert usage[1]["total_tokens"] == 13
    assert llm_usage.summarize(usage)["complete"] is False


@pytest.mark.parametrize("body,code", [
    (b'{"error":"context too long"}', 400),
    (b'{"error":"Model is unloaded."}', 401),
    (b'{"error":"Model is unloaded.","other":true}', 400),
    (b'not json', 400),
])
def test_other_rejections_not_retried_and_body_preserved(client, monkeypatch, body, code):
    cfg, calls, replies = client
    monkeypatch.setattr(ai_routing, "local_config", lambda *args: None)
    replies.append(rejection(body, code))
    with pytest.raises(urllib.error.HTTPError) as error:
        call(cfg)
    assert len(calls) == 1
    assert error.value.read() == body
    assert not isinstance(error.value, ai_client.ModelUnloadedError)


@pytest.mark.parametrize("structured", [False, True])
def test_repeated_unloaded_stops_after_two_including_structured_json(client, structured):
    cfg, calls, replies = client
    replies.extend([rejection(), rejection()])
    with pytest.raises(ai_client.ModelUnloadedError):
        if structured:
            ai_client.chat_json(cfg, {"model": cfg["model"], "messages": [], "max_tokens": 1200},
                                json_schema={"type": "object"}, retry_empty=False, raise_errors=True)
        else:
            call(cfg)
    assert len(calls) == 2


def test_diagnostic_consuming_error_body_does_not_disable_recovery(client, monkeypatch):
    cfg, calls, replies = client
    original = ai_client._post_json

    def traced(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except urllib.error.HTTPError as error:
            assert error.read() == b'{"error":"Model is unloaded."}'
            raise

    monkeypatch.setattr(ai_client, "_post_json", traced)
    replies.extend([rejection(), success()])
    assert call(cfg) == "Texte fictif"
    assert len(calls) == 2


def test_blank_answer_stays_one_attempt(client):
    cfg, calls, replies = client
    replies.append(success(""))
    assert call(cfg) is None
    assert len(calls) == 1


def test_expired_budget_keeps_original_rejection(client, monkeypatch):
    cfg, calls, replies = client
    ticks = iter([0, 31])
    # Patch only the client clock: scheduler uses the shared time module too.
    from types import SimpleNamespace
    monkeypatch.setattr(ai_client, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    monkeypatch.setattr(ai_routing, "local_config", lambda *args: None)
    replies.append(rejection())
    with pytest.raises(ai_client.ModelUnloadedError):
        call(cfg)
    assert len(calls) == 1


def test_second_transport_failure_does_not_start_local_model(client):
    cfg, calls, replies = client
    replies.extend([rejection(), TimeoutError("test")])
    with pytest.raises(TimeoutError):
        call(cfg)
    assert len(calls) == 2
