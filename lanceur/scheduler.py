"""Bounded inference queue with priority for interactive requests."""
from collections import deque
import math
import secrets
import re
import threading
import time
from kiara_shared.request_ids import validate_request_id


class BackgroundBudgetReached(ValueError):
    def __init__(self, retry_after):
        super().__init__('Budget horaire des analyses de projet atteint.')
        self.retry_after = retry_after


class Scheduler:
    def __init__(self, capacity=16, background_budget_seconds=15 * 60):
        self.capacity = capacity
        self.background_budget_seconds = background_budget_seconds
        self.background_calls = deque()
        self.condition = threading.Condition()
        self.requests = []
        self.completed = 0
        self.succeeded = 0
        self.failed = 0
        self.cancelled = 0
        self.last_seconds = None
        self.last_tokens_per_second = None

    def _check_background_budget(self):
        now = time.monotonic()
        cutoff = now - 3600
        while self.background_calls and self.background_calls[0][1] <= cutoff:
            self.background_calls.popleft()
        used = sum(end - max(start, cutoff) for start, end in self.background_calls)
        excess = used - self.background_budget_seconds
        if excess < 0:
            return
        for start, end in self.background_calls:
            left = max(start, cutoff)
            if excess < end - left:
                raise BackgroundBudgetReached(math.floor(left + excess - cutoff) + 1)
            excess -= end - left
        raise BackgroundBudgetReached(3600)

    def submit(self, owner, request_id=None, concurrent=False, *, background=False, budgeted=False):
        if request_id is not None:validate_request_id(request_id)
        with self.condition:
            owned = [r for r in self.requests if r['owner'] == owner]
            if owned and (not concurrent or len(owned) >= 4 or any(not r.get('concurrent') for r in owned)):
                raise ValueError('Une demande de ce client est déjà en cours ou en attente.')
            if len(self.requests) >= self.capacity:
                raise ValueError('La file est pleine. Réessayer plus tard.')
            if request_id and any(r['id'] == request_id and r['owner'] == owner for r in self.requests):
                raise ValueError('Identifiant de demande déjà utilisé.')
            if budgeted:
                self._check_background_budget()
            item = {'id': request_id or secrets.token_hex(16), 'owner': owner, 'created': time.time(), 'started': None,
                    'cancelled': False, 'concurrent': concurrent, 'background': background or budgeted, 'budgeted': budgeted}
            index = len(self.requests)
            if not item['background']:
                index = next((i for i, pending in enumerate(self.requests)
                              if pending['started'] is None and pending['background']), index)
            self.requests.insert(index, item)
            self.condition.notify_all()
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
                    if item['budgeted']:
                        item['budget_started'] = time.monotonic()
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
                if 'budget_started' in item:
                    self.background_calls.append((item.pop('budget_started'), time.monotonic()))
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
