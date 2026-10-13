"""Shared, bounded HTTP ingress for Fred's loopback services."""
from http.server import ThreadingHTTPServer
import json
import threading


class BoundedHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_timeout = 30

    def __init__(self, *args, capacity=32, **kwargs):
        self.workers = threading.BoundedSemaphore(capacity)
        super().__init__(*args, **kwargs)

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(self.request_timeout)
        return request, address

    def process_request(self, request, address):
        if not self.workers.acquire(blocking=False):
            try:
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.workers.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.workers.release()


def json_body(handler, maximum, *, allow_empty=False):
    if handler.headers.get('Transfer-Encoding'):
        raise ValueError('Corps JSON attendu ; encodage de transfert refusé.')
    lengths = handler.headers.get_all('Content-Length', [])
    if len(lengths) > 1:
        raise ValueError('Taille de requête ambiguë.')
    try:
        length = int(lengths[0]) if lengths else 0
    except ValueError:
        raise ValueError('Taille de requête invalide.') from None
    if not (0 if allow_empty else 1) <= length <= maximum:
        raise ValueError('Requête trop volumineuse ou vide (maximum ' + str(maximum) + ' octets).')
    if length or not allow_empty:
        if not handler.headers.get('Content-Type', '').startswith('application/json'):
            raise ValueError('Corps JSON attendu.')
    raw = handler.rfile.read(length)
    if len(raw) != length:
        raise ValueError('Corps de requête incomplet.')
    value = json.loads(raw or b'{}')
    if not isinstance(value, dict):
        raise ValueError('Objet JSON attendu.')
    return value
