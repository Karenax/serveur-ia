"""Preserve the measured Q4 8/16-core comparison and verify its common protocol."""
import csv
import hashlib
import json
from pathlib import Path
import statistics

root = Path(__file__).resolve().parent
archive = Path((root / 'comparatif-cpu8-courant.txt').read_text(encoding='utf-8-sig').strip())
folders = [('16 physiques', 'reference-16-coeurs'), ('8 regroupés', 'q4-8-compacts'),
           ('8 répartis', 'q4-8-repartis')]
data = {label: json.loads((archive / folder / 'resultats.json').read_text(encoding='utf-8-sig'))
        for label, folder in folders}
configs = [json.loads((archive / folder / 'configuration.json').read_text(encoding='utf-8-sig'))
           for _, folder in folders]
if len({cfg['binary_sha256'] for cfg in configs}) != 1:
    raise RuntimeError('Binary hashes differ')
def comparable(config):
    cfg = json.loads(json.dumps(config['config']))
    cfg.pop('log', None)
    i = cfg['args'].index('--pool-workers')
    cfg['args'][i + 1] = '<controlled worker count>'
    return cfg
if any(comparable(cfg) != comparable(configs[0]) for cfg in configs[1:]):
    raise RuntimeError('Settings other than worker count and log path differ')
for _, folder in folders:
    for name in sorted((archive / folder).glob('r*-requete.json')):
        ref = archive / 'reference-16-coeurs' / name.name
        if json.loads(name.read_text(encoding='utf-8-sig')) != json.loads(ref.read_text(encoding='utf-8-sig')):
            raise RuntimeError('Request differs: ' + str(name))
for label, rows in data.items():
    if len(rows) != 6 or any(r['ram_gpu_experts'] or not r['drafts'] for r in rows):
        raise RuntimeError('Incomplete or incompatible measurements: ' + label)
for mode, expected_mask in [('compact', 0xffff), ('spread', 0xff00ff)]:
    before = json.loads((archive / ('affinite-avant-' + mode + '.json')).read_text())
    after = json.loads((archive / ('affinite-apres-' + mode + '.json')).read_text())
    for probe in (before, after):
        if probe['process_mask_before'] != expected_mask:
            raise RuntimeError('CPU process mask changed during ' + mode)
        if any(t['mask'] & ~expected_mask for t in probe['threads_before']):
            raise RuntimeError('A thread could execute outside the eight selected cores')
        expert_masks = [t['mask'] for t in probe['threads_before'] if t['mask'] and not t['mask'] & (t['mask'] - 1)]
        # At least the seven worker masks must survive each complete six-request series.
        expected_workers = [1 << i for i in ([2,4,6,8,10,12,14] if mode == 'compact' else [16,2,18,4,20,6,22])]
        if any(mask not in expert_masks for mask in expected_workers):
            raise RuntimeError('Worker affinity was not retained in ' + mode)
results = []
names = {'ciel': 'Ciel bleu', 'fibonacci': 'Fibonacci Python', 'fourmis': 'Poésie sur les fourmis'}
for test, name in names.items():
    base = statistics.median(r['generation_tps'] for r in data['16 physiques'] if r['test'] == test)
    for label, folder in folders:
        rows = [r for r in data[label] if r['test'] == test]
        tps = statistics.median(r['generation_tps'] for r in rows)
        ref_hashes = {r['answer_sha256'] for r in data['16 physiques'] if r['test'] == test}
        results.append(dict(test=test, prompt=name, mode=label, median_tps=tps,
                            loss_percent=100 * (1 - tps / base),
                            gain_16_over_mode_percent=100 * (base / tps - 1),
                            output_tokens=[r['output_tokens'] for r in rows],
                            min_tps=min(r['generation_tps'] for r in rows), max_tps=max(r['generation_tps'] for r in rows),
                            median_mtp_acceptance=statistics.median(r['mtp_acceptance'] for r in rows),
                            average_cpu_cores=statistics.mean(r['cpu_average_cores'] for r in rows),
                            same_text_as_16=all(r['answer_sha256'] in ref_hashes for r in rows)))
