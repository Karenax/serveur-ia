"""One expressly authorized 30-second raw WASAPI microphone test, local only.

No transcription, source creation, database or HTTP service. Reuses the native
WASAPI inventory/session guard and the Windows child Job Object lifecycle.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def now():
    return datetime.now(timezone.utc).isoformat()


def normalized_name(value):
    # The driver adds only its registered-trademark marker to the user label.
    return " ".join(value.replace("(R)", "").replace("®", "").casefold().split())


def restricted_token():
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.IsTokenRestricted.argtypes = [wintypes.HANDLE]
    advapi.IsTokenRestricted.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return bool(advapi.IsTokenRestricted(token))
    finally:
        kernel.CloseHandle(token)


def save_json(path, value):
    with path.open("w", encoding="utf-8") as target:
        json.dump(value, target, ensure_ascii=False, indent=2)
        target.flush()
        os.fsync(target.fileno())


class CaptureDeadline:
    """Opening and capture use distinct monotonic budgets; no progress reset."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.phase = "opening"
        self.deadline = clock() + 45

    def remaining(self):
        return max(0, self.deadline - self.clock())

    def on_ready(self):
        if self.phase != "opening":
            raise RuntimeError("Le délai de capture ne peut pas être renouvelé")
        if not self.remaining():
            raise TimeoutError("Le périphérique n'est pas prêt dans le délai d'ouverture")
        self.phase = "capture_and_flush"
        self.deadline = self.clock() + 30 + 5


class ActiveCaptureWindow:
    """A single START fixes both wall-clock stop and accepted ADC interval."""
    def __init__(self, rate, clock=time.monotonic):
        self.rate = rate
        self.clock = clock
        self.started = None
        self.adc_started = None
        self.deadline = None

    def start(self, adc_started):
        if self.started is not None:
            raise RuntimeError("La fenêtre matérielle ne peut pas être renouvelée")
        if not math.isfinite(adc_started):
            raise ValueError("Horloge du périphérique invalide")
        self.started = self.clock()
        self.adc_started = adc_started
        self.deadline = self.started + 30

    def remaining(self):
        if self.deadline is None:
            raise RuntimeError("Le début de capture n'a pas été autorisé")
        return max(0, self.deadline - self.clock())

    def accepted_range(self, adc_time, frame_count, accepted_frames):
        if self.adc_started is None or not math.isfinite(adc_time):
            raise ValueError("Horodatage ADC indisponible")
        first = min(frame_count, max(0, math.ceil((self.adc_started - adc_time) * self.rate - 1e-6)))
        last = min(frame_count, max(first, math.floor((self.adc_started + 30 - adc_time)
                                                    * self.rate + 1e-6)))
        last = min(last, first + max(0, self.rate * 30 - accepted_frames))
        return first, last


