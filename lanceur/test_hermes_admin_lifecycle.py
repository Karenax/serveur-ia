"""The local restore route must let an agent/provider worker finish shutting down."""
import http.client
import json
import queue
import socket
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import serve


class AdminLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.token = 'local-admin-test-token'
        self.restore_entered = threading.Event()
        self.provider_released = threading.Event()
        self.restore_calls = []
        self.controller = SimpleNamespace(lock=threading.RLock(),
                                          remote=SimpleNamespace(maintenance=False))

        def restore(data):
            self.restore_calls.append(data)
            self.restore_entered.set()
            # A real restore waits for agent teardown. That worker needs the
            # controller lock to finish its last provider/status operation.
            if not self.provider_released.wait(4):
                raise RuntimeError('Provider worker could not acquire controller.lock')
            return {'message': 'Restauration terminée.'}

        def state():
            with self.controller.lock:
                self.provider_released.set()
            return {'provider_released': True}

        self.controller.operations = SimpleNamespace(restore=restore)
        self.controller.state = state
        # serve() checks Host against the supplied port, so reserve an actual
        # loopback port rather than passing zero to its HTTP server.
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            self.port = reservation.getsockname()[1]
        with patch('app.secrets.token_urlsafe', return_value=self.token):
            self.server = serve(self.port, self.controller)
        self.worker = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': .01}, daemon=True)
        self.worker.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.provider_released.set()
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(5)

    def request(self, method, path, data=None, token=None, origin=None):
        headers = {'Content-Type': 'application/json',
                   'X-Launcher-Token': self.token if token is None else token}
        if origin is not None:
            headers['Origin'] = origin
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=6)
        try:
            body = None if data is None else json.dumps(data).encode()
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_restore_allows_a_second_http_worker_to_acquire_controller_lock(self):
        result = queue.Queue()
        payload = {'file': 'fixture-only.fred-backup', 'password': 'fixture-only'}

        def restore_request():
            try:
                result.put(self.request('POST', '/api/restore', payload))
            except Exception as error:
                result.put(error)

        worker = threading.Thread(target=restore_request, daemon=True)
        worker.start()
        self.addCleanup(worker.join, 6)
        self.assertTrue(self.restore_entered.wait(3), 'Restore handler was not entered')
        status, state = self.request('GET', '/api/state')
        self.assertEqual(status, 200)
        self.assertTrue(state['provider_released'])
        worker.join(6)
        self.assertFalse(worker.is_alive(), 'Restore HTTP request did not complete')
        response = result.get_nowait()
        if isinstance(response, Exception):
            raise response
        self.assertEqual(response, (200, {'message': 'Restauration terminée.'}))
        self.assertEqual(self.restore_calls, [payload])

    def test_restore_requires_the_admin_token(self):
        status, body = self.request('POST', '/api/restore', {}, token='invalid')
        self.assertEqual(status, 403)
        self.assertIn('error', body)
        self.assertEqual(self.restore_calls, [])

    def test_restore_rejects_an_untrusted_origin_even_with_a_valid_token(self):
        status, body = self.request('POST', '/api/restore', {},
                                    origin='https://untrusted.example')
        self.assertEqual(status, 403)
        self.assertIn('error', body)
        self.assertEqual(self.restore_calls, [])

    def test_restore_is_not_started_during_maintenance(self):
        self.controller.remote.maintenance = True
        status, body = self.request('POST', '/api/restore', {})
        self.assertEqual(status, 400)
        self.assertIn('maintenance', body['error'])
        self.assertEqual(self.restore_calls, [])


if __name__ == '__main__':
    unittest.main()
