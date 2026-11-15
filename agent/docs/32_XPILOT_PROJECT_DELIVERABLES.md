# Livrables projet — lot L3

La fermeture d'archive inclut aussi les versions de types utilisées uniquement
par une publication RLP historique. Le précontrôle de schéma utilise la connexion
déjà possédée par l'import coordonné v6, sans la fermer ni installer de tables.
Les types et fichiers historiques restent réconciliés sans écrasement ; le
transport v5 conserve son comportement. Cette extension L4 est décrite dans le
document 33 et reste préparée dans le worktree avant activation.

État au 6 octobre 2026 : **L3 qualifié et actif dans `C:\Agent` sur `8001`**.
Catalogue, sélection, fiches, checklists, visas, versions, historique et liens
des jalons sont disponibles. Le candidat fusionné passe 706 tests Python
(un ignoré), 267 React, Ruff, TypeScript et build. Sa migration et sa restauration
sont qualifiées sur copies ; la bascule conserve les 2 098 lignes ERP et les
13 144 lignes Brain contrôlées. Les dix projets historiques et les nouveaux
parcours sont vérifiés sur le serveur et dans le navigateur. Le catalogue reste
vide jusqu'à une création explicite ; les onze types standard sont des propositions.
Les sections datées suivantes décrivent aussi les qualifications intermédiaires.

Sauvegarde complète : `C:/Agent/logs/xpilot-l3-activation-20261006-190820/full-state-before-l3`.
Preuve de livraison : `.ui-preview/xpilot-l3/integration-1006-v2/delivery-result.json`.
L4–L9 restent à réaliser ; le serveur unique et les modules hérités sont conservés.

## Contrat métier

Le livrable historique conserve son UUID, son titre et son statut. Une extension
porte le statut documentaire, les personnes responsables, le vérificateur et la
version exacte de son type. Un ancien statut `done` n'est jamais transformé en
visa humain. Lire un livrable n'installe aucune extension et ne modifie pas les
données.

Le catalogue suggère les onze types opérationnels XPilot : AF, AR, conception
3D/2D, calcul, AMDEC, notice, V&V, formation, dossier FDR et ACV. Les **67 points
de checklist** et les trois typologies conception/modification/duplication sont
conservés dans `backend/app/data/deliverable_catalogue.json`. Sa provenance donne
le commit de l'audit et l'empreinte du fichier source. Cette ressource est une
suggestion en lecture seule : aucune référence ou sélection projet n'est créée
implicitement. L'extraction lit l'AST local, sans exécuter ni modifier XPilot.

Un type publié est immuable. Publier une nouvelle définition n'affecte pas les
projets utilisant une ancienne version. La checklist est instanciée pour les
jalons sélectionnés avec correspondances explicites. Les anciens intitulés de
jalons ne sont pas assimilés automatiquement aux codes PDR/CDR/FDR. La
progression ordinaire et la progression transverse sont calculées séparément ;
les points inactifs ou non contributifs sont exclus du dénominateur.

Les statuts sont `draft`, `to_verify`, `validated`, `to_revise`, `archived`.
Soumettre exige une dernière version accessible et un vérificateur actif.
Valider exige une empreinte inchangée, un commentaire humain et tous les gates
actifs visés pour **cette version**. Un gate obligatoire ne peut pas être
désactivé. La checklist d'un livrable validé ou archivé est verrouillée jusqu'à
sa réouverture. Rouvrir ou publier une nouvelle version annule les visas des
gates ; les travaux de préparation restent distincts des visas.
Modifier la preuve d'un gate annule également son visa jusqu'à une nouvelle
confirmation explicite ; une preuve vide interdit la validation.

Les commandes partagent le verrou et la révision CAS du planning L2. Une
commande périmée est refusée sans écraser les données de l'autre opérateur.
L'historique du livrable et celui du planning reçoivent la même révision.

## Fichiers, versions et livraisons CDC

Une version publiée fige numéro, nom, empreinte SHA-256, taille, origine,
définition utilisée, état de checklist et manifeste canonique. Référence et
commentaire courants ont une table distincte ; leur correction conserve le
manifeste publié et crée un événement avec les valeurs avant/après.

Les lectures sont bornées à 50 Mio, par blocs, et vérifient qu'un fichier n'a pas
changé pendant la lecture. Un fichier modifié en place ou devenu indisponible
empêche la soumission et le visa, sans supprimer son enregistrement historique.
L'acquisition HTTP copie les octets dans une pièce gérée après contrôle du
projet, des droits et de la révision. Elle utilise un upload ou un lien réseau
du projet avec chemin relatif ; le service interne ne constitue pas une
autorisation de lire un chemin arbitraire envoyé par le navigateur.

Le raccordement CDC référence le `DeliveryVersion` original, sa même empreinte
et son fichier conservé. Il n'exécute aucune génération et ne recrée pas la
livraison. Une livraison ne peut être reliée qu'une fois. Les publications CDC
ou marquées générées restent en brouillon et ne complètent aucun gate.

## Données et droits

Neuf tables additives sont définies : types, versions de types, choix par
typologie, extensions de livrables, associations aux jalons, checklist, versions
de fichiers, métadonnées de versions et événements. Six triggers interdisent
UPDATE/DELETE sur les versions de types, versions de fichiers et événements.
L'installateur explicite vérifie colonnes, PK/FK, unicités, contraintes, index et
triggers avant toute DDL. Une sauvegarde réussie est obligatoire avant création
des tables ou protections manquantes. La réinstallation est sans écriture.

Le contexte d'opérateur est fourni par le serveur. Le propriétaire peut viser ;
un éditeur doit être relié au vérificateur désigné via la nouvelle option serveur
`AGENT_OPERATOR_PERSON_ID`. Aucun rôle, acteur ou lien personne n'est accepté
dans les commandes métier. Un lecteur ne peut écrire et une portée projet ne
permet pas d'administrer le catalogue global.

## Qualification et étapes restantes

Les tests du socle portent sur migration/retour à la copie avant DDL, conservation
des anciennes cellules, neutralité des lectures, CAS concurrent, droits/portée,
versions immuables, gates, génération sans visa, fichiers modifiés/manquants,
métadonnées et lien CDC. Une copie de la sauvegarde Agent précédant L2 reçoit
L2 puis L3 : **14 033 lignes / 116 204 cellules anciennes conservées**, zéro
FK invalide, sauvegarde préalable et retour exact à la copie avant L3 ; sources
de sauvegarde inchangées. Ce contrôle qualifie la DDL, pas encore l'archive
sélective L3 ni le déplacement des fichiers lors d'une restauration globale.

Travail restant avant livraison/activation L3 :

- raccordement UI de l'administration et de la sélection ; les routes sont
  enregistrées dans le candidat avec les commandes historiques et gates ;
- interface complète avec filtres, sélection, checklists, visa et conflits
  explicites, conservation des brouillons lors de la navigation ;
- recette navigateur, tests Python/Ruff et React/TypeScript/build du candidat
  fusionné, activation sauvegardée sur `8001` et vérification en lecture seule.

Le transport dans le worktree conserve désormais les projets L3 par archive v5,
avec fichiers et dépendances, ainsi que les formats existants v2/v3/v4. Les modules
CDC, CDC & BE, Revues, Atelier et Sage sont conservés ; aucun code financier
n'est ajouté, aucune donnée n'est supprimée et XPilot `8000` reste intact.

Qualification enregistrée du socle : **488 tests Python réussis, 1 ignoré**, dont **29 cas L3** ; Ruff conforme. Preuve : `.ui-preview/xpilot-l3/foundation-result.json`. Les contrôles React/build et la recette navigateur L3 restent à effectuer lors du raccordement des écrans. Cette étape ne constitue pas la livraison du lot L3.

## Adaptateurs HTTP et acquisition — L3.3

