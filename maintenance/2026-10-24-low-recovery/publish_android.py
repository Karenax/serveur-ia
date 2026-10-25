"""Publish the signed Android update after checking its original signing identity."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
STAGE=ROOT/'toolchain/releases-staging/android-1.0.18'
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from android_releases import status
from releases import profile


def digest(path):
    with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()


def main():
    release,source=status(STAGE)
    assert release['version']=='1.0.18' and release['version_code']==19
    tools=ROOT/'toolchain/android-sdk/build-tools/36.0.0'
    signature=subprocess.check_output([str(tools/'apksigner.bat'),'verify','--verbose','--print-certs',str(source)],
        text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (OUT/'signature.txt').write_text(signature,encoding='utf-8')
    def certificate(value):return re.search(r'^Signer #1 certificate SHA-256 digest: ([a-f0-9]{64})$',value,re.M).group(1)
    assert certificate(signature)==certificate((OUT/'previous-signature.txt').read_text(encoding='utf-8-sig'))
    key_files=json.loads((OUT/'key-fingerprints.json').read_text(encoding='utf-8'))
    assert all(digest(ROOT/name)==value for name,value in key_files.items()),'Existing Android signing key changed'
    badging=subprocess.check_output([str(tools/'aapt2.exe'),'dump','badging',str(source)],text=True,encoding='utf-8')
    assert "package: name='net.karenax.fred' versionCode='19' versionName='1.0.18'" in badging
    assert "application-label:'Accès serveur Kiara'" in badging
    (OUT/'badging.txt').write_text(badging,encoding='utf-8')
    with zipfile.ZipFile(source) as archive:
        names=archive.namelist()
        html=archive.read('assets/android-chat.html').decode('utf-8')
        assert 'classicLowSpeak' in html and 'classicLowRefresh' in html
        assert 'androidSharedError' in html
        assert 'conversationStatus' in html and 'voice-title' in html and 'Low · écoute sur cet appareil' in html
        assert 'conversation.js' in archive.read('assets/ui-package.json').decode('utf-8')
        assert all(name in names for name in ('assets/android-chat.html','assets/ui-package.json',
            'lib/arm64-v8a/libfredvoice.so','lib/x86_64/libfredvoice.so'))
        assert not any(name.lower().endswith(('.fred-android','.dpapi','.gguf')) or name.lower().endswith('/profil.json') for name in names)
    previous=STAGE/'previous';previous.mkdir(exist_ok=True)
    destination=ROOT/'client-android/dist'
    for path in destination.iterdir():
        if path.is_file() and (path.suffix=='.apk' or path.name.endswith('.apk.sha256') or path.name in ('release.json','build-manifest.json')):
            assert not (previous/path.name).exists(),'Previous distribution was already archived'
            shutil.copy2(path,previous/path.name)
    for name in (source.name,source.name+'.sha256','build-manifest.json','release.json'):
        temporary=destination/(name+'.publish.tmp')
        shutil.copy2(STAGE/name,temporary);temporary.replace(destination/name)
    current,apk=status()
    assert current==release and digest(apk)==release['sha256']
    access=json.loads((ROOT/'lanceur/acces-distants.json').read_text(encoding='utf-8'))
    active=next(item for item in access['clients'] if not item['revoked'])
    personal=profile(ROOT/'lanceur/clients'/(active['id']+'.exe'))
    headers={'Authorization':'Bearer '+personal['token'],'X-Fred-Agent-Protocol':'4'}
    base='http://127.0.0.1:8766'
    with urllib.request.urlopen(urllib.request.Request(base+'/v1/client/android/release',headers=headers),timeout=30) as response:
        served=json.load(response)
    assert served==release
    size=0;check=hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(base+'/v1/client/android/download',headers=headers),timeout=30) as response:
        while block:=response.read(1024*1024):size+=len(block);check.update(block)
    assert size==release['bytes'] and check.hexdigest()==release['sha256']
    result={'passed':True,**release,'file':str(apk),'signing_certificate_sha256':certificate(signature),
        'signing_key_preserved':True,'upgrade_compatible':True,'private_profiles_embedded':False,
        'served_download_verified':True,'physical_device_installation_tested':False}
    (OUT/'android-publication.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
