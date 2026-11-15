"""Explicit seven-table installation, validated before backup and additive DDL."""
from contextlib import nullcontext
from sqlalchemy import CheckConstraint, UniqueConstraint, inspect
from sqlalchemy.engine import Connection

from ..project_planning_models import IMMUTABLE_TABLES, PLANNING_TABLES


def _sql(value):
    return " ".join(str(value).strip().rstrip(";").split()).casefold()


def read_connection(bind):
    """Use the caller's locked connection for preflight, without closing it."""
    return nullcontext(bind) if isinstance(bind, Connection) else bind.connect()


def immutable_triggers():
    return {f"trg_{table}_{operation.lower()}_immutable":
            f"CREATE TRIGGER trg_{table}_{operation.lower()}_immutable BEFORE {operation} ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'Published planning values are immutable'); END"
            for table in IMMUTABLE_TABLES for operation in ("UPDATE", "DELETE")}


def _installation_plan(engine, db):
    """Reflect constraints on one connection, including its current SQLite schema."""
    from .. import models, project_identity_models  # noqa: F401
    inspector = inspect(db)
    existing = set(inspector.get_table_names())
    if not {"projects", "milestones", "tasks", "project_references", "project_people"}.issubset(existing):
        raise ValueError("Une base ERP avec le socle L1 est requise")
    for table in PLANNING_TABLES:
        if table.name not in existing:
            continue
        actual = {column["name"]: column for column in inspector.get_columns(table.name)}
        if any(column.name not in actual
               or column.type.compile(engine.dialect) != actual[column.name]["type"].compile(engine.dialect)
               or column.nullable != actual[column.name]["nullable"] for column in table.columns):
            raise ValueError(f"Schéma de planning incompatible : {table.name}")
        primary = set(inspector.get_pk_constraint(table.name)["constrained_columns"])
        foreign = {(tuple(item["constrained_columns"]), item["referred_table"], tuple(item["referred_columns"]))
                   for item in inspector.get_foreign_keys(table.name)}
        expected_foreign = {(tuple(item.column_keys), item.referred_table.name,
                             tuple(element.column.name for element in item.elements)) for item in table.foreign_key_constraints}
        unique = {tuple(item["column_names"]) for item in inspector.get_unique_constraints(table.name)}
        expected_unique = {tuple(item.columns.keys()) for item in table.constraints if isinstance(item, UniqueConstraint)}
        checks = {_sql(item["sqltext"]) for item in inspector.get_check_constraints(table.name)}
        expected_checks = {_sql(item.sqltext) for item in table.constraints if isinstance(item, CheckConstraint)}
        indexes = {item["name"]: item for item in inspector.get_indexes(table.name)}
        indexes_valid = all(index.name in indexes and indexes[index.name]["column_names"] == [col.name for col in index.columns]
                            and bool(indexes[index.name]["unique"]) == bool(index.unique) for index in table.indexes)
        if (primary != {column.name for column in table.primary_key} or not expected_foreign.issubset(foreign)
                or not expected_unique.issubset(unique) or not expected_checks.issubset(checks) or not indexes_valid):
            raise ValueError(f"Contraintes de planning incomplètes : {table.name}")
    existing_triggers = {name: statement for name, statement in db.exec_driver_sql(
        "SELECT name, sql FROM sqlite_master WHERE type='trigger'")}
    triggers = immutable_triggers()
    for name, statement in triggers.items():
        if name in existing_triggers and _sql(existing_triggers[name]) != _sql(statement):
            raise ValueError(f"Protection de référence incompatible : {name}")
    missing_tables = [table.name for table in PLANNING_TABLES if table.name not in existing]
    missing_triggers = [name for name in triggers if name not in existing_triggers]
    return {"created_tables": missing_tables, "created_triggers": missing_triggers}


def install_planning_schema(engine, *, backup):
    """No project seeding, no existing columns changed, caller owns offline backup."""
    with read_connection(engine) as db:
        plan = _installation_plan(engine, db)
    missing_tables, missing_triggers = plan['created_tables'], plan['created_triggers']
    if not missing_tables and not missing_triggers:
        return {"created_tables": [], "created_triggers": []}
    backup()
    with engine.begin() as db:
        PLANNING_TABLES[0].metadata.create_all(db, tables=list(PLANNING_TABLES))
        for name in missing_triggers:
            db.exec_driver_sql(immutable_triggers()[name])
    return {"created_tables": missing_tables, "created_triggers": missing_triggers}
