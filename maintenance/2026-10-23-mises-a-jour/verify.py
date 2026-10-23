"""Exercise the compiled client and isolated updater fixtures before publishing."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from updater import VERSION


def main():
    executable=ROOT/f'toolchain/releases-staging/windows-{VERSION}/Accès serveur Fred.exe'
    manifest=json.loads(executable.with_name('build-manifest.json').read_text(encoding='utf-8'))
    for name in ('client-qwen/client.py','client-qwen/updater.py'):
        assert manifest['source_files'][name]==hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    os.environ['FRED_TEST_CLIENT_EXE']=str(executable)
    result_file=OUT/'packaged-self-test.txt'
    smoke=subprocess.run([str(executable),'--self-test','--result',str(result_file)],timeout=45,creationflags=0x08000000)
    assert smoke.returncode==0 and 'self-test OK' in result_file.read_text(encoding='utf-8')
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name)
                             for name in ('test_update_layout','test_accounts_updates'))
    with (OUT/'tests.log').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    proof={'passed':result.wasSuccessful() and not result.skipped,'version':VERSION,
           'sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),'bytes':executable.stat().st_size,
           'tests':result.testsRun,'skipped':len(result.skipped),
           'checks':['packaged desktop self-test','incompatible profile exits without a dialog',
                     'signed update and startup rollback','two updates preserve EXE and directory names',
                     'legacy helper handoff cleanup preserves unrelated files']}
    (OUT/'exe-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(proof))
    assert proof['passed'],(OUT/'tests.log').read_text(encoding='utf-8')


if __name__=='__main__':main()
