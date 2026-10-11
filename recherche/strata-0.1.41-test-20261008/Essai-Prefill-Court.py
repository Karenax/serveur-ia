"""Measure short CPU sharing and pinned RAM; always restore the saved production session."""
import argparse,hashlib,json,re,subprocess,time,urllib.request,statistics
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parent
PY=ROOT/'.venv/Scripts/python.exe'
parser=argparse.ArgumentParser()
parser.add_argument('--run',default='prefill-court-pin-20261009')
args=parser.parse_args()
assert Path(args.run).name==args.run and args.run not in ('.','..')
RUN=ROOT/'mesures'/args.run
RUN.mkdir(exist_ok=False)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
status={'outcomes':[]}
def save(**kw):
    status.update(kw)
    (RUN/'etat.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(kw,ensure_ascii=False),flush=True)
def get(port,path):return json.load(opener.open(f'http://127.0.0.1:{port}{path}',timeout=10))
def command(args,name,timeout):
    with (RUN/(name+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run(args,stdout=log,stderr=log,timeout=timeout)
    if result.returncode:raise RuntimeError(f'{name}: code {result.returncode}, voir le journal')
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
            health=get(port,'/health')
            if health.get('loaded') is True:return health
        except Exception:pass
        if port==8081:
            rec=json.loads((ROOT/'test-process.json').read_text(encoding='utf-8-sig'))
            if not psutil.pid_exists(rec['pid']):raise RuntimeError('Le serveur de test a quitte pendant le chargement')
        time.sleep(3)
    raise TimeoutError(f'Chargement port {port} trop long')
def bench(port,pid,model,name):
    deadline=time.monotonic()+180
    while True:
        probe=subprocess.run(['nvidia-smi','--query-gpu=name,temperature.gpu,clocks.sm,clocks_throttle_reasons.active',
                              '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        assert probe.returncode==0,probe.stderr
        temperatures=[float(row.split(',')[1]) for row in probe.stdout.splitlines() if 'P100' in row]
        assert len(temperatures)==2,probe.stdout
        if max(temperatures)<=55 or time.monotonic()>=deadline:break
        time.sleep(3)
    (RUN/(name+'-gpu-avant.json')).write_text(json.dumps({'rows':probe.stdout.splitlines(),
        'cooling_target_reached':max(temperatures)<=55},indent=2),encoding='utf-8')
    command([str(PY),str(ROOT/'Bench.py'),'--port',str(port),'--pid',str(pid),'--model',model,
             '--repeat-long','2','--out',str(RUN/name)],'bench-'+name,1800)
def stop_test():command([str(PY),str(ROOT/'Stop-Test.py')],'arret-test',45)
def evaluate(profile):
    b={r['name']:r for r in json.loads((RUN/'production/results.json').read_text()) if not r['warmup']}
    rows=json.loads((RUN/profile/'results.json').read_text())
    cmp=[]
    for r in rows:
        if r['warmup']:continue
        ref=b[r['name']]
        cmp.append({'name':r['name'],'quality_pass':r['quality_pass'],'strict_json':r['strict_json'],
          'prompt_tokens':r['timings']['prompt_n'],'production_ttft_s':ref['ttft_s'],'trial_ttft_s':r['ttft_s'],
          'production_prefill_tps':ref['timings']['prompt_per_second'],'trial_prefill_tps':r['timings']['prompt_per_second'],
          'prefill_ratio':r['timings']['prompt_per_second']/ref['timings']['prompt_per_second'],
          'decode_ratio':r['timings']['predicted_per_second']/ref['timings']['predicted_per_second']})
    quality=all(r['quality_pass'] for r in rows)
    decode=statistics.median(r['decode_ratio'] for r in cmp)
    minimum=min(r['prefill_ratio'] for r in cmp if r['name'].startswith('dossier-'))
    long=[r for r in cmp if r['name'].startswith('dossier-1024')]
    historical=json.loads((ROOT/'mesures/cpu-prefill-20261009/production/results.json').read_text())
    historical_long=next(r['ttft_s'] for r in historical if r['name']=='dossier-1024')
    long_median=statistics.median(r['trial_ttft_s'] for r in long)
    result={'profile':profile,'quality_pass':quality,'median_decode_ratio':decode,
            'min_document_prefill_ratio':minimum,'long_ttft_median_s':long_median,
            'historical_long_ttft_s':historical_long,
            'long_prefill_ratio':statistics.median(r['prefill_ratio'] for r in long),
            'acceptable':quality and decode>=.97 and minimum>=.95 and long_median<=historical_long*1.05,'rows':cmp}
    (RUN/(profile+'-comparaison.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return {k:v for k,v in result.items() if k!='rows'}
stopped=False
observer=None
try:
    info=json.loads((ROOT/'production-sauvegarde/reprise.json').read_text(encoding='utf-8-sig'))
    cfg=json.loads(Path(info['config_path']).read_text(encoding='utf-8-sig'))
    assert cfg==json.loads((ROOT/'production-sauvegarde/configuration-active.json').read_text(encoding='utf-8-sig'))
    for stamp in info['files']:
        assert hashlib.sha256(Path(stamp['path']).read_bytes()).hexdigest()==stamp['sha256'],stamp['path']
    assert get(8080,'/health')['loaded'] is True
    save(phase='reference-production')
    observer=subprocess.Popen([str(PY),str(ROOT/'Observer-GPU-Prefill.py'),'--run',args.run],
                              creationflags=subprocess.CREATE_NO_WINDOW)
    bench(8080,engine(cfg['exe']).pid,cfg['model_name'],'production')
    baseline=json.loads((RUN/'production/results.json').read_text())
    assert len(baseline)==11 and all(r['quality_pass'] for r in baseline)
    command(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Test.ps1'),
             '-Profil','cpu-court','-VerifierSeulement'],'preparation',90)
    (RUN/'reprise-precedente.json').write_bytes((ROOT/'validation/production-retablie.json').read_bytes())
    html=opener.open('http://127.0.0.1:8765/',timeout=10).read().decode()
    token=re.search(r'name="launcher-token" content="([^"]+)"',html).group(1)
    req=urllib.request.Request('http://127.0.0.1:8765/api/stop',data=b'{}',headers={
        'Content-Type':'application/json','X-Launcher-Token':token,'Origin':'http://127.0.0.1:8765'})
    save(phase='arret-production');stopped=True
    json.load(opener.open(req,timeout=90));time.sleep(5)
    profiles=['cpu-court','cpu-court-pin']
    # A third profile may be requested by placing a small JSON list in suite.json before the second test ends.
    # It can only select the prevalidated 4096 profile, never a production configuration.
    index=0
    while index<len(profiles):
        profile=profiles[index];index+=1
        save(phase='chargement-test',profile=profile)
        try:
            command(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Test.ps1'),
                     '-Profil',profile],'lancement-'+profile,90)
            wait(8081)
            tested=engine(ROOT/'engine-cuda12/strata.exe')
            evidence={'pid':tested.pid,'exe':tested.exe(),'env':{k:v for k,v in tested.environ().items() if k.startswith('STRATA_')}}
            (RUN/(profile+'-processus.json')).write_text(json.dumps(evidence,indent=2),encoding='utf-8')
            save(phase='mesures',profile=profile,pid=tested.pid)
            bench(8081,tested.pid,'qwen3.8-flash-next-iq4-xs-test-0141',profile)
            # Preserve the engine log before a later run reuses this profile's log path.
            (RUN/(profile+'-engine.log')).write_bytes((ROOT/f'logs/engine-{profile}.log').read_bytes())
            result=evaluate(profile)
            status['outcomes'].append(result)
            save(phase='profil-termine',outcomes=status['outcomes'])
        except Exception as exc:
            status['outcomes'].append({'profile':profile,'error':str(exc),'acceptable':False})
            save(outcomes=status['outcomes'])
        finally:
            stop_test();time.sleep(5)
        if index==len(profiles) and (RUN/'suite.json').exists():
            requested=json.loads((RUN/'suite.json').read_text())
            for p in requested:
                assert p=='cpu-court-pin-4096',p
                if p not in profiles:profiles.append(p)
    save(phase='essais-termines')
except Exception as exc:save(error=str(exc))
finally:
    if stopped:
        save(phase='reprise-production')
        try:stop_test()
        except Exception as exc:save(stop_error=str(exc))
        time.sleep(5)
        try:engine(cfg['exe'])
        except AssertionError:command([str(PY),str(ROOT/'Reprendre-Production.py')],'reprise',60)
        wait(8080)
        command([str(PY),str(ROOT/'Reprendre-Console.py')],'reprise-console',90)
        command([str(PY),str(ROOT/'Verifier-Reprise.py')],'verification-reprise',1300)
        (RUN/'production-retablie.json').write_bytes((ROOT/'validation/production-retablie.json').read_bytes())
        save(phase='production-retablie',production_version=get(8080,'/metrics')['engine']['version'])
    if observer is not None:
        (RUN/'observer-stop').touch()
        observer.wait(timeout=20)
