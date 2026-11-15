"""Durable native chunk journal; no device, model, SQL or threads.

Intent contains exact audio bytes and packet, not an inferred historical timecode.
New capture uses Opus; historical WAV v1 intents remain recoverable. Only the
producer's Opus encoding requires PyAV; recovery uses the standard library.
Pending/preimage files are retained. Existing bytes are never overwritten.
"""

import base64
import errno
import re
import binascii
import hashlib
import io
import json
import os
import shutil
import stat
from pathlib import Path
import uuid
import wave

MAX_RAW = 160000
MAX_WAV = MAX_RAW + 44
MAX_INTENT = 256 * 1024
MAX_MANIFEST = 16 * 1024
PACKET_KEYS = {
    "kind",
    "session_id",
    "track",
    "sequence",
    "path",
    "sha256",
    "size_bytes",
    "start_ms",
    "duration_ms",
    "command_id",
}


class FileOps:
    """Small explicit failure-injection boundary; default delegates real file I/O."""

    def free_bytes(self, directory):
        return shutil.disk_usage(directory).free

    def open(self, path):
        return path.open("xb")

    def write(self, target, data, phase):
        return target.write(data)

    def flush(self, target, phase):
        target.flush()

    def fsync(self, target, phase):
        os.fsync(target.fileno())

    def create(self, temporary, target, phase):
        os.link(temporary, target)

    def replace(self, temporary, target, phase):
        os.replace(temporary, target)


def _inside(directory, path):
    directory = Path(directory).resolve(strict=True)
    path = Path(path)
    if path.is_symlink() or path.resolve().parent != directory:
        raise ValueError("Native journal path is not an owned direct child")
    return path.resolve()


def _bounded(path, maximum):
    with path.open("rb") as source:
        raw = source.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("Native journal input exceeds explicit bound")
    return raw


def _pending_path(directory, phase):
    # Phase is an internal bounded namespace, never a packet or caller path.
    if phase not in {"intent", "wav", "preimage", "manifest", "receipt", "receipt-preimage"}:
        raise ValueError("Unknown native journal publication phase")
    return _inside(directory, Path(directory) / (phase + "-" + uuid.uuid4().hex + ".pending"))


def _durable_new(directory, target, data, phase, ops, reservation):
    target = _inside(directory, target)
    temporary = _pending_path(directory, phase)
    reservation.claim(len(data), 2)
    with ops.open(temporary) as sink:
        if ops.write(sink, data, phase) != len(data):
            raise OSError("Incomplete native journal write")
        ops.flush(sink, phase)
        ops.fsync(sink, phase)
    # Atomic exclusive publication. Hard-link creation preserves the pending
    # bytes and refuses a collision on Windows and POSIX; it never replaces WAV.
    ops.create(temporary, target, phase)
    return target


def _durable_replace(directory, target, data, phase, ops, reservation):
    target = _inside(directory, target)
    temporary = _pending_path(directory, phase)
    reservation.claim(len(data), 1)
    with ops.open(temporary) as sink:
        if ops.write(sink, data, phase) != len(data):
            raise OSError("Incomplete native manifest write")
        ops.flush(sink, phase)
        ops.fsync(sink, phase)
    ops.replace(temporary, target, phase)


def _session(sid):
    if not isinstance(sid, str) or str(uuid.UUID(sid)) != sid:
        raise ValueError("Canonical native session UUID required")
    return sid


