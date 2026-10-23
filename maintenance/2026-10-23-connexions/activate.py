"""Promote the tested Windows update; retain rollback and the loaded Qwen."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from core import HOME
from validate_live_lots6_8 import get,models,preserved_files,content_fingerprints,backup_config


def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    stage=ROOT/'toolchain/releases-staging/windows-3.5.37'
    source=stage/'Accès serveur Fred.exe'
    proof=json.loads((OUT/'exe-proof.json').read_text(encoding='utf-8'))
    assert proof['passed'] and hashlib.sha256(source.read_bytes()).hexdigest()==proof['sha256']
    assert json.loads((OUT/'ui-proof.json').read_text(encoding='utf-8'))['passed']
    assert not (OUT/'avant-livraison.json').exists(),'Activation already started; inspect before retrying'
    assert get('/api/state')['queue']['active']==0 and not get('/api/voice')['busy']
    backup=get('/api/backups')
    assert any(item.get('verified') for item in backup['catalog']),'Verified encrypted backup required'
    before={'models':models(),'files':preserved_files(),'users':content_fingerprints(),'backups':backup_config(backup)}
    assert before['models'] and (HOME/'wireguard-prive/signature.dpapi').is_file()
    write('avant-livraison.json',before)
    previous=stage/'previous';previous.mkdir(exist_ok=True)
    destination=ROOT/'client-qwen/dist'
    for name in (source.name,'build-manifest.json','release.json'):
        target=destination/name
        if target.exists():shutil.copy2(target,previous/name)
    for name in (source.name,'build-manifest.json'):
        temporary=destination/(name+'.portable-update.tmp')
        shutil.copy2(stage/name,temporary);temporary.replace(destination/name)
    import releases
    release=releases.manifest(HOME)
    assert releases.status(HOME)['verified']
    prepared=releases.repackage(HOME)
    write('publication.json',{'version':release['version'],'sha256':release['sha256'],'bytes':release['bytes'],
                              'personal_clients_prepared':prepared['count']})
    spec=importlib.util.spec_from_file_location('fred_previous_delivery',ROOT/'maintenance/2026-10-21-api-embeddings/livrer.py')
    delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery)
    delivery.OUT=OUT;delivery.restart()
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        try:
            state=get('/api/state');voice=get('/api/voice');published=get('/api/releases')
            if state['health']['loaded'] and voice['ready'] and published['verified'] and published['server_version']=='3.5.37':break
        except (OSError,ValueError,KeyError):pass
        time.sleep(1)
    else:raise TimeoutError('Fred readiness after update')
    assert models()==before['models']
    assert preserved_files()==before['files'] and content_fingerprints()==before['users']
    assert backup_config(get('/api/backups'))==before['backups']
    assert voice['engine']=='Phonon 0.4.1'
    result={'passed':True,'version':'3.5.37','signed_update':True,'qwen_processes_preserved':True,
            'keys_settings_user_data_preserved':True,'backup_schedule_preserved':True,
            'phonon_ready':True,'personal_clients_prepared':prepared['count']}
    write('production.json',result);print(json.dumps(result))


if __name__=='__main__':main()
