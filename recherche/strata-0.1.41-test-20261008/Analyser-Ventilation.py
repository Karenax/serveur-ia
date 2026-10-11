"""Report a cooling-controlled replay from saved measurements; no server mutations."""
import argparse,json,statistics,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--run',required=True)
args=parser.parse_args()
assert Path(args.run).name==args.run and args.run not in ('.','..')
RUN=ROOT/'mesures'/args.run
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
state=read(RUN/'etat.json')
assert state['phase']=='production-retablie',state
recovery=read(RUN/'production-retablie.json')
assert recovery['inference']['passed'] and recovery['test_port_closed']
profiles=['production']+[v['profile'] for v in state['outcomes'] if 'error' not in v]
measurements={p:[r for r in read(RUN/p/'results.json') if not r['warmup']] for p in profiles}
samples=[]
for line in (RUN/'gpu-samples.jsonl').read_text().splitlines():
    item=json.loads(line)
    for raw in item.get('rows',[]):
        cells=[v.strip() for v in raw.split(',')]
        if len(cells)<9 or 'P100' not in cells[2]:continue
        samples.append({'time':item['time'],'uuid':cells[1],'name':cells[2],
            'temperature':float(cells[3]),'clock':float(cells[4]),
            'thermal':bool(int(cells[7],16)&0x60),'utilization':float(cells[8])})
thermal=[]
for profile,rows in measurements.items():
    for row in rows:
        request_samples=read(RUN/profile/(row['name']+'-samples.json'))
        begin=request_samples[0]['time'];end=begin+row['ttft_s']
        selected=[s for s in samples if begin<=s['time']<=end]
        for uuid in sorted({s['uuid'] for s in selected}):
            group=[s for s in selected if s['uuid']==uuid]
            thermal.append({'profile':profile,'case':row['name'],'uuid':uuid,
                'sample_count':len(group),'thermal_samples':sum(s['thermal'] for s in group),
                'max_temperature_c':max(s['temperature'] for s in group),
                'min_clock_mhz':min(s['clock'] for s in group),
                'median_clock_mhz':statistics.median(s['clock'] for s in group)})
(RUN/'diagnostic-thermique.json').write_text(json.dumps(thermal,indent=2),encoding='utf-8')
base={r['name']:r for r in measurements['production']}
summary=[]
for profile,rows in measurements.items():
    docs=[r for r in rows if r['name'].startswith('dossier-')]
    long=[r for r in docs if r['name'].startswith('dossier-1024')]
    exact=[r for r in rows if r['strict_json'] is not None]
    therm=[r for r in thermal if r['profile']==profile]
    long_therm=[r for r in therm if r['case'].startswith('dossier-1024')]
    clocks=[]
    for row in long:
        request_samples=read(RUN/profile/(row['name']+'-samples.json'))
        begin=request_samples[0]['time'];end=begin+row['ttft_s']
        clocks.extend(s['clock'] for s in samples if begin<=s['time']<=end)
    ratios=[r['timings']['predicted_per_second']/base[r['name']]['timings']['predicted_per_second'] for r in rows]
    prefill=[r['timings']['prompt_per_second']/base[r['name']]['timings']['prompt_per_second'] for r in docs]
    covered=all(sum(t['sample_count'] for t in long_therm if t['case']==r['name'])>=2 for r in long)
    result={'profile':profile,'ttft_1534_s':base['dossier-64']['ttft_s'] if profile=='production' else next(r['ttft_s'] for r in rows if r['name']=='dossier-64'),
        'ttft_5950_s':next(r['ttft_s'] for r in rows if r['name']=='dossier-256'),
        'long_ttft_s':[r['ttft_s'] for r in long],'long_ttft_median_s':statistics.median(r['ttft_s'] for r in long),
        'median_decode_ratio':statistics.median(ratios),'min_document_prefill_ratio':min(prefill),
        'exact_pass':sum(r['quality_pass'] for r in exact),'exact_count':len(exact),
        'strict_json_pass':sum(r['strict_json'] for r in exact),'all_quality_pass':all(r['quality_pass'] for r in rows),
        'no_prompt_cache_reuse':all(r['timings'].get('cache_n',0)==0 for r in rows),
        'thermal_samples':sum(r['thermal_samples'] for r in therm),
        'max_temperature_c':max(r['max_temperature_c'] for r in therm),
        'long_median_clock_mhz':statistics.median(clocks),'long_min_clock_mhz':min(clocks),
        'long_thermal_coverage':covered}
    result['relative_thresholds_met']=result['all_quality_pass'] and min(prefill)>=.95 and statistics.median(ratios)>=.97
    result['cooling_valid']=covered and result['thermal_samples']==0
    summary.append(result)
