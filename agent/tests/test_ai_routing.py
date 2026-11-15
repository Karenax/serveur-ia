from contextlib import contextmanager
import urllib.error

import pytest
from pydantic import ValidationError

from app.routers.settings import AISettings
from app.services import ai_client, ai_routing
from app.services.ai_stream import ChatStream, ChatStreamError


@pytest.fixture
def cfg(monkeypatch):
    monkeypatch.setattr(ai_routing, "_down_until", {})
    config = {"enabled": True, "provider": "openai_compatible", "base_url": "http://remote:1234",
            "model": "remote-model", "api_key": "private-token", "fallback_enabled": True,
            "fallback_model": "google/gemma-4-e4b", "fallback_base_url": "http://127.0.0.1:1234"}
    # Legacy transport/CLI tests run after explicit user consent. Admission is
    # covered separately below with the actual two-minute clock and HTTP calls.
    monkeypatch.setattr(ai_routing, '_outages', {ai_routing._consent_key(config): {
        'since': ai_routing.time.monotonic()-120, 'id': 'approved-test', 'decision': 'offline'}})
    return config


class Connected:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_down_uses_local_and_recovers_after_cooldown(cfg, monkeypatch):
    def down(*args, **kwargs):
        raise ConnectionRefusedError()
    monkeypatch.setattr(ai_routing.socket, "create_connection", down)
    local = ai_routing.resolve(cfg)
    assert local["using_fallback"] and local["api_key"] == ""
    assert local["model"] == "google/gemma-4-e4b"
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *a, **k: Connected())
    assert ai_routing.resolve(cfg)["using_fallback"]
    monkeypatch.setattr(ai_routing.time, "monotonic", lambda: 10**12)
    assert ai_routing.resolve(cfg) is cfg
    assert cfg["model"] == "remote-model" and cfg["api_key"] == "private-token"


@pytest.mark.parametrize("exc", [urllib.error.URLError("offline"), TimeoutError(),
                                  urllib.error.HTTPError("", 503, "down", {}, None)])
def test_failure_after_connect_retries_local_without_remote_key(cfg, monkeypatch, exc):
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *a, **k: Connected())
    calls = []
    def post(url, body, headers=None, timeout=60):
        calls.append((url, body, headers))
        if "remote" in url:
            raise exc
        return {"choices": [{"message": {"content": '{"ok":true}'}}]}
    monkeypatch.setattr(ai_client, "_post_json", post)
    out = ai_client.chat_json(cfg, {"model": "remote-model", "messages": []},
                              json_schema={"type": "object"}, retry_empty=False, raise_errors=True)
    assert out == '{"ok":true}'
    assert len(calls) == 2
    assert calls[1][0] == "http://127.0.0.1:1234/v1/chat/completions"
    assert calls[1][1]["model"] == "google/gemma-4-e4b"
    assert calls[1][1]["reasoning_effort"] == "none"
    assert calls[1][1]["chat_template_kwargs"]["enable_thinking"] is False
    assert calls[1][1]["response_format"]["type"] == "json_schema"
    assert calls[1][2] == {}


@pytest.mark.parametrize("failure", [ConnectionRefusedError("lost after probe"), TimeoutError(),
    urllib.error.HTTPError("", 503, "unavailable", {}, None)])
