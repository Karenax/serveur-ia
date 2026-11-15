"""Backup-first additive capture schema; validate before any installer writes."""
from sqlalchemy import inspect
from sqlalchemy.schema import CreateTable

from app.meeting_session_models import SESSION_TABLES
from backend.app.services.document_schema_rules import _sql
from backend.app.services.project_planning_migration import read_connection


def validate_session_schema(engine):
    with read_connection(engine) as db:
        existing = set(inspect(db).get_table_names())
        for table in SESSION_TABLES:
            if table.name not in existing:
                continue
            actual = db.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table.name,)).scalar()
            if _sql(actual) != _sql(str(CreateTable(table).compile(dialect=engine.dialect))):
                raise ValueError('Schéma de capture incompatible : ' + table.name)
        return [table.name for table in SESSION_TABLES if table.name not in existing]


def install_session_schema(engine, *, backup):
    missing = validate_session_schema(engine)
    if missing:
        backup()
        with engine.begin() as db:
            SESSION_TABLES[0].metadata.create_all(db, tables=list(SESSION_TABLES))
    return missing
