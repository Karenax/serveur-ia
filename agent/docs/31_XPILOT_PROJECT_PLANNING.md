# L2 — Jalons, tâches, modèles et références de planning

Le précontrôle de schéma accepte aussi une connexion déjà possédée par la
transaction d'archive v6 : il la lit sans la fermer ni installer de tables.
Le garde de migration exige toujours une sauvegarde avant toute DDL. Cette
extension prépare la restauration coordonnée L4 décrite dans le document 33 ;
elle ne modifie ni les règles de planning ni les archives v4 existantes.

État au **5 octobre 2026** : **L2 livré et actif sur Agent 8001, migration/restauration qualifiées, 459 tests Python / 155 React ; objectif actif pour L3–L9**.
Le serveur `C:\Agent:8001` utilise L1 et conserve son planning existant.
Références : [plan](28_XPILOT_PROJECT_PLAN.md), [contrats L0](29_XPILOT_FOUNDATION.md),
[suivi](29_XPILOT_EXECUTION.json), [jalons et preuves actuels](26_PROJECT_MILESTONES.md).

## Règles préparées

`backend/app/services/project_planning_rules.py` prépare les contrats sans
importer une base, enregistrer de route ou écrire dans un projet. Référence
locale vérifiée : `XPilot/backend/app/domain/project_workflow.py` et
`domain/work_calendar.py`. Il s'agit de fonctions métier adaptées à Agent ;
aucun accès runtime à XPilot n'est ajouté.

Le modèle standard conserve les 14 codes stables :

| Code | Jalon |
|---|---|
| `reception` | Réception |
| `remise_offre` | Remise offre |
| `recp_commande` | Réception commande |
| `rlp` | RLP |
| `kom` | KOM |
| `pdr` | PDR |
| `cdr` | CDR |
| `fdr` | FDR |
| `go_fabrication` | Go fabrication |
| `reception_ciss` | Réception CISS |
| `livraison` | Livraison |
| `mise_en_service` | Mise en service |
| `validation_client` | Validation client |
| `cloture` | Clôture |

Le jalon Remise offre représente une étape du cycle de vie ; il ne réintroduit
aucun prix, taux, calcul financier ni écran de vente.

Un modèle contient des jalons et des tâches aux clés uniques. Les rattachements
à un jalon et les parents doivent appartenir au modèle. Cycles, clés absentes,
charges non finies/négatives et fin antérieure au début sont refusés. Une tâche
parente ne possède pas de charge ou de dates saisies indépendantes de ses enfants.

La prévisualisation calcule les dates **prévisionnelles** à partir du début et
des décalages explicites, en jours du lundi au vendredi hors dates exclues.
Aucun jour férié n'est supposé. Un décalage nul conserve la date de départ,
y compris un week-end ; un décalage absent reste sans date. Le modèle standard
ne contient pas de délais arbitraires. Le calcul ne remplit jamais les dates
contractuelles ou réelles et exige une future commande d'application explicite.

Charges et dates des parents sont agrégées du bas vers le haut. Une date
d'enfant absente reste visible par l'absence de date agrégée du parent ; la
charge totale ne compte pas simultanément un parent et ses enfants.

Les huit jalons historiques ne sont pas remplacés. Lancement/KOM et Livraison
font l'objet de suggestions à confirmer. Les phases de conception, FAT, SAT et
réception définitive n'ont pas d'équivalence unique établie avec le modèle :
elles restent sans mapping implicite. Les UUID, dates et preuves restent en place.

Une référence est une valeur JSON sérialisée figée avec empreinte SHA-256.
Elle conserve les UUID, trois dates, preuves et relations. Une mutation des
objets source ne la modifie pas. La capture refuse doublons et relations de
planning cassées ou étrangères ; la comparaison refuse une empreinte invalide
et des projets différents. Elle expose les ajouts, écarts et disparitions,
avec sévérité et variation de charge calculée sur les feuilles. Les valeurs
financières restent exclues de ces nouveaux artefacts.

## Schéma et commandes qualifiés sur copies

Le schéma est défini dans `backend/app/project_planning_models.py` :

| Table | Usage |
|---|---|
| `project_planning_templates` | Identité stable et typologie du modèle |
| `project_planning_template_versions` | Valeur publiée et empreinte, numérotation unique |
| `project_planning_states` | Révision du planning, calendrier explicite, modèle appliqué |
| `project_milestone_plans` | Extension du jalon existant : code, ordre, état, commentaire |
| `project_task_plans` | Extension de tâche : hiérarchie, jalon, responsable, dates et heures |
| `project_planning_baselines` | Références initiale/contractuelle/revue/avenant figées |
| `project_planning_changes` | Événements avec opérateur, révision, valeurs avant/après |

