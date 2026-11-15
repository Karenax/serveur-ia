"""Three-phase meeting workflow, grounded synthesis, isolation and crash recovery."""
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal as Brain
from app.models import (MeetingRecording, Project as BrainProject, SourceArtifact,
                        KnowledgeItem, ProvenanceLink, MemoryProjection)
from app.services import meeting_audio as service
from app.services.settings_service import save_section
from backend.app.db import SessionLocal as ERP
from backend.app.models import BrainLink, Meeting, MeetingAction

client = TestClient(app)
SEGMENTS = [
    {"id": "seg-1", "start": 0, "end": 4, "speaker": "SPEAKER_01", "text": "Nous validons le diamètre de 50 mm."},
    {"id": "seg-2", "start": 4, "end": 10, "speaker": "SPEAKER_02", "text": "Jean prépare le plan pour le 2026-10-09."}]
SUMMARY = {"overview": "Validation du diamètre et préparation du plan.",
           "decisions": [{"text": "Diamètre validé : 50 mm", "segment_id": "seg-1", "quote": "validons le diamètre de 50 mm"}],
           "actions": [{"text": "Préparer le plan", "segment_id": "seg-2", "quote": "Jean prépare le plan", "owner": "Jean", "due_date": "2026-10-09"}],
           "open_points": []}


@pytest.fixture
def context(monkeypatch):
    code = "AUDIO-" + uuid.uuid4().hex[:8]
    pid = client.post("/api/v1/projects", json={"code": code, "title": "Projet réunion"}).json()["id"]
    with Brain() as db:
        project = BrainProject(code=code, name="Projet réunion")
        db.add(project)
        db.commit()
        bid = project.id
    with ERP() as db:
        db.add(BrainLink(project_id=pid, brain_project_id=bid, brain_code=code))
        db.commit()
    monkeypatch.setattr(service, "runtime_status", lambda: {"ready": True, "detail": "Prêt", "model": "small", "device": "cpu"})
    monkeypatch.setattr(service, "index_project", lambda _: None)
    path = f"/api/v1/projects/{pid}/recordings"
    response = client.post(path, data={"title": "Point technique", "date": "2026-10-02", "num_speakers": 2},
                           files={"file": ("reunion.wav", b"fictitious-audio-" + code.encode(), "audio/wav")})
    assert response.status_code == 201, response.text
    rid = response.json()["id"]
    return pid, bid, rid, path + "/" + rid


def transcribed(context, monkeypatch):
    _, _, rid, path = context
    def fake_transcribe(row, _):
        service._progress(row.id, "transcribing", 70, duration_seconds=10, processed_seconds=7)
        return {"segments": SEGMENTS, "language": "fr"}
    monkeypatch.setattr(service, "_transcribe", fake_transcribe)
    assert client.post(path + "/transcribe").status_code == 202
    service.run_job(rid)
    result = client.get(path).json()
    assert result["revision"] == 1 and result["job_status"] == "completed"
    return result


def reviewed(context, monkeypatch):
    transcribed(context, monkeypatch)
    response = client.put(context[3] + "/transcript", json={"revision": 1, "segments": SEGMENTS,
                            "speaker_names": {"SPEAKER_01": "Marie", "SPEAKER_02": "Jean"}, "validate": True})
    assert response.status_code == 200, response.text
    return response.json()


def drafted(context, monkeypatch):
    row = reviewed(context, monkeypatch)
    with Brain() as db:
        save_section(db, "ai", {"enabled": True, "provider": "ollama", "model": "test"})
    monkeypatch.setattr(service, "chat_json", lambda *_args, **_kwargs: json.dumps(SUMMARY))
    assert client.post(context[3] + "/synthesize").status_code == 202
    service.run_job(context[2])
    return client.get(context[3]).json(), row


