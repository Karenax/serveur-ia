"""Compare dense RTX 4080 with either one or two P100 expert helpers."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'default-mode'
spec = importlib.util.spec_from_file_location('benchmark_analysis', HERE.parent / '2026-10-30-rtx3080/analyze.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def main():
    arms = {}
    for name, expected_gpu_count in [('two-p100', 3), ('one-p100', 2)]:
        folder = OUT / name
        cfg = analysis.read(folder / 'config.json')
        assert len(cfg['env']['CUDA_VISIBLE_DEVICES'].split(',')) == expected_gpu_count
        assert '--layer-split' not in cfg['args']
        assert ('--expert-cache-device2' in cfg['args']) == (expected_gpu_count == 3)
        summary = analysis.summarize(folder)
        summary['engine'] = analysis.read(folder / 'metrics.json')['engine']
        summary['long_context'] = [r for r in analysis.read(folder / 'results.json') if r['label'] == 'long-context']
        arms[name] = summary
    comparison = {}
    for label, before in arms['two-p100']['groups'].items():
        after = arms['one-p100']['groups'][label]
        first, last = before['median_tokens_per_second'], after['median_tokens_per_second']
        comparison[label] = {'two_p100_tokens_per_second': first, 'one_p100_tokens_per_second': last,
                             'change_percent': 100 * (last / first - 1)}
    result = {'arms': arms, 'comparison': comparison,
              'scope': 'Same dense RTX primary, automatic helper caches; excluded P100 experts remain in locked host RAM. The surviving helper gets its automatically recomputed ranked expert set.'}
    (OUT / 'p100-comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'comparison': comparison, 'engine': {k: v['engine'] for k, v in arms.items()}}, indent=2))


if __name__ == '__main__':
    main()
