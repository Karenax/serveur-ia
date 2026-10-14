"""Publish the verified Windows client while preserving the loaded Qwen model."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
STAGE=ROOT/'toolchain/releases-staging/opencode-20261014/windows'
sys.path.insert(0,str(ROOT/'lanceur'))
import psutil
from core import HOME
from validate_live_lots6_8 import get

spec=importlib.util.spec_from_file_location('previous_rollout',ROOT/'audits/2026-10-12/production_corrections.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
REPORT=OUT/'production-corrections.json'


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def save(report):REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


def deploy():
    report=json.loads(REPORT.read_text());previous.ready()
    assert previous.snapshot()==report['before'],'Protected production state changed since backup'
    artifact=json.loads((OUT/'artifact.json').read_text())
    tested=json.loads((OUT/'verification-2.0.29.json').read_text())
    binary=STAGE/'Accès serveur Fred.exe'
    assert artifact['passed'] and tested['passed'] and artifact['version']=='3.5.29'
    assert digest(binary)==artifact['sha256']==tested['client_binary']['sha256']
    for name in ('Accès serveur Fred.exe','build-manifest.json'):shutil.copy2(STAGE/name,ROOT/'client-qwen/dist'/name)
    import releases
    release=releases.manifest(HOME);assert releases.status(HOME)['verified']
    report['windows_release']={k:release[k] for k in ('version','sha256','bytes')}
    report['personal_clients_prepared']=releases.repackage(HOME)['count'];save(report)
    identity=json.loads((HOME/'interface.pid.json').read_text())
    parent=psutil.Process(identity['pid']);assert abs(parent.create_time()-identity['created'])<.01
    assert str(HOME/'app.py').lower() in [arg.lower() for arg in parent.cmdline()]
    protected={model['pid'] for model in report['before']['models']}
    for model in report['before']['models']:
        process=psutil.Process(model['pid']);assert abs(process.create_time()-model['created'])<.01
        protected.update(child.pid for child in process.children(recursive=True))
        for ancestor in process.parents():
            if ancestor.pid==parent.pid:break
            protected.add(ancestor.pid)
    children=[(child,child.create_time()) for child in parent.children(recursive=True) if child.pid not in protected]
    parent.terminate();parent.wait(timeout=10)
    for child,created in reversed(children):
        try:
            if child.is_running() and abs(child.create_time()-created)<.01:child.terminate();child.wait(timeout=10)
        except psutil.NoSuchProcess:pass
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Interface-Qwen.ps1'),
                           '-SansNavigateur','-PreserverEtatModele'],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,'Console restart failed'
    print('Windows 3.5.29 published; console restarted while Qwen remains loaded.')


def verify():
    report=json.loads(REPORT.read_text());previous.ready();after=previous.snapshot()
    assert after==report['before'],'Protected model, keys, data or backup configuration changed'
    release=get('/api/releases');assert release['verified'] and release['server_version']=='3.5.29'
    assert release['release']['sha256']==report['windows_release']['sha256']
    assert get('/api/remote')['hermes']['service']['available']
    report.update(passed=True,after=after,server_version='3.5.29',hermes_available=True,
                  model_processes_preserved=True,keys_and_user_data_preserved=True,backup_schedule_preserved=True)
    save(report);print('Production verified: signed release, Qwen processes, Hermes, data, keys and backup schedule.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['deploy','verify']);args=parser.parse_args()
    globals()[args.phase]()