def test_three_phases_and_same_knowledge_engine(context, monkeypatch):
    pid, bid, rid, path = context
    assert client.post(path + "/synthesize").status_code == 409
    draft, reviewed_row = drafted(context, monkeypatch)
    assert draft["summary_revision"] == reviewed_row["revision"]
    with Brain() as db:
        assert db.query(KnowledgeItem).filter_by(project_id=bid).count() == 0
        artifact = db.query(SourceArtifact).filter_by(source_id=draft["source_id"], kind="transcription").one()
        assert "Marie" in artifact.content_text and "Jean" in artifact.content_text
        assert artifact.content_json["segments"][1]["id"] == "seg-2"
    result = client.post(path + "/publish", json={"revision": draft["revision"], "summary": SUMMARY})
    assert result.status_code == 200, result.text
    assert result.json()["published_meeting_id"] == rid
    with Brain() as db:
        assert db.query(KnowledgeItem).filter_by(project_id=bid, status="validated").count() == 3
        links = db.query(ProvenanceLink).filter_by(source_id=draft["source_id"]).all()
        assert len(links) == 3
        assert any(p.locator["segment_id"] == "seg-2" and p.locator["start"] == 4 for p in links)
        assert db.query(MemoryProjection).filter_by(project_id=bid, purpose="truth", status="pending").count() == 3
    with ERP() as db:
        report = db.get(Meeting, rid)
        assert report.project_id == pid and report.participants == "Marie, Jean"
        action = db.query(MeetingAction).filter_by(meeting_id=rid).one()
        assert action.owner == "Jean" and action.due_date == "2026-10-09" and action.task_id is None
    # A retry is idempotent and a published transcript is immutable.
    assert client.post(path + "/publish", json={"revision": draft["revision"], "summary": SUMMARY}).status_code == 200
    assert client.put(path + "/transcript", json={"revision": draft["revision"], "segments": SEGMENTS, "validate": False}).status_code == 409
    with ERP() as db:
        assert db.query(MeetingAction).filter_by(meeting_id=rid).count() == 1


def test_review_corrections_invalidate_synthesis_and_keep_history(context, monkeypatch):
    draft, _ = drafted(context, monkeypatch)
    path = context[3]
    changed = [dict(s) for s in SEGMENTS]
    changed[0]["text"] = "Nous validons le diamètre de 55 mm."
    names = draft["speaker_names"]
    correction = client.put(path + "/transcript", json={"revision": draft["revision"], "segments": changed,
                                                         "speaker_names": names, "validate": True})
    assert correction.status_code == 200
    row = correction.json()
    assert row["revision"] == draft["revision"] + 1
    assert row["summary_revision"] != row["revision"]
    assert client.post(path + "/publish", json={"revision": row["revision"], "summary": SUMMARY}).status_code == 409
    assert client.put(path + "/transcript", json={"revision": draft["revision"], "segments": changed, "speaker_names": names}).status_code == 409
    with Brain() as db:
        artifacts = db.query(SourceArtifact).filter_by(source_id=row["source_id"], kind="transcription").all()
        assert len(artifacts) == 2
        assert sum(bool(a.content_json.get("superseded")) for a in artifacts) == 1
    import asyncio
    from app.services.memory_port import FakeMemoryAdapter
    hits = asyncio.run(FakeMemoryAdapter(Brain).recall(context[1], "diamètre", ["evidence"]))
    assert hits and all("50 mm" not in h["excerpt"] for h in hits)
    # Revalidating unchanged text does not duplicate the artifact.
    assert client.put(path + "/transcript", json={"revision": row["revision"], "segments": changed, "speaker_names": names, "validate": True}).status_code == 200
    with Brain() as db:
        assert db.query(SourceArtifact).filter_by(source_id=row["source_id"], kind="transcription").count() == 2


