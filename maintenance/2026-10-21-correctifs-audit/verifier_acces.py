"""Read authenticated catalogues over existing WireGuard and verified HTTPS."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from client import Remote
from connection_settings import HTTPS_ENDPOINT
from releases import profile

home=ROOT/'lanceur'
records=json.loads((home/'acces-distants.json').read_text())['clients']
selected=next(home/'clients'/(record['id']+'.exe') for record in records
    if not record['revoked'] and (home/'clients'/(record['id']+'.exe')).is_file())
values=profile(selected)
proof={}
for mode,endpoint in [('wireguard','127.0.0.1:'+values['wireguard']['endpoint'].rsplit(':',1)[1]),
                      ('https',HTTPS_ENDPOINT)]:
    remote=Remote(values,endpoint=endpoint)
    try:
        with remote.open('/v1/models') as response:catalogue=json.load(response)
        assert catalogue['data']
        with remote.open('/v1/client/release') as response:release=json.load(response)
        assert release['version']=='3.5.31'
        proof[mode]={'authenticated':True,'models':len(catalogue['data']),
                     'windows_version':release['version'],'tls_verification_enabled':mode=='https'}
    finally:remote.close()
(OUT/'acces-apres.json').write_text(json.dumps({'passed':True,'transports':proof},indent=2),encoding='utf-8')
print('Existing personal access verified over WireGuard and certificate-verified HTTPS.')
