"""Publish the tested oral client; preserve loaded Qwen/vision and private data."""
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
sys.path.insert(0,str(ROOT/'lanceur'))
import psutil
from core import HOME
from validate_live_lots6_8 import get

spec=importlib.util.spec_from_file_location('audit_rollout',ROOT/'audits/2026-10-12/production_corrections.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous);previous.OUT=OUT
REPORT=OUT/'production-corrections.json'
STAGE=ROOT/'toolchain/releases-staging/conversation-20261014/windows'


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def save(report):REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')


def prepare():
    previous.prepare()
    report=json.loads(REPORT.read_text())
    report['protected_engines']=[]
    for process in psutil.process_iter(['pid','name','create_time','exe']):
        if process.info['name'] in ('strata.exe','strata-vision.exe'):
            report['protected_engines'].append({'pid':process.pid,'created':process.create_time(),'exe':process.exe()})
    assert len(report['protected_engines'])==2
    save(report)


def deploy():
    report=json.loads(REPORT.read_text());previous.ready()
    assert previous.snapshot()==report['before'],'Protected production state changed after backup'
    artifact=json.loads((OUT/'artifact.json').read_text());binary=STAGE/'Accès serveur Fred.exe'
    assert artifact['passed'] and artifact['version']=='3.5.30' and digest(binary)==artifact['sha256']
    for name in ('ui-conversation.log','ui-conversation-automatic.log'):
        assert '"passed": true' in (OUT/name).read_text(encoding='utf-8-sig'),'UI validation missing'
    saved=STAGE.parent/'previous';saved.mkdir(exist_ok=True)
    distribution=ROOT/'client-qwen/dist'
    for name in ('Accès serveur Fred.exe','build-manifest.json','release.json'):
        source=distribution/name
        if source.exists() and not (saved/name).exists():shutil.copy2(source,saved/name)
    for name in ('Accès serveur Fred.exe','build-manifest.json'):shutil.copy2(STAGE/name,distribution/name)
    import releases
    release=releases.manifest(HOME);assert releases.status(HOME)['verified']
    report['windows_release']={key:release[key] for key in ('version','sha256','bytes')}
    report['personal_clients_prepared']=releases.repackage(HOME)['count'];save(report)
    identity=json.loads((HOME/'interface.pid.json').read_text());parent=psutil.Process(identity['pid'])
    assert abs(parent.create_time()-identity['created'])<.01 and str(HOME/'app.py').lower() in [a.lower() for a in parent.cmdline()]
    protected=set()
    for entry in report['before']['models']+report['protected_engines']:
        process=psutil.Process(entry['pid']);assert abs(process.create_time()-entry['created'])<.01
        protected.add(process.pid);protected.update(child.pid for child in process.children(recursive=True))
        for ancestor in process.parents():
            if ancestor.pid==parent.pid:break
            protected.add(ancestor.pid)
    children=[(child,child.create_time()) for child in parent.children(recursive=True) if child.pid not in protected]
    parent.terminate();parent.wait(timeout=10)
    for child,created in reversed(children):
        try:
            if child.is_running() and abs(child.create_time()-created)<.01:child.terminate();child.wait(timeout=10)
        except psutil.NoSuchProcess:pass
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Interface-Qwen.ps1'),'-SansNavigateur','-PreserverEtatModele'],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,'Console restart failed'
    print('Windows 3.5.30 published; Qwen and vision processes preserved.')


def verify():
    report=json.loads(REPORT.read_text());deadline=time.monotonic()+45
    while True:
        try:previous.ready();voice=get('/api/voice');assert voice['ready'];break
        except Exception:
            if time.monotonic()>deadline:raise
            time.sleep(.5)
    after=previous.snapshot();assert after==report['before'],'Protected state changed'
    for entry in report['protected_engines']:
        process=psutil.Process(entry['pid']);assert abs(process.create_time()-entry['created'])<.01
    release=get('/api/releases');assert release['verified'] and release['server_version']=='3.5.30'
    assert release['release']['sha256']==report['windows_release']['sha256']
    assert get('/api/remote')['hermes']['service']['available']
    report.update(passed=True,after=after,server_version='3.5.30',voice_ready=True,hermes_available=True,model_and_vision_processes_preserved=True,
                  keys_and_user_data_preserved=True,backup_schedule_preserved=True)
    save(report);print('Production verified: voice ready, release signed, Qwen/vision, data, keys and backups preserved.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','deploy','verify']);globals()[parser.parse_args().phase]()
