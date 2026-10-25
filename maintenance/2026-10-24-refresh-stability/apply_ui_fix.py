"""Keep successful background checks from replacing unchanged visible controls."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def edit(name,old,new):
    path=ROOT/name;s=path.read_text(encoding='utf-8');assert old in s,name;path.write_text(s.replace(old,new),encoding='utf-8')
edit('client-qwen/ui.js',"function uiDecorateNavigation(){", "const uiNavigationLabels=new WeakMap();\nfunction uiDecorateNavigation(){")
edit('client-qwen/ui.js',"if(!uiNavTitles[name])continue;if(name==='notifications')", "if(!uiNavTitles[name])continue;const unchangedSignature=JSON.stringify([name,uiNavTitles[name],b.dataset.unreadCount||0,b.dataset.unread==='true'||b.textContent.includes('résultats disponibles')]);if(uiNavigationLabels.get(b)===unchangedSignature&&b.querySelector('.nav-text'))continue;uiNavigationLabels.set(b,unchangedSignature);if(name==='notifications')")
edit('client-qwen/workspace.html',"const data=await api('/v1/workspace');ws.data=data;wsChatSelections();", "const data=await api('/v1/workspace'),unchanged=JSON.stringify(data)===JSON.stringify(ws.data);ws.data=data;if(unchanged)return;wsChatSelections();")
