"""SQL closure and reconciliation on fictional ERP stores, no transport activation."""
from copy import deepcopy
from datetime import datetime

from fastapi import HTTPException
import pytest
from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from backend.app.db import Base
from backend.app.project_deliverable_models import DELIVERABLE_TABLES
from backend.app.services import project_deliverable_archive as contract
from backend.app.services import project_deliverable_archive_store as archive_store
from backend.app.services import project_identity_archive as identity_archive
from backend.app.services.migration_guard import capture_baseline
from backend.app.services.project_deliverable_migration import install_deliverable_schema
from tests.test_project_deliverable_archive_contract import envelope, mapping, store, validate

__all__ = ['envelope', 'store']


def reconcile(db, value, replacements):
    return archive_store.reconcile_references(db, Base.metadata, value['section'], replacements,
        typology_ids=contract.dependencies(value['tables'], value['section'])['typologies'])


def test_sql_export_matches_full_domain_closure_excluding_unrelated_globals(envelope, store):
    before = capture_baseline(store[2])
    with store[0]() as db:
        result = archive_store.export_references(db, Base.metadata, envelope['tables'])
    for name in contract.REFERENCE_TABLES:
        assert sorted(result[name], key=lambda row: row['id']) == sorted(envelope['section'][name], key=lambda row: row['id'])
    value = {**envelope, 'section': result}
    validate(value)
    assert capture_baseline(store[2]) == before


def test_sql_export_keeps_composition_without_deliverable_rows_or_planning_state(envelope, store):
    tables = deepcopy(envelope['tables'])
    for name in contract.PROJECT_TABLES | {'project_planning_changes', 'project_planning_states'}:
        tables[name] = []
    before = capture_baseline(store[2])
    with store[0]() as db:
        section = archive_store.export_references(db, Base.metadata, tables)
    assert {row['id'] for row in section['project_deliverable_types']} == {envelope['ids'][key]['id'] for key in ('main', 'retained')}
    validate({**envelope, 'tables': tables, 'section': section})
    assert capture_baseline(store[2]) == before


def test_same_database_reconciliation_reuses_every_exact_global_and_changes_no_cell(envelope, store):
    validate(envelope)
    before = capture_baseline(store[2])
    replacements = mapping(envelope)
    replacements.update({row['id']: row['id'] for rows in envelope['references'].values() for row in rows})
    with store[0]() as db:
        pending = reconcile(db, envelope, replacements)
    assert all(not rows for rows in pending.values())
    for rows in envelope['section'].values():
        assert all(replacements[row['id']] == row['id'] for row in rows)
    assert capture_baseline(store[2]) == before


@pytest.mark.parametrize('case', ['head_label', 'head_activity', 'head_revision', 'version_definition', 'version_actor',
                                  'version_date', 'composition_activity', 'composition_missing', 'audit_actor', 'audit_snapshot'])
def test_conflicts_refused_before_writes_and_mapping_is_atomic(envelope, store, case):
    validate(envelope)
    value = deepcopy(envelope)
    section = value['section']
    if case.startswith('head_'):
        key = {'head_label': 'label', 'head_activity': 'active', 'head_revision': 'revision'}[case]
        row = section['project_deliverable_types'][0]
        row[key] = 'Different' if key == 'label' else not row[key] if key == 'active' else row[key] + 10
    elif case.startswith('version_'):
        key = {'version_definition': 'definition', 'version_actor': 'actor_id', 'version_date': 'created_at'}[case]
        section['project_deliverable_type_versions'][0][key] = '2026-10-06T12:00:00' if key == 'created_at' else 'Different'
    elif case == 'composition_activity':
        section['project_deliverable_typology_types'][0]['active'] = not section['project_deliverable_typology_types'][0]['active']
    elif case == 'composition_missing':
        section['project_deliverable_typology_types'].clear()
    elif case == 'audit_actor':
        section['project_reference_changes'][-1]['actor_id'] = 'Different'
    else:
        section['project_reference_changes'][-1]['value'] = {'different': 'snapshot'}
    before = capture_baseline(store[2])
    replacements = mapping(value)
    # L1 identity reconciliation runs before L3 in the importer.
    replacements[value['ids']['typology']['id']] = value['ids']['typology']['id']
    initial = dict(replacements)
    with store[0]() as db, pytest.raises(HTTPException) as error:
        reconcile(db, value, replacements)
    assert error.value.status_code == 409
    assert replacements == initial and capture_baseline(store[2]) == before


