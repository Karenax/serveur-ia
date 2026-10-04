"""Verrouille les pages partagees de la table PLE sans modifier Strata ni le GGUF."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
import psutil

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'source-officielle/tools'))
from gguf_reader import GGUFFile
parser=argparse.ArgumentParser()
parser.add_argument('--gguf',required=True,type=Path)
args=parser.parse_args()
state_path=ROOT/'ngram-ram.json'
stop_path=ROOT/'liberer-ngram.flag'
if stop_path.exists():
    stop_path.unlink()
g=GGUFFile(args.gguf)
table=next(t for t in g.tensors if t.name=='per_layer_token_embd.weight')
offset=g.data_start+table.offset
size=table.expected_bytes()
aligned=offset & ~4095
length=size+offset-aligned
pages=(length+4095)//4096
state=dict(status='chargement',pid=os.getpid(),path=str(args.gguf),tensor=table.name,
           offset=offset,bytes=size,gib=size/2**30,locked_bytes=0,verified_locked_pages=0)
def save():
    temporary=state_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(state_path)
save()
if psutil.virtual_memory().available<size+8*2**30:
    raise RuntimeError('RAM insuffisante pour la table et la marge de 8 GiB')
k=c.WinDLL('kernel32',use_last_error=True)
p=c.WinDLL('psapi',use_last_error=True)
def api(lib,name,types,result=w.BOOL):
    f=getattr(lib,name); f.argtypes=types; f.restype=result; return f
current=api(k,'GetCurrentProcess',[],w.HANDLE)()
set_ws=api(k,'SetProcessWorkingSetSizeEx',[w.HANDLE,c.c_size_t,c.c_size_t,w.DWORD])
lock=api(k,'VirtualLock',[c.c_void_p,c.c_size_t])
unlock=api(k,'VirtualUnlock',[c.c_void_p,c.c_size_t])
class Range(c.Structure):
    _fields_=[('address',c.c_void_p),('bytes',c.c_size_t)]
prefetch=api(k,'PrefetchVirtualMemory',[w.HANDLE,c.c_size_t,c.POINTER(Range),w.DWORD])
query=api(p,'QueryWorkingSetEx',[w.HANDLE,c.c_void_p,w.DWORD])
class Ws(c.Structure):
    _fields_=[('address',c.c_void_p),('attributes',c.c_size_t)]
if not set_ws(current,length+512*2**20,length+1024*2**20,2|8):
    raise c.WinError(c.get_last_error())
mapping=np.memmap(args.gguf,dtype=np.uint8,mode='r',offset=aligned,shape=(length,))
address=mapping.ctypes.data
chunk=32*2**20
started=time.monotonic()
locked=0
try:
    for at in range(0,length,chunk):
        if stop_path.exists():
            raise InterruptedError('Arret demande')
        n=min(chunk,length-at)
        entry=Range(address+at,n)
        if not prefetch(current,1,c.byref(entry),0):
            raise c.WinError(c.get_last_error())
        if not lock(address+at,n):
            raise c.WinError(c.get_last_error())
        locked=at+n
        state.update(locked_bytes=locked,elapsed_seconds=round(time.monotonic()-started,1),
                     available_ram_gib=round(psutil.virtual_memory().available/2**30,2))
        if at//chunk % 8==0 or locked==length:
            save()
            print(json.dumps(state,ensure_ascii=False),flush=True)
    # Check every table page, rather than just relying on VirtualLock's return value.
    batch=65536
    checked=0
    for first in range(0,pages,batch):
        count=min(batch,pages-first)
        data=(Ws*count)()
        for i in range(count):
            data[i].address=address+(first+i)*4096
        if not query(current,c.byref(data),c.sizeof(data)):
            raise c.WinError(c.get_last_error())
        good=sum(bool(x.attributes&1 and x.attributes&(1<<22)) for x in data)
        if good!=count:
            raise RuntimeError(f'Pages non verrouillees: {count-good} sur {count}')
        checked+=count
    state.update(status='verrouille',verified_locked_pages=checked,elapsed_seconds=round(time.monotonic()-started,1),
                 note='Read-only shared file pages held physically in RAM by an external process. Official Strata must use --ple-io mmap; its code is unchanged.')
    save()
    print(json.dumps(state,ensure_ascii=False),flush=True)
    while not stop_path.exists():
        time.sleep(2)
finally:
    for at in range(0,locked,chunk):
        unlock(address+at,min(chunk,locked-at))
    state.update(status='libere',released_after_seconds=round(time.monotonic()-started,1))
    save()
