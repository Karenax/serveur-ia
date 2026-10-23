"""Background probes cannot tear down healthy streams or monopolize the bridge."""
import base64
import io
import json
import threading
import time
import unittest
import urllib.error
from unittest.mock import patch
import client


class ConnectionResilienceTests(unittest.TestCase):
    def remote(self,opener):
        key=base64.b64encode(b'x'*32).decode()
        profile={'url':'wireguard://10.77.0.1:8766','transport':'wireguard',
                 'token':'qwen_'+'0'*16+'_'+'x'*43,'protocol':3,
                 'wireguard':{'private_key':key,'server_public_key':key,'preshared_key':key,
                              'address':'10.77.0.2/32','endpoint':'test.example:51820'}}
        remote=client.Remote(profile,opener=opener)
        remote.connected=True;remote.reachable=True;remote.code='ready';remote.error=''
        remote.model='local';remote.models=['local'];remote.last_contact=time.time()
        remote.device_reported_at=time.time()
        return remote

    def test_secondary_timeout_keeps_working_connection_and_auth_denial_does_not(self):
        remote=self.remote(object())
        remote.failure('connection_error','Timeout')
        self.assertTrue(remote.connected);self.assertEqual('Timeout',remote.connection_warning)
        remote.failure('access_revoked','Accès révoqué')
        self.assertFalse(remote.connected);self.assertEqual('access_revoked',remote.code)

    def test_three_failed_probes_required_before_disconnection_and_no_route_churn(self):
        class Offline:
            calls=0
            def open(self,*args,**kwargs):self.calls+=1;raise urllib.error.URLError('offline')
        opener=Offline();remote=self.remote(opener);remote.candidates.append('other.example:51820')
        with patch.object(remote,'_switch_endpoint') as switch:
            for count in (1,2):
                state=remote.check();self.assertTrue(state['connected']);self.assertEqual(count,remote.probe_failures)
                self.assertEqual(['local'],state['models']);switch.assert_not_called()
                # UI polls during backoff do not issue another network probe.
                calls=opener.calls;remote.check();self.assertEqual(calls,opener.calls)
                remote.next_probe=0
            remote.candidates=[remote.endpoint]
            self.assertFalse(remote.check()['connected']);self.assertEqual([],remote.models)

    def test_slow_probe_does_not_block_audio_cancel_or_duplicate_probes(self):
        entered=threading.Event();release=threading.Event();requests=[]
        class Slow:
            def open(self,request,timeout):
                requests.append(request.full_url)
                if request.full_url.endswith('/v1/models'):
                    entered.set()
                    if not release.wait(3):raise TimeoutError('fixture')
                    return io.BytesIO(b'{"data":[{"id":"local"}]}')
                return io.BytesIO(b'{"cancelled":true}')
        remote=self.remote(Slow());worker=threading.Thread(target=remote.check)
        worker.start()
        try:
            self.assertTrue(entered.wait(1));self.assertTrue(remote.check()['checking'])
            start=time.monotonic()
            with remote.open('/v1/voice/cancel',b'{}') as response:self.assertTrue(json.load(response)['cancelled'])
            self.assertLess(time.monotonic()-start,.5)
        finally:release.set();worker.join(4)
        self.assertFalse(worker.is_alive());self.assertTrue(remote.connected)
        self.assertEqual(1,sum(url.endswith('/v1/models') for url in requests))

    def test_concurrent_success_overrules_older_failed_probe(self):
        entered=threading.Event();release=threading.Event()
        class OlderFailure:
            def open(self,request,timeout):
                if request.full_url.endswith('/v1/models'):
                    entered.set();release.wait(3);raise TimeoutError('old probe')
                return io.BytesIO(b'{}')
        remote=self.remote(OlderFailure());remote.probe_failures=2
        worker=threading.Thread(target=remote.check);worker.start()
        try:
            self.assertTrue(entered.wait(1))
            with remote.open('/v1/status'):pass
        finally:release.set();worker.join(4)
        self.assertTrue(remote.connected);self.assertEqual(0,remote.probe_failures)

    def test_late_successful_probe_cannot_clear_concurrent_access_revocation(self):
        entered=threading.Event();release=threading.Event()
        class LateSuccess:
            def open(self,request,timeout):
                entered.set();release.wait(3)
                return io.BytesIO(b'{"data":[{"id":"local"}]}')
        remote=self.remote(LateSuccess());worker=threading.Thread(target=remote.check)
        worker.start()
        try:
            self.assertTrue(entered.wait(1));remote.failure('access_revoked','Accès révoqué')
        finally:release.set();worker.join(4)
        self.assertFalse(remote.connected);self.assertEqual('access_revoked',remote.code)
        self.assertEqual('Accès révoqué',remote.error)


if __name__=='__main__':unittest.main(verbosity=2)