`project_deliverables.py` dans les routers expose les commandes sous
`/api/v1/projects/{project_id}/deliverable-plan` : liste, détail, checklist,
versions, métadonnées, transitions, historique et sélection aperçu/application.
Le catalogue utilise `/api/v1/deliverable-types` ; les compositions
passent par `/api/v1/project-references/{typology_id}/deliverable-types`.
Ces routers sont enregistrés dans `app.main` du worktree et testés avec la
protection locale du mono-serveur sur bases fictives et copies sauvegardées.

Le service `deliverable_queries.py` filtre avant pagination (statut documentaire,
catégorie, jalon, responsable, vérificateur, activation et recherche littérale
insensible aux accents/casse). Les agrégats de progression, versions et liens
de page sont groupés : le nombre de requêtes ne croît pas avec celui des fiches
affichées. Les lectures ne créent aucun plan pour les données historiques.
Checklist, versions et historique ont des pages de 1 à 200 éléments ; le détail
d'un événement fournit les valeurs avant/après et son acteur original.

`deliverable_files.py` contrôle droits et révision avant acquisition. Un fichier
uploadé est conservé dans un dossier unique sous `MINIPILOT_HOME/deliverable-files`.
La copie réseau exige un lien du même projet et un chemin relatif sans traversée.
Un lien vers un fichier ne permet pas de copier son voisin. Après contrôle de
taille (50 Mio maximum) et de stabilité pendant la copie, seule la pièce locale
est publiée. Une modification ultérieure du réseau n'altère pas la version.
Les noms simples sont validés ; le parser multipart conserve le nom de base
des chemins Windows fournis par le navigateur. La liaison CDC conserve exactement
sa livraison et ses octets, sans génération.

Un échec de copie ou une commande périmée ne crée aucune version. Si des octets
ont déjà été copiés avant un conflit ou une interruption, leur pièce reste
conservée ; aucune purge n'est effectuée. Le téléchargement vérifie le manifeste
et fige une réponse de 50 Mio maximum contrôlée par SHA/taille, sans rouvrir le
chemin après vérification. Il utilise une pièce jointe, `nosniff` et `no-store`.
Un chemin relocalisé hors stockage géré ou une pièce modifiée/absente est refusé ;
le manifeste historique reste lisible sans dépendre de l'accès au fichier.

Les commandes HTTP valident leurs entrées, committent uniquement après succès
et rollbackent tout échec. Un lecteur peut préparer l'aperçu sans appliquer ;
la portée et les contrôles métier valent aussi lors d'appels sans HTTP.
Les commandes historiques, gates et installation explicite sont raccordés
ci-dessous. L3.5/L3.6 portent encore l'interface, la recette et l'activation
sauvegardée. Le lot L3 n'est pas livré.

## Commandes historiques, gates et démarrage

Les routes héritées de création/modification de `deliverables` acceptent une
`expected_revision` optionnelle et utilisent le même verrou que le planning
et les nouvelles commandes. Sans révision, elles invalident les vues anciennes ;
avec une révision périmée, elles refusent la modification. Elles gardent UUID,
titre, statut historique et forme de réponse, avec ajout de la révision.
Le statut `done` reste distinct du visa et ne modifie aucun statut documentaire.
Les événements capturent `legacy_status` seulement lors d'une commande explicite.
Les anciennes traces restent lisibles ; le contrat v5 compare la chaîne et le
statut final lorsqu'une trace explicite existe, sans réécrire les anciens événements.

`deliverable_gates.py` vérifie les gates des livrables sélectionnés et associés
au jalon : dernière version, preuve humaine, acteur/date et empreinte du fichier.
Un gate propre à une étape ultérieure reste hors de la validation de l'étape
actuelle. Un gate sans jalon spécifique s'applique aux jalons explicitement
associés à son livrable. Désélectionner un livrable le conserve dans les données
et l'historique, mais le retire du périmètre actif. Aucun intitulé historique
ne sert de correspondance implicite. Un fichier modifié ou une nouvelle version
annulant les visas interdit également une confirmation de jalon déjà validé.

Le contrôle est dans `_patch_milestone`, après acquisition du verrou et avant
modification des dates, statut, historique ou ouverture du successeur. Il vaut
pour les routes moderne/historique et appels internes. Une date réelle peut
être renseignée indépendamment sans valider le workflow. La lecture
`deliverable-plan/milestones/{id}/gates` expose les bloqueurs sans écrire.

Le démarrage du candidat prévalide les tables/protections L3 existantes avant
la DDL des autres domaines. Il crée les prérequis L1/L2, puis appelle
`install_deliverable_schema` explicitement ; les tables L3 restent exclues du
`create_all` général. L'ERP enregistre la révision de schéma 7. Une sauvegarde
réussie précède les changements, une installation incompatible ou un échec de
sauvegarde arrête le démarrage, et la seconde exécution n'écrit pas de données
ni de sauvegarde supplémentaire. Aucun catalogue ni sélection n'est créé.
Une jonction redirigeant `deliverable-files` hors du dossier Agent est refusée
avant acquisition, testé sur un vrai dossier Windows.
La réflexion des contraintes de planning reste sur une connexion pendant tout
le contrôle, pour éviter des résultats incohérents après recréation des tables
dans un pool SQLite. Les exigences de clés, unicités et protections sont conservées.

Recette du démarrage réel sur copies de la sauvegarde Agent : **1 456 lignes /
12 939 cellules ERP anciennes conservées**, dix projets et leurs livrables lus
par les routes enregistrées sans mutation, six protections immuables et zéro FK.
La copie Brain, les deux bases originales et le retour à la copie avant DDL
sont conservés. Nouvelle recette après correction de réflexion SQLite :
`.ui-preview/xpilot-l3/startup-on-saved-agent-v2/result.json` ; la première preuve
`startup-on-saved-agent/result.json` reste conservée.
Les workers et le serveur actif ne participent pas à cette recette.

## Administration et sélection — L3.2

Le service `deliverable_catalogue.py` complète le catalogue : listes paginées,
recherche littérale insensible aux accents, détail des types et anciennes
versions. Le rang métier est défini dans la version publiée et appliqué avant
pagination. Nom et activation du type ont leur révision CAS ; catégorie, BE,
ordre et checklist changent par publication d'une nouvelle définition immuable.
L'administration reste réservée au propriétaire sans restriction de portée.
Les modifications sont tracées dans l'historique des référentiels L1.

La composition d'une typologie conserve ses liens désactivés et partage la
révision du référentiel d'identité : une édition concurrente de la fiche du
référentiel ou de sa composition ne peut écraser l'autre. Les lectures d'une
typologie sont limitées aux références des projets autorisés. Les types communs
du catalogue restent lisibles par les lecteurs. Les personnes assignées aux
livrables et leur historique rejoignent les sélecteurs autorisés, même si elles
ne figurent pas dans l'équipe L1 ; les personnes d'autres projets restent cachées.

La sélection projet reçoit des versions exactes, les correspondances de jalons
et les exclusions explicites. La typologie demandée doit correspondre à celle
de la fiche ; ce parcours ne la remplace pas. Un point conditionnel
`typology_codes` s'applique à la typologie réelle du projet. Les deux visas XPilot
« si modification » sont explicitement annotés dans le catalogue suggéré.
Une typologie indéterminée ou un jalon ni rattaché ni exclu bloque l'application.
Les anciennes définitions sans ces nouveaux champs restent lisibles avec leur
empreinte d'origine ; leur contenu publié n'est pas normalisé en place.

L'aperçu ne crée aucune donnée. Son empreinte lie projet/révision, fiche et
typologie, versions et révisions des types, choix et opérations. Après acquisition
du verrou SQLite partagé L2, l'application relit ces valeurs et refuse un aperçu
périmé. Une seule révision et un seul événement Planning couvrent toute la
sélection ; chaque livrable changé reçoit son événement immuable. Même si aucun
livrable ne change, une confirmation valide conserve une trace et avance la
révision sans créer de doublon.

