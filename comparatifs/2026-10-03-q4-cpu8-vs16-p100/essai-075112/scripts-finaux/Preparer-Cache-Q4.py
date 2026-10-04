"""Create an optional contiguous native expert pack; --plan validates its layout without copying weights."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', type=Path, default=Path('C:/Strata-cache/q4-experts-contigus'))
p.add_argument('--plan', action='store_true')
a = p.parse_args()
sys.path.insert(0, str(root / 'Strata-src' / 'tools'))
from gguf_reader import GGUFFile
base = root / 'strata-data' / 'q4-local'
native_dir = root / 'strata-data' / 'model-q4'
files = [GGUFFile(path) for path in sorted(native_dir.glob('Qwen3.8-Flash-Next-UD-Q4_K_XL-*.gguf'))]
tensors = {t.name: (f, t) for f in files for t in f.tensors}
text = (base / 'native_experts.txt').read_text(encoding='utf-8')
layout = []
for line in text.splitlines():
    if not line or line.startswith('#'): continue
    row = line.split(); layer, gt, dt, offset, blob = map(int, row[:5])
    shards = row[8].split(','); shards = shards * 3 if len(shards) == 1 else shards
    roles = []
    for r, name in enumerate(('gate', 'up', 'down')):
        f, t = tensors[f'blk.{layer}.ffn_{name}_exps.weight']
        if f.path.name != shards[r] or f.data_start+t.offset != int(row[5+r]):
            raise RuntimeError('Native source span mismatch at layer '+str(layer))
        if t.type_id != (gt if r < 2 else dt) or t.shape[-1] != 512:
            raise RuntimeError('Native format/shape mismatch at layer '+str(layer))
        size = t.expected_bytes()
        if size is None or size % 512: raise RuntimeError('Unrecognized native byte layout')
        roles.append((f.path, f.data_start+t.offset, size, t.name))
    if sum(r[2] for r in roles) != 512*blob:
        raise RuntimeError('Expert blob size mismatch')
    layout.append((layer, offset, blob, roles))
if len(layout) != 48 or [x[0] for x in layout] != list(range(48)):
    raise RuntimeError('Expected all 48 native layers in order')
total = sum(512*x[2] for x in layout)
if any(offset != sum(512*x[2] for x in layout[:layer]) for layer, offset, _, _ in layout):
    raise RuntimeError('Layer offsets are not contiguous')
identity = dict(schema=1, shards=[dict(name=f.path.name,size=f.path.stat().st_size) for f in files],
                native_experts_sha256=hashlib.sha256(text.encode()).hexdigest(), bytes=total)
source_stat = {f.path.name: f.path.stat().st_mtime_ns for f in files}
plan = dict(bytes=total,gib=total/2**30,layers=48,experts_per_layer=512,
            target=str(a.out),source=identity,source_mtime_ns=source_stat,
            note='Native gate/up/down bytes are copied unchanged. No requantization. '
                 'One preparation pass, separate from inference benchmarks. Startup gain remains to be measured.')
print(json.dumps(plan,ensure_ascii=False,indent=2),flush=True)
if a.plan: raise SystemExit(0)
marker = a.out / 'cache-source.json'
if a.out.exists():
    if not marker.exists() or json.loads(marker.read_text()) != plan:
        raise RuntimeError('Output folder is not an unfinished cache from this exact source')
else:
    a.out.mkdir(parents=True)
    marker.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copytree(base,a.out,dirs_exist_ok=True)
if (a.out/'experts.bin').exists():
    if ((a.out/'experts.bin').stat().st_size == total and
            json.loads((a.out/'experts.bin.src.json').read_text()) == identity):
        print('Complete native expert cache already exists.',flush=True); raise SystemExit(0)
    raise RuntimeError('Existing expert cache does not match this source')
tmp = a.out/'experts.bin.tmp'
existing_bytes = tmp.stat().st_size if tmp.exists() else 0
if existing_bytes > total: raise RuntimeError('Partial cache exceeds the native layout')
if shutil.disk_usage(a.out).free < total - existing_bytes + 10*2**30:
    raise RuntimeError('Insufficient remaining disk space with 10 GiB headroom')
resume_layers = sum(offset + 512*blob <= existing_bytes for _,offset,blob,_ in layout)
print(f'Resuming after byte-for-byte verification of {resume_layers} already copied layers.',flush=True)
import numpy as np
block = 16*2**20
digest = hashlib.sha256(); checks = []
streams = {f.path: f.path.open('rb',buffering=0) for f in files}
with tmp.open('r+b' if tmp.exists() else 'w+b',buffering=0) as output:
    for layer, offset, blob, roles in layout:
        combined = np.empty((512,blob),dtype=np.uint8)
        column = 0
        for path, start, size, name in roles:
            bank = np.empty(size,dtype=np.uint8); stream=streams[path]; stream.seek(start)
            at=0
            while at<size:
                n=stream.readinto(bank[at:at+min(block,size-at)])
                if not n: raise EOFError(name)
                at+=n
            width=size//512
            combined[:,column:column+width]=bank.reshape(512,width)
            checks.append(dict(tensor=name,sha256=hashlib.sha256(bank).hexdigest()))
            column+=width
            del bank
        view=memoryview(combined).cast('B'); at=0
        output.seek(offset)
        while at<len(view):
            data=view[at:at+block]
            if layer < resume_layers:
                actual=output.read(len(data))
                if actual != data: raise RuntimeError(f'Copied bytes differ from the source at layer {layer}')
                n=len(actual)
            else:
                n=output.write(data)
            if not n: raise OSError('Incomplete cache write')
            digest.update(data[:n]); at+=n
        output.flush(); os.fsync(output.fileno())
        action='verified' if layer < resume_layers else 'written'
        print(f'Native layer {layer+1}/48 {action}: {output.tell()/2**30:.2f} GiB',flush=True)
        del data, view, combined
    output.truncate(total)
for stream in streams.values(): stream.close()
if tmp.stat().st_size != total: raise RuntimeError('Incomplete cache size')
# Compare first/middle/last experts in three layers against the original quantized bytes.
with tmp.open('rb') as output:
    for index in (0,23,47):
        layer, offset, blob, roles=layout[index]
        for expert in (0,256,511):
            expected=[]
            for path,start,size,name in roles:
                with path.open('rb') as stream:
                    width=size//512; stream.seek(start+expert*width); expected.append(stream.read(width))
            output.seek(offset+expert*blob)
            if output.read(blob)!=b''.join(expected): raise RuntimeError('Native expert comparison failed')
side=a.out/'experts.bin.src.json'
side.write_text(json.dumps(identity,indent=2)+'\n',encoding='utf-8')
(a.out/'verification-cache.json').write_text(json.dumps(dict(sha256=digest.hexdigest(),roles=checks,
    verified_samples=9,bytes=total,source_mtime_ns=source_stat),indent=2)+'\n',encoding='utf-8')
tmp.replace(a.out/'experts.bin')
print('Contiguous native expert cache completed and validated.',flush=True)
