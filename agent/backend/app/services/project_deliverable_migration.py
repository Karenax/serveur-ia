"""Explicit additive L3 installation, never invoked by a production import."""
from sqlalchemy import CheckConstraint, UniqueConstraint, inspect

from ..project_deliverable_models import DELIVERABLE_TABLES, IMMUTABLE_TABLES
from .project_planning_migration import _sql, read_connection


def immutable_triggers():
    return {f'trg_{table}_{operation.lower()}_immutable':
            f'CREATE TRIGGER trg_{table}_{operation.lower()}_immutable BEFORE {operation} ON {table} '
            "BEGIN SELECT RAISE(ABORT, 'Published deliverable values are immutable'); END"
            for table in IMMUTABLE_TABLES for operation in ('UPDATE', 'DELETE')}


def validate_deliverable_schema(engine, *, require_prerequisites=True):
    """Read-only preflight, including dormant partial tables before any DDL."""
    from .. import models, project_identity_models, project_planning_models  # noqa: F401
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    added_columns = []
    if require_prerequisites and not {'projects', 'deliverables', 'milestones', 'delivery_versions', 'project_people',
            'project_references', 'project_planning_states'}.issubset(existing):
        raise ValueError('Une base ERP avec le socle L2 est requise')
    for table in DELIVERABLE_TABLES:
        if table.name not in existing:
            continue
        actual = {column['name']: column for column in inspector.get_columns(table.name)}
        allowed_missing = set()
        if table.name == 'project_deliverable_version_metadata' and 'storage_path' not in actual:
            allowed_missing.add('storage_path')
            added_columns.append('project_deliverable_version_metadata.storage_path')
        if any(column.name not in actual
               or column.type.compile(engine.dialect) != actual[column.name]['type'].compile(engine.dialect)
               or column.nullable != actual[column.name]['nullable'] for column in table.columns
               if column.name not in allowed_missing):
            raise ValueError(f'Schéma de livrables incompatible : {table.name}')
        primary = set(inspector.get_pk_constraint(table.name)['constrained_columns'])
        foreign = {(tuple(item['constrained_columns']), item['referred_table'], tuple(item['referred_columns']))
                   for item in inspector.get_foreign_keys(table.name)}
        expected_foreign = {(tuple(item.column_keys), item.referred_table.name,
                             tuple(element.column.name for element in item.elements)) for item in table.foreign_key_constraints}
        unique = {tuple(item['column_names']) for item in inspector.get_unique_constraints(table.name)}
        expected_unique = {tuple(item.columns.keys()) for item in table.constraints if isinstance(item, UniqueConstraint)}
        checks = {_sql(item['sqltext']) for item in inspector.get_check_constraints(table.name)}
        expected_checks = {_sql(item.sqltext) for item in table.constraints if isinstance(item, CheckConstraint)}
        indexes = {item['name']: item for item in inspector.get_indexes(table.name)}
        indexes_valid = all(index.name in indexes and indexes[index.name]['column_names'] == [col.name for col in index.columns]
                            and bool(indexes[index.name]['unique']) == bool(index.unique) for index in table.indexes)
        if (primary != {column.name for column in table.primary_key} or not expected_foreign.issubset(foreign)
                or not expected_unique.issubset(unique) or not expected_checks.issubset(checks) or not indexes_valid):
            raise ValueError(f'Contraintes de livrables incomplètes : {table.name}')
    with read_connection(engine) as db:
        installed = {name: statement for name, statement in db.exec_driver_sql(
            "SELECT name, sql FROM sqlite_master WHERE type='trigger'")}
    triggers = immutable_triggers()
    if any(name in installed and _sql(installed[name]) != _sql(statement) for name, statement in triggers.items()):
        raise ValueError('Protection de livrables incompatible')
    missing_tables = [table.name for table in DELIVERABLE_TABLES if table.name not in existing]
    missing_triggers = [name for name in triggers if name not in installed]
    result = {'created_tables': missing_tables, 'created_triggers': missing_triggers}
    if added_columns:
        result['added_columns'] = added_columns
    return result


def install_deliverable_schema(engine, *, backup):
    plan = validate_deliverable_schema(engine)
    missing_tables, missing_triggers = plan['created_tables'], plan['created_triggers']
    added_columns = plan.get('added_columns', [])
    triggers = immutable_triggers()
    if missing_tables or missing_triggers or added_columns:
        backup()
        with engine.begin() as db:
            if added_columns:
                db.exec_driver_sql("ALTER TABLE project_deliverable_version_metadata ADD COLUMN storage_path TEXT NOT NULL DEFAULT ''")
            DELIVERABLE_TABLES[0].metadata.create_all(db, tables=list(DELIVERABLE_TABLES))
            for name in missing_triggers:
                db.exec_driver_sql(triggers[name])
    return plan