`install_planning_schema` crée seulement ces sept tables et six triggers. La
base parent doit déjà disposer de L1, des tâches et des jalons. Types, colonnes,
clés, contraintes, index et triggers existants sont vérifiés avant toute
écriture. Une sauvegarde doit réussir avant DDL. Le second appel ne sauvegarde
et ne modifie rien. Versions, références et événements ne peuvent être mis à
jour ou supprimés, même par une commande SQL ordinaire.

La répétition sur le couple sauvegardé après L1 conserve **1 164 lignes /
10 895 cellules ERP** et **11 926 lignes / 97 623 cellules Brain**. La copie
avant DDL est vérifiée ; aucune violation FK, aucun worker démarré. Preuve :
`.ui-preview/xpilot-l2/migration-rehearsal-1005/result.json`. Le restaurateur
global L1 conserve aussi son usage ; les archives projet doivent encore être
étendues aux dépendances de planning avant activation L2.

`backend/app/services/project_planning.py` ajoute des commandes internes
transactionnelles : lecture neutre, édition de jalon/tâche, capture et comparaison
de référence. Le caller commite une réussite et annule une commande en erreur.
Les lectures ne créent aucune métadonnée. Les écritures acquièrent le verrou
SQLite et comparent la révision attendue : deux commandes concurrentes sur la
même révision ont un seul gagnant, l'autre reçoit 409 sans écrasement.

La portée L1 s'applique aussi sans HTTP. Un lecteur ne peut modifier le planning ;
une tâche, un parent ou un jalon étranger est refusé. Le responsable est validé
par la visibilité des personnes L1. La date réelle reste distincte de l'état
du workflow. L'historique de dates existant reste alimenté avec l'opérateur
serveur, sans valeur d'acteur fournie par le client.

Parents : cycles et parents archivés refusés ; pas d'édition indépendante de
charge/dates pour un groupe. Ajouter un premier enfant à une tâche qui possède
déjà des dates ou heures propres est refusé, pour éviter de remplacer ces
valeurs sans décision. Les agrégats ignorent les enfants archivés tout en
conservant leurs lignes et leurs heures. Un parent avec enfants actifs ne peut
être archivé. Les références figées conservent aussi états et commentaires ;
le delta de charge utilise seulement les feuilles actives.

Le worktree raccorde désormais ces fonctions aux anciennes créations/éditions de
tâches et jalons, à l'acceptation de propositions IA et à la conversion d'action
de réunion. Une seule révision sérialise toutes ces écritures ; l'opérateur est
issu du serveur. Les anciens appels sans révision sont conservés : ils avancent
le compteur et rendent une nouvelle commande préparée auparavant périmée.
Un appel qui fournit une révision dépassée reçoit 409 et ne laisse ni écriture
partielle ni événement. L'acceptation IA conserve aussi son contrôle de source
et de valeur de date ; une décision de rejet ne modifie pas le planning.
Les imports dans un nouveau projet commencent à zéro, sans reprise implicite
du workflow. La création des huit jalons historiques reste inchangée.

Le responsable de tâche reste visible dans les personnes autorisées, y compris
à travers l'historique et une référence figée après désaffectation. Les personnes
liées seulement à un autre projet restent masquées. La consultation d'un
référentiel L1 autonome ne crée jamais les tables de planning.

### API préparée dans le worktree

Préfixe : `/api/v1/projects/{project_id}/planning`.

| Méthode / chemin | Usage |
|---|---|
| `GET /state` | Révision, droits, calendrier, modèle appliqué et codes du workflow |
| `GET /items/tasks`, `/items/milestones` | Listes filtrées et paginées, archivés sur demande |
| `GET /items/{kind}/{id}` | Détail contrôlé par projet, droits, révision et relations hors page |
| `PATCH /tasks/{id}`, `/milestones/{id}` | Commande avec `expected_revision` obligatoire |
| `GET /history`, `/history/{id}` | Résumé paginé puis détail des valeurs avant/après |
| `GET`, `POST /baselines` | Liste paginée et capture complète révisionnée |
| `GET /baselines/{id}/compare` | Écarts avec le planning complet actuel |

La pagination est effectuée par SQL, de 1 à 200 éléments, avec total ; les caractères
`%` et `_` de recherche sont traités littéralement. Une référence capture toutes
les tâches et tous les jalons autorisés, y compris archivés, jamais la page
affichée. Les accès sont vérifiés aussi par les services sans HTTP.
Le détail projet et l'échéancier existants exposent `planning_revision` ; la
revue des propositions IA l'expose également. Les réponses anciennes conservent
leurs clés usuelles et ajoutent la révision. L'alias `due_date` de jalon demeure
une prévision. L'alias de tâche édite la date de fin et recalcule les parents ; il
ne permet pas de saisir une date propre sur un groupe. Un total de groupe au-delà
de 1 000 000 heures reçoit 422 et une annulation complète, plutôt qu'une erreur SQL.

