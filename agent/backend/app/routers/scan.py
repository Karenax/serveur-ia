"""Import projet depuis un dossier réseau, copié de la logique TDAO/TDSP d'XPilot.

Le backend tourne sur le PC : il lit directement V:\\... (dossier affaire),
retrouve le TDAO / TDSP, et en extrait identité + budgets.
"""
from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CdcItem, NetworkLink, Project
from ..services.client_directory import client_directory
from ..services.document_file_access import _handle_path, _mapped, configured_policy, resolve_root

router = APIRouter(prefix="/api/v1", tags=["scan"])

CODE_RE = re.compile(r"[A-Z0-9]*LT[A-Z0-9-]*", re.IGNORECASE)
EXCEL_EXTS = {".xlsm", ".xlsx", ".xls"}

# Cellules d'identité reprises de XPilot (document_filling.DocumentSpec)
TDAO_CELLS = {"offer_number": "E6", "project_code": "E8", "description": "E10",
              "client_name": "K6", "client_requester": "K8",
              "client_responsible": "K10", "trigram": "E15"}
TDSP_CELLS = {"offer_number": "L22", "project_code": "E6", "description": "E8",
              "client_name": "K6", "client_requester": "K8",
              "client_responsible": "K10", "trigram": "E15"}
HOUR_CELLS = [
    ("J138", "Chiffrage BE"), ("K138", "Suivi d'étude"), ("L138", "Qualité"),
    ("M138", "Suivi étude (HR)"), ("N138", "3D"), ("O138", "2D"),
    ("P138", "VR"), ("Q138", "Calcul"), ("R138", "Supply"),
    ("S138", "Suivi étude automatisme"), ("T138", "Élec"), ("U138", "Suivi automatisme"),
    ("V138", "Chantier"), ("W138", "Montage méca"), ("X138", "Câblage"), ("Y138", "Essais"),
]


def parse_folder_name(name: str) -> tuple[str, str]:
    """'00 - AIRB26LTx0000-A - Description' -> (code, titre)."""
    parts = [p.strip() for p in name.split(" - ") if p.strip()]
    code = ""
    for part in parts:
        match = CODE_RE.search(part)
        if match and len(match.group(0)) >= 6:
            code = match.group(0)
            break
    if not code and len(parts) > 1:
        code = parts[1]
    elif not code and parts:
        code = parts[0]
    title_parts = [p for p in parts if code not in p]
    title = " - ".join(title_parts[1:] if title_parts and title_parts[0].isdigit() else title_parts)
    return code, title or name


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


PLACEHOLDER_RE = re.compile(r"^(a remplir\b|xxxx|^-+$|^/$)", re.IGNORECASE)


def _is_real(value: str) -> bool:
    """Ignore les valeurs factices des modèles vierges ('-', 'XXXX…', 'A remplir…')."""
    if not value:
        return False
    return PLACEHOLDER_RE.search(value) is None


def _clean_identity(raw: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in raw.items() if _is_real(value)}


def _as_number(value: object) -> float:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def find_docs(folder: Path) -> dict[str, str | None]:
    """Retrouve les fichiers TDAO / TDSP (profondeur max 3, comme XPilot)."""
    found: dict[str, str | None] = {"tdao": None, "tdsp": None}
    base_depth = len(folder.parts)
    for root, dirs, files in os.walk(folder):
        directory = Path(root)
        if not _canonical(directory):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not d.startswith((".", "~"))
                   and len(directory.parts) - base_depth < 3 and _canonical(directory / d)]
        for filename in files:
            lowered = filename.lower()
            if Path(filename).suffix.lower() not in EXCEL_EXTS:
                continue
            file = directory / filename
            if not _canonical(file) or not file.is_file():
                continue
            full = str(file)
            if "tdao" in lowered and found["tdao"] is None:
                found["tdao"] = full
            elif "tdsp" in lowered and found["tdsp"] is None:
                found["tdsp"] = full
        if found["tdao"] and found["tdsp"]:
            break
    return found


def _canonical(path):
    try:
        return path.resolve(strict=True) == path
    except (OSError, RuntimeError):
        return False


