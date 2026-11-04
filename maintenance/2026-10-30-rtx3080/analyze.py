"""Summarize the paired raw engine timings and GPU observations."""
import json
from pathlib import Path
import statistics
import argparse

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def summarize(folder):
    records = read(folder / 'results.json') if (folder / 'results.json').exists() else []
    telemetry = read(folder / 'telemetry.json')
    groups = {}
    for kind in ('decode', 'prefill-64', 'prefill-256'):
        rows = [row for row in records if row['label'].startswith(kind + '-r')]
        if not rows:
            continue
        metric = 'predicted_per_second' if kind == 'decode' else 'prompt_per_second'
        duration = 'predicted_ms' if kind == 'decode' else 'prompt_ms'
        groups[kind] = {'repeats': len(rows), 'median_tokens_per_second': statistics.median(row['timings'][metric] for row in rows),
                        'median_ms': statistics.median(row['timings'][duration] for row in rows),
                        'prompt_tokens': [row['timings']['prompt_n'] for row in rows],
                        'generated_tokens': [row['timings']['predicted_n'] for row in rows]}
    gpus = {}
    for sample in telemetry:
        if sample.get('phase') in ('loading', 'between') or not sample.get('gpu_csv'):
            continue
        for line in sample['gpu_csv'].splitlines():
            cells = [cell.strip() for cell in line.split(',')]
            index, uuid, name, vram, temp, util, clock, power, mask = cells
            item = gpus.setdefault(uuid, {'name': name, 'max_temp_c': 0, 'max_vram_mib': 0, 'max_utilization': 0,
                                          'thermal_throttle_samples': 0, 'sm_mhz': []})
            item['max_temp_c'] = max(item['max_temp_c'], float(temp))
            item['max_vram_mib'] = max(item['max_vram_mib'], float(vram))
            item['max_utilization'] = max(item['max_utilization'], float(util))
            item['thermal_throttle_samples'] += bool(int(mask, 16) & 0x60)
            item['sm_mhz'].append(float(clock))
    for item in gpus.values():
        item['median_sm_mhz'] = statistics.median(item.pop('sm_mhz'))
    return {'path': str(folder), 'groups': groups, 'gpus': gpus,
            'all_quality_checks_pass': bool(records) and all(row['quality_pass'] for row in records),
            'cache_tokens': [row['timings'].get('cache_n', 0) for row in records], 'final': read(folder / 'final.json')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--p100-run', default='p100-ctx8192-f-ssd')
    parser.add_argument('--rtx-run', default='rtx3080-ctx8192-f-ssd-latest')
    options = parser.parse_args()
    arms = {'p100': summarize(HERE / options.p100_run),
            'rtx3080': summarize(HERE / options.rtx_run)}
    comparison = {}
    for kind in arms['p100']['groups']:
        if kind not in arms['rtx3080']['groups']:
            comparison[kind] = {'available': False, 'reason': 'RTX3080 engine exited at first cuBLAS product; no tokens produced.'}
            continue
        before = arms['p100']['groups'][kind]['median_tokens_per_second']
        after = arms['rtx3080']['groups'][kind]['median_tokens_per_second']
        comparison[kind] = {'p100_tokens_per_second': before, 'rtx3080_tokens_per_second': after,
                            'throughput_ratio': after / before, 'throughput_change_percent': 100 * (after / before - 1)}
    attempts = {p.name: read(p / 'final.json') for p in sorted(HERE.glob('rtx3080-*')) if (p / 'final.json').exists()}
    result = {'arms': arms, 'comparison': comparison, 'rtx3080_attempts': attempts}
    (HERE / 'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
