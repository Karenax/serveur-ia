"""Lot 6: measured retrieval, faithful citations and owner-scoped source access."""
import base64
import hashlib
import io
import json
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace import Workspace, Denied, PRE_DOCUMENT_SCHEMA, HISTORY_RESET_ID, MAX_FILE


def text_pdf(pages):
    """Tiny genuine PDF fixture with explicit page boundaries, using pypdf only."""
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer=PdfWriter()
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    font_id=writer._add_object(font)
    for value in pages:
        page=writer.add_blank_page(612,792)
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font_id})})
        encoded=value.encode('cp1252').replace(b'\\',b'\\\\').replace(b'(',b'\\(').replace(b')',b'\\)')
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 40 740 Td ('+encoded+b') Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output);return output.getvalue()


class DocumentResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fred-document-research-')
        self.home=Path(self.temp.name);self.workspace=Workspace(self.home)
        self.project=self.action('project_create',title='Dossier de référence')['id']

    def tearDown(self):
        self.workspace.shutdown();self.temp.cleanup()

    def action(self,action,**values):
        return self.workspace.action('alice',{'action':action,'reset_id':HISTORY_RESET_ID,**values})

    def document(self,title,value):
        return self.action('document_create',project=self.project,title=title,text=value)['id']

    def search(self,query,**values):
        return self.action('search',project=self.project,query=query,**values)

    def test_known_questions_rank_the_answer_and_preserve_literal_citations(self):
        references=[('Budget annuel','Le budget annuel validé pour 2027 est de 42500 euros.','Quel est le budget annuel validé pour 2027 ?','42500'),
                    ('Réception','La réception définitive du satellite Orion est prévue le 14 novembre 2027.','Quand est prévue la réception définitive du satellite Orion ?','14 novembre'),
                    ('Rétention','La durée de rétention des factures est de 11 ans.','Quelle est la durée de rétention des factures ?','11 ans'),
                    ('Réseau','Le port du service atelier est 9483.','Quel port utilise le service atelier ?','9483'),
                    ('Responsable','La responsable du programme Calypso est Élise Martel.','Qui est responsable du programme Calypso ?','Élise Martel')]
        for title,value,question,answer in references:
            identity=self.document(title,value)
            self.document('Distracteur '+title,'Présentation générale du dossier, état des travaux et questions courantes. '+title)
            result=self.search(question)
            self.assertEqual(result['sources'][0]['document'],identity)
            self.assertIn(answer,result['sources'][0]['text'])
            self.assertIsNone(result['sources'][0]['page'])
            passage=self.action('source_get',source_id=result['sources'][0]['source_id'])
            self.assertEqual(passage['status'],'current');self.assertEqual(passage['text'],value)
            self.assertEqual(passage['excerpt_hash'],hashlib.sha256(value.encode()).hexdigest())

    def test_long_document_tail_and_selected_document_filter_before_candidate_limit(self):
        for index in range(55):self.document('Catalogue '+str(index),'La consigne du protocole Neptune est générale.')
        filler='Les routines générales assurent le suivi régulier des opérations.\n'*7100
        value=filler[:460000]+'\nLa consigne du protocole Neptune impose le code PLATINE-7192 avant départ.'
        identity=self.document('Manuel très long',value)
        result=self.search('Quelle consigne impose le protocole Neptune avant départ ?',document=identity)
        self.assertEqual(result['sources'][0]['document'],identity)
        self.assertIn('PLATINE-7192',result['sources'][0]['text'])
        metadata=self.action('document_get',id=identity)
        self.assertGreater(metadata['chunk_count'],250);self.assertEqual(metadata['index_state'],'ready')
        self.assertEqual(metadata['indexed_revision'],1);self.assertIsNone(metadata['page_count'])

    def test_real_pdf_extraction_and_authentic_page_numbers(self):
        raw=text_pdf(['Introduction du projet et contexte général.', 'La garantie du véhicule Atlas est de 37 mois.'])
        identity=self.action('document_upload',project=self.project,title='Garantie Atlas.pdf',data=base64.b64encode(raw).decode())['id']
        source=self.search('Quelle garantie pour le véhicule Atlas ?')['sources'][0]
        self.assertEqual(source['document'],identity);self.assertEqual(source['page'],2)
        self.assertIn('37 mois',source['text'])
        self.assertEqual(self.action('source_get',source_id=source['source_id'])['page'],2)
        self.assertEqual(self.action('document_get',id=identity)['page_count'],2)

    def test_old_reference_reports_modification_then_deletion_without_forging_pages(self):
        identity=self.document('Contrat','La prime annuelle est 1900 euros.')
        source=self.search('prime annuelle')['sources'][0]
        self.action('document_save',id=identity,project=self.project,title='Contrat révisé',text='La prime annuelle est 2300 euros.',revision=1)
        previous=self.action('source_get',source_id=source['source_id'])
        self.assertEqual(previous['status'],'modified');self.assertEqual(previous['revision'],1);self.assertEqual(previous['current_revision'],2)
        self.assertIn('1900',previous['text']);self.assertIsNone(previous['page'])
        current=self.search('prime annuelle')['sources'][0]
        self.assertEqual(current['revision'],2);self.assertIn('2300',current['text']);self.assertNotEqual(source['source_id'],current['source_id'])
        self.action('document_delete',id=identity,revision=2)
        self.assertEqual(self.action('source_get',source_id=source['source_id'])['status'],'unavailable')
        self.assertTrue(self.search('prime annuelle')['empty'])
        with self.workspace.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM chunks WHERE document=?',(identity,)).fetchone()[0],0)

    def test_owner_and_project_isolation_even_with_a_known_source_identifier(self):
        identity=self.document('Secret','Le code confidentiel améthyste est 69321.')
        source=self.search('code confidentiel')['sources'][0]
        other=self.workspace.action('bob',{'action':'project_create','title':'Espace Bob'})['id']
        self.workspace.action('bob',{'action':'document_create','project':other,'title':'Sans secret','text':'État de la météo.'})
        with self.assertRaises(Denied):self.workspace.action('bob',{'action':'source_get','source_id':source['source_id']})
        self.assertTrue(self.workspace.action('bob',{'action':'search','project':other,'query':'améthyste'})['empty'])
        with self.assertRaises(Denied):self.action('search',project=other,query='améthyste')
        another=self.action('project_create',title='Autre projet Alice')['id']
        with self.assertRaises(Denied):self.action('search',project=another,document=identity,query='code')
        with self.assertRaises(Denied):self.workspace.action('bob',{'action':'index_status','project':self.project})

    def test_no_result_is_explicit_in_search_and_context(self):
        identity=self.document('Budget','Budget annuel : 900 euros.')
        result=self.search('capacité batterie kryptonium')
        self.assertTrue(result['empty']);self.assertEqual(result['sources'],[])
        self.assertIn('Aucun',result['message'])
        messages,sources=self.workspace.context('alice',[{'role':'user','content':'capacité batterie kryptonium'}],self.project)
        self.assertEqual(sources,[]);self.assertIn('ne fabrique pas de citation',messages[0]['content'])
        self.assertEqual(self.search('Quels sont les documents ?')['sources'],[])
        messages,sources=self.workspace.context('alice',[{'role':'user','content':'capacité batterie kryptonium'}],self.project,identity)
        self.assertEqual(sources,[]);self.assertIn('Aucun passage',messages[0]['content'])
        _,sources=self.workspace.context('alice',[{'role':'user','content':'Résume ce document'}],self.project,identity)
        self.assertEqual(sources[0]['document'],identity)

    def test_job_citations_survive_restart_document_deletion_and_catalogue_eviction(self):
        identity=self.document('Factures','La durée de conservation des factures est de 13 ans.')
        job=self.action('job_create',project=self.project,prompt='Quelle durée de conservation des factures ?',request_key=secrets.token_hex(16))['id']
        self.workspace.generation=lambda owner,messages,cancel:'Conservation : 13 ans, selon Factures v1.'
        self.assertTrue(self.workspace.run_one())
        saved=json.loads(self.action('job_get',id=job)['result']);source=saved['sources'][0]
        self.assertEqual(source['revision'],1);self.assertIn('13 ans',source['text'])
        self.action('document_delete',id=identity,revision=1)
        with self.workspace.db() as db:db.execute('DELETE FROM document_sources')
        reopened=Workspace(self.home)
        try:
            passage=reopened.action('alice',{'action':'source_get','source_id':source['source_id']})
            self.assertEqual(passage['status'],'unavailable');self.assertEqual(passage['text'],source['text'])
            with self.assertRaises(Denied):reopened.action('bob',{'action':'source_get','source_id':source['source_id']})
        finally:reopened.shutdown()

    def test_legacy_schema_migration_keeps_documents_and_rebuilds_unindexed_notes(self):
        old=sqlite3.connect(':memory:');old.executescript(PRE_DOCUMENT_SCHEMA)
        old.execute('ALTER TABLE conversations ADD COLUMN archived INTEGER NOT NULL DEFAULT 0')
        old.execute("INSERT INTO settings VALUES('history_reset_id',?)",(HISTORY_RESET_ID,))
        identity=secrets.token_hex(16)
        old.execute('INSERT INTO projects VALUES(?,?,?,?,0,1,?)',(self.project,'alice','Dossier ancien','',time.time()))
        old.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,1,?)',(identity,'alice',self.project,'Ancienne note','Le seuil thermique est de 82 degrés.',None,'note',time.time()))
        package=base64.b64encode(old.serialize()).decode();old.close()
        raw=self.workspace.validate_backup(package,{'alice'});self.workspace.restore(raw)
        source=self.search('seuil thermique')['sources'][0]
        self.assertEqual(source['document'],identity);self.assertIsNone(source['page'])
        self.assertEqual(self.action('document_get',id=identity)['index_state'],'ready')
        self.workspace.validate_backup(self.workspace.backup(),{'alice'})

    def test_stale_fts_index_is_rebuilt_from_current_passages_on_restart(self):
        identity=self.document('Maintenance','La maintenance annuelle commence le 19 septembre.')
        with self.workspace.db() as db:db.execute("INSERT INTO search(search) VALUES('delete-all')")
        self.assertTrue(self.search('maintenance septembre')['empty'])
        reopened=Workspace(self.home)
        try:
            sources=reopened.action('alice',{'action':'search','project':self.project,'query':'maintenance septembre'})['sources']
            self.assertEqual(sources[0]['document'],identity);self.assertIn('19 septembre',sources[0]['text'])
        finally:reopened.shutdown()

    def test_backup_retains_sources_and_rejects_changed_excerpt_or_foreign_owner(self):
        self.document('Informations','Le stock est de 45 pièces de rechange.')
        source=self.search('stock pièces')['sources'][0]
        value=self.workspace.backup();raw=self.workspace.validate_backup(value,{'alice'});self.workspace.restore(raw)
        self.assertEqual(self.action('source_get',source_id=source['source_id'])['text'],source['text'])
        for statement,args in [('UPDATE document_sources SET text=?',('Fausse citation',)),('UPDATE document_sources SET owner=?',('bob',))]:
            with self.subTest(statement=statement):
                db=sqlite3.connect(':memory:');db.deserialize(base64.b64decode(value));db.execute(statement,args);db.commit()
                bad=base64.b64encode(db.serialize()).decode();db.close()
                with self.assertRaises(ValueError):self.workspace.validate_backup(bad,{'alice','bob'})

    def test_blank_notes_and_invalid_reference_inputs_are_bounded(self):
        identity=self.document('Vide','')
        metadata=self.action('document_get',id=identity)
        self.assertEqual(metadata['index_state'],'empty');self.assertEqual(metadata['chunk_count'],0)
        self.assertEqual(self.action('index_status',project=self.project)['empty'],1)
        for invalid in ('',None,'https://example.com', 'f'*10000):
            with self.subTest(invalid=str(invalid)[:30]),self.assertRaises(ValueError):self.action('source_get',source_id=invalid)
        with self.assertRaises(Denied):self.action('source_get',source_id='f'*64)
        with self.assertRaises(ValueError):self.action('document_upload',project=self.project,title='too-large.txt',data=base64.b64encode(b'x'*(MAX_FILE+1)).decode())


if __name__=='__main__':unittest.main()
