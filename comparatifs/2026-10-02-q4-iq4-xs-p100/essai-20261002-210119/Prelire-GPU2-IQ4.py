"""Read-only, rate-limited warming of the second P100's expert banks."""
import ctypes as c
import json
from pathlib import Path
import re
import sys
import time

root = Path(__file__).resolve().parent
archive = Path((root / 'comparatif-iq4-courant.txt').read_text(encoding='utf-8-sig').strip())
flag = archive / 'prelecture-en-cours.flag'
flag.write_text('Second GPU file-page warming; benchmarks must wait.\n', encoding='utf-8')
started = time.perf_counter()
read = total = 0
checksum = 0
state = dict(status='starting', read_gib=0, total_gib=0)

def save_state():
    state.update(read_gib=read / 2**30, total_gib=total / 2**30,
                 elapsed_seconds=time.perf_counter()-started,
                 note='Read-only startup aid. No inference benchmarks run while this helper is active.')
    (archive / 'etat-prelecture-gpu2.json').write_text(
        json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

try:
    import numpy as np
    sys.path.insert(0, str(root / 'Strata-src' / 'tools'))
    from gguf_reader import GGUFFile
    paths = sorted((root / 'strata-data' / 'model-q4').glob(
        'Qwen3.8-Flash-Next-Uncensored-IQ4_XS-*.gguf'))
    files = [GGUFFile(path) for path in paths]
    maps = [np.memmap(path, dtype=np.uint8, mode='r') for path in paths]
    banks = []
    for i, file in enumerate(files):
        for tensor in sorted(file.tensors, key=lambda t:t.offset):
            match = re.fullmatch(r'blk\.(\d+)\..*_exps\.weight', tensor.name)
            if match and int(match[1]) >= 24:
                banks.append((i, tensor))
    total = sum(t.expected_bytes() for _,t in banks)
    if len(banks) != 72:
        raise RuntimeError(f'Expected 72 expert banks for layers 24-47, got {len(banks)}')
    k32 = c.WinDLL('kernel32', use_last_error=True)
    k32.GetCurrentProcess.restype = c.c_void_p
    class Range(c.Structure):
        _fields_=[('VirtualAddress',c.c_void_p), ('NumberOfBytes',c.c_size_t)]
    pvm = k32.PrefetchVirtualMemory
    pvm.argtypes=[c.c_void_p,c.c_size_t,c.POINTER(Range),c.c_ulong]
    pvm.restype=c.c_int
    process = k32.GetCurrentProcess()
    chunk = 4 * 2**20
    rate = 48 * 2**20
    state.update(status='reading', block_mib=4, rate_limit_mib_s=48, layers=[24,47])
    save_state()
    for i, tensor in banks:
        first = files[i].data_start + tensor.offset
        size = tensor.expected_bytes()
        for offset in range(0,size,chunk):
            view = maps[i][first+offset:first+min(size,offset+chunk)]
            entry = Range(view.ctypes.data,view.size)
            pvm(process,1,c.byref(entry),0)
            checksum=(checksum+int(view.view(np.uint64).sum(dtype=np.uint64)))&((1<<64)-1)
            read += view.size
            pause = read/rate-(time.perf_counter()-started)
            if pause > 0:
                time.sleep(pause)
        state['last_tensor'] = tensor.name
        save_state()
        print(json.dumps(state, ensure_ascii=False),flush=True)
    state.update(status='complete', checksum_u64=checksum)
except BaseException as error:
    state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                 error=repr(error))
    raise
finally:
    save_state()
    flag.unlink(missing_ok=True)
