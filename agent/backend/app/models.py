"""Modèles Projet (+ CDC matrice fonctions/contraintes, copié de XPilot, simplifié)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    code: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    hourly_rate: Mapped[float] = mapped_column(Float, default=85)
    margin_pct: Mapped[float] = mapped_column(Float, default=10)
    client_name: Mapped[str] = mapped_column(String(255), default="")
    offer_number: Mapped[str] = mapped_column(String(64), default="")
    tdao_prix_vente: Mapped[float] = mapped_column(Float, default=0)
    tdao_budget_h: Mapped[float] = mapped_column(Float, default=0)
    remaining_hours: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class KiaraProjectMemory(Base):
    __tablename__ = 'kiara_project_memories'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    operator_id: Mapped[str] = mapped_column(String(128), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    text: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(default=1)
    updated: Mapped[float] = mapped_column(Float)


class KiaraConversation(Base):
    __tablename__ = 'kiara_conversations'
    operator_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(120))
    messages: Mapped[list] = mapped_column(JSON)
    archived: Mapped[bool] = mapped_column(default=False)
    revision: Mapped[int] = mapped_column(default=1)
    updated: Mapped[float] = mapped_column(Float)


class CdcSource(Base):
    """Copié de XPilot : registre des sources CDC versionnées.

    Étendu (moteur CDC repris de XPilot) : chemin du fichier stocké, texte
    extrait page par page, qualité et besoin de revue visuelle.
    """

    __tablename__ = "cdc_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), default="")
    revision: Mapped[str] = mapped_column(String(16), default="R1")
    status: Mapped[str] = mapped_column(String(32), default="ready")
    pages: Mapped[int] = mapped_column(Integer, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True, default=None)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    page_rows: Mapped[list["CdcSourcePage"]] = relationship(
        back_populates="source", cascade="all, delete-orphan")


REQUIRED_NETWORK_LINKS = (
    ("offre", "Offre"),
    ("dernier_tdao", "Dernier TDAO"),
    ("dernier_tdsp", "Dernier TDSP"),
)


class NetworkLink(Base):
    """Copié de XPilot (projet_liens_reseau) : chemins réseau du projet, code unique par projet."""

    __tablename__ = "network_links"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    chemin: Mapped[str | None] = mapped_column(String(1024), nullable=True, default=None)
    ordre: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Meeting(Base):
    """Compte rendu de réunion : décisions + actions, les actions deviennent des tâches."""

    __tablename__ = "meetings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    date: Mapped[str] = mapped_column(String(32), default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    participants: Mapped[str] = mapped_column(Text, default="")
    decisions: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class MeetingAction(Base):
    __tablename__ = "meeting_actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), default="")
    due_date: Mapped[str] = mapped_column(String(32), default="")
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)


class SageBatch(Base):
    """Copié d'XPilot (sage_import_batches) : un import = un lot horodaté."""

    __tablename__ = "sage_batches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    status: Mapped[str] = mapped_column(String(16), default="running")
    root_path: Mapped[str] = mapped_column(String(1024), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    sources: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")


class SageConfig(Base):
    __tablename__ = "sage_config"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    root_path: Mapped[str] = mapped_column(String(1024), default="")


class BrainLink(Base):
    """Pont vers Project Brain (cœur de connaissance, service :8002).

    MiniPilot ne duplique jamais la vérité : seul le mapping est stocké ici,
    la connaissance reste lue via REST Project Brain.
    """

    __tablename__ = "brain_links"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    brain_project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    brain_code: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))


class SageRow(Base):
    """Ligne snapshot Sage : code affaire + payload JSON brut (copié d'XPilot)."""

    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, default=0)
    affaire: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    payload: Mapped[str] = mapped_column(Text, default="{}")


class SageAchat(SageRow):
    __tablename__ = "sage_achats"


class SagePointage(SageRow):
    __tablename__ = "sage_pointages"


class BomLine(Base):
    """Ligne de nomenclature manuelle (version atelier du BOM XPilot)."""

    __tablename__ = "bom_lines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    reference: Mapped[str] = mapped_column(String(128), default="")
    designation: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    supplier: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="todo")
    position: Mapped[int] = mapped_column(Integer, default=0)


class TimeEntry(Base):
    """Saisie manuelle d'heures (complète les pointages Sage)."""

    __tablename__ = "time_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    person: Mapped[str] = mapped_column(String(120), nullable=False)
    date: Mapped[str] = mapped_column(String(32), default="")
    hours: Mapped[float] = mapped_column(Float, default=0)
    label: Mapped[str] = mapped_column(String(255), default="")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="todo")
    due_date: Mapped[str] = mapped_column(String(32), default="")


class Deliverable(Base):
    __tablename__ = "deliverables"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="todo")


class Milestone(Base):
    __tablename__ = "milestones"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[str] = mapped_column(String(32), default="")
    contractual_date: Mapped[str] = mapped_column(String(32), default="")
    forecast_date: Mapped[str] = mapped_column(String(32), default="")
    actual_date: Mapped[str] = mapped_column(String(32), default="")
    date_sources: Mapped[dict] = mapped_column(JSON, default=dict)


