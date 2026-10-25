import sys,json,time,http.client
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'lanceur'))
from core import read_json,BASE_PATH
from validate_live_lots6_8 import get
from voice_response import configure,respond
cfg=read_json(BASE_PATH);port=cfg.get('port',8080);key=cfg.get('api_key','');model=cfg.get('model_name','qwen3.8-flash-next')
if '--no-checkpoints' in sys.argv:
    configure_base=configure
    def configure(body):return {**configure_base(body),'strata_checkpoint':False}
questions=[('Bonjour, tu m’entends ?','answer'),('Combien font douze plus dix-sept ?','answer'),('Peux-tu chercher sur Internet ?','clarify'),('Quoi de neuf aujourd’hui dans l’IA ?','search'),('Explique comment fonctionne une recherche sur Internet.','answer')]
rows=[]
for question,expected in questions:
    assert not get('/api/state')['queue']['active'],'Production request is active; retry later'
    body=configure({'model':model,'messages':[{'role':'system','content':'Tu es Kiara. Réponds en français naturel, en deux ou trois phrases courtes.'},{'role':'user','content':question}],'stream':True,'max_tokens':512,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False},'strata_mcp':False})
    start=time.perf_counter();first=[];parts=[]
    def emit(text):
        if not first:first.append(time.perf_counter()-start)
        parts.append(text)
    route=respond(port,model,key,body,lambda:True,lambda:None,emit)
    row={'question':question,'expected':expected,'actual':route['action'],'query':route['query'],'answer':''.join(parts),'first_text_seconds':first[0] if first else None,'total_seconds':time.perf_counter()-start}
    rows.append(row);print(json.dumps(row,ensure_ascii=True),flush=True)
Path(__file__).with_name('reply-comparison.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
