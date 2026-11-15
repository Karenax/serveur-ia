"""Rolling provisional revision preserves text, provenance and human ownership."""

import hashlib
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import select

from app.meeting_session_models import (
    LiveTranscriptSegment,
    MeetingAudioChunk,
    MeetingSessionEvent,
)
from app.services.audio_capture import PreparedAudio
from app.services import live_speech as live

# Load the real subclass before the hardware-free fixture replaces its base.
from app.services import grouped_batch
from scripts.transcribe_live import transcribe
from tests.test_speech_admission_worker import (
    stores,
    isolated_worker,
    seed,
    enable,
    fake_engine,
)

__all__ = ["stores", "isolated_worker", "grouped_batch"]


def test_worker_partitions_previous_words_and_new_words_without_overlap():
    from types import SimpleNamespace as S

    class Model:
        def transcribe(self, samples, **kwargs):
            return [
                S(
                    no_speech_prob=0.01,
                    words=[
                        S(start=4.0, end=4.5, word=" 350"),
                        S(start=4.5, end=4.9, word=" lux"),
                        S(start=5.1, end=5.5, word=" confirmé"),
                    ],
                )
            ], None

    result = transcribe(
        Model(),
        np.zeros(96000),
        {
            "offset_ms": 0,
            "keep_from_ms": 5000,
            "clip_end_ms": 6000,
            "revise_from_ms": 0,
            "track": "mic",
        },
    )
    assert result["context_segments"] == [
        {"start_ms": 4000, "end_ms": 4900, "text": "350 lux", "speaker": "mic"}
    ]
    assert result["segments"] == [
        {"start_ms": 5100, "end_ms": 5500, "text": "confirmé", "speaker": "mic"}
    ]


def test_unit_can_move_to_the_next_chunk_without_repeating_the_value():
    from types import SimpleNamespace as S

    class Model:
        def transcribe(self, samples, **kwargs):
            return [
                S(
                    no_speech_prob=0.01,
                    words=[
                        S(start=4.2, end=4.82, word=" 350"),
                        S(start=5.0, end=5.34, word=" lux."),
                    ],
                )
            ], None

    result = transcribe(
        Model(),
        np.zeros(98320),
        {
            "offset_ms": 0,
            "keep_from_ms": 5000,
            "clip_end_ms": 6145,
            "revise_from_ms": 0,
            "track": "mic",
        },
    )
    assert result["context_segments"][0]["text"] == "350"
    assert result["segments"][0]["text"] == "lux."
    assert result["context_segments"][0]["end_ms"] <= result["segments"][0]["start_ms"]


def seed_revision(stores):
    with stores[0]() as db:
        sid, ids = seed(db, ["completed", "pending"])
        previous, current = [db.get(MeetingAudioChunk, key) for key in ids]
        identity = "live-" + hashlib.sha256(f"{previous.id}:0".encode()).hexdigest()
        db.add(
            LiveTranscriptSegment(
                id=identity,
                session_id=sid,
                chunk_id=previous.id,
                track="mic",
                start_ms=0,
                end_ms=4900,
                speaker="mic",
                text="350 lb",
                revision=1,
                finalized=False,
            )
        )
        enable(db)
        db.commit()
        prepared = PreparedAudio(
            Path(current.storage_path),
            0,
            0,
            10000,
            True,
            Path(previous.storage_path),
            5000,
        )
        return sid, ids, identity, prepared


def test_actual_direct_transaction_revises_only_provisional_with_preimage(
    stores, monkeypatch
):
    from app.meeting_session_models import MeetingSession
    from app.services import scoped_assistant

    sid, ids, identity, prepared = seed_revision(stores)
    with stores[0]() as db:
        old_stamp = scoped_assistant.session_snapshot(db, db.get(MeetingSession, sid))[
            0
        ]
    fake_engine(
        monkeypatch,
        transcribe=lambda *_args, **_kwargs: {
            "segments": [],
            "context_segments": [
                {"start_ms": 0, "end_ms": 4900, "text": "350 lux", "speaker": "mic"}
            ],
            "duration_ms": 10000,
            "compute_s": 0.01,
        },
    )
    monkeypatch.setattr(live, "prepare_direct_chunk", lambda *_a, **_k: prepared)
    live.process_chunk(ids[1])
    assert not live.process_chunk(ids[1])
    with stores[0]() as db:
        assert not scoped_assistant.context_current(
            db,
            db.get(MeetingSession, sid),
            {"session_stamp": old_stamp, "citations": []},
        )
        rows = list(
            db.scalars(
                select(LiveTranscriptSegment).where(
                    LiveTranscriptSegment.session_id == sid
                )
            )
        )
        assert len(rows) == 1 and rows[0].id == identity
        assert (rows[0].text, rows[0].revision, rows[0].finalized) == (
            "350 lux",
            2,
            False,
        )
        events = list(
            db.scalars(
                select(MeetingSessionEvent).where(
                    MeetingSessionEvent.session_id == sid,
                    MeetingSessionEvent.kind == "transcript.context-revised",
                )
            )
        )
        assert len(events) == 1
        assert events[0].data["before"][0]["text"] == "350 lb"
        assert events[0].data["after"][0]["text"] == "350 lux"


@pytest.mark.parametrize(
    "protection",
    [
        "human_revision",
        "finalized",
        "wrong_path",
        "wrong_count",
        "invalid_time",
        "noncompleted",
    ],
)
def test_context_revision_refuses_protected_or_incoherent_rows(stores, protection):
    sid, ids, identity, prepared = seed_revision(stores)
    replacement = [{"start_ms": 0, "end_ms": 4900, "text": "350 lux"}]
    with stores[0]() as db:
        previous, current = [db.get(MeetingAudioChunk, key) for key in ids]
        row = db.get(LiveTranscriptSegment, identity)
        if protection == "human_revision":
            row.text = "Correction humaine : 350 lux"
            row.revision = 2
        if protection == "finalized":
            row.finalized = True
        if protection == "wrong_path":
            prepared = PreparedAudio(
                prepared.path, 0, 0, 10000, True, Path("other-file"), 5000
            )
        if protection == "wrong_count":
            replacement *= 2
        if protection == "invalid_time":
            replacement[0]["start_ms"] = -1
        if protection == "noncompleted":
            previous.speech_status = "retained"
        db.commit()
        before = (row.text, row.revision, row.finalized)
        assert (
            live._revise_context(
                db, current, prepared, {"context_segments": replacement}
            )
            == 0
        )
        db.commit()
        db.refresh(row)
        assert (row.text, row.revision, row.finalized) == before
        assert not list(
            db.scalars(
                select(MeetingSessionEvent).where(
                    MeetingSessionEvent.kind == "transcript.context-revised"
                )
            )
        )


def test_human_correction_committed_during_inference_wins(stores, monkeypatch):
    sid, ids, identity, prepared = seed_revision(stores)

    def engine(*_a, **_k):
        with stores[0]() as db:
            row = db.get(LiveTranscriptSegment, identity)
            row.text = "Réserve humaine, ne rien engager."
            row.revision = 2
            db.commit()
        return {
            "segments": [],
            "context_segments": [{"start_ms": 0, "end_ms": 4900, "text": "350 lux"}],
            "duration_ms": 10000,
            "compute_s": 0.01,
        }

    fake_engine(monkeypatch, transcribe=engine)
    monkeypatch.setattr(live, "prepare_direct_chunk", lambda *_a, **_k: prepared)
    live.process_chunk(ids[1])
    with stores[0]() as db:
        row = db.get(LiveTranscriptSegment, identity)
        assert (row.text, row.revision) == ("Réserve humaine, ne rien engager.", 2)
