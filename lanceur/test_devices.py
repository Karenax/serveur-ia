"""Lot 4 proofs: disposable keys, real gateway and encrypted UDP tunnel only."""
import json
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import socket
import threading
import time
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request
from core import read_json, write_json
from devices import Revocations
from remote import AccessStore
from wireguard_access import Engine
import remote
import test_remote


class DeviceTests(unittest.TestCase):
    setUp = test_remote.RemoteTests.setUp
    tearDown = test_remote.RemoteTests.tearDown
    request = test_remote.RemoteTests.request

    def test_admin_metadata_keeps_credentials_and_owner_spaces_separate(self):
        before=read_json(self.store.path)['clients'][0]
        other=self.store.issue('Tablette')
        self.store.device({'id':self.access['id'],'name':'Téléphone Fred','owner':'Fred','kind':'phone','version':'1.0.0'})
        self.store.device({'id':other['id'],'owner':'Fred','kind':'tablet'})
        after=read_json(self.store.path)['clients'][0]
        self.assertEqual(after['hash'],before['hash'])
        self.assertEqual(after['wireguard_public_key'],before['wireguard_public_key'])
        self.assertEqual(after['address'],before['address'])
        metadata=self.store.metadata()
        self.assertEqual({c['device_owner'] for c in metadata['clients']},{'Fred'})
        self.assertEqual(metadata['clients'][0]['device_kind'],'phone')
        self.assertNotIn('hash',json.dumps(metadata))
        self.assertNotIn(self.access['token'],json.dumps(metadata))
        state=self.store.workspace.history_read(self.access['id'])
        history={'conversations':[{'id':'one','title':'Privée','messages':[]}],'currentId':'one'}
        self.store.workspace.history_write(self.access['id'],{'history':history,'revision':state['revision'],'reset_id':state['reset_id']})
        self.assertIsNone(self.store.workspace.history_read(other['id'])['history'])
        for values in ({'id':other['id'],'kind':'administrator'},{'id':other['id'],'owner':'X\nY'},{'id':other['id'],'role':'admin'},{'id':'missing','kind':'phone'}):
            with self.subTest(values=values),self.assertRaises(ValueError):self.store.device(values)

    def test_authenticated_declaration_server_clock_and_restart(self):
        before=time.time()
        with self.request('/v1/device',{'kind':'phone','version':'1.0.0','transport':'https'}) as response:declaration=json.load(response)
        self.assertGreaterEqual(declaration['server_epoch'],before)
        self.assertLessEqual(declaration['server_epoch'],time.time())
        record=self.store.metadata()['clients'][0]
        self.assertEqual(record['reported_kind'],'phone')
        self.assertEqual(record['reported_version'],'1.0.0')
        self.assertEqual(record['last_transport'],'https')
        self.assertEqual(record['device_kind'],'unknown')
        restarted=AccessStore(self.store.home)
        try:
            loaded=restarted.metadata()['clients'][0]
            self.assertEqual(loaded['reported_kind'],'phone')
            self.assertEqual(loaded['last_activity_epoch'],record['last_activity_epoch'])
        finally:restarted.workspace.shutdown()
        for data in ({'owner':'Admin'},{'id':'0'*16},{'server_epoch':1},{'transport':['https']},{'version':'x'*49}):
            with self.subTest(data=data),self.assertRaises(urllib.error.HTTPError) as error:self.request('/v1/device',data)
            self.assertEqual(error.exception.code,400);error.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/v1/device',{},token='qwen_invalid_bearer_'+'x'*40)
        self.assertEqual(error.exception.code,401);error.exception.close()

    def test_durable_revocation_cannot_be_undone_by_restoring_old_accesses(self):
        old=read_json(self.store.path)
        old_ledger=self.store.revocations.snapshot()
        other=self.store.issue('Autre appareil')
        # Save a pre-revocation file containing both devices, as a restore would.
        old=read_json(self.store.path)
        self.store.revoke(self.access['id'])
        write_json(self.store.path,old)
        self.store.revocations.merge(old_ledger)
        self.assertIsNone(self.store.authenticate(self.access['token']))
        self.assertFalse(self.store.valid_owner(self.access['id']))
        self.assertTrue(self.store.metadata()['clients'][0]['revoked'])
        self.assertEqual(self.store.authenticate(other['token']),other['id'])
        restarted=AccessStore(self.store.home)
        try:
            self.assertIsNone(restarted.authenticate(self.access['token']))
            self.assertEqual(restarted.authenticate(other['token']),other['id'])
        finally:restarted.workspace.shutdown()
        self.assertNotIn(self.access['token'],self.store.revocations.path.read_text())

    def test_revocation_cancels_sessions_queue_and_persistent_jobs_only_for_owner(self):
        other=self.store.issue('Autre appareil')
        item=self.store.scheduler.submit(self.access['id'])
        self.store.scheduler.wait(item,lambda:True,lambda _:None)
        aborted=[];item['abort']=lambda:aborted.append(True)
        other_item=self.store.scheduler.submit(other['id'])
        project=self.store.workspace.action(self.access['id'],{'action':'project_create','title':'Test'})['id']
        job=self.store.workspace.action(self.access['id'],{'action':'job_create','project':project,'prompt':'Test','delay_minutes':100,'request_key':secrets.token_hex(16)})['id']
        # Delay fields vary by known workspace versions; pause before a worker claims it.
        self.store.workspace.action(self.access['id'],{'action':'job_pause','id':job})
        self.store.revoke(self.access['id'])
        self.assertTrue(item['cancelled']);self.assertEqual(aborted,[True])
        self.assertFalse(other_item['cancelled'])
        self.assertFalse(self.store.accounts.valid(self.access['id'],self.session))
        self.assertEqual(self.store.workspace.action(self.access['id'],{'action':'job_get','id':job})['state'],'cancelled')
        self.store.scheduler.finish(item);self.store.scheduler.cancel(other['id'])

    def test_ledger_survives_metadata_write_failure_and_corruption_fails_closed(self):
        engine=Mock();engine.running.return_value=True;self.wireguard.engine=engine
        original=remote.write_json
        def fail(path,value):
            if path==self.store.path:raise OSError('Synthetic metadata failure')
            return original(path,value)
        with patch.object(remote,'write_json',side_effect=fail),self.assertRaises(OSError):self.store.revoke(self.access['id'])
        self.assertIsNone(self.store.authenticate(self.access['token']))
        self.assertEqual(engine.update.call_args.args[0],[])
        self.store.revocations.path.write_text('{damaged',encoding='utf-8')
        self.assertIsNone(self.store.authenticate(self.access['token']))
        self.assertFalse(self.store.valid_owner(self.access['id']))
        with self.assertRaises(ValueError):self.store.metadata()
        with self.assertRaises(ValueError):Revocations(self.store.home)

    def test_failed_peer_update_closes_tunnel_and_keeps_revocation(self):
        engine=Mock();engine.running.return_value=True;engine.update.side_effect=ValueError('Synthetic update failure')
        self.wireguard.engine=engine
        with self.assertRaisesRegex(ValueError,'tunnel a été arrêté'):self.store.revoke(self.access['id'])
        engine.close.assert_called_once();self.assertIsNone(self.wireguard.engine)
        self.assertIsNone(self.store.authenticate(self.access['token']))

    def test_android_profile_without_windows_release_is_private_and_unique(self):
        with patch('releases.status',side_effect=AssertionError('Android profile needs no Windows release')):
            first=self.wireguard.create_android('Téléphone Fred','test-model','Fred','phone')
            second=self.wireguard.create_android('Tablette Fred','test-model','Fred','tablet')
        a=json.loads(self.wireguard.android_profile(first['id']));b=json.loads(self.wireguard.android_profile(second['id']))
        from wg_bridge import validate_profile
        validate_profile(a);validate_profile(b)
        self.assertEqual(a['client_name'],'Téléphone Fred')
        self.assertEqual(a['protocol'],3)
        for field in ('token',):self.assertNotEqual(a[field],b[field])
        for field in ('address','private_key','preshared_key'):self.assertNotEqual(a['wireguard'][field],b['wireguard'][field])
        encrypted=(self.wireguard.directory/'profils-restaures.dpapi').read_bytes()
        self.assertNotIn(a['token'].encode(),encrypted)
        self.assertNotIn(a['wireguard']['private_key'].encode(),encrypted)
        self.assertNotIn('token',first);self.assertNotIn('wireguard',first)
        self.store.rename(first['id'],'Nouveau nom')
        self.assertEqual(json.loads(self.wireguard.android_profile(first['id']))['client_name'],'Nouveau nom')
        self.assertTrue(next(c for c in self.store.metadata()['clients'] if c['id']==first['id'])['has_android_profile'])
        self.wireguard.revoke(first['id'])
        with self.assertRaises(ValueError):self.wireguard.android_profile(first['id'])
        self.assertEqual(json.loads(self.wireguard.android_profile(second['id']))['token'],b['token'])
        for identity in ('../../evil','missing','0'*16):
            with self.assertRaises(ValueError):self.wireguard.android_profile(identity)

    def test_replacement_archives_old_access_keeps_history_and_other_device(self):
        old=self.wireguard.create_android('Téléphone','test-model','Fred','phone')
        old_profile=json.loads(self.wireguard.android_profile(old['id']))
        state=self.store.workspace.history_read(old['id'])
        history={'conversations':[{'id':'saved','title':'Conservée','messages':[]}],'currentId':'saved'}
        self.store.workspace.history_write(old['id'],{'history':history,'revision':state['revision'],'reset_id':state['reset_id']})
        new=self.wireguard.replace(old['id'],'test-model',kind='tablet')
        self.assertNotEqual(new['id'],old['id'])
        self.assertEqual(new['replaces_id'],old['id'])
        self.assertIsNone(self.store.authenticate(old_profile['token']))
        self.assertEqual(self.store.authenticate(self.access['token']),self.access['id'])
        self.assertEqual(self.store.workspace.history_read(old['id'])['history'],history)
        self.assertIsNone(self.store.workspace.history_read(new['id'])['history'])
        self.assertTrue(next(c for c in self.store.metadata()['archived_clients'] if c['id']==old['id'])['revoked'])
        new_record=next(c for c in self.store.metadata()['clients'] if c['id']==new['id'])
        self.assertEqual(new_record['device_owner'],'Fred');self.assertEqual(new_record['device_kind'],'tablet')

    def test_suspension_removes_peer_and_reactivation_preserves_keys(self):
        before=read_json(self.store.path)['clients'][0]
        engine=Mock();engine.running.return_value=True;self.wireguard.engine=engine
        self.wireguard.policy({'id':self.access['id'],'suspended':True})
        self.assertEqual(engine.update.call_args.args[0],[])
        self.assertIsNone(self.store.authenticate(self.access['token']))
        self.wireguard.policy({'id':self.access['id'],'suspended':False})
        self.assertEqual(len(engine.update.call_args.args[0]),1)
        self.assertEqual(read_json(self.store.path)['clients'][0]['wireguard_public_key'],before['wireguard_public_key'])
        self.assertEqual(self.store.authenticate(self.access['token']),self.access['id'])
        self.wireguard.revoke(self.access['id'])
        self.wireguard.policy({'id':self.access['id'],'suspended':False})
        self.assertEqual(engine.update.call_args.args[0],[])
        self.assertIsNone(self.store.authenticate(self.access['token']))

    def test_real_udp_revocation_direct_gateway_denial_and_other_peer_survives(self):
        other=self.store.issue('Second transport')
        other_profile=self.wireguard.new_peer(other)
        engine=Engine({'role':'server','wireguard':{'private_key':self.wireguard.vault()['private_key']},'listen_port':0,
                       'upstream_port':self.gateway.server_port,'peers':self.wireguard.peers()})
        self.wireguard.engine=engine
        endpoint=f'127.0.0.1:{engine.port}'
        first=test_remote.client.Remote(self.profile,endpoint=endpoint)
        second=test_remote.client.Remote(other_profile,endpoint=endpoint)
        try:
            self.assertTrue(first.check()['connected']);self.assertTrue(second.check()['connected'])
            with second.open('/v1/device',json.dumps({'kind':'tablet','version':'fixture','transport':'wireguard'}).encode()) as response:
                self.assertEqual(json.load(response)['id'],other['id'])
            self.wireguard.revoke(self.access['id'])
            with self.assertRaises(urllib.error.HTTPError) as error:self.request('/v1/models')
            self.assertEqual(error.exception.code,401);error.exception.close()
            request=urllib.request.Request(first.bridge.url+'/v1/models',headers={'X-Qwen-Bridge':first.bridge.key})
            with self.assertRaises(OSError):urllib.request.urlopen(request,timeout=2)
            with second.open('/v1/chat/completions',json.dumps({'messages':[{'role':'user','content':'Other still works'}],'stream':True}).encode()) as response:
                self.assertIn(b'[DONE]',response.read())
            self.assertEqual(self.store.authenticate(other['token']),other['id'])
            self.assertEqual(len(self.wireguard.peers()),1)
        finally:first.close();second.close()

    def test_maintenance_is_explicit_and_cannot_activate_tunnel(self):
        self.store.maintenance=True
        self.assertIsNone(self.store.authenticate(self.access['token']))
        self.assertFalse(self.store.valid_owner(self.access['id']))
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/v1/models')
        self.assertEqual(error.exception.code,503)
        self.assertEqual(json.load(error.exception)['error']['code'],'maintenance');error.exception.close()
        with self.assertRaisesRegex(ValueError,'maintenance'):self.wireguard.activate()

    def test_windows_reports_metadata_and_tolerates_previous_server(self):
        recorded=[]
        class Opener:
            def open(inner,request,timeout):
                if request.selector=='/v1/device':recorded.append(json.loads(request.data))
                request.full_url=self.url+request.selector
                return urllib.request.urlopen(request,timeout=timeout)
        client=test_remote.client.Remote(self.profile,Opener())
        try:
            self.assertTrue(client.check()['connected'])
            self.assertTrue(client.check()['connected'])
            self.assertEqual(len(recorded),1)
            self.assertEqual(recorded[0]['kind'],'pc')
            self.assertEqual(self.store.metadata()['clients'][0]['reported_kind'],'pc')
        finally:client.close()
        class Older(Opener):
            def open(inner,request,timeout):
                if request.selector=='/v1/device':
                    raise urllib.error.HTTPError(request.full_url,404,'Previous server',{},io.BytesIO(b'{"error":{"message":"Route non disponible."}}'))
                return super().open(request,timeout)
        client=test_remote.client.Remote(self.profile,Older())
        try:self.assertTrue(client.check()['connected'])
        finally:client.close()

    def test_revocation_interrupts_stalled_stream_without_late_output(self):
        first_chunk=threading.Event();release=threading.Event();received=threading.Event();done=threading.Event()
        body=[];failures=[]
        def stalled(handler):
            handler.rfile.read(int(handler.headers['Content-Length']))
            handler.send_response(200);handler.send_header('Content-Type','text/event-stream');handler.end_headers()
            handler.wfile.write(b'data: {"choices":[{"delta":{"content":"start"}}]}\n\n');handler.wfile.flush()
            first_chunk.set()
            release.wait(10)
            try:
                handler.wfile.write(b'data: {"choices":[{"delta":{"content":"late private output"}}]}\n\ndata: [DONE]\n\n')
                handler.wfile.flush()
            except OSError:pass
        def consume():
            try:
                with self.request('/v1/chat/completions',{'messages':[{'role':'user','content':'stalled test'}],'stream':True}) as response:
                    while True:
                        line=response.readline()
                        if not line:break
                        body.append(line)
                        if b'"start"' in line:received.set()
            except OSError as error:failures.append(type(error).__name__)
            finally:done.set()
        with patch.object(test_remote.FakeModel,'do_POST',stalled):
            thread=threading.Thread(target=consume,daemon=True);thread.start()
            try:
                self.assertTrue(first_chunk.wait(3));self.assertTrue(received.wait(3))
                before=time.monotonic();self.store.revoke(self.access['id'])
                self.assertTrue(done.wait(3),'Revocation must close a blocked upstream read')
                self.assertLess(time.monotonic()-before,3)
                data=b''.join(body)
                self.assertIn(b'"start"',data)
                self.assertNotIn(b'late private output',data)
                self.assertNotIn(b'[DONE]',data)
                self.assertFalse(self.store.accounts.valid(self.access['id'],self.session))
            finally:release.set();thread.join(3)


if __name__=='__main__':unittest.main()