Les opérations possibles sont création, adoption explicite d'un livrable manuel,
réactivation, conservation et désactivation explicitement demandée. Une adoption
conserve titre, statut historique, personnes déjà désignées, checklist et
versions ; elle ajoute seulement les points et liens manquants. Plusieurs fiches
du même type exigent le choix d'une cible. Une nouvelle version de catalogue
sélectionnée ne remplace jamais la définition ni la checklist d'une fiche déjà
typée ; l'aperçu avertit de la version conservée. Les livrables personnalisés
ou historiques sans type ne sont pas désactivés par une sélection de catalogue.
Un livrable validé ou à vérifier doit être rouvert/archivé avant désactivation ;
une sélection ne rouvre pas implicitement un document archivé.

Cette étape n'ajoute pas de table ni de colonne ERP et n'enregistre pas encore
de route HTTP. Le raccordement des écrans, des commandes historiques/gates de
jalons et des archives/restaurations reste nécessaire avant livraison L3.

Qualification L3.2 enregistrée : **509 tests Python réussis, 1 ignoré**, dont **50 cas L3 (21 catalogue)** ; Ruff conforme. Preuve : `.ui-preview/xpilot-l3/catalogue-result.json`. Les anciens chiffres du socle décrivent sa qualification précédente ; ce résultat couvre les services courants. React/build/recette restent à effectuer après intégration UI. L3 reste en cours et non activé.

## L3.4 — Fichiers portables dans la sauvegarde globale

Le chemin `project_deliverable_file_versions.path` reste celui de la publication,
protégé avec le manifeste par les triggers immuables. Le nouvel emplacement de
lecture est `project_deliverable_version_metadata.storage_path` ; une valeur
vide conserve la compatibilité avec le chemin original. Publication, lecture
des preuves et visa utilisent cette résolution sans modifier la version ni son
empreinte. Ce champ interne n'est pas modifiable par la commande de métadonnées.

`create_backup` prend les deux instantanés SQLite, puis associe chaque version
à une pièce gérée sous ERP ou storage. La liaison `deliverable_files` de
`backup.json` contient zone, chemin relatif, projet, SHA-256 et taille. Le fichier
source puis la pièce effectivement copiée doivent correspondre à la version
publiée. Un fichier absent/modifié, des métadonnées incohérentes ou une pièce hors
stockage refusent la sauvegarde complète : aucun manifeste final ni statut
« créée » n'est publié pour une copie partielle. La copie partielle reste
disponible pour diagnostic ; le service n'efface aucune donnée.

La restauration exige un dossier neuf. Avant de le créer, elle vérifie les
empreintes de l'archive, les manifests immuables et l'ensemble exact des liaisons
de versions. Tous les chemins du manifeste global doivent être relatifs,
canoniques et contenus dans la sauvegarde : pas de chemin absolu, `..`,
séparateur Windows, préfixe de lecteur ni chemin normalisable différent.
Les enveloppes/listes de pièces mal formées sont refusées avant toute copie.
Aucun propriétaire inconnu,
liaison manquante ou taille différente n'est accepté. Une ancienne sauvegarde
globale v1 sans ces liaisons recherche les pièces par SHA-256 exact parmi ses
fichiers ERP/storage ; les noms seuls ou les anciens chemins absolus ne suffisent
pas. Après copie, seuls les emplacements des métadonnées L3 sont relocalisés.
Les versions de fichiers/types, historique, référence/commentaire éditables,
checklists et visas restent identiques. Le lien à la livraison CDC retrouve la
même pièce restaurée. Une copie restaurée peut être sauvegardée à nouveau.

L'installateur L3 ajoute `storage_path TEXT NOT NULL DEFAULT ''` aux métadonnées
d'un schéma L3 antérieur après sauvegarde explicite. Il vérifie toujours les
colonnes existantes, contraintes et six triggers ; une sauvegarde en échec
interdit le DDL. La restauration d'une ancienne archive ajoute uniquement cette
colonne dans la copie déjà contrôlée. Les instantanés sources restent inchangés.
La preuve `.ui-preview/xpilot-l3/portable-column-on-saved-agent/result.json`
qualifie cet ajout sur une copie du socle L3 historique : **14 033 lignes et
116 204 cellules conservées**, six triggers, zéro violation FK, second passage
sans modification et copie de retour avant ajout exactement conservée.

Ce volet ne termine pas L3.4 : l'archive sélective v5 doit encore préserver types,
versions, compositions de typologie et personnes historiques, puis remapper les
identifiants selon leur nature. En particulier `version_id` d'un événement de
livrable désigne une version de fichier, distincte d'une version de planning.
Les anciennes archives v2/v3/v4 gardent leur contrat. Le refus temporaire d'export
d'un projet comportant des données L3 reste actif jusqu'à cette qualification.
Routes, commandes historiques/gates de jalons, écrans et activation restent
ouverts ; le serveur unique `8001` reste L2, et XPilot `8000` reste intact.

Qualification de la restauration globale L3.4 : **544 tests Python réussis, 1 ignoré**, dont **85 cas L3 (35 restauration)** ; Ruff et contrôle du diff conformes. Preuve : `.ui-preview/xpilot-l3/file-recovery-result.json`. Cette qualification remplace les empreintes de code du résultat L3.2, qui reste un relevé historique. L3.4 reste en cours pour les archives sélectives ; L3 n’est pas activé.

## L3.4 — Contrat d'archive sélective v5 et provenance v2

Le service `project_deliverable_archive.py` prépare la fermeture des dépendances,
la validation et le remappage ; le transport d'import/export n'est pas encore
raccordé. Le refus temporaire d'export L3 reste en place. Le contrat reçoit les
tables projet, les références L1 et une section `deliverable_references` prévue
pour les types, leurs versions, les liens de composition et l'historique global
des types/typologies concernés. Cette section n'autorise pas de référentiels
étrangers au projet à se justifier par leurs propres événements.

La fermeture tient compte des plans et de leurs responsables/vérificateurs,
des manifests et anciennes définitions, de l'historique des rôles, des choix de
sélection et des compositions actuelles ou historiques des typologies du projet.
Une composition reste conservable même sans livrable sélectionné ni état de
planning encore créé. Un état partagé est exigé dès qu'il existe des commandes
ou données L3 de projet. Les définitions anciennes sans rang/conditions restent
lisibles avec leur contenu et SHA-256 publiés, sans normalisation en place.

Les validations comprennent unicité des identifiants et numéros, appartenance
au projet/livrable, parents et métadonnées obligatoires, liens CDC de même
empreinte, pièces et contrôles historiques, auteurs/dates et formes d'événements
connues. Les nombres de versions sont contrôlés sans allocation proportionnelle
à un numéro arbitraire. Un livrable validé doit avoir version, vérificateur,
activité et gates visés sur sa dernière version. La chronologie impose les
publications successives, les transitions sur la version courante et la
correspondance de l'état final avec les événements. Chaque publication a sa trace.

Un événement de livrable partage révision/acteur avec le Planning L2. Les
commandes ordinaires exigent des instantanés correspondants ; une sélection
atomique accepte plusieurs événements détaillés sous une seule révision, avec
opérations, adoption et activation cohérentes. Le champ `version_id` est traité
selon l'action : version de fichier pour publication/visa/métadonnées, version
de type pour les opérations de sélection. Les clés `existing_mapping` sont des
identifiants de types, les clés `milestone_mapping` sont des codes ; seules les
valeurs du second changent. Labels, titres, commentaires, preuves, codes et
auteurs restent textuels, même lorsqu'ils sont identiques à un UUID connu.

Le format de manifeste de fichier **v2** ajoute `source_publication` : identité
de version originale, texte exact de son manifeste v1 et SHA-256. Les identifiants
du nouvel instantané sont remappés et son empreinte recalculée avant insertion ;
la publication source reste verbatim. Les événements de publication reçoivent
l'empreinte de ce nouvel instantané. Un second import conserve la même feuille
v1 ; il n'empile pas des manifests v2 récursifs. Taille, empreinte de fichier,
numéro, nom, référence/commentaire de publication, origine générée et acteur
doivent rester conformes à la source. Une livraison CDC garde son origine générée.

