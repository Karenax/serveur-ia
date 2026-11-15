"""Prepared local microphone qualification: one opening <=45s, 30s PCM data.

Never invoked during preparation. --approved-data-window attests a NEW human
authorization, including discarded startup audio. No application, database,
STT, LLM, browser or system-output imports. The old 30s harness stays intact.
"""

from __future__ import annotations

import argparse
from array import array
import ast
import ctypes
from ctypes import wintypes
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
from scripts.qualify_microphone_30s import normalized_name, now, save_json  # noqa: E402

RATE, CHANNELS, WIDTH = 48000, 2, 2
BUFFER_FRAMES = RATE // 10
TARGET_FRAMES = RATE * 30
MAX_OPEN_SECONDS, STARTUP_SECONDS, FLUSH_SECONDS = 45, 10, 5
ADC_TOLERANCE_SECONDS = 0.002  # Diagnostic threshold; not physical loss evidence.
QUALIFICATION_SCHEMA = "bounded-pcm-quota-and-timing-v2"
QUALIFICATION_SCOPE = "30s PCM quota, bounded opening and owned cleanup only"
JOB_CLASS_SHA256 = "cbf4ff3dc2788d942cf42fd55667d69554152f6569481f34a3d36264d01f6ea0"


def emit(phase, **fields):
    print(json.dumps({"phase": phase, **fields}, ensure_ascii=False), flush=True)


