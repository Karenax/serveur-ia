"""Single commit, rollback, locks and recovery on two fictional SQLite files."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import subprocess
import sys

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker

from app.db import Base as BrainBase
from app.db_support import configure_sqlite
from app.models import Project as BrainProject, Source
from backend.app.db import Base
from backend.app.models import Project
from backend.app.services.project_archive_transaction import SCHEMA, coordinated
from backend.app.services.migration_guard import capture_baseline, compare_baseline


@pytest.fixture
def stores(tmp_path):
    paths = {'erp': tmp_path / 'erp.db', 'brain': tmp_path / 'brain.db'}
    engines = {key:create_engine(f'sqlite:///{path}', connect_args={'check_same_thread':False}) for key,path in paths.items()}
    for engine in engines.values():
        configure_sqlite(engine)
    Base.metadata.create_all(engines['erp'])
    BrainBase.metadata.create_all(engines['brain'])
    with engines['erp'].begin() as db:
        db.execute(Project.__table__.insert().values(id='kept-erp', code='ERP-OLD', title='Ancien ERP'))
    with engines['brain'].begin() as db:
        db.execute(BrainProject.__table__.insert().values(id='kept-brain', code='BRAIN-OLD', name='Ancien Brain'))
    yield engines, paths
    for engine in engines.values():
        engine.dispose()


def insert(erp, brain, suffix='new'):
    erp.execute(Project.__table__.insert().values(id='erp-'+suffix, code='ERP-'+suffix, title='Nouveau ERP'))
    brain.execute(BrainProject.__table__.insert().values(id='brain-'+suffix, code='BRAIN-'+suffix, name='Nouveau Brain'))
    brain.execute(Source.__table__.insert().values(id='source-'+suffix, project_id='brain-'+suffix,
                  source_type='meeting', original_uri='fictional://audio', sha256=suffix.ljust(64, '0')))


def baseline(paths):
    return {key:capture_baseline(path) for key,path in paths.items()}


def test_one_connection_one_commit_schema_translation_is_session_local_and_no_pool_leak(stores):
    engines, paths = stores
    before = baseline(paths)
    commits = []
    event.listen(engines['erp'], 'commit', lambda connection: commits.append(
        connection.connection.driver_connection.in_transaction))
    with sessionmaker(bind=engines['erp'])() as caller:
        assert caller.get(Project, 'kept-erp').title == 'Ancien ERP'
        with coordinated(caller, engines['brain']) as (erp, brain):
            assert erp.get(Project, 'kept-erp').title == 'Ancien ERP'
            assert brain.get(BrainProject, 'kept-brain').name == 'Ancien Brain'
            insert(erp, brain)
            assert erp.get(Project, 'erp-new').title == 'Nouveau ERP'
            assert brain.get(BrainProject, 'brain-new').name == 'Nouveau Brain'
        assert caller.get(Project, 'erp-new').title == 'Nouveau ERP'
    assert commits.count(True) == 1
    for key,engine in engines.items():
        assert compare_baseline(before[key], capture_baseline(paths[key]))['preserved']
        with engine.connect() as db:
            assert {row[1] for row in db.exec_driver_sql('PRAGMA database_list')} <= {'main', 'temp'}
            assert db.exec_driver_sql('PRAGMA foreign_key_check').all() == []
    with engines['brain'].connect() as db:
        assert db.execute(select(BrainProject.__table__.c.id)).scalars().all() == ['brain-new', 'kept-brain']


@pytest.mark.parametrize('stage', ['after_erp', 'after_brain', 'before_commit', 'inner_commit', 'orm_brain'])
def test_failure_rolls_back_both_stores_without_committing_or_losing_existing_cells(stores, stage):
    engines, paths = stores
    before = baseline(paths)
    with sessionmaker(bind=engines['erp'])() as caller:
        with pytest.raises(RuntimeError):
            with coordinated(caller, engines['brain']) as (erp, brain):
                erp.execute(Project.__table__.insert().values(id='new-erp', code='NEW', title='Nouveau'))
                if stage == 'after_erp':
                    raise RuntimeError('Injected after ERP')
                brain.execute(BrainProject.__table__.insert().values(id='new-brain', code='NEW', name='Nouveau'))
                if stage in {'after_brain', 'before_commit'}:
                    raise RuntimeError('Injected before commit')
                if stage == 'inner_commit':
                    erp.commit()
                else:
                    brain.add(BrainProject(id='wrong', code='wrong', name='Wrong schema'))
    assert baseline(paths) == before
    with engines['erp'].connect() as db:
        assert SCHEMA not in {row[1] for row in db.exec_driver_sql('PRAGMA database_list')}


@pytest.mark.parametrize('kind', ['pending_orm', 'flushed_sql', 'explicit_transaction', 'savepoint'])
def test_callers_pending_changes_are_neither_rolled_back_nor_committed(stores, kind):
    engines, paths = stores
    before = baseline(paths)
    with sessionmaker(bind=engines['erp'])() as caller:
        if kind == 'pending_orm':
            row = Project(id='pending', code='PENDING', title='À conserver')
            caller.add(row)
        elif kind == 'flushed_sql':
            caller.execute(Project.__table__.insert().values(id='pending', code='PENDING', title='À conserver'))
        elif kind == 'explicit_transaction':
            caller.execute(text('BEGIN'))
        else:
            caller.begin_nested()
        transaction = caller.get_transaction()
        with pytest.raises(HTTPException, match='session dédiée') as error:
            with coordinated(caller, engines['brain']):
                pytest.fail('Caller writes cannot be consumed')
        assert error.value.status_code == 409 and caller.get_transaction() is transaction
        if kind == 'pending_orm':
            assert row in caller.new
        elif kind == 'flushed_sql':
            assert caller.get(Project, 'pending').title == 'À conserver'
        caller.rollback()
    assert baseline(paths) == before


@pytest.mark.parametrize('store,pragma', [('erp', 'journal_mode=WAL'), ('brain', 'journal_mode=WAL'),
                                       ('erp', 'synchronous=OFF')])
def test_unsupported_modes_refused_without_forcing_settings(stores, store, pragma):
    engines, paths = stores
    if pragma.startswith('journal'):
        with engines[store].connect() as db:
            db.exec_driver_sql('PRAGMA '+pragma)
    else:
        event.listen(engines[store], 'connect', lambda raw, _:raw.execute('PRAGMA '+pragma))
        engines[store].dispose()
    before = baseline(paths)
    with sessionmaker(bind=engines['erp'])() as caller:
        with pytest.raises(HTTPException, match='Journal') as error:
            with coordinated(caller, engines['brain']):
                pytest.fail('Unsafe mode cannot be used')
        assert error.value.status_code == 409
    assert baseline(paths) == before


def test_brain_other_connections_setting_does_not_weaken_attached_connection(stores):
    engines, paths = stores
    event.listen(engines['brain'], 'connect', lambda raw, _:raw.execute('PRAGMA synchronous=OFF'))
    engines['brain'].dispose()
    before = baseline(paths)
    with engines['brain'].connect() as independent:
        assert independent.exec_driver_sql('PRAGMA synchronous').scalar_one() == 0
    with sessionmaker(bind=engines['erp'])() as caller:
        with coordinated(caller, engines['brain']) as (erp, _):
            # synchronous is connection-local, not a file's persistent mode.
            assert erp.connection().exec_driver_sql(f'PRAGMA {SCHEMA}.synchronous').scalar_one() >= 2
    assert baseline(paths) == before


def test_memory_and_missing_or_identical_files_cannot_be_created_or_used(stores, tmp_path):
    engines, paths = stores
    missing = tmp_path / 'absent.db'
    for brain in (create_engine('sqlite://'), create_engine(f'sqlite:///{missing}'), engines['erp']):
        with sessionmaker(bind=engines['erp'])() as caller:
            with pytest.raises(HTTPException) as error:
                with coordinated(caller, brain):
                    pytest.fail('Invalid database')
            assert error.value.status_code == 409
    assert not missing.exists()


def test_both_stores_locked_during_reconciliation(stores):
    engines, _ = stores
    def writer(engine, table, values):
        with engine.connect() as db:
            db.exec_driver_sql('PRAGMA busy_timeout=100')
            try:
                db.execute(table.insert().values(**values))
            except Exception as exc:
                return str(exc)
            return 'Unexpected unlocked write'
    with sessionmaker(bind=engines['erp'])() as caller:
        with coordinated(caller, engines['brain']):
            with ThreadPoolExecutor(2) as pool:
                erp = pool.submit(writer, engines['erp'], Project.__table__, {'id':'other', 'code':'OTHER', 'title':'Autre'})
                brain = pool.submit(writer, engines['brain'], BrainProject.__table__, {'id':'other', 'code':'OTHER', 'name':'Autre'})
                assert 'locked' in erp.result() and 'locked' in brain.result()


def test_process_exit_after_both_writes_recovers_both_files_on_reopen(stores, tmp_path):
    engines, paths = stores
    before = baseline(paths)
    script = tmp_path / 'interrupt.py'
    script.write_text('''import os, sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db_support import configure_sqlite
from backend.app.services.project_archive_transaction import coordinated
from backend.app.models import Project
from app.models import Project as BrainProject
erp = create_engine(sys.argv[1]); brain = create_engine(sys.argv[2])
configure_sqlite(erp)
with sessionmaker(bind=erp)() as caller:
    with coordinated(caller, brain) as (e, b):
        e.execute(Project.__table__.insert().values(id='interrupted',code='EXIT',title='ERP interrupted'))
        b.execute(BrainProject.__table__.insert().values(id='interrupted',code='EXIT',name='Brain interrupted'))
        os._exit(37)
''', encoding='utf-8')
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1])}
    process = subprocess.run([sys.executable, str(script), str(engines['erp'].url), str(engines['brain'].url)],
                             env=env, capture_output=True, text=True, timeout=30)
    assert process.returncode == 37, process.stderr
    # SQLite recovery is allowed to clear its own journal, but every old cell
    # and both store contents must be exactly the same after reopening.
    assert baseline(paths) == before
