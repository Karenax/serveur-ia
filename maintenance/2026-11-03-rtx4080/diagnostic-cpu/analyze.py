"""Separate measured expert wait from conditional acceleration scenarios."""
import json
from pathlib import Path
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NUMBER = r'(-?[\d.]+)'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def summarize(folder):
    rows = read(folder / 'results.json')
    lines = (folder / 'engine.log').read_text(encoding='utf-8', errors='replace').splitlines()
    timing = [line for line in lines if line.startswith('strata decode timing:')]
    stages = [line for line in lines if line.startswith('strata decode GPU stages')]
    profiled = bool(timing)
    if profiled and (len(timing) != len(rows) or len(stages) != len(rows)):
        raise ValueError(f'Cannot pair timing lines with requests in {folder.name}')
    decode = []
    for index, row in enumerate(rows):
        if not row['label'].startswith('decode-'):
            continue
        item = {'label': row['label'], 'tokens_per_second': row['timings']['predicted_per_second'],
                'generated_tokens': row['timings']['predicted_n']}
        if profiled:
            line = timing[index]
            patterns = {'windows': r'timing: (\d+) windows', 'window_ms': NUMBER + r' ms/window =',
                        'tokens_per_window': NUMBER + r' tokens/window',
                        'cpu_experts_ms_per_window': r'jobs [\d.]+ CPU ' + NUMBER,
                        'host_per_window_ms': r'per-layer host ' + NUMBER,
                        'gpu_reach_wait_ms': r'GPU-reach wait ' + NUMBER}
            for name, pattern in patterns.items():
                match = re.search(pattern, line)
                if not match:
                    raise ValueError((name, line))
                item[name] = float(match.group(1))
            item['gpu_wait_cpu_ms_per_window'] = sum(float(n) for n in re.findall(r'waitCPU ' + NUMBER, stages[index]))
            item['gpu_wait_b_ms_per_window'] = sum(float(n) for n in re.findall(r'waitB ' + NUMBER, stages[index]))
            item['wait_fraction'] = item['gpu_wait_cpu_ms_per_window'] / item['window_ms']
            item['native_host_timing'] = line
            item['native_gpu_timing'] = stages[index]
        decode.append(item)
    metrics = read(folder / 'metrics.json') if (folder / 'metrics.json').exists() else {}
    result = {'median_tokens_per_second': statistics.median(r['tokens_per_second'] for r in decode),
              'decode': decode, 'engine': metrics.get('engine'), 'final': read(folder / 'final.json'),
              'all_targeted_checks_pass': all(r['quality_pass'] for r in rows),
              'all_cache_tokens_zero': all(not r['timings'].get('cache_n', 0) for r in rows)}
    if profiled:
        total = sum(r['window_ms'] * r['windows'] for r in decode)
        wait = sum(r['gpu_wait_cpu_ms_per_window'] * r['windows'] for r in decode)
        result['weighted_gpu_wait_cpu_fraction'] = wait / total
    return result


def capacity():
    sys.path.insert(0, str(ROOT / 'Strata-src/tools'))
    from gguf_reader import GGUFFile
    files = [GGUFFile(path) for path in sorted(Path('F:/').glob('Qwen3.8-Flash-Next-Uncensored-IQ4_XS-*.gguf'))]
    tensors = [t for f in files for t in f.tensors if t.name.endswith('_exps.weight')]
    expert_bytes = sum(t.expected_bytes() for t in tensors)
    return {'expert_tensors': len(tensors), 'expert_bytes': expert_bytes, 'expert_gib': expert_bytes / 2**30,
            'v100_datasheet': 'https://images.nvidia.com/content/tesla/pdf/Tesla-V100-PCIe-Product-Brief.pdf',
            'scope': 'Routed expert weights only; dense, context and runtime buffers are separate.'}


def main():
    runs = {p.name: summarize(p) for p in sorted(HERE.iterdir()) if p.is_dir() and (p / 'final.json').exists()
            and (p / 'results.json').exists()}
    result = {'runs': runs, 'capacity': capacity()}
    baseline = runs.get('w15-profile')
    if baseline:
        fraction = baseline['weighted_gpu_wait_cpu_fraction']
        rate = baseline['median_tokens_per_second']
        result['conditional_scenarios'] = [
            {'net_fraction_of_wait_removed': removal, 'speed_ratio': 1 / (1 - fraction * removal),
             'tokens_per_second_at_profiled_baseline': rate / (1 - fraction * removal)}
            for removal in (0.25, 0.5, 0.75, 1.0)]
        result['scenario_limit'] = ('Not a V100 benchmark or a prediction: a net reduction of measured waiting after '
                                   'accounting for replacement GPU work, transfers, scheduling and changed token paths.')
        slots = baseline['engine']['expert_slots']
        primary = baseline['engine']['expert_slots_primary']
        total_slots = 48 * 512
        bytes_per_slot = result['capacity']['expert_bytes'] // total_slots
        remaining = total_slots - slots
        candidates = total_slots - primary
        # With every helper set to auto, Strata first divides the candidate list
        # into three equal stripes, then each helper clamps to its own free VRAM.
        # A larger third helper therefore receives too few candidates.
        small_capacity = (slots - primary) // 2
        stripes = [candidates // 3 + (i < candidates % 3) for i in range(3)]
        all_auto_resident = primary + min(small_capacity, stripes[0]) + min(small_capacity, stripes[1]) + stripes[2]
        result['capacity'].update({
            'bytes_per_layer_expert': bytes_per_slot, 'total_layer_expert_pairs': total_slots,
            'current_resident_pairs': slots, 'current_primary_pairs': primary,
            'current_missing_pairs': remaining, 'current_missing_gib': remaining * bytes_per_slot / 2**30,
            'v100_16gb_assumed_expert_budget_gib': 14,
            'v100_16gb_remaining_gib_at_that_budget': max(0, remaining * bytes_per_slot / 2**30 - 14),
            'v100_32gb_assumed_expert_budget_gib': 30,
            'v100_32gb_capacity_margin_gib_at_that_budget': 30 - remaining * bytes_per_slot / 2**30,
            'three_auto_helpers_simulated_missing_gib': (total_slots - all_auto_resident) * bytes_per_slot / 2**30,
            'explicit_existing_helper_caps_example': [6000, 6000],
            'v100_needed_pairs_after_explicit_caps': total_slots - primary - 12000,
            'v100_needed_gib_after_explicit_caps': (total_slots - primary - 12000) * bytes_per_slot / 2**30,
            'placement_scope': 'Configuration simulation based on v0.2.10 generate.cpp; not a physical V100 allocation test.'})
    (HERE / 'analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'runs': {k: {'tokens_per_second': r['median_tokens_per_second'],
                                  'gpu_wait_cpu_fraction': r.get('weighted_gpu_wait_cpu_fraction'),
                                  'quality_pass': r['all_targeted_checks_pass']} for k, r in runs.items()},
                      'capacity': result['capacity'], 'scenarios': result.get('conditional_scenarios')}, indent=2))


if __name__ == '__main__':
    main()
