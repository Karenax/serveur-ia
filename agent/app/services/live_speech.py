"""Resident local STT, durable session jobs and separate real qualification."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import logging
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid
from sqlalchemy import select, text

from . import audio_capture
from .inference_scheduler import lease
from scripts import speech_runtime

ROOT = Path(__file__).resolve().parents[2]
_stop = threading.Event()
_wake = threading.Event()
_thread = None
_resident = None
_lock = threading.RLock()
_desired_running = False
_closing = 0
_stop_generation = 0
_lifecycle_generation = 0
_metrics = {"processed_chunks": 0, "failed_chunks": 0, "last_compute_s": None}
LOG = logging.getLogger(__name__)


def runtime_paths():
    python = Path(os.environ.get("PB_SPEECH_PYTHON", str(ROOT / ".venv-speech" /
                   ("Scripts/python.exe" if os.name == "nt" else "bin/python"))))
    configured = os.environ.get("PB_SPEECH_MODELS_DIR")
    if configured:
        return python, Path(configured)
    from .speech_acceleration import configured_device
    if 'PB_SPEECH_DEVICE' not in os.environ and configured_device() == 'cuda':
        return python, ROOT / '.models' / 'audio-medium'
    # The current fixed corpus exposes a critical number error with small.
    # Prefer the already-installed medium on CPU; keep explicit overrides and
    # partial installations intact, and never select CUDA implicitly.
    medium = ROOT / ".models" / "audio-medium"
    if os.environ.get("PB_SPEECH_DEVICE", "cpu").strip().lower() == "cpu":
        try:
            config = json.loads((medium / "models.json").read_text(encoding="utf-8"))
            if (config.get("model") == "medium"
                    and all(Path(config[key]).is_file() for key in ("segmentation", "embedding"))
                    and (Path(config["whisper"]) / "model.bin").is_file()):
                return python, medium
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass
    models = ROOT / ".models" / "audio"
    return python, models


def model_fingerprint(models=None):
    """Bind qualification to the actual Whisper binary, not a model label."""
    if models is None:
        _, models = runtime_paths()
    config = json.loads((Path(models) / "models.json").read_text(encoding="utf-8"))
    model = Path(config["whisper"]) / "model.bin"
    digest = hashlib.sha256()
    with model.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def speech_profile(models=None, *, device_override=None):
    if models is None:
        _, models = runtime_paths()
    models = Path(models)
    config = json.loads((models / "models.json").read_text(encoding="utf-8"))
    threads = int(os.environ.get("PB_SPEECH_THREADS", config.get("cpu_threads", 4)))
    if not 1 <= threads <= 16:
        raise ValueError("Nombre de threads STT attendu entre 1 et 16")
    from .speech_acceleration import configured_device, cuda_profile
    selected_device = configured_device() if device_override is None else device_override
    if selected_device not in ("cpu", "cuda"):
        raise ValueError("Calcul audio attendu : cpu ou cuda")
    if selected_device == "cuda":
        return cuda_profile(models)
    return {"runtime": "faster-whisper", "runtime_version": "1.2.1", "model": config["model"],
            "model_directory": str(Path(config["whisper"]).resolve()), "device": "cpu", "compute_type": "int8",
            "cpu_threads": threads, "language": "fr", "beam_size": 5, "word_timestamps": True,
            "vad_filter": True, "min_silence_ms": 250, "previous_text": False, "pcm_context_ms": 500,
            "no_speech_threshold": .6, "compression_ratio_threshold": 2.4, "contract_revision": 2}


def speech_profile_key(models=None, *, device_override=None):
    profile = speech_profile(models) if device_override is None else speech_profile(models, device_override=device_override)
    return hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def runtime_status():
    from .meeting_audio import runtime_status as batch_status
    _, models = runtime_paths()
    status = batch_status(models_dir=models)
    qualification = {}
    configured_report = os.environ.get("PB_SPEECH_QUALIFICATION_REPORT")
    report = Path(configured_report) if configured_report else models / "audio-qualification.json"
    if not configured_report and not report.exists():
        report = ROOT / "logs" / "foresight-runtime" / report.name
    try:
        qualification = json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(qualification, dict):
            qualification = {}
    except (OSError, ValueError):
        pass
    # Cheap current-file identity detects replacement without hashing the large
    # model on every UI poll. The recorded qualification contains its SHA256.
    try:
        config = json.loads((models / "models.json").read_text(encoding="utf-8"))
        binary = Path(config["whisper"]) / "model.bin"
        current_identity = {"size": binary.stat().st_size, "mtime_ns": binary.stat().st_mtime_ns,
                            "config_sha256": hashlib.sha256((models / "models.json").read_bytes()).hexdigest()}
    except (OSError, ValueError, KeyError, TypeError):
        current_identity = None
    profile = None
    try:
        profile = speech_profile(models) if current_identity else None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        status = {**status, "ready": False, "detail": str(exc)}
    runtime_key = speech_profile_key(models) if profile else None
    qualified = bool(profile and qualification.get("passed") and qualification.get("model_sha256")
                     and qualification.get("model_identity") == current_identity
                     and qualification.get("runtime_profile_key") == runtime_key)
    result = {**{key: value for key, value in status.items() if key not in {"python", "models_dir"}},
            "device": profile["device"] if profile else status.get("device", "cpu"),
            "installed": status["ready"], "loaded": bool(profile and _resident and _resident.loaded and current_identity
                and getattr(_resident, "_loaded_profile_key", None) == runtime_key),
            "ready": bool(status["ready"] and qualified),
            "runtime_profile": profile,
            "real_test_passed": qualified,
            "real_test_model": qualification.get("model"),
            "qualified_live_latency": False,
            "industrial_quality_qualified": False,
            "metrics": dict(_metrics), "capture_owned_here": False,
            "worker_running": bool(_thread and _thread.is_alive()), "stop_requested": _stop.is_set(),
            "speech_language": "fr", "speaker_identity": "track label; human review required"}
    from .speech_acceleration import operational_readiness
    return operational_readiness(result, current_identity)


def _windows_job(process):
    """Kill the resident child if Agent exits unexpectedly; no inherited handle."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
                    ("flags", wintypes.DWORD), ("min_working", ctypes.c_size_t),
                    ("max_working", ctypes.c_size_t), ("active", wintypes.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                    ("scheduling", wintypes.DWORD)]

    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in
                    ("reads", "writes", "other", "read_bytes", "write_bytes", "other_bytes")]

    class Extended(ctypes.Structure):
        _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                    ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                    ("peak_job", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateJobObjectW(None, None)
    info = Extended()
    info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)) \
            or not kernel.AssignProcessToJobObject(handle, int(process._handle)):
        if handle:
            kernel.CloseHandle(handle)
        raise OSError("Isolation du sous-processus audio Windows impossible")
    return kernel, handle


