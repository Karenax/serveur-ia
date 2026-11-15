"""Interactive Windows WASAPI acquisition; durable Ogg/Opus chunks, no HTTP server."""

import argparse
import ctypes
import errno
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
import traceback
from uuid import uuid4


def emit(**event):
    print(json.dumps(event, ensure_ascii=False), flush=True)


def session_id(pid):
    from ctypes import wintypes

    value = wintypes.DWORD()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(value)):
        raise OSError("Session Windows du processus inconnue")
    return value.value


def inventory():
    import pyaudiowpatch as pyaudio
    from importlib.metadata import version

    with pyaudio.PyAudio() as audio:
        host = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
        devices = [
            {
                key: item[key]
                for key in (
                    "index",
                    "name",
                    "maxInputChannels",
                    "maxOutputChannels",
                    "defaultSampleRate",
                    "isLoopbackDevice",
                )
            }
            for item in audio.get_device_info_generator()
            if item["hostApi"] == host["index"]
        ]
        current_session = session_id(os.getpid())
        return {
            "installed": True,
            "version": version("PyAudioWPatch"),
            "session_id": current_session,
            "interactive_session": current_session > 0,
            "session0_supported": False,
            "default_mic": host["defaultInputDevice"],
            "default_output": host["defaultOutputDevice"],
            "devices": devices,
            "permissions_probed": False,
            "capture_started": False,
        }


def check_stream_health(streams, last_callbacks, *, now, active_since):
    """WASAPI microphone callbacks continue through silence; idle loopback may not."""
    for track, stream in streams.items():
        if not stream.is_active():
            raise ValueError(f"Périphérique audio interrompu : {track}")
        if track == "mic" and now - max(
            last_callbacks.get(track, active_since), active_since
        ) >= 10:
            raise ValueError(
                "Microphone interrompu : aucune donnée reçue depuis 10 secondes"
            )


def close_streams(streams):
    """Close every stream, including devices whose health query now fails."""
    failed = []
    for track, stream in streams.items():
        try:
            # close() also aborts an active stream. Do not depend on a health
            # query or stop_stream() succeeding on an invalidated endpoint.
            stream.close()
        except Exception:
            failed.append(track)
    if failed:
        raise ValueError("Fermeture audio non confirmée : " + ", ".join(failed))


