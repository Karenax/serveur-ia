"""Isolated publication and authenticated download tests, without model inference."""
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import android_releases
from remote import AccessStore, serve_gateway


class AndroidUpdatesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.payload = b'APK fixture without personal data' * 4000
        self.apk = self.directory / 'Acces-serveur-Fred-Android.apk'
        self.apk.write_bytes(self.payload)
        self.release = {'package': 'net.karenax.fred', 'version': '1.0.5', 'version_code': 6,
                        'bytes': len(self.payload), 'sha256': hashlib.sha256(self.payload).hexdigest()}
        self.publish()

    def tearDown(self):
        self.temp.cleanup()

    def publish(self):
        (self.directory / 'release.json').write_text(json.dumps(self.release), encoding='utf-8')

    def test_invalid_manifest_corruption_and_cache_invalidation(self):
        self.assertEqual(android_releases.status(self.directory)[0], self.release)
        self.apk.write_bytes(b'x' * len(self.payload))
        with self.assertRaises(ValueError): android_releases.status(self.directory)
        self.apk.write_bytes(self.payload)
        for key, value in [('package', 'other.app'), ('version_code', True), ('bytes', 2**40), ('sha256', '../bad')]:
            original = self.release[key]
            self.release[key] = value
            self.publish()
            with self.assertRaises(ValueError): android_releases.status(self.directory)
            self.release[key] = original
        self.publish()
        self.assertEqual(android_releases.status(self.directory)[1], self.apk)

    def test_authenticated_stream_and_revoked_access(self):
        store = AccessStore(self.directory / 'private')
        access = store.issue('Android fixture')
        store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        server = serve_gateway(store, lambda: (0, 'unused', ''), 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
        def request(path, token=access['token']):
            return urllib.request.urlopen(urllib.request.Request(origin + path, headers={'Authorization': 'Bearer ' + token}), timeout=5)
        try:
            with patch.object(android_releases, 'DIRECTORY', self.directory):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request('/v1/client/android/download', 'invalid')
                self.assertEqual(error.exception.code, 401)
                with request('/v1/client/android/release') as response:
                    self.assertEqual(json.load(response), self.release)
                with request('/v1/client/android/download') as response:
                    self.assertEqual(response.headers['Content-Type'], 'application/vnd.android.package-archive')
                    self.assertEqual(response.read(), self.payload)
                self.apk.write_bytes(b'tampered')
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request('/v1/client/android/download')
                self.assertEqual(error.exception.code, 503)
                store.revoke(access['id'])
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request('/v1/client/android/release')
                self.assertEqual(error.exception.code, 401)
        finally:
            server.shutdown(); server.server_close()

    def test_real_wireguard_download_allowlists(self):
        from core import ROOT
        import wireguard_access
        import wg_bridge
        binary = ROOT / 'toolchain/releases-staging/android-updates/wireguard-bridge.exe'
        if not binary.exists(): self.skipTest('Build the staged WireGuard bridge first.')
        store = AccessStore(self.directory / 'private-wg')
        access = store.issue('WireGuard Android fixture')
        wireguard = wireguard_access.WireGuardAccess(store, store.home)
        wireguard.configure({'public_host': '127.0.0.1', 'listen_port': 51820})
        profile = wireguard.new_peer(access)
        store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        server = serve_gateway(store, lambda: (0, 'unused', ''), 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        engine = bridge = None
        try:
            with patch.object(wireguard_access, 'ENGINE', binary), patch.object(wg_bridge, 'bridge_executable', return_value=binary), patch.object(android_releases, 'DIRECTORY', self.directory):
                engine = wireguard_access.Engine({'role': 'server', 'wireguard': {'private_key': wireguard.vault()['private_key']},
                        'listen_port': 0, 'upstream_port': server.server_port, 'peers': wireguard.peers()}, executable=binary)
                profile['wireguard']['endpoint'] = f'127.0.0.1:{engine.port}'
                bridge = wg_bridge.Bridge(profile)
                for path in ('release', 'download'):
                    request = urllib.request.Request(bridge.url + '/v1/client/android/' + path, headers={'X-Qwen-Bridge': bridge.key})
                    with urllib.request.urlopen(request, timeout=30) as response:
                        self.assertEqual(json.load(response), self.release) if path == 'release' else self.assertEqual(response.read(), self.payload)
        finally:
            if bridge: bridge.close()
            if engine: engine.close()
            wireguard.close(); server.shutdown(); server.server_close()


if __name__ == '__main__': unittest.main()
