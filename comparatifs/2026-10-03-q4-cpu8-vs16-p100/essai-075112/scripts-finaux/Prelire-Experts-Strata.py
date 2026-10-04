"""Read-only, rate-limited warming of the native GGUF expert banks during startup."""
import argparse
import ctypes as c
import json
import os
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
parser.add_argument('--reader', choices=('prefetch', 'file'), default='prefetch')
parser.add_argument('--pause-loader-pid', type=int)
parser.add_argument('--pause-loader-tid', type=int)
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
loader_handle = None
loader_paused = False
pause_flag = archive / 'copie-en-pause.json'

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
    streams = [path.open('rb', buffering=0) for path in paths] if args.reader == 'file' else []
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
    if args.pause_loader_pid is not None:
        if args.order != 'native-copy' or not args.cache_aware or args.pause_loader_tid is None:
            raise RuntimeError('Pausing the loader requires verified native copy order and a thread ID')
        k32.OpenThread.argtypes=[c.c_ulong,c.c_int,c.c_ulong]; k32.OpenThread.restype=c.c_void_p
        k32.GetProcessIdOfThread.argtypes=[c.c_void_p]; k32.GetProcessIdOfThread.restype=c.c_ulong
        k32.SuspendThread.argtypes=[c.c_void_p]; k32.SuspendThread.restype=c.c_ulong
        k32.ResumeThread.argtypes=[c.c_void_p]; k32.ResumeThread.restype=c.c_ulong
        loader_handle=k32.OpenThread(0x0002|0x0040,False,args.pause_loader_tid)
        if not loader_handle or k32.GetProcessIdOfThread(loader_handle)!=args.pause_loader_pid:
            raise RuntimeError('Startup loader thread belongs to another process')
        state.update(paused_loader_pid=args.pause_loader_pid, paused_loader_tid=args.pause_loader_tid)
    trim = k32.SetProcessWorkingSetSize
    trim.argtypes = [c.c_void_p, c.c_size_t, c.c_size_t]
    trim.restype = c.c_int
    chunk = 4 * 2**20
    rate = args.rate_mib * 2**20
    state.update(status='reading', block_mib=4, rate_limit_mib_s=args.rate_mib,
                 layers=[args.first_layer,args.last_layer],cache_aware=args.cache_aware,
                 order=args.order, reader=args.reader)
    save_state()
    engine_log=Path(config['log'])
    read_buffer = np.empty(chunk, dtype=np.uint8) if streams else None
    paused_layer = None
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
        if loader_handle and paused_layer is None:
            text=engine_log.read_text(encoding='utf-8',errors='replace')
            if 'sequential native RAM copy (P100 HDD mode)' not in text or 'sequential copy layer 48/48 verified' in text:
                raise RuntimeError('Engine is not in the verified startup copy phase')
            pause_flag.write_text(json.dumps(dict(engine_pid=args.pause_loader_pid,
                thread_id=args.pause_loader_tid,reader_pid=os.getpid())),encoding='utf-8')
            previous=k32.SuspendThread(loader_handle)
            if previous!=0:
                if previous!=0xffffffff: k32.ResumeThread(loader_handle)
                raise RuntimeError('Loader already suspended or suspension failed')
            loader_paused=True
            paused_layer=layer
        first = files[i].data_start + tensor.offset
        size = tensor.expected_bytes()
        if streams:
            streams[i].seek(first)
        for offset in range(0,size,chunk):
            block_start=time.perf_counter()
            if streams:
                view = read_buffer[:min(size-offset,chunk)]
                at = 0
                while at < view.size:
                    count = streams[i].readinto(view[at:])
                    if not count: raise EOFError(tensor.name)
                    at += count
            else:
                view = maps[i][first+offset:first+min(size,offset+chunk)]
                entry = Range(view.ctypes.data,view.size)
                pvm(process,1,c.byref(entry),0)
            checksum=(checksum+int(view.view(np.uint64).sum(dtype=np.uint64)))&((1<<64)-1)
            read += view.size
            if loader_paused and time.time()-pause_flag.stat().st_mtime>2:
                pause_flag.touch()
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
        if loader_paused and tensor.name.endswith('.ffn_down_exps.weight'):
            k32.ResumeThread(loader_handle)
            loader_paused=False
            pause_flag.unlink(missing_ok=True)
            wait_start=time.perf_counter()
            while True:
                verified=re.findall(r'sequential copy layer (\d+)/48 verified',
                                    engine_log.read_text(encoding='utf-8',errors='replace'))
                if verified and int(verified[-1])>=paused_layer+1: break
                if time.perf_counter()-wait_start>60:
                    raise RuntimeError('Warmed native layer did not finish copying within 60 seconds')
                time.sleep(.1)
            paused_layer=None
    state.update(status='complete', checksum_u64=checksum)
except BaseException as error:
    state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                 error=repr(error))
    raise
finally:
    if loader_paused and loader_handle:
        k32.ResumeThread(loader_handle)
    pause_flag.unlink(missing_ok=True)
    save_state()
    flag.unlink(missing_ok=True)
