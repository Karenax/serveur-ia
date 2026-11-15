"""Purge sauvegardée, non-réimportation et absence de connaissances résiduelles."""
import asyncio
import sqlite3
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import RAW_DIR
from app.db import SessionLocal
from app.main import app
from app.models import (KnowledgeItem, MemoryProjection, Project, Proposal,
                        ProvenanceLink, Source, SourceArtifact, ValidationDecision)
from app.services.mail_discard import discard_mail
from app.services.memory_port import FakeMemoryAdapter
from app.services.triage import is_analyzed, triage_pending


def upload():
    raw = (f"From: spam@example.com\r\nSubject: publicité {uuid.uuid4()}\r\n"
           "Content-Type: text/plain; charset=utf-8\r\n\r\nOffre sans intérêt.").encode()
    c = TestClient(app)
    result = c.post("/v1/sources/upload-eml", files={"file": ("spam.eml", raw)}).json()
    return c, raw, result["source_id"]


def test_discard_backs_up_purges_and_prevents_reimport():
    c, raw, source_id = upload()
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        sha = source.sha256
    result = c.post(f"/api/v1/brain/sources/{source_id}/discard")
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "discarded"
    backup = Path(result.json()["backup"])
    with sqlite3.connect(str(backup / "project_brain.db")) as saved:
        assert saved.execute("SELECT author FROM sources WHERE id=?", (source_id,)).fetchone()[0] == "spam@example.com"
        assert saved.execute("SELECT COUNT(*) FROM source_artifacts WHERE source_id=?", (source_id,)).fetchone()[0]
    assert (backup / "raw" / f"{sha}.eml").read_bytes() == raw
    assert not (RAW_DIR / f"{sha}.eml").exists()
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        assert source.status == "discarded" and source.sha256 == sha
        assert not source.author and not source.project_id and not source.original_uri
        assert source.source_metadata == {} and source.participants == []
        assert not db.query(SourceArtifact).filter_by(source_id=source_id).count()
        assert not db.query(Proposal).filter_by(source_id=source_id).count()
        assert is_analyzed(db, source_id)
    assert c.get(f"/v1/sources/{source_id}").status_code == 410
    assert c.get(f"/v1/sources/{source_id}/raw").status_code == 410
    again = c.post("/v1/sources/upload-eml", files={"file": ("spam.eml", raw)}).json()
    assert again["status"] == "duplicate" and again["source_id"] == source_id
    assert c.post(f"/v1/sources/{source_id}/discard").json()["backup"] is None
    assert source_id not in {row["source_id"] for row in c.get("/v1/sources?limit=1000").json()}
    c.post("/v1/triage/run?force=true&limit=1000")
    assert source_id not in {row["source_id"] for row in c.get("/v1/triage/queue?limit=1000").json()}


def test_discard_removes_exclusive_knowledge_and_retries_memory_cleanup():
    c, _, source_id = upload()
    _, _, other_id = upload()
    with SessionLocal() as db:
        project = Project(code=f"discard-{uuid.uuid4().hex[:8]}", name="Test")
        db.add(project)
        db.flush()
        pid = project.id
        source = db.get(Source, source_id)
        source.status = "resolved"
        source.project_id = pid
        exclusive = KnowledgeItem(project_id=pid, kind="fact", subject="Spam", value="Pollution exclusive")
        shared = KnowledgeItem(project_id=pid, kind="fact", subject="Partagée", value="Preuve indépendante")
        db.add_all([exclusive, shared])
        db.flush()
        exclusive_id, shared_id = exclusive.id, shared.id
        db.add_all([ProvenanceLink(knowledge_item_id=exclusive_id, source_id=source_id),
                    ProvenanceLink(knowledge_item_id=shared_id, source_id=source_id),
                    ProvenanceLink(knowledge_item_id=shared_id, source_id=other_id)])
        prop = Proposal(source_id=source_id, project_id=pid, kind="fact", subject="Spam", value="Pollution", status="accepted")
        db.add(prop)
        db.flush()
        prop_id = prop.id
        db.add(ValidationDecision(proposal_id=prop.id, decision="accept", actor="test", resulting_knowledge_id=exclusive_id))
        db.add_all([MemoryProjection(project_id=pid, source_id=source_id, purpose="evidence", content_hash="h", external_ref="evidence-ref"),
                    MemoryProjection(project_id=pid, knowledge_item_id=exclusive_id, purpose="truth", content_hash="h", external_ref="truth-ref")])
        db.commit()

    class Unavailable(FakeMemoryAdapter):
        async def forget_projection(self, project_id, projection_id):
            return False

    with SessionLocal() as db:
        result = discard_mail(db, Unavailable(SessionLocal), source_id)
        assert result["memory_cleanup_pending"]
        assert db.get(KnowledgeItem, exclusive_id) is None
        assert db.get(KnowledgeItem, shared_id) is not None
        assert not db.query(ValidationDecision).filter_by(proposal_id=prop_id).count()
        assert not db.query(ProvenanceLink).filter_by(source_id=source_id).count()
        assert len(db.query(MemoryProjection).filter_by(source_id=source_id, status="obsolete").all()) == 2
        hits = asyncio.run(FakeMemoryAdapter(SessionLocal).recall(pid, "", ["truth", "evidence"]))
        assert not any("Pollution" in str(hit) for hit in hits)
        result = discard_mail(db, FakeMemoryAdapter(SessionLocal), source_id)
        assert not result["memory_cleanup_pending"]
    assert c.post(f"/v1/resolution/{source_id}/confirm", json={"project_id": pid}).status_code == 409


def test_failed_backup_preserves_mail(monkeypatch):
    _, _, source_id = upload()
    def fail(*args):
        raise OSError("Disque indisponible")
    monkeypatch.setattr("app.services.mail_discard.backup_sqlite", fail)
    with SessionLocal() as db:
        with pytest.raises(OSError):
            discard_mail(db, FakeMemoryAdapter(SessionLocal), source_id)
        db.rollback()
        assert db.get(Source, source_id).status == "resolution_pending"
        assert db.query(SourceArtifact).filter_by(source_id=source_id).count()


def test_running_analysis_cannot_resurrect_discarded_mail(monkeypatch):
    _, _, source_id = upload()
    def classify(cfg, subject, body, sender, projects, timeout=None, participants=None):
        if "publicité" in subject:
            with SessionLocal() as other:
                target = other.get(Source, source_id)
                if target.status != "discarded":
                    discard_mail(other, FakeMemoryAdapter(SessionLocal), source_id)
        return {"project_hints": [], "summary": "Une offre", "items": []}
    monkeypatch.setattr("app.services.ai_client.classify_email", classify)
    with SessionLocal() as db:
        triage_pending(db, FakeMemoryAdapter(SessionLocal), {"enabled": True}, limit=1000, force=True)
    with SessionLocal() as db:
        assert db.get(Source, source_id).status == "discarded"
        assert not db.query(Proposal).filter_by(source_id=source_id).count()


def test_discard_rejects_non_mail():
    with SessionLocal() as db:
        source = Source(source_type="meeting", original_uri="", sha256=uuid.uuid4().hex)
        db.add(source)
        db.commit()
        with pytest.raises(HTTPException) as error:
            discard_mail(db, FakeMemoryAdapter(SessionLocal), source.id)
        assert error.value.status_code == 400
