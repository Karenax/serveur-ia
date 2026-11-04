# Strata 0.1.56, cache RTX et DFlash2 — essais du 3 novembre 2026

**Le gain vient surtout de l'agrandissement du cache d'experts de la RTX 4080.**
Changer seulement le moteur ne montre pas de progrès. Le meilleur profil essayé
atteint 62,2 à 63,1 tokens/s en médiane de trois générations par passage,
contre 57,7 avec les réglages hérités de la 3080 : environ **+8 à +9 %**.
L'avantage supplémentaire de DFlash2 sur le MTP avec cache agrandi est faible
dans cette petite campagne et n'est pas établi statistiquement.

## Comparaison mesurée

| Moteur et profil | Génération médiane | Préfill de 5 932 tokens |
| --- | ---: | ---: |
| 0.1.54, MTP 3, cache primaire 1 — premier test 4080 | 57,7 tok/s | 667,70 tok/s |
| 0.1.56, mêmes réglages | 56,4 tok/s | 651,80 tok/s |
| 0.1.54, MTP 3, cache primaire auto | 60,6 tok/s | 723,45 tok/s |
| 0.1.56, MTP 3, cache primaire auto | 61,8 tok/s | 728,95 tok/s |
| 0.1.56, DFlash2, cache auto, confiance 0,8 | 63,1 tok/s | 728,90 tok/s |
| 0.1.56, DFlash2, cache auto, confiance 0,5 | 61,0 tok/s | 731,35 tok/s |
| 0.1.56, DFlash2, confiance 0,8 — répétition | 62,2 tok/s | 703,30 tok/s |

Le dossier `v0156-dflash2-auto-c08-repeat` répète le profil à confiance 0,8,
sans compilation en parallèle : génération 62,2 tok/s. Les valeurs brutes et
les métriques complètes de cette répétition sont dans `trials-comparison.json`.
Une petite compilation du prototype IO a eu lieu pendant le premier passage
DFlash2 ; celui-ci reste une mesure exploratoire, complétée par cette répétition.

Trois réponses de 256 tokens, deux lectures par longueur et les mêmes prompts
fictifs sont utilisés. Contexte configuré 262144, KV INT8, fenêtre résidente 20480,
préfill 2048, quinze workers, réserve VRAM 1600 Mio. La RTX est CUDA0, les deux
P100 gardent leurs experts distants, la P2200 n'est pas utilisée pour ces essais
texte. Tous les caches de prompt et de conversation sont désactivés.

Ce n'est pas une comparaison générale des drafters sur tous les usages. Le débit
de génération vient d'une demande d'explication en français ; le code, les outils
et les longues conversations peuvent donner d'autres résultats. Les quelques
répétitions ne constituent pas une preuve de significativité statistique.
Les temps de chargement ne sont pas des mesures de démarrage à froid.

## Mémoire et contrôles

Le cache automatique sur le 0.1.56/MTP place 2389 experts sur la RTX, au lieu
d'un seul. Le complément CPU passe d'environ 30,82 à 24,90 Gio. Avec DFlash2,
le moteur place 2487 experts sur la RTX, environ 6,17 Gio, et garde environ
24,65 Gio d'experts côté CPU. Les deux P100 restent remplies de caches distants.
Les journaux conservent les états exacts de verrouillage RAM.

Le moteur confirme explicitement le chargement de DFlash2, de son drafter
de 625 Mio et de sa tête de vocabulaire d'environ 213 Mio, **sans couche MTP**.
Le pack Q4_0/selector Q4_0 a été construit et vérifié par les outils officiels,
à partir du dépôt et de la révision épinglés dans `strata_control/drafting.py`.

Les contrôles portent sur l'arithmétique, le JSON, la négation, les codes de
documents et trois codes dispersés dans un prompt de 27683 tokens. Ce dernier
dépasse la fenêtre KV en VRAM ; il ne remplit pas le contexte maximal de 262144.
Les réponses, usages, débits et nombres de tokens réutilisés sont conservés
pour chaque requête. Ces contrôles ciblés ne valident pas la qualité générale,
les images ou les appels d'outils de Kiara.

