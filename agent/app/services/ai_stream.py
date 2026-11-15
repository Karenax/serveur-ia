"""Real provider streams, forwarded as SSE and closed on browser cancellation."""
import asyncio
from contextlib import aclosing, contextmanager, nullcontext
import http.client
import json
import queue
import socket
import threading
import time
from urllib.parse import urlsplit

from anyio import CancelScope
from starlette.responses import StreamingResponse


STREAM_HEARTBEAT_SECONDS = 1
STREAM_HEARTBEAT = ": agent-keepalive\n\n"


class AssistantStreamingResponse(StreamingResponse):
    async def stream_response(self, send):
        try:
            await super().stream_response(send)
        finally:
            with CancelScope(shield=True):
                await self.body_iterator.aclose()


class ChatStreamError(RuntimeError):
    """Public error text, without upstream bodies, credentials or local paths."""


class ChatStream:
    def __init__(self, cfg, messages, max_tokens=1000):
        self.cfg, self.messages, self.max_tokens = cfg, messages, max_tokens
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._connection = None
        self._socket = None

    def close(self):
        self._stop.set()
        with self._lock:
            sock, connection = self._socket, self._connection
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        if connection:
            connection.close()

    def __iter__(self):
        from .llm_activity import foreground
        from . import ai_routing
        from .inference_scheduler import InferenceBusy
        with foreground():
            original = self.cfg
            epoch = ai_routing.primary_epoch(original)
            self.cfg = ai_routing.resolve(original)
            emitted = False
            useful = False
            try:
                with self._reservation():
                    for text in self._iterate():
                        emitted = True
                        useful = useful or bool(text.strip())
                        yield text
                if useful and not self._stop.is_set() and not self.cfg.get('using_fallback'):
                    ai_routing.primary_succeeded(original, epoch)
            except InferenceBusy as exc:
                if not self._stop.is_set():
                    raise ChatStreamError(str(exc)) from exc
            except ChatStreamError as exc:
                fallback = ai_routing.local_config(self.cfg)
                if emitted or self._stop.is_set() or fallback is None or not ai_routing.transport_failure(exc.__cause__):
                    raise
                ai_routing.unavailable(original)
                self.cfg = fallback
                try:
                    with self._reservation():
                        yield from self._iterate()
                except InferenceBusy as busy:
                    if not self._stop.is_set():
                        raise ChatStreamError(str(busy)) from busy

    @contextmanager
    def _reservation(self):
        from . import ai_routing
        from .inference_scheduler import engine_key, lease
        try:
            key = engine_key(str(self.cfg.get("base_url") or ""))
        except ValueError:
            # _iterate owns the public configuration error and validates before I/O.
            with nullcontext():
                yield
            return
        try:
            with lease(key, priority=0, cancel=self._stop):
                if self.cfg.get('using_fallback'):
                    try:
                        ai_routing.ensure_local(self.cfg)
                    except RuntimeError as exc:
                        raise ChatStreamError(str(exc)) from exc
                yield
        finally:
            ai_routing.release_recovered_fallback(self.cfg)

    def _iterate(self):
        provider = str(self.cfg.get("provider") or "none").lower()
        if not self.cfg.get("enabled") or provider not in {"ollama", "openai_compatible"}:
            raise ChatStreamError("Le fournisseur IA configuré ne permet pas cette réponse en direct.")
        base = str(self.cfg.get("base_url") or "").rstrip("/")
        try:
            url = urlsplit(base + ("/api/chat" if provider == "ollama" else "/v1/chat/completions"))
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
                raise ValueError("Invalid endpoint")
            port = url.port
        except ValueError:
            raise ChatStreamError("Adresse du serveur IA invalide.") from None
        timeout = max(1, int(self.cfg.get("timeout_s") or 600))
        connection_type = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
        connection = connection_type(url.hostname, port, timeout=min(timeout, 15))
        with self._lock:
            self._connection = connection
        response = None
        try:
            if self._stop.is_set():
                return
            headers = {"Content-Type": "application/json", "Accept": "application/x-ndjson" if provider == "ollama" else "text/event-stream"}
            if self.cfg.get("api_key"):
                headers["Authorization"] = "Bearer " + self.cfg["api_key"]
            payload = {"model": self.cfg.get("model", ""), "messages": self.messages, "stream": True}
            if provider == "ollama":
                payload.update(think=False, options={"num_predict": self.max_tokens, "temperature": 0.2})
            else:
                payload.update(temperature=0.2, max_tokens=self.max_tokens, reasoning_effort="none",
                               chat_template_kwargs={"enable_thinking": False})
            path = url.path + ("?" + url.query if url.query else "")
            connection.request("POST", path, body=json.dumps(payload).encode(), headers=headers)
            with self._lock:
                self._socket = connection.sock
            if self._stop.is_set():
                return
            if self._socket:
                self._socket.settimeout(timeout)
            response = connection.getresponse()
            if response.status != 200:
                if response.status in {502, 503, 504}:
                    raise ChatStreamError(f"Le serveur IA est indisponible (HTTP {response.status}).") from ConnectionError()
                raise ChatStreamError(f"Le serveur IA a refusé le streaming (HTTP {response.status}).")
            content_type = response.getheader("Content-Type", "").lower()
            expected = "application/x-ndjson" if provider == "ollama" else "text/event-stream"
            if expected not in content_type:
                raise ChatStreamError("Ce serveur IA ne renvoie pas de flux progressif ; le streaming n'est pas pris en charge.")
            parser = self._ollama if provider == "ollama" else self._openai
            yield from parser(response)
        except ChatStreamError:
            raise
        except (OSError, http.client.HTTPException, ValueError, TypeError, KeyError) as exc:
            if not self._stop.is_set():
                raise ChatStreamError("La réponse en direct a été interrompue par le serveur IA ou le réseau.") from exc
        finally:
            if response:
                response.close()
            connection.close()

    def _lines(self, response):
        while not self._stop.is_set():
            raw = response.readline(65537)
            if not raw:
                return
            if len(raw) > 65536:
                raise ChatStreamError("Un fragment de réponse IA dépasse la limite autorisée.")
            yield raw.decode("utf-8", "strict").rstrip("\r\n")

    def _openai(self, response):
        data, finished, size = [], False, 0
        for line in self._lines(response):
            if line.startswith("data:"):
                data.append(line[5:].lstrip(" "))
                continue
            if line or not data:
                continue
            event = "\n".join(data)
            data = []
            if event == "[DONE]":
                finished = True
                break
            chunk = json.loads(event)
            if chunk.get("error"):
                raise ChatStreamError("Le serveur IA a signalé une erreur pendant la réponse.")
            for choice in chunk.get("choices") or []:
                if choice.get("index", 0) != 0:
                    continue
                text = (choice.get("delta") or {}).get("content") or ""
                if not isinstance(text, str):
                    raise ChatStreamError("Format de réponse progressive IA incompatible.")
                size += len(text)
                if size > 100000:
                    raise ChatStreamError("La réponse IA dépasse la limite de longueur autorisée.")
                if text:
                    yield text
                if choice.get("finish_reason"):
                    finished = True
        if not finished and not self._stop.is_set():
            raise ChatStreamError("Le flux IA s'est fermé avant la fin de la réponse.")

    def _ollama(self, response):
        finished, size = False, 0
        for line in self._lines(response):
            if not line:
                continue
            chunk = json.loads(line)
            if chunk.get("error"):
                raise ChatStreamError("Le serveur IA a signalé une erreur pendant la réponse.")
            text = (chunk.get("message") or {}).get("content") or ""
            if not isinstance(text, str):
                raise ChatStreamError("Format de réponse progressive IA incompatible.")
            size += len(text)
            if size > 100000:
                raise ChatStreamError("La réponse IA dépasse la limite de longueur autorisée.")
            if text:
                yield text
            if chunk.get("done"):
                finished = True
                break
        if not finished and not self._stop.is_set():
            raise ChatStreamError("Le flux IA s'est fermé avant la fin de la réponse.")


