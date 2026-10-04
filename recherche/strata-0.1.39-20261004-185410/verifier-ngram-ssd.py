"""Controle en lecture seule du mode PLE SSD et de l'absence de copie RAM complete."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'normal-ngram-ssd-262144'
parser=argparse.ArgumentParser()
parser.add_argument('--pid',type=int,required=True)
args=parser.parse_args()
process=psutil.Process(args.pid)
config=json.loads((RUN/'config.json').read_text(encoding='utf-8'))
if Path(process.exe()).resolve()!=Path(config['exe']).resolve():
    raise RuntimeError('Mauvais moteur')
command=process.cmdline()
if command[command.index('--ple-io')+1]!='direct':
    raise RuntimeError('Le moteur ne lit pas la PLE en mode direct')
path=Path(command[command.index('--ple-gguf')+1])
if path.drive.upper()!='C:':
    raise RuntimeError('La PLE n\'est pas sur C')
table_bytes=28800138240
class Region(c.Structure):
    _fields_=[('base',c.c_void_p),('allocation_base',c.c_void_p),('allocation_protect',w.DWORD),
              ('partition_id',w.WORD),('size',c.c_size_t),('state',w.DWORD),('protect',w.DWORD),('kind',w.DWORD)]
k32=c.WinDLL('kernel32',use_last_error=True)
k32.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD]
k32.OpenProcess.restype=w.HANDLE
k32.VirtualQueryEx.argtypes=[w.HANDLE,c.c_void_p,c.POINTER(Region),c.c_size_t]
k32.VirtualQueryEx.restype=c.c_size_t
k32.CloseHandle.argtypes=[w.HANDLE]
handle=k32.OpenProcess(0x0400|0x0010,False,args.pid)
if not handle:
    raise c.WinError(c.get_last_error())
try:
    address=0
    full_copies=[]
    large_private=[]
    while address<2**47:
        region=Region()
        if not k32.VirtualQueryEx(handle,address,c.byref(region),c.sizeof(region)):
            break
        if region.state==0x1000 and region.kind==0x20000:
            if region.size==((table_bytes+4095)//4096)*4096:
                full_copies.append(hex(region.base))
            if region.size>=2**30:
                large_private.append(dict(base=hex(region.base),bytes=region.size))
        following=(region.base or 0)+region.size
        if following<=address:
            raise RuntimeError('Region memoire invalide')
        address=following
    result=dict(pid=args.pid,mode='direct',table=str(path),table_bytes=table_bytes,
        full_private_table_copies=full_copies,large_private_allocations=large_private,
        engine_ram_gib=process.memory_info().rss/2**30,verified=not full_copies,
        note='Absence of the complete private PLE allocation used by our RAM mode; direct I/O bypasses Windows file cache, while the bounded row cache remains enabled.')
    (RUN/'ngram-ssd-verifie.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    if full_copies:
        raise RuntimeError('Une copie RAM complete est encore presente')
finally:
    k32.CloseHandle(handle)
