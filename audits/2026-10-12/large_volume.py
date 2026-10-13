"""64/120 MiB original-document contracts in disposable access registries."""
import base64
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys
import threading
import time
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'lanceur'))
import psutil
from docx import Document
from test_backups import BackupsTests,PHRASE

def run(mebibytes):
    case=BackupsTests();case.setUp()
    try:
        doc=Document();doc.add_paragraph('Document synthétique du test de volume.')
        stream=io.BytesIO();doc.save(stream);template=stream.getvalue()
        sized=io.BytesIO(template)
        with zipfile.ZipFile(sized,'a',compression=zipfile.ZIP_STORED) as archive:archive.writestr('word/media/volume.bin',b'')
        padded=io.BytesIO(template)
        with zipfile.ZipFile(padded,'a',compression=zipfile.ZIP_STORED) as archive:archive.writestr('word/media/volume.bin',b'\x7f'*(2*1024*1024-len(sized.getvalue())))
        original=padded.getvalue();expected=hashlib.sha256(original).hexdigest();ids=[]
        for group in range((mebibytes//2+7)//8):
            owner=case.c.remote.issue('Volume '+str(group))['id']
            project=case.w.action(owner,{'action':'project_create','title':'Volume'})['id']
            with case.w.db(owner) as db:
                for i in range(min(8,mebibytes//2-len(ids))):
                    identity=secrets.token_hex(16);ids.append(identity)
                    db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)',(identity,owner,project,'Volume.docx','Texte du document',original,'docx',1,time.time()))
        with case.w.db() as db:assert case.w.usage(db)<128*1024*1024
        baseline=psutil.Process().memory_info().rss;peak=[baseline];halt=threading.Event()
        def sample():
            while not halt.wait(.01):peak[0]=max(peak[0],psutil.Process().memory_info().rss)
        sampler=threading.Thread(target=sample);sampler.start()
        try:
            start=time.monotonic();archive=case.backup();backup_seconds=time.monotonic()-start
            with case.w.db() as db:db.execute("UPDATE documents SET original=X'01' WHERE kind='docx'")
            start=time.monotonic();case.c.operations.restore({'file':archive['file'],'password':PHRASE});restore_seconds=time.monotonic()-start
            with case.w.db() as db:
                for identity in ids:
                    assert hashlib.sha256(db.execute('SELECT original FROM documents WHERE id=?',(identity,)).fetchone()[0]).hexdigest()==expected
            return {'original_mib':mebibytes,'documents':len(ids),'sha256_match':True,'archive_bytes':Path(archive['file']).stat().st_size,
                'backup_seconds':round(backup_seconds,3),'restore_seconds':round(restore_seconds,3),'rss_increase_bytes':peak[0]-baseline}
        finally:halt.set();sampler.join()
    finally:case.tearDown()

if __name__=='__main__':
    result=run(int(sys.argv[1]));print(json.dumps(result))
    Path(__file__).with_name('volume-'+sys.argv[1]+'.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
