"""Publish only the signed runtime exercised by the complete replay test."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from core import HOME
from signing import public
from max_installation import verify_catalogue
from validate_live_lots6_8 import get
source=ROOT/'toolchain/voice-max-realtime-release';destination=ROOT/'toolchain/voice-max-release'
assert get('/api/backups')['job']['state']=='succeeded'
catalogue=verify_catalogue(json.loads((source/'release.json').read_text(encoding='utf-8')),public(HOME,create=False))
proof=json.loads((OUT/'stack-validation.json').read_text(encoding='utf-8'))
assert catalogue['runtime_api']==6 and proof['revision']==catalogue['revision']
assert proof['benchmark']['functional'] and len(proof['turns'])==2
assert all(len(turn['recognized'])<140 and turn['max_playback_gap_ms']==0 for turn in proof['turns'])
server=json.loads((OUT/'server-installation.json').read_text(encoding='utf-8'))
assert server['passed'] and server['workers_unloaded'] and server['revision']==catalogue['revision']
with (source/'runtime.zip').open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==catalogue['runtime']['sha256']
previous=OUT/'previous-pack';previous.mkdir(exist_ok=True)
for name in ('runtime.zip','release.json'):
    assert not (previous/name).exists(),'Already published; inspect evidence before resuming'
    shutil.copy2(destination/name,previous/name)
    shutil.copy2(source/name,destination/(name+'.publish.tmp'))
for name in ('runtime.zip','release.json'):(destination/(name+'.publish.tmp')).replace(destination/name)
from voice_max_package import package
served,_=package(HOME);assert served==catalogue
vad=sum(item['bytes'] for item in catalogue['models'] if item['name'].endswith(('smart-turn.onnx','silero-vad.onnx')))
result={'passed':True,'revision':catalogue['revision'],'runtime_api':6,'signature_verified':True,'runtime_bytes':catalogue['runtime']['bytes'],
        'upgrade_download_bytes':catalogue['runtime']['bytes']+sum(item['bytes'] for item in catalogue['models'])-vad,
        'fresh_download_bytes':catalogue['runtime']['bytes']+sum(item['bytes'] for item in catalogue['models']),
        'voice':'Phonon · français · Tiphaine','recognizer':'Whisper large-v3-turbo Q5 · Vulkan','previous_distribution_preserved':True}
(OUT/'pack-publication.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
