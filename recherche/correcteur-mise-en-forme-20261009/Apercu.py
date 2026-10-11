"""Isolated rich corrector with a simulated model and temporary encrypted settings."""
import importlib.util, json, os, secrets, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SERVER=ROOT.parent.parent
sys.path.insert(0,str(SERVER/'lanceur'))
from test_remote import RemoteTests,FakeModel
from wireguard_access import Engine
spec=importlib.util.spec_from_file_location('corrector_preview_client',ROOT/'client/client.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)

def answer(self):
    data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    mode=(ROOT/'mode-reponse.txt').read_text(encoding='utf-8').strip() if (ROOT/'mode-reponse.txt').exists() else 'normal'
    try:
        source=json.loads(data['messages'][-1]['content'])
        (ROOT/'derniere-requete.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        replacements={'Bonjours':'Bonjour','Je vous envoi':'Je vous envoie','demmandés':'demandés','reçeption':'réception'}
        result=[]
        for fragment in source['fragments']:
            text=fragment['text']
            for before,after in replacements.items():text=text.replace(before,after)
            result.append({'id':fragment['id'],'text':text})
        if mode=='bad':result=result[:-1]
        text=json.dumps({'fragments':result},ensure_ascii=False)
        if mode=='truncated':text=text[:len(text)//2]
    except (ValueError,KeyError,TypeError):text='Aperçu du correcteur : réponse simulée.'
    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
    try:
        for index in range(0,len(text),45):
            self.wfile.write(('data: '+json.dumps({'choices':[{'delta':{'content':text[index:index+45]}}]})+'\n\n').encode());self.wfile.flush()
            time.sleep(.2 if mode=='slow' else .01)
        if mode!='truncated':self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
    except (BrokenPipeError,ConnectionResetError):pass

FakeModel.do_POST=answer
fixture=RemoteTests();fixture.setUp();engine=remote=server=None
os.environ['LOCALAPPDATA']=str(Path(fixture.temporary.name)/'local-data')
try:
    identity=secrets.token_hex(16)
    fixture.store.workspace.history_write(fixture.access['id'],{'history':{'currentId':identity,'conversations':[{'id':identity,'title':'Aperçu isolé du correcteur','messages':[]}]},'revision':0,'reset_id':'20261006-remove-assistants'})
    config={'role':'server','wireguard':{'private_key':fixture.wireguard.vault()['private_key']},'listen_port':0,'upstream_port':fixture.gateway.server_port,'peers':fixture.wireguard.peers()}
    engine=Engine(config)
    remote=client.Remote(fixture.profile,endpoint=f'127.0.0.1:{engine.port}');remote.session=fixture.session
    server=client.serve_local(remote,secrets.token_urlsafe(32),8098)
    print('Prototype isole : http://127.0.0.1:8098/chat — reponses simulees, aucun appel au moteur IA.',flush=True)
    server.serve_forever()
finally:
    if server:server.server_close()
    if remote:remote.close()
    if engine:engine.close()
    fixture.tearDown()
