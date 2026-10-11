# Essai Strata officiel 0.1.41 avec CPU au prefill — 9 octobre 2026

Essai local sur deux Tesla P100 et Threadripper PRO 3955WX. Le binaire officiel et le modèle sont identiques à l’essai 0.1.41 précédent. La source officielle, commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, est inchangée. La production reste sur 0.1.35 avec notre hybride P100.

## Configuration

- `STRATA_PREFILL_CPU_SHARE=auto` ; plafond `STRATA_PREFILL_CPU_SHARE_MAX=3072`.
- Prefill par blocs de 2048 tokens ; répartition de 24 couches par P100 ; 15 workers CPU.
- Experts absents du cache GPU conservés en RAM pageable (`--resident-cpu-experts`).
- Aucun cache de prompt réutilisé : `cache_n=0` pour toutes les mesures.
- Variables vérifiées dans l’environnement du véritable processus moteur (preuve : `processus-test.json`).

## Temps avant le premier texte

| Tokens du prompt | Hybride actuel, nouvelle mesure | Officiel 0.1.41 sans CPU, mesure du 8 octobre | Officiel 0.1.41 avec CPU | Écart CPU / actuel |
|---:|---:|---:|---:|---:|
| 1534 | 7.63 s | 7.86 s | 7.12 s | -6.6% |
| 5950 | 17.86 s | 18.03 s | 18.54 s | +3.8% |
| 23614 | 67.19 s | 83.83 s | 105.00 s | +56.3% |

Débit de génération : écart médian de +13.4% par rapport à l’hybride actuel sur les neuf mesures.

Contrôles exacts : 7/7 réussis, plus l’échauffement JSON réussi. Les deux réponses explicatives sont non vides ; cette vérification ne constitue pas une évaluation générale de leur qualité.

Format JSON strict : 5/7 réponses respectent le contrat sans nettoyage. Les deux réponses Fibonacci contiennent les bonnes valeurs, entourées de balises Markdown ; le contrôle fonctionnel accepte ces balises. L’étiquette `quality_pass` ne signifie donc pas que tous les contrats de format sont respectés.

Le mode automatique partage le travail selon les temps CPU/GPU observés. Ce test ne garantit pas des réponses identiques bit à bit entre deux exécutions.

## Activité CPU observée

| Prompt | Temps CPU cumulé avant le premier texte | Cœurs CPU utilisés en moyenne |
|---|---:|---:|
| dossier-64 | 44.4 s | 6.42 |
| dossier-256 | 163.4 s | 8.92 |
| dossier-1024 | 835.8 s | 7.96 |

Ces compteurs portent sur tout le processus moteur pendant le prefill ; ils ne donnent pas le nombre précis d’experts traités par le CPU.

## Décision et reprise

Critère de comparaison : contrôles réussis, génération ≥97 % de la référence et débit de prefill ≥95 % sur chacun des trois dossiers. Résultat : non acceptable pour remplacer le moteur actuel.

Le moteur actuel 0.1.35 est rétabli, PID 13576. Une véritable inférence après reprise a répondu `301` à `43 × 7`. Le port de test 8081 est fermé et les cinq empreintes de fichiers de production sont inchangées.

Les données détaillées, réponses, échantillons CPU et journaux restent dans ce dossier. Les mesures sans CPU du 8 octobre sont indicatives ; la comparaison décisive utilise la nouvelle référence de production juste avant cet essai. Chaque taille de dossier a été mesurée une fois : des répétitions seraient nécessaires pour caractériser la variance.
