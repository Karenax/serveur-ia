# L1 — Identité projet, référentiels et équipe

État au **5 octobre 2026** : **L1 livré et activé dans C:\Agent sur 8001**.
Références : [plan](28_XPILOT_PROJECT_PLAN.md),
[contrats L0](29_XPILOT_FOUNDATION.md), [suivi](29_XPILOT_EXECUTION.json).

Ces modules sont actifs : routeur enregistré dans Agent, migration additive
sauvegardée au démarrage ERP et écrans fiche/équipe/référentiels. Les tests et
la recette navigateur précèdent leur activation. Les données de recette sont
isolées sur `8011`, sans workers ; aucun projet fictif n'est créé en production.
Le serveur de lancement reste `C:\Agent`, sur `8001`. La remise en service de
la refonte claire dans cette copie a été coordonnée avec l'autre chat ; elle
conserve les corrections de classement multicritère. Ne pas la remplacer par
une copie brute du worktree lors de l'activation de L1.

## Modèle additif

`backend/app/project_identity_models.py` définit six nouvelles tables :

| Table | Contenu et conservation |
|---|---|
| `project_profiles` | Extension à clé `project_id` : aucun remplacement du projet existant |
| `project_references` | Clients, agences, BU, familles, typologies ; UUID et code stable par type |
| `project_people` | Prénom, nom, email, trigramme, fonction, service, téléphone, agence |
| `project_members` | Projet, personne, rôle, dates et archivage de l'affectation |
| `project_identity_changes` | Historique des fiches et affectations, acteur serveur et révision |
| `project_reference_changes` | Historique des référentiels et personnes |

Le profil porte la description, référence/site/contact client, numéro
d'outillage, quantité, début, échéance prévue, standby et responsable.
La clôture réelle est distincte et reste inaccessible aux PATCH ordinaires ;
son workflow sera livré avec L9. Les cinq états hérités ne sont pas réécrits.
`client_name` reste la valeur historique du projet et ne devient pas une
fusion implicite avec un client de même nom. Les UUID ERP et liens Brain,
les colonnes financières historiques et toutes leurs valeurs sont conservés.

Une lecture d'un ancien projet renvoie une fiche neutre de révision 0 sans
créer de profil. La première commande validée crée l'extension. Les écritures
suivantes nécessitent `expected_revision` ; un conflit renvoie 409 sans
écraser une autre édition. Le verrou d'écriture SQLite est acquis avant de
rafraîchir l'état et de valider les dates fusionnées, y compris si un service
utilise une session ayant déjà lu une ancienne version.

## Règles métier

- Fin antérieure au début refusée ; dates ISO réelles, absence représentée par
  `""`. `null` explicite est permis pour retirer une relation ou la quantité,
  pas pour un champ texte, une date ou un booléen.
- Référence de type incompatible, inexistante ou archivée refusée lors d'une
  nouvelle affectation. Une référence historique archivée reste lisible et
  n'empêche pas la correction d'autres champs.
- Code de référentiel stable : édition du libellé et activation/archivage.
  Un code archivé reste réservé. Recherche insensible à la casse/aux accents,
  caractères `%` et `_` traités comme du texte, pagination de 50 à 200 maximum.
- Les noms identiques ne fusionnent pas deux personnes. Email et trigramme
  non vides sont uniques sans distinction de casse ; identifiants vides permis.
- Dix rôles XPilot : responsable projet, pilote étude, concepteurs 3D/2D,
  vérificateur BE, qualité, calcul, chargé de fabrication, collaborateur et
  lecteur projet. Une personne peut occuper plusieurs rôles, sans doublon
  d'affectation active pour un même rôle.
- Un seul responsable actif par projet. Son changement depuis la fiche
  archive l'ancienne affectation, enregistre son historique et crée la
  suivante. Les commandes d'équipe synchronisent également le responsable.
- Archivage d'une affectation, d'une personne ou d'un référentiel : aucune
  suppression de ligne. Une personne inactive ne reçoit pas de nouveau rôle ;
  les dates d'une affectation historique restent corrigeables.
- Un identifiant de membre ne peut être utilisé dans un autre projet.

