"""Compare two isolated Agent restores and check their referenced mail and audio files."""

import argparse
import email
import email.policy
import hashlib
import json
import sqlite3
import wave
from contextlib import closing
from pathlib import Path


def database_summary(path):
    with closing(sqlite3.connect(path.resolve(strict=True).as_uri() + '?mode=ro', uri=True)) as db:
        tables = [row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts = {table: db.execute('SELECT count(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0]
                  for table in tables}
        return {'integrity': db.execute('PRAGMA integrity_check').fetchone()[0],
                'foreign_key_violations': len(db.execute('PRAGMA foreign_key_check').fetchall()),
                'counts': counts}


def checked_path(root, value):
    path = Path(value).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError('Une référence sort de la restauration')
    return path


def verify_files(root):
    result = {'mails': 0, 'html': 0, 'with_attachment': 0, 'audio': 0}
    with closing(sqlite3.connect((root / 'brain/project_brain.db').as_uri() + '?mode=ro', uri=True)) as db:
        for value, expected in db.execute("SELECT original_uri,sha256 FROM sources "
                                          "WHERE source_type='email' AND original_uri IS NOT NULL AND original_uri != ''"):
            raw = checked_path(root, value).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('Empreinte de mail incorrecte')
            message = email.message_from_bytes(raw, policy=email.policy.default)
            result['mails'] += 1
            result['html'] += any(part.get_content_type() == 'text/html' for part in message.walk())
            result['with_attachment'] += any(part.get_content_disposition() == 'attachment'
                                             and part.get_payload(decode=True) is not None for part in message.walk())
        for value, expected, size in db.execute('SELECT storage_path,sha256,size_bytes FROM meeting_session_chunks'):
            path = checked_path(root, value)
            if path.stat().st_size != size:
                raise ValueError('Taille de fragment audio incorrecte')
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    raise ValueError('Empreinte de fragment audio incorrecte')
            with wave.open(str(path), 'rb') as audio:
                while audio.readframes(65536):
                    pass
            result['audio'] += 1
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path)
    parser.add_argument('second', type=Path)
    args = parser.parse_args()
    roots = [args.first.resolve(strict=True), args.second.resolve(strict=True)]
    if roots[0] == roots[1]:
        raise ValueError('Deux restaurations distinctes sont nécessaires')
    databases = {}
    for name in ('brain/project_brain.db', 'erp/minipilot.db'):
        first, second = (database_summary(root / name) for root in roots)
        if (any(value['integrity'] != 'ok' or value['foreign_key_violations'] for value in (first, second))
                or first['counts'] != second['counts']):
            raise ValueError('Intégrité ou comptages des bases différents')
        databases[name] = {'tables': len(first['counts']), 'integrity': 'ok', 'foreign_key_violations': 0}
    files = verify_files(roots[1])
    print(json.dumps({'databases': databases, 'files': files}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
