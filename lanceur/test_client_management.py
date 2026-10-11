"""Client edits must preserve credentials; removal must revoke both transports."""
import json
from pathlib import Path
import re
import socket
import struct
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request
from urllib.parse import unquote
from app import serve
from core import read_json
import remote
import test_remote


class ClientManagementTests(unittest.TestCase):
    setUp=test_remote.RemoteTests.setUp
    tearDown=test_remote.RemoteTests.tearDown
    request=test_remote.RemoteTests.request

    def test_rename_keeps_token_peer_and_history(self):
        before=read_json(self.store.path)['clients'][0]
        history={'conversations':[{'id':'test','title':'Test','messages':[]}],'currentId':'test'}
        with self.request('/v1/history') as response:state=json.load(response)
        with self.request('/v1/history',{'history':history,'revision':state['revision'],'reset_id':state['reset_id']}) as response:response.read()
        self.store.rename(self.access['id'],'  PC Frédéric  ')
        after=read_json(self.store.path)['clients'][0]
        self.assertEqual(after,{**before,'name':'PC Frédéric'})
        self.assertEqual(self.store.authenticate(self.access['token']),self.access['id'])
        with self.request('/v1/history') as response:self.assertEqual(json.load(response)['history'],history)
        for name in ('', ' '*3, 'x'*81, None, 'PC\r\nInjected'):
            with self.subTest(name=name),self.assertRaises(ValueError):self.store.rename(self.access['id'],name)
        with self.assertRaises(ValueError):self.store.rename('missing','PC')
        self.assertEqual(read_json(self.store.path)['clients'][0],after)

    def test_delete_blocks_api_updates_tunnel_and_preserves_other_client(self):
        other=self.store.issue('Autre PC');self.wireguard.new_peer(other)
        before=next(c for c in read_json(self.store.path)['clients'] if c['id']==other['id'])
        history={'conversations':[{'id':'test','title':'Test','messages':[]}],'currentId':'test'}
        with self.request('/v1/history') as response:state=json.load(response)
        with self.request('/v1/history',{'history':history,'revision':state['revision'],'reset_id':state['reset_id']}) as response:response.read()
        engine=Mock();engine.running.return_value=True;self.wireguard.engine=engine
        self.wireguard.delete(self.access['id'])
        self.assertIsNone(self.store.authenticate(self.access['token']))
        self.assertEqual(read_json(self.store.path)['clients'],[before])
        deleted=read_json(self.store.path)['deleted_clients'][0]
        self.assertEqual(deleted['id'],self.access['id']);self.assertTrue(deleted['revoked'])
        self.assertNotIn('deleted_clients',self.store.metadata())
        engine.update.assert_called_once_with(self.wireguard.peers())
        self.assertEqual(len(engine.update.call_args.args[0]),1)
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/v1/models')
        self.assertEqual(error.exception.code,401);error.exception.close()
        self.assertEqual(self.store.workspace.history_read(self.access['id'])['history'],history)
        from profiles import validate_access
        from app import Controller
        from operations import cipher
        validate_access(read_json(self.store.path))
        controller=Controller(self.temporary.name,include_legacy=False)
        directory=Path(self.temporary.name)/'clients';directory.mkdir()
        blob=json.dumps({**self.profile,'version':'3.5.3'}).encode()
        exe=b'MZfixture'+blob+struct.pack('<I',len(blob))+b'QWENPROFILE1'
        (directory/(self.access['id']+'.exe')).write_bytes(exe)
        (directory/'Acces Fred v3.5.3 - Copie.exe').write_bytes(exe)
        backup=controller.operations.backup('test backup password long')
        raw=Path(backup['file']).read_bytes()
        package=json.loads(cipher('test backup password long',raw[11:27]).decrypt(raw[27:]))
        records=package['files']['acces-distants.json']
        owners={c['id'] for c in records['clients']+records['deleted_clients']}
        controller.remote.workspace.validate_backup(package['files']['workspace'],owners)
        self.assertEqual(set(package['files']['profiles']),{self.access['id']})
        controller.remote.configure({'enabled':False,'url':'wireguard://10.77.0.1:8766'})
        controller.operations.restore({'file':backup['file'],'password':'test backup password long'})
        self.assertEqual(controller.remote.workspace.history_read(self.access['id'])['history'],history)
        self.assertEqual(read_json(self.store.path)['deleted_clients'][0]['id'],self.access['id'])
        with self.assertRaises(ValueError):self.wireguard.delete(self.access['id'])

    def test_failed_deletion_keeps_access_revoked(self):
        write=remote.write_json
        def fail_removal(path,values):
            if path==self.store.path and not any(c['id']==self.access['id'] for c in values['clients']):
                raise OSError('Simulated write failure')
            return write(path,values)
        with patch.object(remote,'write_json',side_effect=fail_removal):
            with self.assertRaises(OSError):self.store.delete(self.access['id'])
        self.assertTrue(read_json(self.store.path)['clients'][0]['revoked'])
        self.assertIsNone(self.store.authenticate(self.access['token']))

    def test_http_edit_and_download_name_are_authenticated_and_consistent(self):
        home=Path(self.temporary.name);directory=home/'clients';directory.mkdir()
        target=directory/(self.access['id']+'.exe')
        profile={**self.profile,'version':'3.5.3'};encoded=json.dumps(profile).encode()
        target.write_bytes(b'MZfixture'+encoded+struct.pack('<I',len(encoded))+b'QWENPROFILE1')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        controller=SimpleNamespace(home=home,remote=self.store,wireguard=self.wireguard,lock=threading.RLock())
        server=serve(port,controller);threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{port}'
        try:
            with urllib.request.urlopen(base) as response:html=response.read().decode()
            token=re.search('name="launcher-token" content="([^"]+)"',html)[1]
            def post(route,data,key=token,origin=base):
                return urllib.request.urlopen(urllib.request.Request(base+route,json.dumps(data).encode(),
                    {'Content-Type':'application/json','Origin':origin,'X-Launcher-Token':key}),timeout=5)
            for route in ('rename','delete'):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    post('/api/remote/'+route,{'id':self.access['id'],'name':'PC'},key='bad')
                self.assertEqual(error.exception.code,403);error.exception.close()
            with post('/api/remote/rename',{'id':self.access['id'],'name':'PC Frédéric'}) as response:self.assertEqual(response.status,200)
            with urllib.request.urlopen(base+'/api/remote/client/'+self.access['id']) as response:
                filename=unquote(response.headers['Content-Disposition'].split("filename*=UTF-8''")[1])
                self.assertEqual(filename,'Accès serveur Fred 3.5.3 - PC Frédéric.exe')
                self.assertEqual(response.read(),target.read_bytes())
            with post('/api/remote/delete',{'id':self.access['id']}) as response:self.assertEqual(response.status,200)
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+'/api/remote/client/'+self.access['id'])
            self.assertEqual(error.exception.code,404);error.exception.close()
        finally:server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
