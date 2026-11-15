"""Pure provenance/selection regressions. No application, process or model import."""

from dataclasses import replace
import json
from pathlib import Path
import unittest

from scripts.grouped_pcm_core import (
    Group,
    GroupRefused,
    Individual,
    Member,
    group_from_manifest,
    map_words,
    plan_groups,
    publication_guard,
    validate_group,
)


def member(index, **changes):
    value = Member(
        str(index),
        "session",
        "mic",
        index,
        f"fixture-{index}.wav",
        "a" * 64,
        32044,
        index * 1000,
        1000,
        16000,
        effective_metadata_verified=True,
    )
    return replace(value, **changes)


def word(start, end, text=" mot", *, segment=0, ordinal=0):
    return {
        "start": start,
        "end": end,
        "word": text,
        "segment_ordinal": segment,
        "word_ordinal": ordinal,
    }


class PlannerTests(unittest.TestCase):
    def test_contiguous_sources_group_without_changing_input(self):
        items = (member(0), member(1), member(2))
        plan = plan_groups(items)
        self.assertEqual(plan, (Group(items),))
        self.assertEqual(group_from_manifest(plan[0].manifest), plan[0])

    def test_gap_and_overlap_keep_individual_sources(self):
        for start in (999, 1001):
            with self.subTest(start=start):
                plan = plan_groups((member(0), member(1, start_ms=start)))
                self.assertTrue(all(isinstance(item, Individual) for item in plan))

    def test_missing_sequence_track_and_session_never_join(self):
        for changed in (
            member(1, sequence=3),
            member(1, track="system"),
            member(1, session_id="other"),
        ):
            with self.subTest(source=changed):
                self.assertTrue(
                    all(
                        isinstance(item, Individual)
                        for item in plan_groups((member(0), changed))
                    )
                )

    def test_unknown_underdeclared_codec_format_and_human_fallback(self):
        variants = (
            dict(duration_ms=0),
            dict(decoded_frames=16001),
            dict(standalone_pcm_wav=False),
            dict(sample_rate=48000),
            dict(channels=True),
            dict(existing_segments=True),
            dict(effective_metadata_verified=False),
            dict(sequence=True),
        )
        for changes in variants:
            with self.subTest(changes=changes):
                plan = plan_groups((replace(member(0), **changes), member(1)))
                self.assertTrue(all(isinstance(item, Individual) for item in plan))
                self.assertNotEqual(plan[0].reason, "single_complete_source")

    def test_oversized_complete_source_is_not_split(self):
        long = member(0, duration_ms=26000, decoded_frames=416000, size_bytes=832044)
        plan = plan_groups((long,))
        self.assertIs(plan[0].member, long)
        self.assertEqual(plan[0].reason, "complete_source_exceeds_group_limit")

    def test_twenty_target_and_twentyfive_hard_limit(self):
        items = (
            member(0, duration_ms=10000, decoded_frames=160000, size_bytes=320044),
            member(
                1,
                start_ms=10000,
                duration_ms=15000,
                decoded_frames=240000,
                size_bytes=480044,
            ),
        )
        self.assertEqual(plan_groups(items)[0].frames, 400000)
        with self.assertRaises(GroupRefused):
            validate_group(
                Group(
                    (
                        items[0],
                        replace(items[1], duration_ms=15001, decoded_frames=240016),
                    )
                )
            )
        plan = plan_groups(
            tuple(
                member(
                    i,
                    start_ms=i * 5000,
                    duration_ms=5000,
                    decoded_frames=80000,
                    size_bytes=160044,
                )
                for i in range(6)
            )
        )
        self.assertEqual([len(item.members) for item in plan], [4, 2])

    def test_duplicate_sources_refuse_and_identity_changes_with_source(self):
        with self.assertRaises(GroupRefused):
            plan_groups((member(0), member(0)))
        original = Group((member(0), member(1)))
        self.assertNotEqual(
            original.id, Group((member(0), member(1, sha256="b" * 64))).id
        )

    def test_worker_manifest_rejects_reference_or_unknown_fields(self):
        manifest = Group((member(0), member(1))).manifest
        manifest["members"][0]["expected_text"] = "don't leak a reference"
        with self.assertRaises(GroupRefused):
            group_from_manifest(manifest)


