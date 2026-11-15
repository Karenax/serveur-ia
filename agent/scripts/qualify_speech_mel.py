"""One isolated paired experiment: shorten mel padding, preserve all useful frames.

Medium CPU4/int8/beam1, VAD and real word timestamps remain unchanged. This
never edits installed packages, activates a profile or reads hardware audio.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.qualify_speech_beam import IsolatedWorker, digest, emit  # noqa: E402

MODES = ("pad3000", "short_stride2")


def short_mel(features, length=3000, *, axis=-1):
    """Keep every useful mel column; add at most one zero for encoder stride2.

    The caller already slices windows to <=3000 frames. Oversize input is
    rejected rather than silently discarding audio. No normalization changes.
    """
    import numpy as np
    if features.ndim != 2 or axis not in (-1, 1) or length != 3000:
        raise ValueError("Contrat mel2D, dernier axe et maximum3000 requis")
    frames = features.shape[-1]
    if not 0 < frames <= length:
        raise ValueError("Fenêtre mel vide ou supérieure à3000 ; aucune troncature")
    if frames % 2:
        return np.pad(features, ((0, 0), (0, 1)))
    return features


def worker(args):
    from scripts.offline_guard import verify
    guard = verify()
    if not guard["enabled"] or not guard["probe_blocked"]:
        raise RuntimeError("Garde réseau Python non vérifiée")
    import ctranslate2
    import faster_whisper
    import numpy as np
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio
    from scripts.transcribe_live import transcribe

    config = json.loads((args.models / "models.json").read_text(encoding="utf-8"))
    binary = Path(config["whisper"]).resolve()
    if config["model"] != "medium" or not binary.is_relative_to(args.models.resolve()):
        raise ValueError("Le protocole requiert le medium local indiqué")
    common = {"runtime": "faster-whisper", "runtime_version": faster_whisper.__version__,
        "ctranslate2_version": ctranslate2.__version__, "model": "medium",
        "model_sha256": digest(binary / "model.bin"), "device": "cpu", "compute_type": "int8",
        "cpu_threads": 4, "num_workers": 1, "language": "fr", "beam_size": 1,
        "word_timestamps": True, "without_timestamps": False, "vad_filter": True,
        "min_silence_ms": 250, "condition_on_previous_text": False,
        "initial_prompt": None, "hotwords": None, "no_speech_threshold": .6,
        "compression_ratio_threshold": 2.4, "temperature_fallback": [0, .2, .4, .6, .8, 1],
        "log_prob_threshold": -1, "best_of": 5, "patience": 1, "contract_revision": 1,
        "qualification_kind": "sealed-full-phrase-paired-mel-padding", "maximum_mel_frames": 3000}
    profiles = {mode: dict(common, mel_padding_policy=mode) for mode in MODES}
    keys = {mode: hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            for mode, profile in profiles.items()}
    started = time.perf_counter()
    model = WhisperModel(str(binary), device="cpu", compute_type="int8", cpu_threads=4,
                         num_workers=1, local_files_only=True)
    load_s = time.perf_counter() - started
    timings, mel_calls, encoder_shapes = {}, [], []

    def instrument(original, key):
        def wrapped(*values, **options):
            begin = time.perf_counter()
            try:
                return original(*values, **options)
            finally:
                timings[key] = timings.get(key, 0) + time.perf_counter() - begin
        return wrapped

    module = importlib.import_module("faster_whisper.transcribe")
    original_pad = module.pad_or_trim
    mode = "pad3000"

    def selected_pad(features, length=3000, *, axis=-1):
        if not 0 < features.shape[-1] <= 3000:
            raise ValueError("Fenêtre hors maximum ; aucune donnée utile supprimée")
        result = (original_pad(features, length, axis=axis) if mode == "pad3000"
                  else short_mel(features, length, axis=axis))
        mel_calls.append({"input_frames": features.shape[-1], "encoder_frames": result.shape[-1],
            "added_zero_frames": result.shape[-1] - features.shape[-1],
            "useful_frames_preserved": bool(np.array_equal(features, result[:, :features.shape[-1]]))})
        return result

    original_encode = model.encode

    def tracked_encode(features):
        encoder_shapes.append(list(features.shape))
        return original_encode(features)

    # Overrides live only in this one isolated child, never in the installed file.
    module.pad_or_trim = selected_pad
    module.get_speech_timestamps = instrument(module.get_speech_timestamps, "vad_s")
    model.add_word_timestamps = instrument(model.add_word_timestamps, "word_alignment_s")
    model.find_alignment = instrument(model.find_alignment, "alignment_core_s")
    model.encode = instrument(tracked_encode, "encode_s")
    model.generate_with_fallback = instrument(model.generate_with_fallback, "decode_s")
    permitted = args.storage_source.resolve()
    emit(kind="ready", runtime_profiles=profiles, runtime_profile_keys=keys,
         model_sha256=common["model_sha256"], model_load_s=load_s, offline_guard=guard,
         installed_transcribe_sha256=digest(Path(module.__file__)))
    for line in sys.stdin:
        if len(line) > 16384:
            raise ValueError("Commande trop longue")
        request = json.loads(line)
        if request.get("op") == "stop":
            return
        path = Path(request["path"]).resolve()
        mode = request["mode"]
        if mode not in profiles or not path.is_file() or not path.is_relative_to(permitted):
            raise ValueError("Requête hors corpus scellé")
        started = time.perf_counter()
        samples = decode_audio(str(path), sampling_rate=16000)
        audio_decode_s = time.perf_counter() - started
        timings.clear()
        mel_calls.clear()
        encoder_shapes.clear()
        raw_parts, actual_options = [], None

        class Proxy:
            def transcribe(self, data, **options):
                nonlocal actual_options
                parts, info = model.transcribe(data, **options)
                actual_options = asdict(info.transcription_options)

                def tracked():
                    for part in parts:
                        raw_parts.append(asdict(part))
                        yield part
                return tracked(), info

        result = transcribe(Proxy(), samples, {"track": "system"})
        timecodes_valid = bool(result["segments"]) and all(
            0 <= row["start_ms"] <= row["end_ms"] <= result["duration_ms"]
            for row in result["segments"])
        emit(kind="result", request_id=request["request_id"], mode=mode, **result,
             compute_s=time.perf_counter() - started,
             component_timings=dict(timings, audio_decode_s=audio_decode_s),
             raw_engine_segments=raw_parts, actual_options=actual_options,
             mel_windows=list(mel_calls), encoder_shapes=list(encoder_shapes),
             timecodes_within_original_audio=timecodes_valid)


class MelWorker(IsolatedWorker):
    def start(self):
        from app.services.live_speech import _windows_job
        python = ROOT / ".venv-speech" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        environment = dict(os.environ, AGENT_QUALIFICATION_OFFLINE="1", HF_HUB_OFFLINE="1",
                           TRANSFORMERS_OFFLINE="1", PYTHONUTF8="1")
        self.stderr = (self.directory / "worker-stderr.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen([str(python), "-u", str(Path(__file__).resolve()), "--worker",
            "--models", str(self.args.models.resolve()), "--storage-source", str(self.fixtures),
            "--report", str(self.args.report.resolve())],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, encoding="utf-8", text=True,
            env=environment, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            self.job = _windows_job(self.process)

            def read():
                for line in self.process.stdout:
                    try:
                        self.events.put(json.loads(line))
                    except ValueError:
                        continue
                self.events.put({"kind": "error", "error": "Worker arrêté"})

            threading.Thread(target=read, name="mel-qualification-events", daemon=True).start()
            ready = self.receive()
            if ready.get("kind") != "ready":
                raise ValueError("Chargement du modèle non confirmé")
            return ready
        except Exception:
            self.close()
            raise

    def transcribe(self, path, mode):
        identity = uuid.uuid4().hex
        command = {"request_id": identity, "path": str(path), "mode": mode}
        started = time.perf_counter()
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()
        output = self.receive()
        if output.get("kind") != "result" or output.get("request_id") != identity:
            raise ValueError("Réponse hors requête")
        output["request_wall_s"] = time.perf_counter() - started
        return output


def qualify(args):
    from scripts.qualify_speech_corpus import INDUSTRIAL, percentile, score_report
    from scripts.qualify_speech_resources import ProcessTreeMeter
    report_path = args.report.resolve()
    if not report_path.is_relative_to(ROOT / "logs" / "foresight-runtime"):
        raise ValueError("Rapport hors preuves locales")
    if report_path.exists():
        raise FileExistsError("Rapport existant conservé")
    original = json.loads(args.baseline_report.read_text(encoding="utf-8"))
    cases = [case for case in original["cases"] if case["condition"] == "clean_sapi_industrial"]
    fixtures = Path(cases[0]["audio"]).resolve().parent
    for case, (reference, _) in zip(cases, INDUSTRIAL, strict=True):
        path = Path(case["audio"]).resolve()
        if path.parent != fixtures or case["reference"] != reference or digest(path) != case["audio_sha256"]:
            raise ValueError("Le corpus ou les références ont changé")
    directory = report_path.parent / (report_path.stem + "-" + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True)
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "completed": False,
        "hypothesis": "Remove only mel zero-padding to3000; preserve every useful frame and word timestamps",
        "baseline_report": str(args.baseline_report.resolve()), "baseline_sha256": digest(args.baseline_report),
        "worker_sha256": digest(Path(__file__)), "canonical_transcribe_sha256": digest(ROOT / "scripts/transcribe_live.py"),
        "directory": str(directory), "timeout_s": args.timeout,
        "primary_sources": ["https://github.com/OpenNMT/CTranslate2/blob/v4.8.2/src/layers/whisper.cc",
            "https://github.com/OpenNMT/CTranslate2/blob/v4.8.2/include/ctranslate2/layers/whisper.h",
            "https://github.com/OpenNMT/CTranslate2/blob/v4.8.2/src/layers/common.cc"],
        "sealed_audio_sha256": [case["audio_sha256"] for case in cases],
        "warmups_excluded_from_latency": [], "conditions": {mode: {"cases": []} for mode in MODES},
        "paired_order": "alternate AB/BA by case, full identical WAVs, one warmup per policy excluded",
        "model_receives_references": False, "production_config_changed": False, "production_data_modified": False,
        "hardware_audio_accessed": False, "gpu_used": False, "lm_studio_unloaded": False,
        "five_second_direct_quality_qualified": False, "browser_sse_visibility_measured": False,
        "industrial_direct_qualified": False}

    def save():
        temporary = directory / "report.pending.json"
        with temporary.open("w", encoding="utf-8") as target:
            json.dump(report, target, ensure_ascii=False, indent=2)
            target.flush()
            os.fsync(target.fileno())
        temporary.replace(report_path)

    runtime, meter = MelWorker(args, fixtures, directory), None
    save()
    try:
        report.update(runtime.start())
        if report["model_sha256"] != original["model_sha256"]:
            raise ValueError("Le modèle medium diffère du modèle scellé")
        for mode in MODES:
            report["warmups_excluded_from_latency"].append(runtime.transcribe(Path(cases[0]["audio"]), mode))
            save()
            emit(phase="warmup", mode=mode)
        meter = ProcessTreeMeter(runtime.process.pid)
        for index, case in enumerate(cases):
            order = MODES if index % 2 == 0 else tuple(reversed(MODES))
            for mode in order:
                request_meter = ProcessTreeMeter(runtime.process.pid)
                try:
                    output = runtime.transcribe(Path(case["audio"]).resolve(), mode)
                finally:
                    request_resources = request_meter.finish()
                report["conditions"][mode]["cases"].append({**case, **output,
                    "resources": request_resources,
                    "transcript": " ".join(row["text"] for row in output["segments"])})
                save()
                emit(phase="paired_full_phrase", case=index + 1, mode=mode,
                     request_wall_s=output["request_wall_s"], encode_s=output["component_timings"].get("encode_s", 0),
                     encoder_shapes=output["encoder_shapes"])
        report["resources"] = meter.finish()
        meter = None
        for mode, condition in report["conditions"].items():
            score_report(condition)
            durations = [case["request_wall_s"] for case in condition["cases"]]
            condition.update(request_p50_s=percentile(durations, .5), request_p95_s=percentile(durations, .95),
                request_min_s=min(durations), request_max_s=max(durations), request_mean_s=statistics.mean(durations),
                full_phrase_sample_size=len(durations),
                all_full_phrases_under_5s=all(value <= 5 for value in durations),
                full_phrases_under_5s=sum(value <= 5 for value in durations),
                all_timecodes_within_original_audio=all(case["timecodes_within_original_audio"] for case in condition["cases"]))
            components = set().union(*(case["component_timings"] for case in condition["cases"]))
            condition["component_means_s"] = {name: statistics.mean(case["component_timings"].get(name, 0)
                for case in condition["cases"]) for name in sorted(components)}
        control, short = (report["conditions"][mode] for mode in MODES)
        report["paired_latency_ratios_short_over_control"] = [b["request_wall_s"] / a["request_wall_s"]
            for a, b in zip(control["cases"], short["cases"], strict=True)]
        report["all_actual_options_identical"] = all(a["actual_options"] == b["actual_options"]
            for a, b in zip(control["cases"], short["cases"], strict=True))
        report["all_useful_mel_frames_preserved"] = all(window["useful_frames_preserved"]
            for condition in report["conditions"].values() for case in condition["cases"] for window in case["mel_windows"])
        report["all_source_hashes_still_sealed"] = all(digest(Path(c["audio"])) == c["audio_sha256"] for c in cases)
        report["canonical_transcribe_unchanged"] = report["canonical_transcribe_sha256"] == digest(ROOT / "scripts/transcribe_live.py")
        report["full_phrase_quality_and_latency_gate_passed"] = bool(short["industrial_quality_gate_passed"]
            and short["all_full_phrases_under_5s"] and short["all_timecodes_within_original_audio"]
            and report["all_actual_options_identical"] and report["all_useful_mel_frames_preserved"]
            and report["all_source_hashes_still_sealed"])
        report["completed"] = True
        save()
        emit(report=str(report_path), summary={mode: {key: value for key, value in condition.items() if key != "cases"}
                                              for mode, condition in report["conditions"].items()})
        return 0
    except Exception as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"
        save()
        raise
    finally:
        try:
            if meter:
                report["interrupted_resources"] = meter.finish()
        finally:
            runtime.close()
            report["worker_process_exited"] = runtime.process is None or runtime.process.poll() is not None
            report["job_object_closed"] = runtime.job is None
            save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=ROOT / ".models/audio-medium")
    parser.add_argument("--baseline-report", type=Path, default=ROOT / "logs/foresight-runtime/speech-corpus-medium.json")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600, choices=range(30, 601))
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--storage-source", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        try:
            worker(args)
            return 0
        except Exception as exc:
            emit(kind="error", error=f"{type(exc).__name__}: {exc}")
            raise
    return qualify(args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
