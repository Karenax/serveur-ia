"""Compare the measured RTX 4080 configurations with zero, one and two P100s."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'no-p100'
spec = importlib.util.spec_from_file_location('benchmark_analysis', HERE.parent / '2026-10-30-rtx3080/analyze.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def main():
    folders = {'zero': OUT / 'trial', 'one': HERE / 'default-mode/one-p100', 'two': HERE / 'default-mode/two-p100'}
    arms = {}
    for name, folder in folders.items():
        summary = analysis.summarize(folder)
        summary['engine'] = analysis.read(folder / 'metrics.json')['engine']
        summary['long_context'] = [r for r in analysis.read(folder / 'results.json') if r['label'] == 'long-context']
        arms[name] = summary
    cfg = analysis.read(folders['zero'] / 'config.json')
    assert cfg['env']['CUDA_VISIBLE_DEVICES'] == 'GPU-7d35736d-3ef5-1304-0e9e-1d26021be1a0'
    assert '--remote-expert-opt' not in cfg['args']
    assert not any(flag.startswith('--expert-cache-device') for flag in cfg['args'])
    for uuid in ['GPU-a39f1b57-5a26-b53d-e943-44ef8042a438', 'GPU-486d5352-582e-2880-78bf-3dec4688e142']:
        assert arms['zero']['gpus'][uuid]['max_vram_mib'] == 9
    comparisons = {}
    for group in arms['two']['groups']:
        rates = {name: arm['groups'][group]['median_tokens_per_second'] for name, arm in arms.items()}
        comparisons[group] = {'rates': rates, 'zero_vs_two_percent': 100 * (rates['zero'] / rates['two'] - 1),
                              'zero_vs_one_percent': 100 * (rates['zero'] / rates['one'] - 1),
                              'two_vs_zero_gain_percent': 100 * (rates['two'] / rates['zero'] - 1)}
    result = {'arms': arms, 'comparisons': comparisons,
              'scope': 'Same RTX primary, model, drafter and CPU workers; automatic expert placement is recomputed for each available GPU set. No model split porting.'}
    (OUT / 'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'comparison': comparisons, 'expert_ram_gib': {k: a['engine']['arena_mib'] / 1024 for k, a in arms.items()}}, indent=2))


if __name__ == '__main__':
    main()
