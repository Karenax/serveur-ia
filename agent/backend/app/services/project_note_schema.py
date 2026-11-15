"""Explicit backup-first note installation; no project or note seeds."""
from sqlalchemy import inspect
from sqlalchemy.schema import CreateTable

from ..project_note_models import NOTE_TABLES, NoteVersion, NoteSourceImport
from .document_schema_rules import _sql
from .project_planning_migration import read_connection


def note_triggers():
    triggers = {}
    for table in ('project_note_versions', 'project_note_attachments', 'project_note_imports'):
        for action in ('UPDATE', 'DELETE'):
            name = f'trg_{table}_{action.lower()}_immutable'
            condition = ''
            if table in {'project_note_versions', 'project_note_imports'} and action == 'UPDATE':
                model = NoteVersion if table == 'project_note_versions' else NoteSourceImport
                same = ' AND '.join(f'NEW.{column.name} IS OLD.{column.name}' for column in model.__table__.c
                                    if column.name != 'execution_blocked')
                # Offline restoration may only freeze a historical nonce. It
                # can never unfreeze it or alter its capture/actor/bindings.
                condition = f'WHEN NOT (OLD.execution_blocked=0 AND NEW.execution_blocked=1 AND {same}) '
            triggers[name] = (f'CREATE TRIGGER {name} BEFORE {action} ON {table} {condition}'
                              "BEGIN SELECT RAISE(ABORT, 'Note history and attachments are immutable'); END")
    name = 'trg_project_notes_delete_retained'
    triggers[name] = (f'CREATE TRIGGER {name} BEFORE DELETE ON project_notes '
                      "BEGIN SELECT RAISE(ABORT, 'Notes must be retained'); END")
    name = 'trg_project_note_versions_sequence'
    triggers[name] = (f'CREATE TRIGGER {name} BEFORE INSERT ON project_note_versions '
        'WHEN NEW.revision != COALESCE((SELECT MAX(revision) FROM project_note_versions WHERE note_id=NEW.note_id),0)+1 '
        "OR json_extract(NEW.snapshot,'$.revision') IS NOT NEW.revision "
        "OR json_extract(NEW.snapshot,'$.actor_id') IS NOT NEW.actor_id "
        "OR json_extract(NEW.snapshot,'$.command_id') IS NOT NEW.command_id "
        "OR (NEW.revision>1 AND EXISTS (SELECT 1 FROM project_note_imports i WHERE i.note_id=NEW.note_id AND i.source_kind='external_office')) "
        "OR (json_extract(NEW.snapshot,'$.operation')='restore' AND (NEW.restored_version_id IS NULL "
        "OR NOT EXISTS (SELECT 1 FROM project_note_versions v WHERE v.id=NEW.restored_version_id "
        "AND v.project_id=NEW.project_id AND v.note_id=NEW.note_id AND v.revision<NEW.revision))) "
        "OR (json_extract(NEW.snapshot,'$.operation')!='restore' AND NEW.restored_version_id IS NOT NULL) "
        "BEGIN SELECT RAISE(ABORT, 'Note version must append a consistent revision'); END")
    for action in ('INSERT', 'UPDATE'):
        name = f'trg_project_notes_{action.lower()}_head'
        condition = ('NOT EXISTS (SELECT 1 FROM project_note_versions v WHERE v.id=NEW.current_version_id '
            'AND v.note_id=NEW.id AND v.project_id=NEW.project_id AND v.revision=NEW.revision '
            "AND json_extract(v.snapshot,'$.title') IS NEW.title "
            "AND json_extract(v.snapshot,'$.plain_text') IS NEW.plain_text) "
            'OR NEW.revision != (SELECT MAX(revision) FROM project_note_versions WHERE note_id=NEW.id)')
        if action == 'UPDATE':
            condition += (' OR NEW.id != OLD.id OR NEW.project_id != OLD.project_id '
                          'OR NEW.created_at != OLD.created_at OR NEW.revision != OLD.revision+1')
        triggers[name] = (f'CREATE TRIGGER {name} BEFORE {action} ON project_notes WHEN {condition} '
                          "BEGIN SELECT RAISE(ABORT, 'Note head must match the next saved version'); END")
    name = 'trg_project_note_attachments_quota'
    triggers[name] = (f'CREATE TRIGGER {name} BEFORE INSERT ON project_note_attachments '
        'WHEN (SELECT COUNT(*) FROM project_note_attachments WHERE note_id=NEW.note_id)>=20 '
        'OR COALESCE((SELECT SUM(size_bytes) FROM project_note_attachments WHERE note_id=NEW.note_id),0)+NEW.size_bytes>26214400 '
                      "BEGIN SELECT RAISE(ABORT, 'Note attachment quota exceeded'); END")
    name = 'trg_project_note_imports_capture'
    triggers[name] = (f'CREATE TRIGGER {name} BEFORE INSERT ON project_note_imports '
        "WHEN json_extract(NEW.snapshot,'$.format') IS NOT 'agent-note-source-import' "
        "OR json_type(NEW.snapshot,'$.version') IS NOT 'integer' "
        "OR json_extract(NEW.snapshot,'$.version') IS NOT 1 "
        "OR json_extract(NEW.snapshot,'$.actor_id') IS NOT NEW.actor_id "
        "OR json_extract(NEW.snapshot,'$.command_id') IS NOT NEW.command_id "
        "OR json_extract(NEW.snapshot,'$.source_kind') IS NOT NEW.source_kind "
        "OR json_extract(NEW.snapshot,'$.bundle_sha256') IS NOT NEW.sha256 "
        "OR json_extract(NEW.snapshot,'$.bundle_size_bytes') IS NOT NEW.size_bytes "
        "OR (NEW.execution_blocked=0 AND (json_extract(NEW.snapshot,'$.project_id') IS NOT NEW.project_id "
        "OR json_extract(NEW.snapshot,'$.note_id') IS NOT NEW.note_id)) "
        "BEGIN SELECT RAISE(ABORT, 'Import capture must match immutable source metadata'); END")
    return triggers


