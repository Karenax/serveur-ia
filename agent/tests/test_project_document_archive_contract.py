"""Typed forms closure using rows really saved by the form services."""
from copy import deepcopy
from datetime import datetime
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import DateTime, create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from app.services.deliverable_manifest import freeze
from backend.app.db import Base
from backend.app.models import NetworkLink, Project
from backend.app.project_document_models import DOCUMENT_FORM_PROJECT_TABLES
from backend.app.project_identity_models import IDENTITY_TABLES
from backend.app.project_planning_models import ProjectPlanningState
from backend.app.services import document_forms as forms
from backend.app.services import project_document_archive as contract
from backend.app.services.project_document_migration import install_document_schema

@pytest.fixture
def envelope(tmp_path):
    file = tmp_path / 'source.db'
    engine = create_engine(f'sqlite:///{file}')
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[Project.__table__, NetworkLink.__table__, *IDENTITY_TABLES,
                                            ProjectPlanningState.__table__])
    install_document_schema(engine, backup=lambda: backup_sqlite(file, tmp_path / 'before.db'))
    factory = sessionmaker(bind=engine)
    with factory() as db:
        project = Project(code='AIRB26LTH0205-A', title='Recette documentaire')
        db.add(project)
        db.flush()
        links = [NetworkLink(project_id=project.id, code='same', libelle='Première', chemin='V:/fictitious/one'),
                 NetworkLink(project_id=project.id, code='same', libelle='Deuxième', chemin='V:/fictitious/two')]
        db.add_all(links)
        db.flush()
        forms.save_draft(db, project.id, 'tdao', expected_revision=0, link_id=links[0].id,
                         relative_path='Etudes/TDAO.xlsx', overrides={'description': project.id})
        forms.save_draft(db, project.id, 'tdao', expected_revision=1, link_id=links[1].id,
                         overrides={'description': links[0].id})
        forms.save_draft(db, project.id, 'tdsp', expected_revision=0, overrides={'agency_city': 'Nantes'})
        db.commit()
        db.delete(links[0])  # Only a fictional source models an already absent legacy link.
        db.commit()
        tables = {}
        for name in ('projects', 'network_links', *sorted(DOCUMENT_FORM_PROJECT_TABLES)):
            rows = db.execute(select(Base.metadata.tables[name])).mappings()
            tables[name] = [{key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()}
                            for row in rows]
        section = contract.section_for(tables)
    engine.dispose()
    return tables, section


def replacements(tables, section):
    ids = {row['id'] for name in ('projects', 'network_links', *contract.PROJECT_TABLES) for row in tables[name]}
    ids.update(section['unresolved_link_ids'])
    return {key: str(uuid.uuid4()) for key in ids}


def test_two_restorations_keep_raw_snapshot_and_text_without_nested_bindings(envelope):
    tables, section = envelope
    originals = deepcopy(tables)
    assert len(contract.validate(tables, section)['unresolved_link_ids']) == 1
    raw = {row['snapshot'] for row in tables['project_document_draft_versions']}
    text = {head['overrides'].get('description') for head in tables['project_document_drafts']}
    for _ in range(2):
        mapping = replacements(tables, section)
        documents, next_section = contract.remap(tables, section, mapping)
        native = {name: [{**row, 'id': mapping[row['id']], **({'project_id': mapping[row['project_id']]} if 'project_id' in row else {})}
                          for row in tables[name]] for name in ('projects', 'network_links')}
        tables, section = {**native, **documents}, next_section
        contract.validate(tables, section)
        assert {row['snapshot'] for row in tables['project_document_draft_versions']} == raw
        assert {head['overrides'].get('description') for head in tables['project_document_drafts']} == text
        assert all(set(row['bindings']) == {'project_id', 'draft_id', 'link_id'} for row in tables['project_document_draft_versions'])
    assert originals == envelope[0]


@pytest.mark.parametrize('damage', ['foreign_project', 'foreign_draft', 'duplicate_revision', 'missing_revision',
    'future_revision', 'wrong_hash', 'rehash_bad_choice', 'head_value', 'wrong_binding', 'nested_binding',
    'undeclared_missing_link', 'global_preferences', 'financial_override', 'boolean_revision', 'absolute_path'])