Le parseur commun `app/services/deliverable_manifest.py` vérifie champs,
encodage canonique, empreintes, contrôles et provenance. Les services de visa et
de restauration globale utilisent les mêmes règles. Les formats de sauvegarde
globale et de transport projet sont distincts : le premier garde sa version 1
avec lecture des manifests de fichiers v1/v2 ; le transport projet du worktree
accepte désormais v2/v3/v4/v5. Le runtime actif reste L2.

Les essais construisent un projet fictif avec ancienne définition, deux versions
de fichier, réouverture et visa humain, adoption d'un livrable CDC historique,
personne anciennement assignée et composition désactivée. Ils vérifient le
remappage puis une insertion dans une autre base avec tous les triggers actifs,
une sauvegarde/restauration globale et un visa toujours lisible. Les originaux
restent inchangés. Cette preuve de données/manifests ne constitue pas encore une
recette des écrans/API de gestion des livrables ; la qualification ultérieure
du transport ci-dessous couvre les imports/exports internes et leurs pièces.

Qualification historique du contrat d’archive L3.4 : **590 tests Python réussis, 1 ignoré**, dont **131 cas L3 (46 contrat v5)** ; Ruff et contrôle du diff conformes. Preuve : `.ui-preview/xpilot-l3/archive-contract-result.json`. Les contrôles de checklist et services SQL décrits ci-dessous sont postérieurs à ce relevé. Le transport v5, les écrans et l’activation restent ouverts.

### Contrôles de checklist et services SQL sélectifs — 6 octobre 2026

L'adoption conserve les contrôles manuels compatibles et leur preuve humaine.
Si un point de même code/périmètre masque un gate obligatoire (point ordinaire,
inactif, autre jalon ou flags différents), l'aperçu expose le conflit et l'application
est refusée sans écriture. Choisir un type avec un code distinct ou un autre livrable
permet de conserver les deux contrôles ; aucun point n'est supprimé ou écrasé.

Le contrat compare les champs fixes des contrôles à leurs captures historiques.
Il rejoue les snapshots connus, les publications et les réouvertures, vérifie les
états précédents et courants, et remet les seuls visas à zéro dans sa représentation
en mémoire. Un visa historique ne peut s'appuyer sur des gates déjà réinitialisés.
Les dates avec/sans offset UTC issues de JSON/SQLite sont comparées par instant.
Ces contrôles vérifient la cohérence des données ; ils ne constituent pas une
signature cryptographique d'une action humaine.

`project_deliverable_archive_store.py` lit les versions/types utilisés, la composition
actuelle et ses types retirés dans l'historique, puis toutes les versions figées de
ces types. Les logs d'autres projets ne justifient aucun import global. Une composition
est conservée même sans plan de livrable ni état de Planning. Les types/personnes
sans lien sont exclus. Ces fonctions sont raccordées au transport projet dans
le worktree et ne déclenchent aucune migration.

La réconciliation s'effectue après validation du contrat et des références L1,
sous le verrou d'import pris par le transport. Une tête exacte est réutilisée
par ID/code et garde sa révision ; chaque version doit être strictement identique
(définition publiée, hash, acteur, date). Une version absente d'une tête existante
ne peut être publiée implicitement. Compositions, liens inactifs et journaux sont
comparés avant toute insertion. Les données divergentes entraînent un conflit 409.
Les nouvelles lignes sont seulement préparées, et les correspondances d'identifiants
ne sont appliquées au dictionnaire de l'appelant qu'après succès de tous les contrôles.

Les tests SQL ciblés couvrent export exact, exclusions, composition seule, réutilisation
par clés métier avec UUID différents, insertion sous triggers immuables, refus de
publication implicite, conflits d'ID/code et de contenu, mapping atomique et absence
de DDL implicite. La recette `.ui-preview/xpilot-l3/archive-store-on-saved-agent/result.json`
vérifie les lectures SQL des dix projets d'une copie de la paire historique Agent : toutes
les cellules conservées, six protections immuables, zéro FK invalide, sources
inchangées. Elle qualifie les lectures SQL ; la recette de transport est décrite ci-dessous.

Qualification historique des services SQL L3.4 : **621 tests Python réussis, 1 ignoré**, dont **162 cas L3** (**18 SQL, 53 contrat v5**). Ruff et contrôle du diff conformes. Preuve : `.ui-preview/xpilot-l3/archive-store-result.json`. Le raccordement du transport décrit ci-dessous est postérieur à ce relevé ; le serveur reste L2.

### Transport v5 et fermeture des preuves mail — 6 octobre 2026

`project_archive.py` exporte/importe les données L3 avec `deliverable_references`
(types, versions exactes, compositions actives/inactives et journaux liés). Les
anciens projets conservent v2/v3/v4 ; une ancienne enveloppe ne peut contenir de
données L3 non vides. Une composition seule utilise v5 et conserve l'absence
d'état de Planning. Les modèles chargés ne provoquent pas de tables L3 ni de
sauvegardes répétées au démarrage L2 : l'installateur reste une étape explicite.

Le module `project_archive_v5.py` filtre les seules actions L3 du validateur
Planning L2, qui valide les autres actions sans modifier la révision partagée.
Les fichiers ordinaires portent la zone `deliverable` ; un fichier lié au CDC
réutilise la zone `delivery` et son empreinte/taille publiées. Pièces manquantes,
altérées même après recalcul du hash d'enveloppe, inconnues/dupliquées, destinations
hors stockage ou déjà présentes avec d'autres octets sont refusées avant écriture.
Les manifests et événements reçoivent leurs nouveaux identifiants/hashes sous les
protections immuables. Seul `version_metadata.storage_path` est relocalisé ; le
chemin, nom et preuve de publication originaux restent conservés. La restauration
globale des données issues du transport v5 est aussi testée.

La recette historique a révélé des propositions projet dont le mail parent est
encore non classé. `project_archive_brain.py` ajoute seulement ces parents utilisés
et leurs textes/pièces ; ils gardent `project_id=None` et leur statut. Un mail non
classé sans relation au projet est refusé. Une référence à un mail appartenant à
un autre projet refuse l'export et indique la sauvegarde globale, au lieu de
supprimer la proposition ou transférer ses sources. À l'import, un hash de source
présent dans un autre cœur canonique est refusé avant écriture de fichiers ;
réutiliser le projet Brain d'origine ou restaurer dans une paire neuve conserve
les identités canoniques et évite une duplication forcée.

La recette `.ui-preview/xpilot-l3/archive-transport-on-saved-agent-v4/result.json`
examine les dix projets historiques restaurés dans une nouvelle copie : neuf
aller-retours avec leurs anciens formats puis neuf en v5, dans deux paires cibles
distinctes. Les visas et octets sont relus, les exports sont réémis, les six triggers
L3 restent actifs et zéro FK invalide est constaté. Les 1 456 lignes/12 939 cellules
ERP déjà présentes dans la copie sont conservées ; les deux fichiers de base de
la sauvegarde originale sont inchangés. Le dixième projet dépasse la limite de
150 Mio et est refusé avec code 413 et indication de la sauvegarde globale. Cette
limite est conservée ; le projet n'est pas tronqué. Les essais sur bases fictives
couvrent aussi les archives avec modèles/baselines L2, chevauchement de namespaces
ERP/Brain et réutilisation du cœur Brain d'origine.

Qualification historique du transport L3.4 : **653 tests Python réussis, 1 ignoré**, dont **194 cas L3 (32 transport)**. Ruff et contrôle du diff conformes. Preuve : `.ui-preview/xpilot-l3/archive-transport-result.json`. L3.4 est terminé dans le worktree ; à cette étape, L3.3/L3.5/L3.6 restaient ouverts avant activation 8001.

Qualification historique des adaptateurs HTTP/fichiers L3.3 : **688 tests Python réussis, 1 ignoré**, dont **35 cas HTTP/fichiers**. Ruff et contrôle du diff conformes. Preuve : `.ui-preview/xpilot-l3/http-files-result.json`. À cette étape, la qualification était isolée, sans enregistrement dans Agent ni activation ; le raccordement des commandes historiques/gates et l'installation explicite décrits plus haut sont postérieurs à ce relevé.

