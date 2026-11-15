"""Dormant, additive project notes; imports neither seed nor install tables."""
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .project_identity_models import now, uid

DIGEST = "length(sha256)=64 AND sha256 NOT GLOB '*[^0-9a-f]*'"


class ProjectNote(Base):
    __tablename__ = 'project_notes'
    __table_args__ = (UniqueConstraint('project_id', 'id'), CheckConstraint('revision >= 1'),
                     CheckConstraint('length(title) BETWEEN 1 AND 255'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    title: Mapped[str] = mapped_column(String(255))
    plain_text: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer)
    current_version_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)
    updated_at: Mapped[object] = mapped_column(DateTime, default=now)


class NoteVersion(Base):
    __tablename__ = 'project_note_versions'
    __table_args__ = (UniqueConstraint('note_id', 'revision'), UniqueConstraint('project_id', 'command_id'),
                     ForeignKeyConstraint(['project_id', 'note_id'], ['project_notes.project_id', 'project_notes.id'],
                                          deferrable=True, initially='DEFERRED'),
                     CheckConstraint('revision >= 1'), CheckConstraint(DIGEST),
                     CheckConstraint("length(command_sha256)=64 AND command_sha256 NOT GLOB '*[^0-9a-f]*'"),
                     CheckConstraint('json_valid(snapshot)'), CheckConstraint('execution_blocked IN (0,1)'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    note_id: Mapped[str] = mapped_column(String(36), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    command_id: Mapped[str] = mapped_column(String(36))
    command_sha256: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(120))
    attachment_bindings: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    restored_version_id: Mapped[str | None] = mapped_column(String(36),
        ForeignKey('project_note_versions.id', deferrable=True, initially='DEFERRED'), nullable=True)
    execution_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('0'))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


class NoteAttachment(Base):
    __tablename__ = 'project_note_attachments'
    __table_args__ = (ForeignKeyConstraint(['project_id', 'note_id'], ['project_notes.project_id', 'project_notes.id'],
                                          deferrable=True, initially='DEFERRED'),
                     UniqueConstraint('storage_id'), UniqueConstraint('note_id', 'command_id'),
                     CheckConstraint(DIGEST), CheckConstraint('size_bytes BETWEEN 1 AND 5242880'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    note_id: Mapped[str] = mapped_column(String(36), index=True)
    storage_id: Mapped[str] = mapped_column(String(36))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    command_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


class NoteSourceImport(Base):
    """Immutable originals/provenance receipt, separate from editable versions."""
    __tablename__ = 'project_note_imports'
    __table_args__ = (ForeignKeyConstraint(['project_id', 'note_id'], ['project_notes.project_id', 'project_notes.id'],
                                          deferrable=True, initially='DEFERRED'),
                     UniqueConstraint('note_id'), UniqueConstraint('project_id', 'command_id'),
                     UniqueConstraint('storage_id'), CheckConstraint(DIGEST),
                     CheckConstraint('size_bytes BETWEEN 1 AND 54525952'),
                     CheckConstraint("length(snapshot_sha256)=64 AND snapshot_sha256 NOT GLOB '*[^0-9a-f]*'"),
                     CheckConstraint("length(command_sha256)=64 AND command_sha256 NOT GLOB '*[^0-9a-f]*'"),
                     CheckConstraint('json_valid(snapshot)'), CheckConstraint('execution_blocked IN (0,1)'),
                     CheckConstraint("source_kind IN ('xpilot_note','legacy_text_note','external_office')"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    note_id: Mapped[str] = mapped_column(String(36), index=True)
    command_id: Mapped[str] = mapped_column(String(36))
    command_sha256: Mapped[str] = mapped_column(String(64))
    source_kind: Mapped[str] = mapped_column(String(20))
    snapshot: Mapped[str] = mapped_column(Text)
    snapshot_sha256: Mapped[str] = mapped_column(String(64))
    storage_id: Mapped[str] = mapped_column(String(36))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[str] = mapped_column(String(120))
    version_bindings: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    attachment_bindings: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    execution_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('0'))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


NOTE_TABLES = tuple(model.__table__ for model in (ProjectNote, NoteVersion, NoteAttachment, NoteSourceImport))
