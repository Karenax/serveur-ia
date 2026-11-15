"""CUDA integration with fictitious models/transport; never imports an ASR runtime."""
from contextlib import nullcontext
import hashlib
import io
import json
from pathlib import Path
import queue
import runpy
import sys
from types import ModuleType, SimpleNamespace as NS

import pytest

from app.services import live_speech as live, meeting_audio as audio, grouped_batch
from scripts import speech_runtime as runtime
from tests.test_meeting_audio_lifecycle import child, Process

__all__ = ["child"]


@pytest.fixture
def cuda_config(tmp_path, monkeypatch):
    model = tmp_path / "whisper-medium"
    model.mkdir()
    (model / "model.bin").write_bytes(b"FICTITIOUS, NOT MODEL WEIGHTS")
    dll = tmp_path / "cuda"
    dll.mkdir()
    for name in ("cublas64_12.dll", "cublasLt64_12.dll", "cudnn64_9.dll"):
        (dll / name).write_bytes(b"FICTITIOUS, NEVER LOAD")
    config = {"model": "medium", "whisper": str(model), "cpu_threads": 4}
    for name in ("segmentation", "embedding"):
        path = tmp_path / (name + ".onnx")
        path.write_bytes(b"FICTITIOUS")
        config[name] = str(path)
    (tmp_path / "models.json").write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("PB_SPEECH_DEVICE", "cuda")
    monkeypatch.setenv("PB_SPEECH_THREADS", "4")
    monkeypatch.setenv("PB_SPEECH_CUDA_DLL_DIRS", json.dumps([str(dll)]))
    monkeypatch.setenv("PB_SPEECH_MODELS_DIR", str(tmp_path))
    return tmp_path


def observed(profile, **changes):
    native = dict(device="cuda", compute_type="int8_float16", device_index=[0], num_workers=1)
    native.update(changes)
    return {"requested": {"model_directory": profile["model_directory"], "device": "cuda", "device_index": 0,
                          "compute_type": "int8_float16", "cpu_threads": 4, "num_workers": 1, "local_files_only": True},
            "native": native, "versions": {"faster_whisper": "1.2.1", "ctranslate2": "4.8.2"}}


def test_quality_CPU_profile_invalidates_previous_fast_qualification_key(cuda_config, monkeypatch):
    monkeypatch.delenv("PB_SPEECH_DEVICE")
    profile = live.speech_profile(cuda_config)
    expected = {"runtime": "faster-whisper", "runtime_version": "1.2.1", "model": "medium",
                "model_directory": str((cuda_config / "whisper-medium").resolve()), "device": "cpu", "compute_type": "int8",
                "cpu_threads": 4, "language": "fr", "beam_size": 5, "word_timestamps": True, "vad_filter": True,
                "min_silence_ms": 250, "previous_text": False, "pcm_context_ms": 500,
                "no_speech_threshold": .6, "compression_ratio_threshold": 2.4, "contract_revision": 2}
    assert profile == expected
    assert live.speech_profile_key(cuda_config) == hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    previous = {**expected, "beam_size": 1, "contract_revision": 1}
    assert live.speech_profile_key(cuda_config) != runtime.profile_key(previous)


def test_DLL_replacement_invalidates_profile_without_changing_model(cuda_config):
    before = live.speech_profile_key(cuda_config)
    (cuda_config / "cuda/cublas64_12.dll").write_bytes(b"FICTITIOUS REPLACEMENT, NEVER LOAD")
    assert live.speech_profile_key(cuda_config) != before


def test_only_child_PATH_is_prefixed_and_search_handles_close(cuda_config, monkeypatch):
    profile = live.speech_profile(cuda_config)
    environment = {"Path": "unchanged-system-path", "FICTITIOUS": "retained"}
    before = dict(environment)
    child_env = runtime.child_environment(profile, environment)
    assert environment == before and child_env["FICTITIOUS"] == "retained"
    assert child_env["PATH"].startswith(str(cuda_config / "cuda"))
    assert sum(k.upper() == "PATH" for k in child_env) == 1
    handles = []
    monkeypatch.setattr(runtime.os, "add_dll_directory", lambda p: NS(close=lambda: handles.append(p)), raising=False)
    original = dict(runtime.os.environ)
    with pytest.raises(RuntimeError, match="fictitious"):
        with runtime.cuda_libraries(profile):
            assert runtime.os.environ["PATH"].startswith(str(cuda_config / "cuda"))
            raise RuntimeError("fictitious inference error")
    assert dict(runtime.os.environ) == original
    if runtime.os.name == "nt":
        assert handles == [str(cuda_config / "cuda")]


@pytest.mark.parametrize("change", [{"device": "cpu"}, {"compute_type": "float16"},
                                  {"device_index": 0}, {"num_workers": True}, {"num_workers": None}])
