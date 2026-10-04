"""Même protocole, télémétrie NVML directe ; archives précédentes conservées."""
import ctypes as c
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / dt.datetime.now().strftime('inference-%Y%m%d-%H%M%S')
OUT.mkdir()
PROTOCOL = json.loads((ROOT/'protocole-comparatif-q4.json').read_text(encoding='utf-8-sig'))
LOG = ROOT/'strata-engine-p100.log'
nv = c.WinDLL(r'C:\Windows\System32\nvml.dll')
class Util(c.Structure):
    _fields_=[('gpu',c.c_uint),('memory',c.c_uint)]
def api(name, types):
    f=getattr(nv,name); f.argtypes=types; f.restype=c.c_int; return f
init=api('nvmlInit_v2',[])
gethandle=api('nvmlDeviceGetHandleByIndex_v2',[c.c_uint,c.POINTER(c.c_void_p)])
pcie=api('nvmlDeviceGetPcieThroughput',[c.c_void_p,c.c_uint,c.POINTER(c.c_uint)])
util=api('nvmlDeviceGetUtilizationRates',[c.c_void_p,c.POINTER(Util)])
clock=api('nvmlDeviceGetClockInfo',[c.c_void_p,c.c_uint,c.POINTER(c.c_uint)])
power=api('nvmlDeviceGetPowerUsage',[c.c_void_p,c.POINTER(c.c_uint)])
temp=api('nvmlDeviceGetTemperature',[c.c_void_p,c.c_uint,c.POINTER(c.c_uint)])
throttle=api('nvmlDeviceGetCurrentClocksThrottleReasons',[c.c_void_p,c.POINTER(c.c_ulonglong)])
assert init()==0
handles={}
for i in (1,2):
    h=c.c_void_p(); assert gethandle(i,c.byref(h))==0; handles[i]=h
def query(f,h,*args,typ=c.c_uint):
    result=typ(); error=f(h,*args,c.byref(result))
    return result.value if error==0 else None
def monitor(stop,rows,start):
    while not stop.is_set():
        for i,h in handles.items():
            u=Util(); e=util(h,c.byref(u))
            rows.append(dict(seconds=time.perf_counter()-start,gpu_index=i,
                rx_kib_s=query(pcie,h,1),tx_kib_s=query(pcie,h,0),
                gpu_util_pct=u.gpu if e==0 else None,memory_util_pct=u.memory if e==0 else None,
                sm_mhz=query(clock,h,1),power_mw=query(power,h),temp_c=query(temp,h,0),
                throttle=query(throttle,h,typ=c.c_ulonglong)))
        stop.wait(.02)
def integrate(samples,key):
    return sum((b['seconds']-a['seconds'])*((a[key] or 0)+(b[key] or 0))/2 for a,b in zip(samples,samples[1:]))
results=[]
(OUT/'protocole.json').write_text(json.dumps(PROTOCOL,ensure_ascii=False,indent=2),encoding='utf-8')
snapshot=json.loads((ROOT/'strata-q4-p100.json').read_text(encoding='utf-8-sig'))
snapshot['binary_sha256']=hashlib.sha256((ROOT/'strata-build-p100/strata.exe').read_bytes()).hexdigest()
(OUT/'configuration.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
for test,prompt in enumerate(PROTOCOL['prompts'],1):
    payload=dict(model='qwen3.8-flash-next',messages=[dict(role='user',content=prompt)],
        max_tokens=256,temperature=0,seed=42,cache_prompt=False,chat_template_kwargs=dict(enable_thinking=False))
    body=json.dumps(payload,ensure_ascii=False).encode('utf-8')
    (OUT/f'requete-{test}.json').write_bytes(body)
    before=len(LOG.read_text(encoding='utf-8-sig',errors='replace').splitlines())
    rows=[]; stop=threading.Event(); start=time.perf_counter()
    worker=threading.Thread(target=monitor,args=(stop,rows,start)); worker.start()
    try:
        req=urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',data=body,headers={'Content-Type':'application/json; charset=utf-8'})
        with urllib.request.urlopen(req,timeout=600) as response: answer=json.load(response)
        elapsed=time.perf_counter()-start
    finally:
        stop.set(); worker.join()
        with (OUT/f'nvml-{test}.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        log='\n'.join(LOG.read_text(encoding='utf-8-sig',errors='replace').splitlines()[before:])
        (OUT/f'engine-{test}.log').write_text(log,encoding='utf-8')
    (OUT/f'reponse-{test}.json').write_text(json.dumps(answer,ensure_ascii=False,indent=2),encoding='utf-8')
    assert 'decode expert compute: 0 CPU jobs,' in log
    metrics={}
    for i in handles:
        samples=[r for r in rows if r['gpu_index']==i]
        metrics[i]=dict(rx_integrated_GB=integrate(samples,'rx_kib_s')*1024/1e9,
            rx_mean_GB_s=integrate(samples,'rx_kib_s')*1024/1e9/elapsed,
            rx_peak_GB_s=max((r['rx_kib_s'] or 0) for r in samples)*1024/1e9,
            mean_gpu_util=sum(r['gpu_util_pct'] or 0 for r in samples)/len(samples),
            mean_memory_util=sum(r['memory_util_pct'] or 0 for r in samples)/len(samples),
            sm_min=min(r['sm_mhz'] or 0 for r in samples),sm_max=max(r['sm_mhz'] or 0 for r in samples),
            max_power_w=max(r['power_mw'] or 0 for r in samples)/1000,
            max_temp_c=max(r['temp_c'] or 0 for r in samples),throttle_values=sorted(set(r['throttle'] for r in samples if r['throttle'] is not None)))
    result=dict(test=test,elapsed_seconds=elapsed,timings=answer['timings'],nvml=metrics)
    results.append(result)
    (OUT/'resultats.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
print(OUT,flush=True)
