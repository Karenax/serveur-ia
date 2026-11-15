"""Durable capture/staging. Imports never install schemas or start workers."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class MeetingSession(Base):
    __tablename__ = 'meeting_sessions'
    __table_args__ = (CheckConstraint('revision >= 1'),
                     CheckConstraint("kind IN ('meeting','note','import')"),
                     CheckConstraint("state IN ('created','recording','paused','finalizing','completed','interrupted','cancelled')"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16), default='meeting')
    date: Mapped[str] = mapped_column(String(10), default='')
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    brain_project_id: Mapped[str | None] = mapped_column(ForeignKey('projects.id'), nullable=True)
    operator_id: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(16), default='created')
    revision: Mapped[int] = mapped_column(Integer, default=1)
    recording_id: Mapped[str | None] = mapped_column(ForeignKey('meeting_recordings.id'), nullable=True)
    note_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    staged_note: Mapped[dict] = mapped_column(JSON, default=dict)
    pending_command_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MeetingAudioChunk(Base):
    __tablename__ = 'meeting_session_chunks'
    __table_args__ = (UniqueConstraint('session_id', 'track', 'sequence'),
                     CheckConstraint('sequence >= 0 AND size_bytes > 0 AND start_ms >= 0 AND duration_ms >= 0'),
                     CheckConstraint("track IN ('mic','system')"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey('meeting_sessions.id'), index=True)
    track: Mapped[str] = mapped_column(String(12))
    sequence: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    storage_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    start_ms: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    speech_status: Mapped[str] = mapped_column(String(16), default='pending')
    speech_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LiveTranscriptSegment(Base):
    __tablename__ = 'meeting_live_segments'
    __table_args__ = (CheckConstraint('start_ms >= 0 AND end_ms >= start_ms AND revision >= 1'),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('meeting_sessions.id'), index=True)
    chunk_id: Mapped[str | None] = mapped_column(ForeignKey('meeting_session_chunks.id'), nullable=True)
    track: Mapped[str] = mapped_column(String(12))
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    speaker: Mapped[str] = mapped_column(String(120), default='UNKNOWN')
    text: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    finalized: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MeetingSessionEvent(Base):
    __tablename__ = 'meeting_session_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('meeting_sessions.id'), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MeetingSessionCommand(Base):
    __tablename__ = 'meeting_session_commands'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('meeting_sessions.id'), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    operator_id: Mapped[str] = mapped_column(String(120))
    digest: Mapped[str] = mapped_column(String(64))
    body: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default='prepared')
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class StagedSessionNoteVersion(Base):
    __tablename__ = 'meeting_staged_note_versions'
    __table_args__ = (UniqueConstraint('session_id', 'revision'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    session_id: Mapped[str] = mapped_column(ForeignKey('meeting_sessions.id'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[dict] = mapped_column(JSON)
    plain_text: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    operator_id: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class NoteEvidenceBinding(Base):
    __tablename__ = 'note_evidence_bindings'
    __table_args__ = (UniqueConstraint('erp_project_id', 'note_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    erp_project_id: Mapped[str] = mapped_column(String(36))
    note_id: Mapped[str] = mapped_column(String(36))
    brain_project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'))
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    version_id: Mapped[str] = mapped_column(String(36))
    revision: Mapped[int] = mapped_column(Integer)


class NoteEvidenceReceipt(Base):
    __tablename__ = 'note_evidence_receipts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    digest: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str | None] = mapped_column(ForeignKey('sources.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


SESSION_TABLES = tuple(model.__table__ for model in (MeetingSession, MeetingAudioChunk,
    LiveTranscriptSegment, MeetingSessionEvent, MeetingSessionCommand, StagedSessionNoteVersion,
    NoteEvidenceBinding, NoteEvidenceReceipt))
