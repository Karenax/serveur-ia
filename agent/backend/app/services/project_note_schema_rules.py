"""Pure read-only schema/protection signature, without runtime configuration."""
import json
from pathlib import Path

from backend.app.services.document_schema_rules import _sql
from backend.app.services.project_note_history import PROJECT_TABLES
from backend.app.project_note_schemas import NOTE_ATTACHMENT_BUDGET

SEQUENCE_TRIGGER = 'trg_project_note_versions_sequence'
OFFICE_GUARD = "NEW.revision>1 AND json_extract(NEW.snapshot,'$.operation')!='delete' AND EXISTS"


def legacy_attachment_sql(sql):
    return sql.replace(f'size_bytes BETWEEN 1 AND {NOTE_ATTACHMENT_BUDGET}', 'size_bytes BETWEEN 1 AND 5242880')


def legacy_sequence_sql(sql):
    return sql.replace(OFFICE_GUARD, 'NEW.revision>1 AND EXISTS')


def specification():
    path = Path(__file__).resolve().parents[1] / 'data/notes_schema.json'
    value = json.loads(path.read_text(encoding='utf-8'))
    if (set(value) != {'format', 'version', 'tables', 'triggers'}
            or value['format'] != 'agent-note-sqlite-schema' or type(value['version']) is not int
            or value['version'] != 1 or set(value['tables']) != PROJECT_TABLES
            or len(value['triggers']) != 12):
        raise ValueError('Contrat SQLite de notes incompatible')
    return value


def validate_schema(db):
    spec = specification()
    existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    present = existing & PROJECT_TABLES
    if not present:
        return False
    for name in present:
        declared = spec['tables'][name]
        sql = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()[0]
        sql = sql.replace(f'CREATE TABLE "{name}" ', f'CREATE TABLE {name} ', 1)
        alternatives = [declared['sql']]
        if name == 'project_note_attachments':
            alternatives.append(legacy_attachment_sql(declared['sql']))
        if _sql(sql) not in {_sql(value) for value in alternatives}:
            raise ValueError('Schéma de notes incompatible : ' + name)
        indexes = {}
        for row in db.execute(f'PRAGMA index_list({name})'):
            quoted = row[1].replace('"', '""')
            indexes[row[1]] = {'columns': [col[2] for col in db.execute(f'PRAGMA index_info("{quoted}")')],
                               'unique': bool(row[2])}
        if any(indexes.get(key) != value for key, value in declared['indexes'].items()):
            raise ValueError('Index de notes incompatible : ' + name)
    installed = {row[0]: row[1] for row in db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")}
    if any(name in installed and _sql(installed[name]) not in {
            _sql(sql), _sql(legacy_sequence_sql(sql)) if name == SEQUENCE_TRIGGER else _sql(sql)
    } for name, sql in spec['triggers'].items()):
        raise ValueError('Protection de notes incompatible')
    complete = present == PROJECT_TABLES and set(spec['triggers']) <= installed.keys()
    populated = any(db.execute(f'SELECT 1 FROM {name} LIMIT 1').fetchone() for name in present)
    if populated and (not complete or 'projects' not in existing):
        raise ValueError('Schéma de notes partiel avec données')
    return complete
