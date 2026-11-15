"""SQLite local, sans login, sans serveur externe."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from app.db_support import configure_sqlite, record_schema, backup_sqlite
from sqlalchemy.orm import DeclarativeBase, sessionmaker

APP_DIR = Path(os.environ.get("MINIPILOT_HOME", str(Path.home() / ".minipilot")))
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / "minipilot.db"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
configure_sqlite(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def _backup() -> None:
    """Copie SQLite cohérente avant migration ; aucune purge automatique."""
    from datetime import datetime

    if not DB_PATH.exists() or DB_PATH.stat().st_size == 0:
        return
    backup_dir = APP_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_sqlite(DB_PATH, backup_dir / f"minipilot-{stamp}.db")


def init_db() -> None:
    from . import models  # noqa: F401
    from . import project_identity_models  # noqa: F401
    from . import project_planning_models  # noqa: F401
    from . import project_deliverable_models  # noqa: F401
    from . import project_review_models  # noqa: F401
    from . import project_knowledge_models  # noqa: F401
    from . import note_evidence_models  # noqa: F401
    from .services.project_identity_migration import install_identity_schema
    from .services.project_planning_migration import install_planning_schema
    from .services.project_deliverable_migration import install_deliverable_schema, validate_deliverable_schema
    from .services.project_review_migration import install_review_schema, validate_review_schema
    from .services.project_document_migration import validate_document_schema, install_document_schema
    from .services.document_job_schema import validate_job_schema, install_job_schema
    from .services.project_note_schema import validate_note_schema, install_note_schema
    from .services.note_evidence_outbox import validate_outbox_schema, install_outbox_schema

    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    backed_up = False

    def ensure_backup():
        nonlocal backed_up
        if not backed_up:
            _backup()
            backed_up = True

    # Validate even a dormant/partial L3 installation before any other DDL.
    # Legacy native tables may be absent on a fresh base; their creation below
    # deliberately excludes L3, which only its explicit installer can create.
    validate_deliverable_schema(engine, require_prerequisites=False)
    # A dormant/partial L4 must be checked before any other installer can write.
    # Its protected tables remain excluded from the generic create_all below.
    validate_review_schema(engine, require_prerequisites=False)
    # Validate both L5 groups before ANY DDL. Imports/generic metadata creation
    # never activate their histories; only the guarded installers below do.
    validate_document_schema(engine, require_prerequisites=False)
    validate_job_schema(engine, require_prerequisites=False)
    # Check Notes before any DDL; only their backup-first installer creates the
    # tables/protections after the other project prerequisites are ready.
    validate_note_schema(engine, require_prerequisites=False)
    validate_outbox_schema(engine)

    # Advancing the startup marker is itself a write, even if an explicit
    # installation already created every table. Preserve the old database
    # before this ERP10 upgrade, sharing the same backup with all installers.
    if tables:
        with engine.connect() as connection:
            version_installed = 'schema_migrations' in tables and connection.execute(
                text("SELECT 1 FROM schema_migrations WHERE domain='erp' AND version=11")
            ).first() is not None
        if not version_installed:
            ensure_backup()

    # Validate existing L1 constraints before create_all can conceal a partial
    # installation. Existing databases require a successful backup before DDL.
    if "projects" in tables:
        install_identity_schema(engine, backup=ensure_backup)
        install_planning_schema(engine, backup=ensure_backup)
    # Preserve one pre-migration copy, rather than a new backup at every launch.
    required = {"projects": {"remaining_hours", "tdao_budget_h", "tdao_prix_vente", "hourly_rate", "margin_pct", "client_name", "offer_number"},
                "cdc_items": {"estimated_hours", "unit_price", "created_at", "human_id", "knowledge_status", "criterion", "unit", "acceptance_criterion", "responsible_party"},
                "cdc_sources": {"sha256", "storage_path", "content_type", "extracted_at", "extraction_error"},
                "milestones": {"contractual_date", "forecast_date", "actual_date", "date_sources"}}
    # L3 is always installed explicitly, never hidden inside create_all.
    runtime_tables = [table for table in Base.metadata.sorted_tables
                      if not table.name.startswith('project_deliverable_')
                      and not table.name.startswith('project_document_')
                      and not table.name.startswith('project_note')
                      and table.name != 'note_evidence_outbox'
                      and not table.name.startswith('foresight_')
                      and table.name not in {'project_reviews', 'project_review_publications', 'project_review_events'}]
    if tables and (any(table.name not in tables for table in runtime_tables) or
                   any(not columns.issubset({c["name"] for c in inspector.get_columns(name)})
                       for name, columns in required.items() if name in tables)):
        ensure_backup()
    Base.metadata.create_all(bind=engine, tables=runtime_tables)
    # On a fresh database, create_all installs the tables; the explicit installer
    # validates them and adds immutable-history protections as on an upgrade.
    install_planning_schema(engine, backup=ensure_backup)
    install_deliverable_schema(engine, backup=ensure_backup)
    install_review_schema(engine, backup=ensure_backup)
    install_document_schema(engine, backup=ensure_backup)
    install_job_schema(engine, backup=ensure_backup)
    install_note_schema(engine, backup=ensure_backup)
    install_outbox_schema(engine, backup=ensure_backup)
    # Migration légère : colonnes de chiffrage sur cdc_items (sans Alembic)
    with engine.begin() as conn:
        milestone_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(milestones)"))}
        for col in ("contractual_date", "forecast_date", "actual_date"):
            if col not in milestone_cols:
                conn.execute(text(f"ALTER TABLE milestones ADD COLUMN {col} VARCHAR(32) DEFAULT ''"))
        if "date_sources" not in milestone_cols:
            conn.execute(text("ALTER TABLE milestones ADD COLUMN date_sources JSON DEFAULT '{}'"))
        # An old single due date is a forecast, never an invented contractual date.
        if "forecast_date" not in milestone_cols:
            conn.execute(text("UPDATE milestones SET forecast_date=due_date WHERE due_date IS NOT NULL"))
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(cdc_items)")).fetchall()}
        if "estimated_hours" not in cols:
            conn.execute(text("ALTER TABLE cdc_items ADD COLUMN estimated_hours FLOAT DEFAULT 0"))
        if "unit_price" not in cols:
            conn.execute(text("ALTER TABLE cdc_items ADD COLUMN unit_price FLOAT DEFAULT 0"))
        pcols = {row[1] for row in conn.execute(text("PRAGMA table_info(projects)")).fetchall()}
        if "hourly_rate" not in pcols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN hourly_rate FLOAT DEFAULT 85"))
        if "margin_pct" not in pcols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN margin_pct FLOAT DEFAULT 10"))
        if "remaining_hours" not in pcols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN remaining_hours FLOAT"))
        for col, ddl in (
            ("client_name", "ALTER TABLE projects ADD COLUMN client_name VARCHAR(255) DEFAULT ''"),
            ("offer_number", "ALTER TABLE projects ADD COLUMN offer_number VARCHAR(64) DEFAULT ''"),
            ("tdao_prix_vente", "ALTER TABLE projects ADD COLUMN tdao_prix_vente FLOAT DEFAULT 0"),
            ("tdao_budget_h", "ALTER TABLE projects ADD COLUMN tdao_budget_h FLOAT DEFAULT 0"),
        ):
            if col not in pcols:
                conn.execute(text(ddl))
        # Moteur CDC repris de XPilot : stockage, texte par page, preuves, contrôles
        cdc_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(cdc_sources)")).fetchall()}
        for col, ddl in (
            ("sha256", "ALTER TABLE cdc_sources ADD COLUMN sha256 VARCHAR(64)"),
            ("storage_path", "ALTER TABLE cdc_sources ADD COLUMN storage_path VARCHAR(1024)"),
            ("content_type",
             "ALTER TABLE cdc_sources ADD COLUMN content_type VARCHAR(120) DEFAULT 'application/octet-stream'"),
            ("extracted_at", "ALTER TABLE cdc_sources ADD COLUMN extracted_at DATETIME"),
            ("extraction_error", "ALTER TABLE cdc_sources ADD COLUMN extraction_error TEXT"),
        ):
            if col not in cdc_cols:
                conn.execute(text(ddl))
        item_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(cdc_items)")).fetchall()}
        for col, ddl in (
            ("created_at", "ALTER TABLE cdc_items ADD COLUMN created_at DATETIME"),
            ("human_id", "ALTER TABLE cdc_items ADD COLUMN human_id VARCHAR(32)"),
            ("knowledge_status",
             "ALTER TABLE cdc_items ADD COLUMN knowledge_status VARCHAR(32) DEFAULT 'candidate'"),
            ("criterion", "ALTER TABLE cdc_items ADD COLUMN criterion TEXT"),
            ("unit", "ALTER TABLE cdc_items ADD COLUMN unit VARCHAR(32)"),
            ("acceptance_criterion", "ALTER TABLE cdc_items ADD COLUMN acceptance_criterion TEXT"),
            ("responsible_party", "ALTER TABLE cdc_items ADD COLUMN responsible_party VARCHAR(120)"),
        ):
            if col not in item_cols:
                conn.execute(text(ddl))
    record_schema(engine, "erp", 2)
    record_schema(engine, "erp", 3)
    record_schema(engine, "erp", 4)
    record_schema(engine, "erp", 5)
    record_schema(engine, "erp", 6)
    record_schema(engine, "erp", 7)
    record_schema(engine, "erp", 8)
    record_schema(engine, "erp", 9)
    record_schema(engine, "erp", 10)
    record_schema(engine, "erp", 11)
    # A single Agent process owns this ERP database. Runs interrupted by its
    # previous shutdown remain visible and can be manually restarted.
    with engine.begin() as conn:
        conn.execute(text("UPDATE cdc_llm_runs SET status='failed', "
                          "error_message='Analyse interrompue ; relancer depuis la source conservée' "
                          "WHERE status='running'"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
