"""Prepare pinned local keyword spotting resources; no ASR/runtime replacement."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import tarfile
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
MODEL='sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20'
ASSETS=[('https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/'+MODEL+'.tar.bz2',32885699,'68447f4fbc67e70eee3a93961f36e81e98f47aef73ce7e7ca00885c6cd3616a6'),
        ('https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.8/sherpa-onnx-1.13.8.aar',50129134,'633c24321e06b1fe79feafa03ea16cbc0f8a286641e2da3559bac91bdb13bd96')]


def main():
    p=argparse.ArgumentParser();p.add_argument('--download',action='store_true');args=p.parse_args()
    cache=ROOT/'toolchain/wakeword-downloads';cache.mkdir(parents=True,exist_ok=True)
    for url,size,sha in ASSETS:
        path=cache/url.rsplit('/',1)[1]
        if not path.exists():
            if not args.download:raise ValueError('Run prepare_wakeword.py --download first')
            with urllib.request.urlopen(url,timeout=45) as src,path.open('wb') as dst:
                total=0
                while block:=src.read(1024*1024):
                    total+=len(block)
                    if total>size:raise ValueError('Artifact exceeds pinned size')
                    dst.write(block)
        if path.stat().st_size!=size or hashlib.file_digest(path.open('rb'),'sha256').hexdigest()!=sha:
            raise ValueError('Pinned artifact verification failed: '+path.name)
    outputs=[ROOT/'client-qwen/voice/wakeword',ROOT/'client-android/app/src/main/assets/wakeword']
    files={name:MODEL+'/'+original for name,original in {
        'encoder.onnx':'encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx',
        'decoder.onnx':'decoder-epoch-13-avg-2-chunk-8-left-64.onnx',
        'joiner.onnx':'joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx',
        'tokens.txt':'tokens.txt'}.items()}
    manifest={'format':1,'engine':'sherpa-onnx 1.13.8','phrase':'Bonjour Kiara','experimental':True,
              'model':MODEL,'languages':['en','zh'],'files':[]}
    with tarfile.open(cache/(MODEL+'.tar.bz2'),'r:bz2') as archive:
        for name,member in files.items():
            entry=archive.getmember(member)
            if not entry.isfile() or entry.size>20*1024*1024:raise ValueError('Invalid model member')
            raw=archive.extractfile(entry).read()
            for directory in outputs:directory.mkdir(parents=True,exist_ok=True);(directory/name).write_bytes(raw)
            manifest['files'].append({'name':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    # Acoustic spelling for the complete phrase. A two-token standalone name
    # would also trigger ordinary French "qui a" and is deliberately excluded.
    raw=('b ú sh uō j iǎ :1.5 #0.25 @KIARA\n'
         'b ú sh uō j iā :1.5 #0.25 @KIARA\n').encode('utf-8')
    for directory in outputs:(directory/'keywords.txt').write_bytes(raw)
    manifest['files'].append({'name':'keywords.txt','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    for directory in outputs:(directory/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for filename,url in [('SHERPA-APACHE-2.0.txt','https://raw.githubusercontent.com/k2-fsa/sherpa-onnx/v1.13.8/LICENSE'),
                         ('KOTLIN-APACHE-2.0.txt','https://raw.githubusercontent.com/JetBrains/kotlin/v2.0.21/license/LICENSE.txt'),
                         ('ONNXRUNTIME-MIT.txt','https://raw.githubusercontent.com/microsoft/onnxruntime/v1.28.2/LICENSE')]:
        license_path=cache/filename
        if not license_path.exists():
            if not args.download:raise ValueError('License missing: '+filename)
            license_path.write_bytes(urllib.request.urlopen(url,timeout=30).read(200000))
        for directory in outputs:shutil.copy2(license_path,directory/filename)
    (ROOT/'client-voice/wakeword-models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Pinned wakeword resources prepared; French acoustic validation is still required.')


if __name__=='__main__':main()
