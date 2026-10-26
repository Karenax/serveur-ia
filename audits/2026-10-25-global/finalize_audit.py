"""Validate audit links and record the final read-only workspace state."""
from pathlib import Path
import datetime, hashlib, json, re, subprocess
import psutil

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
expected = [
 ' M .agents/skills/frontend-human-centered/SKILL.md',
 ' M .agents/skills/professional-ui-design/SKILL.md',
 ' M .agents/skills/ux-consistency-review/SKILL.md',
 ' M .agents/skills/ux-writing-cleaner/SKILL.md',
 ' M AGENTS.md',
 ' M Certificat-NAS-karenax-20261006.md',
 ' M Configuration-Cloudflare-karenax-20261006.md',
 ' M preuves/model-picker-fix-20261011/selector-windows.png',
 ' M preuves/reasoning-models-20261011/reasoning-windows.png',
 '?? analyses/2026-10-24-deepseek/',
 '?? maintenance/2026-10-24-bolt-cpu/',
 '?? maintenance/2026-10-24-diagnostic-disque/',
 '?? maintenance/2026-10-25-assistant-integration/avant/',
]
bad_links = []
links_checked = 0
documents = []
for path in OUT.glob('*.md'):
    content = path.read_text(encoding='utf-8').replace('</D:/', '<D:/')
    path.write_text(content, encoding='utf-8')
    for target in re.findall(r'\]\(<([^>]+)>\)', content):
        if target.startswith('D:/'):
            links_checked += 1
            name = re.sub(r':\d+$', '', target)
            linked = Path(name)
            if not linked.exists():
                bad_links.append({'document': path.name, 'target': target})
            elif target != name:
                line = int(target.rsplit(':', 1)[1])
                if line > len(linked.read_text(encoding='utf-8-sig').splitlines()):
                    bad_links.append({'document': path.name, 'target': target, 'reason': 'line outside file'})
    documents.append({'path': path.name, 'words': len(content.split()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
status = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT).decode('utf-8').splitlines()
observed_without_audit = [line for line in status if line != '?? audits/2026-10-25-global/']
ports = {51872, 51873, 8875}
listeners = [{'port': c.laddr.port, 'pid': c.pid} for c in psutil.net_connections(kind='tcp')
             if c.status == psutil.CONN_LISTEN and c.laddr.port in ports]
report = {
 'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
 'git_status': status,
 'preexisting_status_preserved': sorted(observed_without_audit) == sorted(expected),
 'audit_fixture_listeners_remaining': listeners,
 'local_links_checked': links_checked,
 'invalid_links': bad_links,
 'documents': documents,
 'test_counts': {'python_server': 568, 'python_windows': 87, 'python_voice': 38,
                 'python_android': 13, 'go_tests': 1, 'ui_suites': 15},
 'findings': {'P0': 0, 'P1': 2, 'P2': 13, 'P3': 2},
 'application_changes_made': False,
}
(OUT/'final-state.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
if bad_links or listeners or not report['preexisting_status_preserved']:
    raise SystemExit(1)
