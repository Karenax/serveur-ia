"""Real private SQL/filesystem persistence; no device, model or child process.

ENOSPC is injected on the real receipt stream/descriptor or replacement only.
These cases simulate I/O failure, not a physically full disk or hardware capture.
"""
import errno
import hashlib
import io
import json
import re
from pathlib import Path
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import event, func, select

from app.meeting_session_models import (
    MeetingAudioChunk, MeetingSession, MeetingSessionCommand, MeetingSessionEvent,
)
from app.services import meeting_sessions as sessions, native_audio as native
from backend.app.project_note_models import NoteVersion, ProjectNote
from backend.app.project_note_schemas import NoteCreate
from backend.app.services import project_notes as notes
from backend.app.services.project_operator import Operator, operator_context
from tests.test_meeting_sessions import stores as stores_fixture, content, create, key, wav

stores = stores_fixture


@pytest.fixture
def capture(stores, tmp_path, monkeypatch):
    brain, erp, pid, _ = stores
    from app.config import settings

    def forbidden(*args, **kwargs):
        raise AssertionError("Receipt recovery never opens hardware or a real process")

    monkeypatch.setattr(native, "_captures", {})
    monkeypatch.setattr(native, "_qualification", None)
    monkeypatch.setattr(native, "inventory", forbidden)
    monkeypatch.setattr(native.subprocess, "Popen", forbidden)
    assert all(Path(factory.kw["bind"].url.database).resolve().is_relative_to(tmp_path.resolve())
               for factory in (brain, erp))
    with erp() as db:
        notes.create_note(db, pid, NoteCreate(command_id=key(), title="Note humaine fictive",
                                            content=content("Décision humaine conservée")))
    with brain() as db:
        row = create(db, project_id=pid)
        record = db.get(MeetingSession, row["id"])
        record.state = "recording"  # Synthetic producer reservation; no native start.
        owner_event = sessions.append_event(db, record, "native.capture.owner", {"tracks": ["mic"]})
        db.commit()
        item = native.NativeCapture(row["id"], settings.storage_dir, ["mic"], {}, {"mic": 0}, 0)
        item.owner_event_id = owner_event.id
        item.state = "recording"
    native._captures[item.sid] = item
    raw = wav(samples=80_000)
    path = item.directory / "mic-00000000.wav"
    path.write_bytes(raw)
    packet = {"kind": "chunk", "session_id": item.sid, "track": "mic", "sequence": 0,
              "path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
              "command_id": str(uuid.uuid5(uuid.UUID(item.sid), "mic:0:" + hashlib.sha256(raw).hexdigest())),
              "start_ms": 0, "duration_ms": 5000}
    manifest = path.with_suffix(".json")
    manifest.write_text(json.dumps(packet), encoding="utf-8")
    value = SimpleNamespace(brain=brain, erp=erp, item=item, raw=raw, path=path, packet=packet,
                            manifest=manifest, receipt=path.with_suffix(".receipt.json"))
    value.manifest_before = manifest.read_bytes()
    value.notes_before = note_snapshot(erp)
    yield value
    item.close()


def note_snapshot(factory):
    with factory() as db:
        return (list(db.execute(select(ProjectNote.id, ProjectNote.title, ProjectNote.plain_text,
                                       ProjectNote.revision, ProjectNote.current_version_id).order_by(ProjectNote.id))),
                list(db.execute(select(NoteVersion.id, NoteVersion.revision, NoteVersion.snapshot,
                                       NoteVersion.sha256, NoteVersion.command_id).order_by(NoteVersion.id))))


def assert_committed(value):
    with value.brain() as db:
        chunks = list(db.scalars(select(MeetingAudioChunk).where(MeetingAudioChunk.session_id == value.item.sid)))
        assert len(chunks) == 1
        chunk = chunks[0]
        assert (chunk.sequence, chunk.sha256, chunk.size_bytes) == (0, value.packet["sha256"], len(value.raw))
        assert Path(chunk.storage_path).read_bytes() == value.raw
        command = db.get(MeetingSessionCommand, value.packet["command_id"])
        assert command.status == "completed" and command.result["acknowledged"] is True
        assert db.scalar(select(func.count()).select_from(MeetingSessionCommand).where(
            MeetingSessionCommand.session_id == value.item.sid, MeetingSessionCommand.kind == "chunk")) == 1
        assert db.scalar(select(func.count()).select_from(MeetingSessionEvent).where(
            MeetingSessionEvent.session_id == value.item.sid, MeetingSessionEvent.kind == "chunk.received")) == 1
        return json.dumps(command.result).encode("utf-8")


