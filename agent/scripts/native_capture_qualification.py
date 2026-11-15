"""Opt-in integrated WASAPI qualification. Importing this module opens nothing.

The ordinary native helper delegates here only with a private fixture policy.
Acquisition is bounded in RAM; resampling and durable session packets happen
after owned hardware closure. No microphone authorization is granted by code.
"""

from __future__ import annotations

from array import array
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import threading
import time
import uuid
import wave

from scripts.qualify_microphone_data_window import (
    BUFFER_FRAMES,
    CHANNELS,
    DataWindow,
    MAX_OPEN_SECONDS,
    RATE,
    TARGET_FRAMES,
    exclusive_json,
)

SCHEMA = "integrated-jabra-capture-v1"
MIC_NAME = OUTPUT_NAME = "Casque (Jabra Evolve 75)"
LOOPBACK_NAME = "Casque (Jabra Evolve 75) [Loopback]"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def validate_policy(policy, *, storage=None, sid=None):
    if policy.get("schema") != SCHEMA or policy.get("approved") is not True:
        raise PermissionError("Politique intégrée et nouvel accord explicite requis")
    uuid.UUID(policy["token"])
    uuid.UUID(policy["session_id"])
    if not str(policy.get("authorization_reference", "")).strip():
        raise PermissionError("Référence de nouvel accord humain absente")
    if sid is not None and policy["session_id"] != sid:
        raise PermissionError("Séance différente de l'unique séance autorisée")
    if policy.get("names") != {
        "mic": MIC_NAME,
        "output": OUTPUT_NAME,
        "system": LOOPBACK_NAME,
    }:
        raise ValueError("Identités Jabra exactes requises")
    devices = policy.get("devices", {})
    if set(devices) != {"mic", "system", "output"} or any(
        type(v) is not int or v < 0 for v in devices.values()
    ):
        raise ValueError("Trois indices explicites, sans périphérique par défaut")
    if len(set(devices.values())) != 3:
        raise ValueError("Indices microphone, sortie et loopback distincts requis")
    if policy.get("stimulus") not in {True, False}:
        raise ValueError("Choix explicite de stimulus synthétique requis")
    root = Path(policy["fixture_root"]).resolve()
    proof = Path(policy["proof_dir"]).resolve()
    if not proof.is_relative_to(root) or proof == root:
        raise ValueError("Preuves hors fixture")
    if storage is not None and not Path(storage).resolve().is_relative_to(root):
        raise ValueError("Stockage hors fixture")
    return proof


def exact_devices(audio, pyaudio, policy):
    """Enumerate all WASAPI identities; index-only and substring matches fail."""
    host = audio.get_host_api_info_by_type(pyaudio.paWASAPI)["index"]
    devices = list(audio.get_device_info_generator())
    resolved = {}
    for track, name in policy["names"].items():
        matches = [
            d
            for d in devices
            if d.get("hostApi") == host
            and d.get("name") == name
            and bool(d.get("isLoopbackDevice")) == (track == "system")
            and (
                int(d.get("maxOutputChannels", 0)) == 2
                if track == "output"
                else int(d.get("maxInputChannels", 0)) == 2
            )
        ]
        if len(matches) != 1:
            raise ValueError(f"Identité {track} absente ou ambiguë")
        device = matches[0]
        if (
            device["index"] != policy["devices"][track]
            or device["defaultSampleRate"] != RATE
        ):
            raise ValueError(f"Index ou format {track} changé ; ouverture refusée")
        resolved[track] = dict(device)
    return resolved


def check_armed(policy, parent_pid):
    proof = validate_policy(policy)
    armed = json.loads((proof / "armed.json").read_text(encoding="utf-8"))
    if (
        armed.get("token") != policy["token"]
        or armed.get("backend_pid") != parent_pid
        or armed.get("owned_job_attached") is not True
    ):
        raise PermissionError("Watchdog externe et Job propriétaire non attestés")
    return proof


