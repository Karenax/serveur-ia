"""Read-only synthetic follow-ups exercise the advancing Strata prefix boundary."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from core import read_json,BASE_PATH
from validate_live_lots6_8 import get
from voice_response import configure,respond
if '--static-prefix' in sys.argv:
    source=(ROOT/'lanceur/voice_response.py').read_text(encoding='utf-8').replace("max(1,len(result['messages'])-1)",'1').replace("max(1,len(body['messages'])-1)",'1')
    namespace={'__name__':'qa_static_voice'};exec(compile(source,'qa_static_voice.py','exec'),namespace)
    configure=namespace['configure'];respond=namespace['respond']
cfg=read_json(BASE_PATH)
messages=[{'role':'system','content':'Tu es Kiara. Pour cet exercice de calcul, réponds seulement avec le résultat en chiffres.'}]
if '--fresh' in sys.argv:
    import uuid
    messages[0]['content']+=' Exercice synthétique '+uuid.uuid4().hex+'.'
rows=[]
for question,expected in [('Combien font treize plus vingt-quatre ?','37'),('Ajoute cinq au résultat précédent.','42'),('Multiplie maintenant ce dernier résultat par deux.','84'),('Retire quatre à ce résultat.','80'),('Divise le résultat obtenu par deux.','40')]:
    assert not get('/api/state')['queue']['active']
    messages.append({'role':'user','content':question});parts=[];first=[];start=time.perf_counter()
    def emit(text):
        if not first:first.append(time.perf_counter()-start)
        parts.append(text)
    body=configure({'messages':messages,'stream':True,'max_tokens':1024,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False},'strata_mcp':False})
    route=respond(cfg.get('port',8080),cfg.get('model_name','local'),cfg.get('api_key',''),body,lambda:time.perf_counter()-start<45,lambda:None,emit)
    text=''.join(parts).strip();assert route['action']=='answer' and expected in text,(expected,text)
    rows.append({'question':question,'answer':text,'first_text_seconds':first[0],'pin_messages':body['strata_prefix']['messages']})
    messages.append({'role':'assistant','content':text});print(json.dumps(rows[-1]),flush=True)
(OUT/'dialogue-validation.json').write_text(json.dumps({'passed':True,'turns':rows},ensure_ascii=False,indent=2),encoding='utf-8')
