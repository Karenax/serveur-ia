"""Produce repeatable isolated backup/restoration evidence without live changes."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().parent
DESTINATION = SOURCE.parent / 'preuves' / 'lots-0-4'
FILES = ('app.py', 'operations.py', 'backups.py', 'restoration.py', 'server_state.py',
         'workspace.py', 'remote.py', 'devices.py', 'test_backups.py', 'test_restoration.py')


def hashes():
    return {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in FILES}


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    before = hashes()
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    started = time.time()
    result = subprocess.run([sys.executable, '-m', 'unittest', 'test_backups', 'test_restoration', '-v'],
                            cwd=SOURCE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    log = result.stdout.decode('utf-8', errors='replace')
    # Failure diagnostics must not turn credential values into proof artefacts.
    log = re.sub(r'([\"\x27](?:api_key|token|private_key|preshared_key|password_hash|password)[\"\x27]\s*:\s*)([\"\x27])[^\r\n]*?\2',
                 lambda match: match[1] + match[2] + '[masqué]' + match[2], log)
    (DESTINATION / 'backup-tests.log').write_text(log, encoding='utf-8', newline='')
    volume = next((json.loads(line.split('VOLUME_PROOF ', 1)[1]) for line in log.splitlines() if 'VOLUME_PROOF ' in line), {})
    count = re.search(r'Ran (\d+) tests in ([0-9.]+)s', log)
    after = hashes()
    report = {'exit_code': result.returncode, 'success': result.returncode == 0,
              'test_count': int(count[1]) if count else 0,
              'test_seconds': float(count[2]) if count else round(time.time() - started, 3),
              'isolated': True, 'source_files_unchanged_during_run': before == after,
              'source_sha256': before, 'volume': volume,
              'limits': {'source_document_bytes': 2097152, 'owner_storage_bytes': 20971520,
                         'global_storage_bytes': 134217728, 'sqlite_restore_bytes': 268435456,
                         'encrypted_archive_bytes': 419430400},
              'notes': ['Archives Fernet en mémoire avec limites explicites ; mesures de volume sur 8 DOCX valides.',
                        'L’horloge de programmation est celle du serveur ; le processus serveur doit fonctionner.',
                        'Seconde copie : une erreur conserve la source locale et déclenche une nouvelle tentative.']}
    (DESTINATION / 'backup-volume.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'success': report['success'], 'test_count': report['test_count'],
                     'sources_stable': report['source_files_unchanged_during_run'], 'volume': volume,
                     'log': str(DESTINATION / 'backup-tests.log'), 'report': str(DESTINATION / 'backup-volume.json')}, ensure_ascii=False))
    return result.returncode or (0 if before == after else 2)


if __name__ == '__main__': sys.exit(main())
