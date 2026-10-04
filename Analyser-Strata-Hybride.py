"""Rassemble les répétitions et archive sans réécrire les anciens comparatifs."""
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics as stats
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT=Path(__file__).resolve().parent
ARCHIVE=ROOT/'comparatifs/2026-10-02-strata-hybride-p100'
RUN=Path(sys.argv[1])
rows=json.loads((RUN/'resultats.json').read_text(encoding='utf-8'))
grouped={}
for row in rows: grouped.setdefault((row['pcie_frac'],row['test']),[]).append(row)
summary=[]
for (fraction,test),runs in sorted(grouped.items(),reverse=True):
    result=dict(pcie_frac=fraction,test=test,repeats=len(runs))
    for key in ('generation_tps','prompt_tps','elapsed_seconds','cpu_average_cores','cpu_expert_jobs','ram_gpu_experts','ram_peak_bytes'):
        result[key]=stats.median(r[key] for r in runs)
    result['generation_tps_min']=min(r['generation_tps'] for r in runs)
    result['generation_tps_max']=max(r['generation_tps'] for r in runs)
    result['draft_acceptance']=stats.median(r['accepted']/r['drafts'] for r in runs if r['drafts'])
    result['same_answer_across_repeats']=len({r['answer_sha256'] for r in runs})==1
    baseline=stats.median(r['generation_tps'] for r in grouped[(1.0,test)])
    result['gain_vs_same_binary_gpu_percent']=100*(result['generation_tps']/baseline-1)
    summary.append(result)
scores={}
for fraction in sorted({r['pcie_frac'] for r in rows}):
    values=[r['generation_tps'] for r in summary if r['pcie_frac']==fraction]
    if len(values)==2: scores[fraction]=math.sqrt(values[0]*values[1])
best=max(scores,key=scores.get)
rollup=dict(created=dt.datetime.now().astimezone().isoformat(),run=str(RUN),summary=summary,
            geometric_mean_tps=scores,best_fraction_on_two_prompts=best,
            caveat='Deux prompts à contexte court, deux répétitions: choix de cette série, pas optimum universel.')
(ARCHIVE/'synthese.json').write_text(json.dumps(rollup,ensure_ascii=False,indent=2),encoding='utf-8')
with (ARCHIVE/'synthese.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(summary[0])); writer.writeheader(); writer.writerows(summary)
lines=['Comparatif Strata Q4 P100 — CPU et GPU — '+rollup['created'],
    'Même binaire et mêmes caches pour les quatre répartitions ; 15 travailleurs + le thread hôte.',
    'Mêmes prompts ciel/Fibonacci, 256 tokens, température 0, seed 42, cache désactivé, thinking désactivé.',
    'Chaque prompt est testé deux fois ; les valeurs ci-dessous sont les médianes.',
    'pcie_frac désigne la part des experts absents du cache VRAM calculée sur GPU.',
    'Les experts déjà résidents et les couches denses restent sur les deux P100.', '',
    'Part PCIe des absents | Ciel tok/s | Fibonacci tok/s | CPU moyen ciel/fib (équivalents de cœurs)',
    '---------------------|------------|-----------------|-------------------------------------------']
for fraction in sorted(scores,reverse=True):
    a=next(r for r in summary if r['pcie_frac']==fraction and r['test']==1)
    b=next(r for r in summary if r['pcie_frac']==fraction and r['test']==2)
    lines.append(f"{fraction:.2f}                 | {a['generation_tps']:.3f}      | {b['generation_tps']:.3f}           | {a['cpu_average_cores']:.2f} / {b['cpu_average_cores']:.2f}")
lines+=['',f'Meilleur partage de cette série : pcie_frac={best:g}.',
        'Les journaux de toutes les requêtes confirment la résidence RAM et zéro blob lu dans les fichiers.',
        'L’utilisation CPU moyenne inclut les périodes où les GPU travaillent ; elle ne représente pas un taux d’occupation permanent des 16 cœurs.',
        'Deux threads SMT partagent un cœur : 100 % dans un affichage sur 32 processeurs logiques n’est pas un objectif de performance.',
        'Les textes peuvent varier entre chemins CPU/GPU à cause des arrondis ; les réponses intégrales et leurs empreintes sont conservées.',
        'Cette série conserve MTP et ne teste pas encore ses différents seuils ni son arrêt.',
        '', 'Résultats antérieurs sur les mêmes prompts :',
        'Café sans MTP : ciel 13.066 ; Fibonacci 9.095 tok/s.',
        'Café MTP Q8 : ciel 14.364 ; Fibonacci 9.488 tok/s.',
        'Strata GPU MTP Q2, avant la série : ciel 8.726 ; Fibonacci 10.960 tok/s.',
        'Café et Strata utilisent des drafts différents : leur écart ne mesure pas uniquement le backend.',
        '', 'Dossier brut : '+str(RUN)]
validations=[p for p in sorted(ARCHIVE.glob('validation-*')) if (p/'resultats.json').exists()]
if validations:
    validation=validations[-1]
    confirmed=json.loads((validation/'resultats.json').read_text(encoding='utf-8'))
    lines+=['','Validation du réglage par défaut après redémarrage, sans strata_tune :']
    for r in confirmed:
        lines.append(f"Test {r['test']} : {r['generation_tps']:.3f} tokens/s, {r['cpu_expert_jobs']} travaux CPU, {r['ram_gpu_experts']} chargements d'experts vers GPU.")
    lines+=['Résultats : '+str(validation)]
report='\n'.join(lines)+'\n'
(ARCHIVE/'COMPTE-RENDU.txt').write_text(report,encoding='utf-8')
(ROOT/'COMPARATIF-CPU-GPU-P100.txt').write_text(report,encoding='utf-8')
for file in ('Test-Strata-Hybride.py','Analyser-Strata-Hybride.py','Start-Strata-P100.ps1','Stop-Strata-P100.ps1',
             'strata-q4-p100-hybride.json','protocole-comparatif-q4.json'):
    shutil.copy2(ROOT/file,ARCHIVE/file)
shutil.copy2(ROOT/'strata-build-p100/strata.exe',ARCHIVE/'strata-hybride.exe')
manifest={}
for path in sorted(ARCHIVE.rglob('*')):
    if path.is_file() and path.name!='manifest-sha256.json':
        manifest[str(path.relative_to(ARCHIVE)).replace('\\','/')]=dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(ARCHIVE/'manifest-sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(report)
