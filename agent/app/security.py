"""Local session protection for the desktop API (no user accounts)."""
import os
import secrets
import threading
from urllib.parse import urlsplit

from fastapi.responses import JSONResponse
from fastapi import HTTPException
from .http_protection import body_budget

SESSION_TOKEN = secrets.token_urlsafe(32)
_kiara_verifier = None
_kiara_verifier_key = None
_kiara_verifier_lock = threading.Lock()


async def local_guard(request, call_next):
    async def authorized_next(checked_request):
        return await _operator_guard(checked_request, call_next)
    if os.environ.get('AGENT_KIARA_KEY'):
        return await _kiara_guard(request, authorized_next)
    return await _local_session_guard(request, authorized_next)


async def _kiara_guard(request, call_next):
    """Only accept requests carrying a fresh context signed by Kiara."""
    global _kiara_verifier, _kiara_verifier_key
    from backend.app.services.project_operator import Operator, operator_context
    from kiara_shared.agent_auth import Verifier

    if request.url.hostname not in {'127.0.0.1', 'localhost', '::1', 'testserver'}:
        return JSONResponse({'detail': 'Hôte Agent invalide'}, status_code=403)
    try:
        key_text = os.environ['AGENT_KIARA_KEY']
        key = bytes.fromhex(key_text)
        with _kiara_verifier_lock:
            if _kiara_verifier is None or _kiara_verifier_key != key:
                _kiara_verifier = Verifier(key)
                _kiara_verifier_key = key
            verifier = _kiara_verifier
        raw_path = request.scope.get('raw_path')
        target = raw_path.decode('ascii') if raw_path is not None else request.url.path
        query = request.scope.get('query_string', b'')
        if query:
            target += '?' + query.decode('ascii')
        value = verifier.verify(request.headers.get('X-Kiara-Agent-Context', ''), request.method, target)
        projects = value['project_ids']
        operator = Operator(value['id'], value['role'], frozenset(projects) if projects is not None else None,
                            value['person_id'])
    except (KeyError, TypeError, ValueError, UnicodeError):
        return JSONResponse({'detail': 'Identité Kiara absente ou invalide'}, status_code=403)
    length = request.headers.get('content-length')
    if length:
        try:
            if int(length) < 0 or int(length) > body_budget(request.url.path):
                return JSONResponse({'detail': 'Requête trop volumineuse'}, status_code=413)
        except ValueError:
            return JSONResponse({'detail': 'Content-Length invalide'}, status_code=400)
    with operator_context(operator):
        return await call_next(request)


async def _operator_guard(request, call_next):
    from backend.app.services.project_operator import current_operator, operator_context
    from .services.project_access import authorize

    try:
        operator = current_operator()
        body = None
        if operator.project_ids is not None and request.method not in {"GET", "HEAD", "OPTIONS"}:
            if "application/json" in request.headers.get("content-type", ""):
                try:
                    if await request.body():
                        body = await request.json()
                except ValueError:
                    return JSONResponse({"detail": "Corps JSON invalide"}, status_code=422)
        authorize(request.method, request.url.path, query=request.query_params, body=body)
    except HTTPException as exc:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    except ValueError:
        return JSONResponse({"detail": "Configuration d'opérateur invalide"}, status_code=503)
    with operator_context(operator):
        return await call_next(request)


async def _local_session_guard(request, call_next):
    length = request.headers.get("content-length")
    path = request.url.path
    maximum = body_budget(path)
    if length:
        try:
            if int(length) > maximum or int(length) < 0:
                return JSONResponse({"detail": "Requête trop volumineuse"}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Content-Length invalide"}, status_code=400)
    hostname = request.url.hostname
    allowed = {"127.0.0.1", "localhost", "::1"}
    testing = os.environ.get("AGENT_TESTING") == "1"
    if testing:
        allowed.add("testserver")
    if hostname not in allowed:
        return JSONResponse({"detail": "Hôte local non autorisé"}, status_code=400)
    origin = request.headers.get("origin")
    bridge = request.url.path.startswith("/v1/thunderbird/bridge/")
    extension_origin = bool(origin and urlsplit(origin).scheme == "moz-extension")
    if bridge:
        if origin and not extension_origin:
            return JSONResponse({"detail": "Origine de liaison non autorisée"}, status_code=403)
        headers = {"Access-Control-Allow-Origin": origin, "Vary": "Origin"} if origin else {}
        if request.method == "OPTIONS":
            return JSONResponse({}, headers={**headers, "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-Agent-Thunderbird-Token"})
        from .services.thunderbird import pairing_token
        expected = pairing_token()
        provided = request.headers.get("x-agent-thunderbird-token", "")
        if not expected or not secrets.compare_digest(provided, expected):
            return JSONResponse({"detail": "Liaison Thunderbird non appairée"}, status_code=403, headers=headers)
        response = await call_next(request)
        response.headers.update(headers)
        return response
    if origin:
        parsed = urlsplit(origin)
        same = parsed.netloc == request.url.netloc and parsed.scheme == request.url.scheme
        dev = origin in {"http://localhost:5174", "http://127.0.0.1:5174"}
        if not (same or dev):
            return JSONResponse({"detail": "Origine non autorisée"}, status_code=403)
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not testing:
        provided = request.headers.get("x-agent-token", "")
        if not secrets.compare_digest(provided, SESSION_TOKEN):
            return JSONResponse({"detail": "Session locale absente ou expirée ; recharge la page"}, status_code=403)
    return await call_next(request)


def session():
    from backend.app.services.project_operator import current_operator
    operator = current_operator()
    return {"token": SESSION_TOKEN, "operator": {"id": operator.id, "role": operator.role,
            "can_edit": operator.role != "reader", "can_administer": operator.role == "owner" and operator.project_ids is None,
            "project_ids": sorted(operator.project_ids) if operator.project_ids is not None else None}}
