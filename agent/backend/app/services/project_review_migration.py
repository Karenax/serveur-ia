"""L4 preflight and explicit installation; backup must succeed before any DDL."""
from sqlalchemy import CheckConstraint, UniqueConstraint, inspect

from ..project_review_models import REVIEW_TABLES
from .project_planning_migration import _sql, read_connection


def immutable_triggers():
    definitions = {}
    for name in ('project_review_publications', 'project_review_events', 'project_reviews'):
        for operation in ('UPDATE', 'DELETE'):
            key = f'trg_{name}_{operation.lower()}_immutable'
            condition = " WHEN OLD.status = 'published'" if name == 'project_reviews' else ''
            definitions[key] = (f'CREATE TRIGGER {key} BEFORE {operation} ON {name}{condition} '
                                "BEGIN SELECT RAISE(ABORT, 'Published review values are immutable'); END")
    return definitions


def validate_review_schema(engine, *, require_prerequisites=True):
    from .. import models, project_identity_models, project_planning_models, project_deliverable_models  # noqa: F401
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    added_columns = []
    if require_prerequisites and not {'projects', 'project_people', 'project_planning_states',
                                      'project_deliverable_plans'}.issubset(existing):
        raise ValueError('Le socle ERP L3 est requis pour les revues')
    for table in REVIEW_TABLES:
        if table.name not in existing:
            continue
        columns = {column['name']: column for column in inspector.get_columns(table.name)}
        missing = {column.name for column in table.columns} - set(columns)
        if missing == {'bindings'} and table.name in {'project_review_publications', 'project_review_events'}:
            added_columns.append(table.name)
        elif missing:
            raise ValueError(f'Schéma de revues incompatible : {table.name}')
        if any(column.nullable != columns[column.name]['nullable']
               or column.type.compile(engine.dialect) != columns[column.name]['type'].compile(engine.dialect)
               for column in table.columns if column.name in columns):
            raise ValueError(f'Schéma de revues incompatible : {table.name}')
        primary = set(inspector.get_pk_constraint(table.name)['constrained_columns'])
        unique = {tuple(value['column_names']) for value in inspector.get_unique_constraints(table.name)}
        checks = {_sql(value['sqltext']) for value in inspector.get_check_constraints(table.name)}
        foreign = {(tuple(value['constrained_columns']), value['referred_table'], tuple(value['referred_columns']))
                   for value in inspector.get_foreign_keys(table.name)}
        expected_foreign = {(tuple(value.column_keys), value.referred_table.name,
                             tuple(element.column.name for element in value.elements))
                            for value in table.foreign_key_constraints}
        indexes = {value['name']: value for value in inspector.get_indexes(table.name)}
        if (primary != {column.name for column in table.primary_key}
                or not {tuple(value.columns.keys()) for value in table.constraints
                        if isinstance(value, UniqueConstraint)}.issubset(unique)
                or not {_sql(value.sqltext) for value in table.constraints
                        if isinstance(value, CheckConstraint)}.issubset(checks)
                or not expected_foreign.issubset(foreign)
                or any(index.name not in indexes or indexes[index.name]['column_names'] != [col.name for col in index.columns]
                       or bool(indexes[index.name]['unique']) != bool(index.unique) for index in table.indexes)):
            raise ValueError(f'Contraintes de revues incomplètes : {table.name}')
    triggers = immutable_triggers()
    with read_connection(engine) as db:
        installed = {name: statement for name, statement in db.exec_driver_sql(
            "SELECT name, sql FROM sqlite_master WHERE type='trigger'")}
    if any(name in installed and _sql(installed[name]) != _sql(statement) for name, statement in triggers.items()):
        raise ValueError('Protection de revues incompatible')
    plan = {'created_tables': [table.name for table in REVIEW_TABLES if table.name not in existing],
            'created_triggers': [name for name in triggers if name not in installed]}
    if plan['created_tables']:
        # Installing an empty group is additive. Reconstructing missing parts of
        # a populated review group would invent absent publication/audit state.
        with read_connection(engine) as db:
            if any(db.exec_driver_sql(f'SELECT 1 FROM {table.name} LIMIT 1').first()
                   for table in REVIEW_TABLES if table.name in existing):
                raise ValueError('Schéma de revues partiel avec données ; restauration contrôlée requise')
    if added_columns:
        plan['added_binding_columns'] = added_columns
    return plan


def install_review_schema(engine, *, backup):
    plan = validate_review_schema(engine)
    if plan['created_tables'] or plan['created_triggers'] or plan.get('added_binding_columns'):
        backup()
        with engine.begin() as db:
            REVIEW_TABLES[0].metadata.create_all(db, tables=list(REVIEW_TABLES))
            for table in plan.get('added_binding_columns', []):
                db.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN bindings JSON NOT NULL DEFAULT '{{}}'")
            for name in plan['created_triggers']:
                db.exec_driver_sql(immutable_triggers()[name])
    return plan
