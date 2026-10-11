"""Measure streaming inference, correctness and memory; never restart a server."""
import argparse, json, time, threading, hashlib, statistics, urllib.request, re
from pathlib import Path
import psutil

ap = argparse.ArgumentParser()
ap.add_argument('--port', type=int, required=True)
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--model', required=True)
ap.add_argument('--pid', type=int, required=True)
ap.add_argument('--repeat-long', type=int, default=1)
a = ap.parse_args()
a.out.mkdir(parents=True, exist_ok=False)
base = f'http://127.0.0.1:{a.port}'
proc = psutil.Process(a.pid)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
    return json.load(opener.open(base+path, timeout=10))
def save(name, obj):
    (a.out/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
cases = [
    ('ciel', 'Explique en français pourquoi le ciel est bleu, puis pourquoi il devient rouge au coucher du soleil. Donne une explication précise et accessible.', 192, None),
    ('fibonacci', 'Réponds uniquement avec un objet JSON valide contenant la clé fibonacci : les 10 premiers nombres de Fibonacci, en commençant par 0 et 1.', 128, {'fibonacci':[0,1,1,2,3,5,8,13,21,34]}),
    ('calcul', 'Réponds uniquement avec un objet JSON valide contenant ces clés : produit pour 17 multiplié par 23, somme pour 125 plus 375, capitale pour la capitale de la France.', 128, {'produit':391,'somme':500,'capitale':'Paris'}),
]
for lines in (64, 256, 1024):
    rows=[f'Ligne {i:04d}: le dossier décrit un jardin, des arbres et un chemin de pierre.' for i in range(lines)]
    rows.insert(lines//2, 'Information prioritaire : le code secret du dossier est LUMIERE-7429.')
    prompt='Lis le dossier suivant.\n'+'\n'.join(rows)+'\nRéponds uniquement avec un objet JSON contenant la clé code et le code secret indiqué au milieu du dossier.'
    cases.append((f'dossier-{lines}',prompt,80,{'code':'LUMIERE-7429'}))
save('metrics-avant.json',get('/metrics'))
records=[]
def run(name, prompt, limit, expected, warmup=False):
    payload={'model':a.model,'messages':[{'role':'user','content':prompt}], 'stream':True,
             'temperature':0,'seed':42,'max_tokens':limit,'cache_prompt':False,
             'chat_template_kwargs':{'enable_thinking':False},'reasoning_effort':'none'}
    save(name+'-request.json',payload)
    samples=[]; done=threading.Event()
    def monitor():
        while not done.is_set():
            try:
                mem=proc.memory_info(); io=proc.io_counters()
                samples.append({'time':time.time(),'rss':mem.rss,'system_used':psutil.virtual_memory().used,
                                'read_bytes':io.read_bytes,'cpu_seconds':sum(proc.cpu_times()[:2])})
            except psutil.Error:
                break
            done.wait(.25)
    worker=threading.Thread(target=monitor,daemon=True);worker.start()
    start=time.perf_counter();ttft=None;text='';events=[];timing=None;finish=None
    try:
        req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        with opener.open(req,timeout=600) as response:
            for line in response:
                if not line.startswith(b'data: '):continue
                raw=line[6:].strip()
                if raw==b'[DONE]':break
                event=json.loads(raw);events.append(event)
                if event.get('error'):raise RuntimeError(event['error'])
                for choice in event.get('choices',[]):
                    delta=choice.get('delta',{}).get('content','') or ''
                    if delta and ttft is None:ttft=time.perf_counter()-start
                    text+=delta
                    finish=choice.get('finish_reason') or finish
                timing=event.get('timings') or timing
    except Exception as exc:
        save(name+'-error.json',{'error':str(exc),'elapsed':time.perf_counter()-start})
        raise
    finally:
        done.set();worker.join()
        save(name+'-samples.json',samples)
        save(name+'-events.json',events)
        (a.out/(name+'-answer.txt')).write_text(text,encoding='utf-8')
    valid=bool(text.strip());strict_json=None
    if expected is not None:
        try:
            parsed=json.loads(text.strip());strict_json=True
        except ValueError:
            strict_json=False
            fenced=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```',text.strip(),re.S)
            try:parsed=json.loads(fenced.group(1)) if fenced else None
            except ValueError:parsed=None
        valid=isinstance(parsed,dict) and all(parsed.get(k)==v for k,v in expected.items())
    row={'name':name,'warmup':warmup,'ttft_s':ttft,'elapsed_s':time.perf_counter()-start,'timings':timing,
         'quality_pass':valid,'strict_json':strict_json,'finish':finish,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
         'rss_peak_gib':max((r['rss'] for r in samples),default=0)/2**30,
         'read_mib':(samples[-1]['read_bytes']-samples[0]['read_bytes'])/2**20 if samples else None}
    records.append(row);save('results.json',records)
    print(json.dumps(row,ensure_ascii=False),flush=True)
    if not text.strip():raise RuntimeError('Empty answer: '+name)
    if timing and timing.get('cache_n',0)!=0:raise RuntimeError('Unexpected prompt cache reuse: '+name)
run('warmup','Réponds uniquement avec un objet JSON contenant la clé resultat et le nombre 42.',64,{'resultat':42},True)
for repeat in (1,2):
    for case,prompt,limit,expected in cases[:3]:run(f'r{repeat}-{case}',prompt,limit,expected)
for case,prompt,limit,expected in cases[3:]:run(case,prompt,limit,expected)
for repeat in range(2,a.repeat_long+1):
    case,prompt,limit,expected=cases[-1]
    # The persistent engine can reuse its live prefix even with cache_prompt=False.
    # Put a distinct marker before the repeated dossier; every profile receives the same variant.
    run(f'{case}-repeat{repeat}',f'Mesure distincte {repeat}.\n'+prompt,limit,expected)
save('metrics-apres.json',get('/metrics'))
print('BENCHMARK_OK',flush=True)
