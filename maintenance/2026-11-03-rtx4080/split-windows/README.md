# Tentative de portage Windows du nouveau partage Strata

**Portage partiel validé ; aucun moteur d'inférence split complet ne fonctionne
encore sur ce poste. Aucun débit d'inférence n'est attribué à ce prototype.**

Les sources officielles de `v0.2.10` sont isolées sous
`toolchain/strata-0156-source`, commit `ffa80d73133ea5c548aefe57889a16e8085a938f`.
Le paquet binaire 0.1.56 utilisé dans les benchmarks est une construction officielle
distincte, commit `06698c674673`, CUDA 12.9 ; son manifeste est dans le paquet.

## Partie réellement adaptée et exécutée

Le vrai `src/split/src/gguf.cpp` a reçu un backend Windows dans ce checkout isolé.
`port_gguf.py` applique le portage de façon répétable ; `gguf-windows.patch`
conserve le diff et `win32_io.hpp` le nouveau backend.

- Lecture seule par `CreateFileMappingW` et `MapViewOfFile`, fermeture des mappings.
- Tailles de fichiers et positions de lecture sur 64 bits.
- Lectures à position explicite avec `ReadFile` et un événement propre par opération.
- Allocation alignée et libération correspondante avec les fonctions MSVC.
- Remplacement des contrôles de dépassement d'entier propres à GCC.
- Utilisation explicite du chemin de lecture avec cache déjà prévu par Strata.
  La résidence des pages est considérée inconnue et aucune page n'est omise ;
  le prototype ne prétend pas reproduire `O_DIRECT` ou mesurer les débits Linux.

MSVC 14.44 compile le lecteur et son stager multithread d'origine. Les tests
dans `io-validation.json` valident les 64 valeurs d'un petit GGUF fictif,
les **8 388 608 valeurs d'un GGUF de 32 Mio**, les gardes de dépassement d'entier,
et le refus d'un fichier dont la signature est invalide. Aucun modèle utilisateur
n'est modifié. Cela ne valide pas les noyaux CUDA, le chargement complet du
modèle réel ou une conversation.

Reconstruction locale : exécuter `port_gguf.py` avec le Python du projet, puis
`compile_gguf.cmd` depuis ce dossier. `gguf_smoke.cpp` lit les fixtures locales.
`verify_io.py` régénère les trois fixtures fictives et exécute leur validation.
Les EXE, objets et fixtures générés sont exclus de Git dans ce dossier.

## Prérequis matériels mesurés

`../probe_windows_split.py` interroge le pilote et exerce, pour chaque GPU,
une allocation hôte mappée, une écriture de signal CUDA, une synchronisation,
puis une attente dont la condition est déjà satisfaite. Tous ces appels passent,
y compris sur la 4080 en WDDM et les P100 en TCC. Les résultats sont dans
`../windows-split-prerequisites.json`.

L'attribut historique `stream_memops_v1` renvoie 0 ; cela ne doit pas être
interprété comme un échec des API v2, puisque leurs appels réels réussissent.
Ce test concerne des signaux locaux à chaque contexte : **il ne valide pas
un anneau de réduction entre GPU ni ses performances**.

## Obstacle de calcul reproduit

`upstream_mma_probe.cu` reprend exactement `mma_884` de
`src/split/src/moe_mma.cuh` et l'appelle dans un noyau minimal.
`compile_mma.cmd` utilise NVCC 12.4 et MSVC pour les deux architectures :

- **sm_89, RTX 4080 : compilation réussie** (`mma-sm89.log`).
- **sm_60, P100 : compilation refusée** (`mma-sm60.log`) : les instructions
  `mma` / `m8n8k4` exigent sm_70 ou plus récent.

Le code split vérifie aussi que toutes les cartes ont exactement l'architecture
de compilation (`card_check.hpp`, appelée par `model.cpp`). Une construction
sm_89 refuserait donc les deux P100 sm_60. Ce contrôle est conservé.

Faire tourner ce partage sur notre trio exige **un chemin de calcul Pascal
correct, sans ces instructions**, une compilation pour architectures mixtes
avec sélection des noyaux adaptée, puis la suite du portage Windows
(verrouillage mémoire, allocation/session, ordonnancement et synchronisation).
Remplacer seulement le contrôle Linux dans CMake ne règle pas ces points.
Les débits publiés sur deux RTX homogènes ne prédisent pas ceux de ce trio.

Les possibilités VMM diffèrent également : le pilote rapporte le support sur
la 4080 et son absence sur les P100. Cela concerne notamment le mécanisme
optionnel de mémoire partagée entre processus du laboratoire ; il ne faut pas
en déduire à lui seul que le chargement normal du split est impossible.

## Sources

- [Conditions de construction du split](https://github.com/Niko1221/Strata/blob/v0.2.10/src/split/CMakeLists.txt).
- [Contrôle des architectures](https://github.com/Niko1221/Strata/blob/v0.2.10/src/split/src/card_check.hpp).
- [Noyaux matriciels du préremplissage](https://github.com/Niko1221/Strata/blob/v0.2.10/src/split/src/moe_mma.cuh).
- [Lecteur GGUF d'origine](https://github.com/Niko1221/Strata/blob/v0.2.10/src/split/src/gguf.cpp).

Les fichiers de production, les pilotes et la configuration des GPU restent
inchangés par cette tentative. Les adaptations sont dans le checkout d'essai.
