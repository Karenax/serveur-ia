"""Synthèse reproductible des microtests et des deux requêtes de référence."""
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics as stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def medians(filename, keys, values):
    grouped={}
    with (HERE/filename).open(encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            key=tuple(row[k] for k in keys)
            grouped.setdefault(key,[]).append(row)
    return [dict(zip(keys,key),**{v:stats.median(float(r[v]) for r in rows) for v in values})
            for key,rows in grouped.items()]
bandwidth=medians('bandwidth.csv',['kind','device','threads','bytes_per_op'],['GB_s'])
copies=medians('kernel-copy.csv',['kind','device','experts'],['GB_s'])
cpu=medians('cpu-experts.csv',['gu_type','down_type','tokens_per_expert','threads'],['experts_s','logical_weight_GB_s'])
pool=medians('cpu-pool.csv',['threads_including_host','tokens_per_expert','jobs_per_batch'],['experts_s','logical_weight_GB_s'])
ram=medians('ram-affinite.csv',['kind','threads','affinity'],['GB_s'])
ram_spread=medians('ram-affinite-repartie.csv',['kind','threads','affinity'],['GB_s'])
layer_bytes=[int(line.split()[4]) for line in (ROOT/'strata-data/q4-local/native_experts.txt').read_text().splitlines()
             if line and not line.startswith('#')]
fetch_rate=stats.median(r['GB_s'] for r in copies if r['kind']=='Strata_fetch_kernel')
reference=HERE/'inference-20261002-184822'
inference=json.loads((reference/'resultats.json').read_text())
for row in inference:
    log=(reference/f"engine-{row['test']}.log").read_text()
    jobs,count=map(int,re.search(r'decode expert compute: (\d+) CPU jobs, (\d+) RAM-to-GPU experts',log).groups())
    t=row['timings']; sec=t['predicted_ms']/1000; tokens=t['predicted_n']
    row.update(cpu_expert_jobs=jobs,ram_gpu_experts=count,generation_tps=tokens/sec,
        ram_gpu_experts_per_output_token=count/tokens,ram_gpu_experts_per_second=count/sec,
        logical_weight_bytes_min=count*min(layer_bytes),
        logical_weight_bytes_mean_estimate=count*stats.mean(layer_bytes),
        logical_weight_bytes_max=count*max(layer_bytes),
        logical_weight_GB_per_token_min=count*min(layer_bytes)/tokens/1e9,
        logical_weight_GB_per_token_mean_estimate=count*stats.mean(layer_bytes)/tokens/1e9,
        copy_ms_per_token_min_estimate=count*min(layer_bytes)/tokens/fetch_rate/1e6,
        copy_time_fraction_min_estimate=count*min(layer_bytes)/fetch_rate/1e9/sec,
        draft_acceptance=t['draft_n_accepted']/t['draft_n'])
summary=dict(units='GB/s = 10^9 bytes/s; GiB = 2^30 bytes',
    caveats=['La bande passante RAM dépend du test et de l’affinité; elle n’est pas le débit maximal garanti des DIMM.',
             'La durée des copies est estimée à partir de comptes logiciels et de microtests, sans profilage CUDA des phases.',
             'Les compteurs PCIe NVML ont des pointes physiquement impossibles: les volumes intégrés ne sont pas retenus comme mesures exactes.',
             'Le test CPU utilise les vrais kernels Strata mais des poids synthétiques et des lots plus grands que l’inférence.'],
    theoretical_DDR4_3200_eight_channels_GB_s=204.8,layer_blob_bytes=dict(min=min(layer_bytes),mean=stats.mean(layer_bytes),max=max(layer_bytes)),
    bandwidth=bandwidth,kernel_copies=copies,cpu_experts=cpu,cpu_pool=pool,ram_affinity=ram,ram_spread=ram_spread,
    reference_inference=inference)
(HERE/'mesures-synthetisees.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
for row in inference:
    print({k:row[k] for k in ('test','generation_tps','ram_gpu_experts','ram_gpu_experts_per_output_token',
        'ram_gpu_experts_per_second','logical_weight_GB_per_token_min','copy_ms_per_token_min_estimate','copy_time_fraction_min_estimate')})
print('fetch median GB/s',fetch_rate)
for row in pool: print(row)

def manifest(folder):
    result={}
    for path in sorted(folder.rglob('*')):
        if path.is_file() and path.name!='manifest-sha256.json' and '__pycache__' not in path.parts:
            result[str(path.relative_to(folder)).replace('\\','/')]=dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (folder/'manifest-sha256.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
manifest(HERE)
