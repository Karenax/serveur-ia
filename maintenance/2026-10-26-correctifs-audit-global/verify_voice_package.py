"""Verify signed inventory and frozen worker startup; never open audio devices."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent


def main():
    sys.path.insert(0,str(ROOT/'lanceur'))
    from core import HOME
    from voice_max_package import package
    catalogue,archive=package(HOME,ROOT/'toolchain/releases-staging/voice-max')
    target=ROOT/'toolchain/voice-audit-probe'
    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as packed:
        expected={row['name']:row for row in catalogue['runtime']['files']}
        assert set(packed.namelist())==set(expected)
        for name,row in expected.items():
            destination=(target/name).resolve()
            assert destination.is_relative_to(target.resolve())
            data=packed.read(name)
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
        packed.extractall(target)
    config=target/'probe-config.json'
    config.write_text(json.dumps({'root':str(target)}),encoding='utf-8')
    result=subprocess.run([str(target/'max-worker.exe'),'--config',str(config),'--probe-gpus'],capture_output=True,
                          timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT/'voice-probe.txt').write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,'Frozen voice worker startup failed'
    value=json.loads(result.stdout.decode('utf-8').strip().splitlines()[-1])
    assert 'error' not in value and isinstance(value.get('devices'),list),value
    proof={'passed':True,'signature_verified':True,'inventory_verified':True,
           'revision':catalogue['revision'],'runtime_bytes':archive.stat().st_size,
           'frozen_worker_probe':True,'microphone_opened':False,'speech_inference_tested':False}
    (OUT/'voice-package-validation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps(proof))


if __name__=='__main__':main()
