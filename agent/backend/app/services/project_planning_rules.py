"""L2 planning rules, independent of storage and without implicit project writes.

An explicit preview/application service will consume these contracts. The
existing eight milestones, their dates and their evidence remain authoritative.
"""
from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator


PROJECT_WORKFLOW = (
    ("reception", "Réception"), ("remise_offre", "Remise offre"),
    ("recp_commande", "Réception commande"), ("rlp", "RLP"),
    ("kom", "KOM"), ("pdr", "PDR"), ("cdr", "CDR"), ("fdr", "FDR"),
    ("go_fabrication", "Go fabrication"), ("reception_ciss", "Réception CISS"),
    ("livraison", "Livraison"), ("mise_en_service", "Mise en service"),
    ("validation_client", "Validation client"), ("cloture", "Clôture"),
)


class MilestoneSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    title: str = Field(min_length=1, max_length=255)
    offset_workdays: int | None = Field(default=None, ge=-10000, le=10000)


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    key: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    title: str = Field(min_length=1, max_length=255)
    parent_key: str | None = Field(default=None, min_length=1, max_length=64)
    milestone_code: str | None = Field(default=None, min_length=1, max_length=64)
    start_offset_workdays: int | None = Field(default=None, ge=-10000, le=10000)
    end_offset_workdays: int | None = Field(default=None, ge=-10000, le=10000)
    planned_hours: FiniteFloat = Field(default=0, ge=0, le=1000000)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    design: bool = False
    manufacturing: bool = False

    @model_validator(mode="after")
    def dates_order(self):
        if (self.start_offset_workdays is not None and self.end_offset_workdays is not None
                and self.end_offset_workdays < self.start_offset_workdays):
            raise ValueError("La fin de tâche précède son début")
        return self