class MilestoneCandidate(Base):
    """A dated assertion with its evidence, never a silent contractual change."""
    __tablename__ = "milestone_candidates"
    __table_args__ = (UniqueConstraint("project_id", "fingerprint", name="uq_milestone_candidate"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    date_type: Mapped[str] = mapped_column(String(32))
    value: Mapped[str] = mapped_column(String(32))
    quote: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    fingerprint: Mapped[str] = mapped_column(String(64))
    base_value: Mapped[str] = mapped_column(String(32), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class MilestoneChange(Base):
    __tablename__ = "milestone_changes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    milestone_id: Mapped[str] = mapped_column(ForeignKey("milestones.id"), index=True)
    field: Mapped[str] = mapped_column(String(32))
    previous: Mapped[str] = mapped_column(String(255), default="")
    value: Mapped[str] = mapped_column(String(255), default="")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class MilestoneInput(Base):
    """Incremental processing ledger, including failed inputs for retry."""
    __tablename__ = "milestone_inputs"
    __table_args__ = (UniqueConstraint("project_id", "input_key", name="uq_milestone_input"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    input_key: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="completed")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class MilestoneScanJob(Base):
    __tablename__ = "milestone_scan_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    processed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    proposed: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CdcSourcePage(Base):
    """Texte extrait page par page (XPilot `CdcSourcePage`) : ancre de citation."""

    __tablename__ = "cdc_source_pages"
    __table_args__ = (UniqueConstraint("source_id", "physical_page", name="uq_cdc_page"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    source_id: Mapped[str] = mapped_column(ForeignKey("cdc_sources.id", ondelete="CASCADE"),
                                          nullable=False, index=True)
    physical_page: Mapped[int] = mapped_column(Integer, nullable=False)
    printed_page: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    character_count: Mapped[int] = mapped_column(Integer, default=0)
    extraction_quality: Mapped[float] = mapped_column(Float, default=0.0)
    visual_review_required: Mapped[bool] = mapped_column(Integer, default=0)

    source: Mapped[CdcSource] = relationship(back_populates="page_rows")


class CdcEvidenceAnchor(Base):
    """Preuve mot-pour-mot d'un élément CDC (XPilot `CdcEvidenceAnchor`)."""

    __tablename__ = "cdc_evidence_anchors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    item_id: Mapped[str] = mapped_column(ForeignKey("cdc_items.id", ondelete="CASCADE"),
                                         nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_page_id: Mapped[str] = mapped_column(String(36), nullable=False)
    physical_page: Mapped[int] = mapped_column(Integer, nullable=False)
    locator: Mapped[str] = mapped_column(String(255), default="")
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    visually_verified: Mapped[bool] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CdcCheck(Base):
    """Contrôle déterministe post-génération (XPilot `cdc_checks`)."""

    __tablename__ = "cdc_checks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    item_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    check_code: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info")  # blocker|warning|info
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CdcLlmRun(Base):
    """Trace d'un appel IA CDC : modèle, empreinte de requête, durée (audit)."""

    __tablename__ = "cdc_llm_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    model_name: Mapped[str] = mapped_column(String(128), default="")
    prompt_version: Mapped[str] = mapped_column(String(64), default="cdc-v1")
    request_checksum: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="running")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    items_returned: Mapped[int] = mapped_column(Integer, default=0)
    items_accepted: Mapped[int] = mapped_column(Integer, default=0)
    items_rejected: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CdcItem(Base):
    """Moteur CDC repris de XPilot : kinds, preuve page, ancrages, statuts."""

    __tablename__ = "cdc_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # function|constraint|requirement|data|interface|open_point
    human_id: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_wording: Mapped[str] = mapped_column(Text, default="")
    source_quote: Mapped[str] = mapped_column(Text, nullable=False)
    physical_page: Mapped[int] = mapped_column(Integer, default=1)
    modality: Mapped[str] = mapped_column(String(32), default="information")
    priority: Mapped[str] = mapped_column(String(32), default="unclassified")
    knowledge_status: Mapped[str] = mapped_column(String(32), default="candidate")
    criterion: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    acceptance_criterion: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    responsible_party: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    estimated_hours: Mapped[float] = mapped_column(Float, default=0)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class BusinessDecision(Base):
    __tablename__ = "business_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor: Mapped[str] = mapped_column(String(128), default="validator")
    operation: Mapped[str] = mapped_column(String(64))
    previous_value: Mapped[str] = mapped_column(Text, default="{}")
    new_value: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class CdcAnalysisJob(Base):
    __tablename__ = "cdc_analysis_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("cdc_sources.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_batches: Mapped[int] = mapped_column(Integer, default=0)
    total_batches: Mapped[int] = mapped_column(Integer, default=0)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("cdc_llm_runs.id"), nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class DeliveryVersion(Base):
    __tablename__ = "delivery_versions"
    __table_args__ = (UniqueConstraint("project_id", "kind", "version", name="uq_delivery_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="transfer-be")
    version: Mapped[int] = mapped_column(Integer)
    draft: Mapped[bool] = mapped_column(default=False)
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
