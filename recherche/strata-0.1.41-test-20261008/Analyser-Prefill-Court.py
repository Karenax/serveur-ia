"""Summarize measured profiles and per-phase CUDA timings without changing any server."""
import json,re,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUN=ROOT/'mesures/prefill-court-pin-20261009'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
state=read(RUN/'etat.json')
profiles=[r['profile'] for r in state['outcomes'] if 'error' not in r]
diagnostics={}
for profile in profiles:
    phases={};group=[];host_readings=[];wall_ms=0;timeline_ms=0
    for line in (ROOT/f'logs/engine-{profile}.log').read_text(encoding='utf-8',errors='replace').splitlines():
        if line.startswith('strata prefill timing: ') and 'GPU timeline' in line:
            m=re.search(r'GPU timeline ([\d.]+) ms, wall ([\d.]+) ms, host staging ([\d.]+) ms:(.*)',line)
            if m:
                timeline_ms+=float(m[1]);wall_ms+=float(m[2]);host_readings.append(float(m[3]))
                for name,val in re.findall(r' ([a-zA-Z+/ ]+) ([\d.]+) \([\d.]+%\)',m[4]):
                    phases[name.strip()]=phases.get(name.strip(),0)+float(val)
        m=re.search(r'strata serve: prompt (\d+) tokens = .* read in ([\d.]+) ms',line)
        if m:
            group.append({'prompt_tokens':int(m[1]),'prompt_ms':float(m[2]),'sum_gpu_timeline_ms':timeline_ms,
                          'sum_part_wall_ms':wall_ms,'raw_host_staging_readings_ms':host_readings,
                          'phases_ms':dict(sorted(phases.items(),key=lambda kv:-kv[1]))})
            phases={};host_readings=[];wall_ms=0;timeline_ms=0
    diagnostics[profile]=group
