"""Closed commands shared by the studio and durable session API."""
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.project_note_schemas import NoteContent


class Closed(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Command(Closed):
    command_id: str
    expected_revision: int = Field(ge=1)

    @field_validator('command_id')
    @classmethod
    def uuid(cls, value):
        if str(UUID(value)) != value:
            raise ValueError('UUID canonique requis')
        return value


class SessionCreate(Closed):
    command_id: str
    title: str = Field(min_length=1, max_length=255)
    kind: Literal['meeting', 'note', 'import'] = 'meeting'
    project_id: str | None = None
    date: str = ''

    _command = field_validator('command_id')(Command.uuid.__func__)

    @field_validator('date')
    @classmethod
    def iso_date(cls, value):
        if value and date.fromisoformat(value).isoformat() != value:
            raise ValueError('Date ISO requise')
        return value


class SessionAssign(Command):
    project_id: str


class BrowserCaptureReservation(Command):
    owner_id: str

    _owner = field_validator('owner_id')(Command.uuid.__func__)


class CaptureControl(Command):
    browser_capture_owner_id: str | None = None

    @field_validator('browser_capture_owner_id')
    @classmethod
    def owner_uuid(cls, value):
        return Command.uuid(value) if value is not None else None


class SessionNoteSave(Command):
    title: str = Field(min_length=1, max_length=255)
    content: NoteContent
    expected_note_revision: int | None = Field(default=None, ge=1)
    expected_note_version_id: str | None = None


class SessionSegmentEdit(Closed):
    command_id: str
    expected_session_revision: int = Field(ge=1)
    expected_segment_revision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=10000)
    speaker: str = Field(min_length=1, max_length=120)

    _command = field_validator('command_id')(Command.uuid.__func__)