def capture(args):
    from scripts.native_audio_capture import inventory, session_id
    from scripts.offline_guard import verify
    import pyaudiowpatch as audio_api

    guard = verify()
    if not guard["enabled"] or not guard["probe_blocked"]:
        raise ValueError("Garde de connexions Python indisponible")
    devices = inventory()
    if not devices["interactive_session"] or session_id(args.parent_pid) != devices["session_id"]:
        raise ValueError("Session Windows interactive propriétaire différente")
    matches = [item for item in devices["devices"] if item["index"] == args.device_index
        and normalized_name(item["name"]) == normalized_name(args.authorized_device_name)
        and item["maxInputChannels"] > 0 and not item["isLoopbackDevice"]]
    if len(matches) != 1:
        raise ValueError("Le périphérique ne correspond pas au microphone explicitement autorisé")
    selected = matches[0]
    print(json.dumps({"phase": "validated_before_open", "device": selected}, ensure_ascii=False), flush=True)
    if sys.stdin.readline().strip() != "OPEN":
        raise ValueError("Le parent n'a pas attaché le Job Object avant l'ouverture")
    directory = args.directory.resolve()
    if not directory.is_relative_to(ROOT / "logs" / "foresight-runtime" / "qualification"):
        raise ValueError("Qualification hors dossier local autorisé")
    directory.mkdir(parents=True, exist_ok=True)
    rate, channels = int(selected["defaultSampleRate"]), min(2, int(selected["maxInputChannels"]))
    target_frames, frame_bytes = rate * 30, channels * 2
    received, errors, finished = queue.Queue(maxsize=64), [], False
    window = ActiveCaptureWindow(rate)
    stop_lock, stop_watchdog = threading.Lock(), threading.Event()
    watchdog = None
    counters = {"frames": 0, "callbacks": 0, "discarded_final_buffer_frames": 0,
                "discarded_initial_buffer_frames": 0,
                "first_input_adc_time": None, "last_input_adc_end": None,
                "first_callback_received_at": None, "sample_budget_reached_at": None}
    stream = None
    report = {"kind": "explicitly_authorized_real_microphone_30s", "created_at": now(),
        "authorization_label": args.authorized_device_name, "device": selected,
        "device_index": args.device_index, "windows_session_id": devices["session_id"],
        "restricted_process_token": restricted_token(),
        "pyaudiowpatch_version": devices["version"], "channels": channels, "sample_rate": rate,
        "sample_width_bytes": 2, "target_duration_s": 30, "target_frames": target_frames,
        "active_deadline_anchor": "start_monotonic_no_reset", "active_timeout_s": 30,
        "offline_guard": guard, "recording_id": str(uuid.uuid4()), "chunks": [], "passed": False,
        "pause_resume_tested": False, "transcription_performed": False, "external_audio_search": False,
        "source_created": False, "erp_or_brain_accessed": False, "proactive_activation": False}
    report_path = directory / "qualification.json"
    save_json(report_path, report)

    def callback(data, frame_count, timing, status):
        if status:
            errors.append(f"PortAudio callback status={status}")
            return None, audio_api.paAbort
        try:
            first, last = window.accepted_range(timing["input_buffer_adc_time"], frame_count,
                                                counters["frames"])
        except (KeyError, ValueError) as exc:
            errors.append(str(exc))
            return None, audio_api.paAbort
        take = last - first
        if take <= 0:
            return None, audio_api.paComplete if not window.remaining() else audio_api.paContinue
        if counters["first_input_adc_time"] is None:
            counters["first_input_adc_time"] = timing["input_buffer_adc_time"] + first / rate
            counters["first_callback_received_at"] = now()
        try:
            received.put_nowait(data[first * frame_bytes:last * frame_bytes])
        except queue.Full:
            errors.append("File de WAV saturée ; arrêt de la capture")
            return None, audio_api.paAbort
        counters["last_input_adc_end"] = timing["input_buffer_adc_time"] + last / rate
        counters["frames"] += take
        if counters["frames"] == target_frames:
            counters["sample_budget_reached_at"] = now()
        counters["callbacks"] += 1
        counters["discarded_initial_buffer_frames"] += first
        counters["discarded_final_buffer_frames"] += frame_count - last
        complete = counters["frames"] == target_frames or not window.remaining()
        return None, audio_api.paComplete if complete else audio_api.paContinue

    def write_chunk(raw):
        index = len(report["chunks"])
        path = directory / f"mic-raw-{index:04d}.wav"
        if path.exists():
            raise FileExistsError("Fragment de qualification déjà présent")
        temporary = path.with_suffix(".part.wav")
        with wave.open(str(temporary), "wb") as target:
            target.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
            target.writeframes(raw)
        with temporary.open("r+b") as content:
            os.fsync(content.fileno())
        temporary.replace(path)
        frames = len(raw) // frame_bytes
        proof = {"sequence": index, "path": str(path), "frames": frames,
                 "start_frame": sum(item["frames"] for item in report["chunks"]),
                 "duration_s": frames / rate, "channels": channels, "sample_rate": rate,
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size,
                 "durable_at": now()}
        report["chunks"].append(proof)
        save_json(report_path, report)
        print(json.dumps({"phase": "chunk_durable", **proof}, ensure_ascii=False), flush=True)

    pending = bytearray()

    def consume(data):
        pending.extend(data)
        chunk_bytes = rate * 5 * frame_bytes
        while len(pending) >= chunk_bytes:
            write_chunk(bytes(pending[:chunk_bytes]))
            del pending[:chunk_bytes]

    def stop_hardware(reason):
        with stop_lock:
            if report.get("active_stop_requested_at"):
                return
            report["active_stop_requested_at"] = now()
            report["active_stop_reason"] = reason
            report["active_stop_requested_elapsed_s"] = time.monotonic() - window.started
            try:
                if stream.is_active():
                    stream.stop_stream()
                report["active_stream_stopped_at"] = now()
                report["active_stop_completed_elapsed_s"] = time.monotonic() - window.started
            except OSError as exc:
                errors.append(f"Arrêt matériel impossible : {exc}")

    def watchdog_stop():
        if not stop_watchdog.wait(window.remaining()):
            stop_hardware("fixed_30s_start_deadline")

    try:
        with audio_api.PyAudio() as audio:
            actual = audio.get_device_info_by_index(args.device_index)
            host = audio.get_host_api_info_by_type(audio_api.paWASAPI)
            if (actual["hostApi"] != host["index"] or actual["isLoopbackDevice"]
                    or normalized_name(actual["name"]) != normalized_name(args.authorized_device_name)
                    or int(actual["maxInputChannels"]) < channels or int(actual["defaultSampleRate"]) != rate):
                raise ValueError("Le périphérique a changé avant son ouverture ; aucun autre microphone essayé")
            report["open_requested_at"] = now()
            stream = audio.open(format=audio_api.paInt16, channels=channels, rate=rate,
                input=True, input_device_index=args.device_index, frames_per_buffer=rate // 10,
                stream_callback=callback, start=False)
            report["opened_at"] = now()
            save_json(report_path, report)
            print(json.dumps({"phase": "ready", "device_index": args.device_index,
                "opened_at": report["opened_at"]}), flush=True)
            if sys.stdin.readline().strip() != "START":
                raise ValueError("Le parent n'a pas autorisé le début de la fenêtre bornée")
            window.start(stream.get_time())
            started = window.started
            report["start_requested_at"] = now()
            report["adc_window_start"] = window.adc_started
            report["adc_window_end"] = window.adc_started + 30
            watchdog = threading.Thread(target=watchdog_stop, name="mic-30s-active-stop", daemon=True)
            watchdog.start()
            stream.start_stream()
            print(json.dumps({"phase": "recording", "device_index": args.device_index,
                "duration_s": 30, "sample_rate": rate, "channels": channels}), flush=True)
            while sum(item["frames"] for item in report["chunks"]) + len(pending) // frame_bytes < target_frames:
                if errors:
                    raise RuntimeError(errors[0])
                if not window.remaining():
                    # Stop the endpoint first. The five-second grace is solely
                    # for already acquired buffers, WAV fsync and child exit.
                    stop_hardware("fixed_30s_start_deadline")
                    break
                try:
                    data = received.get(timeout=min(.1, window.remaining()))
                except queue.Empty:
                    if not stream.is_active() and counters["frames"] < target_frames:
                        break
                    continue
                consume(data)
            stop_hardware("sample_quota_or_endpoint_stop")
            stop_watchdog.set()
            watchdog.join(timeout=1)
            while True:
                try:
                    consume(received.get_nowait())
                except queue.Empty:
                    break
            finished = counters["frames"] == target_frames
            report["stream_wall_s_until_budget"] = time.monotonic() - started
            stream.close()
            stream = None
            report["stream_closed_at"] = now()
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        stop_watchdog.set()
        if watchdog:
            watchdog.join(timeout=1)
        if stream is not None:
            try:
                if stream.is_active():
                    stream.stop_stream()
            except OSError as exc:
                report["stream_stop_error"] = str(exc)
            finally:
                try:
                    stream.close()
                    report["stream_closed_at"] = now()
                except OSError as exc:
                    report["stream_close_error"] = str(exc)
        if pending:
            write_chunk(bytes(pending))
        report.update(counters)
        report["recorded_frames"] = sum(item["frames"] for item in report["chunks"])
        report["duration_s"] = report["recorded_frames"] / rate
        report["partial_capture"] = report["recorded_frames"] != target_frames
        if report["partial_capture"] and not report.get("error"):
            report["error"] = "Quota incomplet ; le délai matériel reste limité à 30 s sans prolongation"
        report["stream_closed"] = bool(report.get("stream_closed_at"))
        report["pyaudio_terminated"] = True
        report["no_capture_remaining_in_worker"] = not report.get("opened_at") or report["stream_closed"]
        report["passed"] = bool(finished and not errors and report["recorded_frames"] == target_frames
                                and report["stream_closed"])
        save_json(report_path, report)
    print(json.dumps({"phase": "closed", "passed": report["passed"], "duration_s": report["duration_s"],
        "recorded_frames": report["recorded_frames"], "stream_closed": report["stream_closed"],
        "report": str(report_path)}, ensure_ascii=False), flush=True)
    return report["passed"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--device-index", type=int, required=True)
    parser.add_argument("--authorized-device-name", required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--parent-pid", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return 0 if capture(args) else 1
    from app.services.live_speech import _windows_job, runtime_paths
    directory = args.directory.resolve()
    if not directory.is_relative_to(ROOT / "logs" / "foresight-runtime" / "qualification"):
        raise ValueError("Rapport hors dossier local de qualification")
    directory.mkdir(parents=True, exist_ok=False)
    python, _ = runtime_paths()
    stderr_file = (directory / "worker-stderr.log").open("w", encoding="utf-8")
    process = subprocess.Popen([str(python), "-u", str(Path(__file__).resolve()), "--worker",
        "--directory", str(directory), "--device-index", str(args.device_index),
        "--authorized-device-name", args.authorized_device_name, "--parent-pid", str(os.getpid())],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_file,
        text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW,
        env=dict(os.environ, AGENT_QUALIFICATION_OFFLINE="1", PYTHONUTF8="1"))
    job = None
    events = queue.Queue()
    budget = CaptureDeadline()
    controller_error = None
    ready_received_at = None
    try:
        job = _windows_job(process)

        def read_events():
            for line in process.stdout:
                print(line, end="", flush=True)
                try:
                    events.put(json.loads(line))
                except ValueError:
                    continue
            events.put({"phase": "worker_eof"})

        threading.Thread(target=read_events, name="mic-qualification-events", daemon=True).start()
        process.stdin.write("OPEN\n")
        process.stdin.flush()
        while True:
            remaining = budget.remaining()
            if not remaining:
                raise TimeoutError(f"Délai borné du contrôleur dépassé : {budget.phase}")
            try:
                event = events.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError(f"Délai borné du contrôleur dépassé : {budget.phase}") from exc
            if event.get("phase") == "ready":
                budget.on_ready()
                ready_received_at = now()
                process.stdin.write("START\n")
                process.stdin.flush()
            elif event.get("phase") == "closed":
                process.wait(timeout=max(.01, min(5, budget.remaining())))
                break
            elif event.get("phase") == "worker_eof":
                process.wait(timeout=5)
                raise RuntimeError("Le worker s'est arrêté sans fermeture normale confirmée")
        if process.returncode:
            raise RuntimeError("La capture isolée a échoué ; les fragments locaux restent conservés")
    except Exception as exc:
        controller_error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for pipe in (process.stdin, process.stdout):
            if pipe:
                pipe.close()
        if job:
            job[0].CloseHandle(job[1])
        stderr_file.close()
        report_path = directory / "qualification.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report.update(child_pid=process.pid, child_returncode=process.returncode, job_object_closed=bool(job),
                          worker_process_exited=process.poll() is not None, parent_finished_at=now(),
                          controller_open_timeout_s=45, controller_capture_flush_timeout_s=35,
                          controller_deadline_anchor="ready_after_stream_open", ready_received_at=ready_received_at,
                          controller_error=controller_error)
            save_json(report_path, report)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