class ResidentWhisper:
    def __init__(self, storage_root: Path, *, python=None, models=None, device_override=None):
        if not python or not models:
            default_python, default_models = runtime_paths()
            python, models = python or default_python, models or default_models
        self.python = Path(python)
        self.models = Path(models)
        self.device_override = device_override
        self.storage = storage_root.resolve()
        self.process = None
        self._job = None
        self._reader = None
        self._events = queue.Queue()
        self._request_lock = threading.RLock()
        self._close_lock = threading.RLock()
        self.loaded = False
        self._loaded_profile_key = None
        self.ready_details = None

    @staticmethod
    def _remaining(deadline, cancel=None):
        if cancel is not None and cancel.is_set():
            raise InterruptedError("Transcription locale arrêtée")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Budget de transcription locale dépassé")
        return remaining

    def _next_event(self, deadline, cancel=None):
        while True:
            timeout = min(.2, self._remaining(deadline, cancel))
            try:
                event = self._events.get(timeout=timeout)
            except queue.Empty:
                continue
            self._remaining(deadline, cancel)
            return event

    def start(self, timeout=600, *, cancel=None, deadline=None):
        deadline = min(time.monotonic() + timeout, deadline) if deadline is not None else time.monotonic() + timeout
        self._remaining(deadline, cancel)
        key = (speech_profile_key(self.models) if self.device_override is None else
            speech_profile_key(self.models, device_override=self.device_override))
        self._remaining(deadline, cancel)
        if self.process and self.process.poll() is None and self.loaded and self._loaded_profile_key == key:
            return
        self.close()
        self._events = queue.Queue()
        with self._close_lock:
            self._remaining(deadline, cancel)
            profile = (speech_profile(self.models) if self.device_override is None else
                speech_profile(self.models, device_override=self.device_override))
            command = [str(self.python), "-u", str(ROOT / "scripts" / "transcribe_live.py"),
                       "--models", str(self.models), "--storage", str(self.storage)]
            launch = {}
            if profile["device"] == "cuda":
                command.extend(["--profile-key", key])
                launch["env"] = speech_runtime.child_environment(profile)
            self._remaining(deadline, cancel)
            self.process = subprocess.Popen(command,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                **launch)
            try:
                self._job = _windows_job(self.process)
            except Exception:
                self.close()
                raise
            process, events = self.process, self._events
        try:
            def read_events():
                try:
                    for line in process.stdout:
                        try:
                            events.put(json.loads(line))
                        except ValueError:
                            pass
                except (OSError, ValueError):
                    pass  # A deliberate close can interrupt the stdout reader.
                finally:
                    events.put({"kind": "error", "error": "Sous-processus audio arrêté"})

            self._reader = threading.Thread(target=read_events, name="live-speech-events", daemon=True)
            self._reader.start()
            event = self._next_event(deadline, cancel)
            if event.get("kind") != "ready":
                raise RuntimeError(event.get("error", "Runtime audio non prêt"))
            if profile["device"] == "cuda":
                speech_runtime.validate_cuda_ready(event, profile)
            elif event.get("cpu_threads") != profile["cpu_threads"]:
                raise ValueError("Le worker STT utilise un profil CPU différent")
            self._remaining(deadline, cancel)
            self.loaded = True
            self.ready_details = event
            self._loaded_profile_key = key
        except Exception:
            self.close()
            raise

    def transcribe(self, prepared: audio_capture.PreparedAudio, *, track="mic",
                   keep_from_ms=0, timeout=900, cancel=None):
        deadline = time.monotonic() + timeout
        while not self._request_lock.acquire(timeout=min(.2, self._remaining(deadline, cancel))):
            pass
        try:
            with lease("speech:local-cpu", priority=0, timeout=self._remaining(deadline, cancel), cancel=cancel):
                # Waiting for the lease, loading and response share one budget.
                # SQL/codec calls and termination grace are separate; never
                # report a completed inference after its deadline or cancel.
                try:
                    self.start(timeout=min(600, self._remaining(deadline, cancel)), cancel=cancel, deadline=deadline)
                    self._remaining(deadline, cancel)
                    request_id = uuid.uuid4().hex
                    request = {"op": "transcribe", "request_id": request_id, "path": str(prepared.path),
                               "track": track, "offset_ms": prepared.offset_ms,
                               "clip_start_ms": prepared.clip_start_ms,
                               "clip_end_ms": prepared.clip_end_ms, "keep_from_ms": keep_from_ms}
                    if prepared.context_path is not None:
                        request['context'] = {'path': str(prepared.context_path), 'duration_ms': prepared.context_ms}
                        request['revise_from_ms'] = prepared.offset_ms + prepared.clip_start_ms
                    self.process.stdin.write(json.dumps(request) + "\n")
                    self.process.stdin.flush()
                    event = self._next_event(deadline, cancel)
                    if event.get("kind") != "result" or event.get("request_id") != request_id:
                        raise RuntimeError(event.get("error", "Réponse audio incohérente"))
                    return event
                except Exception:
                    self.close()
                    raise
        finally:
            self._request_lock.release()

    def close(self):
        with self._close_lock:
            self.loaded = False
            self._loaded_profile_key = None
            self.ready_details = None
            process, self.process = self.process, None
            job, self._job = self._job, None
            reader, self._reader = getattr(self, "_reader", None), None
            try:
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
            finally:
                try:
                    if process:
                        for stream in (process.stdin, process.stdout):
                            if stream:
                                stream.close()
                finally:
                    try:
                        if reader and reader is not threading.current_thread():
                            reader.join(timeout=2)
                            if reader.is_alive():
                                raise OSError("Le lecteur du sous-processus STT reste actif")
                    finally:
                        if job:
                            kernel, handle = job
                            if not kernel.CloseHandle(handle):
                                raise OSError("Fermeture du Job STT Windows impossible")


