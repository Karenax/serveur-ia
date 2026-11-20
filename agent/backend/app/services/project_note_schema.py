"""Explicit backup-first note installation; no project or note seeds."""
from sqlalchemy import inspect
from sqlalchemy.schema import CreateTable

from ..project_note_models import NOTE_TABLES, NoteVersion, NoteSourceImport
from ..personal_note_models import PersonalNoteImage
from .document_schema_rules import _sql
from .project_planning_migration import read_connection
from .project_note_schema_rules import OFFICE_GUARD, SEQUENCE_TRIGGER, legacy_attachment_sql, legacy_sequence_sql


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
    name = SEQUENCE_TRIGGER
    triggers[name] = (f'CREATE TRIGGER {name} BEFORE INSERT ON project_note_versions '
        'WHEN NEW.revision != COALESCE((SELECT MAX(revision) FROM project_note_versions WHERE note_id=NEW.note_id),0)+1 '
        "OR json_extract(NEW.snapshot,'$.revision') IS NOT NEW.revision "
        "OR json_extract(NEW.snapshot,'$.actor_id') IS NOT NEW.actor_id "
        "OR json_extract(NEW.snapshot,'$.command_id') IS NOT NEW.command_id "
        f"OR ({OFFICE_GUARD} (SELECT 1 FROM project_note_imports i WHERE i.note_id=NEW.note_id AND i.source_kind='external_office')) "
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
        upgrades = []
        if require_prerequisites and 'projects' not in existing:
            raise ValueError('Notes : socle projet requis')
        for table in (*NOTE_TABLES, PersonalNoteImage.__table__):
            if table.name not in existing:
                continue
            statement = db.exec_driver_sql('SELECT sql FROM sqlite_master WHERE type=\'table\' AND name=?', (table.name,)).scalar()
            expected = str(CreateTable(table).compile(dialect=engine.dialect))
            table_name = f'CREATE TABLE {table.name} '
            statement = statement.replace(f'CREATE TABLE "{table.name}" ', table_name, 1)
            if _sql(statement) != _sql(expected):
                if table.name in {'project_note_attachments', 'personal_note_images'} and _sql(statement) == _sql(legacy_attachment_sql(expected)):
                    upgrades.append(table.name)
                else:
                    raise ValueError('Schéma de notes incompatible : ' + table.name)
            indexes = {item['name']: item for item in inspector.get_indexes(table.name)}
            if any(indexes.get(index.name, {}).get('column_names') != [column.name for column in index.columns]
                   or bool(indexes[index.name]['unique']) != bool(index.unique) for index in table.indexes):
                raise ValueError('Index de notes incompatible : ' + table.name)
        installed = {row[0]: row[1] for row in db.exec_driver_sql("SELECT name,sql FROM sqlite_master WHERE type='trigger'")}
        expected = note_triggers()
        for name, statement in expected.items():
            if name in installed and _sql(installed[name]) != _sql(statement):
                if name == SEQUENCE_TRIGGER and _sql(installed[name]) == _sql(legacy_sequence_sql(statement)):
                    upgrades.append(name)
                else:
                    raise ValueError('Protection de notes incompatible')
        plan = {'created_tables': [table.name for table in NOTE_TABLES if table.name not in existing],
                'created_triggers': [name for name in expected if name not in installed]}
        populated = any(db.exec_driver_sql(f'SELECT 1 FROM {table.name} LIMIT 1').first()
                        for table in NOTE_TABLES if table.name in existing)
        if populated and (plan['created_tables'] or plan['created_triggers']):
            raise ValueError('Schéma de notes partiel avec données : restauration contrôlée requise')
        if upgrades:
            plan['upgrades'] = upgrades
        return plan


def install_note_schema(engine, *, backup):
    plan = validate_note_schema(engine)
    if plan['created_tables'] or plan['created_triggers'] or plan.get('upgrades'):
        backup()
        with engine.begin() as db:
            db.exec_driver_sql('BEGIN IMMEDIATE')
            NOTE_TABLES[0].metadata.create_all(db, tables=list(NOTE_TABLES))
            triggers = note_triggers()
            to_create = set(plan['created_triggers'])
            for name in plan.get('upgrades', ()):
                if name == SEQUENCE_TRIGGER:
                    db.exec_driver_sql(f'DROP TRIGGER {name}')
                    to_create.add(name)
                    continue
                table = NOTE_TABLES[0].metadata.tables[name]
                temporary = f'{name}_upgrade'
                ddl = str(CreateTable(table).compile(dialect=engine.dialect))
                db.exec_driver_sql(ddl.replace(f'CREATE TABLE {name} ', f'CREATE TABLE {temporary} ', 1))
                db.exec_driver_sql(f'INSERT INTO {temporary} SELECT * FROM {name}')
                db.exec_driver_sql(f'DROP TABLE {name}')
                db.exec_driver_sql(f'ALTER TABLE {temporary} RENAME TO {name}')
                for index in table.indexes:
                    index.create(db)
                if name == 'project_note_attachments':
                    to_create.update(key for key in triggers if key.startswith('trg_project_note_attachments_'))
            for name in to_create:
                db.exec_driver_sql(triggers[name])
    return plan
