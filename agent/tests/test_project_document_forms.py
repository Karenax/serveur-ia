"""Durable forms, actual SQLite protections and concurrent saved choices."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import sqlite3
from threading import Barrier

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db_support import backup_sqlite, configure_sqlite
from backend.app.db import Base
from backend.app.models import NetworkLink, Project
from backend.app.project_document_models import DOCUMENT_FORM_TABLES, DocumentDraftVersion, DocumentSearchVersion, ProjectDocumentDraft
from backend.app.project_identity_models import IDENTITY_TABLES
from backend.app.project_planning_models import ProjectPlanningState
from backend.app.services import document_forms as forms
from backend.app.services.project_document_migration import install_document_schema, validate_document_schema
from backend.app.services.project_operator import Operator, operator_context


@pytest.fixture
def store(tmp_path):
    path = tmp_path / 'forms.db'
    engine = create_engine(f'sqlite:///{path}', connect_args={'check_same_thread': False})
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[Project.__table__, NetworkLink.__table__, *IDENTITY_TABLES,
                                            ProjectPlanningState.__table__])
    factory = sessionmaker(bind=engine)
    with factory() as db:
        first = Project(code='AIRB26LTH0205-A', title='LED', hourly_rate=99, margin_pct=14, tdao_prix_vente=123)
        second = Project(code='OTHER', title='Autre')
        db.add_all([first, second])
        db.flush()
        links = [NetworkLink(project_id=first.id, code='same', libelle='Premier', chemin='V:/first'),
                 NetworkLink(project_id=first.id, code='same', libelle='Doublon conservé', chemin='V:/second'),
                 NetworkLink(project_id=second.id, code='same', libelle='Autre', chemin='V:/other')]
        db.add_all(links)
        db.commit()
        ids = first.id, second.id, *(link.id for link in links)
    yield engine, factory, ids, path
    engine.dispose()


def install(store):
    engine, _, _, path = store
    return install_document_schema(engine, backup=lambda: backup_sqlite(path, path.with_suffix('.before.db')))


def assert_error(code, call):
    with pytest.raises(HTTPException) as error:
        call()
    assert error.value.status_code == code


def test_read_defaults_never_installs_seeds_or_touches_network(store, monkeypatch):
    engine, factory, ids, _ = store
    monkeypatch.setattr('backend.app.services.document_file_access.os.stat', lambda *args, **kwargs: pytest.fail('filesystem probe'))
    with factory() as db:
        assert forms.search_preferences(db)['revision'] == 0
        assert len(forms.search_preferences(db)['items']) == 8
        assert forms.draft(db, ids[0], 'tdao')['available'] is False
        assert forms.draft_history(db, ids[0], 'tdao') == []
        assert not db.new and not db.dirty
    assert not {table.name for table in DOCUMENT_FORM_TABLES} & set(inspect(engine).get_table_names())


def test_backup_precedes_ddl_preserves_all_legacy_rows_and_idempotent(store):
    engine, factory, ids, path = store
    calls = []
    def backup():
        assert 'project_document_drafts' not in inspect(engine).get_table_names()
        backup_sqlite(path, path.with_suffix('.before.db'))
        calls.append(True)
    assert len(install_document_schema(engine, backup=backup)['created_tables']) == 4
    assert calls == [True]
    assert install_document_schema(engine, backup=lambda: pytest.fail('duplicate backup')) == {
        'created_tables': [], 'created_triggers': []}
    with sqlite3.connect(path.with_suffix('.before.db')) as previous, sqlite3.connect(path) as current:
        for name in ('projects', 'network_links'):
            assert previous.execute(f'SELECT * FROM {name}').fetchall() == current.execute(f'SELECT * FROM {name}').fetchall()
    with factory() as db:
        assert forms.search_preferences(db)['available'] is True
        assert db.scalar(select(DocumentSearchVersion)) is None
        assert db.get(Project, ids[0]).tdao_prix_vente == 123


def test_failed_backup_and_incompatible_dormant_schema_make_no_ddl(store):
    engine, _, _, _ = store
    def failure():
        raise OSError('disk full')
    with pytest.raises(OSError):
        install_document_schema(engine, backup=failure)
    assert 'project_document_drafts' not in inspect(engine).get_table_names()
    with engine.begin() as db:
        db.exec_driver_sql('CREATE TABLE project_document_drafts (id TEXT PRIMARY KEY)')
    with pytest.raises(ValueError, match='incompatible'):
        install_document_schema(engine, backup=lambda: pytest.fail('preflight must precede backup'))


def test_empty_metadata_tables_are_dormant_until_explicit_protection_install(store):
    engine, factory, _, _ = store
    Base.metadata.create_all(engine, tables=list(DOCUMENT_FORM_TABLES))
    with factory() as db:
        assert forms.search_preferences(db)['available'] is False
        assert_error(409, lambda: forms.save_search_preferences(db, expected_revision=0, items=forms.default_preferences()))
    plan = install(store)
    assert plan['created_tables'] == [] and len(plan['created_triggers']) == 8


def test_preferences_save_reopen_conflict_and_restore_retains_raw_snapshots(store):
    _, factory, _, _ = store
    install(store)
    items = forms.default_preferences()
    items[0]['label'] = 'Libellé personnalisé'
    with factory() as db:
        first = forms.save_search_preferences(db, expected_revision=0, items=items)
        db.commit()
        raw = db.get(DocumentSearchVersion, first['version_id']).snapshot
        items[0]['active'] = False
        forms.save_search_preferences(db, expected_revision=1, items=items)
        db.commit()
    with factory() as db:
        assert forms.search_preferences(db)['revision'] == 2
        assert_error(409, lambda: forms.save_search_preferences(db, expected_revision=1, items=items))
        db.rollback()
        restored = forms.restore_search_preferences(db, expected_revision=2, version_id=first['version_id'])
        db.commit()
        assert restored['revision'] == 3
        assert restored['items'] == first['items']
        assert db.get(DocumentSearchVersion, first['version_id']).snapshot == raw
        assert len(forms.search_history(db)) == 3


@pytest.mark.parametrize('mutation', ['duplicate', 'format', 'absolute', 'traversal', 'financial', 'active_empty', 'boolean_revision', 'boolean_order'])
def test_invalid_preferences_cannot_write_any_version(store, mutation):
    _, factory, _, _ = store
    install(store)
    items = forms.default_preferences()
    expected = 0
    if mutation == 'duplicate':
        items[1] = deepcopy(items[0])
    if mutation == 'format':
        items[0]['format'] = 'DOCX' if items[0]['format'] != 'DOCX' else 'XLSX'
    if mutation == 'absolute':
        items[0]['relative_paths'] = ['V:/foreign']
    if mutation == 'traversal':
        items[0]['relative_paths'] = ['../escape']
    if mutation == 'financial':
        items[0]['hourly_rate'] = 85
    if mutation == 'active_empty':
        items[0]['filename_patterns'] = []
    if mutation == 'boolean_revision':
        expected = False
    if mutation == 'boolean_order':
        items[0]['order'] = True
    with factory() as db:
        assert_error(422, lambda: forms.save_search_preferences(db, expected_revision=expected, items=items))
        db.rollback()
        assert db.scalar(select(DocumentSearchVersion)) is None


def test_draft_choice_override_reopen_history_restore_and_finance_unchanged(store):
    _, factory, ids, _ = store
    install(store)
    with factory() as db:
        first = forms.save_draft(db, ids[0], 'tdao', expected_revision=0, link_id=ids[2],
                                relative_path=r'Etudes\Trame.xlsx', overrides={'description': 'Texte propre au document'})
        db.commit()
        raw = db.get(DocumentDraftVersion, first['version_id']).snapshot
        forms.save_draft(db, ids[0], 'tdao', expected_revision=1, link_id=ids[3], overrides={'description': 'Nouvelle saisie'})
        db.commit()
    with factory() as db:
        assert forms.draft(db, ids[0], 'tdao')['revision'] == 2
        assert forms.draft(db, ids[0], 'tdsp')['revision'] == 0
        assert forms.draft(db, ids[1], 'tdao')['revision'] == 0
        assert_error(409, lambda: forms.save_draft(db, ids[0], 'tdao', expected_revision=1))
        db.rollback()
        result = forms.restore_draft(db, ids[0], 'tdao', expected_revision=2, version_id=first['version_id'])
        db.commit()
        assert result['revision'] == 3 and result['relative_path'] == 'Etudes/Trame.xlsx'
        assert result['link_id'] == ids[2]
        assert db.get(DocumentDraftVersion, first['version_id']).snapshot == raw
        assert len(forms.draft_history(db, ids[0], 'tdao')) == 3
        project = db.get(Project, ids[0])
        assert (project.title, project.hourly_rate, project.margin_pct, project.tdao_prix_vente) == ('LED', 99, 14, 123)


@pytest.mark.parametrize('changes,code', [({'link_id': 'foreign'}, 404), ({'relative_path': '../escape'}, 422),
    ({'relative_path': 'unbound.docx'}, 422), ({'overrides': {'hourly_rate': '80'}}, 422),
    ({'overrides': {'project_code': 'FAKE'}}, 422), ({'overrides': []}, 422),
    ({'overrides': {'description': '\x01'}}, 422), ({'expected_revision': True}, 422)])
def test_invalid_draft_never_changes_head_or_historical_cells(store, changes, code):
    _, factory, ids, _ = store
    install(store)
    args = {'expected_revision': 0, **changes}
    if changes.get('link_id') == 'foreign':
        args['link_id'] = ids[4]
    with factory() as db:
        assert_error(code, lambda: forms.save_draft(db, ids[0], 'tdao', **args))
        db.rollback()
        assert db.scalar(select(ProjectDocumentDraft)) is None


def test_missing_selected_link_retains_history_and_requires_explicit_reselection(store):
    _, factory, ids, _ = store
    install(store)
    with factory() as db:
        saved = forms.save_draft(db, ids[0], 'tdao', expected_revision=0, link_id=ids[2])
        db.commit()
        db.delete(db.get(NetworkLink, ids[2]))  # Isolated fixture models legacy link removal, not product deletion.
        db.commit()
        assert forms.draft(db, ids[0], 'tdao')['warnings'] == ['selected_link_missing']
        assert_error(404, lambda: forms.restore_draft(db, ids[0], 'tdao', expected_revision=1, version_id=saved['version_id']))
        db.rollback()
        forms.save_draft(db, ids[0], 'tdao', expected_revision=1, link_id=ids[3])
        db.commit()
        assert len(forms.draft_history(db, ids[0], 'tdao')) == 2


def test_actual_sqlite_triggers_prevent_history_mutation_head_deletion_and_revision_skip(store):
    engine, factory, ids, _ = store
    install(store)
    with factory() as db:
        forms.save_draft(db, ids[0], 'tdao', expected_revision=0)
        forms.save_search_preferences(db, expected_revision=0, items=forms.default_preferences())
        db.commit()
    statements = ['UPDATE project_document_draft_versions SET actor_id="bad"', 'DELETE FROM project_document_draft_versions',
        'UPDATE project_document_search_versions SET actor_id="bad"', 'DELETE FROM project_document_search_versions',
        'DELETE FROM project_document_drafts', 'DELETE FROM project_document_search_states',
        'UPDATE project_document_drafts SET revision=revision+2', 'UPDATE project_document_search_states SET revision=revision+2']
    for statement in statements:
        with engine.begin() as db, pytest.raises(IntegrityError):
            db.exec_driver_sql(statement)


def test_foreign_keys_reject_cross_project_history(store):
    _, factory, ids, _ = store
    install(store)
    with factory() as db:
        saved = forms.save_draft(db, ids[0], 'tdao', expected_revision=0)
        db.commit()
        version = db.get(DocumentDraftVersion, saved['version_id'])
        db.add(DocumentDraftVersion(project_id=ids[1], draft_id=version.draft_id, document_id='tdao', revision=2,
                snapshot=version.snapshot, sha256=version.sha256, actor_id='local', bindings={}))
        with pytest.raises(IntegrityError):
            db.commit()


@pytest.mark.parametrize('role,scope', [('reader', None), ('editor', None), ('owner', 'scoped')])
def test_global_preferences_authorization_precedes_schema_access(store, role, scope, monkeypatch):
    _, factory, ids, _ = store
    monkeypatch.setattr(forms, '_available', lambda *args, **kwargs: pytest.fail('unauthorized schema read'))
    with factory() as db, operator_context(Operator('limited', role, frozenset({ids[0]}) if scope else None)):
        for call in (lambda: forms.search_history(db),
                     lambda: forms.save_search_preferences(db, expected_revision=0, items=[]),
                     lambda: forms.restore_search_preferences(db, expected_revision=0, version_id='unknown')):
            assert_error(403, call)


def test_project_scopes_and_reader_write_are_enforced_before_schema_access(store, monkeypatch):
    _, factory, ids, _ = store
    monkeypatch.setattr(forms, '_available', lambda *args, **kwargs: pytest.fail('unauthorized schema read'))
    with factory() as db, operator_context(Operator('reader', 'reader', frozenset({ids[0]}))):
        assert_error(404, lambda: forms.draft(db, ids[1], 'tdao'))
        assert_error(403, lambda: forms.save_draft(db, ids[0], 'tdao', expected_revision=0))
        assert_error(403, lambda: forms.restore_draft(db, ids[0], 'tdao', expected_revision=0, version_id='unknown'))


@pytest.mark.parametrize('kind', ['preferences', 'draft'])
def test_two_actual_sessions_have_exactly_one_cas_winner(store, kind):
    _, factory, ids, _ = store
    install(store)
    barrier = Barrier(2)
    def worker(label):
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                if kind == 'draft':
                    forms.save_draft(db, ids[0], 'tdao', expected_revision=0, overrides={'description': label})
                else:
                    items = forms.default_preferences()
                    items[0]['label'] = label
                    forms.save_search_preferences(db, expected_revision=0, items=items)
                db.commit()
                return 'saved'
            except HTTPException as exc:
                db.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(worker, ['premier', 'second']), key=str) == [409, 'saved']
    with factory() as db:
        history = forms.draft_history(db, ids[0], 'tdao') if kind == 'draft' else forms.search_history(db)
        assert len(history) == 1 and history[0]['revision'] == 1


def test_missing_protection_with_data_fails_closed_and_controlled_install_backups_first(store):
    engine, factory, ids, path = store
    install(store)
    with factory() as db:
        saved = forms.save_draft(db, ids[0], 'tdao', expected_revision=0)
        db.commit()
    with engine.begin() as db:
        db.exec_driver_sql('DROP TRIGGER trg_project_document_draft_versions_update_immutable')
    with factory() as db:
        assert_error(409, lambda: forms.draft(db, ids[0], 'tdao'))
    calls = []
    def backup():
        backup_sqlite(path, path.with_suffix('.repair.db'))
        calls.append(True)
    install_document_schema(engine, backup=backup)
    assert calls == [True]
    with factory() as db:
        assert forms.draft(db, ids[0], 'tdao')['version_id'] == saved['version_id']


def test_populated_partial_schema_refused_before_backup(store):
    engine, _, ids, _ = store
    ProjectDocumentDraft.__table__.create(engine)
    with engine.begin() as db:
        db.execute(ProjectDocumentDraft.__table__.insert().values(project_id=ids[0], document_id='tdao', revision=1))
    with pytest.raises(ValueError, match='partiel avec données'):
        install_document_schema(engine, backup=lambda: pytest.fail('must refuse before backup'))


def test_raw_backup_into_new_root_reopens_identical_forms_and_immutable_versions(store, tmp_path):
    _, factory, ids, path = store
    install(store)
    with factory() as db:
        forms.save_draft(db, ids[0], 'tdao', expected_revision=0, link_id=ids[2], overrides={'description': 'Conservé'})
        forms.save_search_preferences(db, expected_revision=0, items=forms.default_preferences())
        db.commit()
        expected = forms.draft_history(db, ids[0], 'tdao')
    restored = tmp_path / 'new-root' / 'forms.db'
    backup_sqlite(path, restored)
    engine = create_engine(f'sqlite:///{restored}')
    configure_sqlite(engine)
    try:
        assert validate_document_schema(engine) == {'created_tables': [], 'created_triggers': []}
        with sessionmaker(bind=engine)() as db:
            assert forms.draft_history(db, ids[0], 'tdao') == expected
            assert forms.search_preferences(db)['revision'] == 1
    finally:
        engine.dispose()


def test_legacy_archive_refuses_populated_document_history_and_no_dormant_placeholders(store):
    _, factory, ids, _ = store
    from backend.app.services.project_archive import _validate_tables
    install(store)
    with factory() as db:
        project = dict(db.execute(select(Project.__table__).where(Project.id == ids[0])).mappings().one())
        assert_error(400, lambda: _validate_tables(Base.metadata, {'projects': [project], 'project_document_drafts': []}))
    # The complete export's early gate is covered separately without requiring
    # unrelated legacy tables: it must reject before querying any such tables.
    from backend.app.services.project_archive import _rows
    with factory() as db:
        forms.save_draft(db, ids[0], 'tdao', expected_revision=0)
        db.commit()
        assert_error(409, lambda: _rows(db, Base.metadata, ids[0]))


def test_runtime_init_preserves_document_guards_through_schema_v11(tmp_path, monkeypatch):
    from backend.app import db as runtime
    path = tmp_path / 'runtime.db'
    engine = create_engine(f'sqlite:///{path}')
    configure_sqlite(engine)
    monkeypatch.setattr(runtime, 'engine', engine)
    monkeypatch.setattr(runtime, 'DB_PATH', path)
    monkeypatch.setattr(runtime, 'APP_DIR', tmp_path)
    try:
        runtime.init_db()
        assert {table.name for table in DOCUMENT_FORM_TABLES} <= set(inspect(engine).get_table_names())
        assert validate_document_schema(engine) == {'created_tables': [], 'created_triggers': []}
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT max(version) FROM schema_migrations WHERE domain='erp'").scalar_one() == 11
    finally:
        engine.dispose()


@pytest.mark.parametrize('damage', ['trigger', 'default', 'quoted_literal'])
def test_preflight_rejects_semantically_different_protection_before_backup(store, damage):
    engine, _, _, _ = store
    install(store)
    with engine.begin() as db:
        if damage == 'trigger':
            db.exec_driver_sql('DROP TRIGGER trg_project_document_draft_versions_update_immutable')
            db.exec_driver_sql("CREATE TRIGGER trg_project_document_draft_versions_update_immutable "
                               "BEFORE UPDATE ON project_document_draft_versions BEGIN SELECT 1; END")
        else:
            # Direct isolated schema corruption reproduces a malformed dormant
            # installation. No product route uses writable_schema.
            db.exec_driver_sql('PRAGMA writable_schema=ON')
            before = db.exec_driver_sql("SELECT sql FROM sqlite_master WHERE name='project_document_drafts'").scalar_one()
            after = before.replace("DEFAULT '{}'", "DEFAULT '[]'") if damage == 'default' else before.replace("'tdao'", "'TDAO'")
            assert before != after
            db.exec_driver_sql("UPDATE sqlite_master SET sql=? WHERE name='project_document_drafts'", (after,))
            db.exec_driver_sql('PRAGMA writable_schema=OFF')
            version = db.exec_driver_sql('PRAGMA schema_version').scalar_one()
            db.exec_driver_sql(f'PRAGMA schema_version={version+1}')
    with pytest.raises(ValueError, match='incompatible'):
        install_document_schema(engine, backup=lambda: pytest.fail('must reject before backup'))


def test_forged_version_digest_and_head_payload_are_not_returned(store):
    engine, factory, ids, path = store
    install(store)
    with factory() as db:
        saved = forms.save_draft(db, ids[0], 'tdao', expected_revision=0)
        db.commit()
    with engine.begin() as db:
        db.exec_driver_sql('DROP TRIGGER trg_project_document_draft_versions_update_immutable')
        db.exec_driver_sql("UPDATE project_document_draft_versions SET sha256=? WHERE id=?", ('0'*64, saved['version_id']))
    install_document_schema(engine, backup=lambda: backup_sqlite(path, path.with_suffix('.corrupt-before-repair.db')))
    with factory() as db:
        assert_error(409, lambda: forms.draft(db, ids[0], 'tdao'))


def test_cached_reader_detects_new_revision_without_losing_local_text(store):
    _, factory, ids, _ = store
    install(store)
    with factory() as first:
        forms.save_draft(first, ids[0], 'tdao', expected_revision=0, overrides={'description': 'Initial'})
        first.commit()
        cached = forms.draft(first, ids[0], 'tdao')
        with factory() as second:
            forms.save_draft(second, ids[0], 'tdao', expected_revision=1, overrides={'description': 'Autre opérateur'})
            second.commit()
        local = {'description': 'Ma saisie conservée'}
        assert_error(409, lambda: forms.save_draft(first, ids[0], 'tdao', expected_revision=cached['revision'], overrides=local))
        first.rollback()
        assert local == {'description': 'Ma saisie conservée'}
        assert forms.draft(first, ids[0], 'tdao')['overrides'] == {'description': 'Autre opérateur'}


def test_restore_without_installation_fails_explicitly_and_never_queries_absent_head(store):
    _, factory, ids, _ = store
    with factory() as db:
        assert_error(409, lambda: forms.restore_draft(db, ids[0], 'tdao', expected_revision=0, version_id='unknown'))


def test_reopened_history_timestamps_keep_explicit_utc_offset(store):
    _, factory, ids, _ = store
    install(store)
    with factory() as db:
        forms.save_draft(db, ids[0], 'tdao', expected_revision=0)
        forms.save_search_preferences(db, expected_revision=0, items=forms.default_preferences())
        db.commit()
    with factory() as db:
        assert forms.draft_history(db, ids[0], 'tdao')[0]['created_at'].endswith('+00:00')
        assert forms.search_history(db)[0]['created_at'].endswith('+00:00')
