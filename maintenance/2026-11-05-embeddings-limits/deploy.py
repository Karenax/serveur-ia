"""Server-only activation and synthetic end-to-end checks, without recording secrets."""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('KIARA_EVIDENCE_DIR', 'D:/Archives Kiara/preuves')) / '2026-11-05-embeddings-limits'
OUT.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(ROOT/'lanceur'), str(ROOT/'client-qwen')]
from validate_live_lots6_8 import get, post, models, preserved_files, backup_config, digest
from core import HOME
from releases import profile


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def write(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def prepare():
    assert not (OUT/'avant-livraison.json').exists(), 'Snapshot already exists'
    delivery = module('preserving_delivery', 'maintenance/2026-10-31-publication-windows/publish.py')
    delivery.idle()
    before = {'models': models(), 'files': preserved_files(),
              'users': delivery.prior.user_fingerprints(),
              'backups': backup_config(get('/api/backups'))}
    write('avant-livraison.json', before)
    job = post('/api/backups/create', {'kind':'manual', 'protected':True})
    deadline = time.monotonic()+300
    while time.monotonic()<deadline:
        state = get('/api/backups'); current = state['job']
        assert current['id']==job['job']['id']
        if current['state'] in ('succeeded','failed'):break
        time.sleep(1)
    else:raise TimeoutError('Backup timeout')
    assert current['state']=='succeeded', current.get('message')
    backup = current['result']
    record = next(row for row in state['catalog'] if row['id']==backup['id'])
    assert record['verified'] and digest(backup['file'])==record['sha256']
    write('sauvegarde-avant.json', {'verified':True, 'encrypted':True,
          'file':backup['file'], 'sha256':record['sha256'], 'timestamp':time.time()})
    print('Encrypted backup verified.', flush=True)


def activate():
    backup = json.loads((OUT/'sauvegarde-avant.json').read_text(encoding='utf-8'))
    assert backup['verified'] and time.time()-backup['timestamp']<3600
    assert digest(backup['file'])==backup['sha256']
    before = json.loads((OUT/'avant-livraison.json').read_text(encoding='utf-8'))
    delivery = module('preserving_delivery', 'maintenance/2026-10-31-publication-windows/publish.py')
    delivery.idle(); delivery.unchanged(before)
    restart = module('preserving_restart', 'maintenance/2026-10-21-api-embeddings/livrer.py')
    restart.OUT = OUT
    restart.restart()


def verify():
    deadline = time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            if get('/api/knowledge')['engine']['status']=='pret':break
        except OSError:pass
        time.sleep(1)
    else:raise TimeoutError('EG2 startup timeout')
    access = json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))
    active = {r['id'] for r in access['clients'] if not r['revoked'] and not r.get('suspended')}
    personal = next(profile(p) for p in (HOME/'clients').glob('*.exe') if p.stem in active)
    import client
    remote = client.Remote(personal, endpoint=client.HTTPS_ENDPOINT)
    report = {'synthetic_text_only':True, 'checks':[]}
    def exercise(origin, token, label, text, expected=200, mode='document'):
        body = {'model':'google/embeddinggemma-2', 'input':text, 'input_type':mode}
        request = urllib.request.Request(origin+'/v1/embeddings', json.dumps(body).encode(),
            {'Authorization':'Bearer '+token, 'Content-Type':'application/json',
             'X-Fred-Agent-Protocol':'4',
             'User-Agent':'AccesServeurKiara/'+client.VERSION+' (Windows; HTTPS)'})
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=95) as response:
                status=response.status; value=json.load(response)
        except urllib.error.HTTPError as error:
            status=error.code; value=json.load(error); error.close()
        assert status==expected, (label, status, value.get('error'))
        if status==200:
            vector=value['data'][0]['embedding']
            assert len(vector)==768 and all(math.isfinite(v) for v in vector)
            assert .98<=math.sqrt(sum(v*v for v in vector))<=1.02
        else:assert value['error']['code']=='input_too_long'
        report['checks'].append({'path':label, 'characters':len(text), 'mode':mode,
            'http':status, 'usage':value.get('usage'), 'error':value.get('error'),
            'seconds':round(time.monotonic()-started, 3)})
        print(label+': HTTP '+str(status)+', '+str(len(text))+' characters.', flush=True)
    # Exactly 4,835 characters, and an input exceeding the old 2,048-token truncation.
    text = ('Le rapport du projet confirme la réception du document PDF. '*100)[:4835]
    long_text = 'bonjour '*3000
    local = None
    try:
        exercise(client.HTTPS_ENDPOINT, personal['token'], 'public_https_4835', text)
        exercise(client.HTTPS_ENDPOINT, personal['token'], 'public_https_above_2048_tokens', long_text)
        assert report['checks'][-1]['usage']['prompt_tokens']>2048
        exercise(client.HTTPS_ENDPOINT, personal['token'], 'public_https_over_model_limit', 'bonjour '*9000, 400)
        # Existing shipped EXE entrypoint, loaded by the established verification helper.
        import marshal, types, subprocess
        frozen=types.ModuleType('frozen_embeddings_client'); frozen.__file__=str(ROOT/'client-qwen/client.py')
        sys.modules[frozen.__name__]=frozen
        bytecode=subprocess.check_output([str(ROOT/'toolchain/build-python/Scripts/python.exe'), '-c',
            "import sys;from PyInstaller.archive.readers import CArchiveReader;sys.stdout.buffer.write(CArchiveReader(sys.argv[1]).extract('client'))",
            str(ROOT/'client-qwen/dist/Accès serveur Fred.exe')])
        exec(marshal.loads(bytecode), frozen.__dict__)
        remote.close(); remote=frozen.Remote(personal, endpoint=frozen.HTTPS_ENDPOINT)
        import secrets, tempfile, threading
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='kiara-limits-') as temp:
            with patch.object(frozen, 'settings_path', return_value=Path(temp)/'client.dpapi'):
                remote.check(); assert remote.connected
                token=secrets.token_urlsafe(32); local=frozen.serve_local(remote, token, port=0)
                threading.Thread(target=local.serve_forever, daemon=True).start()
                exercise('http://127.0.0.1:'+str(local.server_port), token, 'published_windows_relay_4835', text)
                exercise('http://127.0.0.1:'+str(local.server_port), token, 'published_windows_relay_query_4835', text, mode='query')
    finally:
        if local:local.shutdown();local.server_close()
        remote.close()
    before=json.loads((OUT/'avant-livraison.json').read_text(encoding='utf-8'))
    assert models()==before['models'] and preserved_files()==before['files']
    assert backup_config(get('/api/backups'))==before['backups']
    report.update(passed=True, qwen_processes_preserved=True, engine=get('/api/knowledge')['engine'],
                  exact_user_passage_tested=False,
                  sources={str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'lanceur').glob('*embedding*.py')})
    write('production.json', report)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase', choices=['prepare','activate','verify'])
    globals()[parser.parse_args().phase]()
