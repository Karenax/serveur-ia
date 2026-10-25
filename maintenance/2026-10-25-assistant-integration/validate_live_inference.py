"""Synthetic, non-persistent local inference. Never executes returned commands."""
import http.client
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'lanceur'))
from voice_response import configure,Decoder


def main():
    connection=http.client.HTTPConnection('127.0.0.1',8080,timeout=300)
    connection.request('GET','/v1/models');response=connection.getresponse()
    model=json.loads(response.read())['data'][0]['id'];connection.close()
    rows=[]
    for prompt in ('Bonjour, réponds en une phrase.','Retiens que je préfère les réponses courtes à l’oral.','Quels sont mes prochains rappels ?'):
        body=configure({'model':model,'messages':[{'role':'system','content':'Tu es Kiara. Réponds en français. Les données de cet essai sont fictives.'},{'role':'user','content':prompt}],
                        'max_tokens':512,'stream':True,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False},'strata_mcp':False},commands=True)
        start=time.perf_counter();first=None;text='';decoder=Decoder(commands=True)
        connection=http.client.HTTPConnection('127.0.0.1',8080,timeout=300)
        connection.request('POST','/v1/chat/completions',body=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        response=connection.getresponse()
        if response.status!=200:raise ValueError('Local inference unavailable: '+str(response.status))
        for line in response:
            if not line.startswith(b'data: '):continue
            if line.strip()==b'data: [DONE]':break
            frame=json.loads(line[6:])
            for choice in frame.get('choices',[]):
                part=choice.get('delta',{}).get('content','')
                if part and first is None:first=time.perf_counter()-start
                text+=part;decoder.feed(part)
        result=decoder.finish();connection.close()
        rows.append({'prompt':prompt,'first_text_seconds':first,'total_seconds':time.perf_counter()-start,'result':result,'wire':text,'commands_executed':False})
        print(json.dumps({'completed':len(rows),'mode':result['action'],'first_text_seconds':first}),flush=True)
    output=Path(__file__).with_name('live-inference.json')
    output.write_text(json.dumps({'model':model,'scope':'direct local inference only; no microphone, no application writes','samples':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
