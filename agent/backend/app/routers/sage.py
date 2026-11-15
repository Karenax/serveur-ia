"""Import Sage copié d'XPilot : CSV `;` (utf-8-sig → cp1252), dernier fichier par
dossier (Achats et Pointages), lignes rattachées par code affaire.
"""
from __future__ import annotations

import codecs
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SageAchat, SageBatch, SageConfig, SagePointage

router = APIRouter(prefix="/api/v1", tags=["sage"])

# Audit : seules les sources affichées dans l'UI sont importées.
# Budget/Ventes Sage ne sont ni affichées ni agrégées (modèles conservés en base
# pour compatibilité, mais exclus de l'import pour ne pas exiger 4 dossiers).
SOURCES = (
    ("achats", "Achats", SageAchat),
    ("pointages", "Pointages", SagePointage),
)

DECIMAL_VALUE = re.compile(r"^[+-]?(?:\d+)?[,]\d+$")


def _detect_encoding(path: Path) -> str:
    decoder = codecs.getincrementaldecoder("utf-8-sig")()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "cp1252"


def _affaire(payload: dict) -> str | None:
    for key, value in payload.items():
        if key.casefold() == "affaire":
            return (value or "")[:128] or None
    return None


@router.get("/sage/config")
def get_config(db: Session = Depends(get_db)):
    row = db.get(SageConfig, "default")
    return {"root_path": (row.root_path if row else os.environ.get("MINIPILOT_SAGE_ROOT", "")) or ""}


class SageConfigUpdate(BaseModel):
    root_path: str


@router.put("/sage/config")
def put_config(payload: SageConfigUpdate, db: Session = Depends(get_db)):
    root = payload.root_path.strip()
    if not root:
        raise HTTPException(400, "Le chemin des exports Sage est obligatoire")
    row = db.get(SageConfig, "default")
    if row is None:
        row = SageConfig(id="default", root_path=root)
        db.add(row)
    else:
        row.root_path = root
    db.commit()
    return {"root_path": root}


@router.get("/sage/status")
def sage_status(db: Session = Depends(get_db)):
    batch = db.query(SageBatch).order_by(SageBatch.started_at.desc()).first()
    if batch is None:
        return {"batch": None, "sources": []}
    try:
        sources = json.loads(batch.sources or "{}").get("items", [])
    except (TypeError, ValueError):
        sources = []
    return {
        "batch": {"id": batch.id, "status": batch.status,
                  "root_path": batch.root_path,
                  "started_at": str(batch.started_at),
                  "finished_at": str(batch.finished_at) if batch.finished_at else None,
                  "total_rows": batch.total_rows,
                  "error_message": batch.error_message or ""},
        "sources": sources,
    }


@router.post("/sage/run")
def run_import(db: Session = Depends(get_db)):
    row = db.get(SageConfig, "default")
    root = (row.root_path if row else "") or os.environ.get("MINIPILOT_SAGE_ROOT", "")
    root_path = Path(root.strip())
    if not root.strip():
        raise HTTPException(400, "Configure d'abord le chemin des exports Sage (onglet Import)")
    if not root_path.is_dir():
        raise HTTPException(422, f"Partage Sage inaccessible : {root_path}")
    batch = SageBatch(status="running", root_path=str(root_path))
    db.add(batch)
    db.commit()
    db.refresh(batch)
    items: list[dict] = []
    total = 0
    try:
        for key, folder_name, model in SOURCES:
            folder = root_path / folder_name
            if not folder.is_dir():
                raise HTTPException(422, f"Dossier Sage manquant : {folder}")
            candidates = [e for e in os.scandir(folder)
                          if e.is_file() and Path(e.name).suffix.casefold() == ".csv"]
            if not candidates:
                raise HTTPException(422, f"Aucun CSV dans {folder}")
            latest = max(candidates, key=lambda e: (e.stat().st_mtime_ns, e.name))
            rows = _replace_source(db, batch.id, model, Path(latest.path))
            total += rows
            items.append({"source": key, "folder": folder_name,
                          "file_name": Path(latest.path).name, "rows": rows})
        batch.status = "success"
        batch.total_rows = total
    except HTTPException as exc:
        db.rollback()
        batch = db.get(SageBatch, batch.id)
        batch.status = "failed"
        batch.error_message = str(exc.detail)[:2000]
        batch.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise
    except Exception as exc:
        db.rollback()
        batch = db.get(SageBatch, batch.id)
        batch.status = "failed"
        batch.error_message = f"Échec de l'import Sage : {exc}"[:2000]
        batch.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(503, batch.error_message)
    batch.finished_at = datetime.now(timezone.utc)
    batch.sources = json.dumps({"items": items})
    db.commit()
    return {"id": batch.id, "status": batch.status, "total_rows": total, "sources": items}


def _replace_source(db: Session, batch_id: str, model, path: Path) -> int:
    count = 0
    with path.open("r", encoding=_detect_encoding(path), newline="") as stream:
        reader = csv.reader(stream, delimiter=";", strict=True)
        raw_headers = _read_row(reader, path, 1)
        if not raw_headers:
            raise HTTPException(422, f"{path.name}, ligne 1 : en-tête CSV manquant")
        headers = [h.strip() or f"colonne_{i}" for i, h in enumerate(raw_headers, start=1)]
        names = [header.casefold() for header in headers]
        if "affaire" not in names:
            raise HTTPException(422, f"{path.name}, ligne 1 : colonne Affaire manquante (séparateur attendu : ;)")
        if len(set(names)) != len(headers):
            raise HTTPException(422, f"{path.name}, ligne 1 : noms de colonnes en double")

        db.query(model).delete()
        while True:
            row_number = reader.line_num + 1
            values = _read_row(reader, path, row_number)
            if values is None:
                break
            if not values or not any(v.strip() for v in values):
                continue
            if len(values) != len(headers):
                raise HTTPException(422, f"{path.name}, ligne {row_number} : {len(values)} colonnes "
                                    f"au lieu de {len(headers)}")
            payload = {}
            for header, value in zip(headers, values):
                cleaned = value.strip()
                if DECIMAL_VALUE.fullmatch(cleaned):
                    cleaned = cleaned.replace(",", ".")
                payload[header] = cleaned
            db.add(model(batch_id=batch_id, row_number=row_number,
                         affaire=_affaire(payload), payload=json.dumps(payload, ensure_ascii=False)))
            count += 1
    db.flush()
    return count


def _read_row(reader, path: Path, row_number: int) -> list[str] | None:
    try:
        return next(reader, None)
    except csv.Error as exc:
        raise HTTPException(422, f"{path.name}, ligne {row_number} : format CSV invalide ({exc})") from exc
    except UnicodeError as exc:
        raise HTTPException(422, f"{path.name} : encodage illisible (UTF-8 ou Windows-1252 attendu)") from exc
