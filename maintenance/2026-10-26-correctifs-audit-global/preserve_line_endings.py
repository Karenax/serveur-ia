"""Keep tracked source line endings; never touch files already edited by the user."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def main():
    protected=json.loads((OUT/'preexisting-files.json').read_text(encoding='utf-8'))
    modified=subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0')
    restored=[]
    for name in modified:
        if not name or name in protected:continue
        path=ROOT/name
        if not path.is_file():continue
        old=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        current=path.read_bytes()
        if b'\x00' in old or b'\x00' in current:continue
        lf=current.replace(b'\r\n',b'\n')
        if old.count(b'\r\n')==old.count(b'\n') and b'\n' in old:
            normalized=lf.replace(b'\n',b'\r\n')
        elif b'\r\n' not in old:
            normalized=lf
        else:continue
        if normalized!=current:path.write_bytes(normalized);restored.append(name)
    manifest_path=ROOT/'dependances/verrous/manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    for name,entry in manifest['environments'].items():
        entry['sha256']=hashlib.sha256((manifest_path.parent/(name+'.requirements.txt')).read_bytes()).hexdigest()
    manifest_path.write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    unchanged={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in protected.items()}
    if not all(unchanged.values()):raise ValueError('A pre-existing user edit changed: '+repr(unchanged))
    (OUT/'line-endings.json').write_text(json.dumps({'restored':restored,'preexisting_preserved':unchanged},indent=2),encoding='utf-8')
    print('Source line endings preserved; all pre-existing file hashes match.')


if __name__=='__main__':main()
