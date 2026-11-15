"""Owned interactive WASAPI helper, feeding the existing durable session service."""

from __future__ import annotations

from contextvars import copy_context
import errno
import hashlib
import json
import os
from pathlib import Path
import queue
import sqlite3
import subprocess
import threading
import time

from fastapi import HTTPException

from .live_speech import ROOT, _windows_job, runtime_paths

_lock = threading.RLock()
_captures = {}
_inventory = {}
_inventory_time = 0
_qualification = None  # Private fixture configuration, never an HTTP field.


def _capture_failure_detail(exc):
    """Describe storage failure without leaking SQL, file paths or payloads."""
    original = getattr(exc, "orig", exc)
    code = getattr(original, "sqlite_errorcode", None)
    if (
        isinstance(original, sqlite3.Error)
        and isinstance(code, int)
        and code & 0xFF == sqlite3.SQLITE_FULL
    ):
        return (
            "Stockage de la base saturé : capture interrompue. "
            "Les fragments natifs restent conservés ; "
            "libérez de l’espace avant de les synchroniser."
        )
    if (
        isinstance(original, OSError)
        and (
            original.errno == errno.ENOSPC
            or getattr(original, "winerror", None) in {39, 112}
        )
    ) or (isinstance(original, HTTPException) and original.status_code == 507):
        return (
            "Stockage audio saturé : capture interrompue. "
            "Les fragments natifs restent conservés ; "
            "libérez de l’espace avant de les synchroniser."
        )
    if isinstance(exc, ValueError):
        return str(exc)
    return "Capture interrompue ; fragments natifs conservés et rejouables"


def configure_qualification(policy, native_python):
    """Explicit preparation entry point; canonical processes cannot opt in."""
    global _qualification, runtime_paths
    from scripts.native_capture_qualification import validate_policy

    root = os.environ.get("AGENT_INTEGRATED_CAPTURE_FIXTURE_ROOT")
    if (
        os.environ.get("AGENT_TESTING") != "1"
        or not root
        or Path(root).resolve() != Path(policy["fixture_root"]).resolve()
    ):
        raise PermissionError("Qualification réservée à une nouvelle fixture isolée")
    from app.config import settings
    from sqlalchemy.engine import make_url
    from backend.app.db import DB_PATH

    fixture = Path(root).resolve()
    canonical_logs = (ROOT / "logs" / "foresight-runtime").resolve()
    if (
        not fixture.is_relative_to(canonical_logs)
        or not fixture.name.startswith("integrated-jabra-fixture-")
        or not Path(make_url(settings.database_url).database)
        .resolve()
        .is_relative_to(fixture)
        or not Path(DB_PATH).resolve().is_relative_to(fixture)
    ):
        raise PermissionError(
            "Brain et ERP ne sont pas tous deux dans la nouvelle fixture dédiée"
        )
    proof = validate_policy(policy, storage=settings.storage_dir)
    python = Path(native_python).resolve()
    if not python.is_file():
        raise ValueError("Runtime WASAPI local absent")
    with _lock:
        if (
            _qualification is not None
            or (proof / "consumed.json").exists()
            or _captures
        ):
            raise PermissionError("Accord de qualification déjà configuré ou consommé")
        _qualification = json.loads(json.dumps(policy))

        # Patch this imported alias alone; live_speech retains its disabled runtime.
        def qualification_runtime_paths():
            return python, proof / "speech-models-disabled"

        runtime_paths = qualification_runtime_paths


def _claim_qualification(sid, storage, tracks, devices):
    if _qualification is None:
        return None
    from scripts.native_capture_qualification import (
        check_armed,
        validate_policy,
        exclusive_json,
    )

    policy = json.loads(json.dumps(_qualification))
    proof = validate_policy(policy, storage=storage, sid=sid)
    if set(tracks) != {"mic", "system"} or devices != {
        k: policy["devices"][k] for k in ("mic", "system")
    }:
        raise PermissionError(
            "Seules les deux pistes Jabra explicitement autorisées sont admises"
        )
    check_armed(policy, os.getpid())
    # Durable exclusive claim before creating any helper. A failed opening never
    # grants a retake, including a backend restart or a second browser tab.
    try:
        exclusive_json(
            proof / "consumed.json",
            {
                "token": policy["token"],
                "session_id": sid,
                "backend_pid": os.getpid(),
                "claimed_monotonic": time.monotonic(),
                "authorization_reference": policy["authorization_reference"],
            },
        )
    except FileExistsError as exc:
        raise HTTPException(
            409, "Accord matériel déjà consommé ; aucune nouvelle ouverture"
        ) from exc
    return policy


