"""Enable only Kiara's model in OpenCode Desktop's model picker preferences."""
from contextlib import closing
import json
from pathlib import Path
import secrets
import sqlite3
import time

import psutil
from file_lock import locked
from history_store import atomic

NAMESPACE='opencode.global.dat'
MAX_STATE=2*1024*1024


def running(executable):
    target=str(Path(executable).resolve()).casefold()
    for process in psutil.process_iter(['name','exe']):
        if (process.info['name'] or '').casefold()!=Path(executable).name.casefold():continue
        # An unreadable matching process may own a cached copy of these settings.
        if not process.info['exe'] or str(Path(process.info['exe']).resolve()).casefold()==target:return True
    return False


def model_state(raw,provider,model):
    if not isinstance(raw,str):raise ValueError('Préférences de modèles invalides.')
    if len(raw.encode('utf-8'))>MAX_STATE:raise ValueError('Préférences trop volumineuses.')
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError('Préférences de modèles invalides.')
    value.setdefault('recent',[]);value.setdefault('variant',{})
    users=value.setdefault('user',[])
    if not isinstance(users,list) or not all(isinstance(item,dict) for item in users):raise ValueError('Visibilité des modèles invalide.')
    matches=[item for item in users if item.get('providerID')==provider and item.get('modelID')==model]
    if len(matches)>1:raise ValueError('Préférence du modèle dupliquée.')
    if matches:
        if matches[0].get('visibility')=='show':return raw
        matches[0]['visibility']='show'
    else:users.append({'providerID':provider,'modelID':model,'visibility':'show'})
    return json.dumps(value,ensure_ascii=False,separators=(',',':'))


def backup_path(path):
    return path.with_name(path.name+'.fred-model-backup-'+time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.json')


def enable(desktop,provider,model):
    if not desktop:return {'status':'manual','backup':None}
    path=Path(desktop['state_path'])
    try:
        if running(desktop['executable']):return {'status':'close_required','backup':None}
        with locked(path):
            if desktop['format']=='sqlite':
                # Never create or migrate OpenCode's database. Its own schema must exist.
                with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=rw',uri=True,timeout=2)) as db, db:
                    db.execute('BEGIN IMMEDIATE')
                    row=db.execute('SELECT value,updated_at FROM state WHERE name=? AND key=?',(NAMESPACE,'model')).fetchone()
                    raw=row[0] if row else '{}';updated=model_state(raw,provider,model)
                    if updated==raw:return {'status':'enabled','backup':None}
                    if running(desktop['executable']):return {'status':'close_required','backup':None}
                    backup=backup_path(path)
                    atomic(backup,json.dumps({'name':NAMESPACE,'key':'model','previous':{'value':row[0],'updated_at':row[1]} if row else None},ensure_ascii=False).encode())
                    db.execute('INSERT INTO state(name,key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(name,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
                               (NAMESPACE,'model',updated,int(time.time()*1000)))
            elif desktop['format']=='legacy':
                # OpenCode 2 imports this namespace before its first window opens.
                raw=path.read_bytes() if path.exists() else b'{}'
                if len(raw)>MAX_STATE:raise ValueError('Préférences trop volumineuses.')
                value=json.loads(raw.decode('utf-8-sig'))
                if not isinstance(value,dict):raise ValueError('Préférences OpenCode invalides.')
                previous=value.get('model','{}')
                updated=model_state(previous,provider,model)
                if updated==previous:return {'status':'enabled','backup':None}
                if running(desktop['executable']):return {'status':'close_required','backup':None}
                backup=backup_path(path) if path.exists() else None
                if backup:atomic(backup,raw)
                value['model']=updated;atomic(path,json.dumps(value,ensure_ascii=False,indent=2).encode())
            else:return {'status':'manual','backup':None}
        return {'status':'enabled','backup':str(backup) if backup else None}
    except (OSError,ValueError,TypeError,sqlite3.Error,psutil.Error):
        # Configuration was saved separately; report the remaining GUI action honestly.
        return {'status':'manual','backup':None}
