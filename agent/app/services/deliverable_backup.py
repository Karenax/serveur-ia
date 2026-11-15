"""L3 portable file bindings without importing runtime DB/config/ORM modules."""
import hashlib
from pathlib import Path, PurePosixPath
import sqlite3

from .deliverable_manifest import check_row


def _rows(path):
    with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'project_deliverable_file_versions' not in tables:
            return []
        versions = [dict(row) for row in db.execute('SELECT * FROM project_deliverable_file_versions')]
        if not versions:
            return []
        if 'project_deliverable_version_metadata' not in tables:
            raise ValueError('Métadonnées de livrables absentes : sauvegarde/restauration refusée')
        metadata = {row['version_id']: dict(row) for row in db.execute('SELECT * FROM project_deliverable_version_metadata')}
        for row in versions:
            current = metadata.get(row['id'])
            if not current or current['project_id'] != row['project_id']:
                raise ValueError('Métadonnées de livrable incohérentes')
            try:
                check_row(row)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError('Manifeste de version incohérent') from exc
            row['current_path'] = current.get('storage_path') or row['path']
        return versions


def _digest(path):
    digest = hashlib.sha256()
    size = 0
    try:
        with Path(path).open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise ValueError('Fichier de livrable absent ou inaccessible') from exc
    return digest.hexdigest(), size


def collect_bindings(database, erp_home, storage):
    bindings = {}
    roots = {'erp': Path(erp_home).resolve(), 'storage': Path(storage).resolve()}
    for row in _rows(database):
        original = Path(row['current_path'])
        path = original.resolve()
        area = next((key for key, root in roots.items() if path.is_relative_to(root)), None)
        if area is None or not path.is_file() or original.is_symlink():
            raise ValueError('Fichier de livrable absent ou hors stockage géré')
        digest, size = _digest(path)
        if (digest, size) != (row['sha256'], row['size_bytes']):
            raise ValueError('Fichier de livrable modifié : restaurer la version originale')
        bindings[row['id']] = {'area': area, 'name': path.relative_to(roots[area]).as_posix(),
                              'project_id': row['project_id'], 'sha256': digest, 'size_bytes': size}
    return bindings


def validate_bindings(database, source, manifest):
    rows = _rows(database)
    bindings = manifest.get('deliverable_files')
    if bindings is None:
        # Older offline v1 snapshots can be resolved by exact content hashes,
        # never by trusting an absolute path from another machine.
        bindings = {}
        for row in rows:
            candidates = sorted(name for name, digest in manifest['files'].items()
                                if name.split('/')[0] in {'erp', 'storage'} and digest == row['sha256'])
            if not candidates:
                raise ValueError('Fichier de livrable absent du manifeste de sauvegarde')
            area, name = candidates[0].split('/', 1)
            bindings[row['id']] = {'area': area, 'name': name, 'project_id': row['project_id'],
                                  'sha256': row['sha256'], 'size_bytes': row['size_bytes']}
    if not isinstance(bindings, dict) or set(bindings) != {row['id'] for row in rows}:
        raise ValueError('Propriétaires de fichiers de livrables absents ou inconnus')
    for row in rows:
        entry = bindings[row['id']]
        if (not isinstance(entry, dict) or set(entry) != {'area', 'name', 'project_id', 'sha256', 'size_bytes'}
                or not isinstance(entry['area'], str) or entry['area'] not in {'erp', 'storage'}
                or not isinstance(entry['name'], str) or not isinstance(entry['project_id'], str)
                or not isinstance(entry['sha256'], str) or type(entry['size_bytes']) is not int):
            raise ValueError('Liaison de fichier de livrable invalide')
        relative = PurePosixPath(entry['name'])
        if (relative.is_absolute() or '..' in relative.parts or '\\' in entry['name'] or ':' in entry['name']
                or not relative.parts or relative.as_posix() != entry['name']):
            raise ValueError('Chemin de livrable interdit')
        name = entry['area'] + '/' + entry['name']
        original = Path(source) / name
        path = original.resolve()
        if not path.is_relative_to(Path(source).resolve()) or original.is_symlink():
            raise ValueError('Fichier de livrable hors sauvegarde')
        if (any(entry[key] != row[key] for key in ('project_id', 'sha256', 'size_bytes'))
                or manifest['files'].get(name) != row['sha256'] or _digest(path) != (row['sha256'], row['size_bytes'])):
            raise ValueError('Liaison ou contenu de livrable incohérent')
    return bindings


def relocate_bindings(database, output, bindings):
    if not bindings:
        return
    with sqlite3.connect(database) as db:
        columns = {row[1] for row in db.execute('PRAGMA table_info(project_deliverable_version_metadata)')}
        if 'storage_path' not in columns:
            # Only the new restored copy is extended; the source snapshot is
            # already fully backed up and remains byte-for-byte unchanged.
            db.execute("ALTER TABLE project_deliverable_version_metadata ADD COLUMN storage_path TEXT NOT NULL DEFAULT ''")
        for identity, entry in bindings.items():
            target = Path(output) / entry['area'] / entry['name']
            changed = db.execute('UPDATE project_deliverable_version_metadata SET storage_path=? WHERE version_id=? AND project_id=?',
                                 (str(target), identity, entry['project_id']))
            if changed.rowcount != 1:
                raise ValueError('Métadonnées de livrable absentes dans la copie restaurée')
