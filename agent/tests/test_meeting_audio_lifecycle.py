"""Legacy batch children cannot survive Agent or failed Windows isolation."""
from contextlib import nullcontext
import io
import json
import subprocess
from types import SimpleNamespace

import pytest

from app.services import live_speech, meeting_audio as audio


class Process:
    def __init__(self, events, *, exit_code=0, terminate_timeout=False):
        self.stdout = io.StringIO("".join(json.dumps(event) + "\n" for event in events))
        self.exit_code = exit_code
        self.returncode = None
        self.terminate_timeout = terminate_timeout
        self.calls = []

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        self.calls.append(("wait", timeout))
        if self.terminate_timeout and ("terminate",) in self.calls and ("kill",) not in self.calls:
            raise subprocess.TimeoutExpired("isolated-audio", timeout)
        self.returncode = self.exit_code
        return self.returncode

    def terminate(self):
        self.calls.append(("terminate",))

    def kill(self):
        self.calls.append(("kill",))


@pytest.fixture
def child(monkeypatch, tmp_path):
    original = tmp_path / "fictitious.wav"
    original.write_bytes(b"Exact original audio remains intact")
    monkeypatch.setattr(audio, "runtime_status", lambda: {"python": "fixture-python", "models_dir": "fixture-models"})
    monkeypatch.setattr(audio, "SessionLocal", lambda: nullcontext(SimpleNamespace(
        get=lambda *_: SimpleNamespace(cancel_requested=False))))
    monkeypatch.setattr(audio, "_stop", SimpleNamespace(is_set=lambda: False))
    row = SimpleNamespace(id="fixture-recording", num_speakers=2)
    attached, closed = [], []
    kernel = SimpleNamespace(CloseHandle=lambda handle: closed.append(handle))
    def isolate(process):
        attached.append(process)
        return kernel, "private-job-handle"
    monkeypatch.setattr(live_speech, "_windows_job", isolate)
    return row, original, attached, closed


def launch(monkeypatch, process):
    def popen(*_args, **kwargs):
        assert kwargs["stdin"] == subprocess.DEVNULL
        return process
    monkeypatch.setattr(audio.subprocess, "Popen", popen)


def test_completed_legacy_child_releases_job_and_keeps_original(child, monkeypatch):
    row, original, attached, closed = child
    result = {"segments": [{"text": "Phrase fictive"}]}
    process = Process([{"result": result}])
    launch(monkeypatch, process)
    assert audio._transcribe(row, str(original)) == result
    assert attached == [process] and closed == ["private-job-handle"]
    assert process.returncode == 0 and process.stdout.closed
    assert ("terminate",) not in process.calls
    assert original.read_bytes() == b"Exact original audio remains intact"


def test_isolation_failure_terminates_before_reading_and_does_not_publish(child, monkeypatch):
    row, original, _, closed = child
    process = Process([{"result": {"segments": []}}], terminate_timeout=True)
    launch(monkeypatch, process)
    def refuse(_):
        raise OSError("Isolation Windows impossible")
    monkeypatch.setattr(live_speech, "_windows_job", refuse)
    with pytest.raises(OSError, match="Isolation"):
        audio._transcribe(row, str(original))
    assert process.calls == [("terminate",), ("wait", 5), ("kill",), ("wait", 5)]
    assert process.stdout.closed and closed == []
    assert original.read_bytes() == b"Exact original audio remains intact"


@pytest.mark.parametrize("failure", ["cancel", "invalid-event", "failed-exit"])
def test_every_legacy_failure_closes_the_job(child, monkeypatch, failure):
    row, original, attached, closed = child
    process = Process([], exit_code=1)
    if failure == "invalid-event":
        process.stdout = io.StringIO("not-json\n")
    if failure == "cancel":
        monkeypatch.setattr(audio, "_stop", SimpleNamespace(is_set=lambda: True))
    launch(monkeypatch, process)
    exception = audio.Cancelled if failure == "cancel" else ValueError
    with pytest.raises(exception):
        audio._transcribe(row, str(original))
    assert attached == [process] and closed == ["private-job-handle"]
    assert process.stdout.closed and process.returncode is not None
    if failure != "failed-exit":
        assert ("terminate",) in process.calls
    assert original.read_bytes() == b"Exact original audio remains intact"
