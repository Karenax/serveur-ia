# RTX 4080 seule + RAM — 3 novembre 2026

**Génération médiane : 47,2 tokens/s**, contre 55,4 avec une P100 et 61,5
avec deux P100 dans la comparaison précédente du même jour.

| Configuration | Génération médiane | Experts en RAM |
| --- | ---: | ---: |
| RTX 4080 seule | 47,2 tok/s | environ 54,77 Gio |
| RTX 4080 + une P100 | 55,4 tok/s | environ 39,71 Gio |
| RTX 4080 + deux P100 | 61,5 tok/s | environ 24,65 Gio |

Retirer les deux P100 réduit le débit de **23,3 %** par rapport au profil à deux
P100. Dans l'autre sens, les deux P100 augmentent le débit de **30,3 %** par
rapport à la 4080 seule. La première P100 apporte environ 17,4 % par rapport à
zéro ; la seconde environ 11 % par rapport à une. Ces ratios ont des références
différentes et ne s'additionnent pas.

## Protocole et vérifications

Le moteur ne voit que l'UUID de la RTX 4080. Aucun `--expert-cache-deviceN`,
`--remote-expert-opt`, `--layer-split` ou `--split-device` n'est activé. Les deux
P100 restent à 9 Mio et ne calculent aucun expert pendant les requêtes.
La P2200 est également exclue du test texte.

La RTX conserve ses couches denses, DFlash2 et son cache automatique d'experts.
Tous les autres experts sont conservés en RAM et calculés par les quinze
workers CPU : ce test n'est donc pas une inférence entièrement GPU.

Strata 0.1.56 CUDA 12.9, modèle IQ4_XS, DFlash2 avec `--spec 6`, confiance 0,8,
KV INT8, contexte maximal configuré 262144, fenêtre KV résidente 20480,
préfill 2048 et réserve VRAM 1600 Mio sont conservés. Les caches de prompt et
de conversation sont neutralisés, comme dans les références à une et deux P100.

Trois générations plafonnées à 256 tokens : **48,7, 45,5 et 47,2 tok/s**.
Préremplissage de 1516 tokens : 579,8 et 580,5 tok/s ; de 5932 tokens :
731,4 et 738,8 tok/s. La lecture du prompt reste donc proche des références ;
le coût du retrait des P100 apparaît surtout dans la génération sur cette charge.

Chaque passage utilise des données fictives et des contrôles ciblés de calcul,
JSON, négation et restitution de codes, dont un document dépassant la fenêtre
KV résidente. Les réponses brutes et les résultats sont dans `trial/`.
Une configuration complète à 262144 tokens n'est pas un stress test avec un
prompt de cette taille. Ces quelques répétitions ne constituent pas une étude
statistique ni une évaluation générale de qualité.

Les treize contrôles passent, avec zéro token de cache réutilisé. Le document
long compte 27683 tokens, ses trois codes sont correctement restitués.
Les 54,77 Gio d'experts CPU sont verrouillés via VirtualLock après refus du
verrouillage CUDA ; les journaux ne rapportent aucune lecture de blob depuis
les fichiers pendant les requêtes. Les contrôles de sources passent :
517 Python, 94 JavaScript, 98 PowerShell dans chaque interpréteur.

Le placement automatique des experts est recalculé pour chaque ensemble de
cartes ; le sous-ensemble placé sur la RTX ou sur une P100 n'est pas entièrement
figé entre les configurations. Les calculs GPU et CPU peuvent aussi diverger
légèrement par arrondi et changer les propositions acceptées par DFlash2.
La comparaison décrit les configurations réellement utilisables, pas seulement
un coût matériel isolé à continuation de tokens imposée.

## Service par défaut

Le service géré est arrêté lorsqu'il est inactif pour libérer les ressources.
Le benchmark tourne séparément sur le port 18080. Le script `test_no_p100.py`
rétablit ensuite le profil enregistré **RTX 4080 + deux P100, DFlash2, vision
P2200 et caches habituels** et attend l'état prêt. Aucun profil par défaut n'est
remplacé par le mode sans P100.

`status.json` contient l'état de la restauration : `default_restored` signifie
que le superviseur a terminé sa validation et que le moteur répond chargé.
Les preuves de comparaison et de contrôle final sont dans `comparison.json`
et `validation.json` lorsqu'ils sont produits.

Les scripts `compare_no_p100.py` et `test_no_p100.py` dans le dossier parent
documentent l'analyse et le déroulement. Le pilote de benchmark accepte désormais
`--p100-count 0`, sans changer les deux modes précédents.
