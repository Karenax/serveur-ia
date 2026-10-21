"""Local comparison, thermal evidence, and restoration of the current saved session."""
import datetime, hashlib, json, os, re, socket, subprocess, sys, threading, time, urllib.request
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent.parent
PY=ROOT.parent/'strata-0.1.41-test-20261008/.venv/Scripts/python.exe'
RUN=ROOT/'mesures'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
RUN.mkdir(parents=True,exist_ok=False)
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))
STATE={'phase':'preparation','profile':None,'outcomes':[]}
COOLED='--refroidi' in sys.argv
ONLY_MTP='--mtp-seulement' in sys.argv
COOL_LIMIT=600 if ONLY_MTP else 300
STATE['cooling_between_requests']=COOLED
STATE['mtp_only']=ONLY_MTP
DONE=threading.Event()
HOT=threading.Event()
TEST=None
STOPPED=False

def write(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def state(**kw):
    STATE.update(kw);write(RUN/'etat.json',STATE)
    print(json.dumps(kw,ensure_ascii=False),flush=True)
def get(port,path):
    return json.load(OPENER.open(f'http://127.0.0.1:{port}{path}',timeout=15))
def post(port,path,data,timeout=600):
    req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    return json.load(OPENER.open(req,timeout=timeout))
def gpu():
    query='uuid,name,temperature.gpu,clocks.sm,clocks.mem,power.draw,clocks_throttle_reasons.active,utilization.gpu,memory.used'
    result=subprocess.run(['nvidia-smi','--query-gpu='+query,'--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    result.check_returncode()
    rows=[]
    for line in result.stdout.splitlines():
        c=[v.strip() for v in line.split(',')]
        if 'P100' not in c[1]:continue
        rows.append(dict(uuid=c[0],temperature_c=float(c[2]),sm_mhz=float(c[3]),mem_mhz=float(c[4]),
                         power_w=float(c[5]),throttle_mask=int(c[6],16),utilization=float(c[7]),vram_mib=float(c[8])))
    assert len(rows)==2,rows
    return rows
def observer():
    with (RUN/'gpu-samples.jsonl').open('w',encoding='utf-8') as stream:
        while not DONE.is_set():
            try:
                rows=gpu()
                stream.write(json.dumps(dict(time=time.time(),phase=STATE['phase'],profile=STATE['profile'],rows=rows))+'\n');stream.flush()
                if max(r['temperature_c'] for r in rows)>=80 or any(r['throttle_mask']&0x60 for r in rows):HOT.set()
            except Exception as exc:
                stream.write(json.dumps({'time':time.time(),'error':str(exc)})+'\n');stream.flush()
            DONE.wait(2)
def cooling():
    deadline=time.monotonic()+COOL_LIMIT
    while True:
        rows=gpu()
        if max(r['temperature_c'] for r in rows)<=55:
            HOT.clear();return rows
        if time.monotonic()>deadline:raise RuntimeError(f'Refroidissement sous 55 C non atteint en {COOL_LIMIT//60} minutes.')
        time.sleep(3)
def health(port,limit=1800):
    end=time.monotonic()+limit
    while time.monotonic()<end:
        if TEST and TEST.poll() is not None:raise RuntimeError('Le serveur de test a quitté pendant le chargement.')
        try:
            value=get(port,'/health')
            if value.get('loaded') is True or value.get('status')=='ok':return value
        except (OSError,ValueError):pass
        time.sleep(3)
    raise TimeoutError(f'Chargement port {port} trop long.')
def stop_test():
    global TEST
    if TEST:
        try:
            proc=psutil.Process(TEST.pid)
            if abs(proc.create_time()-TEST.created_at)>2:raise RuntimeError('Identité PID de test différente.')
            children=proc.children(recursive=True)
            for child in reversed(children):
                try:child.terminate()
                except psutil.NoSuchProcess:pass
            try:proc.terminate()
            except psutil.NoSuchProcess:pass
            _,alive=psutil.wait_procs(children+[proc],timeout=15)
            for p in alive:p.kill()
        except psutil.NoSuchProcess:pass
        TEST=None
def spawn(command,cwd,name,env=None):
    global TEST
    assert TEST is None
    out=(RUN/(name+'-server.stdout.log')).open('wb');err=(RUN/(name+'-server.stderr.log')).open('wb')
    TEST=subprocess.Popen(command,cwd=cwd,env=env,stdout=out,stderr=err,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    TEST.created_at=psutil.Process(TEST.pid).create_time()
    out.close();err.close()
    write(RUN/(name+'-process.json'),dict(pid=TEST.pid,created_at=TEST.created_at,command=command))
def control_stop():
    base='http://127.0.0.1:8765'
    html=OPENER.open(base+'/',timeout=15).read().decode()
    token=re.search(r'name="launcher-token" content="([^"]+)"',html).group(1)
    req=urllib.request.Request(base+'/api/stop',data=b'{}',headers={'Content-Type':'application/json','X-Launcher-Token':token,'Origin':base})
    return json.load(OPENER.open(req,timeout=120))
def hashfile(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def benchmark(name,port,model,long=True,stress=False):
    folder=RUN/name;folder.mkdir()
    state(phase='mesures',profile=name)
    write(folder/'gpu-avant.json',cooling())
    cases=[('ciel','Explique en français pourquoi le ciel est bleu, puis pourquoi il devient rouge au coucher du soleil. Donne une explication précise et accessible.',256,None),
           ('fibonacci-code','Écris une fonction Python fibonacci(n) qui retourne les n premiers nombres de Fibonacci, puis donne un exemple pour n=8. Réponds en français.',256,None),
           ('calcul','Réponds uniquement avec un objet JSON valide contenant ces clés : produit pour 17 multiplié par 23, somme pour 125 plus 375, capitale pour la capitale de la France.',128,{'produit':391,'somme':500,'capitale':'Paris'})]
    records=[]
    def one(case,prompt,limit,expected,warmup=False):
        if COOLED and not case.startswith('soutenu-'):
            write(folder/(case+'-gpu-refroidi.json'),cooling())
        if HOT.is_set():raise RuntimeError('Limitation thermique ou 80 C observés ; profil interrompu.')
        # Distinct first bytes prevent the persistent engine from reusing a live prefix.
        prefix='' if warmup else f'Mesure indépendante {case}.\n'
        payload=dict(model=model,messages=[dict(role='user',content=prefix+prompt)],max_tokens=limit,temperature=0,seed=42,
                     cache_prompt=False,stream=False,chat_template_kwargs=dict(enable_thinking=False),reasoning_effort='none')
        write(folder/(case+'-request.json'),payload)
        start=time.time();answer=post(port,'/v1/chat/completions',payload);end=time.time()
        write(folder/(case+'-response.json'),answer)
        text=answer['choices'][0]['message']['content'] or ''
        (folder/(case+'-answer.txt')).write_text(text,encoding='utf-8')
        valid=bool(text.strip());strict=None
        if expected:
            try:parsed=json.loads(text.strip());strict=True
            except ValueError:
                strict=False;fenced=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```',text.strip(),re.S)
                try:parsed=json.loads(fenced.group(1)) if fenced else None
                except ValueError:parsed=None
            valid=isinstance(parsed,dict) and all(parsed.get(k)==v for k,v in expected.items())
        timing=answer.get('timings') or {}
        row=dict(name=case,warmup=warmup,start=start,end=end,elapsed_s=end-start,timings=timing,usage=answer.get('usage'),
                 quality_pass=valid,strict_json=strict,text_sha256=hashlib.sha256(text.encode()).hexdigest())
        records.append(row);write(folder/'results.json',records)
        print(json.dumps(dict(profile=name,case=case,elapsed_s=end-start,timings=timing,quality=valid),ensure_ascii=False),flush=True)
        if timing.get('cache_n',0)!=0:raise RuntimeError('Réutilisation du prompt détectée ; mesure refusée.')
        if HOT.is_set():raise RuntimeError('Limitation thermique ou 80 C observés ; profil interrompu.')
        if not valid:raise RuntimeError('Vérification échouée : '+case)
    one('warmup','Réponds uniquement avec un objet JSON contenant la clé resultat et le nombre 42.',64,{'resultat':42},True)
    for rep in range(1,4):
        for case,prompt,limit,expected in cases:one(f'r{rep}-{case}',prompt,limit,expected)
    if long:
        for lines in (64,256,1024):
            rows=[f'Ligne {i:04d}: le dossier décrit un jardin, des arbres et un chemin de pierre.' for i in range(lines)]
            rows.insert(lines//2,'Information prioritaire : le code secret du dossier est LUMIERE-7429.')
            prompt='Lis le dossier suivant.\n'+'\n'.join(rows)+'\nRéponds uniquement avec un objet JSON contenant la clé code et le code secret indiqué au milieu du dossier.'
            for rep in (1,2):one(f'dossier-{lines}-r{rep}',prompt,80,{'code':'LUMIERE-7429'})
    if stress:
        # At least three minutes, at most twelve 512-token answers; no cooling between requests.
        stress_start=time.monotonic()
        for rep in range(1,13):
            one(f'soutenu-{rep}','Décris en français le trajet de l’eau, de la pluie à la rivière puis à la mer. Développe une explication détaillée et continue.',512,None)
            if time.monotonic()-stress_start>=180 and rep>=4:break
    write(folder/'gpu-apres.json',gpu())
    return dict(profile=name,requests=len(records)-1,quality_pass=all(r['quality_pass'] for r in records))

def launch_strata(profile):
    cfg=json.loads((ROOT/f'config-{profile}.json').read_text())
    cfg['log']=str(RUN/f'engine-{profile}.log')
    cfgpath=RUN/f'config-{profile}.json';write(cfgpath,cfg)
    state(phase='chargement',profile='strata-'+profile)
    spawn([str(PY),'-u','-m','serve.server','--engine','strata','--config',str(cfgpath),'--host','127.0.0.1','--port','8081'],cfg['cwd'],'strata-'+profile)
    health(8081)
    return cfg['model_name']
def launch_27(mtp,context):
    name=f'27b-{"mtp2" if mtp else "sans-mtp"}-{context}'
    deadline=time.monotonic()+120
    while any(r['vram_mib']>1024 for r in gpu()):
        if time.monotonic()>deadline:raise RuntimeError('VRAM encore occupée ; second chargement refusé.')
        time.sleep(2)
    if psutil.virtual_memory().available/2**30<20:raise RuntimeError('Moins de 20 Gio de RAM disponibles pour le 27B.')
    exe=PROJECT/'cafe-build-p100/bin/llama-server.exe'
    model=Path(r'D:\modèle\huihui-ai\Huihui-Qwen3.8-27B-abliterated-GGUF\Huihui-Qwen3.8-27B-abliterated-UD-DW-Q4_K_M.gguf')
    command=[str(exe),'-m',str(model),'--host','127.0.0.1','--port','8081','--alias','huihui-27b','-c',str(context),'-np','1','-t','4','-tb','4','-b','512','-ub','256','-ngl','99','--fit','off','--split-mode','tensor','--tensor-split','1,1','--flash-attn','on','--jinja','--metrics']
    if mtp:command+=['-md',str(model.parent/'mtp-Qwen3.8-27B-Q4_0.gguf'),'--spec-type','draft-mtp','--spec-draft-n-max','2','--spec-draft-ngl','99']
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='GPU-a39f1b57-5a26-b53d-e943-44ef8042a438,GPU-486d5352-582e-2880-78bf-3dec4688e142',CUDA_DISABLE_PTX_JIT='1')
    env['PATH']=str(PROJECT/'toolchain/cuda-12.4/bin')+';'+env['PATH']
    state(phase='chargement',profile=name)
    write(RUN/(name+'-identity.json'),dict(binary_sha256=hashfile(exe),model=str(model),model_size=model.stat().st_size,context=context,mtp=mtp))
    spawn(command,exe.parent,name,env);health(8081,900)
    return name

try:
    pointer=json.loads((PROJECT/'lanceur/session.json').read_text(encoding='utf-8-sig'))
    session=Path(pointer['directory']);cfgpath=session/'strata.json'
    production=json.loads(cfgpath.read_text(encoding='utf-8-sig'))
    files=[PROJECT/'lanceur/reglages.json',PROJECT/'lanceur/base-strata.json',PROJECT/'strata-iq4-p100-hybride.json',Path(production['exe']),cfgpath]
    stamps=[dict(path=str(p),sha256=hashfile(p)) for p in files]
    backup=RUN/'production-sauvegarde';backup.mkdir()
    write(backup/'configuration-active.json',production)
    write(backup/'reprise.json',dict(config_path=str(cfgpath),files=stamps,session=str(session),floor=6))
    write(RUN/'production-metrics-avant.json',get(8080,'/metrics'))
    monitor=threading.Thread(target=observer,daemon=True);monitor.start()
    if not ONLY_MTP:
        try:
            STATE['outcomes'].append(benchmark('flash-production',8080,production['model_name'],stress=not COOLED))
        except Exception as exc:
            STATE['outcomes'].append(dict(profile='flash-production',error=str(exc)))
            state(profile_error=str(exc))
    state(phase='arret-production',profile=None)
    STOPPED=True;write(RUN/'arret-production.json',control_stop());time.sleep(5)
    for profile in (() if ONLY_MTP else ('reference','mtp-batch')):
        try:
            model=launch_strata(profile)
            STATE['outcomes'].append(benchmark('strata-'+profile,8081,model,stress=profile=='reference' and not COOLED))
        except Exception as exc:
            STATE['outcomes'].append(dict(profile='strata-'+profile,error=str(exc)))
            state(profile_error=str(exc))
        finally:stop_test();state(outcomes=STATE['outcomes']);time.sleep(3)
    cases_27=((True,4096,False,True),) if ONLY_MTP else ((True,32768,True,False),(True,4096,False,True),(False,4096,False,False))
    for mtp,context,full,stress in cases_27:
        try:
            name=launch_27(mtp,context)
            STATE['outcomes'].append(benchmark(name,8081,'huihui-27b',long=full,stress=stress))
        except Exception as exc:
            STATE['outcomes'].append(dict(profile=STATE['profile'],error=str(exc)))
            state(profile_error=str(exc))
        finally:stop_test();state(outcomes=STATE['outcomes']);time.sleep(3)
except Exception as exc:
    state(error=str(exc))
finally:
    stop_test()
    if STOPPED:
        state(phase='reprise-production',profile=None)
        assert all(hashfile(s['path'])==s['sha256'] for s in stamps),'Fichiers de production modifiés.'
        command=[str(PROJECT/'Strata-src/.venv/Scripts/python.exe'),'-u',str(PROJECT/'lanceur/runtime.py'),'--config',str(cfgpath),'--run-dir',str(session),'--floor','6']
        with (RUN/'reprise-production.log').open('wb') as log:
            recovery=subprocess.Popen(command,cwd=PROJECT,stdout=log,stderr=log,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
        state(recovery_pid=recovery.pid)
        health(8080,1800)
    try:
        response=post(8080,'/v1/chat/completions',dict(model=production['model_name'],messages=[dict(role='user',content='Réponds uniquement avec un objet JSON contenant la clé resultat et le résultat de 43 multiplié par 7.')],temperature=0,max_tokens=64,cache_prompt=False,chat_template_kwargs=dict(enable_thinking=False),reasoning_effort='none'))
        text=response['choices'][0]['message']['content'].strip()
        match=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```',text,re.S)
        assert json.loads(match.group(1) if match else text)['resultat']==301,text
        with socket.socket() as probe:assert probe.connect_ex(('127.0.0.1',8081))!=0
        metrics=get(8080,'/metrics')
        write(RUN/'production-retablie.json',dict(health=get(8080,'/health'),engine=metrics.get('engine'),inference_pass=True,answer=text,files_unchanged=all(hashfile(s['path'])==s['sha256'] for s in stamps),test_port_closed=True))
        state(phase='production-retablie',profile=None)
    finally:
        DONE.set()
        if 'monitor' in globals():monitor.join(15)
    print('DOSSIER_RESULTATS '+str(RUN),flush=True)
