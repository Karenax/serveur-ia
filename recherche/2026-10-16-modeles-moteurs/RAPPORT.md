# Modèles locaux et moteurs — recherche du 16 octobre 2026

> **Périmètre corrigé à la demande de l'utilisateur : comparer les variantes de Flash-Next uniquement.** Voir [l'analyse recentrée et ses recommandations](RAPPORT-FLASH-NEXT.md). Ce document reste une annexe de recherche ; ses propositions d'autres familles de modèles ne correspondent pas à la demande corrigée.

## Conclusion pour ce serveur

La première évolution à évaluer est **Strata 0.1.44.1 CUDA 12 avec notre IQ4_XS actuel**, afin de séparer les corrections du moteur des effets d'un nouveau modèle. Pour gagner en fidélité, le candidat le plus proche est **Flash-Next UD-Q4_K_XL**. Pour réduire fortement l'empreinte et chercher une meilleure latence, **Qwen3.6-35B-A3B** mérite un profil séparé avec un moteur et un projecteur compatibles. Les branches **Kmic/qr0n optimisées P100** justifient aussi de réexaminer **Qwen 27B**, malgré nos anciennes mesures Café. **Swift 1.5 Flash-Next** intéresse surtout les usages qui activent la réflexion.

Aucune source consultée ne démontre qu'un remplacement serait à la fois plus intelligent, plus rapide, moins gourmand et compatible avec toutes nos fonctions. Les conclusions suivantes sont des choix d'essais, sans nouvelle mesure de performance locale. Aucun modèle, moteur, pilote ou service de production n'a été remplacé pendant cette recherche.

## Point de comparaison réel

Lecture du contexte, des réglages et de `/health` : deux Tesla P100 PCIe de 16 Gio, P2200 de 5 Gio pour la vision, Threadripper PRO 3955WX 16 cœurs/32 threads, 127,86 Gio de RAM, Windows et pilote 528.89. Strata officiel 0.1.43.1, Flash-Next Uncensored IQ4_XS, split 24/24, MTP 3/seuil 0,5, préfill 2048, 15 workers, contexte 262144. Tail skip et adaptation overlap explicitement désactivés. Les experts sont sur HDD D:, la table ngram sur SSD C: en lecture directe. [Instantané avant recherche](serveur-avant.json).

Notre [campagne du 13 octobre](../strata-0.1.43.1-20261013/mesures/20261013-092456/RAPPORT.md) mesurait environ 35,2 tok/s en explication et 38,9 en code pour Flash-Next 0.1.43.1. Le 27B Huihui Q4_K_M avec Café/MTP2 atteignait 30,6–35,7 tok/s à 32K et prenait 115 s pour lire le grand document, contre 56,8 s pour Flash-Next. Les variantes, prompts et conditions de refroidissement sont ceux de cette campagne : pas un classement universel de qualité ou de débit soutenu. Certaines séries ont été interrompues par la température ; les chiffres externes ne doivent pas être comparés directement à ces médianes.

## Modèles à considérer

Les tailles ci-dessous sont des **fichiers de poids en Go décimaux**, pas une promesse de consommation VRAM. Les caches, états récurrents, bibliothèques, brouillons MTP et projecteurs s'ajoutent. Deux cartes de 16 Gio nécessitent une répartition compatible ; elles ne constituent pas une carte unique de 32 Gio.