def record_capture_failure(directory, error):
    """Keep technical causes locally without exposing them in the user message."""
    causes, seen = [], set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        causes.append({
            'type': type(error).__name__, 'module': type(error).__module__,
            'errno': getattr(error, 'errno', None), 'winerror': getattr(error, 'winerror', None),
            'message': str(error)[:1000],
            'frames': [{'file': frame.filename, 'line': frame.lineno, 'function': frame.name}
                       for frame in traceback.extract_tb(error.__traceback__)],
        })
        error = error.__cause__ or error.__context__
    path = directory / ('capture-failure-' + uuid4().hex + '.json')
    try:
        with path.open('x', encoding='utf-8') as output:
            json.dump({'kind': 'capture.failure', 'causes': causes}, output, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
    except OSError:
        return None  # Full/unwritable storage must not mask the actual failure.
    return path


def capture(request, *, parent_pid):
    if "qualification" in request:
        # Private, optional fixture policy: ordinary acquisition is unchanged.
        if session_id(os.getpid()) == 0 or session_id(parent_pid) != session_id(
            os.getpid()
        ):
            raise ValueError("Qualification réservée à la session Windows interactive")
        from scripts.native_capture_qualification import capture as qualify

        return qualify(
            request,
            parent_pid=parent_pid,
            emit=emit,
            parent_alive=lambda: _parent_alive(parent_pid),
        )
    from app.operational_limits import CAPTURE_BYTES, CAPTURE_DURATION_MS
    import av
    import numpy as np
    import pyaudiowpatch as pyaudio
    from ctypes import wintypes
    from scripts.windows_audio_endpoints import EndpointMonitor

    if session_id(os.getpid()) == 0 or session_id(parent_pid) != session_id(
        os.getpid()
    ):
        raise ValueError(
            "Capture réservée à la session Windows interactive de l'opérateur"
        )
    storage = Path(request["storage"]).resolve()
    directory = Path(request["directory"]).resolve()
    if not directory.is_relative_to(storage):
        raise ValueError("Capture hors du stockage autorisé")
    directory.mkdir(parents=True, exist_ok=True)
    tracks = request["tracks"]
    if (
        not tracks
        or len(set(tracks)) != len(tracks)
        or any(track not in {"mic", "system"} for track in tracks)
    ):
        raise ValueError("Choix explicite des pistes mic/system requis")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    parent = kernel.OpenProcess(0x00101000, False, parent_pid)
    if not parent:
        raise ValueError("Processus propriétaire inaccessible")
    controls, incoming = queue.Queue(), queue.Queue(maxsize=1024)
    overflow = threading.Event()

    def read_controls():
        for line in sys.stdin:
            try:
                controls.put(json.loads(line) if len(line) <= 4096 else {"op": "stop"})
            except ValueError:
                controls.put({"op": "stop"})
        controls.put({"op": "stop"})

    threading.Thread(target=read_controls, name="native-controls", daemon=True).start()
    started = time.monotonic() - request.get("offset_ms", 0) / 1000
    states, streams = {}, {}
    active = False
    active_since = None
    last_callbacks = {}
    max_bytes = CAPTURE_BYTES
    total_bytes = request.get("total_bytes", 0)

    def callback(track):
        def receive(data, frame_count, _timing, status):
            if status:
                overflow.set()
            stamp = time.monotonic()
            if data and frame_count > 0:
                last_callbacks[track] = stamp
            try:
                incoming.put_nowait((track, data, frame_count, stamp))
            except queue.Full:
                overflow.set()
            return None, pyaudio.paContinue

        return receive

    from scripts.native_chunk_journal import commit_chunk, commit_buffer, drain_buffer

    def write_chunk(track, raw, start_ms):
        duration_ms = len(raw) // 32
        if start_ms + duration_ms > CAPTURE_DURATION_MS or total_bytes >= max_bytes:
            raise ValueError(
                "Limite de capture de 12 heures ou 512 Mio atteinte"
            )
        return commit_chunk(
            directory,
            request["session_id"],
            track,
            states[track]["sequence"],
            raw,
            start_ms,
            codec="opus",
        )

    def flush_buffer(track, amount):
        nonlocal total_bytes
        packet = commit_buffer(
            states[track], track, amount, write_chunk, lambda value: emit(**value)
        )
        total_bytes += packet["size_bytes"]

    def consume(item):
        track, data, frame_count, stamp = item
        state = states[track]
        channels, rate = state["channels"], state["rate"]
        frame = av.AudioFrame.from_ndarray(
            np.frombuffer(data, dtype=np.int16).reshape(1, -1),
            format="s16",
            layout="stereo" if channels == 2 else "mono",
        )
        frame.sample_rate = rate
        if state["start_ms"] is None:
            state["start_ms"] = max(
                0, round((stamp - started - frame_count / rate) * 1000)
            )
        for converted in state["resampler"].resample(frame):
            state["buffer"].extend(converted.to_ndarray().tobytes())
        while len(state["buffer"]) >= 160000:
            flush_buffer(track, 160000)

    def drain():
        while True:
            try:
                consume(incoming.get_nowait())
            except queue.Empty:
                break
        for track, state in states.items():
            for converted in state["resampler"].resample(None):
                state["buffer"].extend(converted.to_ndarray().tobytes())
            drain_buffer(state, lambda amount: flush_buffer(track, amount))
            state["buffer"].clear()
            state["start_ms"] = None
            state["resampler"] = av.AudioResampler(
                format="s16", layout="mono", rate=16000
            )

    try:
        with pyaudio.PyAudio() as audio, EndpointMonitor() as endpoints:
            try:
                host = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
                for track in tracks:
                    selected = request.get("devices", {}).get(track)
                    device = (
                        audio.get_device_info_by_index(selected)
                        if selected is not None
                        else audio.get_default_wasapi_loopback()
                        if track == "system"
                        else audio.get_device_info_by_index(host["defaultInputDevice"])
                    )
                    if (
                        device["hostApi"] != host["index"]
                        or not device["maxInputChannels"]
                        or bool(device["isLoopbackDevice"]) != (track == "system")
                    ):
                        raise ValueError(
                            "Périphérique WASAPI incompatible avec la piste choisie"
                        )
                    endpoints.bind(track, device["name"])
                    channels, rate = (
                        min(2, int(device["maxInputChannels"])),
                        int(device["defaultSampleRate"]),
                    )
                    states[track] = {
                        "channels": channels,
                        "rate": rate,
                        "buffer": bytearray(),
                        "start_ms": None,
                        "sequence": request.get("sequences", {}).get(track, 0),
                        "resampler": av.AudioResampler(
                            format="s16", layout="mono", rate=16000
                        ),
                    }
                    streams[track] = audio.open(
                        format=pyaudio.paInt16,
                        channels=channels,
                        rate=rate,
                        input=True,
                        input_device_index=device["index"],
                        frames_per_buffer=2048,
                        stream_callback=callback(track),
                        start=False,
                    )
                emit(
                    kind="ready",
                    tracks=tracks,
                    session_id=session_id(os.getpid()),
                    permissions_probed=True,
                    selected_devices={
                        track: {"rate": state["rate"], "channels": state["channels"]}
                        for track, state in states.items()
                    },
                )
                while True:
                    if kernel.WaitForSingleObject(parent, 0) != 258:
                        break
                    if overflow.is_set():
                        raise ValueError(
                            "Discontinuité ou débordement audio ; capture interrompue"
                        )
                    if (time.monotonic() - started) * 1000 >= CAPTURE_DURATION_MS:
                        raise ValueError("Limite de durée de capture atteinte")
                    try:
                        control = controls.get_nowait()
                    except queue.Empty:
                        control = None
                    if control:
                        op = control.get("op")
                        if op in {"start", "resume"} and not active:
                            active_since = time.monotonic()
                            endpoints.check(active_since, force=True)
                            for stream in streams.values():
                                stream.start_stream()
                            active = True
                            emit(kind="state", state="recording")
                        elif op in {"pause", "stop"}:
                            if active:
                                for stream in streams.values():
                                    stream.stop_stream()
                                drain()
                            active = False
                            emit(
                                kind="state", state="stopped" if op == "stop" else "paused"
                            )
                            if op == "stop":
                                break
                    if active:
                        endpoints.check(time.monotonic())
                        check_stream_health(
                            streams, last_callbacks, now=time.monotonic(),
                            active_since=active_since,
                        )
                        try:
                            consume(incoming.get(timeout=0.05))
                        except queue.Empty:
                            pass
                    else:
                        time.sleep(0.05)
            except Exception:
                # Stop callbacks before consuming their remaining queue and
                # resampler tail. Durable chunk notifications precede the
                # terminal error; an interruption never becomes a normal stop.
                try:
                    close_streams(streams)
                finally:
                    streams.clear()
                drain()
                raise
            finally:
                close_streams(streams)
                streams.clear()
    except Exception as error:
        record_capture_failure(directory, error)
        raise
    finally:
        kernel.CloseHandle(parent)


def _parent_alive(pid):
    """Owned parent's exact handle only; never enumerate or terminate processes."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000, False, pid)
    if not handle:
        return False
    try:
        return kernel.WaitForSingleObject(handle, 0) == 258
    finally:
        kernel.CloseHandle(handle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--parent-pid", type=int)
    args = parser.parse_args()
    if os.name != "nt":
        raise ValueError("WASAPI disponible uniquement sur Windows")
    if args.inventory:
        emit(**inventory())
    elif args.request and args.parent_pid:
        capture(
            json.loads(args.request.read_text(encoding="utf-8")),
            parent_pid=args.parent_pid,
        )
    else:
        raise ValueError("Commande native de capture incomplète")


def cli_main():
    """Report storage exhaustion distinctly from device/permission failures."""
    try:
        main()
    except Exception as exc:
        if isinstance(exc, OSError) and (
            exc.errno == errno.ENOSPC or getattr(exc, "winerror", None) in (39, 112)
        ):
            detail = (
                "Stockage audio saturé : capture interrompue. "
                "Les fragments déjà acquittés sont conservés. "
                "Libérez de l’espace avant de reprendre la capture."
            )
        else:
            detail = str(exc) if isinstance(exc, ValueError) else (
                "Périphérique audio inaccessible, permission Windows refusée ou runtime arrêté"
            )
        emit(
            kind="error",
            error=detail,
        )
        return 1
    return 0


if __name__ == "__main__":
    # Direct script launch must also resolve the optional repository module.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(cli_main())
