"""Failure and concurrency regressions from the two Fred audits."""
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from core import HOME, ROOT
import test_remote
client = test_remote.client
sys.path.insert(0, str(ROOT/'client-qwen'))
import history_store
import updater
from signing import public, sign

class AuditTests(unittest.TestCase):
    def test_history_corruption_conflict_and_atomic_failure_preserve_original(self):
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            path=Path(folder)/'history.dpapi'
            history={'conversations':[{'id':'a','title':'Test','messages':[]}],'currentId':'a'}
            first=history_store.write(path,client.protect,history,'');original=path.read_bytes()
            self.assertEqual(history_store.read(path,client.protect)['history'],history)
            with self.assertRaises(history_store.HistoryConflict):history_store.write(path,client.protect,history,'')
            with patch.object(history_store.os,'replace',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):history_store.write(path,client.protect,history,first['revision'])
            self.assertEqual(path.read_bytes(),original)
            path.write_bytes(b'corrupt fixture')
            with self.assertRaises(history_store.HistoryError):history_store.read(path,client.protect)
            with self.assertRaises(history_store.HistoryError):history_store.write(path,client.protect,history,'')
            self.assertEqual(path.read_bytes(),b'corrupt fixture')

    def test_history_rejects_duplicate_ids_invalid_messages_and_excess(self):
        row={'id':'a','title':'Test','messages':[]}
        for rows in [[row,row],[{**row,'messages':[{'role':'assistant','content':42}]}],[row]*201]:
            with self.subTest(rows=len(rows)),self.assertRaises(history_store.HistoryError):history_store.validate({'conversations':rows,'currentId':'a'})

    def test_history_recovery_keeps_encrypted_original_and_refuses_valid_history(self):
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            path=Path(folder)/'history.dpapi';path.write_bytes(b'unreadable fixture')
            history={'conversations':[{'id':'a','title':'Test','messages':[]}],'currentId':'a'}
            result=history_store.recover(path,client.protect,history)
            self.assertEqual((path.parent/result['backup']).read_bytes(),b'unreadable fixture')
            self.assertEqual(history_store.read(path,client.protect)['history'],history)
            with self.assertRaises(history_store.HistoryError):history_store.recover(path,client.protect,history)

    def test_two_processes_cannot_overwrite_the_same_history_revision(self):
        import subprocess,time
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            home=Path(folder);path=home/'history.dpapi'
            history={'conversations':[{'id':'a','title':'Test','messages':[]}],'currentId':'a'}
            revision=history_store.write(path,client.protect,history,'')['revision']
            code="""import sys,time,json
from pathlib import Path
from client import protect
import history_store
home=Path(sys.argv[1]);identity=sys.argv[2];revision=sys.argv[3]
(home/(identity+'.ready')).write_text('ready')
deadline=time.monotonic()+10
while not (home/'go').exists():
 if time.monotonic()>deadline:sys.exit(8)
 time.sleep(.01)
history={'conversations':[{'id':'a','title':identity,'messages':[]}],'currentId':'a'}
try:history_store.write(home/'history.dpapi',protect,history,revision)
except history_store.HistoryConflict:sys.exit(7)
"""
            workers=[subprocess.Popen([sys.executable,'-c',code,str(home),name,revision],cwd=ROOT/'client-qwen') for name in ('one','two')]
            try:
                deadline=time.monotonic()+10
                while len(list(home.glob('*.ready')))!=2:
                    if time.monotonic()>deadline:self.fail('History workers did not start')
                    time.sleep(.01)
                (home/'go').write_text('go')
                self.assertEqual(sorted(worker.wait(timeout=10) for worker in workers),[0,7])
            finally:
                for worker in workers:
                    if worker.poll() is None:worker.kill();worker.wait(timeout=10)

    def test_rollback_is_transactional_and_keeps_new_client_metadata(self):
        import releases,struct
        from wg_crypto import keypair
        from core import write_json,read_json
        from profiles import public_key
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            root=Path(folder);home=root/'home';home.mkdir();clients=home/'clients';clients.mkdir()
            dist=root/'client-qwen/dist';dist.mkdir(parents=True);(dist/'Accès serveur Fred.exe').write_bytes(b'new fixture')
            records=[]
            for number in (2,3):
                identity=f'{number:016x}';private,key=keypair();token='qwen_'+identity+'_'+secrets.token_urlsafe(32)
                profile={'url':'wireguard://10.77.0.1:8766','transport':'wireguard','token':token,'wireguard':{'private_key':private,'server_public_key':key,'preshared_key':key,'address':f'10.77.0.{number}/32','endpoint':'127.0.0.1:51820'}}
                raw=json.dumps(profile).encode();(clients/(identity+'.exe')).write_bytes(b'old fixture'+raw+struct.pack('<I',len(raw))+b'QWENPROFILE1')
                records.append({'id':identity,'revoked':False,'hash':hashlib.sha256(token.encode()).hexdigest(),'address':profile['wireguard']['address'],'wireguard_public_key':public_key(private)})
            write_json(home/'acces-distants.json',{'enabled':False,'url':'wireguard://10.77.0.1:8766','clients':records})
            with patch.object(releases,'ROOT',root):releases.manifest(home);releases.repackage(home)
            versions=read_json(home/'versions-clients.json');versions['new-client']={'version':'9.0.0'};write_json(home/'versions-clients.json',versions)
            originals={p:p.read_bytes() for p in clients.glob('*.exe')};replace=Path.replace;failed=[False]
            def fail_second(path,target):
                if path.parent.name.startswith('retour-') and path.stem==records[1]['id'] and not failed[0]:failed[0]=True;raise OSError('simulated disk failure')
                return replace(path,target)
            with patch.object(Path,'replace',fail_second),self.assertRaises(OSError):releases.rollback(home)
            self.assertEqual({p:p.read_bytes() for p in originals},originals)
            self.assertEqual(read_json(home/'versions-clients.json'),versions)
            releases.rollback(home);self.assertEqual(read_json(home/'versions-clients.json')['new-client'],{'version':'9.0.0'})

    def test_distribution_rejects_swapped_device_token_or_wireguard_key(self):
        import copy
        from profiles import match
        fixture=test_remote.RemoteTests();fixture.setUp()
        try:
            record=json.loads(fixture.store.path.read_text())['clients'][0]
            match(record,fixture.profile)
            for field in ('private_key','address'):
                changed=copy.deepcopy(fixture.profile)
                changed['wireguard'][field]=fixture.profile['wireguard']['server_public_key'] if field=='private_key' else '10.77.0.3/32'
                with self.assertRaises(ValueError):match(record,changed)
            changed=copy.deepcopy(fixture.profile);changed['token']='qwen_'+record['id']+'_'+secrets.token_urlsafe(32)
            with self.assertRaises(ValueError):match(record,changed)
        finally:fixture.tearDown()

    def test_closing_waits_for_history_and_cancels_close_after_failed_save(self):
        import time
        from types import SimpleNamespace
        class Event:
            def __iadd__(self,callback):self.callback=callback;return self
        class Window:
            def __init__(self):self.events=SimpleNamespace(closing=Event());self.callback=None;self.closed=False
            def evaluate_js(self,script,callback):self.callback=callback
            def create_confirmation_dialog(self,*args):return False
            def destroy(self):self.closed=True
        window=Window();state=client.install_close_guard(window)
        self.assertFalse(window.events.closing.callback())
        deadline=time.monotonic()+2
        while window.callback is None and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(window.closed);window.callback({'saved':False,'message':'disk full'})
        self.assertFalse(state['pending']);self.assertFalse(window.closed)
        self.assertFalse(window.events.closing.callback());time.sleep(.03);window.callback({'saved':True})
        self.assertTrue(window.closed);self.assertTrue(window.events.closing.callback())

    def test_restore_rejects_mixed_device_keys_before_mutation(self):
        from app import Controller
        from operations import cipher
        from wg_crypto import protect
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            home=Path(folder);c=Controller(home,include_legacy=False);password='test backup phrase long enough'
            c.wireguard.configure({'public_host':'127.0.0.1','listen_port':51820})
            access=c.remote.issue('Test');profile=c.wireguard.new_peer(access)
            (c.wireguard.directory/'profils-restaures.dpapi').write_bytes(protect(json.dumps({access['id']:profile}).encode()))
            backup=Path(c.operations.backup(password)['file']);blob=backup.read_bytes();salt=blob[11:27]
            package=json.loads(cipher(password,salt).decrypt(blob[27:]));package['files']['profiles'][access['id']]['wireguard']['address']='10.77.0.3/32'
            bad=home/'bad.qwenbackup';bad.write_bytes(blob[:27]+cipher(password,salt).encrypt(json.dumps(package).encode()))
            before={p:p.read_bytes() for p in [c.remote.path,c.wireguard.vault_path,c.wireguard.settings_path]}
            with patch.object(c,'processes',return_value=[]),patch.object(c,'supervisor',return_value=None),self.assertRaises(ValueError):c.operations.restore({'file':str(bad),'password':password})
            self.assertEqual({p:p.read_bytes() for p in before},before)

    def test_unsigned_binary_cannot_issue_a_new_access(self):
        fixture=test_remote.RemoteTests();fixture.setUp()
        try:
            before=len(fixture.store.metadata()['clients'])
            with patch('releases.status',return_value={'verified':False}),self.assertRaises(ValueError):fixture.wireguard.create_client('Unverified test','test-model')
            self.assertEqual(len(fixture.store.metadata()['clients']),before)
        finally:fixture.tearDown()

    def test_signed_release_rejects_malformed_version_digest_and_protocol(self):
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            home=Path(folder);release={'version':'3.2.0','protocol':3,'bytes':10,'sha256':'a'*64}
            for changes in [{'version':'-1.2.3'},{'version':'01.2.3'},{'version':'1.2.3.4'},{'sha256':'A'*64},{'sha256':'bad'},{'protocol':3.0}]:
                with self.subTest(changes=changes),self.assertRaises(ValueError):updater.verify(sign({**release,**changes},home),public(home))

    def test_inference_blocks_update_and_endpoint_without_starting_helper(self):
        fixture=test_remote.RemoteTests();fixture.setUp()
        try:
            remote=client.Remote(fixture.profile,opener=object());remote.active_requests=1
            with patch.object(updater,'prepare') as prepare:
                with self.assertRaises(ValueError):remote.update(True)
                prepare.assert_not_called()
            before=remote.endpoint
            with self.assertRaises(ValueError):remote.set_endpoint('127.0.0.1:10')
            self.assertEqual(remote.endpoint,before)
        finally:fixture.tearDown()

    def test_truncated_stream_has_explicit_error_and_releases_active_counter(self):
        fixture=test_remote.RemoteTests();fixture.setUp()
        class Response(io.BytesIO):
            status=200
        try:
            remote=client.Remote(fixture.profile,opener=object());key=secrets.token_urlsafe(32)
            server=client.serve_local(remote,key,0);threading.Thread(target=server.serve_forever,daemon=True).start()
            with patch.object(remote,'open',return_value=Response(b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n')):
                request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/v1/chat/completions',b'{"stream":true}',{'Authorization':'Bearer '+key,'Content-Type':'application/json'})
                with urllib.request.urlopen(request) as response:body=response.read()
                self.assertIn(b'partial',body);self.assertIn(b'"error"',body)
                self.assertEqual(remote.active_requests,0)
        finally:
            if 'server' in locals():server.shutdown();server.server_close()
            fixture.tearDown()

if __name__=='__main__':unittest.main()
