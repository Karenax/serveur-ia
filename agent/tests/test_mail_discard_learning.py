import uuid

from app.db import SessionLocal
from app.models import AuditLog, Source, SourceArtifact, Project, Proposal
from app.services.mail_discard_learning import EVENT, build_discard_context, fingerprint, remember_discard, similarity


def mail(db, subject="Promotion capteurs laser", sender="news@example.com", status="resolution_pending"):
    source = Source(source_type="email", status=status, author=sender, original_uri="", sha256=uuid.uuid4().hex,
                    source_metadata={"subject": subject})
    db.add(source)
    db.flush()
    db.add(SourceArtifact(source_id=source.id, kind="body_text", content_text="Promotion capteurs laser mesure optique industrielle"))
    db.flush()
    db.refresh(source)
    return source


def test_estimate_learns_only_actual_discards_and_retained_mail_lowers_score():
    with SessionLocal() as db:
        old = mail(db)
        remember_discard(db, old)
        current = mail(db)
        assert build_discard_context(db).estimate(current)["probability"] is None
        old.status = "discarded"
        db.flush()
        first = build_discard_context(db).estimate(current)
        assert 0 < first["probability"] < 1 and first["discarded_samples"] == 1
        mail(db, status="resolved")
        db.flush()
        second = build_discard_context(db).estimate(current)
        assert second["probability"] < first["probability"]
        assert second["retained_samples"] == 1
        assert current.status == "resolution_pending"
        remember_discard(db, old)
        assert db.query(AuditLog).filter_by(event_type=EVENT, correlation_id=old.id).count() == 1
        payload = db.query(AuditLog).filter_by(event_type=EVENT, correlation_id=old.id).one().payload
        assert "news@example.com" not in str(payload) and "Promotion" not in str(payload)
        db.rollback()


def test_same_sender_and_footer_do_not_qualify():
    old = fingerprint("shared@example.com", "Promotion robot capteurs", "Bonjour\nCatalogue robot nouveautes exclusives\n--\nSignature partagée")
    new = fingerprint("shared@example.com", "AIRB26LTH0205-A jalon livraison", "Bonjour\nValidation jalon contractuel livraison\n--\nSignature partagée")
    assert similarity(old, new)[0] == 0
    assert similarity(fingerprint("a@b.com", "", ""), fingerprint("a@b.com", "", ""))[0] == 0
    footer = "\nBien cordialement\nFrédéric Lefrançois Chargé affaires Account Manager entreprise ingénierie Nantes Montoir France"
    assert similarity(fingerprint("shared@example.com", "Promotion robot capteurs", "Catalogue robot nouveautes exclusives" + footer),
                      fingerprint("shared@example.com", "Jalon livraison", "Validation jalon contractuel livraison" + footer))[0] == 0


def test_pending_routes_expose_identical_discard_estimate():
    from app.routers.mail_search import mail_page
    from app.routers.triage import triage_queue
    with SessionLocal() as db:
        old = mail(db)
        remember_discard(db, old)
        old.status = "discarded"
        current = mail(db)
        project = Project(code=uuid.uuid4().hex, name="Test")
        db.add(project)
        db.flush()
        db.add(Proposal(source_id=current.id, project_id=project.id, kind="project_attach", confidence=.4, status="pending", subject="Projet", value="{}"))
        db.flush()
        page = mail_page(scope="pending", q="", sort="newest", project_id=None, offset=0, limit=200, db=db)
        paged = next(row for row in page["rows"] if row["source_id"] == current.id)
        queued = next(row for row in triage_queue(db=db) if row["source_id"] == current.id)
        assert paged["discard_suggestion"] == queued["discard_suggestion"]
        assert paged["discard_suggestion"]["probability"] > 0
        db.rollback()


def test_history_recovery_reads_backup_without_restoring_content(tmp_path):
    import json
    import sqlite3
    from scripts.learn_discarded_mail import recover_fingerprints
    folder = tmp_path / "before-mail-discard-20261007"
    folder.mkdir()
    path = folder / "project_brain.db"
    with sqlite3.connect(path) as saved:
        saved.execute("CREATE TABLE sources (id TEXT, author TEXT, source_metadata TEXT, status TEXT, sha256 TEXT)")
        saved.execute("CREATE TABLE source_artifacts (source_id TEXT, kind TEXT, content_text TEXT)")
        saved.execute("INSERT INTO sources VALUES (?,?,?,?,?)", ("one", "news@example.com", json.dumps({"subject": "Promotion"}), "resolved", "hash"))
        saved.execute("INSERT INTO source_artifacts VALUES (?,?,?)", ("one", "body_text", "Offre publicitaire"))
    before = path.read_bytes()
    assert recover_fingerprints(tmp_path, {"one": "wrong"}) == {}
    recovered = recover_fingerprints(tmp_path, {"one": "hash"})
    assert recovered["one"] == fingerprint("news@example.com", "Promotion", "Offre publicitaire")
    assert path.read_bytes() == before
