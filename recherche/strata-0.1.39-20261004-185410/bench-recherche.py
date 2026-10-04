"""Paired local-model benchmark; preserves requests, responses, engine logs and telemetry."""
import argparse
import csv
import ctypes as c
from ctypes import wintypes as w
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import statistics
import threading
import time
import urllib.request
import psutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config', required=True, type=Path)
parser.add_argument('--out', required=True, type=Path)
parser.add_argument('--label', required=True)
parser.add_argument('--pid', required=True, type=int)
parser.add_argument('--repeats', type=int, default=2)
parser.add_argument('--warmups', type=int, default=1)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=False)
config = json.loads(args.config.read_text(encoding='utf-8-sig'))
root = Path(__file__).resolve().parent.parent.parent
historic = json.loads((root / 'protocole-comparatif-q4.json').read_text(encoding='utf-8-sig'))
cases = [dict(id='ciel', prompt=historic['prompts'][0], max_tokens=256),
         dict(id='fibonacci', prompt=historic['prompts'][1], max_tokens=256),
         dict(id='fourmis', prompt='creer une poésie sur les fourmis de 200 mots', max_tokens=512)]
protocol = dict(id='strata-0.1.39-p100-recherche-v1', cases=cases, temperature=0, seed=42,
                cache_prompt=False, enable_thinking=False,
                context=int(config['args'][config['args'].index('--max-context')+1]),
                warmups=args.warmups,
                note='Two repetitions per prompt; reverse prompt order on repetition 2. '
                     'Natural EOS is recorded; truncated and complete answers are distinguished.')
log_path = Path(config['log'])
url = f"http://127.0.0.1:{config.get('port',8080)}"

