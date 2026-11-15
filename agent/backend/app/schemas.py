"""Shared validation for desktop business commands."""
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, AfterValidator


def iso_date(value: str) -> str:
    if value:
        if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
            raise ValueError("Date attendue au format AAAA-MM-JJ")
    return value


IsoDate = Annotated[str, AfterValidator(iso_date)]


def project_code(value: str) -> str:
    # Keep ordinary industrial references and legacy values readable. Only new
    # commands are checked; no migration rewrites existing project references.
    if (len(value) > 64 or any(ord(char) < 32 for char in value)
            or any(char in value for char in '/\\:') or value in {'.', '..'}):
        raise ValueError('Référence projet de 64 caractères maximum, sans séparateur de chemin')
    return value


ProjectCode = Annotated[str, AfterValidator(project_code)]
TaskStatus = Literal["todo", "in_progress", "done", "cancelled"]
ProjectStatus = Literal["active", "paused", "done", "archived", "cancelled"]


class DomainInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", allow_inf_nan=False)
