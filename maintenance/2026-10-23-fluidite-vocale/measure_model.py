"""Measure the already loaded local model with fictional, ephemeral oral prompts."""
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from validate_live_lots6_8 import get


def main():
    state=get('/api/state')
    assert state['health']['loaded'] and not state['queue']['active'] and not state['queue']['waiting']
    active=state.get('active',{})
    port=active.get('port',8080) if isinstance(active,dict) else 8080
    results=[]
    for prompt in ('Bonjour Fred, tu m’entends ?', 'À quelle heure faut-il partir pour arriver à une réunion à neuf heures si le trajet dure trente minutes ?'):
        assert not get('/api/state')['queue']['active'],'Leave the server free for the user'
        request={'model':state['health']['model'],'messages':[{'role':'system','content':'Tu es Fred. Réponds en français naturel et brièvement, en deux phrases courtes. Pas de préambule.'},{'role':'user','content':prompt}],
                 'stream':True,'max_tokens':80,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False}}
        started=time.perf_counter();first=None;prefix=None;sentence=None;text='';tokens=None
        req=urllib.request.Request(f'http://127.0.0.1:{port}/v1/chat/completions',json.dumps(request).encode(),{'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=60) as response:
            for line in response:
                if not line.startswith(b'data: '):continue
                payload=line[6:].strip()
                if payload==b'[DONE]':break
                frame=json.loads(payload);delta=(frame.get('choices') or [{}])[0].get('delta',{}).get('content','')
                if delta:
                    text+=delta;elapsed=time.perf_counter()-started
                    if first is None:first=elapsed
                    if prefix is None and len(text.split())>=6:prefix=elapsed
                    if sentence is None and any(c in text for c in '.!?'):sentence=elapsed
                if frame.get('usage'):tokens=frame['usage'].get('completion_tokens')
        results.append({'prompt':prompt,'text':text,'first_text_seconds':first,'six_words_seconds':prefix,'first_sentence_seconds':sentence,'total_seconds':time.perf_counter()-started,'completion_tokens':tokens})
    report={'model':state['health']['model'],'route':'local Strata; no user history, client transport, ASR or TTS included','results':results,
            'placement':{k:v for k,v in (active.items() if isinstance(active,dict) else []) if k in ('gpu_layers','threads','context','context_size','tensor_split','split_mode','cpu_moe','n_gpu_layers')},
            'limits':'Two synthetic short prompts on this server; not measurements on the user client or its current conversation context.'}
    (OUT/'model-latency.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()
