"""Read-only validation of private-note history and embedded images."""
from hashlib import sha256
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

from backend.app.project_note_schemas import ImageBlock, NoteContent, content_text

TABLES = {'personal_notes', 'personal_note_versions', 'personal_note_images'}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate(database):
    """Accept legacy databases without private notes; reject partial or corrupt data."""
    try:
        with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as db:
            db.execute('BEGIN')
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            present = TABLES & tables
            if not present:
                return
            if present != TABLES:
                raise ValueError('Tables de notes personnelles incomplètes')
            # SQLite may contain data written outside the API. Bound JSON before
            # loading it; escaped Unicode can occupy six bytes per character.
            if db.execute('''SELECT 1 FROM personal_note_versions WHERE
                typeof(content)<>'text' OR length(CAST(content AS BLOB))>12000000
                OR typeof(attachment_ids)<>'text' OR length(CAST(attachment_ids AS BLOB))>4096 LIMIT 1''').fetchone():
                raise ValueError('Contenu de note personnelle trop volumineux ou invalide')
            if db.execute('''SELECT 1 FROM personal_notes n
                LEFT JOIN personal_note_versions v ON v.id=n.current_version_id
                WHERE v.id IS NULL OR v.note_id<>n.id OR v.owner_id<>n.owner_id
                   OR v.revision<>n.revision OR v.title<>n.title LIMIT 1''').fetchone():
                raise ValueError('Version courante de note personnelle invalide')
            if db.execute('''SELECT 1 FROM personal_note_versions v
                LEFT JOIN personal_notes n ON n.id=v.note_id
                WHERE n.id IS NULL OR v.owner_id<>n.owner_id LIMIT 1''').fetchone():
                raise ValueError('Historique de note personnelle invalide')
            if db.execute('''SELECT 1 FROM personal_note_images i
                LEFT JOIN personal_notes n ON n.id=i.note_id WHERE n.id IS NULL LIMIT 1''').fetchone():
                raise ValueError('Image de note personnelle orpheline')
            for image_id, size, digest, actual_size in db.execute(
                    'SELECT id, size_bytes, sha256, length(data) FROM personal_note_images'):
                if (type(size) is not int or not 1 <= size <= MAX_IMAGE_BYTES or actual_size != size
                        or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
                    raise ValueError('Taille ou empreinte d’image de note personnelle invalide')
                data = db.execute('SELECT data FROM personal_note_images WHERE id=?', (image_id,)).fetchone()[0]
                if not isinstance(data, bytes) or sha256(data).hexdigest() != digest:
                    raise ValueError('Image de note personnelle endommagée')
            for note_id, revision, title, plain_text, current, owner in db.execute(
                    'SELECT id, revision, title, plain_text, current_version_id, owner_id FROM personal_notes'):
                versions = db.execute('''SELECT id, revision, title, content, attachment_ids
                    FROM personal_note_versions WHERE note_id=? AND owner_id=?''', (note_id, owner))
                for version_id, version_revision, version_title, raw_content, raw_ids in versions:
                    content = NoteContent.model_validate(json.loads(raw_content))
                    ids = json.loads(raw_ids)
                    if not isinstance(ids, list) or len(ids) > 20 or len(ids) != len(set(ids)):
                        raise ValueError('Liste d’images de note personnelle invalide')
                    for image_id in ids:
                        if not isinstance(image_id, str) or not db.execute(
                                'SELECT 1 FROM personal_note_images WHERE id=? AND note_id=?', (image_id, note_id)).fetchone():
                            raise ValueError('Image de note personnelle absente')
                    if any(isinstance(block, ImageBlock) and block.attachment_id not in ids for block in content.blocks):
                        raise ValueError('Image de note personnelle non liée')
                    if version_id == current and (version_revision != revision or version_title != title
                                                  or content_text(content) != plain_text):
                        raise ValueError('Contenu courant de note personnelle incohérent')
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise ValueError('Notes personnelles ou images invalides') from exc
