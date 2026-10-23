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

ACTIVE={'installing','loading','listening','stopping','finishing','cancelling'}
class ConversationService:
    def __init__(self,resources,cache=None,*,mode='conversation'):
        self.mode=mode
        self.resources=Path(resources);self.spec=json.loads((self.resources/'conversation-models.json').read_text(encoding='utf-8'))
        self.cache=Path(cache) if cache else Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'QwenClient/asr'
        self.lock=threading.RLock();self.process=None;self.thread=None;self.cancelled=threading.Event()
        self.value={'phase':'idle','session':'','partial':'','text':'','turns':[]};self.closed=False;self.finishing=False
        self.mute_requested=False
    def installed(self):
        return all((self.cache/f['name']).is_file() and (self.cache/f['name']).stat().st_size==f['bytes'] for f in self.spec['files'])
    def status(self):
        with self.lock:return {**self.value,'installed':self.installed(),'model':self.spec.get('asr','Parakeet v3'),'model_bytes':sum(f['bytes'] for f in self.spec['files']),'local':True}
    def _verify(self):
        for item in self.spec['files']:
            with (self.cache/item['name']).open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=item['sha256']:raise ValueError('Modèle de conversation corrompu. Réinstallez-le.')
    def _send(self,value):
        if self.process and self.process.poll() is None:
            self.process.stdin.write(json.dumps(value)+'\n');self.process.stdin.flush()
    def action(self,value):
        if not isinstance(value,dict) or set(value)-{'action','session','turn','muted'}:raise ValueError('Commande de conversation invalide.')
        command=value.get('action')
        if 'muted' in value and command!='mute':raise ValueError('Commande de microphone invalide.')
        with self.lock:
            if self.closed:raise ValueError('Client en cours de fermeture.')
            if command in ('stop','cancel','ack','mute'):
                if not value.get('session') or value['session']!=self.value['session']:raise ValueError('Cette session vocale est terminée.')
                if command=='mute':
                    if self.mode!='conversation' or self.value['phase'] not in ('loading','listening') or type(value.get('muted')) is not bool:
                        raise ValueError('Le microphone peut être coupé pendant une conversation active.')
                    self.mute_requested=value['muted'];self.value['mute_pending']=True
                    self._send({'action':'mute','muted':self.mute_requested})
                elif command=='ack':
                    if self.mode!='conversation':raise ValueError('Commande vocale invalide.')
                    if type(value.get('turn')) is not int or value['turn']<1:raise ValueError('Tour vocal invalide.')
                    self._send({'action':'ack','turn':value['turn']})
                elif command=='stop' and self.mode=='dictation':
                    self.finishing=True;self.value['phase']='finishing';self._send({'action':'finish'})
                    if not self.thread or not self.thread.is_alive():self.value['phase']='ready'
                else:
                    self.cancelled.set();self.value['phase']='cancelling' if self.mode=='dictation' else 'stopping';self._send({'action':'stop'})
                    if not self.thread or not self.thread.is_alive():self.value.update(phase='cancelled' if self.mode=='dictation' else 'stopped',partial='',text='',turns=[],muted=False,mute_pending=False,microphone_closed=True)
                return self.status()
            if command not in ('start','install','remove') or command=='remove' and self.mode!='dictation':raise ValueError('Commande de conversation inconnue.')
            if self.value['phase'] in ACTIVE or (self.thread and self.thread.is_alive()):raise ValueError('Une conversation est déjà active.')
            if command=='remove':
                for item in self.spec['files']:
                    path=self.cache/item['name'];path.unlink(missing_ok=True);path.with_suffix(path.suffix+'.part').unlink(missing_ok=True)
                self.value.update(phase='idle',text='',partial='',turns=[],message='Modèle vocal désinstallé.');return self.status()
            if command=='start' and not self.installed():raise ValueError('Installez les modèles de conversation avant de parler.')
            self.cancelled.clear();self.finishing=False;self.mute_requested=False;self.value={'phase':'installing' if command=='install' else 'loading','session':secrets.token_hex(16),'partial':'','text':'','turns':[],'muted':False,'mute_pending':False}
            self.thread=threading.Thread(target=self._install if command=='install' else self._run,daemon=True);self.thread.start()
            return self.status()
    def _install(self):
        try:
            from file_lock import locked
            self.cache.mkdir(parents=True,exist_ok=True)
            with locked(self.cache/'installation'):
                if not self.cancelled.is_set():self._install_locked()
        except (ValueError,OSError) as error:
            with self.lock:self.value.update(phase='error',message=str(error))
        finally:
            if self.cancelled.is_set():
                with self.lock:self.value.update(phase='cancelled' if self.mode=='dictation' else 'stopped',message='Installation arrêtée.')
    def _install_locked(self):
        try:
            self.cache.mkdir(parents=True,exist_ok=True)
            if shutil.disk_usage(self.cache).free<sum(f['bytes'] for f in self.spec['files'])+20*1024*1024:raise OSError('Espace disque insuffisant pour la conversation.')
            opener=urllib.request.build_opener(HTTPSRedirect());downloaded=0
            for item in self.spec['files']:
                path=self.cache/item['name'];part=path.with_suffix(path.suffix+'.part')
                # A repair downloads only missing/corrupt files. Both Windows
                # modes use this same immutable, hash-checked model cache.
                if path.is_file() and path.stat().st_size==item['bytes']:
                    with path.open('rb') as stream:valid=hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256']
                    if valid:
                        downloaded+=item['bytes']
                        with self.lock:self.value['downloaded_bytes']=downloaded
                        continue
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
            command+=['--models',str(self.cache),'--resources',str(self.resources),'--mode',self.mode]
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            with self.lock:
                self.process=process
                if self.cancelled.is_set():self._send({'action':'stop'})
                elif self.finishing:self._send({'action':'finish'})
                elif self.mute_requested:self._send({'action':'mute','muted':True})
            for line in process.stdout:
                if len(line)>128000:raise ValueError('Réponse du moteur vocal trop volumineuse.')
                value=json.loads(line)
                with self.lock:
                    self.value.update(value)
                    if 'muted' in value:self.value['mute_pending']=value['muted']!=self.mute_requested
                    if self.cancelled.is_set() and value.get('phase')=='listening':self.value['phase']='cancelling' if self.mode=='dictation' else 'stopping'
                    elif self.finishing and value.get('phase')=='listening':self.value['phase']='finishing'
            process.wait(timeout=3)
            with self.lock:
                if self.value['phase'] not in ('error','stopped','ready'):self.value.update(phase='error',message='Le moteur vocal s’est arrêté.')
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
                with self.lock:self.value.update(phase='cancelled' if self.mode=='dictation' else 'stopped',partial='',text='',turns=[],muted=False,mute_pending=False,microphone_closed=True)
    def close(self):
        with self.lock:self.closed=True;self.cancelled.set();self._send({'action':'stop'})
        if self.thread:self.thread.join(timeout=5)
        with self.lock:
            if self.process and self.process.poll() is None:self.process.terminate()


class DictationService(ConversationService):
    """Manual-send dictation, using exactly the conversation ASR and model cache."""
    def __init__(self,resources,cache=None):
        super().__init__(resources,cache,mode='dictation')

    def action(self,value):
        if not isinstance(value,dict) or set(value)-{'action','session'}:
            raise ValueError('Commande vocale invalide.')
        return super().action(value)
