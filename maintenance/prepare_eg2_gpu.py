"""Prepare the explicitly selected CUDA runtime from pinned public wheels."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def main():
    config=json.loads((ROOT/'lanceur/eg2-runtime.json').read_text(encoding='utf-8'))
    python=(ROOT/config['python']).resolve()
    assert python.is_relative_to(ROOT/'toolchain') and python.name=='python.exe'
    cpu=ROOT/'toolchain/eg2-python'
    assert (cpu/'Scripts/python.exe').is_file(),'Prepare the CPU runtime first'
    env=python.parents[1]
    if not python.is_file():subprocess.run([str(cpu/'Scripts/python.exe'),'-m','venv','--without-pip',str(env)],check=True)
    (env/'Lib/site-packages/eg2_dependencies.pth').write_text(
        str(cpu/'Lib/site-packages')+'\n'+str(ROOT/'shared')+'\n',encoding='utf-8')
    versions=json.loads(subprocess.check_output([str(python),'-c',
        "import importlib.metadata as m,json;print(json.dumps({p:m.version(p) for p in ('torch','torchvision')}))"],text=True))
    expected={'torch':'2.14.1+cu126','torchvision':'0.29.1+cu126'}
    if versions!=expected:
        lock=(ROOT/'dependances/verrous/eg2-gpu.requirements.txt').read_text(encoding='utf-8')
        urls=[line for line in lock.splitlines() if line.startswith('https://download-r2.pytorch.org/whl/cu126/')]
        assert len(urls)==2
        folder=ROOT/'toolchain/eg2-cuda-wheels';folder.mkdir(exist_ok=True);wheels=[]
        for raw in urls:
            url,wanted=raw.split('#sha256=');name=urllib.parse.unquote(url.rsplit('/',1)[1]);target=folder/name
            assert target.resolve().is_relative_to(folder)
            if not target.is_file():
                key=hashlib.sha224(url.encode()).hexdigest()
                cache=Path(os.environ['LOCALAPPDATA'])/'pip/Cache/http-v2'
                cache=cache.joinpath(*key[:5],key+'.body')
                if cache.is_file():shutil.copy2(cache,target)
                else:
                    partial=target.with_suffix('.whl.part')
                    with urllib.request.urlopen(url,timeout=60) as response,partial.open('wb') as output:
                        shutil.copyfileobj(response,output,1024*1024)
                    partial.replace(target)
            with target.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
            assert actual==wanted,'Wheel hash mismatch: '+name
            wheels.append(str(target))
        uv=Path(os.environ['LOCALAPPDATA'])/'hermes/bin/uv.exe'
        subprocess.run([str(uv),'pip','install','--python',str(python),'--no-deps','--no-index',*wheels],check=True)
    subprocess.run([str(python),'-m','pip','check'],check=True)
    print('CUDA runtime ready. CPU dependencies remain separately locked and available for fallback.')


if __name__=='__main__':main()
