"""Additive document preferences/forms, with immutable saved versions.

Importing this module performs no DDL or seeding. Explicit installation and typed
archive integration precede runtime activation. Server actor IDs are not signatures.
"""
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .project_identity_models import now, uid
from .services.document_template_catalogue import DOCUMENT_IDS

DOCUMENT_ID_CHECK = 'document_id IN (' + ','.join(repr(value) for value in sorted(DOCUMENT_IDS)) + ')'
DIGEST_CHECK = "length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'"


class DocumentSearchVersion(Base):
    __tablename__ = 'project_document_search_versions'
    __table_args__ = (UniqueConstraint('revision'), UniqueConstraint('id', 'revision'),
                     CheckConstraint('revision >= 1'), CheckConstraint(DIGEST_CHECK))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


class DocumentSearchState(Base):
    __tablename__ = 'project_document_search_states'
    __table_args__ = (CheckConstraint("id = 'common' AND revision >= 1"),
                     ForeignKeyConstraint(['current_version_id', 'revision'],
                         ['project_document_search_versions.id', 'project_document_search_versions.revision']))
    id: Mapped[str] = mapped_column(String(16), primary_key=True, default='common')
    revision: Mapped[int] = mapped_column(Integer)
    current_version_id: Mapped[str] = mapped_column(String(36))
    updated_at: Mapped[object] = mapped_column(DateTime, default=now)


class ProjectDocumentDraft(Base):
    __tablename__ = 'project_document_drafts'
    __table_args__ = (UniqueConstraint('project_id', 'document_id'), UniqueConstraint('project_id', 'id', 'document_id'),
                     CheckConstraint('revision >= 1'), CheckConstraint(DOCUMENT_ID_CHECK))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    document_id: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer)
    # Historical link identities are retained even when a link becomes absent.
    # Commands validate the parent; history never cascades with a legacy link.
    link_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    relative_path: Mapped[str] = mapped_column(String(2048), default='')
    overrides: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    updated_at: Mapped[object] = mapped_column(DateTime, default=now)


class DocumentDraftVersion(Base):
    __tablename__ = 'project_document_draft_versions'
    __table_args__ = (UniqueConstraint('draft_id', 'revision'),
                     ForeignKeyConstraint(['project_id', 'draft_id', 'document_id'],
                         ['project_document_drafts.project_id', 'project_document_drafts.id', 'project_document_drafts.document_id']),
                     CheckConstraint('revision >= 1'), CheckConstraint(DOCUMENT_ID_CHECK), CheckConstraint(DIGEST_CHECK))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    draft_id: Mapped[str] = mapped_column(String(36), index=True)
    document_id: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    bindings: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    actor_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[object] = mapped_column(DateTime, default=now)


DOCUMENT_FORM_TABLES = tuple(model.__table__ for model in (
    DocumentSearchVersion, DocumentSearchState, ProjectDocumentDraft, DocumentDraftVersion))
DOCUMENT_FORM_PROJECT_TABLES = frozenset({'project_document_drafts', 'project_document_draft_versions'})