def inventory(*, refresh=False):
    global _inventory, _inventory_time
    if not refresh and _inventory and time.monotonic() - _inventory_time < 30:
        return dict(_inventory)
    python, _ = runtime_paths()
    if os.name != "nt" or not python.is_file():
        return {
            "installed": False,
            "devices": [],
            "interactive_session": False,
            "error": "Runtime WASAPI Windows non installé",
        }
    try:
        result = subprocess.run(
            [
                str(python),
                str(ROOT / "scripts" / "native_audio_capture.py"),
                "--inventory",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        value = json.loads(result.stdout.splitlines()[-1])
        if result.returncode:
            value = {
                "installed": False,
                "devices": [],
                "error": value.get("error", "WASAPI indisponible"),
            }
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        value = {
            "installed": False,
            "devices": [],
            "error": "Inventaire WASAPI inaccessible",
        }
    _inventory, _inventory_time = value, time.monotonic()
    return dict(value)


def status(sid=None):
    value = inventory()
    report = {}
    try:
        report = json.loads(
            (
                ROOT / "logs" / "foresight-runtime" / "native-audio-qualification.json"
            ).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        pass
    devices = value.get("devices", [])
    loopbacks = [item for item in devices if item.get("isLoopbackDevice")]
    qualified = bool(
        report.get("passed")
        and report.get("version") == value.get("version")
        and report.get("device_name") in {item["name"] for item in loopbacks}
    )
    with _lock:
        active = [
            {"session_id": sid, "state": item.state, "tracks": item.tracks}
            for sid, item in _captures.items()
            if item.process and item.process.poll() is None
        ]
        selected = _captures.get(sid) if sid else None
    return {
        **value,
        "loopback_available": bool(loopbacks),
        "loopback_ready": qualified,
        "real_test_passed": qualified,
        "microphone_test_passed": False,
        "ready": bool(
            value.get("installed") and value.get("interactive_session") and loopbacks
        ),
        "active": active,
        "requires_explicit_tracks": True,
        "session0_supported": False,
        "session": {
            "session_id": sid,
            "state": selected.state,
            "tracks": selected.tracks,
            "error": selected.error,
        }
        if selected
        else None,
        "capture_scope": "Windows output mix in the operator's interactive session",
    }


def registered_snapshots():
    """Private owner snapshots, including stopped helpers, without device I/O.

    Never nest registry, event or session writer locks. Route/service callers
    must authorize each SID before including this internal data in a DTO.
    """
    with _lock:
        references = tuple(_captures.items())
    result = []
    for sid, item in references:
        guard = getattr(item, "_event_lock", None)
        if guard is None:
            from contextlib import nullcontext

            guard = nullcontext()
        with guard:
            state = item.state
            tracks = list(item.tracks)
            process = item.process
            error = getattr(item, "error", None)
            persistence_failed = getattr(item, "_interruption_persistence_error", False)
        try:
            alive = process.poll() is None if process else False
        except (OSError, ValueError):
            alive = None
        with _lock:
            if _captures.get(sid) is not item:
                continue
        result.append(
            {
                "session_id": sid,
                "state": "starting"
                if state == "created"
                else state
                if state
                in {"starting", "recording", "paused", "interrupted", "stopped"}
                else "unknown",
                "tracks": tracks,
                "process_alive": alive,
                "stop_confirmation_required": True,
                **(
                    {
                        "problem_code": "interruption-unpersisted"
                        if persistence_failed
                        else "interrupted"
                        if error
                        else "status-unknown"
                    }
                    if error or alive is None
                    else {}
                ),
            }
        )
    return result


def owner_status():
    """Metadata for workspace ownership, deliberately without an inventory probe."""
    return {
        "installed": bool(_inventory.get("installed")),
        "ready": False,
        "loopback_ready": False,
        "real_test_passed": False,
        "microphone_test_passed": False,
        "devices": [],
        "active": [],
        "session": None,
    }


def owns_session(sid):
    with _lock:
        item = _captures.get(sid)
        return bool(item and item.state != "stopped")


def has_registered_capture(sid):
    """Retained owner needing stop confirmation, including auto-ended helpers."""
    with _lock:
        return sid in _captures


def owned_session_ids():
    """In-process reservations, including interrupted owners; no hardware probe."""
    with _lock:
        return [sid for sid, item in _captures.items() if item.state != "stopped"]


def has_capture_owner():
    with _lock:
        return bool(_captures)  # Stopped owners still require drain confirmation.


def accepts_owner(sid, owner):
    """Private Python object identity; never accepted from an HTTP request."""
    with _lock:
        return owner is not None and _captures.get(sid) is owner


class NativeCapture:
    def __init__(
        self, sid, storage, tracks, devices, sequences, offset_ms, total_bytes=0
    ):
        self.sid, self.storage, self.tracks = sid, Path(storage).resolve(), list(tracks)
        self.directory = self.storage / "meeting-sessions" / "native" / sid
        self.directory.mkdir(parents=True, exist_ok=True)
        self.request = {
            "session_id": sid,
            "storage": str(self.storage),
            "directory": str(self.directory),
            "tracks": self.tracks,
            "devices": devices,
            "sequences": sequences,
            "offset_ms": offset_ms,
            "total_bytes": total_bytes,
        }
        policy = _claim_qualification(sid, self.storage, self.tracks, devices)
        if policy is not None:
            self.request["qualification"] = policy
        self.process, self._job = None, None
        # Chunks already have durable files/journals and SQL receipts. Only
        # protocol controls belong here; otherwise a long recording retains
        # every chunk notification until the next user command.
        self.events = queue.Queue(maxsize=8)
        self.state = "created"
        self.error = None
        self._write_lock = threading.Lock()
        self._event_lock = threading.RLock()
        self._reader_done = threading.Event()
        self.owner_event_id = None
        self._interruption_persistence_error = False

    def _interrupt(self, detail):
        # Never block the stdout reader behind a full notification queue. The
        # sticky error prevents an older queued state from acknowledging a
        # command after persistence/protocol failure.
        with self._event_lock:
            self.error = self.error or detail
            self.state = "interrupted"
            while True:
                try:
                    self.events.get_nowait()
                except queue.Empty:
                    break
            self.events.put_nowait({"kind": "error", "error": self.error})

    def _check_error(self):
        with self._event_lock:
            detail = self.error
        if detail:
            raise ValueError(detail)

    def _confirm_stop(self, deadline):
        detail = None
        if not self._reader_done.wait(max(0, deadline - time.monotonic())):
            detail = "Fin de capture native non confirmée ; fragments conservés"
        else:
            self._check_error()
            try:
                if self.process.wait(timeout=max(0, deadline - time.monotonic())) != 0:
                    detail = "Capture native terminée en erreur ; fragments conservés"
            except subprocess.TimeoutExpired:
                detail = "Fin de capture native non confirmée ; fragments conservés"
        if detail:
            self._interrupt(detail)
            self._record_interruption()
            self._check_error()

    def _receive_event(self, event):
        if not isinstance(event, dict):
            raise ValueError("Notification native invalide ; fragments conservés")
        kind = event.get("kind")
        if kind == "chunk":
            self._persist(event)
            return  # No second, unconsumed in-memory copy of the journal.
        with self._event_lock:
            if kind == "error":
                detail = event.get("error")
                if not isinstance(detail, str) or not detail:
                    raise ValueError("Erreur native invalide ; fragments conservés")
                self._interrupt(detail[:500])
                return
            if kind not in {"ready", "state", "qualification.armed"}:
                raise ValueError("Contrôle natif inconnu ; fragments conservés")
            if kind == "state":
                if event.get("state") not in {"recording", "paused", "stopped"}:
                    raise ValueError("État natif invalide ; fragments conservés")
                if not self.error:
                    self.state = event["state"]
            if self.error:
                return  # A subsequent control cannot clear a terminal failure.
            try:
                self.events.put_nowait(event)
            except queue.Full:
                raise ValueError(
                    "File de contrôles natifs saturée ; capture interrompue, fragments conservés"
                ) from None

    def _receive(self):
        process = self.process
        try:
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except (TypeError, ValueError):
                    raise ValueError(
                        "Notification native illisible ; fragments conservés"
                    ) from None
                self._receive_event(event)
            if self.state != "stopped" and not self.error:
                self._interrupt(
                    "Capture native terminée sans arrêt confirmé ; fragments conservés"
                )
        except Exception as exc:
            self._interrupt(_capture_failure_detail(exc))
            if process and process.poll() is None:
                process.terminate()
        finally:
            try:
                if self.state not in {"stopped", "created"}:
                    self._record_interruption()
            finally:
                self._reader_done.set()

    def _authorize_persistence(self):
        from app.db import SessionLocal
        from .meeting_sessions import get_session

        with SessionLocal() as db:
            get_session(db, self.sid, write=True)
        if not accepts_owner(self.sid, self):
            raise HTTPException(403, "Propriétaire de persistance native invalide")

    def _persist(self, packet):
        self._authorize_persistence()
        from app.db import SessionLocal
        from .meeting_sessions import store_chunk

        path = Path(packet["path"]).resolve()
        if not path.is_relative_to(self.directory) or not path.is_file():
            raise ValueError("Fragment natif hors stockage autorisé")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != packet["sha256"]:
            raise ValueError("Empreinte du fragment natif modifiée")
        with SessionLocal() as db:
            receipt = store_chunk(
                db,
                self.sid,
                packet["track"],
                packet["sequence"],
                raw=raw,
                filename=path.name,
                mime_type={".wav": "audio/wav", ".ogg": "audio/ogg"}[path.suffix.lower()],
                command_id=packet["command_id"],
                sha256=packet["sha256"],
                start_ms=packet["start_ms"],
                duration_ms=packet["duration_ms"],
                internal_capture_owner=self,
            )
        # SQL remains the acknowledgement authority. Filesystem publication has
        # its own current authority and exact native-folder/headroom admission.
        from scripts.native_chunk_journal import publish_receipt

        publish_receipt(
            self.directory,
            self.sid,
            packet,
            receipt,
            authorize=self._authorize_persistence,
        )

    def replay(self):
        # Complete only exact durable intents before reading ordinary manifests.
        # File repair has its own current authority barrier; SQL still confirms
        # every command below and remains the sole acknowledgement authority.
        from scripts.native_chunk_journal import iter_reconcile

        authorize_repair = self._authorize_persistence

        # Each durable repaired pair reaches the existing real SQL confirmation
        # before another intent is materialized; a later refusal retains progress.
        for packet in iter_reconcile(
            self.directory, self.sid, authorize=authorize_repair
        ):
            self._persist(packet)
        journal_bytes = 0
        for manifest in sorted(self.directory.glob("*.json")):
            if manifest.name.endswith((".receipt.json", "-request.json")):
                continue
            packet = json.loads(manifest.read_text(encoding="utf-8"))
            if packet.get("kind") != "chunk":
                continue
            if (
                packet.get("session_id") != self.sid
                or packet.get("track") not in {"mic", "system"}
                or not isinstance(packet.get("sequence"), int)
                or packet["sequence"] < 0
            ):
                raise ValueError("Journal natif incompatible avec cette séance")
            path = Path(packet["path"]).resolve()
            if not path.is_relative_to(self.directory) or not path.is_file():
                raise ValueError("Fragment du journal natif absent ou hors stockage")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != packet["sha256"]:
                raise ValueError("Empreinte du journal natif modifiée")
            # A local receipt (even valid JSON) cannot replace current SQL authority.
            # The canonical command is idempotent; only its confirmation permits
            # advancing the sequence/offset or repairing an interrupted receipt.
            self._persist(packet)
            track = packet["track"]
            if track in self.request["sequences"]:
                self.request["sequences"][track] = max(
                    self.request["sequences"][track], packet["sequence"] + 1
                )
            self.request["offset_ms"] = max(
                self.request["offset_ms"], packet["start_ms"] + packet["duration_ms"]
            )
            journal_bytes += len(raw)
        self.request["total_bytes"] = max(self.request["total_bytes"], journal_bytes)

    def start(self):
        self.replay()
        request_path = self.directory / "capture-request.json"
        request_path.write_text(json.dumps(self.request), encoding="utf-8")
        python, _ = runtime_paths()
        self.process = subprocess.Popen(
            [
                str(python),
                "-u",
                str(ROOT / "scripts" / "native_audio_capture.py"),
                "--request",
                str(request_path),
                "--parent-pid",
                str(os.getpid()),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            self._job = _windows_job(self.process)
            context = copy_context()

            self._reader_done.clear()
            threading.Thread(
                target=lambda: context.run(self._receive),
                name="native-audio-events",
                daemon=True,
            ).start()
            event = self.events.get(timeout=30)
            self._check_error()
            if "qualification" in self.request:
                if (
                    event.get("kind") != "qualification.armed"
                    or event.get("token") != self.request["qualification"]["token"]
                ):
                    raise ValueError("Handshake privé de qualification absent")
                # Child cannot open a stream before this exact private handshake,
                # after its local Job assignment and the external fixture Job.
                with self._write_lock:
                    self.process.stdin.write(
                        json.dumps(
                            {
                                "op": "qualification.open",
                                "token": self.request["qualification"]["token"],
                                "job_attached": True,
                            }
                        )
                        + "\n"
                    )
                    self.process.stdin.flush()
                event = self.events.get(timeout=10)
                self._check_error()
            if event.get("kind") != "ready":
                raise ValueError(
                    event.get("error", "Ouverture des pistes WASAPI impossible")
                )
            self.command("start", target_state="recording")
        except Exception:
            self.close()
            raise

    def _record_interruption(self):
        from app.db import SessionLocal
        from app.meeting_session_models import MeetingSession, MeetingSessionEvent, now
        from .meeting_sessions import append_event, _lock as session_lock
        from sqlalchemy import select, text

        with self._event_lock:
            detail, generation = (
                self.error or "Capture native arrêtée",
                self.owner_event_id,
            )
        try:
            with session_lock, SessionLocal() as db:
                db.execute(
                    text("UPDATE meeting_sessions SET revision=revision WHERE 0")
                )
                row = db.get(MeetingSession, self.sid)
                latest_owner = db.scalar(
                    select(MeetingSessionEvent.id)
                    .where(
                        MeetingSessionEvent.session_id == self.sid,
                        MeetingSessionEvent.kind == "native.capture.owner",
                    )
                    .order_by(MeetingSessionEvent.id.desc())
                    .limit(1)
                )
                if generation is None:
                    raise ValueError("Propriétaire natif non confirmé")
                if latest_owner != generation:
                    return  # An old reader cannot interrupt a newer owner.
                if row and row.state in {"recording", "paused", "interrupted"}:
                    previous = list(
                        db.scalars(
                            select(MeetingSessionEvent).where(
                                MeetingSessionEvent.session_id == self.sid,
                                MeetingSessionEvent.kind
                                == "native.capture.interrupted",
                            )
                        )
                    )
                    if not any(
                        (event.data or {}).get("owner_event_id") == generation
                        for event in previous
                    ):
                        row.state = "interrupted"
                        row.updated_at = now()
                        row.revision += 1
                        append_event(
                            db,
                            row,
                            "native.capture.interrupted",
                            {"error": detail, "owner_event_id": generation},
                        )
                        db.commit()
            with self._event_lock:
                self._interruption_persistence_error = False
        except Exception:
            with self._event_lock:
                self._interruption_persistence_error = True

    def command(self, op, *, target_state, timeout=300):
        self._check_error()
        if op == "stop" and self.state == "stopped":
            self._confirm_stop(time.monotonic() + timeout)
            return {
                "session_id": self.sid,
                "state": self.state,
                "tracks": self.tracks,
                "durable_chunks_acknowledged": True,
            }
        if not self.process or self.process.poll() is not None:
            raise ValueError(self.error or "Capture native arrêtée")
        with self._write_lock:
            self.process.stdin.write(json.dumps({"op": op}) + "\n")
            self.process.stdin.flush()
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    event = self.events.get(
                        timeout=max(0.01, deadline - time.monotonic())
                    )
                except queue.Empty:
                    break
                self._check_error()
                if event.get("kind") == "error":
                    raise ValueError(event["error"])
                if event.get("kind") == "state" and event["state"] == target_state:
                    if target_state == "stopped":
                        # The qualification helper may report a final error
                        # immediately after stopped. Await EOF before success.
                        self._confirm_stop(deadline)
                    return {
                        "session_id": self.sid,
                        "state": self.state,
                        "tracks": self.tracks,
                        "durable_chunks_acknowledged": True,
                    }
            raise ValueError("Le périphérique ne répond pas ; fragments conservés")

    def close(self):
        with self._event_lock:
            process, self.process = self.process, None
        if process:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(5)
            for stream in (process.stdin, process.stdout):
                if stream:
                    try:
                        stream.close()
                    except OSError:
                        pass
        if self._job:
            kernel, handle = self._job
            kernel.CloseHandle(handle)
            self._job = None


def start_capture(db, sid, *, tracks, devices=None):
    from app.config import settings
    from app.meeting_session_models import MeetingAudioChunk, MeetingSessionEvent
    from .meeting_sessions import get_session, append_event, require_enabled

    require_enabled(db)
    row = get_session(db, sid, write=True)
    if row.state != "recording":
        raise HTTPException(
            409, "Reprendre la séance avant de démarrer la capture native"
        )
    if (
        not tracks
        or len(set(tracks)) != len(tracks)
        or any(track not in {"mic", "system"} for track in tracks)
    ):
        raise HTTPException(
            422, "Choisir explicitement les pistes microphone et/ou système"
        )
    capabilities = status()
    if not capabilities["ready"]:
        raise HTTPException(
            409, "WASAPI indisponible dans cette session Windows interactive"
        )
    previous_owner = (
        db.query(MeetingSessionEvent)
        .filter_by(session_id=sid, kind="native.capture.owner")
        .first()
    )
    chunks = db.query(MeetingAudioChunk).filter_by(session_id=sid).all()
    if chunks and previous_owner is None:
        raise HTTPException(
            409,
            "Cette séance utilise déjà la capture navigateur ; créer une nouvelle séance native",
        )
    with _lock:
        if _captures:
            raise HTTPException(
                409, "Une capture native Windows reste à arrêter ou à conserver"
            )
        sequences = {
            track: max(
                (chunk.sequence for chunk in chunks if chunk.track == track), default=-1
            )
            + 1
            for track in tracks
        }
        offset = max(
            (chunk.start_ms + chunk.duration_ms for chunk in chunks), default=0
        )
        item = NativeCapture(
            sid,
            settings.storage_dir,
            tracks,
            devices or {},
            sequences,
            offset,
            total_bytes=sum(chunk.size_bytes for chunk in chunks),
        )
        # Reserve atomically, then release the registry before any SQL writer.
        # Session serialization can inspect this starting owner during commit.
        _captures[sid] = item
    try:
        event = append_event(
            db,
            row,
            "native.capture.owner",
            {
                "tracks": tracks,
                "backend_pid": os.getpid(),
                **(
                    {"start_command_id": row.pending_command_id}
                    if row.pending_command_id
                    else {}
                ),
            },
        )
        db.commit()
        item.owner_event_id = event.id
    except Exception:
        try:
            db.rollback()
        finally:
            with _lock:
                if _captures.get(sid) is item:
                    _captures.pop(sid)
            item.close()  # No hardware has been opened; preserve files/journals.
        raise
    try:
        item.start()
    except (ValueError, OSError, queue.Empty) as exc:
        with _lock:
            if _captures.get(sid) is item:
                _captures.pop(sid)
        item.close()
        raise HTTPException(
            409,
            str(exc)
            if isinstance(exc, ValueError)
            else "Ouverture WASAPI impossible ; vérifier permissions Windows",
        ) from exc
    return {"session_id": sid, "state": item.state, "tracks": item.tracks}


def _capture(sid):
    with _lock:
        item = _captures.get(sid)
        if not item:
            raise HTTPException(409, "Cette séance n'a pas de capture native active")
        return item


def pause_capture(sid):
    return _capture(sid).command("pause", target_state="paused")


def resume_capture(sid):
    return _capture(sid).command("resume", target_state="recording")


def stop_capture(sid):
    item = _capture(sid)
    try:
        return item.command("stop", target_state="stopped")
    except (ValueError, OSError, queue.Empty) as exc:
        raise NativeStopNotConfirmed(
            str(exc) or "Arrêt natif non confirmé ; fragments conservés"
        ) from exc
    finally:
        item.close()
        with _lock:
            _captures.pop(sid, None)


class NativeStopNotConfirmed(ValueError):
    """The helper ended without a trustworthy drain/exit receipt."""


class NativeStartNotConfirmed(ValueError):
    """An interrupted prepared start cannot be acknowledged or open new audio."""


def stop_all():
    for sid in list(_captures):
        try:
            stop_capture(sid)
        except (HTTPException, ValueError, queue.Empty):
            with _lock:
                item = _captures.pop(sid, None)
            if item:
                item.close()
