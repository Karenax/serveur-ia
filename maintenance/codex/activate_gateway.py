"""Activate the qualified gateway, preserving loaded Qwen and existing user data."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'lanceur'), str(ROOT/'maintenance')]
import psutil
from core import HOME, HIDDEN
from validate_live_lots6_8 import get, post, models, preserved_files, backup_config
from releases import profile

spec = importlib.util.spec_from_file_location('prior_gateway_delivery', ROOT/'maintenance/2026-10-26-correctifs-audit-global/deliver.py')
prior = importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)


def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'activate', 'verify'))
    parser.add_argument('--reports', type=Path, default=ROOT/'toolchain/test-results/codex-20261102')
    parser.add_argument('--refresh', action='store_true', help='Reload a newly qualified source revision; keep the initial preservation snapshot.')
    args = parser.parse_args(); out=args.reports/'deployment'; out.mkdir(parents=True, exist_ok=True)
    def write(name, value): (out/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.phase == 'prepare':
        if (out/'before.json').exists(): raise RuntimeError('Preparation exists; inspect it before repeating.')
        for name in ('live-client.json','live-subagents.json','app-server.json'):
            assert json.loads((args.reports/name).read_text(encoding='utf-8'))['passed'], name
        prior.idle()
        snapshot = {'models': models(), 'files': preserved_files(), 'users': prior.user_fingerprints(),
                    'backups': backup_config(get('/api/backups')),
                    'source_sha256': {name:digest(ROOT/name) for name in ('lanceur/remote.py','lanceur/gateway_responses.py','lanceur/scheduler.py','client-qwen/wireguard-bridge/main.go')},
                    'bridge_sha256': digest(ROOT/'toolchain/releases-staging/codex-20261102/wireguard-bridge.exe')}
        assert snapshot['models']
        write('before.json', snapshot)
        job = post('/api/backups/create', {'kind':'manual','protected':True})
        write('backup-job.json', {'id':job['job']['id']})
        print('Preservation snapshot saved; encrypted backup started.'); return

    before = json.loads((out/'before.json').read_text(encoding='utf-8'))
    def unchanged():
        assert models() == before['models'], 'Loaded model processes changed'
        assert preserved_files() == before['files'], 'Access, keys or settings changed'
        assert prior.user_fingerprints() == before['users'], 'User content changed'
        assert backup_config(get('/api/backups')) == before['backups'], 'Backup policy changed'
    if args.phase == 'activate':
        assert args.refresh or not (out/'activated.json').exists(), 'Already activated; verify instead'
        backup = get('/api/backups'); job = backup['job']
        assert job['id'] == json.loads((out/'backup-job.json').read_text(encoding='utf-8'))['id']
        assert job['state'] == 'succeeded', 'Wait for encrypted backup completion'
        record = next(row for row in backup['catalog'] if row['id'] == job['result']['id'])
        assert record['verified'] and digest(job['result']['file']) == record['sha256']
        write('backup.json', {'verified':True, 'encrypted':True, 'sha256':record['sha256'], 'file':job['result']['file']})
        prior.idle(); unchanged()
        if args.refresh:
            assert json.loads((args.reports/'responses-tests.json').read_text(encoding='utf-8'))['passed']
            before['source_sha256']={name:digest(ROOT/name) for name in before['source_sha256']}
            write('refresh-sources.json',before['source_sha256'])
        for name, wanted in before['source_sha256'].items(): assert digest(ROOT/name)==wanted, 'Sources changed after qualification'
        staged = ROOT/'toolchain/releases-staging/codex-20261102/wireguard-bridge.exe'
        assert digest(staged)==before['bridge_sha256']
        owner = json.loads((HOME/'interface.pid.json').read_text(encoding='utf-8'))
        parent = psutil.Process(owner['pid'])
        assert abs(parent.create_time()-owner['created']) < .01
        assert str(HOME/'app.py').casefold() in [v.casefold() for v in parent.cmdline()]
        protected=set()
        for row in before['models']:
            p=psutil.Process(row['pid']); assert abs(p.create_time()-row['created']) < .01
            protected.add(p.pid); protected.update(c.pid for c in p.children(recursive=True))
            for ancestor in p.parents():
                if ancestor.pid == parent.pid: break
                protected.add(ancestor.pid)
        children=[(p,p.create_time()) for p in parent.children(recursive=True) if p.pid not in protected]
        parent.terminate(); parent.wait(timeout=10)
        for child, created in reversed(children):
            try:
                if child.is_running() and abs(child.create_time()-created)<.01:
                    child.terminate(); child.wait(timeout=10)
            except psutil.NoSuchProcess: pass
        target=ROOT/'client-qwen/wireguard-bridge.exe'
        if not (out/'wireguard-bridge-before.exe').exists(): shutil.copy2(target,out/'wireguard-bridge-before.exe')
        shutil.copy2(staged,target)
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
            '-File',str(ROOT/'Start-Interface-Qwen.ps1'),'-SansNavigateur','-PreserverEtatModele'],
            capture_output=True, timeout=60, creationflags=HIDDEN)
        assert result.returncode == 0, 'Gateway restart failed'
        write('activated.json', {'model_processes_preserved':models()==before['models'], 'bridge_sha256':digest(target)})
        print('Gateway activated; loaded Qwen processes preserved.'); return

    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        try:
            remote=get('/api/remote')
            if remote['hermes']['service']['available']: break
        except (OSError,ValueError,KeyError): pass
        time.sleep(1)
    else: raise RuntimeError('Gateway readiness timeout')
    unchanged()
    records=json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))['clients']
    active={r['id'] for r in records if not r.get('revoked') and not r.get('suspended') and not r.get('hermes_pending') and (not r.get('expires_epoch') or r['expires_epoch']>time.time())}
    access=next(profile(p) for p in (HOME/'clients').glob('*.exe') if p.stem in active)
    headers={'Content-Type':'application/json','Authorization':'Bearer '+access['token'], 'User-Agent':'AccesServeurKiara/Codex-qualification'}
    checks=[]
    for endpoint in ('http://127.0.0.1:8766','https://ia.karenax.net'):
        raw={'model':'fred-qwen','input':'Réponds uniquement KIARA-CODEX-OK','stream':True,'store':False,'reasoning':{'effort':'none'},'max_output_tokens':64}
        request=urllib.request.Request(endpoint+'/v1/responses',json.dumps(raw).encode(),headers)
        with urllib.request.urlopen(request,timeout=120) as response:
            events=[json.loads(line[6:]) for line in response if line.startswith(b'data: ')]
        final=events[-1]
        assert final['type']=='response.completed'
        result=final['response']
        answer=''.join(part.get('text','') for item in result['output'] if item['type']=='message' for part in item.get('content',[]))
        assert answer.strip()=='KIARA-CODEX-OK' and result['model']=='fred-qwen'
        checks.append({'endpoint':endpoint, 'model':result['model'], 'stream_completed':True, 'answer':answer})
    unchanged()
    write('verified.json', {'passed':True,'checks':checks,'model_processes_preserved':True,'keys_settings_user_content_preserved':True})
    print('Production verified over loopback and HTTPS; model, keys, settings and user content preserved.')


if __name__ == '__main__': main()
