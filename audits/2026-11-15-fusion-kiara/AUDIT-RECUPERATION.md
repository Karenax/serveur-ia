# Audit de récupération de Kiara — 16 novembre 2026

Contrôles sur D:, le partage de sauvegarde de DS218 et GitHub. La restauration a été exécutée dans un dossier de recette sur D:, avec les accès distants désactivés. E: et les données en service sont restés hors des opérations d’écriture et E: n’a été ni parcouru ni lu.

## Code et dépendances

| Périmètre | Constat au 16 novembre |
| --- | --- |
| Kiara publié | Les 7 096 fichiers suivis sont présents. Aucun fichier suivi supprimé dans l’arbre de travail. `git fsck --full --no-dangling` réussit. Le `main` local et le `main` interrogé directement sur GitHub pointent sur `010cf315b0f946980ccd537cba8f69e23eaa68a9`. Ce commit contient déjà la fusion. Aucune perte de source publiée détectée. |
| Kiara en cours de fusion | 27 fichiers suivis modifiés au début de l’audit. Le patch binaire complet depuis HEAD et l’inventaire Git sont sur D: dans le dossier de preuves, avant mise à jour du présent rapport. Les trois chemins non suivis sont ce rapport, un cache TypeScript et un journal de diagnostic. La copie historique sur le NAS ne contient qu’un patch Kiara antérieur. |
| Sources historiques | L’ancien dépôt publié est récupérable au commit `0c2e08abfb43a032e879ba5abcd728a17cf03161`, copié sur D:. Le rapprochement antérieur relève 7 fichiers identiques octet pour octet, 705 identiques après normalisation des fins de ligne, 157 différents, 37 sans même chemin dans la fusion et 16 propres au dépôt intégré. Les absences comprennent des scripts autonomes, de la documentation et des sorties générées. Examiner les 157 différences et les 37 chemins par parcours avant toute réintroduction. Les changements jamais publiés et conservés uniquement sur l’ancien disque restent impossibles à inventorier à partir de Git. |
| Strata et outils de production | La copie NAS du patch Strata et du test local est vérifiée par empreinte dans `code-et-audit/travail-local-kiara-strata-20261116.zip`. Les Python métier et audio pointent actuellement vers D:. La remise en service a déjà vérifié les dépendances et un essai audio. Des moteurs et modèles Strata sont présents sur D: selon l’inventaire antérieur. Le contenu de tous les modèles n’a pas été vérifié par empreinte. |

## Sauvegarde et données

La dernière paire visible sur le NAS, datée du 16 novembre à 03 h 00 min 19 s, a été copiée sur D:. Les SHA-256 de la copie et des deux fichiers du NAS concordent. La restauration vérifie l’intégrité et les clés étrangères des trois bases, les empreintes de 1 181 courriels originaux, dont 407 avec pièce jointe, et de 98 fragments audio. Elle n’a démarré aucun service et ne valide pas un parcours client sur ces données.

Le catalogue courant configure D: en primaire et DS218 en secondaire à 03 h 00. Les deux fichiers primaires sont présents. Le fichier principal correspond par empreinte à celui du NAS. L’accès en lecture au compagnon primaire a été refusé au compte d’audit. Le compagnon NAS et sa copie de recette sont lisibles et vérifiés.

| Domaine | État restauré et écarts avec D: |
| --- | --- |
| Projets | 11 projets, 88 jalons, 5 038 entrées liées aux jalons, 40 liens réseau, 1 note et 3 fiches CDC. Mêmes clés sur D: et dans la sauvegarde sur les 73 tables. Onze lignes de traitements de scan ont des valeurs différentes. |
| Connaissances | 1 710 sources, 3 020 éléments de connaissance, 2 fils d’assistant et 2 séances. Mêmes clés sur les 29 tables. Une ligne de réglages a un contenu différent. Les 34 courriels originaux qui manquaient à la paire du 15 novembre sont couverts par la nouvelle paire. |
| Espaces privés | Deux lignes d’historique client. Les tables de conversations serveur contrôlées sont vides des deux côtés. Un réglage est uniquement sur D:, sur les 20 tables comparées. Les brouillons et historiques locaux non synchronisés dépendent de chaque appareil. Leur récupération n’a pas été vérifiée. |
| Originaux hors périmètre | L’inventaire précédent relève 528 sources mail sans chemin d’original. Un cas prioritaire est le PDF CDC `694184-STB-A3.pdf` dont l’original attendu est référencé sur F:. Le texte des 35 pages a été retrouvé auparavant. L’original doit encore être identifié par son empreinte. Les 40 liens réseau se répartissent en 23 cibles V:, 11 D:, une UNC et 5 chemins relatifs. Les liens sont préservés dans les bases. L’accessibilité des cibles et la version de leurs documents restent à vérifier. |

