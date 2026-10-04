"""Isolated UI verification with representative Markdown and French correction fixtures."""
import json
import os
from pathlib import Path
import secrets
import threading
import time
from test_remote import RemoteTests,FakeModel,client
from wireguard_access import Engine

SAMPLE='''## Préparer une image avec ComfyUI

Commencez par un **workflow simple**, puis ajustez les paramètres progressivement.

### 1. Démarrer ComfyUI

```bash
python main.py
```

Ouvrez ensuite l’interface dans votre navigateur.

### 2. Construire votre workflow

1. Chargez le modèle avec **Load Checkpoint**.
2. Ajoutez votre description dans **CLIP Text Encode**.
3. Reliez le **KSampler**, le décodeur et l’enregistrement.

| Paramètre | Conseil pour débuter |
| --- | --- |
| Résolution | 1024 × 1024 |
| Description | Sujet, lumière et composition |

> Enregistrez votre workflow pour retrouver vos réglages.
'''

def answer(self):
    data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    FakeModel.captured.append((dict(self.headers),data))
    system=' '.join(m.get('content','') for m in data['messages'] if m['role']=='system')
    if 'Corrige l’orthographe' in system:text='Bonjour,\n\nJe vous envoie les documents demandés. Pouvez-vous me confirmer leur réception ?\n\nMerci et bonne journée.'
    elif 'français professionnel' in system:text='Bonjour,\n\nVeuillez trouver les documents demandés. Je vous remercie de bien vouloir me confirmer leur réception.\n\nJe vous souhaite une excellente journée.'
    elif 'français amical' in system:text='Salut !\n\nJe t’envoie les documents que tu m’as demandés. Tu peux me dire si tu les as bien reçus ?\n\nMerci et bonne journée !'
    else:text=SAMPLE
    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
    self.wfile.write(('data: '+json.dumps({'choices':[{'delta':{'content':text}}]})+'\n\ndata: [DONE]\n\n').encode());self.wfile.flush()

FakeModel.do_POST=answer
fixture=RemoteTests();fixture.setUp();engine=None;remote=None;server=None
flag=Path(__file__).with_name('preview-350-network.txt');flag.write_text('online',encoding='utf-8')
try:
    os.environ['LOCALAPPDATA']=str(Path(fixture.temporary.name)/'local-data')
    owner=fixture.access['id'];identity=secrets.token_hex(16)
    fixture.store.workspace.history_write(owner,{'history':{'currentId':identity,'conversations':[{'id':identity,'title':'Créer une image avec ComfyUI','messages':[{'role':'user','content':'Comment créer une image avec ComfyUI ?'},{'role':'assistant','content':SAMPLE}]}]},'revision':0})
    configuration={'role':'server','wireguard':{'private_key':fixture.wireguard.vault()['private_key']},'listen_port':0,'upstream_port':fixture.gateway.server_port,'peers':fixture.wireguard.peers()}
    engine=Engine(configuration);configuration['listen_port']=engine.port
    remote=client.Remote(fixture.profile,endpoint=f'127.0.0.1:{engine.port}')
    server=client.serve_local(remote,secrets.token_urlsafe(32),8099)
    def control():
        global engine
        while True:
            try:
                desired=flag.read_text(encoding='utf-8').strip()
                if desired=='offline' and engine:engine.close();engine=None
                if desired=='online' and not engine:engine=Engine(configuration)
            except OSError:pass
            time.sleep(.3)
    threading.Thread(target=control,daemon=True).start()
    print('Client de vérification isolé : http://127.0.0.1:8099/chat',flush=True)
    server.serve_forever()
finally:
    if server:server.server_close()
    if remote:remote.close()
    if engine:engine.close()
    fixture.tearDown()
