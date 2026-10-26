"""HTTP adapters for transactional commands; identity always comes from ingress."""
from kiara_shared.http import json_body
from workspace_types import Conflict,Denied

ROUTES={
    '/v1/agent/action':8192,
    '/v1/notifications/action':65536,
    '/v1/device':2048,
    '/v1/history':10*1024*1024,
    '/v1/workspace/action':8*1024*1024,
}


def handle(handler,store):
    if not handler.authorized():return
    path=handler.path
    try:
        if path=='/v1/agent/action' and not store.hermes:
            raise ValueError('Les agents ne sont pas activés sur ce serveur.')
        value=json_body(handler,ROUTES[path])
        prepared=store.workspace.prepare_upload(handler.identity,value) if path=='/v1/workspace/action' else None
        if path=='/v1/agent/action':
            if store.authenticate(handler.access_token)!=handler.identity:raise Denied('Accès désactivé.')
            result=store.hermes.action(handler.identity,value)
        else:
            # Parsing/extraction happens outside this lock. Revalidate under
            # the same lock as suspension/revocation before any mutation.
            with store.lock:
                if store.authenticate(handler.access_token)!=handler.identity:raise Denied('Accès désactivé.')
                if path=='/v1/workspace/action':result=store.workspace.action(handler.identity,value,prepared)
                elif path=='/v1/history':result=store.workspace.history_write(handler.identity,value)
                elif path=='/v1/device':result=store.heartbeat(handler.identity,value)
                else:result=store.notifications.action(handler.identity,value)
        return handler.respond(200,result)
    except Conflict as error:
        detail={'message':str(error)}
        if path=='/v1/history':detail['code']='history_conflict'
        return handler.respond(409,{'error':detail})
    except Denied as error:return handler.respond(403,{'error':{'message':str(error)}})
    except (ValueError,OSError,TypeError,ImportError) as error:
        message='Cette demande agent ne peut pas être traitée.' if path=='/v1/agent/action' else str(error)
        return handler.respond(400,{'error':{'message':message}})
