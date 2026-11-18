"""Cancellation route shared by chat, text transformations and voice requests."""
from http_boundary import json_body


def handle(handler, store, scheduler):
    if not handler.authorized():
        return
    try:
        value = json_body(handler, 4096, allow_empty=True)
        if not isinstance(value, dict) or set(value) - {'text_transform', 'voice_conversation'}:
            raise ValueError('Requête d’annulation invalide.')
        direct = bool(value)
        if direct and (len(value) != 1 or next(iter(value.values())) is not True):
            raise ValueError('Annulation directe invalide.')
        request = handler.headers.get('X-Qwen-Request') or None
        if request is not None or direct:
            store.text_transforms.request_id(request)
        # Keep the receipt if cancellation arrives before submission or health checks finish.
        if direct:
            store.text_transforms.cancel(handler.identity, request)
        with scheduler.condition:
            transforms = [item['id'] for item in scheduler.requests
                          if item['owner'] == handler.identity
                          and (item.get('text_transform') or item.get('voice_conversation'))
                          and (request is None or item['id'] == request)]
        for target in transforms:
            store.text_transforms.cancel(handler.identity, target)
        scheduler.cancel(handler.identity, request)
        manager = getattr(store.hermes, 'conversations', None)
        agent_active = request is None and manager is not None and manager.context(handler.identity) is not None
        if direct or (transforms and not agent_active):
            return handler.respond(200, {'cancelled': True, 'request_id': request})
    except (ValueError, TypeError, OSError) as error:
        return handler.respond(400, {'error': {'message': str(error)}})
    if store.hermes:
        try:
            return handler.respond(200, store.hermes.cancel(handler.identity, request))
        except ValueError as error:
            return handler.respond(400, {'error': {'message': str(error)}})
    return handler.respond(200, {'cancelled': True})
