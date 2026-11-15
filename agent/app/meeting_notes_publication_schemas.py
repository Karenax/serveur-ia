"""Explicit human publication with citations into an immutable Notes version."""
from datetime import date

from pydantic import Field, field_validator

from .meeting_session_schemas import Closed, Command


class NoteEvidence(Closed):
    text: str = Field(min_length=1, max_length=2000)
    block_index: int = Field(ge=0, le=499)
    quote: str = Field(min_length=1, max_length=1500)


class NoteAction(NoteEvidence):
    text: str = Field(min_length=1, max_length=255)
    owner: str = Field(default='', max_length=120)
    due_date: str = ''

    @field_validator('due_date')
    @classmethod
    def iso_date(cls, value):
        if value and date.fromisoformat(value).isoformat() != value:
            raise ValueError('Date ISO requise')
        return value


class NotesSummary(Closed):
    overview: str = Field(default='', max_length=12000)
    decisions: list[NoteEvidence] = Field(default_factory=list, max_length=100)
    actions: list[NoteAction] = Field(default_factory=list, max_length=100)
    open_points: list[NoteEvidence] = Field(default_factory=list, max_length=100)


class PublishNotes(Command):
    expected_note_revision: int = Field(ge=1)
    expected_note_version_id: str = Field(min_length=36, max_length=36)
    summary: NotesSummary
