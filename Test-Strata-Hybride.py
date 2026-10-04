"""Comparatif CPU+GPU séquentiel, sans modifier les archives GPU précédentes."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import threading
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--pid', required=True, type=int)
parser.add_argument('--fractions', default='1,.5,.25,0')
parser.add_argument('--repeats', default=2, type=int)
parser.add_argument('--sans-override', action='store_true', help='Vérifie le réglage de démarrage sans strata_tune dans la requête')
args = parser.parse_args()
OUT = ROOT/'comparatifs/2026-10-02-strata-hybride-p100'/dt.datetime.now().strftime(('validation-' if args.sans_override else 'essai-')+'%Y%m%d-%H%M%S')
OUT.mkdir(parents=True)
PROTOCOL = json.loads((ROOT/'protocole-comparatif-q4.json').read_text(encoding='utf-8-sig'))
CONFIG = json.loads((ROOT/'strata-q4-p100-hybride.json').read_text(encoding='utf-8-sig'))
LOG = ROOT/'strata-engine-p100.log'
CONFIG.update(binary_sha256=hashlib.sha256(Path(CONFIG['exe']).read_bytes()).hexdigest(), engine_pid=args.pid,
              fractions=args.fractions, repeats=args.repeats, request_override=not args.sans_override,
              created=dt.datetime.now().astimezone().isoformat())
(OUT/'configuration.json').write_text(json.dumps(CONFIG, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT/'protocole.json').write_text(json.dumps(PROTOCOL, ensure_ascii=False, indent=2), encoding='utf-8')

k32 = c.WinDLL('kernel32', use_last_error=True)
psapi = c.WinDLL('psapi', use_last_error=True)
nv = c.WinDLL(r'C:\Windows\System32\nvml.dll')
def api(lib, name, types, result=c.c_int):
    f=getattr(lib,name); f.argtypes=types; f.restype=result; return f
class FileTime(c.Structure):
    _fields_=[('low',w.DWORD),('high',w.DWORD)]
class Memory(c.Structure):
    _fields_=[('cb',w.DWORD),('faults',w.DWORD),('peak_ws',c.c_size_t),('ws',c.c_size_t),
              ('peak_paged',c.c_size_t),('paged',c.c_size_t),('peak_nonpaged',c.c_size_t),
              ('nonpaged',c.c_size_t),('pagefile',c.c_size_t),('peak_pagefile',c.c_size_t),('private',c.c_size_t)]
class Io(c.Structure):
    _fields_=[(name,c.c_ulonglong) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
class Util(c.Structure):
    _fields_=[('gpu',c.c_uint),('memory',c.c_uint)]
class GpuMemory(c.Structure):
    _fields_=[('total',c.c_ulonglong),('free',c.c_ulonglong),('used',c.c_ulonglong)]
openprocess=api(k32,'OpenProcess',[w.DWORD,w.BOOL,w.DWORD],w.HANDLE)
times=api(k32,'GetProcessTimes',[w.HANDLE]+[c.POINTER(FileTime)]*4,w.BOOL)
memory=api(psapi,'GetProcessMemoryInfo',[w.HANDLE,c.POINTER(Memory),w.DWORD],w.BOOL)
io=api(k32,'GetProcessIoCounters',[w.HANDLE,c.POINTER(Io)],w.BOOL)
handle=openprocess(0x0400|0x0010,False,args.pid)
if not handle: raise c.WinError(c.get_last_error())
def process_sample():
    ft=[FileTime() for _ in range(4)]
    if not times(handle,*[c.byref(x) for x in ft]): raise c.WinError(c.get_last_error())
    mem=Memory(); mem.cb=c.sizeof(mem); memory(handle,c.byref(mem),mem.cb)
    counter=Io(); io(handle,c.byref(counter))
    cpu=sum((x.high<<32)+x.low for x in ft[2:])/1e7
    return dict(cpu_seconds=cpu,ram_bytes=mem.ws,io_read_bytes=counter.read_bytes)
assert api(nv,'nvmlInit_v2',[])()==0
gethandle=api(nv,'nvmlDeviceGetHandleByIndex_v2',[c.c_uint,c.POINTER(c.c_void_p)])
util=api(nv,'nvmlDeviceGetUtilizationRates',[c.c_void_p,c.POINTER(Util)])
power=api(nv,'nvmlDeviceGetPowerUsage',[c.c_void_p,c.POINTER(c.c_uint)])
temp=api(nv,'nvmlDeviceGetTemperature',[c.c_void_p,c.c_uint,c.POINTER(c.c_uint)])
gpu_memory=api(nv,'nvmlDeviceGetMemoryInfo',[c.c_void_p,c.POINTER(GpuMemory)])
handles={}
for index in (1,2):
    h=c.c_void_p(); assert gethandle(index,c.byref(h))==0; handles[index]=h
def monitor(stop,rows,start):
    while not stop.is_set():
        proc=process_sample()
        for index,h in handles.items():
            u=Util(); p=c.c_uint(); t=c.c_uint(); gm=GpuMemory()
            eu=util(h,c.byref(u)); ep=power(h,c.byref(p)); et=temp(h,0,c.byref(t)); em=gpu_memory(h,c.byref(gm))
            rows.append(dict(seconds=time.perf_counter()-start,gpu_index=index,
                gpu_util_pct=u.gpu if eu==0 else None,memory_util_pct=u.memory if eu==0 else None,
                power_w=p.value/1000 if ep==0 else None,temp_c=t.value if et==0 else None,
                vram_bytes=gm.used if em==0 else None,**proc))
        stop.wait(.2)
def save_json(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
results=[]
for repeat in range(1,args.repeats+1):
    # Reverse the second pass to make monotonic clock/load drift less influential.
    fractions=[float(x) for x in args.fractions.split(',')]
    if repeat%2==0: fractions.reverse()
    for fraction in fractions:
        for test,prompt in enumerate(PROTOCOL['prompts'],1):
            name=f'r{repeat}-pcie{fraction:g}-test{test}'
            payload=dict(model=CONFIG['model_name'],messages=[dict(role='user',content=prompt)],
                max_tokens=PROTOCOL['max_tokens'],temperature=PROTOCOL['temperature'],seed=PROTOCOL['seed'],
                cache_prompt=PROTOCOL['cache_prompt'],chat_template_kwargs=dict(enable_thinking=PROTOCOL['enable_thinking']),
                strata_tune=dict(pcie_frac=fraction))
            if args.sans_override:
                payload.pop('strata_tune')
            save_json(f'{name}-requete.json',payload)
            before=len(LOG.read_text(encoding='utf-8-sig',errors='replace').splitlines())
            rows=[]; stop=threading.Event(); begin=process_sample(); start=time.perf_counter()
            worker=threading.Thread(target=monitor,args=(stop,rows,start)); worker.start()
            try:
                request=urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',
                    data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json; charset=utf-8'})
                with urllib.request.urlopen(request,timeout=600) as response: answer=json.load(response)
                elapsed=time.perf_counter()-start
            except Exception as error:
                save_json(f'{name}-erreur.json',dict(error=str(error),elapsed_seconds=time.perf_counter()-start))
                raise
            finally:
                stop.set(); worker.join()
                with (OUT/f'{name}-telemetrie.csv').open('w',newline='',encoding='utf-8') as f:
                    writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
                log='\n'.join(LOG.read_text(encoding='utf-8-sig',errors='replace').splitlines()[before:])
                (OUT/f'{name}-engine.log').write_text(log,encoding='utf-8')
            end=process_sample(); save_json(f'{name}-reponse.json',answer)
            match=re.search(r'decode expert compute: (\d+) CPU jobs, (\d+) RAM-to-GPU experts',log)
            if not match: raise RuntimeError('Compteurs CPU/GPU absents')
            cpu_jobs,gpu_copies=map(int,match.groups())
            if fraction==1 and cpu_jobs!=0: raise RuntimeError('La référence GPU contient du calcul CPU')
            if fraction<1 and cpu_jobs==0: raise RuntimeError('Mode hybride non engagé')
            if '0 blob reads from the file' not in log: raise RuntimeError('Résidence RAM sans lecture disque non confirmée')
            t=answer['timings']
            if t['cache_n']!=0 or t['predicted_n']!=PROTOCOL['max_tokens']:
                raise RuntimeError('La requête ne respecte pas le protocole sans cache et à 256 tokens')
            row=dict(repeat=repeat,pcie_frac=fraction,test=test,prompt=prompt,elapsed_seconds=elapsed,
                generation_tps=t['predicted_n']*1000/t['predicted_ms'],prompt_tps=t['prompt_per_second'],
                output_tokens=t['predicted_n'],drafts=t['draft_n'],accepted=t['draft_n_accepted'],
                cpu_expert_jobs=cpu_jobs,ram_gpu_experts=gpu_copies,
                cpu_average_cores=(end['cpu_seconds']-begin['cpu_seconds'])/elapsed,
                engine_io_read_bytes=end['io_read_bytes']-begin['io_read_bytes'],
                ram_peak_bytes=max(r['ram_bytes'] for r in rows),
                gpu_max_temp_c=max(r['temp_c'] or 0 for r in rows),gpu_max_power_w=max(r['power_w'] or 0 for r in rows),
                vram_peak_mib={i:max(r['vram_bytes'] or 0 for r in rows if r['gpu_index']==i)/1024**2 for i in handles},
                answer_sha256=hashlib.sha256(answer['choices'][0]['message']['content'].encode('utf-8')).hexdigest())
            results.append(row); save_json('resultats.json',results)
            with (OUT/'resultats.csv').open('w',newline='',encoding='utf-8') as f:
                writer=csv.DictWriter(f,fieldnames=list(row)); writer.writeheader(); writer.writerows(results)
            print(json.dumps(row,ensure_ascii=False),flush=True)
save_json('metrics.json',json.load(urllib.request.urlopen('http://127.0.0.1:8080/metrics')))
print(OUT,flush=True)
