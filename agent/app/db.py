"""Project Brain - DB session."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings
from .db_support import configure_sqlite, record_schema
from sqlalchemy import text

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
configure_sqlite(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401
    from . import meeting_session_models  # noqa: F401
    from .services.meeting_session_schema import install_session_schema, validate_session_schema
    from .services.source_library import validate_library_db
    from sqlalchemy import inspect
    from sqlalchemy.engine import make_url
    from .db_support import backup_sqlite
    from pathlib import Path
    from datetime import datetime, timezone
    inspector = inspect(engine)
    existing = inspector.get_table_names()
    session_missing = validate_session_schema(engine)
    validate_library_db(engine)
    needs_backup = bool(existing) and ("meeting_recordings" not in existing or "mail_identities" not in existing or "thunderbird_jobs" not in existing or "memory_projections" not in existing or
        "external_ref" not in {col["name"] for col in inspector.get_columns("memory_projections")})
    needs_backup = needs_backup or bool(existing and session_missing)
    backed_up = False
    def ensure_session_backup():
        nonlocal backed_up
        if not backed_up and existing and engine.dialect.name == 'sqlite':
            path = Path(make_url(settings.database_url).database)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
            backup_sqlite(path, path.parent / 'backups' / f'brain-{stamp}.db')
            backed_up = True

    if "app_settings" in existing:
        with engine.connect() as conn:
            stored = conn.execute(text("SELECT value FROM app_settings WHERE key='ai'")).scalar()
        import json
        key = (json.loads(stored).get("api_key") or "") if stored else ""
        needs_backup = needs_backup or bool(key and not key.startswith("dpapi:"))
    if needs_backup and engine.dialect.name == "sqlite":
        path = Path(make_url(settings.database_url).database)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        backup_sqlite(path, path.parent / "backups" / f"brain-{stamp}.db")
        backed_up = True
    protected = {table.name for table in meeting_session_models.SESSION_TABLES}
    Base.metadata.create_all(bind=engine, tables=[table for table in Base.metadata.sorted_tables
        if table.name not in protected and not table.name.startswith('foresight_')])
    install_session_schema(engine, backup=ensure_session_backup)
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(memory_projections)"))}
        if "external_ref" not in cols:
            conn.execute(text("ALTER TABLE memory_projections ADD COLUMN external_ref TEXT"))
    record_schema(engine, "brain", 2)
    import os
    if os.name == "nt":
        from .models import AppSetting
        from .services.secrets_store import protect
        with SessionLocal() as db:
            row = db.get(AppSetting, "ai")
            if row and row.value.get("api_key") and not row.value["api_key"].startswith("dpapi:"):
                row.value = {**row.value, "api_key": protect(row.value["api_key"])}
                db.commit()
    record_schema(engine, "brain", 3)
    record_schema(engine, "brain", 4)
    record_schema(engine, "brain", 5)
    record_schema(engine, "brain", 6)
