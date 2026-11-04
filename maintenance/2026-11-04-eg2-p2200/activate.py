"""Activate server-only EG2 changes, preserving loaded Qwen and personal access."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from validate_live_lots6_8 import get,post,models,preserved_files,backup_config
spec=importlib.util.spec_from_file_location('delivery',ROOT/'maintenance/2026-10-31-publication-windows/publish.py')
delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery)


def write(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def idle():
    deadline=time.monotonic()+1800
    while True:
        try:delivery.idle();return
        except AssertionError:
            if time.monotonic()>deadline:raise TimeoutError('User work remains active; restart deferred')
            time.sleep(.5)


def main():
    assert not (OUT/'production.json').exists(),'Already activated; inspect existing evidence'
    assert json.loads((OUT/'worker-validation.json').read_text())['passed']
    idle()
    before={'models':models(),'files':preserved_files(),'users':delivery.prior.user_fingerprints(),
        'backups':backup_config(get('/api/backups')),'model_running':get('/api/state')['running'],
        'engine':get('/api/knowledge')['engine'],'release':get('/api/releases')['release']}
    write('avant-livraison.json',before)
    job=post('/api/backups/create',{'kind':'manual','protected':True})
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        state=get('/api/backups');current=state['job'];assert current['id']==job['job']['id']
        if current['state'] in ('succeeded','failed'):break
        time.sleep(1)
    else:raise TimeoutError('Backup timeout')
    assert current['state']=='succeeded',current.get('message')
    result=current['result'];record=next(r for r in state['catalog'] if r['id']==result['id'])
    assert record['verified'] and delivery.digest(Path(result['file']))==record['sha256']
    write('sauvegarde-avant.json',{'file':result['file'],'sha256':record['sha256'],'verified':True,
        'secondary':result.get('secondary',{}).get('status')})
    idle();delivery.unchanged(before)
    print('Backup verified; restarting the console with Qwen preserved.',flush=True)
    spec=importlib.util.spec_from_file_location('preserving_restart',ROOT/'maintenance/2026-10-21-api-embeddings/livrer.py')
    restart=importlib.util.module_from_spec(spec);spec.loader.exec_module(restart);restart.OUT=OUT
    restart.restart()
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            engine=get('/api/knowledge')['engine']
            if engine['status']=='pret':break
        except (OSError,ValueError):pass
        time.sleep(1)
    else:raise TimeoutError('EG2 readiness')
    assert engine['device']=='cuda:0' and engine['gpu_name']=='Quadro P2200',engine
    assert engine['gpu_uuid']=='GPU-97ca6406-8625-b829-b053-191c238ff046'
    delivery.unchanged(before)
    assert get('/api/state')['running']==before['model_running']
    release=get('/api/releases');assert release['verified'] and release['release']==before['release']
    write('production.json',{'passed':True,'engine':engine,'qwen_processes_preserved':True,
        'user_data_keys_settings_preserved':True,'backup_policy_preserved':True,
        'client_release_unchanged':True,'client_update_required':False})
    names=('lanceur/embeddings.py','lanceur/embedding_worker.py','lanceur/eg2_runtime.py',
        'lanceur/eg2-runtime.json','dependances/verrous/eg2-gpu.requirements.txt')
    write('source-hashes.json',{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names})
    print('EG2 ready on P2200. Clients unchanged; Qwen and preserved state verified.',flush=True)


if __name__=='__main__':main()
