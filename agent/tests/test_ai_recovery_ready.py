"""Fresh principal inventory releases the rescue without generating any text."""
from contextlib import contextmanager
import threading
from types import SimpleNamespace
import urllib.error

import pytest

from app.services import ai_client, ai_routing, connection_health as health
from app.services import inference_scheduler
from tests.test_ai_recovery_unload import (
    MODEL, assert_rescue_released, recovery as recovery, release_waiting,
)


@pytest.fixture(autouse=True)
def isolated_health(monkeypatch):
    monkeypatch.setattr(health, "_cache", {})
    monkeypatch.setattr(health, "_last_llm_test", {})
    monkeypatch.setattr(ai_routing, "_configured_principal", None, raising=False)
    monkeypatch.setattr(ai_client, "_post_json", lambda *args, **kwargs:
                        pytest.fail("Readiness must not generate a model reply"))


def inventory(monkeypatch, cfg, ids=None, before_return=None):
    calls = []

    def get(url, key="", payload=None):
        assert url == cfg["base_url"].removesuffix("/v1") + "/v1/models"
        assert key == cfg["api_key"]
        assert payload is None
        calls.append(url)
        if before_return:
            before_return()
        return {"data": [{"id": value} for value in (ids if ids is not None else [cfg["model"]])]}

    monkeypatch.setattr(health, "http_json", get)
    return calls


def test_fresh_exact_ready_without_generation_releases_only_rescue(recovery, monkeypatch):
    ai_routing.unavailable(recovery.cfg)
    calls = inventory(monkeypatch, recovery.cfg)
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    assert calls == [recovery.cfg["base_url"] + "/v1/models"]
    assert_rescue_released(recovery)
    assert recovery.cfg["base_url"] not in ai_routing._down_until


@pytest.mark.parametrize("ids", [[], ["principal-extra"], ["PRINCIPAL"], ["other", "principal:latest"]])
def test_missing_exact_model_keeps_rescue(recovery, monkeypatch, ids):
    inventory(monkeypatch, recovery.cfg, ids)
    assert health.llm_check(recovery.cfg)["state"] == "warning"
    assert recovery.server.instances == ["rescue-a", "rescue-b"]
    assert not recovery.workers and not recovery.server.requests


@pytest.mark.parametrize("changed", [
    {"model": "new-principal"}, {"base_url": "http://new-remote.invalid:1234"},
    {"fallback_model": "new-rescue"}, {"fallback_enabled": False},
])
def test_configuration_changed_during_probe_keeps_rescue(recovery, monkeypatch, changed):
    def change():
        with ai_routing.settings_update({**recovery.cfg, **changed}):
            pass

    inventory(monkeypatch, recovery.cfg, before_return=change)
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    assert not recovery.workers and not recovery.server.requests
    assert recovery.server.instances == ["rescue-a", "rescue-b"]


def test_old_probe_starting_after_saved_model_change_keeps_rescue(recovery, monkeypatch):
    with ai_routing.settings_update({**recovery.cfg, "model": "new-principal"}):
        pass
    inventory(monkeypatch, recovery.cfg)
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    assert not recovery.workers and not recovery.server.requests


def test_failed_settings_update_keeps_committed_principal_identity(recovery, monkeypatch):
    with ai_routing.settings_update(recovery.cfg):
        pass

    def failed_save():
        with pytest.raises(ValueError, match="simulated commit failure"):
            with ai_routing.settings_update({**recovery.cfg, "model": "not-committed"}):
                raise ValueError("simulated commit failure")

    inventory(monkeypatch, recovery.cfg, before_return=failed_save)
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    assert not recovery.workers and not recovery.server.requests
    inventory(monkeypatch, recovery.cfg)
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    assert_rescue_released(recovery)


