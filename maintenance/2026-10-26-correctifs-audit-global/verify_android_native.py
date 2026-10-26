"""Inspect the actual signed APK, including both embedded Go runtime generations."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def main():
    folder=ROOT/'toolchain/releases-staging/android'
    release=json.loads((folder/'release.json').read_text(encoding='utf-8-sig'))
    apk=folder/'Acces-serveur-Kiara-Android.apk'
    spec=json.loads((ROOT/'client-qwen/wireguard-toolchain.json').read_text(encoding='utf-8'))
    go=ROOT/'client-qwen/wireguard-tools/versions'/spec['version']/'go/bin/go.exe'
    assert hashlib.sha256(apk.read_bytes()).hexdigest()==release['sha256']
    binaries={}
    with zipfile.ZipFile(apk) as packed,tempfile.TemporaryDirectory(prefix='kiara-apk-go-') as temporary:
        for abi in ('arm64-v8a','x86_64'):
            data=packed.read('lib/'+abi+'/libfredwireguard.so')
            path=Path(temporary)/('wireguard-'+abi+'.so');path.write_bytes(data)
            value=subprocess.check_output([str(go),'version','-m',str(path)],text=True,timeout=30)
            assert value.splitlines()[0].endswith(': '+spec['version']),value.splitlines()[0]
            binaries[abi]={'go':spec['version'],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        licenses=json.loads(packed.read('assets/third-party/manifest.json'))
        assert any(row.get('version')==spec['version'] for row in licenses['components'])
        assert not any(name.lower().endswith(('.dpapi','.fred-android')) or name.lower().endswith('/profil.json')
                       for name in packed.namelist())
    proof={'passed':True,'apk_sha256':release['sha256'],'version':release['version'],
           'version_code':release['version_code'],'native_bridges':binaries,'private_profiles_embedded':False}
    (OUT/'android-native-validation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps(proof))


if __name__=='__main__':main()
