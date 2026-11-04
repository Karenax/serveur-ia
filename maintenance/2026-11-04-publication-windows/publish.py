"""Deliver Windows 3.5.58 using the established preserving publication procedure."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STAGE = ROOT / 'toolchain/releases-staging/windows-3.5.58'
sys.path[:0] = [str(ROOT / 'lanceur'), str(ROOT / 'client-qwen')]
spec = importlib.util.spec_from_file_location('windows_delivery', ROOT / 'maintenance/2026-10-31-publication-windows/publish.py')
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)
delivery.OUT = OUT
delivery.STAGE = STAGE
delivery.VERSION = '3.5.58'


def prepare():
    assert not (OUT / 'avant-livraison.json').exists(), 'Preparation exists; inspect before repeating'
    delivery.idle()
    current = delivery.get('/api/releases')
    assert current['server_version'] == '3.5.57' and current['verified']
    before = {'models': delivery.models(), 'files': delivery.preserved_files(),
        'users': delivery.prior.user_fingerprints(),
        'backups': delivery.backup_config(delivery.get('/api/backups')),
        'model_running': delivery.get('/api/state')['running'],
        'personal_identities': {p.stem: delivery.identity(delivery.profile(p))
            for p in (delivery.HOME / 'clients').glob('*.exe')},
        'old_version': current['server_version']}
    assert before['models']
    delivery.write('avant-livraison.json', before)
    job = delivery.post('/api/backups/create', {'kind': 'manual', 'protected': True})
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        state = delivery.get('/api/backups'); current = state['job']
        assert current['id'] == job['job']['id'], 'Backup job replaced'
        if current['state'] in ('succeeded', 'failed'): break
        time.sleep(1)
    else: raise TimeoutError('Backup did not finish')
    assert current['state'] == 'succeeded', current.get('message')
    backup = current['result']; path = Path(backup['file'])
    record = next(row for row in state['catalog'] if row['id'] == backup['id'])
    assert record['verified'] and delivery.digest(path) == record['sha256']
    delivery.write('sauvegarde-avant.json', {'file': str(path), 'sha256': record['sha256'],
        'verified': True, 'encrypted': True, 'timestamp': time.time(),
        'secondary': backup.get('secondary', {}).get('status')})
    print('Encrypted pre-publication backup verified.', flush=True)


def check():
    from PyInstaller.archive.readers import CArchiveReader
    import marshal
    import types
    archive = CArchiveReader(str(STAGE / 'Accès serveur Fred.exe'))
    resources = ('chat.html', 'workspace.html', 'ui.js', 'ui.css', 'conversation.js',
                 'attachments.js', 'selection.js', 'thinking.js', 'markdown.js', 'corrector.js', 'voice.js')
    for name in resources:
        assert archive.extract(name) == (ROOT / 'client-qwen' / name).read_bytes(), name
    assert archive.extract('wireguard-bridge.exe') == (ROOT / 'client-qwen/wireguard-bridge.exe').read_bytes()
    pyz = archive.open_embedded_archive('PYZ.pyz')
    assert '3.5.58' in pyz.extract('kiara_shared.version').co_consts
    # Compare the actual entry-point bytecode with the current client source.
    # PyInstaller changes filenames, so recursively normalize only co_filename.
    def normalized(code):
        return code.replace(co_filename='<source>', co_consts=tuple(
            normalized(value) if isinstance(value, types.CodeType) else value
            for value in code.co_consts))
    frozen = marshal.loads(archive.extract('client'))
    source = compile((ROOT / 'client-qwen/client.py').read_bytes(), '<source>', 'exec', optimize=0)
    assert normalized(frozen) == normalized(source), 'Entry point differs from current source'
    delivery.write('frozen-validation.json', {'passed': True, 'version': '3.5.58',
        'ui_matches_sources': True, 'client_bytecode_matches_sources': True,
        'wireguard_matches_published': True, 'resources': list(resources)})
    print('Frozen client, UI resources, version and WireGuard verified.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'check', 'publish', 'verify'))
    phase = parser.parse_args().phase
    if phase == 'prepare': prepare()
    elif phase == 'check': check()
    elif phase == 'publish': delivery.publish()
    else: delivery.verify_served()