def prepare(directory, sid, track, sequence, raw, start_ms, *, codec="wav"):
    directory = Path(directory).resolve(strict=True)
    sid = _session(sid)
    if track not in {"mic", "system"} or type(sequence) is not int or sequence < 0:
        raise ValueError("Explicit native track and sequence required")
    if (
        type(start_ms) is not int
        or start_ms < 0
        or not isinstance(raw, bytes)
        or not 0 < len(raw) <= MAX_RAW
        or len(raw) % 2
    ):
        raise ValueError("Bounded PCM16 native fragment and actual start required")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16000)
        target.writeframes(raw)
    wav = buffer.getvalue()
    if codec == "opus":
        from scripts.audio_codec import encode_opus
        wav = encode_opus(raw)
    elif codec != "wav":
        raise ValueError("Unsupported native codec")
    return _packet(directory, sid, track, sequence, wav, start_ms, len(raw) // 32, codec), wav


def _packet(directory, sid, track, sequence, wav, start_ms, duration_ms, codec):
    sha = hashlib.sha256(wav).hexdigest()
    path = _inside(directory, directory / f"{track}-{sequence:08d}.{'ogg' if codec == 'opus' else 'wav'}")
    packet = {
        "kind": "chunk",
        "session_id": sid,
        "track": track,
        "sequence": sequence,
        "path": str(path),
        "sha256": sha,
        "size_bytes": len(wav),
        "start_ms": start_ms,
        "duration_ms": duration_ms,
        "command_id": str(uuid.uuid5(uuid.UUID(sid), f"{track}:{sequence}:{sha}")),
    }
    from app.operational_limits import CAPTURE_DURATION_MS
    if type(start_ms) is not int or start_ms < 0 or start_ms + packet["duration_ms"] > CAPTURE_DURATION_MS:
        raise ValueError("Native duration limit reached")
    return packet


def validate_intent(directory, sid, value):
    directory = Path(directory).resolve(strict=True)
    sid = _session(sid)
    if isinstance(value, dict) and value.get("kind") == "native.chunk.intent.opus.v2":
        return _validate_opus_intent(directory, sid, value)
    if (
        not isinstance(value, dict)
        or set(value) != {"kind", "packet", "wav_b64", "intent_sha256"}
        or value["kind"] != "native.chunk.intent.v1"
    ):
        raise ValueError("Exact durable native intent required")
    core = {key: value[key] for key in ("kind", "packet", "wav_b64")}
    encoded = json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    if value["intent_sha256"] != hashlib.sha256(encoded).hexdigest():
        raise ValueError("Native intent packet/payload checksum differs")
    packet = value["packet"]
    if (
        not isinstance(packet, dict)
        or set(packet) != PACKET_KEYS
        or packet.get("kind") != "chunk"
        or packet.get("session_id") != sid
    ):
        raise ValueError("Native intent belongs to another or incomplete session")
    if not isinstance(value["wav_b64"], str):
        raise ValueError("Exact WAV payload required")
    try:
        wav = base64.b64decode(value["wav_b64"], validate=True)
    except (ValueError, TypeError, binascii.Error) as exc:
        raise ValueError("Invalid native WAV intent payload") from exc
    if not 44 < len(wav) <= MAX_WAV:
        raise ValueError("Intent WAV size outside explicit bound")
    try:
        with wave.open(io.BytesIO(wav), "rb") as source:
            if (
                source.getnchannels(),
                source.getsampwidth(),
                source.getframerate(),
                source.getcomptype(),
            ) != (1, 2, 16000, "NONE"):
                raise ValueError("Intent WAV PCM profile differs")
            frames = source.getnframes()
            raw = source.readframes(frames)
            if len(raw) != frames * 2:
                raise ValueError("Intent WAV frame payload is truncated")
    except (wave.Error, EOFError) as exc:
        raise ValueError("Intent WAV is not complete PCM") from exc
    rebuilt, expected = prepare(
        directory, sid, packet["track"], packet["sequence"], raw, packet["start_ms"]
    )
    if (
        packet != rebuilt
        or any(
            type(packet[key]) is not int
            for key in ("sequence", "size_bytes", "start_ms", "duration_ms")
        )
        or wav != expected
    ):
        raise ValueError(
            "Intent bytes, SHA, UUID5, packet or historical timecode disagree"
        )
    return packet, wav



def _validate_opus_intent(directory, sid, value):
    from scripts.audio_codec import opus_duration_ms
    if set(value) != {"kind", "packet", "wav_b64", "intent_sha256"}:
        raise ValueError("Exact compressed native intent required")
    core = {key: value[key] for key in ("kind", "packet", "wav_b64")}
    encoded = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    if value["intent_sha256"] != hashlib.sha256(encoded).hexdigest():
        raise ValueError("Native intent packet/payload checksum differs")
    packet = value["packet"]
    if not isinstance(packet, dict) or set(packet) != PACKET_KEYS or packet.get("session_id") != sid:
        raise ValueError("Incomplete compressed native packet")
    if packet["track"] not in {"mic", "system"} or type(packet["sequence"]) is not int or packet["sequence"] < 0:
        raise ValueError("Explicit native track and sequence required")
    payload = base64.b64decode(value["wav_b64"], validate=True)
    if not 0 < len(payload) <= MAX_WAV:
        raise ValueError("Compressed fragment exceeds bound")
    duration = opus_duration_ms(payload)
    if not 0 < duration <= 5000:
        raise ValueError("Compressed fragment duration exceeds bound")
    rebuilt = _packet(directory, sid, packet["track"], packet["sequence"], payload, packet["start_ms"], duration, "opus")
    if packet != rebuilt or any(type(packet[key]) is not int for key in ("sequence", "size_bytes", "start_ms", "duration_ms")):
        raise ValueError("Compressed bytes, packet or historical timecode disagree")
    return packet, payload


def _intent(directory, path, sid):
    path = _inside(directory, path)
    value = json.loads(_bounded(path, MAX_INTENT).decode("utf-8"))
    packet, wav = validate_intent(directory, sid, value)
    if path != Path(packet["path"]).with_suffix(".intent"):
        raise ValueError("Native intent filename does not match its packet")
    return packet, wav


class Limits:
    """Session bounds, distinct from the historical completed WAV quota.

    Storage is conservative logical bytes of ALL direct file names, including
    hard-linked pending names, failed attempts, preimages and consumer receipts.
    Exact payload admission is not an exclusive OS disk reservation.
    """

    def __init__(
        self,
        *,
        storage_bytes=3 * 1024**3,
        audio_bytes=512 * 1024**2,
        file_count=200000,
        intent_count=20000,
        intent_bytes=1024**3,
        reserve_bytes=128 * 1024**2,
    ):
        for name, value in locals().copy().items():
            if name == "self":
                continue
            if type(value) is not int or value < 0:
                raise ValueError("Strict native journal bound required")
            setattr(self, name, value)


def inventory(directory, limits):
    """Re-scan a concurrently published staging file; never omit its bytes.

    Only the two atomic-replace namespaces may disappear normally. Restart
    the complete quota inventory rather than silently dropping the vanished
    name and missing its newly published destination. Persistent churn,
    missing audio, unexpected names and permission failures remain failures.
    """
    directory = Path(directory).resolve(strict=True)
    for attempt in range(4):
        try:
            return _inventory_snapshot(directory, limits)
        except FileNotFoundError as error:
            missing = Path(error.filename) if isinstance(error.filename, str) else None
            if (error.errno != errno.ENOENT or missing is None
                    or missing.parent != directory
                    or re.fullmatch(r"(?:manifest|receipt)-[0-9a-f]{32}\.pending", missing.name) is None
                    or attempt == 3):
                raise


def _inventory_snapshot(directory, limits):
    """Bounded metadata admission before recovery reads or any mutation."""
    directory = Path(directory).resolve(strict=True)
    paths = []
    total = audio = intent_bytes = 0
    intents = []
    for path in directory.iterdir():
        if len(paths) >= limits.file_count:
            raise ValueError("Native journal file count limit reached")
        # iterdir yields direct children of the already canonical directory.
        # Read non-following metadata once; actual content I/O and every
        # mutation still pass through _inside at their existing authority gates.
        if path.parent != directory:
            raise ValueError("Native journal path is not an owned direct child")
        info = path.lstat()
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise ValueError("Native journal path is not an owned direct child")
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Native journal requires owned regular direct files")
        paths.append(path)
        total += info.st_size
        if total > limits.storage_bytes:
            raise ValueError("Native journal cumulative storage limit reached")
        if path.suffix in {".wav", ".ogg"}:
            audio += info.st_size
        if path.suffix == ".intent":
            intents.append(path)
            intent_bytes += info.st_size
            if (
                info.st_size > MAX_INTENT
                or len(intents) > limits.intent_count
                or intent_bytes > limits.intent_bytes
            ):
                raise ValueError(
                    "Native recovery cumulative intent admission limit reached"
                )
    if audio > limits.audio_bytes:
        raise ValueError("Native cumulative WAV quota reached")
    return {
        "paths": paths,
        "intents": sorted(intents),
        "bytes": total,
        "audio_bytes": audio,
    }


class Reservation:
    """Exact bounded operation payloads admitted before the first file open.

    A new exclusive hard-link publication retains TWO logical file names;
    replace retains ONE new name at peak alongside any previous manifest.
    File-system block/metadata allocation and concurrent external disk writes
    remain covered only by the free-space margin and actual I/O error handling.
    """

    def __init__(self, directory, work, ops, limits, *, new_wav_bytes=0):
        admitted = inventory(directory, limits)
        self.logical = sum(size * copies for size, copies in work)
        self.payload = sum(size for size, copies in work)
        self.names = sum(copies for size, copies in work)
        if admitted["bytes"] + self.logical > limits.storage_bytes:
            raise ValueError(
                "Native journal transaction exceeds cumulative storage quota"
            )
        if len(admitted["paths"]) + self.names > limits.file_count:
            raise ValueError("Native journal transaction exceeds file count quota")
        if admitted["audio_bytes"] + new_wav_bytes > limits.audio_bytes:
            raise ValueError("Native completed WAV quota reached")
        if work and ops.free_bytes(directory) < self.payload + limits.reserve_bytes:
            raise ValueError(
                "Native journal exact transaction exceeds free-space reserve"
            )

    def claim(self, size, copies):
        if size * copies > self.logical or size > self.payload or copies > self.names:
            raise ValueError("Native journal mutation exceeds admitted transaction")
        self.logical -= size * copies
        self.payload -= size
        self.names -= copies


def _pair_work(directory, packet, wav):
    path = _inside(directory, packet["path"])
    manifest = _inside(directory, path.with_suffix(".json"))
    work = []
    if path.exists():
        if _bounded(path, MAX_WAV) != wav:
            raise ValueError("Existing native WAV differs; original retained")
    else:
        work.append((len(wav), 2))
    previous = _bounded(manifest, MAX_MANIFEST) if manifest.is_file() else None
    matches = False
    if previous is not None:
        try:
            decoded = json.loads(previous.decode("utf-8"))
            matches = (
                isinstance(decoded, dict)
                and decoded == packet
                and all(
                    type(decoded[key]) is int
                    for key in ("sequence", "size_bytes", "start_ms", "duration_ms")
                )
            )
        except (ValueError, UnicodeError):
            pass
    encoded = json.dumps(packet, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_MANIFEST:
        raise ValueError("Native manifest exceeds bound")
    if not matches:
        if previous is not None:
            work.append((len(previous), 2))
        work.append((len(encoded), 1))
    return work, not path.exists()


def _materialize(directory, packet, wav, ops, authorize, reservation):
    path = _inside(directory, packet["path"])
    manifest = _inside(directory, path.with_suffix(".json"))
    authorize()
    if path.exists():
        if _bounded(path, MAX_WAV) != wav:
            raise ValueError("Existing native WAV differs; original retained")
    else:
        _durable_new(directory, path, wav, "wav", ops, reservation)
    authorize()
    previous = _bounded(manifest, MAX_MANIFEST) if manifest.is_file() else None
    if previous is not None:
        try:
            decoded = json.loads(previous.decode("utf-8"))
            matches = (
                isinstance(decoded, dict)
                and decoded == packet
                and all(
                    type(decoded[key]) is int
                    for key in ("sequence", "size_bytes", "start_ms", "duration_ms")
                )
            )
        except (ValueError, UnicodeError):
            matches = False
        if matches:
            return dict(packet)
        retained = _inside(
            directory,
            manifest.with_name(
                manifest.name + ".previous-" + uuid.uuid4().hex + ".preimage"
            ),
        )
        _durable_new(directory, retained, previous, "preimage", ops, reservation)
    authorize()
    encoded = json.dumps(packet, ensure_ascii=False, allow_nan=False).encode("utf-8")
    _durable_replace(directory, manifest, encoded, "manifest", ops, reservation)
    if json.loads(_bounded(manifest, MAX_MANIFEST).decode("utf-8")) != packet:
        raise OSError("Published native manifest readback differs")
    return dict(packet)


def commit_chunk(
    directory, sid, track, sequence, raw, start_ms, *, ops=None, limits=None, codec="wav"
):
    """Producer-owned directory; exact transaction before any disk allocation."""
    directory = Path(directory).resolve(strict=True)
    ops = ops or FileOps()
    limits = limits or Limits()
    # Admit existing cumulative files BEFORE allocating the bounded WAV/base64.
    admitted = inventory(directory, limits)
    packet, wav = prepare(directory, sid, track, sequence, raw, start_ms, codec=codec)
    path = Path(packet["path"])
    intent = path.with_suffix(".intent")
    encoded = None
    if intent.exists():
        frozen, data = _intent(directory, intent, sid)
        if frozen != packet or data != wav:
            raise ValueError("Intent collision; frozen capture timecode retained")
    else:
        if path.exists() or path.with_suffix(".json").exists():
            raise ValueError(
                "Historical fragment without exact intent; replay first, no guessed timecode"
            )
        if len(admitted["intents"]) + 1 > limits.intent_count:
            raise ValueError("Native intent count quota reached")
        value = {
            "kind": "native.chunk.intent.opus.v2" if codec == "opus" else "native.chunk.intent.v1",
            "packet": packet,
            "wav_b64": base64.b64encode(wav).decode("ascii"),
        }
        core = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        value["intent_sha256"] = hashlib.sha256(core).hexdigest()
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_INTENT:
            raise ValueError("Intent exceeds explicit bound")
        if (
            sum(p.stat().st_size for p in admitted["intents"]) + len(encoded)
            > limits.intent_bytes
        ):
            raise ValueError("Native cumulative intent byte quota reached")
    work, new_wav = _pair_work(directory, packet, wav)
    if encoded is not None:
        work.insert(0, (len(encoded), 2))
    reservation = Reservation(
        directory, work, ops, limits, new_wav_bytes=len(wav) if new_wav else 0
    )
    if encoded is not None:
        _durable_new(directory, intent, encoded, "intent", ops, reservation)
    return _materialize(directory, packet, wav, ops, lambda: None, reservation)


def iter_reconcile(directory, sid, *, authorize, ops=None, limits=None):
    """Bounded cumulative admission, then one pair before each consumer ACK.

    The consumer MUST persist each yielded packet before requesting the next.
    Memory holds only one bounded intent/WAV. No inference of orphan timecodes.
    """
    directory = Path(directory).resolve(strict=True)
    sid = _session(sid)
    ops = ops or FileOps()
    limits = limits or Limits()
    authorize()
    admitted = inventory(directory, limits)
    for path in admitted["paths"]:
        if (
            path.suffix in {".wav", ".ogg"}
            and not path.with_suffix(".json").is_file()
            and not path.with_suffix(".intent").is_file()
        ):
            raise ValueError(
                "Unrecoverable historical native orphan retained: " + path.name
            )
    for path in admitted["intents"]:
        authorize()
        packet, wav = _intent(directory, path, sid)
        work, new_wav = _pair_work(directory, packet, wav)
        reservation = Reservation(
            directory, work, ops, limits, new_wav_bytes=len(wav) if new_wav else 0
        )
        result = _materialize(directory, packet, wav, ops, authorize, reservation)
        authorize()
        yield result


def reconcile(directory, sid, *, authorize, ops=None, limits=None):
    """Private helper test convenience; product uses progressive iter_reconcile."""
    return list(
        iter_reconcile(directory, sid, authorize=authorize, ops=ops, limits=limits)
    )


def drain_buffer(state, flush):
    """Commit full fixed fragments before short resampler tail; fail retains tail."""
    if state["buffer"] and state["start_ms"] is None:
        raise ValueError("Buffered PCM lacks actual start time")
    while len(state["buffer"]) >= MAX_RAW:
        flush(MAX_RAW)
    if state["buffer"]:
        flush(len(state["buffer"]))


def commit_buffer(state, track, amount, persist, acknowledge):
    """Consume only after durable pair and successful notification; exact retry IDs."""
    if type(amount) is not int or not 0 < amount <= len(state["buffer"]):
        raise ValueError("Invalid native buffered commit size")
    raw = bytes(state["buffer"][:amount])
    start = state["start_ms"]
    sequence = state["sequence"]
    packet = persist(track, raw, start)
    if (
        packet["track"],
        packet["sequence"],
        packet["start_ms"],
        packet["duration_ms"],
    ) != (track, sequence, start, len(raw) // 32):
        raise ValueError("Committed native packet differs from buffered capture")
    acknowledge(packet)
    del state["buffer"][:amount]
    state["sequence"] = sequence + 1
    state["start_ms"] = start + packet["duration_ms"]
    return packet


MAX_RECEIPT = 16 * 1024


def publish_receipt(
    directory, sid, packet, receipt, *, authorize, ops=None, limits=None
):
    """Publish only the actual SQL-confirmed receipt, within native-folder quota.

    SQL may already be committed when quota/headroom refuses. No fake ACK,
    counter advancement, deletion or WAV rewrite is permitted. Caller retries
    its real idempotent store_chunk command after space/authority is available.
    """
    authorize()
    directory = Path(directory).resolve(strict=True)
    sid = _session(sid)
    ops = ops or FileOps()
    limits = limits or Limits()
    inventory(directory, limits)
    path = _inside(directory, packet["path"])
    acknowledged = _inside(directory, path.with_suffix(".receipt.json"))
    accepted = {
        "track": packet["track"],
        "seq": packet["sequence"],
        "sha256": packet["sha256"],
        "size_bytes": packet["size_bytes"],
    }
    if (
        packet.get("session_id") != sid
        or type(receipt) is not dict
        or receipt.get("acknowledged") is not True
        or receipt.get("session_id") != sid
        or receipt.get("accepted_chunk") != accepted
    ):
        raise ValueError("Exact current SQL-confirmed native receipt required")
    encoded = json.dumps(receipt).encode("utf-8")
    if len(encoded) > MAX_RECEIPT:
        raise ValueError("Native SQL receipt exceeds publication bound")
    previous = _bounded(acknowledged, MAX_RECEIPT) if acknowledged.is_file() else None
    if previous == encoded:
        authorize()
        return  # Real SQL confirmed before caller reached this helper.
    work = [(len(encoded), 1)]
    if previous is not None:
        work.insert(0, (len(previous), 2))
    reservation = Reservation(directory, work, ops, limits)
    if previous is not None:
        authorize()
        retained = _inside(
            directory,
            path.with_name(
                path.stem + ".previous-" + uuid.uuid4().hex + ".receipt.json"
            ),
        )
        _durable_new(
            directory, retained, previous, "receipt-preimage", ops, reservation
        )
    authorize()
    _durable_replace(directory, acknowledged, encoded, "receipt", ops, reservation)
    if _bounded(acknowledged, MAX_RECEIPT) != encoded:
        raise OSError("Published SQL receipt readback differs")
    authorize()
