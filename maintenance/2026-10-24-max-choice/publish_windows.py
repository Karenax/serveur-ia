"""Publish the authorized Windows update, preserving personal identities and loaded Qwen."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
STAGE=ROOT/'toolchain/releases-staging/windows-3.5.45'
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from core import HOME
from validate_live_lots6_8 import get,models,preserved_files,content_fingerprints,backup_config
from releases import profile,digest
from signing import public
from updater import verify


def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def identity(value):
    stable={k:v for k,v in value.items() if k not in ('version','protocol','client_name','local_routes')}
    return hashlib.sha256(json.dumps(stable,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def idle():
    state=get('/api/state')
    assert not state['queue']['active'] and not state['queue']['waiting'],'Wait for active model requests'
    assert not get('/api/voice')['busy'],'Wait for voice playback'
    assert not any(run['status'] in ('starting','running','waiting_for_approval')
                   for run in get('/api/remote')['hermes'].get('runs',[])),'Wait for active agents'


def run():
    assert not (OUT/'publication.json').exists(),'Already published; inspect evidence before retrying'
    idle()
    backups=get('/api/backups')
    assert backups['job']['state']=='succeeded','A fresh verified backup must finish first'
    verified=[item for item in backups['catalog'] if item.get('verified') and item.get('kind')=='manual']
    assert verified and max(item['timestamp'] for item in verified)>time.time()-3600,'Fresh verified manual backup required'
    assert (HOME/'wireguard-prive/signature.dpapi').is_file(),'Keep the existing signing key'
    manifest=json.loads((STAGE/'build-manifest.json').read_text(encoding='utf-8'))
    source=STAGE/'Accès serveur Fred.exe'
    result=OUT/'base-self-test.txt'
    completed=subprocess.run([str(source),'--self-test','--result',str(result)],timeout=60,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert completed.returncode==0 and 'self-test OK' in result.read_text(encoding='utf-8'),'Native EXE smoke failed'
    from voice_max_package import package
    voice_catalogue,voice_archive=package(HOME)
    from max_installation import verify_catalogue
    verify_catalogue(voice_catalogue,public(HOME,create=False))
    active_ids={item['id'] for item in json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))['clients'] if not item['revoked']}
    credentials={path.stem:identity(profile(path)) for path in (HOME/'clients').glob('*.exe')}
    before={'models':models(),'files':preserved_files(),'users':content_fingerprints(),
            'backups':backup_config(backups),'personal_identities':credentials,
            'old_version':get('/api/releases')['server_version'],
            'backup_verified':True,'backup_sha256':max(verified,key=lambda item:item['timestamp'])['sha256']}
    assert before['models']
    if (OUT/'avant-livraison.json').exists():
        original=json.loads((OUT/'avant-livraison.json').read_text(encoding='utf-8'))
        assert all(original[key]==before[key] for key in ('models','files','users','backups','personal_identities')),'State changed while resuming publication'
        before=original
    else:
        write('avant-livraison.json',before)
    previous=STAGE/'previous';previous.mkdir(exist_ok=True)
    destination=ROOT/'client-qwen/dist'
    for name in ('Accès serveur Fred.exe','build-manifest.json','release.json'):
        old=destination/name
        if old.exists() and not (previous/name).exists():shutil.copy2(old,previous/name)
    idle()
    for name in ('Accès serveur Fred.exe','build-manifest.json'):
        pending=destination/(name+'.publish.tmp')
        shutil.copy2(STAGE/name,pending);pending.replace(destination/name)
    import releases
    release=releases.manifest(HOME)
    verify(release,public(HOME,create=False))
    assert release['version']=='3.5.45' and releases.status(HOME)['verified']
    prepared=releases.repackage(HOME)
    for path in (HOME/'clients').glob('*.exe'):
        if path.stem in credentials:
            assert identity(profile(path))==credentials[path.stem],'Personal access changed'
        if path.stem in active_ids:
            assert profile(path)['version']=='3.5.45'
            test_result=OUT/'personal-self-test.txt'
            check=subprocess.run([str(path),'--self-test','--with-profile','--result',str(test_result)],timeout=60,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            assert check.returncode==0 and 'self-test OK' in test_result.read_text(encoding='utf-8')
    prepared_count=sum(path.stem in active_ids and profile(path)['version']=='3.5.45' for path in (HOME/'clients').glob('*.exe'))
    write('publication.json',{'version':release['version'],'sha256':release['sha256'],'bytes':release['bytes'],
          'signature_verified':True,'personal_clients_prepared':prepared_count,
          'personal_credentials_preserved':True,'voice_revision':voice_catalogue['revision'],
          'voice_pack_bytes':voice_catalogue['runtime']['bytes']})
    spec=importlib.util.spec_from_file_location('kiara_delivery_restart',ROOT/'maintenance/2026-10-21-api-embeddings/livrer.py')
    delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery);delivery.OUT=OUT
    delivery.restart()
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            state=get('/api/state');voice=get('/api/voice');remote=get('/api/remote')
            if state['health']['loaded'] and voice['ready'] and remote['hermes']['service']['available']:break
        except (OSError,ValueError,KeyError):pass
        time.sleep(1)
    else:raise TimeoutError('Services did not become ready after reloading the gateway')
    active=get('/api/releases')
    assert active['server_version']=='3.5.45' and active['verified']
    assert voice['voice']=='Tiphaine'
    assert models()==before['models'],'Qwen processes changed'
    assert preserved_files()==before['files'],'Access/settings/key files changed'
    assert content_fingerprints()==before['users'],'User histories or data changed'
    assert backup_config(get('/api/backups'))==before['backups'],'Backup policy changed'
    personal=profile(next(path for path in (HOME/'clients').glob('*.exe') if path.stem in active_ids))
    headers={'Authorization':'Bearer '+personal['token'],'X-Fred-Agent-Protocol':'4'}
    def request(path,authenticated=True):
        return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8766'+path,headers=headers if authenticated else {}),timeout=30)
    with request('/v1/client/release') as response:
        served=json.load(response);verify(served,personal['update_public_key'])
        assert served['version']=='3.5.45' and served['sha256']==release['sha256']
    with request('/v1/voice/max/package') as response:
        served_voice=verify_catalogue(json.load(response),personal['update_public_key'])
        assert served_voice['revision']==voice_catalogue['revision']
    for route,expected in (('/v1/client/download',release),('/v1/voice/max/package/download',voice_catalogue['runtime'])):
        check=hashlib.sha256();size=0
        with request(route) as response:
            while block:=response.read(1024*1024):size+=len(block);check.update(block)
        assert size==expected['bytes'] and check.hexdigest()==expected['sha256'],'Published download mismatch'
    try:
        with request('/v1/voice/max/package/download',False):raise AssertionError('Unauthenticated voice download allowed')
    except urllib.error.HTTPError as error:
        assert error.code==401
        error.close()
    result={'passed':True,'version':'3.5.45','update_available':True,'base_and_voice_downloads_verified':True,
            'voice_pack_authenticated':True,'personal_credentials_preserved':True,'qwen_processes_preserved':True,
            'settings_keys_user_data_preserved':True,'backup_schedule_preserved':True,'low_voice':'Tiphaine',
            'personal_clients_prepared':prepared_count,'automatic_max_download':False}
    write('production.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':run()
