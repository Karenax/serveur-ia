"""Check local links and release identities in the current documentation corpus."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DOCUMENTS = (
    'README.md', 'ARCHITECTURE-ACTUELLE.md', 'RECONSTRUIRE-FRED.md',
    'CONTEXTE-PROJET.md', 'ARCHIVES-ET-PREUVES.md', 'GUIDE-ASSISTANT-KIARA.md',
    'LISEZ-MOI.txt', 'client-qwen/LISEZ-MOI.txt', 'client-android/README.md',
    'client-linux/README.md', 'client-voice/README.md', 'client-voice/COMPATIBILITE.md',
    'client-voice/CONVERSATION-WINDOWS.md', 'shared/README.md',
    'lanceur/LISEZ-MOI.txt', 'lanceur/HERMES-FRED.md', 'lanceur/ESPACES-FRED.txt',
    'lanceur/RECHERCHE-NOTIFICATIONS.md', 'PLAN-INTEGRATION-ASSISTANT-KIARA.md',
    'lanceur/SAUVEGARDES-APPAREILS.md',
    'PLAN-GLOBAL-SERVEUR-FRED.md', 'PLAN-SAUVEGARDES-APPAREILS.md',
    'maintenance/codex/README.md', 'maintenance/2026-11-04-publication-windows/README.md',
)


def main():
    texts = {name: (ROOT / name).read_text(encoding='utf-8-sig') for name in DOCUMENTS}
    broken = []; checked = 0
    for name, text in texts.items():
        for match in re.finditer(r'(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)', text):
            target = match.group(1).split(' "', 1)[0].strip('<>')
            if re.match(r'^[a-zA-Z][\w+.-]*:', target) or target.startswith('#'): continue
            path = unquote(target.split('#', 1)[0])
            if not path: continue
            checked += 1
            if not ((ROOT / name).parent / path).exists():
                broken.append({'document': name, 'target': target})
    version = re.search(r"VERSION = '([^']+)'", (ROOT / 'shared/kiara_shared/version.py').read_text())[1]
    release = json.loads((ROOT / 'client-qwen/dist/release.json').read_text())
    windows_manifest = json.loads((ROOT / 'client-qwen/dist/build-manifest.json').read_text())
    windows_drift = [name for name, wanted in windows_manifest['source_files'].items()
        if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != wanted]
    windows_digest = hashlib.sha256((ROOT / 'client-qwen/dist/Accès serveur Fred.exe').read_bytes()).hexdigest()
    android = json.loads((ROOT / 'client-android/dist/release.json').read_text())
    required = ('README.md', 'ARCHITECTURE-ACTUELLE.md', 'RECONSTRUIRE-FRED.md',
        'CONTEXTE-PROJET.md', 'GUIDE-ASSISTANT-KIARA.md', 'client-qwen/LISEZ-MOI.txt',
        'lanceur/LISEZ-MOI.txt', 'lanceur/HERMES-FRED.md', 'client-voice/COMPATIBILITE.md',
        'client-voice/CONVERSATION-WINDOWS.md')
    missing_versions = [name for name in required if version not in texts[name]]
    manifest = json.loads((ROOT / 'client-android/dist/build-manifest.json').read_text())
    android_drift = [name for name, wanted in manifest['source_files'].items()
        if (ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != wanted]
    result = {'passed': not broken and not missing_versions and not windows_drift
        and release['version'] == version and windows_digest == release['sha256'],
        'documents': list(DOCUMENTS), 'local_link_targets_checked': checked, 'broken_links': broken,
        'missing_current_version': missing_versions, 'windows_published': release['version'],
        'windows_source_drift': windows_drift, 'windows_binary_matches_release': windows_digest == release['sha256'],
        'android_published': {'version': android['version'], 'code': android['version_code']},
        'android_source_drift': android_drift,
        'limits': ['External URLs and Markdown anchors not checked.',
            'Historical reports retain their original versions and measurements.',
            'Documentation audit does not qualify physical microphone/camera or Linux hardware.',
            'Android APK and Linux archive were not rebuilt by this Windows publication.']}
    (OUT / 'documentation-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
