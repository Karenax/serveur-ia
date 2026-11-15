"""Additive L4 reviews. Published content, PDFs and the audit remain immutable."""
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .project_identity_models import now, uid


class ProjectReview(Base):
    __tablename__ = 'project_reviews'
    __table_args__ = (UniqueConstraint('project_id', 'type_code', 'number'),
                     CheckConstraint('number >= 1 AND revision >= 1'),
                     CheckConstraint("status IN ('draft','published')"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    type_code: Mapped[str] = mapped_column(String(64), default='rlp')
    number: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default='draft')
    content: Mapped[dict] = mapped_column(JSON)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_review_id: Mapped[str | None] = mapped_column(ForeignKey('project_reviews.id'), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)
    updated_at: Mapped[object] = mapped_column(DateTime, default=now)


class ReviewPublication(Base):
    __tablename__ = 'project_review_publications'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    review_id: Mapped[str] = mapped_column(ForeignKey('project_reviews.id'), unique=True)
    snapshot: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    # Canonical base64 keeps all PDF bytes in coordinated SQLite backups, without
    # a mutable path or a second filesystem transaction during publication.
    pdf_base64: Mapped[str] = mapped_column(Text)
    pdf_sha256: Mapped[str] = mapped_column(String(64))
    # Restore bindings refer to current identities without changing captured
    # snapshot/PDF bytes. Flat ERP/Brain namespaces never form nested origins.
    bindings: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


class ReviewEvent(Base):
    __tablename__ = 'project_review_events'
    __table_args__ = (UniqueConstraint('project_id', 'planning_revision'),
                     CheckConstraint('planning_revision >= 1'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    review_id: Mapped[str] = mapped_column(ForeignKey('project_reviews.id'), index=True)
    planning_revision: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(120))
    previous: Mapped[dict] = mapped_column(JSON)
    value: Mapped[dict] = mapped_column(JSON)
    bindings: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


REVIEW_TABLES = tuple(model.__table__ for model in (ProjectReview, ReviewPublication, ReviewEvent))
