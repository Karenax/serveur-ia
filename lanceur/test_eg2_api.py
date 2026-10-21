"""Public EG2 validation, authorization, pressure and actual Windows/WireGuard proxy."""
import base64
import json
from pathlib import Path
import struct
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from public_embeddings import MODEL_ID, request
import test_remote
from test_remote import Engine, client


class EmbeddingsAPITests(unittest.TestCase):
    setUp=test_remote.RemoteTests.setUp
    tearDown=test_remote.RemoteTests.tearDown

    def prepare(self):
        self.calls=[]
        def encode(texts,**kwargs):
            self.calls.append((texts,kwargs))
            return {'vectors':[[1.0]+[0.0]*767 for _ in texts],'prompt_tokens':len(texts)*3}
        self.engine=SimpleNamespace(encode=encode,status=lambda:{'enabled':True,'status':'pret'})
        self.store.workspace.knowledge=SimpleNamespace(engine=self.engine,close=lambda:None)

    def call(self,value=None,token=None,headers=None):
        if value is None:value={'model':MODEL_ID,'input':['bonjour','document']}
        req=urllib.request.Request(self.url+'/v1/embeddings',json.dumps(value).encode(),
            {'Content-Type':'application/json','Authorization':'Bearer '+(token or self.access['token']),**(headers or {})})
        return urllib.request.urlopen(req,timeout=5)

    def test_float_base64_usage_catalogue_and_no_chat_routing(self):
        self.prepare()
        with self.call() as response:value=json.load(response)
        self.assertEqual(value['model'],MODEL_ID);self.assertEqual(value['usage']['total_tokens'],6)
        self.assertEqual([row['index'] for row in value['data']],[0,1]);self.assertEqual(len(value['data'][0]['embedding']),768)
        with self.call({'model':MODEL_ID,'input':'question','encoding_format':'base64','input_type':'query'}) as response:encoded=json.load(response)
        self.assertEqual(struct.unpack('<768f',base64.b64decode(encoded['data'][0]['embedding']))[0],1)
        self.assertEqual(self.calls[-1][1]['mode'],'query')
        req=urllib.request.Request(self.url+'/v1/models',headers={'Authorization':'Bearer '+self.access['token']})
        with urllib.request.urlopen(req) as response:catalogue=json.load(response)
        self.assertTrue(catalogue['data'][-1]['capabilities']['embedding'])

    def test_limits_and_unknown_fields_rejected_before_computation(self):
        self.prepare()
        for patch_value in ({'input':[]},{'input':[1]},{'input':['a']*9},{'input':' '},{'input':'a'*4501},
                            {'dimensions':True},{'dimensions':512},{'model':'qwen'},{'encoding_format':'unknown'},
                            {'stream':True},{'input_type':'bad'},{'user':{}}):
            with self.subTest(value=patch_value),self.assertRaises(urllib.error.HTTPError) as error:
                self.call({'model':MODEL_ID,'input':'ok',**patch_value})
            self.assertEqual(error.exception.code,400);error.exception.close()
        self.assertFalse(self.calls)

    def test_auth_origin_pressure_and_revocation_during_calculation(self):
        self.prepare()
        for kwargs,status in [({'token':'invalid'},401),({'headers':{'Origin':'https://evil.test'}},403)]:
            with self.assertRaises(urllib.error.HTTPError) as error:self.call(**kwargs)
            self.assertEqual(error.exception.code,status);error.exception.close()
        self.store.embedding_slot.acquire()
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:self.call()
            self.assertEqual(error.exception.code,429);error.exception.close()
        finally:self.store.embedding_slot.release()
        original=self.engine.encode
        def revoked(*args,**kwargs):
            result=original(*args,**kwargs);self.store.revoke(self.access['id']);return result
        self.engine.encode=revoked
        with self.assertRaises(urllib.error.HTTPError) as error:self.call()
        self.assertEqual(error.exception.code,403);error.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as error:self.call()
        self.assertEqual(error.exception.code,401);error.exception.close()

    def test_engine_failure_is_sanitized_and_slot_released(self):
        self.prepare()
        original=self.engine.encode
        def fail(*args,**kwargs):raise ValueError('private-engine-token')
        self.engine.encode=fail
        with self.assertRaises(urllib.error.HTTPError) as error:self.call()
        self.assertEqual(error.exception.code,503);self.assertNotIn(b'private-engine-token',error.exception.read());error.exception.close()
        self.engine.encode=original
        with self.call() as response:self.assertEqual(response.status,200)

    def test_actual_windows_local_api_through_wireguard(self):
        self.prepare()
        bridge=Engine({'role':'server','wireguard':{'private_key':self.wireguard.vault()['private_key']},
                      'listen_port':0,'upstream_port':self.gateway.server_port,'peers':self.wireguard.peers()})
        profile=json.loads(json.dumps(self.profile));profile['wireguard']['endpoint']='127.0.0.1:'+str(bridge.port)
        remote=client.Remote(profile)
        with patch.object(client,'settings_path',return_value=Path(self.temporary.name)/'local.dpapi'):
            server=client.serve_local(remote,'local-fixture',port=0)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            remote.check();self.assertNotIn(MODEL_ID,remote.models)
            self.assertIn(MODEL_ID,[row['id'] for row in remote.models_catalogue['data']])
            req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/v1/embeddings',
                json.dumps({'model':MODEL_ID,'input':'exemple'}).encode(),
                {'Authorization':'Bearer local-fixture','Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=10) as response:self.assertEqual(json.load(response)['usage']['prompt_tokens'],3)
        finally:server.shutdown();server.server_close();remote.close();bridge.close()

    def test_request_rejects_token_arrays_and_wrong_payload_types(self):
        for value in ([],None,{'model':MODEL_ID,'input':[1,2]}):
            with self.assertRaises(ValueError):request(value)

    def test_discovery_without_chat_and_through_hermes_catalogue(self):
        self.prepare()
        req=urllib.request.Request(self.url+'/v1/models',headers={'Authorization':'Bearer '+self.access['token']})
        with patch('remote.health',return_value={'loaded':False}):
            with urllib.request.urlopen(req) as response:rows=json.load(response)['data']
            self.assertEqual([row['id'] for row in rows],[MODEL_ID])
            with self.call() as response:self.assertEqual(response.status,200)
        self.store.hermes=SimpleNamespace(model_catalog=lambda owner:{'object':'list','source':'hermes','data':[{'id':'chat'}]})
        with urllib.request.urlopen(req) as response:rows=json.load(response)['data']
        self.assertEqual([row['id'] for row in rows],['chat',MODEL_ID])


if __name__=='__main__':unittest.main()
