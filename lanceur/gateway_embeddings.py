"""Bounded authenticated public embedding adapter."""
import json
import http.client
from collections import deque
import threading
import time
from kiara_shared.http import json_body
from workspace_types import Conflict, Denied


class EmbeddingQueue:
    """One active public request and at most 16 FIFO waiters."""
    def __init__(self, capacity=16):
        self.capacity = capacity
        self.condition = threading.Condition()
        self.waiters = deque()
        self.active = False

    def acquire(self, timeout=30):
        deadline = time.monotonic() + timeout
        ticket = object()
        with self.condition:
            if not self.active and not self.waiters:
                self.active = True
                return True
            if len(self.waiters) >= self.capacity:
                return False
            self.waiters.append(ticket)
            self.condition.notify_all()
            try:
                while self.active or self.waiters[0] is not ticket:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    self.condition.wait(remaining)
                self.active = True
                return True
            finally:
                self.waiters.remove(ticket)
                self.condition.notify_all()

    def release(self):
        with self.condition:
            if not self.active:
                raise RuntimeError('No active embedding request')
            self.active = False
            self.condition.notify_all()

def handle(handler,store):
    if not handler.authorized():
        return
    from public_embeddings import request, response
    try:
        texts, encoding, mode = request(json_body(handler, 2 * 1024 * 1024))
    except (ValueError, TypeError):
        return handler.respond(400, {'error': {'message': 'Requête embeddings invalide : modèle google/embeddinggemma-2, 1 à 32 textes de 4500 caractères, 768 dimensions, float/base64.'}})
    if not store.embedding_queue.acquire(timeout=30):
        return handler.respond(429, {'error': {'message': 'File EG2 pleine ou délai d’attente dépassé. Réessayez dans un instant.'}})
    try:
        if store.authenticate(handler.access_token) != handler.identity:
            raise Denied('Accès désactivé.')
        engine = getattr(getattr(store.workspace, 'knowledge', None), 'engine', None)
        if engine is None:
            raise ValueError('EG2 indisponible.')
        result = response(engine, texts, encoding, mode)
        if store.authenticate(handler.access_token) != handler.identity:
            raise Denied('Accès désactivé.')
        return handler.respond(200, result)
    except Denied:
        return handler.respond(403, {'error': {'message': 'Accès désactivé.'}})
    except (OSError, ValueError, RuntimeError, http.client.HTTPException):
        return handler.respond(503, {'error': {'message': 'EmbeddingGemma 2 indisponible ou occupé. Réessayez plus tard.'}})
    finally:
        store.embedding_queue.release()

