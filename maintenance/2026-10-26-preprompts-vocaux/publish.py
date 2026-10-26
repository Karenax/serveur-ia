"""Publish the tested clients without changing access identities or user data."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from core import HOME
from validate_live_lots6_8 import get,models,preserved_files,content_fingerprints,backup_config
import releases
from android_releases import status as android_status


def identity(path):
    value=releases.profile(path)
    return {key:value[key] for key in value if key not in ('version','protocol','client_name','local_routes')}


def replace_distribution(stage,destination,names,archive):
    archive.mkdir(parents=True,exist_ok=True)
    for name in names:
        source=destination/name
        if source.exists():
            if (archive/name).exists():raise RuntimeError('Publication déjà commencée : '+name)
            shutil.copy2(source,archive/name)
    for name in names:
        if (stage/name).exists():
            pending=destination/(name+'.publish.tmp')
            shutil.copy2(stage/name,pending)
            pending.replace(destination/name)


def main():
    if (OUT/'publication-3.5.54.json').exists():raise RuntimeError('Version déjà publiée.')
    state=get('/api/state')
    assert not state['queue']['active'] and not state['queue']['waiting']
    backup=get('/api/backups')
    assert backup['job']['state']=='succeeded'
    assert any(item.get('verified') and item['timestamp']>time.time()-3600 for item in backup['catalog'])
    before={'models':models(),'files':preserved_files(),'users':content_fingerprints(),'backups':backup_config(backup)}
    credentials={path.stem:identity(path) for path in (HOME/'clients').glob('*.exe')}
    windows=ROOT/'toolchain/releases-staging/windows-3.5.54'
    android=ROOT/'toolchain/releases-staging/android-1.0.25'
    apk_release,apk=android_status(android)
    assert apk_release['version']=='1.0.25' and apk_release['version_code']==26
    assert (windows/'build-manifest.json').is_file()
    destination=ROOT/'client-qwen/dist'
    if (OUT/'previous-windows').exists():
        assert releases.digest(destination/'Accès serveur Fred.exe')==releases.digest(windows/'Accès serveur Fred.exe')
        release=releases.status(HOME)['release']
        for archive in HOME.glob('clients-retour-3.5.54*'):
            for old in archive.glob('*.exe'):
                assert identity(old)==identity(HOME/'clients'/old.name)
    else:
        replace_distribution(windows,destination,('Accès serveur Fred.exe','build-manifest.json','release.json'),OUT/'previous-windows')
        release=releases.manifest(HOME)
    assert release['version']=='3.5.54' and releases.status(HOME)['verified']
    releases.repackage(HOME)
    for path in (HOME/'clients').glob('*.exe'):
        if path.stem in credentials:assert identity(path)==credentials[path.stem]
    replace_distribution(android,ROOT/'client-android/dist',(apk.name,apk.name+'.sha256','build-manifest.json','release.json'),OUT/'previous-android')
    old=OUT/'activation.json'
    if old.exists():old.replace(OUT/'activation-before-token-change.json')
    subprocess.run([sys.executable,str(OUT/'activate.py')],check=True,timeout=150)
    assert models()==before['models'] and preserved_files()==before['files']
    assert content_fingerprints()==before['users']
    assert backup_config(get('/api/backups'))==before['backups']
    assert get('/api/releases')['server_version']=='3.5.54'
    assert get('/api/releases')['verified'] and get('/api/voice')['ready']
    assert android_status()[0]==apk_release
    active={item['id'] for item in json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))['clients'] if not item['revoked']}
    personal=releases.profile(next(path for path in (HOME/'clients').glob('*.exe') if path.stem in active))
    headers={'Authorization':'Bearer '+personal['token'],'X-Fred-Agent-Protocol':'4'}
    for route,expected in (('/v1/client/download',release),('/v1/client/android/download',apk_release)):
        digest=hashlib.sha256();size=0
        request=urllib.request.Request('http://127.0.0.1:8766'+route,headers=headers)
        with urllib.request.urlopen(request,timeout=30) as response:
            while block:=response.read(1024*1024):digest.update(block);size+=len(block)
        assert size==expected['bytes'] and digest.hexdigest()==expected['sha256']
    result={'passed':True,'windows':'3.5.54','android':'1.0.25','output_tokens':100000,
            'model_context':get('/api/state')['health']['max_context'],'low_ready':True,
            'model_processes_preserved':True,'keys_settings_and_user_data_preserved':True,
            'backup_schedule_preserved':True,'downloads_verified':True,'personal_clients':len(credentials)}
    (OUT/'publication-3.5.54.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