@pytest.mark.parametrize("known_epoch_before_save", [False, True])
def test_save_commit_invalidates_probe_started_inside_model_change(recovery, monkeypatch, known_epoch_before_save):
    with ai_routing.settings_update(recovery.cfg):
        pass
    assert not ai_routing._failure_epochs
    if known_epoch_before_save:
        ai_routing.primary_epoch(recovery.cfg)
    updated = {**recovery.cfg, "model": "new-principal"}
    assert ai_routing._release_target(recovery.cfg) == ai_routing._release_target(updated)
    inventory(monkeypatch, recovery.cfg)
    waiting, _ = release_waiting(monkeypatch)
    with ai_routing.settings_update(updated):
        # The caller reads the still-committed old config during the save. It
        # creates the first epoch key here when the dictionary was initially empty.
        assert health.llm_check(recovery.cfg)["state"] == "ok"
        assert waiting.wait(1)
        assert not recovery.server.requests
    recovery.join()
    assert not recovery.server.requests, "Commit must invalidate the old model's queued release"
    assert recovery.server.instances == ["rescue-a", "rescue-b"]
    # Only a new observation of the newly committed model can release the rescue.
    inventory(monkeypatch, updated)
    assert health.llm_check(updated)["state"] == "ok"
    assert_rescue_released(recovery)


@pytest.mark.parametrize("changed", [{"enabled": False}, {"provider": "none"}])
def test_disabled_ai_does_not_read_inventory_or_release(recovery, monkeypatch, changed):
    monkeypatch.setattr(health, "http_json", lambda *args, **kwargs:
                        pytest.fail("Disabled AI must not request model inventory"))
    assert health.llm_check({**recovery.cfg, **changed})["state"] == "disabled"
    assert not recovery.workers and not recovery.server.requests


def test_new_outage_during_probe_invalidates_ready_response(recovery, monkeypatch):
    inventory(monkeypatch, recovery.cfg,
              before_return=lambda: ai_routing.unavailable(recovery.cfg))
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    assert not recovery.workers and not recovery.server.requests


def test_slow_inventory_is_not_fresh_release_evidence(recovery, monkeypatch):
    clock = iter([100.0, 106.001])
    monkeypatch.setattr(health, "time", SimpleNamespace(monotonic=lambda: next(clock)))
    inventory(monkeypatch, recovery.cfg)
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    assert not recovery.workers and not recovery.server.requests


@pytest.mark.parametrize("base", ["http://127.0.0.1:1234", "http://localhost:1234", "http://[::1]:1234"])
def test_local_principal_inventory_does_not_unload_itself(recovery, monkeypatch, base):
    cfg = {**recovery.cfg, "base_url": base}
    inventory(monkeypatch, cfg)
    assert health.llm_check(cfg)["state"] == "ok"
    assert not recovery.workers and not recovery.server.requests


def test_disabled_fallback_keeps_local_model(recovery, monkeypatch):
    cfg = {**recovery.cfg, "fallback_enabled": False}
    inventory(monkeypatch, cfg)
    assert health.llm_check(cfg)["state"] == "ok"
    assert not recovery.workers and not recovery.server.requests


def test_transport_failure_does_not_release(recovery, monkeypatch):
    def fail(*args, **kwargs):
        raise urllib.error.URLError("private fake endpoint")

    monkeypatch.setattr(health, "http_json", fail)
    result = health.guarded(health.llm_check, recovery.cfg)
    assert result["state"] == "error"
    assert "private" not in result["detail"]
    assert not recovery.workers and not recovery.server.requests


def test_ready_defers_until_local_generation_lease_finishes(recovery, monkeypatch):
    inventory(monkeypatch, recovery.cfg)
    waiting, _ = release_waiting(monkeypatch)
    fallback = ai_routing.local_config(recovery.cfg)
    with ai_routing.local_generation(fallback):
        assert health.llm_check(recovery.cfg)["state"] == "ok"
        assert waiting.wait(1), "The release was not queued after inventory readiness"
        assert not recovery.server.unloaded.is_set()
        assert not recovery.server.requests
    assert_rescue_released(recovery)


def test_settings_change_cancels_ready_release_waiting_for_local_lease(recovery, monkeypatch):
    inventory(monkeypatch, recovery.cfg)
    waiting, _ = release_waiting(monkeypatch)
    fallback = ai_routing.local_config(recovery.cfg)
    with ai_routing.local_generation(fallback):
        assert health.llm_check(recovery.cfg)["state"] == "ok"
        assert waiting.wait(1)
        with ai_routing.settings_update({**recovery.cfg, "base_url": fallback["base_url"]}):
            pass
    recovery.join()
    assert not recovery.server.requests
    assert recovery.server.instances == ["rescue-a", "rescue-b"]


