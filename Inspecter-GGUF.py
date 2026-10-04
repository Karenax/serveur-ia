import struct,json
from pathlib import Path
base=Path(r'D:\modèle\huihui-ai\Huihui-Qwen3.8-27B-abliterated-GGUF')
for p in base.glob('*.gguf'):
 if p.name.startswith('mmproj'):continue
 f=p.open('rb'); magic,ver,nt,nk=struct.unpack('<4sIQQ',f.read(24))
 def s():return f.read(struct.unpack('<Q',f.read(8))[0]).decode('utf8')
 def v(t):
  fm={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
  if t==8:return s()
  if t==9:
   typ,n=struct.unpack('<IQ',f.read(12));return [v(typ) for _ in range(n)]
  fmt='<'+fm[t];return struct.unpack(fmt,f.read(struct.calcsize(fmt)))[0]
 meta={}
 for _ in range(nk):
  k=s();val=v(struct.unpack('<I',f.read(4))[0])
  if k.startswith('general.') or any(x in k for x in ['block_count','expert_count','embedding_length','context_length']):meta[k]=val
 print(p.name,json.dumps(meta))
