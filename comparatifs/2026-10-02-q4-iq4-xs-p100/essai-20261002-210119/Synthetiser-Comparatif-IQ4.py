"""Build a measured comparison and hash the experiment files without hashing full model weights."""
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics

root = Path(__file__).resolve().parent
archive = Path((root / 'comparatif-iq4-courant.txt').read_text(encoding='utf-8-sig').strip())
data = {label:json.loads((archive / label / 'resultats.json').read_text(encoding='utf-8'))
        for label in ('q4','iq4')}
if any(len(rows)!=6 for rows in data.values()):
    raise RuntimeError('Both models must complete all six runs')
configs = {label:json.loads((archive / label / 'configuration.json').read_text(encoding='utf-8'))
           for label in data}
if configs['q4']['binary_sha256'] != configs['iq4']['binary_sha256']:
    raise RuntimeError('The two models did not use the same engine binary')
def common_settings(saved):
    config = saved['config'].copy()
    arguments = config['args'].copy()
    for option in ('--pack','--native'):
        arguments[arguments.index(option)+1] = '<local-model>'
    config['args'] = arguments
    config['env'] = config['env'].copy()
    sync_flag = Path(config['env']['STRATA_P100_DIAGNOSTIC_SYNC_FILE'])
    if sync_flag.exists():
        raise RuntimeError('Diagnostic synchronization is still enabled')
    config['env']['STRATA_P100_DIAGNOSTIC_SYNC_FILE'] = '<disabled-sync-flag>'
    for key in ('model_name','log'):
        config.pop(key)
    return config
if common_settings(configs['q4']) != common_settings(configs['iq4']):
    raise RuntimeError('Engine settings differ beyond the intended model paths')
if (archive / 'prelecture-en-cours.flag').exists():
    raise RuntimeError('File-page warming is still running')
protocols = {label:json.loads((archive / label / 'protocole.json').read_text(encoding='utf-8'))
             for label in data}
metrics = {label:json.loads((archive / label / 'metrics.json').read_text(encoding='utf-8'))['engine']
           for label in data}
if protocols['q4'] != protocols['iq4']:
    raise RuntimeError('Protocols differ')
shared_config=configs['q4']['config']
shared_args=shared_config['args']
profile_path=Path(shared_args[shared_args.index('--expert-profile')+1])
shutil.copy2(profile_path,archive/'expert-profile.bin')
tokenizer_copy=archive/'tokenizer-commun'
tokenizer_copy.mkdir(exist_ok=True)
for path in Path(shared_config['tokenizer']).iterdir():
    if path.is_file():
        shutil.copy2(path,tokenizer_copy/path.name)