def save(name, data):
    (args.out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

save('protocole.json', protocol)
save('configuration.json', dict(config=config, engine_pid=args.pid,
    binary_sha256=hashlib.sha256(Path(config['exe']).read_bytes()).hexdigest(),
    label=args.label, created=dt.datetime.now(dt.timezone.utc).isoformat(),
    note='Process CPU time includes spin waits. No inference runs overlap.'))

k32 = c.WinDLL('kernel32', use_last_error=True)
psapi = c.WinDLL('psapi', use_last_error=True)
nv = c.WinDLL(r'C:\Windows\System32\nvml.dll')
def api(lib, name, types, result=c.c_int):
    f = getattr(lib,name); f.argtypes=types; f.restype=result; return f
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
if not handle:
    raise c.WinError(c.get_last_error())
def process_sample():
    ft=[FileTime() for _ in range(4)]
    if not times(handle,*[c.byref(x) for x in ft]):
        raise c.WinError(c.get_last_error())
    mem=Memory(); mem.cb=c.sizeof(mem)
    if not memory(handle,c.byref(mem),mem.cb):
        raise c.WinError(c.get_last_error())
    counter=Io()
    if not io(handle,c.byref(counter)):
        raise c.WinError(c.get_last_error())
    return dict(cpu_seconds=sum((x.high<<32)+x.low for x in ft[2:])/1e7,
                ram_bytes=mem.ws,io_read_bytes=counter.read_bytes)
if api(nv,'nvmlInit_v2',[])()!=0:
    raise RuntimeError('NVML initialization failed')
gethandle=api(nv,'nvmlDeviceGetHandleByUUID',[c.c_char_p,c.POINTER(c.c_void_p)])
util=api(nv,'nvmlDeviceGetUtilizationRates',[c.c_void_p,c.POINTER(Util)])
power=api(nv,'nvmlDeviceGetPowerUsage',[c.c_void_p,c.POINTER(c.c_uint)])
temp=api(nv,'nvmlDeviceGetTemperature',[c.c_void_p,c.c_uint,c.POINTER(c.c_uint)])
gpu_memory=api(nv,'nvmlDeviceGetMemoryInfo',[c.c_void_p,c.POINTER(GpuMemory)])
clock_info=api(nv,'nvmlDeviceGetClockInfo',[c.c_void_p,c.c_uint,c.POINTER(c.c_uint)])
throttle_info=api(nv,'nvmlDeviceGetCurrentClocksThrottleReasons',[c.c_void_p,c.POINTER(c.c_ulonglong)])
handles={}
for slot,uuid in enumerate(config['env']['CUDA_VISIBLE_DEVICES'].split(',')):
    h=c.c_void_p()
    if gethandle(uuid.encode(),c.byref(h))!=0:
        raise RuntimeError('GPU UUID unavailable: '+uuid)
    handles[slot]=h

def check_ngram_ram():
    if not config.get('research_ngram_lock_state'):
        return
    state=json.loads(Path(config['research_ngram_lock_state']).read_text(encoding='utf-8'))
    if state['status']!='verrouille' or state['locked_bytes']<state['bytes'] or state['verified_locked_pages']<=0:
        raise RuntimeError('PLE RAM lock is incomplete')
    process=psutil.Process(state['pid'])
    if 'verrouiller-ngram.py' not in ' '.join(process.cmdline()):
        raise RuntimeError('PLE RAM lock process is unavailable')
def monitor(stop, rows, start):
    while not stop.is_set():
        proc=process_sample()
        system=psutil.virtual_memory()
        external=0
        if config.get('research_ngram_lock_state'):
            lock_state=json.loads(Path(config['research_ngram_lock_state']).read_text(encoding='utf-8'))
            if lock_state['status']!='verrouille':
                raise RuntimeError('External PLE lock lost')
            external=psutil.Process(lock_state['pid']).memory_info().rss
        for slot,h in handles.items():
            u=Util(); p=c.c_uint(); t=c.c_uint(); gm=GpuMemory()
            sm=c.c_uint(); mc=c.c_uint(); th=c.c_ulonglong()
            eu=util(h,c.byref(u)); ep=power(h,c.byref(p)); et=temp(h,0,c.byref(t)); em=gpu_memory(h,c.byref(gm))
            ec=clock_info(h,1,c.byref(sm)); ecm=clock_info(h,2,c.byref(mc)); eth=throttle_info(h,c.byref(th))
            rows.append(dict(seconds=time.perf_counter()-start,gpu_slot=slot,
                gpu_util_pct=u.gpu if eu==0 else None, power_w=p.value/1000 if ep==0 else None,
                temp_c=t.value if et==0 else None,vram_bytes=gm.used if em==0 else None,
                sm_mhz=sm.value if ec==0 else None,memory_mhz=mc.value if ecm==0 else None,
                throttle_mask=th.value if eth==0 else None,
                ngram_helper_ram_bytes=external,
                system_ram_used_bytes=system.total-system.available, **proc))
        stop.wait(.2)

records=[]
for run in range(args.warmups + args.repeats):
    warmup=run < args.warmups
    repeat=run+1 if warmup else run-args.warmups+1
    for case in cases if repeat%2 else cases[::-1]:
        check_ngram_ram()
        name=f"{'warmup' if warmup else 'r'}{repeat}-{case['id']}"
        payload=dict(model=config['model_name'],messages=[dict(role='user',content=case['prompt'])],
                     max_tokens=case['max_tokens'],temperature=0,seed=42,cache_prompt=False,
                     chat_template_kwargs=dict(enable_thinking=False))
        save(name+'-requete.json',payload)
        offset=log_path.stat().st_size
        rows=[]; stop=threading.Event(); begin=process_sample(); start=time.perf_counter()
        worker=threading.Thread(target=monitor,args=(stop,rows,start),daemon=True); worker.start()
        try:
            request=urllib.request.Request(url+'/v1/chat/completions',
                data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type':'application/json; charset=utf-8'})
            with urllib.request.urlopen(request,timeout=3600) as response:
                answer=json.load(response)
            elapsed=time.perf_counter()-start
            save(name+'-reponse.json',answer)
        except Exception as error:
            body=error.read().decode('utf-8',errors='replace') if isinstance(error,urllib.error.HTTPError) else None
            save(name+'-erreur.json',dict(error=str(error),body=body,elapsed_seconds=time.perf_counter()-start))
            raise
        finally:
            stop.set(); worker.join()
            with log_path.open('rb') as stream:
                stream.seek(offset); log=stream.read().decode('utf-8',errors='replace')
            (args.out/(name+'-engine.log')).write_text(log,encoding='utf-8')
            if rows:
                with (args.out/(name+'-telemetrie.csv')).open('w',newline='',encoding='utf-8') as f:
                    writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        end=process_sample()
        check_ngram_ram()
        match=re.search(r'decode expert compute: (\d+) CPU jobs, (\d+) RAM-to-GPU experts',log)
        cpu_jobs,copies=map(int,match.groups()) if match else (None,None)
        if '--resident-cpu-experts' in config['args']:
            if not match or '0 blob reads from the file' not in log or copies!=0 or cpu_jobs==0:
                raise RuntimeError('Adapted CPU miss mode or RAM residency unconfirmed')
        timing=answer['timings']
        if timing['cache_n']!=0 or timing['draft_n']<=0:
            raise RuntimeError('Prompt cache reused or MTP inactive')
        content=answer['choices'][0]['message']['content']
        (args.out/(name+'-texte.txt')).write_text(content,encoding='utf-8')
        row=dict(label=args.label,repeat=repeat,test=case['id'],elapsed_seconds=elapsed,
            generation_tps=timing['predicted_n']*1000/timing['predicted_ms'],
            prompt_tps=timing['prompt_per_second'],prompt_tokens=timing['prompt_n'],
            output_tokens=timing['predicted_n'],max_tokens=case['max_tokens'],
            finish_reason=answer['choices'][0]['finish_reason'],
            drafts=timing['draft_n'],accepted=timing['draft_n_accepted'],
            mtp_acceptance=timing['draft_n_accepted']/timing['draft_n'],
            cpu_expert_jobs=cpu_jobs,ram_gpu_experts=copies,
            cpu_average_cores=(end['cpu_seconds']-begin['cpu_seconds'])/elapsed,
            engine_io_read_bytes=end['io_read_bytes']-begin['io_read_bytes'],
            ram_peak_gib=max(r['ram_bytes'] for r in rows)/2**30,
            vram_peak_gib={slot:max(r['vram_bytes'] or 0 for r in rows if r['gpu_slot']==slot)/2**30 for slot in handles},
            answer_sha256=hashlib.sha256(content.encode()).hexdigest())
        row['warmup']=warmup
        row['system_ram_peak_gib']=max(r['system_ram_used_bytes'] for r in rows)/2**30
        row['ngram_helper_peak_gib']=max(r['ngram_helper_ram_bytes'] for r in rows)/2**30
        row['gpu_observations']={slot:dict(
            temperature_max_c=max(r['temp_c'] or 0 for r in rows if r['gpu_slot']==slot),
            sm_min_busy_mhz=min((r['sm_mhz'] for r in rows if r['gpu_slot']==slot and r['sm_mhz'] and (r['gpu_util_pct'] or 0)>20),default=None),
            sm_max_mhz=max(r['sm_mhz'] or 0 for r in rows if r['gpu_slot']==slot),
            power_max_w=max(r['power_w'] or 0 for r in rows if r['gpu_slot']==slot),
            throttle_masks=sorted(set(r['throttle_mask'] for r in rows if r['gpu_slot']==slot and r['throttle_mask'] is not None))
            ) for slot in handles}
        if warmup:
            save(name+'-mesures.json',row)
            print(json.dumps(row,ensure_ascii=False),flush=True)
            continue
        records.append(row); save('resultats.json',records)
        with (args.out/'resultats.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(row)); writer.writeheader(); writer.writerows(records)
        print(json.dumps(row,ensure_ascii=False),flush=True)
summary={case['id']:dict(median_tps=statistics.median(r['generation_tps'] for r in records if r['test']==case['id']),
    output_tokens=[r['output_tokens'] for r in records if r['test']==case['id']],
    median_mtp_acceptance=statistics.median(r['mtp_acceptance'] for r in records if r['test']==case['id'])) for case in cases}
save('synthese.json',summary)
save('metrics.json',json.load(urllib.request.urlopen(url+'/metrics',timeout=10)))
print(json.dumps(summary,ensure_ascii=False),flush=True)
