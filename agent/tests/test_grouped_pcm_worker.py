"""Private operation with synthetic PCM and fake Whisper parts only."""

from array import array
from dataclasses import dataclass
import hashlib
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import tempfile
import uuid
import wave

from scripts.grouped_pcm_core import CONTRACT, Group, GroupRefused, Member
from scripts.grouped_pcm_worker import transcribe_group
from scripts.transcribe_live import transcribe


@dataclass
class FakeOptions:
    beam_size: int = 5
    word_timestamps: bool = True
    condition_on_previous_text: bool = False
    no_speech_threshold: float = 0.6
    compression_ratio_threshold: float = 2.4


def part(words, *, probability=0.1):
    return NS(
        start=words[0].start,
        end=words[-1].end,
        text="".join(w.word for w in words),
        words=words,
        no_speech_prob=probability,
    )


class FakeModel:
    def __init__(self, parts, callback=None):
        self.parts, self.callback, self.calls = parts, callback, []
        self.model = NS(device="cpu", compute_type="int8_float32")

    def transcribe(self, samples, **kwargs):
        self.calls.append((samples.tobytes(), kwargs))
        if self.callback:
            self.callback()
        return iter(self.parts), NS(transcription_options=FakeOptions())


def fake_decode(stream, *, sampling_rate):
    if sampling_rate != 16000:
        raise AssertionError("Decoder rate changed")
    with wave.open(stream, "rb") as wav:
        ints = array("h")
        ints.frombytes(wav.readframes(wav.getnframes()))
    return array("f", (x / 32768 for x in ints))


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp_base = (
            Path(tempfile.mkdtemp(prefix="agent-grouped-pcm-test-"))
        )
        self.temp_base.mkdir(parents=True, exist_ok=True)
        self.root = self.temp_base / uuid.uuid4().hex
        self.root.mkdir(exist_ok=False)
        self.members = []
        for i in range(2):
            path = self.root / f"{i}.wav"
            with wave.open(str(path), "wb") as target:
                target.setnchannels(1)
                target.setsampwidth(2)
                target.setframerate(16000)
                target.writeframes(array("h", [i + 1] * 16000).tobytes())
            self.members.append(
                Member(
                    str(i),
                    "session",
                    "mic",
                    i,
                    str(path),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    path.stat().st_size,
                    i * 1000,
                    1000,
                    16000,
                    effective_metadata_verified=True,
                )
            )
        self.group = Group(tuple(self.members))
        self.request = {
            "op": CONTRACT,
            "group_id": self.group.id,
            "manifest": self.group.manifest,
        }
        self.words = [
            NS(start=0.1, end=0.4, word=" Premier"),
            NS(start=1.1, end=1.4, word=" second."),
        ]

    def tearDown(self):
        if not self.root.resolve().is_relative_to(self.temp_base.resolve()):
            raise AssertionError("Temporary cleanup target escaped isolated QA")
        # Preserve only these fresh fictitious inputs; no ACL edit or recursive delete.

    def operation(self, model, **kwargs):
        return transcribe_group(
            model, self.request, self.root, fake_decode, transcribe, **kwargs
        )

    def test_one_call_preserves_frozen_PCM_options_ordinals_and_provenance(self):
        model = FakeModel([part(self.words)])
        result = self.operation(model)
        expected = array("f", [1 / 32768] * 16000 + [2 / 32768] * 16000).tobytes()
        self.assertEqual(model.calls[0][0], expected)
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(
            result["grouped_pcm_sha256"], hashlib.sha256(expected).hexdigest()
        )
        self.assertEqual(result["mapping_status"], "mapped")
        self.assertEqual([x["chunk_id"] for x in result["segments"]], ["0", "1"])
        self.assertEqual(
            [
                (w["segment_ordinal"], w["word_ordinal"])
                for w in result["retained_words"]
            ],
            [(0, 0), (0, 1)],
        )
        self.assertEqual(
            model.calls[0][1],
            {
                "language": "fr",
                "beam_size": 5,
                "word_timestamps": True,
                "vad_filter": True,
                "condition_on_previous_text": False,
                "no_speech_threshold": 0.6,
                "compression_ratio_threshold": 2.4,
                "vad_parameters": {"min_silence_duration_ms": 250},
            },
        )
        self.assertFalse(result["production_publication_performed"])

    def test_canonical_filtered_part_is_observed_but_never_published(self):
        filtered = part(
            [NS(start=0.5, end=0.7, word=" hallucination")], probability=0.9
        )
        valid = part([NS(start=1.1, end=1.4, word=" Utile.")])
        result = self.operation(FakeModel([filtered, valid]))
        self.assertEqual([w["word"] for w in result["retained_words"]], [" Utile."])
        self.assertEqual(
            [w["retained_by_canonical_filter"] for w in result["native_words"]],
            [False, True],
        )
        self.assertEqual(result["segments"][0]["text"], "Utile.")

    def test_ambiguous_word_refuses_entire_group_without_retry(self):
        model = FakeModel([part([NS(start=0.9, end=1.1, word=" frontière")])])
        result = self.operation(model)
        self.assertEqual(
            (result["mapping_status"], result["segments"]), ("refused", [])
        )
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(result["mapping_refusal"], "word_crosses_source_boundary")

    def test_source_changed_before_decode_never_invokes_model(self):
        path = Path(self.members[0].path)
        path.write_bytes(path.read_bytes() + b"x")
        model = FakeModel([part(self.words)])
        with self.assertRaisesRegex(GroupRefused, "source_size_or_hash_changed"):
            self.operation(model)
        self.assertFalse(model.calls)

    def test_source_changed_during_inference_refuses_response(self):
        path = Path(self.members[0].path)
        model = FakeModel(
            [part(self.words)],
            callback=lambda: path.write_bytes(path.read_bytes() + b"x"),
        )
        with self.assertRaisesRegex(GroupRefused, "source_changed_during_group"):
            self.operation(model)

    def test_frozen_buffer_prevents_path_race_during_decode(self):
        seen = []

        def decoder(stream, **kwargs):
            seen.append(hasattr(stream, "read"))
            return fake_decode(stream, **kwargs)

        transcribe_group(
            FakeModel([part(self.words)]), self.request, self.root, decoder, transcribe
        )
        self.assertEqual(seen, [True, True])

    def test_cancel_before_decode_or_after_inference_has_no_result(self):
        def cancelled():
            raise InterruptedError("simulated cancel")

        model = FakeModel([part(self.words)])
        with self.assertRaises(InterruptedError):
            self.operation(model, check_cancel=cancelled)
        self.assertFalse(model.calls)
        cancelled_flag = [False]

        def check():
            if cancelled_flag[0]:
                raise InterruptedError("simulated cancel")

        model = FakeModel(
            [part(self.words)], callback=lambda: cancelled_flag.__setitem__(0, True)
        )
        with self.assertRaises(InterruptedError):
            self.operation(model, check_cancel=check)

    def test_changed_group_identity_or_storage_root_never_invokes_model(self):
        model = FakeModel([part(self.words)])
        original = self.request["group_id"]
        self.request["group_id"] = "b" * 64
        with self.assertRaisesRegex(GroupRefused, "identity"):
            self.operation(model)
        self.request["group_id"] = original
        with self.assertRaisesRegex(GroupRefused, "storage"):
            transcribe_group(
                model, self.request, self.root / "other", fake_decode, transcribe
            )
        self.assertFalse(model.calls)

    def test_loaded_profile_must_actually_be_CPU_int8_family(self):
        model = FakeModel([part(self.words)])
        model.model.device = "cuda"
        with self.assertRaisesRegex(GroupRefused, "loaded_CPU"):
            self.operation(model)
        self.assertFalse(model.calls)

    def test_no_speech_completes_with_explicit_empty_retained_words(self):
        result = self.operation(FakeModel([part(self.words, probability=0.99)]))
        self.assertEqual(
            (result["mapping_status"], result["retained_words"], result["segments"]),
            ("mapped", [], []),
        )
        self.assertTrue(
            all(
                not x["retained_by_canonical_filter"] for x in result["native_segments"]
            )
        )

if __name__ == "__main__":
    unittest.main()