class WordMappingTests(unittest.TestCase):
    def setUp(self):
        self.group = Group((member(0), member(1)))

    def test_one_native_segment_crossing_chunks_splits_only_between_words(self):
        words = [
            word(0.2, 0.8, " Premier", ordinal=0),
            word(1.1, 1.4, " deuxième.", ordinal=1),
        ]
        result = map_words(self.group, words)
        self.assertEqual(
            [(x["chunk_id"], x["text"], x["start_ms"], x["end_ms"]) for x in result],
            [("0", "Premier", 200, 800), ("1", "deuxième.", 1100, 1400)],
        )
        self.assertEqual([w for item in result for w in item["native_words"]], words)

    def test_word_crossing_boundary_produces_no_partial_mapping(self):
        with self.assertRaisesRegex(GroupRefused, "word_crosses"):
            map_words(
                self.group, [word(0.1, 0.3, ordinal=0), word(0.99, 1.01, ordinal=1)]
            )

    def test_before_rounding_crossing_boundary_still_refuses(self):
        with self.assertRaisesRegex(GroupRefused, "word_crosses"):
            map_words(self.group, [word(0.999999, 1.000001)])

    def test_positive_native_word_with_zero_rounded_duration_refuses(self):
        with self.assertRaisesRegex(GroupRefused, "rounded_native_interval"):
            map_words(self.group, [word(0.9996, 0.9999)])

    def test_native_invalid_timestamps_and_ordinals_refuse(self):
        variants = [
            word(float("nan"), 0.2),
            word(0.1, float("inf")),
            word(-0.01, 0.2),
            word(2, 2.1),
            word(1, 1),
            word(0.1, 0.2, segment=True),
            {"end": 0.2, "word": "x", "segment_ordinal": 0, "word_ordinal": 0},
        ]
        for words in variants:
            with self.subTest(value=words), self.assertRaises(GroupRefused):
                map_words(self.group, [words])

    def test_duplicate_out_of_order_or_overlapping_native_words_refuse(self):
        variants = [
            [word(0.1, 0.2), word(0.3, 0.4)],
            [word(0.3, 0.5, ordinal=0), word(0.1, 0.2, ordinal=1)],
            [word(0.1, 0.4, ordinal=0), word(0.3, 0.5, ordinal=1)],
        ]
        for words in variants:
            with self.subTest(words=words), self.assertRaises(GroupRefused):
                map_words(self.group, words)

    def test_nonzero_group_offset_preserves_absolute_clock(self):
        shifted = Group(
            tuple(replace(m, start_ms=m.start_ms + 12000) for m in self.group.members)
        )
        row = map_words(shifted, [word(0.1, 0.2)])[0]
        self.assertEqual((row["start_ms"], row["end_ms"]), (12100, 12200))

    def test_actual_native_words_map_13_12_17_without_engine(self):
        fixture = json.loads(
            (
                Path(__file__).parent / "fixtures/actual-group-observations.json"
            ).read_text(encoding="utf-8")
        )
        durations = [5855, 6145, 6750]
        offsets = [0, 5855, 12000]
        group = Group(
            tuple(
                member(
                    i,
                    start_ms=offsets[i],
                    duration_ms=duration,
                    decoded_frames=duration * 16,
                    size_bytes=duration * 32 + 46,
                )
                for i, duration in enumerate(durations)
            )
        )
        mapped = map_words(group, fixture["retained_words"])
        counts = {
            str(i): sum(
                len(x["native_words"]) for x in mapped if x["chunk_id"] == str(i)
            )
            for i in range(3)
        }
        self.assertEqual(counts, {"0": 13, "1": 12, "2": 17})
        self.assertEqual(sum(len(x["native_words"]) for x in mapped), 42)
        self.assertEqual(" ".join(x["text"] for x in mapped), fixture["published_text"])

    def test_publication_guard_rejects_changed_source_human_collision_and_cancel(self):
        variants = [
            dict(
                current_members=(member(0), member(1, sha256="b" * 64)), existing_ids=()
            ),
            dict(
                current_members=(member(0), member(1, existing_segments=True)),
                existing_ids=(),
            ),
            dict(current_members=self.group.members, existing_ids=("live-existing",)),
            dict(
                current_members=self.group.members,
                existing_ids=(),
                cancel_requested=True,
            ),
        ]
        for kwargs in variants:
            with self.subTest(kwargs=kwargs), self.assertRaises(GroupRefused):
                publication_guard(self.group, **kwargs)
        self.assertTrue(
            publication_guard(
                self.group, current_members=self.group.members, existing_ids=()
            )
        )


if __name__ == "__main__":
    unittest.main()
