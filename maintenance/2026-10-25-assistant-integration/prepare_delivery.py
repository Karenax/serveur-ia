"""Verify staged resources, preserve signing identities, and create a verified backup."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from validate_live_lots6_8 import get,post,PHRASE,preserved_files,content_fingerprints,models


def sha(path):
    with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()


def main():
    windows=ROOT/'toolchain/releases-staging/windows-3.5.52'
    android=ROOT/'toolchain/releases-staging/android-1.0.23'
    for folder in (windows,android):
        manifest=json.loads((folder/'build-manifest.json').read_text(encoding='utf-8'))
        artifact=folder/manifest['artifact']['name']
        assert artifact.stat().st_size==manifest['artifact']['bytes'] and sha(artifact)==manifest['artifact']['sha256']
    from PyInstaller.archive.readers import CArchiveReader
    archive=CArchiveReader(str(windows/'Accès serveur Fred.exe'))
    assert archive.extract('workspace.html')==(ROOT/'client-qwen/workspace.html').read_bytes()
    assert archive.extract('conversation.js')==(ROOT/'client-qwen/conversation.js').read_bytes()
    pyz=archive.open_embedded_archive('PYZ.pyz')
    assert all(name in pyz.toc for name in ('screen_capture','PIL.ImageGrab','conversation_service'))
    wake_manifest=json.loads(archive.extract('voice\\wakeword\\manifest.json'))
    for record in wake_manifest['files']:
        raw=archive.extract('voice\\wakeword\\'+record['name'])
        assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256']
    with zipfile.ZipFile(android/'Acces-serveur-Kiara-Android.apk') as apk:
        assert apk.read('assets/android-chat.html')==(ROOT/'client-android/app/src/main/assets/android-chat.html').read_bytes()
        assert all(name in apk.namelist() for name in ('assets/wakeword/manifest.json','lib/arm64-v8a/libsherpa-onnx-jni.so','lib/x86_64/libsherpa-onnx-jni.so'))
        for record in wake_manifest['files']:
            assert hashlib.sha256(apk.read('assets/wakeword/'+record['name'])).hexdigest()==record['sha256']
    key_names=('toolchain/android-signing/fred-client.p12','toolchain/android-signing/password.dpapi')
    key_hashes={name:sha(ROOT/name) for name in key_names}
    (OUT/'key-fingerprints.json').write_text(json.dumps(key_hashes,indent=2),encoding='utf-8')
    signer=ROOT/'toolchain/android-sdk/build-tools/36.0.0/apksigner.bat'
    old=ROOT/'client-android/dist/Acces-serveur-Kiara-Android.apk'
    cert=subprocess.check_output([str(signer),'verify','--verbose','--print-certs',str(old)],text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT/'previous-signature.txt').write_text(cert,encoding='utf-8')
    before={'files':preserved_files(),'users':content_fingerprints(),'models':models()}
    assert before['models']
    state=get('/api/state')
    assert not state['queue']['active'] and not state['queue']['waiting'],'Wait for current interactive work'
    phrase=PHRASE.read_text(encoding='utf-8')
    post('/api/backups/create',{'password':phrase})
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        backups=get('/api/backups')
        if backups['job']['state']!='running':break
        time.sleep(.5)
    assert backups['job']['state']=='succeeded','Backup must complete before publication'
    newest=max((row for row in backups['catalog'] if row.get('kind')=='manual'),key=lambda row:row['timestamp'])
    verification=post('/api/backups/verify',{'file':newest['file'],'password':phrase})
    assert verification['summary']['sha256']==newest['sha256']
    assert before=={'files':preserved_files(),'users':content_fingerprints(),'models':models()}
    report={'passed':True,'staged_resources_verified':True,'windows_modules_present':True,'android_jni_both_abis':True,
            'backup_verified':True,'backup_sha256':newest['sha256'],'existing_data_unchanged':True}
    (OUT/'delivery-preparation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
