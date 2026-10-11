# Prefill Strata 0.1.41 : CPU court et RAM verrouillée — 9 octobre 2026

**Conclusion : le gain logiciel de prefill n’est pas établi. Les deux P100 limitent leur fréquence pour raison thermique. Les profils officiels sont fonctionnels sur cette suite, mais la comparaison ne justifie pas une mise à jour de production. Le refroidissement doit être corrigé avant une nouvelle comparaison.**

Deux pistes testées sur le même modèle IQ4_XS, deux P100, 15 workers CPU, découpage 24/24 couches et KV FP16. Le binaire officiel et ses sources restent inchangés.

CPU limité aux blocs de moins de 1024 tokens (`STRATA_PREFILL_CPU_SHARE=auto`, `STRATA_PREFILL_CPU_SHARE_MAX=1024`). La variante RAM verrouillée remplace `--resident-cpu-experts` par `--resident-experts`. Le profil 4096, s’il apparaît dans les résultats, augmente aussi le bloc de prefill de 2048 à 4096.

Les profils officiels activent le diagnostic `STRATA_PREFILL_TIMING=1`. Les temps incluent son coût. Aucun cache de prompt réutilisé. Le long dossier est mesuré deux fois sur chaque profil. La seconde lecture ajoute un bref identifiant au début afin d’invalider le cache vivant de Strata ; chaque profil reçoit exactement les mêmes deux variantes. La première tentative de répétition identique, servie depuis le cache, a été exclue et conservée dans le dossier `prefill-court-pin-20261009-reference-invalidee`.

| Profil | 1 534 tokens : premier texte | 5 950 tokens : premier texte | Environ 23 600 tokens : médiane (deux essais) | Génération / actuel |
|---|---:|---:|---:|---:|
| Actuel 0.1.35 | 7.69 s | 22.05 s | 166.00 s | référence |
| cpu-court | 7.84 s | 22.30 s | 168.45 s | +14.4% |
| cpu-court-pin | 7.55 s | 18.12 s | 155.59 s | +13.4% |

## Température et validité de la comparaison

Les P100 ont signalé un ralentissement thermique logiciel (`SW Thermal Slowdown`, masque 0x20). La nouvelle référence de production peut donc être beaucoup plus lente que les 67–70 s mesurées auparavant. Un gain contre cette référence chaude ne démontre pas à lui seul un progrès du moteur.

| Profil / lecture longue | Température maximale observée | Fréquence SM médiane | Échantillons avec limitation thermique |
|---|---:|---:|---:|
| production / dossier-1024 | 80 °C | 562 MHz | 29/52 |
| production / dossier-1024-repeat2 | 80 °C | 550 MHz | 56/114 |
| cpu-court / dossier-1024 | 80 °C | 607 MHz | 54/104 |
| cpu-court / dossier-1024-repeat2 | 81 °C | 424 MHz | 75/112 |
| cpu-court-pin / dossier-1024 | 81 °C | 632 MHz | 48/88 |
| cpu-court-pin / dossier-1024-repeat2 | 81 °C | 430 MHz | 80/112 |

Échantillonnage toutes les trois secondes, deux GPU réunis. Le suivi a commencé pendant la première lecture longue de la référence ; ses premiers instants ne sont pas couverts. Aucun réglage thermique ni limite de puissance n’a été modifié.

Le verdict logiciel doit aussi retrouver les 67–70 s historiques et être confirmé avec un refroidissement comparable. Les essais précédents sans relevé de température ne permettent pas d’attribuer toute leur différence au logiciel.

## Contrôles et limites

- cpu-court : valeurs correctes 8/8, JSON strict 6/8. Seuil de comparaison à la référence de cette session atteint ; cela ne valide pas une mise à jour en présence de limitation thermique.
  État RAM observé : FileExpertSource: pageable resident cache complement ready: resident 51.54 GiB, pinned 0.00 GiB in 69 s
- cpu-court-pin : valeurs correctes 8/8, JSON strict 6/8. Seuil de comparaison à la référence de cette session atteint ; cela ne valide pas une mise à jour en présence de limitation thermique.
  État RAM observé : FileExpertSource: mapped pinned cache complement ready: resident 51.54 GiB, pinned 51.54 GiB in 186 s; page-locked and mapped

Le seuil calculé par le pilote demande au moins 97 % du débit de génération actuel et 95 % du débit de prefill sur chaque dossier, avec des valeurs attendues correctes. Il compare la référence chaude de cette session. Une validation de mise à jour doit en plus retrouver les 67–70 s historiques et éliminer le biais thermique. Les contrôles tolèrent les balises Markdown autour du JSON ; leur présence est signalée séparément. Les deux réponses explicatives sont seulement vérifiées non vides : ce test n’est pas une validation générale de qualité.

## Diagnostic sur le long dossier

- cpu-court : gemm gate/up 95.94 s, gemm down 51.92 s, embed+steps 42.10 s, gdn 29.89 s, hc read 16.32 s, qsa attn 15.45 s.
- cpu-court-pin : gemm gate/up 91.78 s, gemm down 48.56 s, embed+steps 34.02 s, gdn 28.40 s, hc read 15.35 s, qsa attn 14.54 s.

Les phases sont des sommes de segments de chronologie GPU. Une phase peut inclure une attente du CPU ou des copies. Le détail brut est dans `diagnostic-phases.json` ; les temps par phase ne sont pas des mesures de calcul pur.

## Reprise

Production 0.1.35 rétablie et vérifiée (PID 26180). Une vraie réponse a donné 301 pour 43 × 7. Port 8081 fermé ; les cinq empreintes de production sont inchangées.

## Sources examinées

- [Documentation du partage CPU officiel](https://github.com/Niko1221/Strata/blob/v0.1.41/docs/DETAILS.md#short-prompts-the-cpu-shares-the-experts-on-by-default-on-one-nvidia-gpu-strata_prefill_cpu_share).
- [Rapport communautaire 2 P100](https://github.com/Niko1221/Strata/pull/1157) : autre quantification IQ3_S et Linux, utile pour identifier des pistes, chiffres non comparables directement à notre IQ4_XS sous Windows.
- [Correction cuBLAS 12 proposée](https://github.com/Niko1221/Strata/pull/1659) : concerne des échecs de GEMM ; non appliquée, nos essais ne rencontrent pas cette erreur.

- [NVIDIA : signification du ralentissement thermique logiciel](https://docs.nvidia.com/deploy/archive/R510/nvml-api/group__nvmlClocksThrottleReasons.html).
