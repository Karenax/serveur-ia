"""One-off read-only sequential warming during the authorized cold reload."""
import ctypes as c
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'mesures/essai-01/reprise-sans-seuil'
OUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('--from-layer', type=int, choices=range(48), default=0)
args = parser.parse_args()
sys.path.insert(0, str(ROOT / 'Strata-src/tools'))
from gguf_reader import GGUFFile

kernel = c.WinDLL('kernel32', use_last_error=True)
api = c.WinDLL('psapi', use_last_error=True)
kernel.GetCurrentProcess.restype = c.c_void_p
handle = kernel.GetCurrentProcess()
api.EmptyWorkingSet.argtypes = [c.c_void_p]
api.EmptyWorkingSet.restype = c.c_int

class Range(c.Structure):
    _fields_ = [('VirtualAddress', c.c_void_p), ('NumberOfBytes', c.c_size_t)]

kernel.PrefetchVirtualMemory.argtypes = [c.c_void_p, c.c_size_t, c.POINTER(Range), c.c_ulong]
kernel.PrefetchVirtualMemory.restype = c.c_int
paths = sorted((ROOT / 'strata-data/model-q4').glob('Qwen3.8-Flash-Next-Uncensored-IQ4_XS-*.gguf'))
files = [GGUFFile(p) for p in paths]
maps = [np.memmap(p, dtype=np.uint8, mode='r') for p in paths]
banks = [(i, t) for i, f in enumerate(files) for t in sorted(f.tensors, key=lambda t: t.offset)
         if t.name.endswith('_exps.weight') and int(t.name.split('.')[1]) >= args.from_layer]
total = sum(t.expected_bytes() for _, t in banks)
start = time.perf_counter()
read = checksum = since_trim = 0
stopped_for_memory = False
last_print = start
for i, tensor in banks:
    first = files[i].data_start + tensor.offset
    size = tensor.expected_bytes()
    for offset in range(0, size, 64 * 2**20):
        if psutil.virtual_memory().available < 24 * 2**30:
            stopped_for_memory = True
            break
        view = maps[i][first + offset:first + min(size, offset + 64 * 2**20)]
        entry = Range(view.ctypes.data, view.size)
        kernel.PrefetchVirtualMemory(handle, 1, c.byref(entry), 0)
        checksum = (checksum + int(view.view(np.uint64).sum(dtype=np.uint64))) & ((1 << 64) - 1)
        read += view.size
        since_trim += view.size
        if since_trim >= 2**30:
            # Only this reader's working set, never the inference engine's.
            api.EmptyWorkingSet(handle)
            since_trim = 0
        if time.perf_counter() - last_print >= 30:
            last_print = time.perf_counter()
            print(json.dumps({'read_gib': round(read / 2**30, 2),
                'total_gib': round(total / 2**30, 2),
                'elapsed_s': round(last_print - start),
                'available_gib': round(psutil.virtual_memory().available / 2**30, 2)}), flush=True)
    if stopped_for_memory:
        break
result = {'read_only': True, 'read_bytes': read, 'total_expert_bytes': total,
    'from_layer': args.from_layer,
    'elapsed_seconds': round(time.perf_counter() - start, 2), 'stopped_for_memory': stopped_for_memory,
    'reader_working_set_trim_only': True, 'checksum_u64': checksum}
name = 'prelecture.json' if args.from_layer == 0 else f'prelecture-{args.from_layer}.json'
(OUT / name).write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result), flush=True)