def test_invalid_timestamps_empty_text_and_wrong_project_are_rejected(context, monkeypatch):
    row = transcribed(context, monkeypatch)
    path = context[3]
    changed = [dict(s) for s in SEGMENTS]
    changed[1]["end"] = 99
    assert client.put(path + "/transcript", json={"revision": row["revision"], "segments": changed}).status_code == 409
    changed[1]["text"] = ""
    assert client.put(path + "/transcript", json={"revision": row["revision"], "segments": changed}).status_code == 422
    other = client.post("/api/v1/projects", json={"title": "Autre projet"}).json()["id"]
    assert client.get(f"/api/v1/projects/{other}/recordings/{context[2]}").status_code == 409
    assert client.get(f"/api/v1/projects/{other}/recordings").json() == []


def test_failed_llm_preserves_reviewed_transcript_for_retry(context, monkeypatch):
    row = reviewed(context, monkeypatch)
    with Brain() as db:
        save_section(db, "ai", {"enabled": True, "provider": "ollama", "model": "test"})
    monkeypatch.setattr(service, "chat_json", lambda *_args, **_kwargs: None)
    assert client.post(context[3] + "/synthesize").status_code == 202
    service.run_job(context[2])
    failed = client.get(context[3]).json()
    assert failed["job_status"] == "failed" and failed["segments"] == row["segments"]
    assert failed["reviewed_revision"] == row["reviewed_revision"]
    assert client.post(context[3] + "/synthesize").status_code == 202
    client.post(context[3] + "/cancel")
    assert client.get(context[3]).json()["job_status"] == "cancelled"


def test_cancel_running_transcription_preserves_original(context, monkeypatch):
    def cancel_transcription(row, _):
        assert client.post(context[3] + "/cancel").status_code == 200
        raise service.Cancelled()
    monkeypatch.setattr(service, "_transcribe", cancel_transcription)
    assert client.post(context[3] + "/transcribe").status_code == 202
    service.run_job(context[2])
    assert client.get(context[3]).json()["job_status"] == "cancelled"
    assert client.get(context[3] + "/audio").content.startswith(b"fictitious-audio-")
    assert client.post(context[3] + "/transcribe").status_code == 202
    client.post(context[3] + "/cancel")


def test_long_meeting_processes_every_chunk_and_rejects_false_evidence(monkeypatch):
    segments = [dict(SEGMENTS[0], id=f"seg-{i}", text=("Sujet technique. " * 400) + f"Décision finale {i}.") for i in range(4)]
    sent = []
    def reply(cfg, payload, **kwargs):
        assert payload["reasoning_effort"] == "none"
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        text = payload["messages"][1]["content"]
        sent.append(text)
        segment = next(s for s in segments if s["id"] in text)
        return json.dumps({"overview": segment["id"], "decisions": [
            {"text": segment["id"], "segment_id": segment["id"], "quote": "Sujet technique."},
            {"text": "Inventé", "segment_id": segment["id"], "quote": "Cet extrait n’existe pas"}], "actions": [], "open_points": []})
    monkeypatch.setattr(service, "chat_json", reply)
    monkeypatch.setattr(service, "chat_text", lambda cfg, messages, **kwargs: "Synthèse de toutes les parties : " + messages[1]["content"])
    result = service.synthesize(segments, {}, {"enabled": True}, lambda *_: None)
    assert len(sent) == 4 and "Décision finale 3" in sent[-1]
    assert len(result["decisions"]) == 4 and result["rejected_items"] == 4
    assert "seg-3" in result["overview"]


def test_publish_rejects_hallucinated_quote(context, monkeypatch):
    draft, _ = drafted(context, monkeypatch)
    changed = json.loads(json.dumps(SUMMARY))
    changed["decisions"][0]["quote"] = "diamètre de 80 mm"
    assert client.post(context[3] + "/publish", json={"revision": draft["revision"], "summary": changed}).status_code == 409
    with ERP() as db:
        assert db.get(Meeting, context[2]) is None


