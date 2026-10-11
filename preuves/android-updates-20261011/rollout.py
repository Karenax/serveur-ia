"""Reload only the console and its helpers; keep inference processes and access keys intact."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lanceur'))
from core import HOME, HIDDEN, read_json, same_process
from validate_live_lots6_8 import get, models, preserved_files
from android_releases import status
from wg_crypto import protect


def main():
    release, apk = status()
    assert release['version'] == '1.0.5' and release['version_code'] == 6
    staged = ROOT / 'toolchain/releases-staging/android-updates/wireguard-bridge.exe'
    assert staged.is_file()
    if '--verify-only' in sys.argv:
        verify_download(release)
        return
    before = {'models': models(), 'files': preserved_files()}
    live = get('/api/state')
    assert live['running'] and live['health']['loaded'] and not live['queue']['active'] and not live['queue']['waiting']
    remote = get('/api/remote')
    assert not remote.get('active', 0)
    target = ROOT / 'client-qwen/wireguard-bridge.exe'
    backup = staged.parent / 'wireguard-bridge-before.exe'
    if not backup.exists(): shutil.copy2(target, backup)
    process = same_process(read_json(HOME / 'interface.pid.json', {}))
    assert process is not None and str(HOME / 'app.py').lower() in [arg.lower() for arg in process.cmdline()]
    helpers = []
    for child in process.children(recursive=True):
        args = child.cmdline()
        if any(Path(arg).name.lower() in ('embedding_worker.py', 'voice_worker.py', 'wireguard-bridge.exe') for arg in args):
            assert child.pid not in {item['pid'] for item in before['models']}
            helpers.append((child, child.create_time()))
    process.terminate(); process.wait(timeout=10)
    for child, created in reversed(helpers):
        try:
            if child.is_running() and abs(child.create_time()-created) < .01:
                child.terminate(); child.wait(timeout=10)
        except psutil.NoSuchProcess: pass
    try:
        shutil.copy2(staged, target)
    finally:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                str(ROOT / 'Start-Interface-Qwen.ps1'), '-SansNavigateur', '-PreserverEtatModele'],
                capture_output=True, timeout=45, creationflags=HIDDEN)
        assert result.returncode == 0, 'Console restart failed'
    live = get('/api/state')
    assert live['running'] and live['health']['loaded']
    after = {'models': models(), 'files': preserved_files()}
    assert before == after, 'Model processes or access/configuration files changed'
    verify_download(release)


def verify_download(release):
    from releases import profile as exe_profile
    saved = HOME / 'wireguard-prive/profils-restaures.dpapi'
    profiles = json.loads(protect(saved.read_bytes(), decrypt=True)) if saved.exists() else {}
    clients = get('/api/remote')['clients']
    allowed = {c['id'] for c in clients if not c['revoked'] and not c.get('suspended') and (not c.get('expires_epoch') or c['expires_epoch'] > time.time())}
    for identity in allowed:
        executable = HOME / 'clients' / (identity + '.exe')
        if identity not in profiles and executable.is_file(): profiles[identity] = exe_profile(executable)
    for executable in (HOME / 'clients').glob('*.exe'):
        try:
            value = exe_profile(executable)
            identity = value['token'].split('_')[1]
            if identity in allowed: profiles[identity] = value
        except (ValueError, KeyError, IndexError): pass
    profile = next(value for key, value in profiles.items() if key in allowed)
    headers = {'Authorization': 'Bearer ' + profile['token'], 'User-Agent': 'AccesServeurFred/1.0.5 (Android)'}
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8766/v1/client/android/release', headers=headers), timeout=10) as response:
        assert json.load(response) == release
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8766/v1/client/android/download', headers=headers), timeout=30) as response:
        digest = hashlib.sha256(); count = 0
        while chunk := response.read(65536): digest.update(chunk); count += len(chunk)
    assert count == release['bytes'] and digest.hexdigest() == release['sha256']
    report = {'passed': True, 'release': release, 'model_processes_preserved': models(),
              'access_and_settings_preserved': True, 'authenticated_download_verified': True, 'contains_secrets': False}
    (Path(__file__).parent / 'production-validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__': main()
