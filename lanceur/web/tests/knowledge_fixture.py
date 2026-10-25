"""Disposable HTTP fixture for the memory console; never touches live Kiara data."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import socket
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from app import Controller,serve
from workspace import HISTORY_RESET_ID

with tempfile.TemporaryDirectory(prefix='fred-knowledge-ui-') as temporary:
    c=Controller(Path(temporary),include_legacy=False)
    owner=c.remote.issue('Accès synthétique')['id']
    w=c.remote.workspace
    p=w.action(owner,{'action':'project_create','title':'Projet synthétique'})['id']
    w.action(owner,{'action':'document_create','project':p,'title':'Budget projet','text':'Le budget du projet est de 42500 euros.'})
    history={'conversations':[{'id':'synthetic','title':'Choix des repas','messages':[{'role':'user','content':'Je préfère les repas végétariens.'}]}],'currentId':'synthetic'}
    w.history_write(owner,{'history':history,'revision':0,'reset_id':HISTORY_RESET_ID})
    class Engine:
        state='arrete'
        def enabled(self):return self.state=='pret'
        def encode(self,texts,mode='document',timeout=8):return [[1.0]+[0.0]*767 for _ in texts]
        def tick(self):pass
        def stop(self):self.state='arrete'
        def configure(self,enabled):self.state='pret' if enabled else 'arrete';return self.status()
        def status(self):return {'status':self.state,'enabled':self.enabled(),'error':'','last_seconds':.01}
    c.embeddings=Engine();w.knowledge.engine=c.embeddings;w.knowledge.start()
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    server=serve(port,c);threading.Thread(target=server.serve_forever,daemon=True).start()
    print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_address[1]),'fixture':True}),flush=True)
    try:sys.stdin.readline()
    finally:server.shutdown();server.server_close();w.shutdown();c.operations.backups.close()
