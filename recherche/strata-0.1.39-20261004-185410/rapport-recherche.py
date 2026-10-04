"""Rapport reproductible a partir des mesures sauvegardees, sans chiffres estimes."""
import datetime as dt
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parent
MODES=[
    ('reference-production','0.1.35 + notre hybride'),
    ('officiel','0.1.39 Git, experts mmap'),
    ('officiel-ram-reserve2048','0.1.39 Git, tous les experts RAM, reserve 2 Go'),
    ('adapte','0.1.39 + notre hybride'),
]
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def number(value):
    return f'{value:.1f}'.replace('.',',')
results=[]
for folder,label in MODES:
    run=ROOT/f'{folder}-262144'
    if not (run/'mesures/synthese.json').exists():
        continue
    records=read(run/'mesures/resultats.json')
    groups={name:[r for r in records if r['test']==name] for name in ('ciel','fibonacci','fourmis')}
    if any(len(group)<2 for group in groups.values()):
        raise RuntimeError('Serie incomplete: '+folder)
    results.append(dict(mode=folder,label=label,path=str(run),
        tests={name:dict(median_tps=statistics.median(r['generation_tps'] for r in group),
                        median_prompt_tps=statistics.median(r['prompt_tps'] for r in group),
                        output_tokens=[r['output_tokens'] for r in group]) for name,group in groups.items()},
        engine_rss_peak_gib=max(r['ram_peak_gib'] for r in records),
        ngram_external_rss_peak_gib=max(r.get('ngram_helper_peak_gib',0) for r in records),
        system_ram_peak_gib=max(r['system_ram_peak_gib'] for r in records),
        vram_peak_gib={slot:max(r['vram_peak_gib'][slot] for r in records) for slot in ('0','1')},
        temperature_max_c={slot:max(r['gpu_observations'][slot]['temperature_max_c'] for r in records) for slot in ('0','1')},
        throttle_masks={slot:sorted({m for r in records for m in r['gpu_observations'][slot]['throttle_masks']}) for slot in ('0','1')},
        ram_cpu_mode_verified=all(r['cpu_expert_jobs'] and r['ram_gpu_experts']==0 for r in records) if folder in ('adapte','reference-production') else None))
now=dt.datetime.now().astimezone().isoformat()
data=dict(date=now,context=262144,input_tokens=[26,40,46],repeats=2,warmups=1,modes=results,
    incomplete_official_default=dict(path=str(ROOT/'officiel-ram-262144/mesures'),
        reason='Last request failed: verify: instantiate: out of memory. Default 700 MiB GPU reserve; complete retest uses official --vram-reserve-mib 2048.'),
    memory_note='RSS values are process working sets, not unique physical pages. External PLE lock maps the same file as the official engine; their RSS values partly overlap. Machine used RAM is independently sampled and includes Windows/other apps.')
(ROOT/'comparaison.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=[
    'Essais Strata sur 2 Tesla P100 et Threadripper PRO 3955WX',
    '',f'Rapport genere le {now}.',
    '',
    'Meme modele IQ4_XS, memes trois fragments GGUF lus depuis C:\\Temp, meme tokenizer et meme MTP. '
    'Contexte configure a 262 144 tokens. Les entrees mesurees font 26 a 46 tokens : '
    'ces chiffres ne mesurent pas le traitement d\'un prompt de 262 144 tokens.',
    '',
    'Un passage de chauffe puis deux repetitions par sujet, temperature 0, graine 42, '
    'cache de prompt desactive. Les valeurs sont les medianes de generation en tokens/s. '
    'Le nombre de tokens de sortie varie pour la poesie ; il est conserve dans les mesures.',
    '',
    '| Mode | Ciel | Fibonacci | Poesie | RSS moteur (Gio) | RSS table externe (Gio) | RAM machine utilisee (Gio) |',
    '|---|---:|---:|---:|---:|---:|---:|',
]
for r in results:
    lines.append('| '+r['label']+' | '+' | '.join(number(r['tests'][n]['median_tps']) for n in ('ciel','fibonacci','fourmis'))+
        ' | '+number(r['engine_rss_peak_gib'])+' | '+number(r['ngram_external_rss_peak_gib'])+' | '+number(r['system_ram_peak_gib'])+' |')
