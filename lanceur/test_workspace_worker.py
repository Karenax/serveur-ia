"""Retired task entry points and the remaining reminder scheduler."""
import datetime as dt
import json
from pathlib import Path
import secrets
import tempfile
import time
import unittest
from unittest.mock import Mock

from assistant_commands import execute
from notifications import Notifications
from workspace import Workspace


class WorkspaceRetirementTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='kiara-without-tasks-')
        self.workspace = Workspace(self.directory.name)
        self.owner = 'a'
        self.project = self.workspace.action(self.owner, {'action':'project_create','title':'Projet fictif'})['id']

    def tearDown(self):
        self.workspace.shutdown()
        self.directory.cleanup()

    def test_retired_commands_rejected_and_capabilities_removed(self):
        for action in ('job_create','job_get','job_retry','job_pause','job_cancel'):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.workspace.action(self.owner, {'action':action,'project':self.project})
            with self.subTest(admin=action), self.assertRaises(ValueError):
                self.workspace.admin_action({'action':action}, {self.owner})
        for operation in ('task_list','task_create','task_pause','task_cancel','brief_generate','brief_settings'):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                execute(self.workspace,self.owner,{'operation':operation},project=self.project,request_key=secrets.token_hex(16))
        snapshot=self.workspace.snapshot(self.owner)
        self.assertNotIn('jobs',snapshot)
        self.assertNotIn('jobs',snapshot['capabilities'])
        self.assertNotIn('jobs',snapshot['limits'])
        self.assertNotIn('jobs',self.workspace.admin())

    def test_archived_jobs_never_execute_but_reminders_still_fire(self):
        identity=secrets.token_hex(16)
        with self.workspace.db() as db:
            db.execute('INSERT INTO jobs(id,owner,project,title,prompt,kind,state,created,due,request_key) VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (identity,self.owner,self.project,'Ancienne analyse','Texte fictif','analysis','queued',0,0,identity))
        generate=Mock(side_effect=AssertionError('Retired jobs must never call a model'))
        due=time.time()+30
        reminder=execute(self.workspace,self.owner,{'operation':'reminder_create','text':'Rappel fictif',
                         'at':dt.datetime.fromtimestamp(due,dt.timezone.utc).isoformat()},request_key=secrets.token_hex(16))
        with self.workspace.db() as db:
            row=db.execute('SELECT payload FROM assistant_items WHERE id=?',(reminder['id'],)).fetchone()
            payload=json.loads(row[0]);payload['due']=time.time()-1
            db.execute('UPDATE assistant_items SET payload=? WHERE id=?',(json.dumps(payload),reminder['id']))
        self.workspace.hermes=Mock(generate=generate)
        self.workspace.start(lambda owner:True)
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            items=Notifications(self.workspace).snapshot(self.owner)['items']
            if items:break
            time.sleep(.05)
        self.assertEqual([n['type'] for n in items],['assistant_reminder'])
        generate.assert_not_called()
        with self.workspace.db() as db:
            self.assertEqual(db.execute('SELECT state FROM jobs WHERE id=?',(identity,)).fetchone()[0],'queued')
        raw=self.workspace.validate_backup(self.workspace.backup(),{self.owner})
        self.workspace.shutdown()
        self.workspace.restore(raw)
        self.assertNotIn('jobs',self.workspace.snapshot(self.owner))

    def test_old_policy_and_notifications_remain_restorable_and_hidden(self):
        identity=secrets.token_hex(16)
        with self.workspace.db() as db:
            db.execute('INSERT INTO policies VALUES(?,?)',(self.owner,json.dumps({'storage_mb':20,'projects':50,'jobs':5,'web':False})))
            db.execute('INSERT INTO notifications(id,owner,type,source_key,target,created) VALUES(?,?,?,?,?,?)',
                       (identity,self.owner,'job_completed','old-job',json.dumps({'kind':'notifications'}),time.time()))
        inbox=Notifications(self.workspace)
        self.assertEqual(inbox.snapshot(self.owner)['items'],[])
        self.assertEqual(inbox.snapshot(self.owner)['unread_count'],0)
        self.assertNotIn('jobs',self.workspace.snapshot(self.owner)['limits'])
        with self.assertRaises(ValueError):inbox.publish(self.owner,'job_completed','new-job')
        self.workspace.validate_backup(self.workspace.backup(),{self.owner})


if __name__ == '__main__':
    unittest.main()