def _event(kind, value):
    return f"event: {kind}\ndata: {json.dumps(value, ensure_ascii=False)}\n\n"


async def prepared_sse_events(prepare, request, finalize_metadata):
    """Keep cancellation working while project sources are still being recalled."""
    if await request.is_disconnected():
        return
    lookup = asyncio.create_task(prepare())
    try:
        while not lookup.done():
            done, _ = await asyncio.wait((lookup,), timeout=STREAM_HEARTBEAT_SECONDS)
            if await request.is_disconnected():
                return
            if not done:
                yield STREAM_HEARTBEAT
        cfg, messages, metadata = lookup.result()
    except Exception:
        yield _event("error", {"message": "La recherche des sources a été interrompue."})
        return
    finally:
        if not lookup.done():
            lookup.cancel()
        with CancelScope(shield=True):
            await asyncio.gather(lookup, return_exceptions=True)

    async with aclosing(sse_events(ChatStream(cfg, messages), metadata, request,
                                   finalize_metadata=lambda: finalize_metadata(metadata))) as frames:
        async for frame in frames:
            yield frame


async def sse_events(stream, metadata, request, finalize_metadata=None):
    """The queue preserves actual provider fragments and limits buffered output."""
    fragments = queue.Queue(maxsize=32)
    stop = threading.Event()

    def send(kind, value):
        while not stop.is_set():
            try:
                fragments.put((kind, value), timeout=0.1)
                return
            except queue.Full:
                continue

    def produce():
        try:
            for text in stream:
                if stop.is_set():
                    break
                send("delta", text)
            send("end", None)
        except Exception as exc:
            send("error", str(exc) if isinstance(exc, ChatStreamError) else "La réponse en direct a été interrompue.")
        finally:
            stream.close()

    worker = threading.Thread(target=produce, name="assistant-stream", daemon=True)
    try:
        if await request.is_disconnected():
            return
        yield _event("metadata", metadata)
        worker.start()
        answer = []
        heartbeat = time.monotonic() + STREAM_HEARTBEAT_SECONDS
        while not stop.is_set():
            if await request.is_disconnected():
                break
            try:
                kind, value = await asyncio.to_thread(fragments.get, True, 0.2)
            except queue.Empty:
                if time.monotonic() >= heartbeat:
                    # Flush the proxy even when the provider waits before sending more text.
                    heartbeat = time.monotonic() + STREAM_HEARTBEAT_SECONDS
                    yield STREAM_HEARTBEAT
                continue
            if kind == "delta":
                answer.append(value)
                heartbeat = time.monotonic() + STREAM_HEARTBEAT_SECONDS
                yield _event("delta", {"text": value})
            elif kind == "end":
                content = "".join(answer).strip()
                if content:
                    completed = finalize_metadata() if finalize_metadata else metadata
                    yield _event("done", {"answer": content, **completed})
                else:
                    yield _event("error", {"message": "Le serveur IA a terminé sans texte de réponse."})
                break
            else:
                yield _event("error", {"message": value})
                break
    finally:
        stop.set()
        stream.close()
