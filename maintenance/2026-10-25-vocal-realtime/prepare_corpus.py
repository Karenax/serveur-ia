import sys,io,json,urllib.request,hashlib,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'toolchain/vocal-benchmark-libs'))
import pyarrow.parquet as pq
import numpy as np,struct
OUT=Path(__file__).resolve().parent
BASE='https://huggingface.co/datasets/google/fleurs/resolve/refs%2Fconvert%2Fparquet/fr_fr/test/0000.parquet'
class Remote(io.RawIOBase):
    pos=0;length=445464011;downloaded=0
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.length+offset
        return self.pos
    def read(self,n=-1):
        start=self.pos;end=min(self.length-1,start+(self.length-start if n<0 else n)-1)
        if end<start:return b''
        cache=ROOT/'toolchain/french-speech-benchmark-cache'/f'{start}-{end}.bin';cache.parent.mkdir(exist_ok=True)
        if cache.exists():
            raw=cache.read_bytes();self.pos+=len(raw);return raw
        req=urllib.request.Request(BASE+'?range_start='+str(start),headers={'Range':f'bytes={start}-{end}'})
        with urllib.request.urlopen(req,timeout=90) as response:
            assert response.status==206 and response.headers.get('Content-Range','').startswith(f'bytes {start}-'),(response.status,response.headers.get('Content-Range'))
            raw=response.read(end-start+1)
        cache.write_bytes(raw)
        self.pos+=len(raw);self.downloaded+=len(raw);print(json.dumps({'range':start,'bytes':len(raw),'total':self.downloaded}),flush=True)
        return raw
remote=Remote();file=pq.ParquetFile(remote)
print(json.dumps({'row_groups':file.num_row_groups,'rows_first_group':file.metadata.row_group(0).num_rows}),flush=True)
rows=file.read_row_group(0,columns=['audio','raw_transcription','transcription','gender']).to_pylist()
folder=ROOT/'toolchain/french-speech-benchmark';folder.mkdir(exist_ok=True)
corpus=[]
for i,row in enumerate(rows[:8]):
    audio=row['audio']['bytes'];name=f'fleurs-fr-{i+1}.wav'
    offset=12;raw=b'';rate=16000
    while offset+8<=len(audio):
        tag,size=struct.unpack_from('<4sI',audio,offset);block=audio[offset+8:offset+8+size]
        if tag==b'fmt ':fmt,channels,rate,_,_,bits=struct.unpack_from('<HHIIHH',block);assert channels==1
        if tag==b'data':raw=block
        offset+=8+size+(size%2)
    assert fmt==3 and bits==32
    samples=np.frombuffer(raw,dtype='<f4');seconds=len(samples)/rate
    with wave.open(str(folder/name),'wb') as dest:
        dest.setnchannels(1);dest.setsampwidth(2);dest.setframerate(rate);dest.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
    corpus.append({'file':name,'text':row['raw_transcription'],'gender':row['gender'],'rate':rate,'seconds':seconds,'sha256':hashlib.sha256(audio).hexdigest()})
(OUT/'corpus.json').write_text(json.dumps({'source':'google/fleurs, fr_fr/test, first 8 rows','license':'CC-BY-4.0','files':corpus,'downloaded_bytes':remote.downloaded},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'prepared':len(corpus),'seconds':sum(row['seconds'] for row in corpus),'downloaded_bytes':remote.downloaded}),flush=True)
