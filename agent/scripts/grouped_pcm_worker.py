"""Private group operation; imports no model, process, database or UI at import."""
from __future__ import annotations

from array import array
from dataclasses import asdict, is_dataclass
import hashlib
from io import BytesIO
import math
from pathlib import Path
import wave

try:
    from .grouped_pcm_core import CONTRACT, GroupRefused, group_from_manifest, map_words
except ImportError:  # Direct script entry point in the isolated resident.
    from grouped_pcm_core import CONTRACT, GroupRefused, group_from_manifest, map_words


def native_json_number(value):
    """Use the numeric primitive JSON will transport, without changing its value."""
    if isinstance(value, bool):
        raise GroupRefused("nonfinite_native_timestamp")
    if isinstance(value, int):
        return int.__int__(value)
    if isinstance(value, float):
        number = float.__float__(value)
        if math.isfinite(number):
            return number
    raise GroupRefused("nonfinite_native_timestamp")


def transcribe_group(model, request, storage_root, decode_audio, canonical_transcribe, *,
                     check_cancel=lambda: None, loaded_profile=None):
    """One model call; native full-word provenance or an explicit refusal."""
    check_cancel()
    actual_device = str(getattr(getattr(model, "model", None), "device", "")).lower()
    actual_compute = str(getattr(getattr(model, "model", None), "compute_type", "")).lower()
    if actual_device != "cpu" or actual_compute not in {"int8", "int8_float32"}:
        raise GroupRefused("loaded_CPU_int8_family_not_observed")
    if request.get("op") != CONTRACT:
        raise GroupRefused("unsupported_operation")
    group = group_from_manifest(request.get("manifest"))
    if request.get("group_id") != group.id:
        raise GroupRefused("group_identity_differs")
    storage = Path(storage_root).resolve()
    pcm, metadata = array("f"), []
    for member in group.members:
        check_cancel()
        path = Path(member.path).resolve()
        if not path.is_relative_to(storage) or not path.is_file():
            raise GroupRefused("source_outside_storage_or_missing")
        if path.stat().st_size != member.size_bytes:
            raise GroupRefused("source_size_or_hash_changed")
        frozen = path.read_bytes()
        if len(frozen) != member.size_bytes or hashlib.sha256(frozen).hexdigest() != member.sha256:
            raise GroupRefused("source_size_or_hash_changed")
        with wave.open(BytesIO(frozen), "rb") as source:
            params = (source.getnchannels(), source.getsampwidth(), source.getframerate(),
                      source.getnframes(), source.getcomptype())
        if params != (1, 2, 16000, member.decoded_frames, "NONE"):
            raise GroupRefused("source_effective_PCM_changed")
        samples = decode_audio(BytesIO(frozen), sampling_rate=16000)
        if len(samples) != member.decoded_frames or getattr(samples, "dtype", "float32") != "float32":
            raise GroupRefused("decoded_PCM_shape_or_type_changed")
        if getattr(samples, "ndim", 1) != 1:
            raise GroupRefused("decoded_PCM_dimension_changed")
        raw = samples.tobytes()
        if len(raw) != member.decoded_frames * 4:
            raise GroupRefused("decoded_PCM_bytes_changed")
        own = array("f")
        own.frombytes(raw)
        pcm.extend(own)
        metadata.append({"chunk_id": member.id, "frames": len(samples),
                         "file_sha256": member.sha256,
                         "pcm_sha256": hashlib.sha256(raw).hexdigest()})
    check_cancel()
    native_parts, options, native_options = [], {}, {}

    class ObservedModel:
        def transcribe(self, samples, **kwargs):
            options.update(kwargs)
            parts, info = model.transcribe(samples, **kwargs)
            if not is_dataclass(info.transcription_options):
                raise GroupRefused("native_options_not_observed")
            native_options.update(asdict(info.transcription_options))

            def observed():
                for ordinal, part in enumerate(parts):
                    check_cancel()
                    native_parts.append((ordinal, part))
                    yield part
            return observed(), info

    # NumPy is required only when an actual numpy decode was supplied. No ASR import.
    if type(samples).__module__.split(".")[0] == "numpy":
        import numpy as np
        grouped_samples = np.frombuffer(pcm, dtype=np.float32)
    else:
        grouped_samples = pcm  # stdlib synthetic fake-decoder tests only
    result = canonical_transcribe(ObservedModel(), grouped_samples,
        {"offset_ms": group.offset_ms, "clip_start_ms": 0, "keep_from_ms": group.offset_ms,
         "track": group.members[0].track})
    check_cancel()
    retained, native, native_segments = [], [], []
    for ordinal, part in native_parts:
        words = list(part.words or [])
        emitted = [word for word in words if group.offset_ms + (word.start + word.end) * 500 >= group.offset_ms]
        text = "".join(word.word for word in emitted).strip()
        keep = bool(text and part.no_speech_prob <= .85)
        native_segments.append({"segment_ordinal": ordinal,
                                "start": native_json_number(part.start), "end": native_json_number(part.end),
                                "text": part.text, "no_speech_prob": native_json_number(part.no_speech_prob),
                                "retained_by_canonical_filter": keep})
        for index, word in enumerate(words):
            item = {"segment_ordinal": ordinal, "word_ordinal": index,
                    "start": native_json_number(word.start), "end": native_json_number(word.end), "word": word.word}
            native.append({**item, "retained_by_canonical_filter": keep and word in emitted})
            if keep and word in emitted:
                retained.append(item)
    rebuilt = " ".join("".join(item["word"] for item in retained if item["segment_ordinal"] == ordinal).strip()
                       for ordinal, part in native_parts if any(item["segment_ordinal"] == ordinal for item in retained))
    if rebuilt != " ".join(item["text"] for item in result["segments"]):
        raise GroupRefused("retained_native_words_differ_from_canonical_text")
    if result["duration_ms"] * 16 != group.frames:
        raise GroupRefused("canonical_duration_differs")
    for member in group.members:
        check_cancel()
        path = Path(member.path).resolve()
        if (not path.is_relative_to(storage) or not path.is_file()
                or path.stat().st_size != member.size_bytes
                or hashlib.sha256(path.read_bytes()).hexdigest() != member.sha256):
            raise GroupRefused("source_changed_during_group")
    try:
        mapped = map_words(group, retained)
        status, refusal = "mapped", None
    except GroupRefused as exc:
        mapped, status, refusal = [], "refused", str(exc)
    if any(not math.isfinite(float(word[key])) for word in retained for key in ("start", "end")):
        status, refusal, mapped = "refused", "nonfinite_native_timestamp", []
    return {"contract": CONTRACT, "group_id": group.id, "duration_ms": result["duration_ms"],
            "offset_ms": group.offset_ms, "language": result["language"],
            "source_pcm_metadata": metadata, "grouped_frames": len(pcm),
            "grouped_pcm_sha256": hashlib.sha256(pcm.tobytes()).hexdigest(),
            "effective_transcribe_options": options, "native_transcription_options": native_options,
            "loaded_model_profile": {**(loaded_profile or {}), "actual_device": actual_device,
                                     "actual_compute_type": actual_compute},
            "native_words": native, "native_segments": native_segments,
            "retained_words": retained, "canonical_segments": result["segments"],
            "mapping_status": status, "mapping_refusal": refusal, "segments": mapped,
            "production_publication_performed": False}