def test_native_mismatch_is_rejected_before_ready(cuda_config, change):
    profile = live.speech_profile(cuda_config)
    calls = []
    def construct(path, **kwargs):
        calls.append((path, kwargs))
        return NS(model=NS(**observed(profile, **change)["native"]))
    with pytest.raises(ValueError, match="aucun repli CPU"):
        runtime.construct_cuda_model(construct, profile, "1.2.1", "4.8.2")
    assert len(calls) == 1 and calls[0][1]["local_files_only"] is True
    assert calls[0][1]["num_workers"] == 1


def test_wrong_runtime_version_does_not_construct_model(cuda_config):
    with pytest.raises(ValueError, match="Versions"):
        runtime.construct_cuda_model(lambda *a, **k: pytest.fail("No model"), live.speech_profile(cuda_config), "1.2.1", "0.0")


class Output:
    def __init__(self, ready):
        self.lines = queue.Queue()
        self.lines.put(json.dumps(ready) + "\n")
        self.closed = False
    def __iter__(self):
        while True:
            line = self.lines.get(timeout=3)
            if line is None:
                return
            yield line
    def close(self):
        self.closed = True
        self.lines.put(None)


class FakeResidentProcess:
    def __init__(self, ready):
        self.stdout, self.stdin = Output(ready), io.StringIO()
        self.returncode = None
    def poll(self):
        return self.returncode
    def terminate(self):
        self.returncode = 0
        self.stdout.lines.put(None)
    def kill(self):
        self.terminate()
    def wait(self, timeout=None):
        return self.returncode


@pytest.mark.parametrize("invalid", [False, "native-cpu", "different-key", "bool-index"])
def test_actual_parent_validates_profile_before_loaded_and_closes_reader(cuda_config, monkeypatch, invalid):
    profile = live.speech_profile(cuda_config)
    ready = runtime.cuda_ready(profile, observed(profile), .1, {"enabled": False})
    if invalid == "native-cpu":
        ready["observed_constructor"]["native"]["device"] = "cpu"
    elif invalid == "different-key":
        ready["runtime_profile_key"] = "stale"
    elif invalid == "bool-index":
        ready["device_index"] = False
    process = FakeResidentProcess(ready)
    calls = []
    monkeypatch.setattr(live.subprocess, "Popen", lambda command, **kw: calls.append((command, kw)) or process)
    monkeypatch.setattr(live, "_windows_job", lambda p: None)
    resident = live.ResidentWhisper(cuda_config / "storage", models=cuda_config)
    try:
        if invalid:
            with pytest.raises(ValueError):
                resident.start(timeout=2)
            assert not resident.loaded and resident.ready_details is None
        else:
            resident.start(timeout=2)
            assert resident.loaded and resident.ready_details == ready
        assert calls[0][0][-2:] == ["--profile-key", live.speech_profile_key(cuda_config)]
        assert calls[0][1]["env"]["PATH"].startswith(str(cuda_config / "cuda"))
        reader = resident._reader
    finally:
        resident.close()
    assert process.stdout.closed and process.stdin.closed
    assert resident._reader is None and resident._loaded_profile_key is None
    assert reader is None or not reader.is_alive()


@pytest.mark.parametrize("include_ready", [False, True])
def test_full_meeting_parent_requires_matching_GPU_ready(child, cuda_config, monkeypatch, include_ready):
    row, original, attached, closed = child
    profile = runtime.configured_cuda_profile(cuda_config, task="meeting")
    ready = runtime.cuda_ready(profile, observed(profile), .1, {"enabled": False})
    answer = {"segments": [{"id": "fictitious", "text": "SIMULATED ASR"}]}
    process = Process(([ready] if include_ready else []) + [{"result": answer}])
    monkeypatch.setattr(audio, "runtime_status", lambda: {"ready": True, "python": "fake", "models_dir": str(cuda_config), "runtime_profile": profile})
    monkeypatch.setattr(audio.subprocess, "Popen", lambda *a, **k: process)
    if include_ready:
        assert audio._transcribe(row, str(original)) == answer
    else:
        with pytest.raises(ValueError, match="confirmé son profil"):
            audio._transcribe(row, str(original))
    assert attached == [process] and closed == ["private-job-handle"] and process.stdout.closed


def test_GPU_admission_uses_individuals_and_keeps_CPU_group_guard(cuda_config, monkeypatch):
    monkeypatch.setattr(grouped_batch, "enabled", lambda db: True)
    packet = {"chunks": [{"id": "one"}, {"id": "two"}]}
    plan = grouped_batch.admit_plan(None, packet)
    assert [u["chunk_id"] for u in plan["units"]] == ["one", "two"]
    assert all(u["reason"] == "grouped_batch_requires_CPU_profile" for u in plan["units"])
    assert plan["runtime"] is None


