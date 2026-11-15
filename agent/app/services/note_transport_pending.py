"""Interim refusal of populated notes until typed/offline transport is qualified.

Pure read-only SQLite, no ORM/configuration import. Existing archives/backups
remain usable when no note data exists. This guard is replaced by the L5.4
typed history/file validator, not used as the final notes transport behavior.
"""
import sqlite3
from pathlib import Path

NOTE_NAMES = ('project_notes', 'project_note_versions', 'project_note_attachments', 'project_note_imports')


def require_no_pending_notes(database: Path):
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        present = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if any(db.execute(f'SELECT 1 FROM {name} LIMIT 1').fetchone() for name in NOTE_NAMES if name in present):
            raise ValueError('Transport des notes non encore qualifié : sauvegarde/restauration refusée avant création du dossier de sortie')
