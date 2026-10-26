"""Bounded diagnostics containing metadata only, never worker output or prompts."""
from collections import defaultdict, deque
import json
from pathlib import Path
import re
import secrets
import threading
import time

SAFE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}\Z')
ERRORS = re.compile(rb'(ImportError|ModuleNotFoundError|FileNotFoundError|PermissionError|MemoryError|RuntimeError|ValueError|OSError):')


class Metrics:
    def __init__(self):
        self.lock=threading.Lock()
        self.samples=defaultdict(lambda:deque(maxlen=256))
        self.counts=defaultdict(int)

    def observe(self,name,seconds):
        if not SAFE.fullmatch(name):raise ValueError('Invalid metric name')
        with self.lock:
            self.samples[name].append(max(0,seconds)*1000)
            self.counts[name]+=1

    def snapshot(self):
        with self.lock:
            result={}
            for name,items in self.samples.items():
                values=sorted(items)
                result[name]={'count':self.counts[name],'window':len(values),
                    'p50_ms':round(values[(len(values)-1)//2],3),
                    'p95_ms':round(values[min(len(values)-1,int(len(values)*0.95))],3),
                    'max_ms':round(values[-1],3)}
            return result


class Diagnostics:
    MAX_BYTES=256*1024

    def __init__(self,home):
        self.directory=Path(home)/'diagnostics'
        self.path=self.directory/'runtime.jsonl'
        self.lock=threading.RLock()
        self.fallback=deque(maxlen=16)

    def record(self,component,operation,error=None,*,elapsed=None,exit_code=None,stderr=None):
        if not SAFE.fullmatch(component) or not SAFE.fullmatch(operation):
            raise ValueError('Invalid diagnostic category')
        category=type(error).__name__ if error is not None else 'WorkerError'
        if stderr:
            match=ERRORS.search(stderr[:65536])
            if match:category=match[1].decode('ascii')
        if not SAFE.fullmatch(category):category='Error'
        entry={'time':time.time(),'reference':secrets.token_hex(6),'component':component,
               'operation':operation,'category':category}
        if elapsed is not None:entry['duration_ms']=round(max(0,elapsed)*1000,3)
        if type(exit_code) is int:entry['exit_code']=exit_code
        if stderr is not None:entry['stderr_present']=bool(stderr)
        raw=(json.dumps(entry,separators=(',',':'))+'\n').encode()
        with self.lock:
            try:
                from wg_crypto import private_directory
                private_directory(self.directory)
                if self.path.exists() and self.path.stat().st_size+len(raw)>self.MAX_BYTES:
                    self.path.replace(self.path.with_suffix('.previous.jsonl'))
                with self.path.open('ab') as stream:stream.write(raw)
            except (OSError,ValueError):
                self.fallback.append(entry)
        return entry['reference']

    def recent(self,limit=16):
        with self.lock:
            try:lines=self.path.read_text(encoding='utf-8').splitlines()[-min(limit,100):]
            except OSError:return list(self.fallback)[-min(limit,100):]
        result=[]
        for line in lines:
            try:result.append(json.loads(line))
            except ValueError:continue
        return (result+list(self.fallback))[-min(limit,100):]


def watch_stderr(process,diagnostics,component):
    """Drain the pipe without storing text; classify the bounded prefix on exit."""
    def read():
        prefix=bytearray()
        try:
            stream=getattr(process,'stderr',None)
            if stream is None:return
            while chunk:=stream.read(4096):
                if isinstance(chunk,str):chunk=chunk.encode('utf-8',errors='replace')
                if not isinstance(chunk,bytes):break
                if len(prefix)<65536:prefix.extend(chunk[:65536-len(prefix)])
            if prefix:diagnostics.record(component,'worker_stderr',stderr=bytes(prefix),exit_code=process.poll())
        except (OSError,ValueError):return
    threading.Thread(target=read,daemon=True,name='kiara-worker-diagnostics').start()
