"""Full restoration and crash recovery against isolated server instances."""
import base64
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from app import Controller, serve
from core import ROOT, PYTHON, read_json, write_json
from restoration import atomic, recover
from server_state import generation, inventory
from wg_crypto import protect

PASSWORD='isolated restoration phrase 2026'


class RestorationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='fred-restore-')
        self.home=Path(self.tmp.name)
        self.c=Controller(self.home,include_legacy=False)
        self.c.wireguard.configure({'public_host':'127.0.0.1','listen_port':51820})
        self.device=self.c.wireguard.create_android('Téléphone essai','fixture-model')
        self.owner=self.device['id']
        self.w=self.c.remote.workspace
        self.project=self.w.action(self.owner,{'action':'project_create','title':'Projet essai'})['id']
        self.document=self.w.action(self.owner,{'action':'document_upload','project':self.project,'title':'preuve.txt','data':base64.b64encode(b'original document proof').decode()})['id']
        self.history={'conversations':[{'id':'proof','title':'Preuve','messages':[{'role':'user','content':'avant sauvegarde'}]}],'currentId':'proof'}
        self.w.history_write(self.owner,{'history':self.history,'revision':0,'reset_id':self.w.history_read(self.owner)['reset_id']})
        self.c.remote.configure({'enabled':False,'url':'wireguard://10.77.0.1:8766'})

    def tearDown(self):
        self.c.operations.backups.close()
        self.w.shutdown()
        self.tmp.cleanup()

    def backup(self):return self.c.operations.backups.create(PASSWORD)

    def test_voice_configuration_is_backed_up_and_restored_with_worker_stopped(self):
        from core import write_json,read_json
        write_json(self.home/'voix.json',{'enabled':True})
        archive=self.backup()
        write_json(self.home/'voix.json',{'enabled':False})
        self.c.operations.restorations.restore_sync({'file':archive['file'],'password':PASSWORD})
        self.assertEqual(read_json(self.home/'voix.json'),{'enabled':True})
        self.assertEqual(self.c.voice.status()['phase'],'stopped')
        self.assertIsNone(self.c.voice.process)

    def test_complete_restore_preserves_original_profile_settings_and_blocks_old_cache(self):
        before=self.c.wireguard.android_profile(self.owner)
        original=self.c.settings()
        archive=self.backup()
        oldgen=generation(self.home)['id']
        self.c.save({**original,'context':8192})
        second={'conversations':[{'id':'proof','title':'Preuve','messages':[{'role':'user','content':'après sauvegarde'}]}],'currentId':'proof'}
        state=self.w.history_read(self.owner)
        self.w.history_write(self.owner,{'history':second,'revision':state['revision'],'reset_id':state['reset_id']})
        result=self.c.operations.restorations.restore_sync({'file':archive['file'],'password':PASSWORD})
        self.assertTrue(Path(result['rollback']).is_file())
        self.assertEqual(self.c.settings(),original)
        self.assertEqual(self.w.history_read(self.owner)['history'],self.history)
        self.assertEqual(self.w.action(self.owner,{'action':'document_download','id':self.document})['data'],base64.b64encode(b'original document proof').decode())
        self.assertEqual(json.loads(self.c.wireguard.android_profile(self.owner)),json.loads(before))
        self.assertFalse(self.c.remote.metadata()['enabled'])
        state=self.w.history_read(self.owner)
        self.assertNotEqual(state['generation'],oldgen)
        body={'history':second,'revision':state['revision'],'reset_id':state['reset_id'],'generation':oldgen}
        with self.assertRaisesRegex(ValueError,'restauré'):self.w.history_write(self.owner,body)
        body['generation']=state['generation']
        self.assertTrue(self.w.history_write(self.owner,body)['saved'])
        self.assertTrue(any(row['protected'] for row in self.c.operations.backups.status()['catalog']))

    def test_revocation_after_snapshot_survives_restore_and_restart(self):
        archive=self.backup()
        self.c.wireguard.revoke(self.owner)
        self.c.operations.restore({'file':archive['file'],'password':PASSWORD})
        self.assertTrue(self.c.remote.revocations.contains(self.owner))
        self.assertTrue(self.c.remote.metadata()['clients'][0]['revoked'])
        with self.assertRaises(ValueError):self.c.wireguard.android_profile(self.owner)
        fresh=Controller(self.home,include_legacy=False)
        self.assertTrue(fresh.remote.metadata()['clients'][0]['revoked'])
        fresh.operations.backups.close();fresh.remote.workspace.shutdown()

    def test_bad_password_and_modified_archive_do_not_mutate_data(self):
        archive=self.backup();before=self.c.settings();state=self.w.history_read(self.owner)
        with self.assertRaises(ValueError):self.c.operations.restorations.preview({'file':archive['file'],'password':'another wrong phrase'})
        preview=self.c.operations.restorations.preview({'file':archive['file'],'password':PASSWORD})
        path=Path(archive['file']);raw=path.read_bytes();path.write_bytes(raw[:-4]+b'bad!')
        with self.assertRaises(ValueError):self.c.operations.restorations.start({'file':str(path),'password':PASSWORD,'restore_token':preview['restore_token'],'confirm':True})
        self.assertEqual(self.c.settings(),before);self.assertEqual(self.w.history_read(self.owner),state)

    def test_failure_during_restore_rolls_back_and_preserves_point_of_return(self):
        archive=self.backup();before=self.c.settings();self.c.save({**before,'context':8192});changed=self.c.settings()
        with patch.object(self.c.wireguard,'save_vault',side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):self.c.operations.restore({'file':archive['file'],'password':PASSWORD})
        self.assertEqual(self.c.settings(),changed)
        self.assertEqual(self.w.history_read(self.owner)['history'],self.history)
        self.assertEqual(read_json(self.home/'securite'/'restauration.json')['state'],'recovered')

    def test_process_termination_recovers_before_database_opens(self):
        # An actual process exits between mutation and commit, not a caught exception.
        original=self.c.settings()
        script='''import sys,json,base64,os
from pathlib import Path
sys.path.insert(0,sys.argv[2])
from core import write_json
from restoration import atomic
from wg_crypto import protect
home=Path(sys.argv[1]);path=home/'reglages.json'
raw=path.read_bytes()
atomic(home/'securite'/'retour-restauration.dpapi',protect(json.dumps({'reglages.json':base64.b64encode(raw).decode()}).encode()))
write_json(home/'securite'/'restauration.json',{'state':'applying','active':True})
changed=json.loads(raw);changed['context']=8192;write_json(path,changed)
os._exit(47)
'''
        completed=subprocess.run([str(PYTHON),'-c',script,str(self.home),str(ROOT/'lanceur')],capture_output=True)
        self.assertEqual(completed.returncode,47,completed.stderr.decode())
        fresh=Controller(self.home,include_legacy=False)
        self.assertEqual(fresh.settings(),original)
        self.assertEqual(fresh.operations.restorations.status()['state'],'recovered')
        fresh.operations.backups.close();fresh.remote.workspace.shutdown()

    def test_failed_rollback_keeps_access_closed_until_retry(self):
        archive=self.backup();settings=self.c.settings()
        self.c.save({**settings,'context':8192});changed=self.c.settings()
        with patch.object(self.c.wireguard,'save_vault',side_effect=OSError('simulated failure')),patch('restoration.recover',side_effect=OSError('storage unavailable')):
            with self.assertRaises(OSError):self.c.operations.restore({'file':archive['file'],'password':PASSWORD})
        self.assertTrue(self.c.remote.maintenance)
        self.assertTrue(self.w.maintenance)
        self.assertEqual(read_json(self.home/'securite'/'restauration.json')['state'],'applying')
        self.assertFalse(self.c.remote.valid_owner(self.owner))
        status=self.c.operations.restorations.recover_now()
        self.assertEqual(status['state'],'recovered')
        self.assertFalse(self.c.remote.maintenance)
        self.assertEqual(self.c.settings(),changed)

    def test_no_disk_space_refuses_without_leaving_preparation_active(self):
        from collections import namedtuple
        archive=self.backup();settings=self.c.settings()
        usage=namedtuple('Usage','total used free')(1024,1024,0)
        with patch('shutil.disk_usage',return_value=usage):
            with self.assertRaisesRegex(ValueError,'Espace disque insuffisant'):
                self.c.operations.restore({'file':archive['file'],'password':PASSWORD})
        self.assertEqual(self.c.settings(),settings)
        self.assertFalse(self.c.remote.maintenance)
        self.assertFalse(self.c.operations.restorations.status()['active'])
        self.assertEqual(self.c.operations.restorations.status()['state'],'failed')

    def test_new_machine_requires_access_validation(self):
        archive=self.backup()
        with tempfile.TemporaryDirectory(prefix='fred-new-server-') as folder:
            fresh=Controller(folder,include_legacy=False)
            try:
                fresh.operations.restore({'file':archive['file'],'password':PASSWORD})
                self.assertTrue(fresh.remote.metadata()['clients'][0]['suspended'])
                self.assertFalse(fresh.remote.valid_owner(self.owner))
                self.assertEqual(fresh.remote.workspace.history_read(self.owner)['history'],self.history)
            finally:fresh.operations.backups.close();fresh.remote.workspace.shutdown()

    def test_loopback_http_validation_job_and_security(self):
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        server=serve(port,self.c);threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{port}'
        try:
            with urllib.request.urlopen(base) as response:html=response.read().decode()
            token=re.search('name="launcher-token" content="([^"]+)"',html)[1]
            def post(route,body,key=token):
                request=urllib.request.Request(base+route,json.dumps(body).encode(),{'Content-Type':'application/json','Origin':base,'X-Launcher-Token':key})
                with urllib.request.urlopen(request,timeout=15) as response:return json.load(response)
            with self.assertRaises(urllib.error.HTTPError) as error:post('/api/backups/create',{'password':PASSWORD},'wrong')
            self.assertEqual(error.exception.code,403);error.exception.close()
            with urllib.request.urlopen(base+'/api/inventory') as response:inv=json.load(response)
            self.assertEqual(inv['storage']['documents'],1)
            post('/api/backups/create',{'password':PASSWORD})
            deadline=time.time()+15
            while time.time()<deadline:
                with urllib.request.urlopen(base+'/api/backups') as response:status=json.load(response)
                if status['job']['state']!='running':break
                time.sleep(.05)
            self.assertEqual(status['job']['state'],'succeeded',status)
            identity=status['catalog'][0]['id']
            preview=post('/api/backups/verify',{'id':identity,'password':PASSWORD})
            self.assertNotIn('package',preview);self.assertNotIn('files',preview)
            with self.assertRaises(urllib.error.HTTPError):post('/api/backups/restore',{'id':identity,'password':PASSWORD,'confirm':False})
            post('/api/backups/restore',{'id':identity,'password':PASSWORD,'restore_token':preview['restore_token'],'confirm':True})
            deadline=time.time()+15
            while time.time()<deadline:
                with urllib.request.urlopen(base+'/api/maintenance') as response:status=json.load(response)
                if not status['active']:break
                time.sleep(.05)
            self.assertEqual(status['state'],'completed',status)
            with self.assertRaises(urllib.error.HTTPError) as denied:urllib.request.urlopen(base+'/api/remote/profile/'+self.owner)
            self.assertEqual(denied.exception.code,403);denied.exception.close()
            with urllib.request.urlopen(urllib.request.Request(base+'/api/remote/profile/'+self.owner,headers={'X-Launcher-Token':token})) as response:
                self.assertEqual(json.load(response)['token'].split('_')[1],self.owner)
        finally:server.shutdown();server.server_close()

    def test_admin_command_started_before_maintenance_is_refused_after_body(self):
        with socket.socket() as candidate:
            candidate.bind(('127.0.0.1',0));port=candidate.getsockname()[1]
        server=serve(port,self.c);threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{port}'
        checked=threading.Event();blocked=threading.Event()
        class Maintenance:
            def __bool__(self):checked.set();return blocked.is_set()
        try:
            with urllib.request.urlopen(base) as response:
                token=re.search('name="launcher-token" content="([^"]+)"',response.read().decode())[1]
            for scenario in ('slow_body','waiting_for_lock'):
                with self.subTest(scenario=scenario):
                    checked.clear();blocked.clear();self.c.remote.maintenance=Maintenance()
                    headers=f'POST /api/operations HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\nOrigin: {base}\r\nX-Launcher-Token: {token}\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n'.encode()
                    with patch.object(self.c.operations,'configure') as configure,socket.create_connection(('127.0.0.1',port),timeout=3) as connection:
                        if scenario=='waiting_for_lock':self.c.lock.acquire()
                        try:
                            connection.sendall(headers+(b'{' if scenario=='slow_body' else b'{}'))
                            self.assertTrue(checked.wait(3),'Initial maintenance check was not reached')
                            blocked.set()
                            if scenario=='slow_body':connection.sendall(b'}')
                        finally:
                            if scenario=='waiting_for_lock':self.c.lock.release()
                        response=b''
                        while True:
                            part=connection.recv(4096)
                            if not part:break
                            response+=part
                        self.assertIn(b'400 Bad Request',response)
                        self.assertIn(b'maintenance',response)
                        configure.assert_not_called()
                    self.c.remote.maintenance=False
        finally:
            self.c.remote.maintenance=False;server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
