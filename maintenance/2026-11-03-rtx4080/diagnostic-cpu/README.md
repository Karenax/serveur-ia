# Diagnostic CPU, PCIe et capacité V100 — 3 novembre 2026

**Le chemin des experts CPU/RAM limite effectivement cette charge.** Une grande
partie du temps GPU est passée à attendre leurs résultats. Une V100 32 Go pourrait
supprimer le manque de capacité VRAM des experts, mais aucun débit V100 n'a été
mesuré. Le portage du nouveau moteur split n'a pas été poursuivi pour ce diagnostic.

## Cinq essais réels

Même moteur officiel 0.1.56 CUDA 12.9, même modèle IQ4_XS, contexte 262144,
KV INT8, fenêtre résidente 20480, préfill 2048, cache RTX automatique, deux
caches P100 automatiques, couche MTP avec maximum de trois propositions,
cache de prompt/conversation désactivé. Chaque passage comporte une chauffe,
quatre contrôles ciblés et trois générations de 256 tokens sur le même texte.

| Configuration | Génération médiane | Part d'attente `waitCPU` |
| --- | ---: | ---: |
| 15 workers, profilage activé | 59,3 tok/s | 54,3 % |
| 8 workers, profilage activé | 48,8 tok/s | 62,6 % |
| 15 workers, une part des experts RAM calculée par la RTX (`--pcie-frac 0.5`) | 57,9 tok/s | 1,4 % |
| 15 workers, P2200 ajoutée comme troisième cache distant | 54,7 tok/s | 57,4 % |
| Témoin 15 workers, sans profilage | 61,7 tok/s | non mesurée |

Les 40 requêtes passent leurs contrôles ciblés ; aucune ne réutilise de tokens
de cache. Les empreintes des configurations/session surveillées sont conservées.
Les processus de test sont arrêtés et le port 18080 est libéré.

Le témoin indique un écart de débit d'environ 4 % avec l'instrumentation. Les
comparaisons de perturbation ci-dessus utilisent donc le même profilage. Elles
portent sur un petit nombre de requêtes, pas sur une campagne statistique générale
ou sur les performances de tous les usages.

## Ce qui est chronométré

Les options d'essai activent les fonctions natives `STRATA_DECODE_TIMING=1` et
`STRATA_VERIFY_PROFILE=1`, pas le mode CUDA synchrone de diagnostic.

Sur la référence à 15 workers, chaque fenêtre de vérification prend environ
31 ms et produit environ 1,85 token. Les estampilles GPU montrent environ 17 ms
d'attente `waitCPU`. Le total d'attente est pondéré par le nombre de fenêtres
des trois requêtes pour obtenir 54,3 %.

Ce compteur mesure l'attente du drapeau indiquant que les résultats de la voie
hôte sont disponibles. Il peut inclure le calcul CPU, la planification et la
coordination des experts distants. **Ce n'est pas 54,3 % d'opérations CPU pures.**
Le temps CPU du journal et l'attente GPU se chevauchent : ils ne sont pas additionnés.
La baisse à huit workers, à capacité GPU inchangée, confirme que cette voie est
sur le chemin critique, sans isoler à elle seule calcul arithmétique et bande
passante RAM.

Avec `--pcie-frac 0.5`, l'attente CPU tombe à environ 0,4 ms par fenêtre, mais
elle est remplacée principalement par l'attente `waitB`, qui comprend la mise
à disposition/transfert des poids pour la part PCIe. Le débit n'augmente pas.
Faire calculer des experts RAM par la RTX ne remplace donc pas le bénéfice
potentiel de les conserver en VRAM.

L'ajout de la P2200 augmente le cache total de 36,04 à 39,58 Gio et réduit le
complément CPU de 24,90 à 21,36 Gio. Pourtant, le débit baisse de 7,8 % dans
ce passage : les coûts de coordination/calcul de cette carte peuvent dépasser
le travail CPU économisé. Ce résultat ne prédit pas celui d'une V100, matériel
différent et capacité bien supérieure.

