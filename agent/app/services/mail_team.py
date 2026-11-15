"""Add eXcent correspondents from committed mail classifications to project teams."""
import logging
import re
from email import policy
from email.parser import BytesHeaderParser
from email.utils import getaddresses
from pathlib import Path

from sqlalchemy.dialects.sqlite import insert

from backend.app.db import SessionLocal as ERP
from backend.app.models import BrainLink, Project
from backend.app.project_identity_models import ProjectIdentityChange, ProjectMember, ProjectPerson, ProjectProfile
from backend.app.project_identity_schemas import MemberCreate, PersonCreate
from backend.app.services.project_identity import add_member, create_person
from backend.app.services.project_operator import Operator, operator_context

logger = logging.getLogger(__name__)
SERVICE_ADDRESSES = {"contact", "support", "info", "noreply", "no-reply", "commercial", "achats", "comptabilite"}


def correspondents(source):
    values = [source.author or "", *(source.participants or [])]
    try:
        with Path(source.original_uri).open("rb") as stream:
            headers = BytesHeaderParser(policy=policy.default).parsebytes(stream.read(256 * 1024), headersonly=True)
        values = [str(value) for key in ("From", "To", "Cc") for value in headers.get_all(key, [])] + values
    except (OSError, ValueError):
        pass
    people = {}
    for name, address in getaddresses(values):
        address = address.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@excent\.fr", address) or len(address) > 255:
            continue
        local = address.split("@", 1)[0]
        if local in SERVICE_ADDRESSES:
            continue
        words = name.strip().split() or [word.capitalize() for word in re.split(r"[._-]+", local) if word]
        if len(words) < 2:
            continue  # A mailbox without an identifiable person is not a team member.
        people.setdefault(address, (words[0][:120], " ".join(words[1:])[:120]))
    return people


def synchronize(source, erp_db):
    """Caller owns ERP transaction. No reactivation, role replacement or access grant."""
    if source.source_type != "email" or source.status != "resolved" or not source.project_id:
        return 0
    projects = erp_db.query(Project).join(BrainLink, BrainLink.project_id == Project.id).filter(
        BrainLink.brain_project_id == source.project_id, Project.status == "active").all()
    if len(projects) != 1 or projects[0].code.upper() == "DIVERS":
        return 0
    project = projects[0]
    people = correspondents(source)
    if not people:
        return 0
    # Serialize identity creation and membership checks in this ERP transaction.
    erp_db.execute(insert(ProjectProfile).values(project_id=project.id).on_conflict_do_nothing(
        index_elements=["project_id"]))
    count = 0
    with operator_context(Operator("mail-team", "owner")):
        for address, (first, last) in people.items():
            person = erp_db.query(ProjectPerson).filter_by(normalized_email=address).first()
            if person and not person.active:
                continue
            if not person:
                result = create_person(erp_db, PersonCreate(first_name=first, last_name=last, email=address))
                person = erp_db.get(ProjectPerson, result["id"])
            # Include archived assignments: a human removal must not be undone.
            if erp_db.query(ProjectMember).filter_by(project_id=project.id, person_id=person.id).first():
                continue
            profile = erp_db.get(ProjectProfile, project.id)
            result = add_member(erp_db, project.id, MemberCreate(person_id=person.id,
                role="collaborateur_projet", expected_revision=profile.revision if profile else 0))
            change = erp_db.query(ProjectIdentityChange).filter_by(project_id=project.id,
                revision=result["revision"], action="member_added").one()
            change.value = {**change.value, "mail_source_id": source.id, "mail_project_id": source.project_id,
                            "email": address, "origin": "classified_mail"}
            count += 1
    return count


def sync_classified_mail(source):
    """ERP failure does not roll back a committed classification; backfill can retry."""
    if source.source_type != "email" or source.status != "resolved":
        return
    try:
        with ERP() as db:
            synchronize(source, db)
            db.commit()
    except Exception:
        logger.exception("Ajout à l’équipe depuis le mail %s : reprise nécessaire", source.id)


def team_emails(project_ids):
    with ERP() as db:
        rows = db.query(BrainLink.brain_project_id, ProjectPerson.email).join(
            Project, BrainLink.project_id == Project.id).join(
            ProjectMember, ProjectMember.project_id == Project.id).join(
            ProjectPerson, ProjectMember.person_id == ProjectPerson.id).filter(
            BrainLink.brain_project_id.in_(project_ids), Project.status == "active",
            ProjectMember.active.is_(True), ProjectPerson.active.is_(True)).all()
        return rows
