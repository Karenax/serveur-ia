"""Update the independent server Max pack, without loading or restarting Qwen."""
import json,os,shutil,sys,time,urllib.request
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen'),str(ROOT/'client-voice')]
from advanced_voice import AdvancedVoice
from max_installation import MaxInstallation
from prepare_max_pack import Release
from validate_live_lots6_8 import get,models
from releases import profile

assert get('/api/backups')['job']['state']=='succeeded'
assert not get('/api/state')['queue']['active']
active={item['id'] for item in json.loads((ROOT/'lanceur/acces-distants.json').read_text(encoding='utf-8'))['clients'] if not item['revoked']}
personal=profile(next(path for path in (ROOT/'lanceur/clients').glob('*.exe') if path.stem in active))
request=urllib.request.Request('http://127.0.0.1:8766/v1/voice/max/status',headers={'Authorization':'Bearer '+personal['token']})
with urllib.request.urlopen(request,timeout=20) as response:before=json.load(response)
assert not before['busy'] and not before['testing'] and not before['loaded'],before
home=ROOT/'toolchain/voice-max-server';saved=OUT/'previous-server';saved.mkdir(exist_ok=True)
assert not (OUT/'server-installation.json').exists(),'Already installed; inspect evidence first'
for process in psutil.process_iter(['pid','cmdline']):
    if process.pid==os.getpid():continue
    assert not any(str(home).lower() in str(argument).lower() for argument in process.info['cmdline'] or []),'An existing Max server worker is running'
for name in ('runtime.json','benchmark.json','gpu.json'):
    path=home/name
    if path.exists() and not (saved/name).exists():shutil.copy2(path,saved/name)
proof=json.loads((OUT/'stack-validation.json').read_text(encoding='utf-8'))
assert proof['benchmark']['functional'] and proof['runtime_api']==6
assert 'P2200' in proof['device']['description']
before_models=models();low=get('/api/voice')['enabled']
home.mkdir(exist_ok=True)
(home/'gpu.json').write_text(json.dumps({'device':proof['device']['id']}),encoding='utf-8')
cache=home/'models/asr/ggml-large-v3-turbo-q5_0.bin';cache.parent.mkdir(parents=True,exist_ok=True)
if not cache.exists():os.link(ROOT/'toolchain/max-realtime-models/ggml-large-v3-turbo-q5_0.bin',cache)
runtime=AdvancedVoice(home);installer=MaxInstallation(home,Release(ROOT/'toolchain/voice-max-realtime-release',ROOT/'lanceur'),runtime,ROOT/'toolchain/asr-models')
try:
    installer.detect();plan=installer.plan();installer.install(plan['plan'])
    deadline=time.monotonic()+300
    while installer.thread.is_alive() and time.monotonic()<deadline:installer.thread.join(5)
    assert not installer.thread.is_alive() and installer.status()['phase']=='ready',installer.status()
    status=runtime.status();assert status['available'] and status['loaded'],status
    assert status['device']['id']==proof['device']['id'],status
    result={'passed':True,'revision':runtime.configuration()['catalogue']['revision'],'device':status['device'],'benchmark':json.loads((home/'benchmark.json').read_text(encoding='utf-8')),'previous_weights_preserved':True}
finally:installer.close();runtime.close()
assert models()==before_models and get('/api/voice')['enabled']==low
result['workers_unloaded']=not runtime.status()['loaded']
(OUT/'server-installation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
