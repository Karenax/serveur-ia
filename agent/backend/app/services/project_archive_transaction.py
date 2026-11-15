"""Owned, single-commit ERP/Brain transaction for the typed v6 archive.

No DDL, journal setting changes or filesystem writes. The two sessions issue
Core statements on one connection; only the Brain session translates its schema.
The caller's pending edits are never committed or rolled back by this adapter.
"""
from contextlib import contextmanager
import logging
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

SCHEMA = 'agent_archive_brain'
ROLLBACK_JOURNALS = frozenset({'delete', 'truncate', 'persist'})
logger = logging.getLogger(__name__)


class ArchiveSession(Session):
    def commit(self):
        raise RuntimeError('La transaction d’archive coordonnée possède le seul commit')


def _path(engine):
    if (not isinstance(engine, Engine) or engine.dialect.name != 'sqlite'
            or not engine.url.database or engine.url.database == ':memory:' or engine.url.query):
        raise HTTPException(409, 'L’archive v6 exige deux bases SQLite locales sur disque')
    path = Path(engine.url.database).resolve()
    if not path.is_file():
        raise HTTPException(409, 'Base d’archive absente ; aucune base ne sera créée implicitement')
    return path


def _prerequisites(connection):
    for schema in ('main', SCHEMA):
        journal = connection.exec_driver_sql(f'PRAGMA {schema}.journal_mode').scalar_one()
        synchronous = connection.exec_driver_sql(f'PRAGMA {schema}.synchronous').scalar_one()
        if journal not in ROLLBACK_JOURNALS or synchronous < 2:
            raise HTTPException(409, 'Journal SQLite incompatible avec l’import coordonné ; conserver la sauvegarde globale')
    if connection.exec_driver_sql('PRAGMA foreign_keys').scalar_one() != 1:
        raise HTTPException(409, 'Les relations SQLite doivent être protégées avant l’import coordonné')
    if connection.exec_driver_sql('PRAGMA query_only').scalar_one():
        raise HTTPException(409, 'Connexion SQLite en lecture seule')


def _brain_statement(state):
    state.update_execution_options(schema_translate_map={None: SCHEMA})


def _no_brain_orm_flush(session, *_):
    # ORM flushes bypass do_orm_execute. Archive inserts are explicit Core SQL;
    # rejecting an accidental ORM mutation prevents writes in the main schema.
    if session.new or session.dirty or session.deleted:
        raise RuntimeError('L’archive Brain exige des écritures SQL explicites')


@contextmanager
def coordinated(caller, brain_engine):
    """Attach configured Brain only, hold both locks, commit once, detach safely.

    This owns an independent connection and transaction. A caller may have only
    idle reads, never pending ORM changes, explicit SQL writes or a savepoint.
    SQLite handles rollback journals on process interruption before commit.
    File staging/recovery belongs to the transport and is not covered here.
    """
    if caller.new or caller.dirty or caller.deleted or caller.in_nested_transaction():
        raise HTTPException(409, 'Ouvrir une session dédiée à l’import ; modifications existantes conservées')
    if caller.in_transaction() and caller.connection().connection.driver_connection.in_transaction:
        raise HTTPException(409, 'Transaction existante conservée ; ouvrir une session dédiée à l’import')
    erp_engine = caller.get_bind()
    erp_path, brain_path = _path(erp_engine), _path(brain_engine)
    if erp_path.samefile(brain_path):
        raise HTTPException(409, 'ERP et Brain doivent être deux bases distinctes')
    with erp_engine.connect() as connection:
        attached = False
        try:
            databases = connection.exec_driver_sql('PRAGMA database_list').all()
            if any(name not in {'main', 'temp'} for _, name, _ in databases):
                raise HTTPException(409, 'Connexion déjà attachée à une autre base')
            connection.exec_driver_sql(f'ATTACH DATABASE ? AS {SCHEMA}', (str(brain_path),))
            attached = True
            _prerequisites(connection)
            connection.commit()  # Ends SQLAlchemy's preflight; no SQL writes.
            with connection.begin():
                connection.exec_driver_sql('BEGIN IMMEDIATE')
                # Acquires the attached database's write lock before any reuse
                # reconciliation. The predicate changes no existing cell.
                connection.exec_driver_sql(f'UPDATE {SCHEMA}.projects SET id=id WHERE id IS NULL')
                erp = ArchiveSession(bind=connection, autoflush=False, join_transaction_mode='rollback_only')
                brain = ArchiveSession(bind=connection, autoflush=False, join_transaction_mode='rollback_only')
                event.listen(brain, 'do_orm_execute', _brain_statement)
                event.listen(brain, 'before_flush', _no_brain_orm_flush)
                try:
                    yield erp, brain
                    erp.flush()
                    brain.flush()
                finally:
                    event.remove(brain, 'do_orm_execute', _brain_statement)
                    event.remove(brain, 'before_flush', _no_brain_orm_flush)
                    brain.close()
                    erp.close()
            caller.expire_all()
        finally:
            connection.rollback()
            # A failing commit hook/DBAPI commit can leave SQLite's transaction
            # active after SQLAlchemy has deassociated its RootTransaction.
            # End the actual driver transaction before detaching or pool return.
            if not connection.invalidated and connection.connection.driver_connection.in_transaction:
                connection.connection.driver_connection.rollback()
            if attached:
                try:
                    connection.exec_driver_sql(f'DETACH DATABASE {SCHEMA}')
                    connection.commit()
                except Exception:
                    # Never return an attached or failed connection to the pool.
                    connection.invalidate()
                    logger.exception('Connexion d’archive invalidée après échec du détachement')