def test_manual_structured_reply_preserves_schema_on_transport_failover(cfg, monkeypatch, failure):
    """An outage between TCP probe and HTTP must not lose a manual suggestion."""
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *a, **k: Connected())
    monkeypatch.setattr(ai_routing, "_failure_epochs", {})
    releases, calls, reservation = [], [], []
    monkeypatch.setattr(ai_routing, "primary_succeeded", lambda *a: releases.append(a))

    @contextmanager
    def local_generation(selected, **kwargs):
        assert selected["api_key"] == "" and selected["using_fallback"]
        reservation.append("held")
        try:
            yield
        finally:
            reservation.append("released")

    monkeypatch.setattr(ai_routing, "local_generation", local_generation)
    schema = {"type": "json_schema", "json_schema": {"name": "additions", "strict": True,
              "schema": {"type": "object", "properties": {"additions": {"type": "array"}},
                         "required": ["additions"], "additionalProperties": False}}}
    messages = [{"role": "user", "content": "FICTITIOUS SOURCE [S1]"}]

    def post(url, payload, headers=None, timeout=60):
        calls.append((url, payload, headers))
        assert payload["response_format"] == schema and payload["messages"] == messages
        if "remote" in url:
            raise failure
        assert reservation == ["held"] and headers == {}
        assert payload["model"] == cfg["fallback_model"]
        return {"choices": [{"message": {"content": '{"additions":[]}'}}]}

    monkeypatch.setattr(ai_client, "_post_json", post)
    assert ai_client.chat_text(cfg, messages, response_format=schema,
        retry_empty=False, raise_errors=True) == '{"additions":[]}'
    assert len(calls) == 2 and reservation == ["held", "released"] and releases == []
    assert calls[0][2] == {"Authorization": "Bearer private-token"}
    assert cfg["base_url"] in ai_routing._down_until
    assert cfg["api_key"] == "private-token" and cfg["model"] == "remote-model"


@pytest.mark.parametrize("status", [400, 401, 404, 422])
def test_structured_schema_or_auth_refusal_never_switches_transport(cfg, monkeypatch, status):
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *a, **k: Connected())
    monkeypatch.setattr(ai_routing, "local_generation", lambda *a, **k: pytest.fail("Unexpected local load"))
    calls = []
    def post(*args, **kwargs):
        calls.append(args)
        raise urllib.error.HTTPError("", status, "request refused", {}, None)
    monkeypatch.setattr(ai_client, "_post_json", post)
    with pytest.raises(urllib.error.HTTPError):
        ai_client.chat_text(cfg, [], response_format={"type": "json_schema"},
                            retry_empty=False, raise_errors=True)
    assert len(calls) == 1 and not ai_routing._down_until


def test_automatic_structured_transport_failure_never_loads_rescue(cfg, monkeypatch):
    cfg = {**cfg, "fallback_enabled": False, "fallback_autostart": False}
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *a, **k: Connected())
    monkeypatch.setattr(ai_routing, "local_generation", lambda *a, **k: pytest.fail("Automatic rescue forbidden"))
    monkeypatch.setattr(ai_routing, "_failure_epochs", {})
    calls = []
    def post(*args, **kwargs):
        calls.append(args)
        raise TimeoutError("network lost")
    monkeypatch.setattr(ai_client, "_post_json", post)
    with pytest.raises(TimeoutError):
        ai_client.chat_text(cfg, [], response_format={"type": "json_schema"},
                            retry_empty=False, raise_errors=True)
    assert len(calls) == 1
    assert cfg['base_url'] in ai_routing._down_until


def test_unusable_json_is_not_a_server_outage(cfg, monkeypatch):
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *a, **k: Connected())
    calls = []
    def post(*args, **kwargs):
        calls.append(args)
        raise urllib.error.HTTPError("", 401, "unauthorized", {}, None)
    monkeypatch.setattr(ai_client, "_post_json", post)
    assert ai_client.chat_text(cfg, []) is None
    assert len(calls) == 1 and not ai_routing._down_until


def test_disabled_fallback_never_probes(cfg, monkeypatch):
    cfg["fallback_enabled"] = False
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *a, **k: pytest.fail("probe"))
    assert ai_routing.resolve(cfg) is cfg


@pytest.mark.parametrize("provider, path, thinking", [
    ("openai_compatible", "/v1/chat/completions", {
        "reasoning_effort": "low", "chat_template_kwargs": {"enable_thinking": True},
    }),
    ("ollama", "/api/chat", {"think": True}),
])
def test_mail_analysis_requests_thinking(cfg, monkeypatch, provider, path, thinking):
    cfg = {**cfg, "provider": provider, "fallback_enabled": False}

    def post(url, payload, headers=None, timeout=60):
        assert url == cfg["base_url"] + path
        assert {key: payload[key] for key in thinking} == thinking
        message = {"content": '{"summary":"Réunion déplacée"}', "reasoning_content": "Réflexion"}
        return {"message": message} if provider == "ollama" else {"choices": [{"message": message}]}

    monkeypatch.setattr(ai_client, "_post_json", post)
    result = ai_client.classify_email(cfg, "Réunion", "Report à mardi", "test@example.net", [])
    assert result["summary"] == "Réunion déplacée"


