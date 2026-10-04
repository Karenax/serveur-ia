"""One-shot source integration; all edits have exact, checked anchors."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent
def replace(path,old,new,count=1):
    p=root/path;s=p.read_text(encoding='utf-8')
    if s.count(old)!=count:raise ValueError('Unexpected source anchor: '+path)
    p.write_text(s.replace(old,new),encoding='utf-8')

if __name__=='__main__':
    replace('client-qwen/Build-Client.ps1','--add-data ((Join-Path $PSScriptRoot \'chat.html\') + \';.\')','--add-data $workspaceData --add-data ((Join-Path $PSScriptRoot \'chat.html\') + \';.\')')
    replace('client-qwen/wireguard-bridge/main.go','r.URL.Path == "/v1/models" || r.URL.Path == "/v1/status"','r.URL.Path == "/v1/workspace" || r.URL.Path == "/v1/models" || r.URL.Path == "/v1/status"',2)
    replace('client-qwen/wireguard-bridge/main.go','r.URL.Path == "/v1/chat/completions" || r.URL.Path == "/v1/cancel"','r.URL.Path == "/v1/workspace/action" || r.URL.Path == "/v1/chat/completions" || r.URL.Path == "/v1/cancel"',2)
    replace('client-qwen/wireguard-bridge/main.go','if r.Method == "POST" && (r.ContentLength < 1 || r.ContentLength > 2*1024*1024) {','bodyLimit := int64(2 * 1024 * 1024)\n\t\tif r.URL.Path == "/v1/workspace/action" { bodyLimit = 8 * 1024 * 1024 }\n\t\tif r.Method == "POST" && (r.ContentLength < 1 || r.ContentLength > bodyLimit) {',2)
    replace('client-qwen/wireguard-bridge/main.go','http.MaxBytesReader(w, r.Body, 2*1024*1024)','http.MaxBytesReader(w, r.Body, bodyLimit)',2)
    replace('client-qwen/chat.html','model:config.model,messages:history,stream:true','...workspaceFields(),model:config.model,messages:history,stream:true')
    replace('lanceur/web/index.html','<script src="/app.js" defer></script>','<script src="/app.js" defer></script><script src="/workspace.js" defer></script>')
    replace('lanceur/web/index.html','Gérer les comptes clients','Gérer les accès clients')
    replace('lanceur/operations.py','with c.lock, c.wireguard.lock, c.remote.lock:','with c.lock, c.wireguard.lock, c.remote.lock, c.remote.workspace.lock:',2)
    print('Source integration complete.')