(RUN/'diagnostic-phases.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
base=read(RUN/'production/results.json')
base_long=[r['ttft_s'] for r in base if r['name'].startswith('dossier-1024')]
gpu_samples=[]
for line in (RUN/'gpu-samples.jsonl').read_text().splitlines():
    try:
        item=json.loads(line)
        for raw in item.get('rows',[]):
            cells=[x.strip() for x in raw.split(',')]
            if 'P100' not in cells[2]:continue
            gpu_samples.append({'time':item['time'],'uuid':cells[1],'temperature':float(cells[3]),
                                'clock':float(cells[4]),'thermal':bool(int(cells[7],16)&0x60)})
    except (ValueError,IndexError):pass
thermal=[]
for profile in ['production']+profiles:
    for row in read(RUN/profile/'results.json'):
        if not row['name'].startswith('dossier-1024'):continue
        cpu_samples=read(RUN/profile/(row['name']+'-samples.json'))
        start=cpu_samples[0]['time'];end=start+row['ttft_s']
        selected=[s for s in gpu_samples if start<=s['time']<=end]
        if not selected:continue
        thermal.append({'profile':profile,'case':row['name'],'ttft_s':row['ttft_s'],
                        'sample_count':len(selected),'thermal_samples':sum(s['thermal'] for s in selected),
                        'max_temperature':max(s['temperature'] for s in selected),
                        'min_clock_mhz':min(s['clock'] for s in selected),
                        'median_clock_mhz':statistics.median(s['clock'] for s in selected)})
(RUN/'diagnostic-thermique.json').write_text(json.dumps(thermal,indent=2),encoding='utf-8')
lines=['# Prefill Strata 0.1.41 : CPU court et RAM verrouillée — 9 octobre 2026','',
       '**Conclusion : le gain logiciel de prefill n’est pas établi. Les deux P100 limitent leur fréquence pour raison thermique. Les profils officiels sont fonctionnels sur cette suite, mais la comparaison ne justifie pas une mise à jour de production. Le refroidissement doit être corrigé avant une nouvelle comparaison.**','',
       'Deux pistes testées sur le même modèle IQ4_XS, deux P100, 15 workers CPU, découpage 24/24 couches et KV FP16. Le binaire officiel et ses sources restent inchangés.',
       '', 'CPU limité aux blocs de moins de 1024 tokens (`STRATA_PREFILL_CPU_SHARE=auto`, `STRATA_PREFILL_CPU_SHARE_MAX=1024`). La variante RAM verrouillée remplace `--resident-cpu-experts` par `--resident-experts`. Le profil 4096, s’il apparaît dans les résultats, augmente aussi le bloc de prefill de 2048 à 4096.',
       '', 'Les profils officiels activent le diagnostic `STRATA_PREFILL_TIMING=1`. Les temps incluent son coût. Aucun cache de prompt réutilisé. Le long dossier est mesuré deux fois sur chaque profil. La seconde lecture ajoute un bref identifiant au début afin d’invalider le cache vivant de Strata ; chaque profil reçoit exactement les mêmes deux variantes. La première tentative de répétition identique, servie depuis le cache, a été exclue et conservée dans le dossier `prefill-court-pin-20261009-reference-invalidee`.',
       '', '| Profil | 1 534 tokens : premier texte | 5 950 tokens : premier texte | Environ 23 600 tokens : médiane (deux essais) | Génération / actuel |',
       '|---|---:|---:|---:|---:|']
def doc(rows,name):return next(r['ttft_s'] for r in rows if r['name']==name)
lines.append(f"| Actuel 0.1.35 | {doc(base,'dossier-64'):.2f} s | {doc(base,'dossier-256'):.2f} s | {statistics.median(base_long):.2f} s | référence |")
for profile in profiles:
    rows=read(RUN/profile/'results.json');comp=read(RUN/(profile+'-comparaison.json'))
    lines.append(f"| {profile} | {doc(rows,'dossier-64'):.2f} s | {doc(rows,'dossier-256'):.2f} s | {comp['long_ttft_median_s']:.2f} s | {comp['median_decode_ratio']-1:+.1%} |")
lines+=['','## Température et validité de la comparaison','',
        'Les P100 ont signalé un ralentissement thermique logiciel (`SW Thermal Slowdown`, masque 0x20). La nouvelle référence de production peut donc être beaucoup plus lente que les 67–70 s mesurées auparavant. Un gain contre cette référence chaude ne démontre pas à lui seul un progrès du moteur.',
        '', '| Profil / lecture longue | Température maximale observée | Fréquence SM médiane | Échantillons avec limitation thermique |',
        '|---|---:|---:|---:|']
for item in thermal:
    lines.append(f"| {item['profile']} / {item['case']} | {item['max_temperature']:.0f} °C | {item['median_clock_mhz']:.0f} MHz | {item['thermal_samples']}/{item['sample_count']} |")
lines+=['','Échantillonnage toutes les trois secondes, deux GPU réunis. Le suivi a commencé pendant la première lecture longue de la référence ; ses premiers instants ne sont pas couverts. Aucun réglage thermique ni limite de puissance n’a été modifié.',
        '', 'Le verdict logiciel doit aussi retrouver les 67–70 s historiques et être confirmé avec un refroidissement comparable. Les essais précédents sans relevé de température ne permettent pas d’attribuer toute leur différence au logiciel.',
        '', '## Contrôles et limites','']
for profile in profiles:
    rows=read(RUN/profile/'results.json');checked=[r for r in rows if not r['warmup'] and r['strict_json'] is not None]
    exact=sum(r['quality_pass'] for r in checked);strict=sum(r['strict_json'] for r in checked)
    comp=read(RUN/(profile+'-comparaison.json'))
    log=(ROOT/f'logs/engine-{profile}.log').read_text(encoding='utf-8',errors='replace')
    ram=re.findall(r'FileExpertSource: .*cache complement ready:.*',log)
    lines += [f"- {profile} : valeurs correctes {exact}/{len(checked)}, JSON strict {strict}/{len(checked)}. Seuil de comparaison à la référence de cette session {'atteint' if comp['acceptable'] else 'non atteint'} ; cela ne valide pas une mise à jour en présence de limitation thermique.",
              '  État RAM observé : '+(ram[-1] if ram else 'consulter le journal moteur')]
lines+=['','Le seuil calculé par le pilote demande au moins 97 % du débit de génération actuel et 95 % du débit de prefill sur chaque dossier, avec des valeurs attendues correctes. Il compare la référence chaude de cette session. Une validation de mise à jour doit en plus retrouver les 67–70 s historiques et éliminer le biais thermique. Les contrôles tolèrent les balises Markdown autour du JSON ; leur présence est signalée séparément. Les deux réponses explicatives sont seulement vérifiées non vides : ce test n’est pas une validation générale de qualité.',
        '', '## Diagnostic sur le long dossier','']
for profile,groups in diagnostics.items():
    long=[g for g in groups if g['prompt_tokens']>=23000]
    if not long:continue
    names=set().union(*(g['phases_ms'] for g in long))
    averages={name:statistics.mean(g['phases_ms'].get(name,0) for g in long) for name in names}
    top=sorted(averages.items(),key=lambda kv:-kv[1])[:6]
    lines.append('- '+profile+' : '+', '.join(f'{name} {value/1000:.2f} s' for name,value in top)+'.')
lines+=['','Les phases sont des sommes de segments de chronologie GPU. Une phase peut inclure une attente du CPU ou des copies. Le détail brut est dans `diagnostic-phases.json` ; les temps par phase ne sont pas des mesures de calcul pur.',
        '', '## Reprise','']
if state.get('phase')=='production-retablie':
    recovery=read(RUN/'production-retablie.json')
    assert recovery['inference']['passed'] and recovery['test_port_closed']
    lines += [f"Production 0.1.35 rétablie et vérifiée (PID {recovery['engine_pid']}). Une vraie réponse a donné 301 pour 43 × 7. Port 8081 fermé ; les cinq empreintes de production sont inchangées."]
else:lines+=['Essai encore en cours : la reprise de production reste à vérifier.']
lines+=['','## Sources examinées','',
        '- [Documentation du partage CPU officiel](https://github.com/Niko1221/Strata/blob/v0.1.41/docs/DETAILS.md#short-prompts-the-cpu-shares-the-experts-on-by-default-on-one-nvidia-gpu-strata_prefill_cpu_share).',
        '- [Rapport communautaire 2 P100](https://github.com/Niko1221/Strata/pull/1157) : autre quantification IQ3_S et Linux, utile pour identifier des pistes, chiffres non comparables directement à notre IQ4_XS sous Windows.',
        '- [Correction cuBLAS 12 proposée](https://github.com/Niko1221/Strata/pull/1659) : concerne des échecs de GEMM ; non appliquée, nos essais ne rencontrent pas cette erreur.','']
lines+=['- [NVIDIA : signification du ralentissement thermique logiciel](https://docs.nvidia.com/deploy/archive/R510/nvml-api/group__nvmlClocksThrottleReasons.html).','']
(RUN/'RESULTATS.md').write_text('\n'.join(lines),encoding='utf-8')
(RUN/'decision.json').write_text(json.dumps({'deployment_validated':False,
    'reason':'Limitation thermique observee; les meilleurs temps historiques de prefill ne sont pas retrouves.',
    'profiles_measured':profiles,'profiles_prepared_but_not_measured':['cpu-court-pin-4096'],
    'next_priority':'Ameliorer le refroidissement des deux P100, puis refaire un A/B avec temperatures et frequences controlees.',
    'production_restored':state.get('phase')=='production-retablie'},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'profiles':profiles,'phase':state['phase'],'report':str(RUN/'RESULTATS.md')},ensure_ascii=False))
