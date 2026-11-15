"""Real SQLite transaction tests on fictitious stores, with fake ASR only."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest
from sqlalchemy import select

from app.meeting_session_models import (
    LiveTranscriptSegment,
    MeetingAudioChunk,
    MeetingSessionCommand,
)
from app.services import grouped_batch as grouped, session_batch_transcription as batch
from app.services import meeting_sessions as sessions
from app.services.settings_service import save_section
from scripts.grouped_pcm_core import map_words
from scripts.grouped_response_evidence import EXPECTED_OPTIONS, NATIVE_OPTIONS
from tests.test_session_batch_transcription import (
    action,
    harness as harness_fixture,
    stores as stores_fixture,
)
from tests.test_meeting_sessions import create, chunk, command, content, wav

stores = stores_fixture
harness = harness_fixture


def prepare(db, tracks=("mic",), count=2, duration_ms=1000):
    save_section(
        db,
        "foresight",
        {
            "enabled": True,
            "live_transcription_enabled": False,
            "grouped_batch_transcription_enabled": True,
        },
    )
    row = create(db, kind="note")
    sid = row["id"]
    for track in tracks:
        for i in range(count):
            chunk(
                db,
                sid,
                i,
                track=track,
                raw=wav(samples=duration_ms * 16, sample=i + 3),
                start_ms=i * duration_ms,
                duration_ms=duration_ms,
            )
    row = command(
        db,
        sid,
        "notes",
        sessions.get_session(db, sid).revision,
        title="Humain",
        content=content("Conserver la décision humaine."),
    )
    return command(db, sid, "finalize", row["revision"])


@pytest.fixture
def profile(tmp_path, monkeypatch):
    from app.services import live_speech

    models = tmp_path / "models"
    model = models / "fake-medium"
    model.mkdir(parents=True)
    (model / "model.bin").write_bytes(b"NOT A REAL MODEL: FICTITIOUS TEST ONLY")
    (models / "models.json").write_text(
        json.dumps(
            {"model": "fictional-medium", "whisper": str(model), "cpu_threads": 4}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        live_speech, "runtime_paths", lambda: (Path(sys.executable), models)
    )
    monkeypatch.delenv("PB_SPEECH_THREADS", raising=False)
    return models


class GroupResident:
    process = None

    def __init__(self, profile, callback=None, refusal=False):
        self.profile = profile
        self.callback = callback
        self.refusal = refusal
        self.calls = []
        self.closed = False

    def transcribe_group(self, group, **kwargs):
        self.calls.append(group)
        words = []
        offset = 0
        for i, member in enumerate(group.members):
            start = (offset + 100) / 1000
            end = (offset + 800) / 1000
            if self.refusal and i == 0:
                start, end = (offset + 990) / 1000, (offset + 1010) / 1000
            words.append(
                {
                    "segment_ordinal": 0,
                    "word_ordinal": i,
                    "start": start,
                    "end": end,
                    "word": f" Valeur{i}.",
                }
            )
            offset += member.duration_ms
        canonical = [
            {
                "start_ms": group.offset_ms + round(words[0]["start"] * 1000),
                "end_ms": group.offset_ms + round(words[-1]["end"] * 1000),
                "text": "".join(w["word"] for w in words).strip(),
                "speaker": group.members[0].track,
            }
        ]
        try:
            mapped = map_words(group, words)
            state, reason = "mapped", None
        except ValueError as exc:
            mapped, state, reason = [], "refused", str(exc)
        if self.callback:
            self.callback(group)
        return {
            "kind": "result",
            "contract": "batch_group_pcm_v1",
            "group_id": group.id,
            "duration_ms": offset,
            "grouped_frames": group.frames,
            "offset_ms": group.offset_ms,
            "language": "fr",
            "source_pcm_metadata": [
                {
                    "chunk_id": m.id,
                    "frames": m.decoded_frames,
                    "file_sha256": m.sha256,
                    "pcm_sha256": "b" * 64,
                }
                for m in group.members
            ],
            "grouped_pcm_sha256": "c" * 64,
            "effective_transcribe_options": deepcopy(EXPECTED_OPTIONS),
            "native_transcription_options": deepcopy(NATIVE_OPTIONS),
            "loaded_model_profile": {
                "model": self.profile["model"],
                "model_path": self.profile["model_directory"],
                "cpu_threads": 4,
                "runtime_version": "1.2.1",
                "actual_device": "cpu",
                "actual_compute_type": "int8_float32",
            },
            "native_words": [
                {**w, "retained_by_canonical_filter": True} for w in words
            ],
            "native_segments": [
                {
                    "segment_ordinal": 0,
                    "start": words[0]["start"],
                    "end": words[-1]["end"],
                    "text": canonical[0]["text"],
                    "no_speech_prob": 0.1,
                    "retained_by_canonical_filter": True,
                }
            ],
            "retained_words": words,
            "canonical_segments": canonical,
            "mapping_status": state,
            "mapping_refusal": reason,
            "segments": mapped,
            "production_publication_performed": False,
        }

    def close(self):
        self.closed = True


def install(monkeypatch, models, callback=None, refusal=False):
    from app.services.live_speech import speech_profile

    resident = GroupResident(speech_profile(models), callback, refusal)
    original = grouped.resident

    def factory(packet):
        # Keep the actual runtime snapshot check; only replace the constructed
        # owner, never start its fake model or subprocess.
        probe = original(packet)
        assert probe.process is None
        return resident

    monkeypatch.setattr(grouped, "resident", factory)
    return resident


def test_group_is_atomic_replayable_and_keeps_words_notes_and_originals(
    stores, harness, profile, monkeypatch
):
    brain, _, _, _ = stores
    resident = install(monkeypatch, profile)
    with brain() as db:
        row = prepare(db)
        sid = row["id"]
        body = action(row["revision"])
        originals = {
            c.id: Path(c.storage_path).read_bytes()
            for c in db.scalars(select(MeetingAudioChunk))
        }
        accepted = batch.request(db, sid, body)
        packet = deepcopy(batch._packet(db.get(MeetingSessionCommand, body.command_id)))
        assert len(packet["grouping_plan"]["units"]) == 1
        assert not resident.calls
    batch._run(harness[0][0])
    assert resident.closed and len(resident.calls) == 1 and batch._active is None
    with brain() as db:
        final = sessions.serialize_session(db, sessions.get_session(db, sid))
        assert final["transcription_batch"]["state"] == "completed"
        assert (
            len(final["segments"]) == 2
            and final["staged_note"]["plain_text"] == "Conserver la décision humaine."
        )
        current = batch._packet(db.get(MeetingSessionCommand, body.command_id))
        assert current["grouping_plan"] == packet["grouping_plan"]
        assert set(current["completed_ids"]) == set(originals)
        proof = next(iter(current["group_results"].values()))
        assert (
            proof["state"] == "completed"
            and len(proof["response"]["native_words"]) == 2
        )
        for chunk_id, raw in originals.items():
            c = db.get(MeetingAudioChunk, chunk_id)
            assert (
                c.speech_status == "completed"
                and Path(c.storage_path).read_bytes() == raw
            )
        assert batch.request(db, sid, body) == accepted and len(harness[0]) == 1


@pytest.mark.parametrize(
    "change",
    ["cancel", "correction", "source", "rights", "feature", "group_feature", "profile"],
)
def test_change_during_model_publishes_no_group(
    stores, harness, profile, monkeypatch, change
):
    brain, _, _, _ = stores

    def callback(group):
        if change == "cancel":
            harness[0][0].cancel.set()
        elif change == "source":
            path = Path(group.members[-1].path)
            path.write_bytes(path.read_bytes() + b"x")
        elif change == "profile":
            (profile / "fake-medium/model.bin").write_bytes(b"CHANGED MODEL FIXTURE")
        elif change == "rights":
            monkeypatch.setenv("AGENT_OPERATOR_ID", "different-operator")
        else:
            with brain() as db:
                if change == "feature":
                    save_section(db, "foresight", {"enabled": False})
                elif change == "group_feature":
                    save_section(
                        db, "foresight", {"grouped_batch_transcription_enabled": False}
                    )
                else:
                    m = group.members[-1]
                    db.add(
                        LiveTranscriptSegment(
                            id="human-new",
                            session_id=m.session_id,
                            chunk_id=m.id,
                            track=m.track,
                            start_ms=m.start_ms,
                            end_ms=m.start_ms + 500,
                            speaker="mic",
                            text="Correction humaine.",
                            revision=1,
                            finalized=False,
                        )
                    )
                    db.commit()

    resident = install(monkeypatch, profile, callback)
    with brain() as db:
        row = prepare(db)
        sid = row["id"]
        batch.request(db, sid, action(row["revision"]))
    batch._run(harness[0][0])
    assert resident.closed and batch._active is None
    with brain() as db:
        current = batch._packet(
            db.scalar(
                select(MeetingSessionCommand).where(
                    MeetingSessionCommand.kind == batch.KIND
                )
            )
        )
        if change == "profile":
            # Final profile change is caught before terminal completion, but
            # must also be checked BEFORE publication: this regression enforces it.
            assert current["completed_ids"] == []
        segments = list(db.scalars(select(LiveTranscriptSegment)))
        assert len(segments) == (1 if change == "correction" else 0)
        assert current["completed_ids"] == []
        assert all(
            c.speech_status != "completed"
            for c in db.scalars(select(MeetingAudioChunk))
        )


def test_boundary_refusal_is_durable_and_no_individual_retry(
    stores, harness, profile, monkeypatch
):
    brain, _, _, _ = stores
    resident = install(monkeypatch, profile, refusal=True)
    with brain() as db:
        row = prepare(db)
        batch.request(db, row["id"], action(row["revision"]))
    batch._run(harness[0][0])
    assert len(resident.calls) == 1 and resident.closed
    with brain() as db:
        packet = batch._packet(
            db.scalar(
                select(MeetingSessionCommand).where(
                    MeetingSessionCommand.kind == batch.KIND
                )
            )
        )
        assert packet["state"] == "failed" and packet["completed_ids"] == []
        proof = next(iter(packet["group_results"].values()))
        assert (
            proof["state"] == "refused"
            and proof["response"]["mapping_refusal"] == "word_crosses_source_boundary"
        )
        assert not list(db.scalars(select(LiveTranscriptSegment)))


def test_plan_change_or_source_omission_refuses_before_new_resident(
    stores, harness, profile, monkeypatch
):
    brain, _, _, _ = stores
    with brain() as db:
        row = prepare(db)
        body = action(row["revision"])
        batch.request(db, row["id"], body)
        receipt = db.get(MeetingSessionCommand, body.command_id)
        packet = deepcopy(batch._packet(receipt))
        packet["grouping_plan"]["units"].clear()
        batch._save_packet(receipt, packet)
        db.commit()
    monkeypatch.setattr(
        grouped,
        "resident",
        lambda _: pytest.fail("Invalid plan must fail before owner construction"),
    )
    batch._run(harness[0][0])
    with brain() as db:
        assert (
            batch._packet(db.get(MeetingSessionCommand, body.command_id))[
                "completed_ids"
            ]
            == []
        )
        assert not list(db.scalars(select(LiveTranscriptSegment)))


def test_model_configuration_change_before_loading_is_rejected(
    stores, harness, profile, monkeypatch
):
    brain, _, _, _ = stores
    with brain() as db:
        row = prepare(db)
        body = action(row["revision"])
        batch.request(db, row["id"], body)
    (profile / "models.json").write_text("{}", encoding="utf-8")
    batch._run(harness[0][0])
    assert batch._active is None
    with brain() as db:
        assert (
            batch._packet(db.get(MeetingSessionCommand, body.command_id))["state"]
            == "failed"
        )
        assert not list(db.scalars(select(LiveTranscriptSegment)))


@pytest.mark.parametrize("fault", ["exception_after_add", "cancel_after_add"])
def test_final_packet_fault_rolls_back_all_group_rows_and_events(
    stores, harness, profile, monkeypatch, fault
):
    from app.meeting_session_models import MeetingSessionEvent

    brain, _, _, _ = stores
    resident = install(monkeypatch, profile)
    original = batch._save_packet

    def save(receipt, packet):
        original(receipt, packet)
        if (
            packet.get("completed_ids")
            and packet.get("running_group_id") is None
            and packet.get("group_results")
        ):
            if fault == "cancel_after_add":
                harness[0][0].cancel.set()
            else:
                raise RuntimeError("Deliberate final transaction fault")

    monkeypatch.setattr(batch, "_save_packet", save)
    with brain() as db:
        row = prepare(db)
        sid = row["id"]
        batch.request(db, sid, action(row["revision"]))
    batch._run(harness[0][0])
    assert resident.closed and batch._active is None
    with brain() as db:
        packet = batch._packet(
            db.scalar(
                select(MeetingSessionCommand).where(
                    MeetingSessionCommand.kind == batch.KIND
                )
            )
        )
        assert packet["completed_ids"] == [] and not packet.get("group_results")
        assert not list(db.scalars(select(LiveTranscriptSegment)))
        assert not list(
            db.scalars(
                select(MeetingSessionEvent).where(
                    MeetingSessionEvent.kind == "transcript.updated"
                )
            )
        )


def test_global_identity_collision_preserves_human_row_and_refuses_entire_group(
    stores, harness, profile, monkeypatch
):
    brain, _, _, _ = stores

    def callback(group):
        identity = (
            "live-" + hashlib.sha256(f"{group.members[0].id}:0".encode()).hexdigest()
        )
        with brain() as db:
            db.add(
                LiveTranscriptSegment(
                    id=identity,
                    session_id=group.members[0].session_id,
                    chunk_id=None,
                    track="mic",
                    start_ms=0,
                    end_ms=500,
                    speaker="Personne",
                    text="Texte humain protégé.",
                    revision=2,
                    finalized=False,
                )
            )
            db.commit()

    resident = install(monkeypatch, profile, callback)
    with brain() as db:
        row = prepare(db)
        body = action(row["revision"])
        batch.request(db, row["id"], body)
    batch._run(harness[0][0])
    assert resident.closed
    with brain() as db:
        rows = list(db.scalars(select(LiveTranscriptSegment)))
        assert (
            len(rows) == 1
            and rows[0].text == "Texte humain protégé."
            and rows[0].revision == 2
        )
        assert (
            batch._packet(db.get(MeetingSessionCommand, body.command_id))[
                "completed_ids"
            ]
            == []
        )


def test_cancel_second_group_keeps_whole_first_committed_group(
    stores, harness, profile, monkeypatch
):
    brain, _, _, _ = stores

    def callback(group):
        if group.members[0].sequence == 4:
            harness[0][0].cancel.set()

    resident = install(monkeypatch, profile, callback)
    with brain() as db:
        row = prepare(db, count=6, duration_ms=5000)
        body = action(row["revision"])
        batch.request(db, row["id"], body)
    batch._run(harness[0][0])
    assert len(resident.calls) == 2 and resident.closed
    with brain() as db:
        packet = batch._packet(db.get(MeetingSessionCommand, body.command_id))
        assert packet["state"] == "cancelled" and len(packet["completed_ids"]) == 4
        rows = list(db.scalars(select(LiveTranscriptSegment)))
        assert len(rows) == 4 and {row.chunk_id for row in rows} == set(
            packet["completed_ids"]
        )
        chunks = list(
            db.scalars(select(MeetingAudioChunk).order_by(MeetingAudioChunk.sequence))
        )
        assert [chunk.speech_status for chunk in chunks] == ["completed"] * 4 + [
            "retained"
        ] * 2


@pytest.mark.parametrize(
    "mutation", ["word_flag", "retained_text", "missing_segment", "option"]
)
def test_native_evidence_contradiction_cannot_complete_a_group(
    stores, harness, profile, monkeypatch, mutation
):
    brain, _, _, _ = stores
    resident = install(monkeypatch, profile)
    original = resident.transcribe_group

    def corrupt(group, **kwargs):
        value = original(group, **kwargs)
        if mutation == "word_flag":
            value["native_words"][0]["retained_by_canonical_filter"] = False
        elif mutation == "retained_text":
            value["retained_words"][0] = {
                **value["retained_words"][0],
                "word": "Fake text",
            }
        elif mutation == "missing_segment":
            value.pop("native_segments")
        else:
            value["native_transcription_options"]["beam_size"] = 5
        return value

    resident.transcribe_group = corrupt
    with brain() as db:
        row = prepare(db)
        body = action(row["revision"])
        batch.request(db, row["id"], body)
    batch._run(harness[0][0])
    assert resident.closed
    with brain() as db:
        assert (
            batch._packet(db.get(MeetingSessionCommand, body.command_id))[
                "completed_ids"
            ]
            == []
        )
        assert not list(db.scalars(select(LiveTranscriptSegment)))


@pytest.mark.parametrize("change", ["profile", "group_feature"])
def test_mixed_individual_unit_obeys_same_frozen_profile_and_feature(
    stores, harness, profile, monkeypatch, change
):
    brain, _, _, _ = stores
    resident = install(monkeypatch, profile)
    individual_calls = []

    def transcribe(prepared, **kwargs):
        individual_calls.append(prepared)
        if change == "profile":
            (profile / "fake-medium/model.bin").write_bytes(
                b"NEW MODEL DURING INDIVIDUAL UNIT"
            )
        else:
            with brain() as db:
                save_section(
                    db, "foresight", {"grouped_batch_transcription_enabled": False}
                )
        return {
            "duration_ms": 10000,
            "segments": [
                {
                    "start_ms": prepared.offset_ms + 100,
                    "end_ms": prepared.offset_ms + 800,
                    "speaker": "mic",
                    "text": "Do not publish this late result.",
                }
            ],
        }

    resident.transcribe = transcribe
    with brain() as db:
        row = prepare(db, count=3, duration_ms=10000)
        body = action(row["revision"])
        batch.request(db, row["id"], body)
    batch._run(harness[0][0])
    assert resident.closed and len(individual_calls) == 1 and len(resident.calls) == 1
    with brain() as db:
        packet = batch._packet(db.get(MeetingSessionCommand, body.command_id))
        assert len(packet["completed_ids"]) == 2
        segments = list(db.scalars(select(LiveTranscriptSegment)))
        assert len(segments) == 2 and all(
            segment.text != "Do not publish this late result." for segment in segments
        )


def test_grouping_is_disabled_by_default_without_reading_a_model(
    stores, harness, monkeypatch
):
    from tests.test_session_batch_transcription import personal

    brain, _, _, _ = stores
    monkeypatch.setattr(
        grouped,
        "_profile_snapshot",
        lambda: pytest.fail("Default must not inspect grouped model"),
    )
    with brain() as db:
        row = personal(db)
        body = action(row["revision"])
        batch.request(db, row["id"], body)
        plan = batch._packet(db.get(MeetingSessionCommand, body.command_id))[
            "grouping_plan"
        ]
        assert plan["runtime"] is None
        assert plan["units"][0]["reason"] == "grouped_batch_capability_disabled"
    batch._run(harness[0][0])
    assert harness[1].closed and len(harness[1].calls) == 1


def test_group_feature_off_after_prepare_rejects_without_starting_a_model(
    stores, harness, profile, monkeypatch
):
    from fastapi import HTTPException

    brain, _, _, _ = stores
    original = sessions._begin
    with brain() as db:
        row = prepare(db)
        body = action(row["revision"])

    def begin_then_disable(*args, **kwargs):
        receipt = original(*args, **kwargs)
        with brain() as changed:
            save_section(
                changed, "foresight", {"grouped_batch_transcription_enabled": False}
            )
        return receipt

    monkeypatch.setattr(sessions, "_begin", begin_then_disable)
    with brain() as db, pytest.raises(HTTPException) as error:
        batch.request(db, row["id"], body)
    assert error.value.status_code == 409 and not harness[0]
    with brain() as db:
        assert db.get(MeetingSessionCommand, body.command_id).status == "rejected"
        assert not list(db.scalars(select(LiveTranscriptSegment)))
