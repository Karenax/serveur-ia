"""Controle physique de chaque page de la copie PLE privee, sans toucher au moteur."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import time
import psutil

parser=argparse.ArgumentParser()
parser.add_argument('--pid',type=int,required=True)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
process=psutil.Process(args.pid)
if process.name().lower()!='strata.exe':
    raise RuntimeError('Le PID ne correspond pas a Strata')
table_bytes=28800138240
page=4096
allocation_bytes=((table_bytes+page-1)//page)*page
class Region(c.Structure):
    _fields_=[('base',c.c_void_p),('allocation_base',c.c_void_p),('allocation_protect',w.DWORD),
              ('partition_id',w.WORD),('size',c.c_size_t),('state',w.DWORD),('protect',w.DWORD),('kind',w.DWORD)]
class Page(c.Structure):
    _fields_=[('address',c.c_void_p),('attributes',c.c_size_t)]
k32=c.WinDLL('kernel32',use_last_error=True)
psapi=c.WinDLL('psapi',use_last_error=True)
k32.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]
k32.OpenProcess.restype=w.HANDLE
k32.VirtualQueryEx.argtypes=[w.HANDLE,c.c_void_p,c.POINTER(Region),c.c_size_t]
k32.VirtualQueryEx.restype=c.c_size_t
k32.CloseHandle.argtypes=[w.HANDLE]
psapi.QueryWorkingSetEx.argtypes=[w.HANDLE,c.c_void_p,w.DWORD]
psapi.QueryWorkingSetEx.restype=w.BOOL
handle=k32.OpenProcess(0x0400|0x0010,False,args.pid)
if not handle:
    raise c.WinError(c.get_last_error())
start=time.monotonic()
try:
    address=0
    candidates=[]
    while address<2**47:
        region=Region()
        if not k32.VirtualQueryEx(handle,address,c.byref(region),c.sizeof(region)):
            break
        if region.state==0x1000 and region.kind==0x20000 and region.size==allocation_bytes:
            candidates.append(region.base)
        following=(region.base or 0)+region.size
        if following<=address:
            raise RuntimeError('Region de memoire invalide')
        address=following
    if len(candidates)!=1:
        raise RuntimeError('Copie PLE privee introuvable ou ambigue: '+str(candidates))
    base=candidates[0]
    total=allocation_bytes//page
    valid=locked=0
    for first in range(0,total,131072):
        count=min(131072,total-first)
        entries=(Page*count)()
        for i in range(count):
            entries[i].address=base+(first+i)*page
        if not psapi.QueryWorkingSetEx(handle,entries,c.sizeof(entries)):
            raise c.WinError(c.get_last_error())
        for entry in entries:
            present=bool(entry.attributes&1)
            valid+=present
            locked+=present and bool(entry.attributes&(1<<22))
    result=dict(pid=args.pid,engine_exe=process.exe(),table_bytes=table_bytes,
        allocation_address=hex(base),pages=total,valid_pages=valid,locked_pages=locked,
        complete=valid==locked==total,elapsed_seconds=round(time.monotonic()-start,2))
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
    if not result['complete']:
        raise RuntimeError('La table PLE ne reside pas entierement en RAM verrouillee')
finally:
    k32.CloseHandle(handle)