Le démarrage ERP du worktree installe le schéma avec sauvegarde préalable, valide
les contraintes et les six triggers, puis enregistre la version ERP 6. Un démarrage
ne lance aucune application automatique de modèle. La répétition du vrai démarrage
sur le couple sauvegardé L1 conserve les **13 090 lignes / 108 518 cellules**,
avec une sauvegarde avant DDL, zéro violation FK et un second démarrage sans
modification. Preuve : `.ui-preview/xpilot-l2/startup-rehearsal-1005/result.json`.
Les fixtures qui recréent la base ERP passent aussi par ce démarrage pour vérifier
les protections réelles. Le serveur actif n'a reçu ni ces routes ni cette migration.
Ne pas activer L2 avant les modèles, archives et écrans qualifiés.

## Modèles versionnés et application contrôlée

`backend/app/services/planning_templates.py` publie une nouvelle version avec
numéro unique, définition canonique et SHA-256. Les versions déjà publiées sont
immuables. La publication ne touche aucun projet. Le code du catalogue est unique,
y compris si le modèle est archivé. Son nom, sa typologie et son état disposent
de leur propre révision ; l'historique de référentiels conserve leurs modifications.
La recherche du catalogue est normalisée, littérale et paginée ; dernière version
et capacité d'administration sont exposées sans lecture de toutes les définitions.

Administration : propriétaire sans restriction seulement. Les lecteurs/éditeurs
peuvent lire les modèles génériques, ceux des typologies de leurs projets autorisés
et ceux déjà utilisés par ces projets. Un modèle lié à une typologie exige la même
classification dans la fiche du projet avant application. Un modèle archivé reste
consultable dans ses anciennes versions, mais ne peut plus être publié ou appliqué.

| Méthode / chemin | Usage dans le worktree |
|---|---|
| `GET`, `POST /api/v1/planning-templates` | Catalogue et création avec première version |
| `GET /api/v1/planning-templates/standard-definition` | Définition neutre des 14 étapes |
| `PATCH /api/v1/planning-templates/{id}` | Nom, typologie, archivage/réactivation révisionnés |
| `GET`, `POST /api/v1/planning-templates/{id}/versions` | Liste paginée et nouvelle publication |
| `GET /api/v1/planning-templates/{id}/versions/{version_id}` | Définition publiée et empreinte |
| `GET /planning/mapping-proposals` | Suggestions de correspondance sans affectation automatique |
| `POST /planning/templates/{version_id}/preview` | Aperçu complet sans écriture, accessible au lecteur autorisé |
| `POST /planning/templates/{version_id}/apply` | Application liée à l'aperçu et à la révision |

Les chemins `/planning/*` ci-dessus utilisent le préfixe projet déjà décrit.
L'aperçu indique créations/écarts, delta de charge, calendrier avant/après et
version appliquée avant/après. Il contient la révision et `preview_sha256` ;
l'application exige `expected_preview_sha256` identique. Une édition concurrente,
des paramètres changés ou un aperçu devenu différent entraînent 409 avec annulation
complète. Dates de début et exclusions explicites alimentent le calcul en jours
ouvrés ; calendrier hors plage, correspondances étrangères/dupliquées et dépassement
de charge de groupe sont rejetés avant application.

`milestone_mapping` associe explicitement un code du modèle à un UUID du projet.
Un code déjà affecté est réutilisé ; aucun rapprochement par le seul titre n'est
effectué. Les jalons restants du modèle sont ajoutés, jamais substitués aux huit
jalons existants. Dates contractuelles/réelles, titres et preuves historiques
restent en place. Les prévisions modifiées ont une provenance de modèle/version
et alimentent l'historique de dates partagé. `forecast_policy` choisit :

- `preserve` : conserver les prévisions existantes ;
- `fill_empty` : compléter seulement les prévisions vides (valeur initiale) ;
- `replace` : appliquer les nouvelles prévisions calculées, visibles dans l'aperçu.

Une prévision absente du modèle ne vide jamais une date existante. Les dates des
nouveaux objets proviennent du calcul explicite, même avec `preserve`. Une tâche
déjà issue du même modèle conserve sa clé/UUID : une nouvelle version ou application
ne la duplique pas. `update_tasks=false` conserve ses champs ; `true` permet de
réviser titre, priorité, BE/fabrication, rattachements et charge, ainsi que ses dates
selon la politique choisie. Responsable, état, commentaire et archivage sont préservés.
Tâches manuelles et tâches retirées de la définition restent présentes. Les groupes
agrègent aussi leurs enfants manuels. Transformer une ancienne feuille ayant des
dates/heures en groupe nécessite cette mise à jour explicite et affiche ses écarts.

