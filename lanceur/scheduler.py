"""Bounded FIFO inference queue, at most one request per identity."""
import secrets
import re
import threading
import time
from kiara_shared.request_ids import validate_request_id

class Scheduler:
    def __init__(self, capacity=16):
        self.capacity = capacity
        self.condition = threading.Condition()
        self.requests = []
        self.completed = 0
        self.succeeded = 0
        self.failed = 0
        self.cancelled = 0
        self.last_seconds = None
        self.last_tokens_per_second = None

    def submit(self, owner, request_id=None, background=False):
        if request_id is not None:validate_request_id(request_id)
        with self.condition:
            if any(r['owner'] == owner and (not r.get('background') or r['started'] is not None or background) for r in self.requests):
                raise ValueError('Une demande de ce client est déjà en cours ou en attente.')
            if len(self.requests) >= self.capacity:
                raise ValueError('La file est pleine. Réessayer plus tard.')
            item = {'id': request_id or secrets.token_hex(16), 'owner': owner, 'created': time.time(), 'started': None, 'cancelled': False, 'background':background}
            position=next((i for i,r in enumerate(self.requests) if r.get('background') and r['started'] is None),len(self.requests)) if not background else len(self.requests)
            self.requests.insert(position,item)
            return item

    def position(self, item):
        with self.condition:
            return self.requests.index(item) if item in self.requests else -1

    def cancel(self, owner, request_id=None):
        with self.condition:
            for item in list(self.requests):
                if item['owner'] == owner and (request_id is None or item['id']==request_id):
                    item['cancelled'] = True
                    if item.get('abort'):
                        item['abort']()
                    if item['started'] is None:
                        self.requests.remove(item)
                        self.cancelled += 1
            self.condition.notify_all()

    def wait(self, item, valid, heartbeat):
        deadline = time.monotonic() + 900
        while True:
            if not valid():
                raise ValueError('Accès désactivé.')
            with self.condition:
                if item['cancelled']:
                    raise ValueError('Demande annulée ou accès désactivé.')
                if self.requests and self.requests[0] is item:
                    item['started'] = time.time()
                    item['progress'] = item['started']
                    return
                if time.monotonic() >= deadline:
                    raise ValueError('Attente maximale de 15 minutes dépassée.')
                position = self.position(item)
            heartbeat(position)
            with self.condition:
                self.condition.wait(1)

    def progress(self,item):
        with self.condition:item['progress']=time.time()

    def expire(self):
        with self.condition:
            for item in list(self.requests):
                if item['started'] and (time.time()-item.get('progress',item['started'])>120 or time.time()-item['started']>900):
                    self.cancel(item['owner'],item['id'])

    def finish(self, item):
        with self.condition:
            if item in self.requests:
                self.requests.remove(item)
            if item['started']:
                self.completed += 1
                if item['cancelled']: self.cancelled += 1
                elif item.get('succeeded'): self.succeeded += 1
                else: self.failed += 1
                self.last_seconds = round(time.time() - item['started'], 2)
            self.condition.notify_all()

    def snapshot(self, owner=None):
        with self.condition:
            return {'active': sum(r['started'] is not None for r in self.requests),
                    'waiting': sum(r['started'] is None for r in self.requests),
                    'completed': self.completed, 'succeeded':self.succeeded, 'failed':self.failed, 'cancelled':self.cancelled,
                    'last_seconds': self.last_seconds, 'tokens_per_second':self.last_tokens_per_second,
                    'requests': [{'id': r['id'], 'position': i, 'started': r['started'], 'cancelled': r['cancelled']}
                                 for i, r in enumerate(self.requests) if owner is None or r['owner'] == owner]}
