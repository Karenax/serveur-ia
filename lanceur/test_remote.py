"""Gateway access, portable client and real encrypted WireGuard UDP checks."""
import importlib.util
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import sys
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from core import ROOT, HOME
from remote import AccessStore, serve_gateway, chat_request, secure_url
from wireguard_access import WireGuardAccess,Engine
from wg_crypto import keypair

spec = importlib.util.spec_from_file_location('qwen_client', ROOT / 'client-qwen/client.py')
sys.path.insert(0,str(ROOT/'client-qwen'))
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
from wg_bridge import validate_endpoint,connection_candidates

class FakeModel(BaseHTTPRequestHandler):
    captured = []
    def log_message(self, *args):
        pass
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"default_generation_settings":{"n_ctx":262144}}' if self.path=='/props' else b'{"service":"strata","loaded":true}')
    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.captured.append((dict(self.headers), data))
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream' if data.get('stream') else 'application/json')
        self.end_headers()
        if self.path=='/v1/messages/count_tokens':
            self.wfile.write(json.dumps({'input_tokens':len(json.dumps(data).encode())}).encode());return
        if data.get('stream'):
            self.wfile.write(b'data: {"choices":[{"delta":{"content":"Bonjour"}}]}\n\ndata: [DONE]\n\n')
        else:
            self.wfile.write(b'{"choices":[{"message":{"content":"Bonjour"}}]}')