Le schéma reste à sept tables et six protections, enrichi avant toute activation :
`PlanningTemplate.search_text` et la provenance `TaskPlan.template_id/template_key`
avec unicité par projet/modèle/clé et dépendance FK. Cette provenance figure aussi
dans les références figées et les archives portables v4 qualifiées dans le worktree.
La migration du schéma courant est requalifiée depuis la sauvegarde L1 dans
`.ui-preview/xpilot-l2/startup-template-rehearsal-1005/result.json` : mêmes
**13 090 lignes / 108 518 cellules** conservées, un backup avant DDL, aucun changement
au second démarrage, zéro FK. Les répétitions antérieures restent des preuves de
leurs états de schéma précédents, pas un point de départ à activer.

Une seconde copie vérifie l'application deux fois du modèle neutre : 14 étapes
ajoutées, UUID historiques et **13 091 lignes / 108 521 cellules** préalables conservés,
aucune duplication ni changement du projet à la publication suivante. La différence
d'une ligne est l'enregistrement du schéma ERP 6 sur cette copie. Aucun worker ni
connexion de production. Preuve :
`.ui-preview/xpilot-l2/template-application-copy-1005/result.json`.

## Workflow et tâches

Les jalons codés actifs ont au plus un jalon ouvert. Une ouverture ne valide pas
un autre jalon automatiquement ; elle est refusée si un autre reste ouvert.
Une validation ouvre le prochain jalon en attente dans l'ordre, en ignorant les
étapes explicitement sautées/archivées. Un jalon bloqué empêche cet avancement ;
un jalon déjà ouvert reste en place lorsqu'une validation antérieure est enregistrée.
Une deuxième validation du même jalon ne fait pas avancer à nouveau le cycle.
Les deux modifications sont enregistrées dans la même révision/historique complet.
La date réelle reste indépendante : aucune date du jour ni confirmation d'une
réalisation n'est inventée par le changement d'état. Les jalons sans code ne sont
pas entraînés implicitement dans le cycle du modèle.

`POST /planning/tasks` crée atomiquement titre, hiérarchie, jalon, responsable,
priorité, dates, charge et flags BE/fabrication. Une erreur ne laisse ni tâche
incomplète ni révision supplémentaire. Les états XPilot sont `todo`, `assigned`,
`in_progress`, `blocked`, `done`, `cancelled` ; `assigned` exige un responsable.
Les anciennes éditions de tâche acceptent aussi ces états et restent révisionnées.

## Travail suivant

L2.1–L2.6 sont livrés et actifs. La suite est L3 : catalogue de livrables par
typologie, rattachement aux jalons, checklists/gates, avancement, versions et
fichiers immuables, en conservant les livraisons CDC existantes. Le suivi des
étapes de qualification ci-dessous est historique ; la livraison finale figure
à la fin du document.

Les contrôles d'opérateur L1 sont appelés par les services transactionnels.
Les fonctions pures n'authentifient pas un utilisateur.
Les participants métier et responsables de tâches ne confèrent aucun droit.

## Qualification

Les tests de `tests/test_project_planning_rules.py` portent sur absence de
mutation du planning historique, ambiguïtés de mapping, calendrier explicite,
hiérarchie, charge sans double comptage, dates manquantes, intégrité et
conservation des références : **24 cas réussis**. Les schémas et commandes ajoutent
**30 cas** de sauvegarde, contraintes, immutabilité, concurrence, périmètre,
routes paginées, révisions croisées, acceptation IA, conversion de réunion et
conservation du responsable dans les références/historiques et création atomique.
Les modèles ajoutent **20 cas** de publication, aperçu, application, préservation,
typologie, contrôle d'accès, workflow et erreurs explicites : **74 cas** de socle/modèles et **30 cas** d’archives : **104 cas L2** au total.
La suite complète réussit **436 tests Python, 1 ignoré** ; Ruff est conforme. Les preuves de
démarrage sont tenues dans le suivi 29. Les routes et le démarrage sont raccordés
dans le worktree ; Jalons/Tâches/Références/Historique sont qualifiés sur écran de bureau ;
complément des instantanés projet, Modèles UI et activation restent à livrer.

## Archives portables v4

Le format `agent-project-archive` v4 ajoute `planning_references`, contenant
uniquement les modèles utilisés par l'état, les tâches, preuves, références
figées ou historiques du projet, avec toutes leurs versions publiées. Les
typologies associées et personnes utilisées seulement dans un ancien instantané
sont incluses dans `references`. Aucun catalogue global n'est importé. Les projets
sans planning enrichi restent en v2/v3 ; une rétrogradation contenant des données
L2 est refusée. La migration explicite L2 est exigée avant import/export v4 :
l'archive ne crée pas un schéma incomplet implicitement.

L'import attribue de nouveaux UUID aux objets projet. Les référentiels/personnes,
modèles et versions de même identité métier sont réutilisés seulement si leurs
champs métier correspondent ; un conflit refuse l'import sans écraser l'existant.
Les UUID ERP et Brain sont remappés séparément, même s'ils étaient identiques.
Parent, jalon, responsable, provenance de modèle, action/réunion et preuves
source/artefact/page sont remappés selon leur type. Les textes, citations, acteurs,
clés de modèles et définitions publiées restent identiques. Les charges agrégées,
cycles, appartenance au projet, révisions, calendriers et empreintes sont vérifiés.
Les métadonnées JSON opaques du Brain sont conservées : elles ne sont pas
interprétées comme des relations métier ; les pointeurs relationnels déclarés sont
remappés. Les anciens JSON ERP hors planning gardent leur traitement existant.

