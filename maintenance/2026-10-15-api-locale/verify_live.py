"""Real personal transport and local API tests; persist public evidence only."""
import json
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time
import urllib.request
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
import client
import releases
from connection_settings import HTTPS_ENDPOINT


def main():
    profile=releases.profile(ROOT/'lanceur/clients/0402a094eeb03bdc.exe')
    report={'passed':False,'checks':[],'contains_secret_values':False}
    for endpoint in (HTTPS_ENDPOINT,None):
        remote=client.Remote(profile,endpoint=endpoint);key=secrets.token_urlsafe(32)
        with tempfile.TemporaryDirectory(prefix='fred-live-local-api-') as directory:
            with patch.object(client,'settings_path',return_value=Path(directory)/'settings.dpapi'):
                local=client.serve_local(remote,key,0)
            threading.Thread(target=local.serve_forever,daemon=True).start()
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            base=f'http://127.0.0.1:{local.server_port}'
            headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}
            def request(path,body=None):
                return opener.open(urllib.request.Request(base+path,None if body is None else json.dumps(body).encode(),headers),timeout=180)
            try:
                with request('/v1/models') as response:catalog=json.load(response)
                selected=[row for row in catalog['data'] if row['id']=='fred-qwen' or endpoint==HTTPS_ENDPOINT and row['name']=='gpt-6-luna']
                for row in selected:
                    for streaming in (False,True):
                        started=time.monotonic()
                        body={'model':row['id'],'messages':[{'role':'user','content':'Réponds uniquement API_OK.'}],
                            'stream':streaming,'max_tokens':24,'reasoning_effort':'none'}
                        with request('/v1/chat/completions',body) as response:
                            raw=response.read()
                            if streaming:
                                events=[json.loads(line[6:]) for line in raw.splitlines() if line.startswith(b'data: ') and line!=b'data: [DONE]']
                                assert all(not event.get('error') for event in events),events
                                text=''.join(choice.get('delta',{}).get('content') or '' for event in events for choice in event.get('choices',[]))
                                assert b'data: [DONE]' in raw
                            else:
                                result=json.loads(raw);text=result['choices'][0]['message']['content']
                        assert 'API_OK' in text,text
                        report['checks'].append({'transport':'https' if endpoint else 'wireguard','model':row['name'],
                            'stream':streaming,'answer':text,'seconds':round(time.monotonic()-started,2)})
                        print(json.dumps(report['checks'][-1],ensure_ascii=False),flush=True)
                if endpoint==HTTPS_ENDPOINT:
                    tool={'type':'function','function':{'name':'fred_probe','description':'Return a number','parameters':{'type':'object','properties':{'value':{'type':'integer'}},'required':['value']}}}
                    body={'model':'fred-qwen','messages':[{'role':'user','content':'Appelle fred_probe avec value=7.'}],
                        'tools':[tool],'tool_choice':{'type':'function','function':{'name':'fred_probe'}},'max_tokens':128,'reasoning_effort':'none'}
                    with request('/v1/chat/completions',body) as response:answer=json.load(response)
                    message=answer['choices'][0]['message'];calls=message.get('tool_calls',[])
                    assert calls and calls[0]['function']['name']=='fred_probe',answer
                    assert json.loads(calls[0]['function']['arguments'])['value']==7
                    body['messages'] += [message,{'role':'tool','tool_call_id':calls[0]['id'],'content':'7'}]
                    body.pop('tool_choice');body.pop('tools')
                    with request('/v1/chat/completions',body) as response:final=json.load(response)
                    assert final['choices'][0]['message'].get('content')
                    report['client_tool_roundtrip']=True
            finally:local.shutdown();local.server_close();remote.close()
    report['passed']=True
    (OUT/'live-local-api.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
