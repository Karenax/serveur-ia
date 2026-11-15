"""Structured RLP inputs: human content is editable, provenance is server-owned."""
from typing import Literal

from pydantic import Field, model_validator

from .project_identity_schemas import RevisionCommand
from .schemas import DomainInput, IsoDate

ReviewSection = Literal['vigilance_points', 'expected_functions', 'initial_constraints', 'decisions', 'actions']


class ReviewParticipant(DomainInput):
    person_id: str | None = Field(default=None, min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=120)
    function: str = Field(default='', max_length=120)
    signature_required: bool = True


class ReviewItem(DomainInput):
    id: str = Field(min_length=1, max_length=36)
    section_code: ReviewSection
    text: str = Field(min_length=1, max_length=4000)
    reviewed: bool = False
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)
    owner: str = Field(default='', max_length=120)
    due_date: IsoDate = ''


class ReviewContent(DomainInput):
    meeting_date: IsoDate = ''
    location: str = Field(default='', max_length=255)
    notes: str = Field(default='', max_length=20000)
    milestone_id: str | None = Field(default=None, min_length=1, max_length=36)
    participants: list[ReviewParticipant] = Field(default_factory=list, max_length=50)
    items: list[ReviewItem] = Field(default_factory=list, max_length=300)
    deliverable_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def unique_values(self):
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError('Identifiants de points de revue dupliqués')
        people = [item.person_id for item in self.participants if item.person_id]
        if len(set(people)) != len(people):
            raise ValueError('Participants dupliqués')
        if (len(set(self.deliverable_ids)) != len(self.deliverable_ids)
                or any(not value or len(value) > 36 for value in self.deliverable_ids)):
            raise ValueError('Livrables invalides ou dupliqués')
        for item in self.items:
            if (len(set(item.evidence_ids)) != len(item.evidence_ids)
                    or any(not value or len(value) > 36 for value in item.evidence_ids)):
                raise ValueError('Preuves invalides ou dupliquées')
        return self


class ReviewCreate(RevisionCommand):
    type_code: Literal['rlp'] = 'rlp'
    content: ReviewContent = Field(default_factory=ReviewContent)


class ReviewCommand(RevisionCommand):
    expected_review_revision: int = Field(ge=1)


class ReviewSave(ReviewCommand):
    content: ReviewContent


class ReviewPublish(ReviewCommand):
    confirmed: Literal[True]


class RecordingImport(ReviewCommand):
    recording_id: str = Field(min_length=1, max_length=36)
    expected_recording_revision: int = Field(ge=1)