Qualification du candidat enregistré L3.3 : **702 tests Python réussis, 1 ignoré**, dont **36 cas HTTP/fichiers** et **13 cas de raccordement**. Ruff et contrôle du diff conformes. Les anciennes erreurs de réflexion SQLite après remise à zéro de la base de test sont corrigées par une vérification sur une connexion unique, sans diminuer les contraintes. La prévisualisation de sélection est explicitement reconnue comme lecture. La recette sur nouvelle copie sauvegardée conserve 1 456 lignes/12 939 cellules ERP, une sauvegarde préalable exacte et zéro FK invalide. Preuve : `.ui-preview/xpilot-l3/registered-integration-result.json`. L3.3 est terminé dans le worktree ; L3.5/interface et L3.6/activation restent à réaliser.

## Interface L3.5 — liste et fiche, première étape

`web/src/lib/projectDeliverables.ts` décrit les contrats et adaptateurs L3.
`ProjectDeliverablesPanel.tsx` étend le sous-onglet Livrables dans Projets/Planning.
La liste affiche le total du serveur, recherche, filtres documentaires/catégorie,
affectations et jalon, sélection active/inactive, avancement ordinaire/transverse
et dernière version. Un travail « Terminé » conserve un document « Brouillon »
tant qu'aucun visa documentaire n'a été confirmé.

Création et fiche conservent la saisie après erreur. Un conflit charge une
comparaison ; seul un choix explicite prépare le brouillon sur la nouvelle
révision. Les champs non modifiés d'un collègue sont conservés. Les formulaires
de fiche et de statut de travail se protègent mutuellement lorsque l'un porte
un brouillon. Fermeture et navigation sont verrouillées pendant une commande.
Le lecteur consulte sans commande ni marqueur de saisie. Changer de projet
ignore les réponses tardives ; masquer un onglet conserve sa saisie et suspend
les lectures de liste. Les transitions de rubrique et fermeture préviennent
l'abandon d'une saisie. Le titre et la fermeture restent visibles sous le menu fixe.

La recette sur bases fictives utilise le port temporaire 18231 : pagination
27 éléments, passage à 28 après création, recherche donnant un résultat,
sauvegarde de commentaire et statut de travail sans visa. Les vues à 390, 650
et 1280 pixels n'ajoutent pas de débordement horizontal à la page ; les tableaux
gardent leur propre défilement. La recette conserve ses bases et captures, puis
arrête le serveur temporaire. Le serveur actif 8001 et XPilot restent inchangés.

Qualification de cette première étape : **168 tests React réussis**, dont **13
cas Livrables**, TypeScript/build/Ruff conformes. Le backend n'a pas changé ;
ses empreintes correspondent à la qualification de 702 tests Python/1 ignoré.
La checklist était consultable en lecture seule à cette première étape ; les
commandes de checklist et validation décrites ci-dessous lui succèdent.

## Interface L3.5 — checklist et validation documentaire

La checklist utilise une liste serveur paginée à 25 points, recherche littérale
et inclusion explicite des points inactifs. Sa progression garde le total
global de la fiche. Un point manuel précise code stable, intitulé, portée jalon,
visa obligatoire, progression transverse et contribution au total. Le sélecteur
de jalon est nommé, recherchable et paginé ; seuls les jalons déjà associés au
livrable sont sélectionnables. Aucun point ajouté ne reçoit de visa implicitement.

L'édition distingue préparation et visa. Preuve, commentaire et identité/date
de confirmation sont visibles. Le profil éditeur modifie les préparations ;
les gates sont réservés au vérificateur désigné ou au propriétaire selon les
droits renvoyés par le serveur. Un gate ne peut être désactivé. Confirmer un visa
requiert une version publiée et une preuve non vide. Modifier son intitulé ou sa
preuve retire la confirmation affichée, qui doit être donnée à nouveau. Un ancien
visa sur une autre version n'apparaît pas comme confirmation de la version actuelle.
Le serveur reste l'autorité pour le périmètre, les droits et les octets vérifiés.

La rubrique Validation présente les visas manquants et les transitions possibles.
Soumettre exige un vérificateur et un livrable actif ; valider exige les visas,
un commentaire humain et une confirmation de l'action sur la version affichée.
Toutes les commandes transmettent la révision et l'identifiant de dernière
version capturés. La réouverture retire les visas des gates sans effacer les preuves ni les
préparations. Les documents validés/archivés verrouillent l'édition de checklist.
Archivage et réouverture restent des changements d'état, aucune donnée n'est supprimée.

Une erreur conserve la saisie. La comparaison affiche les valeurs actuelles et
le brouillon ; la préparation explicite reprend les champs non modifiés du collègue.
La reprise d'un visa ou d'une décision documentaire retire la confirmation humaine,
qui doit être redonnée pour le contexte actuel. Une action devenue impossible,
un jalon détaché ou un droit perdu empêche l'enregistrement. La fermeture et les
rubriques se verrouillent pendant les commandes ; abandonner un brouillon demande
une confirmation locale. Le statut de travail est remonté seulement lors d'une
nouvelle révision, pour éviter qu'un effet tardif de montage remplace une saisie rapide.
Les dates SQLite de preuve sans suffixe sont interprétées comme UTC à l'affichage,
sans modifier les horodatages immuables.

La version visée affiche son numéro, sa référence et son fichier, avec
l'identifiant exact consultable. Sa lecture descriptive ne remplace jamais la
révision ni l'identifiant capturés par le formulaire. Si ses métadonnées sont
indisponibles, la fiche et ses preuves restent consultables.

Qualification de cette étape : **702 tests Python réussis, un ignoré**, **195
tests React réussis** dont 40 cas Livrables (14 liste/fiche, 14 checklist, 8
validation, 4 dates/client), TypeScript/build/Ruff et contrôle du diff conformes.
La recette sur une paire fictive à 18232 confirme ajout immédiat, préparation,
preuve/visa, soumission, validation, verrouillage et réouverture conservant la
préparation. Un vrai conflit HTTP préserve brouillon et commentaire du collègue,
puis impose de reconfirmer le visa. Le parcours final vérifie la validation au
clavier et le contexte de fichier nommé. À 390/650/1280 pixels, la page ne déborde
pas horizontalement. La lecture finale vérifie la révision 48, le visa sur la
dernière version, les octets et leur SHA-256 ; aucun fichier réel n'est utilisé.
Preuve : `.ui-preview/xpilot-l3/ui-checklist-result.json`. Les anciens rapports
d'échec sont conservés ; la qualification finale couvre les corrections.
Le serveur de recette et le navigateur sont fermés après ces contrôles.

À l'issue de cette qualification historique, restaient : versions et fichiers, historique, sélection avec aperçu,
catalogue dans Réglages, retours des gates jalons, recette complète puis activation
L3.6. L3.5 et l'objectif intégral L4–L9 restent en cours. Cette interface est dans
le worktree ; la version active du serveur unique 8001 reste L2.

## Interface L3.5 — versions, fichiers et historique

La fiche propose Fiche, Checklist, Versions, Validation et Historique.
La liste des versions est paginée par le serveur à 25 entrées, avec référence,
nom de fichier, numéro, taille, date et empreintes. La version CDC conserve
l'identifiant exact de sa livraison d'origine et indique son caractère généré.

La publication choisit un fichier local non vide de 50 Mio maximum, un lien réseau
enregistré dans le projet avec chemin relatif, ou une livraison CDC existante.
Elle ne régénère pas le CDC. Référence et confirmation humaine sont obligatoires ;
changer le fichier ou sa source retire la confirmation. Publier revient au brouillon,
retire les visas obligatoires et conserve les préparations. Le serveur contrôle
droits, révision, chemin et octets. Un document archivé interdit la publication.
Les sources réseau/CDC utilisent les listes existantes du projet, actuellement non
paginées. Une source indisponible reste une erreur visible avec reprise explicite.

