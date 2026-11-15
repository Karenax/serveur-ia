"""Identity/reference/team rules, also enforced when called without HTTP.

Callers own the transaction and must roll back a failed command. No service here
deletes a row, rewrites a historical project cell or alters a Brain link.
"""
import re
import unicodedata

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError

from ..models import Project
from ..project_identity_models import (
    ProjectIdentityChange, ProjectMember, ProjectPerson, ProjectProfile, ProjectReference,
    ProjectReferenceChange, now,
)
from .project_operator import current_operator, require_project_access, require_reference_write

REFERENCE_FIELDS = {
    "client_id": "client", "agency_id": "agency", "business_unit_id": "business_unit",
    "family_id": "family", "typology_id": "typology",
}
ROLE_LABELS = {
    "responsable_projet": "Responsable projet", "pilote_etude": "Pilote étude",
    "be_3d": "Concepteur 3D", "be_2d": "Concepteur 2D", "verificateur_be": "Vérificateur BE",
    "qualite": "Qualité", "calcul": "Calcul", "charge_fabrication": "Chargé de fabrication",
    "collaborateur_projet": "Collaborateur projet", "lecteur_projet": "Lecteur projet",
}
PROFILE_FIELDS = tuple(REFERENCE_FIELDS) + (
    "responsible_id", "description", "client_reference", "client_site", "client_contact",
    "equipment_number", "quantity", "start_date", "planned_end_date", "actual_closure_date", "standby",
)
PERSON_FIELDS = (
    "first_name", "last_name", "email", "trigram", "function", "service", "phone", "agency_id", "active",
)
MEMBER_FIELDS = ("id", "project_id", "person_id", "role", "start_date", "end_date", "active")


def _normalized(value):
    return "".join(char for char in unicodedata.normalize("NFD", value.casefold())
                   if unicodedata.category(char) != "Mn")


def _page(query, search_column, search, offset, limit):
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 200 or len(search) > 200:
        raise HTTPException(422, "Pagination ou recherche invalide")
    if search.strip():
        term = _normalized(search.strip()).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(search_column.like("%" + term + "%", escape="\\"))
    total = query.count()
    return query.offset(offset).limit(limit).all(), total


def _project(db, project_id, *, write=False):
    actor = require_project_access(project_id, write=write)
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    return actor


def _reference(db, reference_id, kind, *, allow_inactive=False):
    if reference_id is None:
        return None
    if current_operator().project_ids is not None and reference_id not in _visible_ids(db)[0]:
        raise HTTPException(404, "Référence introuvable dans les projets autorisés")
    row = db.get(ProjectReference, reference_id)
    if not row or row.kind != kind:
        raise HTTPException(422, f"Référence {kind} introuvable ou de type incompatible")
    if not allow_inactive and not row.active:
        raise HTTPException(409, f"Référence {kind} archivée : choisir une référence active")
    return row


def _person(db, person_id, *, allow_inactive=False):
    if person_id is None:
        return None
    if current_operator().project_ids is not None and person_id not in _visible_ids(db)[1]:
        raise HTTPException(404, "Personne introuvable dans les projets autorisés")
    row = db.get(ProjectPerson, person_id)
    if not row:
        raise HTTPException(422, "Personne introuvable")
    if not allow_inactive and not row.active:
        raise HTTPException(409, "Personne archivée : choisir une personne active")
    return row


def _dates(start, end):
    if start and end and end < start:
        raise HTTPException(422, "La date de fin ne peut précéder la date de début")


def describe_reference(row):
    return {name: getattr(row, name) for name in ("id", "kind", "code", "label", "active", "revision")}


def describe_person(row):
    return {"id": row.id, **{name: getattr(row, name) for name in PERSON_FIELDS}, "revision": row.revision}


def describe_member(row):
    from app.db_support import utc_iso
    return {**{name: getattr(row, name) for name in MEMBER_FIELDS},
            "archived_at": utc_iso(row.archived_at) if row.archived_at else None}