def exclusive_json(path, value):
    """Publish a complete receipt atomically, without replacing any proof."""
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as target:
            json.dump(value, target, ensure_ascii=False)
            target.flush()
            os.fsync(target.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_report(path, value):
    """Replace only this fresh run's mutable report, never an older artifact."""
    temporary = path.with_name(f".{path.name}.pending")
    save_json(temporary, value)
    os.replace(temporary, path)


def worker_passed(report):
    """Qualify only the current PCM/closure schema, never physical continuity."""
    delta = report.get("adc_nominal_span_difference_s")
    closed = report.get("hardware_closed_monotonic")
    deadline = report.get("physical_deadline_monotonic")
    opened = report.get("open_monotonic")
    return bool(
        report.get("qualification_schema") == QUALIFICATION_SCHEMA
        and report.get("qualification_scope") == QUALIFICATION_SCOPE
        and report.get("physical_continuity_qualified") is False
        and report.get("physical_continuity_status") == "unknown"
        and not report.get("error")
        and not report.get("hardware_close_error")
        and report.get("physical_limit_passed") is True
        and report.get("stream_closed") is True
        and report.get("pyaudio_terminated") is True
        and report.get("accepted_frames")
        == report.get("recorded_frames")
        == TARGET_FRAMES
        and type(delta) in (int, float)
        and math.isfinite(delta)
        and type(closed) in (int, float)
        and type(deadline) in (int, float)
        and type(opened) in (int, float)
        and math.isfinite(closed)
        and math.isfinite(deadline)
        and math.isfinite(opened)
        and deadline == opened + MAX_OPEN_SECONDS
        and opened <= closed <= deadline
    )


def stopped_flush_deadline(receipt, token, physical_deadline):
    """Only a timely confirmed closure permits a separate inactive flush budget."""
    closed = receipt.get("closed_monotonic")
    if (
        physical_deadline is None
        or receipt.get("token") != token
        or receipt.get("physical_limit_passed") is not True
        or type(closed) not in (int, float)
        or not math.isfinite(closed)
        or not physical_deadline - MAX_OPEN_SECONDS <= closed <= physical_deadline
    ):
        raise ValueError("Arrêt matériel hors borne ou non attesté")
    return closed + FLUSH_SECONDS


def controller_deadline(bootstrap, physical, flush, data_started):
    """A blocked OPEN/START still has a parent-side ten-second startup limit."""
    if flush is not None:
        return flush
    if physical is None:
        return bootstrap
    return (
        physical
        if data_started
        else min(physical, physical - MAX_OPEN_SECONDS + STARTUP_SECONDS)
    )


def close_audio_handles(stream, audio):
    """Attempt every owned handle cleanup even when a previous call fails."""
    receipt = {"stream_closed": stream is None, "pyaudio_terminated": audio is None}
    errors = []
    if stream is not None:
        try:
            if stream.is_active():
                stream.stop_stream()
        except Exception as exc:
            errors.append(f"stop_stream: {type(exc).__name__}: {exc}")
        try:
            stream.close()
            receipt["stream_closed"] = True
        except Exception as exc:
            errors.append(f"stream.close: {type(exc).__name__}: {exc}")
    if audio is not None:
        try:
            audio.terminate()
            receipt["pyaudio_terminated"] = True
        except Exception as exc:
            errors.append(f"PyAudio.terminate: {type(exc).__name__}: {exc}")
    receipt["errors"] = errors
    return receipt


def checked_options(args):
    """Pure admission guard; called before runtime imports/process creation."""
    if not args.approved_data_window:
        raise PermissionError(
            "Nouvelle autorisation explicite --approved-data-window requise"
        )
    if (
        not args.authorization_reference.strip()
        or len(args.authorization_reference) > 200
    ):
        raise ValueError("Référence de la nouvelle autorisation humaine requise")
    if not args.authorized_device_name.strip() or args.device_index < 0:
        raise ValueError(
            "Nom exact et index frais explicites requis ; aucun périphérique par défaut"
        )
    directory = args.directory.resolve()
    if not directory.is_relative_to(ROOT / "logs/foresight-runtime/qualification"):
        raise ValueError("Répertoire hors qualification locale")
    return directory


def select_device(inventory, index, name):
    """A unique name first, then its index; never disambiguate by index alone."""
    if not inventory["interactive_session"] or not inventory["session_id"]:
        raise ValueError("Session Windows interactive requise")
    matches = [
        d
        for d in inventory["devices"]
        if normalized_name(d["name"]) == normalized_name(name)
        and d["maxInputChannels"] > 0
        and not d["isLoopbackDevice"]
    ]
    if len(matches) != 1:
        raise ValueError("Microphone exact absent ou nom ambigu ; aucune ouverture")
    device = matches[0]
    if (
        device["index"] != index
        or device["defaultSampleRate"] != RATE
        or device["maxInputChannels"] < CHANNELS
    ):
        raise ValueError("Index/format changé ; uniquement PCM16 stéréo48kHz préparé")
    return device


class DataWindow:
    """One immutable OPEN budget; warmup excluded, quota defined in PCM frames."""

    def __init__(self, opened_monotonic, clock=time.monotonic):
        if not math.isfinite(opened_monotonic) or opened_monotonic < 0:
            raise ValueError("Ancrage monotone OPEN invalide")
        self.clock, self.opened = clock, opened_monotonic
        self.deadline = opened_monotonic + MAX_OPEN_SECONDS
        self.startup_deadline = opened_monotonic + STARTUP_SECONDS
        self.previous_adc_end = None
        self.good_callbacks = self.warmup_frames = self.frames = 0
        self.data_adc_start = self.data_adc_end = None
        self.stable_at = self.first_data_at = None
        self.error = self.stop_reason = None
        self.callbacks = []
        self.timing_anomalies = []
        self.lock = threading.RLock()

    def fail(self, reason):
        with self.lock:
            self.error = self.error or reason
            self.stop_reason = self.stop_reason or "error"

    def expired(self):
        with self.lock:
            if self.clock() >= self.deadline:
                self.stop_reason = self.stop_reason or "fixed_open_deadline"
            elif self.first_data_at is None and self.clock() >= self.startup_deadline:
                self.fail("Stabilisation et premier buffer de données absents dans10s")
            return self.stop_reason is not None

    def accept(self, adc, frames, status=0):
        with self.lock:
            arrived = self.clock()
            if self.stop_reason or self.expired():
                return 0, True
            if status or frames != BUFFER_FRAMES or not math.isfinite(adc):
                self.callbacks.append(
                    {
                        "sequence": len(self.callbacks),
                        "received_monotonic": arrived,
                        "adc_start": adc if math.isfinite(adc) else repr(adc),
                        "frames": frames,
                        "status": status,
                        "accepted_frames": 0,
                        "phase": "rejected_invalid",
                    }
                )
                self.fail("Statut/format/horodatage callback invalide")
                return 0, True
            delta = (
                None if self.previous_adc_end is None else adc - self.previous_adc_end
            )
            coherent = delta is None or abs(delta) <= ADC_TOLERANCE_SECONDS
            record = {
                "sequence": len(self.callbacks),
                "received_monotonic": arrived,
                "adc_start": adc,
                "adc_end": adc + frames / RATE,
                "frames": frames,
                "status": status,
                "adc_delta_s": delta,
                "timestamp_coherent": coherent,
                "accepted_frames": 0,
                "phase": "stabilization",
            }
            if delta is not None and adc <= self.previous_adc_end - frames / RATE:
                record["phase"] = "rejected_nonmonotone"
                self.callbacks.append(record)
                self.fail("Horodatage ADC non monotone")
                return 0, True
            self.previous_adc_end = adc + frames / RATE
            if self.stable_at is None:
                self.good_callbacks = self.good_callbacks + 1 if coherent else 1
                self.warmup_frames += frames
                if self.good_callbacks >= 5:
                    self.stable_at = arrived
                self.callbacks.append(record)
                return 0, False
            if not coherent:
                self.timing_anomalies.append(
                    {
                        "sequence": record["sequence"],
                        "adc_delta_s": delta,
                        "received_monotonic": arrived,
                        "physical_loss_proven": False,
                        "physical_continuity_qualified": False,
                    }
                )
            if self.data_adc_start is None:
                self.data_adc_start, self.first_data_at = adc, arrived
            take = min(frames, TARGET_FRAMES - self.frames)
            self.frames += take
            self.data_adc_end = adc + take / RATE
            record.update(
                phase="data" if coherent else "data_timing_anomaly", accepted_frames=take
            )
            self.callbacks.append(record)
            if self.frames == TARGET_FRAMES:
                self.stop_reason = "data_quota_reached"
            return take, self.stop_reason is not None

    def snapshot(self):
        with self.lock:
            span = (
                None
                if self.data_adc_start is None
                else self.data_adc_end - self.data_adc_start
            )
            span_delta = None if span is None else span - self.frames / RATE
            timestamp_coherent = bool(
                self.frames
                and not self.timing_anomalies
                and not any(
                    r["phase"].startswith("rejected") for r in self.callbacks
                )
                and math.isfinite(span_delta)
                and abs(span_delta) <= ADC_TOLERANCE_SECONDS
            )
            return {
                "qualification_schema": QUALIFICATION_SCHEMA,
                "qualification_scope": QUALIFICATION_SCOPE,
                "open_monotonic": self.opened,
                "physical_deadline_monotonic": self.deadline,
                "startup_deadline_monotonic": self.startup_deadline,
                "stability_confirmed_monotonic": self.stable_at,
                "first_data_monotonic": self.first_data_at,
                "warmup_frames_discarded": self.warmup_frames,
                "accepted_frames": self.frames,
                "data_adc_start": self.data_adc_start,
                "data_adc_end": self.data_adc_end,
                "data_adc_span_s": span,
                "data_nominal_seconds": self.frames / RATE,
                "adc_nominal_span_difference_s": span_delta,
                "timing_diagnostic_threshold_seconds": ADC_TOLERANCE_SECONDS,
                "timestamp_coherence_passed": timestamp_coherent,
                "timing_anomaly_count": len(self.timing_anomalies),
                "timing_anomalies": list(self.timing_anomalies),
                "physical_continuity_qualified": False,
                "physical_continuity_status": "unknown",
                "continuity_note": "Les horodatages ne certifient pas la continuité physique ; aucun silence ajouté.",
                "error": self.error,
                "stop_reason": self.stop_reason,
                "callbacks": list(self.callbacks),
            }


def replay_callback_metadata(report):
    """Pure decision replay; no PCM read, device, process or hardware claim."""
    clock_value = [report["open_monotonic"]]
    window = DataWindow(clock_value[0], lambda: clock_value[0])
    processed = 0
    for callback in report["callbacks"]:
        arrival = callback["received_monotonic"]
        if type(arrival) not in (int, float) or not math.isfinite(arrival):
            raise ValueError("Horodatage de réception invalide dans les métadonnées")
        if arrival < clock_value[0]:
            raise ValueError("Réception non monotone dans les métadonnées")
        clock_value[0] = arrival
        _, stopped = window.accept(
            callback["adc_start"], callback["frames"], callback["status"]
        )
        processed += 1
        if stopped:
            break
    return {
        "mode": "metadata_decision_replay_only",
        "hardware_opened": False,
        "wav_decoded": False,
        "recorded_audio_changed": False,
        "original_passed": report.get("passed"),
        "original_recorded_frames": report.get("recorded_frames"),
        "observed_callbacks": len(report["callbacks"]),
        "processed_callbacks": processed,
        "hypothetical_decisions": window.snapshot(),
        "warning": "Un compteur de métadonnées ne crée aucun PCM et ne requalifie pas l'essai d'origine.",
    }


class WavParts:
    """Bounded chunks, each acknowledgement follows file fsync and SHA."""

    def __init__(self, directory):
        self.directory, self.pending, self.parts = directory, bytearray(), []

    def consume(self, raw):
        if len(raw) % (CHANNELS * WIDTH):
            raise ValueError("PCM tronqué")
        self.pending.extend(raw)
        chunk_bytes = RATE * 5 * CHANNELS * WIDTH
        while len(self.pending) >= chunk_bytes:
            data = bytes(self.pending[:chunk_bytes])
            del self.pending[:chunk_bytes]
            self.write(data)

    def write(self, data):
        path = self.directory / f"mic-data-{len(self.parts):04d}.wav"
        if path.exists():
            raise FileExistsError("Ne jamais remplacer une preuve WAV")
        with wave.open(str(path), "wb") as target:
            target.setnchannels(CHANNELS)
            target.setsampwidth(WIDTH)
            target.setframerate(RATE)
            target.writeframes(data)
        with path.open("rb+") as target:
            target.flush()
            os.fsync(target.fileno())
        frames = len(data) // (CHANNELS * WIDTH)
        self.parts.append(
            {
                "sequence": len(self.parts),
                "path": str(path),
                "frames": frames,
                "start_frame": sum(p["frames"] for p in self.parts),
                "duration_s": frames / RATE,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
                "fsync_ack_at": now(),
            }
        )

    def finish(self):
        if self.pending:
            self.write(bytes(self.pending))
            self.pending.clear()


def audit_wavs(directory, parts):
    total, squares, peaks, clips, checks = 0, [0, 0], [0, 0], [0, 0], []
    for sequence, part in enumerate(parts):
        path = Path(part["path"]).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError("WAV hors qualification")
        with wave.open(str(path), "rb") as wav:
            fmt = (
                wav.getnchannels(),
                wav.getsampwidth(),
                wav.getframerate(),
                wav.getcomptype(),
            )
            frames = wav.getnframes()
            samples = array("h", wav.readframes(frames))
        if sys.byteorder != "little":
            samples.byteswap()
        exact = (
            fmt == (CHANNELS, WIDTH, RATE, "NONE")
            and part["sequence"] == sequence
            and part["start_frame"] == total
            and part["frames"] == frames
            and path.stat().st_size
            == part["size_bytes"]
            == 44 + frames * CHANNELS * WIDTH
            and hashlib.sha256(path.read_bytes()).hexdigest() == part["sha256"]
        )
        checks.append(exact)
        total += frames
        for channel in range(CHANNELS):
            values = samples[channel::CHANNELS]
            squares[channel] += sum(x * x for x in values)
            peaks[channel] = max(
                peaks[channel], max((abs(x) for x in values), default=0)
            )
            clips[channel] += sum(x in (-32768, 32767) for x in values)
    return {
        "all_sha_size_format_offsets_exact": bool(checks) and all(checks),
        "recorded_frames": total,
        "duration_s": total / RATE,
        "quota_30s_passed": total == TARGET_FRAMES,
        "rms_per_channel": [math.sqrt(x / total) if total else 0 for x in squares],
        "peaks_per_channel": peaks,
        "clipped_samples_per_channel": clips,
        "audio_listened_or_transcribed": False,
    }


def owned_child_class():
    """Reuse only the reviewed Job class, not the network controller module."""
    import msvcrt

    source = (ROOT / ".ui-preview/pilots/offline_physical_qualification.py").read_text(
        encoding="utf-8-sig"
    )
    node = next(
        n
        for n in ast.parse(source).body
        if isinstance(n, ast.ClassDef) and n.name == "OwnedChild"
    )
    fragment = ast.get_source_segment(source, node)
    if hashlib.sha256(fragment.encode("utf-8")).hexdigest() != JOB_CLASS_SHA256:
        raise ValueError("Helper Job modifié ; nouvelle revue requise avant capture")
    namespace = {
        "ctypes": ctypes,
        "wintypes": wintypes,
        "msvcrt": msvcrt,
        "os": os,
        "subprocess": subprocess,
        "time": time,
        "now": now,
    }
    exec(compile(fragment, "reviewed-OwnedChild-only", "exec"), namespace)
    return namespace["OwnedChild"]


def worker(args, directory):
    from scripts.native_audio_capture import inventory, session_id
    from scripts.offline_guard import verify
    import pyaudiowpatch as api

    guard = verify()
    if not guard["enabled"] or not guard["probe_blocked"]:
        raise ValueError("Garde Python indisponible")
    metadata = inventory()
    device = select_device(metadata, args.device_index, args.authorized_device_name)
    if session_id(args.parent_pid) != metadata["session_id"]:
        raise ValueError("Session du propriétaire différente")
    report = {
        "kind": "newly_authorized_45s_open_30s_data",
        "qualification_schema": QUALIFICATION_SCHEMA,
        "qualification_scope": QUALIFICATION_SCOPE,
        "physical_continuity_qualified": False,
        "physical_continuity_status": "unknown",
        "created_at": now(),
        "passed": False,
        "authorization_reference": args.authorization_reference,
        "approval_attested_by_operator": True,
        "device": device,
        "windows_session_id": metadata["session_id"],
        "offline_guard": guard,
        "sample_rate": RATE,
        "channels": CHANNELS,
        "sample_width_bytes": WIDTH,
        "target_frames": TARGET_FRAMES,
        "max_open_seconds": MAX_OPEN_SECONDS,
        "adc_tolerance_seconds": ADC_TOLERANCE_SECONDS,
        "parts": [],
        "stream_closed": False,
        "pyaudio_terminated": False,
        "transcription_performed": False,
        "audio_listened": False,
        "database_accessed": False,
        "system_output_captured": False,
        "retry_or_device_fallback": False,
    }
    save_report(directory / "qualification.json", report)
    emit("validated_before_open", device=device)
    open_path = directory / "OPEN.json"
    while not open_path.exists():
        time.sleep(0.02)
    command = json.loads(open_path.read_text(encoding="utf-8"))
    if (
        command["token"] != args.run_token
        or command["parent_pid"] != args.parent_pid
        or command["deadline_monotonic"] != command["open_monotonic"] + MAX_OPEN_SECONDS
    ):
        raise ValueError("Commande OPEN non conforme ; aucune ouverture")
    window = DataWindow(command["open_monotonic"])
    if window.expired():
        raise TimeoutError("Budget OPEN consommé avant acquisition")
    received, done, cancel_watchdog = (
        queue.Queue(maxsize=64),
        threading.Event(),
        threading.Event(),
    )
    hardware_lock = threading.RLock()
    audio = stream = None
    parts = WavParts(directory)
    saved_part_count = 0
    announced_data = False

    def callback(raw, frames, timing, status):
        try:
            if len(raw) != frames * CHANNELS * WIDTH:
                raise ValueError("Taille PCM callback incohérente")
            take, stop = window.accept(timing["input_buffer_adc_time"], frames, status)
            if take:
                received.put_nowait(raw[: take * CHANNELS * WIDTH])
            if stop:
                done.set()
            return None, api.paComplete if stop else api.paContinue
        except Exception as exc:
            with window.lock:
                window.fail(f"Callback : {type(exc).__name__}: {exc}")
            done.set()
            return None, api.paAbort

    def close_hardware(reason):
        nonlocal stream, audio
        with hardware_lock:
            if report.get("close_requested_monotonic") is not None:
                return
            report.update(
                close_reason=reason,
                close_requested_monotonic=time.monotonic(),
                close_requested_at=now(),
            )
            try:
                receipt = close_audio_handles(stream, audio)
                report.update(
                    stream_closed=receipt["stream_closed"],
                    pyaudio_terminated=receipt["pyaudio_terminated"],
                )
                if receipt["stream_closed"]:
                    stream = None
                if receipt["pyaudio_terminated"]:
                    audio = None
                if receipt["errors"]:
                    report["hardware_close_error"] = "; ".join(receipt["errors"])
                    window.fail(report["hardware_close_error"])
                if not receipt["stream_closed"] or not receipt["pyaudio_terminated"]:
                    raise RuntimeError("Handles audio non fermés ; arrêt Job requis")
                report.update(
                    hardware_closed_monotonic=time.monotonic(), hardware_closed_at=now()
                )
                report["physical_open_seconds_upper_bound"] = (
                    report["hardware_closed_monotonic"] - window.opened
                )
                report["physical_limit_passed"] = (
                    report["hardware_closed_monotonic"] <= window.deadline
                )
                exclusive_json(
                    directory / "STOPPED.json",
                    {
                        "token": args.run_token,
                        "closed_monotonic": report["hardware_closed_monotonic"],
                        "physical_limit_passed": report["physical_limit_passed"],
                    },
                )
                emit(
                    "hardware_closed",
                    seconds=report["physical_open_seconds_upper_bound"],
                )
            except Exception as exc:
                with window.lock:
                    window.fail(f"Fermeture matérielle non attestée : {exc}")
                report["hardware_close_error"] = str(exc)
            finally:
                done.set()

    def watchdog():
        # Early request reserves250ms for scheduling/API; parent still kills at45s.
        if not cancel_watchdog.wait(max(0, window.deadline - time.monotonic() - 0.25)):
            close_hardware("fixed_45s_budget_preemptive_stop")

    def flush_pending():
        if not report["stream_closed"] or not report["pyaudio_terminated"]:
            raise RuntimeError("Vidage interdit avant fermeture matérielle confirmée")
        flush_deadline = report["hardware_closed_monotonic"] + FLUSH_SECONDS
        while not received.empty():
            if time.monotonic() >= flush_deadline:
                raise TimeoutError(
                    "Vidage local dépassé après fermeture ; aucun micro ouvert"
                )
            parts.consume(received.get_nowait())
        if parts.pending:
            if time.monotonic() >= flush_deadline:
                raise TimeoutError(
                    "Fsync non commencé hors délai ; données partielles conservées"
                )
            parts.finish()
        if time.monotonic() >= flush_deadline:
            raise TimeoutError("Fsync dépassé ; qualification refusée")

    guard_thread = threading.Thread(
        target=watchdog, name="mic-data-window-45s", daemon=True
    )
    guard_thread.start()
    try:
        with hardware_lock:
            if report.get("close_requested_monotonic") is not None or window.expired():
                raise TimeoutError("Délai matériel expiré avant ouverture")
            audio = api.PyAudio()
            actual = audio.get_device_info_by_index(args.device_index)
            host = audio.get_host_api_info_by_type(api.paWASAPI)
            if (
                actual["hostApi"] != host["index"]
                or actual["isLoopbackDevice"]
                or normalized_name(actual["name"])
                != normalized_name(args.authorized_device_name)
                or actual["maxInputChannels"] < CHANNELS
                or actual["defaultSampleRate"] != RATE
            ):
                raise ValueError("Identité/format changé juste avant ouverture")
            report["open_requested_at"] = now()
            stream = audio.open(
                format=api.paInt16,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=args.device_index,
                frames_per_buffer=BUFFER_FRAMES,
                stream_callback=callback,
                start=False,
            )
            report["opened_at"] = now()
            emit("ready", device_index=args.device_index)
            stream.start_stream()
            report["start_requested_at"] = now()
            emit("stabilizing")
        while not done.is_set():
            if window.expired():
                break
            if window.first_data_at is not None and not announced_data:
                announced_data = True
                emit("data_recording", first_data_monotonic=window.first_data_at)
            try:
                parts.consume(received.get(timeout=0.02))
                if len(parts.parts) != saved_part_count:
                    saved_part_count = len(parts.parts)
                    report.update(window.snapshot(), parts=list(parts.parts))
                    save_report(directory / "qualification.json", report)
                    emit("durable_part", sequence=saved_part_count - 1)
            except queue.Empty:
                continue
        close_hardware(window.stop_reason or "worker_stop")
        if not report.get("physical_limit_passed"):
            raise RuntimeError(
                "Borne physique45s ou fermeture non confirmée ; qualification refusée"
            )
        flush_pending()
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        close_hardware("finally")
        cancel_watchdog.set()
        guard_thread.join(timeout=0.1)
        execution_error = report.get("error")
        if (received.qsize() or parts.pending) and report.get(
            "hardware_closed_monotonic"
        ) is not None:
            try:
                flush_pending()
            except Exception as exc:
                execution_error = execution_error or f"{type(exc).__name__}: {exc}"
        report.update(window.snapshot(), parts=parts.parts, finished_at=now())
        report["error"] = execution_error or window.error
        report["recorded_frames"] = sum(p["frames"] for p in parts.parts)
        report["partial_capture"] = report["recorded_frames"] != TARGET_FRAMES
        report["passed"] = worker_passed(report)
        report["pcm_quota_qualified"] = report["passed"]
        save_report(directory / "qualification.json", report)
        emit("closed", passed=report["passed"], frames=report["recorded_frames"])
    return report["passed"]


def controller(args, directory):
    directory.mkdir(parents=True, exist_ok=False)
    run_token = uuid.uuid4().hex
    report = {
        "created_at": now(),
        "qualification_schema": QUALIFICATION_SCHEMA,
        "qualification_scope": QUALIFICATION_SCOPE,
        "physical_continuity_qualified": False,
        "physical_continuity_status": "unknown",
        "passed": False,
        "recording_executed": False,
        "authorization_reference": args.authorization_reference,
        "shutdown": None,
        "limit": "45s request/deadline, not an OS real-time guarantee; any unconfirmed/late closure fails",
    }
    child = None
    cancel_hard_stop, hard_stop_fired = threading.Event(), threading.Event()
    job_lock = threading.RLock()
    hard_stop_thread = None
    try:
        python = ROOT / ".venv-speech/Scripts/python.exe"
        if not python.is_file():
            raise FileNotFoundError("Runtime audio isolé absent")
        command = [
            str(python),
            "-u",
            str(Path(__file__).resolve()),
            "--worker",
            "--approved-data-window",
            "--authorization-reference",
            args.authorization_reference,
            "--directory",
            str(directory),
            "--device-index",
            str(args.device_index),
            "--authorized-device-name",
            args.authorized_device_name,
            "--parent-pid",
            str(os.getpid()),
            "--run-token",
            run_token,
        ]
        scratch = directory / "scratch"
        scratch.mkdir()
        environment = dict(
            os.environ,
            AGENT_QUALIFICATION_OFFLINE="1",
            PYTHONUTF8="1",
            PB_DATABASE_URL=f"sqlite:///{(scratch / 'unused.db').as_posix()}",
            PB_STORAGE_DIR=str(scratch),
            MINIPILOT_HOME=str(scratch),
            TEMP=str(scratch),
            TMP=str(scratch),
        )
        owner = owned_child_class()
        stdout = directory / "worker.stdout.jsonl"
        child = owner(
            command, ROOT, environment, stdout, directory / "worker.stderr.log"
        )
        report["child_pid"] = child.pid
        bootstrap_deadline = time.monotonic() + 20
        physical_deadline = flush_deadline = None
        data_started = False
        seen = 0
        while True:
            current = time.monotonic()
            if current >= controller_deadline(
                bootstrap_deadline, physical_deadline, flush_deadline, data_started
            ):
                child.stop()
                raise TimeoutError(
                    "Limite contrôleur atteinte ; arrêt du seul Job propriétaire"
                )
            lines = (
                stdout.read_text(encoding="utf-8", errors="replace").splitlines()
                if stdout.exists()
                else []
            )
            for line in lines[seen:]:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    break
                seen += 1
                print(line, flush=True)
                if event.get("phase") == "validated_before_open":
                    if physical_deadline is not None:
                        raise RuntimeError(
                            "Validation répétée ; budget non renouvelable"
                        )
                    opened = time.monotonic()
                    physical_deadline = opened + MAX_OPEN_SECONDS
                    report["open_command_monotonic"] = opened
                    report["physical_deadline_monotonic"] = physical_deadline
                    report["recording_executed"] = (
                        None  # Unknown until a child START event.
                    )

                    def hard_stop(deadline=physical_deadline):
                        if not cancel_hard_stop.wait(
                            max(0, deadline - time.monotonic())
                        ):
                            hard_stop_fired.set()
                            report["parent_hard_stop_requested_monotonic"] = (
                                time.monotonic()
                            )
                            try:
                                with job_lock:
                                    child.stop()
                            except OSError as exc:
                                report["parent_hard_stop_error"] = str(exc)

                    hard_stop_thread = threading.Thread(
                        target=hard_stop, name="owned-mic-45s-stop", daemon=True
                    )
                    hard_stop_thread.start()
                    exclusive_json(
                        directory / "OPEN.json",
                        {
                            "token": run_token,
                            "parent_pid": os.getpid(),
                            "open_monotonic": opened,
                            "deadline_monotonic": physical_deadline,
                        },
                    )
                elif event.get("phase") == "stabilizing":
                    report["recording_executed"] = True
                elif event.get("phase") == "data_recording":
                    started = event.get("first_data_monotonic")
                    if (
                        physical_deadline is None
                        or type(started) not in (int, float)
                        or not (
                            physical_deadline - MAX_OPEN_SECONDS
                            <= started
                            < physical_deadline - MAX_OPEN_SECONDS + STARTUP_SECONDS
                        )
                    ):
                        raise ValueError(
                            "Premier buffer hors délai de démarrage ; pas de renouvellement"
                        )
                    data_started = True
                    report["first_data_monotonic"] = started
            stopped = directory / "STOPPED.json"
            if stopped.exists() and flush_deadline is None:
                receipt = json.loads(stopped.read_text(encoding="utf-8"))
                flush_deadline = stopped_flush_deadline(
                    receipt, run_token, physical_deadline
                )
                cancel_hard_stop.set()
                report["hardware_shutdown_receipt"] = receipt
            code = child.exit_code()
            if code is not None:
                report["child_exit_code"] = code
                if code:
                    raise RuntimeError(
                        "Capture partielle/échouée ; aucune nouvelle ouverture"
                    )
                break
            time.sleep(0.01)
        raw = json.loads((directory / "qualification.json").read_text(encoding="utf-8"))
        report["passed"] = raw.get("passed") is True and worker_passed(raw)
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        if getattr(exc, "owned_cleanup", None):
            report["shutdown"] = exc.owned_cleanup
    finally:
        cancel_hard_stop.set()
        if hard_stop_thread is not None:
            hard_stop_thread.join(timeout=0.1)
        if child is not None:
            with job_lock:
                report["shutdown"] = child.close()
            if not report["shutdown"]["shutdown_confirmed"]:
                report["passed"] = False
        if hard_stop_fired.is_set():
            report["passed"] = False
        raw_path = directory / "qualification.json"
        if raw_path.is_file():
            try:
                before = hashlib.sha256(raw_path.read_bytes()).hexdigest()
                raw = json.loads(raw_path.read_text(encoding="utf-8"))
                if raw.get("start_requested_at") or raw.get("accepted_frames", 0) > 0:
                    report["recording_executed"] = True
                audit = audit_wavs(directory, raw["parts"])
                after = hashlib.sha256(raw_path.read_bytes()).hexdigest()
                audit.update(
                    raw_report_sha256_before=before,
                    raw_report_sha256_after=after,
                    raw_report_unchanged=before == after,
                    owned_shutdown=report["shutdown"],
                    qualification_scope=QUALIFICATION_SCOPE,
                    physical_continuity_qualified=False,
                    physical_continuity_status="unknown",
                    timestamp_coherence_passed=raw.get("timestamp_coherence_passed"),
                    timing_anomaly_count=raw.get("timing_anomaly_count"),
                )
                exclusive_json(directory / "postmortem.json", audit)
                report["passed"] = bool(
                    report["passed"]
                    and audit["quota_30s_passed"]
                    and audit["all_sha_size_format_offsets_exact"]
                    and audit["raw_report_unchanged"]
                )
                report["timestamp_coherence_passed"] = raw.get(
                    "timestamp_coherence_passed"
                )
                report["timing_anomaly_count"] = raw.get("timing_anomaly_count")
            except Exception as exc:
                report.update(passed=False, audit_error=f"{type(exc).__name__}: {exc}")
        report["parent_hard_stop_fired"] = hard_stop_fired.is_set()
        report["pcm_quota_qualified"] = report["passed"]
        report["finished_at"] = now()
        save_report(directory / "controller.json", report)
    return report["passed"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-data-window", action="store_true")
    parser.add_argument("--authorization-reference", default="")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--device-index", type=int, required=True)
    parser.add_argument("--authorized-device-name", required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--parent-pid", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--run-token", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    directory = checked_options(args)
    if os.name != "nt":
        parser.error("Windows interactif uniquement")
    if args.worker:
        if not args.parent_pid or not args.run_token:
            parser.error("Worker réservé au contrôleur propriétaire")
        return 0 if worker(args, directory) else 1
    return 0 if controller(args, directory) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