Le détail sépare référence/commentaire actuels et manifeste publié immuable.
Enregistrer envoie seulement les métadonnées modifiées et la révision capturée,
sans réécrire fichier, manifeste ou visas. Une comparaison concurrente garde les
champs modifiés de l'utilisateur et reprend les autres champs du collègue ; elle
refuse un contexte lu sur deux révisions différentes. Les erreurs conservent aussi
le fichier choisi et le chemin d'une publication. Après comparaison de publication,
la confirmation doit être redonnée. Fermeture/navigation restent verrouillées
pendant les commandes ; les brouillons sont protégés lors d'un abandon.

Télécharger le fichier exige une vérification d'empreinte côté serveur. Le manifeste
reste consultable séparément. La lecture est annulable et bornée à 60 secondes.
La reprise d'un téléchargement en erreur conserve les métadonnées saisies. Un
lien « Enregistrer [fichier] » conserve les mêmes octets vérifiés en mémoire pour
les navigateurs bloquant le téléchargement automatique ; il est libéré à la
fermeture ou au remplacement du téléchargement. Le journal paginé traduit les
actions métier et affiche les valeurs avant/après en lecture seule. Le changement
de page ferme le détail précédent ; les réponses tardives sont annulées/ignorées.

Qualification : **219 tests React réussis**, dont **64 cas Livrables** (15 liste/fiche,
14 checklist, 8 validation, 7 client, 15 versions, 5 historique), TypeScript/build,
Ruff et contrôle du diff conformes. La suite Python complète confirme **702 réussites
et un test ignoré** ; les empreintes backend correspondent au candidat enregistré.
Les premiers rapports d'échec sont conservés : incompatibilité Blob/Response dans
un mock de test, expirations sous forte parallélisation, puis ciblage ambigu de la
pagination des filtres. La pagination principale possède maintenant un groupe
accessible nommé ; les assertions et délais des tests sont conservés.

La recette sur données exclusivement fictives à 18233 passe de la révision 62 à 70,
de 27 à 31 versions et atteint 44 événements. Elle vérifie les trois sources de
publication, la remise à zéro des visas, la préparation conservée, les conflits
réels de métadonnées et de publication avec reconfirmation, l'avant/après et les
deux pages du journal. Un fichier fictif volontairement corrompu est refusé sans
perdre la saisie ; son manifeste reste accessible. Le fichier est rétabli exactement,
avec octets d'origine et corrompus conservés dans la recette. Les 31 fichiers et
manifestes ont été vérifiés par SHA-256 ; le CDC copié conserve ses octets exacts.
Les captures du build final à 390/650/1280 pixels confirment un document sans
débordement horizontal, avec défilement propre aux tableaux.

**Limite de recette du téléchargement :** le navigateur intégré affiche le lien
Blob prêt, mais ses outils de capture de téléchargement expirent. La sauvegarde
effective d'un fichier par ce navigateur n'est pas qualifiée ; seuls les octets HTTP,
le manifeste et le lien prêt sont confirmés. Cette vérification reste au périmètre
de la recette complète L3.5. Preuve : `.ui-preview/xpilot-l3/ui-files-result.json`.
Le navigateur est fermé, sa taille rétablie et le serveur fictif arrêté. Aucun
fichier, module ou donnée réel n'a été supprimé et aucun commit/push n'a été réalisé.

Restent : sélection avec aperçu et associations explicites, catalogue Réglages,
retours des gates jalons, recette complète incluant sauvegarde du téléchargement,
puis fusion/activation sauvegardée L3.6. À cette étape, L3.5 restait en cours ; L4–L9 conservent
leur périmètre intégral. Le serveur Agent unique sur 8001 reste actif L2.

## Interface L3.5 — sélection liée à un aperçu

« Sélection depuis le catalogue » prépare les pièces attendues dans Projets →
Planning → Livrables. Le catalogue et ses publications utilisent les pages serveur
à 25 entrées, recherche bornée et filtre facultatif sur la typologie actuelle de
la fiche. Aucun catalogue n'est créé à la lecture. Un type sans publication ne
peut être choisi. Une publication antérieure peut être choisie explicitement ;
l'identifiant, le numéro, l'empreinte et la définition lus restent ceux de cette
version. Au maximum 100 types distincts sont conservés dans le brouillon.

Chaque code de jalon actif propose un jalon existant du projet ou une exclusion
explicite de ses contrôles. Choisir l'un retire l'autre. Aucune correspondance
de nom historique n'est appliquée automatiquement. Les contrôles conditionnels
suivent la typologie actuelle, vérifiée de nouveau par le serveur. Les versions
choisies affichent catégories, métier BE, contrôles et conditions. Retirer un type
du brouillon retire ses seules correspondances devenues inutiles.

Une cible existante peut être choisie pour chaque type : fiche personnalisée à
adopter, ou fiche du même type à départager. Le sélecteur recherche et pagine les
fiches du projet, avec noms et statut ; il interdit les fiches déjà d'un autre type
et les cibles utilisées par un autre choix. Le serveur contrôle les collisions
de checklist et les états documentaires avant toute adoption. À défaut de cible,
il garde la fiche de même type ou en ajoute une, selon l'aperçu. Les responsables
et vérificateurs proposés complètent les nouvelles fiches ou les champs vides,
sans remplacer les affectations existantes.

L'aperçu affiche opérations, versions choisies, jalons nommés, exclusions,
blocages et vigilances. Une version plus récente proposée au catalogue ne remplace
pas silencieusement la checklist utilisée par le projet : l'aperçu avertit de la
version conservée. « Désélectionner les types absents » est un choix explicite,
avec conservation des données et aperçu des fiches concernées. Les fiches
personnalisées non adoptées restent conservées dans la sélection.

L'application exige une confirmation humaine, l'absence de blocage, les droits
d'écriture actuels et la même révision/empreinte que l'aperçu. Elle transmet
exactement les paramètres capturés lors du calcul. Tout changement, nouveau
calcul ou échec retire l'aperçu et la confirmation. Une erreur conserve les choix.
« Relire et comparer » affiche révision et typologie actuelles ; préparer ce
contexte conserve les versions/correspondances/exclusions, mais impose un nouveau
calcul et une nouvelle confirmation. Un aperçu portant sur un autre projet ou
une autre révision est refusé. Le profil lecteur consulte et calcule sans action
d'application ni marqueur de données à sauvegarder.

Les lectures de catalogue/publication/identité/aperçu sont annulables. Les réponses
tardives après fermeture/inactivité ne remplacent pas les choix. Fermeture et
navigation restent verrouillées pendant lecture de version, calcul ou application.
Les choix d'un éditeur portent le marqueur de brouillon déjà utilisé par la
navigation globale. Après application, la liste et les compteurs se relisent
immédiatement ; l'adoption garde le titre et le fichier d'origine.

Contrôles UI : **234 tests React réussis**, dont **79 cas Livrables**, puis **37
tests ciblés** après ajout des noms de jalons et des exclusions à l'aperçu.
Les 13 cas de sélection couvrent entrées/empreinte capturées, retrait d'aperçu,
blocages, version ancienne, jalon explicite, conflit/reconfirmation, lecteur,
pagination, mauvais contexte, adoption, annulation tardive et inactivité.
TypeScript/build/Ruff sont conformes. Le premier échec de suite complète provenait
d'un clic de test avant la fin de lecture de la version ; l'attente explicite du
bouton disponible conserve les assertions et délais. La compilation a ensuite
signalé une fixture d'identité incomplète, remplacée par tous les champs requis.

La recette fictive sur 18234 contient 27 types, dont deux publications de notice.
Elle confirme seconde page du catalogue, choix de V1 alors que V2 est publiée,
blocage sans correspondances, choix PDR et exclusion CDR, adoption de la fiche
client avec actualisation immédiate. Sa préparation et son fichier exact restent
présents ; deux contrôles du catalogue sont ajoutés sans visa. Un aperçu V2
avertit que V1 reste utilisée. Un vrai changement concurrent 5→6 refuse l'ancienne
application, conserve les choix et retire la confirmation. Désélection 7 et
resélection 8 gardent une seule fiche, un fichier vérifié, trois contrôles, la
préparation et le commentaire du collègue. Fichier et manifeste gardent leurs
empreintes. À 390/650/1280 pixels, le document ne déborde pas horizontalement.
Le navigateur est fermé, sa taille rétablie et le serveur fictif arrêté.