def _visible_ids(db):
    """Scoped readers/editors see only references belonging to visible projects."""
    scope = current_operator().project_ids
    if scope is None:
        return None, None
    profiles = db.query(ProjectProfile).filter(ProjectProfile.project_id.in_(scope)).all()
    members = db.query(ProjectMember).filter(ProjectMember.project_id.in_(scope)).all()
    changes = db.query(ProjectIdentityChange).filter(ProjectIdentityChange.project_id.in_(scope)).all()
    person_ids = {row.person_id for row in members}
    person_ids.update(row.responsible_id for row in profiles if row.responsible_id)
    ref_ids = {getattr(row, field) for row in profiles for field in REFERENCE_FIELDS if getattr(row, field)}
    for change in changes:
        for snapshot in (change.previous, change.value):
            ref_ids.update(snapshot[field] for field in REFERENCE_FIELDS if snapshot.get(field))
            person_ids.update(snapshot[field] for field in ("responsible_id", "person_id") if snapshot.get(field))
    # Read-only compatibility with a standalone L1 database: never create the
    # planning schema as a side effect of opening a picker.
    from sqlalchemy import inspect
    from ..project_planning_models import PlanningBaseline, PlanningChange, TaskPlan
    tables = set(inspect(db.connection()).get_table_names())
    if TaskPlan.__tablename__ in tables:
        person_ids.update(row.responsible_id for row in db.query(TaskPlan).filter(TaskPlan.project_id.in_(scope))
                          if row.responsible_id)
    if PlanningChange.__tablename__ in tables:
        for change in db.query(PlanningChange).filter(PlanningChange.project_id.in_(scope)):
            for snapshot in (change.previous, change.value):
                tasks = snapshot.get("tasks", [])
                if "task" in snapshot:
                    tasks = [*tasks, snapshot["task"]]
                person_ids.update(row["responsible_id"] for row in tasks if row.get("responsible_id"))
    if PlanningBaseline.__tablename__ in tables:
        import hashlib
        import json
        for baseline in db.query(PlanningBaseline).filter(PlanningBaseline.project_id.in_(scope)):
            if hashlib.sha256(baseline.payload.encode("utf-8")).hexdigest() != baseline.sha256:
                continue
            try:
                snapshot = json.loads(baseline.payload)
            except (TypeError, ValueError):
                continue
            if isinstance(snapshot, dict) and snapshot.get("project_id") == baseline.project_id:
                person_ids.update(row["responsible_id"] for row in snapshot.get("tasks", [])
                                  if isinstance(row, dict) and row.get("responsible_id"))
    if 'project_deliverable_plans' in tables:
        from ..project_deliverable_models import DeliverablePlan, DeliverableEvent
        for plan in db.query(DeliverablePlan).filter(DeliverablePlan.project_id.in_(scope)):
            person_ids.update(identity for identity in (plan.responsible_id, plan.verifier_id) if identity)
        if DeliverableEvent.__tablename__ in tables:
            for event in db.query(DeliverableEvent).filter(DeliverableEvent.project_id.in_(scope)):
                for snapshot in (event.previous, event.value):
                    person_ids.update(snapshot[field] for field in ('responsible_id', 'verifier_id') if snapshot.get(field))
    ref_ids.update(row.agency_id for row in db.query(ProjectPerson).filter(ProjectPerson.id.in_(person_ids))
                   if row.agency_id)
    return ref_ids, person_ids


def list_references(db, *, kind=None, search="", include_inactive=False, offset=0, limit=50):
    if kind is not None and kind not in REFERENCE_FIELDS.values():
        raise HTTPException(422, "Type de référentiel invalide")
    query = db.query(ProjectReference)
    visible, _ = _visible_ids(db)
    if visible is not None:
        query = query.filter(ProjectReference.id.in_(visible))
    if kind:
        query = query.filter_by(kind=kind)
    if not include_inactive:
        query = query.filter_by(active=True)
    rows, total = _page(query.order_by(ProjectReference.kind, ProjectReference.normalized_code, ProjectReference.id),
                        ProjectReference.search_text, search, offset, limit)
    return {"items": [describe_reference(row) for row in rows], "total": total, "offset": offset, "limit": limit}


