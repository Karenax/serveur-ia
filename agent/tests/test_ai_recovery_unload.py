"""Recovery releases only the configured local rescue, without real LLM I/O."""
from contextlib import contextmanager
import io
import itertools
import json
from pathlib import Path
import threading
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from app.services import ai_client, ai_routing, inference_scheduler, llm_activity
from app.services.ai_stream import ChatStream, ChatStreamError


REAL_THREAD = threading.Thread
MODEL = "google/gemma-4-e4b"


class Connected:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class LocalServer:
    """REST inventory includes a different model and two differently named rescues."""
    def __init__(self):
        self.instances = ["rescue-a", "rescue-b"]
        self.other_instances = ["unrelated-model-instance"]
        self.requests = []
        self.unloaded = threading.Event()
        self.fail_unload = False

    def urlopen(self, request, timeout):
        url = request if isinstance(request, str) else request.full_url
        parsed = urlsplit(url)
        assert parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        assert parsed.port == 1234
        if isinstance(request, str):
            assert parsed.path == "/api/v1/models"
            self.requests.append(("GET", None))
            data = {"models": [
                {"key": "another-model", "loaded_instances": [
                    {"id": item} for item in self.other_instances]},
                {"key": MODEL, "loaded_instances": [
                    {"id": item} for item in self.instances]},
            ]}
        else:
            assert parsed.path == "/api/v1/models/unload"
            assert request.get_method() == "POST"
            assert request.get_header("Authorization") is None
            data = json.loads(request.data)
            self.requests.append(("POST", data))
            if self.fail_unload:
                raise TimeoutError("simulated local unload failure")
            identifier = data["instance_id"]
            assert identifier in self.instances
            self.instances.remove(identifier)
            self.unloaded.set()
        return io.BytesIO(json.dumps(data).encode())


@pytest.fixture
def recovery(monkeypatch):
    """Isolate routing, scheduler and activity state; join every worker before teardown."""
    monkeypatch.setattr(ai_routing, "_lock", threading.Lock())
    monkeypatch.setattr(ai_routing, "_local_lock", threading.Lock())
    monkeypatch.setattr(ai_routing, "_down_until", {})
    monkeypatch.setattr(ai_routing, "_failure_epochs", {})
    monkeypatch.setattr(ai_routing, "_release_states", {})
    monkeypatch.setattr(ai_routing, "_recovery_versions", {})
    monkeypatch.setattr(ai_routing, "_routing_configured", False)
    monkeypatch.setattr(ai_routing, "_configured_target", None)
    monkeypatch.setattr(inference_scheduler, "_condition", threading.Condition(threading.RLock()))
    monkeypatch.setattr(inference_scheduler, "_engines", {})
    monkeypatch.setattr(inference_scheduler, "_sequence", itertools.count())
    monkeypatch.setattr(llm_activity, "_condition", threading.Condition())
    monkeypatch.setattr(llm_activity, "_active", 0)
    monkeypatch.setattr(llm_activity, "_waiting", 0)
    monkeypatch.setattr(llm_activity, "_background", None)
    monkeypatch.setattr(llm_activity, "_last_activity", llm_activity.time.monotonic())
    workers = []
    # This fixture isolates unload/lease races after admission; the consent
    # boundary is exercised end-to-end by test_offline_consent.py.
    monkeypatch.setattr(ai_routing, 'require_offline_consent', lambda cfg: None)

    def worker(*args, **kwargs):
        result = REAL_THREAD(*args, **kwargs)
        workers.append(result)
        return result

    monkeypatch.setattr(ai_routing.threading, "Thread", worker)
    monkeypatch.setattr(ai_routing.socket, "create_connection", lambda *args, **kwargs: Connected())
    server = LocalServer()
    monkeypatch.setattr(ai_routing.urllib.request, "urlopen", server.urlopen)
    cfg = {"enabled": True, "provider": "openai_compatible",
           "base_url": "http://remote.invalid:1234", "model": "principal",
           "api_key": "remote-secret", "fallback_enabled": True,
           "fallback_base_url": "http://127.0.0.1:1234",
           "fallback_model": MODEL, "fallback_autostart": False}

    def join_workers():
        for item in tuple(workers):
            item.join(2)
            assert not item.is_alive(), "release worker did not finish within two seconds"

    yield SimpleNamespace(cfg=cfg, server=server, workers=workers, join=join_workers)
    join_workers()
    assert inference_scheduler.status()["active"] == 0
    assert inference_scheduler.status()["waiting"] == 0
    assert llm_activity.status()["active_calls"] == 0