La comparaison couvre les 122 tables applicatives ordinaires des trois bases. Elle rapproche la clé primaire et l’empreinte de chaque ligne. Aucune clé présente uniquement sur le NAS et aucune table absente d’un côté. Une différence de ligne peut provenir d’une évolution normale postérieure à la sauvegarde ou d’un traitement de restauration. Les binaires hors périmètre, le contenu des appareils et les fichiers externes exigent leurs propres vérifications.

## Archives et paquets

- Le catalogue conserve 16 références vers l’ancien E:. Recherche par nom sur le partage NAS de sauvegarde, avec deux paires présentes, un fichier principal seul et 13 noms absents. L’inventaire du 15 novembre signalait aussi 57 chemins historiques sur D: sans fichier à l’emplacement exact enregistré. Des déplacements, purges ou instantanés peuvent expliquer ces écarts. L’état de l’ancien disque et la liste de ses fichiers restent inconnus.
- Sur D:, le dossier `essais/pilote-https-kiara` contient les preuves du pilote, le portail précédent et ses empreintes de retour. La recette serveur `essais/kiara-serveur-route-projets` a vérifié le retour puis la réactivation et la conservation de deux écritures de recette. Les anciens artefacts identifiés uniquement par les références de l’ancien disque restent à rechercher si leur empreinte historique est nécessaire.
- Le candidat Windows et la recette WebView2 sont disponibles sur D:. L’installation et le retour signés restent à qualifier. Les deux tarballs Linux amd64 et arm64 sont disponibles avec leurs empreintes et leur manifeste de 80 fichiers chacun. La recette graphique Linux native reste à faire.
- L’APK de recette Android 1.0.27 est présent, SHA-256 `E316F2F3040F9467CDD07D83B14C50A7D28B476B5B906806419E2FB35EACE9E2`. La validation HTTPS avec un téléphone physique et un compte de recette reste à faire. La clé de signature de publication reste à localiser et à vérifier auprès de son détenteur. Le fichier `.fredkeys` du NAS ne permet pas d’en déduire la présence.

## Plan de reconstruction et de qualification

| Priorité | Action | Validation |
| --- | --- | --- |
| P0 | Mettre à l’abri la version courante non publiée du code Kiara. Conserver le patch de cet audit sur D: et déposer une référence vérifiable hors machine avant toute opération de nettoyage ou de bascule. | Le patch et les fichiers sources non suivis utiles se rejouent sur le commit Git publié. Le patch antérieur Kiara et le travail Strata sont déjà sur le NAS. |
| P0 | Conserver la paire du 16 novembre et vérifier la couverture du prochain point de reprise. Identifier dans le schéma la portée du réglage présent seulement sur D: et des douze lignes différentes avant toute réimportation. | Nouvelle restauration isolée et comparaison des clés et révisions. Conserver l’état en service tant que les écarts n’ont pas été qualifiés. |
| P1 | Retrouver les originaux exclus dans les boîtes mail, dossiers clients, partages et postes sources. Commencer par le PDF CDC et les cibles des liens de projets actifs. | Rapprochement fichier par fichier avec la version et l’empreinte attendues quand elles existent. Vérification des brouillons et historiques non synchronisés sur les appareils concernés. |
| P1 | Reprendre la fusion depuis les sources et paquets disponibles sur D:. Recenser les écarts du dépôt historique par parcours métier avant de recréer un module. | Parcours Projets et Conversations validés. Mise à niveau et retour Windows signés, interface Linux native et parcours Android HTTPS sur téléphone physique, dont téléchargement d’un original, historique, brouillons et mode éphémère. |
| P2 | Rechercher les anciennes paires, preuves et versions exactes manquantes dans les instantanés du NAS et les supports sains autorisés. | Chaque référence historique est associée à une copie contrôlée ou documentée comme introuvable. Une nouvelle preuve de recette porte sa propre date et sa propre empreinte. |

## Preuves sur D:

- `D:\Kiara\essais\audit-pertes-20261116` contient la paire chiffrée recopiée du NAS, les empreintes, le résultat de restauration, la comparaison des bases, trois copies SQLite de recette issues de cette restauration et le patch de travail. Les copies SQLite contiennent des données privées et sont conservées sous des permissions Windows restreintes.
- `D:\Kiara\recuperation-nas-20261115` contient les inventaires historiques des chemins Git, des originaux et du catalogue.
- `D:\Kiara\remise-en-service-20261116\REMISE-EN-SERVICE.md` documente les environnements rétablis, la sauvegarde automatique et la reprise de production.
