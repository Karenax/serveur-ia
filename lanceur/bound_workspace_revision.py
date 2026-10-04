"""Ensure a whole-document revision never silently truncates the original."""
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'client-qwen/workspace.html'
s=p.read_text(encoding='utf-8')
anchor="await wsFlush();const d=ws.document,r=await wsAction('job_create'"
if s.count(anchor)!=1:raise ValueError('Revision source anchor changed.')
s=s.replace(anchor,"await wsFlush();if($('ws-document-text').value.length>7500)throw new Error('Révision complète limitée à 7 500 caractères. Travaillez par passages dans le chat pour un document plus long.');const d=ws.document,r=await wsAction('job_create'")
s=s.replace("$('ws-document-text').value.slice(0,7500)","$('ws-document-text').value")
p.write_text(s,encoding='utf-8')
