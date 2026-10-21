"""Restore the verified NAS copy inside a private temporary, non-running controller."""
import base64
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from app import Controller
from validate_live_lots6_8 import get, preserved_files, models
from wg_crypto import protect

before={'models':models(),'files':preserved_files()}
catalog=get('/api/backups')['catalog']
record=next(r for r in catalog if r.get('protected') and r.get('secondary',{}).get('status')=='copied')
nas=Path(record['secondary']['file'])
with nas.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
assert digest==record['sha256']
password=protect((ROOT/'lanceur/sauvegardes/automatisation.dpapi').read_bytes(),decrypt=True).decode()
with tempfile.TemporaryDirectory(prefix='audit-nas-restore-',dir=ROOT/'toolchain') as temp:
    home=Path(temp)
    c=Controller(home,include_legacy=False)
    # A recovery drill restores bytes and profiles but never binds production ports.
    c.recreate_hermes=lambda **kwargs:None
    try:
        assert not c.processes() and not c.gateway and not c.remote.metadata()['enabled']
        inspected=c.operations.backups.inspect({'file':str(nas),'password':password})
        source_db=home/'archive-source.sqlite3'
        source_db.write_bytes(base64.b64decode(inspected['package']['files']['workspace']))
        def data_fingerprints(path):
            values={}
            with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
                for table in ('client_histories','projects','documents','memories','conversations'):
                    rows=db.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()
                    normalized=[[v.hex() if isinstance(v,bytes) else v for v in row] for row in rows]
                    encoded=json.dumps(normalized,ensure_ascii=False,separators=(',',':')).encode()
                    values[table]={'rows':len(rows),'sha256':hashlib.sha256(encoded).hexdigest()}
            return values
        expected=data_fingerprints(source_db)
        c.operations.restorations.restore_sync({'file':str(nas),'password':password})
        actual=data_fingerprints(home/'espaces-prives/espaces.sqlite3')
        assert actual==expected
        assert not c.remote.metadata()['enabled'] and c.gateway is None and c.hermes is None
        evidence={'passed':True,'nas_sha256':digest,'nas_bytes':nas.stat().st_size,
                  'restored_in_private_temporary_directory':True,'no_service_started':True,
                  'data':actual,'remote_disabled_after_restore':True,
                  'hermes_restored':(home/'hermes-fred/fred-integration.db').is_file()}
    finally:
        c.operations.backups.close(); c.remote.workspace.shutdown(); c.voice.close(); c.embeddings.stop()
        password=None
assert before=={'models':models(),'files':preserved_files()}
evidence['production_model_keys_settings_preserved']=True
(OUT/'restauration-nas.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print('NAS archive restored and verified in isolation; production unchanged.')
