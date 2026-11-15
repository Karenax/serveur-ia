"""Liens réseau du projet, copié de XPilot (GET liste + PUT remplacement complet)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import REQUIRED_NETWORK_LINKS, NetworkLink, Project

router = APIRouter(prefix="/api/v1", tags=["network-links"])

REQUIRED_CODES = {code for code, _ in REQUIRED_NETWORK_LINKS}


class NetworkLinkUpsert(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    libelle: str = Field(min_length=1, max_length=255)
    chemin: str | None = Field(default=None, max_length=1024)


class NetworkLinksUpdate(BaseModel):
    liens: list[NetworkLinkUpsert]


class OpenPathRequest(BaseModel):
    path: str = Field(min_length=1, max_length=2048)


@router.post("/open-path")
def open_path(payload: OpenPathRequest, db: Session = Depends(get_db)):
    """Ouvre un dossier/fichier réseau dans l'Explorateur du PC local.

    Le navigateur bloque l'ouverture directe des chemins UNC : c'est le
    backend (qui tourne sur le PC) qui ouvre via l'OS.
    """
    import subprocess
    import sys

    p = payload.path.strip()
    if not p:
        raise HTTPException(400, "Chemin vide : renseigne un chemin réseau")
    from pathlib import Path
    import os
    from ..models import NetworkLink
    requested = Path(p).resolve()
    roots = [Path(value).resolve() for value in os.environ.get("AGENT_OPEN_ROOTS", "").split(os.pathsep) if value]
    for link in db.query(NetworkLink).all():
        if link.chemin:
            path = Path(link.chemin).resolve()
            roots.append(path if path.is_dir() else path.parent)
    if not roots or not any(requested.is_relative_to(root) for root in roots):
        raise HTTPException(403, "Chemin hors des dossiers réseau configurés")
    allowed = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg",
               ".pptx", ".dwg", ".dxf", ".step", ".stp", ".iges", ".igs", ".sldprt"}
    if not requested.exists():
        raise HTTPException(404, "Fichier ou dossier introuvable")
    if not requested.is_dir() and requested.suffix.lower() not in allowed:
        raise HTTPException(403, "Ce type de fichier ne peut pas être ouvert par Agent")
    p = str(requested)
    try:
        if sys.platform.startswith("win"):
            import os

            os.startfile(p)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception as exc:
        raise HTTPException(422, f"Ouverture impossible : {exc}")
    return {"opened": p}


def _ensure_required(db: Session, project_id: str) -> None:
    existing = {link.code for link in db.query(NetworkLink).filter_by(project_id=project_id).all()}
    for order, (code, libelle) in enumerate(REQUIRED_NETWORK_LINKS):
        if code not in existing:
            db.add(NetworkLink(project_id=project_id, code=code, libelle=libelle,
                               chemin=None, ordre=order))


def _read(db: Session, project_id: str) -> list[dict]:
    links = db.query(NetworkLink).filter_by(project_id=project_id).order_by(NetworkLink.ordre).all()
    result = [{"id": link.id, "code": link.code, "libelle": link.libelle,
             "chemin": link.chemin, "ordre": link.ordre,
             "required": link.code in REQUIRED_CODES} for link in links]
    # Legacy projects may not yet have their required links. Present editable
    # placeholders without changing their database on a GET, including readers.
    existing = {link.code for link in links}
    for order, (code, label) in enumerate(REQUIRED_NETWORK_LINKS):
        if code not in existing:
            result.append({'id': f'missing:{project_id}:{code}', 'code': code,
                           'libelle': label, 'chemin': None, 'ordre': order, 'required': True})
    return sorted(result, key=lambda link: link['ordre'])


@router.get("/projects/{project_id}/network-links")
def list_links(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    return _read(db, project_id)


@router.put("/projects/{project_id}/network-links")
def replace_links(project_id: str, payload: NetworkLinksUpdate, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Projet introuvable")
    codes = [link.code.strip() for link in payload.liens]
    if any(not code for code in codes):
        raise HTTPException(400, "Chaque lien doit avoir un code")
    if len(set(codes)) != len(codes):
        raise HTTPException(409, "Codes en double : chaque code doit être unique par projet")
    if missing := REQUIRED_CODES - set(codes):
        raise HTTPException(400, f"Liens obligatoires manquants : {', '.join(sorted(missing))}")
    existing = {}
    for row in db.query(NetworkLink).filter_by(project_id=project_id).order_by(NetworkLink.ordre, NetworkLink.id):
        existing.setdefault((row.code, row.chemin), []).append(row)
    for order, (code, link) in enumerate(zip(codes, payload.liens)):
        chemin = (link.chemin or "").strip() or None
        matches = existing.get((code, chemin))
        if matches:
            row = matches.pop(0)
        else:
            row = NetworkLink(project_id=project_id, code=code, chemin=chemin)
            db.add(row)
        row.libelle = link.libelle.strip()
        row.ordre = order
    for removed in existing.values():
        for row in removed:
            db.delete(row)
    db.commit()
    return _read(db, project_id)