| Candidat | Empreinte vérifiée | Intérêt possible | Limite pour nous | Priorité |
|---|---|---|---|---|
| Flash-Next UD-Q4_K_XL | 111,3 Go ; experts 71,7 Gio avant répartition GPU/RAM | Quantification plus fidèle, famille déjà intégrée | Plus de trafic mémoire et de RAM que l'IQ4_XS ; démarrage HDD potentiellement encore plus long | Première comparaison de qualité |
| Qwen3.6-35B-A3B | 22,85 Go pour le GGUF UD-Q4_K_XL avec MTP proposé par Strata ; projecteur 0,90 Go | 3B actifs, beaucoup moins de poids et absence de la grosse table PLE de Flash-Next ; potentiel profil réactif | Nouveau chemin Strata sans vision raccordée ; répartition sur les deux P100 non validée ici | Premier profil léger à tester séparément |
| Swift 1.5 Flash-Next | IQ3_S GSQ-RCO : 83,74 Go ; projecteur 0,91 Go | Réponses avec réflexion plus courte | Gain principalement sur le nombre de tokens réfléchis, pas sur les tok/s ni la RAM à quantification égale | Utile si la réflexion est activée |
| Gemma 4 26B-A4B IT QAT | GGUF officiel 14,44 Go ; projecteur 1,19 Go | Petit MoE multimodal avec quantification entraînée ; autre profil léger | Intégration des outils, réflexion, vision et attention à valider sur Pascal ; pas le modèle principal de Strata | Deuxième candidat léger |
| Nemotron 3.5 Bolt 74B-A9B 24GB | GGUF officiel 22,02 Go ; projecteur 1,73 Go | Modèle récent pour agents et vision, taille attractive | Architecture Mamba/LatentMoE, mélange IQ2 et NVFP4 ; recettes documentées sur matériel RTX/Spark moderne, aucun résultat P100 trouvé | Exploratoire, après validation des kernels |
| Qwen3.8-27B | UD-Q4_K_M 16,46 Go ou Q5_K_M 19,77 Go ; projecteur 0,93 Go, MTP séparé possible | Poids pouvant être répartis en VRAM ; faible empreinte RAM | Famille déjà testée localement sans avantage global de vitesse ; coût du dense et des longs prompts | À réexaminer avec Kmic/qr0n et leurs kernels P100 |
| Flash-Next IQ3_S | Plus petit que notre IQ4_XS, famille conservée | Chercher moins de RAM et plus de débit | Quantification moins fidèle ; conserver l'architecture ne garantit pas les mêmes réponses | Option efficacité, pas amélioration de qualité établie |

