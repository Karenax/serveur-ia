"""Password accounts bound to issued devices, with expiring in-memory sessions."""
import hashlib
import hmac
import re
import secrets
import threading
import time
from core import read_json, write_json

class Accounts:
    def __init__(self, home):
        self.path=home/'comptes.json'
        self.lock=threading.RLock()
        self.sessions={};self.failures={}
        self._dummy=None

    @property
    def dummy(self):
        # This compatibility layer no longer authenticates the current clients.
        # Retain its timing protection only when a legacy login actually uses it.
        with self.lock:
            if self._dummy is None:self._dummy=hashlib.scrypt(b'dummy',salt=bytes(16),n=16384,r=8,p=1).hex()
            return self._dummy

    def metadata(self):
        with self.lock:
            return [{k:v for k,v in account.items() if k not in ('salt','password_hash')} for account in read_json(self.path,[])]

    def configure(self, data, clients):
        identity=data.get('id');username=data.get('username','')
        if not isinstance(username,str) or not isinstance(data.get('enabled',True),bool):raise ValueError('Compte invalide.')
        username=username.strip().casefold()
        password=data.get('password','')
        if not any(c['id']==identity and not c['revoked'] for c in clients):raise ValueError('Client inconnu ou révoqué.')
        if not isinstance(username,str) or not re.fullmatch(r'[a-z0-9_.@-]{3,80}',username):raise ValueError('Identifiant : 3–80 lettres, chiffres, . _ @ ou -.')
        if not isinstance(password,str) or (password and not 12<=len(password)<=256):raise ValueError('Mot de passe : 12–256 caractères.')
        with self.lock:
            accounts=read_json(self.path,[])
            if any(a['username']==username and a['id']!=identity for a in accounts):raise ValueError('Identifiant déjà utilisé.')
            old=next((a for a in accounts if a['id']==identity),None)
            if old is None and not password:raise ValueError('Un mot de passe est nécessaire pour créer le compte.')
            record=dict(old or {'id':identity});record.update(username=username,enabled=bool(data.get('enabled',True)))
            if password:
                salt=secrets.token_bytes(16)
                record.update(salt=salt.hex(),password_hash=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1).hex())
            write_json(self.path,[a for a in accounts if a['id']!=identity]+[record])
            self.invalidate(identity)
        return self.metadata()

    def invalidate(self, identity):
        with self.lock:
            self.sessions={token:s for token,s in self.sessions.items() if s['id']!=identity}

    def login(self, identity, username, password):
        if not isinstance(username,str) or not isinstance(password,str) or len(username)>80 or len(password)>256:raise ValueError('Identifiant ou mot de passe incorrect.')
        with self.lock:
            now=time.time();attempts=[t for t in self.failures.get(identity,[]) if now-t<300]
            if len(attempts)>=5:raise ValueError('Trop de tentatives. Attendre cinq minutes.')
            record=next((a for a in read_json(self.path,[]) if a['id']==identity and a['username']==username.strip().casefold() and a.get('enabled')),None)
            computed=hashlib.scrypt(password.encode(),salt=bytes.fromhex(record['salt']) if record else bytes(16),n=16384,r=8,p=1).hex()
            if not hmac.compare_digest(computed,record['password_hash'] if record else self.dummy) or record is None:
                self.failures[identity]=attempts+[now];raise ValueError('Identifiant ou mot de passe incorrect, ou compte non configuré.')
            self.failures.pop(identity,None)
            self.sessions={t:s for t,s in self.sessions.items() if s['expires']>now}
            own=[t for t,s in self.sessions.items() if s['id']==identity]
            for token in own[:-3]:self.sessions.pop(token,None)
            token=secrets.token_urlsafe(32)
            self.sessions[hashlib.sha256(token.encode()).hexdigest()]={'id':identity,'expires':now+12*3600,'username':record['username']}
            return {'session':token,'username':record['username'],'expires_epoch':now+12*3600}

    def valid(self, identity, token):
        if not isinstance(token,str) or not 32<=len(token)<=128:return False
        with self.lock:
            record=self.sessions.get(hashlib.sha256(token.encode()).hexdigest())
            return bool(record and record['id']==identity and record['expires']>time.time())

    def logout(self, token):
        with self.lock:self.sessions.pop(hashlib.sha256(token.encode()).hexdigest(),None)
