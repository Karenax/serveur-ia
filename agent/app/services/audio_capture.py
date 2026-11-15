"""Codec-aware preparation of durable audio fragments; no device acquisition."""
from __future__ import annotations
from app.operational_limits import CAPTURE_BYTES, CAPTURE_DURATION_MS

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import wave



MAX_SESSION_MS = CAPTURE_DURATION_MS
MAX_SESSION_BYTES = CAPTURE_BYTES


@dataclass(frozen=True)
class PreparedAudio:
    path: Path
    offset_ms: int
    clip_start_ms: int
    clip_end_ms: int | None
    assembled: bool
    context_path: Path | None = None
    context_ms: int = 0


def _value(row, name):
    return row[name] if isinstance(row, dict) else getattr(row, name)


def stored_path(row, storage_root: Path) -> Path:
    path = Path(_value(row, "storage_path")).resolve()
    if not path.is_relative_to(storage_root.resolve()) or not path.is_file():
        raise ValueError("Fragment audio absent du stockage autorisé")
    if path.stat().st_size != _value(row, "size_bytes"):
        raise ValueError("Taille du fragment audio modifiée")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != _value(row, "sha256"):
        raise ValueError("Empreinte du fragment audio modifiée")
    return path


def wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as source:
        if source.getcomptype() != "NONE" or source.getnchannels() not in {1, 2}:
            raise ValueError("WAV PCM mono ou stéréo attendu")
        if not 8000 <= source.getframerate() <= 96000 or source.getsampwidth() not in {1, 2, 3, 4}:
            raise ValueError("Format PCM non pris en charge")
        duration = round(source.getnframes() * 1000 / source.getframerate())
        if duration <= 0 or duration > MAX_SESSION_MS:
            raise ValueError("Durée audio invalide ou supérieure à douze heures")
        return duration