def _scan_path(value, *, project_id=None):
    policy = configured_policy(project_id)
    if not policy.roots:
        raise HTTPException(409, 'Renseignez les racines documentaires autorisées sur le serveur')
    candidate = _mapped(value, policy)
    roots = [Path(root) for root in policy.roots if candidate.is_relative_to(root)]
    if not roots:
        raise HTTPException(403, 'Chemin hors des racines documentaires autorisées')
    try:
        resolved = candidate.resolve(strict=True)
        if any(resolved.is_relative_to(resolve_root(root, policy)) for root in roots):
            return candidate, resolved
    except (OSError, RuntimeError) as exc:
        raise HTTPException(400, 'Dossier ou fichier indisponible') from exc
    raise HTTPException(403, 'Chemin hors des racines documentaires autorisées')


@contextmanager
def _open(path: str):
    from openpyxl import load_workbook

    expected = Path(path)
    with expected.open('rb') as stream:
        if _handle_path(stream) != expected:
            raise HTTPException(403, 'Emplacement du classeur modifié')
        workbook = load_workbook(stream, data_only=True, read_only=True)
        try:
            yield workbook
        finally:
            workbook.close()


def read_identity(path: str, kind: str) -> dict[str, str]:
    """Lit la page d'accueil TDAO ('Accueil') ou TDSP (\"Page d'Accueil\")."""
    cells = TDAO_CELLS if kind == "tdao" else TDSP_CELLS
    wanted = "page d'accueil" if kind == "tdsp" else "accueil"
    try:
        with _open(path) as workbook:
            sheet = next((ws for ws in workbook.worksheets if wanted in str(ws.title or '').lower()), None)
            if sheet is None:
                sheet = workbook.worksheets[0]
            return {key: _as_text(sheet[cell].value) for key, cell in cells.items()}
    except HTTPException:
        raise
    except Exception:
        return {}


def read_tdao_hours(path: str) -> dict[str, float]:
    """Lit les heures prévues TDAO, sans extraction financière."""
    lines: dict[str, float] = {}
    try:
        with _open(path) as workbook:
            for sheet in workbook.worksheets:
                try:
                    if _as_text(sheet["J135"].value) != "TOTAL HEURES PREVUES":
                        continue
                except Exception:
                    continue
                for cell, label in HOUR_CELLS:
                    try:
                        value = _as_number(sheet[cell].value)
                    except Exception:
                        continue
                    if value:
                        lines[label] = value
                break
    except HTTPException:
        raise
    except Exception:
        lines.clear()
    return {"budget_h": sum(lines.values(), 0.0), "lines": lines}


def scan_folder(folder: str) -> dict:
    configured, root = _scan_path(folder)
    if not root.exists() or not root.is_dir():
        raise HTTPException(400, f"Dossier introuvable ou inaccessible : {folder}")
    code, title = parse_folder_name(configured.name)
    docs = find_docs(root)
    identity: dict[str, str] = {}
    hours: dict[str, float] = {"budget_h": 0.0}
    folder_code = code if CODE_RE.fullmatch(code) else ""
    warnings = []
    tdao_compatible = True

    def compatible(values, kind):
        document_code = values.get("project_code", "")
        if folder_code and document_code and document_code.casefold() != folder_code.casefold():
            warnings.append(f"{kind.upper()} : code {document_code} différent du dossier {folder_code}. "
                            "Son identité et ses heures ne sont pas reprises automatiquement.")
            return False
        return True

    if docs["tdao"]:
        raw = _clean_identity(read_identity(docs["tdao"], "tdao")) or {}
        tdao_compatible = compatible(raw, "tdao")
        if tdao_compatible:
            identity = raw
            hours = read_tdao_hours(docs["tdao"])
    if docs["tdsp"]:
        tdsp_identity = _clean_identity(read_identity(docs["tdsp"], "tdsp")) or {}
        if compatible(tdsp_identity, "tdsp"):
            for key, value in tdsp_identity.items():
                if not identity.get(key):
                    identity[key] = value
    return {
        "folder": str(configured),
        "code": folder_code or identity.get("project_code") or code,
        "title": title if folder_code else identity.get("description") or title,
        "client_name": identity.get("client_name", ""),
        "offer_number": identity.get("offer_number", ""),
        "trigram": identity.get("trigram", ""),
        "tdao_file": str(configured / Path(docs["tdao"]).relative_to(root)) if docs["tdao"] else None,
        "tdsp_file": str(configured / Path(docs["tdsp"]).relative_to(root)) if docs["tdsp"] else None,
        "warnings": warnings,
        "tdao_compatible": tdao_compatible,
        **hours,
    }


