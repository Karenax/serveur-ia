"""Checked final source adjustments for the workspace release."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent
def replace(path,old,new,count=1):
    p=root/path;s=p.read_text(encoding='utf-8')
    if s.count(old)!=count:raise ValueError('Unexpected source anchor: '+path)
    p.write_text(s.replace(old,new),encoding='utf-8')
if __name__=='__main__':
    replace('client-qwen/chat.html','async function api(path,body){','async function api(path,body,headers={}){')
    replace('client-qwen/chat.html',"fetch(path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json'}","fetch(path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+config.key,'Content-Type':'application/json',...headers}")
    print('Final source adjustments complete.')
