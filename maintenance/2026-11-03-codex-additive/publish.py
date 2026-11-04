"""Publish the integrated Windows client and its authenticated Codex resources."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
STAGE=ROOT/'toolchain/releases-staging/windows-3.5.57'
BRIDGE=ROOT/'toolchain/releases-staging/codex-button-20261103/wireguard-bridge.exe'
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen'),str(ROOT/'maintenance')]
from core import HOME,HIDDEN
from validate_live_lots6_8 import get,post,models,preserved_files,backup_config
from releases import profile,digest
import psutil

spec=importlib.util.spec_from_file_location('prior_windows_delivery',ROOT/'maintenance/2026-10-31-publication-windows/publish.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
prior.OUT=OUT;prior.STAGE=STAGE;prior.VERSION='3.5.57'


def write(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def prepare():
    assert not (OUT/'avant-livraison.json').exists(),'Inspect existing preparation'
    prior.idle()
    before={'models':models(),'files':preserved_files(),'users':prior.prior.user_fingerprints(),
            'backups':backup_config(get('/api/backups')),'model_running':get('/api/state')['running'],
            'personal_identities':{p.stem:prior.identity(profile(p)) for p in (HOME/'clients').glob('*.exe')},
            'old_version':get('/api/releases')['server_version']}
    assert before['models'] and before['old_version']=='3.5.56'
    write('avant-livraison.json',before)
    job=post('/api/backups/create',{'kind':'manual','protected':True})
    write('backup-job.json',{'id':job['job']['id']})
    print('Preservation snapshot saved; encrypted backup started.')


def check():
    from PyInstaller.archive.readers import CArchiveReader
    archive=CArchiveReader(str(STAGE/'Accès serveur Fred.exe'))
    for name in ('chat.html','ui.js','ui.css'):
        assert archive.extract(name)==(ROOT/'client-qwen'/name).read_bytes(),name
    assert b'integration-codex-guide' in archive.extract('chat.html')
    assert hashlib.sha256(archive.extract('wireguard-bridge.exe')).hexdigest()==digest(BRIDGE)
    pyz=archive.open_embedded_archive('PYZ.pyz')
    assert '3.5.57' in pyz.extract('kiara_shared.version').co_consts
    import types,tempfile
    module=types.ModuleType('frozen_codex_setup');exec(pyz.extract('codex_integration'),module.__dict__)
    from codex_assets import payload
    from signing import public
    with tempfile.TemporaryDirectory(prefix='frozen-codex-') as folder:
        home=Path(folder);pinned=public(home);target=home/'verified';target.mkdir()
        module.unpack(payload(home),pinned,target)
        assert (target/'Installer-Codex-Kiara.ps1').is_file()
    write('frozen-validation.json',{'passed':True,'version':'3.5.57','ui_matches_sources':True,
          'codex_download_verifier_executed':True,'wireguard_matches_staged':True})
    print('Frozen client: real UI, signed-download verifier and new WireGuard bridge verified.')


def publish():
    state=get('/api/backups');job=state['job']
    assert job['id']==json.loads((OUT/'backup-job.json').read_text(encoding='utf-8'))['id']
    assert job['state']=='succeeded','Wait for backup completion'
    backup=job['result'];record=next(r for r in state['catalog'] if r['id']==backup['id'])
    assert record['verified'] and digest(backup['file'])==record['sha256']
    write('sauvegarde-avant.json',{'file':backup['file'],'sha256':record['sha256'],'verified':True,'timestamp':time.time()})
    # The established delivery validates source hashes and signatures, repackages
    # existing recipients, and verifies their unchanged access identities.
    restart_spec=importlib.util.spec_from_file_location('gateway_restart',ROOT/'maintenance/2026-10-21-api-embeddings/livrer.py')
    restart=importlib.util.module_from_spec(restart_spec);restart_spec.loader.exec_module(restart)
    original_run=subprocess.run
    def launch(command,*args,**kwargs):
        if any(str(value).endswith('Start-Interface-Qwen.ps1') for value in command):
            target=ROOT/'client-qwen/wireguard-bridge.exe'
            saved=OUT/'previous';saved.mkdir(exist_ok=True)
            if not (saved/'wireguard-bridge.exe').exists():shutil.copy2(target,saved/'wireguard-bridge.exe')
            shutil.copy2(BRIDGE,target)
        return original_run(command,*args,**kwargs)
    # The previous publisher imports its restart helper itself. Patch only the
    # process-launch boundary: the stopped bridge is replaced immediately before
    # the standard preserving restart starts the new console.
    from unittest.mock import patch
    with patch.object(subprocess,'run',side_effect=launch):prior.publish()
    print('Windows 3.5.57 published with personal access and loaded model preserved.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('prepare','check','publish','verify'));args=parser.parse_args()
    if args.phase=='verify':prior.verify_served()
    else:globals()[args.phase]()
