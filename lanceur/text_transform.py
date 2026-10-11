"""Fixed French text transformations and bounded, owner-scoped cancellation receipts."""
from collections import OrderedDict
import http.client
import io
import re
import select
import threading
import time


INSTRUCTIONS = {
    'correct': 'Corrige l’orthographe, la grammaire, la conjugaison, les accords et la ponctuation du texte français. Conserve son sens, son registre, ses paragraphes et ses informations. Retourne uniquement le texte corrigé, sans explication ni introduction.',
    'professional': 'Reformule intégralement le texte en français professionnel, clair, poli et naturel. Conserve toutes les informations et le sens exact. N’ajoute aucun fait ni engagement. Respecte les paragraphes utiles. Retourne uniquement le texte reformulé, sans explication ni introduction.',
    'friendly': 'Reformule intégralement le texte en français amical et familier, naturel et chaleureux, avec tutoiement. Corrige aussi l’orthographe et la grammaire. Conserve toutes les informations et le sens exact, sans ajouter de fait ni engagement. Retourne uniquement le texte reformulé, sans explication ni introduction.'
}
REQUEST = re.compile(r'[a-f0-9]{32}')


def transform_request(value):
    """Produce the only messages/settings this route is allowed to send upstream."""
    if set(value) - {'text_transform', 'stream', 'model'}:
        raise ValueError('Paramètre non admis pour la transformation de texte.')
    transform = value.get('text_transform')
    if not isinstance(transform, dict) or set(transform) != {'mode', 'text'}:
        raise ValueError('Mode et texte de transformation attendus.')
    mode = transform['mode']; text = transform['text']
    if not isinstance(mode, str) or mode not in INSTRUCTIONS:
        raise ValueError('Mode de transformation invalide.')
    if not isinstance(text, str) or not text.strip() or len(text) > 100000:
        raise ValueError('Texte attendu, entre 1 et 100000 caractères.')
    if not isinstance(value.get('stream', False), bool):
        raise ValueError('Mode de réponse invalide.')
    return {'messages': [{'role': 'system', 'content': INSTRUCTIONS[mode]},
                         {'role': 'user', 'content': text}],
            'stream': value.get('stream', False),
            'chat_template_kwargs': {'enable_thinking': False}, 'reasoning_effort': 'none'}


class TextTransforms:
    """Remember early cancellation without introducing agent sessions or durable state."""
    def __init__(self, ttl=900, per_owner=128, capacity=8192, clock=time.monotonic):
        self.ttl = ttl; self.per_owner = per_owner; self.capacity = capacity; self.clock = clock
        self.lock = threading.Lock()
        self.receipts = OrderedDict()

    @staticmethod
    def request_id(value):
        if not isinstance(value, str) or not REQUEST.fullmatch(value):
            raise ValueError('Identifiant de demande invalide.')
        return value

    def _prune(self, now):
        while self.receipts:
            key, expiry = next(iter(self.receipts.items()))
            if expiry > now: break
            self.receipts.pop(key)

    def cancel(self, owner, request):
        self.request_id(request)
        with self.lock:
            now = self.clock(); self._prune(now)
            key = (owner, request)
            self.receipts.pop(key, None)
            self.receipts[key] = now + self.ttl
            owned = [key for key in self.receipts if key[0] == owner]
            for key in owned[:-self.per_owner]: self.receipts.pop(key)
            while len(self.receipts) > self.capacity: self.receipts.popitem(last=False)

    def cancelled(self, owner, request):
        with self.lock:
            now = self.clock(); self._prune(now)
            return (owner, request) in self.receipts


class _CancellableReader(io.RawIOBase):
    """Poll before recv: Windows socket shutdown cannot reliably wake a blocked read."""
    def __init__(self, sock, source, valid):
        self.sock = sock; self.source = source; self.valid = valid

    def readable(self): return True

    def readinto(self, buffer):
        deadline = time.monotonic() + 120
        while True:
            if not self.valid(): raise ValueError('Demande annulée ou accès désactivé.')
            if time.monotonic() >= deadline: raise TimeoutError('Le moteur ne répond pas.')
            if select.select([self.sock], [], [], .2)[0]:
                count = self.source.readinto(buffer)
                if not self.valid(): raise ValueError('Demande annulée ou accès désactivé.')
                return count

    def close(self):
        try: self.source.close()
        finally: super().close()


class CancellableResponse(http.client.HTTPResponse):
    def __init__(self, sock, *args, valid, **kwargs):
        super().__init__(sock, *args, **kwargs)
        original = self.fp
        # Keep a makefile reference: HTTPConnection closes its socket on HTTP/1.0,
        # but the response must continue to own it until its body is consumed.
        self.fp = io.BufferedReader(_CancellableReader(sock, sock.makefile('rb', buffering=0), valid))
        original.close()