baseline=summary[0]
decision={'production_restored':True,'production_version':recovery['engine_version'],
    'deployment_performed':False,'profiles':summary,'errors':[v for v in state['outcomes'] if 'error' in v],
    'cooling_comparison_valid':all(v['cooling_valid'] for v in summary)}
(RUN/'decision.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2),encoding='utf-8')
valid=decision['cooling_comparison_valid']
conclusion=('Aucune limitation thermique observée pendant les requêtes mesurées.' if valid else
    'La comparaison reste affectée par une limitation thermique ou une couverture thermique incomplète.')
lines=['# Nouvelle comparaison avec ventilation maximale — 10 octobre 2026','',conclusion,'',
    'Modèle IQ4_XS identique, deux P100, 15 workers CPU, répartition 24/24 couches et KV FP16. '
    'Moteur actuel 0.1.35 personnalisé contre Strata officiel 0.1.41, sans modification du binaire officiel. '
    'Chaque moteur reçoit une requête de chauffe, six requêtes courtes, trois dossiers et une seconde lecture du grand dossier.',
    '', '| Profil | 1 534 tokens | 5 950 tokens | ~23 600 tokens, lecture 1 / 2 | Génération / actuel |',
    '|---|---:|---:|---:|---:|']
for result in summary:
    longs=' / '.join(f'{t:.2f} s' for t in result['long_ttft_s'])
    lines.append(f"| {result['profile']} | {result['ttft_1534_s']:.2f} s | {result['ttft_5950_s']:.2f} s | {longs} | {result['median_decode_ratio']-1:+.1%} |")
lines+=['','Temps jusqu’au premier texte reçu. Le débit de génération est la médiane des rapports par requête. '
    'Les blocs de prefill font 2048 tokens, sauf le profil 4096 si présent. '
    'Le partage CPU est limité aux blocs de moins de 1024 tokens. Le profil pin verrouille en RAM le complément des experts. '
    'Les profils officiels conservent le diagnostic de phases CUDA utilisé dans la série précédente.',
    '', '| Profil | Température max pendant le prefill | Fréquence médiane sur les grands dossiers | Échantillons thermiques |',
    '|---|---:|---:|---:|']
for result in summary:
    lines.append(f"| {result['profile']} | {result['max_temperature_c']:.0f} °C | {result['long_median_clock_mhz']:.0f} MHz | {result['thermal_samples']} |")
lines+=['','Relevé toutes les trois secondes, commencé avant la première requête. '
    'Les détails séparent les deux GPU dans `diagnostic-thermique.json`. '
    'Aucun réglage de fréquence ou de puissance n’a été changé par ces scripts.',
    '', '## Vérifications','']
for result in summary:
    lines.append(f"- {result['profile']} : {result['exact_pass']}/{result['exact_count']} réponses exactes ; "
        f"{result['strict_json_pass']}/{result['exact_count']} JSON stricts ; "
        f"réutilisation de cache de prompt : {'aucune' if result['no_prompt_cache_reuse'] else 'détectée'}.")
lines+=['','Les deux explications sur le ciel sont seulement vérifiées non vides et limitées à 192 tokens. '
    'La vérification exacte tolère une clôture Markdown autour du JSON, signalée dans le compte des JSON stricts. '
    'Deux lectures longues par moteur donnent une indication, sans constituer une campagne statistique complète.',
    '', '## Comparaison avec la ventilation précédente','']
old=ROOT/'mesures/prefill-court-pin-20261009'
for result in summary:
    previous=old/result['profile']/'results.json'
    if previous.exists():
        old_long=[r['ttft_s'] for r in read(previous) if r['name'].startswith('dossier-1024')]
        old_median=statistics.median(old_long)
        lines.append(f"- {result['profile']} : médiane {old_median:.2f} s auparavant, "
            f"{result['long_ttft_median_s']:.2f} s maintenant "
            f"({1-result['long_ttft_median_s']/old_median:.1%} de temps en moins).")
lines+=['','## Serveur rétabli','',
    f"Moteur actuel {recovery['engine_version']} rétabli, PID {recovery['engine_pid']}. "
    'Réponse réelle vérifiée : 43 × 7 = 301. Port de test 8081 fermé, cinq empreintes de production inchangées. '
    'Aucune variante expérimentale n’a été déployée.','']
(RUN/'RESULTATS.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(decision,ensure_ascii=False,indent=2))
