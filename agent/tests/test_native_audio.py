"""Native ownership, durable replay and drain order without opening hardware."""
import hashlib
import io
import json
import queue
import subprocess
import sys
from types import SimpleNamespace
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import Event

import pytest

from app.services import native_audio
from scripts import native_audio_capture


def capture(tmp_path):
    return native_audio.NativeCapture(str(uuid.uuid4()), tmp_path, ["system"], {}, {"system": 0}, 0)


def allow_pure_fixture_authority(item, tmp_path, monkeypatch):
    """Only these four pure instances; this never proves real SQL authority."""
    sid = item.sid
    assert str(uuid.UUID(sid)) == sid
    root = tmp_path.resolve()
    expected = root / "meeting-sessions" / "native" / sid
    calls = []

    def authorize():
        assert item.sid == sid
        assert item.storage == root
        assert item.directory.resolve(strict=True) == expected
        calls.append((sid, str(expected)))

    monkeypatch.setattr(item, "_authorize_persistence", authorize)
    return calls


def test_owner_cannot_be_recreated_from_http_data(tmp_path, monkeypatch):
    item = capture(tmp_path)
    monkeypatch.setattr(native_audio, "_captures", {item.sid: item})
    assert native_audio.owns_session(item.sid)
    assert native_audio.has_registered_capture(item.sid)
    assert native_audio.accepts_owner(item.sid, item)
    assert not native_audio.accepts_owner(item.sid, {"session_id": item.sid})
    assert not native_audio.accepts_owner(item.sid, None)
    assert not native_audio.accepts_owner(str(uuid.uuid4()), item)
    assert not native_audio.has_registered_capture(str(uuid.uuid4()))
    item.state = "stopped"
    assert not native_audio.owns_session(item.sid)
    assert native_audio.has_registered_capture(item.sid)


def test_journal_replay_updates_sequence_before_new_hardware_start(tmp_path, monkeypatch):
    item = capture(tmp_path)
    authority_calls = allow_pure_fixture_authority(item, tmp_path, monkeypatch)
    raw = b"immutable-native-chunk"
    path = item.directory / "system-00000003.wav"
    path.write_bytes(raw)
    packet = {"kind": "chunk", "session_id": item.sid, "track": "system", "sequence": 3,
              "path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
              "command_id": str(uuid.uuid4()), "start_ms": 18000, "duration_ms": 3000}
    path.with_suffix(".json").write_text(json.dumps(packet))
    acknowledgements = []

    def persist(value):
        acknowledgements.append(value["command_id"])
        path.with_suffix(".receipt.json").write_text("{}")

    monkeypatch.setattr(item, "_persist", persist)
    item.replay()
    assert acknowledgements == [packet["command_id"]]
    assert item.request["sequences"] == {"system": 4}
    assert item.request["offset_ms"] == 21000
    assert item.request["total_bytes"] == len(raw)
    item.replay()
    assert acknowledgements == [packet["command_id"], packet["command_id"]]
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Empreinte"):
        item.replay()
    assert authority_calls


def test_journal_cannot_replay_another_sessions_fragment(tmp_path, monkeypatch):
    item = capture(tmp_path)
    authority_calls = allow_pure_fixture_authority(item, tmp_path, monkeypatch)
    packet = {"kind": "chunk", "session_id": str(uuid.uuid4()), "track": "system", "sequence": 0}
    (item.directory / "system-00000000.json").write_text(json.dumps(packet))
    with pytest.raises(ValueError, match="cette séance"):
        item.replay()
    assert authority_calls


