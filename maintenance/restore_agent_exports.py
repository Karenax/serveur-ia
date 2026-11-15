"""Restore staged Agent exports with the project's offline restore routines."""

import argparse
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path, PureWindowsPath

AGENT = Path(__file__).resolve().parents[1] / 'agent'
sys.path.insert(0, str(AGENT))

from app.services.backup import restore_backup, restored_eg2_index  # noqa: E402


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare_manifest(source):
    source = source.resolve(strict=True)
    marker = json.loads((source / 'import.json').read_text(encoding='utf-8'))
    if marker.get('format') != 'agent-export-staging-v1' or marker.get('status') != 'staged':
        raise ValueError('Import Agent non reconnu')
    files = {}
    for path in source.rglob('*'):
        if path.is_symlink() or path.is_junction():
            raise ValueError('Lien interdit dans les données importées')
        if path.is_file() and path != source / 'backup.json':
            files[path.relative_to(source).as_posix()] = digest(path)
    for name, folder in [('minipilot.db', 'erp'), ('project_brain.db', 'brain')]:
        if files[f'{folder}/{name}'] != marker['inputs'][name]['sha256']:
            raise ValueError(f'Base importée modifiée : {name}')
    captures = {}
    brain = source / 'brain/project_brain.db'
    with closing(sqlite3.connect(brain.as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
        for identity, original, sha256, size in db.execute(
                'SELECT id,storage_path,sha256,size_bytes FROM meeting_session_chunks'):
            parts = PureWindowsPath(original).parts
            positions = [index for index, part in enumerate(parts) if part.lower() == 'storage']
            if len(positions) != 1:
                raise ValueError('Chemin de capture ambigu')
            relative = Path(*parts[positions[0]:]).as_posix()
            if not relative.startswith('storage/meeting-sessions/'):
                raise ValueError('Chemin de capture invalide')
            path = source / relative
            if files.get(relative) != sha256 or path.stat().st_size != size:
                raise ValueError('Fragment de réunion absent ou modifié')
            captures[identity] = {'path': relative, 'sha256': sha256, 'size_bytes': size}
    manifest = {'format': 'agent-offline-backup', 'version': 1,
                'files': files, 'meeting_session_files': captures}
    manifest_path = source / 'backup.json'
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding='utf-8'))
        if previous != manifest:
            raise ValueError('Les données importées ont changé depuis le premier contrôle')
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return len(captures)


def configure_restored_copy(destination):
    brain = destination / 'brain/project_brain.db'
    with closing(sqlite3.connect(brain)) as db, db:
        for key, raw in db.execute(
                "SELECT key,value FROM app_settings WHERE key IN ('memory','mail','ai')").fetchall():
            value = json.loads(raw or '{}')
            if key == 'memory' and value.get('index_path'):
                path = restored_eg2_index(value['index_path'], destination / 'storage')
                if path is None:
                    raise ValueError('Index configuré absent ou hors stockage')
                value['index_path'] = str(path)
            elif key == 'mail':
                value['auto_scan'] = False
            elif key == 'ai':
                value['api_key'] = ''
                value['enabled'] = False
                value['fallback_enabled'] = False
                value['fallback_autostart'] = False
            db.execute('UPDATE app_settings SET value=? WHERE key=?',
                       (json.dumps(value, ensure_ascii=False), key))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    destination = args.destination.resolve()
    if destination.exists() or destination == source or destination.is_relative_to(source):
        raise ValueError('La destination doit être neuve et extérieure aux données sources')
    count = prepare_manifest(source)
    result = restore_backup(source, destination)
    configure_restored_copy(destination)
    print(json.dumps({'restore': result, 'meeting_chunks': count}, indent=2))


if __name__ == '__main__':
    main()