Chaque référence figée est relue et son empreinte contrôlée avant import, puis
réencodée avec les nouveaux identifiants et une nouvelle empreinte. L'événement
historique de capture pointe vers cette référence et sa nouvelle empreinte ;
la comparaison reste identique sur le fond. L'archive source conserve l'empreinte
d'origine. Le jeton d'aperçu d'une ancienne application reste une trace historique,
pas une autorisation d'application dans le projet restauré.

Un Brain canonique déjà présent est réutilisé ; les preuves citées et sources
audio doivent encore y exister avec leur contenu/association d'origine. Une liaison
Brain absente ou invalide est refusée plutôt que réparée implicitement. Les chemins
réseau restent des références externes, pas des fichiers embarqués. Les pièces
CDC/livrables et les originaux Brain trouvés dans le stockage géré gardent les
contrôles existants (propriétaire, empreinte, taille), avec chemins portables. Les
enregistrements audio conservent leurs relations et textes ; leurs binaires ne
sont pas ajoutés à ce format, et relèvent de la sauvegarde globale.

Les jobs importés sont interrompus ou remis à relire selon les règles existantes ;
aucun worker n'est lancé par cette recette. Les transactions ERP et Brain restent
distinctes : une sauvegarde globale hors ligne est le recours en cas de panne entre
les deux commits. Cette archive projet ne remplace pas la sauvegarde globale.

`tests/test_project_planning_archive.py` ajoute 25 cas : clôture des dépendances
historiques, arbre/charges, rehashage et comparaison, immutabilité, rapprochement
des UUID, versions conflictuelles, données malformées, namespace ERP/Brain, preuves
canoniques et pièces CDC/livrables. La recette
`.ui-preview/xpilot-l2/archive-application-final-copy-1005/result.json` prépare un
projet fictif connecté dans une copie de la paire déjà sauvegardée, puis vérifie
**13 170 lignes / 109 127 cellules** préalables à l'import, zéro FK et comparaison
identique. Les empreintes des deux fichiers source restent identiques. Les données
et le serveur de production ne sont pas modifiés ; L2 n'est pas encore activé.

## Écrans Jalons et Tâches — recette bureau

Dans Planning, les listes se chargent par pages de 25 avec recherche serveur et
option d’inclure les éléments archivés. Les pickers chargent leurs options par
pages de 50 et conservent une sélection hors page. Le détail scoped
`GET /planning/items/{tasks|milestones}/{id}` fournit les relations, la révision
et les droits ; aucun planning global n’est téléchargé pour éditer une ligne.

Jalons expose les trois dates, l’écart à l’engagement, code, position, workflow,
commentaire, archivage et preuves. Les propositions IA et l’historique des dates
restent accessibles. Valider le workflow n’invente aucune date réelle.
Tâches expose les six états, parent, responsable, jalon, priorité, dates, heures,
BE/fabrication et commentaire. Les groupes montrent leurs agrégats, avec dates
et charge non éditables ; cycles et parents incompatibles restent refusés par
le serveur. Le lecteur consulte des formulaires désactivés sans commande d’écriture.

Les éditions envoient uniquement les champs modifiés avec la révision chargée.
Un conflit garde le brouillon. « Recharger et comparer » relit le détail sans
sauvegarder ; « Préparer mon brouillon sur cette révision » reprend uniquement
les changements de l’utilisateur sur le nouvel état, puis exige une sauvegarde
explicite. La création d’une tâche conserve aussi ses champs en cas de conflit
de projet et peut reprendre la nouvelle révision sans ressaisie. La navigation
entre sous-rubriques conserve les brouillons ; quitter un projet ignore ses
réponses tardives. Les formulaires prennent le focus et précèdent la liste.

`PlanningPanels.test.tsx` couvre 13 cas ; la suite React compte 127 tests dans
26 fichiers. Deux cas backend supplémentaires vérifient les détails, droits et
libellés hors page : le socle L2 compte désormais 97 cas, et la suite Python
429 réussites / 1 ignoré. Ruff, TypeScript et Vite sont conformes.

La recette `.ui-preview/xpilot-l2/ui-lists-final-recipe-1005/result.json` utilise
30 jalons et 31 tâches fictives sur `8011`, sans workers, puis crée une 32e tâche.
Elle vérifie l’actualisation immédiate, la recherche/pagination, la charge du
groupe et deux modifications concurrentes : la priorité sauvegardée ailleurs
reste conservée lors de la reprise du commentaire. Le jalon suivant s’ouvre
après validation, les dates réelles restent vides et les FK sont conformes.
Le serveur temporaire est arrêté ; `8001` reste disponible sur L1.

