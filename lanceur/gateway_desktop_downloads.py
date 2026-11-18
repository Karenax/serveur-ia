"""Authenticated delivery of the signed Windows desktop installer."""
from kiara_shared.releases import DESKTOP_DOWNLOAD, DESKTOP_RELEASE


ROUTES = frozenset((DESKTOP_RELEASE, DESKTOP_DOWNLOAD,
                    '/v1/client/kiara4/release', '/v1/client/kiara4/download'))


def handle(handler, store):
    if not handler.authorized():
        return
    from releases import DESKTOP_INSTALLER, windows_installer
    if handler.path.endswith('/release'):
        try:
            release, _ = windows_installer(store.home)
            return handler.respond(200, release)
        except ValueError as error:
            return handler.respond(503, {'error': {'message': str(error)}})
    try:
        stream = (store.home / 'installateurs' / DESKTOP_INSTALLER).open('rb')
    except OSError:
        return handler.respond(503, {'error': {'message': 'Installateur Kiara 4 indisponible.'}})
    with stream:
        try:
            release, _ = windows_installer(store.home, stream=stream)
        except ValueError as error:
            return handler.respond(503, {'error': {'message': str(error)}})
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/octet-stream')
        handler.send_header('Content-Length', str(release['bytes']))
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('X-Content-Type-Options', 'nosniff')
        handler.end_headers()
        try:
            while chunk := stream.read(256 * 1024):
                if not handler.access_valid():
                    return
                handler.wfile.write(chunk)
        except (ConnectionError, TimeoutError):
            return