## Droits HTTP et internes qualifiés et activés

`backend/app/services/project_operator.py` sépare le rôle métier du contexte
de confiance du serveur. Par défaut : opérateur local propriétaire, compatible
avec la session locale existante. Un rôle dans l'équipe, un en-tête HTTP ou un
champ JSON ne peut changer ses droits.

Le socle lit `AGENT_OPERATOR_ID`, `AGENT_OPERATOR_ROLE` (`owner`, `editor`,
`reader`) et éventuellement `AGENT_OPERATOR_PROJECT_IDS` (liste JSON ; `[]`
désigne une portée vide). Les références globales sont administrables par un
propriétaire sans portée restreinte. Les services L1 refusent les écritures
d'un lecteur ; pour une portée restreinte, ils ne montrent que les projets,
personnes et références effectivement liés à cette portée. Le contexte interne
utilise un `ContextVar` et se réinitialise après utilisation.

`app/services/project_access.py` applique la même politique dans le middleware
HTTP et `local_dispatch`. Les protections Host/Origin et le jeton local restent
préalables ; le contexte est figé pendant la requête puis réinitialisé.
La session expose les capacités de l'opérateur sans accepter de rôle client.

| Opérateur | Consultation | Modification | Administration globale |
|---|---|---|---|
| Propriétaire sans portée | Tous les projets | Oui | Oui |
| Éditeur | Projets autorisés | Fonctions métier autorisées | Non |
| Lecteur | Projets autorisés | Non | Non |

Une portée restreinte utilise les UUID ERP et leurs liaisons Brain explicites,
jamais une ressemblance de code. Listes, recherches, compteurs, réunions, jobs,
connaissance, propositions et contexte LLM sont filtrés. Une source étrangère
ne devient pas visible via une proposition placée dans un projet autorisé.
Si deux projets ERP partagent un Brain autorisé, les jalons et libellés ERP du
projet hors portée restent masqués. Les fonctions globales sans filtrage sûr
sont refusées à une portée restreinte ; une portée vide n'élargit aucun accès.
Imports d'archives et modifications des liaisons Brain sont réservés au
propriétaire sans portée, comme l'administration des référentiels.

Les POST de consultation (`memory/recall`, chat et chat en flux) restent
accessibles au lecteur selon sa portée ; ils n'autorisent pas une écriture.
Le dispatch interne ne contourne pas les contrôles ; la configuration privée
du moteur CDC continue à être lue par son service serveur de confiance.
Les workers sont des traitements serveur : le rôle lecteur ne suspend pas
automatiquement une indexation déjà configurée. Les rôles métier dans l'équipe
n'authentifient personne. Ce dispositif n'ajoute pas de comptes ni
d'authentification multi-utilisateur et ne copie pas celle d'XPilot.

Qualification : **36 cas ciblés**, incluant chaque route ERP/Brain de mutation
enregistrée, appels internes, rôle forgé, portée vide, requêtes hors portée,
listes/compteurs, sources étrangères et contexte LLM partagé. Les résultats de
la suite complète sont consignés dans le suivi JSON. Ce code est qualifié dans
le worktree, **pas encore activé dans `C:\Agent`**.

## Contrats API raccordés dans le worktree

Le routeur `backend/app/routers/project_identity.py` est testé isolément et
enregistré dans `app/main.py`. Un parcours HTTP utilise cette application réelle
avec une dépendance ERP temporaire : création de références/personnes, fiche,
responsable, modification de membre, historique et portée lecteur. Ces chemins
ne sont pas encore disponibles dans la copie de lancement `C:\Agent`.

| Méthode et chemin, sous `/api/v1` | Fonction |
|---|---|
| `GET/POST /project-references` | Recherche paginée / création |
| `PATCH /project-references/{id}` | Libellé, activation et révision attendue |
| `GET/POST /project-people` | Recherche paginée / création |
| `PATCH /project-people/{id}` | Fiche personne et révision attendue |
| `GET/PATCH /projects/{id}/identity` | Identité, équipe, références / édition |
| `GET /projects/{id}/identity/history` | Historique paginé |
| `POST /projects/{id}/members` | Affectation à un rôle |
| `PATCH /projects/{id}/members/{member_id}` | Rôle et dates |
| `POST /projects/{id}/members/{member_id}/archive` | Archivage sans suppression |

