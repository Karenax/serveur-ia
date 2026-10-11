# Strata 0.1.41 et notre moteur hybride P100

Cette analyse a été rédigée **avant les essais**. Le [rapport des mesures du 8 octobre](../../recherche/strata-0.1.41-test-20261008/RESULTATS.md) et le [suivi du 9 octobre](../2026-10-09-suivi-strata/suivi.md) donnent la décision et l’état actualisés : deux hybrides 0.1.41 testés, serveur 0.1.35 conservé.

Analyse du 8 octobre 2026. **Recommandation : préparer une migration vers 0.1.41, puis décider du remplacement après un comparatif sur notre machine.** Le maintien systématique de tout notre patch P100 n'est plus justifié : plusieurs fonctions existent maintenant dans Strata. Aucun benchmark de 0.1.41 n'a été exécuté et aucun moteur de production n'a été remplacé.

## Versions et configuration vérifiées

L'API GitHub `releases/latest` renvoie **v0.1.41**, publiée le 8 octobre à 12:14:59 UTC, soit 14:14:59 à Paris. Le clone isolé de ce tag pointe sur `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`. La copie de sources est dans `source-officielle/`, déjà exclue par le `.gitignore` du projet. La référence amont est enregistrée dans `version-amont.json`.

Le `/metrics` local confirme un moteur **0.1.35**. Les sources de production sont sur `5c284bf`, notre contribution au-dessus de `d9ab843` (0.1.35), avec des modifications locales supplémentaires pour les conversations. Le processus actif utilise bien `strata-build-p100/strata.exe`.

La configuration réellement lancée, plus récente que le comparatif du 4 octobre, est :

- Deux Tesla P100 PCIe 16 Go, compute capability 6.0 ; Threadripper PRO 3955WX, 128 Gio de RAM selon les rapports matériels locaux.
- Modèle IQ4_XS et partage des couches 24/24 ; experts manquants calculés sur CPU, `--pcie-frac 0`, `--adapt-every 0`, 15 workers.
- Réserve de 2 048 Mio par GPU, sans emprunt du cache pour le prefill ; **prefill 2 048**, contexte maximal 262 144, KV FP16.
- MTP actif, options de lancement `--spec 3 --spec-min-p 0.5`.
- **Table PLE/ngram sur SSD C, `--ple-io direct`**. Le rapport initial utilisant la table entière en RAM ne décrit plus ce réglage.
- Checkpoints de prompt configurés avec `--prompt-cache 8 --prompt-cache-every 160000`. La métrique du moteur indique toutefois **`conversation_cache_mib=0`** : ne pas confondre ce réglage avec huit conversations entièrement conservées en RAM.
- Aucun `--batch`, `parallel` ou `--pipeline-windows` dans la ligne de commande active.

## Ce qui change réellement pour nous

| Changement | Conséquence pour notre configuration |
|---|---|
| Experts résidents en RAM avec plusieurs GPU, introduits en 0.1.40 | Le mode officiel exclut du complément RAM les experts déjà présents dans les caches de chaque GPU. Il accepte notre architecture de partage des couches. Une part essentielle de notre adaptation peut être remplacée. |
| Chemin P100 dans le moteur CUDA 12 | Le support reste expérimental. Les projections BF16 passent officiellement par **FP32**, alors que notre variante convertit en FP16. Le prefill, la mémoire et les arrondis doivent être comparés. |
| Cache de conversations par étage GPU | Les sources 0.1.41 capturent et restaurent les états de chaque étage et le KV du draft sur sa carte. Cela recouvre le problème traité par nos modifications locales ; les scénarios de changement de conversation restent à valider dans notre client. |
| `--trim-stage-weights` | Avec un partage explicite comme 24/24, chaque carte peut charger seulement les poids denses de ses propres couches. Candidat intéressant pour libérer de la VRAM et augmenter le cache d'experts ; gain local non mesuré. |
| `--pipeline-windows 2` | Option pour chevaucher les fenêtres MTP d'une seule conversation entre exactement deux étages GPU. Architecture compatible en principe ; coût supplémentaire annoncé de 160 Mio par carte, plus états récurrents sur la première. À tester séparément. |
| Corrections serveur et sélection AVX2/AVX-512 | Intérêt pour la stabilité et la maintenance sur notre CPU AVX2. Elles ne constituent pas une mesure de gain de génération. |

