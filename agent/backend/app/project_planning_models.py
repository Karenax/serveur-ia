"""L2 additive planning tables; importing registers metadata, never migrates."""
from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc)


class PlanningTemplate(Base):
    __tablename__ = "project_planning_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    typology_id: Mapped[str | None] = mapped_column(ForeignKey("project_references.id"), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PlanningTemplateVersion(Base):
    __tablename__ = "project_planning_template_versions"
    __table_args__ = (UniqueConstraint("template_id", "number"), CheckConstraint("number >= 1"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    template_id: Mapped[str] = mapped_column(ForeignKey("project_planning_templates.id"), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)


class ProjectPlanningState(Base):
    __tablename__ = "project_planning_states"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_template_version_id: Mapped[str | None] = mapped_column(ForeignKey("project_planning_template_versions.id"), nullable=True)
    excluded_dates: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class MilestonePlan(Base):
    __tablename__ = "project_milestone_plans"
    __table_args__ = (UniqueConstraint("project_id", "code"), CheckConstraint("position IS NULL OR position >= 0"),
                     CheckConstraint("workflow_status IN ('pending','open','validated','blocked','skipped')"))
    milestone_id: Mapped[str] = mapped_column(ForeignKey("milestones.id"), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workflow_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TaskPlan(Base):
    __tablename__ = "project_task_plans"
    __table_args__ = (CheckConstraint("planned_hours >= 0 AND planned_hours <= 1000000"),
                     CheckConstraint("priority IN ('low','normal','high','urgent')"),
                     CheckConstraint("parent_task_id IS NULL OR parent_task_id != task_id"),
                     UniqueConstraint("project_id", "template_id", "template_key"),
                     CheckConstraint("(template_id IS NULL AND template_key IS NULL) OR "
                                     "(template_id IS NOT NULL AND template_key IS NOT NULL)"))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    parent_task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    milestone_id: Mapped[str | None] = mapped_column(ForeignKey("milestones.id"), nullable=True)
    responsible_id: Mapped[str | None] = mapped_column(ForeignKey("project_people.id"), nullable=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("project_planning_templates.id"), nullable=True)
    template_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    start_date: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    end_date: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    planned_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    design: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manufacturing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PlanningBaseline(Base):
    __tablename__ = "project_planning_baselines"
    __table_args__ = (CheckConstraint("kind IN ('initial','contractual','review','amendment')"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    planning_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)


class PlanningChange(Base):
    __tablename__ = "project_planning_changes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    previous: Mapped[dict] = mapped_column(JSON, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)


PLANNING_TABLES = tuple(model.__table__ for model in (
    PlanningTemplate, PlanningTemplateVersion, ProjectPlanningState, MilestonePlan, TaskPlan, PlanningBaseline, PlanningChange))
IMMUTABLE_TABLES = tuple(model.__tablename__ for model in (PlanningTemplateVersion, PlanningBaseline, PlanningChange))
