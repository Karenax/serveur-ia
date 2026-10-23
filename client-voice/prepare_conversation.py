"""Download only the reviewed, pinned shared Windows ASR catalogue."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT/'toolchain/asr-models'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true')
    args=parser.parse_args()
    spec=json.loads((ROOT/'client-voice/conversation-models.json').read_text(encoding='utf-8'))
    CACHE.mkdir(parents=True,exist_ok=True)
    for item in spec['files']:
        path=CACHE/item['name']
        if not path.exists() and args.download:
            part=path.with_suffix(path.suffix+'.part')
            with urllib.request.urlopen(item['url'],timeout=60) as response,part.open('wb') as output:
                while block:=response.read(1024*1024):
                    output.write(block)
                    if output.tell()>item['bytes']:raise ValueError('Unexpected model size')
            with part.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if part.stat().st_size!=item['bytes'] or digest!=item['sha256']:raise ValueError('Invalid model download')
            os.replace(part,path)
        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if path.stat().st_size!=item['bytes'] or digest!=item['sha256']:raise ValueError('Invalid cached model: '+item['name'])
        print(item['name'],item['bytes'],digest,flush=True)


if __name__=='__main__':main()
