"""Produce a comparison from completed/partial measurements without model requests."""
import argparse, json, statistics
from pathlib import Path

ap=argparse.ArgumentParser();ap.add_argument('run',type=Path);ap.add_argument('--supplement',type=Path);a=ap.parse_args()
RUN=a.run
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def median(values):return statistics.median(values) if values else None
samples=[]
telemetry=(RUN/'gpu-samples.jsonl').read_text()
if a.supplement:telemetry+='\n'+(a.supplement/'gpu-samples.jsonl').read_text()
for line in telemetry.splitlines():
    try:samples.append(json.loads(line))
    except ValueError:pass
summary=[]
rows_by_profile={}
folders=list(RUN.iterdir())+(list(a.supplement.iterdir()) if a.supplement else [])
for folder in sorted(folders):
    if not folder.is_dir() or not (folder/'results.json').exists():continue
    rows=[r for r in read(folder/'results.json') if not r['warmup']]
    rows_by_profile[folder.name]=rows
    def throughput(case):
        return median([r['timings']['predicted_per_second'] for r in rows if r['name'].endswith('-'+case) and r['timings'].get('predicted_per_second')])
    def doc(size,key):
        return median([r['timings'][key] for r in rows if r['name'].startswith(f'dossier-{size}-') and key in r['timings']])
    thermal=[]
    for request in rows:
        span=[s for s in samples if request['start']<=s.get('time',0)<=request['end'] and s.get('rows')]
        for uuid in sorted({v['uuid'] for s in span for v in s['rows']}):
            group=[v for s in span for v in s['rows'] if v['uuid']==uuid]
            thermal.append(dict(case=request['name'],uuid=uuid,samples=len(group),max_temperature_c=max(v['temperature_c'] for v in group),
                                min_sm_mhz=min(v['sm_mhz'] for v in group),median_sm_mhz=median([v['sm_mhz'] for v in group]),
                                thermal_samples=sum(bool(v['throttle_mask']&0x60) for v in group)))
    (folder/'thermique-par-requete.json').write_text(json.dumps(thermal,indent=2),encoding='utf-8')
    sustained=[r for r in rows if r['name'].startswith('soutenu-')]
    sustained_rate=sum(r['timings'].get('predicted_n',0) for r in sustained)/(sum(r['timings'].get('predicted_ms',0) for r in sustained)/1000) if sustained else None
    exact=[r for r in rows if r['strict_json'] is not None]
    result=dict(profile=folder.name,source_folder=str(folder.resolve()),requests=len(rows),sky_tps=throughput('ciel'),fibonacci_code_tps=throughput('fibonacci-code'),
                document_prompt_ms={str(n):doc(n,'prompt_ms') for n in (64,256,1024)},
                document_prompt_tps={str(n):doc(n,'prompt_per_second') for n in (64,256,1024)},
                sustained_tps=sustained_rate,sustained_seconds=sum(r['elapsed_s'] for r in sustained),sustained_requests=len(sustained),
                sustained_individual_tps=[r['timings'].get('predicted_per_second') for r in sustained],
                exact_pass=sum(r['quality_pass'] for r in exact),exact_count=len(exact),strict_json_pass=sum(r['strict_json'] is True for r in exact),
                max_temperature_c=max((r['max_temperature_c'] for r in thermal),default=None),thermal_samples=sum(r['thermal_samples'] for r in thermal),
                thermal_sample_count=sum(r['samples'] for r in thermal),no_prompt_reuse=all(r['timings'].get('cache_n',0)==0 for r in rows))
    summary.append(result)
baseline={r['name']:r for r in rows_by_profile.get('flash-production',[])}
baseline_summary=next((r for r in summary if r['profile']=='flash-production'),None)
baseline_thermal_valid=bool(baseline_summary and baseline_summary['thermal_samples']==0)
for result in summary:
    if not result['profile'].startswith('strata-'):continue
    rows=rows_by_profile[result['profile']]
    ratios=[r['timings']['predicted_per_second']/baseline[r['name']]['timings']['predicted_per_second'] for r in rows if r['name'] in baseline and r['name'].startswith('r')]
    doc_ratios=[r['timings']['prompt_per_second']/baseline[r['name']]['timings']['prompt_per_second'] for r in rows if r['name'] in baseline and r['name'].startswith('dossier-')]
    result['median_decode_ratio']=median(ratios)
    result['min_document_prefill_ratio']=min(doc_ratios) if doc_ratios else None
    result['baseline_thermal_valid']=baseline_thermal_valid
    result['speed_and_exact_checks_met']=bool(ratios and doc_ratios and result['median_decode_ratio']>=.97 and min(doc_ratios)>=.95 and result['exact_pass']==result['exact_count'] and result['exact_count']==9)
    result['thresholds_met']=bool(baseline_thermal_valid and result['speed_and_exact_checks_met'] and result['thermal_samples']==0)
