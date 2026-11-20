"""Version history of each operator's document search criteria."""
from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .project_identity_models import now, uid


class PersonalDocumentSearchVersion(Base):
    __tablename__ = 'personal_document_search_versions'
    __table_args__ = (
        UniqueConstraint('actor_id', 'revision'),
        CheckConstraint('revision >= 1'),
        CheckConstraint("length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)
