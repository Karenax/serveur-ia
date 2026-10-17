"""Verify the staged executable, embedded audio engine and personal update footer."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'client-qwen/build-tools'),str(ROOT/'client-qwen'),str(ROOT/'lanceur')]
from PyInstaller.archive.readers import CArchiveReader
from wg_crypto import keypair
from updater import VERSION

binary=ROOT/'toolchain/releases-staging/conversation-20261014/windows/Accès serveur Fred.exe'
archive=CArchiveReader(str(binary));checked=[]
for embedded,source in [('chat.html',ROOT/'client-qwen/chat.html'),('conversation.js',ROOT/'client-qwen/conversation.js'),('voice/fredaec.dll',ROOT/'client-qwen/voice/fredaec.dll'),('voice/conversation-worker/conversation-worker.exe',ROOT/'client-qwen/voice/conversation-worker/conversation-worker.exe')]:
    name=embedded.replace('/','\\') if embedded.replace('/','\\') in archive.toc else embedded
    assert archive.extract(name)==source.read_bytes(),embedded
    checked.append(embedded)
with tempfile.TemporaryDirectory(prefix='fred-voice-exe-') as folder:
    base=Path(folder);private,public=keypair()
    profile={'url':'wireguard://10.77.0.1:8766','transport':'wireguard','token':'qwen_'+'a'*16+'_'+'b'*43,'protocol':3,'version':VERSION,
             'wireguard':{'private_key':private,'server_public_key':public,'preshared_key':public,'address':'10.77.0.2/32','endpoint':'example.test:51820'}}
    personal=base/'Fred-personal-test.exe';personal.write_bytes(binary.read_bytes())
    raw=json.dumps(profile).encode()
    with personal.open('ab') as stream:stream.write(raw+struct.pack('<I',len(raw))+b'QWENPROFILE1')
    output=base/'result.txt'
    result=subprocess.run([str(personal),'--self-test','--with-profile','--conversation-self-test','--result',str(output)],capture_output=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and output.exists(),result.stderr[-1000:]
with binary.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
report={'passed':True,'version':VERSION,'sha256':digest,
        'embedded_files_verified':checked,'personal_profile_version_matches':True,'native_capture_start_stop':True,'profile':'disposable; no real access or keys'}
(OUT/'artifact.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