Le CSS prévoit une grille à une colonne à 650 px et un défilement horizontal
interne des tableaux. La tentative de viewport dans cette recette a conservé
un DOM à 1280 px ; elle ne valide donc pas le rendu étroit. Cette recette
responsive, Modèles, Références figées, Historique et activation L2.6 restent
à réaliser. Aucune donnée réelle, aucun module hérité ni build actif n’est modifié.

## Références & écarts et Historique — recette bureau

La capture révisionnée comprend tous les jalons et tâches, y compris hors page
ou archivés. L’instantané, son nom d’origine, son opérateur, sa date et son SHA
restent protégés par les triggers existants. Les métadonnées courantes sont
projetées depuis le dernier événement `baseline_metadata_changed` : nom,
commentaire et état actif. Une édition utilise la révision commune du planning
et ajoute un événement avant/après ; aucune ligne de référence n’est modifiée
ou supprimée, aucune nouvelle table n’est nécessaire. Deux commandes dans une
transaction voient les événements précédents après flush.

`GET /baselines?include_inactive=true` inclut les références archivées ; la
pagination est SQL. `GET /baselines/{id}` renvoie métadonnées, révision et droits,
`PATCH /baselines/{id}` accepte uniquement nom/commentaire/actif et révision.
Instantané, SHA, type, opérateur et date de capture ne sont pas des entrées
modifiables. L’archive v4 conserve les événements et vérifie leurs champs/types,
la chaîne avant/après et les liens de référence ; le remappage change seulement
les pointeurs déclarés, jamais les commentaires. Les anciens formats restent
compatibles. La restauration sur copies conserve **13 171 lignes / 109 135
cellules** après préparation ; comparaison, métadonnées archivées et empreintes
sources restent conformes :
`.ui-preview/xpilot-l2/archive-metadata-application-copy-1005/result.json`.

L’écran propose captures initiale/contractuelle/revue/avenant, métadonnées et
comparaison à la révision actuelle. Capture et édition conservent leur brouillon
après conflit et exigent une reprise explicite ; le lecteur consulte et compare.
La comparaison indique noms des éléments, champs, sévérités, ajouts/retraits,
avant/après, sources, filtres et delta de charge. Le tableau se pagine par 25
écarts ; les compteurs et le delta décrivent la comparaison complète. Une charge
8 → 12 h sur une feuille et son parent produit +4 h, sans double comptage.
Le journal charge 25 résumés puis le détail seulement à la demande, avec révision,
date, opérateur et changements. Les preuves conservées peuvent ouvrir le lecteur
de source. Les titres restent visibles sous les deux en-têtes fixes et les
tableaux de bureau n’ajoutent plus de défilement horizontal inutile.

`PlanningBaselinesHistory.test.tsx` couvre 12 cas, en plus des 13 cas Jalons/Tâches.
La suite React compte 139 tests / 27 fichiers ; les deux panels Planning modifiés
ont ensuite été revérifiés à 25 cas. TypeScript et Vite sont conformes ; le build
privé émet un avertissement de chunk supérieur à 500 kB (environ 511 kB brut /
149 kB gzip), sans erreur. La suite Python finale passe à 436 tests / 1 ignoré
et Ruff est conforme. La recette navigateur
`.ui-preview/xpilot-l2/ui-baselines-history-recipe-1005/result.json` valide une
capture des 30 jalons / 31 tâches fictifs, modification de charge, métadonnées,
archivage et journal ; l’instantané conserve ses valeurs et son empreinte.
Le serveur de recette est arrêté et `8001` reste sur L1.

**Complément encore requis par l’audit :** le service local XPilot
`ProjectBaselineService.PROJECT_FIELDS` capture aussi les dates de début/fin
et `budget_hr_total` du projet (`project_governance.py:294`). Dans Agent, les
dates sont dans le profil L1 et le budget heures opérationnel est
`Project.tdao_budget_h`. Les instantanés actuels ne capturent pas encore ces
champs projet ; ils portent jalons/tâches et UUID projet. L2.4 est remis en cours
pour ajouter ce contrat, sa comparaison et sa compatibilité avec les captures
v1, sans copier prix/budget achat/taux/marges. Modèles UI, recette responsive
et activation L2.6 restent également nécessaires avant livraison du lot.

## Engagements projet — instantanés v2 et compatibilité v1

Le complément annoncé précédemment est maintenant qualifié. Les nouvelles
captures utilisent `version: 2`, avec un objet `project` contenant exactement
`start_date`, `planned_end_date` (profil L1) et `budget_hours`
(`Project.tdao_budget_h`). Le budget enregistré, y compris zéro, n’est jamais
déduit des tâches ou du CDC. Aucune donnée financière n’entre dans ce contrat.
Dates ISO strictes, ordre début/fin et budget fini non négatif sont contrôlés ;
un engagement stocké invalide bloque la capture avec 409, sans correction
silencieuse. Les tâches et jalons restent intégralement figés hors pagination.

