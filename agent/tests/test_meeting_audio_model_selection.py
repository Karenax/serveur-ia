"""Explicit overrides remain independent; cached medium is the CPU default."""
import json
from pathlib import Path

import pytest

from app.services import live_speech, meeting_audio


@pytest.fixture
def models(tmp_path, monkeypatch):
    monkeypatch.setattr(meeting_audio, "ROOT", tmp_path)
    monkeypatch.setattr(live_speech, "ROOT", tmp_path)
    for name in ("PB_SPEECH_MODELS_DIR", "PB_MEETING_SPEECH_MODELS_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PB_SPEECH_DEVICE", "cpu")
    monkeypatch.setenv("PB_SPEECH_THREADS", "4")
    monkeypatch.setenv("PB_SPEECH_QUALIFICATION_REPORT", str(tmp_path / "no-qualification.json"))
    python = tmp_path / "metadata-only-python.exe"
    python.write_bytes(b"Not an executable; readiness checks metadata only")
    monkeypatch.setenv("PB_SPEECH_PYTHON", str(python))
    result = {}
    for model, directory in (("small", "audio"), ("medium", "audio-medium")):
        path = tmp_path / ".models" / directory
        whisper = path / ("whisper-" + model)
        whisper.mkdir(parents=True)
        (whisper / "model.bin").write_bytes(b"Fictitious model metadata")
        for filename in ("segmentation.onnx", "embedding.onnx"):
            (path / filename).write_bytes(b"Fictitious diarization metadata")
        (path / "models.json").write_text(json.dumps({
            "model": model, "whisper": str(whisper),
            "segmentation": str(path / "segmentation.onnx"), "embedding": str(path / "embedding.onnx"),
        }), encoding="utf-8")
        result[model] = path
    return result


def test_full_recording_and_live_prefer_cached_medium_on_cpu(models):
    batch = meeting_audio.runtime_status()
    live = live_speech.runtime_status()
    assert batch["ready"] and batch["model"] == "medium"
    assert Path(batch["models_dir"]) == models["medium"]
    assert live["installed"] and live["model"] == "medium"
    assert live["runtime_profile"]["model"] == "medium"
    assert live["runtime_profile"]["beam_size"] == 5
    assert not live["real_test_passed"] and not live["qualified_live_latency"]


def test_common_explicit_runtime_remains_authoritative(models, monkeypatch):
    monkeypatch.setenv("PB_SPEECH_MODELS_DIR", str(models["small"]))
    assert meeting_audio.models_directory() == models["small"]
    assert live_speech.runtime_paths()[1] == models["small"]


def test_recording_override_does_not_reconfigure_live(models, monkeypatch):
    monkeypatch.setenv("PB_SPEECH_MODELS_DIR", str(models["small"]))
    monkeypatch.setenv("PB_MEETING_SPEECH_MODELS_DIR", str(models["medium"]))
    assert meeting_audio.models_directory() == models["medium"]
    assert live_speech.runtime_paths()[1] == models["small"]


@pytest.mark.parametrize("missing", ["models.json", "segmentation.onnx", "embedding.onnx", "whisper-medium/model.bin"])
def test_partial_optional_medium_keeps_existing_runtime_available(models, missing):
    (models["medium"] / missing).unlink()  # Only this test's freshly created fake file.
    status = meeting_audio.runtime_status()
    assert status["ready"] and status["model"] == "small"
    assert live_speech.runtime_paths()[1] == models["small"]


@pytest.mark.parametrize("payload", ["not-json", "[]", '{"model":"small"}', '{"model":"medium","whisper":null}'])
def test_invalid_optional_medium_falls_back_without_loading_anything(models, payload):
    (models["medium"] / "models.json").write_text(payload, encoding="utf-8")
    assert meeting_audio.runtime_status()["model"] == "small"
    assert live_speech.runtime_paths()[1] == models["small"]


def test_missing_explicit_runtime_is_reported_instead_of_silent_model_change(models, monkeypatch):
    missing = models["medium"].parent / "operator-selected-missing"
    monkeypatch.setenv("PB_MEETING_SPEECH_MODELS_DIR", str(missing))
    assert meeting_audio.models_directory() == missing
    assert not meeting_audio.runtime_status()["ready"]


def test_cached_medium_never_enables_or_selects_GPU_implicitly(models, monkeypatch):
    monkeypatch.setenv("PB_SPEECH_DEVICE", "cuda")
    assert meeting_audio.models_directory() == models["small"]
    assert live_speech.runtime_paths()[1] == models["small"]


def test_invalid_device_keeps_runtime_status_error_contract(models, monkeypatch):
    monkeypatch.setenv("PB_SPEECH_DEVICE", "invalid")
    status = meeting_audio.runtime_status()
    assert not status["ready"] and "PB_SPEECH_DEVICE" in status["detail"]
