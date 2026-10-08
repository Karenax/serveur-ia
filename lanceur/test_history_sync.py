"""Server histories, offline recovery, conflicts and persistent client settings."""
import base64
import copy
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'client-qwen'))
from history_sync import HistorySync,merge,fingerprints
from workspace import Workspace,Conflict,HISTORY_RESET_ID
from test_remote import client

def history(text='Texte initial',identity='conversation'):
    return {'currentId':identity,'conversations':[{'id':identity,'title':'Discussion','messages':[{'role':'user','content':text}]}]}

class FakeRemote:
    def __init__(self):
        self.connected=True;self.reachable=True;self.code='';self.active_requests=0;self.activity_lock=threading.RLock()
        self.value={'history':None,'revision':0,'reset_id':HISTORY_RESET_ID}
    def open(self,path,body=None):
        if not self.connected and self.code!='model_unloaded':raise urllib.error.URLError('Hors ligne')
        if body is not None:
            data=json.loads(body)
            if data['revision']!=self.value['revision']:raise urllib.error.HTTPError(path,409,'history_conflict',{},io.BytesIO())
            self.value={'history':data['history'],'revision':self.value['revision']+1,'reset_id':HISTORY_RESET_ID}
        return io.BytesIO(json.dumps(self.value).encode())

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.remote=FakeRemote()
    def tearDown(self):self.tmp.cleanup()
    def sync(self,name='first'):
        return HistorySync(self.remote,self.home/(name+'.history.dpapi'),client.protect)

    def test_fresh_pc_loads_server_without_empty_overwrite(self):
        first=self.sync();initial=history('Texte confidentiel');first.synchronize(initial)
        second=self.sync('second');placeholder=history('',identity='placeholder');placeholder['conversations'][0]['messages']=[];result=second.synchronize(placeholder)
        self.assertEqual(result['history'],initial);self.assertEqual(self.remote.value['revision'],1)
        self.assertNotIn(b'Texte confidentiel',first.path.read_bytes())
        self.assertEqual(HistorySync(self.remote,first.path,client.protect).read()['history'],initial)

    def test_offline_write_is_uploaded_after_reconnection(self):
        sync=self.sync();result=sync.synchronize(history());self.remote.connected=False
        changed=history('Modifié hors connexion');sync.write(changed,result['revision'])
        self.assertEqual(sync.read()['history'],changed);self.assertTrue(sync.status()['pending'])
        self.remote.connected=True;self.assertTrue(sync.synchronize()['server_synced'])
        self.assertEqual(self.remote.value['history'],changed)

    def test_archive_survives_offline_sync_and_reopening(self):
        from history_store import validate,HistoryError
        sync=self.sync();initial=sync.synchronize(history());self.remote.connected=False
        archived=history();archived['conversations'][0]['archived']=True
        sync.write(archived,initial['revision'])
        self.remote.connected=True;sync.synchronize()
        placeholder=history('',identity='placeholder');placeholder['conversations'][0]['messages']=[]
        reopened=self.sync('second').synchronize(placeholder)
        self.assertTrue(reopened['history']['conversations'][0]['archived'])
        invalid=copy.deepcopy(archived);invalid['conversations'][0]['archived']=1
        with self.assertRaises(HistoryError):validate(invalid)

    def test_concurrent_edits_preserve_both_texts(self):
        one=self.sync();a=one.synchronize(history());two=self.sync('second');b=two.synchronize(history(''))
        self.remote.connected=False
        one.write(history('Texte premier PC'),a['revision']);two.write(history('Texte deuxième PC'),b['revision'])
        self.remote.connected=True;one.synchronize();result=two.synchronize()
        self.assertEqual(result['merged'],1)
        contents={row['messages'][0]['content'] for row in result['history']['conversations']}
        self.assertEqual(contents,{'Texte premier PC','Texte deuxième PC'})

    def test_background_revision_conflict_requires_merge(self):
        sync=self.sync();result=sync.synchronize(history())
        self.remote.value={'history':history('Modification distante'),'revision':2,'reset_id':HISTORY_RESET_ID}
        sync.write(history('Modification locale'),result['revision']);sync.flush()
        self.assertTrue(sync.status()['needs_merge']);self.assertEqual(self.remote.value['history'],history('Modification distante'))
        merged=sync.synchronize();self.assertEqual(merged['merged'],1)

    def test_deletions_and_independent_edits_survive_merge(self):
        original=history();original['conversations'].extend(history('Autre texte','second')['conversations'])
        local=copy.deepcopy(original);local['conversations']=local['conversations'][1:];local['currentId']='second'
        server=copy.deepcopy(original);server['conversations'][1]['messages'][0]['content']='Autre texte modifié'
        merged,count=merge(local,server,fingerprints(original))
        self.assertEqual(count,0);self.assertEqual(len(merged['conversations']),1)
        self.assertEqual(merged['conversations'][0]['messages'][0]['content'],'Autre texte modifié')

    def test_history_remains_available_with_model_stopped(self):
        sync=self.sync();result=sync.synchronize(history());self.remote.connected=False;self.remote.code='model_unloaded'
        sync.write(history('Modèle arrêté'),result['revision']);sync.flush()
        self.assertTrue(sync.status()['server_synced']);self.assertEqual(self.remote.value['history'],history('Modèle arrêté'))

    def test_corrupt_metadata_does_not_destroy_local_history(self):
        sync=self.sync();initial=history();sync.synchronize(initial)
        sync.meta_path.write_bytes(client.protect(b'[]'))
        reopened=self.sync();self.assertEqual(reopened.read()['history'],initial)
        self.assertEqual(reopened.synchronize()['history'],initial)

    def test_server_history_isolation_revision_and_backup_migration(self):
        workspace=Workspace(self.home);initial=history('Historique privé')
        try:
            workspace.history_write('a',{'history':initial,'revision':0,'reset_id':HISTORY_RESET_ID})
            self.assertIsNone(workspace.history_read('b')['history'])
            owner=workspace.admin()['owners'][0];self.assertEqual(owner['projects'],0);self.assertEqual(owner['conversations'],1);self.assertGreater(owner['used_bytes'],0)
            with self.assertRaises(Conflict):workspace.history_write('a',{'history':history('Écrasement'),'revision':0,'reset_id':HISTORY_RESET_ID})
            self.assertEqual(Workspace(self.home).history_read('a')['history'],initial)
            backup=workspace.backup();raw=workspace.validate_backup(backup,{'a'});workspace.restore(raw)
            self.assertEqual(workspace.history_read('a')['history'],initial)
            with self.assertRaises(ValueError):workspace.validate_backup(backup,{'b'})
            db=sqlite3.connect(':memory:');db.deserialize(base64.b64decode(backup));db.execute('DROP TABLE client_histories')
            legacy=base64.b64encode(db.serialize()).decode();db.close()
            migrated=workspace.validate_backup(legacy,{'a'});workspace.restore(migrated)
            self.assertIsNone(workspace.history_read('a')['history'])
            workspace.history_write('a',{'history':initial,'revision':0,'reset_id':HISTORY_RESET_ID})
        finally:workspace.stop.set()

    def test_upgrade_erases_old_encrypted_cache_without_backup_or_reappearance(self):
        import history_store
        path=self.home/'legacy.history.dpapi';old=history('À effacer')
        history_store.write(path,client.protect,old,'')
        recovery=path.with_name(path.stem+'.unreadable-old.dpapi')
        recovery.write_bytes(client.protect(b'ancienne copie'))
        sync=HistorySync(self.remote,path,client.protect)
        self.assertIsNone(sync.read()['history']);self.assertFalse(recovery.exists())
        new=history('Nouvelle discussion')
        sync.synchronize(new)
        self.assertEqual(HistorySync(self.remote,path,client.protect).read()['history'],new)
        self.assertEqual(self.remote.value['history'],new)

    def test_server_rejects_old_client_history_upload_after_reset(self):
        workspace=Workspace(self.home)
        with self.assertRaises(Conflict):workspace.history_write('a',{'history':history('Ancienne copie'),'revision':0})
        self.assertIsNone(workspace.history_read('a')['history'])

    def test_preferences_survive_restart_and_preserve_identity(self):
        profile={'url':'wireguard://10.77.0.1:8766','token':'isolated-settings-fixture-identity'}
        with patch.dict(os.environ,{'LOCALAPPDATA':str(self.home)}):
            key=client.local_key(profile);client.save_endpoint(profile,'127.0.0.1:51820')
            values={'theme':'dark','font':'serif','text_size':'large','thinking':False,'sidebar_collapsed':True,'corrector_text':'Mon brouillon confidentiel'}
            client.save_preferences(profile,values);saved=client.client_settings(profile)
            self.assertEqual(saved['preferences'],values);self.assertEqual(saved['endpoint'],'127.0.0.1:51820')
            self.assertEqual(client.local_key(profile),key)
            self.assertNotIn(b'Mon brouillon',client.settings_path(profile).read_bytes())
            with self.assertRaises(ValueError):client.save_preferences(profile,{'font':'invalid'})
            self.assertEqual(client.client_settings(profile)['preferences'],values)

if __name__=='__main__':unittest.main()
