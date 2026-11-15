"""Stage the three Agent exports in a new directory without starting Agent."""

import argparse
import hashlib
import json
import shutil
import sqlite3
import stat
import zipfile
from contextlib import closing
from pathlib import Path, PurePosixPath


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect_database(path):
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
        integrity = db.execute('PRAGMA integrity_check').fetchall()
        foreign_keys = db.execute('PRAGMA foreign_key_check').fetchall()
        if integrity != [('ok',)] or foreign_keys:
            raise ValueError(f'Base invalide : {path.name}')


def import_exports(downloads, destination):
    downloads = downloads.resolve(strict=True)
    destination = destination.resolve()
    inputs = {name: downloads / name for name in ('minipilot.db', 'project_brain.db', 'storage.zip')}
    if destination.exists():
        raise FileExistsError('La destination doit être nouvelle')
    if destination == downloads or destination.is_relative_to(downloads):
        raise ValueError('La destination doit être extérieure aux fichiers fournis')
    for path in inputs.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    for name in ('minipilot.db', 'project_brain.db'):
        for suffix in ('-wal', '-shm'):
            if (downloads / (name + suffix)).exists():
                raise ValueError(f'Fichier SQLite associé présent : {name}{suffix}')
        inspect_database(inputs[name])

    with zipfile.ZipFile(inputs['storage.zip']) as archive:
        names = set()
        retained = []
        for entry in archive.infolist():
            name = entry.filename
            relative = PurePosixPath(name)
            if (not name or '\\' in name or ':' in name or relative.is_absolute()
                    or '..' in relative.parts or relative.parts[:1] != ('storage',)
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('Chemin interdit dans storage.zip')
            normalized = relative.as_posix().casefold()
            if normalized in names:
                raise ValueError('Chemin en double dans storage.zip')
            names.add(normalized)
            if len(relative.parts) > 1 and relative.parts[1].casefold() == 'multimodal':
                continue
            retained.append(entry)
        destination.mkdir(parents=True)
        for name, subdirectory in (('minipilot.db', 'erp'), ('project_brain.db', 'brain')):
            target = destination / subdirectory / name
            target.parent.mkdir()
            shutil.copyfile(inputs[name], target)
            if digest(target) != digest(inputs[name]):
                raise ValueError(f'Copie incorrecte : {name}')
            inspect_database(target)
        for entry in retained:
            target = destination.joinpath(*PurePosixPath(entry.filename).parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)

    manifest = {
        'format': 'agent-export-staging-v1',
        'inputs': {name: {'size': path.stat().st_size, 'sha256': digest(path)}
                   for name, path in inputs.items()},
        'files_extracted': sum(not entry.is_dir() for entry in retained),
        'status': 'staged',
    }
    (destination / 'import.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(import_exports(args.downloads, args.destination), indent=2))


if __name__ == '__main__':
    main()
