"""Compare this RTX 4080 run with the recorded RTX 3080 INT8 reference."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / '2026-10-30-rtx3080'
spec = importlib.util.spec_from_file_location('gpu_benchmark_analysis', PREVIOUS / 'analyze.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def compute_options(arguments):
    options = {}
    index = 0
    while index < len(arguments):
        name = arguments[index]
        index += 1
        value = None
        if index < len(arguments) and not arguments[index].startswith('--'):
            value = arguments[index]
            index += 1
        if name != '--vision':
            options[name] = value
    return options


def main():
    reference = PREVIOUS / 'rtx3080-ctx262144-opt3-int8-p2048-cache1'
    current = HERE / 'int8-cache1'
    arms = {'rtx3080': analysis.summarize(reference), 'rtx4080': analysis.summarize(current)}
    comparison = {}
    for kind, before in arms['rtx3080']['groups'].items():
        after = arms['rtx4080']['groups'].get(kind)
        if after:
            first = before['median_tokens_per_second']
            last = after['median_tokens_per_second']
            comparison[kind] = {'rtx3080_tokens_per_second': first,
                                'rtx4080_tokens_per_second': last,
                                'change_percent': 100 * (last / first - 1)}
    configs = {name: analysis.read(folder / 'config.json')
               for name, folder in [('rtx3080', reference), ('rtx4080', current)]}
    rows = analysis.read(current / 'results.json')
    result = {
        'comparison': comparison,
        'same_engine_binary': analysis.read(reference / 'before.json')['engine_sha256']
                              == analysis.read(current / 'before.json')['engine_sha256'],
        'same_compute_arguments': compute_options(configs['rtx3080']['args'])
                                  == compute_options(configs['rtx4080']['args']),
        'limits': ['Historical reference, not a simultaneous hardware comparison.',
                   'Vision disabled on RTX 4080; enabled in the historical reference.',
                   'Three decode and two prefill repetitions per length.',
                   'Maximum configured context is not a full-context stress test.',
                   'Primary expert cache remains limited to one entry.'],
        'long_context': [r for r in rows if r['label'] == 'long-context'],
        'arms': arms,
    }
    (HERE / 'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'arms'}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
