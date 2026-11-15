"""Protocol and deadline tests with in-memory transport, never a process."""

from contextlib import nullcontext
from dataclasses import replace
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace as NS
import threading
import unittest
from unittest.mock import patch

from app.services.audio_capture import PreparedAudio
from app.services.grouped_resident import GroupedResidentWhisper
from scripts.grouped_pcm_core import Group, Member
from scripts.grouped_response_evidence import EXPECTED_OPTIONS, NATIVE_OPTIONS


class FakeResident(GroupedResidentWhisper):
    def __init__(self, response_factory):
        super().__init__(
            Path(__file__).parent,
            python=Path("fictional-python"),
            models=Path("fictional-model"),
        )
        self.process = NS(stdin=StringIO())
        self.response_factory = response_factory
        self.started = False
        self.closed = False

    def start(self, **kwargs):
        self.started = True
        self.start_arguments = kwargs
        self._remaining(kwargs["deadline"], kwargs["cancel"])

    def _next_event(self, deadline, cancel=None):
        self._remaining(deadline, cancel)
        request = json.loads(self.process.stdin.getvalue().splitlines()[-1])
        return self.response_factory(request)

    def close(self):
        self.closed = True


def group():
    return Group(
        tuple(
            Member(
                str(i),
                "session",
                "mic",
                i,
                f"{i}.wav",
                "a" * 64,
                32044,
                i * 1000,
                1000,
                16000,
                effective_metadata_verified=True,
            )
            for i in range(2)
        )
    )


def response(request):
    return {
        "kind": "result",
        "request_id": request["request_id"],
        "contract": "batch_group_pcm_v1",
        "group_id": request["group_id"],
        "duration_ms": 2000,
        "grouped_frames": 32000,
        "offset_ms": 0,
        "grouped_pcm_sha256": "a" * 64,
        "source_pcm_metadata": [
            {
                "chunk_id": str(i),
                "frames": 16000,
                "file_sha256": "a" * 64,
                "pcm_sha256": "b" * 64,
            }
            for i in range(2)
        ],
        "loaded_model_profile": {
            "actual_device": "cpu",
            "actual_compute_type": "int8_float32",
        },
        "language": "fr",
        "effective_transcribe_options": EXPECTED_OPTIONS,
        "native_transcription_options": NATIVE_OPTIONS,
        "native_segments": [],
        "native_words": [],
        "canonical_segments": [],
        "retained_words": [],
        "mapping_status": "mapped",
        "mapping_refusal": None,
        "segments": [],
    }


