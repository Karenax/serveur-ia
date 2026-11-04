"""Verify native OpenAI model discovery remains intact with optional Kiara.

No user configuration is written. Only model metadata is requested from OpenAI;
the single inference is performed by the already loaded local Qwen.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'lanceur')]
from core import HIDDEN
from remote import AccessStore,serve_gateway


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    report={'passed':False};started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='kiara-provider-coexistence-') as folder:
        store=AccessStore(Path(folder)/'server');store.configure({'enabled':True,'url':'wireguard://10.77.0.1:8766'})
        access=store.issue('Temporary provider qualification')
        server=serve_gateway(store,lambda:(8080,'qwen3.8-flash-next-iq4-xs',''),0)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base='http://127.0.0.1:'+str(server.server_port)+'/v1'
        provider='model_providers.kiara={name="Qwen via Kiara",base_url="'+base+'",env_key="KIARA_API_KEY",wire_api="responses",requires_openai_auth=false,model_catalog_url="'+base+'/client/codex/models"}'
        command=[shutil.which('codex'),'app-server','--stdio','-c',provider,
                 '-c','features.apps=false','-c','features.plugins=false','-c','agents.enabled=false','-c','web_search="disabled"']
        process=subprocess.Popen(command,env=dict(os.environ,KIARA_API_KEY=access['token']),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=HIDDEN)
        messages=queue.Queue();errors=[]
        def read():
            for line in process.stdout:
                try:messages.put(json.loads(line))
                except ValueError:pass
        def stderr():
            for line in process.stderr:errors.append(line)
        threading.Thread(target=read,daemon=True).start();threading.Thread(target=stderr,daemon=True).start()
        def send(method,params,ident=None):
            value={'method':method,'params':params}
            if ident is not None:value['id']=ident
            process.stdin.write(json.dumps(value)+'\n');process.stdin.flush()
        def wait(predicate):
            deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                value=messages.get(timeout=max(.1,deadline-time.monotonic()))
                if value.get('error'):raise RuntimeError(str(value['error']))
                if predicate(value):return value
            raise TimeoutError('Provider qualification timeout')
        try:
            send('initialize',{'clientInfo':{'name':'kiara_coexistence','version':'1.0.0'},'capabilities':{'experimentalApi':True}},1);wait(lambda v:v.get('id')==1)
            send('initialized',{})
            send('model/list',{'includeHidden':False,'limit':100},2)
            before=wait(lambda v:v.get('id')==2)['result']['data']
            report['default_models_before']=[row['model'] for row in before]
            report['native_default']=[row['model'] for row in before if row.get('isDefault')]
            assert any(row['model'].startswith('gpt-') for row in before),'Native ChatGPT models missing'
            assert all(row['model']!='fred-qwen' for row in before),'Qwen replaced the native catalogue'
            send('thread/start',{'model':'fred-qwen','modelProvider':'kiara','cwd':folder,'ephemeral':True,
                                'approvalPolicy':'never','sandbox':'read-only','config':{'model_reasoning_effort':'none'}},3)
            thread=wait(lambda v:v.get('id')==3)['result']['thread']['id']
            send('turn/start',{'threadId':thread,'input':[{'type':'text','text':'Réponds uniquement COEXISTENCE-OK.'}]},4);wait(lambda v:v.get('id')==4)
            turn=wait(lambda v:v.get('method')=='turn/completed')['params']['turn']
            report['qwen_answer']='\n'.join(item.get('text','') for item in turn.get('items',[]) if item.get('type')=='agentMessage')
            send('model/list',{'includeHidden':False,'limit':100},5)
            after=wait(lambda v:v.get('id')==5)['result']['data']
            report['native_models_unchanged']=before==after
            report['passed']=report['native_models_unchanged'] and turn['status']=='completed' and 'COEXISTENCE-OK' in report['qwen_answer']
        except Exception as error:report['error']=str(error)
        finally:
            process.terminate();process.wait(timeout=10)
            for stream in (process.stdin,process.stdout,process.stderr):stream.close()
            store.scheduler.cancel(access['id']);server.shutdown();server.server_close()
            report.update(seconds=round(time.monotonic()-started,2),stderr=''.join(errors))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='stderr'},ensure_ascii=True))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
