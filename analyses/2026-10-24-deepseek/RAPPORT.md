# DeepSeek sur le serveur Kiara — étude du 24 octobre 2026

## Décision proposée

**Avec les deux P100 et le stockage actuel : DeepSeek V4 Flash 0731 en IQ3 est un candidat local crédible via llama.cpp ; DeepSeek V4.1 via le Strata publié n'est pas directement exploitable sur les P100. Avec une RTX 3080 et un NVMe disposant de 450 Go libres, V4.1 devient un candidat raisonnable à essayer via Strata, de préférence avec la 3080 12 Go.**

Ces conclusions portent sur la faisabilité. Aucun poids DeepSeek n'a été téléchargé, aucune inférence DeepSeek exécutée, aucune supériorité sur le Qwen actuel ni vitesse locale DeepSeek mesurée. La configuration de production n'a pas été modifiée.

## Matériel relevé

Relevé par CIM et `nvidia-smi`, conservé dans `materiel.json` :

- Windows 10 Professionnel ; Threadripper PRO 3955WX, 16 cœurs / 32 threads.
- 127,86 Gio de RAM utilisable ; huit DIMM de 16 Gio à 3 200 MT/s.
- Deux Tesla P100 PCIe de 16 Gio ; Quadro P2200 de 5 Gio, affectée aussi à la vision.
- Pilote NVIDIA 528.89 ; environ 14,1 et 14,2 Gio utilisés sur les P100 au premier relevé.
- D: Seagate ST5000DM000, HDD SATA, environ 4 187 Gio libres.
- C: Kingston A400, SSD SATA de 224 Gio, environ 31 Gio libres. Aucun NVMe relevé.

La production utilise Strata moteur 0.1.45.3 CUDA 12, serveur Python 0.1.43.1 corrigé et Qwen3.8-Flash-Next IQ4_XS. Les 32 Gio des P100 ne sont pas disponibles pour un autre gros modèle pendant son exécution. Un essai utilisant la RAM massivement doit également libérer les poids et caches Qwen ; changer de moteur ne libère aucune ressource à lui seul.

Les mesures historiques de `ANALYSE-GOULOTS-P100.txt` donnent environ 80 Go/s de lecture RAM par les cœurs et 13 Go/s de transfert RAM→GPU par P100. Elles expliquent les compromis possibles, mais ne constituent pas un benchmark DeepSeek.

## Sans achat : modèles possibles

Tailles exactes additionnées depuis les métadonnées publiques Hugging Face, révisions et tailles par fichier conservées dans `sources.json`. Il s'agit des poids, sans les allocations du moteur, caches et système.

| Modèle | Poids | Appréciation sur la configuration actuelle |
| --- | ---: | --- |
| R1-Distill-Qwen-32B Q5_K_M | 23,26 Go / 21,66 Gio | Essai le plus simple ; partage sur les deux P100, contexte initial 8K. Modèle distillé plus ancien, sans garantie d'amélioration face au Qwen courant. |
| R1-Distill-Qwen-32B Q6_K | 26,89 Go / 25,04 Gio | Possible mais moins de marge VRAM pour le contexte et les buffers. |
| R1-Distill-Llama-70B Q4_K_M | 42,52 Go / 39,60 Gio | Mémoire suffisante en hybride ; une partie du modèle dense reste sur CPU. Moins prioritaire pour la fluidité. |
| V4-Flash-0731 UD-IQ3_XXS | 104,21 Go / 97,05 Gio | Premier essai proposé pour le modèle complet ; RAM/GPU, contexte limité et une seule requête. |
| V4-Flash-0731 UD-IQ3_S | 116,07 Go / 108,10 Gio | Deuxième essai pour préserver davantage les poids, après validation du budget mémoire. |
| V4-Flash-0731 UD-IQ4_XS | 136,66 Go / 127,28 Gio | Exige un placement partiel réel en VRAM ; budget global serré, à dimensionner après les essais IQ3. |
| V4-Flash-0731 UD-Q4_K_XL | 155,10 Go / 144,44 Gio | Très peu de marge sur 128 + 32 Gio bruts ; ne pas commencer par cette version. |