def test_recover_between_erp_and_brain_publication(context, monkeypatch):
    draft, _ = drafted(context, monkeypatch)
    # Fail after the ERP commit and the first canonical insert, before Brain commit.
    import app.services.projections as projections
    real_enqueue = projections.enqueue
    monkeypatch.setattr(projections, "enqueue", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("simulated crash")))
    with Brain() as db:
        row = db.get(MeetingRecording, context[2])
        with pytest.raises(RuntimeError):
            service.publish(db, row, service.MeetingSummary.model_validate(SUMMARY), draft["revision"])
        db.rollback()
    with ERP() as db:
        assert db.get(Meeting, context[2]) is not None
    monkeypatch.setattr(projections, "enqueue", real_enqueue)
    response = client.post(context[3] + "/publish", json={"revision": draft["revision"], "summary": {**SUMMARY, "overview": "Texte différent ignoré pendant la reprise"}})
    assert response.status_code == 200
    assert response.json()["summary"]["overview"] == SUMMARY["overview"]
    with ERP() as db:
        assert db.query(MeetingAction).filter_by(meeting_id=context[2]).count() == 1


def test_upload_validation_and_deduplication(context):
    pid, _, _, path = context
    row = client.get(path).json()
    original = client.get(path + "/audio").content
    assert client.get(path + "/audio").headers["content-type"] == "audio/wav"
    assert client.get(path + "/audio").headers["x-content-type-options"] == "nosniff"
    result = client.post(f"/api/v1/projects/{pid}/recordings", data={"title": "Doublon"}, files={"file": ("reunion.wav", original, "audio/wav")})
    assert result.status_code == 201 and result.json()["id"] == row["id"]
    assert client.post(f"/api/v1/projects/{pid}/recordings", data={"title": "Mauvais format"}, files={"file": ("fichier.exe", b"bad")}).status_code == 400
    assert client.post(f"/api/v1/projects/{pid}/recordings", data={"title": "Audio vide"}, files={"file": ("vide.wav", b"")}).status_code == 400


def test_project_archive_preserves_audio_workflow_and_report(context, monkeypatch):
    draft, _ = drafted(context, monkeypatch)
    assert client.post(context[3] + "/publish", json={"revision": draft["revision"], "summary": SUMMARY}).status_code == 200
    archive = client.get(f"/api/v1/projects/{context[0]}/export").json()
    assert len(archive["brain"]["meeting_recordings"]) == 1
    code = "RESTORED-AUDIO-" + uuid.uuid4().hex[:8]
    imported = client.post("/api/v1/projects/import-json", json={"data": archive, "code": code})
    assert imported.status_code == 201, imported.text
    new_pid = imported.json()["id"]
    recordings = client.get(f"/api/v1/projects/{new_pid}/recordings").json()
    assert len(recordings) == 1
    row = client.get(f"/api/v1/projects/{new_pid}/recordings/{recordings[0]['id']}").json()
    assert row["speaker_names"] == draft["speaker_names"] and row["segments"] == draft["segments"]
    assert row["published_meeting_id"] != context[2]
    assert client.get(f"/api/v1/projects/{new_pid}/recordings/{row['id']}/audio").status_code == 200
    with ERP() as db:
        assert db.get(Meeting, row["published_meeting_id"]).project_id == new_pid
    # Exporting the clone must not export the original ERP project's recording.
    second = client.get(f"/api/v1/projects/{new_pid}/export").json()
    assert len(second["brain"]["meeting_recordings"]) == 1
    assert second["brain"]["meeting_recordings"][0]["erp_project_id"] == new_pid


def test_audio_words_keep_speaker_changes_and_unknown_voice():
    from types import SimpleNamespace as Word
    from scripts.transcribe_meeting import assign_words
    words = [Word(start=0, end=0.4, word="Bonjour"), Word(start=0.5, end=0.8, word=" Marie"),
             Word(start=1.0, end=1.8, word=" Réponse"), Word(start=3, end=3.5, word=" Incertain")]
    turns = [Word(start=0, end=0.9, speaker=0), Word(start=0.9, end=2.0, speaker=1)]
    result = assign_words(words, turns)
    assert [r["speaker"] for r in result] == ["SPEAKER_01", "SPEAKER_02", "UNKNOWN"]
    assert result[0]["text"] == "Bonjour Marie" and result[0]["end"] == 0.8
