"""Rehearse a common project catalogue using isolated SQLite snapshots."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'lanceur'), str(ROOT / 'shared')]
from wg_crypto import private_directory

ASSOCIATIONS = ('documents', 'chunks', 'document_index', 'document_sources',
                'conversations', 'memories', 'jobs')


def readonly(path):
    return closing(sqlite3.connect(path.resolve(strict=True).as_uri() + '?mode=ro', uri=True))


def check_database(database):
    if database.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise ValueError('Une base source ne passe pas le contrôle d’intégrité.')
    if database.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('Une base source contient des références orphelines.')


def snapshot(source, target):
    with readonly(source) as reader, closing(sqlite3.connect(target)) as copy:
        reader.backup(copy)
        check_database(copy)


def private_projects(workspace):
    projects = dict(workspace.execute('SELECT id, owner FROM projects'))
    tables = {name for name, in workspace.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
    counts = {}
    for table in ASSOCIATIONS:
        if table not in tables:
            continue
        for project, owner in workspace.execute(f'SELECT project, owner FROM {table}'):
            if projects.get(project) != owner:
                raise ValueError('Une donnée appartient à un autre espace privé.')
        counts[table] = workspace.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
    for table in ('chunks', 'document_sources', 'document_index'):
        if table in tables and workspace.execute(
            f"""SELECT 1 FROM {table} s JOIN documents d ON d.id=s.document
                WHERE s.project!=d.project OR s.owner!=d.owner LIMIT 1"""
        ).fetchone():
            raise ValueError('Un passage ou un index ne correspond pas à son document privé.')
    return projects, counts


def rehearse(workspace, erp, brain, registry):
    private, counts = private_projects(workspace)
    managed = {key for key, in erp.execute('SELECT id FROM projects')}
    if private.keys() & managed:
        raise ValueError('Des identifiants entrent en collision. Rapprochement explicite requis.')
    brain_ids = {key for key, in brain.execute('SELECT id FROM projects')}
    links = list(erp.execute('SELECT project_id, brain_project_id FROM brain_links'))
    if any(key not in managed or target not in brain_ids for key, target in links):
        raise ValueError('Un lien entre le portefeuille et les connaissances est orphelin.')

    # Keep each private object and its citations in the owning store. The
    # catalogue records an explicit routing decision and keeps the original ID.
    with registry:
        registry.execute('''CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, owner TEXT,
            CHECK ((kind='private' AND owner IS NOT NULL) OR (kind='managed' AND owner IS NULL))
        )''')
        registry.execute('DELETE FROM projects')
        registry.executemany('INSERT INTO projects VALUES (?, ?, ?)',
                             [(key, 'private', owner) for key, owner in private.items()])
        registry.executemany('INSERT INTO projects VALUES (?, ?, NULL)', [(key, 'managed') for key in managed])
        for owner in set(private.values()):
            visible = {key for key, in registry.execute(
                "SELECT id FROM projects WHERE kind='private' AND owner=?", (owner,))}
            if visible != {key for key, expected in private.items() if expected == owner}:
                raise ValueError('Le catalogue change le périmètre d’un espace privé.')
    project_references = {'private': 0, 'managed': 0, 'missing': 0, 'owner_mismatch': 0}
    if workspace.execute("SELECT 1 FROM sqlite_schema WHERE name='client_histories'").fetchone():
        for owner, history in workspace.execute('SELECT owner, history FROM client_histories'):
            for conversation in json.loads(history).get('conversations', []):
                key = conversation.get('project_id')
                if key is None:
                    continue
                if key in private:
                    kind = 'private' if private[key] == owner else 'owner_mismatch'
                else:
                    kind = 'managed' if key in managed else 'missing'
                project_references[kind] += 1
    return {
        'history_project_references': project_references,
        'private_projects': len(private), 'private_owners': len(set(private.values())),
        'archived_private_projects': workspace.execute('SELECT count(*) FROM projects WHERE archived=1').fetchone()[0],
        'managed_projects': len(managed), 'knowledge_links': len(links),
        'private_objects': counts, 'preserved_ids': len(private) + len(managed),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'erp', 'brain', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    private_directory(output)
    for name in ('workspace', 'erp', 'brain'):
        snapshot(getattr(args, name), output / f'{name}.sqlite3')
    with (readonly(output/'workspace.sqlite3') as workspace, readonly(output/'erp.sqlite3') as erp,
          readonly(output/'brain.sqlite3') as brain, closing(sqlite3.connect(output/'catalogue.sqlite3')) as registry):
        report = rehearse(workspace, erp, brain, registry)
        first = sorted(registry.execute('SELECT id, kind, owner FROM projects'))
        repeated = rehearse(workspace, erp, brain, registry)
        if repeated != report or sorted(registry.execute('SELECT id, kind, owner FROM projects')) != first:
            raise ValueError('Le résultat du rejeu du catalogue diffère.')
    report['replay_identical'] = True
    (output/'recette.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
