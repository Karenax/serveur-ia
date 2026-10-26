"""Publish verified local releases, preserve existing identities, and restart only Kiara."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
STAGE=ROOT/'toolchain/releases-staging'
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'maintenance')]
from core import HOME
from validate_live_lots6_8 import get,post,models,preserved_files,content_fingerprints,backup_config
from releases import profile
from signing import public
from kiara_shared.releases import verify as verify_release


def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def identity(value):
    stable={k:v for k,v in value.items() if k not in ('version','protocol','client_name','local_routes')}
    return hashlib.sha256(json.dumps(stable,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def user_fingerprints():
    result=content_fingerprints()
    database=HOME/'espaces-prives/espaces.sqlite3'
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=20) as db:
        tables=('personal_memories','assistant_items','assistant_commands','knowledge_exclusions')
        for name in (*tables,'assistant_settings'):
            query=('SELECT * FROM '+name+' ORDER BY 1,2') if name in tables else (
                "SELECT key,value FROM settings WHERE key LIKE 'assistant-%' OR key LIKE 'command-journal-floor:%' ORDER BY key")
            rows=db.execute(query).fetchall()
            values=[[value.hex() if isinstance(value,bytes) else value for value in row] for row in rows]
            result[name]={'count':len(rows),'sha256':hashlib.sha256(json.dumps(values,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()}
    return result


def idle():
    state=get('/api/state')
    assert not state['queue']['active'] and not state['queue']['waiting'],'Active model requests'
    assert not get('/api/voice')['busy'],'Active voice request'
    assert not any(r['status'] in ('starting','running','waiting_for_approval')
                   for r in get('/api/remote')['hermes'].get('runs',[])),'Active agent request'


def publish_file(source,destination,archive):
    destination.parent.mkdir(parents=True,exist_ok=True)
    archive.mkdir(parents=True,exist_ok=True)
    previous=archive/destination.name
    if destination.is_file() and not previous.exists():shutil.copy2(destination,previous)
    pending=destination.with_name(destination.name+'.audit-publish.tmp')
    shutil.copy2(source,pending);pending.replace(destination)


def main():
    assert not (OUT/'publication.json').exists(),'Inspect existing publication before retrying'
    from deployment_manifest import generate
    manifests=[STAGE/name/'build-manifest.json' for name in ('server','windows','android','voice-max')]
    validation=OUT/'validation-final/validation.json'
    generate(manifests,validation)
    for name in ('reconstruction-isolated.json','voice-package-validation.json','android-native-validation.json'):
        assert json.loads((OUT/name).read_text(encoding='utf-8'))['passed'],name
    assert json.loads((OUT/'reconstruction-isolated.json').read_text())['source_archive_sha256']==digest(STAGE/'server/kiara-server-sources.zip')
    assert json.loads((OUT/'android-native-validation.json').read_text())['apk_sha256']==digest(STAGE/'android/Acces-serveur-Kiara-Android.apk')
    assert 'self-test OK' in (STAGE/'windows/self-test.txt').read_text(encoding='utf-8')
    idle()
    before={'models':models(),'files':preserved_files(),'users':user_fingerprints(),
            'backups':backup_config(get('/api/backups')),
            'model_running':get('/api/state')['running'],
            'personal_identities':{p.stem:identity(profile(p)) for p in (HOME/'clients').glob('*.exe')}}
    assert (HOME/'wireguard-prive/signature.dpapi').is_file()
    write('avant-livraison.json',before)
    job=post('/api/backups/create',{'kind':'manual','protected':True})
    deadline=time.monotonic()+240
    while time.monotonic()<deadline:
        backup_state=get('/api/backups');current=backup_state['job']
        assert current['id']==job['job']['id'],'Backup job changed'
        if current['state'] in ('succeeded','failed'):break
        time.sleep(1)
    else:raise TimeoutError('Pre-delivery backup')
    assert current['state']=='succeeded',current.get('message')
    backup=current['result'];archive=Path(backup['file'])
    record=next(row for row in backup_state['catalog'] if row['id']==backup['id'])
    assert record['verified'] and digest(archive)==record['sha256']
    write('sauvegarde-avant.json',{'file':str(archive),'sha256':digest(archive),'bytes':archive.stat().st_size,
                                  'encrypted':True,'verified_by_operations':True,'secondary':backup.get('secondary',{}).get('status')})
    assert preserved_files()==before['files'] and user_fingerprints()==before['users']
    assert models()==before['models'],'Model state changed during preparation'
    idle()
    # APK signing identity must remain identical for an in-place Android update.
    from android_releases import status as android_status
    android,new_apk=android_status(STAGE/'android')
    _,old_apk=android_status()
    signer=ROOT/'toolchain/android-sdk/build-tools/36.0.0/apksigner.bat'
    def certificate(path):
        result=subprocess.check_output([str(signer),'verify','--print-certs',str(path)],
                                       creationflags=subprocess.CREATE_NO_WINDOW,text=True,timeout=45)
        return re.search(r'^Signer #1 certificate SHA-256 digest: ([a-f0-9]{64})$',result,re.M).group(1)
    assert certificate(new_apk)==certificate(old_apk),'Android signing identity changed'
    previous=STAGE/'previous-audit-3.5.53'
    windows=ROOT/'client-qwen/dist'
    for name in ('Accès serveur Fred.exe','build-manifest.json'):
        publish_file(STAGE/'windows'/name,windows/name,previous/'windows')
    if (windows/'release.json').is_file():shutil.copy2(windows/'release.json',previous/'windows/release.json')
    import releases
    release=releases.manifest(HOME);verify_release(release,public(HOME,create=False))
    assert release['version']=='3.5.53' and releases.status(HOME)['verified']
    prepared=releases.repackage(HOME)
    for path in (HOME/'clients').glob('*.exe'):
        if path.stem in before['personal_identities']:
            assert identity(profile(path))==before['personal_identities'][path.stem]
    for name in (new_apk.name,new_apk.name+'.sha256','build-manifest.json','release.json'):
        publish_file(STAGE/'android'/name,ROOT/'client-android/dist'/name,previous/'android')
    from voice_max_package import package
    catalogue,_=package(HOME,STAGE/'voice-max')
    for name in ('runtime.zip','release.json','build-manifest.json'):
        publish_file(STAGE/'voice-max'/name,ROOT/'toolchain/voice-max-release'/name,previous/'voice-max')
    # No live WireGuard process may retain the obsolete server helper.
    import psutil
    engine=(ROOT/'client-qwen/wireguard-bridge.exe').resolve()
    running=[]
    for process in psutil.process_iter(['exe']):
        try:
            if process.info['exe'] and Path(process.info['exe']).resolve()==engine:running.append(process.pid)
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    if not running:publish_file(STAGE/'wireguard-bridge.exe',engine,previous/'wireguard')
    write('publication.json',{'windows':release,'android':android,'voice_revision':catalogue['revision'],
          'personal_clients_prepared':prepared.get('count'),'personal_identities_preserved':True,
          'server_wireguard_replaced':not running,'previous_distribution':str(previous)})
    # Reuse the established, identity-checked restart procedure. It preserves
    # all model processes recorded immediately before this delivery.
    idle();assert models()==before['models']
    spec=importlib.util.spec_from_file_location('kiara_audit_restart',ROOT/'maintenance/2026-10-21-api-embeddings/livrer.py')
    delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery);delivery.OUT=OUT
    delivery.restart()
    finish(before,android,catalogue,bool(running))


def finish(before,android,catalogue,wireguard_pending):
    import releases
    from android_releases import status as android_status
    from voice_max_package import package
    if wireguard_pending:
        idle();assert models()==before['models']
        # Activation starts a new helper immediately. Pause only the owned
        # WireGuard service around replacement, then restore its enabled state.
        post('/api/remote/deactivate',{})
        try:
            publish_file(STAGE/'wireguard-bridge.exe',ROOT/'client-qwen/wireguard-bridge.exe',
                         STAGE/'previous-audit-3.5.53/wireguard')
        finally:post('/api/remote/activate',{})
        publication=json.loads((OUT/'publication.json').read_text(encoding='utf-8'))
        publication['server_wireguard_replaced']=True
        write('publication.json',publication)
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            remote=get('/api/remote')
            if remote['hermes']['service']['available']:break
        except (OSError,ValueError,KeyError):pass
        time.sleep(1)
    else:raise TimeoutError('Kiara/Hermes readiness after restart')
    assert releases.status(HOME)['verified'] and android_status()[0]==android
    assert package(HOME)[0]==catalogue
    assert models()==before['models'] and get('/api/state')['running']==before['model_running']
    assert preserved_files()==before['files'] and user_fingerprints()==before['users']
    assert backup_config(get('/api/backups'))==before['backups']
    write('production.json',{'passed':True,'server_windows':'3.5.53','android':'1.0.24','android_code':25,
        'voice_revision':catalogue['revision'],'personal_identities_preserved':True,'keys_settings_data_preserved':True,
        'backup_schedule_preserved':True,'model_processes_and_state_preserved':True,'hermes_ready':True,
        'microphone_tested':False,'physical_android_tested':False})
    print('Kiara 3.5.53 / Android 1.0.24 published and activated; data, identities and model state preserved.')


if __name__=='__main__':
    if '--resume-verification' in sys.argv:
        publication=json.loads((OUT/'publication.json').read_text(encoding='utf-8'))
        before=json.loads((OUT/'avant-livraison.json').read_text(encoding='utf-8'))
        from voice_max_package import package
        catalogue,_=package(HOME)
        finish(before,publication['android'],catalogue,not publication['server_wireguard_replaced'])
    else:main()