@pytest.mark.parametrize("selected", ["cpu", "cuda"])
def test_original_live_entry_uses_selected_constructor_and_keeps_CPU_protocol(cuda_config, monkeypatch, capsys, selected):
    monkeypatch.setenv("PB_SPEECH_DEVICE", selected)
    script = Path(__file__).resolve().parents[1] / "scripts/transcribe_live.py"
    monkeypatch.syspath_prepend(str(script.parent))
    constructor_calls, closed = [], []
    def construct(path, **kwargs):
        constructor_calls.append(kwargs)
        return NS(model=NS(device=selected, compute_type="int8_float16" if selected == "cuda" else "int8", device_index=[0], num_workers=1))
    fw = ModuleType("faster_whisper")
    fw.__version__, fw.WhisperModel = "1.2.1", construct
    fwa = ModuleType("faster_whisper.audio")
    fwa.decode_audio = lambda *a, **k: pytest.fail("No audio in cold-start control")
    monkeypatch.setitem(sys.modules, "faster_whisper", fw)
    monkeypatch.setitem(sys.modules, "faster_whisper.audio", fwa)
    monkeypatch.setitem(sys.modules, "ctranslate2", NS(__version__="4.8.2"))
    monkeypatch.setitem(sys.modules, "offline_guard", NS(verify=lambda: {"enabled": False}))
    monkeypatch.setattr(runtime.os, "add_dll_directory", lambda p: NS(close=lambda: closed.append(p)), raising=False)
    # The direct entry imports the same source as a top-level script module.
    monkeypatch.setitem(sys.modules, "speech_runtime", runtime)
    argv = [str(script), "--models", str(cuda_config), "--storage", str(cuda_config / "storage")]
    if selected == "cuda":
        argv.extend(["--profile-key", live.speech_profile_key(cuda_config)])
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    runpy.run_path(str(script))["main"]()
    event = json.loads(capsys.readouterr().out)
    assert len(constructor_calls) == 1 and constructor_calls[0]["device"] == selected
    assert event["device"] == selected
    if selected == "cuda":
        runtime.validate_cuda_ready(event, live.speech_profile(cuda_config))
        if runtime.os.name == "nt":
            assert len(closed) == 1
    else:
        assert "runtime_profile_key" not in event and "device_index" not in constructor_calls[0]


@pytest.mark.parametrize("selected", ["cpu", "cuda"])
def test_full_recording_entry_keeps_diarization_CPU_and_uses_selected_Whisper(cuda_config, monkeypatch, capsys, selected):
    monkeypatch.setenv("PB_SPEECH_DEVICE", selected)
    script = Path(__file__).resolve().parents[1] / "scripts/transcribe_meeting.py"
    monkeypatch.syspath_prepend(str(script.parent))
    calls, decoding, diarization = [], [], []
    def construct(path, **kwargs):
        calls.append(kwargs)
        def transcribe(samples, **options):
            calls.append(options)
            return [NS(words=[NS(start=0., end=1., word=" FICTIF")], end=1.)], NS(language="fr")
        return NS(model=NS(device=selected, compute_type="int8_float16" if selected == "cuda" else "int8",
                           device_index=[0], num_workers=1), transcribe=transcribe)
    fw = ModuleType("faster_whisper")
    fw.__version__, fw.WhisperModel = "1.2.1", construct
    fwa = ModuleType("faster_whisper.audio")
    fwa.decode_audio = lambda *a, **k: decoding.append(k) or [0.] * 32000
    def diarize(config):
        diarization.append(config)
        return NS(process=lambda *a, **k: NS(sort_by_start_time=lambda: [NS(start=0., end=2., speaker=0)]))
    config_types = {name: lambda **kwargs: NS(**kwargs) for name in (
        "OfflineSpeakerSegmentationModelConfig", "OfflineSpeakerSegmentationPyannoteModelConfig",
        "SpeakerEmbeddingExtractorConfig", "FastClusteringConfig")}
    sherpa = NS(**config_types,
        OfflineSpeakerDiarizationConfig=lambda **kwargs: NS(**kwargs, validate=lambda: True),
        OfflineSpeakerDiarization=diarize)
    for name, module in {"faster_whisper": fw, "faster_whisper.audio": fwa,
                         "ctranslate2": NS(__version__="4.8.2"), "sherpa_onnx": sherpa,
                         "av": NS(open=lambda p: nullcontext(NS(duration=2_000_000)), time_base=1_000_000),
                         "speech_runtime": runtime}.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(runtime.os, "add_dll_directory", lambda p: NS(close=lambda: None), raising=False)
    argv = [str(script), "--models", str(cuda_config), "--audio", str(cuda_config / "FICTIF.wav")]
    if selected == "cuda":
        argv.extend(["--profile-key", runtime.profile_key(runtime.configured_cuda_profile(cuda_config, task="meeting"))])
    monkeypatch.setattr(sys, "argv", argv)
    runpy.run_path(str(script))["main"]()
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert calls[0]["device"] == selected and calls[0]["local_files_only"] is True
    assert calls[1]["beam_size"] == 5 and calls[1]["condition_on_previous_text"] is False
    assert decoding == [{"sampling_rate": 16000}]
    assert diarization[0].segmentation.provider == diarization[0].embedding.provider == "cpu"
    assert events[-1]["result"]["segments"][0]["text"] == "FICTIF"
    ready = [event for event in events if event.get("kind") == "ready"]
    assert len(ready) == (1 if selected == "cuda" else 0)
    if ready:
        runtime.validate_cuda_ready(ready[0], runtime.configured_cuda_profile(cuda_config, task="meeting"))
