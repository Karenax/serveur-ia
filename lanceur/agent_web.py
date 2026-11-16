"""Browser sessions for Kiara on a dedicated HTTPS origin behind a local proxy."""

import hashlib
import html
import json
import re
import secrets
import threading
import time
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from agent_gateway import proxy
from http_boundary import BoundedHTTPServer
from kiara_shared.thunderbird import PREFIX as THUNDERBIRD_PREFIX
from releases import DESKTOP_INSTALLER as WINDOWS_INSTALLER, windows_installer


COOKIE = '__Host-kiara-agent'
SESSION_SECONDS = 8 * 60 * 60
WINDOWS_DOWNLOAD = "/telechargements/" + WINDOWS_INSTALLER
OLD_WINDOWS_DOWNLOAD = '/telechargements/Kiara_3.5.63_x64-setup.exe'
PREVIOUS_WINDOWS_DOWNLOAD = '/telechargements/Kiara_4.0.0_x64-setup.exe'


class BrowserSessions:
    def __init__(self):
        self.lock = threading.Lock()
        self.entries = {}

    def create(self, identity, credential_hash):
        token = secrets.token_urlsafe(32)
        with self.lock:
            now = time.monotonic()
            self.entries = {key: entry for key, entry in self.entries.items() if entry[1] > now}
            if len(self.entries) >= 4096:
                return None
            self.entries[self.key(token)] = (identity, credential_hash), now + SESSION_SECONDS
        return token

    @staticmethod
    def key(token):
        return hashlib.sha256(token.encode('ascii')).digest()

    def identity(self, token):
        with self.lock:
            entry = self.entries.get(self.key(token))
            return entry[0] if entry and entry[1] > time.monotonic() else None

    def remove(self, token):
        with self.lock:
            self.entries.pop(self.key(token), None)


def validate_origin(origin):
    url = urlsplit(origin)
    if url.scheme != 'https' or not url.hostname or not re.fullmatch(r'[a-zA-Z0-9.-]+(?::[0-9]{1,5})?', url.netloc) or origin != f'https://{url.netloc}':
        raise ValueError('Origine HTTPS du portail Kiara invalide.')
    if url.port is not None and not 1 <= url.port <= 65535:
        raise ValueError('Port HTTPS du portail Kiara invalide.')
    return url


SHARED_PORTAL_PREFIXES = ('/kiara', '/agent')


def portal_prefix(path, prefixes):
    return next((prefix for prefix in prefixes if path == prefix or path.startswith(prefix + '/')), None)


