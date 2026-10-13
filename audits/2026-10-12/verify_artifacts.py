"""Verify staged resources and execute the compiled Windows workers in a fixture."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
sys.path.insert(0,str(ROOT/'client-qwen/build-tools'))
from core import HIDDEN
from test_remote import RemoteTests
from PyInstaller.archive.readers import CArchiveReader

windows=OUT/'distribution/windows/Accès serveur Fred.exe'
android=OUT/'distribution/android/Acces-serveur-Fred-Android.apk'
reader=CArchiveReader(str(windows))
assert reader.extract('chat.html')==(ROOT/'client-qwen/chat.html').read_bytes()
assert reader.extract('workspace.html')==(ROOT/'client-qwen/workspace.html').read_bytes()
pyz=reader.open_embedded_archive('PYZ.pyz')
assert 'fred_http' in pyz.toc
with zipfile.ZipFile(android) as apk:
    assert apk.read('assets/android-chat.html')==(ROOT/'client-android/app/src/main/assets/android-chat.html').read_bytes()
    assert apk.getinfo('classes.dex').file_size>0
    assert all(not name.endswith(('.dpapi','.fred-android')) and not name.endswith('/profil.json') for name in apk.namelist())
fixture=RemoteTests();fixture.setUp()
try:
    with tempfile.TemporaryDirectory(prefix='fred-audit-compiled-') as temporary:
        folder=Path(temporary);executable=folder/windows.name;shutil.copyfile(windows,executable)
        raw=json.dumps({**fixture.profile,'version':'3.5.28','protocol':3}).encode()
        with executable.open('ab') as stream:stream.write(raw+struct.pack('<I',len(raw))+b'QWENPROFILE1')
        result=folder/'self-test.txt'
        process=subprocess.run([str(executable),'--self-test','--voice-self-test','--conversation-self-test','--result',str(result)],timeout=120,creationflags=HIDDEN)
        assert process.returncode==0 and result.is_file() and 'self-test OK' in result.read_text(encoding='utf-8')
finally:fixture.tearDown()
report={'passed':True,'windows_compiled_workers_passed':True,'shared_assets_exact':True,'personal_data_absent':True,
    'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (windows,android)}}
(OUT/'artifacts-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