Les captures v1 existantes restent immuables. Leur comparaison affiche
`project_comparison_available: false` et `project_budget_hours_delta: null` ;
l’écran signale que leurs engagements projet n’ont pas été capturés. En v2/v2,
les écarts `kind: project` exposent les deux dates et le budget séparément ;
`project_budget_hours_delta` ne s’ajoute pas à `planned_hours_delta`. Le journal
affiche les dates projet dans des lignes distinctes. Les modifications de dates
par la fiche L1 ajoutent `project_changed` et invalident la révision planning
dans la même transaction. Une modification de description seule ne le fait
pas. Le pont reste inactif sans les six triggers immuables L2 ; des tables
dormantes ne suffisent pas à activer le planning. Des protections partielles ou
altérées produisent un conflit explicite, sans migration déclenchée par la fiche.

L’archive v4 accepte les captures v1/v2, contrôle les champs projet avant import,
remappe l’identité projet et recalcule le SHA sans changer les dates/heures ni
les textes historiques. Les tests couvrent restauration v1/v2, budget et dates
distincts, refus des champs financiers ou invalides avant écriture, révision
périmée et compatibilité des archives L1. La qualification compte 125 cas L2,
457 tests Python réussis / 1 ignoré et 142 tests React / 27 fichiers ; Ruff,
TypeScript et Vite passent (avertissement de chunk d’environ 512 kB conservé).

Preuves : `.ui-preview/xpilot-l2/ui-project-snapshot-recipe-1005/result.json`
et `.ui-preview/xpilot-l2/archive-project-commitments-copy-1005/result.json`.
Le navigateur valide une référence contractuelle révision 63, puis une fin
01/12 → 10/12 en révision 64 et son journal opérateur, avec variations de charge
et budget nulles ; l’instantané conserve 80 h et la date initiale. Les copies
qualifient aussi un budget 80 → 120 h, des métadonnées archivées, des UUID typés
et une comparaison identique après restauration : 13 176 lignes / 109 185
cellules préexistantes après préparation conservées, fichiers source inchangés,
aucune violation FK. Le serveur fictif sans travailleurs est arrêté. Modèles UI,
recette responsive et activation globale L2 restent nécessaires ; aucune source,
ressource compilée ou base L2 n’a été déployée dans `C:/Agent`.

## Modèles UI et qualification responsive (L2.5 terminé)

Le catalogue paginé/recherchable inclut les modèles archivés sur choix explicite.
`GET /api/v1/planning-templates/{id}` donne la révision exacte et `can_manage`,
avec les mêmes règles de typologie/périmètre que les versions. Un lecteur peut
consulter et calculer un aperçu, sans publier ni appliquer. Les métadonnées sont
modifiées par patch avec révision ; archiver conserve les versions. Le brouillon
de publication est une copie de la version choisie, jamais une réécriture.
Conflit : brouillon conservé, relecture puis reprise explicite sur la nouvelle
révision ; aucune tentative automatique d’enregistrement.

L’éditeur structure les jalons (code, titre, ordre/décalage) et tâches (clé,
parent, jalon, priorité, BE/fabrication, jours ouvrés, heures). Pagination par
10, clés stables, validation de cycles/relations/dates/charges avant publication ;
le backend reste autoritaire. Un groupe agrège ses enfants et ne porte pas de
charge/dates propres. Retirer une entrée du brouillon ne retire aucun élément
de projet. Aucun import JSON ni champ financier n’est nécessaire à ce parcours.

Chaque application relit le planning puis choisit une version immuable, y compris
ancienne, et un calendrier explicite. Correspondances compactes par jalon,
sélecteur chargé à l’ouverture et suggestions choisies manuellement ; code
identique réutilisé sans remplacement implicite. Politique de prévisions et
mise à jour des tâches actives issues du modèle sont explicites (celle-ci reste
décochée par défaut). L’aperçu expose ajouts/écarts/charge, exclusions et changement
de version, même sans écart de tâches. Modifier un paramètre ou rencontrer un
conflit invalide l’aperçu. Après relecture, reprendre volontairement sur la
révision actuelle ; calendrier du collègue repris seulement si le brouillon
n’a pas modifié les exclusions initiales.