rows = []
for case in protocols['q4']['cases']:
    selected = {label:[r for r in runs if r['test']==case['id']] for label,runs in data.items()}
    if any(len(runs)!=2 for runs in selected.values()):
        raise RuntimeError('Missing paired repetitions')
    token_counts = {label:{r['prompt_tokens'] for r in runs} for label,runs in selected.items()}
    if token_counts['q4'] != token_counts['iq4']:
        raise RuntimeError('The input token count changed despite the shared tokenizer/template')
    medians = {label:statistics.median(r['generation_tps'] for r in runs) for label,runs in selected.items()}
    texts = {label:[(archive / label / f"r{run['repeat']}-{case['id']}-texte.txt").read_text(encoding='utf-8')
                   for run in runs] for label,runs in selected.items()}
    rows.append(dict(test=case['id'],prompt=case['prompt'],q4_tps=medians['q4'],iq4_tps=medians['iq4'],
        iq4_change_pct=(medians['iq4']/medians['q4']-1)*100,
        mtp_acceptance={label:statistics.median(r['mtp_acceptance'] for r in runs) for label,runs in selected.items()},
        ram_peak_gib={label:max(r['ram_peak_gib'] for r in runs) for label,runs in selected.items()},
        output_tokens={label:[r['output_tokens'] for r in runs] for label,runs in selected.items()},
        output_words={label:[len(re.findall(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*", text)) for text in answers]
                      for label,answers in texts.items()},
        deterministic_output={label:len({r['answer_sha256'] for r in runs})==1 for label,runs in selected.items()},
        complete_answers={label:[r['finish_reason']=='stop' for r in runs] for label,runs in selected.items()}))
(archive / 'synthese.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (archive / 'synthese.csv').open('w',newline='',encoding='utf-8') as f:
    flat=[{k:r[k] for k in ('test','q4_tps','iq4_tps','iq4_change_pct')} for r in rows]
    writer=csv.DictWriter(f,fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)

models=json.loads((archive/'modeles.json').read_text(encoding='utf-8-sig'))
lines=['Comparatif Q4_K_XL / IQ4_XS — deux P100, Strata expérimental',
       'Deux répétitions par prompt, mêmes requêtes, même binaire, même MTP Q2 (spec 3, seuil 0.5).',
       'Température 0, seed 42, reasoning désactivé, cache de prompt désactivé, contexte 4096.',
       'Ciel/Fibonacci : limite 256 tokens ; poésie : limite 512 pour permettre une réponse complète.',
       '15 travailleurs CPU + thread principal ; tous les experts absents de la VRAM calculés sur CPU.',
       'Cache VRAM auto, réserve 2048 Mio, partage par couches 24/24, caches fixes, adaptation désactivée.',
       'Experts en RAM épinglée, table ngram en RAM verrouillée ; aucune lecture de blob d’expert pendant les réponses.',
       'Le profil d’experts et le tokenizer commun sont copiés dans cette archive pour les comparatifs ultérieurs.',
       '', 'Résultats : médianes des deux répétitions, en tokens générés par seconde.']
for row in rows:
    lines.append(f"{row['test']}: Q4 {row['q4_tps']:.2f} t/s ; IQ4 {row['iq4_tps']:.2f} t/s ; écart {row['iq4_change_pct']:+.1f} %.")
    lines.append('  MTP accepté : '+', '.join(f"{label} {value*100:.1f} %" for label,value in row['mtp_acceptance'].items()))
    lines.append('  Tokens produits : '+', '.join(f"{label} {counts}" for label,counts in row['output_tokens'].items()))
lines += ['', 'Interprétation :',
          'Le gain sur la poésie est faible (+1.5 % sur ces deux répétitions) : les débits sont pratiquement équivalents.',
          'L’acceptation MTP sur la poésie baisse de 65.4 % en Q4 à 56.7 % en IQ4, ce qui peut réduire le gain apporté par les caches.',
          'Sur ciel et Fibonacci, les médianes IQ4 augmentent respectivement de 5.5 % et 10.3 %.',
          'À température 0 et seed 42, les deux sorties IQ4 diffèrent sur ciel et poésie ; Fibonacci reste identique.',
          'Le protocole identique ne garantit donc pas un texte identique ni une comparaison à parcours de calcul strictement identique.',
          'Les poèmes sont complets et compréhensibles, mais les deux modèles dépassent les 200 mots demandés.',
          'Le code Fibonacci IQ4 donne bien [0, 1, 1, 2, 3, 5, 8, 13] pour n=8 ; son commentaire final est tronqué par la limite commune.',
          'Les explications du ciel sont également tronquées par la limite commune de 256 tokens.',
          'Ce petit ensemble permet de comparer vitesse et placement ; il ne prouve pas une qualité globale supérieure.']
lines += ['', 'Placement et portée de la comparaison :',
          f"Experts natifs : Q4 {models['q4']['expert_bytes']/2**30:.2f} Gio ; IQ4 {models['iq4']['expert_bytes']/2**30:.2f} Gio.",
          'Table PLE/ngram : même format IQ4_NL et même taille de 26.82 Gio pour les deux artefacts.',
          'Le vocabulaire, les merges et les IDs spéciaux sont identiques. Les templates fournis diffèrent.',
          'Le serveur IQ4 utilise volontairement le tokenizer/template Q4 pour produire les mêmes tokens d’entrée.',
          'Le template original IQ4 est conservé dans chat_template-iq4-original.jinja.',
          'Les noms/provenances et les calibrations des deux artefacts diffèrent : ce test compare ces fichiers locaux,',
          'pas uniquement deux quantifications d’un checkpoint dont l’identité des poids aurait été prouvée.',
          'Les petits tenseurs nécessaires à Strata sont convertis en BF16 ; les experts gardent leurs octets natifs.',
          'Le wrapper Preparer-IQ4-Strata.py conserve aussi la clé PLE native IQ4_XS, déjà supportée par le moteur.',
          'Le brouillon MTP Q2 reste strictement le même ; son taux d’acceptation peut donc varier selon le modèle cible.',
          'Les réponses ciel/Fibonacci limitées à 256 tokens ne constituent pas une étude complète de qualité.',
          'Les réponses, télémétries et traces de chaque essai sont conservées dans q4/ et iq4/.',
          'L’utilisation CPU inclut les attentes actives des travailleurs ; elle ne mesure pas uniquement du calcul utile.',
          'Les hash des GGUF portent seulement sur leurs en-têtes ; aucun hash intégral des poids n’est revendiqué.',
          '',f"Binaire commun SHA256 : {configs['q4']['binary_sha256']}"]
lines += ['', 'Placement mesuré au terme des essais :']
for label in data:
    engine = metrics[label]
    peak_ram = max(run['ram_peak_gib'] for run in data[label])
    peak_vram = {slot:max(run['vram_peak_gib'][slot] for run in data[label])
                 for slot in data[label][0]['vram_peak_gib']}
    lines.append(f"{label}: {engine['expert_slots']} experts en VRAM "
                 f"({engine['expert_slots_primary']} sur la première P100, "
                 f"{engine['expert_slots']-engine['expert_slots_primary']} sur la seconde), "
                 f"{engine['expert_cache_mib']/1024:.2f} Gio de cache expert.")
    lines.append(f"  Complément expert en RAM : {engine['arena_mib']/1024:.2f} Gio ; "
                 f"pic RAM du processus : {peak_ram:.2f} Gio.")
    lines.append('  VRAM occupée, toutes allocations comprises : '+
                 ', '.join(f"P100 {int(slot)+1} {used:.2f} Gio" for slot,used in peak_vram.items()))
poem = next(row for row in rows if row['test']=='fourmis')
lines += ['  Poésie, nombre de mots selon le même compteur : '+
          ', '.join(f"{label} {counts}" for label,counts in poem['output_words'].items()),
          'Le pic RAM est le working set du processus ; il peut aussi inclure des pages des GGUF mises en cache.',
          'Il doit être distingué du complément expert épinglé et de la table PLE verrouillée, dont les tailles sont explicites.',
          'Les mesures GPU ci-dessus proviennent de NVML, avec les UUID des deux P100 explicitement sélectionnés.',
          'Le panneau matériel de /metrics identifie la Quadro P2200 : ses graphiques GPU ne sont pas utilisés ici.']
prefetch_path = archive / 'etat-prelecture.json'
if prefetch_path.exists():
    prefetch = json.loads(prefetch_path.read_text(encoding='utf-8-sig'))
    lines += ['', 'Chargement initial :',
              'Une prélecture séquentielle supplémentaire a été essayée, puis arrêtée avant les requêtes mesurées.',
              f"État archivé : {prefetch.get('status', 'voir etat-prelecture.json')}; "
              f"{prefetch.get('read_gib', 0):.2f} Gio lus par cet auxiliaire.",
              'Les lectures dispersées du profil rendent le démarrage depuis le HDD très lent.',
              'Ce temps de démarrage ne fait pas partie des débits d’inférence présentés.']
gpu2_prefetch_path = archive / 'etat-prelecture-gpu2.json'
if gpu2_prefetch_path.exists():
    gpu2_prefetch = json.loads(gpu2_prefetch_path.read_text(encoding='utf-8'))
    if gpu2_prefetch.get('status') != 'complete':
        raise RuntimeError('The second GPU page warming did not finish successfully')
    lines += [f"Une seconde prélecture, limitée aux couches 24-47, a lu "
              f"{gpu2_prefetch['read_gib']:.2f} Gio en "
              f"{gpu2_prefetch['elapsed_seconds']:.1f} s ; blocs de 4 Mio, plafond de 48 Mio/s.",
              'Cette aide au démarrage se termine avant le warmup et les six réponses mesurées.']
for filename in ('etat-prelecture-complement.json','etat-prelecture-complement-rapide.json'):
    prefetch_path=archive/filename
    if not prefetch_path.exists():
        continue
    attempt=json.loads(prefetch_path.read_text(encoding='utf-8-sig'))
    lines.append(f"Aide à la copie RAM ({filename}) : état {attempt['status']}, "
                 f"{attempt['read_gib']:.2f} Gio lus en {attempt['elapsed_seconds']:.1f} s, "
                 f"{attempt.get('skipped_verified_gib',0):.2f} Gio ignorés car déjà copiés/vérifiés par Strata.")
lines += ['La dernière aide bride les blocs lents et parcourt immédiatement les blocs déjà chauds.',
          'Le seuil temporel utilisé pour reconnaître les blocs chauds est une heuristique, pas une mesure matérielle de cache.',
          'Le code du moteur copiant les projections natives utilise memcpy sur les vues des GGUF sans PrefetchVirtualMemory.',
          'Le démarrage Q4/IQ4 ne fait pas l’objet d’un ratio comparable : les états du cache fichier diffèrent.',
          'Ces étapes copient les octets natifs ; le temps d’attente ne démontre pas un coût de calcul IQ4 en inférence.']
startup_log = Path(configs['iq4']['config']['log']).read_text(encoding='utf-8', errors='replace')
last_run=data['iq4'][-1]
last_trace=(archive/'iq4'/f"r{last_run['repeat']}-{last_run['test']}-engine.log").read_text(encoding='utf-8')
last_line=next(line for line in reversed(last_trace.splitlines()) if line.strip())
snapshot_lines=startup_log.splitlines()
ends=[index for index,line in enumerate(snapshot_lines) if line==last_line]
if len(ends)!=1:
    raise RuntimeError('Could not delimit the benchmark snapshot before subsequent user requests')
startup_log='\n'.join(snapshot_lines[:ends[0]+1])+'\n'
(archive / 'engine-iq4-snapshot.log').write_text(startup_log, encoding='utf-8')
health_path = archive / 'health-iq4.json'
stdout_path = archive / 'serveur-iq4.stdout.log'
if health_path.exists() and stdout_path.exists():
    startup_elapsed = health_path.stat().st_mtime-stdout_path.stat().st_ctime
    lines.append(f"Serveur IQ4 observé prêt après environ {startup_elapsed/60:.1f} minutes "
                 '(horodatages des fichiers, interrogation toutes les dix secondes).')
(archive/'RAPPORT.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
shutil.copy2(Path(__file__),archive / Path(__file__).name)
manifest = {}
for path in sorted(archive.rglob('*')):
    if not path.is_file() or path.name=='manifest-sha256.json' or path.name in (
            'engine-iq4.log','serveur-iq4.stdout.log','serveur-iq4.stderr.log','tests-iq4.stdout.log',
            'tests-iq4-suite.stdout.log'):
        continue
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(2**20),b''):
            digest.update(block)
    manifest[path.relative_to(archive).as_posix()]=dict(bytes=path.stat().st_size,sha256=digest.hexdigest())
(archive/'manifest-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
print(archive/'RAPPORT.txt')
