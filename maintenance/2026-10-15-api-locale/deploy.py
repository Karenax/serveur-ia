"""Server-only API correction, preserving engines, credentials and user state."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
import psutil
from core import HOME
from validate_live_lots6_8 import get

spec=importlib.util.spec_from_file_location('previous_rollout',ROOT/'audits/2026-10-12/production_corrections.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous);previous.OUT=OUT
REPORT=OUT/'production-corrections.json'


def prepare():
    previous.prepare()
    report=json.loads(REPORT.read_text())
    report['engines']=[{'pid':p.pid,'created':p.create_time(),'name':p.name()}
        for p in psutil.process_iter() if p.name() in ('strata.exe','strata-vision.exe')]
    assert len(report['engines'])==2
    REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')


def deploy():
    report=json.loads(REPORT.read_text());previous.ready()
    assert previous.snapshot()==report['before']
    identity=json.loads((HOME/'interface.pid.json').read_text());parent=psutil.Process(identity['pid'])
    assert abs(parent.create_time()-identity['created'])<.01
    assert str(HOME/'app.py').lower() in [a.lower() for a in parent.cmdline()]
    protected=set()
    for entry in report['before']['models']+report['engines']:
        p=psutil.Process(entry['pid']);assert abs(p.create_time()-entry['created'])<.01
        protected.add(p.pid);protected.update(c.pid for c in p.children(recursive=True))
        for ancestor in p.parents():
            if ancestor.pid==parent.pid:break
            protected.add(ancestor.pid)
    children=[(p,p.create_time()) for p in parent.children(recursive=True) if p.pid not in protected]
    parent.terminate();parent.wait(timeout=10)
    for p,created in reversed(children):
        try:
            if p.is_running() and abs(p.create_time()-created)<.01:p.terminate();p.wait(timeout=10)
        except psutil.NoSuchProcess:pass
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Interface-Qwen.ps1'),
        '-SansNavigateur','-PreserverEtatModele'],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,'Console restart failed'
    print('Server correction loaded; model and vision engines preserved.')


def verify():
    report=json.loads(REPORT.read_text());deadline=time.monotonic()+50
    while True:
        try:previous.ready();assert get('/api/remote')['hermes']['service']['available'];break
        except Exception:
            if time.monotonic()>deadline:raise
            time.sleep(.5)
    assert previous.snapshot()==report['before']
    for entry in report['engines']:assert abs(psutil.Process(entry['pid']).create_time()-entry['created'])<.01
    report.update(passed=True,after=previous.snapshot(),hermes_available=True,engines_preserved=True,
        keys_data_and_backup_schedule_preserved=True,client_rebuild_required=False)
    REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Production verified: Hermes, loaded models, keys, data and backup schedule preserved.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','deploy','verify'])
    globals()[parser.parse_args().phase]()
