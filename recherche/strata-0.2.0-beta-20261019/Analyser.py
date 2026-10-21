"""Summarize saved measurements only; never calls the model."""
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
RUN = HERE / 'mesures/essai-01'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    arms = ['reference-0.1.43.1', 'nouveau-0.1.45.3']
    results = {arm: read(RUN / arm / 'results.json') for arm in arms}
    records = {arm: {row['name']: row for row in rows} for arm, rows in results.items()}
    summary = {}
    lines = ['# Comparaison réelle des moteurs Strata — 19 octobre 2026', '',
             'Même modèle Flash-Next Uncensored IQ4_XS, mêmes deux P100, split 24, préfill 2048, 15 workers, MTP 3 / seuil 0,5, contexte 262144, serveur Python 0.1.43.1 avec correctifs Fred et vision P2200 conservés. Seuls le moteur et ses bibliothèques CUDA changent. Aucune installation du nouveau serveur ou de son application.', '',
             '## Génération', '',
             'La référence initiale était instable pendant la préparation du paquet : les deux premières répétitions sont conservées mais exclues de cette synthèse. La référence a ensuite fait la répétition 3, les documents, puis 4 et 5. Le premier pilote nouveau avait exécuté 3 à 5 avant les documents. Les répétitions après documents prévues pour aligner la chauffe n’ont pas été exécutées, car la seconde lecture longue a atteint le seuil d’arrêt à 80 °C. Les médianes 3 à 5 ci-dessous sont donc descriptives et ne permettent pas d’attribuer un gain ou une régression au moteur. Les requêtes sont identiques ; un processus mesuré par moteur, sans redémarrage entre répétitions.', '',
             '| Cas | 0.1.43.1 tok/s (médiane et étendue) | 0.1.45.3 tok/s (médiane et étendue) |', '|---|---:|---:|']
    for case in ('ciel', 'fibonacci-code'):
        values = {}
        for arm in arms:
            chosen = [records[arm][f'r{i}-{case}'] for i in (3, 4, 5)]
            assert all(x['thermally_valid'] for x in chosen)
            values[arm] = statistics.median(x['timings']['predicted_per_second'] for x in chosen)
        gain = values[arms[1]] / values[arms[0]] - 1
        summary[case] = {'reference_tok_s': values[arms[0]], 'new_tok_s': values[arms[1]], 'gain_percent': gain * 100}
        ranges = {arm: [records[arm][f'r{i}-{case}']['timings']['predicted_per_second'] for i in (3, 4, 5)] for arm in arms}
        summary[case]['comparison_validated'] = False
        lines.append(f'| {case} | {values[arms[0]]:.2f} ({min(ranges[arms[0]]):.1f}–{max(ranges[arms[0]]):.1f}) | {values[arms[1]]:.2f} ({min(ranges[arms[1]]):.1f}–{max(ranges[arms[1]]):.1f}) |')
    lines += ['', '## Lecture des documents', '',
              'Durée moteur de lecture du prompt, hors génération. Médianes des requêtes qui respectent le critère thermique, cache de prompt nul. La taille en tokens est celle du moteur. Pour 23,6K, un seul essai nouveau respecte le seuil : le second donne 54,265 s mais atteint 80 °C, il est exclu.', '',
              '| Taille | 0.1.43.1 | 0.1.45.3 | Accélération du débit | Essais retenus ancien / nouveau |', '|---|---:|---:|---:|---:|']
    for count in (64, 256, 1024):
        values = {}
        for arm in arms:
            chosen = [records[arm][f'dossier-{count}-r{i}'] for i in (1, 2) if records[arm][f'dossier-{count}-r{i}']['thermally_valid']]
            assert all(x['thermally_valid'] and x['quality_pass'] and x['timings'].get('cache_n', 0) == 0 for x in chosen)
            values[arm] = statistics.median(x['timings']['prompt_ms'] / 1000 for x in chosen)
        n = chosen[0]['usage']['prompt_tokens']
        speedup = values[arms[0]] / values[arms[1]]
        summary[f'dossier-{count}'] = {'tokens': n, 'reference_seconds': values[arms[0]], 'new_seconds': values[arms[1]], 'speedup': speedup}
        kept = [sum(records[arm][f'dossier-{count}-r{i}']['thermally_valid'] for i in (1, 2)) for arm in arms]
        lines.append(f'| {n:,} tokens | {values[arms[0]]:.2f} s | {values[arms[1]]:.2f} s | {speedup - 1:+.1%} | {kept[0]} / {kept[1]} |'.replace(',', ' '))
    thermal = {}
    for arm in arms:
        samples = [json.loads(s) for s in (RUN / ('telemetrie-' + arm + '.jsonl')).read_text().splitlines() if s]
        samples = [s for s in samples if 'rows' in s]
        thermal[arm] = {'max_temperature_c': max(v['temperature_c'] for s in samples for v in s['rows']),
                        'thermal_throttle_samples': sum(any(v['throttle_mask'] & 0x60 for v in s['rows']) for s in samples),
                        'min_available_ram_gib': min(s['ram_available_gib'] for s in samples)}
    summary['telemetry'] = thermal
    lines += ['', '## Vérifications et limites', '',
              '- Départ des requêtes à 55 °C ou moins, avec pauses de refroidissement. Ces débits ne mesurent pas une charge continue.',
              f'- Température maximale échantillonnée : référence {thermal[arms[0]]["max_temperature_c"]:.0f} °C, nouveau {thermal[arms[1]]["max_temperature_c"]:.0f} °C. Échantillons avec limitation thermique : {thermal[arms[0]]["thermal_throttle_samples"]} / {thermal[arms[1]]["thermal_throttle_samples"]}.',
              '- Les vérifications arithmétiques et les codes cachés dans les documents sont contrôlés automatiquement ; les réponses de texte et de code sont conservées, mais leur seule présence ne mesure pas la qualité générale du modèle.',
              '- La seconde lecture longue a atteint 80 °C, seuil du protocole repris de la campagne précédente. Aucun échantillon ne signale de bridage thermique matériel. Le pilote a interrompu la campagne puis restauré la production : il ne s’agit ni d’un crash du moteur ni d’une erreur de lecture du document.',
              '- Les tests réels d’outils, d’image et d’alternance de conversations n’ont pas été exécutés : l’arrêt thermique les précède. Aucune validation fonctionnelle complète ni validation de charge continue du nouveau moteur n’est revendiquée.']
    common = sorted(set(records[arms[0]]) & set(records[arms[1]]))
    compared = [name for name in common if name.startswith(('r3-', 'r4-', 'r5-', 'dossier-'))]
    equal = sum(records[arms[0]][name]['text_sha256'] == records[arms[1]][name]['text_sha256'] for name in compared)
    summary['identical_text'] = {'equal': equal, 'compared': len(compared)}
    lines.append(f'- Sorties textuelles identiques sur les requêtes communes sélectionnées : {equal}/{len(compared)}. Cela ne constitue pas une preuve générale d’identité numérique.')
    for name, title in [('outil-verification.json', 'Appel d’outil booléen'), ('vision-verification.json', 'Image : code et formes'), ('cache-verification.json', 'Alternance des conversations')]:
        path = RUN / arms[1] / name
        data = read(path) if path.exists() else {'not_run': True, 'reason': 'thermal protocol stop'}
        summary[name] = data
        lines.append(f'- {title} : ' + ('non exécuté.' if data.get('not_run') else ('réussi.' if data.get('passed', data.get('same_content')) else 'échec.')))
    restore = read(RUN / 'production-retablie.json')
    summary['production_restored'] = restore['old_engine_restored'] and restore['fingerprints_identical'] and restore['console_identical']
    lines += ['', '## Paquet et remise en service', '',
              'Paquet officiel 0.1.45.3 CUDA 12.9, SHA-256 et signature Ed25519 vérifiés. BUILD.json annonce le commit f6d65cb584c0. Le --version du binaire affiche 0.1.45 ; la version 0.1.45.3 est celle du paquet officiel. Le manifeste annonce un pilote minimal 576.02, supérieur au pilote installé 528.89 : les essais ci-dessus constituent nos observations locales et ne modifient pas cette exigence déclarée. Aucun pilote n’a été mis à jour.', '',
              'La production a été remise sur son moteur 0.1.43.1. Calcul réel 43 × 7 = 301 vérifié après reprise, console conservée, empreintes des réglages persistants et configurations d’accès identiques.', '',
              'Une première tentative a été interrompue par une variable non initialisée dans le pilote de test avant le chargement du nouveau moteur. Le pilote a déclenché la reprise prévue ; cette reprise a été arrêtée pendant son chargement pour reprendre le test après correction. Une tentative de relance du pilote a également constaté l’absence normale du port HTTP pendant ce chargement. Les journaux des tentatives sont conservés séparément. Ces événements ne sont pas comptés comme des échecs d’inférence du moteur.', '',
              'Une prélecture séquentielle en lecture seule, issue de la procédure déjà utilisée le 16 octobre, a aidé le chargement des experts. Elle contrôle une réserve de RAM de 24 Gio et ne réduit que son propre ensemble de travail. Le superviseur conserve sa protection RAM. Les durées de démarrage ne sont pas comparables à un démarrage froid et ne font pas partie du classement de performances.', '',
              'Preuves : requêtes et réponses complètes sous mesures/essai-01/, résultats JSON et télémétrie toutes les deux secondes. Le profil nouveau conserve les paramètres utilisateur et applique les nouveaux réglages automatiques du binaire. Le gain éventuel n’est donc pas attribué à un seul réglage.']
    (HERE / 'RESULTATS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (HERE / 'resultats-synthese.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
