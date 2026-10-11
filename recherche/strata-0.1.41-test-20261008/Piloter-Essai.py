"""Run candidates sequentially and restore production in a finally block."""
import json,re,subprocess,time,urllib.request,statistics,sys,os
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parent
PY=ROOT/'.venv/Scripts/python.exe'
SOURCE=ROOT/'source-officielle'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
status={}
def save(**kwargs):
    status.update(kwargs)
    (ROOT/'validation/essai-en-cours.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(kwargs,ensure_ascii=False),flush=True)
def get(url):return json.load(opener.open(url,timeout=8))
def control_stop():
    base='http://127.0.0.1:8765'
    html=opener.open(base+'/',timeout=10).read().decode()
    token=re.search(r'name="launcher-token" content="([^"]+)"',html).group(1)
    req=urllib.request.Request(base+'/api/stop',data=b'{}',headers={'Content-Type':'application/json','X-Launcher-Token':token,'Origin':base})
    return json.load(opener.open(req,timeout=90))
def stop_test():
    result=subprocess.run([str(PY),str(ROOT/'Stop-Test.py')],capture_output=True,text=True,timeout=45)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
def wait_ready(port,timeout=900):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        try:
            health=get(f'http://127.0.0.1:{port}/health')
            if health.get('loaded') is True:return health
        except Exception:pass
        if port==8081:
            state=json.loads((ROOT/'test-process.json').read_text(encoding='utf-8-sig'))
            if not psutil.pid_exists(state['pid']):raise RuntimeError('Le serveur de test a quitte pendant le chargement.')
        time.sleep(3)
    raise TimeoutError(f'Chargement port {port} trop long')
def evaluate(folder):
    baseline=json.loads((ROOT/'mesures/production-complet/results.json').read_text())
    results=json.loads((folder/'results.json').read_text())
    b={r['name']:r for r in baseline if not r['warmup']}
    ratios=[];prefill=[]
    for r in results:
        if r['name'] not in b:continue
        ref=b[r['name']]
        ratios.append(r['timings']['predicted_per_second']/ref['timings']['predicted_per_second'])
        if r['name'].startswith('dossier-'):prefill.append(r['timings']['prompt_per_second']/ref['timings']['prompt_per_second'])
    quality=all(r['quality_pass'] for r in results)
    return {'quality_pass':quality,'median_decode_ratio':statistics.median(ratios),
            'median_long_prefill_ratio':statistics.median(prefill),
            'min_long_prefill_ratio':min(prefill),
            'acceptable':quality and statistics.median(ratios)>=.97 and min(prefill)>=.95}
resume='--reprendre-test' in sys.argv
stopped=resume
try:
    baseline=json.loads((ROOT/'mesures/production-complet/results.json').read_text())
    assert len(baseline)==10,'La reference doit etre complete avant interruption'
    if not resume:
        save(phase='arret-production',baseline_quality=all(r['quality_pass'] for r in baseline))
        control_stop();stopped=True
        time.sleep(5)
    outcomes=[]
    profiles=('fp16',) if '--fp16' in sys.argv else ('reference','trim','pipeline')
    for profile in profiles:
        save(phase='chargement-test',profile=profile)
        if not (resume and profile=='reference'):
            with (ROOT/f'logs/launch-{profile}.log').open('w',encoding='utf-8') as stream:
                launch=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Test.ps1'),'-Profil',profile],stdout=stream,stderr=stream,timeout=90)
            if launch.returncode:raise RuntimeError('Lancement refuse : consulter launch-'+profile+'.log')
        try:
            wait_ready(8081)
            engine=next(p for p in psutil.process_iter(['name']) if p.info['name']=='strata.exe' and Path(p.exe()).resolve()==ROOT/'engine-cuda12/strata.exe')
            folder=ROOT/'mesures'/('officiel-'+profile)
            save(phase='mesures',profile=profile,engine_pid=engine.pid)
            cmd=[str(PY),str(ROOT/'Bench.py'),'--port','8081','--pid',str(engine.pid),'--model','qwen3.8-flash-next-iq4-xs-test-0141','--out',str(folder)]
            with (ROOT/f'logs/bench-{profile}.stdout.log').open('w',encoding='utf-8') as out,(ROOT/f'logs/bench-{profile}.stderr.log').open('w',encoding='utf-8') as err:
                bench=subprocess.run(cmd,stdout=out,stderr=err,timeout=1800)
            if bench.returncode:raise RuntimeError('Benchmark incomplet : consulter les journaux '+profile)
            result={'profile':profile,**evaluate(folder)};outcomes.append(result)
            save(outcomes=outcomes)
            if result['acceptable']:break
        except Exception as exc:
            outcomes.append({'profile':profile,'acceptable':False,'error':str(exc)})
            save(outcomes=outcomes)
        finally:
            stop_test();time.sleep(5)
    save(phase='essais-termines')
except Exception as exc:
    save(error=str(exc))
finally:
    if stopped:
        save(phase='reprise-production')
        stop_test()
        with (ROOT/'logs/commande-reprise.log').open('w',encoding='utf-8') as stream:
            result=subprocess.run([str(PY),str(ROOT/'Reprendre-Production.py')],stdout=stream,stderr=stream,timeout=60)
        if result.returncode:save(recovery_error='Consulter commande-reprise.log');raise RuntimeError('Reprise impossible')
        wait_ready(8080,900)
        save(phase='production-retablie',production_version=get('http://127.0.0.1:8080/metrics')['engine']['version'])
