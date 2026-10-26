"""Server-owned history with an encrypted offline cache and optimistic merging."""
import copy
import hashlib
import json
import secrets
import threading
import urllib.error
from pathlib import Path
import history_store

def fingerprints(history):
    return {row['id']:hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            for row in history['conversations']}

def authoritative_turns(local, server):
    """Replace a cached partial turn by its server result without copying the chat.

    A matching turn id authorizes only the assistant result. User messages and
    conversation scope must still agree; unrelated simultaneous edits keep the
    existing conflict-copy behavior.
    """
    if any(local.get(k) != server.get(k) for k in ('id', 'project_id', 'document_id', 'archived', 'model')):
        return None
    left, right = local['messages'], server['messages']
    if len(left) > len(right): return None
    changed = False
    for index, message in enumerate(left):
        target = right[index]
        if message == target: continue
        same_turn = message.get('turn_id') and message.get('turn_id') == target.get('turn_id')
        if same_turn and message['role'] == target['role'] == 'assistant' and not target.get('interrupted'):
            changed = True; continue
        normalized = {k:v for k,v in message.items() if not ((k=='reasoning_content' and not v) or (k=='interrupted' and not v))}
        other = {k:v for k,v in target.items() if not ((k=='reasoning_content' and not v) or (k=='interrupted' and not v))}
        if normalized != other: return None
    for index in range(len(left),len(right)):
        message=right[index]
        if message['role']!='assistant' or not message.get('turn_id') or index==0 or right[index-1].get('turn_id')!=message['turn_id'] or right[index-1]['role']!='user':
            return None
        changed=True
    if not changed:return None
    return {**copy.deepcopy(local), 'messages':copy.deepcopy(right)}

def merge(local,server,base):
    """Keep independent edits; conflicting messages become a separate conversation."""
    left={r['id']:r for r in local['conversations']};right={r['id']:r for r in server['conversations']}
    lh=fingerprints(local);rh=fingerprints(server);rows=[];current=local['currentId'];conflicts=0
    for identity in dict.fromkeys([*left,*right]):
        l=left.get(identity);r=right.get(identity);before=base.get(identity)
        if l==r:
            if l is not None:rows.append(copy.deepcopy(l))
        elif before and lh.get(identity)==before:
            if r is not None:rows.append(copy.deepcopy(r))
        elif before and rh.get(identity)==before:
            if l is not None:rows.append(copy.deepcopy(l))
        elif l is None:
            if r is not None:rows.append(copy.deepcopy(r))
        elif r is None:rows.append(copy.deepcopy(l))
        else:
            reconciled=authoritative_turns(l,r)
            if reconciled is not None:
                rows.append(reconciled);continue
            rows.append(copy.deepcopy(r));branch=copy.deepcopy(l);branch['id']=secrets.token_hex(16)
            branch['title']=branch['title'][:103]+' (copie locale)';branch.pop('server_revision',None)
            rows.append(branch);conflicts+=1
            if current==identity:current=branch['id']
    if not rows:raise history_store.HistoryError('Conserver au moins une conversation.')
    if current not in {r['id'] for r in rows}:current=rows[0]['id']
    return history_store.validate({'conversations':rows,'currentId':current}),conflicts

