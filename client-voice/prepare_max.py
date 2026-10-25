"""Explicit opt-in installation of the independent Max runtimes and pinned weights."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ASR = ('mistralai/Voxtral-Mini-4B-Realtime-2602', '2769294da9567371363522aac9bbcfdd19447add')
TTS = ('Qwen/Qwen3-TTS-12Hz-1.7B-Base', 'fd4b254389122332181a7c3db7f27e918eec64e3')


def select_device(requested):
    if requested!='auto':return requested
    try:
        result=subprocess.run(['nvidia-smi','--query-gpu=index,compute_cap,memory.free','--format=csv,noheader,nounits'],
            capture_output=True,text=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=True)
        cards=[]
        for line in result.stdout.splitlines():
            index,capability,free=[part.strip() for part in line.split(',')]
            if float(capability)>=7.5 and int(free)>=20*1024:cards.append((int(free),int(index)))
        if cards:return 'cuda:'+str(max(cards)[1])
    except (OSError,ValueError,subprocess.SubprocessError):pass
    return 'cpu'


def main():
    parser = argparse.ArgumentParser()
    target=parser.add_mutually_exclusive_group()
    target.add_argument('--home', type=Path)
    target.add_argument('--server', action='store_true')
    parser.add_argument('--device', choices=('auto','cpu','cuda:0','cuda:1','cuda:2'), default='auto')
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if not args.download:
        print('Installation explicite : ajouter --download (deux runtimes et environ 13 Go de modèles).')
        return
    default_home=Path(__file__).resolve().parents[1]/'toolchain/voice-max-server' if args.server else Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'QwenClient/voice-max'
    home = (args.home or default_home).resolve()
    args.device=select_device(args.device)
    if any(part in str(home).casefold() for part in ('strata-src', 'phonon-server-python', 'conversation-client-python')):
        raise ValueError('Choisissez un dossier indépendant pour le moteur Max.')
    home.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(home).free < 30*1024**3:
        raise ValueError('Au moins 30 Go libres sont nécessaires pour préparer le mode Max.')
    worker = Path(__file__).with_name('max_worker.py')
    for name in ('python', 'tts-python'):
        folder = home/name
        if not (folder/'Scripts/python.exe').is_file():
            venv.EnvBuilder(with_pip=True).create(folder)
        python = folder/'Scripts/python.exe'
        if sys.version_info[:2]!=(3,12):raise ValueError('La préparation Max nécessite Python 3.12.')
        wheels=json.loads(Path(__file__).with_name('max-torch-wheels.json').read_text(encoding='utf-8'))['cpu' if args.device=='cpu' else 'cu128']
        torch_requirements=home/(name+'-torch.requirements.txt')
        torch_requirements.write_text('\n'.join(package+' @ '+item['url']+' --hash=sha256:'+item['sha256'] for package,item in wheels.items())+'\n',encoding='utf-8')
        subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
            '--no-deps','--require-hashes','-r',str(torch_requirements)], check=True)
        requirements=Path(__file__).with_name('requirements-max-'+('asr' if name=='python' else 'tts')+'.txt')
        subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check','--require-hashes','-r',str(requirements),
                        '--report', str(home/(name+'-installation.json'))], check=True)
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
        versions = subprocess.check_output([str(python), '-m', 'pip', 'freeze'], text=True)
        (home/(name+'-versions.txt')).write_text(versions, encoding='utf-8')
    python = home/'python/Scripts/python.exe'
    script = """import hashlib,json,sys
from pathlib import Path
from huggingface_hub import HfApi,snapshot_download
settings=json.loads(sys.stdin.read())
for item in settings:
    snapshot_download(item['repo'],revision=item['revision'],local_dir=item['target'],
        allow_patterns=['*.json','*.safetensors','*.model','*.txt','README.md','LICENSE*','NOTICE*','**/*.json','**/*.safetensors'],
        ignore_patterns=['consolidated.safetensors'])
    info=HfApi().model_info(item['repo'],revision=item['revision'],files_metadata=True)
    for expected in info.siblings:
        path=Path(item['target'])/expected.rfilename
        if path.is_file():
            with path.open('rb') as source:
                actual=hashlib.file_digest(source,'sha256' if expected.lfs else 'sha1') if expected.lfs else None
            if expected.lfs:
                valid=actual.hexdigest()==expected.lfs.sha256
            else:
                content=path.read_bytes()
                valid=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\\0'+content).hexdigest()==expected.blob_id
            if not valid:raise ValueError('Downloaded model does not match pinned repository: '+expected.rfilename)
"""
    specifications = [{'repo': repo, 'revision': revision, 'target': str(home/name)}
                      for name, (repo, revision) in (('asr', ASR), ('tts', TTS))]
    subprocess.run([str(python), '-c', script], input=json.dumps(specifications), text=True, check=True,
        env={**os.environ,'HF_HOME':str(home/'hub-cache'),'HF_XET_CACHE':str(home/'xet-cache')})
    shutil.copyfile(worker, home/'worker.py')
    shutil.copyfile(Path(__file__).with_name('french_voice.py'),home/'french_voice.py')
    shutil.copytree(Path(__file__).with_name('max-french'),home/'voices/fr-fr',dirs_exist_ok=True)
    manifest = {}
    for name in ('asr', 'tts', 'voices'):
        for file in (home/name).rglob('*'):
            if file.is_file() and '.cache' not in file.parts and file.name!='consolidated.safetensors':
                with file.open('rb') as source:
                    manifest[file.relative_to(home).as_posix()] = {'bytes': file.stat().st_size, 'sha256': hashlib.file_digest(source, 'sha256').hexdigest()}
    configuration = {'device': args.device, 'asr': str(home/'asr'), 'tts': str(home/'tts'),
                     'models': specifications, 'manifest': manifest}
    (home/'runtime.json').write_text(json.dumps(configuration, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Mode Max installé. Lancez Tester le PC / serveur dans Vocal pour vérifier la fluidité.')


if __name__ == '__main__':
    main()
