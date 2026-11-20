"""Private notes live in the backed-up ERP database, outside the project catalogue."""
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, JSON, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .project_note_schemas import NOTE_ATTACHMENT_BUDGET


class PersonalNote(Base):
    __tablename__ = 'personal_notes'
    __table_args__ = (Index('ix_personal_notes_owner_updated', 'owner_id', 'updated_at'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    plain_text: Mapped[str] = mapped_column(Text)
    revision: Mapped[int]
    current_version_id: Mapped[str] = mapped_column(String(36))
    updated_at: Mapped[datetime]


class PersonalNoteVersion(Base):
    __tablename__ = 'personal_note_versions'
    __table_args__ = (UniqueConstraint('note_id', 'revision'), UniqueConstraint('owner_id', 'command_id'))

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(120))
    note_id: Mapped[str] = mapped_column(ForeignKey('personal_notes.id'))
    revision: Mapped[int]
    command_id: Mapped[str] = mapped_column(String(36))
    command_digest: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[dict] = mapped_column(JSON)
    attachment_ids: Mapped[list] = mapped_column(JSON)
    operation: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime]


class PersonalNoteImage(Base):
    __tablename__ = 'personal_note_images'
    __table_args__ = (CheckConstraint(f'size_bytes BETWEEN 1 AND {NOTE_ATTACHMENT_BUDGET}'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    note_id: Mapped[str] = mapped_column(ForeignKey('personal_notes.id'), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