Lors de cette qualification, la suite Python complète confirmait **702 tests
réussis, un ignoré** et les empreintes du backend correspondaient au candidat enregistré. Le relevé
`.ui-preview/xpilot-l3/ui-selection-result.json` consolide cette qualification.
À cette étape historique, restaient : catalogue structuré dans Réglages et
composition des typologies, liens des gates jalons, recette complète incluant
sauvegarde effective des téléchargements, puis L3.6 fusion/activation. L3.5
reste en cours ; le périmètre opérationnel intégral L4–L9 est conservé. Le serveur
unique Agent sur 8001 reste actif L2 ; XPilot 8000 n'est pas modifié.

## Catalogue structuré et composition des typologies — 6 octobre 2026

Le volet actif `WorkspaceShell` ajoute Réglages → Livrables, chargé seulement
à son premier affichage. Les deux sous-rubriques gardent leurs brouillons entre
les ouvertures. Catalogue/recherche/inactifs sont paginés côté serveur ; les
publications conservées sont consultables par ID exact, y compris une ancienne.
La création part d'un formulaire vide ou d'une proposition choisie explicitement
parmi les définitions standard ; aucun peuplement implicite du catalogue.

L'éditeur structuré expose catégorie, bureau d'études, ordre et dix contrôles par
page : code stable unique, intitulé, code du jalon, activité, visa obligatoire,
transverse, contribution et conditions de typologie. Il valide les bornes serveur
(250 contrôles, 100 conditions uniques par contrôle). Les conditions inconnues
restent conservées. Le sélecteur lit les noms et `condition_code` autoritatifs sur
GET `/api/v1/deliverable-types/condition-typologies`, avec portée du lecteur et
pagination ; accents et casefold Unicode ne sont pas recalculés côté navigateur.
Cette lecture ne modifie ni schéma ni événements de référentiel.

Une publication crée une nouvelle version depuis la définition choisie et une
révision capturée. Les libellés et états actif/archivé se modifient séparément ;
archiver puis réactiver conserve toutes les publications et données des projets.
Les commandes exigent les droits du propriétaire global et une confirmation
humaine. Toute saisie différente, comparaison ou erreur retire la confirmation.
Après conflit, relecture explicite des droits/révision puis préparation sur cette
révision conserve la définition du brouillon. Les métadonnées ne transmettent
que les champs changés, en conservant les autres changements d'un collègue.

La composition charge une typologie nommée et ses types retenus (dix par page),
puis un catalogue paginé de 25 choix. Un type archivé déjà lié peut être conservé,
sans ajout nouveau. Retirer un type conserve son lien historique et les projets.
La comparaison montre composition actuelle, ajouts et retraits propres ; sa
préparation applique ces différences à la nouvelle composition, conserve les
changements indépendants et exige une nouvelle confirmation. La limite reste
100 types. Une typologie archivée et un lecteur restent en consultation.
Modifier le catalogue ou sa composition ne sélectionne aucun livrable de projet.

Les lectures annulables ne remplacent pas un formulaire après inactivité ; les
commandes attendent leur résultat. Fermeture/navigation sont verrouillées pendant
l'opération, et abandonner un brouillon modifié demande confirmation locale.
La recette fictive confirme création V1, condition `machine`, vraie collision
1→2 puis publication V2 à révision 3, archivage 4 et réactivation 5. La V1 exacte
reste identique. La composition rencontre une vraie collision 2→3, puis sa
confirmation à révision 4 conserve le retrait indépendant du collègue. Les 45
tables hors catalogue/référentiels restent identiques (24 lignes / 186 cellules),
ainsi que le fichier original, la préparation et la révision 4 du projet ; zéro FK.
Les anciens types, publications et événements sont conservés. À 390/650/1280 pixels,
le document ne déborde pas ; navigateur fermé et taille rétablie.

Qualification finale : **255 tests React**, dont **99 cas Livrables**, **704
tests Python réussis, un ignoré**, TypeScript/build/Ruff conformes. La lecture
des codes de condition est le seul ajout de service/API backend de cette étape ;
la suite complète couvre à nouveau les règles, archives et restaurations. Un
ancien test de sélection cliquait avant la fin de lecture de version : son helper
attend désormais la disponibilité effective du calcul, sans réduire les assertions.
Les empreintes actuelles sont dans `.ui-preview/xpilot-l3/ui-catalogue-result.json`.
Restent les liens des blocages de jalons, la recette intégrale avec sauvegarde
effective des téléchargements et L3.6. L3.5 reste en cours, 8001 actif L2 ; tout le
périmètre L4–L9 reste à réaliser. Aucun commit/push ni modification d'XPilot 8000.
Le contrôle final a trouvé 8001 arrêté : absence de serveur/écoute et refus de
connexion confirmés avant relance. La version L2 installée dans `C:\Agent` a été
remise en service (PID 7848, démarrage complet, santé `ok`, zéro route L3).
Le code canonique n'a pas été remplacé ; cette relance n'active pas L3.

## Visas des jalons et ouverture du contrôle exact — 6 octobre 2026

Planning → Jalons propose « Visas de livrables » dans chaque ligne et dans
l'éditeur. La lecture paginée affiche le nombre global de contrôles requis et de
blocages, puis les contrôles de la page : libellé, livrable, version/nom du fichier,
référence, responsable et vérificateur. L'option « Afficher aussi les visas
obtenus » conserve ce calcul global. Une page vide au-delà des résultats ne vaut
jamais disponibilité du jalon. Les lectures sont annulées lors d'un changement
de contexte ou d'onglet ; un échec garde la validation du workflow verrouillée
jusqu'à une lecture valide. Une autre révision impose comparaison/préparation.

GET `/api/v1/projects/{project_id}/deliverable-plan/milestones/{milestone_id}/gates/page`
accepte `include_ready`, `offset` et `limit` (1 à 200). Le service réutilise la
vérification exhaustive existante des visas et fichiers avant de paginer les
descriptions et leurs affectations. Il ne modifie ni événement ni donnée métier.
La route historique `/gates`, la garde avant transition, les archives, la migration
et leurs formats restent inchangés. Portée projet et limites sont vérifiées.

Le lien « Ouvrir le livrable et son contrôle » passe par le composant Projet actif
et ouvre l'ID de fiche exact, puis Checklist recherchée par code du contrôle,
avec son ID mis en évidence. Il ne prépare aucune commande ni aucun visa. Le
contexte rappelle jalon et version observée ; une nouvelle publication entre les
lectures est signalée. Une fiche d'un autre projet est refusée. Un brouillon
déjà ouvert peut être conservé en refusant son abandon, et une commande en cours
attend son résultat avant cette ouverture. Les brouillons des jalons restent
montés dans l'onglet masqué pendant la consultation du livrable.

La transition explicite du workflow vers Validé exige disponibilité et révision
actuelles. La date réelle seule reste indépendante et peut être renseignée sans
valider le workflow. Le backend contrôle toujours la commande finale. Valider
ouvre le prochain jalon en attente et ne renseigne aucune date réelle implicite.

La recette fictive vérifie le visa manquant nommé en V1, son ouverture exacte,
une confirmation humaine explicite (révision 6→7), le retour avec brouillon
conservé et la comparaison exigée. Le jalon sauvegardé à 8 garde la date réelle
06/10/2026 et son commentaire ; le successeur s'ouvre sans date. Une publication
indépendante V2 à 9 retire le visa, conserve préparation, preuve antérieure et
dates, puis se reflète dans les blocages. Les anciens événements, versions et
métadonnées sont conservés ; V1 garde ses octets/empreinte. Les 41 tables hors
parcours sont identiques (12 lignes / 78 cellules), zéro FK. À 390/650/1280,
aucun débordement horizontal ; les vues sont conservées dans la preuve.
La saisie automatisée DOM d'un champ date n'engageait pas sa valeur contrôlée
dans ce navigateur ; la saisie native AX a été utilisée, puis la valeur vérifiée
après navigation et dans la commande sauvegardée. Aucun changement du composant
date n'a été fait pour contourner cette limitation de recette.

