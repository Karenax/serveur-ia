"""Authorized Windows rollout. Never read recovery phrases or record access secrets."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import psutil
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'lanceur'))
from validate_live_lots6_8 import get,post,models,preserved_files,backup_config
from core import HOME,write_json
import releases
OUT=Path(__file__).resolve().parent
def users():
    value={}
    with sqlite3.connect((HOME/'espaces-prives/espaces.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=20) as db:
        for name in ('client_histories','projects','documents','memories','conversations','policies','jobs','personal_memories','knowledge_exclusions'):
            rows=db.execute('SELECT * FROM '+name+' ORDER BY 1').fetchall()
            encoded=json.dumps([[item.hex() if isinstance(item,bytes) else item for item in row] for row in rows],ensure_ascii=False,separators=(',',':')).encode()
            value[name]={'count':len(rows),'sha256':hashlib.sha256(encoded).hexdigest()}
    return value
report={'before':{'models':models(),'files':preserved_files(),'users':users(),'backups':backup_config(get('/api/backups'))},'contains_secret_values':False}
state=get('/api/state');assert state['running'] and state['health']['loaded'] and not state['queue']['active']
proof=json.loads((OUT/'windows-release.json').read_text(encoding='utf-8'));assert proof['passed']
source=ROOT/'toolchain/releases-staging/windows-3.5.21/Accès serveur Fred.exe'
assert releases.digest(source)==proof['sha256']
target=ROOT/'client-qwen/dist/Accès serveur Fred.exe'
previous=ROOT/'toolchain/releases-staging/windows-before-conversation';previous.mkdir(parents=True,exist_ok=True)
shutil.copy2(target,previous/target.name);shutil.copy2(target.parent/'release.json',previous/'release.json')
shutil.copy2(source,target);signed=releases.manifest(HOME);assert releases.status(HOME)['verified']
report['release']={'version':signed['version'],'sha256':signed['sha256'],'bytes':signed['bytes'],'signature_verified':True}
report['personal_clients_prepared']=releases.repackage(HOME)
write_json(HOME/'voix.json',{'enabled':True})
identity=json.loads((HOME/'interface.pid.json').read_text());parent=psutil.Process(identity['pid'])
assert abs(parent.create_time()-identity['created'])<.01
assert str(HOME/'app.py').lower() in [arg.lower() for arg in parent.cmdline()]
children=[]
for child in parent.children(recursive=True):
    args=child.cmdline();assert child.pid not in (8200,14628) and 'serve.server' not in args
    if any(Path(arg).name.lower() in ('embedding_worker.py','voice_worker.py','wireguard-bridge.exe') for arg in args):
        children.append((child,child.create_time()))
parent.terminate();parent.wait(timeout=10)
for child,created in reversed(children):
    try:
        if child.is_running() and abs(child.create_time()-created)<.01:child.terminate();child.wait(timeout=10)
    except psutil.NoSuchProcess:pass
result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Interface-Qwen.ps1'),'-SansNavigateur','-PreserverEtatModele'],
    capture_output=True,text=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,'Console restart failed'
deadline=time.monotonic()+90
while time.monotonic()<deadline:
    voice=get('/api/voice');knowledge=get('/api/knowledge')
    if voice['ready'] and knowledge['engine']['status']=='pret' and not knowledge['index']['pending']:break
    time.sleep(.5)
assert voice['ready'] and knowledge['engine']['status']=='pret' and not knowledge['index']['pending']
state=get('/api/state');assert state['running'] and state['health']['loaded']
report['after']={'models':models(),'files':preserved_files(),'users':users(),'backups':backup_config(get('/api/backups'))}
assert report['before']==report['after'],'Production data/process/settings changed'
report.update({'passed':True,'voice':voice,'knowledge':knowledge,'qwen_loaded':True,'release_served_verified':get('/api/releases')['verified']})
assert report['release_served_verified']
post('/api/backups/create',{})
deadline=time.monotonic()+90
while time.monotonic()<deadline:
    backups=get('/api/backups')
    if backups['job']['state']!='running':break
    time.sleep(.5)
assert backups['job']['state']=='succeeded'
record=next(item for item in backups['catalog'] if item['verified'] and item['version']==2)
report['backup_created']={key:record[key] for key in ('file','size','sha256','version','verified')}
assert backup_config(backups)==report['before']['backups']
(OUT/'production-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'version':signed['version'],'voice_ready':voice['ready'],'eg2_ready':knowledge['engine']['status'],'passages':knowledge['index']['indexed'],'qwen_preserved':True,'backup_verified':record['verified']}))