Les commandes HTTP prennent en charge commit/rollback. Les appels directs aux
services utilisent une transaction explicite : commit après succès, rollback
sur exception. Les acteurs d'historique proviennent du serveur, jamais du corps
envoyé par l'utilisateur.

## Migration qualifiée sur copies

`backend/app/services/project_identity_migration.py` fournit
`install_identity_schema(engine, backup=...)`. Il exige une base ERP existante,
refuse les tables d'identité incomplètes ou privées de contraintes attendues,
appelle la sauvegarde fournie **avant** toute création et reste idempotent.
Il n'exécute aucun ALTER, UPDATE ou DELETE sur les tables historiques.

Le démarrage ERP appelle désormais cette installation avant `create_all` sur
une base existante. Un schéma L1 incomplet est refusé avant les autres DDL.
La sauvegarde cohérente est exigée avant création et mutualisée avec les
migrations historiques du démarrage ; elle n'est pas répétée si le schéma est
déjà conforme. Une base neuve reçoit les six tables à sa création.

La répétition locale `.ui-preview/xpilot-l1/rehearse.py` a travaillé uniquement
sur les copies ERP/Brain sauvegardées le 5 octobre. Six tables ERP ajoutées,
aucune table Brain ajoutée. Conservation vérifiée par les empreintes L0 :
**449 lignes / 5 788 cellules ERP**, **9 859 lignes / 78 625 cellules Brain**,
soit **10 308 lignes / 84 413 cellules**, sans perte ni changement. Ré-exécution
sans modification, clés étrangères valides, récupération dans de nouveaux
fichiers depuis les copies précédentes vérifiée. Rapport :
`.ui-preview/xpilot-l1/rehearsal-final/result.json`, preuve locale ignorée par Git.

Les tests couvrent les règles ci-dessus, conflits entre deux transactions,
cache de session périmé, rollback, lecture sans écriture, refus d'un acteur
forgé, pagination, absence de sauvegarde et contraintes de schéma manquantes.
Qualification : **28 cas ciblés**, suite complète **214 tests réussis,
1 ignoré**, Ruff conforme. Résultats actualisés dans le suivi JSON.
Aucun changement de production,
redémarrage, nouveau service, commit ou push n'est effectué par ce socle L1.

## Archives v3 sélectives, préparées et qualifiées

`backend/app/services/project_identity_archive.py` étend le service existant
`project_archive.py`. Un projet sans extension d'identité continue à être
exporté et importé en **version 2**, y compris sur une base sans schéma L1.
Un projet doté d'une fiche, d'une équipe ou de leur historique est exporté en
**version 3**. Cette version exige une migration L1 complète dans la base cible ;
un import sur l'ancien schéma est refusé clairement avant toute insertion.

La partie `tables` reste limitée aux données du projet. Le nouveau bloc
`references` contient seulement `project_references` et `project_people` :
clients/agences/BU/familles/typologies et personnes utilisés par la fiche,
les affectations conservées, leurs historiques et les agences de ces personnes.
Une ancienne référence remplacée reste exportée si l'historique la cite.
Une référence étrangère au projet, une personne manquante ou une table globale
injectée dans `tables` sont refusées. L'historique global des référentiels
(`project_reference_changes`) reste dans la sauvegarde globale : il n'est pas
copié dans une archive projet. Les historiques de fiche et d'équipe sont
intégralement conservés et leurs relations remappées.

À l'import, les UUID métier sont remappés sans modifier les descriptions,
références client et autres textes qui pourraient ressembler à un UUID.
Dates, responsable/membre, acteurs, révisions, identifiants et index de recherche
sont validés avant insertion. Le code projet est vérifié sans distinction de
casse ; le contrôle et la réconciliation des références sont sérialisés avec
les autres écritures SQLite, sans changer une cellule existante.

