"""Summarize delivered evidence after the complete regression suite succeeds."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from validate_live_lots6_8 import get,preserved_files,models,backup_config
import releases
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
def test_log(name):
    text=(OUT/name).read_text(encoding='utf-8-sig');match=re.search(r'Ran (\d+) tests? in ([\d.]+)s',text)
    assert match and re.search(r'^OK\s*$',text,re.M),name
    return {'passed':int(match[1]),'seconds':float(match[2])}
suite=test_log('regression.log')
logs={name:test_log(name) for name in ('unit-tests.log','http-tests.log','restoration-tests.log','small-service-tests.log','small-http-tests.log')}
ui=read('browser/conversation-ui.json');small=read('small-browser/voice-ui.json')
assert ui['passed'] and not ui['errors'] and len(ui['checks'])==10 and small['passed']
production=read('production-validation.json');assert production['passed']
voice=get('/api/voice');knowledge=get('/api/knowledge');state=get('/api/state')
assert voice['ready'] and knowledge['engine']['status']=='pret' and not knowledge['index']['pending']
assert state['health']['loaded'] and models()==production['before']['models']
assert preserved_files()==production['before']['files'] and backup_config(get('/api/backups'))==production['before']['backups']
with sqlite3.connect((ROOT/'lanceur/espaces-prives/espaces.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=20) as db:
    for name,expected in production['before']['users'].items():
        rows=db.execute('SELECT * FROM '+name+' ORDER BY 1').fetchall()
        data=json.dumps([[v.hex() if isinstance(v,bytes) else v for v in row] for row in rows],ensure_ascii=False,separators=(',',':')).encode()
        assert expected=={'count':len(rows),'sha256':hashlib.sha256(data).hexdigest()},name
status=releases.status(ROOT/'lanceur');assert status['verified'] and status['server_version']=='3.5.21'
release=read('windows-release.json');assert release['sha256']==status['release']['sha256']
after=read('after.json');assert all(after['preserved'].values())
sources={}
for folder in ('client-qwen','client-voice','lanceur'):
    directory=ROOT/folder
    candidates=list(directory.glob('*.py'))+list(directory.glob('*.js'))+list(directory.glob('*.html'))
    if folder=='client-voice':candidates+=list(directory.glob('*.cpp'))+list(directory.glob('*.h'))
    if folder=='client-qwen':candidates+=[directory/'wireguard-bridge/main.go']
    if folder=='lanceur':candidates+=list((directory/'web').glob('*.js'))+list((directory/'web').glob('*.html'))
    for path in candidates:sources[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
(OUT/'source-manifest.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')
result={'passed':True,'windows_server_version':'3.5.21','android_version_unchanged':'1.0.3/code4','release_sha256':release['sha256'],
    'regression':suite,'targeted_test_logs':logs,'conversation_browser_scenarios':len(ui['checks']),'small_browser_scenarios':len(small['checks']),
    'native_capture':read('native-capture.json'),'tts':read('tts-real.json'),'voice_ready':True,'eg2_ready':True,
    'eg2_passages':knowledge['index']['indexed'],'qwen_preserved':True,'user_rows_preserved':True,'backup_config_preserved':True,
    'backup_archive_verified':production['backup_created']['verified'],'all_preservation_hashes_match':True,
    'human_acoustic_trial_performed':False,'authenticated_public_https_audio_trial_performed':False}
(OUT/'delivery-final.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
doc=OUT/'VALIDATION.md';text=doc.read_text(encoding='utf-8').replace('Suite complète en cours ; résultat final consigné dans le journal',str(suite['passed'])+' tests réussis en '+str(suite['seconds'])+' s')
doc.write_text(text,encoding='utf-8')
context=ROOT/'CONTEXTE-PROJET.md';text=context.read_text(encoding='utf-8');old='Régression globale dans [la validation](preuves/conversation-windows-20261011/VALIDATION.md).'
text=text.replace(old,str(suite['passed'])+' tests de régression globale réussis en '+str(suite['seconds'])+' s, dans [la validation](preuves/conversation-windows-20261011/VALIDATION.md).')
context.write_text(text,encoding='utf-8')
print(json.dumps({'passed':True,'version':'3.5.21','regression':suite,'browser_scenarios':len(ui['checks']),'preserved':True}))
