"""Isolated conversation UI fixture: temporary data, no real access or model."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import sys
import tempfile
import threading
from urllib.parse import urlsplit

from workspace import Workspace, Conflict, Denied


def main():
    root=Path(__file__).resolve().parent.parent/'client-qwen'
    sys.path.insert(0,str(root))
    import app_integrations
    with tempfile.TemporaryDirectory(prefix='fred-conversations-preview-') as home:
        workspace=Workspace(home);owner='preview';lock=threading.RLock()
        def action(name,**values):return workspace.action(owner,{'action':name,**values})
        first=action('project_create',title='Projet Alpha')['id']
        action('project_create',title='Projet Bêta')
        identity=secrets.token_hex(16);messages=[{'role':'user','content':'Contenu à conserver pendant le déplacement.'}]
        action('conversation_save',id=identity,project=first,title='Discussion publiée',messages=messages)
        state={'revision':0,'history':{'currentId':identity,'conversations':[
            {'id':identity,'title':'Discussion publiée','messages':messages,'project_id':first,'server_revision':1},
            {'id':secrets.token_hex(16),'title':'Discussion personnelle','messages':[{'role':'user','content':'Message personnel'}]},
            {'id':secrets.token_hex(16),'title':'Ancienne discussion','messages':[],'archived':True},
        ]}}
        settings={'endpoint':'preview.example:51820','automatic':True,'preferences':{}}
        api_key='fixture-'+'x'*32
        apps={name:{'installed':True,'config_path':str(Path(home)/(name+suffix))} for name,suffix in [('opencode','.json'),('hermes','.yaml')]}
        Path(apps['opencode']['config_path']).write_text('{"model":"existing/model"}',encoding='utf-8')
        Path(apps['hermes']['config_path']).write_text('model:\n  default: existing/model\n',encoding='utf-8')
        nonce=secrets.token_hex(16)
        config=json.dumps({'key':api_key,'storage':'preview-conversations','model':'Modèle fictif','version':'sources'})
        html=(root/'chat.html').read_text(encoding='utf-8').replace('__UI_CSS__',(root/'ui.css').read_text(encoding='utf-8'))
        markdown='<script nonce="__NONCE__">'+(root/'vendor/markdown-it.min.js').read_text(encoding='utf-8')+'\n'+(root/'markdown.js').read_text(encoding='utf-8')+'</script>'
        presentation='<script nonce="__NONCE__">'+(root/'ui.js').read_text(encoding='utf-8')+'\n'+(root/'corrector.js').read_text(encoding='utf-8')+'</script>'
        html=html.replace('</head>',markdown+'</head>').replace('</body>',(root/'workspace.html').read_text(encoding='utf-8')+presentation+'</body>').replace('__CONFIG__',config).replace('__NONCE__',nonce)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,value,status=200):
                raw=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def do_GET(self):
                path=urlsplit(self.path).path
                if path=='/chat':
                    raw=html.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
                with lock:
                    if path=='/v1/workspace':return self.reply(workspace.snapshot(owner))
                    if path=='/client/history':return self.reply(state)
                    if path=='/v1/models':return self.reply({'data':[{'id':'Modèle fictif'}]})
                    if path=='/v1/status':return self.reply({'protocol':3,'version':'fixture'})
                    if path=='/client/draft':return self.reply({'draft':None})
                    if path=='/client/integrations':return self.reply({'apps':apps})
                    if path=='/client/state':return self.reply({'version':'sources','local_api':f'http://127.0.0.1:{self.server.server_port}/v1','key':api_key,'endpoint':settings['endpoint'],'internet_endpoint':'preview.example:51820','preferences':settings['preferences'],'update':{'message':'Aperçu isolé','available':False},'history':{'message':'Historique fictif enregistré'},'connection':{'connected':True,'model':'Modèle fictif','endpoint':settings['endpoint'],'automatic':settings['automatic']}})
                self.reply({'error':{'message':'Route fictive absente'}},404)
            def do_POST(self):
                try:
                    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    with lock:
                        if self.path=='/client/integrations/apply':return self.reply(app_integrations.install(body['app'],f'http://127.0.0.1:{self.server.server_port}/v1',api_key,'Modèle fictif',apps))
                        if self.path=='/v1/workspace/action':return self.reply(workspace.action(owner,body))
                        if self.path=='/client/history':
                            from history_store import validate
                            if body['revision']!=state['revision']:raise Conflict('Historique modifié.')
                            state['history']=validate(body['history']);state['revision']+=1
                            return self.reply({'saved':True,'revision':state['revision'],'message':'Historique fictif enregistré'})
                        if self.path=='/client/history/sync':return self.reply({**state,'server_synced':True})
                        if self.path=='/client/endpoint':
                            from connection_settings import parse
                            settings['endpoint']=parse(body['endpoint']) if body.get('endpoint') else 'preview.example:51820'
                            settings['automatic']=not bool(body.get('endpoint'))
                            return self.reply({'endpoint':settings['endpoint']})
                        if self.path=='/client/preferences':settings['preferences']=body;return self.reply({'saved':True})
                        return self.reply({'saved':True})
                except Exception as error:
                    self.reply({'error':{'message':str(error)}},409 if isinstance(error,Conflict) else 403 if isinstance(error,Denied) else 400)

        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        print(f'http://127.0.0.1:{server.server_port}/chat',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close();workspace.stop.set()


if __name__=='__main__':main()
