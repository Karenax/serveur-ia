import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'client-qwen/build-tools'))
from PyInstaller.archive.readers import CArchiveReader
exe=ROOT/'toolchain/releases-staging/windows-3.5.21/Accès serveur Fred.exe';archive=CArchiveReader(str(exe))
files=['chat.html','conversation.js','voice.js','THIRD-PARTY.txt','wireguard-bridge.exe',
       'voice/conversation-models.json','voice/native-manifest.json','voice/fredaec.dll',
       'voice/conversation-worker/conversation-worker.exe','voice/licenses/CONVERSATION-NOTICES.txt',
       'voice/licenses/silero-vad-LICENSE.txt','voice/licenses/smart-turn-LICENSE.txt']
checked={}
for name in files:
    key=next(key for key in archive.toc if key.replace('\\','/')==name)
    actual=archive.extract(key);expected=(ROOT/'client-qwen'/name).read_bytes()
    assert actual==expected,name
    checked[name]=hashlib.sha256(actual).hexdigest()
result=ROOT/'preuves/conversation-windows-20261011/windows-exe-self-test.txt'
process=subprocess.run([str(exe),'--self-test','--voice-self-test','--conversation-self-test','--result',str(result)],timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
assert process.returncode==0,result.read_text(encoding='utf-8')
value={'passed':True,'version':'3.5.21','sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'bytes':exe.stat().st_size,
       'embedded_files_verified':checked,'self_test_exit_code':process.returncode}
(result.parent/'windows-release.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'version':value['version'],'bytes':value['bytes'],'sha256':value['sha256']}))
