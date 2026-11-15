"""Streaming body budgets and response headers, independent of Content-Length."""
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

from .operational_limits import AUDIO_IMPORT_BYTES, DOCUMENT_IMPORT_BYTES


def body_budget(path):
    if path.endswith('/import-json'):
        return 220 * 1024**2
    audio = '/recordings' in path or '/meeting-sessions/' in path and '/chunks/' in path
    return (AUDIO_IMPORT_BYTES if audio else DOCUMENT_IMPORT_BYTES) + 16 * 1024**2


class BodyBudgetExceeded(Exception):
    pass


class HTTPProtection:
    """Count bytes as consumers read them; do not preload or copy request bodies."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        maximum = body_budget(scope['path'])
        consumed = 0
        exceeded = False
        started = False
        rejected = False

        async def bounded_receive():
            nonlocal consumed, exceeded
            if exceeded:
                raise BodyBudgetExceeded()
            message = await receive()
            if message['type'] == 'http.request':
                consumed += len(message.get('body', b''))
                if consumed > maximum:
                    exceeded = True
                    raise BodyBudgetExceeded()
            return message

        async def protected_send(message):
            nonlocal started, rejected
            if rejected:
                return
            if exceeded:
                # Some multipart/JSON handlers translate parser exceptions to
                # 400. Preserve the actual cause and never emit a successful ACK.
                if started:
                    raise BodyBudgetExceeded()
                rejected = True
                await JSONResponse({'detail': 'Requête trop volumineuse'}, status_code=413)(scope, receive, send)
                return
            if message['type'] == 'http.response.start':
                started = True
                headers = MutableHeaders(scope=message)
                headers['X-Content-Type-Options'] = 'nosniff'
                headers['X-Frame-Options'] = 'DENY'
                headers['Referrer-Policy'] = 'no-referrer'
                headers['Permissions-Policy'] = 'camera=(), geolocation=(), microphone=(self)'
                path = scope['path']
                if not path.startswith(('/assets/', '/static/')):
                    headers['Cache-Control'] = 'private, no-store'
                # Legacy Jinja/fallback HTML still has inline handlers. Keep
                # those working, with the same framing/base/object protections;
                # the React application can prohibit all inline script.
                legacy = path.startswith('/ui') or not self._react_available()
                docs = path in {'/docs', '/redoc', '/docs/oauth2-redirect'}
                scripts = "'self' 'unsafe-inline'" if legacy else "'self'"
                if docs:
                    scripts = "'self' 'unsafe-inline' https://cdn.jsdelivr.net"
                frames = "'self' blob: data:"
                # srcdoc mail frames inherit the parent's policy: their own
                # stricter CSP blocks remote images until explicit opt-in.
                headers['Content-Security-Policy'] = (
                    "default-src 'self'; script-src " + scripts + "; style-src 'self' 'unsafe-inline'"
                    + (' https://cdn.jsdelivr.net' if docs else '')
                    + "; img-src 'self' data: blob: https: http:; font-src 'self' data:; "
                    + "connect-src 'self'; frame-src " + frames
                    + "; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'")
            await send(message)

        try:
            await self.app(scope, bounded_receive, protected_send)
        except Exception:
            if not exceeded or started:
                raise
            if not rejected:
                await JSONResponse({'detail': 'Requête trop volumineuse'}, status_code=413)(scope, receive, send)

    @staticmethod
    def _react_available():
        from pathlib import Path
        return (Path(__file__).resolve().parents[1] / 'web/dist/index.html').is_file()