def test_cached_health_and_manual_result_are_not_new_readiness(recovery, monkeypatch):
    cfg = recovery.cfg
    key = health._settings_key([cfg, {}])
    health._cache.update(key=key, running=False, expires=health.time.monotonic()+90,
                         values={"llm": health.result("ok", "Old model advertisement")})
    health.record_llm_test(cfg, {"ok": True, "reply": "historical"})
    monkeypatch.setattr(health, "http_json", lambda *args, **kwargs:
                        pytest.fail("No fresh GET should run while health is cached"))
    assert health.connection_status(cfg, {})["services"]["llm"]["state"] == "ok"
    assert not recovery.workers and not recovery.server.requests


def test_failed_release_retries_from_fresh_readiness_after_thirty_seconds(recovery, monkeypatch):
    inventory(monkeypatch, recovery.cfg)
    clock = [1000.0]
    monkeypatch.setattr(ai_routing, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    recovery.server.fail_unload = True
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    recovery.join()
    assert ai_routing.status(recovery.cfg)["local_model_release"]["state"] == "error"
    recovery.server.fail_unload = False
    clock[0] += 29.9
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    assert len(recovery.workers) == 1
    clock[0] += .1
    assert health.llm_check(recovery.cfg)["state"] == "ok"
    recovery.join()
    assert not recovery.server.instances
    assert recovery.server.other_instances == ["unrelated-model-instance"]
    assert [body for method, body in recovery.server.requests if method == "POST"] == [
        {"instance_id": "rescue-a"},  # Failed first request is still a real simulated attempt.
        {"instance_id": "rescue-a"}, {"instance_id": "rescue-b"},
    ]
    assert len(recovery.workers) == 2


def test_repeated_fresh_ready_does_not_duplicate_waiting_release(recovery, monkeypatch):
    inventory(monkeypatch, recovery.cfg)
    waiting = threading.Event()
    original = inference_scheduler.lease

    @contextmanager
    def observe(*args, **kwargs):
        if threading.current_thread().name == "lmstudio-release":
            waiting.set()
        with original(*args, **kwargs):
            yield

    monkeypatch.setattr(inference_scheduler, "lease", observe)
    with original(inference_scheduler.engine_key(recovery.cfg["fallback_base_url"])):
        assert health.llm_check(recovery.cfg)["state"] == "ok"
        assert waiting.wait(1)
        assert health.llm_check(recovery.cfg)["state"] == "ok"
        assert len(recovery.workers) == 1
    assert_rescue_released(recovery)
    assert MODEL == recovery.cfg["fallback_model"]


def test_old_probe_starting_after_api_key_save_keeps_rescue(recovery, monkeypatch):
    old = {**recovery.cfg, "api_key": "old-test-key"}
    current = {**old, "api_key": "new-test-key"}
    with ai_routing.settings_update(old):
        pass
    with ai_routing.settings_update(current):
        pass
    inventory(monkeypatch, old)
    # A worker can retain the old settings snapshot, then start its GET only
    # after the replacement credential is committed. Its fresh epoch is not
    # evidence that the CURRENT credential reaches the configured principal.
    assert health.llm_check(old)["state"] == "ok"
    recovery.join()
    assert not recovery.server.requests
    assert recovery.server.instances == ["rescue-a", "rescue-b"]

    def rejected_current(url, key="", payload=None):
        assert key == "new-test-key"
        assert payload is None
        raise urllib.error.HTTPError(url, 401, "simulated replacement rejection", None, None)

    monkeypatch.setattr(health, "http_json", rejected_current)
    assert health.guarded(health.llm_check, current)["state"] == "error"
    assert not recovery.server.requests
    assert recovery.server.instances == ["rescue-a", "rescue-b"]


def test_fresh_probe_with_saved_api_key_releases_after_local_generation(recovery, monkeypatch):
    old = {**recovery.cfg, "api_key": "old-test-key"}
    current = {**old, "api_key": "new-test-key"}
    with ai_routing.settings_update(old):
        pass
    with ai_routing.settings_update(current):
        pass
    calls = inventory(monkeypatch, current)
    waiting, _ = release_waiting(monkeypatch)
    with ai_routing.local_generation(ai_routing.local_config(current)):
        assert health.llm_check(current)["state"] == "ok"
        assert calls == [current["base_url"] + "/v1/models"]
        assert waiting.wait(1)
        assert not recovery.server.requests
        assert recovery.server.instances == ["rescue-a", "rescue-b"]
    assert_rescue_released(recovery)