def list_people(db, *, search="", include_inactive=False, offset=0, limit=50):
    query = db.query(ProjectPerson)
    _, visible = _visible_ids(db)
    if visible is not None:
        query = query.filter(ProjectPerson.id.in_(visible))
    if not include_inactive:
        query = query.filter_by(active=True)
    rows, total = _page(query.order_by(ProjectPerson.search_text, ProjectPerson.id),
                        ProjectPerson.search_text, search, offset, limit)
    return {"items": [describe_person(row) for row in rows], "total": total, "offset": offset, "limit": limit}


def _flush(db, message):
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(409, message) from exc


def _reference_change(db, actor, kind, entity_id, revision, before, value):
    db.add(ProjectReferenceChange(entity_kind=kind, entity_id=entity_id, revision=revision,
                                  actor_id=actor.id, previous=before, value=value))


def create_reference(db, payload):
    actor = require_reference_write()
    values = payload.model_dump()
    row = ProjectReference(**values, normalized_code=_normalized(values["code"]),
                           search_text=_normalized(values["code"] + " " + values["label"]))
    db.add(row)
    _flush(db, "Ce code existe déjà dans ce référentiel, même s'il est archivé")
    result = describe_reference(row)
    _reference_change(db, actor, "reference", row.id, row.revision, {}, result)
    return result


