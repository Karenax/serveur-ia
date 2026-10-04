"""Sequential read-only warming of expert file pages before inference benchmarking."""
import ctypes as c
import json
from pathlib import Path
import sys
import time
import numpy as np

root = Path(__file__).resolve().parent
sys.path.insert(0,str(root / 'Strata-src' / 'tools'))
from gguf_reader import GGUFFile
archive = Path((root / 'comparatif-iq4-courant.txt').read_text(encoding='utf-8-sig').strip())
flag = archive / 'prelecture-en-cours.flag'
flag.write_text('Sequential file-page warming; wait before benchmarking.\n',encoding='utf-8')
folder = root / 'strata-data' / 'model-q4'
paths = sorted(folder.glob('Qwen3.8-Flash-Next-Uncensored-IQ4_XS-*.gguf'))
files = [GGUFFile(path) for path in paths]
maps = [np.memmap(path,dtype=np.uint8,mode='r') for path in paths]
banks = [(i,t) for i,file in enumerate(files) for t in sorted(file.tensors,key=lambda t:t.offset)
         if t.name.endswith('_exps.weight')]
total = sum(t.expected_bytes() for _,t in banks)
k32 = c.WinDLL('kernel32',use_last_error=True)
k32.GetCurrentProcess.restype = c.c_void_p
class Range(c.Structure):
    _fields_=[('VirtualAddress',c.c_void_p),('NumberOfBytes',c.c_size_t)]
pvm = k32.PrefetchVirtualMemory
pvm.argtypes=[c.c_void_p,c.c_size_t,c.POINTER(Range),c.c_ulong]
pvm.restype=c.c_int
process = k32.GetCurrentProcess()
read = 0; checksum = 0; start=time.perf_counter()
for i,tensor in banks:
    first=files[i].data_start+tensor.offset
    size=tensor.expected_bytes()
    for offset in range(0,size,64*2**20):
        view=maps[i][first+offset:first+min(size,offset+64*2**20)]
        entry=Range(view.ctypes.data,view.size)
        pvm(process,1,c.byref(entry),0)
        checksum=(checksum+int(view.view(np.uint64).sum(dtype=np.uint64)))&((1<<64)-1)
        read+=view.size
    elapsed=time.perf_counter()-start
    print(json.dumps(dict(tensor=tensor.name,read_gib=read/2**30,total_gib=total/2**30,
                          elapsed_seconds=elapsed,average_mib_s=read/2**20/elapsed)),flush=True)
result=dict(read_bytes=read,total_expert_bytes=total,elapsed_seconds=time.perf_counter()-start,
            checksum_u64=checksum,note='Read-only sequential page warming; checksum is not a model SHA256.')
(archive / 'prelecture-experts.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
flag.unlink()
