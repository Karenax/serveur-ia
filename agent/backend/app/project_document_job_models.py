"""Dormant additive document queue. Import creates neither tables nor workers."""
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .project_identity_models import now, uid
from .project_document_models import DIGEST_CHECK, DOCUMENT_ID_CHECK


class DocumentJob(Base):
    __tablename__ = 'project_document_jobs'
    __table_args__ = (UniqueConstraint('project_id', 'command_id'), UniqueConstraint('project_id', 'id'),
        CheckConstraint("status IN ('queued','running','completed','failed','cancelled','interrupted')"),
        CheckConstraint('revision >= 1 AND total BETWEEN 1 AND 8'), CheckConstraint(DIGEST_CHECK))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    command_id: Mapped[str] = mapped_column(String(36))
    snapshot: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(120))
    total: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default='queued')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('0'))
    execution_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('0'))
    active_attempt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=now)
    updated_at: Mapped[object] = mapped_column(DateTime, default=now)


class DocumentJobItem(Base):
    __tablename__ = 'project_document_job_items'
    __table_args__ = (ForeignKeyConstraint(['project_id', 'job_id'], ['project_document_jobs.project_id', 'project_document_jobs.id']),
        UniqueConstraint('project_id', 'job_id', 'id'), UniqueConstraint('job_id', 'position'), UniqueConstraint('job_id', 'document_id'),
        CheckConstraint('position BETWEEN 0 AND 7'), CheckConstraint(DOCUMENT_ID_CHECK), CheckConstraint(DIGEST_CHECK),
        CheckConstraint("status IN ('queued','running','succeeded','failed','cancelled','interrupted')"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    document_id: Mapped[str] = mapped_column(String(64))
    # Flat live bindings can be remapped without changing historical captures.
    # Like saved forms, retain a missing link identity without a cascade FK.
    link_id: Mapped[str] = mapped_column(String(36))
    draft_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default='queued')
    last_attempt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class DocumentJobAttempt(Base):
    __tablename__ = 'project_document_job_attempts'
    __table_args__ = (ForeignKeyConstraint(['project_id', 'job_id', 'item_id'],
        ['project_document_job_items.project_id', 'project_document_job_items.job_id', 'project_document_job_items.id']),
        UniqueConstraint('project_id', 'job_id', 'item_id', 'id'), UniqueConstraint('item_id', 'number'), CheckConstraint('number >= 1'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    item_id: Mapped[str] = mapped_column(String(36), index=True)
    number: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


class DocumentJobArtifact(Base):
    __tablename__ = 'project_document_job_artifacts'
    __table_args__ = (ForeignKeyConstraint(['project_id', 'job_id', 'item_id', 'attempt_id'],
        ['project_document_job_attempts.project_id', 'project_document_job_attempts.job_id', 'project_document_job_attempts.item_id', 'project_document_job_attempts.id']),
        UniqueConstraint('attempt_id'), UniqueConstraint('storage_key'), UniqueConstraint('project_id', 'attempt_id', 'id'),
        CheckConstraint(DIGEST_CHECK), CheckConstraint('size_bytes BETWEEN 1 AND 52428800'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    item_id: Mapped[str] = mapped_column(String(36))
    attempt_id: Mapped[str] = mapped_column(String(36))
    storage_key: Mapped[str] = mapped_column(String(80))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    provenance: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


class DocumentJobReceipt(Base):
    __tablename__ = 'project_document_job_receipts'
    __table_args__ = (ForeignKeyConstraint(['project_id', 'job_id', 'item_id', 'attempt_id'],
        ['project_document_job_attempts.project_id', 'project_document_job_attempts.job_id', 'project_document_job_attempts.item_id', 'project_document_job_attempts.id']),
        ForeignKeyConstraint(['project_id', 'attempt_id', 'artifact_id'],
        ['project_document_job_artifacts.project_id', 'project_document_job_artifacts.attempt_id', 'project_document_job_artifacts.id']),
        UniqueConstraint('attempt_id'), CheckConstraint("outcome IN ('succeeded','failed','interrupted')"),
        CheckConstraint("(outcome = 'succeeded' AND artifact_id IS NOT NULL AND error = '') OR (outcome != 'succeeded' AND artifact_id IS NULL)"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    item_id: Mapped[str] = mapped_column(String(36))
    attempt_id: Mapped[str] = mapped_column(String(36))
    artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16))
    error: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


class DocumentJobEvent(Base):
    __tablename__ = 'project_document_job_events'
    __table_args__ = (ForeignKeyConstraint(['project_id', 'job_id'], ['project_document_jobs.project_id', 'project_document_jobs.id']),
        UniqueConstraint('job_id', 'revision'), CheckConstraint('revision >= 1'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[str] = mapped_column(String(120))
    detail: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


DOCUMENT_JOB_TABLES = tuple(cls.__table__ for cls in (DocumentJob, DocumentJobItem, DocumentJobAttempt,
    DocumentJobArtifact, DocumentJobReceipt, DocumentJobEvent))
