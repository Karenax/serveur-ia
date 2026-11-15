"""Reviewed bounded batch commands; no roots, output paths or client actors."""
from pydantic import Field, StrictInt, model_validator
from .schemas import DomainInput
from .project_document_schemas import DocumentPrepare


class DocumentBatchItem(DocumentPrepare):
    expected_identity_revision: StrictInt = Field(ge=0)
    expected_planning_revision: StrictInt = Field(ge=0)
    expected_draft_revision: StrictInt = Field(default=0, ge=0)


class DocumentBatchSubmit(DomainInput):
    command_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,36}$')
    items: list[DocumentBatchItem] = Field(min_length=1, max_length=8)

    @model_validator(mode='after')
    def distinct_templates(self):
        if len({item.document_id for item in self.items}) != len(self.items):
            raise ValueError('Une seule sélection par trame dans un lot')
        return self


class DocumentJobCommand(DomainInput):
    expected_revision: StrictInt = Field(ge=1)
