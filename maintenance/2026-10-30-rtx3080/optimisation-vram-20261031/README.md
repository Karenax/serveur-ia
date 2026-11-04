# Optimisation de la VRAM — 31 octobre 2026

Le profil retenu et actif conserve RTX 3080 dense/MTP, deux P100 experts et
P2200 vision. Seul le cache de contexte passe de FP16 à INT8 ; les poids IQ4_XS
ne changent pas. Le cache d'experts de la 3080 est limité à une entrée, minimum
nécessaire pour activer les experts distants. Les deux P100 restent en auto.
Sans cette limite, le cache auto utiliserait la place libérée par le KV INT8.

Le contexte maximal reste 262144, la fenêtre KV en VRAM 20480, le préfill 2048,
le MTP 3 avec seuil 0,5, la réserve 1600 Mio, les quinze workers CPU et les caches
d'historique/conversation habituels. Le KV complet utilise 3,09 Gio de RAM
verrouillée contre 6 Gio en FP16. Les 30,81 Gio d'experts CPU sont également
verrouillés, via VirtualLock ; le garde Kiara valide cet état avant les requêtes.

## Comparaison contrôlée

Même moteur officiel 0.1.54, même pilote 581.80 et même contexte 262144. Trois
générations de 256 tokens et deux préremplissages par longueur. Les caches sont
neutralisés pour cette comparaison, avec contrôle explicite de zéro token réutilisé.
Les premiers essais `opt-*`, où le moteur réutilisait des conversations malgré
`cache_prompt=false`, sont conservés mais exclus des résultats.

| Profil | Génération médiane | Préfill 5932 tokens | VRAM libre minimale estimée |
| --- | ---: | ---: | ---: |
| Référence FP16, préfill 2048, cache primaire auto | 54,0 tok/s | 599,75 tok/s | 943 Mio |
| FP16, préfill 1024, cache primaire 1 | 55,5 tok/s | 332,8 tok/s | 1588 Mio |
| INT8, préfill 1024, cache primaire 1 | 52,2 tok/s | 337,4 tok/s | 2097 Mio |
| Même profil, MTP 4 | 52,6 tok/s | 339,2 tok/s | 2102 Mio |
| **INT8, préfill 2048, cache primaire 1 — retenu** | **52,4 tok/s** | **622,25 tok/s** | **1733 Mio** |

Gain mémoire mesuré : **790 Mio**, environ 0,77 Gio. Écart de génération : −2,96 % ;
écart de préfill long : +3,75 %. Ces petites différences de débit reposent sur peu
de répétitions et ne démontrent pas un gain statistique général. La baisse de
préfill à 1024 est, elle, suffisamment importante pour écarter ces profils.

La combinaison FP16 `--prefill-head-alias --mtp-q4 all` quitte le moteur avant
d'être prête. Elle n'est pas déployée ; aucune cause précise ou responsabilité
individuelle des deux options n'est affirmée.

La VRAM libre est estimée à partir du maximum d'utilisation totale échantillonné,
en retirant aussi les quelque 187 Mio réservés par le pilote. Elle inclut les
autres usages graphiques de Windows et varie selon la charge et le contexte.
Les premières estimations affichées pendant les essais ne retiraient pas encore
cette réserve. Les différences entre profils restent identiques. Les sondes sont
espacées de deux secondes et complétées après chaque requête : ce ne sont pas des
captures de tous les pics instantanés.

## Validation de cohabitation et de qualité

`../rtx3080-ctx262144-opt4-int8-coexist1g/` valide le profil retenu avec les caches
de production actifs et une allocation CUDA initialisée de **1024 Mio** dans un
second processus. Des préfixes système distincts empêchent la réutilisation de
prompts sans désactiver les caches. Toutes les réponses ont zéro token réutilisé.

- Génération médiane : 54,9 tok/s ; préfill d'environ 5965 tokens : 590,55 tok/s.
- Trois codes placés au début, au milieu et à la fin d'un dossier de **27702 tokens**
  sont correctement restitués en JSON. Ce prompt dépasse la fenêtre KV résidente.
- Les contrôles de calcul, JSON, négation et image passent également.
- Température RTX maximale échantillonnée : 60 °C, aucun signal thermique relevé.
- La VRAM libre descend jusqu'à **141 Mio** durant cette validation avec l'allocation
  supplémentaire. Le test à 1 Gio réussit, mais laisse une marge trop faible pour
  en faire un budget confortable au quotidien. Commencer vers **512 Mio** pour
  un autre modèle et mesurer son usage réel, y compris son contexte CUDA.

Ce second processus réserve et initialise de la mémoire ; il n'exécute pas
l'inférence d'un autre modèle. Les tests ne prouvent donc pas l'absence de
ralentissement lorsque deux modèles calculent simultanément sur la 3080.
Le KV INT8 modifie la précision de l'attention ; les contrôles ciblés réussis ne
constituent pas une évaluation générale de qualité. Aucun prompt de 262144 tokens
complets n'a été soumis.

## Activation persistante

Le profil validé avec caches actifs a été promu dans les deux bases de configuration,
les réglages courants et par défaut. La console a été redémarrée pour recharger sa
base, puis le service a été lancé et validé par son superviseur habituel. L'image
VISION 47, cercle rouge et carré bleu est correctement reconnue sur le service géré.
`production-image.json` conserve la réponse et sa configuration effective.

`status.json` vérifie l'état prêt, la cohérence des réglages courants/défauts/derniers
valides, KV INT8, MTP actif et autochargement/reprise conservés. La session active
est `lanceur/sessions/20261031-104644-100032`. La capture de fin relève 1523 Mio
libres sur la 3080 après la requête image ; cette valeur instantanée ne remplace
pas les minima sous charge ci-dessus. Le processus de réservation CUDA est arrêté.

Neuf tests du lanceur et les contrôles de sources passent (479 Python, 88 JS,
94 PowerShell dans chaque interpréteur). Aucun composant UI n'est modifié par
cette campagne.

## Preuves et retour arrière

- `comparison.json` : six tentatives comparables, erreurs et débits bruts résumés.
- `coexistence.json` : protocole distinct avec caches actifs et allocation supplémentaire.
- `memory-layout.csv` : mémoire totale/réservée/utilisée/libre rapportée par NVIDIA.
- Les dossiers `../rtx3080-ctx262144-opt2-*`, `opt3-*` et `opt4-*` conservent les
  configurations, requêtes, réponses, journaux et télémétries.
- `avant/` conserve le profil trois GPU précédent, avec KV FP16 et cache primaire
  auto. Pour y revenir, arrêter le modèle quand il est inactif, restaurer les deux
  bases et les réglages courants/défauts/derniers valides, redémarrer la console puis
  relancer le modèle. Ne pas restaurer un ancien PID ou pointeur de session.
