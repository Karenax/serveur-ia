"""Disposable real server, desktop proxy and encrypted UDP transport for lots 6/8."""
import base64
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import Controller, serve
from core import ROOT, write_json
from remote import serve_gateway
from wireguard_access import Engine
from test_remote import FakeModel, client
import wg_bridge


def main():
    with tempfile.TemporaryDirectory(prefix='fred-lots6-8-') as folder:
        home = Path(folder)
        os.environ['LOCALAPPDATA'] = str(home / 'desktop-private')
        write_json(home / 'base-strata.json', {'model_name':'test-model','host':'127.0.0.1','port':49998,
            'api_key':'','tokenizer':str(home/'fake-tokenizer'),'exe':str(home/'fake-engine.exe'),
            'env':{'CUDA_VISIBLE_DEVICES':'0,1'},'args':['--pack',str(home/'fake-pack'),
            '--native',str(home/'fake-model.gguf'),'--max-context','32768','--pool-workers','15']})
        controller = Controller(home, include_legacy=False)
        controller.voice.configure(True)
        import time
        deadline=time.monotonic()+60
        while not controller.voice.ready.is_set() and time.monotonic()<deadline:time.sleep(.1)
        assert controller.voice.ready.is_set(),controller.voice.status()
        store = controller.remote
        access = store.issue('Appareil de preuve isolé')
        other = store.issue('Autre propriétaire isolé')
        controller.wireguard.configure({'public_host':'127.0.0.1','listen_port':51820})
        profile = {**controller.wireguard.new_peer(access), 'model':'test-model','version':'3.5.18','local_routes':[]}
        store.configure({'enabled':True,'url':'wireguard://10.77.0.1:8766'})
        fake = ThreadingHTTPServer(('127.0.0.1',0),FakeModel)
        controller.remote_backend = lambda: (fake.server_port,'test-model','')
        gateway = serve_gateway(store,controller.remote_backend,0)
        stage = ROOT/'client-qwen/wireguard-bridge.exe'
        engine = Engine({'role':'server','wireguard':{'private_key':controller.wireguard.vault()['private_key']},
            'listen_port':0,'upstream_port':gateway.server_port,'peers':controller.wireguard.peers()}, executable=stage)
        profile['wireguard']['endpoint'] = f'127.0.0.1:{engine.port}'
        server_remote = client.Remote(profile)
        bridge_patch = patch.object(wg_bridge,'bridge_executable',return_value=stage)
        bridge_patch.start()
        local = client.serve_local(server_remote,'local_'+secrets.token_urlsafe(32),0)
        controller.state = lambda: {'status':'arrete','running':False,'error':'','ram':{'available_gib':32,'total_gib':64,'percent':50},'gpus':[],'disks':[],
            'logs':'Fixture isolée lots6/8','queue':{},'lan_ips':['127.0.0.1'],'operations':controller.operations.status()}
        from core import available_port
        available_port('127.0.0.1',24800)
        admin = serve(24800,controller)
        servers = (fake,gateway,local,admin)
        for server in servers: threading.Thread(target=server.serve_forever,daemon=True).start()
        owner=access['id'];workspace=store.workspace
        project=workspace.action(owner,{'action':'project_create','title':'Sources et notifications'})['id']
        document=workspace.action(owner,{'action':'document_create','project':project,'title':'Contrat de référence','text':'La livraison du projet Orion est prévue le 23 novembre. Le budget autorisé est de 4200 euros.'})['id']
        sources=workspace.action(owner,{'action':'search','project':project,'query':'livraison Orion'})['sources']
        other_project=workspace.action(other['id'],{'action':'project_create','title':'Projet privé séparé'})['id']
        workspace.action(other['id'],{'action':'document_create','project':other_project,'title':'Secret autre propriétaire','text':'NE DOIT PAS APPARAÎTRE dans la recherche Orion.'})
        print(json.dumps({'fixture':True,'home':str(home),'url':f'http://127.0.0.1:{local.server_port}',
            'admin_url':f'http://127.0.0.1:{admin.server_port}','project':project,'document':document,
            'source_id':sources[0]['source_id'],'source_count':len(sources),'transport':'real-wireguard-udp'}),flush=True)
        try:
            for line in sys.stdin:
                command=json.loads(line);action=command.get('action')
                if action=='stop': print('{"stopped":true}',flush=True);break
                if action=='modify':
                    doc=workspace.action(owner,{'action':'document_get','id':document})
                    workspace.action(owner,{'action':'document_save','id':document,'project':project,'title':doc['title'],'text':'Livraison Orion révisée : le 30 novembre. Budget : 4500 euros.','revision':doc['revision']})
                    print('{"modified":true}',flush=True)
                elif action=='delete':
                    doc=workspace.action(owner,{'action':'document_get','id':document})
                    workspace.action(owner,{'action':'document_delete','id':document,'revision':doc['revision']})
                    print('{"deleted":true}',flush=True)
                elif action=='publish_job':
                    job=workspace.action(owner,{'action':'job_create','project':project,'prompt':'Quelle est la date de livraison Orion ?','request_key':secrets.token_hex(16)})
                    print(json.dumps({'job':job['id']}),flush=True)
                elif action=='publish_many':
                    for i in range(110): store.notifications.publish(owner,'job_completed','fixture:'+str(i))
                    print('{"published":110}',flush=True)
                elif action=='admin_alert':
                    store.notifications.publish('admin','backup_failed','fixture:backup')
                    print('{"published":true}',flush=True)
                elif action=='read_elsewhere':
                    box=store.notifications.snapshot(owner)
                    ids=[item['id'] for item in box['items']]
                    if ids:store.notifications.action(owner,{'action':'read','ids':ids})
                    print(json.dumps({'read':len(ids)}),flush=True)
                elif action=='expire_notification':
                    with workspace.db() as db:
                        db.execute('DELETE FROM notifications WHERE id=? AND owner=?',(command['id'],owner))
                    print('{"expired":true}',flush=True)
                elif action=='publish_receipt_race':
                    event=store.notifications.publish(owner,'job_completed','fixture:receipt-race')
                    print(json.dumps({'id':event['id']}),flush=True)
                elif action=='rotate_generation':
                    from server_state import new_generation
                    print(json.dumps(new_generation(home)),flush=True)
                elif action=='revoke':
                    store.revoke(owner)
                    print('{"revoked":true}',flush=True)
                else: print(json.dumps({'error':'Commande de fixture inconnue.'}),flush=True)
        finally:
            for server in reversed(servers):server.shutdown();server.server_close()
            server_remote.close();engine.close();bridge_patch.stop();controller.operations.backups.close();controller.wireguard.close();controller.voice.close()



class ConversationModel(FakeModel):
    def do_POST(self):
        if self.path!='/v1/chat/completions':return super().do_POST()
        import time
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.captured.append((dict(self.headers),data))
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        try:
            for text in ['La livraison du projet Orion est prévue le 23 novembre. ']+['Je continue à expliquer la réponse et les documents. ']*30:
                self.wfile.write(('data: '+json.dumps({'choices':[{'delta':{'content':text}}]})+'\n\n').encode());self.wfile.flush();time.sleep(.15)
            self.wfile.write(b'data: [DONE]\n\n')
        except (OSError,BrokenPipeError):pass

FakeModel=ConversationModel

if __name__=='__main__':main()
