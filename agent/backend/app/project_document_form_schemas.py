"""Versioned form commands contain no roots, business writes or client actor."""
from pydantic import Field, StrictBool, StrictInt

from .project_document_schemas import DocumentId
from .schemas import DomainInput


class DocumentSearchItem(DomainInput):
    document_id: DocumentId
    label: str = Field(min_length=1, max_length=255)
    format: str = Field(pattern=r'^(DOCX|DOCM|XLSX|XLSM)$')
    relative_paths: list[str] = Field(max_length=16)
    filename_patterns: list[str] = Field(max_length=16)
    excluded_tokens: list[str] = Field(default_factory=list, max_length=16)
    preferred_version: StrictInt | None = Field(default=None, ge=0, le=999)
    active: StrictBool = True
    order: StrictInt = Field(ge=0, le=10000)


class DocumentSearchSave(DomainInput):
    expected_revision: StrictInt = Field(ge=0)
    items: list[DocumentSearchItem] = Field(min_length=8, max_length=8)


class DocumentDraftSave(DomainInput):
    expected_revision: StrictInt = Field(ge=0)
    link_id: str | None = Field(default=None, min_length=1, max_length=36)
    relative_path: str = Field(default='', max_length=2048)
    overrides: dict[str, str] = Field(default_factory=dict, max_length=19)


class DocumentFormRestore(DomainInput):
    expected_revision: StrictInt = Field(ge=0)
    version_id: str = Field(min_length=1, max_length=36)
