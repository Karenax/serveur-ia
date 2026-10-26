"""Read-only counters around one short local inference; no settings or model restart."""
import ctypes as c
import datetime
import json
from pathlib import Path
import threading
import time
import urllib.request
import psutil

OUT=Path(__file__).resolve().parent
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get_metrics():
    with opener.open('http://127.0.0.1:8080/metrics',timeout=5) as response:return json.load(response)

class Value(c.Structure):
    _fields_=[('status',c.c_uint32),('value',c.c_double)]

def main():
    metrics=get_metrics()
    if metrics.get('live',{}).get('state')!='idle' or metrics.get('live',{}).get('queued'):
        raise RuntimeError('An inference is already active; no diagnostic request sent.')
    engine=next(p for p in psutil.process_iter(['name']) if p.info['name'].lower()=='strata.exe')
    api=c.WinDLL('pdh.dll');handle=c.c_void_p()
    api.PdhOpenQueryW.argtypes=[c.c_wchar_p,c.c_size_t,c.POINTER(c.c_void_p)]
    api.PdhAddEnglishCounterW.argtypes=[c.c_void_p,c.c_wchar_p,c.c_size_t,c.POINTER(c.c_void_p)]
    api.PdhCollectQueryData.argtypes=[c.c_void_p]
    api.PdhGetFormattedCounterValue.argtypes=[c.c_void_p,c.c_uint32,c.c_void_p,c.POINTER(Value)]
    api.PdhCloseQuery.argtypes=[c.c_void_p]
    assert api.PdhOpenQueryW(None,0,c.byref(handle))==0
    names={'c_read':r'\LogicalDisk(C:)\Disk Read Bytes/sec','d_read':r'\LogicalDisk(D:)\Disk Read Bytes/sec',
           'd_write':r'\LogicalDisk(D:)\Disk Write Bytes/sec','d_idle':r'\LogicalDisk(D:)\% Idle Time',
           'd_queue':r'\LogicalDisk(D:)\Current Disk Queue Length',
           'pages_in':r'\Memory\Pages Input/sec','page_reads':r'\Memory\Page Reads/sec',
           'available_mib':r'\Memory\Available MBytes','strata_faults':r'\Process(strata)\Page Faults/sec',
           'strata_read':r'\Process(strata)\IO Read Bytes/sec'}
    counters={};samples=[];stop=threading.Event();phase=['baseline']
    try:
        for name,path in names.items():
            counter=c.c_void_p();status=api.PdhAddEnglishCounterW(handle,path,0,c.byref(counter))
            if status:raise OSError(f'Counter {name} unavailable: {status:#x}')
            counters[name]=counter
        api.PdhCollectQueryData(handle)
        started=time.monotonic()
        def sample():
            while not stop.wait(.5):
                api.PdhCollectQueryData(handle);row={'t':round(time.monotonic()-started,3),'phase':phase[0]}
                for name,counter in counters.items():
                    value=Value();status=api.PdhGetFormattedCounterValue(counter,0x200,None,c.byref(value))
                    row[name]=round(value.value,3) if status==0 and value.status in (0,1) else None
                samples.append(row)
        thread=threading.Thread(target=sample,daemon=True);thread.start();time.sleep(2)
        before=engine.memory_info()._asdict();io_before=engine.io_counters()._asdict()
        # Recheck admission immediately before sending a bounded synthetic prompt.
        live=get_metrics()['live']
        if live.get('state')!='idle' or live.get('queued'):raise RuntimeError('Inference started meanwhile; diagnostic skipped.')
        phase[0]='inference';call_start=time.monotonic()
        body={'model':'qwen3.8-flash-next-iq4-xs','messages':[{'role':'user','content':'Diagnostic local du disque. Réponds seulement : bonjour.'}],
              'max_tokens':8,'temperature':0,'stream':False,'chat_template_kwargs':{'enable_thinking':False}}
        request=urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
        try:
            with opener.open(request,timeout=25) as response:answer=json.load(response)
            outcome={'finished':True,'usage':answer.get('usage',{})}
        except (OSError,ValueError) as error:
            outcome={'finished':False,'error':str(error)}
        outcome['seconds']=round(time.monotonic()-call_start,3);phase[0]='after';time.sleep(2)
        after=engine.memory_info()._asdict();io_after=engine.io_counters()._asdict()
        stop.set();thread.join(2)
        summary={}
        for label in ('baseline','inference','after'):
            rows=[row for row in samples if row['phase']==label]
            summary[label]={'samples':len(rows)}
            for name in names:
                values=[row[name] for row in rows if row[name] is not None]
                if values:summary[label][name]={'mean':round(sum(values)/len(values),3),'max':max(values)}
        report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':engine.pid,'inference':outcome,'summary':summary,'samples':samples,
                'memory_before':before,'memory_after':after,'io_before':io_before,'io_after':io_after,
                'live_after':get_metrics().get('live')}
        (OUT/'measurement.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'inference':outcome,'summary':summary,'live_after':report['live_after']}),flush=True)
    finally:
        stop.set();api.PdhCloseQuery(handle)

if __name__=='__main__':main()
