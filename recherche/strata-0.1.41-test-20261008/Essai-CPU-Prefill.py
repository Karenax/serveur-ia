"""Fresh production baseline, official CPU prefill trial, automatic production recovery."""
import hashlib,json,re,subprocess,time,urllib.request,statistics
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parent
PY=ROOT/'.venv/Scripts/python.exe'
RUN=ROOT/'mesures/cpu-prefill-20261009'
RUN.mkdir(exist_ok=False)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
status={}
def save(**kw):
    status.update(kw)
    (RUN/'etat.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(kw,ensure_ascii=False),flush=True)
def get(port,path):
    return json.load(opener.open(f'http://127.0.0.1:{port}{path}',timeout=10))
def command(args,name,timeout):
    with (RUN/(name+'.log')).open('w',encoding='utf-8') as f:
        result=subprocess.run(args,stdout=f,stderr=f,timeout=timeout)
    if result.returncode:raise RuntimeError(f'{name}: code {result.returncode}, consulter le journal')
def engine(path):
    found=[]
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name']=='strata.exe' and Path(p.exe()).resolve()==Path(path).resolve():found.append(p)
        except psutil.Error:pass
    assert len(found)==1,found
    return found[0]
def wait(port,limit=1200):
    end=time.monotonic()+limit
    while time.monotonic()<end:
        try:
            h=get(port,'/health')
            if h.get('loaded') is True:return h
        except Exception:pass
        if port==8081:
            rec=json.loads((ROOT/'test-process.json').read_text(encoding='utf-8-sig'))
            if not psutil.pid_exists(rec['pid']):raise RuntimeError('Serveur test termine pendant chargement')
        time.sleep(3)
    raise TimeoutError(f'Chargement port {port}')
def bench(port,pid,model,folder):
    command([str(PY),str(ROOT/'Bench.py'),'--port',str(port),'--pid',str(pid),'--model',model,'--out',str(folder)],folder.name,1800)
def evaluate():
    b={r['name']:r for r in json.loads((RUN/'production/results.json').read_text()) if not r['warmup']}
    rows=json.loads((RUN/'officiel-cpu/results.json').read_text())
    comparisons=[]
    for r in rows:
        if r['warmup']:continue
        ref=b[r['name']]
        comparisons.append({'name':r['name'],'quality_pass':r['quality_pass'],
          'prompt_tokens':r['timings']['prompt_n'],
          'production_ttft_s':ref['ttft_s'],'cpu_ttft_s':r['ttft_s'],
          'production_prefill_tps':ref['timings']['prompt_per_second'],
          'cpu_prefill_tps':r['timings']['prompt_per_second'],
          'prefill_ratio':r['timings']['prompt_per_second']/ref['timings']['prompt_per_second'],
          'decode_ratio':r['timings']['predicted_per_second']/ref['timings']['predicted_per_second']})
    quality=all(r['quality_pass'] for r in rows)
    decode=statistics.median(r['decode_ratio'] for r in comparisons)
    prefill=min(r['prefill_ratio'] for r in comparisons if r['name'].startswith('dossier-'))
    result={'quality_pass':quality,'median_decode_ratio':decode,'min_document_prefill_ratio':prefill,
      'acceptable':quality and decode>=.97 and prefill>=.95,'rows':comparisons}
    (RUN/'comparaison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {k:v for k,v in result.items() if k!='rows'}

stopped=False
try:
    info=json.loads((ROOT/'production-sauvegarde/reprise.json').read_text(encoding='utf-8-sig'))
    cfg=json.loads(Path(info['config_path']).read_text(encoding='utf-8-sig'))
    assert cfg==json.loads((ROOT/'production-sauvegarde/configuration-active.json').read_text(encoding='utf-8-sig'))
    for stamp in info['files']:
        assert hashlib.sha256(Path(stamp['path']).read_bytes()).hexdigest()==stamp['sha256'],stamp['path']
    assert get(8080,'/health')['loaded'] is True
    production=engine(cfg['exe'])
    save(phase='reference-production',production_pid=production.pid)
    bench(8080,production.pid,cfg['model_name'],RUN/'production')
    baseline=json.loads((RUN/'production/results.json').read_text())
    assert len(baseline)==10 and all(r['quality_pass'] for r in baseline)
    command(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Test.ps1'),'-Profil','cpu-prefill','-VerifierSeulement'],'preparation',90)
    html=opener.open('http://127.0.0.1:8765/',timeout=10).read().decode()
    token=re.search(r'name="launcher-token" content="([^"]+)"',html).group(1)
    req=urllib.request.Request('http://127.0.0.1:8765/api/stop',data=b'{}',headers={'Content-Type':'application/json','X-Launcher-Token':token,'Origin':'http://127.0.0.1:8765'})
    save(phase='arret-production')
    stopped=True  # Recovery also runs if the stop HTTP response is interrupted.
    json.load(opener.open(req,timeout=90))
    time.sleep(5)
    save(phase='chargement-officiel-cpu')
    command(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Test.ps1'),'-Profil','cpu-prefill'],'lancement-test',90)
    wait(8081)
    tested=engine(ROOT/'engine-cuda12/strata.exe')
    save(phase='mesures-officiel-cpu',test_pid=tested.pid)
    bench(8081,tested.pid,'qwen3.8-flash-next-iq4-xs-test-0141',RUN/'officiel-cpu')
    save(phase='mesures-terminees',result=evaluate())
except Exception as exc:
    save(error=str(exc))
finally:
    if stopped:
        save(phase='reprise-production')
        try:command([str(PY),str(ROOT/'Stop-Test.py')],'arret-test',45)
        except Exception as exc:save(stop_error=str(exc))
        time.sleep(5)
        try:
            engine(cfg['exe'])
            save(recovery='Moteur de production deja actif')
        except AssertionError:
            command([str(PY),str(ROOT/'Reprendre-Production.py')],'reprise',60)
        wait(8080)
        command([str(PY),str(ROOT/'Reprendre-Console.py')],'reprise-console',90)
        command([str(PY),str(ROOT/'Verifier-Reprise.py')],'verification-reprise',1300)
        (RUN/'production-retablie.json').write_bytes((ROOT/'validation/production-retablie.json').read_bytes())
        save(phase='production-retablie',production_version=get(8080,'/metrics')['engine']['version'])