def validate_note_schema(engine, *, require_prerequisites=True):
    if engine.dialect.name != 'sqlite':
        raise ValueError('Notes : stockage SQLite requis')
    with read_connection(engine) as db:
        inspector = inspect(db)
        existing = set(inspector.get_table_names())
        if require_prerequisites and 'projects' not in existing:
            raise ValueError('Notes : socle projet requis')
        for table in NOTE_TABLES:
            if table.name not in existing:
                continue
            statement = db.exec_driver_sql('SELECT sql FROM sqlite_master WHERE type=\'table\' AND name=?', (table.name,)).scalar()
            expected = str(CreateTable(table).compile(dialect=engine.dialect))
            if _sql(statement) != _sql(expected):
                raise ValueError('Schéma de notes incompatible : ' + table.name)
            indexes = {item['name']: item for item in inspector.get_indexes(table.name)}
            if any(indexes.get(index.name, {}).get('column_names') != [column.name for column in index.columns]
                   or bool(indexes[index.name]['unique']) != bool(index.unique) for index in table.indexes):
                raise ValueError('Index de notes incompatible : ' + table.name)
        installed = {row[0]: row[1] for row in db.exec_driver_sql("SELECT name,sql FROM sqlite_master WHERE type='trigger'")}
        expected = note_triggers()
        if any(name in installed and _sql(installed[name]) != _sql(statement) for name, statement in expected.items()):
            raise ValueError('Protection de notes incompatible')
        plan = {'created_tables': [table.name for table in NOTE_TABLES if table.name not in existing],
                'created_triggers': [name for name in expected if name not in installed]}
        populated = any(db.exec_driver_sql(f'SELECT 1 FROM {table.name} LIMIT 1').first()
                        for table in NOTE_TABLES if table.name in existing)
        if populated and (plan['created_tables'] or plan['created_triggers']):
            raise ValueError('Schéma de notes partiel avec données : restauration contrôlée requise')
        return plan


def install_note_schema(engine, *, backup):
    plan = validate_note_schema(engine)
    if plan['created_tables'] or plan['created_triggers']:
        backup()
        with engine.begin() as db:
            NOTE_TABLES[0].metadata.create_all(db, tables=list(NOTE_TABLES))
            for name in plan['created_triggers']:
                db.exec_driver_sql(note_triggers()[name])
    return plan