Les sept passages, dont le premier benchmark 4080, totalisent **91 requêtes** :
tous les contrôles ciblés passent, sans réutilisation de cache. Température RTX
maximale échantillonnée : **53 °C**, aucun signal thermique relevé sur les GPU.
La réserve libre annoncée par le moteur avec DFlash2 descend autour de 1,5 Gio ;
ce n'est pas un budget validé pour un autre modèle exécuté simultanément.
Les débits de préfill varient également entre les deux passages DFlash2 :
703,3 à 728,9 tok/s pour 5932 tokens. Ne pas retenir uniquement le meilleur chiffre.

Les configurations et sessions surveillées restent identiques avant et après
chaque benchmark. Les processus de test sont arrêtés par le pilote en fin de
passage. **Aucun profil permanent n'est promu par cette campagne.** Il référence
encore l'UUID de l'ancienne 3080 ; une mise en service de la 4080 devra le mettre
à jour et vérifier aussi la vision, les caches actifs et la cohabitation vocale.

## Nouveau partage multi-GPU sur Windows

Une adaptation partielle du vrai lecteur GGUF/stager du moteur split compile
et fonctionne sous Windows, y compris sur 32 Mio de données fictives.
Les API CUDA de signalisation en mémoire hôte mappée passent sur les quatre GPU.

**Le moteur split complet n'a pas été rendu opérationnel.** Le noyau matriciel
repris directement des sources compile pour la 4080, mais NVCC refuse la cible
P100 : ces instructions demandent sm_70 ou plus, alors que les P100 sont sm_60.
Le split vérifie également une architecture identique sur toutes les cartes.
Le port exige un chemin de calcul Pascal et une sélection de noyaux pour les
architectures mixtes, en plus des autres dépendances Linux à adapter.

[Rapport technique, patch, essais IO et erreur de compilation](split-windows/README.md).
Les protections d'architecture sont conservées ; aucun débit de modèle n'est
revendiqué pour ce prototype.

## Preuves et reproduction

- `trials-comparison.json` : résumés, répétitions, écarts, télémétrie et empreintes.
- `v0154-cache-auto/` et `v0156-*/` : configurations, requêtes, réponses et journaux.
- `analyze_trials.py` : recalcul des résumés à partir des résultats bruts.
- `trials-validation.json` : contrôles agrégés, empreintes conservées, arrêt et port libre.
- `trials-provenance.json` : versions et empreinte vérifiée du pack DFlash2 utilisé.
- `split-windows/` : portage IO isolé, sources des tests et résultats.
- `windows-split-prerequisites.json` : sondes CUDA exécutées sous Windows.

L'archive officielle est
`strata-engine-0.1.56-windows-x86_64-cuda-cuda12.tar.gz`, SHA-256
`70fd72378ef19207365164c5d3d171a19c4e6a86526bb4b45a15d4ca8ee61424`.
Elle est conservée avec sa provenance dans `F:/Kiara-tests/strata-0.1.56-cuda12/`.
Le moteur et ses DLL sont dans son sous-dossier `package/`. Les paquets et
modèles auxiliaires d'essai n'ont pas remplacé les installations précédentes.

Exemple pour un nouveau passage du meilleur profil, depuis la racine
(choisir un dossier de sortie inexistant et laisser le port 18080 libre) :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' -u maintenance/2026-10-30-rtx3080/benchmark.py rtx4080 --primary-gpu-uuid GPU-7d35736d-3ef5-1304-0e9e-1d26021be1a0 --context 262144 --quality-suite --long-prefill --expert-cache auto --spec 6 --draft-model F:/Kiara-tests/dflash2-0156/dflash2/qwen3.8-flash-next-dflash2.q4_0-selq4.pack --draft-conf 0.8 --engine-dir F:/Kiara-tests/strata-0.1.56-cuda12/package --output-dir maintenance/2026-11-03-rtx4080/nouveau-passage
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/2026-11-03-rtx4080/analyze_trials.py
```

Sources officielles : [version 0.2.10 / moteur 0.1.56](https://github.com/Niko1221/Strata/releases/tag/v0.2.10),
[sélection et paramètres de DFlash2](https://github.com/Niko1221/Strata/blob/v0.2.10/strata_control/drafting.py).

Les contrôles de sources passent : 511 Python, 94 JavaScript, 98 PowerShell
dans chacun des deux interpréteurs. Les trois tests du portage IO passent aussi.
