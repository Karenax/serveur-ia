# Calcul avec les experts verrouillés en RAM — 26 octobre 2026

Demande : empêcher les lectures du disque D: pendant les calculs du modèle,
en conservant une consommation finale proche de 70 Go de RAM.

## Diagnostic

Le processus initial 24820 utilisait `--resident-cpu-experts` : son cache de
51,57 Gio était **pageable**, même avec de la RAM libre. Windows disposait d'un
fichier d'échange sur D: (31 506 Mio utilisés au premier relevé). La table PLE
était encore en `--ple-io direct` sur C:. Les GGUF étaient ouverts sur D:.
La pagination était la cause principale suspectée
des lectures pendant l'inférence ; les anciens compteurs ne permettent pas de
prouver quel fichier de D: fournissait chaque page.

Le journal du processus initial signale un blocage et son arrêt automatique
pendant le diagnostic, avant le déploiement. Aucun calcul synthétique n'avait
encore été envoyé par cette intervention. La mesure du 24 octobre fournit le
[diagnostic précédent](../2026-10-24-diagnostic-disque/README.md).

## Corrections

- Les deux profils persistants (`lanceur/base-strata.json` et
  `strata-iq4-p100-hybride.json`) demandent désormais `--resident-experts`,
  `STRATA_RESIDENT_PIN=1` et une réserve de 6 Gio. La table PLE reste en
  `--ple-io direct` sur le SSD C:, comme avant : la charger en RAM ajouterait
  26,82 Gio et dépasserait la cible précisée par l'utilisateur.
- `serve/ram_residency.py` vérifie le journal du **démarrage courant** avant que
  `StrataEngine` accepte des calculs. Un verrouillage partiel, absent ou un repli
  vers les fichiers provoque l'arrêt du moteur et une erreur récupérable.
  Le contrôle s'applique également aux redémarrages automatiques. En mode PLE
  direct, le chemin résolu doit être sur C: (un lien vers D: est refusé).
- Par précaution complémentaire, la table `token_embd.weight` (337 715 200 octets)
  est mappée en lecture seule et verrouillée avec `VirtualLock` dans le serveur
  HTTP. Ce verrouillage du fichier s'ajoute à la table chargée par le moteur
  natif en mémoire hôte accessible au GPU. Les pages de fichier
  partagées restent en RAM pendant la vie du serveur, y compris entre deux
  démarrages du moteur. Le fichier modèle n'est pas modifié.
- La récupération existante des copies temporaires au chargement est conservée.
  Le verrouillage physique des experts protège désormais ces données contre la
  pagination, indépendamment des copies de fichiers encore présentes en cache.

La copie de référence du module, l'installateur et le patch ciblé du serveur tiers
sont dans ce dossier. `avant/` conserve les deux profils et le serveur tels qu'ils
étaient avant l'intervention. Réappliquer le contrôle lors d'une mise à jour de
Strata ; les options natives seules autorisent encore certains replis sur disque.

Le [contrat Microsoft de VirtualLock](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtuallock)
garantit que les pages verrouillées restent en mémoire physique et ne sont pas
écrites dans le fichier d'échange tant qu'elles sont verrouillées.

## Vérifications

- 14 tests du contrôle de résidence et de l'admission du serveur,
  dont un contrôle réel des pages Windows par `QueryWorkingSetEx` sur un fichier
  synthétique, et le refus d'un faux moteur annonçant READY sans verrouillage.
- 8 tests de récupération mémoire au démarrage.
- 8 tests du lanceur : réussis.
- Contrôles de syntaxe du projet : 463 sources Python, 88 sources JavaScript,
  93 scripts PowerShell vérifiés avec les deux interpréteurs, réussis.

La session corrigée figure dans `demarrage.json`. `measure.py` mesure les lectures
de C:/D:, les écritures sur D:, les pages entrantes et les lectures explicites
du moteur pendant deux requêtes fictives. Le rapport est écrit seulement après
les mesures, pour ne pas ajouter d'accès au disque pendant les calculs.

### Résultat sur le moteur chargé

Session `20261026-114252-106060`, moteur 34904, serveur 37304 :

- Le journal confirme **51,57 Gio d'experts page-locked**, avec zéro échange
  vers le cache GPU et zéro lecture de blobs experts pendant les quatre calculs.
- `physical-validation.json` vérifie les **82 451 pages** de la table des tokens
  avec `QueryWorkingSetEx` : toutes sont présentes et verrouillées. La protection
  stricte est active dans l'environnement du processus.
- Après le chargement, environ **75 Gio** étaient utilisés sur toute la machine.
  Après les quatre tests : **76,60 Gio utilisés et 51,26 Gio disponibles**.
  Ces chiffres incluent Windows, les autres applications et les caches ; ce ne
  sont pas uniquement les poids du modèle. Le cache des conversations a aussi
  conservé environ 0,90 Gio de calculs fictifs.
- Première série (`measurement.json`) : deux réponses obtenues en 2,63 s et
  4,75 s. D: présentait encore de faibles lectures globales (moyennes 0,306 et
  0,065 Mo/s), avec environ 98 % de temps au repos. Leur fichier d'origine
  n'est pas déterminé.
- Seconde série (`measurement-repeat.json`), avec un nouveau préfixe et zéro
  token de prompt réutilisé : réponses en **2,11 s** et **4,44 s**, pour 36 et
  469 tokens de prompt. **Zéro lecture mesurée sur D: pendant les deux calculs** ;
  D: au repos en moyenne 99,99 % et 99,85 % du temps. Des écritures globales
  restent mesurées. Le moteur est revenu à l'état `idle`, sans requête en attente.

Le pic de chargement ne représente pas la consommation finale : les pages des
fichiers sources et le cache résident peuvent coexister pendant la copie. Le
passage provisoire de PLE en RAM ajoutait aussi **26,82 Gio** ; cette option a été
retirée et la table est de nouveau lue sur C:. Les prélectures de dépannage sont
terminées, leurs verrous temporaires libérés et le moteur n'est plus suspendu.
Le cache des conversations peut faire augmenter la RAM lors de l'utilisation ;
70 Gio ne constitue pas une limite fixe configurée.

## Portée

Les fichiers des modèles sont toujours lus au chargement initial. L'historique,
les journaux, les sauvegardes et les autres applications peuvent encore accéder
à D:. La table PLE effectue toujours ses lectures sur le SSD C:. Le fichier
d'échange Windows n'a pas été supprimé ni déplacé. Les compteurs
disque sont globaux : ils ne constituent pas une trace noyau par fichier.

## Retour

Arrêter le modèle depuis la console, restaurer les deux profils et `server.py`
depuis `avant/`, puis relancer la console et le modèle. Aucun poids, historique, accès
client, clé ou réglage de fichier d'échange n'est modifié par ce retour.