def prepare_direct_chunk(chunk, earlier, *, storage_root, derived_root):
    """Retain codec bootstrap files without adding archived PCM to ASR.

    A cumulative container still needs all preceding codec fragments. Only an
    admitted/completed contiguous previous fragment supplies context. Native
    Opus retains that one fragment (at most five seconds) in memory; legacy
    PCM retains its short overlap. Cumulative containers remain separate.
    """
    value = audio_capture._value
    start = int(value(chunk, "start_ms"))
    previous = next((row for row in earlier if value(row, "session_id") == value(chunk, "session_id")
        and value(row, "track") == value(chunk, "track")
        and int(value(row, "sequence")) == int(value(chunk, "sequence")) - 1), None)
    context = bool(previous is not None and value(previous, "speech_status") in {"pending", "running", "completed"}
        and int(value(previous, "duration_ms")) > 0
        and abs(int(value(previous, "start_ms")) + int(value(previous, "duration_ms")) - start) <= 50)
    prepared = audio_capture.prepare_chunk(chunk, earlier, storage_root=storage_root,
        derived_root=derived_root, with_pcm_context=context)
    if context:
        earliest = (prepared.offset_ms if prepared.context_path is not None else
                    max(0, start - 500, int(value(previous, "start_ms"))))
    else:
        earliest = start
    if prepared.offset_ms + prepared.clip_start_ms < earliest:
        prepared = replace(prepared, clip_start_ms=max(0, earliest - prepared.offset_ms))
    return prepared


