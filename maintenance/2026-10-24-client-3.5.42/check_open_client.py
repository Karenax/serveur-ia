"""Ask the open local client to check its update, without applying/closing it."""
import json
from pathlib import Path
import time
import urllib.request

BASE='http://127.0.0.1:17841'
with urllib.request.urlopen(BASE,timeout=10) as response:
    html=response.read(2*1024*1024).decode('utf-8')
marker='const config='
position=html.index(marker)+len(marker)
configuration,_=json.JSONDecoder().raw_decode(html[position:])
headers={'Authorization':'Bearer '+configuration['key'],'Content-Type':'application/json'}
request=urllib.request.Request(BASE+'/client/update/check',data=b'{}',headers=headers)
with urllib.request.urlopen(request,timeout=30) as response:
    response.read(65536)
for attempt in range(20):
    with urllib.request.urlopen(urllib.request.Request(BASE+'/client/state',headers=headers),timeout=15) as response:
        state=json.load(response)
    update=state.get('update',{})
    if state.get('version')=='3.5.42' or update.get('available') and update.get('version')=='3.5.42':break
    time.sleep(.5)
else:raise ValueError('The open client did not confirm the published update')
result={'passed':True,'running_version':state.get('version'),'offered_version':update.get('version'),
        'available':bool(update.get('available')),'forced_install':False}
Path(__file__).with_name('open-client-update.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