display={'flash-production':'Flash-Next / Strata 0.1.35 actuel','strata-mtp-batch':'Flash-Next / Strata 0.1.43.1, MTP groupé demandé',
         '27b-mtp2-4096':'27B / Café MTP 2, contexte 4K','27b-sans-mtp-4096':'27B / Café sans MTP, contexte 4K',
         '27b-mtp2-32768':'27B / Café MTP 2, contexte 32K'}
order={name:index for index,name in enumerate(display)}
summary.sort(key=lambda r:order.get(r['profile'],99))
state=read(RUN/'etat.json')
recovery=read(RUN/'production-retablie.json') if (RUN/'production-retablie.json').exists() else None
report=dict(profiles=summary,state=state,production_restored=bool(recovery and recovery['inference_pass'] and recovery['test_port_closed'] and recovery['files_unchanged']),deployment_performed=False)
supplement_state=None
if a.supplement:
    supplement_state=read(a.supplement/'etat.json')
    sr=read(a.supplement/'production-retablie.json') if (a.supplement/'production-retablie.json').exists() else None
    report['supplement_run']=str(a.supplement.resolve())
    report['supplement_state']=supplement_state
    report['production_restored']=bool(report['production_restored'] and sr and sr['inference_pass'] and sr['test_port_closed'] and sr['files_unchanged'])
