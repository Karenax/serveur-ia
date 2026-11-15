"""Additive L3 records installed explicitly at Agent startup.

Legacy deliverables and CDC delivery_versions remain the original identities.
"""
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .project_identity_models import now, uid


class DeliverableType(Base):
    __tablename__ = 'project_deliverable_types'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class DeliverableTypeVersion(Base):
    __tablename__ = 'project_deliverable_type_versions'
    __table_args__ = (UniqueConstraint('type_id', 'number'), CheckConstraint('number >= 1'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    type_id: Mapped[str] = mapped_column(ForeignKey('project_deliverable_types.id'), index=True)
    number: Mapped[int] = mapped_column(Integer)
    definition: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


class DeliverableTypologyType(Base):
    __tablename__ = 'project_deliverable_typology_types'
    __table_args__ = (UniqueConstraint('typology_id', 'type_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    typology_id: Mapped[str] = mapped_column(ForeignKey('project_references.id'), index=True)
    type_id: Mapped[str] = mapped_column(ForeignKey('project_deliverable_types.id'), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DeliverablePlan(Base):
    __tablename__ = 'project_deliverable_plans'
    __table_args__ = (CheckConstraint("document_status IN ('draft','to_verify','validated','to_revise','archived')"),)
    deliverable_id: Mapped[str] = mapped_column(ForeignKey('deliverables.id'), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    type_version_id: Mapped[str | None] = mapped_column(ForeignKey('project_deliverable_type_versions.id'), nullable=True)
    responsible_id: Mapped[str | None] = mapped_column(ForeignKey('project_people.id'), nullable=True)
    verifier_id: Mapped[str | None] = mapped_column(ForeignKey('project_people.id'), nullable=True)
    document_status: Mapped[str] = mapped_column(String(32), default='draft')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    comment: Mapped[str] = mapped_column(Text, default='')
    position: Mapped[int] = mapped_column(Integer, default=0)


class DeliverableMilestone(Base):
    __tablename__ = 'project_deliverable_milestones'
    __table_args__ = (UniqueConstraint('deliverable_id', 'milestone_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    deliverable_id: Mapped[str] = mapped_column(ForeignKey('deliverables.id'), index=True)
    milestone_id: Mapped[str] = mapped_column(ForeignKey('milestones.id'), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DeliverableFileVersion(Base):
    __tablename__ = 'project_deliverable_file_versions'
    __table_args__ = (UniqueConstraint('deliverable_id', 'number'), CheckConstraint('number >= 1'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    deliverable_id: Mapped[str] = mapped_column(ForeignKey('deliverables.id'), index=True)
    source_delivery_id: Mapped[str | None] = mapped_column(ForeignKey('delivery_versions.id'), nullable=True, unique=True)
    number: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[str] = mapped_column(Text)
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    generated: Mapped[bool] = mapped_column(Boolean, default=False)
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


class DeliverableVersionMetadata(Base):
    __tablename__ = 'project_deliverable_version_metadata'
    version_id: Mapped[str] = mapped_column(ForeignKey('project_deliverable_file_versions.id'), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    reference: Mapped[str] = mapped_column(String(120))
    comment: Mapped[str] = mapped_column(Text, default='')
    storage_path: Mapped[str] = mapped_column(Text, default='', server_default=text("''"))


class DeliverableChecklistItem(Base):
    __tablename__ = 'project_deliverable_checklist'
    __table_args__ = (UniqueConstraint('deliverable_id', 'code', 'scope_key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    deliverable_id: Mapped[str] = mapped_column(ForeignKey('deliverables.id'), index=True)
    code: Mapped[str] = mapped_column(String(64))
    scope_key: Mapped[str] = mapped_column(String(64), default='')
    milestone_id: Mapped[str | None] = mapped_column(ForeignKey('milestones.id'), nullable=True)
    label: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    transverse: Mapped[bool] = mapped_column(Boolean, default=False)
    contributes: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_version_id: Mapped[str | None] = mapped_column(ForeignKey('project_deliverable_file_versions.id'), nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    comment: Mapped[str] = mapped_column(Text, default='')
    proof: Mapped[str] = mapped_column(Text, default='')


class DeliverableEvent(Base):
    __tablename__ = 'project_deliverable_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    deliverable_id: Mapped[str] = mapped_column(ForeignKey('deliverables.id'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(120))
    previous: Mapped[dict] = mapped_column(JSON, default=dict)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


DELIVERABLE_TABLES = tuple(model.__table__ for model in (
    DeliverableType, DeliverableTypeVersion, DeliverableTypologyType, DeliverablePlan,
    DeliverableMilestone, DeliverableFileVersion, DeliverableVersionMetadata, DeliverableChecklistItem, DeliverableEvent))
IMMUTABLE_TABLES = (DeliverableTypeVersion.__tablename__, DeliverableFileVersion.__tablename__, DeliverableEvent.__tablename__)