Une référence est réutilisée lorsque son UUID ou son code stable identifie
une ligne dont les données métier concordent. Une personne peut être reconnue
par son UUID, son email ou son trigramme ; un nom identique seul ne suffit pas.
Révision et date de création de la ligne existante sont conservées. Une
différence ou deux identifiants désignant des personnes distinctes renvoient
**409**, avec la table et les identifiants concernés : aucun écrasement,
fusion implicite ou changement de référentiel n'est effectué. Il faut résoudre
ce conflit explicitement avant de réimporter ; cette étape ne fournit pas
encore de formulaire de résolution.

Toutes les pièces sont décodées et vérifiées avant leur copie : empreinte,
propriétaire, zone (`cdc`, `raw`, `delivery`), doublons et présence des fichiers
CDC/livrables exigés. Une archive incomplète ne laisse pas de première pièce
copiée. Les fichiers CDC restaurés sont placés sous le nouvel UUID de projet.
Le dictionnaire d'archive fourni par l'appelant n'est pas modifié.

Qualification des archives : **38 cas ciblés**, dont deux bases distinctes,
réutilisation locale, homonymes, conflits, historiques étrangers, pièces
manquantes/corrompues, ancien schéma et relecture d'un export restauré.
La suite complète vérifie aussi les pièces CDC, versions de livrables, workflow
audio et la sauvegarde/restauration existants : **252 tests réussis, 1 ignoré**,
Ruff conforme.

Une recette complémentaire utilise les copies ERP/Brain de la remise en service
(`C:\Agent\logs\interface-restore-20261005-153424\databases`), sans ouvrir les
bases actives. Elle installe les tables L1 sur une copie, ajoute un projet fictif,
puis exporte et restaure sa fiche/équipe/historique dans une autre base isolée.
Les empreintes des données antérieures restent identiques : **683 lignes /
7 532 cellules ERP** et **10 865 lignes / 87 711 cellules Brain**, soit
**11 548 lignes / 95 243 cellules** conservées ; zéro violation de clé étrangère.
Ce projet fictif n'a pas de pièces externes ; leur portabilité est couverte par
les tests isolés précédents. La première tentative sur une sauvegarde plus
ancienne était antérieure aux tables de jalons ; cette recette a été reprise
sur les copies récentes, sans modification du schéma du serveur actif.
Preuve locale : `.ui-preview/xpilot-l1/archive-rehearsal-final/result.json`.
Résultats courants dans le suivi.
Cette modification n'est pas encore déployée dans `C:\Agent`.

## Écrans et raccordement qualifiés dans le worktree

`ProjectIdentityPanel` complète la Vue d'ensemble par **Fiche**, **Équipe** et
**Historique**. La fiche présente les cinq référentiels, responsable,
description, référence/site/contact client, outillage, quantité, dates et
standby. Client historique et offre restent visibles sans fusion ni chiffrage.
Seuls les champs modifiés sont envoyés avec la révision chargée. Le changement
de responsable synchronise l'équipe via le service existant.

L'équipe permet l'ajout, l'édition de rôle/dates et l'archivage d'affectations ;
les affectations archivées se consultent explicitement. L'historique paginé
présente les différences, date et acteur serveur. Les rôles métier sont
distincts des droits d'accès.

**Réglages → Référentiels** permet la recherche paginée, création, modification,
archivage et réactivation de clients/agences/BU/familles/typologies/personnes.
Le code d'un référentiel reste stable. Les commandes d'administration sont
présentées selon les capacités retournées par la session serveur.
Les sélecteurs interrogent des pages de 50 avec recherche ; un choix historique
archivé reste visible. Ils ne téléchargent pas un annuaire complet.

Les brouillons survivent à un conflit et aux changements de réglage. Les
affectations et fiches en cours d'édition ne se remplacent pas entre elles.
Les réponses tardives d'un autre projet sont ignorées. Les écritures réussies
actualisent la fiche et appellent le rechargement projet/portefeuille existant.
Création manuelle et dossier réseau restent leurs parcours existants.

Qualification de la fusion finale : **332 tests Python réussis, 1 ignoré**,
**114 tests React réussis**, Ruff, TypeScript et build
conformes. Ces tests couvrent erreurs/conflits, consultation lecteur,
ajout/édition/archivage, pagination, révisions et navigation Réglages.
La recette navigateur vérifie également le parcours réel sur bases isolées.

