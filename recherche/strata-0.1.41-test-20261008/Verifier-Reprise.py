"""Wait for the original session, then verify its identity and a real answer."""
import hashlib, json, re, socket, time, urllib.request
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parent
backup = json.loads((ROOT/'production-sauvegarde/reprise.json').read_text(encoding='utf-8-sig'))
cfg_path = Path(backup['config_path'])
cfg = json.loads(cfg_path.read_text(encoding='utf-8-sig'))
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(url):
    return json.load(opener.open(url,timeout=10))

deadline = time.monotonic()+1200
while True:
    try:
        health = get('http://127.0.0.1:8080/health')
        state = json.loads((cfg_path.parent/'state.json').read_text(encoding='utf-8-sig'))
        if health.get('loaded') is True and state.get('status')=='pret':
            break
    except (OSError, ValueError):
        pass
    if time.monotonic()>deadline:
        raise TimeoutError('La reprise ne repond pas encore : verifier les journaux sans arreter le moteur.')
    time.sleep(5)

metrics = get('http://127.0.0.1:8080/metrics')
assert metrics['engine']['version']=='0.1.35', metrics['engine']
engines = []
for p in psutil.process_iter(['name']):
    try:
        if p.info['name']=='strata.exe':
            engines.append((p,Path(p.exe()).resolve()))
    except psutil.Error:
        pass
assert len(engines)==1 and engines[0][1]==Path(cfg['exe']).resolve(), engines
checks=[]
for item in backup['files']:
    with Path(item['path']).open('rb') as stream:
        actual = hashlib.file_digest(stream,'sha256').hexdigest()
    checks.append({'path':item['path'],'unchanged':actual==item['sha256']})
assert all(c['unchanged'] for c in checks), checks
with socket.socket() as probe:
    assert probe.connect_ex(('127.0.0.1',8081))!=0, 'Serveur de test encore ouvert'

payload={'model':cfg['model_name'],'messages':[{'role':'user','content':
         'Reponds uniquement avec un objet JSON contenant la cle resultat et le resultat de 43 multiplie par 7.'}],
         'stream':False,'temperature':0,'seed':42,'max_tokens':64,'cache_prompt':False,
         'chat_template_kwargs':{'enable_thinking':False},'reasoning_effort':'none'}
request=urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',
         data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
start=time.monotonic()
response=json.load(opener.open(request,timeout=180))
answer=response['choices'][0]['message']['content'].strip()
fenced=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```',answer,re.S)
parsed=json.loads(fenced.group(1) if fenced else answer)
assert parsed.get('resultat')==301, answer
report={'verified_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'health':health,'session_status':state['status'],'engine_version':metrics['engine']['version'],
        'engine_pid':engines[0][0].pid,'engine_exe':str(engines[0][1]),
        'production_files':checks,'test_port_closed':True,
        'inference':{'passed':True,'answer':answer,'elapsed_s':time.monotonic()-start},
        'launcher_health':get('http://127.0.0.1:8765/health')}
(ROOT/'validation/production-retablie.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'production_restored':True,'version':report['engine_version'],
                  'pid':report['engine_pid'],'answer':answer},ensure_ascii=False),flush=True)
