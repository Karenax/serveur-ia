"""Pure planning and whole-word provenance for explicit batch consolidation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import hashlib
import json
import math
import re

CONTRACT = "batch_group_pcm_v1"
SAMPLE_RATE = 16000
MAX_GROUP_FRAMES = 25 * SAMPLE_RATE
TARGET_GROUP_FRAMES = 20 * SAMPLE_RATE
MAX_GROUP_INPUT_BYTES = MAX_GROUP_FRAMES * 2 + 100 * 4096


class GroupRefused(ValueError):
    """Keep this diagnostic and use the unchanged individual path if admitted."""


@dataclass(frozen=True)
class Member:
    id: str
    session_id: str
    track: str
    sequence: int
    path: str
    sha256: str
    size_bytes: int
    start_ms: int
    duration_ms: int
    decoded_frames: int
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    standalone_pcm_wav: bool = True
    effective_metadata_verified: bool = False
    existing_segments: bool = False


def integer(value, *, minimum=0):
    return type(value) is int and value >= minimum


def eligible(member):
    numbers = (member.sequence, member.start_ms)
    positive = (member.size_bytes, member.duration_ms, member.decoded_frames)
    if not all(integer(x) for x in numbers) or not all(integer(x, minimum=1) for x in positive):
        return "unknown_or_invalid_effective_metadata"
    if not all(isinstance(x, str) and x for x in (member.id, member.session_id, member.path)):
        return "missing_source_identity"
    if not isinstance(member.sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", member.sha256):
        return "invalid_source_hash"
    if member.track not in {"mic", "system"}:
        return "unsupported_track"
    if (not all(integer(x, minimum=1) for x in (member.sample_rate, member.channels, member.sample_width))
            or (member.sample_rate, member.channels, member.sample_width) != (16000, 1, 2)):
        return "unsupported_PCM_format"
    if member.standalone_pcm_wav is not True or member.effective_metadata_verified is not True:
        return "standalone_effective_PCM_not_verified"
    if member.existing_segments is not False:
        return "existing_canonical_segments"
    if member.decoded_frames != member.duration_ms * 16:
        return "declared_effective_duration_differs"
    if member.decoded_frames > MAX_GROUP_FRAMES:
        return "complete_source_exceeds_group_limit"
    if member.size_bytes > MAX_GROUP_INPUT_BYTES:
        return "complete_source_exceeds_input_byte_limit"
    return None


def _source(member):
    return {key: value for key, value in asdict(member).items()
            if key not in {"existing_segments", "effective_metadata_verified"}}


@dataclass(frozen=True)
class Group:
    members: tuple[Member, ...]

    @property
    def frames(self):
        return sum(member.decoded_frames for member in self.members)

    @property
    def offset_ms(self):
        return self.members[0].start_ms

    @property
    def manifest(self):
        return {"contract": CONTRACT, "members": [_source(member) for member in self.members]}

    @property
    def id(self):
        raw = json.dumps(self.manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class Individual:
    member: Member
    reason: str


def validate_group(group):
    members = group.members
    if (not 2 <= len(members) <= 100 or group.frames > MAX_GROUP_FRAMES
            or sum(member.size_bytes for member in members) > MAX_GROUP_INPUT_BYTES):
        raise GroupRefused("invalid_group_size")
    if len({member.id for member in members}) != len(members):
        raise GroupRefused("duplicate_source_identity")
    for index, member in enumerate(members):
        reason = eligible(member)
        if reason:
            raise GroupRefused(reason)
        if index:
            previous = members[index - 1]
            if (member.session_id, member.track) != (previous.session_id, previous.track):
                raise GroupRefused("different_session_or_track")
            if member.sequence != previous.sequence + 1:
                raise GroupRefused("nonconsecutive_sequence")
            if member.start_ms * 16 != previous.start_ms * 16 + previous.decoded_frames:
                raise GroupRefused("gap_or_overlap")
    return group


def plan_groups(members):
    """Preserve selected order. Never split a source or erase timeline gaps."""
    items = tuple(members)
    if len({member.id for member in items}) != len(items):
        raise GroupRefused("duplicate_selected_source")
    result, pending = [], []

    def flush():
        if len(pending) >= 2:
            result.append(validate_group(Group(tuple(pending))))
        elif pending:
            result.append(Individual(pending[0], "single_complete_source"))
        pending.clear()

    for member in items:
        reason = eligible(member)
        if reason:
            flush()
            result.append(Individual(member, reason))
            continue
        if pending:
            previous = pending[-1]
            contiguous = (member.session_id, member.track, member.sequence, member.start_ms * 16) == (
                previous.session_id, previous.track, previous.sequence + 1,
                previous.start_ms * 16 + previous.decoded_frames)
            if (not contiguous or sum(x.decoded_frames for x in pending) + member.decoded_frames > MAX_GROUP_FRAMES
                    or sum(x.size_bytes for x in pending) + member.size_bytes > MAX_GROUP_INPUT_BYTES):
                flush()
        pending.append(member)
        if sum(x.decoded_frames for x in pending) >= TARGET_GROUP_FRAMES:
            flush()
    flush()
    return tuple(result)


def group_from_manifest(manifest):
    if not isinstance(manifest, dict) or set(manifest) != {"contract", "members"} or manifest["contract"] != CONTRACT:
        raise GroupRefused("unsupported_manifest")
    rows = manifest["members"]
    if not isinstance(rows, list) or not 2 <= len(rows) <= 100:
        raise GroupRefused("invalid_members")
    allowed = set(Member.__dataclass_fields__) - {"effective_metadata_verified", "existing_segments"}
    if any(not isinstance(row, dict) or set(row) != allowed for row in rows):
        raise GroupRefused("invalid_member_shape")
    group = Group(tuple(Member(**row, effective_metadata_verified=True) for row in rows))
    return validate_group(group)


def _native_frame(value):
    if type(value) not in {int, float} or not math.isfinite(value):
        raise GroupRefused("nonfinite_native_timestamp")
    return Decimal(str(value)) * SAMPLE_RATE


def map_words(group, retained_words):
    """Return no publishable mapping if any retained word is ambiguous."""
    validate_group(group)
    if not isinstance(retained_words, list) or len(retained_words) > 20000:
        raise GroupRefused("invalid_native_words")
    regions, frame = [], 0
    for member in group.members:
        regions.append((member, frame, frame + member.decoded_frames))
        frame += member.decoded_frames
    admitted, previous_end, previous_ordinal = [], Decimal(0), None
    for item in retained_words:
        if not isinstance(item, dict):
            raise GroupRefused("invalid_native_word")
        segment, word = item.get("segment_ordinal"), item.get("word_ordinal")
        if not integer(segment) or not integer(word):
            raise GroupRefused("invalid_native_ordinal")
        ordinal = (segment, word)
        if previous_ordinal is not None and ordinal <= previous_ordinal:
            raise GroupRefused("native_order_changed")
        text = item.get("word")
        if not isinstance(text, str) or not text.strip() or len(text) > 10000:
            raise GroupRefused("invalid_word_text")
        start, end = _native_frame(item.get("start")), _native_frame(item.get("end"))
        if not 0 <= start < end <= group.frames or start < previous_end:
            raise GroupRefused("word_out_of_range_or_nonpositive_or_overlapping")
        targets = [member for member, begin, finish in regions if begin <= start < end <= finish]
        if len(targets) != 1:
            raise GroupRefused("word_crosses_source_boundary")
        admitted.append((targets[0], item))
        previous_end, previous_ordinal = end, ordinal
    slices = []
    for member, item in admitted:
        key = (member.id, item["segment_ordinal"])
        if slices and slices[-1]["_key"] == key:
            slices[-1]["words"].append(dict(item))
        else:
            slices.append({"_key": key, "chunk_id": member.id, "track": member.track,
                           "words": [dict(item)]})
    counts, result = {}, []
    for item in slices:
        chunk_id = item["chunk_id"]
        ordinal = counts.get(chunk_id, 0)
        counts[chunk_id] = ordinal + 1
        words = item["words"]
        begin_ms = group.offset_ms + round(words[0]["start"] * 1000)
        end_ms = group.offset_ms + round(words[-1]["end"] * 1000)
        member = next(member for member in group.members if member.id == chunk_id)
        if not member.start_ms <= begin_ms < end_ms <= member.start_ms + member.duration_ms:
            raise GroupRefused("rounded_native_interval_not_positive_or_contained")
        result.append({"id": "live-" + hashlib.sha256(f"{chunk_id}:{ordinal}".encode()).hexdigest(),
                       "chunk_id": chunk_id, "track": item["track"], "speaker": item["track"],
                       "start_ms": begin_ms,
                       "end_ms": end_ms,
                       "text": "".join(word["word"] for word in words).strip(),
                       "native_words": words})
    return result


def publication_guard(group, *, current_members, existing_ids, cancel_requested=False):
    """Pure last-check contract; a writer transaction still owns publication."""
    if cancel_requested:
        raise GroupRefused("cancelled_before_publication")
    if tuple(current_members) != group.members:
        raise GroupRefused("source_or_human_snapshot_changed")
    if any(member.existing_segments for member in current_members) or existing_ids:
        raise GroupRefused("canonical_segment_collision")
    return True
