# Essai RTX 3080 — 30 octobre 2026

**État avant redémarrage Windows :** voir [REPRISE.md](REPRISE.md).
Le pilote actif reste 560.94. Les essais du calcul dense sur RTX 3080 échouent
au premier produit cuBLAS, avec le moteur habituel et le dernier moteur officiel
0.1.54 de Strata 0.2.8. Aucun gain de débit RTX n'est validé.
Les processus de test sont arrêtés.

Le modèle et la table PLE sont maintenant configurés sur **F:** dans les cinq
profils actifs. La table est copiée et intégralement vérifiée par SHA-256 ;
l'original sur C: reste provisoirement disponible car la console déjà ouverte
conserve son ancien profil en mémoire. Le redémarrage relira les profils sur F: ;
la suppression de l'ancienne copie reste à faire après cette reprise.
Les tailles et 16 blocs répartis par fichier du modèle sur F: ont été comparés
aux originaux ; ce contrôle n'est pas une vérification intégrale des modèles.

Depuis F:, les deux P100 fonctionnent : médianes 34,9 tokens/s en génération,
247,6 tokens/s pour 1516 tokens de prompt et 398,95 tokens/s pour 5932 tokens.
Tous les calculs et restitutions de code attendus passent, sans cache de prompt
ni bridage thermique échantillonné. La P2200 a réellement encodé l'image fictive
depuis le modèle sur F: : 240 tokens visuels, environ 1,016 s après chargement,
hausse de VRAM et activité GPU confirmées (`vision-configured.json`).

Le dernier moteur CUDA12 est isolé sous
`F:/Kiara-tests/strata-0.1.54-cuda12/package`, archive officielle SHA-256 vérifiée.
La production conserve son moteur 0.1.45.3. Les deux versions déclarent un minimum
Windows NVIDIA de 576.02 ; 560.94 ne satisfait pas cette exigence. Ce constat ne
prouve pas que le pilote soit l'unique cause de l'erreur cuBLAS.

Demande : placer le calcul dense sur la nouvelle RTX 3080 et comparer le
préremplissage et la génération avec la configuration des deux P100.

## Protocole

Modèle Flash-Next Uncensored IQ4_XS et moteur officiel Strata 0.1.45.3 identiques.
Référence : P100/P100 avec séparation des couches à 24. Essai : RTX 3080 comme
CUDA0, tous les poids denses, état de session et MTP sur cette carte ; les deux
P100 servent de caches d'experts supplémentaires via
`--expert-cache-device1 auto --expert-cache-device2 auto --remote-expert-opt`.
Le CPU conserve le calcul des experts absents des caches GPU. La P2200 n'est pas
incluse dans les GPU visibles du moteur de texte ; la vision n'est pas démarrée.

Paramètres communs : contexte **8192**, blocs de préremplissage **2048**, 15 workers,
MTP 3 / seuil 0,5, réserve VRAM 2048 Mio, PLE direct sur F: dans les essais finaux, experts résidents
verrouillés en RAM, cache de prompt et cache de conversations désactivés.
Le contexte habituel de 262144 n'est pas validé par cette campagne.

Chaque configuration est chargée dans un processus de test sur le port local
18080. Les pilotes de benchmark ne modifient pas les profils persistants. Leurs
empreintes avant/après le confirment ; la migration F: distincte est explicitement
demandée et sauvegardée dans `stockage-F/avant`. Le moteur de production était absent au début des essais ; les anciens
fichiers de session ne constituent pas une preuve d'un processus vivant.

Après un calcul de chauffe : trois générations plafonnées à 256 tokens sur la
même demande d'explication, puis deux lectures de chacun des documents de 64 et
256 lignes avec restitution d'un code connu. Les débits et durées viennent des
champs `timings` du serveur. La réutilisation du cache est contrôlée.
Les réponses et les requêtes sont conservées ; les contrôles de contenu sont
limités et ne constituent pas une évaluation générale de qualité.

La télémétrie toutes les deux secondes relève VRAM, utilisation, fréquence,
température, puissance et masques de bridage. Aucun seuil thermique logiciel
supplémentaire n'est imposé. La protection RAM du pilote d'essai arrête le serveur
si moins de 6 Gio sont disponibles. Les processus créés par le pilote sont arrêtés
en fin d'essai, y compris après une erreur.

Une prélecture séquentielle en lecture seule des banques d'experts facilite le
premier chargement. Le script est repris de la procédure existante du 19 octobre.
Elle n'est pas un test de démarrage froid. Les temps de chargement des deux
configurations ne doivent pas être comparés, car l'état du cache disque diffère.

## Reproduction

Depuis la racine, avec le modèle de production arrêté et assez de RAM libre :

```powershell
& 'Strata-src/.venv/Scripts/python.exe' maintenance/2026-10-30-rtx3080/prewarm.py
& 'Strata-src/.venv/Scripts/python.exe' maintenance/2026-10-30-rtx3080/benchmark.py rtx3080
& 'Strata-src/.venv/Scripts/python.exe' maintenance/2026-10-30-rtx3080/benchmark.py p100
& 'Strata-src/.venv/Scripts/python.exe' maintenance/2026-10-30-rtx3080/analyze.py
```

Le pilote refuse d'écraser un dossier de résultats existant. Utiliser `--tag`
pour une nouvelle campagne ; adapter les dossiers de `analyze.py` en conséquence.

## Tensor Cores

Le journal identifie la 3080 comme CUDA0, capacité de calcul 8.6, et confirme le
chargement des projections natives sur cette carte. Le code local de Strata
(`src/prefill/gemm.cu`, fonction `bf16_path`) choisit la voie cuBLAS BF16 à partir
de sm80 ; sur Pascal, il convertit vers FP32. Le placement demandé rend donc les
produits denses du préremplissage éligibles aux Tensor Cores de la 3080.
Sans profilage matériel Nsight, aucun taux d'utilisation des Tensor Cores n'est
revendiqué. Les débits d'inférence incluent les experts, transferts, MTP et CPU :
ils ne mesurent pas uniquement le calcul dense.