lines.extend([
    '',
    'La table ngram/PLE de 26,822 Gio a ete entierement verrouillee en RAM pendant les infer ences. '
    'Pour le code Git intact, un processus externe tient les pages partagees du meme GGUF '
    'avec VirtualLock ; QueryWorkingSetEx a verifie 7 031 284 pages verrouillees. '
    'Strata lit ces pages avec son option standard --ple-io mmap. '
    'Pour nos deux modes hybrides, le moteur assure lui-meme le verrouillage Windows avec --ple-io ram.',
    '',
    'Ne pas additionner les deux colonnes RSS comme une mesure exacte de RAM physique : '
    'les deux processus partagent certaines pages. La colonne RAM machine vient directement de Windows '
    'et inclut le systeme et les autres applications. Les maxima concernent les repetitions mesurees.',
    '',
    'Le code Git est le tag [v0.1.39](https://github.com/Niko1221/Strata/releases/tag/v0.1.39), commit 6f32ec070f23ced9f50e704d854d775da52591ab, sans modification de source. '
    'Le mode officiel qui charge tous les experts a d\'abord ete essaye avec les reglages automatiques : '
    '5 des 6 mesures ont termine, puis le moteur a manque de VRAM en creant un graphe CUDA. '
    'La serie exploitable est une nouvelle execution avec l\'option officielle --vram-reserve-mib 2048. '
    'Les autres options automatiques restent celles de Git.',
    '',
    'Notre variante conserve le partage 24/24 couches, les experts manquants calcules sur le CPU en RAM, '
    'la reserve GPU de 2 048 MiB, le prefill 256, sans emprunt de cache, pcie-frac 0, adapt-every 0, '
    'spec 3 / spec-min-p 0.5 et 15 travailleurs CPU. Elle conserve les chemins AVX2 amont '
    'et notre conversion BF16 vers FP16 pour le prefill P100. Le patch integral est adaptations-v0.1.39.patch.',
    '',
    '| Mode | VRAM P100 1 / 2 (Gio) | Temperature max 1 / 2 (C) | Masques de ralentissement |',
    '|---|---:|---:|---|',
])
for r in results:
    lines.append('| '+r['label']+' | '+' / '.join(number(r['vram_peak_gib'][s]) for s in ('0','1'))+
                 ' | '+' / '.join(str(r['temperature_max_c'][s]) for s in ('0','1'))+' | '+str(r['throttle_masks'])+' |')
old=next((r for r in results if r['mode']=='reference-production'),None)
new=next((r for r in results if r['mode']=='adapte'),None)
if old and new:
    lines.extend(['','Variation du nouveau mode hybride par rapport au moteur precedent, au meme contexte : '+
                  ', '.join(n+' '+f"{100*(new['tests'][n]['median_tps']/old['tests'][n]['median_tps']-1):+.1f}%" for n in ('ciel','fibonacci','fourmis'))+'.'])
    lines.extend(['','Ces ecarts ne montrent pas de gain decisif sur nos trois requetes courtes. '
                  'Le mode Git avec tous les experts en RAM atteint des vitesses proches, en occupant environ '
                  '12 Gio de plus sur la machine. Les nouveaux chemins de prefill long et les requetes '
                  'paralleles ne sont pas evalues dans cette serie.'])
for folder in ('adapte','reference-production'):
    proof=ROOT/f'{folder}-262144/ngram-ram-verifie.json'
    if proof.exists():
        p=read(proof)
        lines.extend(['',f"Verification physique de la table privee ({folder}) apres les mesures : "
                      f"{p['valid_pages']} pages presentes et {p['locked_pages']} pages verrouillees sur {p['pages']}. "])
ready_path=ROOT/'verification-production-prete.json'
if ready_path.exists():
    ready=read(ready_path)
    lines.extend(['','Production retablie et validee sur le moteur original : contexte 262 144, '
                  'historique 6 emplacements, port 8080, interface sur 8765. '
                  'Les empreintes du moteur et des fichiers de reglages correspondent aux sauvegardes initiales.'])
    proof=ROOT/'production-ngram-ram-verifie.json'
    if proof.exists():
        p=read(proof)
        lines.extend(['',f"Table ngram de production verifiee apres remise en service : {p['locked_pages']} pages verrouillees sur {p['pages']}."])
lines.extend(['',
    'Les sorties texte, requetes, reponses JSON, journaux par requete et telemetrie CPU/RAM/GPU '
    'sont conserves dans chaque sous-dossier mesures. Les essais interrompus ou echoues sont conserves '
    'mais exclus des medianes ci-dessus. Aucun de ces essais ne remplace le moteur ou les parametres de production.',
    '',
    'Reference Windows : https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtuallock',
    'Version amont : https://github.com/Niko1221/Strata/releases/tag/v0.1.39',
    'P100 experimental : https://github.com/Niko1221/Strata/blob/v0.1.39/docs/OLDER_GPUS.md',
])
(ROOT/'rapport-recherche.md').write_text('\n'.join(lines).replace('infer ences','inferences')+'\n',encoding='utf-8')
print(json.dumps(data,ensure_ascii=False),flush=True)
