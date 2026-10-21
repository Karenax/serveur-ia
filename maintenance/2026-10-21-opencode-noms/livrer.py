"""Verify and publish the Windows fix, retaining the loaded model and rollback."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
STAGE=ROOT/'toolchain/releases-staging/opencode-noms-20261021'
sys.path[:0]=[str(ROOT/'client-qwen'),str(ROOT/'lanceur')]
from validate_live_lots6_8 import get,models,preserved_files,content_fingerprints,backup_config,digest


def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def artifacts():
    sys.path.insert(0,str(ROOT/'client-qwen/build-tools'))
    from PyInstaller.archive.readers import CArchiveReader
    binary=STAGE/'windows/Accès serveur Fred.exe'
    archive=CArchiveReader(str(binary))
    assert archive.extract('ui.js')==(ROOT/'client-qwen/ui.js').read_bytes()
    assert archive.extract('wireguard-bridge.exe')==(ROOT/'client-qwen/wireguard-bridge.exe').read_bytes()
    pyz=archive.open_embedded_archive('PYZ.pyz')
    assert all(name in pyz.toc for name in ('hermes_catalogue','app_integrations'))
    assert '/hermes/v1/models' in archive.extract('client').decode('latin1')
    with tempfile.TemporaryDirectory(prefix='fred-hermes-build-') as folder:
        result=Path(folder)/'result.txt'
        ran=subprocess.run([str(binary),'--self-test','--result',str(result)],
                           capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        assert ran.returncode==0 and result.is_file(),ran.stderr[-1000:]
    assert json.loads((OUT/'verification-opencode.json').read_text())['readable_model_name']
    write('artefacts.json',{'passed':True,'version':'3.5.34','sha256':digest(binary),
                          'exe_self_test':True,'hermes_modules_embedded':True,'ui_bridge_match_sources':True})
    print('Windows artifact and embedded Hermes integration verified.')


def promote():
    artifact=json.loads((OUT/'artefacts.json').read_text())
    assert artifact['passed'] and artifact['sha256']==digest(STAGE/'windows/Accès serveur Fred.exe')
    assert get('/api/state')['queue']['active']==0
    write('avant-livraison.json',{'models':models(),'files':preserved_files(),'users':content_fingerprints(),
                                'backups':backup_config(get('/api/backups'))})
    dest=ROOT/'client-qwen/dist';previous=STAGE/'previous/windows';previous.mkdir(parents=True,exist_ok=True)
    for name in ('Accès serveur Fred.exe','build-manifest.json','release.json'):
        if (dest/name).is_file() and not (previous/name).exists():shutil.copy2(dest/name,previous/name)
    for name in ('Accès serveur Fred.exe','build-manifest.json'):
        temporary=dest/(name+'.hermes-publish.tmp')
        shutil.copy2(STAGE/'windows'/name,temporary);temporary.replace(dest/name)
    import releases
    assert (ROOT/'lanceur/wireguard-prive/signature.dpapi').is_file()
    release=releases.manifest();assert release['version']=='3.5.34'
    assert releases.status(ROOT/'lanceur')['verified']
    count=releases.repackage(ROOT/'lanceur')['count']
    write('publication.json',{'windows':{k:release[k] for k in ('version','sha256','bytes')},
                            'personal_clients_prepared':count})
    print('Windows 3.5.34 signed and personal clients prepared.')


def restart():
    # Reuse the proven process-identity and model-ancestry checks.
    path=ROOT/'maintenance/2026-10-21-api-embeddings/livrer.py'
    spec=importlib.util.spec_from_file_location('previous_delivery',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.OUT=OUT
    module.restart()


def verify():
    before=json.loads((OUT/'avant-livraison.json').read_text())
    deadline=time.monotonic()+55
    while time.monotonic()<deadline:
        try:
            remote=get('/api/remote');knowledge=get('/api/knowledge')
            if remote['hermes']['service']['available'] and knowledge['engine']['status']=='pret':break
        except (OSError,KeyError,ValueError):pass
        time.sleep(2)
    else:raise ValueError('Services not ready')
    state=get('/api/state');release=get('/api/releases')
    assert state['health']['loaded'] and state['health']['images']
    assert release['server_version']=='3.5.34' and release['verified']
    assert models()==before['models'] and preserved_files()==before['files']
    assert content_fingerprints()==before['users']
    assert backup_config(get('/api/backups'))==before['backups']
    write('production-apres.json',{'passed':True,'server_windows':'3.5.34','update_verified':True,
          'model_processes_preserved':True,'keys_settings_user_data_preserved':True,
          'backup_policy_preserved':True,'hermes_available':True,'eg2_ready':True})
    print('Production and signed update verified; model, keys, settings, data and backups preserved.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['artifacts','promote','restart','verify'])
    globals()[parser.parse_args().phase]()
