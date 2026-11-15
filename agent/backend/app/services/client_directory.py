"""Provision private client directories alongside ERP project creation."""
from contextlib import contextmanager
import os

from fastapi import HTTPException
from sqlalchemy import func, select

from ..models import NetworkLink, REQUIRED_NETWORK_LINKS
from .document_file_access import configured_policy


@contextmanager
def client_directory(db, project_id):
    if os.environ.get("AGENT_DOCUMENT_PROJECT_ROOT", '""') == '""':
        yield
        return
    try:
        folder = configured_policy(project_id, write=True).project_directory
        configured_policy(project_id)
    except HTTPException as exc:
        raise HTTPException(503, "Configuration des dossiers clients invalide") from exc
    if folder is None:
        yield
        return
    try:
        if folder.parent.resolve(strict=True) != folder.parent:
            raise OSError("Redirection de la racine des dossiers clients")
        folder.mkdir()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(503, "Impossible de créer le dossier client sur le serveur") from exc
    try:
        code = "dossier_client_kiara"
        db.flush()
        query = select(NetworkLink).where(NetworkLink.project_id == project_id)
        links = db.scalars(query.where(NetworkLink.code == code)).all()
        if len(links) > 1:
            raise HTTPException(409, "Plusieurs liens désignent le dossier client")
        if links:
            links[0].chemin = str(folder)
        else:
            last = db.scalar(select(func.max(NetworkLink.ordre)).where(NetworkLink.project_id == project_id))
            order = max(last + 1 if last is not None else 0, len(REQUIRED_NETWORK_LINKS))
            db.add(NetworkLink(project_id=project_id, code=code, libelle="Dossier client Kiara",
                               chemin=str(folder), ordre=order))
        yield
    except BaseException:
        try:
            folder.rmdir()
        except OSError:
            pass  # Preserve any files the operator has already added.
        raise
