"""Read-only SQLite queue contract, without importing the application runtime."""
import json
from pathlib import Path

from .document_schema_rules import validate_sqlite_schema


def specification():
    value = json.loads((Path(__file__).resolve().parents[1] / 'data/document_jobs_schema.json').read_text(encoding='utf-8'))
    if (set(value) != {'format', 'version', 'tables', 'triggers'}
            or value['format'] != 'agent-document-sqlite-schema'
            or type(value['version']) is not int or value['version'] != 1):
        raise ValueError('Contrat SQLite de file documentaire incompatible')
    return value


def protections():
    return specification()['triggers']


def validate_queue_schema(db):
    contract = specification()
    return validate_sqlite_schema(db, specification=contract['tables'], triggers=contract['triggers'])
