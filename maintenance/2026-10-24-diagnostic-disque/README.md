# D: sollicité pendant l’inférence

Diagnostic en lecture seule du moteur chargé, PID 24820, démarré le 23 octobre.
Aucune modification de configuration, de fichier d’échange ou de modèle ; aucun
redémarrage. Une requête synthétique locale de huit tokens maximum a été exécutée
alors que le moteur était inactif. Elle a produit trois tokens en 2,078 secondes.
Le moteur est revenu à l’état idle après la mesure.

## Constats

- La commande effective de Strata utilise `--ple-io direct --ple-gguf
  C:/Temp/Strata-ngram-recherche/iq4-xs-ple-iq4_nl.gguf`. Le fichier de
  28 800 138 464 octets existe sur C:, sans lien ou jonction dans ses parents.
  Il figure dans les fichiers ouverts du processus. Le journal confirme la table
  PLE sur ce chemin. C: correspond au SSD Kingston SA400S37240G.
- Les trois shards GGUF ouverts sont sur `D:\modèle\qwen3.8FlashNext\`.
  Le chemin `strata-data/model-q4` est une présentation locale de ces fichiers.
  D: est le disque mécanique Seagate ST5000DM000.
- Windows déclare un fichier d’échange `D:\pagefile.sys` de 30 921 Mio, dont
  30 647 Mio utilisés au relevé. Environ 48 Gio de RAM sont disponibles.
- Le journal de Strata indique un cache d’experts de 51,57 Gio **pageable**,
  avec 0 Gio pinned. La mémoire privée engagée du processus est d’environ
  60,08 Gio et son ensemble de travail de 53,24 Gio après le test. La différence
  n’est pas une mesure exacte de la quantité de données réellement dans pagefile.
- Le moteur annonce zéro lecture explicite de blobs depuis ses fichiers lors
  des dernières requêtes et lors de la requête de diagnostic. Ce compteur ne
  mesure pas les lectures de pages effectuées par Windows.

## Mesure

`measure.py` utilise les compteurs PDH anglais, à intervalles d’environ 0,5 s,
autour d’une requête directe à localhost:8080. Données brutes : `measurement.json`.
Le test ne comporte aucun prompt ni historique utilisateur.

Au repos : aucune lecture mesurée sur D:. Pendant l’inférence : D: atteint
1,78 Mo/s en lecture et environ **57,1 % d’activité** sur le pire intervalle.
Le même intervalle présente 435,377 pages entrantes/s, soit 1,78 Mo/s pour des
pages de 4 Kio. Les lectures explicites de Strata sont alors d’environ 0,032 Mo/s,
proches des lectures sur C:, et non du débit de D:. Les lectures sur D:
retombent à zéro après le test.

Ces observations relient le trafic D: aux lectures de pages nécessaires à
l’inférence. La pagination de la mémoire des experts vers `D:\pagefile.sys` est
la piste principale ; les fichiers GGUF mappés sur D: constituent aussi une
source possible de défauts de page. Sans trace noyau des noms de fichiers,
les compteurs seuls ne permettent pas de répartir exactement les deux.
Le compte utilisé n’est pas administrateur ; aucune trace noyau privilégiée ni
demande d’élévation n’a été lancée.

Le test court n’a pas reproduit 100 % d’activité continue ni le préremplissage
de 1 143 tokens ayant duré environ 295 s dans le journal. Il ne faut pas déduire
une saturation actuelle du seul niveau de remplissage du fichier d’échange.
Le déplacement de la table n-grammes vers D: est en revanche exclu par les
chemins et handles du processus réellement chargé.

Référence pour l’interprétation : [Microsoft — compteurs de défauts de page et
fichier d’échange](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/how-to-determine-the-appropriate-page-file-size-for-64-bit-versions-of-windows).
Un défaut de page matériel peut lire un fichier mappé ou le fichier d’échange ;
un fichier d’échange presque plein ne prouve pas à lui seul un problème de performance.
