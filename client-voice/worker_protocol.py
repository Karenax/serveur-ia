"""Bounded stdin/cancellation protocol shared by voice pack generations."""
from collections import OrderedDict
import json
import queue
import re
import sys
import threading


class CommandInbox:
    def __init__(self,engine,stream=None):
        self.engine=engine
        self.stream=stream if stream is not None else sys.stdin
        self.commands=queue.Queue(maxsize=1)
        self.cancelled=OrderedDict()
        self.stop=threading.Event()
        self.closed=threading.Event()
        self.guard=threading.Lock()
        self.current=None

    def accept(self,value):
        if not isinstance(value,dict):raise ValueError('Commande vocale invalide.')
        identity=value.get('id')
        if not isinstance(identity,str) or not re.fullmatch('[a-f0-9]{32}',identity):
            raise ValueError('Identifiant vocal invalide.')
        if value.get('action')=='cancel':
            with self.guard:
                self.cancelled[identity]=True
                while len(self.cancelled)>64:self.cancelled.popitem(last=False)
                if self.current==identity:self.stop.set()
        elif value.get('action')==('transcribe' if self.engine=='asr' else 'speak'):
            self.commands.put_nowait(value)
        else:raise ValueError('Commande vocale invalide.')

    def read(self):
        try:
            while line:=self.stream.readline(1300002):
                if len(line)>1300000:raise ValueError('Commande vocale trop volumineuse.')
                self.accept(json.loads(line))
        except (OSError,ValueError,queue.Full):
            pass
        finally:
            self.closed.set();self.stop.set()
            try:self.commands.put_nowait(None)
            except queue.Full:pass

    def start(self):
        threading.Thread(target=self.read,daemon=True,name='kiara-voice-commands').start()

    def begin(self,identity):
        with self.guard:
            self.current=identity
            self.stop.clear()
            if self.closed.is_set() or identity in self.cancelled:self.stop.set()

    def finish(self):
        with self.guard:self.current=None
