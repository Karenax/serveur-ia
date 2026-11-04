"""Compare throughput and total RTX memory for isolated candidates."""
import json
from pathlib import Path
import statistics
import csv
import io

HERE = Path(__file__).resolve().parent
OUT = HERE / 'optimisation-vram-20261031'
RTX = 'GPU-c7ec5bca-5502-9e99-2ede-30270b7bde2f'


def rtx_capacity():
    path = OUT / 'memory-layout.csv'
    if path.exists():
        for row in list(csv.reader(io.StringIO(path.read_text(encoding='utf-8-sig'))))[1:]:
            if row[0].strip() == RTX:
                return float(row[1].split()[0]) - float(row[2].split()[0])
    raise FileNotFoundError('Capture memory.total and memory.reserved before estimating free VRAM')


def read(path, default=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default


def summarize(folder):
    records = read(folder / 'results.json', [])
    final = read(folder / 'final.json', {})
    vram = []
    temperatures = []
    throttle = 0
    samples = read(folder / 'telemetry.json', [])
    samples += [{'gpu_csv': row.get('gpu_after', '')} for row in records]
    for sample in samples:
        if sample.get('phase') == 'loading':
            continue
        for line in sample.get('gpu_csv', '').splitlines():
            cells = [cell.strip() for cell in line.split(',')]
            if len(cells) != 9 or cells[1] != RTX:
                continue
            vram.append(float(cells[3]))
            temperatures.append(float(cells[4]))
            throttle += bool(int(cells[8], 16) & 0x60)
    groups = {}
    for kind, field in [('decode', 'predicted_per_second'), ('prefill-64', 'prompt_per_second'),
                        ('prefill-256', 'prompt_per_second')]:
        values = [row['timings'][field] for row in records if row['label'].startswith(kind + '-r')]
        if values:
            groups[kind] = statistics.median(values)
    vision = next((row['content'].lower() for row in records if row['label'] == 'vision'), '')
    quality = bool(records) and all(row['quality_pass'] for row in records)
    quality &= '47' in vision and ('cercle' in vision or 'rond' in vision) and ('carré' in vision or 'carre' in vision)
    return {'folder': folder.name, 'throughput': groups, 'quality_passed': quality,
            'error': final.get('error', 'not_finished'), 'profiles_unchanged': final.get('fingerprints_identical'),
            'peak_rtx_total_used_mib': max(vram) if vram else None,
            'min_rtx_free_mib': rtx_capacity() - max(vram) if vram else None,
            'max_temp_c': max(temperatures) if temperatures else None,
            'thermal_throttle_samples': throttle,
            'cache_tokens': [row['timings'].get('cache_n', 0) for row in records]}


def main():
    folders = [*HERE.glob('rtx3080-ctx262144-opt2-*'), *HERE.glob('rtx3080-ctx262144-opt3-*')]
    rows = [summarize(folder) for folder in sorted(folders)]
    baseline = next(row for row in rows if row['folder'].endswith('opt2-ref-fp16'))
    for row in rows:
        row['change_percent'] = {kind: 100 * (value / baseline['throughput'][kind] - 1)
                                 for kind, value in row['throughput'].items() if kind in baseline['throughput']}
        if row['min_rtx_free_mib'] is not None and baseline['min_rtx_free_mib'] is not None:
            row['extra_headroom_mib'] = row['min_rtx_free_mib'] - baseline['min_rtx_free_mib']
    (OUT / 'comparison.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(rows, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
