"""Regression tests use isolated accounts, signed fixtures and fake model endpoints."""
import base64
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error
from core import HOME,ROOT,read_json,write_json
from accounts import Accounts
from signing import sign,public
from app import Controller
from scheduler import Scheduler
import test_remote
client=test_remote.client
sys.path.insert(0,str(ROOT/'client-qwen'))
import updater

class AccountsTests(unittest.TestCase):
    def test_update_starts_with_active_api_requests_and_closes_after_preparation(self):
        import threading
        from unittest.mock import Mock
        remote=client.Remote.__new__(client.Remote)
        remote.activity_lock=threading.Lock();remote.update_lock=threading.Lock()
        remote.active_requests=3;remote.applying_update=False
        remote.window=Mock();remote.update_state={}
        entered=threading.Event();release=threading.Event()
        def prepare(*args):
            entered.set()
            if not release.wait(5):raise TimeoutError('Test update preparation timed out')
        with patch.object(updater,'prepare',side_effect=prepare) as prepared:
            try:
                self.assertTrue(remote.update(True)['busy'])
                self.assertTrue(entered.wait(2))
                self.assertTrue(remote.applying_update)
                remote.window.destroy.assert_not_called()
                with self.assertRaisesRegex(ValueError,'Installation en cours'):remote.update(True)
            finally:
                release.set()
            self.assertTrue(remote.update_lock.acquire(timeout=2))
            remote.update_lock.release()
        prepared.assert_called_once_with(remote,client.protect)
        remote.window.destroy.assert_called_once()
        self.assertEqual(remote.active_requests,3)
        self.assertFalse(remote.update_state['busy'])
        self.assertNotIn('error',remote.update_state)

    def test_password_hash_reset_expiry_disabled_and_throttle(self):
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            accounts=Accounts(Path(folder));clients=[{'id':'a','revoked':False},{'id':'b','revoked':False}]
            values={'id':'a','username':'Alice','password':'test long password 123'}
            accounts.configure(values,clients)
            self.assertNotIn(values['password'],accounts.path.read_text())
            session=accounts.login('a','alice',values['password'])['session']
            self.assertTrue(accounts.valid('a',session));self.assertFalse(accounts.valid('b',session))
            with patch('accounts.time.time',return_value=time.time()+13*3600):self.assertFalse(accounts.valid('a',session))
            accounts.configure({**values,'password':'another long password'},clients)
            self.assertFalse(accounts.valid('a',session))
            with self.assertRaises(ValueError):accounts.login('a','alice',values['password'])
            session=accounts.login('a','alice','another long password')['session']
            accounts.configure({**values,'password':'','enabled':False},clients)
            self.assertFalse(accounts.valid('a',session))
            for _ in range(5):
                with self.assertRaises(ValueError):accounts.login('a','alice','wrong')
            with self.assertRaisesRegex(ValueError,'cinq minutes'):accounts.login('a','alice','another long password')
            with self.assertRaises(ValueError):accounts.configure({**values,'username':12},clients)

    def test_old_cancel_cannot_abort_new_request_and_stall_expires(self):
        scheduler=Scheduler();old=scheduler.submit('a','a'*32);scheduler.wait(old,lambda:True,lambda _:None);scheduler.finish(old)
        new=scheduler.submit('a','b'*32);scheduler.wait(new,lambda:True,lambda _:None)
        scheduler.cancel('a',old['id']);self.assertFalse(new['cancelled'])
        new['progress']=time.time()-121;calls=[];new['abort']=lambda:calls.append(True)
        scheduler.expire();self.assertTrue(new['cancelled']);self.assertEqual(calls,[True]);scheduler.finish(new)
        self.assertEqual(scheduler.snapshot()['cancelled'],1)

    def test_signed_download_rejects_wrong_key_modified_manifest_and_binary(self):
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            home=Path(folder);payload=b'signed executable fixture'
            import hashlib,io
            release=sign({'version':'3.0.1','protocol':3,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()},home)
            pinned=public(home);updater.verify(release,pinned)
            with self.assertRaises(ValueError):updater.verify({**release,'version':'9.9.9'},pinned)
            with self.assertRaises(ValueError):updater.verify(release,base64.b64encode(secrets.token_bytes(32)).decode())
            class Remote:
                profile={'update_public_key':pinned}
                def open(self,path):return io.BytesIO(b'tampered')
            with self.assertRaisesRegex(ValueError,'altéré'):updater.download(Remote(),release,home)
            self.assertFalse((home/'QwenClient.base.exe').exists())

    def test_restore_failure_rolls_back_every_file_and_keeps_restored_profiles(self):
        from wg_crypto import protect
        from operations import cipher
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            c=Controller(folder,include_legacy=False);password='backup password for regression'
            c.wireguard.configure({'public_host':'127.0.0.1','listen_port':51820})
            access=c.remote.issue('Backup');profile=c.wireguard.new_peer(access)
            saved=c.wireguard.directory/'profils-restaures.dpapi';saved.write_bytes(protect(json.dumps({access['id']:profile}).encode()))
            c.remote.accounts.configure({'id':access['id'],'username':'backup','password':'long test password'},c.remote.metadata()['clients'])
            backup=c.operations.backup(password);blob=Path(backup['file']).read_bytes();package=json.loads(cipher(password,blob[11:27]).decrypt(blob[27:]))
            self.assertEqual(package['files']['profiles'][access['id']],profile)
            before=c.settings();c.save({**before,'context':8192});changed=c.settings()
            with patch.object(c,'processes',return_value=[]),patch.object(c,'supervisor',return_value=None),patch.object(c.wireguard,'save_vault',side_effect=OSError('write failed')):
                with self.assertRaises(OSError):c.operations.restore({'file':backup['file'],'password':password})
            self.assertEqual(c.settings(),changed)
            with patch.object(c,'processes',return_value=[]),patch.object(c,'supervisor',return_value=None):c.operations.restore({'file':backup['file'],'password':password})
            second=c.operations.backup(password);blob=Path(second['file']).read_bytes();second_package=json.loads(cipher(password,blob[11:27]).decrypt(blob[27:]))
            self.assertEqual(second_package['files']['profiles'][access['id']],profile)
            self.assertEqual(second_package['files']['comptes.json'][0]['username'],'backup')

    def test_helper_replaces_verified_exe_preserves_profile_and_keeps_previous(self):
        import shutil,struct,hashlib
        from types import SimpleNamespace
        from wg_crypto import keypair,protect
        source=Path(os.environ.get('FRED_TEST_CLIENT_EXE',str(ROOT/'client-qwen/dist/Accès serveur Fred.exe')))
        if not source.exists():self.skipTest('Compiler le client avant ce test.')
        sys.path.insert(0,str(ROOT/'client-qwen/build-tools'))
        try:import pefile
        finally:sys.path.pop(0)
        with pefile.PE(str(source),fast_load=False) as binary:
            info=binary.VS_FIXEDFILEINFO[0]
            binary_version=f'{info.FileVersionMS>>16}.{info.FileVersionMS&65535}.{info.FileVersionLS>>16}'
        if binary_version!=updater.VERSION:
            self.skipTest('Recompiler le client '+updater.VERSION+' et définir FRED_TEST_CLIENT_EXE sur ce binaire.')
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            home=Path(folder)
            private,key=keypair()
            profile={'transport':'wireguard','url':'wireguard://10.77.0.1:8766','token':'qwen_0000000000000000_'+'x'*43,'version':'2.9.9','protocol':3,'update_public_key':public(home),'wireguard':{'private_key':private,'server_public_key':key,'preshared_key':key,'address':'10.77.0.2/32','endpoint':'127.0.0.1:1'}}
            target=home/'Accès serveur Fred.exe';shutil.copyfile(source,target)
            work=updater.work_directory(target,profile)
            existing_directories={p.name for p in home.iterdir() if p.is_dir()}
            raw=json.dumps(profile).encode()
            with target.open('ab') as stream:stream.write(raw+struct.pack('<I',len(raw))+b'QWENPROFILE1')
            failure_result=home/'self-test-error.txt'
            failed=updater.subprocess.run([str(target),'--self-test','--with-profile','--result',str(failure_result)],timeout=30,creationflags=0x08000000)
            self.assertEqual(failed.returncode,1)
            self.assertIn('Version du profil incompatible',failure_result.read_text(encoding='utf-8'))
            old=hashlib.sha256(target.read_bytes()).hexdigest()
            payload=work/'QwenClient.base.exe';shutil.copyfile(source,payload)
            release=sign({'version':updater.VERSION,'protocol':3,'bytes':payload.stat().st_size,'sha256':hashlib.sha256(payload.read_bytes()).hexdigest()},home)
            release['client_name']='Kiara'
            plan=work/'plan.dpapi';plan.write_bytes(protect(json.dumps({'target':str(target.resolve()),'source':str(payload.resolve()),'profile':profile,'release':release,'pid':99999999,'created':0}).encode()))
            helper=work/'QwenUpdate.exe'
            launch=updater.subprocess.Popen;fail_startup=[False];plan_blob=plan.read_bytes();relaunches=[]
            def test_launch(args,**kwargs):
                if '--self-test' in args:return launch(args,**kwargs)
                if len(args)==1:relaunches.append(args[0])
                if '--update-ack' in args and fail_startup[0]:return SimpleNamespace(pid=0,poll=lambda:1)
                if '--update-ack' in args:Path(args[-1]).write_text(json.dumps({'version':updater.personal_profile(Path(args[0]))['version'],'ready':True}),encoding='utf-8')
                return SimpleNamespace(pid=0,poll=lambda:None)
            with patch.object(updater.sys,'executable',str(helper.resolve())),patch.object(updater.subprocess,'Popen',side_effect=test_launch):
                # A tampered WireGuard identity is rejected even with the correct token and signing pin.
                changed=json.loads(protect(plan_blob,decrypt=True));changed['profile']['wireguard']['address']='10.77.0.3/32';plan.write_bytes(protect(json.dumps(changed).encode()))
                with self.assertRaisesRegex(ValueError,'Profil'):updater.apply(plan,protect,lambda:profile)
                plan.write_bytes(plan_blob)
                # A failed new-binary self-test leaves the old EXE untouched and relaunches it.
                with patch.object(updater.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
                    with self.assertRaises(ValueError):updater.apply(plan,protect,lambda:profile)
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),old)
                self.assertEqual(relaunches,[str(target.resolve())])
                fail_startup[0]=True;plan.write_bytes(plan_blob);shutil.copyfile(source,payload)
                with self.assertRaisesRegex(ValueError,'démarrage'):updater.apply(plan,protect,lambda:profile)
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),old)
                fail_startup[0]=False;plan.write_bytes(plan_blob);shutil.copyfile(source,payload)
                updater.apply(plan,protect,lambda:profile)
            import releases
            renamed=target
            self.assertTrue(target.exists())
            installed=releases.profile(renamed)
            self.assertEqual(installed['wireguard'],profile['wireguard']);self.assertEqual(installed['token'],profile['token'])
            self.assertEqual(installed['version'],updater.VERSION)
            self.assertEqual(installed['client_name'],'Kiara')
            backups=[work/'previous.exe']
            self.assertTrue(backups[0].exists())
            self.assertEqual(hashlib.sha256(backups[0].read_bytes()).hexdigest(),old)
            self.assertFalse(plan.exists());self.assertTrue(read_json(work/'update-result.json')['ok'])
            # A second update uses the new version and the registered client name.
            next_version='.'.join(map(str,(*updater.version(updater.VERSION)[:2],updater.version(updater.VERSION)[2]+1)))
            shutil.copyfile(source,payload)
            next_release=sign({'version':next_version,'protocol':3,'bytes':payload.stat().st_size,'sha256':hashlib.sha256(payload.read_bytes()).hexdigest()},home)
            next_release['client_name']='Kiara'
            plan.write_bytes(protect(json.dumps({'target':str(renamed.resolve()),'source':str(payload.resolve()),'profile':installed,'release':next_release,'pid':99999999,'created':0}).encode()))
            with patch.object(updater.sys,'executable',str(helper.resolve())),patch.object(updater.subprocess,'Popen',side_effect=test_launch),patch.object(updater.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
                updater.apply(plan,protect,lambda:installed)
            self.assertTrue(renamed.exists())
            self.assertEqual([p.name for p in home.glob('*.exe')],[target.name])
            self.assertEqual({p.name for p in home.iterdir() if p.is_dir()},existing_directories)
            self.assertEqual(updater.personal_profile(work/'previous.exe')['version'],updater.VERSION)
            self.assertEqual(updater.personal_profile(target)['version'],next_version)

class AuthGatewayTests(unittest.TestCase):
    # Reuse the fixture, without inheriting and rerunning its full test suite.
    setUp=test_remote.RemoteTests.setUp
    tearDown=test_remote.RemoteTests.tearDown
    request=test_remote.RemoteTests.request

    def test_integration_buttons_require_auth_and_only_use_verified_local_settings(self):
        import threading,urllib.request,yaml
        remote=client.Remote(self.profile,opener=object());key=secrets.token_urlsafe(32)
        home=Path(self.temporary.name)
        remote.models_catalogue={'object':'list','data':[{'id':'test-model','name':'test-model','available':True}]}
        apps={name:{'installed':True,'config_path':str(home/(name+suffix))} for name,suffix in [('opencode','.json'),('hermes','.yaml')]}
        state={'connected':True,'model':'test-model','models':['test-model']}
        with patch.object(client,'settings_path',return_value=home/'settings.dpapi'):
            local=client.serve_local(remote,key,0)
        threading.Thread(target=local.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{local.server_port}'
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}
        def post(value):return urllib.request.urlopen(urllib.request.Request(base+'/client/integrations/apply',json.dumps(value).encode(),headers))
        try:
            with patch.object(client.app_integrations,'detect',return_value=apps),patch.object(remote,'check',return_value=state) as checked:
                with self.assertRaises(urllib.error.HTTPError) as denied:urllib.request.urlopen(base+'/client/integrations')
                self.assertEqual(denied.exception.code,401)
                with urllib.request.urlopen(urllib.request.Request(base+'/client/integrations',headers=headers)) as response:self.assertEqual(json.load(response)['apps'],apps)
                foreign=urllib.request.Request(base+'/client/integrations',headers={**headers,'Origin':'https://example.test'})
                with self.assertRaises(urllib.error.HTTPError) as denied:urllib.request.urlopen(foreign)
                self.assertEqual(denied.exception.code,403)
                for app in apps:
                    expected='test-model' if app=='opencode' else client.hermes_catalogue.catalogue(remote.models_catalogue)[0]['data'][0]['id']
                    with post({'app':app,'model':'test-model'}) as response:self.assertEqual(json.load(response)['model'],expected)
                config=json.loads(Path(apps['opencode']['config_path']).read_text())['providers']['serveur-fred']
                self.assertEqual(config['settings'],{'baseURL':base+'/v1','apiKey':key})
                hermes=yaml.safe_load(Path(apps['hermes']['config_path']).read_text())['providers']['serveur-fred']
                self.assertEqual(hermes['api'],base+'/hermes/v1');self.assertEqual(hermes['api_key'],key)
                snapshots={app:Path(info['config_path']).read_bytes() for app,info in apps.items()}
                for values in [{'app':'opencode','model':'invented'},{'app':'unknown'},{'app':'opencode','config_path':str(home/'injected.json')},{'app':'hermes','key':'injected'}]:
                    with self.assertRaises(urllib.error.HTTPError) as refused:post(values)
                    self.assertEqual(refused.exception.code,400)
                state['connected']=False
                with self.assertRaises(urllib.error.HTTPError) as refused:post({'app':'opencode'})
                self.assertEqual(refused.exception.code,400)
                self.assertGreaterEqual(checked.call_count,3)
                for app,info in apps.items():self.assertEqual(Path(info['config_path']).read_bytes(),snapshots[app])
                self.assertFalse(list(home.glob('*.fred-backup-*')))
        finally:local.shutdown();local.server_close()

    def test_pasted_connection_parameters_are_validated_before_switching(self):
        import threading,urllib.request
        from connection_settings import export
        remote=client.Remote(self.profile,opener=object());key=secrets.token_urlsafe(32)
        with patch.object(client,'settings_path',return_value=Path(self.temporary.name)/'settings.dpapi'):
            local=client.serve_local(remote,key,0)
        threading.Thread(target=local.serve_forever,daemon=True).start()
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}
        url=f'http://127.0.0.1:{local.server_port}/client/endpoint'
        def post(value):return urllib.request.urlopen(urllib.request.Request(url,json.dumps(value).encode(),headers))
        try:
            with patch.object(client,'save_endpoint') as saved:
                with post({'endpoint':json.dumps(export('server.example:51820'),indent=2)}) as response:
                    self.assertEqual(json.load(response)['endpoint'],'server.example:51820')
                saved.assert_called_once_with(remote.profile,'server.example:51820')
                saved.reset_mock()
                with self.assertRaises(urllib.error.HTTPError) as invalid:post({'endpoint':'https://invalid.example/v1'})
                self.assertEqual(invalid.exception.code,400);saved.assert_not_called()
                self.assertEqual(remote.endpoint,'server.example:51820')
                remote.active_requests=1
                with self.assertRaises(urllib.error.HTTPError):post({'endpoint':'new.example:51820'})
                saved.assert_not_called();self.assertEqual(remote.endpoint,'server.example:51820')
        finally:local.shutdown();local.server_close()

    def test_personal_exe_connects_without_login_and_revocation_crosses_wireguard(self):
        from wireguard_access import Engine
        engine=Engine({'role':'server','wireguard':{'private_key':self.wireguard.vault()['private_key']},'listen_port':0,'upstream_port':self.gateway.server_port,'peers':self.wireguard.peers()})
        remote=client.Remote(self.profile,endpoint=f'127.0.0.1:{engine.port}')
        try:
            self.assertFalse(remote.session)
            with remote.open('/v1/models') as response:self.assertEqual(json.load(response)['data'][0]['id'],'test-model')
            with remote.open('/v1/auth/login',b'{}') as response:self.fail('Login route must be unavailable')
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code,404)
            self.store.revoke(self.access['id'])
            with self.assertRaises(urllib.error.HTTPError) as revoked:remote.open('/v1/models')
            self.assertEqual(revoked.exception.code,401)
        finally:remote.close();engine.close()

    def test_local_history_encrypted_and_auth_required(self):
        import threading,urllib.request
        remote=client.Remote(self.profile,opener=object());key=secrets.token_urlsafe(32)
        with patch.object(client,'settings_path',return_value=Path(self.temporary.name)/'settings.dpapi'):
            local=client.serve_local(remote,key,0)
        threading.Thread(target=local.serve_forever,daemon=True).start()
        history={'conversations':[{'id':'a','title':'private fixture','messages':[]}],'currentId':'a'}
        try:
            with patch.object(client,'settings_path',return_value=Path(self.temporary.name)/'settings.dpapi'):
                headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}
                request=urllib.request.Request(f'http://127.0.0.1:{local.server_port}/client/history',json.dumps({'history':history}).encode(),headers)
                with urllib.request.urlopen(request) as response:self.assertTrue(json.load(response)['saved'])
                raw=(Path(self.temporary.name)/'settings.history.dpapi').read_bytes();self.assertNotIn(b'private fixture',raw)
                with urllib.request.urlopen(urllib.request.Request(request.full_url,headers=headers)) as response:self.assertEqual(json.load(response)['history'],history)
                with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(request.full_url)
        finally:local.shutdown();local.server_close()

if __name__=='__main__':unittest.main()
