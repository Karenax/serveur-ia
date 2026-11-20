"""Closed rich note content and stable commands; no caller-supplied HTML/actor."""
import json
import re
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer, model_validator

NOTE_ATTACHMENT_BUDGET = 25 * 1024 * 1024
NoteBackground = Literal['yellow', 'green', 'blue', 'pink']


class Closed(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class TextRun(Closed):
    text: str = Field(max_length=5000)
    marks: list[Literal['bold', 'italic', 'underline', 'strike', 'code']] = Field(default_factory=list, max_length=5)
    href: str | None = Field(default=None, max_length=2048)
    color: str | None = Field(default=None, pattern=r'^#[0-9a-fA-F]{6}$')

    @field_validator('text')
    @classmethod
    def printable(cls, value):
        if any(ord(char) < 32 and char not in '\n\t' for char in value):
            raise ValueError('Caractère de contrôle interdit')
        return value

    @field_validator('marks')
    @classmethod
    def unique_marks(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('Style répété')
        return value

    @field_validator('href')
    @classmethod
    def safe_link(cls, value):
        if value is None:
            return value
        if re.search(r'[\s\x00-\x1f\\]', value):
            raise ValueError('Lien invalide')
        parsed = urlsplit(value)
        if parsed.scheme in {'http', 'https'} and parsed.hostname and not parsed.username and not parsed.password:
            return value
        if parsed.scheme == 'mailto' and re.fullmatch(r'[^?@]+@[^?@]+', parsed.path) and not parsed.query and not parsed.fragment:
            return value
        raise ValueError('Seuls les liens HTTP(S) ou mailto simples sont admis')


class Paragraph(Closed):
    type: Literal['paragraph']
    runs: list[TextRun] = Field(default_factory=list, max_length=500)
    align: Literal['left', 'center', 'right'] = 'left'


class Heading(Closed):
    type: Literal['heading']
    level: int = Field(ge=1, le=3)
    runs: list[TextRun] = Field(max_length=500)


class ListItem(Closed):
    runs: list[TextRun] = Field(default_factory=list, max_length=500)
    checked: bool = False
    indent: int = Field(default=0, ge=0, le=6)


class ListBlock(Closed):
    type: Literal['list']
    kind: Literal['bullet', 'ordered', 'checklist']
    items: list[ListItem] = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def checks_only_for_checklist(self):
        if self.kind != 'checklist' and any(item.checked for item in self.items):
            raise ValueError('Cases réservées à la liste à cocher')
        return self


Cell = Annotated[list[TextRun], Field(max_length=100)]
Row = Annotated[list[Cell], Field(min_length=1, max_length=20)]


class TableBlock(Closed):
    type: Literal['table']
    header: bool = True
    rows: list[Row] = Field(min_length=1, max_length=200)

    @model_validator(mode='after')
    def rectangular(self):
        if any(len(row) != len(self.rows[0]) for row in self.rows):
            raise ValueError('Tableau rectangulaire requis')
        return self


class ImageBlock(Closed):
    type: Literal['image']
    attachment_id: str = Field(pattern=r'^[0-9a-f-]{36}$')
    caption: str = Field(default='', max_length=1000)

    @field_validator('attachment_id')
    @classmethod
    def image_id(cls, value):
        return str(UUID(value))


Block = Annotated[Paragraph | Heading | ListBlock | TableBlock | ImageBlock, Field(discriminator='type')]


class NoteContent(Closed):
    version: Literal[1] = 1
    blocks: list[Block] = Field(default_factory=list, max_length=500)
    background: NoteBackground | None = None

    @model_serializer(mode='wrap')
    def keep_uncolored_format(self, serialize):
        value = serialize(self)
        if self.background is None:
            value.pop('background', None)
        return value

    @field_validator('version', mode='before')
    @classmethod
    def strict_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError('Version entière1requise')
        return value

    @model_validator(mode='after')
    def bounded(self):
        if len(json.dumps(self.model_dump(), ensure_ascii=False).encode('utf-8')) > 2_000_000:
            raise ValueError('Note limitée à 2 Mo de contenu structuré')
        return self


class Command(Closed):
    command_id: str = Field(pattern=r'^[0-9a-f-]{36}$')

    @field_validator('command_id')
    @classmethod
    def command_uuid(cls, value):
        return str(UUID(value))


class NoteCreate(Command):
    title: str = Field(min_length=1, max_length=255)
    content: NoteContent = Field(default_factory=NoteContent)

    @field_validator('title')
    @classmethod
    def title_text(cls, value):
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError('Titre non vide et sans contrôle requis')
        return value


class NoteSave(NoteCreate):
    expected_revision: int = Field(ge=1)
    attachment_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator('attachment_ids')
    @classmethod
    def attachment_uuids(cls, values):
        normalized = [str(UUID(value)) for value in values]
        if len(set(normalized)) != len(normalized):
            raise ValueError('Pièce jointe répétée')
        return normalized


class NoteDelete(Command):
    expected_revision: int = Field(ge=1)


class NoteRestore(NoteDelete):
    version_id: str = Field(pattern=r'^[0-9a-f-]{36}$')

    @field_validator('version_id')
    @classmethod
    def version_uuid(cls, value):
        return str(UUID(value))


class NotePaste(NoteSave):
    expected_revision: int = Field(ge=0)
    insert_at: int = Field(ge=0, le=499)

    @model_validator(mode='after')
    def valid_position(self):
        if self.insert_at > len(self.content.blocks) or len(self.content.blocks) >= 500:
            raise ValueError('La note ne dispose plus de place pour cette image')
        return self


def content_text(content: NoteContent):
    lines = []
    for block in content.blocks:
        if isinstance(block, (Paragraph, Heading)):
            lines.append(''.join(run.text for run in block.runs))
        elif isinstance(block, ListBlock):
            for item in block.items:
                prefix = ('[x] ' if item.checked else '[ ] ') if block.kind == 'checklist' else ''
                lines.append(prefix + ''.join(run.text for run in item.runs))
        elif isinstance(block, TableBlock):
            lines.extend('\t'.join(''.join(run.text for run in cell) for cell in row) for row in block.rows)
        elif isinstance(block, ImageBlock):
            lines.append(block.caption)
    return '\n'.join(lines)