Sources des fichiers : [Flash-Next Unsloth et formats](https://github.com/Niko1221/Strata/blob/v0.1.44.1/docs/QUANTS.md), [Qwen35 MTP](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF), [Swift GGUF](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF), [Gemma QAT](https://huggingface.co/google/gemma-4-26B-A4B-it-qat-q4_0-gguf), [Bolt GGUF](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF), [Qwen27 GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF). Les métadonnées Hugging Face avec tailles et révisions ont été consultées, sans téléchargement des poids.

### Ce que signifie « meilleure qualité »

Le test Strata compare 4995 positions de texte au Q8_0 de référence : accord sur le token le plus probable de **93,09 % pour UD-Q4_K_XL**, contre **88,91 % pour UD-IQ4_XS**, KL moyen 0,056 contre 0,101. Ce sont des mesures de fidélité, **pas des pourcentages de bonnes réponses**. Elles ne mesurent pas directement notre variante Uncensored, les outils Hermes ou les tâches de l'utilisateur. Q5/Q6 sont encore plus fidèles mais leurs experts de 91,6/101,7 Gio compliquent davantage la marge RAM. [Méthode et résultats](https://github.com/Niko1221/Strata/blob/v0.1.44.1/docs/QUANTS.md).

Swift annonce 63,4 % de réduction médiane des tokens de réflexion sur GPQA à xhigh, avec une faible différence de score sur ce test. Cela ne signifie pas que tous les tours sont deux fois plus rapides : sur son Terminal-Bench, la moyenne des tokens de sortie augmente même. Notre voix désactive déjà la réflexion ; le bénéfice principal de Swift ne s'y applique donc pas. Le fine-tune a ses propres conditions d'utilisation et n'est pas notre édition Uncensored. [Évaluation Swift](https://huggingface.co/ukisai/Swift1.5-Qwen3.8-Flash-Next).

Bolt publie des résultats compétitifs face à Qwen35 et Gemma sur plusieurs tâches d'agents, mais ne démontre pas une supériorité générale sur Flash-Next. Les tableaux de fabricants n'emploient pas nécessairement les mêmes harnais ni les mêmes budgets de réflexion. Son GGUF garde du NVFP4 dans certaines couches : « GGUF » et « 24GB » ne suffisent pas à prouver que les kernels fonctionneront efficacement sur P100. [Architecture, quantification et évaluation](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF).

Mistral Small 4 a également été examiné : 119B/6,5B actifs, vision, français et outils. Il reste un gros modèle hybride ; la documentation ik indique des étapes d'attention pouvant revenir au CPU sur Pascal. Je ne dispose d'aucune preuve d'un meilleur compromis ici. [Modèle](https://huggingface.co/mistralai/Mistral-Small-4-119B-2603), [attention sur Pascal](https://github.com/ikawrakow/ik_llama.cpp/blob/main/docs/pascal-volta.md).

## Dernier Strata officiel

Dernière publication stable vérifiée par l'API GitHub : **0.1.44.1**, publiée le **14 octobre 2026**, commit `296b59d2f73c8f04a805df29c2fa97655adace78`. La tête par défaut consultée correspond aussi à ce commit. Nous sommes sur 0.1.43.1. Les résultats d'un index de recherche qui donnait 0.1.39 comme dernière version étaient périmés ; ils n'ont pas servi à choisir la version. [Publication officielle](https://github.com/Niko1221/Strata/releases/tag/v0.1.44.1).

La 0.1.44 apporte des quantifications Unsloth supplémentaires, des packs NVFP4, Qwen35, la conservation du cache lors d'images successives et des corrections du traitement des marqueurs d'outils. La 0.1.44.1 corrige notamment des démarrages sur vieux CPU et des compilations CUDA 12.0/12.1. Ce sont des raisons de l'évaluer, sans en déduire un gain de débit sur notre machine. Les améliorations AMD, Intel ou Blackwell ne constituent pas un benchmark pour deux P100 Windows. [0.1.44](https://github.com/Niko1221/Strata/releases/tag/v0.1.44), [correctif](https://github.com/Niko1221/Strata/releases/tag/v0.1.44.1).

Points de migration trouvés dans les sources :

- **CUDA 12 obligatoire pour Pascal.** Garder les deux P100 pour le texte et la P2200 pour l'encodeur. Préserver notre encodeur CUDA 12.4 fonctionnel ; un remplacement par le précompilé peut réintroduire le repli CPU déjà constaté. [Guide matériel officiel](https://github.com/Niko1221/Strata/blob/v0.1.44.1/docs/OLDER_GPUS.md).
- **Les valeurs de setup changent.** Pour certains Unsloth, il écrit notamment `STRATA_HC_Q8=1` et ajuste le tail skip. Un simple lancement de l'installateur pourrait ainsi changer les arrondis et les réponses en même temps que le moteur. Notre premier A/B doit conserver les réglages actuels, puis tester séparément les options. [Code de configuration](https://github.com/Niko1221/Strata/blob/v0.1.44.1/setup.py).
- **Qwen35 n'est pas un Flash-Next réduit interchangeable.** Il a un chemin propre, sans nos packs/profils/MTP externes. Dans `OWN_PATH_FAMILIES`, `vision` vaut explicitement `False`. Le modèle lui-même sait voir, mais ce chemin Strata ne raccorde pas encore l'encodeur. Prévoir llama.cpp/Café/ik si l'on veut garder la vision, et vérifier leur fonctionnement avec ce modèle précis. [Configuration et code](https://github.com/Niko1221/Strata/blob/v0.1.44.1/setup.py#L426).
- Les options d'adaptation asynchrone d'arène mesurées sur **une carte** ne sont pas une recommandation pour notre split de deux P100. Même réserve pour `STRATA_PIN_BY_NEED`, relatif à une arène différente de notre configuration.
- Je n'ai pas trouvé de preuve que cette version supprime notre copie froide de dizaines de Gio depuis le HDD. Le code du cache résident conserve une copie des experts et une gestion des pages mappées. Les fichiers lourds et le stockage restent donc des facteurs indépendants du choix du modèle. [Chargeur](https://github.com/Niko1221/Strata/blob/v0.1.44.1/src/core/expert_source.cpp).

Précision sur NVFP4 : les P100 n'ont toujours pas d'accélération FP4 native. **La nouvelle version peut néanmoins traiter certains packs NVFP4 par des chemins logiciels.** Les formats/packs explicitement pris en charge ne prouvent pas la compatibilité du nouveau dépôt NVIDIA FP4-Local, dont les facteurs compressés demandent un lecteur adapté. Il ne faut donc ni déclarer tout NVFP4 impossible sur Pascal, ni promettre un gain matériel FP4. [Implémentation et mesures](https://github.com/Niko1221/Strata/blob/v0.1.44.1/docs/NVFP4.md).

## Dérivés et moteurs concurrents

| Projet examiné | Intérêt sur nos cartes | Décision |
|---|---|---|
| [Strata officiel 0.1.44.1](https://github.com/Niko1221/Strata/releases/tag/v0.1.44.1) | Windows/CUDA12, double P100 documenté ; continuité de notre intégration | **Premier moteur à comparer** |
| [Kmic P100](https://github.com/Kmic-68/llama.cpp/tree/p100-optimizations/p100-docs), [patchs qr0n](https://github.com/qr0n/p100-llama-cpp) | Kernels FP16 et attention ciblés GP100, tensor split et MTP sur deux P100 | **Première alternative à Strata pour les petits modèles**, sous réserve de compiler Windows/CUDA12 et de valider les mêmes tâches |
| [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp/blob/main/docs/pascal-volta.md) | Travail récent sur Pascal/Volta ; FA GPU pour plusieurs familles Qwen ; code actif le 16 octobre | Autre moteur à essayer, particulièrement pour les petits MoE ; vérifier le modèle exact, le MTP et les caches |
| [Café llama.cpp](https://github.com/kozmic-labs/cafe-llama.cpp) | Déjà compilé et testé chez nous ; un commit du 13 octobre lit les poids MoE épinglés depuis le fichier plutôt que le mapping | Référence utile pour les petits modèles ; le nouveau commit ne prouve pas un gain local |
| [PXA 3.1](https://github.com/poisonxa16/pxa) | Cible explicitement P100/Pascal/Volta, quants et kernels dédiés, support de splits identiques | **Piste sérieuse, mais hors remplacement Windows immédiat** : Linux et pilote 570+ documentés ; partie PXQN fermée |
| [Strata-V100](https://github.com/jmnargi/Strata-V100) | Kernels tensor cores Volta et options d'images/cache | Optimisations centrales non transposables aux P100 sans tensor cores ; pas prioritaire |
| [Strata-DualGPU](https://github.com/Hardin22/Strata-DualGPU) | Parallélisme pour deux GPU et peu de RAM | Mesuré sur RTX 5080/4060 Ti et 32 Go ; notre problème matériel est différent |
| [eddoursul/Strata](https://github.com/eddoursul/Strata/tree/custom) | Split/pipeline et brouillon adapté à 3090 + 5070 Ti | Comparaisons avec anciens Strata et matériel différent ; benchmark local indispensable |
| [strata-nvfp4](https://github.com/sergqwer/strata-nvfp4) | 0.1.44.1-nvfp4.2 du 15 octobre ; adaptations NVFP4 et agents | Pas de gain P100 établi ; le fork modifie aussi par défaut des prompts Claude Code, ce qui change le comportement indépendamment du modèle |
| [UnbiasedStrata](https://github.com/robertkarl/UnbiasedStrata) | Binaire C++ plus compact et port Qwen35 avec vision | Linux, une carte ; Flash-Next documenté pour une carte 24 Go+, donc pas de remplacement direct de nos deux 16 Go |
| [Infernix](https://github.com/Wallawalla47/Infernix), [Basalt](https://github.com/jesdga95/basalt) | Gros gains annoncés sur Blackwell | Ciblent RTX50/sm120, pas notre architecture ; exclus de la sélection immédiate |
| [Strata GLM53F](https://github.com/lighttransport/Strata/tree/glm53f) | Nouveau modèle et travaux CPU/plusieurs fournisseurs | GLM 321B et variantes prunées, résultats sur RTX/AMD, pas P100 ; trop de changements non validés ici |

### Pourquoi les chiffres PXA ne suffisent pas

La publication 3.1 annonce sur **une P100** 30,70 tok/s en prose et 37,96 en code avec Overdrive, contre 26,91/32,28 sans. Mais elle utilise un Flash-Next PXQN2/32GB, pas notre Uncensored IQ4_XS ; Overdrive est annoncé pour une seule carte et les essais de split Flash-Next n'y gagnent pas. Les meilleurs comparatifs de lecture emploient aussi des quantifications différentes. [Notes et protocole](https://github.com/poisonxa16/pxa/blob/main/RELEASE-NOTES-v3.1.md).

Le noyau public est sous MIT, mais les kernels PXQN sont distribués compilés et certaines fonctions/encodages nécessitent une clé. Cela compte pour la reproductibilité et l'autonomie d'exploitation. Son tarball exige Linux et un pilote 570+, alors que ce serveur est sous Windows/528.89. Je ne recommande pas une migration système pour ces seuls chiffres. [Conditions techniques](https://github.com/poisonxa16/pxa#supported-hardware), [répartition des composants](https://github.com/poisonxa16/pxa#licence).

### Alternative P100 particulièrement pertinente : Kmic et qr0n

La branche Kmic `p100-optimizations`, tête vérifiée `e48e240a8c9549f88c60b4cd47c8cd44bbf22f36` du 8 octobre, vise explicitement deux P100 et Qwen27 Q6_K, KV q4_0. Elle annonce environ 54 tok/s avec MTP à 2K, 29–35 à 260K, et des contrôles de perplexité proches du calcul FP32. Ces nombres dépendent de ce KV, de ce modèle et de ce protocole : pas une comparaison avec notre Flash-Next FP16 KV. Son FP16 accélère le matériel Pascal existant ; il n'exige pas de tensor cores NVFP4. La compilation Windows et la conservation de nos fonctions doivent être vérifiées séparément. [Présentation et méthode](https://github.com/Kmic-68/llama.cpp/blob/p100-optimizations/p100-docs/README.md).

qr0n publie une série de patchs, avec matrice de compatibilité, dont certains reprennent Kmic. Il documente du calcul GP100 FP16, de la fusion DeltaNet et du préfill long contexte ; son attention rapide a notamment été mesurée avec cuBLAS 12.4, disponible dans notre outillage. Ce sont des éléments à tester ensemble sur une révision épinglée, pas à empiler aveuglément dans Strata, dont le scheduler diffère. [Patchs et limites](https://github.com/qr0n/p100-llama-cpp).

Un utilisateur publie également des campagnes sur Qwen35 et plusieurs P100. Les résultats à deux cartes utilisent entre autres une quantification Q3 et un autre hôte/harnais ; ils confirment l'intérêt d'un essai, pas un débit garanti avec notre futur Q4. [Campagne réelle et configurations](https://github.com/4claps/houston-p100-cluster/blob/main/GPU-SCALING.md).

### Réserve sur ik

La documentation Pascal distingue les chemins GPU des replis CPU selon la taille des têtes, le KV et le batch. Elle prévient notamment contre certains formats de cache. Le code reconnaît `qwen4exp` et `qwen35moe`, mais cela ne valide pas toutes les fonctions de Flash-Next avec nos options. Un tableau de compatibilité de kernels n'est pas une preuve de débit ou de qualité de bout en bout. [État Pascal/Volta](https://github.com/ikawrakow/ik_llama.cpp/blob/main/docs/pascal-volta.md).

## Ordre concret des essais proposés

1. **Strata 0.1.44.1, modèle identique, configuration conservée.** Installer le moteur et le serveur Python de la même version dans un répertoire séparé, sans lancer l'installateur sur notre configuration active. Répéter nos cas texte, outils Hermes, OpenCode et images successives. Comparer la réutilisation du cache, le premier token et le débit. Évaluer ensuite séparément HC_Q8 et les options compatibles, sans les activer en bloc.
2. **Flash-Next Q4_K_XL** si la priorité est la fidélité : mesurer d'abord la marge RAM complète et le démarrage froid. Q5/Q6 ne sont pas les premiers essais vu notre mémoire, les autres services et le HDD.
3. **Qwen35 Q4 avec MTP et Qwen27**, via un chemin dont vision et double P100 auront été validés, pour un profil rapide. Comparer les branches P100 Kmic/qr0n, le 27B/Café déjà mesuré et ik récent, sans supposer que les patchs sont absents de chaque autre fork. Éviter de charger deux gros modèles simultanément.
4. **Swift** pour les longues tâches réfléchies ; **Gemma QAT** comme alternative légère ; **Bolt** après vérification de ses kernels Pascal. Les tests d'outils et de français priment sur un simple calcul correct.
5. **PXA** seulement en environnement Linux isolé compatible si l'on souhaite explorer cette piste ; aucune mise à jour de pilote ou migration de ce serveur n'est nécessaire pour terminer l'étude.

Un essai significatif doit séparer chargement froid et cache chaud, employer des sorties et contextes comparables (4K/16K/64K), mesurer le délai client et les débits moteur, conserver les réglages de réflexion et documenter la température. Vérifier français/instructions, code exécutable, JSON/appels d'outils, continuité Hermes et OCR/images. La réussite de « 17 × 19 » ou d'un seul exemple ne suffit pas à classer les modèles. Les jeux de validation peuvent être entièrement synthétiques, sans historiques d'utilisateurs.

La recherche a utilisé uniquement des lectures de fichiers, métadonnées et documentations publiques, et l'état local du serveur. Pas de nouveau benchmark, de requête de génération, de poids téléchargés, de changement de réseau ou de redémarrage. Les modifications préexistantes du projet sont conservées. [Sources et révisions](sources.json).
