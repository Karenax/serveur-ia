"""Exercise the newly installed image decoder through the already loaded backend."""
import base64
import hashlib
import io
import json
from pathlib import Path
import urllib.request

import psutil
from PIL import Image

OUT=Path(__file__).resolve().parent
def backend_pid():
    return next(c.pid for c in psutil.net_connections('tcp') if c.status=='LISTEN' and c.laddr.port==8080)
pid=backend_pid()
before=[m.path for m in psutil.Process(pid).memory_maps() if '_imaging' in m.path]
raw=io.BytesIO(); Image.new('RGB',(64,64),(255,0,0)).save(raw,format='WEBP')
url='data:image/webp;base64,'+base64.b64encode(raw.getvalue()).decode()
request={'model':'qwen3.8-flash-next-iq4-xs','messages':[{'role':'user','content':[
    {'type':'text','text':'Quelle est la couleur dominante de cette image ? Réponds avec un seul mot français.'},
    {'type':'image_url','image_url':{'url':url}}]}], 'max_tokens':16,'temperature':0,
    'chat_template_kwargs':{'enable_thinking':False},'reasoning_effort':'none','stream':False}
req=urllib.request.Request('http://127.0.0.1:8080/v1/chat/completions',json.dumps(request).encode(),{'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=180) as response:value=json.load(response)
answer=value['choices'][0]['message']['content']
assert 'rouge' in answer.casefold(),answer
assert backend_pid()==pid
after=[m.path for m in psutil.Process(pid).memory_maps() if '_imaging' in m.path]
assert after
report={'passed':True,'format':'WEBP','color_identified':True,'backend_pid_preserved':True,
        'native_decoder_loaded_before_test':bool(before),'native_decoder_loaded_after_test':True,
        'pillow_version':Image.__version__,'decoder_sha256':{Path(p).name:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in after}}
(OUT/'vision.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('WebP decoded and red color identified; loaded Qwen process preserved.')
