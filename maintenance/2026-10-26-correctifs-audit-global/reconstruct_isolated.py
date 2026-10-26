"""Reconstruct the source release with locked public packages, without production data."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
TARGET = ROOT / 'toolchain/reconstruction-3.5.53'


def main():
    TARGET.mkdir(exist_ok=False)
    archive = ROOT / 'toolchain/releases-staging/server/kiara-server-sources.zip'
    with zipfile.ZipFile(archive) as packed:
        for name in packed.namelist():
            if not (TARGET / name).resolve().is_relative_to(TARGET.resolve()):
                raise ValueError('Archive path outside reconstruction')
        packed.extractall(TARGET)
    uv = Path(os.environ['LOCALAPPDATA']) / 'hermes/bin/uv.exe'
    python = TARGET / '.venv/Scripts/python.exe'
    commands = [
        [str(uv), 'venv', '--python', str(ROOT / 'Strata-src/.venv/Scripts/python.exe'), str(TARGET / '.venv')],
        [str(uv), 'pip', 'install', '--python', str(python), '--require-hashes',
         '-r', str(TARGET / 'dependances/verrous/strata.requirements.txt')],
        [str(uv), 'pip', 'install', '--python', str(python), '--no-build-isolation', str(TARGET / 'shared')],
        [str(uv), 'pip', 'check', '--python', str(python)],
    ]
    for command in commands:
        subprocess.run(command, check=True, timeout=300)
    verify()


def verify():
    archive = ROOT / 'toolchain/releases-staging/server/kiara-server-sources.zip'
    python = TARGET / '.venv/Scripts/python.exe'
    if '--refresh-sources' in sys.argv:
        with zipfile.ZipFile(archive) as packed:
            for name in packed.namelist():
                if not (TARGET/name).resolve().is_relative_to(TARGET.resolve()):
                    raise ValueError('Archive path outside reconstruction')
            packed.extractall(TARGET)
    # The installed package, exported server modules and synthetic data are the
    # only application inputs. No model, credential or personal home is copied.
    script = r'''
import base64,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path('lanceur').resolve()))
import app,remote,voice_max,kiara_shared
from workspace import Workspace
with tempfile.TemporaryDirectory(prefix='kiara-clean-data-') as folder:
    workspace=Workspace(Path(folder))
    created=workspace.action('fixture',{'action':'personal_memory_create','text':'Souvenir fictif conservé'})
    project=workspace.action('fixture',{'action':'project_create','title':'Restauration fictive'})['id']
    document=workspace.action('fixture',{'action':'document_upload','project':project,'title':'preuve.txt',
        'data':base64.b64encode(b'Extraction depuis le runtime propre').decode()})['id']
    assert 'runtime propre' in workspace.action('fixture',{'action':'document_get','id':document})['text']
    image=workspace.backup()
    raw=workspace.validate_backup(image,{'fixture'})
    workspace.restore(raw)
    snapshot=workspace.snapshot('fixture')
    assert snapshot['personal_memories'][0]['text']=='Souvenir fictif conservé'
    with workspace.db() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==2
    workspace.shutdown()
print(json.dumps({'passed':True,'cold_server_import':True,'synthetic_restoration':True,
    'isolated_document_extraction':True,
    'schema':2,'client_directory_present':Path('client-qwen').exists(),
    'shared_package':kiara_shared.__file__},ensure_ascii=True))
'''
    result = subprocess.run([str(python), '-c', script], cwd=TARGET, capture_output=True,
                            text=True, encoding='utf-8', timeout=60,
                            env={**os.environ, 'PYTHONPATH': '', 'PYTHONIOENCODING': 'utf-8',
                                 'KIARA_DATA_DIR': str(TARGET / 'unused-production-home'),
                                 'KIARA_RUNTIME_PYTHON':str(python)})
    print(result.stdout)
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
    proof = json.loads(result.stdout.strip().splitlines()[-1])
    proof.update({'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'same_host':True,'physical_disaster_recovery_test':False,
                  'public_lock_sha256':hashlib.sha256((TARGET/'dependances/verrous/strata.requirements.txt').read_bytes()).hexdigest()})
    (OUT/'reconstruction-isolated.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')


if __name__ == '__main__':
    verify() if '--verify-only' in sys.argv or '--refresh-sources' in sys.argv else main()