Le V4 Flash 0731 complet est un MoE : seule une partie des experts est utilisée par token, mais tous doivent rester accessibles. Un moteur ne transforme pas pour autant ses poids en un petit modèle. Le HDD peut servir au chargement initial si les poids restent ensuite en mémoire ; des défauts de pages continus pendant la génération changeraient fortement le résultat. [Quantifications Unsloth](https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF), [guide de lancement](https://unsloth.ai/docs/models/deepseek-v4).

## Ce que Strata apporte aujourd'hui

La publication `v0.2.4`, parue le 24 octobre à 04:18 à Paris et actualisée depuis, propose Terminal 0.2.4.2 et moteur DeepSeek 0.1.49.2. Le correctif Zen 2 vise notamment les Threadripper 3000 ; il est pertinent pour le 3955WX, mais son gain annoncé n'est pas une mesure locale. Le moteur DeepSeek est séparé du moteur Qwen. Les seuls paquets NVIDIA DeepSeek publiés sont CUDA 13 : ils ne prennent pas en charge Pascal. La variante CUDA 12 utilisée actuellement pour Qwen ne contient pas ce nouveau moteur. [Publication vérifiée](https://github.com/Niko1221/Strata/releases/tag/v0.2.4).

Les sources contiennent des chemins GPU anciens, mais cela ne démontre pas un port P100 complet : `exl3_legacy.cu`, par exemple, appelle `__dp4a` sans repli sm_60 à cet endroit. Adapter/compiler en CUDA 12 serait une expérimentation distincte, avec validation numérique et mémoire. [Source examinée](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/dsv41/vendor/exl3_legacy.cu#L52).

## Scénario ajouté : RTX 3080 + NVMe de 450 Go

### Carte : distinguer 10 et 12 Go

La RTX 3080 est Ampere et appartient à la famille RTX 30 ciblée par le moteur DeepSeek. La variante **12 Go est préférable** : les essais publiés utilisent notamment des cartes de 12 Go. Le dimensionneur accepte des cartes d'au moins 8 Go ; une 3080 **10 Go reste donc un essai techniquement plausible**, avec moins de cache GPU et sans mesure publiée de cette configuration précise. La puissance de calcul seule ne permet pas d'en déduire le débit : CPU, RAM et stockage traitent une grande partie du modèle. [Spécifications NVIDIA](https://www.nvidia.com/en-us/geforce/graphics-cards/30-series/rtx-3080-3080ti/), [dimensionneur Strata](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/strata_control/dsv41_fit.py).

Point de départ recommandé : **RTX 3080 seule pour le moteur DeepSeek CUDA 13**, P100 exclues de ses périphériques visibles. Pour le modèle V4 Flash via llama.cpp, un partage 3080 + P100 avec un binaire CUDA 12 comprenant sm_60 et sm_86 constitue une autre expérience possible. Les VRAM des trois cartes ne forment pas un bloc unique ; leur somme ne garantit ni chargement ni accélération.

### Stockage : un modèle 2 bits tient

| V4.1 Flash via Strata | Total téléchargé, Engram et drafter inclus | Choix |
| --- | ---: | --- |
| IST-DAS 1.75 bpw / IQ1_M | environ 239 Go | Plus dégradé, surtout en prose ; peu d'intérêt si le 2.00 tient. |
| IST-DAS 2.00 bpw / IQ2_XXS | environ 257 Go | Premier essai recommandé. |
| IST-DAS 2.25 bpw / IQ2_XS | environ 274 Go | Comparaison de qualité ensuite ; davantage d'experts à lire. |

La table Engram commune occupe environ 111 Go et se lit à la demande ; elle doit être sur le NVMe avec les shards. Un espace **libre réel** de 450 Go suffit pour une de ces variantes et ses fichiers de travail : le script de préparation référence les poids et ne les duplique pas intégralement. Les ensembles 2.00 et 2.25 installés ensemble prennent environ 413 Go avant marge de travail ; commencer par un seul. La version UD-Q8_K_XL d'environ 508 Go dépasse ce disque. [Architecture et paquets Strata](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/docs/DEEPSEEK41.md), [préparation sans duplication des poids](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/tools/dsv41/pack_gguf.py).

Le NVMe corrige le principal défaut du stockage actuel pour V4.1. Sa capacité ne renseigne pas sur ses performances : modèle exact, interface PCIe, lectures aléatoires et débit soutenu restent inconnus. Les 128 Gio de RAM permettent un cache plus grand que les machines de 46–64 Go publiées, à condition de libérer Qwen et ses caches. Faire tourner les deux gros modèles simultanément réduirait cet avantage.

### Pilote et installation physique

Le pilote actuel 528.89 est trop ancien pour le paquet DeepSeek CUDA 13 ; NVIDIA fixe le minimum à la branche 580. Une branche R580 prend encore en charge la P100, mais la coexistence concrète GeForce / Tesla / Quadro sous Windows doit être validée avec le paquet choisi. Actualiser le pilote n'ajoute pas de kernels Pascal à un moteur CUDA 13. [Compatibilité CUDA](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html), [P100 dans les matériels R580](https://docs.nvidia.com/datacenter/tesla/tesla-release-notes-580-105-08/index.html).

La 3080 ajoute environ 320 W (10 Go) ou 350 W (12 Go) selon les spécifications de référence. Vérifier alimentation, connecteurs et emplacement en tenant compte des deux P100 et de la P2200 ; la recommandation générique d'alimentation d'un PC à une carte ne dimensionne pas cette machine. Aucun achat ou changement de pilote réalisé.

### Débit et qualité : ce qu'on peut raisonnablement annoncer

La publication Strata donne environ **5 tokens/s sur RTX 5070 12 Go + 64 Go RAM** et **8–10 tokens/s sur RTX 3060 12 Go + 46 Go RAM** pour le 2.00, avec NVMe. Ce sont des références externes, pas une fourchette garantie pour la 3080. La différence entre ces résultats illustre le poids du CPU et du disque. Avec 128 Gio et un bon NVMe, l'objectif d'un chat exploitable est crédible ; promettre 30–60 tokens/s ou un agent rapide serait prématuré. La hausse de perplexité annoncée pour une quantification ne se convertit pas en pourcentage de tâches réussies.

## Moteurs alternatifs et essai à faire

- **llama.cpp CUDA 12 / sm_60** : référence proposée pour V4 Flash 0731 sur le matériel actuel. L'architecture `deepseek4` est présente dans les sources locales. La sonde du binaire existant `llama-b11344` a indiqué sa version, mais `--list-devices` est restée sans réponse et a été arrêtée ; ce binaire n'est donc pas validé comme prêt à l'emploi. Aucun modèle n'a été chargé par cette sonde.
- **ik_llama.cpp** : candidat secondaire pour l'hybride CPU/GPU ; sa documentation décrit un repli attention CPU pour DeepSeek V4 sur P100. Vérifier version, types de poids et cache ; une compilation possible n'est pas une garantie de performances. [Limites Pascal documentées](https://github.com/ikawrakow/ik_llama.cpp/blob/main/docs/pascal-volta.md).
- **KTransformers** : dispose bien de voies AVX2, mais les chemins V4 actuels ciblent Ampere et un environnement différent ; pas de raccourci démontré pour les P100 et le Windows actuels. [Guide AVX2 officiel](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/kt-kernel/AVX2-Tutorial.md).

Après ajout du matériel, le premier comparatif utile serait **V4.1 Flash IST-DAS 2.00 via Strata 0.2.4.2, RTX 3080 seule, 8K de contexte, une requête et DSpark auto**, puis 2.25 si la qualité le justifie. Comparer au Qwen actuel sur français, extraction de documents, code et appels d'outils ; mesurer délai avant premier token, vitesse du texte final, consommation RAM/VRAM et lectures NVMe. Conserver le serveur Kiara corrigé tant que les appels d'outils et erreurs du nouveau moteur n'ont pas été vérifiés.

Si la 3080 est déjà disponible, son ajout avec le NVMe mérite cet essai. Pour un achat spécifiquement destiné aux LLM, une carte de 24 Go donne plus de marge ; la RTX 3090 offre 24 Go, mais aucun rapport qualité/prix n'est établi ici sans prix d'achat. [Spécifications 3090](https://www.nvidia.com/en-us/geforce/graphics-cards/30-series/rtx-3090-3090ti/).

## Preuves et limites

`materiel.json` contient le relevé local. `sources.json` conserve les tailles des poids, les révisions Hugging Face, le commit Strata examiné et les SHA-256 des sources téléchargées. `collecter_sources.py` ne télécharge que des métadonnées et du code texte publics. Les sources consultées sont figées à `7dd5cf18e68c639a8773e096c5c79f971ea2a9f5` pour Strata ; les performances citées restent celles des auteurs.

L'étude n'a pas vérifié un slot PCIe disponible, le bloc d'alimentation, le modèle exact de 3080/NVMe, le fonctionnement conjoint des pilotes ni une inférence DeepSeek locale.