class ResidentTests(unittest.TestCase):
    def test_group_manifest_and_same_deadline_reach_only_fake_transport(self):
        resident = FakeResident(response)
        with patch(
            "app.services.grouped_resident.lease", return_value=nullcontext()
        ) as lease:
            result = resident.transcribe_group(group(), timeout=3)
        request = json.loads(resident.process.stdin.getvalue())
        self.assertEqual(request["manifest"], group().manifest)
        self.assertEqual(request["op"], "batch_group_pcm_v1")
        self.assertEqual(result["mapping_status"], "mapped")
        self.assertEqual(lease.call_args.kwargs["priority"], 0)
        self.assertLessEqual(resident.start_arguments["timeout"], 3)
        self.assertFalse(resident.closed)

    def test_response_identity_mismatch_closes_owner_and_unlocks(self):
        resident = FakeResident(
            lambda request: {**response(request), "request_id": "other"}
        )
        with (
            patch("app.services.grouped_resident.lease", return_value=nullcontext()),
            self.assertRaises(RuntimeError),
        ):
            resident.transcribe_group(group())
        self.assertTrue(resident.closed)
        acquired = []

        def probe():
            locked = resident._request_lock.acquire(timeout=0.1)
            acquired.append(locked)
            if locked:
                resident._request_lock.release()

        thread = threading.Thread(target=probe)
        thread.start()
        thread.join(1)
        self.assertEqual(acquired, [True])

    def test_corrupt_PCM_source_acknowledgement_closes_owner(self):
        def corrupt(request):
            value = response(request)
            value["source_pcm_metadata"][1]["file_sha256"] = "c" * 64
            return value

        resident = FakeResident(corrupt)
        with (
            patch("app.services.grouped_resident.lease", return_value=nullcontext()),
            self.assertRaises(ValueError),
        ):
            resident.transcribe_group(group())
        self.assertTrue(resident.closed)

    def test_wrong_mapped_segments_cannot_pass_to_publication(self):
        resident = FakeResident(
            lambda request: {**response(request), "segments": [{"text": "invented"}]}
        )
        with (
            patch("app.services.grouped_resident.lease", return_value=nullcontext()),
            self.assertRaises(ValueError),
        ):
            resident.transcribe_group(group())
        self.assertTrue(resident.closed)

    def test_missing_native_evidence_cannot_be_an_empty_success(self):
        def missing(request):
            value = response(request)
            value.pop("native_words")
            return value

        resident = FakeResident(missing)
        with (
            patch("app.services.grouped_resident.lease", return_value=nullcontext()),
            self.assertRaises(ValueError),
        ):
            resident.transcribe_group(group())
        self.assertTrue(resident.closed)

    def test_changed_native_or_explicit_options_cannot_pass(self):
        for field in ("native_transcription_options", "effective_transcribe_options"):

            def corrupt(request):
                value = response(request)
                value[field] = {**value[field], "word_timestamps": False}
                return value

            resident = FakeResident(corrupt)
            with (
                self.subTest(field=field),
                patch(
                    "app.services.grouped_resident.lease", return_value=nullcontext()
                ),
                self.assertRaises(ValueError),
            ):
                resident.transcribe_group(group())
            self.assertTrue(resident.closed)

    def test_cancel_before_transport_never_starts(self):
        resident = FakeResident(response)
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(InterruptedError):
            resident.transcribe_group(group(), cancel=cancel)
        self.assertFalse(resident.started)
        self.assertEqual(resident.process.stdin.getvalue(), "")

    def test_oversized_request_is_rejected_before_start(self):
        resident = FakeResident(response)
        huge = Group(
            (replace(group().members[0], path="x" * 17000), group().members[1])
        )
        with self.assertRaisesRegex(ValueError, "command bound"):
            resident.transcribe_group(huge)
        self.assertFalse(resident.started)

    def test_cancel_during_validation_closes_before_return(self):
        cancel = threading.Event()
        resident = FakeResident(response)

        def validating(group, value):
            cancel.set()
            return value

        with (
            patch("app.services.grouped_resident.lease", return_value=nullcontext()),
            patch(
                "app.services.grouped_resident.validate_response",
                side_effect=validating,
            ),
            self.assertRaises(InterruptedError),
        ):
            resident.transcribe_group(group(), cancel=cancel)
        self.assertTrue(resident.closed)

    def test_direct_inherited_request_payload_is_unchanged(self):
        resident = FakeResident(
            lambda request: {
                "kind": "result",
                "request_id": request["request_id"],
                "segments": [],
                "duration_ms": 1000,
            }
        )
        prepared = PreparedAudio(Path("fixture.wav"), 12000, 0, 1000, False)
        with patch("app.services.live_speech.lease", return_value=nullcontext()):
            resident.transcribe(prepared, track="system", keep_from_ms=12000, timeout=3)
        request = json.loads(resident.process.stdin.getvalue())
        request.pop("request_id")
        self.assertEqual(
            request,
            {
                "op": "transcribe",
                "path": "fixture.wav",
                "track": "system",
                "offset_ms": 12000,
                "clip_start_ms": 0,
                "clip_end_ms": 1000,
                "keep_from_ms": 12000,
            },
        )


if __name__ == "__main__":
    unittest.main()