def process_chunk(chunk_id: str):
    from .audio_cpu_coordinator import direct_speech, AudioCpuBusy
    from app.db import SessionLocal
    from app.meeting_session_models import MeetingAudioChunk
    from .meeting_sessions import live_transcription_enabled
    with SessionLocal() as db:
        if not live_transcription_enabled(db):
            return False
        chunk = db.get(MeetingAudioChunk, chunk_id)
        if not chunk or chunk.speech_status != "pending":
            return False
    try:
        with direct_speech():
            return _process_chunk(chunk_id)
    except AudioCpuBusy:
        with SessionLocal() as db:
            db.execute(text('UPDATE meeting_session_chunks SET speech_status=speech_status WHERE 0'))
            db.expire_all()
            if not live_transcription_enabled(db) or _stop.is_set():
                db.rollback()
                return False
            chunk = db.get(MeetingAudioChunk, chunk_id)
            if chunk and chunk.speech_status == "pending":
                chunk.speech_error = "Transcription en attente du traitement audio déjà actif"
                db.commit()
        return False


def _revise_context(db, chunk, prepared, result):
    """Revise untouched provisional ASR and retain its exact preimage.

    Human edits increment revision, including edits committed during inference.
    Cardinality changes stay for explicit review; no row or text is deleted.
    """
    from app.meeting_session_models import MeetingAudioChunk, LiveTranscriptSegment, MeetingSession
    from .meeting_sessions import append_event

    replacements = result.get('context_segments')
    if prepared.context_path is None or not isinstance(replacements, list) or not 0 < len(replacements) <= 64:
        return 0
    previous = db.scalar(select(MeetingAudioChunk).where(
        MeetingAudioChunk.session_id == chunk.session_id, MeetingAudioChunk.track == chunk.track,
        MeetingAudioChunk.sequence == chunk.sequence - 1))
    if (previous is None or previous.speech_status != 'completed'
            or Path(previous.storage_path).resolve() != prepared.context_path.resolve()
            or abs(previous.start_ms - prepared.offset_ms) > 2
            or previous.duration_ms != prepared.context_ms):
        return 0
    segments = list(db.scalars(select(LiveTranscriptSegment).where(LiveTranscriptSegment.chunk_id == previous.id)))
    if len(segments) != len(replacements):
        return 0
    ordered = []
    for ordinal, item in enumerate(replacements):
        identity = 'live-' + hashlib.sha256(f'{previous.id}:{ordinal}'.encode()).hexdigest()
        segment = next((row for row in segments if row.id == identity), None)
        if (segment is None or segment.revision != 1 or segment.finalized
                or not isinstance(item, dict) or not isinstance(item.get('text'), str)
                or not item['text'].strip() or len(item['text']) > 10000
                or type(item.get('start_ms')) is not int or type(item.get('end_ms')) is not int
                or not previous.start_ms <= item['start_ms'] < item['end_ms'] <= previous.start_ms + previous.duration_ms):
            return 0
        ordered.append((segment, item))
    before, after = [], []
    for segment, item in ordered:
        if (segment.text, segment.start_ms, segment.end_ms) == (item['text'].strip(), item['start_ms'], item['end_ms']):
            continue
        before.append({'id': segment.id, 'text': segment.text, 'speaker': segment.speaker,
            'revision': segment.revision, 'start_ms': segment.start_ms, 'end_ms': segment.end_ms})
        segment.text, segment.start_ms, segment.end_ms = item['text'].strip(), item['start_ms'], item['end_ms']
        segment.revision += 1
        after.append({'id': segment.id, 'text': segment.text, 'speaker': segment.speaker,
            'revision': segment.revision, 'start_ms': segment.start_ms, 'end_ms': segment.end_ms})
    if before:
        row = db.get(MeetingSession, chunk.session_id)
        append_event(db, row, 'transcript.context-revised', {'chunk_id': previous.id,
            'following_chunk_id': chunk.id, 'before': before, 'after': after, 'provisional': True})
    return len(before)


