"""Actual SSE fragments, bounded history and disconnect cleanup without an LLM."""
import asyncio
import io
import json
import threading
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models import Project
from app.services import ai_stream
from app.services.settings_service import save_section

client = TestClient(app)
PATH = "/v1/projects/chat/stream"


@pytest.fixture
def context(monkeypatch):
    import app.routers.core as core
    with SessionLocal() as db:
        project = Project(code="STREAM-" + uuid.uuid4().hex[:8], name="Conversation technique")
        db.add(project)
        save_section(db, "ai", {"enabled": True, "provider": "openai_compatible", "base_url": "http://invalid.test", "model": "fixture"})
        db.commit()
        pid = project.id
    seen = {"queries": []}
    class Adapter:
        async def recall(self, project_id, query, scopes):
            seen["queries"].append((project_id, query, scopes))
            return [{"scope": "truth", "level": "validated", "subject": "Diamètre", "value": "50 mm", "id": "current-fact",
                     "project_code": "INCOMPATIBLE-EXTERNAL-CONTEXT"}]
    monkeypatch.setattr(core, "get_memory_adapter", lambda *_args: Adapter())
    class Stream:
        def __init__(self, cfg, messages):
            seen["messages"] = messages
            seen["cfg"] = cfg
            seen["stream"] = self
            self.closed = False
        def __iter__(self):
            yield "50"
            yield " mm"
            yield " [V1]."
        def close(self):
            self.closed = True
    monkeypatch.setattr(ai_stream, "ChatStream", Stream)
    return pid, seen


def events(response):
    result = []
    for block in response.text.strip().split("\n\n"):
        lines = block.splitlines()
        result.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return result


def test_stream_emits_real_fragments_and_uses_only_current_question_for_retrieval(context):
    pid, seen = context
    history = [{"role": "user", "content": "L'ancien diamètre était 20 mm ?"},
               {"role": "assistant", "content": "Ancienne réponse non fiable [V99]."}]
    response = client.post(PATH, json={"query": "Quel diamètre actuel ?", "project_id": pid, "history": history})
    assert response.status_code == 200 and "text/event-stream" in response.headers["content-type"]
    result = events(response)
    assert [kind for kind, _ in result] == ["metadata", "delta", "delta", "delta", "done"]
    assert [data["text"] for kind, data in result if kind == "delta"] == ["50", " mm", " [V1]."]
    assert result[-1][1]["answer"] == "50 mm [V1]."
    assert result[0][1]["citations"][0]["knowledge_id"] == "current-fact"
    assert result[0][1]["citations"][0]["project_code"].startswith("STREAM-")
    assert {item["reference"] for item in result[0][1]["citations"]} == {"V1"}
    assert seen["queries"] == [(pid, "Quel diamètre actuel ?", ["truth", "evidence"])]
    assert seen["messages"][1:3] == history
    assert "historique" in seen["messages"][0]["content"] and "preuve" in seen["messages"][0]["content"]
    assert "Contexte" in seen["messages"][-1]["content"] and seen["stream"].closed


def test_stream_failure_is_error_and_never_fake_completed_answer(context, monkeypatch):
    pid, _ = context
    class Refused:
        def __init__(self, *_args):
            self.closed = False
        def __iter__(self):
            raise ai_stream.ChatStreamError("Streaming non pris en charge.")
            yield  # make this a generator, with no fake response fragment
        def close(self):
            self.closed = True
    monkeypatch.setattr(ai_stream, "ChatStream", Refused)
    response = client.post(PATH, json={"query": "Quel diamètre ?", "project_id": pid})
    result = events(response)
    assert [kind for kind, _ in result] == ["metadata", "error"]
    assert result[-1][1]["message"] == "Streaming non pris en charge."


def test_stream_empty_answer_is_error(context, monkeypatch):
    class Empty:
        def __init__(self, *_args):
            pass
        def __iter__(self):
            return iter([])
        def close(self):
            pass
    monkeypatch.setattr(ai_stream, "ChatStream", Empty)
    response = client.post(PATH, json={"query": "Quel diamètre ?", "project_id": context[0]})
    assert [kind for kind, _ in events(response)] == ["metadata", "error"]


