# Reprise après redémarrage — RTX 3080 et SSD F:

**Dernier état : optimisation VRAM terminée, enregistrée et active le 31/10 à 10:50.**
Profil actuel : RTX 3080 dense/MTP + deux P100 experts + P2200 vision, moteur
0.1.54, contexte262144, KV INT8 avec fenêtre VRAM20480, préfill2048, expert-cache
primaire1 et distantsauto, MTP3 seuil0,5, réserve1600. Modèle et PLE toujours F:.

Six tentatives comparables + validation complète avec caches actifs : le profil
retenu récupère790Mio dans les essais contrôlés, génération54,0 vers52,4tok/s
(~−3%), préfill5932tokens599,75 vers622,25tok/s (~+4%). Les profils préfill1024
sont rejetés pour perte majeure de débit du préfill. MTP4 sans gain décisif.
Combinaison headalias+mtpq4 échoue avantready et n'est pas déployée.

Validation avec allocation CUDA supplémentaire1024Mio : génération54,9tok/s,
préfill~590,55tok/s, 3codes répartis dans27702tokens restitués correctement,
calcul/JSON/négation/image passent. Minimum libre141Mio avec cette allocation :
marge trop faible pour recommander confortablement1Gio permanent. Budget initial
pour un autre modèle~512Mio à mesurer. L'allocation ne simule pas son calcul.
Le processus de réservation est arrêté. Pas de prompt complet262144 testé.

Lire `optimisation-vram-20261031/README.md`, `comparison.json`, `coexistence.json`
et `status.json` (active_verified). Sixprofils/pointeurs vérifiés sémantiquement,
réglages/défauts/derniersvalides cohérents, autoload/restart true. Session active :
`lanceur/sessions/20261031-104644-100032`, étatpret, image correcte sur servicegéré.
Experts CPU30,81Gio verrouillés VirtualLock, KV3,09Gio RAMpinned. Sauvegarde du
profil3GPU FP16 avantoptimisation dans `optimisation-vram-20261031/avant/`.
Neuf tests lanceur et contrôles sources479Python/88JS/94PowerShell passent.

**L'historique ci-dessous décrit le basculement initial en FP16, désormais remplacé
par le cache KV INT8 ; consulter les fichiers d'optimisation pour le défaut actuel.**

**Basculement initial de l’architecture vérifié le 31/10 à 10:12 (historique).**
La génération utilisateur a été laissée se terminer naturellement conformément à
sa réponse. Le défaut est désormais RTX 3080 dense/MTP + deux P100 experts +
P2200 vision, moteur officiel 0.1.54 permanent sur F:. Modèle et PLE sur F:.
Contexte 262144 conservé en FP16 : KV complet en RAM, fenêtre VRAM 20480 ; réserve
VRAM 1600 Mio. Les experts CPU restent verrouillés via VirtualLock (30,74 Gio).
Console redémarrée puis lancement géré validé. Image correcte et requête de
27646 tokens réussie sans réutilisation du cache. Aucun stress test complet à
262144 tokens revendiqué. Autochargement et reprise automatique restent actifs.

Lire `default-architecture/README.md` et `default-architecture/status.json`
(phase active_verified). Les six profils/pointeurs pertinents ont été contrôlés,
les réglages courants, défauts et derniers valides concordent. Session active :
`lanceur/sessions/20261031-101051-123863`. Sauvegarde avant basculement dans
`default-architecture/avant/`. Le lanceur gère durablement 2 ou 3 GPU ; neuf tests
réussissent. Contrôles de sources réussis (476 Python, 88 JS, 94 PowerShell).

**Les paragraphes ci-dessous décrivent les étapes historiques antérieures au
basculement. Leur profil deux P100 n'est plus le défaut actuel.**

**État le 31/10 après redémarrage : essais réussis sous 581.80 sur les quatre GPU.**
Lire `RESULTATS-APRES-REDEMARRAGE.md` et `comparison.json` : génération 34,9 vers
54,5 tok/s (+56,2 %), préfill 1516 tokens 248,7 vers 482,8 tok/s (+94,1 %),
5932 tokens 298,1 vers 580,7 tok/s (+94,8 %). Même moteur 0.1.54, contexte 8192,
zéro cache réutilisé. Vision P2200 réussie (240 tokens, 0,578 s). Aucun échec CUDA
dans les deux essais complets, profils persistants identiques après chaque essai.
Le service habituel est remis en route sur deux P100 + P2200,
moteur 0.1.45.3, contexte 262144. `production-after-58180.json` confirme une
réponse image correcte (VISION 47, cercle rouge, carré bleu) en 6,656 s.
L'ancienne PLE C: est déjà absente à la reprise ; la table F: est utilisée.
**Les paragraphes suivants sont l'historique et ne décrivent plus l'état courant.**

