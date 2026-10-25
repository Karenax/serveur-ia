"""Read-only checks against the published authenticated gateway."""
import json
import base64
import hashlib
from pathlib import Path
import sqlite3
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from core import HOME
from releases import profile
from validate_live_lots6_8 import get,PHRASE


def main():
    access=json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))
    owner=next(item['id'] for item in access['clients'] if not item['revoked'])
    p=profile(HOME/'clients'/(owner+'.exe'))
    headers={'Authorization':'Bearer '+p['token'],'Content-Type':'application/json','X-Fred-Agent-Protocol':'4'}
    def request(path,body=None):
        req=urllib.request.Request('http://127.0.0.1:8766'+path,None if body is None else json.dumps(body).encode(),headers)
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
    workspace=request('/v1/workspace')
    assert {'assistant_commands','reminders','project_briefs'}<=set(workspace['capabilities'])
    result=request('/v1/workspace/action',{'action':'assistant','operation':'list'})
    assert {'memory_add','reminder_create','brief_generate'}<=set(result['capabilities'])
    with sqlite3.connect((HOME/'espaces-prives/espaces.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
        assert {'assistant_items','assistant_commands'}<={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        opted=db.execute("SELECT COUNT(*) FROM assistant_items WHERE kind='brief' AND json_extract(payload,'$.automatic')=1").fetchone()[0]
    import yaml
    configs=list((HOME/'hermes-fred/profiles').glob('fred-*/config.yaml'))
    assert configs
    for config in configs:
        value=yaml.safe_load(config.read_text(encoding='utf-8'))
        assert value['memory']['memory_enabled'] is False and value['memory']['user_profile_enabled'] is False
    # Compare with the actual verified pre-delivery archive, without extracting
    # private content or credentials to disk or tool output.
    before=json.loads((OUT/'avant-livraison.json').read_text(encoding='utf-8'))
    record=next(r for r in get('/api/backups')['catalog'] if r.get('sha256')==before['backup_sha256'])
    blob=Path(record['file']).read_bytes()
    assert hashlib.sha256(blob).hexdigest()==before['backup_sha256'] and blob.startswith(b'FREDBACKUP2')
    from operations import cipher
    package=json.loads(cipher(PHRASE.read_text(encoding='utf-8'),blob[11:27]).decrypt(blob[27:]))['package']['files']
    old=sqlite3.connect(':memory:');old.deserialize(base64.b64decode(package['workspace']))
    preserved=[]
    with sqlite3.connect((HOME/'espaces-prives/espaces.sqlite3').as_uri()+'?mode=ro',uri=True) as current:
        for table in ('projects','documents','memories','personal_memories','conversations','client_histories','policies','jobs','knowledge_exclusions','document_sources'):
            assert old.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()==current.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall(),table+' changed'
            preserved.append(table)
    old.close();memory_files=0
    for name,entry in package.get('hermes',{}).get('files',{}).items():
        if '/memories/' in name:
            assert (HOME/'hermes-fred'/name).is_file()
            assert hashlib.sha256((HOME/'hermes-fred'/name).read_bytes()).hexdigest()==entry['sha256']
            memory_files+=1
    report={'passed':True,'gateway_capabilities_verified':True,'authenticated_assistant_read_verified':True,
        'canonical_tables_present':True,'hermes_native_memory_disabled':True,'legacy_files_preserved_for_review':True,
        'automatic_briefs_enabled':opted,'real_user_data_written_for_tests':False,
        'voice_activation_setting_preserved':get('/api/voice')['enabled'] is False,
        'canonical_tables_identical_to_pre_delivery_backup':preserved,'legacy_memory_files_preserved':memory_files,
        'backend_source_sha256':hashlib.sha256((HOME/'assistant_commands.py').read_bytes()).hexdigest(),
        'gateway_started_after_backend_update':json.loads((HOME/'interface.pid.json').read_text(encoding='utf-8'))['created']>=(HOME/'assistant_commands.py').stat().st_mtime}
    assert report['gateway_started_after_backend_update']
    (OUT/'assistant-production.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
