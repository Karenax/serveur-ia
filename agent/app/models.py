"""Project Brain - canonical domain models (docs/02_DOMAIN_MODEL.md)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def _uid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="active")
    customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_refs: Mapped[list] = mapped_column(JSON, default=list)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    name: Mapped[str] = mapped_column(String(256))
    company: Mapped[str | None] = mapped_column(String(256), nullable=True)
    emails: Mapped[list] = mapped_column(JSON, default=list)
    phones: Mapped[list] = mapped_column(JSON, default=list)
    roles: Mapped[dict] = mapped_column(JSON, default=dict)  # project_id -> role
    aliases: Mapped[list] = mapped_column(JSON, default=list)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32))  # email | phone | meeting | document
    status: Mapped[str] = mapped_column(String(32), default="resolution_pending")  # resolved | resolution_pending | rejected | discarded (hash-only)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    author: Mapped[str | None] = mapped_column(String(512), nullable=True)
    participants: Mapped[list] = mapped_column(JSON, default=list)
    original_uri: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    retention_policy: Mapped[str | None] = mapped_column(String(64), nullable=True)

    artifacts: Mapped[list["SourceArtifact"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    proposals: Mapped[list["Proposal"]] = relationship(back_populates="source")


class SourceArtifact(Base):
    __tablename__ = "source_artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("sources.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64))  # transcription | body_text | ocr | metadata | ...
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    source: Mapped[Source] = relationship(back_populates="artifacts")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    subject: Mapped[str] = mapped_column(String(512))
    value: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="validated")  # validated | superseded | invalidated
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criticality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    validated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_items.id"), nullable=True)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ProvenanceLink(Base):
    __tablename__ = "provenance_links"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    knowledge_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_items.id"), index=True)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("sources.id"), index=True)
    locator: Mapped[dict] = mapped_column(JSON, default=dict)
    excerpt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extraction_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Proposal(Base):
    __tablename__ = "proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    source_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sources.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(64))  # fact|decision|action|...|project_attach
    operation: Mapped[str] = mapped_column(String(32), default="propose_create")  # propose_create|propose_update|...
    subject: Mapped[str] = mapped_column(String(512))
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|accepted|rejected|deferred
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    source: Mapped[Source | None] = relationship(back_populates="proposals")


class ValidationDecision(Base):
    __tablename__ = "validation_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    proposal_id: Mapped[str] = mapped_column(String(36), ForeignKey("proposals.id"), index=True)
    decision: Mapped[str] = mapped_column(String(32))  # accept|reject|edit-and-accept|defer|conflict
    actor: Mapped[str] = mapped_column(String(128))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    resulting_knowledge_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MemoryDatasetMapping(Base):
    __tablename__ = "memory_dataset_mappings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(16))  # evidence | truth
    engine: Mapped[str] = mapped_column(String(32), default="eg2")
    dataset_name: Mapped[str] = mapped_column(String(256))
    engine_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "purpose", "engine", name="uq_proj_purpose_engine"),)


class MemoryProjection(Base):
    __tablename__ = "memory_projections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    knowledge_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(String(16))  # evidence | truth
    dataset_mapping_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    projection_version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(32), default="indexed")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class MailIdentity(Base):
    __tablename__ = "mail_identities"
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("sources.id"), index=True)


class ThunderbirdJob(Base):
    __tablename__ = "thunderbird_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class MeetingRecording(Base):
    """Audio workflow in the canonical store; ERP report is published explicitly."""
    __tablename__ = "meeting_recordings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    erp_project_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(255))
    date: Mapped[str] = mapped_column(String(32), default="")
    filename: Mapped[str] = mapped_column(String(255))
    num_speakers: Mapped[int] = mapped_column(default=0)
    segments: Mapped[list] = mapped_column(JSON, default=list)
    speaker_names: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(default=0)
    reviewed_revision: Mapped[int] = mapped_column(default=0)
    summary_revision: Mapped[int] = mapped_column(default=0)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_model: Mapped[str] = mapped_column(String(255), default="")
    published_meeting_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    job_kind: Mapped[str] = mapped_column(String(32), default="")
    job_status: Mapped[str] = mapped_column(String(32), default="idle", index=True)
    stage: Mapped[str] = mapped_column(String(64), default="uploaded")
    progress: Mapped[float] = mapped_column(Float, default=0)
    processed_seconds: Mapped[float] = mapped_column(Float, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
