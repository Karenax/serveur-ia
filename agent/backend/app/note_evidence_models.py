"""ERP outbox: appended in the note-version transaction, never network-bound."""
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .project_identity_models import now


class NoteEvidenceOutbox(Base):
    __tablename__ = 'note_evidence_outbox'
    __table_args__ = (UniqueConstraint('version_id'), CheckConstraint('revision >= 1 AND attempts >= 0'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    note_id: Mapped[str] = mapped_column(ForeignKey('project_notes.id'))
    version_id: Mapped[str] = mapped_column(ForeignKey('project_note_versions.id'))
    revision: Mapped[int] = mapped_column(Integer)
    digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default='pending', index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=now)
    received_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    retry_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
