import uuid

import pytest

from app.db import SessionLocal
from app.models import AuditLog, Project, Proposal, Source, ValidationDecision
from app.services.triage import auto_classify_pending, auto_classify_proposal, triage_pending
from app.workspace_models import MailEnrichmentJob


@pytest.fixture(autouse=True)
def exact100_policy():
    """The former exact-100 policy remains selectable in mail settings."""
    from app.services.settings_service import save_section
    with SessionLocal() as db:
        save_section(db, "mail", {"auto_classification_threshold": 1.0})


def rows(db, confidence=1.0, status="resolution_pending", code=None):
    project = Project(code=code or f"AUTO-{uuid.uuid4().hex}", name="Automatic mail")
    db.add(project)
    db.flush()
    source = Source(source_type="email", status=status, original_uri="test.eml",
                    sha256=uuid.uuid4().hex, mime_type="message/rfc822", source_metadata={"subject": project.code})
    db.add(source)
    db.flush()
    proposal = Proposal(source_id=source.id, project_id=project.id, kind="project_attach",
                        subject="Test", value="{}", confidence=confidence, reason="triage IA : explicit_code")
    db.add(proposal)
    db.commit()
    return project, source, proposal


def test_exact100_commits_assignment_accept_audit_and_enrichment_together():
    with SessionLocal() as db:
        project, source, proposal = rows(db)
        assert auto_classify_proposal(db, proposal, {"enabled": True})
        assert source.status == "resolved" and source.project_id == project.id
        assert proposal.status == "accepted"
        decision = db.query(ValidationDecision).filter_by(proposal_id=proposal.id).one()
        assert decision.decision == "accept" and decision.actor == "auto-confidence-100"
        assert db.query(MailEnrichmentJob).filter_by(source_id=source.id).one().status == "queued"
        audits = db.query(AuditLog).filter_by(event_type="triage.auto_classified.v1").all()
        assert sum(row.payload["source_id"] == source.id for row in audits) == 1
        assert not auto_classify_proposal(db, proposal)


@pytest.mark.parametrize("confidence,status", [(0.999, "resolution_pending"), (0.9, "resolution_pending"),
    (1.01, "resolution_pending"), (1.0, "resolved"), (1.0, "discarded")])
def test_near100_and_existing_human_decisions_are_untouched(confidence, status):
    with SessionLocal() as db:
        _, source, proposal = rows(db, confidence, status)
        assert not auto_classify_proposal(db, proposal)
        db.commit()
        assert source.status == status and source.project_id is None and proposal.status == "pending"


def test_conflicting_proposals_do_not_trigger_an_arbitrary_assignment():
    with SessionLocal() as db:
        _, source, proposal = rows(db)
        other = Project(code=f"OTHER-{uuid.uuid4().hex}", name="Other")
        db.add(other)
        db.flush()
        db.add(Proposal(source_id=source.id, project_id=other.id, kind="project_attach", confidence=1.0,
                        subject="Conflict", value="{}"))
        db.commit()
        assert not auto_classify_proposal(db, proposal)
        db.rollback()
        assert source.status == "resolution_pending"


def test_triage_auto100_leaves_both_ui_queues_and_reanalysis_is_neutral():
    from fastapi.testclient import TestClient
    from app.main import app
    with SessionLocal() as db:
        project, source, _ = rows(db, 0.9)
        project.aliases = [project.code]
        db.commit()
        result = triage_pending(db, None, {"enabled": False}, force=True, source_ids=[source.id])
        assert result["auto_classified"] == 1 and result["errors"] == []
        again = triage_pending(db, None, None, force=True, source_ids=[source.id])
        assert again["scanned"] == 0
        client = TestClient(app)
        assert not any(row["source_id"] == source.id for row in client.get('/v1/triage/queue').json())
        response = client.get('/v1/mail/page?scope=pending&limit=200')
        assert response.status_code == 200
        assert not any(row["source_id"] == source.id for row in response.json()['rows'])
        classified = client.get(f'/v1/mail/page?scope=resolved&project_id={project.id}').json()
        assert any(row['source_id'] == source.id for row in classified['rows'])
        assert db.get(Source, source.id).project_id == project.id


def test_existing_pending_backfill_and_repeat_preserve_manual_status():
    with SessionLocal() as db:
        project, source, proposal = rows(db)
        _, human, _ = rows(db, status="resolved")
        result = auto_classify_pending(db, {"enabled": True})
        assert result["auto_classified"] >= 1
        assert db.get(Source, source.id).project_id == project.id and proposal.status == "accepted"
        assert db.get(Source, human.id).status == "resolved"
        assert auto_classify_pending(db, {"enabled": True})["auto_classified"] == 0


def test_import_exact100_uses_the_same_audited_classification():
    import asyncio
    from app.services.mail_ingest import ingest_eml_bytes
    with SessionLocal() as db:
        code = f"IMPORT-{uuid.uuid4().hex}"
        project = Project(code=code, name="Import", aliases=[code])
        db.add(project)
        db.commit()
        raw = f"From: sender@example.com\r\nSubject: {code}\r\nMessage-ID: <{code}@test>\r\n\r\nBonjour".encode()
        result = asyncio.run(ingest_eml_bytes(db, raw, None))
        assert result['status'] == 'resolved' and result['project_id'] == project.id
        assert db.query(Proposal).filter_by(source_id=result['source_id'],kind='project_attach').one().status == 'accepted'