def assert_originals(value):
    assert value.path.read_bytes() == value.raw
    assert hashlib.sha256(value.path.read_bytes()).hexdigest() == value.packet["sha256"]
    assert value.manifest.read_bytes() == value.manifest_before
    assert note_snapshot(value.erp) == value.notes_before


@pytest.mark.parametrize("damage", ["truncated", "error", "empty", "false-ack", "cross-session", "event-token"])
def test_damaged_receipt_is_repaired_from_real_SQL_and_old_bytes_retained(capture, monkeypatch, damage):
    value = capture
    value.item._persist(value.packet)
    original = assert_committed(value)
    receipt = json.loads(original)
    if damage == "truncated":
        broken = b'{"acknowledged":'
    elif damage == "error":
        broken = b"ERROR"
    elif damage == "empty":
        broken = b"{}"
    else:
        receipt[{"false-ack": "acknowledged", "cross-session": "session_id", "event-token": "event_token"}[damage]] = (
            False if damage == "false-ack" else str(uuid.uuid4()))
        broken = json.dumps(receipt).encode("utf-8")
    value.receipt.write_bytes(broken)
    value.item.replay()
    assert value.receipt.read_bytes() == original == assert_committed(value)
    retained = list(value.item.directory.glob("*.previous-*.receipt.json"))
    assert len(retained) == 1 and retained[0].read_bytes() == broken
    assert value.item.request["sequences"] == {"mic": 1}
    assert value.item.request["offset_ms"] == 5000
    assert_originals(value)
    before = value.receipt.stat().st_mtime_ns
    value.item.replay()
    assert value.receipt.stat().st_mtime_ns == before
    assert len(list(value.item.directory.glob("*.previous-*.receipt.json"))) == 1
    assert_committed(value)


def test_valid_receipt_still_confirms_current_SQL_without_rewriting(capture, monkeypatch):
    value = capture
    value.item._persist(value.packet)
    calls = []
    original_store = sessions.store_chunk

    def store(*args, **kwargs):
        calls.append(kwargs["command_id"])
        return original_store(*args, **kwargs)

    monkeypatch.setattr(sessions, "store_chunk", store)
    before = value.receipt.read_bytes(), value.receipt.stat().st_mtime_ns
    value.item.replay()
    value.item.replay()
    assert calls == [value.packet["command_id"], value.packet["command_id"]]
    assert (value.receipt.read_bytes(), value.receipt.stat().st_mtime_ns) == before
    assert not list(value.item.directory.glob("*.previous-*.receipt.json"))
    assert_committed(value)
    assert_originals(value)


