"""Server-to-client signed setup with disposable credentials and configurations."""
import base64
import copy
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import tomllib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'client-qwen'))
import codex_integration
import app_integrations
import codex_assets
from signing import public, sign
import test_remote


class CodexSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.home=self.root/'server'
        self.pinned=public(self.home)
        self.value=codex_assets.payload(self.home)
        self.key='qwen_'+secrets.token_hex(8)+'_'+secrets.token_urlsafe(32)
        self.calls=[]
        def open_remote(route):
            self.calls.append(route)
            return io.BytesIO(json.dumps(self.value).encode())
        self.remote=SimpleNamespace(profile={'update_public_key':self.pinned},token=self.key,open=open_remote)
        self.config=self.root/'codex/config.toml'

    def test_pinned_signature_and_archive_integrity_are_required_before_execution(self):
        for change in ('signature','bytes','archive'):
            value=copy.deepcopy(self.value)
            if change=='signature':value['release']['signature']='bad'
            elif change=='bytes':value['release']['bytes']+=1
            else:value['archive']=base64.b64encode(b'untrusted').decode()
            with self.subTest(change=change),patch('codex_integration.subprocess.run') as invoked:
                self.value=value
                with self.assertRaises(ValueError):codex_integration.install(self.remote,self.config)
                invoked.assert_not_called();self.assertFalse(self.config.exists())
            self.value=codex_assets.payload(self.home)

    @unittest.skipUnless(os.name=='nt','Windows Codex installation')
    def test_real_download_installs_application_and_encrypts_personal_key(self):
        self.config.parent.mkdir();self.config.write_text('model="old"\napproval_policy="on-request"\n',encoding='utf-8')
        result=codex_integration.install(self.remote,self.config)
        self.assertEqual(self.calls,['/v1/client/codex'])
        data=tomllib.loads(self.config.read_text(encoding='utf-8'))
        self.assertEqual(data['model'],'old');self.assertEqual(data['approval_policy'],'on-request')
        self.assertNotIn('model_provider',data);self.assertNotIn('model_catalog_json',data)
        self.assertEqual(data['model_providers']['kiara']['base_url'],'https://ia.karenax.net/v1')
        self.assertTrue(result['backups']);self.assertIn('réglages ChatGPT par défaut sont conservés',result['message'])
        for p in self.config.parent.iterdir():
            if p.is_file():self.assertNotIn(self.key.encode(),p.read_bytes())
        auth=data['model_providers']['kiara']['auth']
        resolved=subprocess.run([auth['command'],*auth['args']],capture_output=True,text=True,timeout=15)
        self.assertEqual(resolved.returncode,0);self.assertEqual(resolved.stdout,self.key)

    def test_failed_installer_restores_all_previous_settings(self):
        self.config.parent.mkdir()
        for name in codex_integration.TARGETS:(self.config.parent/name).write_bytes(('old '+name).encode())
        before={p.name:p.read_bytes() for p in self.config.parent.iterdir()}
        def fail(*args,**kwargs):
            self.config.write_text('partly changed',encoding='utf-8')
            return SimpleNamespace(returncode=1)
        with patch('codex_integration.subprocess.run',side_effect=fail),self.assertRaises(ValueError):
            codex_integration.install(self.remote,self.config)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.config.parent.iterdir() if p.name in before})

    def test_codex_detection_and_model_guard(self):
        directory=self.root/'custom-codex';directory.mkdir();(directory/'config.toml').write_text('',encoding='utf-8')
        apps=app_integrations.detect(self.root,{'CODEX_HOME':str(directory)},lambda _:None)
        self.assertTrue(apps['codex']['installed']);self.assertEqual(apps['codex']['config_path'],str(directory/'config.toml'))
        with self.assertRaises(ValueError):app_integrations.install('codex','http://127.0.0.1:1/v1','x'*40,'cloud',apps,remote=self.remote)


class CodexDownloadTests(unittest.TestCase):
    setUp=test_remote.RemoteTests.setUp
    tearDown=test_remote.RemoteTests.tearDown
    request=test_remote.RemoteTests.request
    def test_authenticated_route_and_pinned_signature(self):
        pinned=public(self.store.home)
        with self.request('/v1/client/codex') as response:value=json.load(response)
        target=Path(self.temporary.name)/'verified';target.mkdir()
        codex_integration.unpack(value,pinned,target)
        self.assertTrue((target/'Installer-Codex-Kiara.ps1').is_file())
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/v1/client/codex',token='x'*40)
        self.assertEqual(error.exception.code,401)

    @unittest.skipUnless(os.name=='nt','Windows setup integration')
    def test_application_button_downloads_and_installs_with_personal_access(self):
        import threading,urllib.request
        from test_remote import client
        public_key=public(self.store.home)
        self.profile['update_public_key']=public_key
        self.store.hermes=SimpleNamespace(model_catalog=lambda owner:{'object':'list','source':'hermes',
            'default_model':'fred-qwen','data':[{'id':'fred-qwen','label':'Qwen local','available':True,'capabilities':{}}]})
        remote=client.Remote(self.profile,opener=urllib.request.build_opener(urllib.request.ProxyHandler({})))
        remote.url=self.url;remote.session=self.session
        directory=Path(self.temporary.name)/'codex';directory.mkdir()
        config=directory/'config.toml';config.write_text('model="old"\n',encoding='utf-8')
        apps={'codex':{'installed':True,'config_path':str(config)}}
        with patch.object(client,'settings_path',return_value=Path(self.temporary.name)/'local.dpapi'):
            local=client.serve_local(remote,'fixture-key-'+'x'*32,0)
        threading.Thread(target=local.serve_forever,daemon=True).start()
        try:
            request=urllib.request.Request('http://127.0.0.1:'+str(local.server_port)+'/client/integrations/apply',
                json.dumps({'app':'codex','model':'fred-qwen'}).encode(),
                {'Content-Type':'application/json','Authorization':'Bearer fixture-key-'+'x'*32})
            with patch('app_integrations.detect',return_value=apps),urllib.request.urlopen(request,timeout=30) as response:
                result=json.load(response)
            self.assertEqual(result['app'],'codex')
            data=tomllib.loads(config.read_text(encoding='utf-8'));auth=data['model_providers']['kiara']['auth']
            key=subprocess.run([auth['command'],*auth['args']],capture_output=True,text=True,timeout=10)
            self.assertEqual(key.stdout,self.access['token'])
            self.assertNotIn(remote.token,config.read_text(encoding='utf-8'))
        finally:local.shutdown();local.server_close()


if __name__=='__main__':unittest.main()