Recette `.ui-preview/xpilot-l2/ui-models-recipe-1005/result.json` : deux versions
publiées sans toucher aux 30 jalons / 31 tâches initiaux, application de v1 après
publication de v2, puis v2 avec mise à jour volontaire 8 → 12 h. Les 123 lignes /
1 088 cellules suivies dans cinq tables sont intactes, dont dates/sources/profil ;
les payloads/SHA des versions restent inchangés et le budget projet reste 80 h.
Après application : révision 64, 44 jalons / 33 tâches, exclusions 06/10,
prévisions 05/10 → 08/10, delta de charge +4 h sans double compte du groupe,
zéro FK et aucune erreur console. Bases fictives, aucun travailleur, serveur de
recette arrêté. La dernière qualification passe 126 cas Python L2, 458 Python /
1 ignoré, 41 React L2 et 155 React / 28 fichiers, Ruff, TypeScript et build.
Le bundle principal reste au-dessus du seuil Vite de 500 kB (avertissement).

Les six vues Planning, formulaires d’édition/capture et détails d’historique sont
vérifiés à 390 pixels ; le modèle et la navigation sont aussi vérifiés à 650 et
1280. Correction du défilement interne des onglets/tableaux et de la largeur
intrinsèque des grilles ; les libellés accessibles restent confinés au tableau.
La vue Planning existante est conservée et rechargée lorsqu’elle redevient
visible ; les réponses tardives d’un ancien projet sont ignorées. Les versions
ouvertes se positionnent sous la navigation fixe. Aucune suppression de module
ou de données. Les étapes historiques indiquées « en cours » ci-dessus sont
supersédées par cette qualification. La suite est L2.6 : fusion et activation
globale sur 8001 avec conservation des corrections mails canoniques, sauvegarde
et restauration qualifiées. À ce stade, aucun code, bundle ou schéma L2 n’est
déployé dans `C:/Agent` ; le serveur actif reste L1 et XPilot 8000 est intact.

## Activation globale L2 (L2.6 terminé)

Candidat `integration-models-1005/candidate` : fusion de 56 chemins avec les
sources de `C:/Agent`, conservation de 194 fichiers hors L2 (mails compris),
résolution revue des chevauchements L1/L2 et assemblage des contrats/sélecteurs
partagés. Fixtures CDC/liaison Brain réinitialisées par `init_db()` pour garder
les protections immuables ; aucun affaiblissement de la migration. Le build est
identique à celui de la recette navigateur (JS `index-Th_iZlUu.js`, CSS
`index-CYwYpuEF.css`). Qualification finale du candidat : 459 Python / 1 ignoré,
155 React / 28 fichiers, Ruff, TypeScript, Vite ; 127 cas Python et 41 React L2.

Arrêt coordonné du seul Agent 8001. Sauvegarde
`C:/Agent/logs/xpilot-l2-activation-20261005-220438` : code antérieur, dist antérieur
et `full-state-before-l2` (bases ERP/Brain, fichiers ERP et stockage Brain gérés).
La restauration exige un nouveau dossier : copie de recette
`.ui-preview/xpilot-l2/global-restored-before-l2-1005`, 1 388 fichiers vérifiés
par SHA, 14 033 lignes / 116 204 cellules contrôlées et zéro changement inattendu
ou FK. Les 2 643 changements de chemins portables/états de jobs sont explicitement
vérifiés, sans démarrer de travailleurs ni modifier la production. Les chemins
réseau externes restent soumis aux limites de sauvegarde décrites précédemment.

Après cette preuve, migration de 7 tables / 6 protections immuables et conservation
de toutes les 14 033 lignes / 116 204 cellules préexistantes contrôlées, sans
remplacement de jalons ni import d’XPilot. Les sources sont publiées puis l’index
web bascule, avec anciens bundles conservés. Agent redémarre sur 8001 ; `/health`
est sain pour les deux bases. API de listes/références/historique vérifiée en
lecture sur les dix projets, catalogue de modèles vide et définition de 14 étapes
accessible : aucun modèle n’est appliqué implicitement.

La recette visuelle réelle a révélé un tri alphabétique des jalons hérités sans
position L2. Correction : avant pagination, lire seulement leurs identités/titres
pour retrouver l’ordre métier normalisé (aliases compris) ; une position explicite
L2 prévaut, les autres jalons se rangent après le cycle historique. Test paginé
avec alias et position spécifique, filtres et absence d’écriture ; contrôle API
sur les dix projets et vérification visuelle. Code précédent sauvegardé dans
`legacy-order-code-before`, aucune mutation de données ni nouvelle migration.

Preuves : `.ui-preview/xpilot-l2/delivery-1005.json`,
`runtime-verification-1005.json`, `activated-browser-1005.json`,
`activated-planning-1005.png`, `global-restore-before-l2-1005.json` et
`integration-models-1005/order-patch-result.json` sous `.ui-preview/xpilot-l2`.
Les contrôles d’écriture restent sur copies fictives ; la recette réelle montre
les huit jalons du projet LED 2026 en ordre métier, révision 0, avec sources/dates
conservées, menu latéral blanc et nouveaux onglets. L2 est livré ; toutes les
mentions de préparation/activation attendue ci-dessus sont désormais historiques.
L’objectif reste actif pour L3–L9 ; aucun commit ni push.
