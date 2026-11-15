"""Additive identity/team tables; importing this module never migrates a database."""
from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectReference(Base):
    __tablename__ = "project_references"
    __table_args__ = (UniqueConstraint("kind", "normalized_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    search_text: Mapped[str] = mapped_column(String(512), default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ProjectPerson(Base):
    __tablename__ = "project_people"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="")
    trigram: Mapped[str] = mapped_column(String(12), default="")
    normalized_email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    normalized_trigram: Mapped[str | None] = mapped_column(String(12), nullable=True, unique=True)
    search_text: Mapped[str] = mapped_column(String(512), default="")
    function: Mapped[str] = mapped_column(String(120), default="")
    service: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    agency_id: Mapped[str | None] = mapped_column(ForeignKey("project_references.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ProjectProfile(Base):
    """One extension per existing UUID, keeping every historical project cell intact."""
    __tablename__ = "project_profiles"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("project_references.id"), nullable=True)
    agency_id: Mapped[str | None] = mapped_column(ForeignKey("project_references.id"), nullable=True)
    business_unit_id: Mapped[str | None] = mapped_column(ForeignKey("project_references.id"), nullable=True)
    family_id: Mapped[str | None] = mapped_column(ForeignKey("project_references.id"), nullable=True)
    typology_id: Mapped[str | None] = mapped_column(ForeignKey("project_references.id"), nullable=True)
    responsible_id: Mapped[str | None] = mapped_column(ForeignKey("project_people.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    client_reference: Mapped[str] = mapped_column(String(120), default="")
    client_site: Mapped[str] = mapped_column(String(255), default="")
    client_contact: Mapped[str] = mapped_column(String(255), default="")
    equipment_number: Mapped[str] = mapped_column(String(120), default="")
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[str] = mapped_column(String(10), default="")
    planned_end_date: Mapped[str] = mapped_column(String(10), default="")
    actual_closure_date: Mapped[str] = mapped_column(String(10), default="")
    standby: Mapped[bool] = mapped_column(Boolean, default=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        Index("uq_active_project_person_role", "project_id", "person_id", "role", unique=True,
              sqlite_where=text("active = 1")),
        Index("uq_active_project_responsible", "project_id", unique=True,
              sqlite_where=text("active = 1 AND role = 'responsable_projet'")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("project_people.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[str] = mapped_column(String(10), default="")
    end_date: Mapped[str] = mapped_column(String(10), default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ProjectIdentityChange(Base):
    __tablename__ = "project_identity_changes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    previous: Mapped[dict] = mapped_column(JSON, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ProjectReferenceChange(Base):
    __tablename__ = "project_reference_changes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    entity_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    previous: Mapped[dict] = mapped_column(JSON, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


IDENTITY_TABLES = tuple(cls.__table__ for cls in (
    ProjectReference, ProjectPerson, ProjectProfile, ProjectMember, ProjectIdentityChange, ProjectReferenceChange))
