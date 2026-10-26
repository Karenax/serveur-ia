"""Authenticated bounded voice streaming adapters, independent of inference routing."""
import json
import http.client
from kiara_shared.http import json_body
from workspace_types import Conflict, Denied

def max_voice(handler,store):
    if not handler.authorized():
        return
    frames = None
    sent = False
    try:
        value = json_body(handler, 1300000 if handler.path.endswith('/transcribe') else 8192)
        valid = lambda: store.authenticate(handler.access_token) == handler.identity
        if not valid():
            raise PermissionError('Accès vocal désactivé.')
        if handler.path.endswith('/test'):
            if value != {}:
                raise ValueError('Paramètres du test Max invalides.')
            return handler.respond(200, store.voice_max.test())
        if handler.path.endswith('/warm'):
            if not isinstance(value, dict) or set(value) != {'session'}:
                raise ValueError('Paramètres Max invalides.')
            return handler.respond(200, store.voice_max.warm(handler.identity, value['session']))
        if handler.path.endswith('/end'):
            if not isinstance(value, dict) or set(value) != {'session'} or (not isinstance(value['session'], str)):
                raise ValueError('Session Max invalide.')
            return handler.respond(200, store.voice_max.release(handler.identity, value['session']))
        if handler.path.endswith('/transcribe'):
            return handler.respond(200, store.voice_max.transcribe(handler.identity, value, valid))
        if handler.path.endswith('/cancel'):
            if not isinstance(value, dict) or set(value) != {'request_id'} or (not isinstance(value['request_id'], str)) or (len(value['request_id']) != 32):
                raise ValueError('Annulation Max invalide.')
            return handler.respond(200, store.voice_max.cancel(handler.identity, value['request_id']))
        frames = store.voice_max.frames(handler.identity, 'speak', value, valid)
        first = next(frames)
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/event-stream')
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('Connection', 'close')
        handler.end_headers()
        sent = True
        handler.wfile.write(('data: ' + json.dumps(first) + '\n\n').encode())
        handler.wfile.flush()
        for frame in frames:
            handler.wfile.write(('data: ' + json.dumps(frame) + '\n\n').encode())
            handler.wfile.flush()
    except BlockingIOError as error:
        if not sent:
            handler.respond(429, {'error': {'message': str(error)}})
    except (ValueError, OSError, TypeError, PermissionError) as error:
        if not sent:
            handler.respond(400, {'error': {'message': str(error)}})
    finally:
        if frames:
            frames.close()
    return

def low_voice(handler,store):
    if not handler.authorized():
        return
    frames = None
    sent = False
    try:
        value = json_body(handler, 8192)
        if handler.path.endswith('/cancel'):
            if not isinstance(value, dict) or set(value) != {'request_id'} or (not isinstance(value['request_id'], str)):
                raise ValueError('Annulation vocale invalide.')
            return handler.respond(200, store.voice.cancel(handler.identity, value['request_id']))
        frames = store.voice.stream(handler.identity, value, lambda: store.authenticate(handler.access_token) == handler.identity)
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/event-stream')
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('Connection', 'close')
        handler.end_headers()
        sent = True
        for frame in frames:
            handler.wfile.write(('data: ' + json.dumps(frame, ensure_ascii=False) + '\n\n').encode('utf-8'))
            handler.wfile.flush()
    except BlockingIOError as error:
        if not sent:
            handler.respond(429, {'error': {'message': str(error)}})
    except (ValueError, OSError, TypeError, PermissionError) as error:
        if not sent:
            handler.respond(400, {'error': {'message': str(error)}})
    finally:
        if frames:
            frames.close()
    return

MAX_ROUTES=('/v1/voice/max/test','/v1/voice/max/warm','/v1/voice/max/end','/v1/voice/max/transcribe','/v1/voice/max/speech','/v1/voice/max/cancel')
LOW_ROUTES=('/v1/voice/speech','/v1/voice/cancel')
