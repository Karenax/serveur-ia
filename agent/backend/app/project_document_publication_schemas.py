"""Explicit destination choices; no absolute paths, output names or caller actors."""
from typing import Literal

from pydantic import Field, StrictInt, StrictBool, field_validator

from .schemas import DomainInput
from .services.document_paths import _relative


class DocumentPublicationPreview(DomainInput):
    link_id: str = Field(min_length=1, max_length=36)
    relative_directory: str = Field(default='', max_length=2048)
    replace_existing: StrictBool = False

    @field_validator('relative_directory')
    @classmethod
    def normalized_directory(cls, value):
        return _relative(value)


class DocumentPublicationCommand(DocumentPublicationPreview):
    command_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,36}$')
    expected_revision: StrictInt = Field(ge=1)
    expected_preview_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    reviewed: Literal[True]

    @field_validator('reviewed', mode='before')
    @classmethod
    def explicit_review(cls, value):
        if value is not True:
            raise ValueError('Confirmer explicitement la relecture de la destination')
        return value


class DocumentPublicationAbandon(DomainInput):
    expected_revision: StrictInt = Field(ge=1)
    retain_files: Literal[True]
    reviewed: Literal[True]

    @field_validator('retain_files','reviewed',mode='before')
    @classmethod
    def explicit_acknowledgment(cls,value):
        if value is not True:
            raise ValueError('Confirmer la clôture en conservant tous les fichiers')
        return value
