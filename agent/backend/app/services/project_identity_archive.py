"""Selective L1 archive dependencies, validation and explicit conflict detection."""
from datetime import datetime

from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import inspect, select

from ..project_identity_schemas import IdentityPatch, MemberCreate, PersonCreate, ReferenceCreate
from ..schemas import IsoDate

PROJECT_TABLES = frozenset({"project_profiles", "project_members", "project_identity_changes"})
REFERENCE_TABLES = frozenset({"project_references", "project_people"})
REFERENCE_FIELDS = {"client_id": "client", "agency_id": "agency", "business_unit_id": "business_unit",
                    "family_id": "family", "typology_id": "typology"}
PERSON_KEYS = frozenset({"person_id", "responsible_id"})


def _invalid(message):
    raise HTTPException(400, message)


def _id(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 36:
        _invalid("Identifiant de référentiel invalide dans l'archive")
    return value


def _revision(value):
    if type(value) is not int or value < 0:
        _invalid("Révision d'identité invalide dans l'archive")


def _collect(snapshot, reference_ids, people_ids):
    if not isinstance(snapshot, dict):
        _invalid("Instantané d'identité invalide")
    for field, kind in REFERENCE_FIELDS.items():
        if snapshot.get(field) is not None:
            rid = _id(snapshot[field])
            previous_kind = reference_ids.setdefault(rid, kind)
            if previous_kind != kind:
                _invalid("Référence utilisée avec des types incompatibles")
    for field in PERSON_KEYS:
        if snapshot.get(field) is not None:
            people_ids.add(_id(snapshot[field]))


def dependencies(tables, extra=None):
    references, people = {}, set()
    for row in tables.get("project_profiles", []) + tables.get("project_members", []):
        _collect(row, references, people)
    for row in tables.get("project_identity_changes", []):
        _collect(row.get("previous"), references, people)
        _collect(row.get("value"), references, people)
    if extra:
        additional_refs, additional_people = extra
        for rid, kind in additional_refs.items():
            if references.setdefault(rid, kind) != kind:
                _invalid("Référence utilisée avec des types incompatibles")
        people.update(additional_people)
    return references, people


def export_references(db, metadata, tables, *, extra=None):
    reference_ids, people_ids = dependencies(tables, extra)
    result = {name: [] for name in sorted(REFERENCE_TABLES)}
    people = metadata.tables["project_people"]
    rows = db.execute(select(people).where(people.c.id.in_(people_ids)).order_by(people.c.id)).mappings().all()
    result[people.name] = [dict(row) for row in rows]
    for person in rows:
        _collect({"agency_id": person["agency_id"]}, reference_ids, people_ids)
    references = metadata.tables["project_references"]
    result[references.name] = [dict(row) for row in db.execute(select(references).where(
        references.c.id.in_(reference_ids)).order_by(references.c.id)).mappings()]
    for rows in result.values():
        for row in rows:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
    validate_references(metadata, tables, result, extra=extra)
    return result


def _rows(metadata, section):
    if not isinstance(section, dict) or set(section) != REFERENCE_TABLES:
        _invalid("L'archive v3 exige uniquement ses personnes et référentiels utilisés")
    seen = set()
    for name, rows in section.items():
        table = metadata.tables[name]
        if not isinstance(rows, list) or len(rows) > 100000:
            _invalid("Liste de référentiels d'archive invalide")
        for row in rows:
            if not isinstance(row, dict) or set(row) - set(table.c.keys()):
                _invalid("Colonnes de référentiels d'archive invalides")
            rid = _id(row.get("id"))
            if rid in seen:
                _invalid("Identifiant de référentiel dupliqué dans l'archive")
            seen.add(rid)
            if type(row.get("active")) is not bool:
                _invalid("Activation de référentiel invalide")
            _revision(row.get("revision"))
            try:
                datetime.fromisoformat(row["created_at"])
            except (KeyError, TypeError, ValueError) as exc:
                raise HTTPException(400, "Date de référentiel d'archive invalide") from exc


def validate_references(metadata, tables, section, *, extra=None):
    from .project_identity import _normalized, _person_values

    _rows(metadata, section)
    reference_ids, people_ids = dependencies(tables, extra)
    refs = {row["id"]: row for row in section["project_references"]}
    people = {row["id"]: row for row in section["project_people"]}
    try:
        codes, emails, trigrams = set(), set(), set()
        for row in refs.values():
            clean = ReferenceCreate(**{key: row.get(key) for key in ("kind", "code", "label")}).model_dump()
            normalized = _normalized(clean["code"])
            if any(row[key] != clean[key] for key in clean) or row.get("normalized_code") != normalized:
                _invalid("Code de référentiel non canonique")
            if row.get("search_text") != _normalized(clean["code"] + " " + clean["label"]):
                _invalid("Index de recherche de référentiel incohérent")
            if (clean["kind"], normalized) in codes:
                _invalid("Code de référentiel dupliqué dans l'archive")
            codes.add((clean["kind"], normalized))
        for row in people.values():
            fields = PersonCreate.model_fields
            clean = PersonCreate(**{key: row[key] for key in fields if key in row}).model_dump()
            if any(row.get(key) != clean[key] for key in clean):
                _invalid("Fiche personne non canonique")
            derived = _person_values(clean)
            if any(row.get(key) != derived[key] for key in ("normalized_email", "normalized_trigram", "search_text")):
                _invalid("Identifiants de personne incohérents")
            for key, seen in (("normalized_email", emails), ("normalized_trigram", trigrams)):
                value = derived[key]
                if value and value in seen:
                    _invalid("Identifiant de personne dupliqué dans l'archive")
                if value:
                    seen.add(value)
            _collect({"agency_id": clean["agency_id"]}, reference_ids, people_ids)
    except ValidationError as exc:
        raise HTTPException(400, "Fiche de référentiel invalide dans l'archive") from exc
    except HTTPException as exc:
        if exc.status_code != 400:
            raise HTTPException(400, exc.detail) from exc
        raise
    if set(refs) != set(reference_ids) or set(people) != people_ids:
        _invalid("Référentiel absent ou étranger au projet : import global interdit")
    for rid, kind in reference_ids.items():
        if refs[rid]["kind"] != kind:
            _invalid("Type de référence incompatible avec son utilisation")
    return section


def validate_identity(tables):
    profiles = tables.get("project_profiles", [])
    if len(profiles) > 1:
        _invalid("Plusieurs fiches d'identité pour un projet")
    if not profiles and (tables.get("project_members") or tables.get("project_identity_changes")):
        _invalid("Équipe ou historique sans fiche d'identité")
    profile = profiles[0] if profiles else None
    active_members, responsible = set(), []
    try:
        if profile:
            _revision(profile.get("revision"))
            clean = IdentityPatch(expected_revision=profile["revision"], **{
                key: value for key, value in profile.items() if key in IdentityPatch.model_fields
            }).model_dump(exclude_unset=True, exclude={"expected_revision"})
            if any(profile[key] != clean[key] for key in clean):
                _invalid("Fiche d'identité non canonique")
            TypeAdapter(IsoDate).validate_python(profile.get("actual_closure_date", ""))
            if profile.get("start_date") and profile.get("planned_end_date") and profile["planned_end_date"] < profile["start_date"]:
                _invalid("Échéance antérieure au début du projet")
        for row in tables.get("project_members", []):
            clean = MemberCreate(expected_revision=0, **{key: row.get(key, "") for key in (
                "person_id", "role", "start_date", "end_date")}).model_dump(exclude={"expected_revision"})
            if any(row.get(key, "") != clean[key] for key in clean):
                _invalid("Affectation non canonique")
            if type(row.get("active")) is not bool:
                _invalid("Activation d'affectation invalide")
            if clean["start_date"] and clean["end_date"] and clean["end_date"] < clean["start_date"]:
                _invalid("Dates d'affectation incohérentes")
            if row["active"]:
                pair = (row["person_id"], row["role"])
                if pair in active_members or row.get("archived_at"):
                    _invalid("Affectation active dupliquée ou déjà archivée")
                active_members.add(pair)
                if row["role"] == "responsable_projet":
                    responsible.append(row["person_id"])
            elif not row.get("archived_at"):
                _invalid("Affectation archivée sans date d'archivage")
        expected = [profile["responsible_id"]] if profile and profile.get("responsible_id") else []
        if responsible != expected:
            _invalid("Responsable et équipe de l'archive incohérents")
        for row in tables.get("project_identity_changes", []):
            _revision(row.get("revision"))
            if row["revision"] > profile["revision"]:
                _invalid("Historique d'identité plus récent que sa fiche")
            if not isinstance(row.get("actor_id"), str) or not 1 <= len(row["actor_id"]) <= 120:
                _invalid("Acteur d'historique invalide")
            if row.get("action") not in {"identity_updated", "member_added", "member_updated", "member_archived"}:
                _invalid("Action d'historique inconnue")
            _validate_history_snapshots(row, tables)
    except (ValidationError, TypeError, ValueError) as exc:
        raise HTTPException(400, "Identité ou équipe invalide dans l'archive") from exc


def _validate_history_snapshots(event, tables):
    project_id = tables["projects"][0]["id"]
    member_ids = {row["id"] for row in tables.get("project_members", [])}
    for field in ("previous", "value"):
        snapshot = event.get(field)
        if not isinstance(snapshot, dict):
            _invalid("Instantané d'historique invalide")
        if event["action"] == "identity_updated":
            allowed = (set(IdentityPatch.model_fields) - {"expected_revision"}) | {"actual_closure_date"}
            if set(snapshot) - allowed:
                _invalid("Champs étrangers dans l'historique de fiche")
            clean = IdentityPatch(expected_revision=0, **{key: value for key, value in snapshot.items()
                                                        if key != "actual_closure_date"})
            if clean.start_date and clean.planned_end_date and clean.planned_end_date < clean.start_date:
                _invalid("Dates historiques incohérentes")
            TypeAdapter(IsoDate).validate_python(snapshot.get("actual_closure_date", ""))
        elif event["action"] == "member_added" and field == "previous":
            if snapshot:
                _invalid("Création de membre avec un état précédent incohérent")
        else:
            allowed = {"id", "project_id", "person_id", "role", "start_date", "end_date", "active", "archived_at"}
            if (set(snapshot) - allowed or snapshot.get("id") not in member_ids
                    or snapshot.get("project_id") != project_id or type(snapshot.get("active")) is not bool):
                _invalid("Membre d'historique absent ou étranger au projet")
            clean = MemberCreate(expected_revision=0, **{key: snapshot.get(key, "") for key in (
                "person_id", "role", "start_date", "end_date")})
            if clean.start_date and clean.end_date and clean.end_date < clean.start_date:
                _invalid("Dates d'affectation historiques incohérentes")
            if snapshot.get("archived_at"):
                datetime.fromisoformat(snapshot["archived_at"])


def reconcile_references(db, metadata, section, mapping):
    """Reuse an exact business match; never infer a person from their name alone.

    Detect all conflicts before any file or database write. Revision/timestamp
    remain on the existing row; project history is restored independently.
    """
    pending = {name: [] for name in REFERENCE_TABLES}
    available = set(inspect(db.get_bind()).get_table_names())
    if not REFERENCE_TABLES.issubset(available):
        raise HTTPException(409, "Activer la migration d'identité avant d'importer une archive v3")
    for name in ("project_references", "project_people"):
        table = metadata.tables[name]
        claimed = set()
        for raw in section[name]:
            candidates = {}
            original = db.execute(select(table).where(table.c.id == raw["id"])).mappings().first()
            if original:
                candidates[original["id"]] = original
            if name == "project_references":
                matches = db.execute(select(table).where(table.c.kind == raw["kind"],
                                                        table.c.normalized_code == raw["normalized_code"])).mappings()
                business_fields = ("kind", "code", "label", "active")
            else:
                conditions = [table.c[key] == raw[key] for key in ("normalized_email", "normalized_trigram") if raw[key]]
                from sqlalchemy import or_
                matches = db.execute(select(table).where(or_(*conditions))).mappings() if conditions else []
                business_fields = tuple(PersonCreate.model_fields) + ("active",)
            for row in matches:
                candidates[row["id"]] = row
            comparable = {key: mapping.get(raw[key], raw[key]) if key == "agency_id" else raw[key]
                          for key in business_fields}
            if len(candidates) > 1 or any(any(row[key] != value for key, value in comparable.items())
                                          for row in candidates.values()):
                raise HTTPException(409, {"message": "Référentiel différent : aucune donnée existante modifiée",
                                          "table": name, "archive_id": raw["id"],
                                          "existing_ids": sorted(candidates)})
            if candidates:
                target = next(iter(candidates))
                if target in claimed:
                    _invalid("Deux personnes d'archive désignent la même personne existante")
                claimed.add(target)
                mapping[raw["id"]] = target
            else:
                pending[name].append(raw)
    return pending


def remap_identity_row(row, table, mapping):
    result = dict(row)
    for column in table.c:
        if column.primary_key or column.foreign_keys:
            value = result.get(column.name)
            if isinstance(value, str):
                result[column.name] = mapping.get(value, value)
    if table.name == "project_identity_changes":
        keys = set(REFERENCE_FIELDS) | PERSON_KEYS | {"id", "project_id"}
        for field in ("previous", "value"):
            result[field] = {key: mapping.get(value, value) if key in keys and isinstance(value, str) else value
                             for key, value in row[field].items()}
    return result
