"""Eight prepared real-file/fake-notification fault scenarios; no devices/SQL."""

from copy import deepcopy
import errno
import json
import re
from pathlib import Path
import unittest
import uuid

import pytest

from scripts.native_chunk_journal import (
    FileOps,
    Limits,
    Reservation,
    commit_chunk,
    commit_buffer,
    reconcile,
    iter_reconcile,
    prepare,
    drain_buffer,
    publish_receipt,
)

SID = "a2c258bb-74b8-4403-8f01-866d81fc5294"


class SimulatedCrash(RuntimeError):
    pass


class FaultOps(FileOps):
    def __init__(self, phase, operation):
        self.phase = phase
        self.operation = operation
        self.fired = False

    def matches(self, phase, operation):
        if not self.fired and (phase, operation) == (self.phase, self.operation):
            self.fired = True
            return True
        return False

    def write(self, target, data, phase):
        if self.matches(phase, "write"):
            target.write(data[:17])
            raise OSError(errno.ENOSPC, "fictitious partial write", target.name)
        return super().write(target, data, phase)

    def flush(self, target, phase):
        if self.matches(phase, "flush"):
            raise OSError(errno.ENOSPC, "fictitious flush failure")
        return super().flush(target, phase)

    def fsync(self, target, phase):
        if self.matches(phase, "fsync"):
            raise OSError(errno.ENOSPC, "fictitious fsync failure")
        return super().fsync(target, phase)

    def create(self, temporary, target, phase):
        if self.matches(phase, "promote"):
            raise OSError(errno.ENOSPC, "fictitious exclusive promotion failure")
        super().create(temporary, target, phase)
        if self.matches(phase, "after_promote"):
            raise SimulatedCrash("fictitious crash after WAV publication")

    def replace(self, temporary, target, phase):
        if self.matches(phase, "replace"):
            raise OSError(errno.ENOSPC, "fictitious manifest replace failure")
        return super().replace(temporary, target, phase)


