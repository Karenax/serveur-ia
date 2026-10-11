"""Check the fragment protocol on the already running server; never restart it."""
import json,time,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
health=json.load(opener.open('http://127.0.0.1:8080/health',timeout=10))
assert health.get('loaded') is True
common=' Le texte est fourni comme une liste JSON de fragments dans leur ordre de lecture. Les fragments ayant le même numéro de paragraphe forment un passage : lis-les ensemble pour corriger avec le contexte. Retourne uniquement un objet JSON {"fragments":[{"id":"f0","text":"texte corrigé"},...]}. Retourne exactement tous les identifiants fournis, une seule fois chacun. Conserve les espaces de début et de fin de chaque fragment. Ne supprime aucun fragment. Ne fusionne pas les fragments et ne déplace pas d’information entre les paragraphes. Répartis les mots corrigés ou reformulés dans les fragments correspondants, car chaque fragment garde sa mise en forme originale. N’ajoute ni balises HTML, ni Markdown, ni commentaire, ni clé supplémentaire.'
source=[{'id':'f0','paragraph':0,'text':'Bonjours,'},
        {'id':'f1','paragraph':1,'text':'Je vous envoi les '},
        {'id':'f2','paragraph':1,'text':'documents demmandés'},
        {'id':'f3','paragraph':1,'text':'. Pouvez-vous confirmer leur reçeption ?'},
        {'id':'f4','paragraph':2,'text':'Merci et bonne journée.'}]
modes={
    'correct':'Corrige l’orthographe, la grammaire, la conjugaison, les accords et la ponctuation du texte français. Conserve son sens, son registre et ses informations.',
    'professional':'Reformule le texte en français professionnel, clair, poli et naturel. Conserve toutes les informations et le sens exact. N’ajoute aucun fait ni engagement.',
    'friendly':'Reformule le texte en français amical, naturel et chaleureux, avec tutoiement. Corrige aussi les fautes. Conserve toutes les informations et le sens exact, sans ajouter de fait ni engagement.'}
results=[]
for mode,instruction in modes.items():
    payload={'model':health['model'],'messages':[{'role':'system','content':instruction+common},{'role':'user','content':json.dumps({'fragments':source},ensure_ascii=False)}],
             'stream':False,'temperature':0,'seed':42,'max_tokens':1000,'chat_template_kwargs':{'enable_thinking':False}}
    req=urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    start=time.monotonic();response=json.load(opener.open(req,timeout=180));elapsed=time.monotonic()-start
    raw=response['choices'][0]['message']['content'].strip();parsed=None;issue=None
    try:
        parsed=json.loads(raw)
        fragments=parsed['fragments']
        assert len(fragments)==5 and {f['id'] for f in fragments}=={f['id'] for f in source}
        assert all(set(f)=={'id','text'} and isinstance(f['text'],str) and f['text'].strip() for f in fragments)
    except (ValueError,KeyError,AssertionError,TypeError) as error:issue=str(error) or 'Structure invalide'
    row={'mode':mode,'elapsed_s':elapsed,'protocol_pass':issue is None,'issue':issue,'raw':raw,'parsed':parsed,'finish':response['choices'][0].get('finish_reason')}
    results.append(row)
    (ROOT/'validation-moteur.json').write_text(json.dumps({'model':health['model'],'results':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:row[k] for k in ('mode','elapsed_s','protocol_pass','issue')},ensure_ascii=False),flush=True)
if not all(r['protocol_pass'] for r in results):raise SystemExit(1)
