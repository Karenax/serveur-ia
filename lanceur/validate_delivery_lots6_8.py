"""Verify published lots 6/8 against frozen tests, artifacts and live preservation."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PROOFS = ROOT / 'preuves/lots-6-8'
sys.path.insert(0, str(ROOT / 'lanceur'))
import validate_live_lots6_8 as live


def read(name):
    return json.loads((PROOFS / name).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assert_hashes(values):
    for name, expected in values.items():
        assert digest(ROOT / name) == expected, 'Source differs from evidence: ' + name


def check_links():
    files = [ROOT / name for name in ('README.md', 'CONTEXTE-PROJET.md',
        'PLAN-GLOBAL-SERVEUR-FRED.md', 'lanceur/RECHERCHE-NOTIFICATIONS.md')]
    files.extend(PROOFS.rglob('*.md'))
    checked = 0
    for path in files:
        content = path.read_text(encoding='utf-8-sig')
        for value in re.findall(r'\]\((<[^>]+>|[^)\s]+)\)', content):
            target = urllib.parse.unquote(value.strip('<>')).split('#', 1)[0]
            if not target or re.match(r'^[a-z]+://', target, re.I):
                continue
            resolved = path.parent / target
            assert resolved.exists(), 'Missing document link: ' + str(path.relative_to(ROOT)) + ' -> ' + target
            checked += 1
    return checked


def main():
    regressions = read('regressions-final.json')
    assert regressions['result'] == 'PASS' and regressions['sources_unchanged_during_run']
    assert_hashes(regressions['source_sha256'])
    for name, expected in regressions['test_source_sha256'].items():
        assert digest(ROOT / 'lanceur' / name) == expected
    research = read('recherche/validation.json')
    assert research['status'] == 'PASS' and research['sources_unchanged']
    assert research['measurement']['all_checks_pass']
    assert_hashes(research['sources_after'])
    targeted = {}
    for name in ('notifications/notifications-tests.json', 'notifications/worker-recovery-tests.json'):
        result = read(name)
        assert result['result'] == 'PASS' and result['source_unchanged']
        assert_hashes(result['source_after'])
        targeted[name] = result['tests']
    fence = read('notifications/source-access-fence-tests.json')
    assert fence['result'] == 'PASS' and fence['source_unchanged']
    assert digest(ROOT / 'lanceur/remote.py') == fence['remote_sha256']
    browser_counts = {}
    for name in ('client-ui/client-lots6-8-ui.json', 'notifications/notifications-ui.json'):
        result = read(name)
        assert result['realBackend'] and not result['liveDataUsed'] and not result['errors']
        assert all(item['passed'] for item in result['checks'])
        browser_counts[name] = len(result['checks'])

    windows = read('windows-release.json')
    exe = ROOT / 'client-qwen/dist/Accès serveur Fred.exe'
    assert windows['self_test'] == 'PASS' and digest(exe) == windows['sha256']
    sys.path.insert(0, str(ROOT / 'client-qwen/build-tools'))
    from PyInstaller.archive.readers import CArchiveReader
    packaged = CArchiveReader(str(exe))
    for name, expected in windows['embedded_final_source_sha256'].items():
        assert digest(ROOT / 'client-qwen' / name) == expected
        assert hashlib.sha256(packaged.extract(name)).hexdigest() == expected

    android = read('android/delivery.json')
    apk = ROOT / 'client-android/dist/Acces-serveur-Fred-Android.apk'
    assert android['passed'] and digest(apk) == android['sha256']
    assert apk.stat().st_size == android['bytes']
    assert android['version'] == '1.0.2' and android['versionCode'] == 3
    assert len(android['release_upgrade']) == 2
    signature = (PROOFS / 'android-published-signature.txt').read_text(encoding='utf-8-sig')
    assert 'Signer #1 certificate SHA-256 digest: ' + android['certificate_sha256'] in signature
    assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in signature
    assert 'Verified using v3 scheme (APK Signature Scheme v3): true' in signature
    with zipfile.ZipFile(apk) as archive:
        package = json.loads(archive.read('assets/ui-package.json'))
        assert package == android['ui_package']
        assert hashlib.sha256(archive.read('assets/android-chat.html')).hexdigest() == package['sha256']
    for name, expected in package['shared_sources'].items():
        assert digest(ROOT / 'client-qwen' / name) == expected
    for name, expected in package['mobile_sources'].items():
        assert digest(ROOT / 'client-android/mobile-ui' / name) == expected
    assert all(result['passed'] and result['exceptions'] == 0 for result in android['reports'].values())

    production = read('production-validation.json')
    live.assert_preserved(production)
    assert production['result'] == 'PASS'
    state = live.get('/api/state')
    assert state['running'] and state['health']['loaded']
    release = live.get('/api/releases')
    assert release['verified'] and release['server_version'] == windows['version']
    assert not live.get('/api/maintenance')['active']
    notifications = live.get('/api/notifications')
    assert notifications['delivery'] == {'mode': 'connected', 'push': False}
    static = []
    for route in ('/notifications.js', '/notifications.css'):
        with urllib.request.urlopen(live.BASE + route, timeout=5) as response:
            assert response.status == 200 and response.read()
        static.append(route)
    with urllib.request.urlopen(live.BASE, timeout=5) as response:
        index = response.read().decode('utf-8')
    assert 'notifications.js' in index and 'notifications.css' in index

    private = read('private-git-check.json')
    encoded = ('\0'.join(private['checked_paths']) + '\0').encode()
    ignored = subprocess.run(['git', 'check-ignore', '-z', '--stdin'], cwd=ROOT,
        input=encoded, capture_output=True, check=True).stdout.split(b'\0')
    assert len([item for item in ignored if item]) == len(private['checked_paths'])
    assert all(item['InheritanceDisabled'] for item in read('private-acl.json'))
    subprocess.run(['git', '-c', 'core.whitespace=cr-at-eol', 'diff', '--check'], cwd=ROOT, check=True)
    links = check_links()

    result = {'created_at': datetime.datetime.now().astimezone().isoformat(), 'result': 'PASS',
        'regression_tests': regressions['test_count'], 'product_and_test_sources_match_frozen_run': True,
        'research_tests': research['tests_run'], 'targeted_notification_tests': targeted,
        'source_revocation_tests': fence['tests'], 'browser_scenarios': browser_counts,
        'windows': {'version': windows['version'], 'sha256': windows['sha256'],
            'bytes': exe.stat().st_size, 'embedded_resources_match': True, 'signed_manifest_verified': True},
        'android': {'version': android['version'], 'version_code': android['versionCode'],
            'sha256': android['sha256'], 'bytes': apk.stat().st_size,
            'certificate_sha256': android['certificate_sha256'], 'packaged_assets_match': True,
            'native_core_runs': android['native_core_runs'], 'native_udp_runs': android['native_udp_runs'],
            'webview_checks': android['webview_checks'], 'profile_preserved_upgrade': android['release_upgrade']},
        'live': {'model_processes_preserved': True, 'existing_data_settings_access_keys_preserved': True,
            'automatic_backups_preserved': True, 'model_loaded': True, 'maintenance_idle': True,
            'console_static_assets_http_200': static, 'connected_notifications_no_external_push': True},
        'private_paths_ignored': True, 'private_acl_protected': True,
        'documentation_links_existing': links, 'git_diff_check': 'PASS', 'contains_secret_values': False}
    (PROOFS / 'delivery-final-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'result': result['result'], 'tests': result['regression_tests'],
        'windows': windows['version'], 'android': android['version'], 'documentation_links': links}))


if __name__ == '__main__':
    main()
