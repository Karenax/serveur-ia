"""Closed import commands and descriptive immutable source captures."""
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .project_note_schemas import NOTE_ATTACHMENT_BUDGET, Closed, Command

DIGEST = r'^[0-9a-f]{64}$'


def canonical_uuid(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError('UUID canonique requis')
    return value


class SourceDescriptor(Closed):
    kind: Literal['upload', 'project_link'] = 'upload'
    link_id: str | None = Field(default=None, min_length=1, max_length=36)
    relative_path: str = Field(default='', max_length=2048)

    @model_validator(mode='after')
    def bounded_origin(self):
        if self.kind == 'upload':
            if self.link_id is not None or self.relative_path:
                raise ValueError('Une sélection de fichiers ne porte pas de chemin serveur')
        elif self.link_id is None:
            raise ValueError('Lien du projet requis pour une acquisition réseau')
        if (self.relative_path.startswith(('/', '\\')) or ':' in self.relative_path
                or '\\' in self.relative_path or any(ord(char) < 32 for char in self.relative_path)
                or any(part in {'.', '..'} for part in self.relative_path.split('/'))):
            raise ValueError('Chemin relatif borné au lien du projet requis')
        return self


class NoteImportCommand(Command):
    planned_note_id: str = Field(pattern=r'^[0-9a-f-]{36}$')
    expected_preview_sha256: str = Field(pattern=DIGEST)
    mode: Literal['rich', 'plain'] = 'rich'
    source: SourceDescriptor = Field(default_factory=SourceDescriptor)

    @field_validator('planned_note_id')
    @classmethod
    def note_uuid(cls, value):
        return canonical_uuid(value)


class SourceVersionCapture(Closed):
    source_key: str = Field(min_length=1, max_length=64)
    source_actor: str | None = Field(default=None, max_length=500)
    note_version_id: str = Field(pattern=r'^[0-9a-f-]{36}$')
    content_sha256: str = Field(pattern=DIGEST)
    conversion_mode: Literal['html', 'rich', 'source_plain', 'explicit_plain', 'external']

    @field_validator('note_version_id')
    @classmethod
    def version_uuid(cls, value):
        return canonical_uuid(value)


class ImportedAttachmentCapture(Closed):
    id: str = Field(pattern=r'^[0-9a-f-]{36}$')
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(strict=True, ge=1, le=NOTE_ATTACHMENT_BUDGET)
    sha256: str = Field(pattern=DIGEST)
    source_path: str | None = Field(default=None, max_length=1024)

    @field_validator('id')
    @classmethod
    def attachment_uuid(cls, value):
        return canonical_uuid(value)


class NoteImportCapture(Closed):
    format: Literal['agent-note-source-import'] = 'agent-note-source-import'
    version: int = Field(default=1, strict=True, ge=1, le=1)
    id: str = Field(pattern=r'^[0-9a-f-]{36}$')
    project_id: str = Field(min_length=1, max_length=36)
    note_id: str = Field(pattern=r'^[0-9a-f-]{36}$')
    actor_id: str = Field(min_length=1, max_length=120)
    command_id: str = Field(pattern=r'^[0-9a-f-]{36}$')
    command: NoteImportCommand
    source_kind: Literal['xpilot_note', 'legacy_text_note', 'external_office']
    bundle_sha256: str = Field(pattern=DIGEST)
    bundle_size_bytes: int = Field(strict=True, ge=1, le=54525952)
    source_sha256: str = Field(pattern=DIGEST)
    source_metadata: dict[str, str] = Field(default_factory=dict, max_length=4)
    files: list[dict] = Field(min_length=1, max_length=200)
    versions: list[SourceVersionCapture] = Field(min_length=1, max_length=51)
    attachments: list[ImportedAttachmentCapture] = Field(default_factory=list, max_length=20)

    @field_validator('id', 'note_id', 'command_id')
    @classmethod
    def identity(cls, value):
        return canonical_uuid(value)

    @model_validator(mode='after')
    def consistent_capture(self):
        from .services.project_note_source_bundle import _inventory
        from .services.project_note_source_preview import _digest
        if self.command.command_id != self.command_id or self.command.planned_note_id != self.note_id:
            raise ValueError('Commande et capture d’import incompatibles')
        _inventory(self.files)
        if _digest(self.files) != self.source_sha256:
            raise ValueError('Empreinte de l’inventaire source incompatible')
        if (set(self.source_metadata) - {'created_by', 'updated_by', 'created_at', 'updated_at'}
                or any(len(value) > 500 for value in self.source_metadata.values())
                or len({item.note_version_id for item in self.versions}) != len(self.versions)
                or len({item.source_key for item in self.versions}) != len(self.versions)
                or len({item.id for item in self.attachments}) != len(self.attachments)
                or sum(item.size_bytes for item in self.attachments) > NOTE_ATTACHMENT_BUDGET):
            raise ValueError('Métadonnées source ou liaisons d’import incompatibles')
        if self.source_kind == 'external_office' and (self.attachments or len(self.versions) != 1):
            raise ValueError('Un document Office externe conserve une seule vue en consultation')
        expected_versions = {'current'}
        if self.source_kind == 'xpilot_note':
            expected_versions |= {item['relative_path'].split('/')[1] for item in self.files if item['kind'] == 'version'}
        if {item.source_key for item in self.versions} != expected_versions:
            raise ValueError('Toutes les versions source doivent être reliées à leur capture Agent')
        if any(item.source_actor is not None for item in self.versions if item.source_key != 'current'):
            raise ValueError('Un auteur historique absent des originaux ne peut pas être inventé')
        ordinary = {item['relative_path']: item for item in self.files if item['kind'] == 'attachment'}
        captured = {item.source_path: item for item in self.attachments if item.source_path is not None}
        if (len(captured) != sum(item.source_path is not None for item in self.attachments)
                or set(captured) != set(ordinary) or any((captured[name].sha256, captured[name].size_bytes) !=
                                               (item['sha256'], item['size_bytes']) for name, item in ordinary.items())):
            raise ValueError('Toutes les pièces originales doivent avoir une liaison exacte')
        return self