@pytest.mark.parametrize("url", ["http://remote:1234", "https://127.0.0.1:1234", "http://user:secret@localhost:1234"])
def test_fallback_settings_only_accept_loopback(url):
    with pytest.raises(ValidationError):
        AISettings(fallback_base_url=url)


def test_stream_switches_before_first_token_only(cfg, monkeypatch):
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *a, **k: Connected())
    def iterate(self):
        if not self.cfg.get("using_fallback"):
            raise ChatStreamError("offline") from ConnectionRefusedError()
        yield "local"
    monkeypatch.setattr(ChatStream, "_iterate", iterate)
    assert list(ChatStream(cfg, [])) == ["local"]


def test_stream_never_duplicates_partial_output(cfg, monkeypatch):
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *a, **k: Connected())
    def iterate(self):
        yield "partial"
        raise ChatStreamError("offline") from ConnectionRefusedError()
    monkeypatch.setattr(ChatStream, "_iterate", iterate)
    stream = iter(ChatStream(cfg, []))
    assert next(stream) == "partial"
    with pytest.raises(ChatStreamError):
        next(stream)
    assert not ai_routing._down_until


def test_legacy_settings_save_preserves_fallback(cfg):
    from app.db import SessionLocal
    from app.services.settings_service import get_section, save_section
    with SessionLocal() as db:
        save_section(db, "ai", cfg)
        old_client = AISettings(provider="openai_compatible", base_url="http://remote:1234", model="new-remote-model")
        save_section(db, "ai", old_client.model_dump(exclude_unset=True))
        result = get_section(db, "ai")
    assert result["fallback_enabled"] and result["fallback_model"] == "google/gemma-4-e4b"
    assert result["model"] == "new-remote-model"


def test_local_autostart_uses_installed_cli(cfg, monkeypatch, tmp_path):
    from pathlib import Path
    from types import SimpleNamespace
    cli = tmp_path / ".lmstudio" / "bin" / "lms.exe"
    cli.parent.mkdir(parents=True)
    cli.touch()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    calls = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'{"models":[{"key":"google/gemma-4-e4b","loaded_instances":[{"id":"google/gemma-4-e4b"}]}]}'
    def get(*args, **kwargs):
        if len(calls) < 2:
            raise urllib.error.URLError("offline")
        return Response()
    monkeypatch.setattr(ai_routing.urllib.request, "urlopen", get)
    monkeypatch.setattr(ai_routing.subprocess, "run", lambda args, **kw: calls.append(args) or SimpleNamespace(returncode=0))
    cfg["fallback_autostart"] = True
    ai_routing.ensure_local(ai_routing.local_config(cfg))
    assert calls[0][1:] == ["server", "start", "--port", "1234", "--bind", "127.0.0.1"]
    assert calls[1][1:] == ["load", "google/gemma-4-e4b", "--identifier", "google/gemma-4-e4b", "--context-length", "8192", "--yes"]


def test_downloaded_but_unloaded_model_is_explicitly_loaded(cfg, monkeypatch, tmp_path):
    import json
    from pathlib import Path
    from types import SimpleNamespace
    cli = tmp_path / ".lmstudio" / "bin" / "lms.exe"
    cli.parent.mkdir(parents=True)
    cli.touch()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    calls = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return json.dumps({"models": [{"key": "google/gemma-4-e4b",
                               "loaded_instances": [{"id": "google/gemma-4-e4b"}] if len(calls) == 2 else []}]}).encode()
    def get(url, **kwargs):
        assert url.endswith("/api/v1/models")
        return Response()
    monkeypatch.setattr(ai_routing.urllib.request, "urlopen", get)
    monkeypatch.setattr(ai_routing.subprocess, "run", lambda args, **kw: calls.append(args) or SimpleNamespace(returncode=0))
    cfg["fallback_autostart"] = True
    ai_routing.ensure_local(ai_routing.local_config(cfg))
    assert len(calls) == 2 and calls[1][1] == "load"
