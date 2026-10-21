"""Regression checks for account-isolated administration and bounded EG2 ingress."""
from http.server import BaseHTTPRequestHandler
import socket
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import psutil
from embedding_worker import EmbeddingHTTPServer
from local_access import LocalUserHTTPServer, same_windows_user


class SecurityBoundariesTests(unittest.TestCase):
    def test_peer_identity_comes_from_the_outbound_socket_owner(self):
        connection = Mock()
        connection.getsockname.return_value = ('127.0.0.1', 8765)
        connection.getpeername.return_value = ('127.0.0.1', 49152)
        row = SimpleNamespace(pid=123, laddr=('127.0.0.1', 49152),
                              raddr=('127.0.0.1', 8765), status=psutil.CONN_ESTABLISHED)
        process = Mock(return_value=SimpleNamespace(username=lambda: 'HOST\\Owner'))
        self.assertTrue(same_windows_user(connection, owner='host\\owner', connections=[row], process=process))
        self.assertFalse(same_windows_user(connection, owner='host\\other', connections=[row], process=process))
        self.assertFalse(same_windows_user(connection, owner='host\\owner', connections=[], process=process))
        process.side_effect = psutil.AccessDenied(123)
        self.assertFalse(same_windows_user(connection, owner='host\\owner', connections=[row], process=process))

    def test_console_denies_foreign_account_before_reading_http_headers(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                raise AssertionError('Foreign user reached HTTP handler')
        server = LocalUserHTTPServer(('127.0.0.1', 0), Handler)
        server.windows_owner = 'HOST\\Owner'
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch('local_access.same_windows_user', return_value=False), socket.create_connection(server.server_address, timeout=2) as client:
                self.assertIn(b'403 Forbidden', client.recv(4096))
        finally:
            server.shutdown(); server.server_close(); thread.join(2)

    def test_eg2_incomplete_headers_expire_and_capacity_is_recovered(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b'OK')
        server = EmbeddingHTTPServer(('127.0.0.1', 0), Handler, capacity=1)
        server.request_timeout = .4
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with socket.create_connection(server.server_address, timeout=2) as stalled:
                stalled.sendall(b'GET / HTTP/1.1\r\nHost:')
                deadline = time.monotonic() + 2
                while server.workers._value and time.monotonic() < deadline:
                    time.sleep(.01)
                with socket.create_connection(server.server_address, timeout=2) as excess:
                    self.assertIn(b'503 Service Unavailable', excess.recv(4096))
                self.assertEqual(stalled.recv(4096), b'')
            deadline = time.monotonic() + 2
            while not server.workers._value and time.monotonic() < deadline:
                time.sleep(.01)
            with socket.create_connection(server.server_address, timeout=2) as recovered:
                recovered.sendall(b'GET / HTTP/1.0\r\n\r\n')
                self.assertIn(b'200 OK', recovered.recv(4096))
        finally:
            server.shutdown(); server.server_close(); thread.join(2)