def test_corrupt_or_foreign_closure_is_refused_without_changes(envelope, damage):
    tables, section = deepcopy(envelope)
    version = tables['project_document_draft_versions'][0]
    head = next(row for row in tables['project_document_drafts'] if row['id'] == version['draft_id'])
    if damage == 'foreign_project':
        version['project_id'] = str(uuid.uuid4())
    elif damage == 'foreign_draft':
        version['draft_id'] = str(uuid.uuid4())
    elif damage == 'duplicate_revision':
        tables['project_document_draft_versions'].append(deepcopy(version))
    elif damage == 'missing_revision':
        tables['project_document_draft_versions'].remove(version)
    elif damage == 'future_revision':
        head['revision'] += 1
    elif damage == 'wrong_hash':
        version['sha256'] = '0' * 64
    elif damage == 'rehash_bad_choice':
        import json
        value = json.loads(version['snapshot'])
        value['choice']['overrides']['hourly_rate'] = '85'
        version['snapshot'], version['sha256'] = freeze(value)
    elif damage == 'head_value':
        head['overrides']['description'] = 'Contenu divergent'
    elif damage == 'wrong_binding':
        version['bindings']['project_id'] = str(uuid.uuid4())
    elif damage == 'nested_binding':
        version['bindings'] = {'previous': version['bindings']}
    elif damage == 'undeclared_missing_link':
        section['unresolved_link_ids'] = []
    elif damage == 'global_preferences':
        tables['project_document_search_versions'] = []
    elif damage == 'financial_override':
        head['overrides']['hourly_rate'] = '85'
    elif damage == 'boolean_revision':
        head['revision'] = True
    elif damage == 'absolute_path':
        head['relative_path'] = 'V:/foreign.xlsx'
    before = deepcopy((tables, section))
    with pytest.raises(HTTPException) as error:
        contract.validate(tables, section)
    assert error.value.status_code == 400
    assert (tables, section) == before


def test_missing_or_ambiguous_replacements_are_refused(envelope):
    tables, section = envelope
    mapping = replacements(tables, section)
    removed = mapping.pop(next(iter(mapping)))
    with pytest.raises(HTTPException):
        contract.remap(tables, section, mapping)
    mapping = {key: removed for key in replacements(tables, section)}
    with pytest.raises(HTTPException):
        contract.remap(tables, section, mapping)


def test_remapped_rows_reopen_under_real_fk_and_triggers_and_keep_target_common_preferences(envelope, tmp_path):
    tables, section = envelope
    mapping = replacements(tables, section)
    documents, next_section = contract.remap(tables, section, mapping)
    native = {name: [{**row, 'id': mapping[row['id']], **({'project_id': mapping[row['project_id']]} if 'project_id' in row else {})}
                      for row in tables[name]] for name in ('projects', 'network_links')}
    rebuilt = {**native, **documents}
    contract.validate(rebuilt, next_section)
    file = tmp_path / 'destination.db'
    engine = create_engine(f'sqlite:///{file}')
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[Project.__table__, NetworkLink.__table__, *IDENTITY_TABLES,
                                            ProjectPlanningState.__table__])
    install_document_schema(engine, backup=lambda: backup_sqlite(file, tmp_path / 'destination-before.db'))
    factory = sessionmaker(bind=engine)
    try:
        with factory() as db:
            items = forms.default_preferences()
            items[0]['label'] = 'Préférences de la destination'
            forms.save_search_preferences(db, expected_revision=0, items=items)
            db.commit()
            preferences = forms.search_history(db)
            for name in ('projects', 'network_links', 'project_document_drafts', 'project_document_draft_versions'):
                table = Base.metadata.tables[name]
                for original in rebuilt[name]:
                    row = deepcopy(original)
                    for column in table.c:
                        if isinstance(column.type, DateTime):
                            row[column.name] = datetime.fromisoformat(row[column.name])
                    db.execute(table.insert().values(**row))
            db.commit()
        with factory() as db:
            pid = rebuilt['projects'][0]['id']
            assert forms.search_history(db) == preferences
            history = forms.draft_history(db, pid, 'tdao')
            assert len(history) == 2
            assert history[0]['bindings']['project_id'] == pid
            original = next(row for row in tables['project_document_drafts'] if row['document_id'] == 'tdao')
            assert forms.draft(db, pid, 'tdao')['overrides'] == original['overrides']
    finally:
        engine.dispose()
