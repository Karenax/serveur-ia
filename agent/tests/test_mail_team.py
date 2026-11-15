"""Project team additions and conservative classification signals."""
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db_support import configure_sqlite
from app.services.mail_learning import LearningContext
from app.services.mail_team import correspondents, synchronize
from app.services.resolution import choose_candidate, resolve_project
from backend.app.db import Base
from backend.app.models import BrainLink, Project
from backend.app.project_identity_models import ProjectIdentityChange, ProjectMember, ProjectPerson


@pytest.fixture
def erp():
    engine = create_engine("sqlite://")
    configure_sqlite(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(code="TEAM-A", title="Project")
        db.add(project)
        db.flush()
        db.add(BrainLink(project_id=project.id, brain_project_id="brain-a", brain_code=project.code))
        db.commit()
        yield db, project
    engine.dispose()


def source(**kw):
    return SimpleNamespace(**{**dict(id="mail-a", source_type="email", status="resolved", project_id="brain-a",
        author="Alice Martin <Alice.Martin@excent.fr>", participants=["bob.durand@excent.fr",
        "client@airbus.com", "info@excent.fr", "intrus@excent.fr.evil.test"], original_uri="missing.eml"), **kw})


def test_team_addition_is_idempotent_audited_and_preserves_archives(erp):
    db, project = erp
    assert synchronize(source(), db) == 2
    db.commit()
    assert synchronize(source(), db) == 0
    assert db.query(ProjectPerson).count() == 2
    assert {m.role for m in db.query(ProjectMember)} == {"collaborateur_projet"}
    assert all(c.value["mail_source_id"] == "mail-a" for c in db.query(ProjectIdentityChange))
    member = db.query(ProjectMember).first()
    member.active = False
    db.commit()
    assert synchronize(source(), db) == 0
    assert not member.active
    assert synchronize(source(status="resolution_pending"), db) == 0
    assert synchronize(source(project_id="unknown"), db) == 0


def test_existing_role_and_person_details_are_preserved(erp):
    db, project = erp
    person = ProjectPerson(first_name="Alicia", last_name="Martin", email="alice.martin@excent.fr",
                           normalized_email="alice.martin@excent.fr")
    db.add(person)
    db.flush()
    db.add(ProjectMember(project_id=project.id, person_id=person.id, role="be_3d"))
    db.commit()
    assert synchronize(source(participants=[]), db) == 0
    assert person.first_name == "Alicia"
    assert db.query(ProjectMember).one().role == "be_3d"


def test_committed_sync_is_visible_to_the_classification_context(erp, monkeypatch):
    from sqlalchemy.orm import sessionmaker
    from app.services import mail_team
    db, project = erp
    monkeypatch.setattr(mail_team, "ERP", sessionmaker(bind=db.get_bind(), autoflush=False))
    mail_team.sync_classified_mail(source())
    assert set(mail_team.team_emails({"brain-a"})) == {
        ("brain-a", "alice.martin@excent.fr"), ("brain-a", "bob.durand@excent.fr")}
    assert mail_team.team_emails({"other"}) == []
    person = db.query(ProjectPerson).filter_by(normalized_email="bob.durand@excent.fr").one()
    person.active = False
    db.commit()
    mail_team.sync_classified_mail(source())
    assert mail_team.team_emails({"brain-a"}) == [("brain-a", "alice.martin@excent.fr")]


def test_headers_supply_recipient_names_without_quoted_body(tmp_path):
    path = tmp_path / "mail.eml"
    path.write_bytes(b"From: Alice Martin <alice.martin@excent.fr>\r\nTo: Bob DUPONT <bob.d@excent.fr>\r\n\r\nOld: fake.person@excent.fr")
    found = correspondents(source(original_uri=str(path), participants=[]))
    assert found["bob.d@excent.fr"] == ("Bob", "DUPONT")
    assert "fake.person@excent.fr" not in found


def test_team_signal_is_explained_shared_and_explicit_reference_wins():
    a = SimpleNamespace(id="a", code="TEAM-A", name="Alpha", aliases=[], customer_id="")
    b = SimpleNamespace(id="b", code="TEAM-B", name="Beta", aliases=[], customer_id="")
    context = LearningContext()
    context.teams["a"].add("alice.martin@excent.fr")
    context.teams["b"].add("alice.martin@excent.fr")
    parsed = dict(sender="alice.martin@excent.fr", subject="Discussion", participants=[])
    result = resolve_project(parsed, [a,b], learning_context=context)
    assert all(c["evidence"][0]["shared"] for c in result["candidates"])
    assert choose_candidate(result["candidates"]) is None
    parsed["subject"] = "TEAM-B"
    assert choose_candidate(resolve_project(parsed, [a,b], learning_context=context)["candidates"])["project_id"] == "b"
    context.senders["alice.martin@excent.fr"]["a"] = 3
    result = resolve_project(dict(sender=parsed["sender"], subject="Discussion"), [a], learning_context=context)
    assert result["candidates"][0]["score"] == .8
    assert next(e for e in result["candidates"][0]["evidence"] if e["key"] == "project_team")["weight"] == 0
