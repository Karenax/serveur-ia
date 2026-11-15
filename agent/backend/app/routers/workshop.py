"""Atelier : Achats + Pointage alimentés par Sage, BOM manuelle, saisie d'heures."""
from __future__ import annotations
from app.operational_limits import DOCUMENT_IMPORT_BYTES

import csv
import io
import json
import math
import unicodedata

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import Field
from ..schemas import DomainInput as BaseModel, IsoDate, TaskStatus
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from ..db import get_db
from ..models import BomLine, Project, SageAchat, SagePointage, TimeEntry

router = APIRouter(prefix="/api/v1", tags=["workshop"])

def _first(payload: dict, tokens: tuple[str, ...]) -> str:
    for key, value in payload.items():
        if value not in (None, "") and any(t in key.casefold() for t in tokens):
            return str(value).strip()
    return ""


def _payload(row) -> dict:
    try:
        data = json.loads(row.payload or "{}")
    except (TypeError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


def _for_project(db: Session, model, code: str) -> list:
    code = (code or "").strip().casefold()
    if not code:
        return []
    return db.query(model).filter(func.lower(func.trim(model.affaire)) == code).all()


def _project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")
    return project


# ── Achats ──────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/purchases")
def purchases(project_id: str, db: Session = Depends(get_db)):
    project = _project(db, project_id)
    rows = []
    columns: list[str] = []
    for row in _for_project(db, SageAchat, project.code):
        payload = _payload(row)
        if not columns:
            columns = [k for k in payload if not any(t in k.casefold() for t in ("montant", "total", "prix", "valeur", "marge", "taux"))][:12]
        rows.append({"supplier": _first(payload, ("fournisseur",)),
                     "label": _first(payload, ("designation", "libelle", "objet", "article", "description")),
                     "status": _first(payload, ("statut", "etat")), "date": _first(payload, ("date",)),
                     "payload": {k: payload.get(k, "") for k in columns}})
    return {"rows": rows, "columns": columns, "count": len(rows)}


# ── Pointage ────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/time-tracking")
def time_tracking(project_id: str, db: Session = Depends(get_db)):
    project = _project(db, project_id)
    entries = []
    for row in _for_project(db, SagePointage, project.code):
        payload = _payload(row)
        from ..services.work_hours import sage_hours
        hours = sage_hours(row.payload)
        entries.append({
            "source": "sage",
            "person": _first(payload, ("nom", "salarie", "employe", "intervenant", "collaborateur")),
            "date": _first(payload, ("date",)),
            "label": _first(payload, ("lot", "tache", "libelle", "objet", "description")),
            "hours": round(hours, 2),
        })
    for entry in db.query(TimeEntry).filter_by(project_id=project_id).all():
        entries.append({"source": "manuel", "id": entry.id, "person": entry.person,
                        "date": entry.date, "label": entry.label,
                        "hours": round(entry.hours or 0, 2)})
    by_person: dict[str, float] = {}
    for entry in entries:
        name = entry["person"] or "Non renseigné"
        by_person[name] = round(by_person.get(name, 0.0) + entry["hours"], 2)
    return {"entries": entries,
            "by_person": [{"person": name, "hours": hours} for name, hours in sorted(by_person.items())],
            "total_hours": round(sum(e["hours"] for e in entries), 2)}


class TimeEntryCreate(BaseModel):
    person: str = Field(min_length=1)
    date: IsoDate = ""
    hours: float = Field(ge=0)
    label: str = ""


@router.post("/projects/{project_id}/time-entries", status_code=201)
def add_time_entry(project_id: str, payload: TimeEntryCreate, db: Session = Depends(get_db)):
    _project(db, project_id)
    entry = TimeEntry(project_id=project_id, person=payload.person.strip(),
                      date=payload.date, hours=payload.hours, label=payload.label.strip())
    db.add(entry)
    db.commit()
    return {"id": entry.id}


# ── BOM ─────────────────────────────────────────────────────────────

def _bom_read(db: Session, project_id: str) -> dict:
    lines = db.query(BomLine).filter_by(project_id=project_id).order_by(BomLine.position, BomLine.id).all()
    rows = [{"id": line.id, "reference": line.reference, "designation": line.designation,
             "quantity": line.quantity,
             "supplier": line.supplier, "status": line.status} for line in lines]
    return {"lines": rows, "count": len(rows)}


def _bom_append_position(db: Session, project_id: str) -> int:
    db.execute(text("BEGIN IMMEDIATE"))
    return db.query(func.coalesce(func.max(BomLine.position), -1) + 1).filter(
        BomLine.project_id == project_id).scalar()


class BomLineCreate(BaseModel):
    reference: str = ""
    designation: str = Field(min_length=1)
    quantity: float = Field(ge=0, default=1)
    supplier: str = ""
    status: TaskStatus = "todo"


class BomLinePatch(BaseModel):
    reference: str | None = None
    designation: str | None = None
    quantity: float | None = Field(default=None, ge=0)
    supplier: str | None = None
    status: TaskStatus | None = None


@router.get("/projects/{project_id}/bom")
def get_bom(project_id: str, db: Session = Depends(get_db)):
    _project(db, project_id)
    return _bom_read(db, project_id)


@router.post("/projects/{project_id}/bom", status_code=201)
def add_bom_line(project_id: str, payload: BomLineCreate, db: Session = Depends(get_db)):
    _project(db, project_id)
    position = _bom_append_position(db, project_id)
    line = BomLine(project_id=project_id, reference=payload.reference.strip(),
                   designation=payload.designation.strip(), quantity=payload.quantity, supplier=payload.supplier.strip(),
                   status=payload.status, position=position)
    db.add(line)
    db.commit()
    return {"id": line.id}


@router.patch("/projects/{project_id}/bom/{line_id}")
def patch_bom_line(project_id: str, line_id: str, payload: BomLinePatch,
                   db: Session = Depends(get_db)):
    line = db.query(BomLine).filter_by(id=line_id, project_id=project_id).first()
    if not line:
        raise HTTPException(404, "Ligne introuvable")
    for field in ("reference", "designation", "quantity", "supplier", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(line, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    return {"id": line.id}


@router.post("/projects/{project_id}/bom/import")
def import_bom_csv(project_id: str, file: UploadFile = File(...),
                   db: Session = Depends(get_db)):
    _project(db, project_id)
    raw = file.file.read(DOCUMENT_IMPORT_BYTES + 1)
    if len(raw) > DOCUMENT_IMPORT_BYTES:
        raise HTTPException(413, "CSV limité à 50 MiB")
    content = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        raise HTTPException(400, "Encodage CSV non pris en charge")
    rows = _bom_csv_rows(content)
    _, headers = next(rows, (1, []))
    if not any(header.strip() for header in headers):
        raise HTTPException(400, "CSV sans en-tête")
    names = ["".join(c for c in unicodedata.normalize("NFKD", name.casefold().strip())
                     if not unicodedata.combining(c)) for name in headers]
    named_headers = [name for name in names if name]
    if len(set(named_headers)) != len(named_headers):
        raise HTTPException(422, "Noms de colonnes en double à la ligne 1")
    aliases = {
        "reference": ("reference", "repere", "ref"),
        "designation": ("designation", "libelle", "article"),
        "quantity": ("quantite", "qte", "qty"),
        "supplier": ("fournisseur",),
    }
    columns = {}
    for field, tokens in aliases.items():
        exact = next((i for i, name in enumerate(names) if name in tokens), None)
        columns[field] = exact if exact is not None else next(
            (i for i, name in enumerate(names) if any(token in name for token in tokens)), None)
    if columns["designation"] is None:
        raise HTTPException(422, "Colonne Désignation manquante à la ligne 1. Séparez les colonnes avec un point-virgule.")
    mapped = [index for index in columns.values() if index is not None]
    if len(set(mapped)) != len(mapped):
        raise HTTPException(422, "Colonnes ambiguës à la ligne 1. Séparez les colonnes avec un point-virgule.")

    lines = []
    for row_index, (line_number, row) in enumerate(rows, start=1):
        if row_index > 100000:
            raise HTTPException(413, "CSV limité à 100000 lignes")
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(headers):
            raise HTTPException(422, f"{len(row)} colonnes à la ligne {line_number}, {len(headers)} attendues")
        values = {field: row[index].strip() if index is not None else "" for field, index in columns.items()}
        if not values["designation"]:
            raise HTTPException(422, f"Désignation manquante à la ligne {line_number}")
        try:
            quantity = float((values["quantity"] or "1").replace(" ", "").replace(",", "."))
        except ValueError as exc:
            raise HTTPException(422, f"Quantité invalide à la ligne {line_number}") from exc
        if not math.isfinite(quantity) or quantity < 0:
            raise HTTPException(422, f"Quantité invalide à la ligne {line_number}")
        lines.append(BomLine(project_id=project_id, reference=values["reference"],
                             designation=values["designation"], quantity=quantity,
                             supplier=values["supplier"], status="todo"))

    if not lines:
        return {"created": 0}
    position = _bom_append_position(db, project_id)
    for index, line in enumerate(lines, start=position):
        line.position = index
    db.add_all(lines)
    db.commit()
    return {"created": len(lines)}


def _bom_csv_rows(content: str):
    reader = csv.reader(io.StringIO(content, newline=""), delimiter=";", strict=True)
    while True:
        line_number = reader.line_num + 1
        try:
            row = next(reader, None)
        except csv.Error as exc:
            raise HTTPException(422, f"Format CSV invalide à la ligne {line_number}") from exc
        if row is None:
            return
        if row:
            yield line_number, row