def prepare_chunk(chunk, earlier, *, storage_root: Path,
                  derived_root: Path, with_pcm_context: bool = False) -> PreparedAudio:
    """Reassemble headerless MediaRecorder chunks before decoding.

WAV and full containers are decoded independently for final mixing. Live PCM
decoding can prepend500ms from a contiguous previous fragment. A cumulative container is
never advertised as a standalone fragment, and gaps are never filled by silence.
"""
    start = int(_value(chunk, "start_ms"))
    duration = int(_value(chunk, "duration_ms"))
    if start < 0 or duration < 0 or start + duration > MAX_SESSION_MS:
        raise ValueError("Horodatage audio hors limites")
    path = stored_path(chunk, storage_root)
    with path.open("rb") as source:
        header = source.read(12)
    mime = str(_value(chunk, "mime_type")).split(";", 1)[0].lower()
    is_wav = header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    if is_wav:
        wav_duration_ms(path)
        if with_pcm_context and int(_value(chunk, "sequence")) > 0:
            previous = next((row for row in earlier if
                _value(row, "session_id") == _value(chunk, "session_id") and
                _value(row, "track") == _value(chunk, "track") and
                int(_value(row, "sequence")) == int(_value(chunk, "sequence")) - 1), None)
            if previous is not None and abs(int(_value(previous, "start_ms")) +
                                           int(_value(previous, "duration_ms")) - start) <= 50:
                previous_path = stored_path(previous, storage_root)
                with wave.open(str(previous_path), "rb") as before, wave.open(str(path), "rb") as current:
                    if before.getparams()[:3] == current.getparams()[:3] and before.getcomptype() == "NONE":
                        rate = current.getframerate()
                        count = min(before.getnframes(), rate // 2)
                        before.setpos(before.getnframes() - count)
                        raw = before.readframes(count) + current.readframes(current.getnframes())
                        derived = derived_root.resolve()
                        if not derived.is_relative_to(storage_root.resolve()):
                            raise ValueError("Stockage dérivé hors du périmètre autorisé")
                        derived.mkdir(parents=True, exist_ok=True)
                        identity = hashlib.sha256(f"{_value(chunk, 'session_id')}:{_value(chunk, 'track')}:pcm-context".encode()).hexdigest()
                        destination = derived / f"{identity}.wav"
                        temporary = destination.with_suffix(".part.wav")
                        with wave.open(str(temporary), "wb") as target:
                            target.setparams(current.getparams())
                            target.writeframes(raw)
                        with temporary.open("r+b") as target:
                            os.fsync(target.fileno())
                        temporary.replace(destination)
                        overlap = round(count * 1000 / rate)
                        return PreparedAudio(destination, max(0, start - overlap), 0,
                                             overlap + (duration or wav_duration_ms(path)), True)
    is_webm = mime in {"audio/webm", "video/webm"}
    is_mp4 = mime in {"audio/mp4", "video/mp4"}
    is_ogg = mime in {"audio/ogg", "audio/opus"}
    has_header = (is_webm and header.startswith(b"\x1aE\xdf\xa3")) or \
                 (is_mp4 and header[4:8] == b"ftyp") or \
                 (is_ogg and header.startswith(b"OggS"))
    sequence = int(_value(chunk, "sequence"))
    if with_pcm_context and is_ogg and has_header and sequence > 0:
        previous = next((row for row in earlier if
            _value(row, "session_id") == _value(chunk, "session_id") and
            _value(row, "track") == _value(chunk, "track") and
            int(_value(row, "sequence")) == sequence - 1), None)
        if previous is not None and abs(int(_value(previous, "start_ms")) +
                                       int(_value(previous, "duration_ms")) - start) <= 50:
            previous_path = stored_path(previous, storage_root)
            # Native Opus files are independent, bounded five-second streams.
            # Keep the original compressed bytes; decode the short overlap in
            # the speech worker rather than persisting a derived PCM file.
            if previous_path.stat().st_size <= 160044:
                from scripts.audio_codec import opus_duration_ms
                try:
                    previous_duration = opus_duration_ms(previous_path.read_bytes())
                except ValueError:
                    previous_duration = 0
                if 0 < previous_duration <= 5000:
                    overlap = min(previous_duration, start)
                    return PreparedAudio(path, start - overlap, 0, overlap + duration,
                                         True, previous_path, overlap)
    if is_wav or has_header or not (is_webm or is_mp4 or is_ogg) or sequence == 0:
        return PreparedAudio(path, start, 0, duration or None, False)
    track = _value(chunk, "track")
    session = _value(chunk, "session_id")
    rows = [row for row in earlier if _value(row, "session_id") == session
            and _value(row, "track") == track and int(_value(row, "sequence")) <= sequence]
    if not any(_value(row, "id") == _value(chunk, "id") for row in rows):
        rows.append(chunk)
    rows.sort(key=lambda row: _value(row, "sequence"))
    if [int(_value(row, "sequence")) for row in rows] != list(range(sequence + 1)):
        raise ValueError("Fragments audio manquants ; attendre leur réception")
    if any(str(_value(row, "mime_type")).split(";", 1)[0].lower() != mime for row in rows):
        raise ValueError("Le codec a changé ; ouvrir une nouvelle piste de capture")
    paths = [stored_path(row, storage_root) for row in rows]
    if sum(source.stat().st_size for source in paths) > MAX_SESSION_BYTES:
        raise ValueError("Volume audio cumulé supérieur à la limite de séance")
    derived = derived_root.resolve()
    if not derived.is_relative_to(storage_root.resolve()):
        raise ValueError("Stockage dérivé hors du périmètre autorisé")
    derived.mkdir(parents=True, exist_ok=True)
    # One replaceable decode cache per track, rather than one cumulative copy
    # per fragment (which would grow quadratically during a long session).
    identity = hashlib.sha256(f"{session}:{track}".encode()).hexdigest()
    destination = derived / f"{identity}.{'webm' if is_webm else 'mp4' if is_mp4 else 'ogg'}"
    temporary = destination.with_suffix(destination.suffix + ".part")
    with temporary.open("wb") as output:
        for source in paths:
            with source.open("rb") as incoming:
                while data := incoming.read(1024 * 1024):
                    output.write(data)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(destination)
    return PreparedAudio(destination, 0, max(0, start - 500),
                         start + duration if duration else None, True)
