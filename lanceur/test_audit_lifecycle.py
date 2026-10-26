"""Private runtime independence, data preservation and semantic intent guards."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from assistant_commands import check_intent
from hermes_runtime import private_installation
from workspace import Workspace


class AuditLifecycleTests(unittest.TestCase):
    def test_missing_reset_marker_preserves_current_server_history(self):
        with tempfile.TemporaryDirectory() as folder:
            first=Workspace(folder)
            history={'currentId':'one','conversations':[{'id':'one','title':'À garder','messages':[]}]}
            with first.db() as db:
                db.execute('INSERT INTO client_histories VALUES(?,?,1,1)',('a',json.dumps(history)))
                db.execute("DELETE FROM settings WHERE key='history_reset_id'")
                db.execute('PRAGMA user_version=1')
            first.shutdown()
            second=Workspace(folder)
            try:
                self.assertEqual(second.history_read('a')['history'],history)
                with second.db() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
            finally:second.shutdown()

    def test_private_runtime_does_not_read_personal_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'source/hermes_cli';source.mkdir(parents=True);(source/'main.py').write_text('')
            python=root/'venv/Scripts/python.exe';python.parent.mkdir(parents=True);python.touch()
            for name in ('installs','tools'):(root/name).mkdir()
            pointer=root/'runtime.json'
            pointer.write_text(json.dumps({'format':1,'validated':True,'source':str(root/'source'),
                'python':str(python),'source_commit':'a'*40,'dependencies':str(root/'installs'),'tools':str(root/'tools')}))
            with patch('subprocess.run',side_effect=AssertionError('Personal bootstrap must not run')):
                runtime=private_installation(pointer)
                from hermes_service import installation
                with patch('hermes_runtime.POINTER',pointer):
                    self.assertEqual(installation()['python'],python)
            self.assertEqual(runtime['python'],python)
            self.assertTrue(runtime['private'])

    def test_negative_quoted_and_explanatory_requests_do_not_authorize_writes(self):
        for operation, phrase in (
            ('memory_forget','N’oublie pas mon adresse.'),
            ('memory_add','Ne mémorise pas cette information.'),
            ('reminder_cancel','Explique la phrase « annule mon rappel » sans rien modifier.'),
            ('task_cancel','Ne supprime jamais ma tâche.'),
            ('task_cancel','Ne supprime rien.'),
            ('memory_update','Traduis « modifie mon souvenir ».'),
        ):
            with self.subTest(phrase=phrase),self.assertRaises(ValueError):check_intent(operation,phrase)
        for operation, phrase in (
            ('memory_add','Mémorise mon adresse.'),
            ('memory_forget','Oublie mon adresse.'),
            ('reminder_cancel','Annule mon rappel.'),
            ('memory_update','Peux-tu modifier mon souvenir ?'),
            ('memory_add','Ne supprime rien, mais mémorise ma préférence.'),
            ('reminder_create','N’oublie pas de me rappeler mon rendez-vous.'),
        ):
            with self.subTest(phrase=phrase):check_intent(operation,phrase)


if __name__=='__main__':unittest.main()
