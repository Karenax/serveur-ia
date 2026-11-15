"""Offline validator stays independent from runtime engines and refuses damage."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import sqlite

from app.services.document_backup import validate_document_history
from backend.app.project_document_models import DOCUMENT_FORM_TABLES
from backend.app.services import document_forms as forms
from backend.app.services.document_schema_rules import _sql, immutable_triggers, schema_specification
from tests.test_project_document_forms import store, install

__all__ = ['store']


def test_offline_schema_spec_matches_actual_declarations():
    spec = schema_specification()
    assert set(spec) == {table.name for table in DOCUMENT_FORM_TABLES}
    for table in DOCUMENT_FORM_TABLES:
        expected = spec[table.name]
        assert expected['columns'] == {column.name: {'type': column.type.compile(sqlite.dialect()),
            'nullable': column.nullable, 'default': _sql(column.server_default.arg if column.server_default is not None else '')}
            for column in table.c}
        assert expected['primary_key'] == [column.name for column in table.primary_key]
        assert expected['unique'] == sorted([list(value.columns.keys()) for value in table.constraints if isinstance(value, UniqueConstraint)])
        assert expected['checks'] == sorted(_sql(value.sqltext) for value in table.constraints if isinstance(value, CheckConstraint))
        foreign = [{'columns': list(value.column_keys), 'table': value.referred_table.name,
            'targets': [element.column.name for element in value.elements], 'on_update': value.onupdate or 'NO ACTION',
            'on_delete': value.ondelete or 'NO ACTION'} for value in table.foreign_key_constraints]
        assert expected['foreign_keys'] == sorted(foreign, key=lambda item: json.dumps(item, sort_keys=True))
        assert expected['indexes'] == {value.name: {'columns': [column.name for column in value.columns], 'unique': bool(value.unique)}
                                        for value in table.indexes}


def test_offline_validation_does_not_import_runtime_or_create_configured_home(store, tmp_path):
    _, factory, ids, path = store
    install(store)
    with factory() as db:
        forms.save_draft(db, ids[0], 'tdao', expected_revision=0)
        forms.save_search_preferences(db, expected_revision=0, items=forms.default_preferences())
        db.commit()
    forbidden = tmp_path / 'must-not-create-runtime'
    code = """import sys
from pathlib import Path
from app.services.document_backup import validate_document_history
validate_document_history(Path(sys.argv[1]))
assert not {'backend.app.db','backend.app.models','app.db','app.config','backend.app.services.document_file_access'} & set(sys.modules)
print('offline-only')
"""
    result = subprocess.run([sys.executable, '-c', code, str(path)], cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, 'MINIPILOT_HOME': str(forbidden)}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'offline-only' and not forbidden.exists()


@pytest.mark.parametrize('damage', ['snapshot', 'preferences', 'head', 'missing_trigger', 'changed_trigger', 'column'])
def test_offline_damage_refused_without_changing_any_source_bytes(store, damage):
    _, factory, ids, path = store
    install(store)
    with factory() as db:
        forms.save_draft(db, ids[0], 'tdao', expected_revision=0)
        forms.save_search_preferences(db, expected_revision=0, items=forms.default_preferences())
        db.commit()
    with sqlite3.connect(path) as db:
        if damage in {'snapshot', 'preferences'}:
            table = 'project_document_draft_versions' if damage == 'snapshot' else 'project_document_search_versions'
            trigger = 'trg_' + table + '_update_immutable'
            db.execute('DROP TRIGGER ' + trigger)
            db.execute(f'UPDATE {table} SET sha256=?', ('0'*64,))
            db.execute(immutable_triggers()[trigger])
        elif damage == 'head':
            db.execute('DROP TRIGGER trg_project_document_drafts_revision_cas')
            db.execute("UPDATE project_document_drafts SET overrides='{}', relative_path='missing.docx'")
            db.execute(immutable_triggers()['trg_project_document_drafts_revision_cas'])
        elif damage == 'missing_trigger':
            db.execute('DROP TRIGGER trg_project_document_draft_versions_update_immutable')
        elif damage == 'changed_trigger':
            db.execute('DROP TRIGGER trg_project_document_draft_versions_update_immutable')
            db.execute('CREATE TRIGGER trg_project_document_draft_versions_update_immutable BEFORE UPDATE '
                       'ON project_document_draft_versions BEGIN SELECT 1; END')
        elif damage == 'column':
            db.execute('ALTER TABLE project_document_drafts ADD COLUMN extra TEXT')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='invalide'):
        validate_document_history(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
