"""Check packaged UI, versions, native audio, update profile and Android signer."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
STAGE=ROOT/'toolchain/releases-staging/eg2-20261021'
sys.path[:0]=[str(ROOT/'client-qwen'),str(ROOT/'lanceur')]
from PyInstaller.archive.readers import CArchiveReader
from wg_crypto import keypair
from updater import VERSION

binary=STAGE/'windows/Accès serveur Fred.exe'
archive=CArchiveReader(str(binary))
assert archive.extract('wireguard-bridge.exe')==(ROOT/'client-qwen/wireguard-bridge.exe').read_bytes()
checked=['wireguard-bridge.exe']
for name in ('chat.html','workspace.html','markdown.js','voice/fredaec.dll',
             'voice/conversation-worker/conversation-worker.exe'):
    stored=name.replace('/','\\') if name.replace('/','\\') in archive.toc else name
    assert archive.extract(stored)==(ROOT/'client-qwen'/name).read_bytes(),name
    checked.append(name)
with tempfile.TemporaryDirectory(prefix='fred-audit-exe-') as folder:
    base=Path(folder);private,public=keypair()
    profile={'url':'wireguard://10.77.0.1:8766','transport':'wireguard','token':'qwen_'+'a'*16+'_'+'b'*43,
        'protocol':3,'version':VERSION,'wireguard':{'private_key':private,'server_public_key':public,
        'preshared_key':public,'address':'10.77.0.2/32','endpoint':'example.test:51820'}}
    personal=base/'Fred-verification.exe';shutil.copyfile(binary,personal)
    encoded=json.dumps(profile).encode()
    with personal.open('ab') as stream:stream.write(encoded+struct.pack('<I',len(encoded))+b'QWENPROFILE1')
    output=base/'result.txt'
    result=subprocess.run([str(personal),'--self-test','--with-profile','--voice-self-test','--result',str(output)],
        capture_output=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and output.is_file(),result.stderr[-1000:]
release=json.loads((STAGE/'android/release.json').read_text(encoding='utf-8-sig'))
apk=STAGE/'android/Acces-serveur-Fred-Android.apk'
assert release['version']=='1.0.13' and release['version_code']==14
with apk.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==release['sha256']
with zipfile.ZipFile(apk) as package:
    assert package.read('assets/android-chat.html')==(ROOT/'client-android/app/src/main/assets/android-chat.html').read_bytes()
    assert not any(name.endswith(('.fred-android','.dpapi')) for name in package.namelist())
    assert all(package.getinfo('lib/'+abi+'/libfredwireguard.so').file_size>0 for abi in ('arm64-v8a','x86_64'))
signing=(OUT/'build-android.txt').read_text(encoding='utf-8',errors='replace')
expected=json.loads((ROOT/'maintenance/2026-10-21-correctifs-audit/signatures-nas.json').read_text())['android_certificate_sha256']
assert expected in signing.lower(), 'Android signer changed or signer proof absent'
with binary.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
report={'passed':True,'windows_version':VERSION,'windows_sha256':sha,'windows_profile_self_test':True,
        'windows_silent_pcm_voice_self_test':True,'embedded_files_verified':checked,
        'android_version':release['version'],'android_code':release['version_code'],
        'android_sha256':release['sha256'],'android_signing_key_preserved':True,'android_ui_matches_sources':True}
(OUT/'artefacts.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Windows and Android artifacts verified; existing Android signer retained.')
