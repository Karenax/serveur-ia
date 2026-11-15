"""Authenticated request context between Kiara and the loopback Agent service."""

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time


def _encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _decode(value):
    return base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)


def issue(secret, method, target, operator, *, now=None):
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError('Clé de liaison Agent invalide')
    packet = {'method': method, 'target': target, 'operator': operator,
              'time': int(time.time() if now is None else now), 'nonce': secrets.token_hex(16)}
    payload = _encode(json.dumps(packet, separators=(',', ':'), sort_keys=True).encode('utf-8'))
    signature = _encode(hmac.digest(secret, payload.encode('ascii'), hashlib.sha256))
    return payload + '.' + signature


class Verifier:
    def __init__(self, secret, *, window=60, capacity=100000):
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError('Clé de liaison Agent invalide')
        self.secret = secret
        self.window = window
        self.capacity = capacity
        self.seen = {}
        self.lock = threading.Lock()

    def verify(self, token, method, target, *, now=None):
        current = int(time.time() if now is None else now)
        if not isinstance(token, str) or len(token) > 16384:
            raise ValueError('Identité Agent invalide')
        try:
            payload, signature = token.split('.')
            expected = hmac.digest(self.secret, payload.encode('ascii'), hashlib.sha256)
            if not hmac.compare_digest(_decode(signature), expected):
                raise ValueError('Signature invalide')
            packet = json.loads(_decode(payload))
            if (not isinstance(packet, dict) or packet.get('method') != method
                    or packet.get('target') != target or type(packet.get('time')) is not int
                    or abs(current - packet['time']) > self.window):
                raise ValueError('Requête expirée ou différente')
            nonce = packet.get('nonce')
            if not isinstance(nonce, str) or len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
                raise ValueError('Identifiant de requête invalide')
            operator = packet['operator']
            if not isinstance(operator, dict) or set(operator) != {'id', 'role', 'project_ids', 'person_id'}:
                raise ValueError('Opérateur invalide')
            ids = operator['project_ids']
            if (not isinstance(operator['id'], str) or not 1 <= len(operator['id']) <= 128
                    or operator['role'] not in ('owner', 'editor', 'reader')
                    or (ids is not None and (not isinstance(ids, list) or len(ids) > 1000
                        or any(not isinstance(item, str) or not 1 <= len(item) <= 128 for item in ids)))
                    or (operator['person_id'] is not None and (not isinstance(operator['person_id'], str)
                        or not 1 <= len(operator['person_id']) <= 36))):
                raise ValueError('Opérateur invalide')
        except (KeyError, TypeError, UnicodeError, ValueError) as exc:
            raise ValueError('Identité Agent invalide') from exc
        with self.lock:
            self.seen = {key: expiry for key, expiry in self.seen.items() if expiry >= current}
            if nonce in self.seen or len(self.seen) >= self.capacity:
                raise ValueError('Requête Agent déjà reçue ou capacité atteinte')
            self.seen[nonce] = packet['time'] + self.window
        return operator
