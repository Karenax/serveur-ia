"""Build a credential-free Linux client archive, including a native Go bridge."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('client','linux_support','fred_http','product','updater','history_store','wg_bridge',
           'connection_settings','app_integrations','hermes_catalogue','file_lock',
           'draft_store','history_sync','history_migrations','chat_attachments',
           'opencode_visibility','advanced_voice','max_installation','local_voice',
           'conversation_service','screen_capture')
ASSETS = ('chat.html','workspace.html','ui.css','ui.js','markdown.js','attachments.js','corrector.js',
          'selection.js','thinking.js','voice.js','conversation.js','linux_features.js','fred-icon.png','LICENSE.txt','THIRD-PARTY.txt')


def build(output, architecture):
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
    archive = output/f'Kiara-linux-{architecture}-{VERSION}-vocal.tar.gz'
    with tempfile.TemporaryDirectory(prefix='kiara-linux-') as temporary:
        staging = Path(temporary)/f'Kiara-linux-{architecture}'
        (staging/'client/vendor').mkdir(parents=True)
        (staging/'shared/kiara_shared').mkdir(parents=True)
        for name in MODULES:
            shutil.copyfile(client/(name+'.py'),staging/'client'/(name+'.py'))
        for name in ASSETS:
            shutil.copyfile(client/name,staging/'client'/name)
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
        subprocess.run([str(go),'build','-p','2','-trimpath','-ldflags','-s -w',
                        '-o',str(staging/'client/wireguard-bridge'),'.'],
                       cwd=client/'wireguard-bridge',env={**environment,'GOOS':'linux','GOARCH':architecture},check=True)
        files = {path.relative_to(staging).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(staging.rglob('*')) if path.is_file()}
        manifest = {'format':1,'component':'linux','version':VERSION,'linux_revision':2,'architecture':architecture,
                    'go':version,'native_linux_validated':False,'files':files}
        (staging/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        # Publish only a complete archive. File modes are set independently of Windows.
        pending = archive.with_suffix('.tmp')
        try:
            with tarfile.open(pending,'w:gz') as packed:
                for path in [staging,*sorted(staging.rglob('*'))]:
                    info = packed.gettarinfo(str(path),arcname=path.relative_to(staging.parent).as_posix())
                    info.uid=info.gid=0;info.uname=info.gname=''
                    info.mode=0o755 if path.is_dir() or path.name in ('start.sh','wireguard-bridge') else 0o644
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
    options=parser.parse_args()
    build(options.output,options.architecture)
