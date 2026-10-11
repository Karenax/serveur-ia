"""Durable server generation and read-only inventory, without secret values."""
import secrets
import time
from pathlib import Path
from core import read_json, write_json
from wg_crypto import private_directory


def generation(home):
    directory = Path(home) / 'securite'
    private_directory(directory)
    path = directory / 'generation.json'
    if path.exists():
        value = read_json(path)
        if not isinstance(value, dict) or not isinstance(value.get('id'), str) or len(value['id']) != 32 or any(c not in '0123456789abcdef' for c in value['id']) or type(value.get('restored')) is not bool:
            raise ValueError('État de synchronisation serveur illisible ; original conservé.')
        return value
    value = {'id': secrets.token_hex(16), 'restored': False}
    write_json(path, value)
    return value


def new_generation(home):
    generation(home)
    value = {'id': secrets.token_hex(16), 'restored': True}
    write_json(Path(home) / 'securite' / 'generation.json', value)
    return value


def installation_id(home):
    directory=Path(home)/'securite'
    private_directory(directory)
    path=directory/'installation.json'
    if path.exists():
        value=read_json(path)
        if not isinstance(value,dict) or not isinstance(value.get('id'),str) or len(value['id'])!=32 or any(c not in '0123456789abcdef' for c in value['id']):
            raise ValueError('Identité serveur illisible ; original conservé.')
        return value['id']
    value=secrets.token_hex(16)
    write_json(path,{'id':value})
    return value


def inventory(controller):
    home = controller.home
    names = [('reglages.json', 'configuration'), ('reglages-par-defaut.json', 'configuration'),
             ('derniers-reglages-valides.json', 'configuration'), ('base-strata.json', 'configuration'),
             ('acces-distants.json', 'access'), ('wireguard.json', 'access'), ('comptes.json', 'access'),
             ('exploitation.json', 'configuration'), ('recherche-web.dpapi', 'secret'),
             ('securite/revocations.json', 'security'), ('securite/generation.json', 'security')]
    files = [{'name': name, 'exists': (home / name).is_file(),
              'size': (home / name).stat().st_size if (home / name).is_file() else 0,
              'category': category, 'included': category != 'security'} for name, category in names]
    workspace = controller.remote.workspace
    owner_count=len(controller.remote.metadata()['clients'])
    with workspace.db() as db:
        counts = {label: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                  for label, table in [('history_count', 'client_histories'), ('projects', 'projects'),
                                       ('documents', 'documents'), ('jobs', 'jobs')]}
        counts['owners'] = owner_count
        counts['workspace_bytes'] = workspace.usage(db)
    return {'version': 1, 'created_at': time.time(), 'storage': counts, 'files': files,
            'client_directories':controller.client_storage.status() if hasattr(controller,'client_storage') else None,
            'migration': {'workspace_schema': 1, 'access_model': 'per_device'},
            'limits': {'global_bytes': 128 * 1024 * 1024, 'wireguard_request_bytes': 2 * 1024 * 1024},
            'decisions': ['Les sauvegardes couvrent les données déjà synchronisées.',
                          'Les révocations restent valables après restauration.',
                          'Chaque appareil conserve son identité et son espace.',
                          'Modèles, caches et outils de compilation exclus par défaut.']}
