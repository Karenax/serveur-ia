"""Exercise the installed OpenCode 2 against temporary configs and a fake API."""
import argparse
import base64
from contextlib import closing
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import types
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'client-qwen'),str(ROOT/'client-qwen/build-tools')]
import app_integrations


def integration(binary):
    if not binary:return app_integrations
    from PyInstaller.archive.readers import CArchiveReader
    archive=CArchiveReader(str(binary)).open_embedded_archive('PYZ.pyz')
    code=archive.extract('app_integrations')
    module=types.ModuleType('verified_integrations');exec(code,module.__dict__)
    if hasattr(module,'opencode_visibility'):
        helper=types.ModuleType('verified_visibility');exec(archive.extract('opencode_visibility'),helper.__dict__)
        module.opencode_visibility=helper
    return module



def verify(cli,current,previous=None):
    model='fred-model-'+ 'a'*24;key=secrets.token_urlsafe(32);captured=[]
    class Backend(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            data=json.dumps({'object':'list','data':[{'id':model,'object':'model'}]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            authorized=self.headers.get('Authorization')=='Bearer '+key
            captured.append({'route':self.path,'model':body.get('model'),'authorized':authorized})
            if not authorized:self.send_error(401);return
            response={'id':'chatcmpl-fred-test','created':int(time.time()),'model':model,
                      'object':'chat.completion','choices':[{'index':0,'message':{'role':'assistant','content':'FRED_OPENCODE_OK'},'finish_reason':'stop'}],
                      'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}}
            if body.get('stream'):
                response['object']='chat.completion.chunk'
                response['choices']=[{'index':0,'delta':{'role':'assistant','content':'FRED_OPENCODE_OK'},'finish_reason':None}]
                data=('data: '+json.dumps(response)+'\n\n').encode()
                response['choices']=[{'index':0,'delta':{},'finish_reason':'stop'}]
                data+=('data: '+json.dumps(response)+'\n\ndata: [DONE]\n\n').encode()
            else:data=json.dumps(response).encode()
            self.send_response(200);self.send_header('Content-Type','text/event-stream' if body.get('stream') else 'application/json')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

    backend=ThreadingHTTPServer(('127.0.0.1',0),Backend)
    threading.Thread(target=backend.serve_forever,daemon=True).start()
    api=f'http://127.0.0.1:{backend.server_port}/v1'
    report={}
    try:
        with tempfile.TemporaryDirectory(prefix='fred-opencode-verification-') as temporary:
            root=Path(temporary);directory=root/'config/opencode';directory.mkdir(parents=True)
            lower=directory/'opencode.json';higher=directory/'opencode.jsonc'
            lower.write_text('{"model":"opencode/big-pickle"}',encoding='utf-8')
            higher.write_text(app_integrations.opencode_text('{\n// Keep my comment\n}', 'http://127.0.0.1:1/v1','old-test-key-'+'y'*40,model),encoding='utf-8')
            original=higher.read_bytes()
            env={k:v for k,v in os.environ.items() if not k.startswith(('OPENCODE_','XDG_'))}
            env.update(OPENCODE_PASSWORD=secrets.token_urlsafe(32),OPENCODE_TEST_HOME=str(root),
                       LOCALAPPDATA=str(root/'local'),APPDATA=str(root/'roaming'),
                       XDG_CONFIG_HOME=str(root/'config'),XDG_DATA_HOME=str(root/'data'),
                       XDG_CACHE_HOME=str(root/'cache'),XDG_STATE_HOME=str(root/'state'))
            desktop=root/'local/Programs/@opencodedesktop/OpenCode.exe';desktop.parent.mkdir(parents=True);desktop.touch()
            database=root/'roaming/ai.opencode.desktop/drafts.sqlite';database.parent.mkdir(parents=True)
            with closing(sqlite3.connect(database)) as db,db:
                db.execute('CREATE TABLE state(name TEXT,key TEXT,value TEXT,updated_at INTEGER,PRIMARY KEY(name,key))')
                db.execute('INSERT INTO state VALUES(?,?,?,?)',('opencode.global.dat','model','{"user":[],"recent":[],"variant":{}}',1))
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            server=f'http://127.0.0.1:{port}'
            auth='Basic '+base64.b64encode(('opencode:'+env['OPENCODE_PASSWORD']).encode()).decode()
            def get(path):
                request=urllib.request.Request(server+path,headers={'Authorization':auth})
                with urllib.request.urlopen(request,timeout=5) as response:return json.load(response)
            def command(*args):
                result=subprocess.run([str(cli),*args,'--server',server],cwd=root,env=env,capture_output=True,
                                      text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode:raise AssertionError('OpenCode command failed: '+args[0])
                return result.stdout
            def active_model():
                rows=get('/api/model').get('data',[])
                return next((m for m in rows if m.get('providerID')=='serveur-fred' and m.get('id')==model),{})
            def wait_for(predicate):
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    try:
                        if predicate():return
                    except (OSError,ValueError):pass
                    time.sleep(.1)
                raise AssertionError('OpenCode did not apply the expected configuration')
            with (root/'opencode.log').open('w',encoding='utf-8') as log:
                process=subprocess.Popen([str(cli),'serve','--hostname','127.0.0.1','--port',str(port)],cwd=root,
                                         env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    wait_for(lambda:isinstance(get('/api/config'),list))
                    wait_for(lambda:bool(active_model()))
                    if previous:
                        old_apps=previous.detect(root,env,lambda _:None)
                        previous.install('opencode',api,key,model,old_apps)
                        command('reload')
                        wait_for(lambda:active_model().get('settings',{}).get('baseURL')=='http://127.0.0.1:1/v1')
                        assert Path(old_apps['opencode']['config_path'])==lower
                        report['previous_binary_wrong_config_reproduced']=True
                    lower_before=lower.read_bytes()
                    apps=current.detect(root,env,lambda _:None)
                    result=current.install('opencode',api,key,model,apps,catalogue={'data':[{'id':model,'name':'gpt-6-luna','label':'GPT-6 Luna','available':True}]})
                    assert Path(result['config_path'])==higher
                    assert result['visibility']['status']=='enabled'
                    assert Path(result['backup']).read_bytes()==original
                    assert lower.read_bytes()==lower_before
                    assert '// Keep my comment' in higher.read_text(encoding='utf-8')
                    command('reload')
                    wait_for(lambda:active_model().get('settings',{}).get('baseURL')==api)
                    assert active_model()['settings']['apiKey']==key
                    with closing(sqlite3.connect(database)) as db:
                        preferences=json.loads(db.execute('SELECT value FROM state WHERE name=? AND key=?',('opencode.global.dat','model')).fetchone()[0])
                    assert active_model()['name']=='GPT-6 Luna', active_model().get('name')
                    assert any(row.get('providerID')=='serveur-fred' and row.get('modelID')==model and row.get('visibility')=='show' for row in preferences['user'])
                    report['readable_model_name']=True
                    output=command('run','--model','serveur-fred/'+model,'--title','Fred integration verification',
                                   '--format','json','Reply FRED_OPENCODE_OK.')
                    assert 'FRED_OPENCODE_OK' in output
                    assert captured and all(row['authorized'] and row['model']==model and row['route']=='/v1/chat/completions' for row in captured)
                    report.update(passed=True,selected_config='opencode.jsonc',comments_preserved=True,
                                  exact_backup=True,lower_priority_config_unchanged=True,model_visible=True,
                                  api_url_and_key_effective=True,opencode_chat_request_passed=True,
                                  chat_requests=len(captured),real_user_config_untouched=True)
                finally:process.terminate();process.wait(timeout=10)
    finally:backend.shutdown();backend.server_close()
    version=subprocess.run([str(cli),'--version'],capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    report['opencode_version']=version.stdout.strip()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--cli',type=Path,default=Path(os.environ.get('LOCALAPPDATA',''))/'Programs/@opencodedesktop/resources/opencode-cli.exe')
    parser.add_argument('--client-binary',type=Path)
    parser.add_argument('--baseline-binary',type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).with_name('verification.json'))
    args=parser.parse_args()
    report=verify(args.cli,integration(args.client_binary),integration(args.baseline_binary) if args.baseline_binary else None)
    for name,binary in (('client_binary',args.client_binary),('baseline_binary',args.baseline_binary)):
        if binary:report[name]={'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'bytes':binary.stat().st_size}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