Enfin, un GPU à 80–99 % d'utilisation peut exécuter un noyau qui attend un
drapeau hôte : le pourcentage NVML mesure la présence de noyaux en exécution,
pas leur rendement arithmétique. Le code de Strata utilise précisément ces
noyaux d'attente. [Définition NVIDIA](https://nvidia.custhelp.com/app/answers/detail/a_id/3751/kw/driver),
[séquence de vérification Strata](https://github.com/Niko1221/Strata/blob/v0.2.10/src/core/verify.cpp).

## Estimation conditionnelle du gain

En conservant le reste du temps inchangé, avec `f = 0,543`, le facteur de débit
vaut `1 / (1 - f × r)`, où `r` est la proportion **nette** de cette attente supprimée.
Cette proportion doit déjà déduire le coût des nouveaux calculs GPU, transferts
et synchronisations ; avoir tous les experts en VRAM ne signifie pas `r = 1`.

| Attente supprimée nette | Gain du modèle simplifié | Débit depuis la référence instrumentée |
| --- | ---: | ---: |
| 25 % | +15,7 % | 68,6 tok/s |
| 50 % | +37,3 % | 81,4 tok/s |
| 75 % | +68,8 % | 100,1 tok/s |
| 100 %, cas idéal sans coût de remplacement | +118,9 % | 129,8 tok/s |

**Ce sont des scénarios, pas une prévision ni une garantie de débit V100.** Le
dernier est seulement le plafond du modèle simplifié. Ces mesures ne permettent
pas de choisir honnêtement la valeur de `r` pour une carte absente du poste.
Elles montrent en revanche une marge plus importante que la première estimation
non mesurée de 0–20 %, si le travail critique est réellement accéléré.

## V100 : quelle capacité pour tous les experts ?

Lecture des en-têtes des trois GGUF, sans lecture des poids : 144 tenseurs
d'experts, **65 431 142 400 octets = 60,9375 Gio**, répartis en 24576 paires
(couche, expert) de 2662400 octets. Les allocations denses, les états, le MTP,
le contexte et la table PLE sont distincts.

La référence place 14535 paires en VRAM, soit environ 36,04 Gio ; il en manque
10041, **24,897 Gio**. Avec DFlash2, le manque relevé dans la campagne précédente
est un peu plus petit, environ 24,65 Gio.

- **V100 16 Go : insuffisante** pour porter seule ce complément. Avec un budget
  conservateur de 14 Gio pour les experts, environ 10,9 Gio resteraient hors VRAM.
- **V100 32 Go : capacité potentiellement suffisante.** Un budget hypothétique de
  30 Gio pour ses experts laisse environ 5,1 Gio de marge sur ce complément.
  C'est un calcul de capacité, pas un essai d'allocation sur une carte physique.

Les V100 PCIe existent en 16 et 32 Go HBM2. Le modèle PCIe décrit par NVIDIA
occupe deux slots, consomme jusqu'à 250 W et emploie un radiateur passif avec
flux d'air système requis. L'installation physique et le refroidissement du poste
restent à vérifier avant un achat. [Fiche officielle NVIDIA](https://images.nvidia.com/content/tesla/pdf/Tesla-V100-PCIe-Product-Brief.pdf).

## Un réglage nécessaire pour une V100 32 Go

Le moteur sait déjà exploiter **trois caches GPU distants**, comme l'essai réel
avec la P2200 l'a vérifié. L'ajout d'une V100 en cache distant ne nécessite donc
pas, à lui seul, le portage du nouveau partage tensoriel Linux.

Cependant, la version 0.1.56 répartit d'abord les candidats par bandes entre
les caches distants, puis chaque carte limite son chargement à sa mémoire.
Avec trois helpers tous réglés sur `auto`, la V100 recevrait seulement environ
un tiers des candidats malgré sa plus grande capacité. La simulation du code
actuel laisse alors environ **6,56 Gio** d'experts en RAM, même si l'ensemble
des cartes dispose d'assez de VRAM.

Une configuration avec les caches P100 plafonnés explicitement, par exemple
6000 entrées chacun, puis la V100 en `auto`, transmettrait le reste à la V100 :
10187 entrées, environ **25,26 Gio** sur ce profil. Cela tient dans le budget
hypothétique de 30 Gio. La configuration devra être validée avec la carte réelle,
son UUID, sa mémoire libre, le pilote, la qualité des réponses et la cohabitation.
Ce scénario ne modifie aucun profil permanent aujourd'hui.

Source du placement : [Strata v0.2.10, configuration et répartition des caches distants](https://github.com/Niko1221/Strata/blob/v0.2.10/src/program/generate.cpp).

## Preuves et reproduction

- `analysis.json` : mesures par requête, textes de profilage bruts, calculs de
  capacité, simulation de placement et scénarios conditionnels.
- `analyze.py` : recalcul reproductible de cette analyse.
- `w15-profile/`, `w8-profile/`, `pcie050-profile/`, `extra-p2200-profile/`,
  `w15-control/` : configurations exactes, réponses, journaux et télémétries.
- `validation.json` : contrôle final des résultats, empreintes et arrêt.

Le pilote existant accepte désormais `--profile-timing`, `--pool-workers`,
`--pcie-frac`, `--decode-only` et `--extra-helper-gpu-uuid` pour reproduire ces
perturbations sans changer les réglages de service. Les contrôles de sources
passent : 512 Python, 94 JavaScript et 98 PowerShell dans chaque interpréteur.
