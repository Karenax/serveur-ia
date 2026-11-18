"""Validation rejects incomplete private-note histories without changing them."""
from io import BytesIO
import sqlite3

from PIL import Image
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db_support import configure_sqlite
from app.services.personal_note_backup import validate
from backend.app.db import Base
from backend.app.personal_note_models import PersonalNote, PersonalNoteImage, PersonalNoteVersion
from backend.app.project_note_schemas import NotePaste
from backend.app.services import note_clipboard, personal_notes
from backend.app.services.project_operator import Operator, operator_context
from tests import test_project_notes_core as core


def test_legacy_database_without_private_notes_is_accepted(tmp_path):
    database = tmp_path / 'legacy.db'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE existing_data (content TEXT)')
    validate(database)


def test_partial_private_note_schema_is_refused_without_creating_tables(tmp_path):
    database = tmp_path / 'partial.db'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE personal_notes (id TEXT)')
    with pytest.raises(ValueError, match='Notes personnelles'):
        validate(database)
    with sqlite3.connect(database) as db:
        assert [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")] == ['personal_notes']


@pytest.mark.parametrize('corruption', ['missing-image', 'wrong-owner', 'bad-current', 'bad-content'])
def test_broken_private_note_history_is_rejected(tmp_path, corruption):
    database = tmp_path / 'private.db'
    engine = create_engine('sqlite:///' + database.as_posix())
    configure_sqlite(engine)
    Base.metadata.create_all(engine, tables=[PersonalNote.__table__, PersonalNoteVersion.__table__, PersonalNoteImage.__table__])
    stream = BytesIO()
    Image.new('RGB', (4, 4), 'blue').save(stream, format='PNG')
    command = NotePaste(command_id=core.command(), title='Note fictive', expected_revision=0,
                        content=core.rich(), attachment_ids=[], insert_at=0)
    try:
        with sessionmaker(bind=engine)() as db, operator_context(Operator('test-owner', 'owner')):
            note = personal_notes.save(db, None, command, image=note_clipboard.read_image('capture.png', BytesIO(stream.getvalue())))['note']
            db.commit()
        validate(database)
    finally:
        engine.dispose()
    with sqlite3.connect(database) as db:
        if corruption == 'missing-image':
            db.execute('DELETE FROM personal_note_images WHERE id=?', (note['attachment_ids'][0],))
        elif corruption == 'wrong-owner':
            db.execute('UPDATE personal_note_versions SET owner_id=?', ('different-owner',))
        elif corruption == 'bad-current':
            db.execute('UPDATE personal_notes SET revision=revision+1')
        else:
            db.execute("UPDATE personal_note_versions SET content='{}'")
    with pytest.raises(ValueError, match='Notes personnelles'):
        validate(database)
