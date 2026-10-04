"""Attend la fin de la copie utilisateur: tailles, absence de writer, entetes et echantillons."""
import hashlib
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent.parent/'strata-data/model-q4'
DEST=Path('C:/Temp')
files=sorted(SOURCE.glob('*IQ4_XS*.gguf'))
started=time.monotonic()
while True:
    states=[]
    complete=True
    for source in files:
        dest=DEST/source.name
        expected=source.stat().st_size
        present=dest.stat().st_size if dest.exists() else 0
        ready=False
        if present==expected:
            # Windows: deny sharing WRITE so an active copy cannot be mistaken for a complete preallocated file.
            import ctypes as c
            from ctypes import wintypes as w
            k=c.WinDLL('kernel32',use_last_error=True)
            k.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,c.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
            k.CreateFileW.restype=w.HANDLE
            k.CloseHandle.argtypes=[w.HANDLE]
            handle=k.CreateFileW(str(dest),0x80000000,1,None,3,0x80,None)
            if handle!=c.c_void_p(-1).value:
                k.CloseHandle(handle)
                ready=True
        complete &= ready
        states.append(dict(name=source.name,expected_bytes=expected,present_bytes=present,no_active_writer=ready))
    status=dict(status='copie-terminee' if complete else 'copie-en-cours',files=states,
                elapsed_seconds=round(time.monotonic()-started))
    (ROOT/'copie-ssd.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(status,ensure_ascii=False),flush=True)
    if complete:
        break
    time.sleep(20)
for source in files:
    dest=DEST/source.name
    with source.open('rb') as original,dest.open('rb') as copied:
        for offset in [0,source.stat().st_size//2,source.stat().st_size-262144]:
            original.seek(offset); copied.seek(offset)
            if original.read(262144)!=copied.read(262144):
                raise RuntimeError(f'Echantillon different: {source.name}, offset {offset}')
status.update(status='verifie',verification='Exact sizes, no open writer, and equal 256 KiB samples at beginning/middle/end of all shards')
(ROOT/'copie-ssd.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'modele-ssd.json').write_text(json.dumps(dict(native=str(DEST/files[0].name),
    ple_gguf=str(SOURCE/files[0].name),note='Native model on user SSD copy; D-backed PLE pages externally locked in RAM'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(status,ensure_ascii=False),flush=True)