**Dernier état, installation autorisée effectuée :** les quatre cartes utilisent
maintenant **581.80**, toutes sans erreur PnP, toutes visibles dans `nvidia-smi`.
L'installation élevée a réussi pour RTX 3080, les deux P100 et P2200. Les trois
anciens paquets sont sauvegardés sous
`F:/Kiara-tests/installation-58180-20261030-autorisee/backup/` ; `state.json` et les
journaux de ce dossier contiennent les résultats. L'API Windows n'a pas signalé
de redémarrage obligatoire. L'utilisateur préfère redémarrer avant les mesures :
le nouveau chargement `rtx3080-ctx8192-pilote58180` est interrompu pour cette
raison, ce n'est pas une preuve d'un échec CUDA sous 581.80.
**Attendre le redémarrage propre avant de reprendre les benchmarks.** Aucun
redémarrage n'a été déclenché par l'agent. Le modèle a été arrêté via la console
pour l'installation ; les réglages persistants d'autochargement sont conservés.

Après redémarrage, vérifier encore quatre GPU en 581.80 et zéro erreur PnP,
puis reprendre avec un tag neuf, par exemple `pilote58180-apres-redemarrage`.
Si le modèle de production s'est autochargé, l'arrêter via la console quand il
est inactif avant tout benchmark, puis le remettre en service après les essais.

**Actualisation après redémarrage :** 582.99 est actif sur P100/P2200. La 3080 est
encore présente sur PCIe mais en code 31, associée à l'ancien 560.94. Les nouveaux
INF ne contiennent pas son identifiant DEV_2216. Lire `DIAGNOSTIC-PILOTES.md` avant
de reprendre les tests ; ne pas relancer les mêmes essais tant que la 3080 n'est
pas de nouveau utilisable dans `nvidia-smi`.

**Recherche demandée ensuite :** combinaison 581.80 WHQL préparée, deux paquets
officiels GeForce et RTX/Quadro dans `F:/Kiara-tests/pilotes-581.80/`. INF couvrant
les quatre cartes, signatures NVIDIA/Microsoft valides, `nvlddmkm.sys` et
`nvcuda64.dll` identiques par SHA-256. Aucun pilote installé par l'agent.
Lire `CHOIX-PILOTES.md` pour les fichiers, preuves et limites. L'installation
et la validation sur les quatre cartes restent à faire.

Objectif utilisateur toujours en cours : mesurer préremplissage et génération
avec le calcul dense sur RTX 3080, les deux P100 comme experts, et la P2200 pour
la lecture d'images. L'utilisateur a indiqué avoir installé un pilote NVIDIA
580 et envisage de redémarrer. **Aucun redémarrage n'a été lancé par l'agent.**

## Faits acquis

- `nvidia-smi` avant redémarrage : 560.94 sur les quatre GPU. L'inventaire PnP
  annonce 528.89 pour les P100 et 560.94 pour P2200/3080 ; les paquets NVIDIA du
  magasin Windows ne montrent pas de 580. Aucun indicateur CBS/Windows Update
  de redémarrage n'a été trouvé ; cela ne tranche pas l'installation NVIDIA.
- RTX 3080 : UUID `GPU-c7ec5bca-5502-9e99-2ede-30270b7bde2f`, 10240 Mio, WDDM.
  P100 UUID `GPU-a39f1b57-5a26-b53d-e943-44ef8042a438` et
  `GPU-486d5352-582e-2880-78bf-3dec4688e142`, 16384 Mio chacun, TCC.
  P2200 UUID `GPU-97ca6406-8625-b829-b053-191c238ff046`, 5120 Mio.
- Les trois shards IQ4_XS sont à la racine de F:. Tailles et 16 blocs de 1 Mio
  répartis par fichier correspondent aux originaux ; pas de hash intégral comparé.
- PLE/Ngram : `F:/iq4-xs-ple-iq4_nl.gguf`, 28800138464 octets,
  SHA-256 `7da86c65e2f2b5bc82aac137076d1eb77f0a7cd090478ec89fddfe23cb82a63d`.
  Copie et hash source/destination complets vérifiés. **Original C: encore présent**
  pour la console actuellement en mémoire ; suppression restant à faire après
  relecture du profil F: et validation réelle. Ne pas supprimer les modèles D:.
- Migration persistante des chemins seulement : `lanceur/base-strata.json`,
  `strata-iq4-p100-hybride.json`, réglages courants, défauts, derniers valides.
  Sauvegardes dans `stockage-F/avant/`. Le profil de production conserve deux P100,
  le moteur 0.1.45.3, contexte 262144, vision P2200. Le moteur en production était
  absent à l'arrivée de l'agent ; les fichiers de session étaient périmés.
- Garde RAM adaptée dans le module canonique
  `maintenance/2026-10-26-ram-verrouillee/ram_residency.py` et sa copie active
  `dependances/strata-0.1.43.1/source/serve/ram_residency.py` : PLE direct sur C:
  ou F:, toujours rejet de D: même via un lien. 16 tests résidence/admission et
  8 tests du lanceur passent. Contrôles de sources passent.
- P2200 : encodage réel de `maintenance/2026-10-14-vision/vision-fixture.png`,
  modèle F:, 240 tokens, 1,016 s, CUDA confirmé par VRAM + activité, résultat dans
  `vision-configured.json`. Aucun fallback CPU constaté dans cet essai.