def test_helper_rejects_windows_service_session_before_devices_open(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "av", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", SimpleNamespace())
    monkeypatch.setattr(native_audio_capture, "session_id", lambda pid: 0)
    with pytest.raises(ValueError, match="interactive"):
        native_audio_capture.capture({}, parent_pid=1)


def test_pause_and_stop_return_after_durable_fragment_ack(tmp_path, monkeypatch):
    item = capture(tmp_path)
    authority_calls = allow_pure_fixture_authority(item, tmp_path, monkeypatch)
    trace = []
    events = queue.Queue()
    events.put({"kind": "ready"})

    class Output:
        def __iter__(self):
            while True:
                event = events.get(timeout=3)
                if event is None:
                    return
                yield json.dumps(event) + "\n"

        def close(self):
            pass

    class Input(io.StringIO):
        def flush(self):
            command = json.loads(self.getvalue().splitlines()[-1])["op"]
            if command in {"pause", "stop"}:
                events.put({"kind": "chunk", "label": command})
            events.put({"kind": "state", "state": {"start": "recording", "pause": "paused", "stop": "stopped"}[command]})
            if command == "stop":
                events.put(None)  # The real helper closes stdout after stop.

    class Process:
        stdin, stdout = Input(), Output()
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            self.returncode = -15
            events.put(None)

        def wait(self, timeout):
            if self.returncode is None:
                self.returncode = 0
            return self.returncode

    monkeypatch.setattr(native_audio.subprocess, "Popen", lambda *args, **kwargs: Process())
    monkeypatch.setattr(native_audio, "_windows_job", lambda process: (SimpleNamespace(CloseHandle=lambda handle: None), 1))
    monkeypatch.setattr(item, "_persist", lambda event: trace.append(event["label"] + ":committed"))
    monkeypatch.setattr(item, "_record_interruption", lambda: None)
    try:
        item.start()
        assert item.command("pause", target_state="paused")["durable_chunks_acknowledged"]
        trace.append("pause:returned")
        item.command("stop", target_state="stopped")
        trace.append("stop:returned")
        assert trace == ["pause:committed", "pause:returned", "stop:committed", "stop:returned"]
    finally:
        item.close()
    assert authority_calls


def test_timeout_is_public_error_without_leaking_queue_exception(tmp_path):
    item = capture(tmp_path)
    item.process = SimpleNamespace(poll=lambda: None, stdin=io.StringIO())
    with pytest.raises(ValueError, match="ne répond pas"):
        item.command("pause", target_state="paused", timeout=.01)


def simulated_reader(item, output, monkeypatch):
    class Process:
        stdin = io.StringIO()
        stdout = output
        returncode = None
        terminated = 0

        def poll(self):
            return self.returncode

        def terminate(self):
            self.terminated += 1
            self.returncode = -15

        def wait(self, timeout):
            if self.returncode is None:
                self.returncode = 0
            return self.returncode

    process = Process()
    item.process = process
    interruptions = []
    monkeypatch.setattr(item, "_record_interruption", lambda: interruptions.append(item.error))
    return process, interruptions


@pytest.mark.parametrize("count", [1440, 10000])
def test_long_capture_persists_every_chunk_without_notification_accumulation(tmp_path, monkeypatch, count):
    item = capture(tmp_path)
    received = 0

    def persist(event):
        nonlocal received
        assert item.events.qsize() == 0
        assert event["sequence"] == received
        received += 1

    class Output:
        def __iter__(self):
            for sequence in range(count):
                yield json.dumps({"kind": "chunk", "sequence": sequence}) + "\n"
            yield json.dumps({"kind": "state", "state": "stopped"}) + "\n"

    monkeypatch.setattr(item, "_persist", persist)
    process, interruptions = simulated_reader(item, Output(), monkeypatch)
    item._receive()
    assert received == count
    assert item.events.maxsize == 8 and item.events.qsize() == 1
    assert item.events.get_nowait() == {"kind": "state", "state": "stopped"}
    assert item._reader_done.is_set() and item.error is None
    assert process.terminated == 0 and interruptions == []


def test_control_overflow_wakes_waiter_and_preserves_committed_journal(tmp_path, monkeypatch):
    item = capture(tmp_path)
    journal = item.directory / "retained.json"
    original = b"Immutable fragment already committed before notification overflow"
    monkeypatch.setattr(item, "_persist", lambda event: journal.write_bytes(original))
    lines = [{"kind": "chunk"}] + [{"kind": "ready"}] * 9
    output = io.StringIO("".join(json.dumps(event) + "\n" for event in lines))
    process, interruptions = simulated_reader(item, output, monkeypatch)
    item._receive()
    assert journal.read_bytes() == original
    assert item.state == "interrupted" and "saturée" in item.error
    assert item.events.qsize() == 1 and process.terminated == 1
    assert item.events.get(timeout=.1) == {"kind": "error", "error": item.error}
    assert interruptions == [item.error] and item._reader_done.is_set()
    # Even after consuming the error sentinel, a stale control cannot succeed.
    item.events.put_nowait({"kind": "state", "state": "paused"})
    with pytest.raises(ValueError, match="saturée"):
        item.command("pause", target_state="paused", timeout=.1)
    assert process.stdin.getvalue() == ""


@pytest.mark.parametrize("line", [
    "invalid-json\n", "[]\n", '{"kind":"unknown"}\n',
    '{"kind":"state","state":"invalid"}\n', '{"kind":"error","error":null}\n',
])
def test_invalid_native_protocol_is_terminal_and_cannot_acknowledge_stale_state(tmp_path, monkeypatch, line):
    item = capture(tmp_path)
    item.state = "recording"
    item.events.put_nowait({"kind": "state", "state": "paused"})
    process, interruptions = simulated_reader(item, io.StringIO(line), monkeypatch)
    item._receive()
    assert item.state == "interrupted" and item.error
    assert item.events.qsize() == 1 and process.terminated == 1
    assert interruptions == [item.error] and item._reader_done.is_set()
    with pytest.raises(ValueError):
        item.command("pause", target_state="paused", timeout=.1)
    assert process.stdin.getvalue() == ""


def test_unexpected_eof_wakes_command_with_error_without_timeout(tmp_path, monkeypatch):
    item = capture(tmp_path)
    item.state = "recording"
    _, interruptions = simulated_reader(item, io.StringIO(""), monkeypatch)
    item._receive()
    assert item._reader_done.is_set() and item.events.qsize() == 1
    assert interruptions == [item.error]
    with pytest.raises(ValueError, match="sans arrêt confirmé"):
        item.command("stop", target_state="stopped", timeout=.1)


def test_helper_error_is_sticky_and_later_controls_cannot_clear_it(tmp_path, monkeypatch):
    item = capture(tmp_path)
    lines = [{"kind": "ready"}, {"kind": "error", "error": "Fixture persistence failed"},
             {"kind": "state", "state": "stopped"}, {"kind": "ready"}]
    process, interruptions = simulated_reader(item,
        io.StringIO("".join(json.dumps(event) + "\n" for event in lines)), monkeypatch)
    item._receive()
    assert item.state == "interrupted" and item.error == "Fixture persistence failed"
    assert item.events.qsize() == 1 and interruptions == [item.error]
    with pytest.raises(ValueError, match="persistence failed"):
        item.command("stop", target_state="stopped", timeout=.1)
    assert process.stdin.getvalue() == ""


def test_controller_interruption_cannot_be_overwritten_by_concurrent_helper_state(tmp_path):
    item = capture(tmp_path)
    state_assignment, allow_assignment, interrupt_requested = Event(), Event(), Event()

    class CoordinatedState(dict):
        def __getitem__(self, key):
            if key == "state":
                state_assignment.set()
                assert allow_assignment.wait(2)
            return super().__getitem__(key)

    def interrupt():
        interrupt_requested.set()
        item._interrupt("Controller detected stop failure")

    with ThreadPoolExecutor(max_workers=2) as executor:
        reader = executor.submit(item._receive_event, CoordinatedState(kind="state", state="stopped"))
        assert state_assignment.wait(1)
        controller = executor.submit(interrupt)
        try:
            assert interrupt_requested.wait(1)
            with pytest.raises(FutureTimeout):
                controller.result(timeout=.05)
        finally:
            allow_assignment.set()
        reader.result(timeout=1)
        controller.result(timeout=1)
    assert item.error == "Controller detected stop failure" and item.state == "interrupted"
    assert item.events.qsize() == 1
    assert item.events.get_nowait() == {"kind": "error", "error": item.error}


def test_stop_waits_for_eof_and_rejects_error_after_stopped(tmp_path, monkeypatch):
    item = capture(tmp_path)
    stopped_read, permit_terminal_error = Event(), Event()
    native_events = queue.Queue()

    class Output:
        def __iter__(self):
            event = native_events.get(timeout=2)
            yield json.dumps(event) + "\n"
            assert permit_terminal_error.wait(2)
            yield json.dumps({"kind": "error", "error": "Qualification cleanup failed"}) + "\n"

    process, _ = simulated_reader(item, Output(), monkeypatch)

    class Input(io.StringIO):
        def flush(self):
            native_events.put({"kind": "state", "state": "stopped"})

    process.stdin = Input()
    get = item.events.get

    def observe_get(*args, **kwargs):
        event = get(*args, **kwargs)
        if event == {"kind": "state", "state": "stopped"}:
            stopped_read.set()
        return event

    monkeypatch.setattr(item.events, "get", observe_get)
    with ThreadPoolExecutor(max_workers=2) as executor:
        reader = executor.submit(item._receive)
        command = executor.submit(item.command, "stop", target_state="stopped", timeout=2)
        try:
            assert stopped_read.wait(1)
            with pytest.raises(FutureTimeout):
                command.result(timeout=.05)
        finally:
            permit_terminal_error.set()
        with pytest.raises(ValueError, match="cleanup failed"):
            command.result(timeout=1)
        reader.result(timeout=1)
    assert item.state == "interrupted" and item._reader_done.is_set()


@pytest.mark.parametrize("failure", ["missing-eof", "failed-exit", "exit-timeout"])
def test_stop_without_clean_helper_exit_is_sticky_interruption(tmp_path, monkeypatch, failure):
    item = capture(tmp_path)
    process, interruptions = simulated_reader(item, io.StringIO(""), monkeypatch)
    item.events.put_nowait({"kind": "state", "state": "stopped"})
    if failure != "missing-eof":
        item._reader_done.set()
        if failure == "failed-exit":
            process.wait = lambda timeout: 1
        else:
            def wait(timeout):
                raise subprocess.TimeoutExpired("fixture-native-helper", timeout)
            process.wait = wait
    with pytest.raises(ValueError, match="fragments conservés"):
        item.command("stop", target_state="stopped", timeout=.01)
    assert item.state == "interrupted" and item.error
    assert interruptions == [item.error] and item.events.qsize() == 1
    with pytest.raises(ValueError, match="fragments conservés"):
        item.command("stop", target_state="stopped", timeout=.01)
    assert process.stdin.getvalue().count('"op": "stop"') == 1


def test_qualification_handshake_still_precedes_start_and_stop_ack(tmp_path, monkeypatch):
    item = capture(tmp_path)
    authority_calls = allow_pure_fixture_authority(item, tmp_path, monkeypatch)
    item.request["qualification"] = {"token": "private-fixture-token"}
    native_events = queue.Queue()
    native_events.put({"kind": "qualification.armed", "token": "private-fixture-token"})
    commands, committed, trace = [], [], []

    class Output:
        def __iter__(self):
            while True:
                event = native_events.get(timeout=3)
                if event is None:
                    return
                yield json.dumps(event) + "\n"

        def close(self):
            pass

    class Input(io.StringIO):
        def flush(self):
            command = json.loads(self.getvalue().splitlines()[-1])
            commands.append(command)
            trace.append(command["op"])
            if command["op"] == "qualification.open":
                assert command == {"op": "qualification.open", "token": "private-fixture-token", "job_attached": True}
                native_events.put({"kind": "ready"})
            elif command["op"] == "start":
                native_events.put({"kind": "state", "state": "recording"})
            else:
                assert command["op"] == "stop"
                native_events.put({"kind": "chunk"})
                native_events.put({"kind": "state", "state": "stopped"})
                native_events.put(None)

    process, _ = simulated_reader(item, Output(), monkeypatch)
    process.stdin = Input()
    monkeypatch.setattr(item, "_persist", lambda event: committed.append("durable receipt"))
    monkeypatch.setattr(native_audio.subprocess, "Popen", lambda *args, **kwargs: process)
    def attach_job(value):
        trace.append("job-attached")
        return SimpleNamespace(CloseHandle=lambda handle: None), 1
    monkeypatch.setattr(native_audio, "_windows_job", attach_job)
    try:
        item.start()
        result = item.command("stop", target_state="stopped")
        assert result["durable_chunks_acknowledged"] and committed == ["durable receipt"]
        assert [command["op"] for command in commands] == ["qualification.open", "start", "stop"]
        assert trace == ["job-attached", "qualification.open", "start", "stop"]
        assert item._reader_done.is_set() and item.error is None
    finally:
        item.close()
    assert authority_calls

