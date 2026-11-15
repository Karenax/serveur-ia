"""Failure and concurrency contracts for local capture/STT and arbitration."""
import hashlib
import io
import json
import threading
import time
from types import SimpleNamespace
import uuid
import wave

import numpy as np
import pytest

from app.services import audio_capture, inference_scheduler as scheduler, live_speech
from scripts.transcribe_live import transcribe


def wav_bytes(seconds=1):
    output = io.BytesIO()
    with wave.open(output, "wb") as source:
        source.setnchannels(1)
        source.setsampwidth(2)
        source.setframerate(16000)
        source.writeframes(b"\0\0" * round(16000 * seconds))
    return output.getvalue()


def chunk_file(root, data, sequence=0, **overrides):
    path = root / f"chunk-{sequence}.audio"
    path.write_bytes(data)
    return {"id": str(uuid.uuid4()), "session_id": "test", "track": "mic",
            "sequence": sequence, "mime_type": "audio/webm", "storage_path": str(path),
            "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "start_ms": sequence * 1000, "duration_ms": 1000, **overrides}


def test_container_headers_reassembled_and_gaps_refused(tmp_path):
    first = chunk_file(tmp_path, b"\x1aE\xdf\xa3" + b"header-data")
    second = chunk_file(tmp_path, b"headerless-cluster", 1)
    prepared = audio_capture.prepare_chunk(second, [first, second],
        storage_root=tmp_path, derived_root=tmp_path / "derived")
    assert prepared.assembled and prepared.offset_ms == 0
    assert prepared.clip_start_ms == 500 and prepared.clip_end_ms == 2000
    assert prepared.path.read_bytes() == b"\x1aE\xdf\xa3header-dataheaderless-cluster"
    third = chunk_file(tmp_path, b"third-cluster", 2)
    with pytest.raises(ValueError, match="manquants"):
        audio_capture.prepare_chunk(third, [first, third],
            storage_root=tmp_path, derived_root=tmp_path / "derived")
    latest = audio_capture.prepare_chunk(third, [first, second, third],
        storage_root=tmp_path, derived_root=tmp_path / "derived")
    assert latest.path == prepared.path  # cumulative copies must not exhaust disk
    assert latest.path.read_bytes().endswith(b"third-cluster")


def test_tampered_audio_and_paths_are_never_decoded(tmp_path):
    chunk = chunk_file(tmp_path, wav_bytes(), mime_type="audio/wav")
    assert not audio_capture.prepare_chunk(chunk, [], storage_root=tmp_path,
        derived_root=tmp_path / "derived").assembled
    path = tmp_path / "chunk-0.audio"
    changed = bytearray(path.read_bytes())
    changed[-1] = 1
    path.write_bytes(changed)
    with pytest.raises(ValueError, match="Empreinte"):
        audio_capture.prepare_chunk(chunk, [], storage_root=tmp_path,
            derived_root=tmp_path / "derived")
    with pytest.raises(ValueError, match="autorisé"):
        audio_capture.stored_path(chunk, tmp_path / "other")


def test_pcm_live_overlap_is_not_used_by_final_mixer(tmp_path):
    first = chunk_file(tmp_path, wav_bytes(), mime_type="audio/wav")
    second = chunk_file(tmp_path, wav_bytes(), sequence=1, mime_type="audio/wav")
    normal = audio_capture.prepare_chunk(second, [first, second], storage_root=tmp_path,
                                        derived_root=tmp_path / "derived")
    context = audio_capture.prepare_chunk(second, [first, second], storage_root=tmp_path,
        derived_root=tmp_path / "derived", with_pcm_context=True)
    assert normal.offset_ms == 1000 and not normal.assembled
    assert context.offset_ms == 500 and context.clip_end_ms == 1500
    assert audio_capture.wav_duration_ms(context.path) == 1500
    second["start_ms"] = 2000  # A real pause must not create artificial continuity.
    paused = audio_capture.prepare_chunk(second, [first, second], storage_root=tmp_path,
        derived_root=tmp_path / "derived", with_pcm_context=True)
    assert not paused.assembled and paused.offset_ms == 2000


def test_speech_qualification_is_invalidated_when_cpu_profile_changes(tmp_path, monkeypatch):
    from app.services import meeting_audio
    models = tmp_path / "models"
    models.mkdir()
    whisper = models / "whisper-small"
    whisper.mkdir()
    binary = whisper / "model.bin"
    binary.write_bytes(b"fixture-model-identity")
    config = models / "models.json"
    config.write_text(json.dumps({"model": "small", "whisper": str(whisper)}))
    monkeypatch.setenv("PB_SPEECH_MODELS_DIR", str(models))
    monkeypatch.setenv("PB_SPEECH_THREADS", "4")
    monkeypatch.setattr(live_speech, "ROOT", tmp_path)
    monkeypatch.setattr(meeting_audio, "runtime_status", lambda **_kwargs: {"ready": True})
    report = tmp_path / "logs" / "foresight-runtime" / "audio-qualification.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({"passed": True, "model_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "runtime_profile_key": live_speech.speech_profile_key(models),
        "model_identity": {"size": binary.stat().st_size, "mtime_ns": binary.stat().st_mtime_ns,
                           "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest()}}))
    assert live_speech.runtime_status()["real_test_passed"]
    monkeypatch.setenv("PB_SPEECH_THREADS", "8")
    status = live_speech.runtime_status()
    assert status["installed"] and not status["ready"] and not status["real_test_passed"]
    assert status["runtime_profile"]["cpu_threads"] == 8
    monkeypatch.setenv("PB_SPEECH_THREADS", "17")
    with pytest.raises(ValueError, match="threads"):
        live_speech.speech_profile(models)


def test_overlap_only_keeps_new_words_and_absolute_timecodes():
    words = [SimpleNamespace(start=.1, end=.3, word=" précédent"),
             SimpleNamespace(start=.6, end=.9, word=" nouveau")]

    class Model:
        def transcribe(self, samples, **kwargs):
            assert kwargs["condition_on_previous_text"] is False
            assert len(samples) == 16000
            return [SimpleNamespace(words=words, no_speech_prob=.01)], None

    result = transcribe(Model(), np.zeros(48000), {"offset_ms": 0,
        "clip_start_ms": 1500, "clip_end_ms": 2500, "keep_from_ms": 2000, "track": "system"})
    assert result["segments"] == [{"start_ms": 2100, "end_ms": 2400,
                                    "text": "nouveau", "speaker": "system"}]


def test_inference_priority_orders_waiters_without_preempting():
    resource = "test:" + uuid.uuid4().hex
    order, failures = [], []
    release = threading.Event()
    active = threading.Event()

    def running():
        with scheduler.lease(resource, priority=30):
            active.set()
            release.wait(3)
            order.append("running")

    def waiting(name, priority):
        try:
            with scheduler.lease(resource, priority=priority, timeout=3):
                order.append(name)
        except Exception as exc:
            failures.append(exc)

    worker = threading.Thread(target=running)
    worker.start()
    assert active.wait(2)
    low = threading.Thread(target=waiting, args=("background", 50))
    high = threading.Thread(target=waiting, args=("question", 0))
    low.start()
    high.start()
    deadline = time.monotonic() + 2
    while scheduler.status()["waiting"] < 2 and time.monotonic() < deadline:
        time.sleep(.01)
    assert scheduler.status()["waiting"] >= 2
    assert order == []
    release.set()
    for thread in (worker, low, high):
        thread.join(3)
        assert not thread.is_alive()
    assert not failures and order == ["running", "question", "background"]


def test_wait_cancellation_leaves_no_leaked_reservation():
    resource = "test:" + uuid.uuid4().hex
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(scheduler.InferenceBusy, match="annulée"):
        with scheduler.lease(resource, cancel=cancelled):
            pytest.fail("Cancelled inference ran")
    with scheduler.lease(resource, timeout=0):
        with scheduler.lease(resource, timeout=0):
            assert scheduler.status()["active"] >= 1


@pytest.fixture
def isolated_speech_db(tmp_path, monkeypatch, isolated_settings):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app import db as brain_db
    from app.config import settings
    engine = create_engine(f"sqlite:///{(tmp_path / 'speech.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    try:
        brain_db.Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        monkeypatch.setattr(brain_db, "SessionLocal", session_factory)
        monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
        yield session_factory
    finally:
        engine.dispose()


def test_worker_retry_preserves_durable_human_correction(tmp_path, monkeypatch, isolated_speech_db):
    from app.meeting_session_models import MeetingAudioChunk, MeetingSession, LiveTranscriptSegment
    from app.meeting_session_schemas import Command
    from app.services import meeting_sessions
    from backend.app.services.project_operator import Operator, operator_context
    SessionLocal = isolated_speech_db
    from app.services.settings_service import save_section
    with SessionLocal() as db:
        save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': True})
    data = chunk_file(tmp_path, wav_bytes(), mime_type="audio/wav")
    live_speech._stop.clear()

    class FakeResident:
        loaded = True
        calls = 0

        def transcribe(self, *args, **kwargs):
            self.calls += 1
            return {"segments": [{"start_ms": 0, "end_ms": 800, "speaker": "mic", "text": "Machine"}],
                    "duration_ms": 1000, "compute_s": .1}

    resident = FakeResident()
    monkeypatch.setattr(live_speech, "_resident", resident)
    monkeypatch.setattr(live_speech, "wake_worker", lambda: None)
    from app.services import session_proactive
    committed_wakes = []

    def observe_committed_transcript():
        with SessionLocal() as reader:
            committed_wakes.append(reader.query(LiveTranscriptSegment).filter_by(chunk_id=data['id']).count())

    monkeypatch.setattr(session_proactive, 'wake_worker', observe_committed_transcript)
    with SessionLocal() as db:
        row = MeetingSession(title="Fictif", operator_id="test", state="paused")
        db.add(row)
        db.flush()
        data["session_id"] = row.id
        chunk = MeetingAudioChunk(**data, filename="fictif.wav")
        db.add(chunk)
        db.commit()
    live_speech.process_chunk(data["id"])
    assert resident.calls == 1
    assert committed_wakes == [1]
    with SessionLocal() as db:
        segment = db.query(LiveTranscriptSegment).filter_by(chunk_id=data["id"]).one()
        segment.text, segment.revision = "Correction humaine", 2
        db.get(MeetingAudioChunk, data["id"]).speech_status = "failed"
        db.commit()
    live_speech.process_chunk(data["id"])
    assert resident.calls == 1  # Failed work is never admitted by the worker itself.
    assert committed_wakes == [1]
    with SessionLocal() as db:
        segment = db.query(LiveTranscriptSegment).filter_by(chunk_id=data["id"]).one()
        assert segment.text == "Correction humaine" and segment.revision == 2
        assert db.get(MeetingAudioChunk, data["id"]).speech_status == "failed"
        row = db.get(MeetingSession, data["session_id"])
        with operator_context(Operator(id="test", role="owner")):
            receipt = meeting_sessions.retry_transcription(db, row.id,
                Command(command_id=str(uuid.uuid4()), expected_revision=row.revision))
        assert receipt["retried_chunks"] == 1
        assert db.get(MeetingAudioChunk, data["id"]).speech_status == "pending"
    live_speech.process_chunk(data["id"])
    assert resident.calls == 2
    assert committed_wakes == [1, 1]
    with SessionLocal() as db:
        segment = db.query(LiveTranscriptSegment).filter_by(chunk_id=data["id"]).one()
        assert segment.text == "Correction humaine" and segment.revision == 2
        assert db.get(MeetingAudioChunk, data["id"]).speech_status == "completed"


def test_worker_defers_pending_fragment_when_legacy_batch_owns_cpu(tmp_path, monkeypatch, isolated_speech_db):
    from app.meeting_session_models import MeetingAudioChunk, MeetingSession
    from app.services import audio_cpu_coordinator
    SessionLocal = isolated_speech_db
    from app.services.settings_service import save_section
    with SessionLocal() as db:
        save_section(db, 'foresight', {'enabled': True, 'live_transcription_enabled': True})
    data = chunk_file(tmp_path, wav_bytes(), mime_type="audio/wav")
    with SessionLocal() as db:
        session = MeetingSession(title="Admission fictive", operator_id="test", state="paused")
        db.add(session)
        db.flush()
        data["session_id"] = session.id
        db.add(MeetingAudioChunk(**data, filename="fictif.wav"))
        db.commit()
    monkeypatch.setattr(audio_cpu_coordinator, "_batch_owner", ("batch-fictif", object()))
    monkeypatch.setattr(live_speech, "_process_chunk", lambda cid: pytest.fail("STT must not compete with the batch"))
    assert live_speech.process_chunk(data["id"]) is False
    with SessionLocal() as db:
        row = db.get(MeetingAudioChunk, data["id"])
        assert row.speech_status == "pending" and "attente" in row.speech_error


def test_finalize_mix_preserves_both_tracks_and_offsets(tmp_path):
    if not live_speech.runtime_paths()[0].is_file():
        pytest.skip("Optional isolated audio runtime is not installed")
    # Two distinct tones; positive mic and negative system samples prove both
    # tracks are present, and system's delay proves absolute placement.
    def pcm(frequency):
        output = io.BytesIO()
        with wave.open(output, "wb") as source:
            source.setnchannels(1)
            source.setsampwidth(2)
            source.setframerate(16000)
            source.writeframes((np.sin(np.arange(16000)*2*np.pi*frequency/16000)*16000).astype("<i2").tobytes())
        return output.getvalue()

    mic = chunk_file(tmp_path, pcm(440), mime_type="audio/wav", track="mic")
    system = chunk_file(tmp_path, pcm(880), 0, mime_type="audio/wav", track="system", start_ms=1000)
    # chunk_file shares filenames, so retain mic in its own generated filename.
    mic_path = tmp_path / "mic.wav"
    mic_path.write_bytes(pcm(440))
    mic["storage_path"] = str(mic_path)
    mixed = live_speech.consolidate_session_audio([mic, system],
        lambda row: row["storage_path"], storage_root=tmp_path)
    import subprocess
    result = subprocess.run([str(live_speech.runtime_paths()[0]), '-c',
        'import json,sys,numpy as np; from faster_whisper.audio import decode_audio; '
        'x=decode_audio(sys.argv[1],sampling_rate=16000); '
        'print(json.dumps({"frames":len(x),"frequencies":[int(np.argmax(abs(np.fft.rfft(x[a:a+16000])))) for a in (0,16000)]}))',
        str(mixed)], capture_output=True, text=True, timeout=30, check=True)
    decoded = json.loads(result.stdout)
    assert mixed.suffix == '.ogg' and mixed.stat().st_size < 16000
    assert decoded == {'frames': 32000, 'frequencies': [440, 880]}
