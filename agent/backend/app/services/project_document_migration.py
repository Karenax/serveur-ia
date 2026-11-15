"""Explicit, backup-first installation of immutable document form history."""

from sqlalchemy import CheckConstraint, UniqueConstraint, inspect

from ..project_document_models import DOCUMENT_FORM_TABLES
from .project_planning_migration import read_connection
from .document_schema_rules import _sql, immutable_triggers  # re-export compatibility


def validate_document_schema(engine, *, require_prerequisites=True):
    from .. import models  # noqa: F401
    if engine.dialect.name != 'sqlite':
        raise ValueError('Stockage SQLite Agent requis pour les documents')
    with read_connection(engine) as db:
        inspector = inspect(db)
        existing = set(inspector.get_table_names())
        if require_prerequisites and not {'projects', 'network_links'}.issubset(existing):
            raise ValueError('Socle ERP et liens projet requis pour les documents')
        for table in DOCUMENT_FORM_TABLES:
            if table.name not in existing:
                continue
            columns = {value['name']: value for value in inspector.get_columns(table.name)}
            if set(columns) != set(table.c.keys()) or any(
                    column.type.compile(engine.dialect) != columns[column.name]['type'].compile(engine.dialect)
                    or column.nullable != columns[column.name]['nullable']
                    or _sql(column.server_default.arg if column.server_default is not None else '')
                    != _sql(columns[column.name].get('default') or '') for column in table.c):
                raise ValueError(f'Schéma documentaire incompatible : {table.name}')
            primary = set(inspector.get_pk_constraint(table.name)['constrained_columns'])
            unique = {tuple(value['column_names']) for value in inspector.get_unique_constraints(table.name)}
            checks = {_sql(value['sqltext']) for value in inspector.get_check_constraints(table.name)}
            foreign = {(tuple(value['constrained_columns']), value['referred_table'], tuple(value['referred_columns']),
                        value.get('options', {}).get('ondelete'), value.get('options', {}).get('onupdate'))
                       for value in inspector.get_foreign_keys(table.name)}
            expected_foreign = {(tuple(value.column_keys), value.referred_table.name,
                                 tuple(element.column.name for element in value.elements), value.ondelete, value.onupdate)
                                for value in table.foreign_key_constraints}
            indexes = {value['name']: value for value in inspector.get_indexes(table.name)}
            if (primary != {column.name for column in table.primary_key}
                    or unique != {tuple(value.columns.keys()) for value in table.constraints if isinstance(value, UniqueConstraint)}
                    or checks != {_sql(value.sqltext) for value in table.constraints if isinstance(value, CheckConstraint)}
                    or foreign != expected_foreign
                    or any(index.name not in indexes or indexes[index.name]['column_names'] != [col.name for col in index.columns]
                           or bool(indexes[index.name]['unique']) != bool(index.unique) for index in table.indexes)):
                raise ValueError(f'Contraintes documentaires incompatibles : {table.name}')
        installed = {name: statement for name, statement in db.exec_driver_sql(
            "SELECT name, sql FROM sqlite_master WHERE type='trigger'")}
        expected = immutable_triggers()
        if any(name in installed and _sql(installed[name]) != _sql(statement) for name, statement in expected.items()):
            raise ValueError('Protection documentaire incompatible')
        plan = {'created_tables': [table.name for table in DOCUMENT_FORM_TABLES if table.name not in existing],
                'created_triggers': [name for name in expected if name not in installed]}
        if plan['created_tables'] and any(db.exec_driver_sql(f'SELECT 1 FROM {table.name} LIMIT 1').first()
                                         for table in DOCUMENT_FORM_TABLES if table.name in existing):
            raise ValueError('Schéma documentaire partiel avec données : restauration contrôlée requise')
        return plan


def install_document_schema(engine, *, backup):
    plan = validate_document_schema(engine)
    if plan['created_tables'] or plan['created_triggers']:
        backup()  # Must succeed before DDL; no cleanup or seeding.
        with engine.begin() as db:
            DOCUMENT_FORM_TABLES[0].metadata.create_all(db, tables=list(DOCUMENT_FORM_TABLES))
            for name in plan['created_triggers']:
                db.exec_driver_sql(immutable_triggers()[name])
    return plan
