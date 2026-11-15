"""Additive import identities and immutable versions in the existing Brain DB."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now():
    return datetime.now(timezone.utc)


class LibraryItem(Base):
    __tablename__ = "foresight_library_items"
    __table_args__ = (UniqueConstraint("project_id", "provider", "provider_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    provider_key: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(255))
    current_source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    labels: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class LibraryVersion(Base):
    __tablename__ = "foresight_library_versions"
    __table_args__ = (UniqueConstraint("item_id", "content_sha256"), UniqueConstraint("source_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("foresight_library_items.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    content_sha256: Mapped[str] = mapped_column(String(64))
    provider_version: Mapped[str] = mapped_column(String(255), default="")
    size_bytes: Mapped[int] = mapped_column()
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


LIBRARY_TABLES = (LibraryItem.__table__, LibraryVersion.__table__)
