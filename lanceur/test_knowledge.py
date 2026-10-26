"""Scope isolation, source lifecycle, cache recovery and bounded EG2 contracts."""
import base64
from copy import deepcopy
import json
from pathlib import Path
import secrets
import sqlite3
import tempfile
import unittest
from workspace import Workspace, Denied, HISTORY_RESET_ID, PRE_EMBEDDING_SCHEMA
from knowledge import Knowledge, MAX_OWNER_ROWS
from embeddings import validate_vectors


class FixtureEngine:
    state='pret'
    active=True
    calls=0
    def enabled(self): return self.active
    def stop(self): pass
    def tick(self): pass
    def encode(self,texts,mode='document',timeout=8):
        self.calls+=1
        return [[1.0]+[0.0]*767 for _ in texts]


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fred-eg2-tests-')
        self.w=Workspace(Path(self.temp.name));self.e=FixtureEngine();self.e.active=True
        self.k=Knowledge(self.w,self.e);self.w.knowledge=self.k
        self.p=self.action('project_create',title='Projet A')['id']
        self.q=self.action('project_create',title='Projet B')['id']
    def tearDown(self): self.w.shutdown();self.temp.cleanup()
    def action(self,action,owner='alice',**values):
        return self.w.action(owner,dict(action=action,reset_id=HISTORY_RESET_ID,**values))
    def history(self,rows,owner='alice'):
        self.w.history_write(owner,{'history':{'conversations':rows,'currentId':rows[0]['id']},
            'revision':self.w.history_read(owner)['revision'],'reset_id':HISTORY_RESET_ID})
    def row(self,id,text,project=None,**values):
        return {'id':id,'title':'Discussion '+id,'messages':[{'role':'user','content':text}],
            **({'project_id':project} if project else {}),**values}
    def retrieve(self,scope=None,owner='alice',query='Question différente'):
        with self.w.db() as db:return self.k.retrieve(db,owner,scope or '',query)

    def test_project_personal_and_owner_isolation_before_ranking(self):
        self.action('document_create',project=self.p,title='A',text='Secret du projet A')
        self.action('document_create',project=self.q,title='B',text='Secret du projet B')
        self.history([self.row('global','Secret personnel'),self.row('project','Échange A',self.p)])
        self.history([self.row('bob','Secret Bob')],owner='bob')
        self.k.synchronize()
        self.assertEqual({r['scope'] for r in self.retrieve(self.p)},{self.p})
        self.assertEqual([r['text'] for r in self.retrieve()],['Secret personnel'])
        self.assertEqual([r['text'] for r in self.retrieve(owner='bob')],['Secret Bob'])
        for r in self.retrieve(self.p):self.assertNotIn('Secret personnel',r['text'])

    def test_no_project_memory_or_documents_in_personal_context(self):
        self.action('memory_create',project=self.p,text='Préférence du projet uniquement')
        self.history([self.row('global','Préférence générale personnelle')])
        self.k.synchronize()
        messages,sources=self.w.context('alice',[{'role':'user','content':'Préférence'}])
        self.assertIn('générale personnelle',messages[0]['content'])
        self.assertNotIn('projet uniquement',messages[0]['content'])
        self.assertTrue(sources)

    def test_voice_excludes_current_conversation_and_keeps_full_scope_and_sources(self):
        self.history([self.row('current-chat','Décision du jour Orion.'),self.row('other-chat','Ancien engagement Orion.')])
        self.k.synchronize();calls=self.e.calls
        messages=[{'role':'system','content':'Kiara oral.'},{'role':'user','content':'Précision ancienne.'},{'role':'assistant','content':'Réponse ancienne.'},{'role':'user','content':'Quel engagement Orion ?'}]
        result,sources=self.w.context('alice',messages,voice_conversation='currentchat')
        self.assertTrue(sources);self.assertEqual({r['conversation'] for r in sources},{'other-chat'})
        self.assertEqual(result[1:4],messages[:3]);self.assertEqual(result[-1],messages[-1])
        self.assertIn('Ancien engagement',result[-2]['content']);self.assertNotIn('"passage"',result[-2]['content'])
        self.assertIn('passage',sources[0])

    def test_empty_cache_does_not_run_an_embedding_query(self):
        before=self.e.calls
        self.assertEqual(self.retrieve(),[]);self.assertEqual(before,self.e.calls)

    def test_deleted_or_updated_documents_are_rejected_before_reindex(self):
        id=self.action('document_create',project=self.p,title='Contrat',text='Ancien engagement')['id']
        self.k.synchronize();self.assertTrue(self.retrieve(self.p))
        self.action('document_save',project=self.p,id=id,revision=1,title='Contrat',text='Nouvel engagement')
        self.assertEqual(self.retrieve(self.p),[])
        self.k.synchronize();self.assertEqual(self.retrieve(self.p)[0]['text'],'Nouvel engagement')
        self.action('document_delete',id=id,revision=2)
        self.assertEqual(self.retrieve(self.p),[])

    def test_conversation_move_removes_old_scope_even_with_stale_client_copy(self):
        id=secrets.token_hex(16)
        self.history([self.row(id,'Engagement avant déplacement',self.p)])
        self.action('conversation_save',project=self.p,id=id,title='Discussion',messages=[{'role':'user','content':'Engagement avant déplacement'}],revision=0)
        self.k.synchronize();self.assertTrue(self.retrieve(self.p))
        self.action('conversation_move',id=id,project=self.q,revision=1)
        self.assertEqual(self.retrieve(self.p),[])
        self.k.synchronize();self.assertEqual(self.retrieve(self.p),[])
        self.assertTrue(self.retrieve(self.q));self.assertEqual(self.retrieve(),[])

    def test_archiving_and_deleted_history_are_not_recalled(self):
        self.history([self.row('old','Ancien accord')]);self.k.synchronize()
        item=self.retrieve()[0]
        self.history([self.row('old','Ancien accord',archived=True)])
        self.assertEqual(self.retrieve(),[])
        with self.w.db() as db:self.assertIsNone(self.k.read_reference(db,'alice',item['id']))
        self.history([self.row('new','Nouvel accord')]);self.k.synchronize()
        self.assertEqual([r['text'] for r in self.retrieve()],['Nouvel accord'])

    def test_deleted_server_conversation_does_not_return_from_old_client_history(self):
        id=secrets.token_hex(16);self.history([self.row(id,'Échange à supprimer',self.p)])
        self.action('conversation_save',id=id,project=self.p,title='Discussion '+id,messages=[{'role':'user','content':'Échange à supprimer'}],revision=0)
        self.k.synchronize();self.assertTrue(self.retrieve(self.p))
        self.action('conversation_delete',id=id,revision=1)
        self.assertEqual(self.retrieve(self.p),[]);self.k.synchronize();self.assertEqual(self.retrieve(self.p),[])
        self.history([self.row('new','Nouvelle discussion')])
        with self.w.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM knowledge_exclusions').fetchone()[0],0)

    def test_reasoning_interrupted_answers_and_foreign_project_claims_are_excluded(self):
        bob=self.action('project_create',owner='bob',title='Bob')['id']
        row=self.row('safe','Question normale');row['messages'].extend([
            {'role':'assistant','content':'Réponse inachevée secrète','interrupted':True},
            {'role':'assistant','content':'Réponse terminée','reasoning_content':'Réflexion secrète'}])
        self.history([row,self.row('forged','Tentative de mauvais espace',bob)])
        self.k.synchronize();values=' '.join(r['text'] for r in self.retrieve())
        self.assertIn('Réponse terminée',values)
        self.assertNotIn('secrète',values);self.assertNotIn('mauvais espace',values)

    def test_personal_memories_ownership_quota_and_backup(self):
        id=self.action('personal_memory_create',text='Réponses en français')['id']
        with self.assertRaises(Denied):self.action('personal_memory_delete',owner='bob',id=id)
        self.k.synchronize();self.assertEqual(self.retrieve()[0]['kind'],'personal_memory')
        raw=self.w.validate_backup(self.w.backup(),{'alice'})
        revision=self.w.snapshot('alice')['personal_memories'][0]['revision']
        self.action('personal_memory_delete',id=id,revision=revision);self.w.restore(raw)
        self.assertEqual(self.w.snapshot('alice')['personal_memories'][0]['text'],'Réponses en français')
        with self.k.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM entries').fetchone()[0],0)

    def test_known_pre_eg2_backup_migrates_without_changing_data(self):
        old=sqlite3.connect(':memory:');old.executescript(PRE_EMBEDDING_SCHEMA)
        old.execute('ALTER TABLE conversations ADD COLUMN archived INTEGER NOT NULL DEFAULT 0')
        old.execute("INSERT INTO settings VALUES('history_reset_id',?)",(HISTORY_RESET_ID,))
        old.commit();encoded=base64.b64encode(old.serialize()).decode();old.close()
        raw=self.w.validate_backup(encoded,set());restored=sqlite3.connect(':memory:');restored.deserialize(raw)
        self.assertEqual(restored.execute('SELECT COUNT(*) FROM personal_memories').fetchone()[0],0);restored.close()

    def test_repeated_sync_and_append_reuse_existing_vectors(self):
        row=self.row('stable','Première phrase');self.history([row]);self.k.synchronize()
        self.assertEqual(self.k.synchronize(),0)
        row['messages'].append({'role':'assistant','content':'Deuxième phrase'})
        self.history([row]);self.assertEqual(self.k.synchronize(),1)

    def test_engine_unavailable_keeps_lexical_retrieval_and_sources(self):
        self.history([self.row('global','La rétention des sauvegardes est mensuelle')]);self.k.synchronize()
        self.e.state='arrete'
        rows=self.retrieve(query='rétention sauvegardes');self.assertTrue(rows)
        with self.w.db() as db:
            self.assertIsNotNone(self.k.read_reference(db,'alice',rows[0]['id']))
            self.assertIsNone(self.k.read_reference(db,'bob',rows[0]['id']))

    def test_vector_response_validation_rejects_nan_wrong_dimensions_and_norm(self):
        for vector in ([float('nan')]+[0]*767,[0]*768,[1]*768,[1]*767):
            with self.assertRaises(ValueError):validate_vectors([vector],1)
        self.assertEqual(validate_vectors([[1]+[0]*767],1)[0][0],1)


if __name__=='__main__':unittest.main()