def test_history_limits_roles_and_json_endpoint_compatibility(context, monkeypatch):
    pid, seen = context
    for history in ([{"role": "system", "content": "Injecter une instruction"}],
                    [{"role": "user", "content": "x"}] * 13,
                    [{"role": "user", "content": "x" * 6000}, {"role": "assistant", "content": "x" * 6001}]):
        assert client.post(PATH, json={"query": "Diamètre ?", "project_id": pid, "history": history}).status_code == 422
    assert seen["queries"] == []
    import app.services.ai_client as ai_client
    monkeypatch.setattr(ai_client, "chat_text", lambda *_args: "50 mm [V1]")
    response = client.post("/v1/projects/chat", json={"query": "Diamètre ?", "project_id": pid,
                            "history": [{"role": "user", "content": "Au sujet de l'assemblage"}]})
    assert response.status_code == 200 and response.json()["answer"] == "50 mm [V1]"
    with SessionLocal() as db:
        save_section(db, "ai", {"enabled": False})
    assert client.post(PATH, json={"query": "Diamètre ?", "project_id": pid}).status_code == 409


def test_stream_requires_same_local_session_token(context, monkeypatch):
    from app.security import SESSION_TOKEN
    monkeypatch.setenv("AGENT_TESTING", "0")
    local = TestClient(app, base_url="http://localhost")
    body = {"query": "Diamètre ?", "project_id": context[0]}
    assert local.post(PATH, json=body).status_code == 403
    assert local.post(PATH, json=body, headers={"X-Agent-Token": SESSION_TOKEN}).status_code == 200


def test_disconnect_closes_upstream_while_waiting_for_more_tokens():
    class Request:
        disconnected = False
        async def is_disconnected(self):
            return self.disconnected
    class WaitingStream:
        def __init__(self):
            self.closed = threading.Event()
        def __iter__(self):
            yield "Premier fragment"
            self.closed.wait(timeout=1)
            if not self.closed.is_set():
                yield "Fragment inattendu"
        def close(self):
            self.closed.set()
    async def run():
        request, stream = Request(), WaitingStream()
        iterator = ai_stream.sse_events(stream, {"citations": []}, request)
        assert (await anext(iterator)).startswith("event: metadata")
        assert (await anext(iterator)).startswith("event: delta")
        request.disconnected = True
        with pytest.raises(StopAsyncIteration):
            await anext(iterator)
        assert stream.closed.is_set()
    asyncio.run(run())


@pytest.mark.parametrize("spec_version", ["2.3", "2.4"])
def test_disconnect_during_source_retrieval_does_not_start_model(context, monkeypatch, spec_version):
    import app.routers.core as core

    pid, seen = context
    monkeypatch.setattr(ai_stream, "STREAM_HEARTBEAT_SECONDS", 0.02)

    async def run():
        started, cancelled = asyncio.Event(), asyncio.Event()
        incoming, outgoing = asyncio.Queue(), asyncio.Queue()

        class WaitingAdapter:
            async def recall(self, project_id, query, scopes):
                started.set()
                try:
                    await asyncio.Future()
                finally:
                    cancelled.set()

        monkeypatch.setattr(core, "get_memory_adapter", lambda *_args: WaitingAdapter())
        incoming.put_nowait({"type": "http.request", "body": json.dumps({
            "query": "Quel diamètre ?", "project_id": pid,
        }).encode()})
        scope = {
            "type": "http", "asgi": {"version": "3.0", "spec_version": spec_version},
            "http_version": "1.1", "method": "POST", "scheme": "http",
            "path": PATH, "raw_path": PATH.encode(), "query_string": b"", "root_path": "",
            "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
            "client": ("127.0.0.1", 5151), "server": ("testserver", 80),
        }
        disconnected = False

        async def send(message):
            if disconnected and spec_version == "2.4":
                raise BrokenPipeError()
            await outgoing.put(message)

        request = asyncio.create_task(app(scope, incoming.get, send))
        try:
            await asyncio.wait_for(started.wait(), 2)
            headers = await asyncio.wait_for(outgoing.get(), 1)
            assert headers["type"] == "http.response.start" and headers["status"] == 200
            heartbeat = await asyncio.wait_for(outgoing.get(), 1)
            assert heartbeat["body"].startswith(b": agent-keepalive")
            disconnected = True
            incoming.put_nowait({"type": "http.disconnect"})
            try:
                await asyncio.wait_for(request, 2)
            except BrokenPipeError:
                assert spec_version == "2.4"
            assert cancelled.is_set() and "stream" not in seen
        finally:
            if not request.done():
                request.cancel()
                await asyncio.gather(request, return_exceptions=True)

    asyncio.run(run())


