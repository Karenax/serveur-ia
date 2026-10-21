"""Verify unchanged Android native sources and bytes against the published APK."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
dist=ROOT/'client-android/dist'
release=json.loads((dist/'release.json').read_text(encoding='utf-8-sig'))
apk=dist/'Acces-serveur-Fred-Android.apk'
with apk.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==release['sha256']
manifest=json.loads((dist/'build-manifest.json').read_text(encoding='utf-8-sig'))
names=['client-voice/fred_voice.cpp','client-voice/fred_voice.h','client-voice/fred_voice_jni.cpp',
       'client-qwen/wireguard-bridge/main.go','client-qwen/wireguard-bridge/go.mod','client-qwen/wireguard-bridge/go.sum']
for name in names:
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==manifest['source_files'][name],name
cmake=subprocess.check_output(['git','show',manifest['source_commit']+':client-voice/CMakeLists.txt'],cwd=ROOT)
assert cmake.replace(b'\r\n',b'\n')==(ROOT/'client-voice/CMakeLists.txt').read_bytes().replace(b'\r\n',b'\n')
checked=[]
with zipfile.ZipFile(apk) as archive:
    for name in archive.namelist():
        if name.startswith('lib/') and name.endswith('.so'):
            path=ROOT/'client-android/app/src/main/jniLibs'/name.removeprefix('lib/')
            assert hashlib.sha256(archive.read(name)).digest()==hashlib.sha256(path.read_bytes()).digest(),name
            checked.append(name)
assert checked
(OUT/'natif-android-inchange.json').write_text(json.dumps({'passed':True,'reference_apk_version':release['version'],
    'sources_verified':names+['client-voice/CMakeLists.txt'],'libraries_verified':checked},indent=2),encoding='utf-8')
print('Android native sources and libraries match the verified published APK.')