class SyntheticStimulus:
    """Fictitious two-tone PCM, only <=30s; no file, default output or voice."""

    def __init__(self):
        self.frames = 0
        self.digest = hashlib.sha256()
        self.started = self.closed = None

    def packet(self, frames):
        if type(frames) is not int or frames != BUFFER_FRAMES:
            raise ValueError("Taille de callback sortie invalide")
        take = min(frames, TARGET_FRAMES - self.frames)
        pcm = array("h")
        for index in range(self.frames, self.frames + take):
            frequency = 440 if (index // RATE) % 2 == 0 else 880
            value = round(1200 * math.sin(2 * math.pi * frequency * index / RATE))
            pcm.extend((value, value))
        raw = pcm.tobytes()
        self.digest.update(raw)
        self.frames += take
        # PortAudio requires a full final output callback, zero tail is bounded
        # by the frame budget too: target30s is divisible by buffer4800.
        return raw, self.frames >= TARGET_FRAMES


class CaptureBuffers:
    def __init__(self, opened, clock=time.monotonic):
        self.clock = clock
        self.windows = {track: DataWindow(opened, clock) for track in ("mic", "system")}
        self.raw = {track: bytearray() for track in self.windows}
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.reason = None
        self.error = None

    def fail(self, message):
        with self.lock:
            self.error = self.error or message
            self.reason = self.reason or "error"
            self.stop.set()

    def receive(self, track, data, frames, timing, status):
        with self.lock:
            if self.stop.is_set():
                return True
            if (
                type(frames) is not int
                or frames <= 0
                or not isinstance(data, bytes)
                or len(data) != frames * CHANNELS * 2
            ):
                self.fail("Taille PCM native incohérente")
                return True
            try:
                adc = float(timing["input_buffer_adc_time"])
            except (KeyError, TypeError, ValueError):
                self.fail("Horodatage ADC absent")
                return True
            window = self.windows[track]
            take, done = window.accept(adc, frames, status)
            if take:
                self.raw[track].extend(data[: take * CHANNELS * 2])
            if window.error:
                self.fail(window.error)
            elif all(item.frames == TARGET_FRAMES for item in self.windows.values()):
                self.reason = "data_quotas_reached"
                self.stop.set()
            return done

    def check_deadline(self):
        with self.lock:
            for window in self.windows.values():
                if window.frames != TARGET_FRAMES and window.expired():
                    self.fail(
                        window.error or "Borne OPEN45 atteinte ; données partielles"
                    )
            return self.stop.is_set()


def close_handles(streams, audio):
    receipt = {"streams_closed": {}, "pyaudio_terminated": audio is None, "errors": []}
    for track, stream in list(streams.items()):
        receipt["streams_closed"][track] = False
        try:
            if stream.is_active():
                stream.stop_stream()
        except Exception as exc:
            receipt["errors"].append(f"stop {track}: {type(exc).__name__}: {exc}")
        try:
            stream.close()
            receipt["streams_closed"][track] = True
        except Exception as exc:
            receipt["errors"].append(f"close {track}: {type(exc).__name__}: {exc}")
    if audio is not None:
        try:
            audio.terminate()
            receipt["pyaudio_terminated"] = True
        except Exception as exc:
            receipt["errors"].append(f"terminate: {type(exc).__name__}: {exc}")
    return receipt


def persist_converted(request, buffers, closed, *, emit, clock=time.monotonic):
    """Only after closure: genuine PyAV conversion and existing packet contract."""
    import av
    import numpy as np

    directory = Path(request["directory"]).resolve()
    storage = Path(request["storage"]).resolve()
    if not directory.is_relative_to(storage):
        raise ValueError("Fragment hors stockage fixture")
    deadline = closed + 5
    result = []
    for track in ("mic", "system"):
        window = buffers.windows[track]
        raw = buffers.raw[track]
        if not raw:
            continue
        frame = av.AudioFrame.from_ndarray(
            np.frombuffer(raw, dtype=np.int16).reshape(1, -1),
            format="s16",
            layout="stereo",
        )
        frame.sample_rate = RATE
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        converted = bytearray()
        for item in [*resampler.resample(frame), *resampler.resample(None)]:
            converted.extend(item.to_ndarray().tobytes())
        if len(converted) % 2 or len(converted) // 2 > min(
            480000, window.frames // 3 + 1
        ):
            raise ValueError("Quota dérivé PCM dépassé ; aucun silence ajouté")
        offset = max(
            0,
            round((window.first_data_at - window.opened - BUFFER_FRAMES / RATE) * 1000),
        )
        for sequence, start in enumerate(range(0, len(converted), 160000)):
            if clock() > deadline:
                raise ValueError(
                    "Flush inactif au-delà de5s ; fragments partiels conservés"
                )
            pcm = bytes(converted[start : start + 160000])
            path = directory / f"{track}-{sequence:08d}.wav"
            if path.exists():
                raise ValueError("Fragment déjà présent ; aucun remplacement")
            temporary = path.with_suffix(".part.wav")
            with wave.open(str(temporary), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                output.writeframes(pcm)
            with temporary.open("r+b") as output:
                os.fsync(output.fileno())
            temporary.replace(path)
            content = path.read_bytes()
            fingerprint = hashlib.sha256(content).hexdigest()
            packet = {
                "kind": "chunk",
                "session_id": request["session_id"],
                "track": track,
                "sequence": sequence,
                "path": str(path),
                "sha256": fingerprint,
                "size_bytes": len(content),
                "start_ms": offset + start // 32,
                "duration_ms": len(pcm) // 32,
                "command_id": str(
                    uuid.uuid5(
                        uuid.UUID(request["session_id"]),
                        f"{track}:{sequence}:{fingerprint}",
                    )
                ),
            }
            exclusive_json(path.with_suffix(".json"), packet)
            result.append(packet)
            emit(**packet)
    if clock() > deadline:
        raise ValueError("Flush/ACK après la borne inactive5s")
    return result


def capture(
    request,
    *,
    parent_pid,
    emit,
    audio_module=None,
    clock=time.monotonic,
    controls=None,
    parent_alive=None,
):
    """Real optional helper path; dependencies injectable only for pure tests."""
    policy = request["qualification"]
    proof = check_armed(policy, parent_pid)
    validate_policy(policy, storage=request["storage"], sid=request["session_id"])
    if set(request["tracks"]) != {"mic", "system"} or request["devices"] != {
        k: policy["devices"][k] for k in ("mic", "system")
    }:
        raise PermissionError("Pistes et identités différentes de l'accord intégré")
    if (
        request.get("offset_ms")
        or request.get("total_bytes")
        or any(request["sequences"].values())
    ):
        raise PermissionError("Qualification réservée à une séance native neuve")
    if audio_module is None:
        import pyaudiowpatch as audio_module
    if controls is None:
        import sys

        controls = queue.Queue()

        def read_controls():
            for line in sys.stdin:
                try:
                    controls.put(
                        json.loads(line) if len(line) < 4096 else {"op": "stop"}
                    )
                except ValueError:
                    controls.put({"op": "stop"})
            controls.put({"op": "stop"})

        threading.Thread(
            target=read_controls, daemon=True, name="qualification-controls"
        ).start()
    audio, streams, buffers = None, {}, None
    hardware_lock = threading.RLock()
    watchdog = None
    opened = None
    closed = None
    close_receipt = None
    output_close = None
    error = None
    stimulus = SyntheticStimulus() if policy["stimulus"] else None
    try:
        # Metadata only before the private OPEN, never audio.open.
        audio = audio_module.PyAudio()
        selected = exact_devices(audio, audio_module, policy)
        emit(
            kind="qualification.armed", token=policy["token"], selected_devices=selected
        )
        bootstrap = clock() + 10
        while True:
            if clock() >= bootstrap or (parent_alive and not parent_alive()):
                raise ValueError("OPEN privé absent dans10s")
            try:
                command = controls.get(timeout=0.02)
            except queue.Empty:
                continue
            if command != {
                "op": "qualification.open",
                "token": policy["token"],
                "job_attached": True,
            }:
                raise PermissionError("OPEN privé après attachement au Job requis")
            break
        opened = clock()
        exclusive_json(
            proof / "open.json",
            {
                "schema": SCHEMA,
                "token": policy["token"],
                "session_id": request["session_id"],
                "backend_pid": parent_pid,
                "helper_pid": os.getpid(),
                "open_monotonic": opened,
                "deadline_monotonic": opened + MAX_OPEN_SECONDS,
                "open_utc": utc_now(),
                "selected_devices": selected,
            },
        )
        buffers = CaptureBuffers(opened, clock)

        def receive(track):
            def callback(data, frames, timing, status):
                try:
                    done = buffers.receive(track, data, frames, timing, status)
                except Exception as exc:
                    buffers.fail(f"Callback rejeté : {type(exc).__name__}")
                    done = True
                return (
                    None,
                    audio_module.paComplete if done else audio_module.paContinue,
                )

            return callback

        for track in ("mic", "system"):
            if clock() >= opened + 10:
                raise ValueError(
                    "Ouverture des deux pistes hors budget de démarrage10s"
                )
            exact_devices(
                audio, audio_module, policy
            )  # Revalidate immediately before each OPEN.
            streams[track] = audio.open(
                format=audio_module.paInt16,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=selected[track]["index"],
                frames_per_buffer=BUFFER_FRAMES,
                stream_callback=receive(track),
                start=False,
            )
        if stimulus:

            def output_callback(_data, frames, _timing, status):
                if status or buffers.stop.is_set() or clock() >= opened + 44.75:
                    if status:
                        buffers.fail("Statut sortie synthétique invalide")
                    return b"", audio_module.paComplete
                try:
                    raw, done = stimulus.packet(frames)
                except Exception:
                    buffers.fail("Callback sortie synthétique invalide")
                    return b"", audio_module.paComplete
                return raw, audio_module.paComplete if done else audio_module.paContinue

            exact_devices(audio, audio_module, policy)
            streams["output"] = audio.open(
                format=audio_module.paInt16,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                output_device_index=selected["output"]["index"],
                frames_per_buffer=BUFFER_FRAMES,
                stream_callback=output_callback,
                start=False,
            )

        # This guard does no DB, stdout or flush, so their blocking cannot hold hardware.
        def publish_output_closed():
            if stimulus is None or stimulus.started is None:
                return
            exclusive_json(
                proof / "output-stopped.json",
                {
                    "schema": SCHEMA,
                    "token": policy["token"],
                    "backend_pid": parent_pid,
                    "session_id": request["session_id"],
                    "stimulus_started_monotonic": stimulus.started,
                    "stimulus_closed_monotonic": stimulus.closed,
                    "closed_utc": utc_now(),
                    **(output_close or close_receipt),
                },
            )

        def guard():
            nonlocal close_receipt, closed, output_close
            while not buffers.stop.wait(0.005):
                if (
                    stimulus
                    and stimulus.started is not None
                    and stimulus.closed is None
                    and clock() >= stimulus.started + 29.75
                ):
                    with hardware_lock:
                        output_close = close_handles(
                            {"output": streams.pop("output")}, None
                        )
                        stimulus.closed = clock()
                    publish_output_closed()
                    if (
                        output_close["errors"]
                        or stimulus.closed > stimulus.started + 30
                    ):
                        buffers.fail(
                            "Fermeture sortie synthétique tardive ou en erreur"
                        )
                if parent_alive and not parent_alive():
                    buffers.fail("Processus propriétaire terminé")
                elif clock() >= opened + 44.75:
                    buffers.fail("Borne physique préventive44,75s")
                else:
                    buffers.check_deadline()
            with hardware_lock:
                close_receipt = close_handles(streams, audio)
            closed = clock()
            if stimulus:
                if stimulus.closed is None:
                    stimulus.closed = closed
                    publish_output_closed()
                if output_close:
                    close_receipt["streams_closed"].update(
                        output_close["streams_closed"]
                    )
                    close_receipt["errors"].extend(output_close["errors"])
                if (
                    stimulus.started is not None
                    and stimulus.closed > stimulus.started + 30
                ):
                    close_receipt["errors"].append("Sortie synthétique au-delà de30s")
            exclusive_json(
                proof / "stopped.json",
                {
                    "schema": SCHEMA,
                    "token": policy["token"],
                    "session_id": request["session_id"],
                    "closed_monotonic": closed,
                    "closed_utc": utc_now(),
                    "physical_limit_passed": closed <= opened + MAX_OPEN_SECONDS,
                    "stimulus_started_monotonic": stimulus.started
                    if stimulus
                    else None,
                    "stimulus_closed_monotonic": stimulus.closed if stimulus else None,
                    **close_receipt,
                },
            )

        watchdog = threading.Thread(
            target=guard, name="qualification-hardware-stop", daemon=True
        )
        watchdog.start()
        emit(
            kind="ready",
            tracks=request["tracks"],
            permissions_probed=True,
            selected_devices=selected,
            qualification_schema=SCHEMA,
        )
        active = False
        while not buffers.stop.is_set():
            try:
                command = controls.get(timeout=0.02)
            except queue.Empty:
                continue
            op = command.get("op")
            if op in {"start", "resume"} and not active:
                with hardware_lock:
                    if buffers.stop.is_set() or buffers.check_deadline():
                        break
                    for track, stream in list(streams.items()):
                        if buffers.stop.is_set():
                            break
                        if track == "output" and stimulus.started is None:
                            stimulus.started = clock()  # Before START, never renewed.
                            # The external watchdog reads this immutable receipt,
                            # independently of hardware_lock and start_stream().
                            exclusive_json(
                                proof / "output-start.json",
                                {
                                    "schema": SCHEMA,
                                    "token": policy["token"],
                                    "backend_pid": parent_pid,
                                    "session_id": request["session_id"],
                                    "open_monotonic": opened,
                                    "stimulus_started_monotonic": stimulus.started,
                                    "deadline_monotonic": stimulus.started + 30,
                                    "start_utc": utc_now(),
                                },
                            )
                        stream.start_stream()
                active = True
                emit(kind="state", state="recording")
            elif op == "pause":
                with hardware_lock:
                    if not buffers.stop.is_set():
                        for stream in streams.values():
                            if stream.is_active():
                                stream.stop_stream()
                active = False
                emit(kind="state", state="paused")
            elif op == "stop":
                buffers.reason = buffers.reason or "operator_stop"
                buffers.stop.set()
        watchdog.join(max(0.01, opened + MAX_OPEN_SECONDS - clock()))
        if close_receipt is None or closed is None:
            raise ValueError(
                "Fermeture matérielle non confirmée ; watchdog externe requis"
            )
        if close_receipt["errors"] or closed > opened + MAX_OPEN_SECONDS:
            raise ValueError("Fermeture matérielle en erreur ou tardive")
        packets = persist_converted(request, buffers, closed, emit=emit, clock=clock)
        error = buffers.error
        exclusive_json(
            proof / "complete.json",
            {
                "schema": SCHEMA,
                "token": policy["token"],
                "session_id": request["session_id"],
                "passed": not error
                and all(w.frames == TARGET_FRAMES for w in buffers.windows.values()),
                "error": error,
                "tracks": {k: w.snapshot() for k, w in buffers.windows.items()},
                "chunks": packets,
                "stimulus_frames": stimulus.frames if stimulus else 0,
                "stimulus_started_monotonic": stimulus.started if stimulus else None,
                "stimulus_closed_monotonic": stimulus.closed if stimulus else None,
                "stimulus_sha256": stimulus.digest.hexdigest() if stimulus else None,
                "physical_continuity_qualified": False,
                "physical_continuity_status": "unknown",
            },
        )
        emit(kind="state", state="stopped")
        if error:
            emit(kind="error", error=error)
    except BaseException as exc:
        error = f"{type(exc).__name__}: {exc}"
        if not (proof / "failed.json").exists():
            exclusive_json(
                proof / "failed.json",
                {
                    "schema": SCHEMA,
                    "token": policy["token"],
                    "error": error,
                    "hardware_open_started": opened is not None,
                    "failed_utc": utc_now(),
                },
            )
        raise
    finally:
        if buffers is not None:
            buffers.stop.set()
        if watchdog is None:
            cleanup = close_handles(streams, audio)
            if opened is not None and not (proof / "stopped.json").exists():
                exclusive_json(
                    proof / "stopped.json",
                    {
                        "schema": SCHEMA,
                        "token": policy["token"],
                        "session_id": request["session_id"],
                        "closed_monotonic": clock(),
                        "closed_utc": utc_now(),
                        "physical_limit_passed": clock() <= opened + MAX_OPEN_SECONDS,
                        **cleanup,
                    },
                )
        elif watchdog.is_alive():
            watchdog.join(max(0.01, opened + MAX_OPEN_SECONDS - clock()))
