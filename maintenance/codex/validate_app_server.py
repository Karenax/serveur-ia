"""Two ephemeral turns through the same app-server protocol as desktop Codex."""
import argparse
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'lanceur'))
from core import HIDDEN
from remote import AccessStore, serve_gateway


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--credential-helper', action='store_true')
    args = parser.parse_args(); report = {'passed': False, 'answers': []}
    with tempfile.TemporaryDirectory(prefix='kiara-app-server-') as folder:
        store = AccessStore(Path(folder)/'server')
        store.configure({'enabled': True, 'url': 'wireguard://10.77.0.1:8766'})
        access = store.issue('Temporary app-server qualification')
        server = serve_gateway(store, lambda: (8080, 'qwen3.8-flash-next-iq4-xs', ''), 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:'+str(server.server_port)+'/v1'
        command = [shutil.which('codex'), 'app-server', '--stdio',
                   '-c', 'model_provider="kiara"', '-c', 'model="fred-qwen"',
                   '-c', 'model_catalog_json='+json.dumps(str(Path(__file__).with_name('qwen-models.json')).replace('\\','/')),
                   '-c', 'model_providers.kiara={name="Kiara",base_url="'+base+'",env_key="KIARA_API_KEY",wire_api="responses",requires_openai_auth=false}',
                   '-c', 'web_search="disabled"', '-c', 'features.apps=false', '-c', 'features.plugins=false',
                   '-c', 'agents.enabled=false', '-c', 'model_reasoning_effort="none"']
        child_env = dict(os.environ, KIARA_API_KEY=access['token'])
        if args.credential_helper:
            installed=Path(folder)/'codex-profile'
            setup=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
                str(Path(__file__).with_name('Installer-Codex-Kiara.ps1')),'-CodexDirectory',str(installed),'-BaseUrl',base,'-Application','-EnregistrerCle'],
                env=child_env,capture_output=True,timeout=30,creationflags=HIDDEN)
            if setup.returncode: raise RuntimeError('Credential helper setup failed')
            settings=tomllib.loads((installed/'config.toml').read_text(encoding='utf-8'))
            provider=settings['model_providers']['kiara']
            auth=provider['auth']
            toml_auth='{command='+json.dumps(auth['command'])+',args='+json.dumps(auth['args'])+',timeout_ms=10000,refresh_interval_ms=300000}'
            command=[('model_providers.kiara={name="Kiara",base_url="'+base+'",wire_api="responses",auth='+toml_auth+'}')
                     if value.startswith('model_providers.kiara=') else value for value in command]
            child_env.pop('KIARA_API_KEY',None)
            report['credential_helper']=True
        messages = queue.Queue(); errors = []
        process = subprocess.Popen(command, env=child_env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', creationflags=HIDDEN)
        def reader():
            for line in process.stdout:
                try: messages.put(json.loads(line))
                except ValueError: pass
        threading.Thread(target=reader, daemon=True).start()
        def stderr():
            for line in process.stderr: errors.append(line)
        threading.Thread(target=stderr, daemon=True).start()
        def send(method, params, ident=None):
            value={'method': method, 'params': params}
            if ident is not None: value['id'] = ident
            process.stdin.write(json.dumps(value)+'\n'); process.stdin.flush()
        def wait(predicate, seconds=120):
            deadline = time.monotonic()+seconds
            while time.monotonic()<deadline:
                value = messages.get(timeout=max(.1,deadline-time.monotonic()))
                if value.get('error'): raise RuntimeError(str(value['error']))
                if 'id' in value and 'method' in value:
                    process.stdin.write(json.dumps({'id':value['id'],'error':{'code':-32601,'message':'No interactive tools in this qualification.'}})+'\n'); process.stdin.flush()
                if predicate(value): return value
            raise TimeoutError('App-server qualification timeout')
        started = time.monotonic()
        try:
            send('initialize', {'clientInfo': {'name':'kiara_qualification','version':'1.0.0'}, 'capabilities': {'experimentalApi':True}}, 1)
            wait(lambda v:v.get('id')==1)
            send('initialized', {})
            send('thread/start', {'model':'fred-qwen', 'modelProvider':'kiara', 'cwd':folder,
                                 'approvalPolicy':'never', 'sandbox':'read-only', 'ephemeral':True}, 2)
            thread = wait(lambda v:v.get('id')==2)['result']['thread']['id']
            expected = 'KIARA-' + secrets.token_hex(5)
            for ident, prompt in [(3, 'Voici un code fictif à retenir pour cette conversation : '+expected+'. Réponds uniquement OK.'),
                                  (4, 'Quel est le code fictif donné au message précédent ? Réponds uniquement avec ce code.')]:
                send('turn/start', {'threadId':thread, 'input':[{'type':'text','text':prompt}]}, ident)
                wait(lambda v:v.get('id')==ident)
                turn = wait(lambda v:v.get('method')=='turn/completed')['params']['turn']
                report['answers'].append({'status':turn['status'], 'text':'\n'.join(item.get('text','') for item in turn.get('items',[]) if item.get('type')=='agentMessage')})
            report.update(expected=expected, queue=store.scheduler.snapshot())
            report['passed'] = len(report['answers'])==2 and all(v['status']=='completed' for v in report['answers']) and expected in report['answers'][-1]['text']
            send('thread/compact/start', {'threadId':thread}, 5)
            wait(lambda v:v.get('id')==5)
            compact = wait(lambda v:v.get('method')=='turn/completed')['params']['turn']
            report['compaction_status'] = compact['status']
            send('turn/start', {'threadId':thread, 'input':[{'type':'text','text':'Après cette synthèse, redonne uniquement le code fictif de la conversation.'}]}, 6)
            wait(lambda v:v.get('id')==6)
            after = wait(lambda v:v.get('method')=='turn/completed')['params']['turn']
            report['after_compaction'] = '\n'.join(item.get('text','') for item in after.get('items',[]) if item.get('type')=='agentMessage')
            report['passed'] = report['passed'] and compact['status']=='completed' and after['status']=='completed' and expected in report['after_compaction']
        except Exception as error:
            report['error'] = str(error)
        finally:
            process.terminate(); process.wait(timeout=10)
            for stream in (process.stdin, process.stdout, process.stderr): stream.close()
            store.scheduler.cancel(access['id']); server.shutdown(); server.server_close()
            report.update(seconds=round(time.monotonic()-started,2), stderr=''.join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='stderr'}, ensure_ascii=True))
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
