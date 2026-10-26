"""Install the pinned Go archive after checking the official SHA-256."""
from pathlib import Path
import hashlib
import json
import re
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/'client-qwen/wireguard-toolchain.json'


def main():
    spec=json.loads(SPEC.read_text(encoding='utf-8'))
    if not re.fullmatch(r'go1\.\d+\.\d+',spec['version']):raise ValueError('Invalid pinned Go version')
    if not re.fullmatch('[a-f0-9]{64}',spec['sha256']):raise ValueError('Invalid Go archive hash')
    filename=spec['version']+'.windows-amd64.zip'
    directory=ROOT/'client-qwen/wireguard-tools'
    target=directory/'versions'/spec['version']
    executable=target/'go/bin/go.exe'
    archive=directory/filename
    directory.mkdir(exist_ok=True)
    if not archive.exists():urllib.request.urlretrieve('https://go.dev/dl/'+filename,archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=spec['sha256']:
        raise ValueError('Downloaded Go archive hash mismatch')
    if not executable.is_file():
        target.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive) as packed:
            for name in packed.namelist():
                resolved=(target/name).resolve()
                if not resolved.is_relative_to(target.resolve()):raise ValueError('Unsafe Go archive path')
            packed.extractall(target)
    print(executable)


if __name__=='__main__':main()
