"""Read-only authenticated download integrity checks; never print access credentials."""
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from core import HOME
from releases import profile
from signing import public
from kiara_shared.releases import verify
from kiara_shared.voice_packs import verify_catalogue


def main():
    active={row['id'] for row in json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))['clients'] if not row['revoked']}
    personal=profile(next(p for p in (HOME/'clients').glob('*.exe') if p.stem in active))
    headers={'Authorization':'Bearer '+personal['token']}
    def open_route(path):
        return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8766'+path,headers=headers),timeout=45)
    def read(path):
        with open_route(path) as response:return json.load(response)
    def download(path,expected):
        total=0;digest=hashlib.sha256()
        with open_route(path) as response:
            while block:=response.read(1024*1024):total+=len(block);digest.update(block)
        assert total==expected['bytes'] and digest.hexdigest()==expected['sha256'],path
        return {'bytes':total,'sha256':digest.hexdigest()}
    status=read('/v1/status')
    assert status['version']=='3.5.53' and status['command_nonce_version']==2
    assert abs(status['server_time_ms']-time.time()*1000)<10000
    windows=verify(read('/v1/client/release'),public(HOME,create=False))
    android=read('/v1/client/android/release')
    voice=verify_catalogue(read('/v1/voice/max/package'),public(HOME,create=False))
    assert windows['version']=='3.5.53' and android['version']=='1.0.24'
    proof={'passed':True,'status_version':status['version'],'command_nonce_version':2,
           'windows':download('/v1/client/download',windows),
           'android':download('/v1/client/android/download',android),
           'voice':download('/v1/voice/max/package/download',voice['runtime']),
           'signature_pins_preserved':True,'production_mutations':False}
    (OUT/'served-release-validation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps(proof))


if __name__=='__main__':main()
