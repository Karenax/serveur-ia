from pathlib import Path
import hashlib
import json
import statistics
import subprocess

root = Path(__file__).resolve().parent
repo = root / 'Strata-src'
public = repo / 'bench/results/2026-10-02-p100-resident-hybrid'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

for relative in (
    'comparatifs/2026-10-02-cafe-q4-p100/manifest.json',
    'comparatifs/2026-10-02-strata-q4-p100/manifest-final.json',
    'comparatifs/2026-10-02-strata-hybride-p100/manifest-sha256.json',
    'analyses/2026-10-02-goulots/manifest-sha256.json',
):
    manifest = root / relative
    value = json.loads(manifest.read_text(encoding='utf-8-sig'))
    entries = value.get('files', value)
    if isinstance(entries, list):
        entries = {record.get('path', record.get('name')): record for record in entries}
    checked = 0
    for name, record in entries.items():
        if not isinstance(record, dict) or 'sha256' not in record:
            continue
        path = manifest.parent / name
        assert path.stat().st_size == record['bytes'], path
        assert digest(path) == record['sha256'].lower(), path
        checked += 1
    assert checked > 0, manifest
    print(f'Unchanged archive: {manifest.parent.name}: {checked} files', flush=True)

runs = json.loads((public / 'runs.json').read_text(encoding='utf-8'))
summary = json.loads((public / 'summary.json').read_text(encoding='utf-8'))['summary']
assert len(runs) == 16
assert all(row['output_tokens'] == 256 for row in runs)
for row in summary:
    group = [r for r in runs if r['pcie_frac'] == row['pcie_frac'] and r['test'] == row['test']]
    assert len(group) == 2
    assert statistics.median(r['generation_tps'] for r in group) == row['generation_tps']
patch = subprocess.check_output(['git', 'show', '--format=', 'HEAD'], cwd=repo).decode('utf-8')
for private in ('D:/Serveur IA', 'D:\\Serveur IA', 'C:\\Users\\karen', 'GPU-a39f1b57', 'GPU-486d5352', 'karenax@outlook.com'):
    assert private not in patch, private
print('Verified all medians, 16 fixed-length requests and private-path exclusion', flush=True)