class TemplateDefinition(BaseModel):
    """A version's value; changing it never changes an existing project."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)
    milestones: list[MilestoneSpec] = Field(min_length=1, max_length=100)
    tasks: list[TaskSpec] = Field(default_factory=list, max_length=1000)

    @field_validator("milestones")
    @classmethod
    def unique_milestones(cls, values):
        if len({value.code for value in values}) != len(values):
            raise ValueError("Code de jalon dupliqué")
        return values

    @model_validator(mode="after")
    def task_graph(self):
        codes = {value.code for value in self.milestones}
        tasks = {value.key: value for value in self.tasks}
        if len(tasks) != len(self.tasks):
            raise ValueError("Clé de tâche dupliquée")
        records = {key: {"id": key, "project_id": "template", "parent_id": task.parent_key}
                   for key, task in tasks.items()}
        parents = {task.parent_key for task in self.tasks if task.parent_key}
        for task in self.tasks:
            if task.milestone_code is not None and task.milestone_code not in codes:
                raise ValueError("Jalon de tâche absent du modèle")
            validate_parent(records, "template", task.key, task.parent_key)
            if task.key in parents and (task.planned_hours or task.start_offset_workdays is not None
                                        or task.end_offset_workdays is not None):
                raise ValueError("Les dates et charges d'une tâche parente proviennent de ses enfants")
        aggregate_task_rows('template', [{"id": task.key, "parent_id": task.parent_key,
                                         "planned_hours": task.planned_hours} for task in self.tasks])
        return self


@dataclass(frozen=True)
class WorkCalendar:
    """Monday-Friday, with explicitly supplied exclusions; no guessed holidays."""
    excluded_dates: frozenset[date] = frozenset()

    def __post_init__(self):
        if any(type(value) is not date for value in self.excluded_dates):
            raise ValueError("Les exclusions du calendrier doivent être des dates")
        object.__setattr__(self, "excluded_dates", frozenset(self.excluded_dates))

    def add_workdays(self, start: date, amount: int) -> date:
        if type(start) is not date or isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError("Date et nombre entier de jours ouvrés requis")
        if not -10000 <= amount <= 10000:
            raise ValueError("Décalage en jours ouvrés hors limite")
        current, remaining = start, abs(amount)
        step = timedelta(days=1 if amount >= 0 else -1)
        while remaining:
            try:
                current += step
            except OverflowError as exc:
                raise ValueError("Le calendrier dépasse la plage de dates prise en charge") from exc
            if current.weekday() < 5 and current not in self.excluded_dates:
                remaining -= 1
        return current


def default_template() -> TemplateDefinition:
    return TemplateDefinition(name="Cycle de vie XPilot — 14 jalons",
                              milestones=[MilestoneSpec(code=code, title=title) for code, title in PROJECT_WORKFLOW])


def validate_parent(records: dict, project_id: str, task_id: str, parent_id: str | None):
    """Reject dangling/foreign parents and cycles, including corrupted ancestors."""
    row = records.get(task_id)
    if row is None or row.get("project_id") != project_id:
        raise ValueError("Tâche absente du projet")
    visited = {task_id}
    cursor = parent_id
    while cursor is not None:
        if cursor in visited:
            raise ValueError("Cycle de tâches interdit")
        visited.add(cursor)
        parent = records.get(cursor)
        if parent is None or parent.get("project_id") != project_id:
            raise ValueError("Tâche parente absente du projet")
        cursor = parent.get("parent_id")


def preview_template(definition: TemplateDefinition, start: date | None, calendar=WorkCalendar()):
    """Dates proposed as forecasts only; null offset/start remains undated."""
    definition = TemplateDefinition.model_validate(definition.model_dump())
    if start is not None and type(start) is not date:
        raise ValueError("Date de début requise")
    def proposed(offset):
        return calendar.add_workdays(start, offset).isoformat() if start is not None and offset is not None else ""
    milestones = [{"code": item.code, "title": item.title, "order": order,
                   "forecast_date": proposed(item.offset_workdays), "contractual_date": "", "actual_date": ""}
                  for order, item in enumerate(definition.milestones)]
    tasks = [{**item.model_dump(), "start_date": proposed(item.start_offset_workdays),
              "end_date": proposed(item.end_offset_workdays)} for item in definition.tasks]
    by_key = {item["key"]: item for item in tasks}
    children = {}
    for item in tasks:
        if item["parent_key"]:
            children.setdefault(item["parent_key"], []).append(item["key"])
    # Bottom-up without Python recursion; the validated graph is acyclic.
    pending = set(children)
    while pending:
        ready = [key for key in pending if not any(child in pending for child in children[key])]
        if not ready:
            raise ValueError("Cycle de tâches interdit")
        for key in ready:
            rows = [by_key[child] for child in children[key]]
            by_key[key]["planned_hours"] = sum(row["planned_hours"] for row in rows)
            # An incomplete child must remain visibly incomplete in its parent.
            by_key[key]["start_date"] = min(row["start_date"] for row in rows) if all(row["start_date"] for row in rows) else ""
            by_key[key]["end_date"] = max(row["end_date"] for row in rows) if all(row["end_date"] for row in rows) else ""
            pending.remove(key)
    return {"milestones": milestones, "tasks": tasks,
            "planned_hours": sum(row["planned_hours"] for row in tasks if not row["parent_key"]),
            "application_required": True}


def legacy_mapping_proposals(milestones):
    """Conservative suggestions; ambiguous design/acceptance stages stay unmapped."""
    from .milestones import canonical_title
    proposed_codes = {"Lancement du projet": "kom", "Livraison": "livraison"}
    result = []
    for row in milestones:
        title = canonical_title(row["title"])
        code = proposed_codes.get(title)
        result.append({"milestone_id": row["id"], "title": row["title"], "suggested_code": code,
                       "human_confirmation_required": True,
                       "reason": "Correspondance à vérifier" if code else "Aucune équivalence unique établie"})
    return result


MILESTONE_FIELDS = ("id", "title", "code", "order", "status", "workflow_status", "comment", "active", "due_date",
                    "contractual_date", "forecast_date", "actual_date", "date_sources")
TASK_FIELDS = ("id", "title", "status", "parent_id", "milestone_id", "responsible_id", "priority",
               "template_id", "template_key", "start_date", "end_date", "due_date", "planned_hours",
               "design", "manufacturing", "comment", "active")


def aggregate_task_rows(project_id, tasks):
    """Complete proposed tree, including manual children; no database writes."""
    rows = {row["id"]: {**row, "project_id": project_id} for row in tasks}
    if len(rows) != len(tasks):
        raise ValueError("Identifiant de tâche dupliqué")
    children = {}
    for row in rows.values():
        validate_parent(rows, project_id, row["id"], row.get("parent_id"))
        if row.get("parent_id"):
            children.setdefault(row["parent_id"], []).append(row["id"])
            if row.get("active", True) and not rows[row["parent_id"]].get("active", True):
                raise ValueError("Une tâche active ne peut dépendre d'un parent archivé")
    pending = set(children)
    while pending:
        ready = [key for key in pending if not any(child in pending for child in children[key])]
        if not ready:
            raise ValueError("Cycle de tâches interdit")
        for key in ready:
            active = [rows[child] for child in children[key] if rows[child].get("active", True)]
            hours = sum(row.get("planned_hours", 0) for row in active)
            if hours > 1000000:
                raise ValueError("La charge cumulée du groupe dépasse 1 000 000 heures")
            rows[key].update(planned_hours=hours,
                start_date=min(row["start_date"] for row in active) if active and all(row.get("start_date") for row in active) else "",
                end_date=max(row["end_date"] for row in active) if active and all(row.get("end_date") for row in active) else "")
            rows[key]["due_date"] = rows[key]["end_date"]
            pending.remove(key)
    for row in rows.values():
        if row.get("start_date") and row.get("end_date") and row["end_date"] < row["start_date"]:
            raise ValueError("La fin de tâche précède son début")
    return [{key: value for key, value in row.items() if key != "project_id"} for row in rows.values()]


@dataclass(frozen=True)
class PlanningSnapshot:
    """Serialized immutable value, ready to persist with its integrity hash."""
    payload: str
    sha256: str


def validate_project_values(value):
    """Operational commitments only; never infer budget from task totals."""
    if not isinstance(value, dict) or set(value) != {'start_date', 'planned_end_date', 'budget_hours'}:
        raise ValueError("Champs de référence projet invalides")
    for field in ('start_date', 'planned_end_date'):
        raw = value[field]
        if not isinstance(raw, str):
            raise ValueError("Date de projet invalide")
        if raw:
            try:
                parsed = date.fromisoformat(raw)
            except ValueError as exc:
                raise ValueError("Date de projet invalide") from exc
            if parsed.isoformat() != raw:
                raise ValueError("Date de projet invalide")
    if value['start_date'] and value['planned_end_date'] and value['planned_end_date'] < value['start_date']:
        raise ValueError("La fin du projet précède son début")
    hours = value['budget_hours']
    if type(hours) not in (int, float) or not 0 <= hours <= 1000000000000:
        raise ValueError("Budget d'heures du projet invalide")
    return dict(value)


def capture_snapshot(project_id, milestones, tasks, *, project=None):
    def rows(values, fields):
        result = []
        seen = set()
        for value in values:
            if not value.get("id") or value["id"] in seen:
                raise ValueError("Identifiant de planning absent ou dupliqué")
            if value.get("project_id", project_id) != project_id:
                raise ValueError("Élément de planning appartenant à un autre projet")
            seen.add(value["id"])
            result.append({key: value[key] for key in fields if key in value})
        return sorted(result, key=lambda value: value["id"])
    milestone_rows, task_rows = rows(milestones, MILESTONE_FIELDS), rows(tasks, TASK_FIELDS)
    task_graph = {row["id"]: {**row, "project_id": project_id} for row in task_rows}
    milestone_ids = {row["id"] for row in milestone_rows}
    for row in task_rows:
        validate_parent(task_graph, project_id, row["id"], row.get("parent_id"))
        if row.get("milestone_id") and row["milestone_id"] not in milestone_ids:
            raise ValueError("Jalon de tâche absent du projet")
    value = {"format": "agent-project-planning", "version": 1, "project_id": project_id,
             "milestones": milestone_rows, "tasks": task_rows}
    if project is not None:
        value.update(version=2, project=validate_project_values(project))
    payload = json.dumps(value,
                         ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return PlanningSnapshot(payload=payload, sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest())


def compare_snapshots(before: PlanningSnapshot, after: PlanningSnapshot):
    def decode(value):
        if hashlib.sha256(value.payload.encode("utf-8")).hexdigest() != value.sha256:
            raise ValueError("Empreinte de référence de planning incohérente")
        record = json.loads(value.payload)
        if (not isinstance(record, dict) or record.get("format") != "agent-project-planning"
                or type(record.get('version')) is not int or record['version'] not in (1, 2)):
            raise ValueError("Format de référence de planning non reconnu")
        fields = {'format', 'version', 'project_id', 'milestones', 'tasks'}
        if record['version'] == 2:
            fields.add('project')
            validate_project_values(record.get('project'))
        if set(record) != fields:
            raise ValueError("Champs étrangers dans la référence de planning")
        return record
    previous, current = decode(before), decode(after)
    if previous["project_id"] != current["project_id"]:
        raise ValueError("Références de projets différents")
    changes = []
    project_available = previous['version'] == current['version'] == 2
    if project_available:
        for field in ('start_date', 'planned_end_date', 'budget_hours'):
            old, new = previous['project'][field], current['project'][field]
            if old != new:
                changes.append({'kind': 'project', 'id': current['project_id'], 'title': 'Projet',
                                'field': field, 'severity': 'high', 'before': old, 'after': new})
    for collection in ("milestones", "tasks"):
        left = {row["id"]: row for row in previous[collection]}
        right = {row["id"]: row for row in current[collection]}
        for identity in sorted(left.keys() | right.keys()):
            if identity not in left or identity not in right:
                changes.append({"kind": collection, "id": identity, "field": None, "severity": "high",
                                "title": (right.get(identity) or left[identity]).get('title', identity),
                                "before": left.get(identity), "after": right.get(identity)})
                continue
            for field in sorted(left[identity].keys() | right[identity].keys()):
                old, new = left[identity].get(field), right[identity].get(field)
                if old != new:
                    changes.append({"kind": collection, "id": identity, "field": field,
                                    "title": right[identity].get('title') or left[identity].get('title') or identity,
                                    "severity": "high" if field in {"actual_date", "contractual_date", "parent_id", "milestone_id"} else "normal",
                                    "before": old, "after": new})
    def hours(value):
        active = [row for row in value["tasks"] if row.get("active", True)]
        parents = {row["parent_id"] for row in active if row.get("parent_id")}
        return sum(row.get("planned_hours", 0) for row in active if row["id"] not in parents)
    return {"changes": changes, "planned_hours_delta": hours(current) - hours(previous),
            'project_comparison_available': project_available,
            'project_budget_hours_delta': current['project']['budget_hours'] - previous['project']['budget_hours']
            if project_available else None}