def agent_web_handler(store, origin, prefixes=('',)):
    url = validate_origin(origin)
    sessions = BrowserSessions()
    installer = Path(store.home) / "installateurs" / WINDOWS_INSTALLER
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_content(self, code, data, content_type, *, cookie=None, location=None, nonce=None):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            policy = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            if nonce:
                policy += f"; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; img-src data: blob:"
            self.send_header('Content-Security-Policy', policy)
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'same-origin')
            if cookie is not None:
                age = SESSION_SECONDS if cookie else 0
                self.send_header('Set-Cookie', f'{COOKIE}={cookie}; Max-Age={age}; Path=/; Secure; HttpOnly; SameSite=Strict')
            if location is not None:
                self.send_header('Location', location)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)

        def respond(self, code, data):
            self.send_content(code, json.dumps(data, ensure_ascii=False).encode(), 'application/json; charset=utf-8')

        def entry_path(self):
            return '/app/conversations' if getattr(self, 'browser_conversation', None) else '/app'

        def page(self, code=200, message='', signed_in=False, *, windows=False):
            prefix = self.portal_prefix
            action = prefix + '/connexion' + ('?destination=windows' if windows else '')
            content = (
                f'<p><a href="{prefix}{self.entry_path()}">Ouvrir Kiara</a></p><form method="post" action="{prefix}/deconnexion">'
                '<button>Se déconnecter</button></form>' if signed_in else
                f'<form method="post" action="{action}">'
                '<label for="access">Clé d’accès Kiara</label> '
                '<input id="access" name="access" type="password" autocomplete="current-password" required maxlength="256"> '
                '<button>Se connecter</button></form>'
            )
            if signed_in and installer.is_file():
                content = (f'<p><a href="{prefix}{WINDOWS_DOWNLOAD}">Télécharger Kiara 4 pour Windows</a></p>'
                           '<p>Installateur non signé. Au premier lancement, sélectionnez votre EXE personnel Kiara.</p>'
                           + content)
            status = f'<p role="alert">{html.escape(message)}</p>' if message else ''
            markup = ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
                      '<meta name="viewport" content="width=device-width,initial-scale=1">'
                      '<title>Kiara</title></head><body><main><h1>Kiara</h1>'
                      f'{status}{content}</main></body></html>')
            self.send_content(code, markup.encode(), 'text/html; charset=utf-8')

        def download_installer(self, active):
            if not active():
                return self.respond(403, {'detail': 'Accès Kiara refusé.'})
            try:
                stream = installer.open('rb')
            except FileNotFoundError:
                return self.respond(404, {'detail': 'Installateur Kiara indisponible.'})
            except OSError:
                return self.respond(503, {'detail': 'Impossible de lire l’installateur Kiara.'})
            with stream:
                try:
                    release, _ = windows_installer(store.home, stream=stream)
                except ValueError:
                    return self.respond(503, {'detail': 'Impossible de vérifier l’installateur Kiara.'})
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{WINDOWS_INSTALLER}"')
                self.send_header('Content-Length', str(release['bytes']))
                self.send_header('Cache-Control', 'private, no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                if self.command == 'HEAD':
                    return
                try:
                    while active() and (block := stream.read(256 * 1024)):
                        self.wfile.write(block)
                except (ConnectionError, TimeoutError):
                    return

        def session_token(self):
            try:
                cookies = SimpleCookie()
                cookies.load(self.headers.get('Cookie', ''))
                token = cookies[COOKIE].value
                return token if re.fullmatch(r'[A-Za-z0-9_-]{43}', token) else ''
            except (CookieError, KeyError):
                return ''

        def login(self, previous_token, *, windows=False):
            lengths = self.headers.get_all('Content-Length', [])
            try:
                if (self.headers.get('Transfer-Encoding') or len(lengths) != 1
                        or not 1 <= int(lengths[0]) <= 2048
                        or self.headers.get_content_type() != 'application/x-www-form-urlencoded'):
                    raise ValueError()
                length = int(lengths[0])
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError()
                values = parse_qs(raw.decode('ascii'), max_num_fields=1)
                access = values['access'][0]
            except (KeyError, UnicodeError, ValueError):
                return self.page(400, 'Saisissez votre clé d’accès Kiara.', windows=windows)
            identity = store.authenticate(access)
            bridge = store.agent_bridge
            if not identity or not bridge or not bridge.operator_for(identity):
                return self.page(403, 'Accès Kiara refusé. Vérifiez votre clé ou contactez votre administrateur.', windows=windows)
            sessions.remove(previous_token)
            token = sessions.create(identity, hashlib.sha256(access.encode()).hexdigest())
            if token is None:
                return self.page(503, 'Connexion indisponible. Réessayez dans un instant.', windows=windows)
            destination = WINDOWS_DOWNLOAD if windows else self.entry_path()
            return self.send_content(303, b'', 'text/plain', cookie=token, location=self.portal_prefix+destination)

        def dispatch(self):
            if self.headers.get_all('Host') != [url.netloc] or not self.path.startswith('/') or self.path.startswith('//'):
                return self.respond(400, {'detail': 'Adresse du portail Kiara invalide.'})
            origin_header = self.headers.get_all('Origin')
            if ((origin_header and origin_header != [origin])
                    or (self.command not in ('GET', 'HEAD') and origin_header != [origin])):
                return self.respond(403, {'detail': 'Cette requête doit provenir du portail Kiara.'})
            parsed = urlsplit(self.path)
            prefix = portal_prefix(parsed.path, prefixes)
            if prefix is None:
                return self.respond(404, {'detail': 'Page Kiara indisponible.'})
            self.portal_prefix = prefix
            if prefix and parsed.path == prefix and self.command in ('GET', 'HEAD'):
                return self.send_content(303, b'', 'text/plain', location=prefix+'/')
            if prefix and parsed.path == prefix:
                return self.respond(404, {'detail': 'Page Kiara indisponible.'})
            path = parsed.path[len(prefix):]
            if path in (OLD_WINDOWS_DOWNLOAD, PREVIOUS_WINDOWS_DOWNLOAD) and self.command in ('GET', 'HEAD'):
                return self.send_content(303, b'', 'text/plain', location=prefix+WINDOWS_DOWNLOAD)
            token = self.session_token()
            if self.command == 'POST' and path == '/connexion':
                return self.login(token, windows=parsed.query == 'destination=windows')
            if self.command == 'POST' and path == '/deconnexion':
                sessions.remove(token)
                return self.send_content(303, b'', 'text/plain', cookie='', location=prefix+'/')
            credentials = sessions.identity(token)
            identity, credential_hash = credentials or (None, None)

            def active():
                return bool(identity and sessions.identity(token) == credentials
                            and store.valid_owner(identity, credential_hash=credential_hash))

            if path == '/' and self.command in ('GET', 'HEAD'):
                return self.page(signed_in=active())
            if not active():
                if path == WINDOWS_DOWNLOAD and self.command == 'GET':
                    return self.page(message='Connectez-vous pour télécharger Kiara 4 pour Windows. '
                                     'L’installateur est non signé.', windows=True)
                if self.command in ('GET', 'HEAD') and (path == '/app' or path.startswith('/app/')):
                    return self.send_content(303, b'', 'text/plain', cookie='', location=prefix+'/')
                return self.respond(401, {'detail': 'Reconnectez-vous à Kiara.'})
            if path == WINDOWS_DOWNLOAD and self.command in ('GET', 'HEAD'):
                return self.download_installer(lambda: active() and bool(
                    store.agent_bridge and store.agent_bridge.operator_for(identity)))
            if path.startswith(THUNDERBIRD_PREFIX):
                return self.respond(403, {'detail': 'Cette action est réservée au poste Thunderbird.'})
            browser_conversation = getattr(self, 'browser_conversation', None)
            if browser_conversation and not parsed.query:
                from web_conversations import ROUTES, render
                if self.command in ('GET', 'HEAD') and path == '/app/conversations':
                    if not store.agent_bridge or not store.agent_bridge.operator_for(identity):
                        return self.respond(403, {'detail': 'Accès Kiara refusé.'})
                    nonce = secrets.token_urlsafe(24)
                    try:
                        page = render(identity, prefix, nonce)
                    except (OSError, ValueError):
                        return self.respond(503, {'detail': 'Conversations est indisponible.'})
                    return self.send_content(200, page, 'text/html; charset=utf-8', nonce=nonce)
                if path in ROUTES.get(self.command, ()):
                    return browser_conversation(path, identity, active)
            return proxy(self, store, path, parsed.query, identity, active, browser=True, browser_prefix=prefix)

        do_HEAD = do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = dispatch

    return Handler


def serve_agent_web(store, origin, port):
    return BoundedHTTPServer(('127.0.0.1', port), agent_web_handler(store, origin))
