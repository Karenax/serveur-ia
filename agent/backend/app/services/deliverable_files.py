"""Bounded file acquisition into managed storage and verified attachment reads.

Caller owns transactions. Failed acquisitions are retained, never purged.
Network acquisition accepts a project link plus a relative path, not a raw path.
"""
import hashlib
from pathlib import Path
import stat
import uuid

from fastapi import HTTPException

from ..db import APP_DIR
from ..models import DeliveryVersion
from . import project_deliverables as commands
from .deliverable_queries import _version, version_detail
from .document_file_access import acquire_file
from .planning_revision import revision
from .project_deliverable_rules import MAX_FILE_BYTES
from .project_identity import _project


def _preflight(db, project_id, deliverable_id, payload):
    _project(db, project_id, write=True)
    _, plan = commands._item(db, project_id, deliverable_id)
    if revision(db, project_id) != payload.expected_revision:
        raise HTTPException(409, 'Projet modifié : recharger avant publication')
    if plan and plan.document_status == 'archived':
        raise HTTPException(409, 'Rouvrir le livrable avant de publier')


def _filename(value):
    if (not isinstance(value, str) or not value or len(value) > 255 or value in {'.', '..'}
            or value != value.rstrip(' .') or any(ord(char) < 32 or char in '/\\:<>"|?*' for char in value)
            or value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                                               *(f'LPT{i}' for i in range(1, 10))}):
        raise HTTPException(422, 'Nom de fichier simple et valide requis')
    return value


def _destination(filename):
    base = APP_DIR.resolve()
    root = (base / 'deliverable-files').resolve()
    if not root.is_relative_to(base):
        raise HTTPException(409, 'Dossier de stockage hors de la base Agent')
    path = root / str(uuid.uuid4()) / _filename(filename)
    if not path.resolve().is_relative_to(root):
        raise HTTPException(409, 'Stockage de livrable incohérent')
    path.parent.mkdir(parents=True, exist_ok=False)
    return path


def _copy(stream, path):
    total = 0
    with path.open('xb') as output:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                raise HTTPException(413, 'Fichier de 50 Mio maximum requis')
            output.write(chunk)
    if total == 0:
        raise HTTPException(422, 'Le fichier est vide')


def publish_upload(db, project_id, deliverable_id, payload, *, filename, stream):
    _preflight(db, project_id, deliverable_id, payload)
    if payload.source_delivery_id:
        raise HTTPException(422, 'Utiliser la liaison CDC pour une livraison existante')
    try:
        path = _destination(filename)
        _copy(stream, path)
    except OSError as exc:
        raise HTTPException(409, 'Stockage indisponible ; aucun livrable publié') from exc
    return commands.publish_file(db, project_id, deliverable_id, payload, path=path)


def publish_network(db, project_id, deliverable_id, payload, *, link_id, relative_path):
    _preflight(db, project_id, deliverable_id, payload)
    if payload.source_delivery_id:
        raise HTTPException(422, 'Utiliser la liaison CDC pour une livraison existante')
    data, source = acquire_file(db, project_id, link_id=link_id, relative_path=relative_path)
    try:
        destination = _destination(source['filename'])
        with destination.open('xb') as stream:
            stream.write(data)
    except OSError as exc:
        raise HTTPException(409, 'Stockage indisponible ; aucun livrable publié') from exc
    return commands.publish_file(db, project_id, deliverable_id, payload, path=destination)


def _managed_path(value):
    from app.config import STORAGE_DIR
    try:
        path = Path(value).resolve()
        if not any(path.is_relative_to(root.resolve()) for root in (APP_DIR, STORAGE_DIR)):
            raise HTTPException(409, 'Fichier de version hors stockage géré ; restaurer sa copie')
        return path
    except (OSError, ValueError) as exc:
        raise HTTPException(409, 'Emplacement de version indisponible') from exc


def publish_cdc(db, project_id, deliverable_id, payload):
    _preflight(db, project_id, deliverable_id, payload)
    source = db.query(DeliveryVersion).filter_by(project_id=project_id, id=payload.source_delivery_id).first()
    if source is None:
        raise HTTPException(404, 'Livraison CDC introuvable dans ce projet')
    path = _managed_path(source.path)
    return commands.publish_file(db, project_id, deliverable_id, payload, path=path)


def download(db, project_id, deliverable_id, version_id):
    row, _ = _version(db, project_id, deliverable_id, version_id)
    version_detail(db, project_id, deliverable_id, version_id)
    path = _managed_path(commands.version_file_path(db, row))
    # Freeze the response bytes. A FileResponse would reopen the path after the
    # integrity check and could return a subsequently changed network file.
    try:
        with path.open('rb') as stream:
            import os
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise HTTPException(409, 'Fichier régulier requis')
            data = stream.read(MAX_FILE_BYTES + 1)
    except OSError as exc:
        raise HTTPException(409, 'Fichier indisponible ; conserver la version et rétablir sa copie') from exc
    if len(data) != row.size_bytes or hashlib.sha256(data).hexdigest() != row.sha256:
        raise HTTPException(409, 'Fichier modifié : restaurer la copie ou publier une nouvelle version')
    return data, _filename(row.filename)
