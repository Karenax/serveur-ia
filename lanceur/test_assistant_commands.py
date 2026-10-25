import base64
import datetime as dt
import json
import secrets
import tempfile
import time
import unittest
from pathlib import Path

from workspace import Workspace, Denied, Conflict, PRE_ASSISTANT_SCHEMA, initialize_database
from assistant_commands import execute, tick, local_instant, next_due


class AssistantCommandsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.w=Workspace(Path(self.tmp.name))
        self.p=self.w.action('a',{'action':'project_create','title':'Orion'})['id']

    def tearDown(self):
        self.w.shutdown()
        self.tmp.cleanup()

    def command(self,operation,project=None,**values):
        return execute(self.w,'a',{'operation':operation,**values},project=project,request_key=secrets.token_hex(16))

    def test_memory_mutations_are_scoped_versioned_and_deduplicated(self):
        key=secrets.token_hex(16);v={'operation':'memory_add','text':'Réponses courtes','category':'preference'}
        first=execute(self.w,'a',v,request_key=key)
        self.assertEqual(first,execute(self.w,'a',v,request_key=key))
        with self.assertRaises(Conflict):execute(self.w,'a',{**v,'text':'Autre'},request_key=key)
        m=self.command('memory_list')['memories'][0]
        with self.assertRaises(Denied):self.command('memory_forget',project=self.p,id=m['id'],revision=m['revision'])
        self.command('memory_update',id=m['id'],text='Réponses détaillées',revision=m['revision'])
        with self.assertRaises(Conflict):self.command('memory_forget',id=m['id'],revision=m['revision'])
        m=self.command('memory_list')['memories'][0]
        self.command('memory_forget',id=m['id'],revision=m['revision'])
        self.assertEqual(self.command('memory_list')['memories'],[])
        self.assertEqual(execute(self.w,'b',{'operation':'list'})['memories'],[])

    def test_cancellation_rolls_back_and_legacy_edits_invalidate_revision(self):
        m=self.command('memory_add',text='Français')
        original=self.command('list')['memories'][0]
        self.w.action('a',{'action':'personal_memory_save','id':m['id'],'text':'Anglais'})
        with self.assertRaises(Conflict):self.command('memory_update',id=m['id'],revision=original['revision'],text='Italien')
        calls=[]
        def valid():
            calls.append(1)
            return len(calls)<3
        with self.assertRaises(Denied):execute(self.w,'a',{'operation':'memory_add','text':'Annulée'},request_key=secrets.token_hex(16),valid=valid)
        self.assertEqual(len(self.command('list')['memories']),1)

    def test_note_and_brief_keep_sources_and_never_invent_decisions(self):
        self.command('note_create',project=self.p,title='Budget',text='Budget proposé : 2500 euros.')
        b=self.command('brief_get',project=self.p)
        self.assertEqual(len(b['documents']),1)
        self.assertEqual(b['decisions'],[])
        self.command('memory_add',project=self.p,text='Budget validé : 2400 euros.',category='decision')
        self.assertEqual(len(self.command('brief_get',project=self.p)['decisions']),1)
        other=self.w.action('b',{'action':'project_create','title':'Privé'})['id']
        with self.assertRaises(Denied):self.command('brief_get',project=other)

    def test_simple_reminder_notifies_once_without_a_model(self):
        at=dt.datetime.fromtimestamp(time.time()+60,dt.timezone.utc).isoformat()
        r=self.command('reminder_create',text='Reprendre le dossier',at=at,timezone='Europe/Paris')
        self.assertEqual(tick(self.w,r['due']+1),1)
        self.assertEqual(tick(self.w,r['due']+2),0)
        with self.w.db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM notifications WHERE type='assistant_reminder'").fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],0)
        self.assertEqual(self.command('list')['reminders'][0]['state'],'completed')

    def test_recurrence_follows_paris_calendar_and_rejects_ambiguous_input(self):
        for value in ('2026-03-29T02:30','2026-10-25T02:30'):
            with self.assertRaises(ValueError):local_instant(value,'Europe/Paris')
        due=local_instant('2026-10-24T09:00','Europe/Paris')
        p={'repeat':'daily','due':due,'timezone':'Europe/Paris','weekday':5,'clock':'09:00:00'}
        following=next_due(p,due+1)
        self.assertEqual(following-due,25*3600)
        p.update(due=local_instant('2026-03-28T02:30','Europe/Paris'),clock='02:30:00')
        self.assertEqual(dt.datetime.fromtimestamp(next_due(p,p['due']+1),dt.timezone.utc).date(),dt.date(2026,3,30))

    def test_a_full_account_cannot_delay_another_accounts_reminder(self):
        from unittest.mock import patch
        at=dt.datetime.fromtimestamp(time.time()+60,dt.timezone.utc).isoformat()
        analysis=self.command('reminder_create',project=self.p,text='Compte rendu fictif',kind='analysis',at=at)
        other=execute(self.w,'b',{'operation':'reminder_create','text':'Rappel indépendant','at':at},request_key=secrets.token_hex(16))
        quota=self.w.quota
        def full(db,owner,extra=0):
            if owner=='a':raise ValueError('Quota fictif atteint.')
            return quota(db,owner,extra)
        with patch.object(self.w,'quota',side_effect=full):
            self.assertEqual(tick(self.w,analysis['due']+1),1)
        self.assertEqual(self.command('list',project=self.p)['reminders'][0]['state'],'scheduled')
        self.assertEqual(tick(self.w,analysis['due']+2),1)
        self.assertEqual(tick(self.w,analysis['due']+3),0)
        with self.w.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM notifications').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],1)

    def test_backup_restores_commands_and_upgrades_old_archive(self):
        self.command('memory_add',text='À sauvegarder')
        raw=self.w.validate_backup(self.w.backup(),{'a'})
        self.w.restore(raw)
        self.assertEqual(self.command('list')['memories'][0]['text'],'À sauvegarder')
        import sqlite3
        legacy=sqlite3.connect(':memory:')
        legacy.executescript(PRE_ASSISTANT_SCHEMA)
        legacy.execute("INSERT INTO settings VALUES('history_reset_id','20261006-remove-assistants')")
        legacy.commit()
        upgraded=self.w.validate_backup(base64.b64encode(legacy.serialize()).decode(),{'a'})
        legacy.close()
        self.w.restore(upgraded)
        self.assertEqual(self.command('list')['reminders'],[])

    def test_two_nearby_devices_cannot_both_take_the_same_wake_call(self):
        first=self.w.action('a',{'action':'voice_claim','request_key':secrets.token_hex(16)})
        second=self.w.action('a',{'action':'voice_claim','request_key':secrets.token_hex(16)})
        independent=self.w.action('b',{'action':'voice_claim','request_key':secrets.token_hex(16)})
        self.assertTrue(first['accepted']);self.assertFalse(second['accepted']);self.assertTrue(independent['accepted'])

    def test_generated_brief_is_not_reused_after_sources_change(self):
        self.command('note_create',project=self.p,title='Budget',text='Proposition : 2500 euros.')
        self.command('brief_generate',project=self.p)
        self.w.generation=lambda owner,messages,cancel:'Bilan fictif : proposition de budget, à confirmer.'
        self.assertTrue(self.w.run_one())
        result=self.command('brief_get',project=self.p)
        self.assertIn('narrative',result)
        self.assertEqual(result['narrative'],'Bilan fictif : proposition de budget, à confirmer.')
        self.command('brief_settings',project=self.p,enabled=True)
        self.command('memory_add',project=self.p,text='Décision : budget de 2400 euros.',category='decision')
        result=self.command('brief_get',project=self.p)
        self.assertNotIn('narrative',result);self.assertEqual(result['generated_state'],'outdated');self.assertTrue(result['automatic'])

    def test_global_preference_change_invalidates_generated_brief(self):
        self.command('brief_generate',project=self.p)
        self.w.generation=lambda owner,messages,cancel:'Synthèse avant changement.'
        self.w.run_one()
        self.assertIn('narrative',self.command('brief_get',project=self.p))
        self.command('memory_add',text='Réponds en français.',category='preference',scope='global')
        self.assertEqual(self.command('brief_get',project=self.p)['generated_state'],'outdated')

    def test_reminder_delivery_does_not_wait_for_slow_analysis(self):
        import threading
        began=threading.Event();release=threading.Event()
        def generation(owner,messages,cancel):
            began.set();release.wait(8);return 'Analyse terminée.'
        self.command('task_create',project=self.p,text='Analyse fictive lente')
        reminder=self.command('reminder_create',text='Rappel indépendant',at=dt.datetime.fromtimestamp(time.time()+60,dt.timezone.utc).isoformat())
        with self.w.db() as db:
            row=db.execute('SELECT payload FROM assistant_items WHERE id=?',(reminder['id'],)).fetchone()
            payload=json.loads(row[0]);payload['due']=time.time()+1.5
            db.execute('UPDATE assistant_items SET payload=? WHERE id=?',(json.dumps(payload),reminder['id']))
        self.w.start(generation,lambda owner:True)
        try:
            self.assertTrue(began.wait(4),'Analysis should already be running')
            deadline=time.monotonic()+4;count=0
            while time.monotonic()<deadline:
                with self.w.db() as db:count=db.execute("SELECT COUNT(*) FROM notifications WHERE type='assistant_reminder'").fetchone()[0]
                if count:break
                time.sleep(.05)
            self.assertEqual(count,1);self.assertFalse(release.is_set())
        finally:release.set()

    def test_forgotten_fact_is_not_sent_back_as_old_context(self):
        from assistant_commands import model_history
        self.command('memory_add',text='Je préfère les réponses courtes.')
        memory=self.command('list')['memories'][0]
        history=[{'role':'user','content':'Retiens : je préfère les réponses courtes.'},{'role':'assistant','content':'Bien reçu.'}]
        before=json.dumps(history)
        self.command('memory_forget',id=memory['id'],revision=memory['revision'])
        self.assertNotIn('réponses courtes',model_history(self.w,'a',None,history)[0]['content'])
        self.assertEqual(json.dumps(history),before)

    def test_global_preferences_are_explicit_and_do_not_open_personal_history(self):
        self.command('memory_add',text='Préférence globale choisie',category='preference',scope='global')
        context,_=self.w.context('a',[{'role':'user','content':'Bonjour'}],self.p)
        self.assertIn('Préférence globale choisie',context[0]['content'])
        with self.assertRaises(ValueError):execute(self.w,'a',{'operation':'memory_add','text':'Autre','scope':'global','category':'preference'},request_key=secrets.token_hex(16),request_text='Retiens cette préférence.')
        context,_=self.w.context('b',[{'role':'user','content':'Bonjour'}])
        self.assertNotIn('Préférence globale choisie',context[0]['content'])


if __name__=='__main__':unittest.main()
