"""First-use transport gate, capabilities, multimodal gateway and durable attachments."""
import base64
import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch
import test_remote as fixture
from test_remote import client, FakeModel
from chat_attachments import validate_message, validate_parts
import history_store

PNG='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='

class ChatTests(unittest.TestCase):
    setUp=fixture.RemoteTests.setUp
    tearDown=fixture.RemoteTests.tearDown
    request=fixture.RemoteTests.request

    def test_first_launch_has_no_network_until_choice_and_persists_both_modes(self):
        class Opener:
            def open(self,*args,**kwargs):raise AssertionError('Network before selection')
        remote=client.Remote(self.profile,opener=Opener(),connection_required=True)
        self.assertTrue(remote.check()['connection_required'])
        self.assertEqual(remote.state()['attempts'],0)
        with self.assertRaises(ValueError):remote.open('/v1/models')
        self.assertEqual(remote.state()['bridge_starts'],0)
        with patch.dict(os.environ,{'LOCALAPPDATA':self.temporary.name}):
            for endpoint in ('https://ia.karenax.net',None):
                client.save_endpoint(self.profile,endpoint);remote.set_endpoint(endpoint)
                self.assertFalse(remote.state()['connection_required'])
                settings=client.client_settings(self.profile)
                self.assertTrue(settings['connection_selected'])
                self.assertEqual(settings.get('endpoint'),endpoint)

    def test_gateway_advertises_vision_and_rejects_images_when_disabled(self):
        with self.request('/v1/models') as response:
            caps=json.load(response)['data'][0]['capabilities']
        self.assertFalse(caps['images']);self.assertIn('docx',caps['files'])
        message={'role':'user','content':[{'type':'text','text':'Décris'},{'type':'image_url','image_url':{'url':PNG}}]}
        before=len(FakeModel.captured)
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/v1/chat/completions',{'messages':[message]})
        self.assertEqual(json.load(error.exception)['error']['code'],'image_not_supported');error.exception.close()
        self.assertEqual(len(FakeModel.captured),before)
        with patch('remote.health',return_value={'loaded':True,'images':True}):
            with self.request('/v1/models') as response:self.assertTrue(json.load(response)['data'][0]['capabilities']['images'])
            with self.request('/v1/chat/completions',{'messages':[message],'chat_template_kwargs':{'enable_thinking':True}}) as response:self.assertIn('choices',json.load(response))
        data=FakeModel.captured[-1][1]
        self.assertIn('Tu es Kiara',data['messages'][0]['content'])
        self.assertEqual(data['messages'][1:],[message]);self.assertTrue(data['chat_template_kwargs']['enable_thinking'])
        for source in ('http://localhost/private','file:///secret','D:/secret', 'data:image/png;base64,eA=='):
            with self.subTest(source=source),self.assertRaises(ValueError):validate_parts([{'type':'image_url','image_url':{'url':source}}],'user')

    def test_transient_files_and_history_roundtrip(self):
        w=self.store.workspace;owner=self.access['id'];before=w.snapshot(owner)
        with self.request('/v1/workspace/action',{'action':'attachment_extract','title':'note.txt','data':base64.b64encode('Bonjour pièce jointe'.encode()).decode()}) as response:text=json.load(response)['text']
        self.assertEqual(text,'Bonjour pièce jointe');self.assertEqual(w.snapshot(owner)['projects'],before['projects'])
        m={'role':'user','content':'Analyse','attachments':[{'kind':'file','name':'note.txt','text':text},{'kind':'image','name':'photo.png','url':PNG}]}
        history={'currentId':'a','conversations':[{'id':'a','title':'Pièces','messages':[m]}]}
        self.assertEqual(history_store.validate(history),history)
        path=client.settings_path(self.profile).with_name('test-attachments.dpapi')
        with patch.dict(os.environ,{'LOCALAPPDATA':self.temporary.name}):
            path=client.settings_path(self.profile).with_name('test-attachments.dpapi')
            history_store.write(path,client.protect,history,'');self.assertEqual(history_store.read(path,client.protect)['history'],history)
        with self.assertRaises(ValueError):validate_message({'role':'assistant','content':'test','attachments':m['attachments']})

    def test_multimodal_project_context_and_publication(self):
        w=self.store.workspace;owner=self.access['id']
        project=w.action(owner,{'action':'project_create','title':'Images'})['id']
        w.action(owner,{'action':'document_create','project':project,'title':'Budget','text':'Budget : 2500 euros.'})
        message={'role':'user','content':[{'type':'text','text':'Budget de cette image'},{'type':'image_url','image_url':{'url':PNG}}]}
        with patch('remote.health',return_value={'loaded':True,'images':True}):
            with self.request('/v1/chat/completions',{'project_id':project,'messages':[message]}) as response:self.assertIn('choices',json.load(response))
        sent=FakeModel.captured[-1][1]['messages'];self.assertEqual(sent[-1],message);self.assertEqual(sent[0]['role'],'system')
        from workspace import HISTORY_RESET_ID
        result=w.action(owner,{'action':'conversation_save','reset_id':HISTORY_RESET_ID,'project':project,'id':'a'*32,'title':'Photo','messages':[{'role':'user','content':'Budget','attachments':[{'kind':'image','name':'photo.png','url':PNG}]}]})
        self.assertEqual(result['revision'],1)

if __name__=='__main__':unittest.main(verbosity=2)
