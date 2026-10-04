import json,re,urllib.request
base='http://127.0.0.1:8765'
with urllib.request.urlopen(base+'/') as response:html=response.read().decode()
match=re.search(r'name="launcher-token" content="([^"]+)"',html)
if not match:raise RuntimeError('Token du lanceur introuvable')
req=urllib.request.Request(base+'/api/stop',data=b'{}',headers={'Content-Type':'application/json','X-Launcher-Token':match.group(1),'Origin':base})
with urllib.request.urlopen(req,timeout=90) as response:print(json.load(response))
