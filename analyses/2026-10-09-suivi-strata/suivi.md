# Strata : état des essais et nouveautés vérifiées le 9 octobre 2026

La dernière version publiée reste [0.1.41](https://github.com/Niko1221/Strata/releases/tag/v0.1.41), sortie le 8 octobre à 14 h 14 à Paris. L’API GitHub confirme que `main` est identique au tag, sans commit supplémentaire. Il existe toutefois de nouvelles propositions ouvertes, non intégrées à la version publiée. Les vérifications sont enregistrées dans `verification.json` et les descriptions des propositions dans `propositions.json`.

Le serveur actif répond toujours avec notre moteur **0.1.35**, modèle IQ4_XS, `pcie_frac=0`, 15 workers CPU. Cette vérification n’a arrêté ni relancé le serveur et n’a pas lancé de nouveau benchmark GPU.

## Ce qui a réellement été testé

**Oui, le moteur 0.1.41 a été testé en hybride CPU + deux GPU**, dans deux configurations :

- Hybride officiel : deux P100 en partage de couches 24/24, experts du cache sur GPU et experts manquants calculés sur CPU (`--pcie-frac 0`), complément résident en RAM, 15 workers, MTP, même modèle et table PLE sur SSD que la production.
- Même hybride avec le chemin FP16 existant du moteur officiel forcé par `STRATA_BF16_TC=2` et `STRATA_PREFILL_BF16X2=0`.

Il s’agit du **binaire officiel configuré en hybride**, puis d’une adaptation de ses réglages numériques. Nous n’avons pas recompilé une 0.1.41 avec l’intégralité de notre ancien patch P100. Les journaux officiels indiquent 51,54 Gio d’experts résidents, mais **pageables et non verrouillés** ; zéro blob expert lu sur disque pendant les requêtes. Cette garantie diffère de notre patch de production.

| Configuration | Gain médian de génération sur nos neuf requêtes | Premier texte, document de 23 614 tokens |
|---|---:|---:|
| Notre hybride 0.1.35 | Référence | 69,54 s |
| Hybride officiel 0.1.41 | +14,0 % | 83,83 s |
| Hybride 0.1.41 avec FP16 | +14,9 % | 88,94 s |

Sept vérifications exactes de calcul ou d’extraction réussissent dans chaque configuration ; les deux autres réponses servent à mesurer le débit. Le grand document n’a été exécuté qu’une fois par configuration. Ce corpus montre une régression à investiguer, sans établir la qualité générale ni les performances à 262 144 tokens. [Mesures détaillées](../../recherche/strata-0.1.41-test-20261008/RESULTATS.md).

## Ce qui n’a pas été testé

- Le nouveau partage CPU pendant le **prefill** : `STRATA_PREFILL_CPU_SHARE=0` était fixé dans nos deux essais. Le CPU aidait bien la génération, mais pas la lecture du prompt. La [documentation 0.1.41](https://github.com/Niko1221/Strata/blob/v0.1.41/docs/DETAILS.md#short-prompts-the-cpu-shares-the-experts-on-by-default-on-one-nvidia-gpu-strata_prefill_cpu_share) permet une activation explicite sur un partage de couches.
- `--trim-stage-weights` et `--pipeline-windows 2` : profils préparés, sans résultats mesurés.
- Le prefill automatique, une campagne de tailles de chunks, des lectures 32K/64K/262K répétées et les changements de conversation sur le nouveau moteur.
- Les nouvelles propositions du 9 octobre ci-dessous.

## Nouveautés pertinentes encore proposées

Les bénéfices annoncés ci-dessous sont ceux des auteurs ; aucun n’a été reproduit sur notre machine.

| Proposition ouverte | Contenu et limites pour nous |
|---|---|
| [#1660 — tri des experts résidents pour les packs natifs](https://github.com/Niko1221/Strata/pull/1660) | Mesurée sur quatre GP100 sm_60, 35K tokens en 63,3 → 54,1 s, réponses identiques. Même famille d’architecture que nos P100, mais tous les experts sont résidents sur ces cartes : notre hybride à cache GPU partiel ne permet pas de transposer ce gain. |
| [#1659 — récupération des erreurs FP16 de cuBLAS 12](https://github.com/Niko1221/Strata/pull/1659) | Certaines tailles de matrices échouent après initialisation de plusieurs GPU ; repli ciblé sur un algorithme cuBLAS. Test auteur sur RTX 2080 Ti + P100. Pertinent pour la compatibilité de la variante FP16, mais notre essai n’a pas rencontré cette erreur et ce correctif ne prouve pas une résolution de notre ralentissement. |
| [#1704 — cache de la couche active pendant le prefill](https://github.com/Niko1221/Strata/pull/1704) | Environ +7 % mesuré sur une P4, expérimental. La proposition refuse actuellement le multi-GPU : ce n’est pas une accélération directement activable sur notre partage 24/24. |
| [#1695 — mesures de taille automatique du prefill](https://github.com/Niko1221/Strata/pull/1695) | Résultats sur une P4 avec le dimensionnement automatique déjà existant, pas un nouveau moteur. Justifie d’inclure les tailles de chunks dans nos prochains essais ; notre référence était déjà à 2 048, pas à 512 comme la comparaison de l’auteur. |
| [#1696 — chargement RAM non bufferisé sous Windows](https://github.com/Niko1221/Strata/pull/1696) | Accélère le démarrage d’un pack `experts.bin` sur NVMe. Exclut explicitement la lecture directe des GGUF : ne corrige pas directement notre chargement depuis les shards GGUF sur HDD. Multi-GPU non mesuré par l’auteur. |
| [#1687 — documentation du partage CPU automatique](https://github.com/Niko1221/Strata/pull/1687) | Précise que le mode `auto`, fondé sur les temps mesurés, peut varier entre deux exécutions. Une part fixe ou le mode désactivé est préférable pour les essais de reproductibilité. Proposition documentaire, pas un gain de vitesse. |

Les autres nouveautés examinées sont moins directement applicables : [#1656](https://github.com/Niko1221/Strata/pull/1656) étend les fenêtres pipeline à trois étages ou plus ; [#1529](https://github.com/Niko1221/Strata/pull/1529) propose un cache de conversations sur disque, actuellement mono-GPU. Leur existence ne valide pas notre configuration à deux P100.

## Suite recommandée

Conserver le serveur actuel. Pour la prochaine campagne, viser la lecture des prompts : partir de l’hybride officiel, comparer une aide CPU explicite au prefill et les tailles de chunks, puis mesurer `trim` et le pipeline deux cartes séparément. Répéter le grand document en alternant les configurations, avec contrôles de qualité et de résidence. Vérifier l’applicabilité des modifications proposées avant d’en porter une dans une copie isolée.

La 0.1.41 hybride est donc **testée mais pas validée pour remplacer la production**. Les options d’accélération restantes et les propositions ouvertes n’ont pas encore été mesurées localement.
