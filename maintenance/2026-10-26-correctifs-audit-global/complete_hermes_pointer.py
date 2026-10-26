"""Make the retained dependency directories explicit; no personal bootstrap or install."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def main():
    path=ROOT/'toolchain/hermes-security-runtime/runtime.json'
    previous=OUT/'hermes-runtime-before.json'
    if not previous.exists():shutil.copy2(path,previous)
    value=json.loads(path.read_text(encoding='utf-8'))
    local=Path(os.environ['LOCALAPPDATA'])
    value['dependencies']=str(local/'hermes/installs')
    value['tools']=str(local/'hermes/tools')
    value['runtime_lock']='dependances/verrous/hermes-fred.requirements.txt'
    value['runtime_lock_sha256']=hashlib.sha256((ROOT/value['runtime_lock']).read_bytes()).hexdigest()
    if not all(Path(value[name]).is_dir() for name in ('source','dependencies','tools')):
        raise ValueError('Retained runtime prerequisites missing')
    pending=path.with_suffix('.json.audit.tmp')
    pending.write_text(json.dumps(value,indent=2),encoding='utf-8')
    sys.path.insert(0,str(ROOT/'lanceur'))
    from hermes_runtime import private_installation
    assert private_installation(pending)['private']
    pending.replace(path)
    (OUT/'hermes-runtime.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print('Private Hermes prerequisites recorded without personal bootstrap.')


if __name__=='__main__':main()