Sources : [0.1.40](https://github.com/Niko1221/Strata/releases/tag/v0.1.40), [anciens GPU](https://github.com/Niko1221/Strata/blob/v0.1.41/docs/OLDER_GPUS.md), [plusieurs GPU](https://github.com/Niko1221/Strata/blob/v0.1.41/docs/MULTI_GPU.md), [0.1.41](https://github.com/Niko1221/Strata/releases/tag/v0.1.41).

Vérification dans les sources du tag : `src/program/generate.cpp` accepte `--resident-cpu-experts` avec un layer split et transmet les experts en cache des étages secondaires à `pin_cache_complement`. `src/prefill/gemm.cu` choisit le chemin BF16 → FP32 pour une compute capability inférieure à 7.0. Le code de parking dans `generate.cpp` conserve une image par étage, avec le draft sur le dernier.

## Gains annoncés à ne pas transposer directement

Le **+33 % de traitement d'un prompt de 512 tokens sur P100** en 0.1.41 utilise l'aide CPU par défaut sur **une seule carte NVIDIA**, sans batch. `Prefill::arm_cpu_share` laisse cette aide désactivée par défaut sur notre partage de couches. Une extension explicite aux layer splits existe, mais nécessite sa propre mesure. Ce chiffre ne prédit donc pas notre gain.

Les gains de débit avec plusieurs clients nécessitent les slots `--batch` et les groupes pipeline. Notre service travaille actuellement sans ces options. En outre, `docs/BATCHING.md` indique que le mode `--batch-mtp` n'est pas validé sur un partage de couches et y retombe sur le batching ordinaire : conserver simultanément notre MTP actuel et ces gains n'est pas acquis.

Les accélérations Windows quand le modèle dépasse la RAM concernent surtout les lectures des **experts**, qui sont déjà résidents chez nous. Le mode direct de notre **table PLE** est une autre lecture ; il ne permet pas de déduire que ces gains s'appliquent.

Le correctif Pascal de 0.1.40.4 est inclus dans 0.1.41. L'amont annonce environ +2 % sur une P100 face à 0.1.40.3 ; il répare une régression de la série 0.1.40. Ce n'est pas une prévision de +2 % face à notre 0.1.35. [Correctif Pascal](https://github.com/Niko1221/Strata/releases/tag/v0.1.40.4).

## Ce que disent nos mesures précédentes

Le [rapport du 4 octobre](../../recherche/strata-0.1.39-20261004-185410/rapport-recherche.md) donne, après chauffe et sur deux répétitions :

| Modèle IQ4_XS, génération en tokens/s | Ciel | Fibonacci | Poésie |
|---|---:|---:|---:|
| Notre hybride 0.1.35 | 29,1 | 34,9 | 27,7 |
| Notre hybride adapté à 0.1.39 | 29,6 | 35,3 | 26,6 |
| 0.1.39 officielle, experts en RAM, réserve 2 Go | 29,9 | 34,7 | 27,1 |

Ces résultats justifiaient de garder la production. Ils ne tranchent pas pour 0.1.41 : entrées de seulement 26 à 46 tokens, prefill 256, table PLE verrouillée en RAM. Le contexte maximal configuré à 262 144 ne signifie pas qu'un prompt de cette taille a été mesuré.

Le [test PLE sur SSD](../../recherche/strata-0.1.39-20261004-185410/normal-ngram-ssd-262144/rapport-ngram-ssd.md) montrait des réponses identiques et environ 26,8 Gio libérés pour ces trois requêtes courtes. Il reste pertinent comme justification de notre réglage actuel, avec les limites de son corpus et de son cache de lignes.

## Compatibilité et décision de migration

`git apply --check` du patch adapté à 0.1.39 **échoue** sur le tag 0.1.41, notamment dans `generate.cpp`, `expert_source.cpp`, `verify.cpp`, `gemm.cu` et `ngram.cpp`. Le diagnostic complet est dans `verification-patch.txt`. Le contrôle n'a appliqué aucune modification.

L'amont couvre désormais le mode résident sur plusieurs GPU, le support BF16 de Pascal, le verrouillage PLE Windows et le parking par étage. Il faut partir du moteur officiel CUDA 12, puis identifier les garanties et fonctions locales encore nécessaires. Notre mode strict exige une résidence entièrement verrouillée et refuse des replis ; le comportement officiel dépend de l'option choisie : `--resident-cpu-experts` n'active pas seul le verrouillage, alors que `--resident-experts` le demande avec un repli possible. La résidence réelle doit être vérifiée dans les journaux et la télémétrie.

Un comparatif utile doit opposer une nouvelle référence de production du même jour à 0.1.41, avec les mêmes IQ4_XS, MTP, tokenizer, GPU, table SSD et contexte. Première passe : conserver les réglages actuels, dont prefill 2 048, réserve 2 048 Mio, partage 24/24 et CPU pour les misses. Deuxième passe seulement : mesurer `--trim-stage-weights`, puis `--pipeline-windows 2`, séparément. Ne pas activer les options expérimentales de routage ou de staging dans la référence.

Mesurer le temps au premier token, le traitement des prompts de 512/2K/8K/32K tokens, la génération, les lectures disque, RAM/VRAM, ainsi que les arrêts et reprises, changements de conversations et historiques longs. Ajouter des contrôles de JSON, calcul, code et récupération d'informations ; les différences FP16/FP32 rendent l'identité textuelle insuffisante comme seul critère.

**Décision actuelle : migration intéressante pour réduire nos adaptations et bénéficier des correctifs ; gain de performance encore inconnu. Maintenir le moteur en service jusqu'à validation de cette comparaison.**
