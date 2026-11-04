"""Real EG2 requests through the shipped client's bytecode and local HTTP API."""
import base64
import copy
import hashlib
import json
import marshal
import math
from pathlib import Path
import secrets
import struct
import sys
import tempfile
import threading
import time
import types
import urllib.request
from unittest.mock import patch
from PyInstaller.archive.readers import CArchiveReader

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from releases import profile
from validate_live_lots6_8 import get,models
from wg_crypto import keypair
from wireguard_access import Engine


def main():
    release=json.loads((ROOT/'client-qwen/dist/release.json').read_text())
    artifact=ROOT/'client-qwen/dist/Accès serveur Fred.exe'
    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==release['sha256']
    manifest=json.loads((artifact.parent/'build-manifest.json').read_text())
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==wanted
        for name,wanted in manifest['source_files'].items()),'Dependencies changed since build'
    archive=CArchiveReader(str(artifact))
    client=types.ModuleType('verified_frozen_client')
    client.__file__=str(ROOT/'client-qwen/client.py')
    sys.modules[client.__name__]=client
    exec(marshal.loads(archive.extract('client')),client.__dict__)
    assert client.VERSION==release['version']=='3.5.60'
    before_models=models()
    access=json.loads((ROOT/'lanceur/acces-distants.json').read_text(encoding='utf-8'))
    active={row['id'] for row in access['clients'] if not row['revoked'] and not row.get('suspended')}
    values=next(profile(p) for p in (ROOT/'lanceur/clients').glob('*.exe') if p.stem in active)
    report={'version':client.VERSION,'client_entrypoint':'bytecode extracted from published EXE',
        'dependencies_match_build_manifest':True,'remote_pc_not_observed':True,
        'synthetic_text_only':True,'engine_before':get('/api/knowledge')['engine'],'checks':[]}

    def exercise(transport,personal,endpoint):
        remote=client.Remote(personal,endpoint=endpoint);local=None
        try:
            with tempfile.TemporaryDirectory(prefix='kiara-eg2-client-') as temporary:
                with patch.object(client,'settings_path',return_value=Path(temporary)/'client.dpapi'):
                    remote.check();assert remote.connected,remote.error
                    assert any(r['id']=='google/embeddinggemma-2' and r.get('available',True)
                        for r in remote.models_catalogue['data'])
                    key=secrets.token_urlsafe(32)
                    local=client.serve_local(remote,key,port=0)
                    threading.Thread(target=local.serve_forever,daemon=True).start()
                    for count,encoding,mode in ((1,'float','query'),(2,'base64','document'),(32,'float','document')):
                        texts=[(('Document de contrôle Kiara numéro '+str(i)+'. Un rappel permet de reprendre le projet. ')*60)[:4200] if count==32 else 'Document de contrôle Kiara numéro '+str(i)+'.' for i in range(count)]
                        body={'model':'google/embeddinggemma-2','input':texts[0] if count==1 else texts,
                            'encoding_format':encoding,'input_type':mode}
                        req=urllib.request.Request('http://127.0.0.1:'+str(local.server_port)+'/v1/embeddings',
                            json.dumps(body).encode(),{'Authorization':'Bearer '+key,'Content-Type':'application/json'})
                        started=time.monotonic()
                        with urllib.request.urlopen(req,timeout=95) as response:
                            status=response.status;raw=response.read();result=json.loads(raw)
                        assert status==200 and result['model']==body['model'] and len(result['data'])==count
                        for i,row in enumerate(result['data']):
                            vector=row['embedding'] if encoding=='float' else struct.unpack('<768f',base64.b64decode(row['embedding']))
                            assert row['index']==i and len(vector)==768 and all(math.isfinite(v) for v in vector)
                            assert .98<=math.sqrt(sum(v*v for v in vector))<=1.02
                        assert result['usage']['prompt_tokens']>0
                        report['checks'].append({'transport':transport,'http':status,'texts':count,
                            'encoding':encoding,'mode':mode,'dimensions':768,'normalized':True,
                            'prompt_tokens':result['usage']['prompt_tokens'],'response_bytes':len(raw),
                            'seconds':round(time.monotonic()-started,3)})
                        print(transport+': HTTP 200, '+str(count)+' vectors, '+encoding+', 768 dimensions.',flush=True)
                    local.shutdown();local.server_close();local=None
        finally:
            if local:local.shutdown();local.server_close()
            remote.close()

    exercise('HTTPS',values,client.HTTPS_ENDPOINT)
    server_private,server_public=keypair();client_private,client_public=keypair();psk,_=keypair()
    # Disposable loopback tunnel, forwarding only to the existing authenticated
    # gateway. No production peers, keys, routes or interfaces are changed.
    bridge=Engine({'role':'server','wireguard':{'private_key':server_private},'listen_port':0,
        'upstream_port':8766,'peers':[{'public_key':client_public,'preshared_key':psk,'address':'10.77.0.2/32'}]})
    try:
        personal=copy.deepcopy(values)
        personal['wireguard'].update(private_key=client_private,server_public_key=server_public,
            preshared_key=psk,address='10.77.0.2/32',endpoint='127.0.0.1:'+str(bridge.port))
        exercise('WireGuard (disposable loopback tunnel)',personal,'127.0.0.1:'+str(bridge.port))
    finally:bridge.close()
    report['engine_after']=get('/api/knowledge')['engine']
    assert report['engine_after']['status']=='pret' and report['engine_after']['gpu_name']=='Quadro P2200' and report['engine_after']['device']=='cuda:0'
    assert models()==before_models
    report['qwen_processes_preserved']=True;report['passed']=True
    (OUT/'eg2-client-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
