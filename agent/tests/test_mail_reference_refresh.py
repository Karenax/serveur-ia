"""Reprise ciblée des propositions : historique et décisions préservés."""
import uuid

from app.db import SessionLocal
from app.models import Project, Proposal, Source, SourceArtifact
from app.services.mail_reference_refresh import refresh_reference_suggestions


def test_refresh_only_unique_pending_references_and_is_idempotent():
    with SessionLocal() as db:
        code = "REF-" + uuid.uuid4().hex[:10]
        a, b = Project(code=code, name="Référence"), Project(code=code + "-B", name="Autre")
        db.add_all([a, b])
        db.flush()
        pending = Source(source_type="email", status="resolution_pending",
                         original_uri="test.eml", sha256=uuid.uuid4().hex,
                         source_metadata={"subject": "Livrables"})
        resolved = Source(source_type="email", status="resolved", project_id=b.id,
                          original_uri="test.eml", sha256=uuid.uuid4().hex,
                          source_metadata={"subject": code})
        conflict = Source(source_type="email", status="resolution_pending",
                          original_uri="test.eml", sha256=uuid.uuid4().hex,
                          source_metadata={"subject": f"{code} et {b.code}"})
        db.add_all([pending, resolved, conflict])
        db.flush()
        db.add(SourceArtifact(source_id=pending.id, kind="body_text", content_text=f"PO-26-123-{code}"))
        old = Proposal(source_id=pending.id, kind="project_attach", confidence=0.3,
                       reason="résolution ambiguë", subject="Ancienne", value="[]")
        human = Proposal(source_id=resolved.id, project_id=b.id, kind="project_attach",
                         status="accepted", subject="Validée", value="[]")
        ambiguous = Proposal(source_id=conflict.id, kind="project_attach", subject="Conflit", value="[]")
        db.add_all([old, human, ambiguous])
        db.commit()
        audit = refresh_reference_suggestions(db)
        assert audit["by_code"][code] == 1
        assert audit["updated"] == 0
        assert old.status == "pending" and old.project_id is None
        excluded = refresh_reference_suggestions(db, apply=True, exclude_source_ids={pending.id})
        assert code not in excluded["by_code"]
        assert old.status == "pending"
        applied = refresh_reference_suggestions(db, apply=True)
        assert applied["by_code"][code] == 1
        assert old.status == "superseded"
        new = db.query(Proposal).filter_by(source_id=pending.id, kind="project_attach", status="accepted").one()
        assert new.project_id == a.id and new.confidence >= 0.9
        assert pending.project_id == a.id and pending.status == "resolved"
        assert human.status == "accepted" and resolved.project_id == b.id
        assert ambiguous.status == "pending" and ambiguous.project_id is None
        assert code not in refresh_reference_suggestions(db, apply=True)["by_code"]
