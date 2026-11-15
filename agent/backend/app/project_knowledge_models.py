"""Rebuildable dashboard analysis, independent of canonical planning and CDC."""
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, Integer, JSON, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class ProjectKnowledgeAnalysis(Base):
    __tablename__ = "project_knowledge_analyses"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    working: Mapped[dict] = mapped_column(JSON, default=dict)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_due: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
