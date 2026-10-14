"""OpenCode picker preferences: isolated databases, exact backups, no GUI process."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'client-qwen'))
import app_integrations
import opencode_visibility as visibility


class VisibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fred-picker-test-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'drafts.sqlite'
        self.desktop={'state_path':str(self.path),'format':'sqlite','executable':str(self.root/'OpenCode.exe')}
        self.original=json.dumps({'user':[{'providerID':'other','modelID':'keep-hidden','visibility':'hide','favorite':True},
                                        {'providerID':'serveur-fred','modelID':'old','visibility':'hide'}],
                                  'recent':[{'providerID':'other','modelID':'recent'}],'variant':{'other/recent':'high'},'extra':'keep'})
        self.patch=patch.object(visibility,'running',return_value=False);self.patch.start();self.addCleanup(self.patch.stop)

    def database(self,raw=None):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE state(name TEXT,key TEXT,value TEXT,updated_at INTEGER,PRIMARY KEY(name,key))')
            db.execute('CREATE TABLE document(key TEXT PRIMARY KEY,value TEXT)')
            db.execute('INSERT INTO document VALUES(?,?)',('draft','private draft'))
            db.execute('INSERT INTO state VALUES(?,?,?,?)',('other','setting','untouched',123))
            if raw is not None:db.execute('INSERT INTO state VALUES(?,?,?,?)',(visibility.NAMESPACE,'model',raw,456))

    def rows(self):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute('SELECT * FROM state ORDER BY name,key').fetchall(),db.execute('SELECT * FROM document').fetchall()

    def enable(self,model='fred-qwen'):return visibility.enable(self.desktop,'serveur-fred',model)

    def test_sqlite_changes_only_target_visibility_and_keeps_exact_previous_row(self):
        self.database(self.original);before=self.rows();result=self.enable()
        self.assertEqual(result['status'],'enabled')
        saved=json.loads(Path(result['backup']).read_text(encoding='utf-8'))
        self.assertEqual(saved['previous'],{'value':self.original,'updated_at':456})
        after=self.rows();self.assertEqual(before[1],after[1]);self.assertEqual(before[0][1],after[0][1])
        changed=json.loads(after[0][0][2]);expected=json.loads(self.original)
        expected['user'].append({'providerID':'serveur-fred','modelID':'fred-qwen','visibility':'show'})
        self.assertEqual(changed,expected)
        again=self.enable();self.assertEqual(again,{'status':'enabled','backup':None});self.assertEqual(after,self.rows())

    def test_existing_hidden_model_keeps_its_other_preferences(self):
        original={'user':[{'providerID':'serveur-fred','modelID':'fred-qwen','visibility':'hide','favorite':True}],'recent':[],'variant':{}}
        self.database(json.dumps(original));self.enable()
        changed=json.loads(self.rows()[0][0][2]);original['user'][0]['visibility']='show'
        self.assertEqual(changed,original)

    def test_new_model_namespace_has_the_full_desktop_shape(self):
        self.database();result=self.enable();self.assertEqual(result['status'],'enabled')
        self.assertIsNone(json.loads(Path(result['backup']).read_text())['previous'])
        value=json.loads(self.rows()[0][0][2]);self.assertEqual(value['recent'],[]);self.assertEqual(value['variant'],{})

    def test_open_desktop_never_changes_cached_settings(self):
        self.database(self.original);before=self.rows()
        with patch.object(visibility,'running',return_value=True):self.assertEqual(self.enable()['status'],'close_required')
        with patch.object(visibility,'running',side_effect=[False,True]):self.assertEqual(self.enable()['status'],'close_required')
        self.assertEqual(before,self.rows());self.assertFalse(list(self.root.glob('*.fred-model-backup-*')))

    def test_unsupported_database_and_invalid_preferences_are_not_rewritten(self):
        for source in ('{bad','[]','{"user":{}}','{"user":[null]}',json.dumps({'user':[],'extra':'x'*(visibility.MAX_STATE+1)})):
            with self.subTest(source=source[:30]):
                self.path.unlink(missing_ok=True);self.database(source);before=self.rows()
                self.assertEqual(self.enable()['status'],'manual');self.assertEqual(before,self.rows())
        self.path.unlink();self.assertEqual(self.enable()['status'],'manual');self.assertFalse(self.path.exists())

    def test_legacy_namespace_is_ready_for_desktop_import_and_preserves_other_keys(self):
        self.desktop.update(format='legacy',state_path=str(self.root/'opencode.global.dat'))
        path=Path(self.desktop['state_path']);result=self.enable()
        self.assertEqual(result,{'status':'enabled','backup':None})
        value=json.loads(path.read_text());self.assertEqual(json.loads(value['model'])['user'][0]['visibility'],'show')
        original=json.dumps({'model':self.original,'other':'opaque-json-string'},indent=2).encode()
        path.write_bytes(original);result=self.enable()
        self.assertEqual(Path(result['backup']).read_bytes(),original)
        self.assertEqual(json.loads(path.read_text())['other'],'opaque-json-string')
        before=path.read_bytes();self.assertIsNone(self.enable()['backup']);self.assertEqual(path.read_bytes(),before)

    def test_detect_uses_roaming_desktop_state_and_integration_reports_remaining_action(self):
        local=self.root/'local';exe=local/'Programs/@opencodedesktop/OpenCode.exe';exe.parent.mkdir(parents=True);exe.touch()
        roaming=self.root/'roaming';env={'LOCALAPPDATA':str(local),'APPDATA':str(roaming)}
        apps=app_integrations.detect(self.root,env,lambda _:None)
        self.assertEqual(apps['opencode']['desktop']['state_path'],str(roaming/'ai.opencode.desktop/opencode.global.dat'))
        with patch.object(visibility,'running',return_value=True):
            result=app_integrations.install('opencode','http://127.0.0.1:17841/v1','test-key-'+'x'*40,'fred-qwen',apps)
        self.assertEqual(result['visibility']['status'],'close_required');self.assertIn('fermez complètement',result['message'])
        self.assertNotIn('Modèle activé',result['message'])
        result=app_integrations.install('opencode','http://127.0.0.1:17841/v1','test-key-'+'x'*40,'fred-qwen',apps)
        self.assertEqual(result['visibility']['status'],'enabled');self.assertIn('Modèle activé',result['message'])


if __name__=='__main__':unittest.main()