def _lock_entity(db, model, row, expected):
    changed = db.execute(update(model).where(model.id == row.id, model.revision == expected)
                         .values(revision=model.revision + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise HTTPException(409, "Modification concurrente : recharger avant d'enregistrer")
    db.refresh(row)


def patch_reference(db, reference_id, payload):
    actor = require_reference_write()
    row = db.get(ProjectReference, reference_id)
    if not row:
        raise HTTPException(404, "Référence introuvable")
    _lock_entity(db, ProjectReference, row, payload.expected_revision)
    previous = describe_reference(row)
    previous["revision"] -= 1
    values = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
    values["search_text"] = _normalized(row.code + " " + values.get("label", row.label))
    for field, value in values.items():
        setattr(row, field, value)
    db.flush()
    result = describe_reference(row)
    _reference_change(db, actor, "reference", row.id, row.revision, previous, result)
    return result


def _person_values(values, existing=None):
    merged = {name: getattr(existing, name) for name in PERSON_FIELDS} if existing else {}
    merged.update(values)
    email = merged.get("email", "")
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "Adresse électronique invalide")
    return {**values, "normalized_email": email.casefold() or None,
            "normalized_trigram": merged.get("trigram", "").casefold() or None,
            "search_text": _normalized(" ".join(merged.get(name, "") for name in (
                "first_name", "last_name", "email", "trigram", "function", "service")))}


def create_person(db, payload):
    actor = require_reference_write()
    values = payload.model_dump()
    _reference(db, values["agency_id"], "agency")
    row = ProjectPerson(**_person_values(values))
    db.add(row)
    _flush(db, "L'adresse électronique ou le trigramme identifie déjà une personne")
    result = describe_person(row)
    _reference_change(db, actor, "person", row.id, row.revision, {}, result)
    return result


def patch_person(db, person_id, payload):
    actor = require_reference_write()
    row = _person(db, person_id, allow_inactive=True)
    _lock_entity(db, ProjectPerson, row, payload.expected_revision)
    before = describe_person(row)
    before["revision"] -= 1
    values = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
    if "agency_id" in values:
        _reference(db, values["agency_id"], "agency", allow_inactive=values["agency_id"] == row.agency_id)
    for field, value in _person_values(values, row).items():
        setattr(row, field, value)
    _flush(db, "L'adresse électronique ou le trigramme identifie déjà une personne")
    result = describe_person(row)
    _reference_change(db, actor, "person", row.id, row.revision, before, result)
    return result


def _profile_values(profile):
    if profile:
        return {name: getattr(profile, name) for name in PROFILE_FIELDS}
    return {name: None if name.endswith("_id") or name == "quantity" else False if name == "standby" else ""
            for name in PROFILE_FIELDS}


def read_identity(db, project_id):
    actor = _project(db, project_id)
    project = db.get(Project, project_id)
    profile = db.get(ProjectProfile, project_id)
    values = _profile_values(profile)
    ref_ids = {values[field] for field in REFERENCE_FIELDS if values[field]}
    references = {row.id: describe_reference(row) for row in
                  db.query(ProjectReference).filter(ProjectReference.id.in_(ref_ids))}
    members = db.query(ProjectMember).filter_by(project_id=project_id).order_by(
        ProjectMember.active.desc(), ProjectMember.created_at, ProjectMember.id).all()
    people_ids = {row.person_id for row in members}
    if values["responsible_id"]:
        people_ids.add(values["responsible_id"])
    people = {row.id: describe_person(row) for row in db.query(ProjectPerson).filter(ProjectPerson.id.in_(people_ids))}
    return {"project_id": project_id, "code": project.code, "title": project.title, "status": project.status,
            "legacy_client_name": project.client_name, "offer_number": project.offer_number,
            "revision": profile.revision if profile else 0, **values, "references": references,
            "members": [{**describe_member(row), "person": people[row.person_id]} for row in members],
            "responsible": people.get(values["responsible_id"]), "can_edit": actor.role != "reader",
            "roles": [{"code": code, "label": label} for code, label in ROLE_LABELS.items()]}


def _lock_profile(db, project_id, expected):
    # Acquire SQLite's write lock, then compare revision in the same transaction.
    db.execute(insert(ProjectProfile).values(project_id=project_id).on_conflict_do_nothing(
        index_elements=["project_id"]))
    changed = db.execute(update(ProjectProfile).where(
        ProjectProfile.project_id == project_id, ProjectProfile.revision == expected)
        .values(revision=ProjectProfile.revision + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise HTTPException(409, "Modification concurrente : recharger la fiche et l'équipe")
    profile = db.get(ProjectProfile, project_id)
    db.refresh(profile)
    return profile


def _change(db, actor, profile, action, previous, value):
    db.add(ProjectIdentityChange(project_id=profile.project_id, revision=profile.revision,
                                actor_id=actor.id, action=action, previous=previous, value=value))


def _archive_member(db, actor, profile, member):
    previous = describe_member(member)
    member.active = False
    member.archived_at = now()
    _change(db, actor, profile, "member_archived", previous, describe_member(member))


def _synchronize_responsible(db, actor, profile, person_id):
    current = db.query(ProjectMember).filter_by(project_id=profile.project_id,
                                               role="responsable_projet", active=True).all()
    for member in current:
        if member.person_id != person_id:
            _archive_member(db, actor, profile, member)
    # Release the partial unique index before adding a successor, retaining rows.
    db.flush()
    if person_id and not any(member.person_id == person_id for member in current):
        member = ProjectMember(project_id=profile.project_id, person_id=person_id, role="responsable_projet")
        db.add(member)
        db.flush()
        _change(db, actor, profile, "member_added", {}, describe_member(member))
    profile.responsible_id = person_id


def patch_identity(db, project_id, payload):
    actor = _project(db, project_id, write=True)
    profile = _lock_profile(db, project_id, payload.expected_revision)
    before = _profile_values(profile)
    values = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
    for field, kind in REFERENCE_FIELDS.items():
        if field in values:
            _reference(db, values[field], kind, allow_inactive=values[field] == before[field])
    if "responsible_id" in values:
        _person(db, values["responsible_id"], allow_inactive=values["responsible_id"] == before["responsible_id"])
    merged = {**before, **values}
    _dates(merged["start_date"], merged["planned_end_date"])
    for field, value in values.items():
        if field != "responsible_id":
            setattr(profile, field, value)
    if "responsible_id" in values:
        _synchronize_responsible(db, actor, profile, values["responsible_id"])
    _change(db, actor, profile, "identity_updated", before, _profile_values(profile))
    db.flush()
    from .planning_revision import record_project_dates
    record_project_dates(db, project_id, before, _profile_values(profile))
    return read_identity(db, project_id)


def _validate_member(db, project_id, values, exclude_id=None):
    if values["role"] not in ROLE_LABELS:
        raise HTTPException(422, "Rôle métier invalide")
    _dates(values["start_date"], values["end_date"])
    duplicate = db.query(ProjectMember).filter_by(project_id=project_id, person_id=values["person_id"],
                                                 role=values["role"], active=True)
    if exclude_id:
        duplicate = duplicate.filter(ProjectMember.id != exclude_id)
    if duplicate.first():
        raise HTTPException(409, "Cette personne occupe déjà ce rôle dans le projet")
    if values["role"] == "responsable_projet":
        responsible = db.query(ProjectMember).filter_by(project_id=project_id, role="responsable_projet", active=True)
        if exclude_id:
            responsible = responsible.filter(ProjectMember.id != exclude_id)
        if responsible.first():
            raise HTTPException(409, "Un responsable existe déjà ; le remplacer depuis la fiche projet")


def add_member(db, project_id, payload):
    actor = _project(db, project_id, write=True)
    values = payload.model_dump(exclude={"expected_revision"})
    _person(db, values["person_id"])
    profile = _lock_profile(db, project_id, payload.expected_revision)
    _validate_member(db, project_id, values)
    row = ProjectMember(project_id=project_id, **values)
    db.add(row)
    _flush(db, "Cette affectation existe déjà dans le projet")
    if row.role == "responsable_projet":
        profile.responsible_id = row.person_id
    _change(db, actor, profile, "member_added", {}, describe_member(row))
    db.flush()
    return read_identity(db, project_id)


def _member(db, project_id, member_id):
    row = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.id == member_id))
    if not row:
        raise HTTPException(404, "Membre introuvable dans ce projet")
    if not row.active:
        raise HTTPException(409, "Affectation archivée : créer une nouvelle affectation")
    return row


def patch_member(db, project_id, member_id, payload):
    actor = _project(db, project_id, write=True)
    profile = _lock_profile(db, project_id, payload.expected_revision)
    row = _member(db, project_id, member_id)
    previous = describe_member(row)
    values = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
    if values.get("role", row.role) != row.role:
        _person(db, row.person_id)
    _validate_member(db, project_id, {**previous, **values}, exclude_id=row.id)
    for field, value in values.items():
        setattr(row, field, value)
    if row.role == "responsable_projet":
        profile.responsible_id = row.person_id
    elif previous["role"] == "responsable_projet":
        profile.responsible_id = None
    _change(db, actor, profile, "member_updated", previous, describe_member(row))
    _flush(db, "Cette affectation existe déjà dans le projet")
    return read_identity(db, project_id)


def archive_member(db, project_id, member_id, payload):
    actor = _project(db, project_id, write=True)
    profile = _lock_profile(db, project_id, payload.expected_revision)
    row = _member(db, project_id, member_id)
    _archive_member(db, actor, profile, row)
    if row.role == "responsable_projet":
        profile.responsible_id = None
    db.flush()
    return read_identity(db, project_id)


def identity_history(db, project_id, *, offset=0, limit=50):
    from app.db_support import utc_iso
    _project(db, project_id)
    query = db.query(ProjectIdentityChange).filter_by(project_id=project_id).order_by(
        ProjectIdentityChange.revision.desc(), ProjectIdentityChange.created_at.desc(), ProjectIdentityChange.id.desc())
    rows, total = _page(query, ProjectIdentityChange.action, "", offset, limit)
    return {"items": [{"id": row.id, "revision": row.revision, "actor_id": row.actor_id, "action": row.action,
                       "previous": row.previous, "value": row.value, "created_at": utc_iso(row.created_at)} for row in rows],
            "total": total, "offset": offset, "limit": limit}
