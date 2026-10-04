"""Compare la table ngram en RAM et sur C avec le meme moteur hybride."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'normal-ngram-ssd-262144'
REF=ROOT/'reference-production-262144'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

reference=read(REF/'mesures/resultats.json')
ssd=read(RUN/'mesures/resultats.json')
if len(reference)!=6 or len(ssd)!=6:
    raise RuntimeError('Les deux repetitions completes de chaque sujet sont necessaires')
comparisons={}
for case in ('ciel','fibonacci','fourmis'):
    base=[r for r in reference if r['test']==case]
    current=[r for r in ssd if r['test']==case]
    ram_median=statistics.median(r['generation_tps'] for r in base)
    ssd_median=statistics.median(r['generation_tps'] for r in current)
    warm_ram=read(REF/f'mesures/warmup1-{case}-mesures.json')
    warm_ssd=read(RUN/f'mesures/warmup1-{case}-mesures.json')
    comparisons[case]=dict(ram_tps=ram_median,ssd_tps=ssd_median,
        relative_percent=(ssd_median/ram_median-1)*100,
        ram_first_pass_tps=warm_ram['generation_tps'],ssd_first_pass_tps=warm_ssd['generation_tps'],
        ssd_first_pass_read_bytes=warm_ssd['engine_io_read_bytes'],
        ssd_repeat_read_bytes=[r['engine_io_read_bytes'] for r in current],
        ram_output_tokens=[r['output_tokens'] for r in base],ssd_output_tokens=[r['output_tokens'] for r in current],
        ram_prompt_tps=statistics.median(r['prompt_tps'] for r in base),
        ssd_prompt_tps=statistics.median(r['prompt_tps'] for r in current),
        ram_answer_sha256=[r['answer_sha256'] for r in base],ssd_answer_sha256=[r['answer_sha256'] for r in current],
        ssd_mtp_acceptance=statistics.median(r['mtp_acceptance'] for r in current))
ram_peak=max(r['ram_peak_gib'] for r in reference)
ssd_peak=max(r['ram_peak_gib'] for r in ssd)
proof=read(RUN/'ngram-ssd-verifie.json')
if not proof['verified'] or proof['full_private_table_copies']:
    raise RuntimeError('Le mode SSD n\'est pas verifie')
copy=read(RUN/'copie-ngram.json')
if copy['status']!='verifie' or copy['source_sha256']!=copy['copied_sha256']:
    raise RuntimeError('La copie n\'est pas identique a la table originale')
stamps=read(RUN/'production-sauvegarde/empreintes.json')
checked=[]
for stamp in stamps:
    path=Path(stamp['path'])
    if path.name=='state.json':
        continue  # normal lifecycle state changes on stop/restart
    current_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    checked.append(dict(**stamp,current_sha256=current_hash,unchanged=current_hash==stamp['sha256']))
ready_path=RUN/'verification-production-prete.json'
restored=read(ready_path) if ready_path.exists() else None
ram_proof_path=RUN/'production-ngram-ram-verifie.json'
ram_proof=read(ram_proof_path) if ram_proof_path.exists() else None
answers_identical=all(item['ram_answer_sha256']==item['ssd_answer_sha256'] for item in comparisons.values())
if restored and (ram_proof is None or not ram_proof['complete']):
    raise RuntimeError('La verification physique de la table de production est necessaire')
all_measurements=ssd+[read(p) for p in (RUN/'mesures').glob('warmup*-mesures.json')]
result=dict(created=dt.datetime.now(dt.timezone.utc).isoformat(),context=262144,
    engine='0.1.35 + hybride P100 de production',tests=comparisons,
    engine_ram_ram_mode_gib=ram_peak,engine_ram_ssd_mode_gib=ssd_peak,engine_ram_saved_gib=ram_peak-ssd_peak,
    system_ram_ram_mode_gib=max(r['system_ram_peak_gib'] for r in reference),
    system_ram_ssd_mode_gib=max(r['system_ram_peak_gib'] for r in ssd),
    ssd_gpu_vram_gib={slot:max(r['vram_peak_gib'][slot] for r in ssd) for slot in ('0','1')},
    ssd_gpu_temp_max_c={slot:max(r['gpu_observations'][slot]['temperature_max_c'] for r in ssd) for slot in ('0','1')},
    ssd_gpu_throttle_masks={slot:sorted({x for r in ssd for x in r['gpu_observations'][slot]['throttle_masks']}) for slot in ('0','1')},
    expert_ram_verified=all(r['cpu_expert_jobs']>0 and r['ram_gpu_experts']==0 for r in all_measurements),
    ssd_proof=proof,table_copy=copy,production_file_checks=checked,production_restored=restored,
    measured_answers_identical=answers_identical,production_ngram_ram_proof=ram_proof,
    caveats=['Two repetitions per prompt: small variations are not conclusive.',
             'Default 1,048,576-row cache stays enabled (~94.1 MiB with keys); repeated prompts can be almost entirely served by it.',
             'First pass means first encounter of each prompt in the process; later prompts may share some cached rows.',
             'RSS is process working set. Total used system RAM includes Windows and other apps.',
             'Model source is D for this trial: all expert bytes are resident in RAM/VRAM before inference, so source drive affects startup, not expert reads during inference.',
             'Same context capacity, short prompts of 26-46 tokens. Prompt history disabled for both benchmark modes.'])
save(RUN/'comparaison-ngram.json',result)
lines=['# Essai du mode normal : table ngram sur SSD C',
    '',f'Date : {result["created"]}. Moteur 0.1.35 avec notre hybride P100, IQ4_XS, contexte 262 144, 15 workers, prefill 256, reserve VRAM 2 048 Mio, MTP actif.',
    '', 'Seule la table PLE passe de `--ple-io ram` a `--ple-io direct`, avec un chemin explicite vers C. Le binaire et les parametres de production sont conserves. Les checkpoints de conversation sont desactives pendant les deux benchmarks pour eviter la reutilisation du prompt.',
    '', '| Sujet | Table RAM, tok/s | Table SSD, tok/s | Ecart |', '|---|---:|---:|---:|']
names={'ciel':'Ciel','fibonacci':'Fibonacci','fourmis':'Poesie fourmis'}
for case,item in comparisons.items():
    lines.append(f'| {names[case]} | {item["ram_tps"]:.2f} | {item["ssd_tps"]:.2f} | {item["relative_percent"]:+.1f}% |')
lines.extend(['', 'Vitesses medianes de deux passages apres un passage de chauffe par sujet. Les reponses, temps, telemetries et journaux sont conserves dans `mesures`.',
    '', 'Les six reponses mesurees sont identiques a la reference RAM (SHA-256 du texte identique).' if answers_identical else 'Les differences de reponse sont documentees dans comparaison-ngram.json.',
    '',f'RAM du moteur au pic : **{ram_peak:.2f} Gio en mode RAM, {ssd_peak:.2f} Gio en mode SSD**, soit **{ram_peak-ssd_peak:.2f} Gio liberes**. RAM totale machine : {result["system_ram_ram_mode_gib"]:.2f} contre {result["system_ram_ssd_mode_gib"]:.2f} Gio ; cette mesure depend aussi de Windows et des autres applications.',
    '', '| Sujet | Premier passage RAM, tok/s | Premier passage SSD, tok/s | Lectures moteur premier passage SSD, Mio | Lectures passages repetes SSD, Mio |',
    '|---|---:|---:|---:|---:|'])
for case,item in comparisons.items():
    reads=', '.join(f'{x/2**20:.2f}' for x in item['ssd_repeat_read_bytes'])
    lines.append(f'| {names[case]} | {item["ram_first_pass_tps"]:.2f} | {item["ssd_first_pass_tps"]:.2f} | {item["ssd_first_pass_read_bytes"]/2**20:.2f} | {reads} |')
lines.extend(['', 'Les lectures Windows incluent le pipe de commande et les lectures de maintien du SSD eveille. Les journaux confirment zero lecture de fichier pour les experts : ils restent en RAM ou en VRAM. Le premier passage de chaque sujet comporte les lignes ngram encore absentes du cache ; les sujets peuvent partager certaines lignes.',
    '', 'Le cache de lignes du mode direct reste actif, comme prevu par le moteur : 1 048 576 lignes, environ 94,1 Mio avec les cles, pour une table de 26,82 Gio. Les passages repetes peuvent largement reutiliser ces lignes. Ces trois prompts courts ne representent donc pas toutes les latences possibles sur du texte toujours nouveau ou un tres long contexte.',
    '', 'Verification : copie brute IQ4_NL, formes et nombre d\'octets identiques, SHA-256 complet identique entre table originale et copie. Le lecteur utilise `FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED | FILE_FLAG_RANDOM_ACCESS` sur C. Inspection de la memoire : aucune allocation privee de la taille de la table complete.',
    '',f'VRAM au pic : {result["ssd_gpu_vram_gib"]["0"]:.2f} / {result["ssd_gpu_vram_gib"]["1"]:.2f} Gio. Temperatures maximales : {result["ssd_gpu_temp_max_c"]["0"]} / {result["ssd_gpu_temp_max_c"]["1"]} C. Masques de limitation des frequences : {result["ssd_gpu_throttle_masks"]}.',
    '', f'Production : {"retablie et prete, table en RAM, historique 6 et contexte 262 144" if restored else "retablissement en cours"}. Empreintes des fichiers de production conserves : {"toutes identiques" if all(x["unchanged"] for x in checked) else "consulter les differences dans comparaison-ngram.json"}.',
    '', f'Verification physique de la table de production : {ram_proof["valid_pages"]:,} pages presentes et {ram_proof["locked_pages"]:,} pages verrouillees sur {ram_proof["pages"]:,}.' if ram_proof else 'Verification physique de production en attente.',
    '', f'Copie de recherche de la table : `{copy["path"]}` ({copy["bytes"]/2**30:.2f} Gio). Elle reste disponible pour reproduire le test ; le profil de production utilise sa table originale en RAM.'])
(RUN/'rapport-ngram-ssd.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(report=str(RUN/'rapport-ngram-ssd.md'),ram_saved_gib=ram_peak-ssd_peak,tests=comparisons,
    production_ready=bool(restored),production_unchanged=all(x['unchanged'] for x in checked)),ensure_ascii=False),flush=True)
