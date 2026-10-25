"""Publish the verified French Max pack; preserve the previous signed distribution."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from core import HOME
from signing import public
from max_installation import verify_catalogue
from validate_live_lots6_8 import get

source=ROOT/'toolchain/voice-max-french-release'
destination=ROOT/'toolchain/voice-max-release'
assert get('/api/backups')['job']['state']=='succeeded','Finish the verified backup first'
catalogue=verify_catalogue(json.loads((source/'release.json').read_text(encoding='utf-8')),public(HOME,create=False))
proof=json.loads((OUT/'pack-validation.json').read_text(encoding='utf-8'))
assert proof['revision']==catalogue['revision'] and catalogue['runtime_api']==5
assert all(item['passed'] for item in proof['workers'].values())
assert catalogue['models'][-2]['sha256']=='ea393ebaf2167ea23ce9fc18b093822851358a950d7075cd47ab4f6ce23e887d'
with (source/'runtime.zip').open('rb') as stream:
    assert hashlib.file_digest(stream,'sha256').hexdigest()==catalogue['runtime']['sha256']
previous=OUT/'previous-pack';previous.mkdir(exist_ok=True)
for name in ('runtime.zip','release.json'):
    assert not (previous/name).exists(),'Pack already published; inspect the evidence before resuming'
    shutil.copy2(destination/name,previous/name)
    shutil.copy2(source/name,destination/(name+'.publish.tmp'))
for name in ('runtime.zip','release.json'):
    (destination/(name+'.publish.tmp')).replace(destination/name)
from voice_max_package import package
served,_=package(HOME)
assert served==catalogue
result={'passed':True,'revision':served['revision'],'runtime_api':served['runtime_api'],
        'runtime_bytes':served['runtime']['bytes'],'upgrade_download_bytes':proof['upgrade_download_bytes'],
        'reused_model_bytes':proof['reused_bytes'],'models_bytes':sum(item['bytes'] for item in served['models']),
        'voice':'French reference · fr-FR','signature_verified':True,'previous_distribution_preserved':True}
(OUT/'pack-publication.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
