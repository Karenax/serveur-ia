"""Owned, isolated conversation worker and public model installation."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
import urllib.request
from local_voice import HTTPSRedirect

ACTIVE={'installing','loading','listening','stopping'}
class ConversationService:
    def __init__(self,resources,cache=None):
        self.resources=Path(resources);self.spec=json.loads((self.resources/'conversation-models.json').read_text(encoding='utf-8'))
        self.cache=Path(cache) if cache else Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'QwenClient/conversation'
        self.lock=threading.RLock();self.process=None;self.thread=None;self.cancelled=threading.Event()
        self.value={'phase':'idle','session':'','partial':'','turns':[]};self.closed=False
    def installed(self):
        return all((self.cache/f['name']).is_file() and (self.cache/f['name']).stat().st_size==f['bytes'] for f in self.spec['files'])
    def status(self):
        with self.lock:return {**self.value,'installed':self.installed(),'model_bytes':sum(f['bytes'] for f in self.spec['files']),'local':True}
    def _verify(self):
        for item in self.spec['files']:
            with (self.cache/item['name']).open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=item['sha256']:raise ValueError('Modèle de conversation corrompu. Réinstallez-le.')
    def _send(self,value):
        if self.process and self.process.poll() is None:
            self.process.stdin.write(json.dumps(value)+'\n');self.process.stdin.flush()
    def action(self,value):
        if not isinstance(value,dict) or set(value)-{'action','session','turn'}:raise ValueError('Commande de conversation invalide.')
        command=value.get('action')
        with self.lock:
            if self.closed:raise ValueError('Client en cours de fermeture.')
            if command in ('stop','ack'):
                if not value.get('session') or value['session']!=self.value['session']:raise ValueError('Cette session vocale est terminée.')
                if command=='ack':
                    if type(value.get('turn')) is not int or value['turn']<1:raise ValueError('Tour vocal invalide.')
                    self._send({'action':'ack','turn':value['turn']})
                else:
                    self.cancelled.set();self.value['phase']='stopping';self._send({'action':'stop'})
                    if not self.thread or not self.thread.is_alive():self.value.update(phase='stopped',partial='',turns=[])
                return self.status()
            if command not in ('start','install'):raise ValueError('Commande de conversation inconnue.')
            if self.value['phase'] in ACTIVE or (self.thread and self.thread.is_alive()):raise ValueError('Une conversation est déjà active.')
            if command=='start' and not self.installed():raise ValueError('Installez les modèles de conversation avant de parler.')
            self.cancelled.clear();self.value={'phase':'installing' if command=='install' else 'loading','session':secrets.token_hex(16),'partial':'','turns':[]}
            self.thread=threading.Thread(target=self._install if command=='install' else self._run,daemon=True);self.thread.start()
            return self.status()
    def _install(self):
        try:
            self.cache.mkdir(parents=True,exist_ok=True)
            if shutil.disk_usage(self.cache).free<sum(f['bytes'] for f in self.spec['files'])+20*1024*1024:raise OSError('Espace disque insuffisant pour la conversation.')
            opener=urllib.request.build_opener(HTTPSRedirect());downloaded=0
            for item in self.spec['files']:
                path=self.cache/item['name'];part=path.with_suffix(path.suffix+'.part')
                with opener.open(item['url'],timeout=30) as source,part.open('wb') as output:
                    digest=hashlib.sha256();size=0
                    while block:=source.read(256*1024):
                        if self.cancelled.is_set():return
                        size+=len(block)
                        if size>item['bytes']:raise ValueError('Téléchargement de modèle trop volumineux.')
                        output.write(block);digest.update(block)
                        with self.lock:self.value['downloaded_bytes']=downloaded+size
                if size!=item['bytes'] or digest.hexdigest()!=item['sha256']:raise ValueError('Le modèle téléchargé ne correspond pas à son empreinte.')
                os.replace(part,path);downloaded+=size
            with self.lock:self.value.update(phase='idle',message='Conversation installée.')
        except Exception as error:
            with self.lock:self.value.update(phase='error',message=str(error) if isinstance(error,(ValueError,OSError)) else 'Installation de conversation impossible.')
        finally:
            if self.cancelled.is_set():
                with self.lock:self.value.update(phase='stopped',message='Installation arrêtée.')
    def _run(self):
        try:
            self._verify()
            if self.cancelled.is_set():return
            executable=self.resources/'conversation-worker/conversation-worker.exe'
            if executable.exists():command=[str(executable)]
            else:
                root=Path(__file__).resolve().parent.parent
                command=[str(root/'toolchain/conversation-client-python/Scripts/python.exe'),'-X','utf8',str(root/'client-voice/conversation_worker.py')]
            command+=['--models',str(self.cache),'--resources',str(self.resources)]
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            with self.lock:
                self.process=process
                if self.cancelled.is_set():self._send({'action':'stop'})
            for line in process.stdout:
                if len(line)>128000:raise ValueError('Réponse du moteur vocal trop volumineuse.')
                value=json.loads(line)
                with self.lock:
                    self.value.update(value)
                    if self.cancelled.is_set() and value.get('phase')=='listening':self.value['phase']='stopping'
            process.wait(timeout=3)
            with self.lock:
                if self.value['phase'] not in ('error','stopped'):self.value.update(phase='error',message='Le moteur vocal s’est arrêté.')
        except Exception as error:
            with self.lock:self.value.update(phase='error',message=str(error) if isinstance(error,(ValueError,OSError)) else 'Conversation indisponible.')
        finally:
            with self.lock:
                process=self.process;self.process=None
            if process and process.poll() is None:
                process.terminate();process.wait(timeout=5)
            if process:
                for pipe in (process.stdin,process.stdout):
                    if pipe:
                        try:pipe.close()
                        except OSError:pass
            if self.cancelled.is_set():
                with self.lock:self.value.update(phase='stopped',partial='',turns=[])
    def close(self):
        with self.lock:self.closed=True;self.cancelled.set();self._send({'action':'stop'})
        if self.thread:self.thread.join(timeout=5)
        with self.lock:
            if self.process and self.process.poll() is None:self.process.terminate()
