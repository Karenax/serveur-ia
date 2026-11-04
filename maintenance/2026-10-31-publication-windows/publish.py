"""Publish Windows 3.5.55 with the existing signing key and personal access profiles."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
STAGE=ROOT/'toolchain/releases-staging/windows-3.5.55'
VERSION='3.5.55'
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen'),str(ROOT/'maintenance')]
from core import HOME
from validate_live_lots6_8 import get,post,models,preserved_files,backup_config
from releases import profile,digest
from signing import public
from kiara_shared.releases import verify

spec=importlib.util.spec_from_file_location('prior_delivery',ROOT/'maintenance/2026-10-26-correctifs-audit-global/deliver.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)

def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def identity(values):return prior.identity(values)

def idle():
    prior.idle()
    active={row['id'] for row in json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))['clients'] if not row['revoked']}
    values=next(profile(path) for path in (HOME/'clients').glob('*.exe') if path.stem in active)
    request=urllib.request.Request('http://127.0.0.1:8766/v1/voice/max/status',headers={
        'Authorization':'Bearer '+values['token'],'X-Fred-Agent-Protocol':'4'})
    with urllib.request.urlopen(request,timeout=30) as response:state=json.load(response)
    assert not state.get('busy') and not state.get('testing'),'Max in use'

def prepare():
    assert not (OUT/'avant-livraison.json').exists(),'Preparation exists; inspect before repeating'
    idle()
    before={'models':models(),'files':preserved_files(),'users':prior.user_fingerprints(),
            'backups':backup_config(get('/api/backups')),'model_running':get('/api/state')['running'],
            'personal_identities':{p.stem:identity(profile(p)) for p in (HOME/'clients').glob('*.exe')},
            'old_version':get('/api/releases')['server_version']}
    assert before['models'] and before['old_version']=='3.5.54'
    write('avant-livraison.json',before)
    job=post('/api/backups/create',{'kind':'manual','protected':True})
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        value=get('/api/backups');current=value['job']
        assert current['id']==job['job']['id'],'Backup job replaced'
        if current['state'] in ('succeeded','failed'):break
        time.sleep(1)
    else:raise TimeoutError('Backup did not finish')
    assert current['state']=='succeeded',current.get('message')
    backup=current['result'];path=Path(backup['file'])
    record=next(row for row in value['catalog'] if row['id']==backup['id'])
    assert record['verified'] and digest(path)==record['sha256']
    write('sauvegarde-avant.json',{'file':str(path),'sha256':record['sha256'],
          'verified':True,'encrypted':True,'timestamp':time.time(),'secondary':backup.get('secondary',{}).get('status')})
    print('Encrypted pre-publication backup verified.',flush=True)

def unchanged(before):
    assert models()==before['models'],'Loaded model processes changed'
    assert preserved_files()==before['files'],'Access/settings/key files changed'
    assert prior.user_fingerprints()==before['users'],'User data changed'
    assert backup_config(get('/api/backups'))==before['backups'],'Backup policy changed'

def publish():
    assert not (OUT/'publication.json').exists(),'Already published; use --verify'
    before=json.loads((OUT/'avant-livraison.json').read_text(encoding='utf-8'))
    backup=json.loads((OUT/'sauvegarde-avant.json').read_text(encoding='utf-8'))
    assert backup['verified'] and time.time()-backup['timestamp']<3600
    assert digest(backup['file'])==backup['sha256']
    manifest=json.loads((STAGE/'build-manifest.json').read_text(encoding='utf-8'))
    source=STAGE/'Accès serveur Fred.exe'
    assert digest(source)==manifest['artifact']['sha256']
    for name,wanted in manifest['source_files'].items():assert digest(ROOT/name)==wanted,'Source changed: '+name
    assert 'self-test OK' in (STAGE/'self-test.txt').read_text(encoding='utf-8')
    assert json.loads((OUT/'frozen-validation.json').read_text(encoding='utf-8'))['passed']
    idle();unchanged(before)
    destination=ROOT/'client-qwen/dist'
    previous=OUT/'previous';previous.mkdir(exist_ok=True)
    for name in ('Accès serveur Fred.exe','release.json','build-manifest.json'):
        if (destination/name).exists():shutil.copy2(destination/name,previous/name)
    for name in ('Accès serveur Fred.exe','build-manifest.json'):
        pending=destination/(name+'.publish.tmp');shutil.copy2(STAGE/name,pending);pending.replace(destination/name)
    import releases
    release=releases.manifest(HOME);verify(release,public(HOME,create=False))
    assert release['version']==VERSION and releases.status(HOME)['verified']
    prepared=releases.repackage(HOME)
    records=json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))['clients']
    active={row['id'] for row in records if not row['revoked']}
    count=0
    for path in (HOME/'clients').glob('*.exe'):
        values=profile(path)
        if path.stem in before['personal_identities']:assert identity(values)==before['personal_identities'][path.stem]
        if path.stem in active:
            assert values['version']==VERSION
            result=OUT/('personal-self-test-'+str(count)+'.txt')
            checked=subprocess.run([str(path),'--self-test','--with-profile','--result',str(result)],timeout=90,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            assert checked.returncode==0 and 'self-test OK' in result.read_text(encoding='utf-8')
            count+=1
    write('publication.json',{'version':VERSION,'sha256':release['sha256'],'bytes':release['bytes'],
                            'signature_verified':True,'personal_clients':count,'prepared':prepared.get('count'),
                            'personal_access_preserved':True,'previous':str(previous)})
    idle();unchanged(before)
    restart_spec=importlib.util.spec_from_file_location('preserving_restart',ROOT/'maintenance/2026-10-21-api-embeddings/livrer.py')
    restart=importlib.util.module_from_spec(restart_spec);restart_spec.loader.exec_module(restart);restart.OUT=OUT
    restart.restart()
    verify_served()

def verify_served():
    before=json.loads((OUT/'avant-livraison.json').read_text(encoding='utf-8'))
    publication=json.loads((OUT/'publication.json').read_text(encoding='utf-8'))
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            status=get('/api/releases');remote=get('/api/remote')
            if status['server_version']==VERSION and status['verified'] and remote['hermes']['service']['available']:break
        except (OSError,ValueError,KeyError):pass
        time.sleep(1)
    else:raise TimeoutError('Updated gateway readiness')
    unchanged(before)
    assert get('/api/state')['running']==before['model_running']
    values=next(profile(path) for path in (HOME/'clients').glob('*.exe') if profile(path).get('version')==VERSION)
    headers={'Authorization':'Bearer '+values['token'],'X-Fred-Agent-Protocol':'4'}
    def request(route):return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8766'+route,headers=headers),timeout=60)
    with request('/v1/client/release') as response:release=json.load(response)
    verify(release,values['update_public_key'])
    assert release['version']==VERSION and release['sha256']==publication['sha256']
    total=0;sha=hashlib.sha256()
    with request('/v1/client/download') as response:
        while chunk:=response.read(1024*1024):sha.update(chunk);total+=len(chunk)
    assert sha.hexdigest()==release['sha256'] and total==release['bytes']
    with request('/v1/status') as response:assert json.load(response)['version']==VERSION
    write('production.json',{'passed':True,'version':VERSION,'signed_update_served':True,'download_verified':True,
                            'bytes':total,'sha256':sha.hexdigest(),'personal_access_preserved':True,
                            'model_processes_preserved':True,'user_data_keys_settings_preserved':True,
                            'backup_policy_preserved':True,'personal_clients':publication['personal_clients'],
                            'voice_pack_unchanged':True,'android_unchanged':True})
    print('Windows '+VERSION+' published; authenticated download and preserved state verified.',flush=True)

if __name__=='__main__':
    if '--prepare' in sys.argv:prepare()
    elif '--verify' in sys.argv:verify_served()
    else:publish()