def _process_chunk(chunk_id: str):
    from .audio_cpu_coordinator import _running_batch
    from app.db import SessionLocal
    from app.config import settings
    from app.meeting_session_models import MeetingAudioChunk, MeetingSession, LiveTranscriptSegment
    from .meeting_sessions import append_event, live_transcription_enabled
    from .speech_admission import eligible_direct, reconcile_queue
    global _resident
    with SessionLocal() as db:
        # The writer lock and fresh setting prevent a queued tick from claiming
        # a chunk after the opt-in was disabled on another connection.
        db.execute(text('UPDATE meeting_session_chunks SET speech_status=speech_status WHERE 0'))
        db.expire_all()
        if not live_transcription_enabled(db) or _stop.is_set():
            db.rollback()
            return False
        if _running_batch(db):
            db.rollback()
            return False  # A durable batch reservation outlives its memory token.
        reconcile_queue(db)
        chunk = db.get(MeetingAudioChunk, chunk_id)
        if not chunk or chunk.speech_status != "pending" or not eligible_direct(chunk):
            db.commit()  # Persist reconciliation without inventing an ASR attempt.
            return False
        session = db.get(MeetingSession, chunk.session_id)
        if not session or session.state == "cancelled":
            db.commit()
            return False
        with _lock:
            if _stop.is_set() or _closing:
                db.rollback()
                return False
            chunk.speech_status, chunk.speech_error = "running", None
            generation = _stop_generation
            db.commit()
        try:
            earlier = db.query(MeetingAudioChunk).filter_by(session_id=chunk.session_id, track=chunk.track).all()
            storage = Path(settings.storage_dir).resolve()
            prepared = prepare_direct_chunk(chunk, earlier, storage_root=storage,
                derived_root=storage / "meeting-sessions" / "derived")
            with _lock:
                if _stop.is_set() or generation != _stop_generation:
                    raise InterruptedError("Transcription directe interrompue ; audio conservé")
                if _resident is None:
                    _resident = ResidentWhisper(storage)
                resident = _resident
            result = resident.transcribe(prepared, track=chunk.track, keep_from_ms=chunk.start_ms, cancel=_stop)
            # A stopped/re-enabled loop must not publish an interrupted result.
            db.execute(text('UPDATE meeting_session_chunks SET speech_status=speech_status WHERE 0'))
            db.expire_all()
            chunk = db.get(MeetingAudioChunk, chunk_id)
            session = db.get(MeetingSession, chunk.session_id)
            if (generation != _stop_generation or _stop.is_set()
                    or not live_transcription_enabled(db, operator_id=session.operator_id)
                    or session.state == 'cancelled'):
                raise InterruptedError("Transcription directe interrompue ; audio conservé")
            context_revised = _revise_context(db, chunk, prepared, result)
            for ordinal, item in enumerate(result["segments"]):
                identity = "live-" + hashlib.sha256(f"{chunk.id}:{ordinal}".encode()).hexdigest()
                if db.get(LiveTranscriptSegment, identity):
                    continue  # Never overwrite a human correction on retries.
                db.add(LiveTranscriptSegment(id=identity, session_id=session.id, chunk_id=chunk.id,
                    track=chunk.track, start_ms=item["start_ms"], end_ms=item["end_ms"],
                    speaker=item["speaker"], text=item["text"], revision=1, finalized=False))
            chunk.speech_status = "completed"
            if not chunk.duration_ms:
                chunk.duration_ms = result["duration_ms"]
            append_event(db, session, "transcript.updated", {"chunk_id": chunk.id,
                "segments": len(result["segments"]), "provisional": True,
                "context_revised_segments": context_revised,
                "compute_s": result["compute_s"]})
            db.commit()
            from . import session_proactive
            session_proactive.wake_worker()
            _metrics.update(processed_chunks=_metrics["processed_chunks"] + 1,
                            last_compute_s=result["compute_s"])
        except Exception as exc:
            db.rollback()
            db.execute(text('UPDATE meeting_session_chunks SET speech_status=speech_status WHERE 0'))
            db.expire_all()
            chunk = db.get(MeetingAudioChunk, chunk_id)
            if not chunk or chunk.speech_status != "running":
                db.rollback()
                return False  # Never repair another admission/terminal decision.
            session = db.get(MeetingSession, chunk.session_id)
            if not session:
                db.rollback()
                return False
            interrupted = _stop.is_set() or generation != _stop_generation or isinstance(exc, InterruptedError)
            chunk.speech_status = "pending" if interrupted else "failed"
            chunk.speech_error = str(exc)[:500] if isinstance(exc, ValueError) else "Transcription locale interrompue ; audio conservé"
            append_event(db, session, "transcript.interrupted" if interrupted else "transcript.failed",
                         {"chunk_id": chunk.id, "error": chunk.speech_error})
            if live_transcription_enabled(db):
                reconcile_queue(db)  # Release only this known completed reservation.
            db.commit()
            _metrics["failed_chunks"] += 1


