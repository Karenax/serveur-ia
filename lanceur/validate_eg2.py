"""Real offline CPU model, French retrieval and source isolation on synthetic data."""
from array import array
import json
from pathlib import Path
import sys
import tempfile
import time
import psutil
from workspace import Workspace,HISTORY_RESET_ID
from embeddings import EmbeddingService
from knowledge import Knowledge


def main():
    target=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent.parent/'preuves/eg2-20261011/real-model.json'
    report={'synthetic_only':True,'checks':[]}
    with tempfile.TemporaryDirectory(prefix='fred-eg2-real-') as temporary:
        w=Workspace(Path(temporary));engine=EmbeddingService(w);knowledge=Knowledge(w,engine);w.knowledge=knowledge
        try:
            started=time.monotonic();engine.configure(True)
            while engine.state!='pret' and time.monotonic()-started<120:
                engine.tick();time.sleep(.25)
            assert engine.state=='pret',engine.status()
            report['load_seconds']=time.monotonic()-started;report['engine']=engine.status()
            report['rss_mib']=psutil.Process(engine.status()['pid']).memory_info().rss/1048576
            def action(name,**values):return w.action('alice',{'action':name,'reset_id':HISTORY_RESET_ID,**values})
            p=action('project_create',title='Atelier')['id'];q=action('project_create',title='Autre projet')['id']
            fixtures=[('Sauvegardes','Les archives quotidiennes sont gardées sept jours, les hebdomadaires quatre semaines et les mensuelles six mois.',
                'Combien de temps garde-t-on les copies de secours ?'),
                ('Pneumatiques','Le remplacement des pneus hiver est prévu le 24 novembre.',
                'À quelle date change-t-on les roues pour la saison froide ?'),
                ('Contact','La personne qui dirige le chantier est Sophie Martin.',
                'Qui est responsable des travaux ?'),
                ('Livraison','Le colis arrivera mardi entre neuf heures et midi.',
                'Quand recevra-t-on le paquet ?'),
                ('Réseau','Le service atelier écoute sur le port TCP 9483.',
                'Quel numéro de port utilise le service atelier ?'),
                ('Budget','Le budget approuvé pour la rénovation est de 42500 euros.',
                'Quelle somme a été autorisée pour rénover ?')]
            expected=[]
            for title,text,question in fixtures:
                id=action('document_create',project=p,title=title,text=text)['id'];expected.append((id,question))
            action('document_create',project=q,title='Autre secret',text='Le code de l’autre projet est SECRET-PROJET-B.')
            history={'conversations':[{'id':'personal','title':'Préférence personnelle','messages':[{'role':'user','content':'Pour mes repas, je préfère une alimentation végétarienne.'}]}],'currentId':'personal'}
            w.history_write('alice',{'history':history,'revision':0,'reset_id':HISTORY_RESET_ID})
            started=time.monotonic()
            while True:
                knowledge.synchronize()
                if not knowledge.pending:break
            report['index_seconds']=time.monotonic()-started;report['index']=knowledge.status()
            questions=[]
            for id,question in expected:
                vector=engine.encode([question],mode='query')[0]
                with knowledge.db() as cache:
                    scores=[]
                    for row in cache.execute('SELECT object,vector FROM entries WHERE owner=? AND scope=?',('alice',p)):
                        values=array('f');values.frombytes(row['vector']);scores.append((sum(a*b for a,b in zip(vector,values)),row['object']))
                scores.sort(reverse=True)
                with w.db() as db:found=knowledge.retrieve(db,'alice',p,question)
                questions.append({'question':question,'expected_top':scores[0][1]==id,'expected_score':next(v for v,key in scores if key==id),
                    'next_score':scores[1][0],'retrieved_expected':bool(found and found[0]['object']==id),'results':len(found)})
            report['questions']=questions
            assert all(q['expected_top'] for q in questions),questions
            with w.db() as db:
                personal=knowledge.retrieve(db,'alice','','Que dois-je cuisiner selon mes goûts ?')
                project=knowledge.retrieve(db,'alice',p,'Que dois-je cuisiner selon mes goûts ?')
                foreign=knowledge.retrieve(db,'bob',p,'sauvegardes')
            report['personal_retrieval']=bool(personal)
            assert not foreign
            assert all('végétarienne' not in r['text'] for r in project)
            report['checks']+=['owner_isolation','project_personal_isolation','all_french_expected_top_scores']
            assert all(q['retrieved_expected'] for q in questions),questions
            assert personal,'Mémoire personnelle non retrouvée.'
            # Kiara attaches exact source passages to the context sent to Strata.
            messages,sources=w.context('alice',[{'role':'user','content':fixtures[0][2]}],p)
            assert any('sept jours' in s['text'] for s in sources)
            assert 'sept jours' in messages[0]['content']
            report['checks'].append('qwen_context_contains_exact_sources')
            worker_pid=engine.status()['pid']
            engine.stop()
            assert not psutil.pid_exists(worker_pid), 'Le vrai processus EG2 doit être arrêté.'
            report['checks'].append('worker_process_stops_with_service')
            with w.db() as db:assert knowledge.retrieve(db,'alice',p,'budget rénovation')
            report['checks'].append('lexical_fallback_when_engine_stopped')
            report['passed']=True
        finally:w.shutdown()
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()
