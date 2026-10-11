"""Verify final packages and emulator upgrades; never reads production secrets."""
import hashlib
import json
import re
import struct
import subprocess
import sys
import zipfile
import psutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(__file__).resolve().parent
ADB = ROOT / 'toolchain/android-sdk/platform-tools/adb.exe'
APK = ROOT / 'client-android/dist/Acces-serveur-Fred-Android.apk'
EXE = ROOT / 'client-qwen/dist/Accès serveur Fred.exe'
DEBUG = ROOT / 'client-android/app/build/outputs/apk/debug/app-debug.apk'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write(name, value):
    (PROOF / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def adb(device, *args):
    return subprocess.check_output([str(ADB), '-s', device, *args], encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)

upgrades, installed = {}, {}
with zipfile.ZipFile(DEBUG) as debug:
    for device in ('emulator-5554', 'emulator-5556'):
        before = adb(device, 'shell', 'dumpsys', 'package', 'net.karenax.fred')
        first = re.search(r'firstInstallTime=([^\r\n]+)', before).group(1)
        if '--verify-only' not in sys.argv:
            result = adb(device, 'install', '-r', str(APK))
            assert 'Success' in result, result
        after = adb(device, 'shell', 'dumpsys', 'package', 'net.karenax.fred')
        assert 'versionName=1.0.3' in after and re.search(r'versionCode=4\b', after)
        assert first == re.search(r'firstInstallTime=([^\r\n]+)', after).group(1)
        signed_path = adb(device, 'shell', 'pm', 'path', 'net.karenax.fred').strip().removeprefix('package:')
        signed = PROOF / (device + '-installed-release.apk')
        adb(device, 'pull', signed_path, str(signed))
        assert sha(signed) == sha(APK)
        upgrades[device] = dict(passed=True, upgrade_to='1.0.3', first_install_unchanged=True,
                               uninstall_performed=False, installed_sha256=sha(signed))
        qa_path = adb(device, 'shell', 'pm', 'path', 'net.karenax.fred.voiceqa').strip().removeprefix('package:')
        qa = PROOF / (device + '-installed-debug.apk')
        adb(device, 'pull', qa_path, str(qa))
        with zipfile.ZipFile(qa) as actual:
            installed[device] = {name: actual.read(name) == debug.read(name) for name in
                ('classes.dex', 'lib/x86_64/libfredvoice.so', 'assets/voice/model.json', 'assets/android-chat.html')}
            assert all(installed[device].values())
write('android-signed-upgrade.json', upgrades)
write('android-installed-code-check.json', installed)

alignment = {}
with zipfile.ZipFile(APK) as release, zipfile.ZipFile(DEBUG) as debug:
    for name in release.namelist():
        if not name.startswith('lib/') or not name.endswith('.so') or name.endswith('/libfredwireguard.so'):
            continue
        data = release.read(name)
        assert data == debug.read(name), name
        assert data[:5] == b'\x7fELF\x02'
        offset = struct.unpack_from('<Q', data, 32)[0]
        entry_size, count = struct.unpack_from('<HH', data, 54)
        loads = [struct.unpack_from('<Q', data, offset + i * entry_size + 48)[0]
                 for i in range(count) if struct.unpack_from('<I', data, offset + i * entry_size)[0] == 1]
        assert loads and all(value >= 16384 for value in loads), (name, loads)
        alignment[name] = loads
write('android-elf-alignment.json', dict(passed=True, load_alignment_bytes=alignment))

for artifact, report_name in ((EXE, 'windows-release.json'), (APK, 'android-release.json')):
    report = json.loads((PROOF / report_name).read_text(encoding='utf-8'))
    assert report['passed'] and report['sha256'] == sha(artifact)
    assert artifact.stat().st_size == report['bytes']

expected_tests = {'regressions.log': 246, 'delivery-targeted-tests.log': 15,
                  'service-tests.log': 8, 'http-tests.log': 3, 'android-python-tests.log': 13}
for name, count in expected_tests.items():
    log = (PROOF / name).read_text(encoding='utf-8')
    assert re.search(rf'Ran {count} tests? in ', log) and re.search(r'^OK\s*$', log, re.MULTILINE), name
for name in ('windows-native-results.json', 'production-after.json', 'android-real-install.json', 'browser/voice-ui.json'):
    assert json.loads((PROOF / name).read_text(encoding='utf-8'))['passed'], name
production = json.loads((PROOF / 'production-after.json').read_text(encoding='utf-8'))
for process in production['current']['models']:
    assert abs(psutil.Process(process['pid']).create_time() - process['created']) < 0.01
for name, expected_hash in production['current']['files'].items():
    assert sha(ROOT / 'lanceur' / name) == expected_hash, name

sources = []
for folder, suffixes in (('client-voice', {'.cpp', '.h', '.json', '.txt', '.ps1', '.cmd', '.py'}),
                         ('client-android/app/src/main/java', {'.java'})):
    sources.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in suffixes)
sources.extend(ROOT / p for p in ('client-qwen/local_voice.py', 'client-qwen/voice.js', 'client-qwen/client.py',
    'client-qwen/chat.html', 'client-qwen/ui.css', 'client-qwen/Build-Client.ps1', 'client-qwen/updater.py',
    'client-android/app/build.gradle', 'client-android/app/src/main/AndroidManifest.xml',
    'client-android/scripts/Build-Voice-Android.ps1', 'client-android/Build-Android.ps1',
    'client-android/scripts/Prepare-Assets.py', 'client-android/scripts/Prepare-Licenses.py',
    'lanceur/operations.py'))
sources = [p for p in sources if p.is_file()]
write('delivery-final.json', dict(passed=True, checked_at_utc=datetime.now(timezone.utc).isoformat(),
    artifacts={str(p.relative_to(ROOT)): dict(bytes=p.stat().st_size, sha256=sha(p)) for p in (EXE, APK)},
    emulator_signed_upgrade=upgrades, emulator_installed_code=installed, android_elf_16k=True,
    production_model_processes_and_protected_files_unchanged=True,
    tests=expected_tests, broad_regressions_before_final_css_and_version_metadata=True,
    final_css_native_ui_and_version_targeted_tests_passed=True,
    physical_android_tested=False, sources={str(p.relative_to(ROOT)): sha(p) for p in sorted(set(sources))}))
print('PASS: final signed packages, upgrades, installed QA code, ELF 16K, test evidence and source fingerprints')
