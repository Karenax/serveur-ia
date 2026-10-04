import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
ANALYSIS=ROOT/'analyses/2026-10-02-goulots'
ARCHIVE=ROOT/'comparatifs/2026-10-02-strata-hybride-p100'
checked=[]
for relative,name in (('2026-10-02-cafe-q4-p100','manifest.json'),('2026-10-02-strata-q4-p100','manifest-final.json')):
    folder=ROOT/'comparatifs'/relative
    manifest=json.loads((folder/name).read_text(encoding='utf-8-sig'))
    for record in manifest['files']:
        file=folder/record.get('path',record.get('name'))
        actual=hashlib.sha256(file.read_bytes()).hexdigest()
        if actual.lower()!=record['sha256'].lower(): raise RuntimeError(f'Archive antérieure modifiée: {file}')
    checked.append(dict(archive=relative,files_verified=len(manifest['files'])))

validation=sorted(p for p in ARCHIVE.glob('validation-*') if (p/'resultats.json').exists())[-1]
configuration=json.loads((validation/'configuration.json').read_text(encoding='utf-8-sig'))
results=json.loads((validation/'resultats.json').read_text(encoding='utf-8'))
assert configuration['request_override'] is False
assert len(results)==2 and all(r['cpu_expert_jobs']>0 and r['ram_gpu_experts']==0 for r in results)
active=json.loads((ROOT/'strata-q4-p100-hybride.json').read_text(encoding='utf-8-sig'))
assert active['args'][active['args'].index('--pcie-frac')+1]=='0'
binary=hashlib.sha256(Path(active['exe']).read_bytes()).hexdigest()
assert binary==configuration['binary_sha256']
deployment=dict(checked_at=dt.datetime.now().astimezone().isoformat(),engine='Strata 0.1.35 P100 hybrid',
    source_commit='d9ab8435f654c368c586340d490915f6addf56a3',binary_sha256=binary,
    configuration=active,validation=str(validation),results=results,
    earlier_archives_verified=checked,updated_remote_commit='36fa455e579b23a9c909c2c6fe1bddd9e51cb8ca',
    remote_version='0.1.36 reviewed, not installed')
(ARCHIVE/'activation-validee.json').write_text(json.dumps(deployment,ensure_ascii=False,indent=2),encoding='utf-8')
for source in ('ANALYSE-GOULOTS-P100.txt','COMPARATIF-CPU-GPU-P100.txt','LISEZ-MOI.txt',
               'Finaliser-Analyse-P100.py','Test-Strata-Hybride.ps1','Analyser-Comparatifs.py'):
    shutil.copy2(ROOT/source,ARCHIVE/source)
shutil.copy2(ROOT/'ANALYSE-GOULOTS-P100.txt',ANALYSIS/'ANALYSE-GOULOTS-P100.txt')
shutil.copy2(ROOT/'comparatifs/comparatif-q4-p100.csv',ARCHIVE/'comparatif-q4-p100.csv')
shutil.copy2(ROOT/'comparatifs/ressources-q4-p100.json',ARCHIVE/'ressources-q4-p100.json')
for folder in (ANALYSIS,ARCHIVE):
    manifest={}
    for file in sorted(folder.rglob('*')):
        if file.is_file() and file.name!='manifest-sha256.json' and '__pycache__' not in file.parts:
            manifest[str(file.relative_to(folder)).replace('\\','/')]=dict(bytes=file.stat().st_size,sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    path=folder/'manifest-sha256.json'
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,record in manifest.items():
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==record['sha256']
    print(json.dumps(dict(archive=str(folder),files_verified=len(manifest)),ensure_ascii=True))
print(json.dumps(dict(earlier_archives_verified=checked,binary_sha256=binary),ensure_ascii=True))