class RemoteTests(unittest.TestCase):
    def test_https_mode_preserves_personal_access_without_starting_wireguard(self):
        from connection_settings import HTTPS_ENDPOINT
        requests=[]
        class Opener:
            def open(inner,request,timeout):
                requests.append(request)
                return io.BytesIO(b'{"data":[{"id":"https-model"}]}')
        remote=client.Remote(self.profile,endpoint=HTTPS_ENDPOINT)
        remote.https_opener=Opener()
        remote.session=self.session
        with patch.object(client,'Bridge',side_effect=AssertionError('HTTPS must not start WireGuard')):
            state=remote.check()
            self.assertTrue(state['connected']);self.assertEqual(state['transport'],'https')
            self.assertEqual(state['bridge_starts'],0)
            for path in ('/v1/history','/v1/workspace/action','/v1/client/release','/v1/client/download','/v1/chat/completions'):
                with remote.open(path,b'{}'):pass
        for request in requests:
            self.assertTrue(request.full_url.startswith(HTTPS_ENDPOINT+'/v1/'))
            self.assertEqual(request.get_header('Authorization'),'Bearer '+self.access['token'])
            self.assertEqual(request.get_header('X-qwen-session'),self.session)
            self.assertIsNone(request.get_header('X-qwen-bridge'))
        self.assertNotIn(self.access['token'],json.dumps(state))
        with patch.dict('os.environ',{'LOCALAPPDATA':self.temporary.name}):
            original=client.local_key(self.profile)
            client.save_endpoint(self.profile,HTTPS_ENDPOINT)
            self.assertEqual(client.client_settings(self.profile)['endpoint'],HTTPS_ENDPOINT)
            self.assertEqual(client.local_key(self.profile),original)
        remote.set_endpoint(None)
        self.assertEqual(remote.state()['transport'],'wireguard')
        self.assertEqual(remote.profile,self.profile)

    def test_https_redirect_never_forwards_personal_token(self):
        from connection_settings import HTTPS_ENDPOINT
        redirected=[]
        class Redirector(BaseHTTPRequestHandler):
            def log_message(inner,*args):pass
            def do_GET(inner):
                if inner.path=='/start':
                    inner.send_response(302);inner.send_header('Location','/capture');inner.end_headers()
                else:
                    redirected.append(dict(inner.headers));inner.send_response(200);inner.end_headers()
        server=ThreadingHTTPServer(('127.0.0.1',0),Redirector)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        remote=client.Remote(self.profile,endpoint=HTTPS_ENDPOINT)
        try:
            request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/start',headers={'Authorization':'Bearer fixture'})
            with self.assertRaises(urllib.error.HTTPError) as error:remote.https_opener.open(request,timeout=3)
            self.assertEqual(error.exception.code,302);error.exception.close()
            self.assertEqual(redirected,[])
            tls=next(h for h in remote.https_opener.handlers if isinstance(h,urllib.request.HTTPSHandler))
            if tls._context is not None:
                import ssl
                self.assertEqual(tls._context.verify_mode,ssl.CERT_REQUIRED)
                self.assertTrue(tls._context.check_hostname)
        finally:server.shutdown();server.server_close()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=HOME)
        self.store = AccessStore(Path(self.temporary.name))
        self.access = self.store.issue('Test uniquement')
        self.wireguard=WireGuardAccess(self.store,Path(self.temporary.name))
        self.wireguard.configure({'public_host':'127.0.0.1','listen_port':51820})
        self.profile={**self.wireguard.new_peer(self.access),'model':'test-model'}
        self.profile['local_routes']=[]  # All network tests target their isolated, ephemeral server.
        self.store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        self.store.accounts.configure({'id':self.access['id'],'username':'test-client','password':'test-password-long'},self.store.metadata()['clients'])
        self.session=self.store.accounts.login(self.access['id'],'test-client','test-password-long')['session']
        self.fake = ThreadingHTTPServer(('127.0.0.1', 0), FakeModel)
        self.gateway = serve_gateway(self.store, lambda: (self.fake.server_port, 'test-model', 'private-upstream-key'), 0)
        for server in (self.fake, self.gateway):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        self.url = f'http://127.0.0.1:{self.gateway.server_port}'
    def tearDown(self):
        self.wireguard.close()
        for server in (self.gateway, self.fake):
            server.shutdown()
            server.server_close()
        self.temporary.cleanup()
    def request(self, path, body=None, token=None):
        headers = {'Authorization': 'Bearer ' + (token or self.access['token']), 'Content-Type': 'application/json','X-Qwen-Session':self.session}
        return urllib.request.urlopen(urllib.request.Request(self.url + path, json.dumps(body).encode() if body is not None else None, headers), timeout=5)
    def test_key_never_stored_in_plaintext_and_revocation(self):
        self.assertNotIn(self.access['token'], self.store.path.read_text())
        self.assertNotIn('hash', self.store.metadata()['clients'][0])
        with self.request('/v1/models') as response:
            self.assertEqual(json.load(response)['data'][0]['id'], 'test-model')
        self.store.revoke(self.access['id'])
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/v1/models')
        self.assertEqual(error.exception.code, 401)
    def test_private_routes_and_mcp_rejected(self):
        for path in ('/api/state', '/settings', '/unload', '/load', '/v1/unload', '/mcp'):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request(path)
            self.assertEqual(error.exception.code, 404)
        with self.assertRaises(ValueError):
            chat_request({'messages':[{'role':'user','content':'test'}], 'strata_mcp':True}, 'm')
        for url in ('http://test.invalid','https://test.invalid','wireguard://192.168.1.1:80','wireguard://10.77.0.1:8766/?token=x'):
            with self.assertRaises(ValueError):
                secure_url(url)
    def test_streaming_and_private_upstream_key(self):
        with self.request('/v1/chat/completions', {'messages':[{'role':'user','content':'test'}], 'stream':True}) as response:
            data=response.read()
        self.assertIn(b'Bonjour', data)
        self.assertIn(b'[DONE]', data)
        headers, request = FakeModel.captured[-1]
        self.assertEqual(headers['Authorization'], 'Bearer private-upstream-key')
        self.assertFalse(request['strata_mcp'])
        self.assertEqual(request['model'], 'test-model')
        self.assertNotIn(self.access['token'], json.dumps(headers))
    def test_response_caps_are_removed_even_for_legacy_clients(self):
        from core import read_json,write_json
        data=read_json(self.store.path);before=data['clients'][0]['hash'];data['clients'][0]['max_tokens']=1;write_json(self.store.path,data)
        AccessStore(self.store.home)
        migrated=read_json(self.store.path);self.assertNotIn('max_tokens',migrated['clients'][0]);self.assertTrue(migrated['clients'][0]['hash']==before)
        for limit in (1,4096,999999):
            with self.request('/v1/chat/completions',{'messages':[{'role':'user','content':'test'}],'max_tokens':limit,'max_completion_tokens':limit}) as response:response.read()
            request=FakeModel.captured[-1][1]
            self.assertEqual(request['max_tokens'],-1)
            self.assertNotIn('max_completion_tokens',request)
    def test_server_history_requires_personal_access_and_is_isolated(self):
        history={'currentId':'test','conversations':[{'id':'test','title':'Privée','messages':[{'role':'user','content':'texte personnel'}]}]}
        with self.request('/v1/history',{'history':history,'revision':0,'reset_id':'20261006-remove-assistants'}) as response:self.assertEqual(json.load(response)['revision'],1)
        with self.request('/v1/history') as response:self.assertEqual(json.load(response)['history'],history)
        other=self.store.issue('Second accès isolé')
        with self.request('/v1/history',token=other['token']) as response:self.assertIsNone(json.load(response)['history'])
        with self.assertRaises(urllib.error.HTTPError) as conflict:self.request('/v1/history',{'history':history,'revision':0})
        self.assertEqual(conflict.exception.code,409)
        self.store.revoke(self.access['id'])
        with self.assertRaises(urllib.error.HTTPError):self.request('/v1/history')
    def test_end_to_end_local_api_hides_remote_credentials(self):
        # This fixture bypasses the WireGuard engine; a separate test exercises real encrypted UDP.
        class MockOpener:
            def open(inner, request, timeout):
                request.full_url = self.url + request.selector
                return urllib.request.urlopen(request, timeout=timeout)
        remote = client.Remote(self.profile, MockOpener())
        remote.session=self.session
        key = secrets.token_urlsafe(32)
        local = client.serve_local(remote, key, 0)
        threading.Thread(target=local.serve_forever, daemon=True).start()
        try:
            self.assertTrue(remote.check()['connected'])
            with urllib.request.urlopen(f'http://127.0.0.1:{local.server_port}/chat', timeout=5) as page:
                html = page.read().decode()
                self.assertIn('Accès serveur Fred', html)
                self.assertIn(key, html)
                self.assertNotIn(self.access['token'], html)
                self.assertIn("frame-ancestors 'none'", page.headers['Content-Security-Policy'])
            address = f'http://127.0.0.1:{local.server_port}/v1/chat/completions'
            request = urllib.request.Request(address, json.dumps({'messages':[{'role':'user','content':'test'}], 'stream':True}).encode(), {'Authorization':'Bearer '+key,'Content-Type':'application/json','Origin':f'http://127.0.0.1:{local.server_port}'})
            self.assertIn(b'Bonjour', urllib.request.urlopen(request, timeout=5).read())
            request.add_header('Origin', 'https://other.invalid')
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request, timeout=5)
            self.assertEqual(error.exception.code,403)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(urllib.request.Request(address, b'{}', {'Content-Type':'application/json'}))
            self.assertEqual(error.exception.code,401)
            self.store.configure({'enabled':False,'url':'wireguard://10.77.0.1:8766'})
            self.assertFalse(remote.check()['connected'])
        finally:
            local.shutdown()
            local.server_close()
    def test_unloaded_backend_does_not_receive_generation(self):
        before = len(FakeModel.captured)
        with patch('remote.health', return_value={'loaded':False}):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/v1/chat/completions', {'messages':[{'role':'user','content':'test'}]})
        self.assertEqual(error.exception.code,503)
        self.assertEqual(len(FakeModel.captured),before)
    def test_windows_protection_and_preconfigured_exe_startup(self):
        raw = b'secret test only'
        encrypted = client.protect(raw)
        self.assertNotEqual(encrypted,raw)
        self.assertEqual(client.protect(encrypted,decrypt=True),raw)
        import releases
        # This isolated server has its own signing identity; verify the production build's
        # integrity, then authorize that known fixture for this disposable recipient.
        verified=releases.status(HOME);self.assertTrue(verified['verified'])
        with patch.object(releases,'status',return_value=verified):exe = self.wireguard.create_client('Test executable', 'test-model')
        path = Path(self.temporary.name) / 'clients' / (exe['id']+'.exe')
        result = Path(self.temporary.name) / 'result.txt'
        process = subprocess.Popen([str(path),'--self-test','--with-profile','--result',str(result)])
        self.assertEqual(process.wait(timeout=30),0)
        self.assertEqual(result.read_text(encoding='utf-8'),'Accès serveur Fred self-test OK')

    def test_real_wireguard_udp_api_streaming_and_peer_revocation(self):
        engine=Engine({'role':'server','wireguard':{'private_key':self.wireguard.vault()['private_key']},
                      'listen_port':0,'upstream_port':self.gateway.server_port,'peers':self.wireguard.peers()})
        profile=json.loads(json.dumps(self.profile))
        profile['wireguard']['endpoint']=f'127.0.0.1:{engine.port}'
        remote=client.Remote(profile)
        remote.session=self.session
        try:
            self.assertTrue(remote.check()['connected'])
            with remote.open('/v1/status') as response:
                self.assertEqual(json.load(response)['protocol'], 3)
            with remote.open('/v1/cancel', b'{}') as response:
                self.assertTrue(json.load(response)['cancelled'])
            with remote.open('/v1/chat/completions',json.dumps({'messages':[{'role':'user','content':'test'}],'stream':True}).encode()) as response:
                self.assertIn(b'Bonjour',response.read())
            self.store.revoke(self.access['id']);engine.update(self.wireguard.peers())
            request=urllib.request.Request(remote.bridge.url+'/v1/models',headers={'X-Qwen-Bridge':remote.bridge.key})
            with self.assertRaises(OSError):urllib.request.urlopen(request,timeout=2)
        finally:
            remote.close();engine.close()

    def test_wrong_wireguard_secret_cannot_reach_api(self):
        engine=Engine({'role':'server','wireguard':{'private_key':self.wireguard.vault()['private_key']},
                      'listen_port':0,'upstream_port':self.gateway.server_port,'peers':self.wireguard.peers()})
        profile=json.loads(json.dumps(self.profile))
        profile['wireguard']['endpoint']=f'127.0.0.1:{engine.port}'
        profile['wireguard']['preshared_key']=keypair()[0]
        remote=client.Remote(profile)
        remote.session=self.session
        try:
            state=remote.check()
            self.assertFalse(state['connected']);self.assertFalse(state['reachable'])
            self.assertFalse(state.get('handshake',False))
            self.assertEqual(state['code'],'wireguard_unreachable')
        finally:
            remote.close();engine.close()

    def test_local_network_selection_and_endpoint_validation(self):
        profile=json.loads(json.dumps(self.profile))
        profile['wireguard']['endpoint']='198.51.100.10:51820'
        profile['local_routes']=[{'endpoint':'192.168.1.40:51820','network':'192.168.1.0/24'}]
        self.assertEqual(connection_candidates(profile,{'192.168.1.60'}),['192.168.1.40:51820','198.51.100.10:51820'])
        self.assertEqual(connection_candidates(profile,{'192.168.1.40'}),['127.0.0.1:51820','192.168.1.40:51820','198.51.100.10:51820'])
        self.assertEqual(connection_candidates(profile,{'192.168.2.60'}),['198.51.100.10:51820'])
        for endpoint in ('http://192.168.1.40:51820','192.168.1.40:8080/v1','x:0','x:65536','x:51820\nprivate_key=secret','::1:51820'):
            with self.assertRaises(ValueError):validate_endpoint(endpoint)
        self.assertEqual(validate_endpoint(' [::1]:51820 '),'[::1]:51820')

    def test_reconnect_preserves_keys_and_protected_settings(self):
        engine=Engine({'role':'server','wireguard':{'private_key':self.wireguard.vault()['private_key']},
                      'listen_port':0,'upstream_port':self.gateway.server_port,'peers':self.wireguard.peers()})
        endpoint=f'127.0.0.1:{engine.port}'
        remote=client.Remote(self.profile,endpoint='127.0.0.1:1')
        remote.session=self.session
        try:
            self.assertIsNone(remote.bridge)  # A bad address must not prevent showing the editable window.
            keys={name:self.profile['wireguard'][name] for name in ('private_key','server_public_key','preshared_key')}
            remote.set_endpoint(endpoint)
            state=remote.check()
            self.assertTrue(state['connected']);self.assertTrue(state['handshake'])
            self.assertEqual(state['endpoint'],endpoint)
            self.assertNotIn('private_key',state);self.assertNotIn('preshared_key',state)
            self.assertNotIn(self.access['token'],json.dumps(state))
            request=urllib.request.Request(remote.bridge.url+'/bridge/status')
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request,timeout=3)
            self.assertEqual(error.exception.code,403)
            self.assertEqual({name:remote.profile['wireguard'][name] for name in keys},keys)
            with patch.dict('os.environ',{'LOCALAPPDATA':self.temporary.name}):
                original=client.local_key(self.profile)
                client.save_endpoint(self.profile,endpoint)
                self.assertEqual(client.client_settings(self.profile)['endpoint'],endpoint)
                self.assertEqual(client.local_key(self.profile),original)
                self.assertNotIn(endpoint,client.settings_path(self.profile).read_bytes().decode(errors='ignore'))
                client.save_endpoint(self.profile,None)
                self.assertNotIn('endpoint',client.client_settings(self.profile))
                self.assertEqual(client.local_key(self.profile),original)
        finally:remote.close();engine.close()

    def test_unloaded_model_is_distinct_from_unreachable_tunnel(self):
        engine=Engine({'role':'server','wireguard':{'private_key':self.wireguard.vault()['private_key']},
                      'listen_port':0,'upstream_port':self.gateway.server_port,'peers':self.wireguard.peers()})
        remote=client.Remote(self.profile,endpoint=f'127.0.0.1:{engine.port}')
        remote.session=self.session
        before=len(FakeModel.captured)
        try:
            with patch('remote.health',return_value={'loaded':False}):state=remote.check()
            self.assertFalse(state['connected']);self.assertTrue(state['reachable']);self.assertTrue(state['handshake'])
            self.assertEqual(state['code'],'model_unloaded')
            self.assertEqual(len(FakeModel.captured),before)
        finally:remote.close();engine.close()

    def test_automatic_fallback_reaches_authenticated_server(self):
        engine=Engine({'role':'server','wireguard':{'private_key':self.wireguard.vault()['private_key']},
                      'listen_port':0,'upstream_port':self.gateway.server_port,'peers':self.wireguard.peers()})
        endpoint=f'127.0.0.1:{engine.port}'
        with patch.object(client,'connection_candidates',return_value=['127.0.0.1:1',endpoint]):remote=client.Remote(self.profile)
        remote.session=self.session
        try:
            state=remote.check()
            self.assertTrue(state['connected']);self.assertTrue(state['automatic'])
            self.assertEqual(state['endpoint'],endpoint);self.assertTrue(state['handshake'])
        finally:remote.close();engine.close()

    def test_live_backend_model_name_is_used_for_api_and_generation(self):
        with patch('remote.health',return_value={'loaded':True,'model':'actual-loaded-model'}):
            with self.request('/v1/models') as response:self.assertEqual(json.load(response)['data'][0]['id'],'actual-loaded-model')
            with self.request('/v1/chat/completions',{'messages':[{'role':'user','content':'test'}],'model':'outdated-profile'}):pass
        self.assertEqual(FakeModel.captured[-1][1]['model'],'actual-loaded-model')

    def test_client_discovers_models_and_tracks_inventory_changes(self):
        inventory=[{'id':'alpha'},{'id':'beta'},{'id':'alpha'},None,{'id':42}]
        class InventoryOpener:
            def open(inner,request,timeout):return io.BytesIO(json.dumps({'data':inventory}).encode())
        remote=client.Remote({**self.profile,'model':'obsolete-hardcoded-model'},InventoryOpener())
        remote.session=self.session
        self.assertEqual(remote.model,'');self.assertEqual(remote.models,[])
        self.assertEqual(remote.check()['models'],['alpha','beta'])
        remote.select_model('beta');self.assertEqual(remote.check()['model'],'beta')
        with self.assertRaises(ValueError):remote.select_model('unadvertised')
        inventory[:]=[{'id':'gamma'}]
        self.assertEqual(remote.check()['model'],'gamma')
        inventory.clear();state=remote.check()
        self.assertTrue(state['reachable']);self.assertFalse(state['connected'])
        self.assertEqual(state['models'],[]);self.assertEqual(state['model'],'')
        self.assertEqual(state['code'],'no_models')

    def test_api_failure_updates_connection_and_keeps_error_body(self):
        failing=False
        class Opener:
            def open(inner,request,timeout):
                if failing:
                    raw=b'{"error":{"code":"wireguard_unreachable","message":"Tunnel indisponible"}}'
                    raise urllib.error.HTTPError(request.full_url,503,'Unavailable',{},io.BytesIO(raw))
                return io.BytesIO(b'{"data":[{"id":"test-model"}]}')
        remote=client.Remote(self.profile,Opener())
        self.assertTrue(remote.check()['connected'])
        failing=True
        with self.assertRaises(urllib.error.HTTPError) as error:remote.open('/v1/workspace')
        self.assertEqual(json.load(error.exception)['error']['code'],'wireguard_unreachable')
        error.exception.close()
        self.assertTrue(remote.state()['connected'])  # A workspace timeout is only one failed request.
        remote.failure('wireguard_unreachable','Tunnel indisponible',confirmed=True)
        self.assertFalse(remote.state()['connected']);self.assertFalse(remote.state()['reachable'])
        self.assertEqual(remote.state()['code'],'wireguard_unreachable')
        self.assertNotIn(self.access['token'],json.dumps(remote.state()))
        remote.active_requests=1
        self.assertFalse(remote.check()['connected'])  # A pending chat must not resurrect a stale green status.
        remote.active_requests=0;failing=False
        self.assertTrue(remote.check()['connected'])

    def test_two_personal_profiles_can_use_tunnel_concurrently(self):
        access=self.store.issue('Deuxième personne')
        profile=self.wireguard.new_peer(access);profile['local_routes']=[]
        self.assertNotEqual(profile['wireguard']['private_key'],self.profile['wireguard']['private_key'])
        self.assertNotEqual(profile['wireguard']['preshared_key'],self.profile['wireguard']['preshared_key'])
        self.assertNotEqual(profile['wireguard']['address'],self.profile['wireguard']['address'])
        engine=Engine({'role':'server','wireguard':{'private_key':self.wireguard.vault()['private_key']},
                      'listen_port':0,'upstream_port':self.gateway.server_port,'peers':self.wireguard.peers()})
        endpoint=f'127.0.0.1:{engine.port}'
        remotes=[client.Remote(self.profile,endpoint=endpoint),client.Remote(profile,endpoint=endpoint)]
        remotes[0].session=self.session
        def request(remote):
            self.assertTrue(remote.check()['connected'])
            for _ in range(3):
                with remote.open('/v1/chat/completions',json.dumps({'messages':[{'role':'user','content':'Test simultané'}],'stream':True}).encode()) as response:
                    self.assertIn(b'Bonjour',response.read())
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(request,r) for r in remotes]
                for result in futures:result.result(timeout=40)
        finally:
            for remote in remotes:remote.close()
            engine.close()

if __name__=='__main__':
    unittest.main(verbosity=2)
