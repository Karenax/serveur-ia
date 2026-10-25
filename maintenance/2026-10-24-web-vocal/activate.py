"""Activate semantic oral search; preserve the existing client and loaded models."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from validate_live_lots6_8 import get,models,preserved_files,content_fingerprints,backup_config


def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    for name in ('semantic-validation.json','native-validation.json','checks.json'):
        assert json.loads((OUT/name).read_text(encoding='utf-8'))['passed'],name
    assert not (OUT/'avant-livraison.json').exists(),'Inspect the previous activation before retrying'
    state=get('/api/state');assert not state['queue']['active'] and not state['queue']['waiting'] and not get('/api/voice')['busy']
    assert not any(r['status'] in {'starting','running','waiting_for_approval'} for r in get('/api/remote')['hermes'].get('runs',[]))
    backups=get('/api/backups');assert any(b.get('verified') for b in backups['catalog'])
    before={'models':models(),'files':preserved_files(),'users':content_fingerprints(),
            'backups':backup_config(backups),'version':get('/api/releases')['server_version']}
    before['feature_sources']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
         for name in ('lanceur/remote.py','lanceur/voice_web.py','lanceur/voice_web_plan.py')}
    assert before['models'];write('avant-livraison.json',before)
    spec=importlib.util.spec_from_file_location('kiara_service_restart',ROOT/'maintenance/2026-10-21-api-embeddings/livrer.py')
    delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery);delivery.OUT=OUT;delivery.restart()
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            state=get('/api/state');voice=get('/api/voice');remote=get('/api/remote')
            if state['health']['loaded'] and voice['ready'] and remote['hermes']['service']['available']:break
        except (OSError,ValueError,KeyError):pass
        time.sleep(1)
    else:raise TimeoutError('Readiness after semantic oral search activation')
    assert models()==before['models'] and preserved_files()==before['files']
    assert content_fingerprints()==before['users'] and backup_config(get('/api/backups'))==before['backups']
    assert get('/api/releases')['server_version']==before['version'] and get('/api/releases')['verified']
    assert voice['voice']=='Tiphaine'
    result={'passed':True,'server_only_change':True,'version':before['version'],'qwen_processes_preserved':True,
            'keys_settings_user_histories_preserved':True,'backup_schedule_preserved':True,'existing_client_release_preserved':True,
            'hermes_ready':True,'phonon_ready':True,'feature_sources':before['feature_sources']}
    write('activation.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