console_path=RUN.parent.parent/'validation/console-reprise.json'
if console_path.exists():report['console_recovery']=read(console_path)
(RUN/'comparaison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def fmt(v):return '—' if v is None else f'{v:.2f}'
lines=['# Comparaison Flash-Next et Qwen 27B — 13 octobre 2026','',
       'Débits de génération mesurés par les moteurs, hors chargement et lecture du prompt. Ciel et code Fibonacci : médianes de trois requêtes après chauffe. Les préfixes distincts empêchent la reprise du prompt vivant ; les prompts restent comparables entre profils de cette campagne, mais diffèrent légèrement des essais du 3 octobre.',
       '', '| Profil | Ciel tok/s | Code Fibonacci tok/s | Série sans pauses tok/s | Durée de la série | Température max | Échantillons thermiques |',
       '|---|---:|---:|---:|---:|---:|---:|']
if state.get('cooling_between_requests'):
    lines.insert(2,'Cette campagne refroidit les P100 sous 55 °C entre les requêtes ordinaires. Les débits ordinaires ne sont donc pas des débits garantis en continu. Les seules séries soutenues sont explicitement séparées ci-dessous.\n')
for r in summary:
    duration=fmt(r['sustained_seconds'])+' s' if r['sustained_requests'] else '—'
    lines.append(f"| {display.get(r['profile'],r['profile'])} | {fmt(r['sky_tps'])} | {fmt(r['fibonacci_code_tps'])} | {fmt(r['sustained_tps'])} | {duration} | {fmt(r['max_temperature_c'])} °C | {r['thermal_samples']} |")
lines+=['','| Profil | Lecture ~1,5K | Lecture ~6K | Lecture ~23,6K | Vérifications exactes | JSON strict |',
        '|---|---:|---:|---:|---:|---:|']
for r in summary:
    docs=[None if r['document_prompt_ms'][str(n)] is None else r['document_prompt_ms'][str(n)]/1000 for n in (64,256,1024)]
    lines.append(f"| {display.get(r['profile'],r['profile'])} | {fmt(docs[0])} s | {fmt(docs[1])} s | {fmt(docs[2])} s | {r['exact_pass']}/{r['exact_count']} | {r['strict_json_pass']}/{r['exact_count']} |")
lines+=['','Les durées du tableau documents sont celles de lecture du prompt remontées par le moteur, pas le délai client jusqu’au premier texte. Les comptes réels de tokens figurent dans chaque réponse ; ils peuvent différer entre tokenizers. Chaque dossier est mesuré deux fois.',
        '', 'Flash-Next : même IQ4_XS, deux P100 24/24, 15 workers CPU, prefill 2048, contexte 262144, KV FP16, MTP 3/0,5, PLE direct. Strata reference désactive explicitement le tail skip ; mtp-batch ajoute seulement le traitement groupé du brouillon sur la seconde carte.',
        '', '27B : Huihui abliterated Q4_K_M, deux P100 en mode tensor, Café, MTP Q4_0 2 tokens lorsque indiqué. Le contexte 32768 permet les mêmes documents ; le contexte 4096 reprend les conditions de taille de contexte historiques. Comparer ces configurations séparément.',
        '', 'La charge soutenue enchaîne des réponses plafonnées à 512 tokens sans pauses de refroidissement, pendant au moins trois minutes si elle aboutit. Ce débit agrège les tokens et temps de génération de cette charge ; il dépend du texte. Il ne constitue pas un classement général de qualité des deux modèles. Les réponses explicatives et le code sont conservés pour inspection, mais leur présence seule ne valide pas leur qualité.',
        '', 'Température/fréquences/puissance/limitation thermique relevées toutes les deux secondes. Les échantillons du tableau couvrent uniquement les requêtes mesurées ; le journal complet inclut la chauffe et le chargement. Bits thermiques : masque 0x60. Une campagne est interrompue à 80 °C ; les résultats partiels restent visibles.', '', '## Comparaison des versions Strata','']
for r in summary:
    if 'median_decode_ratio' in r:
        gain='non disponible' if r['median_decode_ratio'] is None else f"{r['median_decode_ratio']-1:+.1%}"
        lines.append(f"- {r['profile']} : génération médiane {gain}, pire rapport de lecture des dossiers {fmt(r['min_document_prefill_ratio'])}. Seuils de vitesse et vérifications exactes atteints : {r['speed_and_exact_checks_met']}. Validation globale avec référence sans limitation thermique : {r['thresholds_met']}.")
        if not r['baseline_thermal_valid']:lines.append('  La référence a un échantillon de limitation thermique sur le grand document ; cela empêche de présenter la comparaison thermique globale comme validée, même si les seuils de vitesse et les valeurs exactes sont bons.')
lines+=['','## État et reprise','',f"Phase : {state['phase']}. Production restaurée et vérifiée par une réponse calculée : {report['production_restored']}. Aucun nouveau moteur déployé en production."]
if report.get('console_recovery'):
    c=report['console_recovery']
    lines+=['',f"Console reconnectée : {c['console_reconnected']}. Moteur conservé pendant cette reconnexion : PID {c['engine_pid_unchanged']}. Réglages conservés : chargement automatique {c['autoload_and_restart_settings']['autoload']}, relance automatique {c['autoload_and_restart_settings']['restart']}."]
mtp=next((r for r in summary if r['profile']=='27b-mtp2-4096'),None)
if mtp and mtp['sustained_requests']:
    lines+=['',f"La série MTP 4K sans pauses comprend {mtp['sustained_requests']} réponses, {mtp['sustained_seconds']:.1f} secondes et {mtp['sustained_tps']:.2f} tokens/s agrégés. Débits individuels : "+' / '.join(fmt(v) for v in mtp['sustained_individual_tps'])+'. La série s’arrête sur une limitation thermique ; elle n’a pas atteint les trois minutes visées.']
if supplement_state:
    lines+=['',f"Complément MTP 4K : {a.supplement.resolve()}, phase {supplement_state['phase']}. L'attente maximale de refroidissement passe de cinq à dix minutes, avec le même seuil de départ de 55 °C. Les données de la première tentative restent conservées séparément."]
for outcome in state['outcomes']:
    if outcome.get('error'):lines.append(f"- Profil {outcome['profile']} : {outcome['error']}")
if state.get('error'):lines.append('- Erreur de campagne : '+state['error'])
if supplement_state:
    for outcome in supplement_state['outcomes']:
        if outcome.get('error'):lines.append(f"- Complément {outcome['profile']} : {outcome['error']}")
    if supplement_state.get('error'):lines.append('- Erreur du complément : '+supplement_state['error'])
if (RUN/'synchronisation-prelecture.json').exists():
    lines+=['','Le premier démarrage officiel a dépassé le délai interne de 900 secondes du serveur pendant la copie des experts, avant toute inférence. Une prélecture séquentielle de 60,94 Gio d’experts a été effectuée ; le pilote des mesures a attendu sa fin. Le démarrage suivant bénéficie du cache de fichiers chaud. Cette campagne ne mesure donc pas un temps de chargement froid comparable entre versions. Le lanceur de test a ensuite été préparé avec STRATA_ENGINE_READY_S=1800 pour les futurs démarrages froids ; ce réglage ne constitue pas une réparation du binaire.']
engine_log=RUN/'engine-mtp-batch.log'
if engine_log.exists() and 'too little scratch for a 64-row batch' in engine_log.read_text(errors='replace'):
    lines+=['','Le moteur a annoncé un refus du MTP groupé sur la première requête courte : moins de 64 lignes disponibles pour un batch. Le diagnostic n’est écrit qu’une fois par processus, alors que le choix est refait pour chaque bloc. Il ne prouve donc pas que tous les documents ont suivi le repli. Faute de mesure complète du même binaire avec cette option désactivée, les gains observés ne peuvent pas être attribués isolément au MTP groupé.']
lines+=['','Les fichiers de production sont contrôlés par leurs empreintes. Les requêtes, réponses complètes, paramètres effectifs et journaux se trouvent dans ce dossier. Les profils non mesurés et les images/conversations concurrentes restent hors de cette campagne.']
(RUN/'RAPPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
