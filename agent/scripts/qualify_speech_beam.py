"""Isolated CPU beam comparison; never changes Agent's resident or settings.

Reuse the exact normalized WAVs and scoring rules from the retained corpus.
The child changes only beam_size in transcribe_live.transcribe, records actual
fallback temperatures, and is bounded by a Windows kill-on-close Job Object.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        while block := source.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def emit(**event):
    print(json.dumps(event, ensure_ascii=False), flush=True)


def worker(args):
    from scripts.offline_guard import verify
    guard = verify()
    if not guard["enabled"] or not guard["probe_blocked"]:
        raise RuntimeError("Garde réseau Python non vérifiée")
    import ctranslate2
    import faster_whisper
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio
    from scripts.transcribe_live import transcribe

    config = json.loads((args.models / "models.json").read_text(encoding="utf-8"))
    binary = Path(config["whisper"]).resolve()
    if not binary.is_relative_to(args.models.resolve()) or not (binary / "model.bin").is_file():
        raise ValueError("Binaire local hors répertoire de modèles")
    profile = {"runtime": "faster-whisper", "runtime_version": faster_whisper.__version__,
        "ctranslate2_version": ctranslate2.__version__, "model": config["model"],
        "model_directory": str(binary), "device": "cpu", "compute_type": "int8",
        "cpu_threads": args.threads, "num_workers": 1, "language": "fr",
        "beam_size": args.beam_size, "word_timestamps": True, "vad_filter": True,
        "min_silence_ms": 250, "previous_text": False, "pcm_context_ms": 500,
        "no_speech_threshold": .6, "compression_ratio_threshold": 2.4,
        "temperature_fallback": [0, .2, .4, .6, .8, 1], "log_prob_threshold": -1,
        "best_of": 5, "patience": 1, "contract_revision": 1,
        "qualification_kind": "isolated-beam-comparison"}
    profile_key = hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    started = time.perf_counter()
    model = WhisperModel(str(binary), device="cpu", compute_type="int8",
                         cpu_threads=args.threads, num_workers=1, local_files_only=True)
    model_load_s = time.perf_counter() - started

    class BeamProxy:
        def __init__(self):
            self.decode_details = []

        def transcribe(self, samples, **options):
            options["beam_size"] = args.beam_size
            segments, info = model.transcribe(samples, **options)

            def tracked():
                for part in segments:
                    self.decode_details.append({"temperature": part.temperature,
                        "avg_logprob": part.avg_logprob, "compression_ratio": part.compression_ratio,
                        "no_speech_prob": part.no_speech_prob})
                    yield part

            return tracked(), info

    proxy = BeamProxy()
    emit(kind="ready", runtime_profile=profile, runtime_profile_key=profile_key,
         actual_model=config["model"], model_sha256=digest(binary / "model.bin"),
         model_load_s=model_load_s, offline_guard=guard)
    permitted = [args.storage_source.resolve(), args.storage_output.resolve()]
    for line in sys.stdin:
        if len(line) > 16384:
            raise ValueError("Commande de qualification trop longue")
        request = json.loads(line)
        if request.get("op") == "stop":
            return
        path = Path(request["path"]).resolve()
        if not path.is_file() or not any(path.is_relative_to(root) for root in permitted):
            raise ValueError("WAV hors corpus de qualification")
        started = time.perf_counter()
        samples = decode_audio(str(path), sampling_rate=16000)
        proxy.decode_details = []
        result = transcribe(proxy, samples, request)
        emit(kind="result", request_id=request["request_id"], **result,
             compute_s=time.perf_counter() - started, decode_details=proxy.decode_details)


class IsolatedWorker:
    def __init__(self, args, fixtures, directory):
        self.args, self.fixtures, self.directory = args, fixtures, directory
        self.process = self.job = None
        self.events = queue.Queue()
        self.deadline = time.monotonic() + args.timeout
        self.stderr = None

    def receive(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Délai total de qualification dépassé")
        try:
            event = self.events.get(timeout=min(120, remaining))
        except queue.Empty as exc:
            raise TimeoutError("Le worker ne répond plus dans le délai borné") from exc
        if event.get("kind") == "error":
            raise RuntimeError(event.get("error", "Worker arrêté"))
        return event

    def start(self):
        from app.services.live_speech import _windows_job
        python = self.args.python or ROOT / ".venv-speech" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        environment = dict(os.environ, AGENT_QUALIFICATION_OFFLINE="1", HF_HUB_OFFLINE="1",
                           TRANSFORMERS_OFFLINE="1", PYTHONUTF8="1")
        self.stderr = (self.directory / "worker-stderr.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen([str(python), "-u", str(Path(__file__).resolve()), "--worker",
            "--models", str(self.args.models.resolve()), "--beam-size", str(self.args.beam_size),
            "--threads", str(self.args.threads), "--storage-source", str(self.fixtures),
            "--storage-output", str(self.directory)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.stderr, encoding="utf-8", text=True, env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            self.job = _windows_job(self.process)

            def read():
                for line in self.process.stdout:
                    try:
                        self.events.put(json.loads(line))
                    except ValueError:
                        continue
                self.events.put({"kind": "error", "error": "Worker de qualification terminé"})

            threading.Thread(target=read, name="beam-qualification-events", daemon=True).start()
            ready = self.receive()
            if ready.get("kind") != "ready":
                raise ValueError("Profil prêt non confirmé")
            profile = ready["runtime_profile"]
            if profile["beam_size"] != self.args.beam_size or profile["cpu_threads"] != self.args.threads:
                raise ValueError("Paramètres réellement chargés incohérents")
            return ready
        except Exception:
            self.close()
            raise

    def transcribe(self, path):
        identity = uuid.uuid4().hex
        command = {"request_id": identity, "path": str(path), "track": "system"}
        started = time.perf_counter()
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()
        result = self.receive()
        if result.get("kind") != "result" or result.get("request_id") != identity:
            raise ValueError("Réponse hors requête de qualification")
        result["request_wall_s"] = time.perf_counter() - started
        return result

    def close(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    stream.close()
        if self.job:
            kernel, handle = self.job
            kernel.CloseHandle(handle)
            self.job = None
        if self.stderr:
            self.stderr.close()


def qualify(args):
    from scripts.qualify_speech_corpus import INDUSTRIAL, fold, score_report
    from scripts.qualify_speech_resources import ProcessTreeMeter
    report_path = args.report.resolve()
    if not report_path.is_relative_to(ROOT / "logs" / "foresight-runtime"):
        raise ValueError("Le rapport doit rester dans logs/foresight-runtime")
    if report_path.exists():
        raise FileExistsError("Rapport existant conservé ; choisir un nouveau nom")
    baseline = json.loads(args.baseline_report.read_text(encoding="utf-8"))
    cases = [case for case in baseline["cases"] if case["condition"] == "clean_sapi_industrial"]
    fixtures = Path(cases[0]["audio"]).resolve().parent
    for case, (reference, _) in zip(cases, INDUSTRIAL, strict=True):
        path = Path(case["audio"]).resolve()
        if path.parent != fixtures or case["reference"] != reference or digest(path) != case["audio_sha256"]:
            raise ValueError("Le corpus critique ne correspond plus aux WAV et références d'origine")
    directory = report_path.parent / (report_path.stem + "-" + uuid.uuid4().hex[:8])
    directory.mkdir(parents=True)
    window = directory / "benchmark-five-seconds.wav"
    with wave.open(str(cases[0]["audio"]), "rb") as source:
        if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (16000, 1, 2):
            raise ValueError("Corpus PCM16 mono16k attendu")
        raw = source.readframes(80000)
        if len(raw) != 160000:
            raise ValueError("Fenêtre de cinq secondes incomplète")
    with wave.open(str(window), "wb") as target:
        target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        target.writeframes(raw)
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "completed": False,
        "baseline_report": str(args.baseline_report.resolve()), "directory": str(directory),
        "worker_sha256": digest(Path(__file__)), "canonical_transcribe_sha256": digest(ROOT / "scripts/transcribe_live.py"),
        "cases": [], "prewarmed_five_second_requests": [], "production_config_changed": False,
        "production_data_modified": False, "browser_sse_visibility_measured": False,
        "physical_hardware_or_teams_tested": False, "real_hardware_120min_measured": False,
        "real_meeting_accuracy_qualified": False, "industrial_direct_qualified": False,
        "window_audio_sha256": digest(window), "timeout_s": args.timeout}

    def save():
        temporary = directory / "report.pending.json"
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(report_path)

    runtime = IsolatedWorker(args, fixtures, directory)
    meter = None
    try:
        report.update(runtime.start())
        meter = ProcessTreeMeter(runtime.process.pid)
        for index in range(3):
            output = runtime.transcribe(window)
            text = " ".join(row["text"] for row in output["segments"])
            report["prewarmed_five_second_requests"].append({**output, "text": text,
                "project_code_present": bool(re.search(INDUSTRIAL[0][1]["project_code"], fold(text))),
                "section_mm2_present": bool(re.search(INDUSTRIAL[0][1]["section_mm2"], fold(text))),
                "wrong_section_metres_asserted": bool(re.search(r"(?:2[.,]5|deux virgule cinq) (?:metres|m)\b", fold(text))),
                "reference_may_extend_beyond_window": True})
            save()
            emit(phase="warm5s", completed=index + 1, request_wall_s=output["request_wall_s"], text=text)
        report["warm_resources"] = meter.finish()
        meter = ProcessTreeMeter(runtime.process.pid)
        for index, case in enumerate(cases):
            output = runtime.transcribe(Path(case["audio"]).resolve())
            report["cases"].append({**case, "transcript": " ".join(row["text"] for row in output["segments"]),
                "compute_s": output["compute_s"], "request_wall_s": output["request_wall_s"],
                "duration_ms": output["duration_ms"], "timecodes": output["segments"],
                "decode_details": output["decode_details"]})
            save()
            emit(phase="industrial", completed=index + 1, request_wall_s=output["request_wall_s"])
        report["corpus_resources"] = meter.finish()
        meter = None
        score_report(report)
        warm = report["prewarmed_five_second_requests"]
        report.update(completed=True, all_requests_under_5s=all(row["request_wall_s"] <= 5 for row in warm),
            window_has_wrong_unit=any(row["wrong_section_metres_asserted"] for row in warm),
            sample_size=3, window_accuracy_fully_qualified=False)
        report["microrecipe_passed"] = bool(report["industrial_quality_gate_passed"]
            and report["all_requests_under_5s"] and not report["window_has_wrong_unit"])
        save()
        emit(report=str(report_path), critical_correct=report["critical_correct"], critical_total=report["critical_total"],
             wer=report["clean_industrial_weighted_wer"], warm_s=[row["request_wall_s"] for row in warm],
             microrecipe_passed=report["microrecipe_passed"], industrial_direct_qualified=False)
        return 0
    except Exception as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"
        save()
        raise
    finally:
        try:
            if meter:
                report["interrupted_resources"] = meter.finish()
                save()
        finally:
            runtime.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--beam-size", type=int, required=True, choices=range(1, 17))
    parser.add_argument("--threads", type=int, required=True, choices=range(1, 17))
    parser.add_argument("--python", type=Path)
    parser.add_argument("--timeout", type=int, default=600, choices=range(30, 1801))
    parser.add_argument("--baseline-report", type=Path, default=ROOT / "logs/foresight-runtime/speech-corpus-qualification.json")
    parser.add_argument("--report", type=Path, default=ROOT / "logs/foresight-runtime/small-beam5-qualification.json")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--storage-source", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--storage-output", type=Path, help=argparse.SUPPRESS)
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