class HistorySync:
    def __init__(self,remote,path,protect):
        self.remote=remote;self.path=Path(path);self.meta_path=self.path.with_suffix('.sync.dpapi');self.protect=protect
        self.lock=threading.RLock();self.worker_lock=threading.Lock();self.worker=None
        self.reset_path=self.path.with_suffix('.reset-id')
        with history_store.LOCK,history_store.locked(self.path):
            from history_migrations import migrate_cache
            quarantined=migrate_cache(self.path,self.meta_path,self.reset_path,protect)
        try:self.meta=json.loads(protect(self.meta_path.read_bytes(),decrypt=True))
        except (OSError,ValueError):self.meta={}
        if not isinstance(self.meta,dict) or not isinstance(self.meta.get('base',{}),dict):self.meta={}
        self.meta['reset_id']=history_store.HISTORY_RESET_ID
        self.result={'server_synced':False,'pending':True,'message':'Copie locale chargée · connexion au serveur nécessaire.'}
        if quarantined:self.result['message']='Ancien historique conservé dans une copie de récupération · connexion au serveur nécessaire.'

    def status(self):return dict(self.result)

    def read(self):return {**history_store.read(self.path,self.protect),**self.status()}

    def write(self,history,revision):
        with self.lock:
            result=history_store.write(self.path,self.protect,history,revision)
            self.result={'server_synced':False,'pending':True,'message':'Copie locale chiffrée enregistrée · synchronisation en attente.'}
        self.schedule();return {**result,**self.status()}

    def api(self,body=None):
        with self.remote.activity_lock:self.remote.active_requests+=1
        try:
            with self.remote.open('/v1/history',json.dumps(body,ensure_ascii=False).encode() if body is not None else None) as response:return json.load(response)
        finally:
            with self.remote.activity_lock:self.remote.active_requests-=1

    def remember(self,history,local_revision,server_revision,generation=None):
        self.meta={'server_revision':server_revision,'local_revision':local_revision,'base':fingerprints(history),'reset_id':history_store.HISTORY_RESET_ID,'generation':generation or self.meta.get('generation','')}
        history_store.atomic(self.meta_path,self.protect(json.dumps(self.meta,ensure_ascii=False).encode()))

    def synchronize(self,initial=None):
        with self.worker_lock,self.lock:
            try:
                local=history_store.read(self.path,self.protect);server=self.api();history=local['history'];conflicts=0
                if server.get('reset_id')!=history_store.HISTORY_RESET_ID:
                    raise history_store.HistoryError('Mettre à jour le serveur pour utiliser ce client sans profils.')
                if history is not None and server.get('generation') and self.meta.get('generation')!=server['generation'] and (self.meta.get('generation') or server.get('restored')):
                    self.result={'server_synced':False,'pending':True,'needs_merge':True,'requires_restore_ack':True,'message':'État serveur différent : confirmer sa reprise. Votre copie locale sera conservée.'}
                    return {**local,**self.status()}
                if history is None:
                    # A fresh empty placeholder must never replace an existing server history.
                    history=server['history'] or history_store.validate(initial)
                    if server['history'] and initial and any(r.get('messages') for r in initial.get('conversations',[])):
                        history,conflicts=merge(history_store.validate(initial),server['history'],{})
                elif server['history'] and local['revision']!=self.meta.get('local_revision'):
                    if server['revision']!=self.meta.get('server_revision'):
                        history,conflicts=merge(history,server['history'],self.meta.get('base',{}))
                elif server['history']:history=server['history']
                if history!=server['history']:
                    saved=self.api({'history':history,'revision':server['revision'],'reset_id':history_store.HISTORY_RESET_ID,'generation':server.get('generation','')});server['revision']=saved['revision']
                if history!=local['history']:
                    local=history_store.write(self.path,self.protect,history,local['revision'])
                self.remember(history,local['revision'],server['revision'],server.get('generation',''))
                self.result={'server_synced':True,'pending':False,'message':'Historique enregistré sur le serveur · copie locale chiffrée.','merged':conflicts}
                return {'history':history,'revision':local['revision'],**self.status()}
            except Exception as error:
                self.result={'server_synced':False,'pending':True,'message':'Copie locale conservée · '+str(error)}
                raise

    def available(self):
        return self.remote.connected or (getattr(self.remote,'reachable',False) and getattr(self.remote,'code','') in ('model_unloaded','no_models'))

    def acknowledge_restore(self,confirmed=False):
        if confirmed is not True:raise history_store.HistoryError('Confirmez la reprise de l’historique du serveur.')
        with self.worker_lock,self.lock:
            local=history_store.read(self.path,self.protect);server=self.api()
            if server.get('reset_id')!=history_store.HISTORY_RESET_ID or not server.get('generation'):
                raise history_store.HistoryError('État de reprise serveur incompatible.')
            if not self.result.get('requires_restore_ack'):raise history_store.HistoryError('Aucune reprise à confirmer ; resynchronisez le client.')
            backup=self.path.with_name(self.path.stem+'.avant-restauration-'+secrets.token_hex(6)+'.dpapi')
            if self.path.exists():history_store.atomic(backup,self.path.read_bytes())
            history=server['history'] or {'conversations':[{'id':secrets.token_hex(16),'title':'Nouvelle conversation','messages':[]}],'currentId':''}
            if not history['currentId']:history['currentId']=history['conversations'][0]['id']
            saved=history_store.write(self.path,self.protect,history,local['revision'])
            self.remember(history,saved['revision'],server['revision'],server['generation'])
            self.result={'server_synced':True,'pending':False,'message':'Historique serveur repris ; copie précédente chiffrée conservée.','restore_backup':str(backup)}
            return {'history':history,'revision':saved['revision'],**self.status()}

    def schedule(self):
        if not self.available() or 'server_revision' not in self.meta or self.result.get('needs_merge'):return
        if not self.worker_lock.acquire(blocking=False):return
        def work():
            try:
                while self.available():
                    with self.lock:
                        local=history_store.read(self.path,self.protect);revision=self.meta['server_revision']
                        if not local['history'] or local['revision']==self.meta.get('local_revision'):break
                    # Writes can continue in the encrypted cache during an upload.
                    saved=self.api({'history':local['history'],'revision':revision,'reset_id':history_store.HISTORY_RESET_ID,'generation':self.meta.get('generation','')})
                    with self.lock:
                        self.remember(local['history'],local['revision'],saved['revision'])
                        latest=history_store.read(self.path,self.protect)
                        pending=latest['revision']!=local['revision']
                        self.result={'server_synced':not pending,'pending':pending,'message':'Synchronisation en cours…' if pending else 'Historique enregistré sur le serveur · copie locale chiffrée.'}
            except Exception as error:
                self.result={'server_synced':False,'pending':True,'needs_merge':isinstance(error,urllib.error.HTTPError) and error.code==409,'message':'Copie locale conservée · synchronisation en attente : '+str(error)}
            finally:self.worker_lock.release()
        self.worker=threading.Thread(target=work,daemon=True);self.worker.start()

    def flush(self):
        self.schedule()
        worker=self.worker
        if worker and worker.is_alive():worker.join(timeout=5)
        return self.status()
