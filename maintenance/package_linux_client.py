"""Build a credential-free Linux client archive, including a native Go bridge."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('kiara_linux_package_contract', ROOT/'client-linux/linux_launch.py')
_contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_contract)
MODULES, ASSETS = _contract.CLIENT_MODULES, _contract.CLIENT_ASSETS


def build(output, architecture, tauri_binary=None, tauri_version=None):
    if tauri_binary is None:
        raise ValueError('Le binaire Tauri Linux et sa version sont nécessaires pour construire le client.')
    sys.path.insert(0,str(ROOT/'shared'))
    from kiara_shared.version import VERSION
    client = ROOT/'client-qwen'
    spec = json.loads((client/'wireguard-toolchain.json').read_text(encoding='utf-8'))
    go = client/'wireguard-tools/versions'/spec['version']/'go/bin/go.exe' if os.name=='nt' else Path(shutil.which('go') or '/missing-go')
    if not go.is_file():
        raise ValueError('Préparez le Go épinglé avec maintenance/prepare_go.py (ou installez cette version sous Linux).')
    environment = {**os.environ, 'GOTOOLCHAIN':'local', 'GOPROXY':'off', 'GOMAXPROCS':'2',
                   'GOPATH':str(client/'wireguard-tools/workspace'),
                   'GOCACHE':str(client/'wireguard-tools/cache'), 'CGO_ENABLED':'0'}
    version = subprocess.check_output([str(go),'version'],env=environment,text=True).strip()
    if spec['version'] not in version.split():
        raise ValueError('La version Go diffère de la version épinglée.')
    subprocess.run([str(go),'mod','verify'],cwd=client/'wireguard-bridge',env=environment,check=True)
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    tauri_binary = Path(tauri_binary).resolve(strict=True)
    if not tauri_binary.is_file():
        raise ValueError('Binaire Tauri Linux ELF attendu.')
    with tauri_binary.open('rb') as stream:
        header = stream.read(20)
    if len(header) < 20 or header[:6] != b'\x7fELF\x02\x01' or int.from_bytes(header[18:20], 'little') != {'amd64':62, 'arm64':183}[architecture]:
        raise ValueError('Binaire Tauri Linux ELF attendu.')
    if not tauri_version or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}', tauri_version):
        raise ValueError('Une version Tauri à trois nombres est nécessaire.')
    archive = output/f'Kiara-linux-{architecture}-{tauri_version}-tauri.tar.gz'
    with tempfile.TemporaryDirectory(prefix='kiara-linux-') as temporary:
        staging = Path(temporary)/f'Kiara-linux-{architecture}'
        (staging/'client/vendor').mkdir(parents=True)
        (staging/'shared/kiara_shared').mkdir(parents=True)
        for name in MODULES:
            shutil.copyfile(client/(name+'.py'),staging/'client'/(name+'.py'))
        # The shared API imports screen_capture; Linux supplies the portal backend.
        shutil.copyfile(client/'linux_screen_capture.py', staging/'client/screen_capture.py')
        for name in ASSETS:
            shutil.copyfile(client/name,staging/'client'/name)
        shutil.copyfile(ROOT/'client-tauri/src/recovery_init.js',staging/'client/recovery_init.js')
        voice = staging/'client/voice'
        (voice/'conversation-worker').mkdir(parents=True)
        shutil.copyfile(client/'voice/conversation-models.json',voice/'conversation-models.json')
        for name in ('conversation_worker','aec_capture','linux_audio','recognition','turn_features','max_recognition','wakeword_recognition'):
            shutil.copyfile(ROOT/'client-voice'/(name+'.py'),voice/'conversation-worker'/(name+'.py'))
        # The keyword spotter is bundled, with exactly the existing pinned resources.
        wake_spec = json.loads((client/'voice/wakeword/manifest.json').read_text(encoding='utf-8'))
        (voice/'wakeword').mkdir()
        for item in wake_spec['files']:
            source = client/'voice/wakeword'/item['name']
            if source.stat().st_size != item['bytes'] or hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Ressource du mot d’appel absente ou corrompue : '+item['name'])
            shutil.copyfile(source,voice/'wakeword'/item['name'])
        for name in ('manifest.json','KOTLIN-APACHE-2.0.txt','ONNXRUNTIME-MIT.txt','SHERPA-APACHE-2.0.txt'):
            shutil.copyfile(client/'voice/wakeword'/name,voice/'wakeword'/name)
        for path in (client/'vendor').iterdir():
            if path.is_file() and path.suffix in ('.js','.txt'):
                shutil.copyfile(path,staging/'client/vendor'/path.name)
        for path in (ROOT/'shared/kiara_shared').glob('*.py'):
            shutil.copyfile(path,staging/'shared/kiara_shared'/path.name)
        for name in ('start.sh','installer.py','linux_launch.py','requirements.txt','README.md'):
            # Shell scripts must retain LF even when the checkout uses CRLF.
            content=(ROOT/'client-linux'/name).read_text(encoding='utf-8')
            (staging/name).write_text(content,encoding='utf-8',newline='\n')
        shutil.copyfile(tauri_binary, staging/'kiara')
        for name in ('start-tauri.sh', 'kiara-relay'):
            content=(ROOT/'client-linux'/name).read_text(encoding='utf-8')
            (staging/name).write_text(content,encoding='utf-8',newline='\n')
        subprocess.run([str(go),'build','-p','2','-trimpath','-ldflags','-s -w',
                        '-o',str(staging/'client/wireguard-bridge'),'.'],
                       cwd=client/'wireguard-bridge',env={**environment,'GOOS':'linux','GOARCH':architecture},check=True)
        files = {path.relative_to(staging).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(staging.rglob('*')) if path.is_file()}
        if not _contract.REQUIRED_FILES <= files.keys():
            raise ValueError('Le paquet Linux ne contient pas tous les fichiers requis.')
        manifest = {'format':1,'component':'linux','version':tauri_version or VERSION,'linux_revision':2,'architecture':architecture,
                    'go':version,'native_linux_validated':False,'files':files}
        manifest.update(shell='tauri', relay_version=VERSION)
        (staging/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        # Publish only a complete archive. File modes are set independently of Windows.
        pending = archive.with_suffix('.tmp')
        try:
            with tarfile.open(pending,'w:gz') as packed:
                for path in [staging,*sorted(staging.rglob('*'))]:
                    info = packed.gettarinfo(str(path),arcname=path.relative_to(staging.parent).as_posix())
                    info.uid=info.gid=0;info.uname=info.gname=''
                    info.mode=0o755 if path.is_dir() or path.name in ('start.sh','start-tauri.sh','kiara','kiara-relay','wireguard-bridge') else 0o644
                    if path.is_file():
                        with path.open('rb') as stream:
                            packed.addfile(info,stream)
                    else:
                        packed.addfile(info)
            os.replace(pending,archive)
        finally:
            pending.unlink(missing_ok=True)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix+'.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    print(archive)
    return archive


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'client-linux/dist')
    parser.add_argument('--architecture',choices=('amd64','arm64'),default='amd64')
    parser.add_argument('--tauri-binary',type=Path,required=True,help='Binaire Tauri Linux compilé pour cette architecture')
    parser.add_argument('--tauri-version',required=True,help='Version à trois nombres du binaire Tauri')
    options=parser.parse_args()
    build(options.output,options.architecture,options.tauri_binary,options.tauri_version)
