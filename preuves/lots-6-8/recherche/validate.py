"""Reproducible isolated lot-6 validation and retrieval measurements."""
import base64
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'lanceur'))
sys.path.insert(0,str(ROOT/'client-qwen'))
from workspace import Workspace
from test_document_research import text_pdf

DIRECTORY=Path(__file__).resolve().parent
sources=[ROOT/'lanceur/workspace.py',ROOT/'lanceur/notifications.py',ROOT/'lanceur/test_document_research.py']
before={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
suite=unittest.defaultTestLoader.loadTestsFromNames(['test_document_research','test_workspace','test_workspace_worker','test_history_sync','test_backups','test_restoration'])
started=time.perf_counter()
with (DIRECTORY/'tests.log').open('w',encoding='utf-8') as output,contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
elapsed=time.perf_counter()-started
measure={'questions':[]}
with tempfile.TemporaryDirectory(prefix='fred-retrieval-quality-') as temporary:
    workspace=Workspace(Path(temporary));owner='reference'
    project=workspace.action(owner,{'action':'project_create','title':'Dossier de mesure'})['id']
    def action(kind,**values):return workspace.action(owner,{'action':kind,**values})
    dataset=[('Budget annuel','Le budget annuel validé pour 2027 est de 42500 euros.','Quel est le budget annuel validé pour 2027 ?','42500'),
             ('Réception','La réception définitive du satellite Orion est prévue le 14 novembre 2027.','Quand est prévue la réception définitive du satellite Orion ?','14 novembre'),
             ('Rétention','La durée de rétention des factures est de 11 ans.','Quelle est la durée de rétention des factures ?','11 ans'),
             ('Réseau','Le port du service atelier est 9483.','Quel port utilise le service atelier ?','9483'),
             ('Responsable','La responsable du programme Calypso est Élise Martel.','Qui est responsable du programme Calypso ?','Élise Martel')]
    for title,value,question,answer in dataset:
        identity=action('document_create',project=project,title=title,text=value)['id']
        action('document_create',project=project,title='Distracteur '+title,text='Présentation générale du dossier, état des travaux et questions courantes. '+title)
        start=time.perf_counter();response=action('search',project=project,query=question);duration=time.perf_counter()-start
        first=response['sources'][0]
        measure['questions'].append({'question':question,'expected_answer':answer,'correct_document_at_rank_1':first['document']==identity,'answer_in_literal_excerpt':answer in first['text'],'no_invented_page':first['page'] is None,'query_seconds':duration})
    filler=('Les routines générales assurent le suivi régulier des opérations.\n'*7100)[:460000]
    long_text=filler+'\nLa consigne du protocole Neptune impose le code PLATINE-7192 avant départ.'
    start=time.perf_counter();identity=action('document_create',project=project,title='Manuel très long',text=long_text)['id'];import_seconds=time.perf_counter()-start
    start=time.perf_counter();response=action('search',project=project,document=identity,query='Quelle consigne impose le protocole Neptune avant départ ?');query_seconds=time.perf_counter()-start
    metadata=action('document_get',id=identity)
    measure['long_document']={'characters':len(long_text),'utf8_bytes':len(long_text.encode()),'passages':metadata['chunk_count'],'index_state':metadata['index_state'],'index_seconds':import_seconds,'query_seconds':query_seconds,'tail_answer_retrieved':bool(response['sources'] and 'PLATINE-7192' in response['sources'][0]['text'])}
    pdf=text_pdf(['Introduction du projet et contexte général.','La garantie du véhicule Atlas est de 37 mois.'])
    start=time.perf_counter();pdf_id=action('document_upload',project=project,title='Garantie Atlas.pdf',data=base64.b64encode(pdf).decode())['id'];pdf_seconds=time.perf_counter()-start
    pdf_source=action('search',project=project,query='Quelle garantie pour le véhicule Atlas ?')['sources'][0]
    measure['pdf']={'original_bytes':len(pdf),'extraction_subprocess_seconds':pdf_seconds,'expected_page':2,'actual_page':pdf_source['page'],'correct_document':pdf_source['document']==pdf_id,'answer_in_literal_excerpt':'37 mois' in pdf_source['text']}
    measure['missing_answer']={'empty':action('search',project=project,query='capacité batterie kryptonium')['empty']}
    measure['precision_at_1']=sum(q['correct_document_at_rank_1'] for q in measure['questions'])/len(measure['questions'])
    measure['literal_answer_rate']=sum(q['answer_in_literal_excerpt'] for q in measure['questions'])/len(measure['questions'])
    measure['all_checks_pass']=all(q['correct_document_at_rank_1'] and q['answer_in_literal_excerpt'] and q['no_invented_page'] for q in measure['questions']) and measure['long_document']['tail_answer_retrieved'] and measure['pdf']['actual_page']==2 and measure['pdf']['correct_document'] and measure['pdf']['answer_in_literal_excerpt'] and measure['missing_answer']['empty']
    workspace.shutdown()
after={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
payload={'status':'PASS' if result.wasSuccessful() and measure['all_checks_pass'] and before==after else 'FAIL','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'seconds':elapsed,'sources_before':before,'sources_after':after,'sources_unchanged':before==after,'scope':'isolated temporary owners, SQLite, documents and server fixtures; no production access','measurement':measure}
(DIRECTORY/'validation.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:payload[key] for key in ('status','tests_run','failures','errors','seconds','sources_unchanged')},ensure_ascii=False))
sys.exit(0 if payload['status']=='PASS' else 1)