class ScanRequest(BaseModel):
    folder: str = Field(min_length=1)


class ImportRequest(BaseModel):
    folder: str = Field(min_length=1)
    code: str | None = None
    title: str | None = None


def _seed_budget_values(db: Session, project_id: str, tdao_file: str | None, lines) -> int:
    """Crée les lignes de charge de travail depuis les heures TDAO.

    Idempotent : les lignes 'Budget TDAO – …' existantes ne sont pas dupliquées.
    """
    if not tdao_file or not lines:
        return 0
    existing = {item.normalized_wording for item in db.query(CdcItem).filter_by(project_id=project_id).all()}
    created = 0
    short = Path(tdao_file).name
    for label, value in lines.items():
        wording = f"Budget TDAO – {label}"
        if wording in existing:
            continue
        db.add(CdcItem(
            project_id=project_id, kind="data", title=wording,
            normalized_wording=wording,
            source_quote=f"TDAO {short} : {value} h ({label})",
            physical_page=1, modality="information", priority="p2",
            confidence=0.9, estimated_hours=float(value),
        ))
        created += 1
    return created


@router.post("/projects/scan")
def scan(payload: ScanRequest):
    return scan_folder(payload.folder.strip())


@router.post("/projects/import", status_code=201)
def import_project(payload: ImportRequest, db: Session = Depends(get_db)):
    preview = scan_folder(payload.folder.strip())
    code = (payload.code or preview["code"]).strip()
    title = (payload.title or preview["title"]).strip()
    if not code or not title:
        raise HTTPException(400, "Code et titre requis (non détectés dans le dossier)")
    exists = db.query(Project).filter_by(code=code).first()
    if exists:
        raise HTTPException(409, f"Un projet '{code}' existe déjà")
    project = Project(
        code=code, title=title, status="active",
        client_name=preview["client_name"], offer_number=preview["offer_number"],
        tdao_budget_h=preview["budget_h"],
    )
    db.add(project)
    db.flush()
    from ..services.milestones import seed
    seed(db, project.id)
    links = [("affaire", "Dossier Affaire", preview["folder"])]
    if preview["tdao_file"]:
        links.append(("dernier_tdao", "TDAO", preview["tdao_file"]))
    if preview["tdsp_file"]:
        links.append(("dernier_tdsp", "TDSP", preview["tdsp_file"]))
    for order, (link_code, libelle, chemin) in enumerate(links):
        db.add(NetworkLink(project_id=project.id, code=link_code, libelle=libelle,
                           chemin=chemin, ordre=order))
    budget_lines = _seed_budget_values(db, project.id, preview["tdao_file"], preview.get("lines", {}))
    with client_directory(db, project.id):
        db.commit()
    db.refresh(project)
    return {"id": project.id, "code": project.code, "title": project.title,
            "client_name": project.client_name, "budget_lines": budget_lines,
            "preview": preview}


@router.post("/projects/{project_id}/budgets-from-tdao")
def budgets_from_tdao(project_id: str, db: Session = Depends(get_db)):
    """(Re)charge les heures prévues depuis le TDAO lié."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projet introuvable")
    link = db.query(NetworkLink).filter_by(project_id=project_id, code="dernier_tdao").first()
    if not link or not (link.chemin or "").strip():
        raise HTTPException(400, "Aucun lien 'dernier_tdao' renseigné (onglet Documents)")
    _, path = _scan_path(link.chemin.strip(), project_id=project_id)
    created = _seed_budget_values(db, project_id, str(path), read_tdao_hours(str(path))["lines"])
    if not created:
        raise HTTPException(400, "Aucune ligne budgétaire trouvée dans le TDAO (ou déjà chargées)")
    db.commit()
    return {"created": created}
