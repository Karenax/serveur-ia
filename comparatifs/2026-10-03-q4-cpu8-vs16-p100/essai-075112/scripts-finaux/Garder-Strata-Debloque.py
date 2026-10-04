"""Resume a startup loader if its temporary prefetch helper exits or stops updating its heartbeat."""
import argparse
import ctypes as c
import json
from pathlib import Path
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--flag', type=Path, required=True)
p.add_argument('--pid', type=int, required=True)
p.add_argument('--tid', type=int, required=True)
a = p.parse_args()
k = c.WinDLL('kernel32', use_last_error=True)
def api(name, argtypes, restype=c.c_int):
    f = getattr(k,name); f.argtypes=argtypes; f.restype=restype; return f
open_thread = api('OpenThread',[c.c_ulong,c.c_int,c.c_ulong],c.c_void_p)
owner = api('GetProcessIdOfThread',[c.c_void_p],c.c_ulong)
resume = api('ResumeThread',[c.c_void_p],c.c_ulong)
open_process = api('OpenProcess',[c.c_ulong,c.c_int,c.c_ulong],c.c_void_p)
exit_code = api('GetExitCodeProcess',[c.c_void_p,c.POINTER(c.c_ulong)])
close = api('CloseHandle',[c.c_void_p])
thread = open_thread(0x0002|0x0040,0,a.tid)
if not thread or owner(thread)!=a.pid: raise RuntimeError('Wrong startup loader thread')
reader = None
try:
    while True:
        if not a.flag.exists():
            if reader:
                code=c.c_ulong()
                if not exit_code(reader,c.byref(code)) or code.value!=259: break
            time.sleep(1); continue
        try: state=json.loads(a.flag.read_text(encoding='utf-8'))
        except (OSError,ValueError): time.sleep(.2); continue
        if state['engine_pid']!=a.pid or state['thread_id']!=a.tid: raise RuntimeError('Flag does not match loader')
        if reader is None: reader=open_process(0x0400,0,state['reader_pid'])
        code=c.c_ulong()
        alive=bool(reader and exit_code(reader,c.byref(code)) and code.value==259)
        if not alive or time.time()-a.flag.stat().st_mtime>60:
            previous=resume(thread)
            print('Startup loader resumed by watchdog, previous suspend count: '+str(previous),flush=True)
            if not alive: break
        time.sleep(1)
finally:
    close(thread)
    if reader: close(reader)
