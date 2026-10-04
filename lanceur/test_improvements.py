import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from app import Controller
from core import HOME, read_json, write_json
from scheduler import Scheduler
from operations import cipher

class ImprovementsTests(unittest.TestCase):
    def test_temporarily_locked_atomic_json_is_retried(self):
        import core
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json';real_replace=core.os.replace;calls=[]
            def replace(source,target):
                calls.append(True)
                if len(calls)==1:raise PermissionError('Simulated transient Windows lock')
                real_replace(source,target)
            with patch('core.os.replace',side_effect=replace):write_json(path,{'status':'pret'})
            self.assertEqual(read_json(path),{'status':'pret'});self.assertEqual(len(calls),2)

    def test_console_reload_preserves_stopped_model(self):
        class StopWatch(BaseException):pass
        with tempfile.TemporaryDirectory() as folder:
            c=Controller(folder,include_legacy=False)
            c.operations.configure({'autoload':True,'restart':True})
            with patch.object(c,'processes',return_value=[]),patch.object(c,'supervisor',return_value=None),patch.object(c,'start') as start,patch('operations.time.sleep',side_effect=StopWatch):
                with self.assertRaises(StopWatch):c.operations.watch(preserve_state=True)
                self.assertFalse(c.operations.desired);start.assert_not_called()
                with self.assertRaises(StopWatch):c.operations.watch()
                start.assert_called_once()

    def test_fifo_duplicate_and_cancel(self):
        scheduler=Scheduler(3)
        a=scheduler.submit('a');b=scheduler.submit('b');c=scheduler.submit('c')
        with self.assertRaises(ValueError):scheduler.submit('a')
        with self.assertRaises(ValueError):scheduler.submit('d')
        scheduler.wait(a,lambda:True,lambda p:None)
        result=[]
        worker=threading.Thread(target=lambda:(scheduler.wait(c,lambda:True,lambda p:None),result.append('c')))
        worker.start()
        scheduler.cancel('b')
        self.assertEqual(scheduler.position(c),1)
        scheduler.finish(a);worker.join(3)
        self.assertEqual(result,['c']);scheduler.finish(c)
        self.assertEqual(scheduler.snapshot()['active'],0)

    def test_cancel_interrupts_active_socket(self):
        scheduler=Scheduler();item=scheduler.submit('a');scheduler.wait(item,lambda:True,lambda p:None)
        result=[];item['abort']=lambda:result.append(True)
        scheduler.cancel('a');self.assertEqual(result,[True]);scheduler.finish(item)

    def test_access_suspension_expiration_and_audit(self):
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            c=Controller(folder,include_legacy=False);store=c.remote
            access=store.issue('Test');store.configure({'enabled':True,'url':''})
            self.assertEqual(store.authenticate(access['token']),access['id'])
            store.policy({'id':access['id'],'suspended':True,'days':1,'max_tokens':500})
            self.assertIsNone(store.authenticate(access['token']))
            store.policy({'id':access['id'],'suspended':False,'days':1,'max_tokens':500})
            with patch('remote.time.time',return_value=time.time()+2*86400):self.assertIsNone(store.authenticate(access['token']))
            self.assertNotIn(access['token'],(Path(folder)/'audit.json').read_text())

    def test_encrypted_backup_wrong_password_and_restore(self):
        with tempfile.TemporaryDirectory(dir=HOME) as folder:
            c=Controller(folder,include_legacy=False)
            password='test phrase sufficiently long'
            backup=c.operations.backup(password)
            blob=Path(backup['file']).read_bytes()
            self.assertNotIn(b'reglages.json',blob)
            with self.assertRaises(ValueError):c.operations.restore({'file':backup['file'],'password':'wrong password long enough'})
            before=c.settings();changed={**before,'context':8192};c.save(changed)
            with patch.object(c,'processes',return_value=[]),patch.object(c,'supervisor',return_value=None):
                result=c.operations.restore({'file':backup['file'],'password':password})
            self.assertEqual(c.settings()['context'],before['context'])
            self.assertTrue(Path(result['rollback']).is_file())
            self.assertFalse(c.remote.metadata()['enabled'])

    def test_release_preserves_keys_rollback_and_rejects_corruption(self):
        import base64
        import secrets
        import struct
        import releases
        import sys
        sys.path.insert(0,str(HOME.parent/'client-qwen'))
        import wg_bridge
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);home=root/'home';home.mkdir()
            dist=root/'client-qwen/dist';dist.mkdir(parents=True)
            source=dist/'Accès serveur Fred.exe';source.write_bytes(b'new executable fixture')
            identity=secrets.token_hex(8);key=base64.b64encode(bytes(range(32))).decode()
            personal={'transport':'wireguard','url':'wireguard://10.77.0.1:8766','token':'qwen_'+identity+'_'+secrets.token_urlsafe(32),
                      'wireguard':{'private_key':key,'server_public_key':key,'preshared_key':key,'address':'10.77.0.2/32','endpoint':'127.0.0.1:51820'}}
            encoded=json.dumps(personal).encode()
            clients=home/'clients';clients.mkdir();target=clients/(identity+'.exe')
            original=b'old fixture'+encoded+struct.pack('<I',len(encoded))+b'QWENPROFILE1'
            target.write_bytes(original)
            from profiles import public_key
            import hashlib
            record={'id':identity,'revoked':False,'hash':hashlib.sha256(personal['token'].encode()).hexdigest(),'address':personal['wireguard']['address'],'wireguard_public_key':public_key(key)}
            write_json(home/'acces-distants.json',{'enabled':False,'url':'wireguard://10.77.0.1:8766','clients':[record]})
            with patch('releases.ROOT',root):
                releases.manifest(home);self.assertEqual(releases.repackage(home)['count'],1)
                self.assertEqual(releases.profile(target)['wireguard'],personal['wireguard'])
                self.assertEqual(releases.profile(target)['token'],personal['token'])
                self.assertEqual(releases.repackage(home)['count'],0)
                releases.rollback(home);self.assertEqual(target.read_bytes(),original)
                source.write_bytes(b'tampered')
                with self.assertRaises(ValueError):releases.repackage(home)

if __name__=='__main__':unittest.main(verbosity=2)