(archive / 'comparaison.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
with (archive / 'comparaison.csv').open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0])); writer.writeheader(); writer.writerows(results)
lines = ['Q4_K_XL — comparaison de 8 et 16 cœurs physiques',
         'Mesures : référence à 16 cœurs du 2 octobre 2026 ; essais à 8 cœurs du 3 octobre 2026.', '',
         'Threadripper PRO 3955WX, 128 Gio DDR4-3200 sur 8 canaux, deux Tesla P100 16 Gio.',
         'Même modèle Qwen3.8-Flash-Next-UD-Q4_K_XL, même binaire Strata et mêmes caches experts GPU.',
         'MTP Q2 activé, spec=3, spec-min-p=0.5 ; thinking et cache des prompts désactivés.',
         'Deux répétitions par prompt, température 0, seed 42, contexte 4096 ; ordre inversé à la seconde répétition.',
         'Ciel et Fibonacci : limite commune de 256 tokens. Poésie : limite de 512 tokens et arrêt naturel enregistré.',
         'Débit de génération hors traitement du prompt, médiane de deux mesures.', '',
         'Prompt ; 16 cœurs ; 8 regroupés ; 8 répartis ; perte de 8 répartis par rapport à 16']
for test, name in names.items():
    rows = [r for r in results if r['test'] == test]
    lines.append(f"{name} ; {rows[0]['median_tps']:.2f} ; {rows[1]['median_tps']:.2f} ; {rows[2]['median_tps']:.2f} tokens/s ; {rows[2]['loss_percent']:.1f} %")
lines += ['', 'Le passage à 8 cœurs utilise 7 travailleurs experts plus le thread principal, contre 15+1 à 16 cœurs.',
          'Affinité effective du moteur : 8 cœurs physiques. Les frères SMT de ces mêmes cœurs restent disponibles',
          'pour les threads auxiliaires CUDA ; chaque travailleur expert est fixé à un seul processeur logique.',
          '8 regroupés : experts sur les processeurs logiques 0,2,4,6,8,10,12,14 ; masque processus 0x0000ffff.',
          '8 répartis : experts sur 0,16,2,18,4,20,6,22 ; masque processus 0x00ff00ff.',
          'Les masques de tous les threads sont vérifiés avant et après chaque série ; le principal est sur 0.',
          'Le nombre de cœurs disponibles pour les autres logiciels et le BIOS restent inchangés.', '',
          'Les trois séries ont des requêtes JSON identiques ; aucune autre option moteur ne diffère sauf le journal.',
          'Experts absents du cache GPU calculés sur CPU depuis la RAM ; 0 transfert RAM→GPU de poids experts.',
          'Tous les journaux de requêtes confirment 0 lecture de blobs experts depuis les fichiers.',
          'La prélecture des fichiers est terminée avant les benchmarks. Chargement et génération sont distingués.',
          'Le débit CPU moyen inclut les attentes actives : il ne représente pas uniquement des calculs utiles.', '',
          'Texte et longueur des réponses :']
for r in results:
    lines.append(f"{r['prompt']} / {r['mode']} : {r['output_tokens']} tokens, MTP accepté {100*r['median_mtp_acceptance']:.1f} %, texte identique à la référence : {r['same_text_as_16']}.")
lines += ['', 'Limites : seulement trois prompts courts et deux répétitions. La référence 16 cœurs provient de la veille,',
          'elle ne forme pas une série alternée 8/16/8. Les caches GPU fixes et le binaire ont été conservés.',
          'Ces résultats mesurent cette machine et ce moteur, sans isoler complètement calcul, accès RAM et synchronisations.',
          'Ils ne permettent pas d’extrapoler linéairement vers un processeur 32 cœurs ou une autre architecture.', '',
          'État final : Q4_K_XL actif sur http://127.0.0.1:8080, huit cœurs répartis et MTP activé.',
          'Redémarrer le même réglage : .\Start-Strata-P100.ps1 -CpuCores 8',
          'Revenir à 16 cœurs : arrêter le serveur, puis .\Start-Strata-P100.ps1 -CpuCores 16',
          'Binaire SHA256 : ' + configs[0]['binary_sha256'], 'Archive : ' + str(archive)]
(archive / 'RAPPORT.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')
print(json.dumps(results, ensure_ascii=False, indent=2))
