"""Restore only the ten screenshots known clean at audit start, after UI tests.

The two screenshots already modified before the audit are deliberately excluded.
New test evidence is copied into this audit before restoring the original bytes.
"""
from pathlib import Path
import hashlib, json, subprocess
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
paths=[f'maintenance/2026-10-24-vocal-workspace/ui/{p}-{v}.png' for p in ('windows','android') for v in ('kiara','microphone')]
paths += [f'maintenance/2026-10-25-assistant-integration/ui/{p}-{v}.png' for p in ('windows','android') for v in ('desktop','phone','tablet')]
records=[]
for name in paths:
 path=ROOT/name
 original=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
 observed=path.read_bytes()
 target=OUT/'ui-tests'/Path(name).parts[1]/path.name
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(observed)
 path.write_bytes(original)
 records.append({'path':name,'restored_sha256':hashlib.sha256(original).hexdigest(),'test_capture':target.relative_to(OUT).as_posix()})
(OUT/'restored-screenshots.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('Restored 10 initially clean historical screenshots; audit captures retained.')