def successful_reply(monkeypatch, content='{"answer":"principal available"}'):
    monkeypatch.setattr(ai_client, "_post_json", lambda *args, **kwargs:
                        {"choices": [{"message": {"content": content}}]})


def assert_rescue_released(recovery):
    recovery.join()
    assert not recovery.server.instances
    assert recovery.server.other_instances == ["unrelated-model-instance"]
    assert [data for method, data in recovery.server.requests if method == "POST"] == [
        {"instance_id": "rescue-a"}, {"instance_id": "rescue-b"}]


def test_useful_principal_json_releases_both_rescue_instances_only(recovery, monkeypatch):
    successful_reply(monkeypatch)
    assert ai_client.chat_json(recovery.cfg, {"messages": [], "model": "principal"},
                               retry_empty=False, raise_errors=True) == '{"answer":"principal available"}'
    assert_rescue_released(recovery)
    # A late external reload must also be released on the next useful primary reply.
    recovery.server.instances.append("late-rescue")
    assert ai_client.chat_text(recovery.cfg, [], retry_empty=False)
    recovery.join()
    assert not recovery.server.instances
    assert len(recovery.workers) == 2
    assert recovery.server.requests[-2] == ("POST", {"instance_id": "late-rescue"})


def test_tcp_reconnection_and_empty_model_reply_keep_rescue_loaded(recovery, monkeypatch):
    ai_routing.unavailable(recovery.cfg)
    monkeypatch.setattr(ai_routing, "time", SimpleNamespace(monotonic=lambda: 10**12))
    assert ai_routing.resolve(recovery.cfg) is recovery.cfg
    assert not recovery.workers
    successful_reply(monkeypatch, "  ")
    assert ai_client.chat_text(recovery.cfg, [], retry_empty=False) is None
    assert not recovery.workers
    assert recovery.server.instances == ["rescue-a", "rescue-b"]


def test_complete_principal_stream_releases_rescue(recovery, monkeypatch):
    monkeypatch.setattr(ChatStream, "_iterate", lambda self: iter(["Available", " now"]))
    assert list(ChatStream(recovery.cfg, [])) == ["Available", " now"]
    assert_rescue_released(recovery)


@pytest.mark.parametrize("ending", ["empty", "partial_failure", "cancelled"])
def test_incomplete_empty_or_cancelled_stream_keeps_rescue(recovery, monkeypatch, ending):
    def iterate(self):
        if ending == "empty":
            yield "  "
            return
        yield "partial"
        if ending == "partial_failure":
            raise ChatStreamError("incomplete") from ConnectionError()
        self.close()

    monkeypatch.setattr(ChatStream, "_iterate", iterate)
    if ending == "partial_failure":
        with pytest.raises(ChatStreamError):
            list(ChatStream(recovery.cfg, []))
    else:
        list(ChatStream(recovery.cfg, []))
    assert not recovery.workers
    assert recovery.server.instances == ["rescue-a", "rescue-b"]


def test_manual_generation_probe_releases_rescue_only_after_useful_reply(recovery, monkeypatch):
    successful_reply(monkeypatch, "")
    assert ai_client.check_connection(recovery.cfg)["ok"] is False
    assert not recovery.workers
    successful_reply(monkeypatch, "OK")
    assert ai_client.check_connection(recovery.cfg)["ok"] is True
    assert_rescue_released(recovery)


