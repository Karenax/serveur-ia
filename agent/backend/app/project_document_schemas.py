"""Project document commands cannot carry a filesystem policy or actor identity."""
from typing import Literal

from pydantic import Field

from .schemas import DomainInput

DocumentId = Literal['offer_lt_simple', 'tdao', 'tdsp', 'manufacturing_specification',
    'user_manual', 'ce_request', 'customer_satisfaction_product', 'customer_satisfaction_fixed_price']


class DocumentDiscover(DomainInput):
    document_id: DocumentId
    link_id: str = Field(min_length=1, max_length=36)


class DocumentPreview(DocumentDiscover):
    relative_path: str = Field(default='', max_length=2048)
    overrides: dict[str, str] = Field(default_factory=dict, max_length=19)


class DocumentPrepare(DocumentPreview):
    expected_source_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_link_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_values_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_identity_revision: int = Field(ge=0)
    expected_planning_revision: int = Field(ge=0)
