"""Read-only destination/source preflight; no implicit L5 installation."""
from fastapi import HTTPException

from .project_document_migration import validate_document_schema


def require_schema(db):
    try:
        if any(validate_document_schema(db.connection()).values()):
            raise ValueError('Installation explicite des formulaires requise')
    except ValueError as exc:
        raise HTTPException(409, 'Schéma documentaire incomplet ou incompatible ; installer après sauvegarde') from exc
