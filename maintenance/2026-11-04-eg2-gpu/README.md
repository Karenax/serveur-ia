# Essais EG2 sur GPU — 4 novembre 2026

**Les deux cartes fonctionnent avec EG2 texte seul.** La P2200 constitue le
meilleur compromis mesuré pour préserver la marge mémoire de la RTX 4080 utilisée
par Qwen. Ces essais n’activent aucun GPU dans le service de production.

## Résultats

Même modèle local, 271 002 624 paramètres, 768 dimensions, séquence limitée à
2 048 jetons, calcul sans gradients et deux threads CPU. Les textes sont
fictifs et identiques entre configurations. Les temps excluent le chargement,
la tokenisation de comptage et les appels HTTP ; ils incluent `model.encode`
avec sa tokenisation et ses transferts CPU/GPU.

| Configuration | Groupe de calcul | 32 textes courts | 32 textes de 4 200 caractères | Gain sur les longs lots | VRAM libre minimale mesurée |
|---|---:|---:|---:|---:|---:|
| CPU actuel, float32, attention eager | 4 | 2,156 s | 84,390 s | référence | sans GPU |
| CPU, float32, SDPA | 4 | 1,641 s | 74,578 s | 1,13× | sans GPU |
| P2200, float32, SDPA | 1 | 1,109 s | 5,938 s | 14,21× | 2 560 Mio |
| **P2200, float32, SDPA** | **4** | **0,297 s** | **5,297 s** | **15,93×** | **2 084 Mio** |
| RTX 4080, float16, SDPA | 1 | 1,453 s | 1,610 s | 52,42× | 605 Mio |

Les lots courts sont mesurés trois fois après échauffement, avec leur médiane.
Les lots longs sont mesurés une fois chacun : les gains restent des résultats
de ces essais, pas une garantie de latence sur tous les contenus ou charges.
L’activité de production continue pendant la campagne ; la RTX était peu
utilisée au début de son essai. L’impact sur une génération Qwen simultanée ou
une analyse d’image sur la P2200 n’a pas été qualifié.

Les comparaisons CPU/GPU utilisent les mêmes textes, mais aussi des précisions,
implémentations d’attention et groupes de calcul adaptés aux cartes. Elles
comparent donc des configurations utilisables, pas le seul effet du matériel.

## Mémoire et fidélité

La P2200 conserve environ 2 Gio disponibles même avec des groupes de quatre.
Le pic du cache de l’allocateur PyTorch est de 1 686 Mio dans cette configuration.
Avec un groupe de un, il descend à 1 210 Mio et laisse davantage de marge pour
le service de vision déjà présent sur cette carte.

La 4080 accepte le modèle texte en float16 : environ 517 Mio de paramètres,
666 Mio de cache PyTorch au pic, et environ 955 Mio supplémentaires observés
au total par `nvidia-smi`, incluant le contexte et les bibliothèques CUDA.
Elle ne conserve que 605 Mio libres au point le plus bas de l’essai. La marge
observée avant la campagne variait d’environ 1 300 à 1 560 Mio : un partage
permanent avec Qwen demande donc une qualification sous charge et davantage
de marge. Aucune réserve ni configuration Qwen n’a été modifiée.

Les vecteurs sont finis et normalisés dans toutes les configurations. Leur
similarité cosinus minimale avec le CPU de référence est supérieure à
**0,999999** sur les textes de l’essai, y compris en float16 sur la 4080.
Cette comparaison numérique ne remplace pas une évaluation sémantique complète
sur les documents réels.

Sous Windows, les valeurs de mémoire retournées par CUDA et par `nvidia-smi`
diffèrent. La décision de marge et les seuils de protection reposent ici sur
`nvidia-smi`, et non sur la mémoire libre retournée par `torch.cuda.mem_get_info`.

## Isolation et contrôles

- Runtime distinct : `toolchain/eg2-gpu-benchmark-python-20261104`.
- PyTorch **2.14.1+cu126**, torchvision **0.29.1+cu126**, roues Windows/Python 3.12
  officielles épinglées par URL et SHA-256 dans `cuda-wheels.requirements.txt`.
  Les autres dépendances sont lues depuis le runtime CPU existant, sans l’écrire.
- Le runtime CUDA confirme les architectures `sm_60` et `sm_61` et exécute un
  calcul sur la P2200. La version CUDA 12.6 conserve la prise en charge de cette
  génération, contrairement aux constructions CUDA récentes qui l’excluent.
- Budget d’allocateur : 2 200 Mio sur P2200, 720 Mio sur RTX 4080. Le superviseur
  arrête uniquement ses propres processus de test si la VRAM libre passe sous
  1 024 Mio sur P2200 ou 512 Mio sur RTX. Aucun de ces seuils n’a été atteint.
- Aucun redémarrage de Qwen ou d’EG2, aucune modification de poids, de pairs
  WireGuard, de données ou de configuration de production.
- Vérification finale : mêmes processus Qwen et même processus EG2 ; service
  EG2 toujours sur CPU et requête authentifiée réelle en HTTP 200, 768 dimensions.
  Les six verrous de production sont conformes.

L’installation de test est restée en attente sur la bibliothèque
`torch_cuda.dll` et bloquait ses lecteurs. L’arrêt du seul installateur isolé,
après extraction, a libéré les fichiers ; les imports et le calcul CUDA ont
alors réussi. Les fichiers `torch_cuda.dll`, `torch_cpu.dll` et `torch/__init__.py`
ont été contrôlés contre les empreintes RECORD de la roue installée, et
`pip check` ne signale aucune dépendance incohérente. Cet incident est conservé
dans les journaux ; le runtime de production n’a pas été réinstallé.

## Preuves et reproduction

`summary.json` synthétise les résultats. Les fichiers par configuration détaillent
les mesures, la mémoire et les écarts numériques. Les `*-monitor.json`
contiennent les seuils, minima mémoire et contrôles de sortie. Les références
NumPy ne contiennent que les vecteurs des textes fictifs.

`benchmark.py` exécute une configuration. `run_gpu_tests.py` supervise les deux
cartes ; `--p2200-batch4` exécute seulement la variante P2200 par groupes de quatre.
`finalize.py` compare les résultats et vérifie le service de production.

Sources techniques : [accélération Sentence Transformers](https://sbert.net/docs/sentence_transformer/usage/efficiency.html),
[roues officielles CUDA 12.6](https://download.pytorch.org/whl/cu126/torch/),
[matrice de compatibilité PyTorch](https://github.com/pytorch/pytorch/blob/main/RELEASE.md).

**Recommandation :** qualifier la P2200 avec la vision simultanée, puis basculer
EG2 sur cette carte avec un retour CPU explicite en cas d’indisponibilité. La
4080 reste une option plus rapide si sa marge mémoire est augmentée et testée
avec Qwen actif. Aucune de ces bascules permanentes n’est réalisée par cet essai.