- Baseline deux P100 sur F:, contexte 8192 : génération médiane 34,9 tok/s sur
  3 x 256 tokens ; préfill 247,6 tok/s à 1516 tokens, 398,95 tok/s à 5932 tokens
  (2 répétitions chaque). Cache réutilisé = 0 ; codes et calculs corrects ; pas de
  bridage thermique échantillonné. Dossier `p100-ctx8192-f-ssd/`.

## Échec RTX avant redémarrage

Le modèle charge les projections, le MTP et la session sur la 3080 ; les P100
contiennent chacun environ 6087 experts / 15,09 Gio. Il reste environ 30 Gio
d'experts verrouillés en RAM. Chargement F: complet, mais la première requête
échoue dans `cublasGemmEx` avec statut 14, avant le moindre token de réponse.

Reproduit avec moteur officiel 0.1.45.3, cuBLAS 12.4 isolé, moteur officiel 0.1.54,
voie FP16 forcée (`STRATA_BF16_TC=2`), puis exécution synchrone + trace CUDA.
Le log cuBLAS détaille la première matrice : m=320, n=31, k=10240, BF16, FP32 out,
algo DEFAULT. Le microproduit indépendant de même forme fonctionne ; la cause
exacte dans le moteur n'est pas établie. Ne pas présenter la mise à jour du pilote
comme un correctif garanti. Aucun proxy DLL ni patch CUDA local n'a été construit.

Dernière version vérifiée le 30/10 : app Strata **0.2.8**, moteur **0.1.54**, release
https://github.com/Niko1221/Strata/releases/tag/v0.2.8 . Archive CUDA12 officielle
téléchargée, SHA-256 vérifié, paquet isolé sous
`F:/Kiara-tests/strata-0.1.54-cuda12/package`. `latest-engine.json` contient les
empreintes. Le manifeste déclare pilote minimal Windows 576.02, supérieur à 560.94.
Le serveur Python corrigé de Kiara reste celui de 0.1.43.1 ; ne pas le remplacer
par le serveur amont sans préserver parseur d'outils, résidence RAM, etc.

Tous les processus de benchmark et de prélecture créés par l'agent sont arrêtés.
Le premier chargement D: a été interrompu à la demande de migration F: ; aucun
résultat de calcul RTX n'en provient. Les essais échoués restent archivés.

## Reprendre

1. Lire `nvidia-smi` et l'inventaire PnP après redémarrage. Vérifier le pilote
   réellement actif sur les quatre cartes ; s'il reste 560.94, examiner
   l'installation 580 signalée par l'utilisateur avant de reproduire les mêmes
   échecs. Aucun installateur ni pilote système n'a été modifié par l'agent.
2. Vérifier si le superviseur a autochargé le modèle. Ne pas lancer un benchmark
   concurrent sur les P100 déjà occupées ; arrêter le modèle via la console locale
   uniquement quand il est inactif, conserver puis restaurer son état.
3. Relancer l'essai officiel 0.1.54 normal, sans trace ni voie FP16 forcée :

```powershell
& 'Strata-src/.venv/Scripts/python.exe' maintenance/2026-10-30-rtx3080/benchmark.py rtx3080 --tag apres-redemarrage --engine-dir F:/Kiara-tests/strata-0.1.54-cuda12/package
& 'Strata-src/.venv/Scripts/python.exe' maintenance/2026-10-30-rtx3080/benchmark.py p100 --tag apres-redemarrage --engine-dir F:/Kiara-tests/strata-0.1.54-cuda12/package
& 'Strata-src/.venv/Scripts/python.exe' maintenance/2026-10-30-rtx3080/analyze.py --p100-run p100-ctx8192-apres-redemarrage --rtx-run rtx3080-ctx8192-apres-redemarrage
```

4. Pas de prélecture D: nécessaire pour F:. Les dossiers de résultats existants
   ne sont jamais écrasés. Les pilotes de test arrêtent leurs processus en sortie.
   Les empreintes des profils doivent rester identiques pendant les benchmarks.
5. Valider le chargement depuis F: dans la vraie session et la vision P2200,
   puis finaliser le déplacement en supprimant **seulement** l'ancienne table
   `C:/Temp/Strata-ngram-recherche/iq4-xs-ple-iq4_nl.gguf` après vérification du
   fichier F: et des profils. Mettre à jour `stockage-F/ple-copy-validation.json`.
6. Terminer un rapport honnête, avec débits, contrôles de réponse, limites du
   contexte 8192 et résultat des quatre cartes. Le contexte 262144 avec tout le
   dense sur la 3080 de 10 Go n'a pas été testé. Ne pas changer silencieusement
   le profil permanent deux P100 en trois GPU : le lanceur valide actuellement
   exactement deux GPU et une séparation de couches entière.

Modifications préexistantes à préserver : README, measure.py, physical-validation.json
et measurement-repeat.json sous `maintenance/2026-10-26-ram-verrouillee/`.