class DurableChunkCases(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def private_file_root(self, tmp_path_factory):
        # Canonical pytest's temporary root; no qualification env, SDK or SQL.
        # Fixtures run before unittest setUp. No private integration conftest.
        self._file_root = tmp_path_factory.mktemp("nj4")

    def setUp(self):
        root = self._file_root.resolve(strict=True)
        self.root = root / uuid.uuid4().hex
        self.root.mkdir()
        self.state = {
            "buffer": bytearray(b"\x07\0" * 800),
            "start_ms": 1200,
            "sequence": 0,
        }
        self.seen = set()
        self.deliveries = []
        self.total = 0
        self.first = self.commit()
        self.previous = {p.name: p.read_bytes() for p in self.root.iterdir()}

    def commit(self, ops=None, ack=None):
        def persist(track, raw, start):
            return commit_chunk(
                self.root, SID, track, self.state["sequence"], raw, start, ops=ops
            )

        def notify(packet):
            self.deliveries.append(packet["command_id"])
            self.seen.add(packet["command_id"])
            if ack:
                ack(packet)

        packet = commit_buffer(
            self.state, "mic", len(self.state["buffer"]), persist, notify
        )
        self.total += packet["size_bytes"]
        return packet

    def refill(self):
        self.state["buffer"].extend(b"\x08\0" * 320)

    def previous_unchanged(self):
        for name, raw in self.previous.items():
            self.assertEqual((self.root / name).read_bytes(), raw)

    def recovered(self):
        calls = []
        packets = reconcile(self.root, SID, authorize=lambda: calls.append(True))
        self.assertTrue(calls)
        self.previous_unchanged()
        return packets

    # No teardown removes files: all logical-fault evidence remains for ROOT.

    def test_intent_partial_write_flush_fsync_or_promotion_retains_buffer_without_complete_chunk(
        self,
    ):
        for operation in ("write", "flush", "fsync", "promote"):
            with self.subTest(operation=operation):
                self.refill()
                before = deepcopy(self.state)
                total = self.total
                with self.assertRaises(OSError):
                    self.commit(FaultOps("intent", operation))
                self.assertEqual(self.state, before)
                self.assertEqual(self.total, total)
                self.assertFalse((self.root / "mic-00000001.intent").exists())
                self.assertFalse((self.root / "mic-00000001.wav").exists())
                self.assertFalse((self.root / "mic-00000001.json").exists())
                self.assertEqual(len(self.seen), 1)
                self.previous_unchanged()
                self.state[
                    "buffer"
                ].clear()  # Fictive case reset only, never producer behavior.

    def test_partial_WAV_write_has_exact_durable_payload_and_recovers_without_timecode_guess(
        self,
    ):
        self.refill()
        before = deepcopy(self.state)
        with self.assertRaises(OSError):
            self.commit(FaultOps("wav", "write"))
        self.assertEqual(self.state, before)
        self.assertTrue((self.root / "mic-00000001.intent").is_file())
        self.assertFalse((self.root / "mic-00000001.wav").exists())
        self.assertFalse((self.root / "mic-00000001.json").exists())
        packet = self.recovered()[-1]
        expected, data = prepare(
            self.root, SID, "mic", 1, bytes(before["buffer"]), before["start_ms"]
        )
        self.assertEqual(packet, expected)
        self.assertEqual(Path(packet["path"]).read_bytes(), data)
        self.assertTrue(
            any(
                re.fullmatch(r"wav-[a-f0-9]{32}\.pending", p.name) is not None
                and p.name.endswith(".pending")
                and p.stat().st_size == 17
                for p in self.root.iterdir()
            )
        )

    def test_WAV_flush_fsync_or_exclusive_promotion_failure_is_recoverable_and_never_overwrites_prior_WAV(
        self,
    ):
        # Each subcase uses an explicit next sequence; prior chunks remain immutable.
        for operation in ("flush", "fsync", "promote"):
            with self.subTest(operation=operation):
                self.refill()
                before = deepcopy(self.state)
                with self.assertRaises(OSError):
                    self.commit(FaultOps("wav", operation))
                self.assertEqual(self.state, before)
                self.previous_unchanged()
                self.recovered()
                self.commit()

    def test_logical_crash_after_WAV_promotion_repairs_only_from_exact_intent(self):
        self.refill()
        before = deepcopy(self.state)
        with self.assertRaises(SimulatedCrash):
            self.commit(FaultOps("wav", "after_promote"))
        self.assertEqual(self.state, before)
        self.assertTrue((self.root / "mic-00000001.wav").is_file())
        self.assertFalse((self.root / "mic-00000001.json").exists())
        packet = self.recovered()[-1]
        expected, _ = prepare(
            self.root, SID, "mic", 1, bytes(before["buffer"]), before["start_ms"]
        )
        self.assertEqual(packet, expected)
        self.assertEqual(packet["command_id"], expected["command_id"])

    def test_manifest_write_flush_fsync_replace_fault_preserves_preimage_and_recovers_exactly(
        self,
    ):
        for operation in ("write", "flush", "fsync", "replace"):
            with self.subTest(operation=operation):
                self.refill()
                before = deepcopy(self.state)
                sequence = before["sequence"]
                with self.assertRaises(OSError):
                    self.commit(FaultOps("manifest", operation))
                self.assertEqual(self.state, before)
                path = self.root / f"mic-{sequence:08d}.json"
                self.assertFalse(path.exists())
                packet = self.recovered()[-1]
                self.assertEqual(json.loads(path.read_text()), packet)
                self.commit()
                self.previous_unchanged()

    def test_incompatible_manifest_is_retained_and_bad_intent_or_unidentified_legacy_orphan_refuses(
        self,
    ):
        self.refill()
        with self.assertRaises(OSError):
            self.commit(FaultOps("manifest", "replace"))
        path = self.root / "mic-00000001.json"
        for old in (
            b"{truncated",
            json.dumps({"kind": "chunk", "session_id": str(uuid.uuid4())}).encode(),
        ):
            path.write_bytes(old)
            self.recovered()
            self.assertTrue(
                any(p.read_bytes() == old for p in self.root.glob("*.preimage"))
            )
        intent = self.root / "mic-00000001.intent"
        original = intent.read_bytes()
        altered = json.loads(original)
        altered["packet"]["start_ms"] += 1
        intent.write_text(json.dumps(altered))
        before_wav = (self.root / "mic-00000001.wav").read_bytes()
        with self.assertRaises(ValueError):
            self.recovered()
        self.assertEqual((self.root / "mic-00000001.wav").read_bytes(), before_wav)
        # Restore own fictive intent, then create a separate deliberately unknowable orphan.
        intent.write_bytes(original)
        orphan = self.root / "system-00000099.wav"
        orphan.write_bytes(b"FICTIVE legacy bytes")
        with self.assertRaisesRegex(ValueError, "historical native orphan"):
            self.recovered()
        self.assertEqual(orphan.read_bytes(), b"FICTIVE legacy bytes")
        self.previous_unchanged()

    def test_notification_failure_retries_exact_command_without_advancement_or_fake_duplicate_ACK(
        self,
    ):
        self.refill()
        before = deepcopy(self.state)
        total = self.total

        def fail(_packet):
            raise OSError("fictitious pipe failure AFTER durable pair")

        with self.assertRaises(OSError):
            self.commit(ack=fail)
        self.assertEqual(self.state, before)
        self.assertEqual(self.total, total)
        packet = json.loads((self.root / "mic-00000001.json").read_text())
        first = packet["command_id"]
        retry = self.commit()
        self.assertEqual(retry["command_id"], first)
        self.assertEqual(self.deliveries[-2:], [first, first])
        self.assertEqual(len(self.seen), 2)
        self.assertEqual(self.state["sequence"], 2)
        self.previous_unchanged()

    def test_short_drain_retains_start_buffer_and_rejects_recovery_without_current_authority(
        self,
    ):
        self.refill()
        before = deepcopy(self.state)
        with self.assertRaises(OSError):
            self.commit(FaultOps("manifest", "fsync"))
        self.assertEqual(self.state, before)
        self.assertEqual(
            before["start_ms"], self.first["start_ms"] + self.first["duration_ms"]
        )
        metadata = {p.name: p.read_bytes() for p in self.root.iterdir()}

        def denied():
            raise PermissionError("fictitious revoked current authority")

        with self.assertRaises(PermissionError):
            reconcile(self.root, SID, authorize=denied)
        self.assertEqual(
            {p.name: p.read_bytes() for p in self.root.iterdir()}, metadata
        )
        packet = self.recovered()[-1]
        self.assertEqual(packet["duration_ms"], len(before["buffer"]) // 32)
        self.assertEqual(packet["start_ms"], before["start_ms"])
        self.previous_unchanged()

    def test_resampler_tail_crosses_full_fragment_then_short_fragment_with_exact_timecodes(
        self,
    ):
        self.state["buffer"] = bytearray(b"\x09\0" * (160000 // 2 + 320))
        raw = bytes(self.state["buffer"])
        start = self.state["start_ms"]
        sequence = self.state["sequence"]
        packets = []

        def flush(amount):
            def persist(track, data, stamp):
                return commit_chunk(
                    self.root, SID, track, self.state["sequence"], data, stamp
                )

            packets.append(
                commit_buffer(self.state, "mic", amount, persist, lambda _: None)
            )

        drain_buffer(self.state, flush)
        self.assertEqual(
            [(p["sequence"], p["start_ms"], p["duration_ms"]) for p in packets],
            [(sequence, start, 5000), (sequence + 1, start + 5000, 20)],
        )
        expected0, wav0 = prepare(self.root, SID, "mic", sequence, raw[:160000], start)
        expected1, wav1 = prepare(
            self.root, SID, "mic", sequence + 1, raw[160000:], start + 5000
        )
        self.assertEqual(packets, [expected0, expected1])
        self.assertEqual(self.state["buffer"], bytearray())
        self.assertEqual(Path(packets[0]["path"]).read_bytes(), wav0)
        self.assertEqual(Path(packets[1]["path"]).read_bytes(), wav1)
        self.previous_unchanged()

    def test_drain_failure_after_full_commit_retains_only_short_tail_with_actual_next_start(
        self,
    ):
        self.state["buffer"] = bytearray(b"\x0a\0" * (160000 // 2 + 320))
        start = self.state["start_ms"]
        sequence = self.state["sequence"]

        def flush(amount):
            fault = (
                FaultOps("manifest", "replace")
                if self.state["sequence"] == sequence + 1
                else None
            )

            def persist(track, data, stamp):
                return commit_chunk(
                    self.root,
                    SID,
                    track,
                    self.state["sequence"],
                    data,
                    stamp,
                    ops=fault,
                )

            commit_buffer(self.state, "mic", amount, persist, lambda _: None)

        with self.assertRaises(OSError):
            drain_buffer(self.state, flush)
        self.assertEqual(self.state["sequence"], sequence + 1)
        self.assertEqual(self.state["start_ms"], start + 5000)
        self.assertEqual(self.state["buffer"], bytearray(b"\x0a\0" * 320))
        self.previous_unchanged()
        self.assertEqual(self.recovered()[-1]["duration_ms"], 20)

    def test_exact_journal_overhead_refuses_before_open_and_preserves_buffer_WAV_and_counters(
        self,
    ):
        self.refill()
        before = deepcopy(self.state)
        files = {p.name: p.read_bytes() for p in self.root.iterdir()}
        total = sum(len(raw) for raw in files.values())

        class OpenGuard(FileOps):
            def open(self, path):
                raise AssertionError("quota refusal must precede any write open")

        # Raw PCM fits this margin; complete base64 intent plus two retained names does not.
        def persist(track, data, stamp):
            return commit_chunk(
                self.root,
                SID,
                track,
                self.state["sequence"],
                data,
                stamp,
                ops=OpenGuard(),
                limits=Limits(storage_bytes=total + len(data)),
            )

        with self.assertRaisesRegex(ValueError, "cumulative storage quota"):
            commit_buffer(
                self.state, "mic", len(self.state["buffer"]), persist, lambda _: None
            )
        self.assertEqual(self.state, before)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, files)

    def test_free_space_checks_exact_payload_before_open_including_intent_and_manifest(
        self,
    ):
        self.refill()
        before = deepcopy(self.state)
        files = {p.name: p.read_bytes() for p in self.root.iterdir()}

        class FreeGuard(FileOps):
            def free_bytes(self, directory):
                return 128 * 1024**2 + len(before["buffer"]) + 44

            def open(self, path):
                raise AssertionError(
                    "full journal payload admission must precede write open"
                )

        def persist(track, data, stamp):
            return commit_chunk(
                self.root,
                SID,
                track,
                self.state["sequence"],
                data,
                stamp,
                ops=FreeGuard(),
            )

        with self.assertRaisesRegex(ValueError, "free-space reserve"):
            commit_buffer(
                self.state, "mic", len(self.state["buffer"]), persist, lambda _: None
            )
        self.assertEqual(self.state, before)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, files)

    def test_completed_WAV_quota_is_separate_from_journal_and_includes_header(self):
        self.refill()
        before = deepcopy(self.state)
        files = {p.name: p.read_bytes() for p in self.root.iterdir()}
        old = self.first["size_bytes"]
        with self.assertRaisesRegex(ValueError, "completed WAV quota"):
            commit_chunk(
                self.root,
                SID,
                "mic",
                self.state["sequence"],
                bytes(self.state["buffer"]),
                self.state["start_ms"],
                limits=Limits(audio_bytes=old + len(self.state["buffer"])),
            )
        self.assertEqual(self.state, before)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, files)

    def test_recovery_rejects_cumulative_bytes_and_counts_before_repairing_any_fragment(
        self,
    ):
        self.refill()
        with self.assertRaises(OSError):
            self.commit(FaultOps("manifest", "replace"))
        files = {p.name: p.read_bytes() for p in self.root.iterdir()}
        intent_bytes = sum(len(v) for k, v in files.items() if k.endswith(".intent"))
        for limits in (
            Limits(intent_bytes=intent_bytes - 1),
            Limits(intent_count=1),
            Limits(file_count=len(files) - 1),
            Limits(storage_bytes=sum(len(v) for v in files.values()) - 1),
        ):
            with self.subTest(limits=limits.__dict__):
                with self.assertRaises(ValueError):
                    list(
                        iter_reconcile(
                            self.root, SID, authorize=lambda: None, limits=limits
                        )
                    )
                self.assertEqual(
                    {p.name: p.read_bytes() for p in self.root.iterdir()}, files
                )

    def test_recovery_yields_first_pair_before_second_repair_and_consumer_ack_failure_stops_progress(
        self,
    ):
        self.refill()
        with self.assertRaises(OSError):
            self.commit(FaultOps("manifest", "replace"))
        # Prepare a distinct exact later intent whose WAV/manifest have not been published.
        third = {"buffer": bytearray(b"\x0b\0" * 320), "start_ms": 1290, "sequence": 2}
        with self.assertRaises(OSError):
            commit_chunk(
                self.root,
                SID,
                "mic",
                2,
                bytes(third["buffer"]),
                third["start_ms"],
                ops=FaultOps("wav", "write"),
            )
        future = self.root / "mic-00000002.wav"
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        iterator = iter_reconcile(self.root, SID, authorize=lambda: None)
        first = next(iterator)
        self.assertEqual(first, self.first)
        self.assertFalse(future.exists())
        second = next(iterator)
        self.assertEqual(second["sequence"], 1)
        self.assertFalse(future.exists())
        # Real consumer stops requesting packets when _persist/SQL ACK raises.
        iterator.close()
        self.assertFalse(future.exists())
        for name, raw in before.items():
            if name != "mic-00000001.json":
                self.assertEqual((self.root / name).read_bytes(), raw)
        third_recovered = list(iter_reconcile(self.root, SID, authorize=lambda: None))[
            -1
        ]
        self.assertEqual(third_recovered["sequence"], 2)
        self.assertEqual(third_recovered["start_ms"], 1290)

    def test_preimage_storage_and_reservation_claim_are_accounted_before_manifest_mutation(
        self,
    ):
        self.refill()
        with self.assertRaises(OSError):
            self.commit(FaultOps("manifest", "replace"))
        path = self.root / "mic-00000001.json"
        old = b"{partial fictitious preimage"
        path.write_bytes(old)
        files = {p.name: p.read_bytes() for p in self.root.iterdir()}
        total = sum(len(v) for v in files.values())
        packet, wav = prepare(
            self.root,
            SID,
            "mic",
            1,
            bytes(self.state["buffer"]),
            self.state["start_ms"],
        )
        encoded = json.dumps(packet, ensure_ascii=False, allow_nan=False).encode(
            "utf-8"
        )
        with self.assertRaisesRegex(ValueError, "cumulative storage quota"):
            list(
                iter_reconcile(
                    self.root,
                    SID,
                    authorize=lambda: None,
                    limits=Limits(storage_bytes=total + len(encoded)),
                )
            )
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, files)
        reservation = Reservation(self.root, [(5, 1)], FileOps(), Limits())
        with self.assertRaisesRegex(ValueError, "admitted transaction"):
            reservation.claim(6, 1)

    def test_short_phase_pending_publishes_receipt_and_retained_preimage_on_calibrated_long_parent(self):
        # Geometry matches ROOT's causal probe. Do not require a particular OS
        # policy or reproduce a rejected long open as a passing-test condition.
        parent_chars = 167
        segment_chars = parent_chars - len(str(self.root)) - 1
        self.assertTrue(1 <= segment_chars <= 255)
        directory = self.root / ("p" * segment_chars)
        directory.mkdir()
        self.assertEqual(len(str(directory)), parent_chars)
        opened, publications = [], []

        class RecordingOps(FileOps):
            def open(self, path):
                opened.append(path)
                return super().open(path)

            def create(self, temporary, target, phase):
                publications.append((phase, temporary, target))
                return super().create(temporary, target, phase)

            def replace(self, temporary, target, phase):
                publications.append((phase, temporary, target))
                return super().replace(temporary, target, phase)

        legacy_pending = directory / "mic-00000000.wav.old.pending"
        legacy_pending.write_bytes(b"retained historical pending")
        ops = RecordingOps()
        packet = commit_chunk(directory, SID, "mic", 0, b"\x01\0" * 80, 0, ops=ops)
        wav = Path(packet["path"]).read_bytes()
        manifest = Path(packet["path"]).with_suffix(".json")
        manifest_before = manifest.read_bytes()
        receipt_path = Path(packet["path"]).with_suffix(".receipt.json")
        receipt_path.write_bytes(b"ERROR")
        receipt = {
            "acknowledged": True,
            "session_id": SID,
            "accepted_chunk": {
                "track": "mic", "seq": 0,
                "sha256": packet["sha256"], "size_bytes": packet["size_bytes"],
            },
        }
        authority = []
        publish_receipt(directory, SID, packet, receipt, authorize=lambda: authority.append(True), ops=ops)
        self.assertTrue(authority)
        self.assertEqual(receipt_path.read_bytes(), json.dumps(receipt).encode("utf-8"))
        retained = list(directory.glob("*.previous-*.receipt.json"))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].read_bytes(), b"ERROR")
        # Same final/retained names. Only the temporary basename is shortened.
        old_pending = retained[0].with_name(retained[0].name + "." + "a" * 32 + ".pending")
        self.assertEqual(len(str(old_pending)), 276)
        self.assertEqual(len(old_pending.name), 108)
        preimages = [(temporary, target) for phase, temporary, target in publications if phase == "receipt-preimage"]
        self.assertEqual(len(preimages), 1)
        temporary, target = preimages[0]
        self.assertEqual(target, retained[0])
        self.assertEqual(len(str(temporary)), 225)
        self.assertEqual(len(temporary.name), 57)
        self.assertEqual(temporary.read_bytes(), b"ERROR")
        self.assertEqual(legacy_pending.read_bytes(), b"retained historical pending")
        self.assertEqual(Path(packet["path"]).read_bytes(), wav)
        self.assertEqual(manifest.read_bytes(), manifest_before)
        for path in opened:
            self.assertEqual(path.parent, directory)
            self.assertRegex(path.name, r"^(intent|wav|preimage|manifest|receipt|receipt-preimage)-[a-f0-9]{32}\.pending$")
            self.assertLessEqual(len(str(path)), 225)

