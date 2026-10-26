"""Bounded authenticated public embedding adapter."""
import json
import http.client
from kiara_shared.http import json_body
from workspace_types import Conflict, Denied

def handle(handler,store):
    if not handler.authorized():
        return
    from public_embeddings import request, response
    try:
        texts, encoding, mode = request(json_body(handler, 65536))
    except (ValueError, TypeError):
        return handler.respond(400, {'error': {'message': 'Requête embeddings invalide : modèle google/embeddinggemma-2, 1 à 8 textes de 4500 caractères, 768 dimensions, float/base64.'}})
    if not store.embedding_slot.acquire(blocking=False):
        return handler.respond(429, {'error': {'message': 'EG2 occupé. Réessayez après la requête en cours.'}})
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
        store.embedding_slot.release()

