"""Read-only, rate-limited warming of the native GGUF expert banks during startup."""
import argparse
import ctypes as c
import json
from pathlib import Path
import re
import sys
import time

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive', type=Path, required=True)
parser.add_argument('--config', type=Path, required=True)
parser.add_argument('--first-layer',type=int,default=24)
parser.add_argument('--last-layer',type=int,default=47)
parser.add_argument('--rate-mib',type=int,default=48)
parser.add_argument('--state-name',default='etat-prelecture-gpu2.json')
parser.add_argument('--cache-aware',action='store_true')
parser.add_argument('--order', choices=('file', 'native-copy'), default='file')
args = parser.parse_args()
if not (0 <= args.first_layer <= args.last_layer <= 47) or args.rate_mib <= 0:
    raise ValueError('Invalid layer range or rate')
archive = args.archive
config = json.loads(args.config.read_text(encoding='utf-8-sig'))
flag = archive / 'prelecture-en-cours.flag'
flag.write_text('Native expert file-page warming; benchmarks must wait.\n', encoding='utf-8')
started = time.perf_counter()
read = total = 0
skipped = hot = 0
checksum = 0
state = dict(status='starting', read_gib=0, total_gib=0)

def save_state():
    state.update(read_gib=read / 2**30, total_gib=total / 2**30,
                 skipped_verified_gib=skipped / 2**30, hot_read_gib=hot / 2**30,
                 elapsed_seconds=time.perf_counter()-started,
                 note='Read-only startup aid. No inference benchmarks run while this helper is active.')
    (archive / args.state_name).write_text(
        json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

try:
    import numpy as np
    sys.path.insert(0, str(root / 'Strata-src' / 'tools'))
    from gguf_reader import GGUFFile
    native = Path(config['args'][config['args'].index('--native') + 1])
    pattern = re.sub(r'-\d{5}-of-\d{5}\.gguf$', '-*.gguf', native.name)
    paths = sorted(native.parent.glob(pattern))
    files = [GGUFFile(path) for path in paths]
    maps = [np.memmap(path, dtype=np.uint8, mode='r') for path in paths]
    banks = []
    for i, file in enumerate(files):
        for tensor in sorted(file.tensors, key=lambda t:t.offset):
            match = re.fullmatch(r'blk\.(\d+)\..*_exps\.weight', tensor.name)
            if match and args.first_layer <= int(match[1]) <= args.last_layer:
                banks.append((i, tensor))
    if args.order == 'native-copy':
        role_order = {'ffn_gate_exps': 0, 'ffn_up_exps': 1, 'ffn_down_exps': 2}
        def native_order(entry):
            match = re.fullmatch(r'blk\.(\d+)\.(ffn_\w+_exps)\.weight', entry[1].name)
            return int(match[1]), role_order[match[2]]
        banks.sort(key=native_order)
    total = sum(t.expected_bytes() for _,t in banks)
    expected_banks = 3 * (args.last_layer-args.first_layer+1)
    if len(banks) != expected_banks:
        raise RuntimeError(f'Expected {expected_banks} expert banks, got {len(banks)}')
    k32 = c.WinDLL('kernel32', use_last_error=True)
    k32.GetCurrentProcess.restype = c.c_void_p
    class Range(c.Structure):
        _fields_=[('VirtualAddress',c.c_void_p), ('NumberOfBytes',c.c_size_t)]
    pvm = k32.PrefetchVirtualMemory
    pvm.argtypes=[c.c_void_p,c.c_size_t,c.POINTER(Range),c.c_ulong]
    pvm.restype=c.c_int
    process = k32.GetCurrentProcess()
    trim = k32.SetProcessWorkingSetSize
    trim.argtypes = [c.c_void_p, c.c_size_t, c.c_size_t]
    trim.restype = c.c_int
    chunk = 4 * 2**20
    rate = args.rate_mib * 2**20
    state.update(status='reading', block_mib=4, rate_limit_mib_s=args.rate_mib,
                 layers=[args.first_layer,args.last_layer],cache_aware=args.cache_aware,order=args.order)
    save_state()
    engine_log=Path(config['log'])
    for i, tensor in banks:
        if args.cache_aware:
            verified=re.findall(r'sequential copy layer (\d+)/48 verified',
                                engine_log.read_text(encoding='utf-8',errors='replace'))
            done=int(verified[-1]) if verified else 0
            layer=int(re.match(r'blk\.(\d+)\.',tensor.name)[1])
            if layer < done:
                skipped+=tensor.expected_bytes()
                state['last_tensor']=tensor.name
                save_state()
                continue
        first = files[i].data_start + tensor.offset
        size = tensor.expected_bytes()
        for offset in range(0,size,chunk):
            view = maps[i][first+offset:first+min(size,offset+chunk)]
            block_start=time.perf_counter()
            entry = Range(view.ctypes.data,view.size)
            pvm(process,1,c.byref(entry),0)
            checksum=(checksum+int(view.view(np.uint64).sum(dtype=np.uint64)))&((1<<64)-1)
            read += view.size
            duration=time.perf_counter()-block_start
            if args.cache_aware:
                if duration < .005:
                    hot+=view.size
                    pause=0
                else:
                    pause=view.size/rate-duration
            else:
                pause=read/rate-(time.perf_counter()-started)
            if pause > 0:
                time.sleep(pause)
        state['last_tensor'] = tensor.name
        save_state()
        # The warmed file pages remain on the Windows standby list. Do not retain tens of GiB
        # in this helper's working set when Strata checks available RAM for its pinned complement.
        trim(process, c.c_size_t(-1).value, c.c_size_t(-1).value)
        print(json.dumps(state, ensure_ascii=False),flush=True)
    state.update(status='complete', checksum_u64=checksum)
except BaseException as error:
    state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                 error=repr(error))
    raise
finally:
    save_state()
    flag.unlink(missing_ok=True)