Le démarrage intégré a été répété deux fois sur de nouvelles copies du couple
ERP/Brain sauvegardé, sans workers : **683 lignes / 7 532 cellules ERP** et
**10 865 lignes / 87 711 cellules Brain** conservées, sauvegarde avant migration
vérifiée, zéro violation de clé étrangère. La première recette avait terminé
la vérification des données mais son contrôle de route utilisait une propriété
absente du routeur différé FastAPI ; elle a été reprise dans de nouvelles copies
en vérifiant le contrat OpenAPI. Preuve finale :
`.ui-preview/xpilot-l1/startup-rehearsal-final-1005/result.json`.

## Livraison et recette L1

La recette du 5 octobre couvre client/responsable/description/dates, ajout d'un
second rôle et archivage sans retirer le responsable, historique, création d'un
référentiel et conservation du brouillon entre réglages. Création manuelle et
import réseau apparaissent immédiatement dans les sélecteurs. Le dossier
`AIRB26LTH0205-A - LED 2026` conserve la priorité sur un ancien TDAO contenant
`AIRB23LTH3146-A` ; ses heures étrangères ne sont pas reprises.

Le sélecteur de l'assistant affiche désormais les projets ERP actuels. Une
sélection explicite d'un projet sans liaison appelle le service de liaison ;
aucune association n'est créée lors du rendu ou déduite du code affiché. Une
erreur bloque l'envoi et propose une reprise, sans envoyer au contexte global.
Quatre cas React couvrent actualisation, liaison explicite, erreur et UUID.
Sur une largeur de 390 pixels, la fiche reste dans une colonne sans débordement.

La fusion préserve les corrections mails du serveur canonique. Sauvegarde :
`C:\Agent\logs\xpilot-l1-activation-20261005-174402` (code, anciens bundles,
ERP et Brain avant migration). Les six tables ajoutées conservent exactement
**1 133 lignes / 10 682 cellules ERP** et **11 866 lignes / 97 103 cellules
Brain**, zéro violation de clé étrangère. Les dix UUID projet ERP historiques
sont conservés. Les routes L1, le contexte d'opérateur et les nouveaux bundles
sont vérifiés sur `8001` ; la fiche d'un projet existant est contrôlée en lecture
seule dans le navigateur. Les recherches de jalons interrompues par le
redémarrage sont remises en file par le worker existant, sans perte des entrées.

Preuves : `activation.json` et `runtime-verification.json` dans la sauvegarde,
`.ui-preview/xpilot-l1/activated-identity-1005.png` pour la fiche active.
L1 est terminé ; la reprise complète L0–L9 reste un objectif actif.

Le checkpoint global complémentaire `full-state-after-l1`, effectué hors ligne
après activation avec le service de sauvegarde existant, comprend **1 388
fichiers** contrôlés par SHA-256. Sa restauration dans un dossier neuf conserve
**1 164 lignes / 10 895 cellules ERP** et **11 926 lignes / 97 623 cellules Brain**.
Les 2 643 transformations attendues de chemins et d'états de jobs sont vérifiées
cellule par cellule ; aucune autre différence, aucune violation FK et aucun
worker lancé dans la copie. Cette restauration ne touche pas la production.
Preuve : `.ui-preview/xpilot-l1/global-restore-result-1005.json`. Le serveur est
relancé sur `8001` après ce checkpoint et ses deux bases répondent `ok`.
## Collaborateurs depuis les mails eXcent — 7 octobre 2026

Après classement d’un mail dans une affaire active, les personnes identifiées en expéditeur/À/Copie avec une adresse `@excent.fr` rejoignent l’équipe comme collaborateurs. L’adresse normalisée dédoublonne l’annuaire. Les noms, rôles, responsables et archivages humains restent conservés. Les affectations ajoutées sont tracées dans l’historique avec le mail d’origine ; elles n’attribuent aucun droit d’accès système. Voir `docs/18_MAIL_TRIAGE.md` pour l’indice de classement et la reprise des mails existants.
