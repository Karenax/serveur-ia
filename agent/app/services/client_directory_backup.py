"""Capture managed client documents and relocate their links on restore."""
import os
import re
import shutil
import sqlite3
import stat
from contextlib import closing
from itertools import chain
from pathlib import Path, PurePosixPath, PureWindowsPath

DIRECTORY = 'dossiers-clients'
PROJECT_ID = re.compile(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}')


def _projects(erp_db):
    with closing(sqlite3.connect(erp_db.as_uri() + '?mode=ro', uri=True)) as db:
        return {row[0] for row in db.execute('SELECT id FROM projects')
                if isinstance(row[0], str) and PROJECT_ID.fullmatch(row[0])}


def client_directories(root, erp_db):
    if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError('Racine des dossiers clients inaccessible ou redirigée')
    for project_id in sorted(_projects(erp_db)):
        folder = root / project_id
        try:
            folder.lstat()
        except FileNotFoundError:
            continue
        if folder.resolve(strict=True) != folder or not folder.is_dir():
            raise ValueError('Dossier client irrégulier ou redirigé')
        yield folder


def client_files(folders):
    def fail(error):
        raise error

    for folder in folders:
        for directory, subdirectories, files in folder.walk(on_error=fail, follow_symlinks=False):
            entries = chain(((name, stat.S_ISDIR) for name in subdirectories),
                            ((name, stat.S_ISREG) for name in files))
            for name, expected_type in entries:
                path = directory / name
                metadata = path.lstat()
                if (stat.S_ISLNK(metadata.st_mode) or path.is_junction()
                        or not expected_type(metadata.st_mode)):
                    raise ValueError('Entrée redirigée ou irrégulière dans un dossier client')
                if expected_type is stat.S_ISREG:
                    yield path, metadata


def capture(root, output, erp_db):
    from backend.app.services.document_file_access import _handle_path

    def identity(metadata):
        return metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns

    folders = tuple(client_directories(root, erp_db))
    for path, metadata in client_files(folders):
        target = output / DIRECTORY / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        with path.open('rb') as stream, target.open('xb') as saved:
            if _handle_path(stream) != path or identity(os.fstat(stream.fileno())) != identity(metadata):
                raise ValueError('Emplacement du fichier client modifié pendant la sauvegarde')
            shutil.copyfileobj(stream, saved)
            if (saved.tell() != metadata.st_size or identity(os.fstat(stream.fileno())) != identity(metadata)
                    or identity(path.lstat()) != identity(metadata)):
                raise ValueError('Fichier client modifié pendant la sauvegarde')
    return {'root': str(root), 'projects': [folder.name for folder in folders]}


def validate(manifest, erp_db):
    section = manifest.get('client_directories')
    files = [PurePosixPath(name).parts for name in manifest['files'] if name.startswith(DIRECTORY + '/')]
    if section is None and not files:
        return
    if not isinstance(section, dict) or set(section) != {'root', 'projects'}:
        raise ValueError('Manifeste des dossiers clients invalide')
    projects = section['projects']
    if (not isinstance(section['root'], str)
            or not (PureWindowsPath(section['root']).is_absolute() or PurePosixPath(section['root']).is_absolute())
            or not isinstance(projects, list)
            or any(not isinstance(project, str) for project in projects)
            or not set(projects).issubset(_projects(erp_db))
            or any(len(parts) < 3 or parts[1] not in projects for parts in files)):
        raise ValueError('Dossiers clients hors des projets sauvegardés')


def relocate(output, db, section):
    if section is None:
        return
    root = output / DIRECTORY
    windows = PureWindowsPath(section['root'])
    source_path = PureWindowsPath if windows.is_absolute() else PurePosixPath
    old_root = source_path(section['root'])
    for project_id in section['projects']:
        folder = root / project_id
        folder.mkdir(parents=True, exist_ok=True)
        original = old_root / project_id
        links = db.execute('SELECT id, chemin FROM network_links WHERE project_id=? AND chemin IS NOT NULL',
                           (project_id,)).fetchall()
        for link_id, path in links:
            relative = source_path(path)
            if '..' not in relative.parts and relative.is_relative_to(original):
                db.execute('UPDATE network_links SET chemin=? WHERE id=?',
                           (str(folder.joinpath(*relative.relative_to(original).parts)), link_id))
