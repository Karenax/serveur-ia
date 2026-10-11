"""Encrypted drafts isolated per window; recover only drafts of exited processes."""
import json
import os
from pathlib import Path
import secrets
import psutil
from file_lock import locked
from history_store import atomic

def validate(draft):
    if draft is None:return
    if not isinstance(draft,dict) or set(draft)!={'id','project','title','text','revision'}:raise ValueError('Brouillon invalide.')
    for key in ('id','project'):
        if not isinstance(draft[key],str) or len(draft[key])!=32 or any(c not in '0123456789abcdef' for c in draft[key]):raise ValueError('Identifiant de brouillon invalide.')
    if not isinstance(draft['title'],str) or len(draft['title'])>180 or not isinstance(draft['text'],str) or len(draft['text'])>500000 or type(draft['revision']) is not int or draft['revision']<1:raise ValueError('Contenu du brouillon invalide.')
    if len(json.dumps(draft,ensure_ascii=False).encode())>2*1024*1024:raise ValueError('Brouillon trop volumineux.')

class DraftStore:
    def __init__(self,settings,protect):
        self.settings=Path(settings);self.protect=protect
        self.prefix=self.settings.stem+'.draft-'
        self.path=self.settings.with_name(self.prefix+secrets.token_hex(16)+'.dpapi')
        self.guard=self.settings.with_suffix('.drafts.lock')
        process=psutil.Process();self.identity={'pid':process.pid,'created':process.create_time()}

    def read_file(self,path):
        if path.stat().st_size>3*1024*1024:raise ValueError('Fichier de brouillon trop volumineux.')
        try:value=json.loads(self.protect(path.read_bytes(),decrypt=True))
        except (ValueError,OSError):raise ValueError('Brouillon illisible : le fichier original est conservé.')
        if value is None:return None
        # Legacy single-file draft, from the first workspace build.
        if isinstance(value,dict) and 'draft' not in value:value={'draft':value}
        if not isinstance(value,dict):raise ValueError('Brouillon illisible.')
        validate(value.get('draft'))
        return value

    @staticmethod
    def active(value):
        try:
            process=psutil.Process(value['pid'])
            return process.is_running() and abs(process.create_time()-value['created'])<.01
        except (ValueError,KeyError,TypeError,psutil.Error):return False

    def read(self):
        with locked(self.guard):
            if self.path.exists():return {'draft':self.read_file(self.path).get('draft')}
            candidates=sorted(self.settings.parent.glob(self.prefix+'*.dpapi'),key=lambda p:p.stat().st_mtime,reverse=True)[:50]
            legacy=self.settings.with_suffix('.draft.dpapi')
            if legacy.exists():candidates.append(legacy)
            for path in candidates:
                value=self.read_file(path)
                if value is None or self.active(value):continue
                # Claim an orphan before exposing it, preventing two windows recovering the same draft.
                os.replace(path,self.path)
                atomic(self.path,self.protect(json.dumps({**self.identity,'draft':value.get('draft')},ensure_ascii=False).encode()))
                return {'draft':value.get('draft')}
            return {'draft':None}

    def write(self,draft):
        validate(draft)
        with locked(self.guard):
            if draft is None:self.path.unlink(missing_ok=True)
            else:atomic(self.path,self.protect(json.dumps({**self.identity,'draft':draft},ensure_ascii=False).encode()))
        return {'saved':True}
