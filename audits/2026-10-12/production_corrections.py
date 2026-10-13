"""Authorized local rollout with encrypted backup and unchanged user/model checks."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
import psutil
from core import HOME
from validate_live_lots6_8 import get,post,models,preserved_files,backup_config

def users():
    result={}
    with sqlite3.connect((HOME/'espaces-prives/espaces.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=20) as db:
        for table in ('client_histories','projects','documents','memories','conversations','policies','jobs','personal_memories','knowledge_exclusions'):
            rows=db.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()
            raw=json.dumps([[v.hex() if isinstance(v,bytes) else v for v in row] for row in rows],ensure_ascii=False,separators=(',',':')).encode()
            result[table]={'count':len(rows),'sha256':hashlib.sha256(raw).hexdigest()}
    return result

def snapshot():
    return {'models':models(),'files':preserved_files(),'users':users(),'backups':backup_config(get('/api/backups'))}

def save(report):
    (OUT/'production-corrections.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

def ready():
    state=get('/api/state')
    assert state['running'] and state['health']['loaded'] and not state['queue']['active'],'Model must stay loaded and idle'
    assert not get('/api/remote')['active'],'Accepted client requests must finish before rollout'

def prepare():
    ready();before=snapshot();current=get('/api/backups')
    assert current['config']['secret_configured'],'Existing automatic backup phrase must be configured'
    started=time.time();post('/api/backups/create',{})
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        state=get('/api/backups')
        if state['job'].get('state')=='succeeded' and any(r['timestamp']>=started for r in state['catalog']):break
        if state['job'].get('state')=='failed':raise ValueError('Predeployment backup failed')
        time.sleep(.5)
    assert state['job']['state']=='succeeded'
    record=max((r for r in state['catalog'] if r['verified']),key=lambda r:r['timestamp'])
    assert record['timestamp']>=started
    verified=post('/api/backups/verify',{'id':record['id']})
    assert verified['verified'] if 'verified' in verified else verified['summary']['verified']
    assert snapshot()==before
    report={'before':before,'backup_before':{key:record[key] for key in ('id','file','size','sha256','version','verified')},'contains_secret_values':False}
    save(report);print('Predeployment encrypted backup verified; model, data and keys preserved.')

def deploy():
    report=json.loads((OUT/'production-corrections.json').read_text(encoding='utf-8'))
    assert snapshot()==report['before'];ready()
    assert json.loads((OUT/'artifacts-verification.json').read_text())['passed']
    previous=ROOT/'toolchain/releases-staging/pre-audit-20261012';previous.mkdir(parents=True,exist_ok=True)
    for platform in ('windows','android'):
        distribution=ROOT/('client-qwen' if platform=='windows' else 'client-android')/'dist'
        staged=OUT/'distribution'/platform
        saved=previous/platform;saved.mkdir(exist_ok=True)
        for path in distribution.iterdir():
            if path.is_file() and path.suffix in ('.exe','.apk','.json','.sha256') and not (saved/path.name).exists():shutil.copy2(path,saved/path.name)
        for path in staged.iterdir():
            if path.is_file():shutil.copy2(path,distribution/path.name)
    import releases
    release=releases.manifest(HOME);assert releases.status(HOME)['verified']
    report['windows_release']={k:release[k] for k in ('version','sha256','bytes')}
    report['android_release']=json.loads((ROOT/'client-android/dist/release.json').read_text())
    report['personal_clients']=report.get('personal_clients',0)+releases.repackage(HOME)['count'];save(report)
    identity=json.loads((HOME/'interface.pid.json').read_text())
    parent=psutil.Process(identity['pid']);assert abs(parent.create_time()-identity['created'])<.01
    assert str(HOME/'app.py').lower() in [arg.lower() for arg in parent.cmdline()]
    qwen={p['pid'] for p in report['before']['models']};owned=parent.children(recursive=True)
    protected=set(qwen)
    for pid in qwen:
        model=psutil.Process(pid);protected.update(p.pid for p in model.children(recursive=True))
        for ancestor in model.parents():
            if ancestor.pid==parent.pid:break
            protected.add(ancestor.pid)
    children=[(p,p.create_time()) for p in owned if p.pid not in protected]
    parent.terminate();parent.wait(timeout=10)
    for child,created in reversed(children):
        try:
            if child.is_running() and abs(child.create_time()-created)<.01:child.terminate();child.wait(timeout=10)
        except psutil.NoSuchProcess:pass
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Interface-Qwen.ps1'),'-SansNavigateur','-PreserverEtatModele'],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,'Console restart failed';print('Updated distributions published; console restart dispatched.')

def verify():
    report=json.loads((OUT/'production-corrections.json').read_text(encoding='utf-8'))
    ready();assert snapshot()==report['before'],'Model/data/key/schedule fingerprint changed'
    release=get('/api/releases');assert release['verified'] and release['server_version']=='3.5.28'
    hermes=get('/api/remote')['hermes'];knowledge=get('/api/knowledge');storage=get('/api/client-storage')
    assert hermes['service']['available'];assert not storage['error']
    assert all(c['status']=='ready' for c in storage['clients'].values())
    report.update(passed=True,after=snapshot(),server_version='3.5.28',hermes_available=True,
                  client_storage_ready=len(storage['clients']),knowledge_status=knowledge['engine']['status'])
    save(report);print(json.dumps({k:report[k] for k in ('passed','server_version','hermes_available','client_storage_ready','knowledge_status')}))

def backup_after():
    report=json.loads((OUT/'production-corrections.json').read_text(encoding='utf-8'))
    started=time.time();post('/api/backups/create',{})
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        state=get('/api/backups')
        if state['job'].get('state')=='succeeded' and any(r['timestamp']>=started for r in state['catalog']):break
        if state['job'].get('state')=='failed':raise ValueError('Backup after deployment failed')
        time.sleep(.5)
    record=max((r for r in state['catalog'] if r['verified']),key=lambda r:r['timestamp'])
    assert record['timestamp']>=started
    verified=post('/api/backups/verify',{'id':record['id']})
    assert verified['verified'] if 'verified' in verified else verified['summary']['verified']
    report['backup_after']={key:record[key] for key in ('id','file','size','sha256','version','verified')};save(report)
    print('Postdeployment encrypted backup including Hermes verified.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','deploy','verify','backup_after']);args=parser.parse_args()
    globals()[args.phase]()
