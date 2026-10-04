"""Copie brute de la seule table IQ4_NL dans un GGUF PLE sur le SSD C."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time

ROOT=Path(__file__).resolve().parent
PROD=ROOT.parent.parent
RUN=ROOT/'normal-ngram-ssd-262144'
sys.path.insert(0,str(PROD/'Strata-src/tools'))
from gguf_reader import GGUFFile

source=PROD/'strata-data/model-q4/Qwen3.8-Flash-Next-Uncensored-IQ4_XS-00001-of-00003.gguf'
output=Path(r'C:\Temp\Strata-ngram-recherche\iq4-xs-ple-iq4_nl.gguf')
state_path=RUN/'copie-ngram.json'
g=GGUFFile(source)
table=next(t for t in g.tensors if t.name=='per_layer_token_embd.weight')
if table.shape!=[160,320001536] or table.type_id!=20 or table.expected_bytes()!=28800138240:
    raise RuntimeError('Table source inattendue')
offset=g.data_start+table.offset
size=table.expected_bytes()
output.parent.mkdir(parents=True,exist_ok=True)
temporary=output.with_suffix('.gguf.part')
if output.exists() or temporary.exists():
    raise RuntimeError('La destination existe deja; ne pas la remplacer')
if shutil.disk_usage(output.parent).free<size+2*2**30:
    raise RuntimeError('Espace SSD insuffisant')

def string(value):
    raw=value.encode('utf-8')
    return struct.pack('<Q',len(raw))+raw

def kv(key,value):
    return string(key)+struct.pack('<I',8)+string(value)

metadata=[kv('general.architecture','strata-ple'),
          kv('general.name','IQ4_XS original PLE IQ4_NL, byte-exact SSD copy')]
header=b'GGUF'+struct.pack('<IQQ',3,1,len(metadata))+b''.join(metadata)
header+=string(table.name)+struct.pack('<IQQIQ',2,*table.shape,table.type_id,0)
header+=b'\0'*((-len(header))%32)
state=dict(status='copie',source=str(source),source_offset=offset,path=str(output),
           tensor=table.name,shape=table.shape,type=table.type_name,bytes=size,
           copied_bytes=0,header_bytes=len(header),note='Raw tensor bytes, no dequantization or requantization')
started=time.monotonic()

def save():
    state['elapsed_seconds']=round(time.monotonic()-started,1)
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(state,ensure_ascii=False),flush=True)

save()
digest=hashlib.sha256()
last_print=0
with source.open('rb') as reader,temporary.open('xb') as writer:
    writer.write(header)
    reader.seek(offset)
    while state['copied_bytes']<size:
        block=reader.read(min(64*2**20,size-state['copied_bytes']))
        if not block:
            raise RuntimeError('Lecture source incomplete')
        digest.update(block)
        writer.write(block)
        state['copied_bytes']+=len(block)
        if time.monotonic()-last_print>=20 or state['copied_bytes']==size:
            save()
            last_print=time.monotonic()
if temporary.stat().st_size!=len(header)+size:
    raise RuntimeError('Taille copie invalide')
state.update(status='verification',source_sha256=digest.hexdigest())
save()
copied_digest=hashlib.sha256()
with temporary.open('rb') as reader:
    reader.seek(len(header))
    while block:=reader.read(64*2**20):
        copied_digest.update(block)
if copied_digest.hexdigest()!=digest.hexdigest():
    raise RuntimeError('La copie differe de la table source')
probe=GGUFFile(temporary)
if len(probe.tensors)!=1 or probe.data_start!=len(header) or probe.tensors[0].expected_bytes()!=size:
    raise RuntimeError('Le GGUF copie est invalide')
temporary.rename(output)
state.update(status='verifie',copied_sha256=copied_digest.hexdigest(),verified_bytes=size)
save()
