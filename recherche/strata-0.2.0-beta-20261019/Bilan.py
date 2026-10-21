"""Report the completed matched campaign from saved evidence, without inference."""
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
RUN = HERE / 'mesures/essai-01'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def records(arm):
    return {row['name']: row for row in read(RUN / arm / 'results.json')}


def telemetry(arm):
    return [json.loads(line) for line in (RUN / ('telemetrie-' + arm + '.jsonl')).read_text().splitlines() if line]


def main():
    old, new = 'reference-sans-seuil', 'nouveau-sans-seuil'
    data = {arm: records(arm) for arm in (old, new)}
    summary = {'generation': {}, 'documents': {}, 'functional': {}, 'temperature_cutoff': None}
    lines = ['# Comparaison réelle Strata 0.1.43.1 / paquet moteur 0.1.45.3', '',
             'Essais du 19 octobre 2026 sur Flash-Next Uncensored IQ4_XS, deux P100 16 Gio, split 24, préfill 2048, 15 workers, MTP 3 / seuil 0,5, contexte configuré 262144. Le serveur Python corrigé et la vision P2200 sont conservés. Le nouveau moteur utilise les DLL CUDA de son paquet officiel ; ses sept réglages P100 sont confirmés actifs dans le journal.', '',
             '## Génération : comparaison finale commune', '',
             'Chaque moteur a été chargé, a lu un document de 23,6K tokens puis a enchaîné les mêmes six requêtes texte/code (trois paires), sans pause de refroidissement. Le seuil artificiel de 80 °C a été supprimé à la demande explicite de l’utilisateur. Les fréquences et le bridage matériel restent relevés. Les médianes portent sur trois requêtes par cas, dans un processus par moteur ; ce sont des séries courtes, pas une validation de débit continu sur plusieurs heures.', '',
             '| Cas | 0.1.43.1 | 0.1.45.3 | Débit |', '|---|---:|---:|---:|']
    identical = 0
    for case in ('ciel', 'fibonacci-code'):
        values = {}
        for arm in (old, new):
            selected = [data[arm][f'serie-r{i}-{case}'] for i in (1, 2, 3)]
            assert all(row['quality_pass'] and row['timings']['cache_n'] == 0 for row in selected)
            values[arm] = [row['timings']['predicted_per_second'] for row in selected]
        for i in (1, 2, 3):
            name = f'serie-r{i}-{case}'
            assert read(RUN / old / (name + '-request.json')) == read(RUN / new / (name + '-request.json'))
            identical += data[old][name]['text_sha256'] == data[new][name]['text_sha256']
        medians = {arm: statistics.median(values[arm]) for arm in (old, new)}
        change = medians[new] / medians[old] - 1
        summary['generation'][case] = {'reference_tok_s': medians[old], 'new_tok_s': medians[new],
                                      'gain_percent': change * 100, 'reference_samples': values[old], 'new_samples': values[new]}
        lines.append(f'| {case} | {medians[old]:.2f} tok/s | {medians[new]:.2f} tok/s | {change:+.1%} |')
    lines += ['', 'Les premières mesures de génération, dont la chauffe différait, restent archivées mais ne servent pas à ce tableau.', '',
              '## Lecture des documents', '',
              'Médianes de deux requêtes identiques par moteur, sans réutilisation du prompt. Ces mesures ont été effectuées dans la phase initiale avec départ à 55 °C ou moins. La seconde lecture longue du nouveau moteur a atteint 80 °C sans bridage thermique déclaré : elle est conservée selon la consigne ultérieure de l’utilisateur, sans modifier les fichiers bruts où l’ancien critère avait marqué thermally_valid=false.', '',
              '| Taille moteur | 0.1.43.1 | 0.1.45.3 | Débit de lecture |', '|---|---:|---:|---:|']
    for count in (64, 256, 1024):
        durations = {}
        for arm in ('reference-0.1.43.1', 'nouveau-0.1.45.3'):
            source = records(arm)
            rows = [source[f'dossier-{count}-r{i}'] for i in (1, 2)]
            assert all(row['quality_pass'] and row['timings']['cache_n'] == 0 for row in rows)
            durations[arm] = statistics.median(row['timings']['prompt_ms'] / 1000 for row in rows)
        for i in (1, 2):
            name = f'dossier-{count}-r{i}'
            assert read(RUN / 'reference-0.1.43.1' / (name + '-request.json')) == read(RUN / 'nouveau-0.1.45.3' / (name + '-request.json'))
        a, b = durations['reference-0.1.43.1'], durations['nouveau-0.1.45.3']
        n = rows[0]['usage']['prompt_tokens']
        summary['documents'][str(n)] = {'reference_seconds': a, 'new_seconds': b, 'throughput_gain_percent': (a / b - 1) * 100}
        lines.append(f'| {n} tokens | {a:.2f} s | {b:.2f} s | {a / b - 1:+.1%} |')

    tool = read(RUN / new / 'outil-verification.json')
    vision = read(RUN / new / 'vision-verification.json')
    cache = read(RUN / new / 'cache-verification.json')
    assert tool['passed'] and vision['passed']
    restored = data[new]['cache-A-restaure']
    ratio = restored['timings']['cache_n'] / restored['usage']['prompt_tokens']
    assert cache['same_content'] and ratio > .9 and cache['metrics']['conversation_cache']['restores'] >= 1
    summary['functional'] = {'tools': tool, 'vision': vision,
                            'cache': {'same_content': True, 'reused_fraction': ratio, 'restore_wall_seconds': restored['elapsed_s'],
                                      'prompt_tokens': restored['usage']['prompt_tokens'], 'reused_tokens': restored['timings']['cache_n']}}
    lines += ['', '## Vérifications réelles', '',
              '- Appel d’outil : booléen false et chaîne "True" conservés avec leur type attendu. Aucune fonction hôte exécutée.',
              '- Image synthétique : texte VISION 47, cercle rouge et carré bleu reconnus dans le JSON demandé, via la P2200.',
              f'- Cache : trois conversations textuelles alternées ; retour à A en {restored["elapsed_s"]:.2f} s, réponse identique à la référence, {ratio:.2%} du prompt réutilisé ({restored["timings"]["cache_n"]}/{restored["usage"]["prompt_tokens"]} tokens).',
              '- Cache configuré à 20 emplacements / 30720 Mio et réserve RAM 6144 Mio. L’essai porte sur environ 2,1K tokens par conversation ; ni les retours à 32K tokens, ni le remplissage complet du cache, ni les 262K tokens de contexte ne sont testés.',
              f'- Génération : {identical}/6 réponses finales identiques entre moteurs. Les réponses et le code sont conservés ; leur présence ne démontre pas une qualité générale équivalente. Les calculs et codes cachés des documents ont des contrôles de valeur exacts.']
    summary['identical_generation_responses'] = identical
    summary['thermal'] = {}
    for arm in (old, new):
        samples = [s for s in telemetry(arm) if s.get('phase') == 'inference' and s.get('case') != 'reprise-calcul' and 'rows' in s]
        peak = max(gpu['temperature_c'] for sample in samples for gpu in sample['rows'])
        throttled = sum(any(gpu['throttle_mask'] & 0x60 for gpu in sample['rows']) for sample in samples)
        summary['thermal'][arm] = {'sampled_max_c': peak, 'hardware_thermal_throttle_samples': throttled}
        lines.append(f'- {arm} : maximum échantillonné {peak:.0f} °C, {throttled} échantillon(s) de bridage thermique matériel. Aucun arrêt manuel à 80 °C dans la série finale.')

    recovery = read(RUN / 'production-retablie.json')
    assert recovery['old_engine_restored'] and recovery['fingerprints_identical'] and recovery['console_identical']
    assert recovery['test_error'] is None and recovery['test_port_closed']
    assert recovery['temperature_cutoff'] is None
    summary['production_restored'] = True
    prepared = read(HERE / 'engine-prepared.json')
    summary['package'] = prepared
    lines += ['', '## État final et portée', '',
              'Production remise sur 0.1.43.1, modèle chargé, calcul réel 43 × 7 = 301 vérifié, console conservée, port de test fermé. Empreintes des réglages persistants et configurations d’accès identiques. Le paquet nouveau reste isolé dans ce dossier ; aucun pilote ni poids de modèle n’a été remplacé.', '',
              'Le paquet officiel annonce 0.1.45.3 / CUDA 12.9, build f6d65cb584c0 ; son --version affiche 0.1.45. SHA-256 de l’archive et des sept fichiers, plus signature Ed25519, vérifiés. Le manifeste annonce un pilote minimal 576.02 alors que le poste utilise 528.89 : les réussites observées ici ne changent pas cette exigence déclarée et ne valident pas tous les chemins CUDA.', '',
              'Les tests concernent le moteur derrière notre serveur Python 0.1.43.1 corrigé, pas la nouvelle application ni son serveur non corrigé. Les chargements ont bénéficié de prélectures séquentielles et de la réduction ponctuelle des pages par le superviseur : aucun temps de démarrage froid comparable n’est revendiqué. La protection RAM reste active.', '',
              'Les premières tentatives, l’erreur initiale du pilote d’attente et le premier arrêt à 80 °C sont conservés dans les journaux. La série finale commune a été rejouée après suppression du seuil. Requêtes, réponses, configurations, empreintes et télémétrie toutes les deux secondes : mesures/essai-01/.']
    (HERE / 'RESULTATS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (HERE / 'resultats-synthese.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