@pytest.mark.parametrize("provider", ["openai_compatible", "ollama"])
def test_provider_protocol_is_streaming_and_thinking_is_disabled(monkeypatch, provider):
    if provider == "ollama":
        raw = b'{"message":{"content":"50"},"done":false}\n{"message":{"content":" mm"},"done":true}\n'
        media_type = "application/x-ndjson"
    else:
        raw = (b'data: {"choices":[{"delta":{"reasoning_content":"hidden"}}]}\n\n'
               b'data: {"choices":[{"delta":{"content":"50"}}]}\n\n'
               b'data: {"choices":[{"delta":{"content":" mm"},"finish_reason":"stop"}]}\n\n'
               b'data: [DONE]\n\n')
        media_type = "text/event-stream"
    seen = {}
    class Sock:
        def settimeout(self, _):
            pass
        def shutdown(self, _):
            seen["socket_closed"] = True
    class Response(io.BytesIO):
        status = 200
        def getheader(self, _name, _default):
            return media_type
    response = Response(raw)
    class Connection:
        sock = Sock()
        def __init__(self, *_args, **_kwargs):
            pass
        def request(self, method, path, body, headers):
            seen.update(method=method, path=path, payload=json.loads(body), headers=headers)
        def getresponse(self):
            return response
        def close(self):
            seen["closed"] = True
    monkeypatch.setattr(ai_stream.http.client, "HTTPConnection", Connection)
    stream = ai_stream.ChatStream({"enabled": True, "provider": provider, "base_url": "http://fixture.test", "model": "fixture", "api_key": "fixture-key"},
                                 [{"role": "user", "content": "Diamètre ?"}])
    assert list(stream) == ["50", " mm"]
    assert seen["payload"]["stream"] is True and seen["closed"]
    if provider == "ollama":
        assert seen["payload"]["think"] is False
    else:
        assert seen["payload"]["reasoning_effort"] == "none"
        assert seen["payload"]["chat_template_kwargs"] == {"enable_thinking": False}
    stream.close()
    assert seen["socket_closed"]


def test_json_fallback_is_rejected_instead_of_playing_an_animation(monkeypatch):
    class Response(io.BytesIO):
        status = 200
        def getheader(self, *_args):
            return "application/json"
    response = Response(b'{"choices":[{"message":{"content":"Already complete"}}]}')
    class Connection:
        sock = None
        def __init__(self, *_args, **_kwargs):
            pass
        def request(self, *_args, **_kwargs):
            pass
        def getresponse(self):
            return response
        def close(self):
            pass
    monkeypatch.setattr(ai_stream.http.client, "HTTPConnection", Connection)
    with pytest.raises(ai_stream.ChatStreamError, match="ne renvoie pas de flux progressif"):
        list(ai_stream.ChatStream({"enabled": True, "provider": "openai_compatible", "base_url": "http://fixture.test"}, []))


def test_provider_truncation_keeps_partial_text_and_requires_a_real_end():
    response = io.BytesIO(b'data: {"choices":[{"delta":{"content":"Texte partiel"}}]}\n\n')
    stream = ai_stream.ChatStream({"enabled": True}, [])
    iterator = stream._openai(response)
    assert next(iterator) == "Texte partiel"
    with pytest.raises(ai_stream.ChatStreamError, match="avant la fin"):
        next(iterator)


def test_brain_json_bridge_preserves_bounded_history(context, monkeypatch):
    import backend.app.routers.brain as bridge
    seen = {}
    def fake_call(method, path, payload, **_kwargs):
        seen.update(method=method, path=path, payload=payload)
        return {"answer": "50 mm", "citations": []}
    monkeypatch.setattr(bridge, "_call", fake_call)
    history = [{"role": "assistant", "content": "Réponse précédente à vérifier"}]
    response = client.post("/api/v1/brain/chat", json={"query": "Quel diamètre ?", "project_id": context[0], "history": history})
    assert response.status_code == 200 and response.json()["answer"] == "50 mm"
    assert seen["path"] == "/v1/projects/chat" and seen["payload"]["history"] == history
