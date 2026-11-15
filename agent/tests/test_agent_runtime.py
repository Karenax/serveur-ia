"""Exercise real child exits and supervisor ownership without application data."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from scripts import agent_runtime as runtime


def wait_until(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError("Supervisor did not reach the expected state")


def spawn_supervisor(tmp_path, port, child_code):
    code = (
        "from pathlib import Path; from scripts import agent_runtime as r; "
        "r.restart_delay=lambda failures: 0.05; "
        f"r.supervise({[sys.executable, '-c', child_code]!r}, "
        f"directory=Path({str(tmp_path)!r}), cwd=Path({str(tmp_path)!r}), "
        f"port={port}, poll_seconds=0.02)"
    )
    return subprocess.Popen([sys.executable, "-c", code], cwd=runtime.ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def stop_supervisor(process, tmp_path):
    state = runtime.read_state(tmp_path)
    (tmp_path / "stop.json").write_text(json.dumps({"token": state.get("token")}), encoding="utf-8")
    try:
        code = process.wait(timeout=5)
        diagnostic = process.stderr.read().decode('utf-8', errors='replace') if code else ''
        assert code == 0, diagnostic
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stderr.close()


@pytest.mark.skipif(os.name != 'nt', reason='Windows reader sharing semantics')
def test_state_replacement_survives_a_reader_holding_the_previous_snapshot(tmp_path, monkeypatch):
    runtime.write_state(tmp_path, {'revision': 1})
    original = Path.replace
    blocked = threading.Event()
    failures = []

    def replace(path, target):
        try:
            return original(path, target)
        except PermissionError:
            blocked.set()
            raise

    monkeypatch.setattr(Path, 'replace', replace)
    def write():
        try:
            runtime.write_state(tmp_path, {'revision': 2})
        except Exception as error:
            failures.append(error)

    with (tmp_path / 'state.json').open('rb') as reader:
        writer = threading.Thread(target=write)
        writer.start()
        try:
            assert blocked.wait(2)
            assert json.load(reader) == {'revision': 1}
        finally:
            reader.close()
            writer.join(6)
    assert not writer.is_alive()
    assert failures == []
    assert runtime.read_state(tmp_path) == {'revision': 2}


@pytest.mark.skipif(os.name != 'nt', reason='Windows replacement errors')
@pytest.mark.parametrize('winerror', [5, 87])
def test_state_replacement_still_reports_persistent_or_unrelated_denial(tmp_path, monkeypatch, winerror):
    runtime.write_state(tmp_path, {'revision': 1})
    ticks = iter(range(10))
    pauses = []
    monkeypatch.setattr(runtime, 'time', SimpleNamespace(monotonic=lambda: next(ticks), sleep=pauses.append))
    error = PermissionError('Denied fictitious snapshot replacement')
    error.winerror = winerror
    def deny(_path, _target):
        raise error
    monkeypatch.setattr(Path, 'replace', deny)
    with pytest.raises(PermissionError):
        runtime.write_state(tmp_path, {'revision': 2})
    assert runtime.read_state(tmp_path) == {'revision': 1}
    assert bool(pauses) == (winerror == 5)


def test_lock_releases_and_backoff_is_bounded(tmp_path):
    with runtime.instance_lock(tmp_path) as first:
        assert first
        with runtime.instance_lock(tmp_path) as second:
            assert not second
    with runtime.instance_lock(tmp_path) as third:
        assert third
    assert [runtime.restart_delay(n) for n in (1, 2, 3, 4, 5, 100)] == [5, 10, 20, 40, 60, 60]


def test_environment_preserves_explicit_document_worker_setting(monkeypatch):
    monkeypatch.setenv("AGENT_DOCUMENT_JOBS_ENABLED", "0")
    assert runtime.child_environment()["AGENT_DOCUMENT_JOBS_ENABLED"] == "0"
    monkeypatch.delenv("AGENT_DOCUMENT_JOBS_ENABLED")
    assert runtime.child_environment()["AGENT_DOCUMENT_JOBS_ENABLED"] == "1"


def test_actual_crash_is_restarted_and_stop_does_not_restart(tmp_path):
    child = (
        "from pathlib import Path; import sys,time; p=Path('launches'); "
        "n=int(p.read_text())+1 if p.exists() else 1; p.write_text(str(n)); "
        "print('attempt',n,flush=True); sys.exit(7) if n < 3 else time.sleep(30)"
    )
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = spawn_supervisor(tmp_path, port, child)
    try:
        wait_until(lambda: runtime.read_state(tmp_path).get("restarts", 0) >= 2
                   and (tmp_path / "launches").exists()
                   and (tmp_path / "launches").read_text() == "3")
        state = runtime.read_state(tmp_path)
        assert state["last_exit_code"] == 7
        assert state["backend_pid"] != os.getpid()
        duplicate = spawn_supervisor(tmp_path, port, child)
        assert duplicate.wait(timeout=5) == 0
        duplicate.stderr.close()
    finally:
        stop_supervisor(process, tmp_path)
    assert runtime.read_state(tmp_path)["status"] == "stopped"
    assert (tmp_path / "launches").read_text() == "3"
    assert "code=7" in (tmp_path / "supervisor.log").read_text(encoding="utf-8")


def test_existing_listener_is_never_stopped_or_adopted(tmp_path):
    child = "from pathlib import Path; import time; Path('launched').touch(); time.sleep(30)"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(16)
        process = spawn_supervisor(tmp_path, listener.getsockname()[1], child)
        try:
            wait_until(lambda: runtime.read_state(tmp_path).get("status") == "waiting_existing_listener")
            assert runtime.read_state(tmp_path)["backend_pid"] is None
            assert not (tmp_path / "launched").exists()
        finally:
            stop_supervisor(process, tmp_path)
        assert listener.fileno() >= 0
