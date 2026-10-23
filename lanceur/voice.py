"""Authenticated, bounded CPU speech service, isolated from Qwen and EG2."""
import json
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from core import ROOT, read_json, write_json, HIDDEN
from phonon_model import SPEC

class VoiceService:
    def __init__(self,home):
        self.home=Path(home);self.path=self.home/'voix.json'
        self.lock=threading.RLock();self.write_lock=threading.Lock();self.slot=threading.Lock()
        self.process=None;self.phase='stopped';self.error='';self.ready=threading.Event()
        self.current=None;self.thread=None
    def settings(self):return read_json(self.path,{'enabled':False})
    def status(self):
        with self.lock:return {'enabled':self.settings()['enabled'],'phase':self.phase,'ready':self.ready.is_set(),
            'engine':'Phonon 0.4.1','language':'fr','voice':SPEC['voice'],'device':'cpu','error':self.error,
            'busy':self.current is not None,'max_text_chars':600,'max_parallel':1}
    def configure(self,enabled):
        if type(enabled) is not bool:raise ValueError('Activation vocale invalide.')
        write_json(self.path,{'enabled':enabled})
        if enabled:self.start()
        else:self.close()
        return self.status()
    def start(self):
        with self.lock:
            if not self.settings()['enabled']:raise ValueError('La voix est désactivée dans la console.')
            if self.process and self.process.poll() is None:return
            executable=ROOT/'toolchain/phonon-server-python/Scripts/python.exe'
            if not executable.exists():raise ValueError('Le moteur vocal serveur n’est pas installé.')
            self.ready.clear();self.phase='loading';self.error=''
            self.process=subprocess.Popen([str(executable),'-X','utf8',str(ROOT/'lanceur/phonon_worker.py')],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                text=True,encoding='utf-8',creationflags=HIDDEN)
            self.thread=threading.Thread(target=self._read,args=(self.process,),daemon=True);self.thread.start()
    def _write(self,value):
        with self.write_lock:
            if not self.process or self.process.poll() is not None:raise OSError('Moteur vocal arrêté.')
            self.process.stdin.write(json.dumps(value,ensure_ascii=False)+'\n');self.process.stdin.flush()
    def _read(self,process):
        try:
            for line in process.stdout:
                if len(line)>65536:raise ValueError('Trame vocale trop volumineuse.')
                value=json.loads(line)
                with self.lock:
                    if process is not self.process:return
                    if value.get('ready'):self.phase='ready';self.ready.set()
                    elif self.current and value.get('id')==self.current['id']:
                        try:self.current['queue'].put_nowait(value)
                        except queue.Full:self.current['cancel'].set();self._write({'action':'cancel','id':self.current['id']})
                        if value.get('done') or value.get('error'):self.current['finished'].set()
                    elif value.get('error'):self.phase='error';self.error=value['error']
        except (OSError,ValueError):pass
        finally:
            with self.lock:
                if process is self.process:
                    self.phase='error';self.error=self.error or 'Le moteur vocal s’est arrêté.';self.ready.clear()
                    if self.current:self.current['cancel'].set();self.current['finished'].set()
    def cancel(self,owner,identifier):
        with self.lock:
            job=self.current
            if job and job['owner']==owner and job['id']==identifier:
                job['cancel'].set();self._write({'action':'cancel','id':identifier})
        return {'cancelled':True}
    def stream(self,owner,value,validate=lambda:True):
        if not isinstance(value,dict) or set(value)-{'request_id','text','stream'}:raise ValueError('Paramètres vocaux invalides.')
        identifier=value.get('request_id');text=value.get('text')
        if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):raise ValueError('Identifiant vocal invalide.')
        if not isinstance(text,str) or not 1<=len(text.strip())<=600:raise ValueError('Texte vocal limité à 600 caractères.')
        if not self.settings()['enabled']:raise ValueError('La voix est désactivée sur le serveur.')
        if not self.ready.is_set():raise ValueError('Le moteur vocal charge encore. Réessayez dans un instant.')
        if not self.slot.acquire(blocking=False):raise BlockingIOError('Le moteur vocal est occupé. Réessayez dans un instant.')
        job={'owner':owner,'id':identifier,'queue':queue.Queue(maxsize=64),'cancel':threading.Event(),'finished':threading.Event()}
        try:
            with self.lock:self.current=job
            self._write({'action':'speak','id':identifier,'text':text})
        except Exception:
            with self.lock:self.current=None
            self.slot.release();raise
        def frames():
            deadline=time.monotonic()+90
            last_frame=time.monotonic()
            try:
                while not job['cancel'].is_set() and time.monotonic()<deadline:
                    if not validate():raise PermissionError('Accès vocal révoqué.')
                    try:frame=job['queue'].get(timeout=.25)
                    except queue.Empty:
                        if job['finished'].is_set():break
                        if time.monotonic()-last_frame>=5:
                            yield {'id':identifier,'waiting':True}
                            last_frame=time.monotonic()
                        continue
                    yield frame
                    last_frame=time.monotonic()
                    if frame.get('done') or frame.get('error'):return
                yield {'id':identifier,'done':True,'cancelled':True}
            finally:
                if not job['finished'].is_set():
                    try:self.cancel(owner,identifier)
                    except OSError:pass
                    job['finished'].wait(timeout=3)
                with self.lock:
                    if self.current is job:self.current=None
                self.slot.release()
        return frames()
    def close(self):
        with self.lock:
            process=self.process;self.process=None;self.ready.clear();self.phase='stopped'
            if self.current:self.current['cancel'].set();self.current['finished'].set()
        if process:
            try:process.stdin.close();process.wait(timeout=3)
            except (OSError,subprocess.TimeoutExpired):
                if process.poll() is None:process.terminate();process.wait(timeout=5)
