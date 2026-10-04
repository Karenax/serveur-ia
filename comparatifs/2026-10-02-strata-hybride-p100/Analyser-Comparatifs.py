"""Consolide les mesures brutes, sans mélanger échecs et essais réussis."""
import csv
import datetime as dt
import json
from pathlib import Path
import statistics as stats

ROOT = Path(__file__).resolve().parent
DEST = ROOT / 'comparatifs'
SOURCES = [
    ('cafe-sans-mtp', '2026-10-02-cafe-q4-p100', 'resultats-sans-mtp.csv'),
    ('cafe-mtp', '2026-10-02-cafe-q4-p100', 'resultats-mtp.csv'),
    ('strata-mtp-hybride', '2026-10-02-strata-q4-p100/essai-hybride-staging16', 'resultats-strata-mtp.csv'),
    ('strata-mtp-gpu-seul', '2026-10-02-strata-q4-p100', 'resultats-strata-mtp.csv'),
]

def number(value):
    return float(value.replace(',', '.')) if value and value != 'N/A' else None

rows = []
resources = {}
for mode, directory, filename in SOURCES:
    source = DEST / directory / filename
    if not source.exists():
        continue
    with source.open(encoding='utf-8-sig', newline='') as stream:
        for raw in csv.DictReader(stream):
            row = {k: number(raw.get(k)) for k in (
                'test', 'elapsed_seconds', 'prompt_tokens', 'output_tokens',
                'prompt_tps', 'generation_tps', 'draft_tokens', 'draft_accepted', 'draft_acceptance')}
            row.update(mode=mode, source=str(source), finish_reason=raw['finish_reason'])
            rows.append(row)
    measured_mode = 'strata-mtp' if mode.startswith('strata-') else mode.removeprefix('cafe-')
    telemetry = DEST / directory / f'mesures-{measured_mode}.csv'
    if not telemetry.exists():
        continue
    with telemetry.open(encoding='utf-8-sig', newline='') as stream:
        samples = list(csv.DictReader(stream))
    if not samples:
        continue
    selected = [r for r in samples if r['gpu_index'] in ('1', '2')]
    first, last = samples[0], samples[-1]
    seconds = (dt.datetime.fromisoformat(last['time']) - dt.datetime.fromisoformat(first['time'])).total_seconds()
    resources[mode] = {
        'samples_gpu': len(selected),
        'vram_peak_mib': {gpu: max(number(r['vram_mib']) for r in selected if r['gpu_index'] == gpu) for gpu in ('1', '2')},
        'gpu_mean_util_pct': {gpu: sum(number(r['gpu_util_pct']) for r in selected if r['gpu_index'] == gpu) / sum(r['gpu_index'] == gpu for r in selected) for gpu in ('1', '2')},
        'ram_peak_gib': max(number(r['server_ram_bytes']) for r in samples) / (1024**3),
        'cpu_equivalent_cores': (number(last['server_cpu_seconds']) - number(first['server_cpu_seconds'])) / seconds if seconds else None,
        'process_io_read_peak_bytes_s': max(number(r['io_read_bytes_per_sec']) or 0 for r in samples),
        'disk_d_read_peak_bytes_s': max(number(r.get('disk_d_read_bytes_per_sec')) or 0 for r in samples) if 'disk_d_read_bytes_per_sec' in first else None,
        'telemetry_seconds': seconds,
    }

hybrid_summary = DEST / '2026-10-02-strata-hybride-p100' / 'synthese.json'
if hybrid_summary.exists():
    consolidated = json.loads(hybrid_summary.read_text(encoding='utf-8'))
    run = Path(consolidated['run'])
    raw_runs = json.loads((run/'resultats.json').read_text(encoding='utf-8'))
    for s in consolidated['summary']:
        frac, test = s['pcie_frac'], s['test']
        mode = f'strata-mtp-cpu16-pcie{frac:g}'
        selected = [r for r in raw_runs if r['pcie_frac']==frac and r['test']==test]
        answer = json.loads((run/f'r1-pcie{frac:g}-test{test}-reponse.json').read_text(encoding='utf-8'))
        rows.append(dict(mode=mode,test=test,elapsed_seconds=s['elapsed_seconds'],
            prompt_tokens=answer['usage']['prompt_tokens'],output_tokens=answer['usage']['completion_tokens'],
            prompt_tps=s['prompt_tps'],generation_tps=s['generation_tps'],
            draft_tokens=stats.median(r['drafts'] for r in selected),
            draft_accepted=stats.median(r['accepted'] for r in selected),draft_acceptance=s['draft_acceptance'],
            finish_reason=answer['choices'][0]['finish_reason'],source=str(run/'resultats.csv')))
        resource = resources.setdefault(mode,dict(pcie_frac=frac,pool_workers=15,host_worker=True,
            repeats=s['repeats'],aggregation='median per prompt',tests={},
            vram_note='Même allocation de caches pour les quatre réglages; VRAM non échantillonnée pendant cette série.'))
        resource['tests'][str(test)] = dict(ram_peak_gib=s['ram_peak_bytes']/1024**3,
            cpu_equivalent_cores=s['cpu_average_cores'],cpu_expert_jobs=s['cpu_expert_jobs'],
            ram_gpu_experts=s['ram_gpu_experts'],expert_file_reads=0)

fields = ['mode', 'test', 'elapsed_seconds', 'prompt_tokens', 'output_tokens', 'prompt_tps',
          'generation_tps', 'draft_tokens', 'draft_accepted', 'draft_acceptance', 'finish_reason', 'source']
with (DEST / 'comparatif-q4-p100.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
(DEST / 'ressources-q4-p100.json').write_text(json.dumps(resources, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'results': rows, 'resources': resources}, ensure_ascii=False, indent=2))
