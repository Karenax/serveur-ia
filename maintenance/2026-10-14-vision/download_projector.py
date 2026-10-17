"""Fetch Strata's pinned vision projector and verify its published LFS hash."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
REPO='ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF'
REVISION='ed59f92082b1e93c0e96d60a8b11aab089b52f09'
NAME='mmproj-Qwen3.8-Flash-Next-BF16.gguf'
TARGET=ROOT/'strata-data/vision'/NAME


def main():
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/tree/{REVISION}',timeout=30) as response:
        row=next(item for item in json.load(response) if item.get('path')==NAME)
    size=row['size'];expected=row['lfs']['oid']
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    def digest(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    url=f'https://huggingface.co/{REPO}/resolve/{REVISION}/{NAME}'
    if not (TARGET.is_file() and TARGET.stat().st_size==size and digest(TARGET)==expected):
        temporary=TARGET.with_suffix('.gguf.partial');offset=temporary.stat().st_size if temporary.exists() else 0
        request=urllib.request.Request(url+'?download=true',headers={'User-Agent':'Fred-vision-trial/1','Range':f'bytes={offset}-'})
        with urllib.request.urlopen(request,timeout=60) as response:
            append=response.status==206 and offset>0
            if not append:offset=0
            last=time.monotonic()
            with temporary.open('ab' if append else 'wb') as stream:
                while block:=response.read(4*1024*1024):
                    stream.write(block);offset+=len(block)
                    if time.monotonic()-last>=15:
                        print(f'Projector: {offset/2**20:.0f} / {size/2**20:.0f} MiB',flush=True);last=time.monotonic()
        assert temporary.stat().st_size==size and digest(temporary)==expected,'Projector integrity check failed'
        temporary.replace(TARGET)
    report={'repository':REPO,'revision':REVISION,'file':NAME,'url':url,'bytes':size,'sha256':expected,'verified':True}
    (OUT/'projector.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
