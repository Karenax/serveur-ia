"""Summarize isolated RTX 4080 engine/cache/drafter trials, including failures."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('benchmark_analysis', HERE.parent / '2026-10-30-rtx3080/analyze.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def main():
    runs = {}
    for folder in [HERE / 'int8-cache1', *sorted(HERE.glob('v015[46]-*'))]:
        if not (folder / 'final.json').exists():
            continue
        summary = analysis.summarize(folder)
        rows = analysis.read(folder / 'results.json') if (folder / 'results.json').exists() else []
        summary['long_context'] = [r for r in rows if r['label'] == 'long-context']
        summary['request_count'] = len(rows)
        summary['generation_rates'] = [r['timings']['predicted_per_second'] for r in rows if r['label'].startswith('decode-')]
        runs[folder.name] = summary
    baseline = runs['int8-cache1']['groups']
    for run in runs.values():
        run['change_percent'] = {
            key: 100 * (group['median_tokens_per_second'] / baseline[key]['median_tokens_per_second'] - 1)
            for key, group in run['groups'].items()
        }
    (HERE / 'trials-comparison.json').write_text(json.dumps(runs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name, run in runs.items():
        print(json.dumps({'run': name, 'error': run['final']['error'], 'checks_pass': run['all_quality_checks_pass'],
                          'profiles_unchanged': run['final']['fingerprints_identical'], 'groups': run['groups'],
                          'generation_rates': run['generation_rates'], 'change_percent': run['change_percent']}, ensure_ascii=True))


if __name__ == '__main__':
    main()