def wake_worker():
    _wake.set()


def warm_up():
    """Explicit model-only preparation; never opens microphone or loopback."""
    from app.config import settings
    from .audio_cpu_coordinator import direct_speech
    from app.db import SessionLocal
    from .meeting_sessions import require_live_transcription
    with SessionLocal() as db:
        require_live_transcription(db)
    global _resident
    with direct_speech():
        with _lock:
            if _resident is None:
                _resident = ResidentWhisper(Path(settings.storage_dir).resolve())
            resident = _resident
        with resident._request_lock:
            resident.start(cancel=_stop)
        return {"loaded": resident.loaded, "runtime_profile_key": speech_profile_key(resident.models),
                "runtime_profile": speech_profile(resident.models), "model_only": True,
                "live_latency_qualified": False}


def consolidate_session_audio(chunks, chunk_path, *, storage_root=None):
    """Finalize all tracks, preserving originals and their absolute offsets."""
    if storage_root is None:
        from app.config import settings
        storage_root = Path(settings.storage_dir)
    storage = Path(storage_root).resolve()
    rows = sorted(chunks, key=lambda row: (audio_capture._value(row, "track"),
                                         audio_capture._value(row, "sequence")))
    if not rows:
        raise ValueError("La séance ne contient pas de fragments audio")
    derived = storage / "meeting-sessions" / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    inputs = []
    for track in sorted({audio_capture._value(row, "track") for row in rows}):
        group = [row for row in rows if audio_capture._value(row, "track") == track]
        if [audio_capture._value(row, "sequence") for row in group] != list(range(len(group))):
            raise ValueError("Fragments audio manquants ; reprendre la réception avant finalisation")
        for row in group:
            # The supplied owner check and the actual content hash must both pass.
            if Path(chunk_path(row)).resolve() != audio_capture.stored_path(row, storage):
                raise ValueError("Chemin audio incohérent")
        latest = audio_capture.prepare_chunk(group[-1], group, storage_root=storage,
                                            derived_root=derived)
        if latest.assembled:
            inputs.append({"path": str(latest.path), "offset_ms": 0, "track": track})
        else:
            for row in group:
                prepared = audio_capture.prepare_chunk(row, group, storage_root=storage,
                                                       derived_root=derived)
                inputs.append({"path": str(prepared.path), "offset_ms": prepared.offset_ms, "track": track})
    identity = hashlib.sha256("|".join(audio_capture._value(row, "sha256") for row in rows).encode()).hexdigest()
    output = derived / f"{identity}-mixed.ogg"
    manifest = derived / f"{identity}-mix.json"
    manifest.write_text(json.dumps({"inputs": inputs, "output": str(output)}), encoding="utf-8")
    python, _ = runtime_paths()
    try:
        with lease("speech:local-cpu", priority=20, timeout=900):
            result = subprocess.run([str(python), str(ROOT / "scripts" / "mix_session_audio.py"),
                str(manifest), "--storage", str(storage)], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                encoding="utf-8", timeout=600,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if result.returncode or not output.is_file():
            raise ValueError("Mix des pistes audio impossible ; fragments conservés")
        details = json.loads(result.stdout.strip().splitlines()[-1])
        if details.get("duration_ms", 0) <= 0 or output.stat().st_size == 0:
            raise ValueError("Mix audio vide ; fragments conservés")
        return output
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Runtime de mix audio indisponible ; fragments conservés") from exc


def select_candidate(active_id, historical_id):
    """Pure admission policy; no preemption and no claim of bounded backlog."""
    return active_id if active_id is not None else historical_id


def pending_candidate(db):
    from app.meeting_session_models import MeetingAudioChunk, MeetingSession
    query = select(MeetingAudioChunk.id).join(MeetingSession,
        MeetingAudioChunk.session_id == MeetingSession.id).where(
            MeetingAudioChunk.speech_status == 'pending', MeetingSession.state != 'cancelled')
    query = query.order_by(MeetingAudioChunk.created_at, MeetingAudioChunk.sequence, MeetingAudioChunk.id).limit(1)
    active = db.scalar(query.where(MeetingSession.state == 'recording'))
    historical = db.scalar(query.where(MeetingSession.state != 'recording')) if active is None else None
    return select_candidate(active, historical)


def startup_recovery(db, *, expected_generation=None):
    """Reconcile orphan reservations only while no local inference owns CPU.

    The CPU admission guard precedes the SQLite writer lock, as in capture
    admission. It blocks new admissions briefly; no model/lease is opened here.
    Active computations, including an explicit warm-up, defer recovery.
    """
    from . import audio_cpu_coordinator as cpu
    from .meeting_sessions import live_transcription_enabled
    from .speech_admission import reconcile_queue
    with cpu._guard:
        if cpu._direct_jobs or cpu._batch_owner is not None:
            return False
        db.execute(text('UPDATE meeting_session_chunks SET speech_status=speech_status WHERE 0'))
        db.expire_all()
        if not live_transcription_enabled(db):
            db.rollback()
            return False
        with _lock:
            if (_stop.is_set() or _closing or
                    (expected_generation is not None and expected_generation != _lifecycle_generation)):
                db.rollback()
                return False
        reconcile_queue(db, recover_running=True)
        with _lock:
            if (_stop.is_set() or _closing or
                    (expected_generation is not None and expected_generation != _lifecycle_generation)):
                db.rollback()
                return False
            db.commit()
        return True


def start_worker():
    from app.db import SessionLocal
    from .meeting_sessions import live_transcription_enabled
    global _thread, _desired_running, _lifecycle_generation
    with SessionLocal() as db:
        if not live_transcription_enabled(db):
            return False  # No state repair or model startup on legacy/general-only activation.
    with _lock:
        _lifecycle_generation += 1
        _desired_running = True
        if not _closing:
            _stop.clear()
        if _thread and _thread.is_alive():
            _wake.set()
            return True

        def run():
            global _thread
            recover = True
            while True:
                with _lock:
                    observed_generation = _lifecycle_generation
                    closing = bool(_closing)
                    if _stop.is_set() and not closing:
                        if not _desired_running:
                            if _thread is threading.current_thread():
                                _thread = None
                            return
                        _stop.clear()
                        recover = True
                if closing:
                    _wake.wait(.1)
                    _wake.clear()
                    continue
                try:
                    with SessionLocal() as db:
                        if not live_transcription_enabled(db):
                            stop_worker(wait=False, expected_generation=observed_generation)
                            continue
                        if recover:
                            recover = not startup_recovery(db, expected_generation=observed_generation)
                        candidate = pending_candidate(db) if not recover and runtime_status()['installed'] else None
                    if candidate:
                        if process_chunk(candidate) is False:
                            _wake.wait(2)
                            _wake.clear()
                    else:
                        _wake.wait(2)
                        _wake.clear()
                except Exception:
                    # A temporary DB/claim failure must not leave a dead loop
                    # reported as an operational resident. Failed ASR itself
                    # remains failed and requires the explicit retry command.
                    LOG.exception('Live speech worker interrupted; durable chunks retained')
                    _metrics['last_worker_error'] = 'Worker STT interrompu ; fragments conservés'
                    _wake.wait(2)
                    _wake.clear()

        _thread = threading.Thread(target=run, name="live-speech", daemon=True)
        _thread.start()
        return True


def stop_worker(*, wait=True, expected_generation=None):
    global _resident, _desired_running, _closing, _stop_generation, _lifecycle_generation
    with _lock:
        if expected_generation is not None and expected_generation != _lifecycle_generation:
            return {'stop_requested': False, 'worker_running': bool(_thread and _thread.is_alive())}
        _lifecycle_generation += 1
        _desired_running = False
        _stop.set()
        _stop_generation += 1
        _wake.set()
        resident, _resident = _resident, None
        thread = _thread
        if resident:
            _closing += 1
    try:
        if resident:
            resident.close()  # Only the owned STT process, never capture hardware.
    finally:
        with _lock:
            if resident:
                _closing -= 1
            reenabled = _desired_running
            _wake.set()
    if wait and not reenabled and thread and thread is not threading.current_thread():
        thread.join(timeout=5)
    return {'stop_requested': True, 'worker_running': bool(thread and thread.is_alive())}