@pytest.mark.parametrize("base", ["http://127.0.0.1:1234", "http://localhost:1234", "http://[::1]:1234"])
def test_local_principal_never_releases_its_model(recovery, monkeypatch, base):
    recovery.cfg["base_url"] = base
    successful_reply(monkeypatch)
    assert ai_client.chat_text(recovery.cfg, [], retry_empty=False)
    assert not recovery.workers
    assert recovery.server.instances == ["rescue-a", "rescue-b"]


def test_failed_unload_retries_on_next_useful_reply_after_thirty_seconds(recovery, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(ai_routing, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    successful_reply(monkeypatch)
    recovery.server.fail_unload = True
    assert ai_client.chat_text(recovery.cfg, [], retry_empty=False)
    recovery.join()
    assert ai_routing.status(recovery.cfg)["local_model_release"]["state"] == "error"
    recovery.server.fail_unload = False
    clock[0] += 29.9
    assert ai_client.chat_text(recovery.cfg, [], retry_empty=False)
    assert len(recovery.workers) == 1
    clock[0] += .1
    assert ai_client.chat_text(recovery.cfg, [], retry_empty=False)
    recovery.join()
    assert not recovery.server.instances
    assert len(recovery.workers) == 2
    assert ai_routing.status(recovery.cfg)["local_model_release"]["state"] == "unloaded"


def release_waiting(monkeypatch):
    waiting = threading.Event()
    original = inference_scheduler.lease

    @contextmanager
    def observe(*args, **kwargs):
        if threading.current_thread().name == "lmstudio-release":
            waiting.set()
        with original(*args, **kwargs):
            yield

    monkeypatch.setattr(inference_scheduler, "lease", observe)
    return waiting, original


def test_new_outage_cancels_queued_release_and_obsolete_success(recovery, monkeypatch):
    waiting, original_lease = release_waiting(monkeypatch)
    key = inference_scheduler.engine_key(recovery.cfg["fallback_base_url"])
    old_epoch = ai_routing.primary_epoch(recovery.cfg)
    with original_lease(key):
        ai_routing.primary_succeeded(recovery.cfg, old_epoch)
        assert waiting.wait(2)
        ai_routing.unavailable(recovery.cfg)
        ai_routing.primary_succeeded(recovery.cfg, old_epoch)
        assert len(recovery.workers) == 1
    recovery.join()
    assert not recovery.server.requests
    assert recovery.server.instances == ["rescue-a", "rescue-b"]
    # A response begun before a second outage is also obsolete before it returns.
    epoch = ai_routing.primary_epoch(recovery.cfg)
    ai_routing.unavailable(recovery.cfg)
    ai_routing.primary_succeeded(recovery.cfg, epoch)
    assert len(recovery.workers) == 1


def test_late_principal_reply_does_not_release_after_a_new_outage(recovery, monkeypatch):
    def late_reply(*args, **kwargs):
        # A concurrent caller discovers a new outage while this response is in flight.
        ai_routing.unavailable(recovery.cfg)
        return {"choices": [{"message": {"content": "older useful answer"}}]}

    monkeypatch.setattr(ai_client, "_post_json", late_reply)
    assert ai_client.chat_text(recovery.cfg, [], retry_empty=False) == "older useful answer"
    assert not recovery.workers
    assert recovery.server.instances == ["rescue-a", "rescue-b"]


def test_switching_to_local_principal_cancels_a_queued_remote_release(recovery, monkeypatch):
    waiting, original_lease = release_waiting(monkeypatch)
    with ai_routing.settings_update(recovery.cfg):
        pass  # Represents the already committed remote configuration.
    key = inference_scheduler.engine_key(recovery.cfg["fallback_base_url"])
    with original_lease(key):
        ai_routing.primary_succeeded(recovery.cfg, ai_routing.primary_epoch(recovery.cfg))
        assert waiting.wait(2)
        local_cfg = {**recovery.cfg, "base_url": "http://127.0.0.1:1234", "model": MODEL}
        with ai_routing.settings_update(local_cfg):
            pass  # The new local principal is committed before the release can run.
    recovery.join()
    assert not recovery.server.requests
    assert recovery.server.instances == ["rescue-a", "rescue-b"]


def test_saved_new_remote_configuration_refuses_success_from_old_configuration(recovery, monkeypatch):
    new_cfg = {**recovery.cfg, "base_url": "http://another-remote.invalid:1234"}
    with ai_routing.settings_update(new_cfg):
        pass
    successful_reply(monkeypatch)
    assert ai_client.chat_text(recovery.cfg, [], retry_empty=False)
    assert not recovery.workers
    assert recovery.server.instances == ["rescue-a", "rescue-b"]
    assert ai_client.chat_text(new_cfg, [], retry_empty=False)
    assert_rescue_released(recovery)


def test_first_inflight_reply_is_obsolete_after_model_change_on_same_remote_url(recovery):
    original_epoch = ai_routing.primary_epoch(recovery.cfg)
    updated = {**recovery.cfg, "model": "another-principal-model"}
    with ai_routing.settings_update(updated):
        pass
    ai_routing.primary_succeeded(recovery.cfg, original_epoch)
    assert not recovery.workers
    assert recovery.server.instances == ["rescue-a", "rescue-b"]
    ai_routing.primary_succeeded(updated, ai_routing.primary_epoch(updated))
    assert_rescue_released(recovery)


def test_release_survives_local_generation_longer_than_thirty_seconds(recovery, monkeypatch):
    clock = [1000.0]
    fake_time = SimpleNamespace(monotonic=lambda: clock[0])
    monkeypatch.setattr(ai_routing, "time", fake_time)
    monkeypatch.setattr(inference_scheduler, "time", fake_time)
    initially_queued, still_queued = threading.Event(), threading.Event()

    class QueueCondition(threading.Condition):
        release_waits = 0

        def wait(self, timeout=None):
            if threading.current_thread().name == "lmstudio-release":
                self.release_waits += 1
                (initially_queued if self.release_waits == 1 else still_queued).set()
            return super().wait(timeout)

    condition = QueueCondition(threading.RLock())
    monkeypatch.setattr(inference_scheduler, "_condition", condition)
    fallback = ai_routing.local_config(recovery.cfg)
    with ai_routing.local_generation(fallback):
        ai_routing.primary_succeeded(recovery.cfg, ai_routing.primary_epoch(recovery.cfg))
        assert initially_queued.wait(2)
        # Advance elapsed time, then wake the real waiter so it rechecks its deadline.
        clock[0] += 40
        with condition:
            condition.notify_all()
        assert still_queued.wait(2)
        assert inference_scheduler.status()["waiting"] == 1
        assert not recovery.server.unloaded.is_set()
    # No additional remote success is needed when the long generation ends.
    assert_rescue_released(recovery)


def test_release_waits_for_local_generation_and_next_outage_can_reload(recovery, monkeypatch, tmp_path):
    waiting, _ = release_waiting(monkeypatch)
    assert {inference_scheduler.engine_key(base) for base in (
        "http://127.0.0.1:1234/v1/chat/completions",
        "http://localhost:1234", "http://[::1]:1234")} == {"generation:http://127.0.0.1:1234"}
    recovery.cfg["fallback_base_url"] = "http://localhost:1234"
    recovery.cfg["fallback_autostart"] = True
    fallback = ai_routing.local_config(recovery.cfg)
    # Active generation uses another loopback alias, but must hold the same engine.
    fallback["base_url"] = "http://127.0.0.1:1234"
    with ai_routing.local_generation(fallback):
        ai_routing.primary_succeeded(recovery.cfg, ai_routing.primary_epoch(recovery.cfg))
        assert waiting.wait(2)
        assert not recovery.server.unloaded.wait(.03)
    assert_rescue_released(recovery)

    fake_cli = tmp_path / ".lmstudio" / "bin" / "lms.exe"
    fake_cli.parent.mkdir(parents=True)
    fake_cli.write_bytes(b"test placeholder; never executed")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    cli_calls = []

    def subprocess_run(args, **kwargs):
        assert args[0] == str(fake_cli)
        cli_calls.append(args[1:])
        if args[1] == "load":
            recovery.server.instances[:] = [MODEL]
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ai_routing.subprocess, "run", subprocess_run)
    ai_routing.unavailable(recovery.cfg)
    with ai_routing.local_generation(fallback):
        assert recovery.server.instances == [MODEL]
    assert cli_calls[0][:2] == ["server", "start"]
    assert cli_calls[1] == ["load", MODEL, "--identifier", MODEL,
                            "--context-length", "8192", "--yes"]


@pytest.mark.parametrize("fails", [False, True])
def test_late_fallback_finishes_after_recovery_and_releases_without_new_probe(recovery, monkeypatch, fails):
    # The call selected fallback before recovery, but only acquires its engine
    # after the first release worker has already finished.
    fallback = ai_routing.local_config(recovery.cfg)
    ai_routing.primary_succeeded(recovery.cfg, ai_routing.primary_epoch(recovery.cfg))
    recovery.join()
    assert not recovery.server.instances

    def load(_cfg):
        recovery.server.instances[:] = ["late-rescue"]

    monkeypatch.setattr(ai_routing, "ensure_local", load)
    if fails:
        with pytest.raises(RuntimeError, match="local request failed"):
            with ai_routing.local_generation(fallback):
                raise RuntimeError("local request failed")
    else:
        with ai_routing.local_generation(fallback):
            assert recovery.server.instances == ["late-rescue"]
    recovery.join()
    assert not recovery.server.instances
    assert len(recovery.workers) == 2


def test_late_stream_fallback_releases_after_recovery_without_new_remote_reply(recovery, monkeypatch):
    fallback = ai_routing.local_config(recovery.cfg)
    ai_routing.primary_succeeded(recovery.cfg, ai_routing.primary_epoch(recovery.cfg))
    recovery.join()
    monkeypatch.setattr(ai_routing, "ensure_local", lambda cfg: recovery.server.instances.append("late-stream"))
    monkeypatch.setattr(ChatStream, "_iterate", lambda self: iter(["local answer"]))
    assert list(ChatStream(fallback, [])) == ["local answer"]
    recovery.join()
    assert not recovery.server.instances


@pytest.mark.parametrize("change", ["outage", "local_principal", "different_model", "different_server"])
def test_late_local_call_does_not_release_without_current_matching_recovery(recovery, monkeypatch, change):
    fallback = ai_routing.local_config(recovery.cfg)
    ai_routing.primary_succeeded(recovery.cfg, ai_routing.primary_epoch(recovery.cfg))
    recovery.join()
    if change == "outage":
        ai_routing.unavailable(recovery.cfg)
    elif change == "local_principal":
        with ai_routing.settings_update({**recovery.cfg, "base_url": "http://127.0.0.1:1234", "model": MODEL}):
            pass
    elif change == "different_model":
        fallback["model"] = "other-fallback"
    else:
        fallback["base_url"] = "http://127.0.0.1:5678"
    monkeypatch.setattr(ai_routing, "ensure_local", lambda cfg: recovery.server.instances.append("keep-local"))
    with ai_routing.local_generation(fallback):
        pass
    recovery.join()
    assert recovery.server.instances == ["keep-local"]
    assert len(recovery.workers) == 1


def test_old_recovery_does_not_release_a_new_explicit_local_diagnostic(recovery, monkeypatch):
    ai_routing.primary_succeeded(recovery.cfg, ai_routing.primary_epoch(recovery.cfg))
    recovery.join()
    # No new exact-model recovery was observed after this explicit local choice.
    # It may be an offline diagnostic; old readiness must not imply a new return.
    fallback = ai_routing.local_config(recovery.cfg)
    monkeypatch.setattr(ai_routing, "ensure_local", lambda cfg: recovery.server.instances.append("diagnostic"))
    with ai_routing.local_generation(fallback):
        pass
    recovery.join()
    assert recovery.server.instances == ["diagnostic"]
    assert len(recovery.workers) == 1
