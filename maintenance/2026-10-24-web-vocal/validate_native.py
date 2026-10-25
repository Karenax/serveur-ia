"""Reproduce natural oral requests with real local planning, web, and Qwen output."""
import json
from pathlib import Path
import re
import secrets
import sys
import tempfile
import threading
import time
import urllib.request
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from remote import AccessStore,serve_gateway,plan_voice_web
from validate_live_lots6_8 import get,models


class NoAgent:
    def stream(self,*args):raise AssertionError('An oral request must not start an agent')
    def select_model(self,*args):raise AssertionError('Keep local Qwen')


def main():
    state=get('/api/state');assert state['health']['loaded'] and not state['queue']['active'] and not state['queue']['waiting']
    before=models();reports=[];plans=[]
    def trace(*args,**kwargs):
        start=time.monotonic();value=plan_voice_web(*args,**kwargs)
        plans.append({**value,'seconds':round(time.monotonic()-start,3)})
        return value
    with tempfile.TemporaryDirectory(prefix='kiara-semantic-web-') as scratch,patch('remote.plan_voice_web',trace):
        store=AccessStore(scratch);store.configure({'enabled':True,'url':'wireguard://10.77.0.1:8766'})
        access=store.issue('Fictional semantic oral validation');store.hermes=NoAgent()
        with store.workspace.db() as db:db.execute('INSERT OR REPLACE INTO policies(owner,settings) VALUES(?,?)',(access['id'],json.dumps({'web':True})))
        server=serve_gateway(store,lambda:(8080,state['health']['model'],''),0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        cases=[('cherche internet la derniere actualité sur l’IA',True,[
            {'role':'user','content':'Peux-tu faire une recherche pour moi ?'},
            {'role':'assistant','content':'Je ne peux pas chercher sur Internet, je n’ai pas accès au web.'}]),
            ('Peux-tu faire une recherche pour moi ?',False,[])]
        try:
            for prompt,search,history in cases:
                deadline=time.monotonic()+5
                while store.scheduler.snapshot()['requests'] and time.monotonic()<deadline:time.sleep(.02)
                assert not store.scheduler.snapshot()['requests'],'Previous request did not release its inference slot'
                identifier=secrets.token_hex(16)
                body={'voice_conversation':True,'conversation_id':'semantic-fiction-'+identifier,'turn_id':identifier,
                      'messages':[*history,{'role':'user','content':prompt}],'stream':True}
                request=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/v1/chat/completions',json.dumps(body).encode(),
                        {'Authorization':'Bearer '+access['token'],'Content-Type':'application/json','X-Qwen-Request':identifier})
                start=time.monotonic();first=None;sources=[];answer='';done=False;phases=[];context=None
                with urllib.request.urlopen(request,timeout=180) as response:
                    for line in response:
                        if not line.startswith(b'data: '):continue
                        raw=line[6:].strip()
                        if raw==b'[DONE]':done=True;break
                        value=json.loads(raw);assert not value.get('error'),value.get('error');assert not value.get('hermes_run')
                        if value.get('hermes_status'):phases.append(value['hermes_status']['message'])
                        if value.get('workspace_sources'):sources=value['workspace_sources']
                        if value.get('voice_context'):context=value['voice_context']
                        content=(value.get('choices') or [{}])[0].get('delta',{}).get('content','')
                        if content and first is None:first=time.monotonic()-start
                        answer+=content
                assert done and answer.strip()
                assert not re.search(r"(?:n['’]ai pas acc[eè]s|ne peux pas (?:chercher|naviguer|effectuer.*recherche))",answer,re.I),answer
                assert bool(sources)==search
                assert plans[-1]['action']==('search' if search else 'clarify')
                assert context['input_tokens']+context['output_tokens']<=16384
                reports.append({'prompt':prompt,'semantic_decision':plans[-1],'answer':answer,'first_text_seconds':round(first,3),
                                'sources':[{'url':s['url'],'retrieved':s['retrieved']} for s in sources],
                                'research_stages':phases,'oral_context':context,'passed':True})
                print(json.dumps(reports[-1],ensure_ascii=True),flush=True)
                (OUT/'native-partial.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        finally:server.shutdown();server.server_close();thread.join(5)
    assert models()==before
    result={'passed':True,'scope':'temporary accounts and HTTP gateway, real local Qwen and Hermes web tools',
            'hermes_agent_called':False,'qwen_processes_preserved':True,'cases':reports,
            'limits':'Fictional questions; no microphone or browser audio playback. A focused regression, not a general accuracy or latency benchmark.'}
    (OUT/'native-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