class ReceiptFault:
    """Delegate to the real file; fail once on its actual receipt boundary."""
    def __init__(self, value, phase):
        self.value, self.phase, self.fired, self.descriptors = value, phase, 0, set()

    def fail(self):
        self.fired += 1
        raise OSError(errno.ENOSPC, "Fictitious receipt ENOSPC", str(self.value.receipt))

    def install(self, patch):
        original_open, original_sync, original_replace = Path.open, native.os.fsync, native.os.replace
        fault = self

        class Stream:
            def __init__(self, real):
                self.real = real

            def __enter__(self):
                self.real.__enter__()
                return self

            def __exit__(self, *args):
                return self.real.__exit__(*args)

            def __getattr__(self, name):
                return getattr(self.real, name)

            def write(self, raw):
                if fault.phase == "write" and not fault.fired:
                    self.real.write(raw[:max(1, len(raw) // 2)])
                    self.real.flush()
                    fault.fail()
                return self.real.write(raw)

            def flush(self):
                if fault.phase == "flush" and not fault.fired:
                    fault.fail()
                return self.real.flush()

        def opened(path, *args, **kwargs):
            real = original_open(path, *args, **kwargs)
            if (path.parent == fault.value.item.directory
                    and ((path.name.startswith(fault.value.receipt.name + ".")
                          and path.suffix == ".pending")
                         or re.fullmatch(r"receipt-[a-f0-9]{32}\.pending", path.name) is not None)):
                fault.descriptors.add(real.fileno())
                return Stream(real)
            return real

        def sync(descriptor):
            if fault.phase == "fsync" and not fault.fired and descriptor in fault.descriptors:
                fault.fail()
            return original_sync(descriptor)

        def replace(source, destination):
            if fault.phase == "replace" and not fault.fired and Path(destination) == fault.value.receipt:
                fault.fail()
            return original_replace(source, destination)

        patch.setattr(Path, "open", opened)
        patch.setattr(native.os, "fsync", sync)
        patch.setattr(native.os, "replace", replace)


@pytest.mark.parametrize("phase", ["write", "flush", "fsync", "replace"])
def test_receipt_ENOSPC_after_real_SQL_commit_keeps_originals_and_replays_without_duplicates(capture, monkeypatch, phase):
    value = capture
    fault = ReceiptFault(value, phase)
    with monkeypatch.context() as patch:
        fault.install(patch)
        with pytest.raises(OSError) as caught:
            value.item.replay()
    assert caught.value.errno == errno.ENOSPC and fault.fired == 1
    expected = assert_committed(value)  # The real commit preceded this ACK failure.
    assert not value.receipt.exists()
    assert value.item.request["sequences"] == {"mic": 0} and value.item.request["offset_ms"] == 0
    diagnostics = {path: path.read_bytes() for path in value.item.directory.glob("*.pending")}
    assert diagnostics and any(diagnostics.values())
    assert_originals(value)
    value.item.replay()
    assert value.receipt.read_bytes() == expected == assert_committed(value)
    assert value.item.request["sequences"] == {"mic": 1} and value.item.request["offset_ms"] == 5000
    assert all(path.read_bytes() == raw for path, raw in diagnostics.items())
    assert_originals(value)


def test_real_SQL_insertion_failure_never_creates_ACK_or_advances_replay(capture):
    value = capture
    engine = value.brain.kw["bind"]

    def fail(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.startswith("INSERT INTO meeting_session_chunks"):
            raise OSError(errno.ENOSPC, "Fictitious SQL write failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(OSError) as caught:
            value.item.replay()
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    assert caught.value.errno == errno.ENOSPC
    with value.brain() as db:
        assert db.scalar(select(func.count()).select_from(MeetingAudioChunk)) == 0
        assert db.get(MeetingSessionCommand, value.packet["command_id"]) is None
    assert not value.receipt.exists()
    assert value.item.request["sequences"] == {"mic": 0} and value.item.request["offset_ms"] == 0
    assert_originals(value)
    value.item.replay()
    assert value.receipt.read_bytes() == assert_committed(value)
    assert_originals(value)


def test_failed_atomic_repair_preserves_existing_bad_receipt_and_its_exact_backup(capture, monkeypatch):
    value = capture
    value.item._persist(value.packet)
    value.receipt.write_bytes(b"ERROR")
    fault = ReceiptFault(value, "replace")
    with monkeypatch.context() as patch:
        fault.install(patch)
        with pytest.raises(OSError) as caught:
            value.item.replay()
    assert caught.value.errno == errno.ENOSPC and fault.fired == 1
    assert value.receipt.read_bytes() == b"ERROR"
    assert value.item.request["sequences"] == {"mic": 0}
    retained = list(value.item.directory.glob("*.previous-*.receipt.json"))
    assert len(retained) == 1 and retained[0].read_bytes() == b"ERROR"
    assert_committed(value)
    assert_originals(value)
    value.item.replay()
    assert value.receipt.read_bytes() == assert_committed(value)
    assert all(path.read_bytes() == b"ERROR" for path in retained)


def test_local_receipt_cannot_bypass_changed_operator_SQL_authority(capture):
    value = capture
    value.item._persist(value.packet)
    before = value.receipt.read_bytes()
    with operator_context(Operator("other-reader", "reader", frozenset())):
        with pytest.raises(HTTPException):
            value.item.replay()
    assert value.receipt.read_bytes() == before
    assert value.item.request["sequences"] == {"mic": 0}
    assert_committed(value)
    assert_originals(value)


def test_reader_ACK_failure_is_sticky_and_cannot_accept_a_later_stopped_state(capture, monkeypatch):
    value = capture
    stopped = []
    lines = json.dumps(value.packet) + "\n" + json.dumps({"kind": "state", "state": "stopped"}) + "\n"
    process = SimpleNamespace(stdout=io.StringIO(lines), poll=lambda: None,
                              terminate=lambda: stopped.append("synthetic producer terminated"))
    value.item.process = process
    fault = ReceiptFault(value, "fsync")
    with monkeypatch.context() as patch:
        fault.install(patch)
        value.item._receive()
    value.item.process = None  # There is no OS child to close in this fixture.
    assert fault.fired == 1 and stopped == ["synthetic producer terminated"]
    assert value.item.state == "interrupted" and value.item.error and value.item._reader_done.is_set()
    assert value.item.events.get_nowait()["kind"] == "error"
    with pytest.raises(ValueError):
        value.item.command("stop", target_state="stopped")
    with value.brain() as db:
        assert db.get(MeetingSession, value.item.sid).state == "interrupted"
    assert_committed(value)
    assert_originals(value)
