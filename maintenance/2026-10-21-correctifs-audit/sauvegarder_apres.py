"""Create and verify the final encrypted NAS copy without disclosing its phrase."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from validate_live_lots6_8 import get,post,models,preserved_files,content_fingerprints

before=json.loads((OUT/'avant-livraison.json').read_text())
post('/api/backups/create',{'kind':'manual','protected':True})
deadline=time.monotonic()+180
while time.monotonic()<deadline:
    status=get('/api/backups')
    if status['job']['state']!='running':break
    time.sleep(1)
assert status['job']['state']=='succeeded'
record=max(status['catalog'],key=lambda row:row['timestamp'])
assert record['verified'] and record['secondary']['status']=='copied'
with Path(record['secondary']['file']).open('rb') as stream:
    assert hashlib.file_digest(stream,'sha256').hexdigest()==record['sha256']
verified=post('/api/backups/verify',{'file':record['file']})
assert verified['summary']['sha256']==record['sha256']
assert models()==before['models'] and preserved_files()==before['files']
assert content_fingerprints()==before['users']
(OUT/'sauvegarde-apres.json').write_text(json.dumps({'passed':True,
    'sha256':record['sha256'],'bytes':record['size'],'nas_verified':True,
    'archive_authenticated':True,'model_keys_user_data_preserved':True},indent=2),encoding='utf-8')
print('Final encrypted backup and NAS copy verified; production data preserved.')
