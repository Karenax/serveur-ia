"""Native Windows catalogue forwarding and encrypted per-conversation choices."""
import base64
import copy
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import client
import history_store


class ModelCatalogueTests(unittest.TestCase):
    def setUp(self):
        encoded=base64.b64encode(bytes(range(32))).decode()
        self.profile={'url':'wireguard://10.77.0.1:8766','transport':'wireguard',
                      'token':'qwen_'+'a'*16+'_'+'b'*43,'protocol':4,
                      'wireguard':{'private_key':encoded,'server_public_key':encoded,'preshared_key':encoded,
                                   'address':'10.77.0.2/32','endpoint':'example.test:51820'}}
        self.catalogue={'object':'list','source':'hermes','default_model':'fred-cloud','data':[
            {'id':'fred-local','name':'Qwen local','provider':'Serveur','available':False,'capabilities':{'vision':False}},
            {'id':'fred-cloud','label':'Modèle cloud','provider':'Fournisseur de test','available':True,
             'capabilities':{'vision':True,'files':['txt','md','pdf','docx'],'reasoning_efforts':['none','high'],'context_length':None},
             'private_config':'must-not-reach-client'}]}
        self.requests=[];self.revoked=False;self.temp=tempfile.TemporaryDirectory()
        owner=self
        class Opener:
            def open(self,request,timeout):
                route=request.full_url.split('/v1/',1)[1]
                body=json.loads(request.data) if request.data else None
                owner.requests.append((route,body,request.headers))
                if owner.revoked:
                    raise urllib.error.HTTPError(request.full_url,401,'revoked',{},io.BytesIO(b'{"error":{"code":"access_revoked","message":"Acces revoque."}}'))
                if route=='chat/completions' and body.get('text_transform'):
                    raise urllib.error.HTTPError(request.full_url,503,'unloaded',{},io.BytesIO(b'{"error":{"code":"model_unloaded","message":"Qwen local non charge."}}'))
                value=owner.catalogue if route=='models' else {'choices':[{'message':{'content':'Réponse cloud.'}}]} if route=='chat/completions' else {}
                result=io.BytesIO(json.dumps(value).encode());result.status=200;result.code=200
                return result
        self.remote=client.Remote(self.profile,Opener());self.server=None

    def tearDown(self):
        if self.server:self.server.shutdown();self.server.server_close()
        self.temp.cleanup()

    def loopback(self):
        with patch.object(client,'settings_path',return_value=Path(self.temp.name)/'fixture.dpapi'):
            self.server=client.serve_local(self.remote,'fixture-loopback-key',port=0)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        return 'http://127.0.0.1:'+str(self.server.server_port)

    def test_real_loopback_preserves_public_catalogue_and_rejects_revoked_cache(self):
        url=self.loopback();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        request=urllib.request.Request(url+'/v1/models',headers={'Authorization':'Bearer fixture-loopback-key'})
        with opener.open(request) as response:actual=json.load(response)
        expected=copy.deepcopy(self.catalogue)
        for row in expected['data']:row['object']='model';row.pop('private_config',None)
        self.assertEqual(actual,expected)
        self.assertEqual(self.remote.state()['model'],'fred-cloud')
        self.catalogue['data'][1]['available']=False
        with opener.open(request) as response:unavailable=json.load(response)
        self.assertTrue(all(not row['available'] for row in unavailable['data']))
        self.revoked=True
        with self.assertRaises(urllib.error.HTTPError) as failure:opener.open(request)
        self.assertEqual(failure.exception.code,401)
        self.assertEqual(json.load(failure.exception)['error']['code'],'access_revoked');failure.exception.close()

    def test_local_qwen_unloaded_does_not_disconnect_available_cloud_and_body_is_retained(self):
        self.remote.check()
        with self.assertRaises(urllib.error.HTTPError) as failure:
            self.remote.open('/v1/chat/completions',json.dumps({'text_transform':{'mode':'correct','text':'Fixture.'},'stream':True}).encode(),'a'*32)
        self.assertEqual(json.load(failure.exception)['error']['code'],'model_unloaded');failure.exception.close()
        self.assertTrue(self.remote.connected);self.assertEqual(self.remote.code,'ready')
        body={'model':'fred-cloud','conversation_id':'model-choice','turn_id':'b'*32,'messages':[{'role':'user','content':'Fixture cloud.'}]}
        with self.remote.open('/v1/chat/completions',json.dumps(body).encode(),'b'*32) as response:
            self.assertEqual(json.load(response)['choices'][0]['message']['content'],'Réponse cloud.')
        route,actual,headers=self.requests[-1]
        self.assertEqual(actual,body);self.assertEqual(headers['X-qwen-request'],'b'*32)

    def test_legacy_catalogue_still_connects_without_new_metadata(self):
        self.catalogue={'data':[{'id':'legacy-model'}]}
        self.assertTrue(self.remote.check()['connected'])
        self.assertEqual(self.remote.state()['model'],'legacy-model')
        self.assertEqual(self.remote.models_catalogue,{'object':'list','data':[{'id':'legacy-model','object':'model','capabilities':{}}]})

    def test_encrypted_history_retains_choice_after_reopen_and_change(self):
        path=Path(self.temp.name)/'choice.dpapi'
        value={'currentId':'model-choice','conversations':[{'id':'model-choice','title':'Choix de modèle','model':'fred-cloud','messages':[]}]}
        saved=history_store.write(path,client.protect,value,'')
        self.assertNotIn(b'fred-cloud',path.read_bytes());self.assertEqual(history_store.read(path,client.protect)['history'],value)
        value['conversations'][0]['model']='fred-local'
        history_store.write(path,client.protect,value,saved['revision'])
        self.assertEqual(history_store.read(path,client.protect)['history']['conversations'][0]['model'],'fred-local')


if __name__=='__main__':unittest.main()
