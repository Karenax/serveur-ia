"""Real server-side EG2 inference over personal access, without persisting text."""
import base64
import json
import math
import os
from pathlib import Path
import secrets
import struct
import sys
import tempfile
import threading
from unittest.mock import patch
import urllib.request

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
import client
from connection_settings import HTTPS_ENDPOINT
from public_embeddings import MODEL_ID
from releases import profile
from validate_live_lots6_8 import models,preserved_files,content_fingerprints

before=json.loads((OUT/'avant-production.json').read_text())
home=ROOT/'lanceur'
records=json.loads((home/'acces-distants.json').read_text())['clients']
selected=next(home/'clients'/(record['id']+'.exe') for record in records
    if not record['revoked'] and (home/'clients'/(record['id']+'.exe')).is_file())
values=profile(selected);proof={}
for mode,endpoint in [('wireguard','127.0.0.1:'+values['wireguard']['endpoint'].rsplit(':',1)[1]),('https',HTTPS_ENDPOINT)]:
    remote=client.Remote(values,endpoint=endpoint)
    try:
        with remote.open('/v1/models') as response:catalogue=json.load(response)
        assert any(row['id']==MODEL_ID and row['capabilities']['embedding'] for row in catalogue['data'])
        body={'model':MODEL_ID,'input':['Une bibliothèque contient des livres.','Une forêt abrite des arbres.']}
        with remote.open('/v1/embeddings',json.dumps(body).encode()) as response:result=json.load(response)
        assert result['model']==MODEL_ID and result['usage']['prompt_tokens']>0 and len(result['data'])==2
        for row in result['data']:
            vector=row['embedding'];assert len(vector)==768 and all(math.isfinite(v) for v in vector)
            assert .98<=math.sqrt(sum(v*v for v in vector))<=1.02
        body={'model':MODEL_ID,'input':'Où trouver des livres ?','encoding_format':'base64','input_type':'query'}
        with remote.open('/v1/embeddings',json.dumps(body).encode()) as response:encoded=json.load(response)
        assert len(base64.b64decode(encoded['data'][0]['embedding']))==768*4
        assert encoded['usage']['prompt_tokens']>0
        proof[mode]={'authenticated':True,'two_normalized_768_vectors':True,'base64_query':True,
                     'prompt_tokens':result['usage']['prompt_tokens'],'catalogue':True}
        if mode=='wireguard':
            scratch=Path(os.environ['LOCALAPPDATA'])/'Fred/validation-embeddings';scratch.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(dir=scratch) as folder:
                key=secrets.token_urlsafe(32)
                with patch.object(client,'settings_path',return_value=Path(folder)/'settings.dpapi'):
                    server=client.serve_local(remote,key,port=0)
                threading.Thread(target=server.serve_forever,daemon=True).start()
                try:
                    base='http://127.0.0.1:'+str(server.server_port)
                    request=urllib.request.Request(base+'/v1/embeddings',json.dumps(body).encode(),
                        {'Authorization':'Bearer '+key,'Content-Type':'application/json'})
                    with urllib.request.urlopen(request,timeout=40) as response:local=json.load(response)
                    assert len(struct.unpack('<768f',base64.b64decode(local['data'][0]['embedding'])))==768
                    proof['windows_local_api']={'authenticated':True,'real_eg2_vector':True}
                finally:server.shutdown();server.server_close()
    finally:remote.close()
assert models()==before['models'] and preserved_files()==before['files']
assert content_fingerprints()==before['users']
(OUT/'inference-distante.json').write_text(json.dumps({'passed':True,'model':MODEL_ID,
    'transports':proof,'qwen_keys_user_data_preserved':True},indent=2),encoding='utf-8')
print('Real EG2 vectors validated through WireGuard, HTTPS and Windows local API; production preserved.')