Qualification : **267 tests React**, **706 tests Python réussis, un ignoré**,
TypeScript/build/Ruff conformes, **52 tests API/intégration ciblés**. Les deux
nouveaux tests backend démontrent portée, pagination/exhaustivité, noms/version
et absence d'écriture. Les tests React couvrent également lecteur, mauvaise
fiche, annulation tardive, contexte masqué, erreur/reprise et date indépendante.
Preuve courante : `.ui-preview/xpilot-l3/ui-gates-result.json`.
L3.5 reste en cours : recette complète incluant fichier effectivement enregistré
par le navigateur, puis L3.6 fusion du candidat, restauration et activation.
Le serveur 8001 reste L2 ; tout L4–L9 reste au périmètre. Aucun commit/push.

## Qualification du fichier enregistré — 6 octobre 2026

La vérification directe de Téléchargements a retrouvé les deux fichiers sauvés
par les actions de la recette Versions : `plan-reseau.txt` (33 octets) et
`manifest-v31.json` (1 225 octets). Ils correspondent exactement à la publication
V31 du projet fictif : empreintes fichier/manifeste, octets du manifeste immuable,
identifiants projet/livrable, numéro, nom et taille vérifiés en lecture seule de
la base de recette. L'outil de capture des événements de téléchargement avait
expiré ; cela ne signifiait pas un échec de l'enregistrement du navigateur.
Aucun téléchargement HTTP n'a été utilisé pour créer ces fichiers dans
Téléchargements. Ils y restent conservés ; des copies exactes sont gardées dans
`.ui-preview/xpilot-l3/verified-browser-downloads-1006`.

Le composant Versions est identique à celui de cette recette ; la suite courante
complète (267 React, 706 Python / un ignoré, TypeScript/build/Ruff) vérifie les
sources actuelles, dont le client de téléchargement. La preuve indépendante
`.ui-preview/xpilot-l3/saved-download-result.json` complète les recettes de liste,
checklist/validation, fichiers/historique, sélection, catalogue/composition et
jalons. L3.5 est qualifié dans le worktree. L3.6 prépare le candidat par rapport
aux sources canoniques actives, puis sa sauvegarde/restauration et activation.
Cette qualification ne prétend pas encore activer L3 sur le serveur 8001.

## Livraison et activation L3 — 6 octobre 2026

Le candidat a été préparé sur les sources canoniques L2, en conservant exactement
227 sources hors évolution et les corrections existantes. Ses 74 fichiers ajoutés
ou adaptés ont été qualifiés ensemble : 706 tests Python réussis / un ignoré,
267 React, Ruff, TypeScript et build. Le bundle est identique à la recette UI.
Sur une sauvegarde historique, démarrage, conservation, lecture de tous les
projets, sauvegarde/restauration et second démarrage idempotent sont vérifiés.

La bascule a arrêté uniquement le processus Agent identifié sur 8001. Code,
ancien bundle, deux bases et fichiers ont été sauvegardés dans
`C:/Agent/logs/xpilot-l3-activation-20261006-190820` ; les 1 397 fichiers du
checkpoint coordonné ont été vérifiés et restaurés sur une nouvelle copie.
La restauration conserve les identités et toutes les cellules, avec les seules
transformations portables et états de jobs interrompus documentés.

La migration additive crée neuf tables et six protections immuables. Elle garde
les 2 098 lignes ERP / 17 429 cellules et 13 144 lignes Brain / 108 134 cellules
contrôlées ; zéro FK invalide. Les anciens bundles restent disponibles. Le serveur
redémarré dans `C:\Agent` expose le schéma ERP 7 et les nouvelles routes ; santé
Brain/ERP `ok`. Les dix projets historiques, leurs listes, livrables et gates sont
lus sans créer de donnée de recette. Le catalogue reste vide et propose onze
définitions standard en lecture seule. Le navigateur confirme Planning/Livrables,
les contrôles d'un jalon historique et Réglages/Livrables, sans erreur console.

L3.1–L3.6 sont livrés et actifs. Preuve :
`.ui-preview/xpilot-l3/integration-1006-v2/delivery-result.json` ; preuve runtime
également retenue dans le dossier d'activation. Aucun commit/push, aucun import
implicite d'XPilot, aucun changement sur son port 8000. L'objectif reste actif
pour l'intégralité de L4–L9, à commencer par cockpit et RLP.

## Ouverture depuis une revue publiée (préparation L4)

La publication RLP peut ouvrir une fiche de livrable avec le contexte `review`.
Après restauration, l’identifiant courant vient de la correspondance ERP ; le
titre affiché dans la revue reste celui de sa publication. La fiche s’ouvre dans
« Fiche », indique son origine et présente l’état actuel. Elle n’interprète pas
la capture comme un visa de jalon et n’affiche pas d’alerte de version observée
pour ce contexte. Le parcours depuis un jalon garde ses contrôles et alertes.
Les champs de la fiche restent désactivés pour le lecteur.

Ce raccordement est testé dans le worktree avec les nouveaux parcours RLP sur
copie fictive, notamment au clavier et à 390 pixels. Il ne modifie pas les
versions, statuts, preuves ou règles L3 déjà actifs sur 8001. Qualification des
liens dans `docs/33_XPILOT_COCKPIT_REVIEWS.md` ; activation L4 à réaliser.

Raccordement L4.5 qualifié dans le worktree : **874 tests Python / 1 ignoré, 22 cas ciblés et 298 React**, Ruff, TypeScript et build conformes. Le serveur unique enregistre cockpit/RLP et installe le schéma ERP v8 avec préflight et sauvegarde commune. Un groupe de tables de revue partiel contenant des données est refusé avant toute DDL. Le démarrage à froid sur les dix projets historiques conserve toutes les cellules ; le second lancement est neutre et le retour à la sauvegarde est qualifié sur copie. La recette globale native/restaurée couvre PDF figé, audio WAV décodable, droits lecteur, clavier, mobile et concurrence avec conservation de saisie. Les lectures gardent les deux bases exactes ; les seules quatre cellules préexistantes modifiées pendant les commandes de recette appartiennent au brouillon fictif et à sa révision projet. Preuve : `.ui-preview/xpilot-l4/review-registration-result.json`. La précision de reconnaissance vocale n’est pas évaluée par cette recette fictive. L4.6 et L5–L9 restent à réaliser ; L0–L3 seuls actifs sur 8001. Aucun commit/push ni suppression.

**Livraison L4 — 6 octobre 2026 : cockpit et revue de lancement actifs sur Agent 8001.** Les dix projets historiques sont accessibles, les routes cockpit/RLP sont enregistrées et le schéma ERP est en version 8. L’activation conserve toutes les cellules contrôlées (ERP : 2 145 lignes / 17 759 cellules ; Brain : 13 144 lignes / 108 134 cellules), après sauvegarde coordonnée de 1 397 fichiers et restauration vérifiée sur une nouvelle copie. Les 57 chemins intégrés préservent 276 sources canoniques ; les sources du candidat correspondent aux sources qualifiées par 874 tests Python / 1 ignoré et 298 React, Ruff/TypeScript/build conformes. La navigation réelle confirme le cockpit et la création de revue disponible, sans données de test en production. ReportLab 4.5.1, déjà verrouillé dans les dépendances, est installé seul avec contrôle des empreintes dans le Python du serveur. Preuve : `.ui-preview/xpilot-l4/integration-1006-l4-v2/delivery-result.json`. L’objectif reste actif : L5–L9 sont à réaliser. XPilot/8000, les modules hérités et les données sont conservés ; aucun commit/push.
