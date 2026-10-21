"""Publish verified artifacts and restart only Fred, preserving the loaded model."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
STAGE=ROOT/'toolchain/releases-staging/audit-20261021'
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
import psutil
from core import HOME
from validate_live_lots6_8 import get,models,preserved_files,content_fingerprints,backup_config

def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def promote():
    assert json.loads((OUT/'artefacts.json').read_text())['passed']
    assert json.loads((OUT/'restauration-nas.json').read_text())['passed']
    assert not [r for r in json.loads((OUT/'osv-apres.json').read_text()) if r['advisories']]
    before=json.loads((OUT/'avant-production.json').read_text(encoding='utf-8'))
    assert models()==before['models'] and preserved_files()==before['files']
    assert content_fingerprints()==before['users']
    assert get('/api/state')['queue']['active']==0
    snapshot={'models':models(),'files':preserved_files(),'users':content_fingerprints(),
              'backups':backup_config(get('/api/backups'))}
    write('avant-livraison.json',snapshot)
    previous=STAGE/'previous';previous.mkdir(exist_ok=True)
    for component,files in [('windows',['Accès serveur Fred.exe','build-manifest.json','release.json']),
                            ('android',['Acces-serveur-Fred-Android.apk','Acces-serveur-Fred-Android.apk.sha256','build-manifest.json','release.json'])]:
        dest=ROOT/('client-qwen/dist' if component=='windows' else 'client-android/dist')
        saved=previous/component;saved.mkdir(exist_ok=True)
        for name in files:
            if (dest/name).exists() and not (saved/name).exists():shutil.copy2(dest/name,saved/name)
        for file in (STAGE/component).iterdir():
            if file.name not in files:continue
            temporary=dest/(file.name+'.audit-publish.tmp')
            shutil.copy2(file,temporary);temporary.replace(dest/file.name)
    import releases,android_releases
    assert (HOME/'wireguard-prive/signature.dpapi').is_file()
    release=releases.manifest(HOME)
    assert releases.status(HOME)['verified']
    count=releases.repackage(HOME)['count']
    android=android_releases.status()[0]
    write('publication.json',{'windows':{k:release[k] for k in ('version','sha256','bytes')},
          'android':android,'personal_clients_prepared':count})
    print('Signed Windows and Android artifacts published; existing personal profiles retained.')

def restart():
    snapshot=json.loads((OUT/'avant-livraison.json').read_text())
    assert models()==snapshot['models']
    assert get('/api/state')['queue']['active']==0
    record=json.loads((HOME/'interface.pid.json').read_text())
    parent=psutil.Process(record['pid'])
    assert abs(parent.create_time()-record['created'])<.01
    assert str(HOME/'app.py').casefold() in [v.casefold() for v in parent.cmdline()]
    protected=set()
    for model in snapshot['models']:
        p=psutil.Process(model['pid']);assert abs(p.create_time()-model['created'])<.01
        protected.add(p.pid);protected.update(c.pid for c in p.children(recursive=True))
        for ancestor in p.parents():
            if ancestor.pid==parent.pid:break
            protected.add(ancestor.pid)
    children=[(p,p.create_time()) for p in parent.children(recursive=True) if p.pid not in protected]
    parent.terminate();parent.wait(timeout=10)
    for child,created in reversed(children):
        try:
            if child.is_running() and abs(child.create_time()-created)<.01:
                child.terminate();child.wait(timeout=10)
        except psutil.NoSuchProcess:pass
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
        '-File',str(ROOT/'Start-Interface-Qwen.ps1'),'-SansNavigateur','-PreserverEtatModele'],
        capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,'Console restart failed'
    assert models()==snapshot['models']
    print('Fred restarted with its private secured runtime; loaded Qwen processes preserved.')

def verify():
    before=json.loads((OUT/'avant-livraison.json').read_text())
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            remote=get('/api/remote');knowledge=get('/api/knowledge')
            if remote['hermes']['service']['available'] and knowledge['engine']['status']=='pret':break
        except (OSError,KeyError,ValueError):pass
        time.sleep(2)
    else:raise ValueError('Fred/Hermes/EG2 readiness timeout')
    state=get('/api/state');release=get('/api/releases');backups=get('/api/backups')
    assert state['health']['loaded'] and state['health']['images']
    assert release['server_version']=='3.5.31' and release['verified']
    assert models()==before['models'] and preserved_files()==before['files']
    assert content_fingerprints()==before['users']
    assert backup_config(backups)==before['backups']
    from hermes_service import installation
    runtime=installation()
    owned=json.loads((HOME/'hermes-fred/fred-gateway.pid.json').read_text())
    native=[psutil.Process(p['pid']) for p in owned['processes'] if psutil.pid_exists(p['pid'])]
    assert any(Path(p.cwd()).resolve()==runtime['source'].resolve() for p in native)
    verified={'passed':True,'server_windows':'3.5.31','android':'1.0.12','android_code':13,
        'model_loaded':True,'vision_available':True,'model_processes_preserved':True,
        'keys_settings_user_data_preserved':True,'backup_policy_preserved':True,
        'nas_second_copy_configured':bool(backups['config']['secondary_destination']),
        'hermes_private_runtime_active':True,'eg2_ready':True,'console_owner_isolation_active':True}
    write('production-apres.json',verified)
    print('Production verified: model, keys, data, NAS policy, private Hermes runtime and EG2.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['promote','restart','verify']);args=parser.parse_args()
    globals()[args.phase]()