@pytest.fixture
def target(tmp_path):
    path = tmp_path / 'target.db'
    engine = create_engine(f'sqlite:///{path}')
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables if table not in DELIVERABLE_TABLES])
    install_deliverable_schema(engine, backup=lambda: backup_sqlite(path, tmp_path / 'target-before-l3.db'))
    yield sessionmaker(bind=engine, autoflush=False), path
    engine.dispose()


def _insert_globals(db, value, replacements):
    for table in Base.metadata.sorted_tables:
        rows = value['references'].get(table.name)
        if rows is not None:
            prepared = [identity_archive.remap_identity_row(row, table, replacements) for row in rows]
        else:
            rows = value['section'].get(table.name, [])
            prepared = [contract.remap_row(row, table, replacements) for row in rows]
        for row in prepared:
            for key in row:
                if isinstance(table.c[key].type, DateTime) and isinstance(row[key], str):
                    row[key] = datetime.fromisoformat(row[key])
            db.execute(table.insert().values(**row))
    db.commit()


def test_new_catalogue_is_only_prepared_and_can_be_inserted_under_immutable_triggers(envelope, target):
    validate(envelope)
    factory, path = target
    before = capture_baseline(path)
    replacements = mapping(envelope)
    with factory() as db:
        pending = reconcile(db, envelope, replacements)
    assert pending == envelope['section'] and capture_baseline(path) == before
    with factory() as db:
        _insert_globals(db, envelope, replacements)
    after = capture_baseline(path)
    with factory() as db:
        pending = reconcile(db, envelope, replacements)
    assert all(not rows for rows in pending.values()) and capture_baseline(path) == after


def test_reuse_matches_business_keys_with_different_ids_and_retains_all_current_revisions(envelope, target):
    validate(envelope)
    factory, path = target
    replacements = mapping(envelope)
    with factory() as db:
        _insert_globals(db, envelope, replacements)
    before = capture_baseline(path)
    incoming_mapping = mapping(envelope)
    incoming_mapping.update({row['id']: replacements[row['id']] for rows in envelope['references'].values() for row in rows})
    with factory() as db:
        pending = reconcile(db, envelope, incoming_mapping)
    assert all(not rows for rows in pending.values())
    for rows in envelope['section'].values():
        assert all(incoming_mapping[row['id']] == replacements[row['id']] for row in rows)
    assert capture_baseline(path) == before


def test_existing_type_refuses_silent_publication_of_absent_version(envelope, target):
    factory, path = target
    older = deepcopy(envelope)
    head = next(row for row in older['section']['project_deliverable_types'] if row['id'] == older['ids']['main']['id'])
    head['revision'] += 10  # existing head is newer, but lacks the incoming v2
    older['section']['project_deliverable_type_versions'] = [row for row in older['section']['project_deliverable_type_versions']
        if row['type_id'] != head['id'] or row['number'] == 1]
    older['section']['project_reference_changes'] = []
    replacements = mapping(envelope)
    with factory() as db:
        _insert_globals(db, older, replacements)
    before = capture_baseline(path)
    incoming = mapping(envelope)
    incoming[envelope['ids']['typology']['id']] = replacements[envelope['ids']['typology']['id']]
    with factory() as db, pytest.raises(HTTPException) as error:
        reconcile(db, envelope, incoming)
    assert error.value.status_code == 409 and error.value.detail['table'] == 'project_deliverable_type_versions'
    assert capture_baseline(path) == before


def test_id_and_business_code_pointing_to_different_heads_are_refused(envelope, store):
    value = deepcopy(envelope)
    value['section']['project_deliverable_types'][0]['id'] = value['ids']['unused']['id']
    replacements = mapping(value)
    with store[0]() as db, pytest.raises(HTTPException) as error:
        reconcile(db, value, replacements)
    assert error.value.status_code == 409


def test_missing_schema_is_refused_without_implicit_ddl(tmp_path):
    path = tmp_path / 'no-l3.db'
    engine = create_engine(f'sqlite:///{path}')
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables if table not in DELIVERABLE_TABLES])
    before = capture_baseline(path)
    with sessionmaker(bind=engine)() as db, pytest.raises(HTTPException) as error:
        archive_store.export_references(db, Base.metadata, {})
    assert error.value.status_code == 409 and capture_baseline(path) == before
    engine.dispose()
