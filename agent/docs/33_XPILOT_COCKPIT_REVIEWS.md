# L4 - Cockpit projet et revue de lancement

État au 6 octobre 2026 : **L4 livré et actif sur Agent 8001 ; objectif L0–L9 encore actif, L5–L9 à réaliser**. Cockpit, RLP, archive v6 et relations restaurées sont qualifiés ; sauvegarde, migration conservatrice et navigation du serveur réel sont vérifiées. L0–L4 sont disponibles depuis `C:\Agent`. XPilot et son port 8000 sont inchangés. Les qualifications préparatoires ci-dessous restent des preuves historiques ; la livraison courante est enregistrée en fin de document.

## Périmètre conservé

Le [plan L4](28_XPILOT_PROJECT_PLAN.md) exige un cockpit ERP interactif, une RLP
structurée, la réinjection des réunions locales, des publications figées et une
recette clavier/chargements/erreurs/performance. Les travaux backend ci-dessous
ne remplacent aucun de ces parcours. L5-L9 restent dans l'objectif.

Les sources XPilot lues sont `domain/project_reviews.py`, les modèles/schémas,
le service de revues, son générateur PDF et la validation de publication.
La RLP est seule opérationnelle. Son catalogue expose trois sections obligatoires :
`vigilance_points`, `expected_functions`, `initial_constraints`. Agent ajoute
`decisions` et `actions`, conservant leurs preuves audio et leur correction humaine.
Les six autres types désactivés dans XPilot ne deviennent pas des commandes actives.
La signature est préparée par participant (`signature_required`), mais son workflow
appartient à L5. Aucun envoi, API vocale payante ou publication automatique.

## Cockpit relationnel qualifié dans le worktree

La Vue d'ensemble accueille deux rubriques nommées : **Cockpit** et **Fiche et
équipe**. La fiche, ses référentiels, son historique et les autres modules restent
accessibles. Le cockpit présente un parcours ordonné de jalons ; chaque sélection
charge les tâches et livrables réellement reliés, avec accès aux éléments sans
jalon. Les dates contractuelle/prévisionnelle/réelle et le workflow restent séparés.

Les lectures `/api/v1/projects/{id}/cockpit`, `/items/tasks`, `/items/deliverables`
et `/alerts` sont indépendantes et paginées. La recherche accepte accents et `%`
littéraux, inclut les jalons portant un élément correspondant, et le filtre des
jalons passés conserve le jalon explicitement ouvert. Les agrégats comptent tout
le projet ; aucun plafond de 500 tâches ne définit les totaux. Avancement et heures
suivent les règles du portefeuille : CDC actif puis budget d'heures du projet,
consommation manuelle + Sage, reste à faire réestimé ou solde de charge. Les totaux
historiques de tâches restent ceux du portefeuille ; les listes concernent les
tâches actives. Les livrables liés à plusieurs jalons ne sont pas dupliqués dans
le total projet.

L'inspecteur réutilise les formulaires L2 pour créer/modifier une tâche ou modifier
les dates du jalon, avec révision partagée et comparaison en cas de conflit.
Actualiser conserve la saisie. Une sélection reste verrouillée tant que l'inspecteur
est ouvert, et les requêtes tardives sont annulées. Les lectures incohérentes entre
révisions exigent une actualisation ; chaque branche dispose de son erreur et de
sa relance. L'inspection documentaire ouvre la fiche L3 et ses preuves en précisant
son origine cockpit, sans inventer un contrôle absent ou une version observée.

La vue compacte borne la hauteur des listes sans intercepter les événements de
molette. Pagination, boutons natifs et indicateurs de sélection sont accessibles
au clavier. À 390 px demandés (375 px utiles observés avec scrollbar), l'inspecteur
s'empile et le formulaire passe à une colonne, sans débordement horizontal.

Preuve antérieure cockpit : `.ui-preview/xpilot-l4/cockpit-result.json`. Cette suite passe
**752 Python / un ignoré, 277 React, Ruff, TypeScript et build**. 17 cas ciblés
contrôlent totaux au-delà de 500, multi-rattachements, recherche, heures, neutralité,
droits, corruption de relations et révisions mélangées. La recette navigateur
sur données fictives contrôle sélection clavier, création/compteurs, date prévisionnelle
sans changement de workflow, lien livrable, fiche/équipe et petit écran. Les erreurs
de branche/brouillons sont également contrôlées par React ; la recette globale
de L4.5 reste à réaliser. Sur 100 jalons/5 000 tâches/2 500 livrables, le service
structure culmine à 49 ms ; création et modification avec commit restent sous
420 ms. La mesure HTTP réelle inclut protection locale/middleware/transport et
reste sous 1,5 s. Ces mesures ne sont pas une garantie sur les réseaux/fichiers réels.

Les routers cockpit et revues sont raccordés seulement dans la recette fictive
isolée ; ils restent non enregistrés dans `app.main` pour l'activation finale
coordonnée après restauration et qualification globale. Aucun nouveau service de production.

## Interface RLP et réunions conservées

Réunions & revues accueille **Revue de lancement** et **Réunions et audio**.
Le code de transcription, comptes rendus, export Markdown et conversion d'actions
en tâches est conservé. La RLP propose un premier brouillon puis une liste paginée
de révisions, avec droits serveur. Contexte : date, lieu, notes, jalon, participants
du répertoire/de l'équipe ou externes, signatures attendues et livrables du projet.
Les sélecteurs jalon/personne/livrable sont paginés et retiennent leur sélection.
Les trois sections obligatoires, décisions et actions sont éditables ; modifier
un point ou son pilote/échéance invalide sa relecture. Les limites de saisie sont
celles des contrats backend. Les citations conservent interlocuteur, secondes,
texte original, révision, modèle et empreinte ; corriger le point ne les écrase pas.

Le sélecteur de réunion est paginé et rechargeable. Seules les sources liées,
sans traitement actif, avec transcription validée et synthèse sur la même révision
sont proposées. La liste est scalaire ; l'aperçu ouvre seulement la source choisie
et détecte une révision changée. Il faut enregistrer la saisie avant l'import.
La commande serveur réexamine portée, versions et citations ; les propositions
importées restent à vérifier. Elle ne crée aucune tâche/réunion ni publication.

Une modification concurrente conserve le brouillon. La comparaison utilise
base/saisie/version actuelle par champ et identifiant de point ; les conflits
exigent un choix humain. Un point supprimé par un collègue n'est pas recréé si
l'utilisateur ne l'a pas changé. Appliquer la comparaison prépare un brouillon,
sans sauvegarde automatique. Si la revue est figée ou les droits ont changé, la
saisie reste copiable avant abandon explicite. Les changements de sous-vue gardent
le brouillon ; changer de projet annule les lectures précédentes. La sélection
des révisions reste verrouillée pendant une saisie.

Publier exige un brouillon enregistré, les contrôles serveur et une confirmation.
La fiche publiée est désactivée et affiche les titres/noms capturés ; le navigateur
vérifie SHA-256 du PDF avant de proposer son téléchargement. Seule la dernière
publication autorisée propose une nouvelle révision. L'historique paginé ouvre
contenu et preuves avant/après chaque événement. Les signatures attendues du PDF
restent à recueillir ; leur workflow est L5.

Preuve réelle : `.ui-preview/xpilot-l4/rlp-ui-evidence.json`. Sur le mono-serveur de
recette fictif : création clavier, source par interlocuteur, jalon/personne/livrable,
sections, relecture, sauvegarde, publication/PDF, révision indépendante et historique.
La source Brain et la première publication restent inchangées après modification
de la seconde revue. Un second client modifie le planning : conflit visible, saisie
conservée puis reprise explicite avec la nouvelle révision partagée. Les anciens
comptes rendus/audio et le brouillon entre vues sont vérifiés. Console sans erreur
observée. À 390 px demandés (375 utiles), la fiche a 342 px clients et 342 px de
contenu, formulaire à une colonne. La suite passe 292 React, dont 12 parcours RLP
et trois cas de fusion sélective. La recette globale L4.5 et l'activation restent
nécessaires ; cette préparation n'est pas disponible sur 8001.

## Socle de données et de concurrence

- `project_reviews` : révision métier numérotée, brouillon JSON structuré,
  participants, date/lieu, notes, items ordonnés, jalon, livrables et provenance.
  Le code existant de réunions et ses tables restent en place.
- `project_review_publications` : snapshot canonique et SHA-256, PDF encodé en
  base64 et SHA-256, auteur et horodatage. Les octets sont dans la base ERP :
  la publication ne repose pas sur une transaction séparée vers un lecteur réseau.
- `project_review_events` : audit immuable des commandes, révision de planning,
  auteur, contenu et provenance avant/après. Une correction ne perd pas son histoire.

Le module de migration effectue une prévalidation des colonnes, types, clés,
contraintes, index et triggers. Une sauvegarde réussie précède tout DDL. Trois
tables et six protections sont installées explicitement, jamais par un import
ou un `create_all` générique. Une seconde installation ne sauvegarde ni ne migre.
Le démarrage du mono-serveur n'est pas encore raccordé à cet installateur L4.

Les commandes verrouillent la révision ERP commune à L2/L3 avant toute lecture
de la révision de brouillon. Elles exigent `expected_revision` et
`expected_review_revision`. La transaction est annulée en cas de conflit/erreur.
Les événements de RLP ont leur propre table typée ; ils ne deviennent pas des
actions inconnues dans l'historique de planning L2.

Une publication exige la date, une équipe active, au moins un participant et
un livrable actif sélectionné, les trois sections obligatoires et la vérification
de chaque point. `confirmed: true` est une commande humaine explicite. Le snapshot
inclut projet, équipe, livrables, contrôles, notes et preuves tels que publiés.
Les triggers interdisent UPDATE/DELETE des publications et événements, ainsi
que toute modification/suppression d'une révision déjà publiée.
La nouvelle révision copie le contenu dans un brouillon indépendant, conserve
les preuves et laisse l'ancienne révision et son PDF inchangés.

## Adaptateur HTTP préparé

Ces routes sont qualifiées avec un `TestClient` sur bases fictives, mais **ne sont
pas encore enregistrées dans `app.main`**, ni activées sur 8001 :

| Méthode | Route | Usage |
|---|---|---|
| GET | `/api/v1/review-types` | Trame RLP opérationnelle |
| GET/POST | `/api/v1/projects/{id}/reviews` | Liste paginée / premier brouillon |
| GET | `.../reviews/recording-choices` | Sources liées, validées et actuelles, liste scalaire paginée |
| GET/PUT | `.../reviews/{review}` | Lecture neutre / sauvegarde explicite |
| POST | `.../reviews/{review}/revision` | Nouveau brouillon depuis une publication |
| POST | `.../reviews/{review}/recordings` | Import explicite de la synthèse audio |
| POST | `.../reviews/{review}/publish` | Gel et génération du PDF |
| GET | `.../reviews/{review}/publication` | Snapshot et empreintes |
| GET | `.../reviews/{review}/pdf` | Octets exacts, ETag, téléchargement |
| GET | `.../reviews/{review}/history` | Journal paginé |
| GET | `.../reviews/{review}/history/{event}` | Contenu et preuves avant/après dans cette revue |

Les services appliquent eux-mêmes la portée projet et le rôle lecture seule,
y compris sans HTTP. Les références de jalons, livrables et personnes sont
contrôlées dans le même projet ou dans le référentiel autorisé. Pagination et
tailles des commandes sont bornées ; les champs supplémentaires sont refusés.

## Réunion locale et preuves

L'import lit seulement le Brain. Il vérifie le lien ERP/Brain, l'appartenance de
l'enregistrement, la révision demandée, la transcription validée et une synthèse
issue de cette même révision. Un job actif ou une source étrangère bloque l'import.
Chaque décision/action/point ouvert doit citer un segment existant et un extrait
présent dans la transcription. Sa preuve conserve source, enregistrement,
versions, modèle, empreinte de synthèse, nom de l'interlocuteur, texte et secondes.

Les points arrivent avec `reviewed: false`, donc bloquent la publication jusqu'à
leur relecture. La synthèse générale est ajoutée aux notes comme proposition
« à vérifier » ; elle ne remplace pas les notes existantes. Le traitement audio,
la transcription par interlocuteur, les anciennes réunions et leurs tâches ne
sont pas modifiés. L'import ne crée ni réunion ERP, ni tâche, ni publication.
Une synthèse identique ne s'importe pas deux fois. Sa correction reste possible
dans le brouillon sans changer la citation originale.

## PDF et dépendances

ReportLab est ajouté aux fichiers de dépendances et verrous, avec Pillow et
charset-normalizer. Les 30 versions applicatives et 42 versions de développement
existantes sont conservées. La recette utilise ReportLab **4.5.1** installé dans
`.ui-preview/xpilot-l4/pdf-runtime`, sans modifier Python système ou le serveur.
Avant activation, installer les dépendances verrouillées dans son environnement.

Le moteur compose un A4 lisible, avec police embarquée, accents, pagination,
participants, sections, citations, contrôles, équipe et pied de page de publication.
Les textes sont échappés ; aucun HTML de la réunion ne devient une instruction
du générateur. La panne du moteur laisse le brouillon et sa révision inchangés.
L'exemple fictif `.ui-preview/xpilot-l4/pdf-qa/rlp-sample.pdf` est rendu par Poppler
sur trois pages ; les trois images finales sont inspectées, y compris notes
longues, noms longs, saut de page d'action et libellés métier français.

## Sauvegarde et travaux restants

La copie SQLite du corpus fictif conserve exactement brouillons, événements,
publications et PDF. La migration conserve toutes les cellules préexistantes.
Le contrat typé de RLP et sa migration de correspondances sont préparés et
qualifiés dans le worktree. Le transport d'archive sélective et sa restauration
coordonnée restent **à raccorder et qualifier** : le remappage générique de v5
n'est pas valide pour les snapshots immuables et leurs preuves ERP/Brain.
Un garde provisoire refuse un export contenant des revues ou leur import générique
plutôt que de perdre leurs données. Ce garde sera remplacé par le format typé L4
avant raccordement/activation. Les archives existantes sans RLP restent utilisables.

Cockpit avec inspection/couches/recherche et mutations L2/L3 partagées qualifié.
À achever :
archive sélective typée et restauration globale avec source audio ; raccordement
de la migration/routes ; recette réelle
390/650/1280 px, clavier, concurrence et erreurs ; mesure du corpus sous 1,5 s ;
qualification globale finale puis sauvegarde/activation de 8001. Le suivi exact
est [docs/29_XPILOT_EXECUTION.json](29_XPILOT_EXECUTION.json).

## Vérification locale

### Contrat de restauration RLP préparé (L4.4)

`project_review_archive.py` vérifie les publications canoniques et empreintes PDF,
la chaîne complète de brouillon/publication/révision, les références de personnes,
jalons, livrables, contrôles et versions de fichiers, ainsi que les preuves audio
ERP/Brain. Les dates UTC conservent leur sens après sérialisation SQLite. Les
compteurs et blocages documentaires sont recalculés depuis les contrôles capturés.
Une version de fichier ou un visa d'un autre livrable est refusé, même dans le
même projet. Les révisions de planning, livrables et revues forment un journal
commun complet ; aucune publication ne peut apparaître comme sauvegarde manuelle.

Deux colonnes JSON `bindings` ajoutent des correspondances séparées ERP et Brain
aux publications et événements. Leur contenu publié, PDF, citations et payloads
avant/après restent inchangés. Les nouveaux identifiants concernent seulement les
liens matérialisés connus du contenu vivant. Les identifiants locaux des points,
noms, notes et textes ressemblant à des UUID sont conservés. Les correspondances
restent plates après vingt restaurations simulées ; un même UUID présent dans
ERP et Brain garde deux correspondances indépendantes.

Une transcription ultérieure ne remplace pas l'extrait historique : sa version
validée conservée dans `source_artifacts` est requise avec texte, interlocuteur et
secondes identiques. Le remappage du pointeur d'enregistrement de cet artefact est
explicite ; son texte et ses segments restent intacts. L'empreinte de synthèse
décrit la proposition capturée ; elle n'est pas une signature d'authenticité.

La migration détecte les deux colonnes absentes, exige la sauvegarde avant tout
DDL, ajoute seulement ces colonnes avec défaut `{}` et préserve les six triggers.
Elle refuse un schéma incompatible et reste idempotente. Une panne de sauvegarde
ne modifie aucune cellule. La copie du corpus de recette UI conserve **17 737
lignes / 146 808 cellules ERP**, le Brain exact et les publications/PDF/événements
exacts. Son contrat est validé en lecture seule : deux revues, six événements RLP
et sept événements planning/livrables, révision partagée 13. Preuves :
`.ui-preview/xpilot-l4/review-bindings-copy-result.json` et
`.ui-preview/xpilot-l4/review-archive-corpus-result.json`.

Cette première qualification concernait le contrat et la migration sur copies.
Le transport v6 est maintenant raccordé dans le worktree, avec réconciliation
historique et import coordonné ERP/Brain. Le refus d'import de revues par les
formats v2–v5 reste en place. La lecture API/UI des correspondances et l'activation
demeurent à terminer ; aucun processus de recette/production n'a été migré ou
redémarré par cette étape.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -q
ruff check app backend/app tests
python -m pytest tests/test_project_reviews.py tests/test_project_review_api.py -q
python -m pytest tests/test_project_review_archive_contract.py -q
```

Qualification ciblée actuelle : **31 tests réussis**, dont publication/révision, six
contournements SQL du gel, concurrence, portée/lecture seule, erreurs et rollback,
copie de sauvegarde, import sourcé, refus de citation fabriquée et PDF réel,
portée du détail d'événement et sélecteur de source paginé/neutre/actuel.
La dépendance verrouillée est qualifiée séparément de la première recette utilisant
le runtime PDF embarqué. Le test de pagination finale est répété après correction.
La suite complète passe **735 tests (un ignoré)**, avec Ruff conforme. Le PDF final
est également testé avec ReportLab 4.5.1 après sa dernière correction. Preuve :
`.ui-preview/xpilot-l4/core-result.json`. Cette preuve qualifie le socle préparé,
pas l'intégralité de L4 ni son activation.
Les **159 cas** d'archives L1-L3 et du garde provisoire RLP sont requalifiés après
le changement de l'exporteur (`.ui-preview/xpilot-l4/archive-regression.xml`).

Qualification consolidée RLP/UI : **754 Python / un ignoré, 292 React, Ruff, TypeScript et build**. Les 31 tests RLP sont requalifiés après la dernière validation de synthèse JSON. Preuve : `.ui-preview/xpilot-l4/rlp-result.json`. L4 n’est pas activé ; archive/restauration et qualification globale restent à réaliser.

Contrat RLP/restauration préparé : **815 tests Python / un ignoré et 94 tests ciblés**, dont 63 cas de contrat/migration ; Ruff conforme. Les deux derniers cas de refus de schéma sont couverts par la requalification ciblée après collecte de la suite globale. Preuve historique : `.ui-preview/xpilot-l4/review-archive-contract-result.json` ; la qualification du transport ci-dessous la complète.

## Transport sélectif v6 et récupération sur copies

L'export choisit v6 pour un projet contenant des revues. Il exige les trois tables
protégées et les socles L1/L2/L3 déjà installés. Export/import ne migrent aucune
base. Les personnes et types historiques des publications sont inclus, puis
réconciliés sans modifier les référentiels existants. Les projets sans revue
conservent v2–v5 ; ces formats refusent toujours toute revue.

`project_archive_transaction.coordinated` possède une connexion ERP indépendante
et y attache seulement la base Brain configurée. Les deux sessions partagent la
connexion ; seules les instructions Brain reçoivent une traduction de schéma.
Les mutations ORM Brain et commits internes sont interdits. Une session appelante
avec éditions, écritures SQL ou savepoint en attente est refusée sans consommer
ses modifications. Les deux verrous précèdent la réconciliation et un seul commit
valide les bases. Les fichiers SQLite doivent exister et être distincts, les
relations protégées, les journaux `delete`, `truncate` ou `persist` et
`synchronous` au moins `FULL` sur la connexion utilisée. Aucun mode n'est forcé ;
WAL est refusé. La connexion est détachée avant retour au pool, sinon invalidée.
Une erreur de commit annule aussi la transaction SQLite réelle qui peut subsister
après détachement logique par SQLAlchemy.

Ces conditions suivent la documentation de l'[attachement SQLite](https://www.sqlite.org/lang_attach.html).
Les tests couvrent erreurs et arrêts de processus avant validation et après
commit, sur disque local Windows. Ils ne simulent pas une coupure électrique
pendant COMMIT et ne qualifient pas les garanties d'un stockage réseau.

Les captures, PDF et payloads du journal restent exacts. Les correspondances
plates ERP/Brain composent les références originales avec les nouveaux IDs,
y compris à la deuxième restauration et si un UUID apparaît dans les deux bases.
Une chaîne reçue dans un ordre différent est insérée parents en premier. Textes,
interlocuteurs, citations et identifiants locaux restent inchangés. Si le Brain
d'origine est réutilisé, ses sources et artefacts restent intacts ; les
enregistrements du nouveau projet et leurs transcriptions retenues sont copiés
avec leurs propres IDs. Le pointeur d'enregistrement est le seul champ JSON
déplacé. Une correction ultérieure conserve la preuve figée grâce à l'artefact
de transcription historique.

La limite de 150 Mo cumule pièces décodées et données des revues, PDF/captures
inclus. Une pièce brute déclarée dans `source_metadata.raw_path`, ou le chemin
local d'un enregistrement, doit être présente et correspondre au SHA Brain.
Un ancien URI distant sans pièce déclarée reste une référence. Les dépendances,
fichiers et destinations sont vérifiés avant insertion. Les nouvelles pièces
sont créées exclusivement, synchronisées et vérifiées. Une pièce déjà présente
avec d'autres octets est refusée sans écrasement.

SQL et fichiers restent deux supports distincts. Le journal sous
`APP_DIR/backups/archive-imports/<nouveau-projet>/` décrit destinations,
empreintes, tailles et présence préalable. `manifest.json` et `events.ndjson`
sont synchronisés. Les pièces préparées après interruption sont conservées,
sans suppression ni reprise automatique. La lecture neutre
`inspect_preparation(erp_session, directory, brain_session)` distingue
`committed`, `not_committed` et `inconsistent` en vérifiant les deux bases et
en tenant compte d'un Brain réutilisé. L'absence du dernier marqueur n'est pas un
échec SQL. Une erreur de journal après commit est loguée sans transformer un
import réussi en invitation à le répéter.

La copie `.ui-preview/xpilot-l4/review-transport-copy-20261006-200450` conserve
le corpus initial et ajoute un projet fictif par les commandes L1/L3/L4. Le
corpus de performance contient des états ORM sans journal ; il reste exact et
n'est pas présenté comme une archive métier valide. La restauration sélective du
nouveau projet préserve **17 770 lignes / 147 115 cellules ERP** et les **13 lignes
/ 118 cellules Brain** contrôlées. La sauvegarde globale existante est ensuite
réellement restaurée dans un dossier neuf : seuls les chemins mutables sont
relocalisés, les captures/PDF restent identiques et le projet peut être ré-exporté
en v6. Preuve : `.ui-preview/xpilot-l4/review-transport-copy-result.json`.

À l’étape transport, le backend était préparé sur copies ; les correspondances
API/UI restaient à raccorder. La qualification de lecture ci-dessous complète
désormais L4.4. L4.5/L4.6 et L5–L9 restent au plan. L0–L3 seuls restent actifs
sur 8001 ; aucun serveur canonique n'est migré ou relancé par ces préparations.

```powershell
python -m pytest tests/test_project_review_archive.py tests/test_project_archive_transaction.py -q
```

Transport sélectif RLP v6 qualifié dans le worktree : **863 tests Python / 1 ignoré et 327 tests ciblés**, Ruff conforme. Les erreurs et arrêts de processus préservent les deux bases ; les pièces préparées restent journalisées. Une restauration globale sur copie conserve les publications et relocalise seulement les chemins mutables. Preuve : `.ui-preview/xpilot-l4/review-transport-result.json`. Les correspondances API/UI et l’activation restent à terminer ; L4.4 et l’objectif L0–L9 restent en cours, L0–L3 seuls actifs sur 8001.

## Lecture des publications et historiques restaurés

Les réponses `GET .../reviews/{review_id}/publication` et
`GET .../reviews/{review_id}/history/{event_id}` exposent désormais `bindings`
à côté des captures immuables. Une publication native renvoie `{}` ; une
publication transportée contient les correspondances plates `erp` et `brain`.
`snapshot`, `previous` et `value` gardent les valeurs originales, ainsi que les
empreintes et les octets du PDF. La consultation ne réécrit aucune publication.

L’interface résout seulement les relations déclarées, dans leur espace :
livrables et jalons ERP, enregistrements et sources Brain. Un identifiant présent
dans les deux bases ne partage pas sa correspondance. Les identifiants locaux
de point, preuve et segment, les textes, notes, noms et citations restent exacts.
Les réponses anciennes sans correspondances restent lisibles.

Les livrables associés affichent leur titre capturé après restauration. Le
bouton « Ouvrir le livrable » mène à la fiche actuelle du projet restauré ; son
contexte précise la différence avec la publication figée. Il ne crée pas de
contrôle ni de visa de jalon. Les droits de la fiche restent appliqués.

Chaque preuve propose « Consulter la réunion source », y compris dans le détail
d’un événement historique. La lecture commence à la demande, vérifie les IDs
d’enregistrement et de source reçus, puis montre le segment actuel et son
interlocuteur. La révision actuelle et celle de la citation conservée sont
indiquées séparément. Si le segment a disparu, la citation reste disponible.
Une erreur peut être retentée ; quitter la vue annule la lecture et ignore sa
réponse tardive. Cette consultation ne lance ni transcription ni synthèse.
Le lecteur audio utilise le chemin de cette réunion dans ce projet et s’adapte
à la largeur disponible.

La recette utilise une **nouvelle copie fictive restaurée**, distincte des
preuves précédentes et des bases canoniques. La transcription actuelle y est
volontairement corrigée à la révision 4 ; la citation et son artefact historique
restent à la révision 3. Le parcours est vérifié en propriétaire et lecteur,
au clavier et à 390 pixels, avec conservation exacte des deux fichiers SQLite
pendant la séquence finale de consultation. Le profil lecteur est qualifié
pour RLP et la fiche liée, pas pour tous les écrans hérités. L’audio de ce corpus
est constitué d’octets fictifs : cette recette vérifie son lien et ses commandes,
sans prétendre qualifier un décodage ou une lecture sonore réelle.
Preuves : `.ui-preview/xpilot-l4/review-links-ui-evidence.json` et
`.ui-preview/xpilot-l4/review-links-browser-neutral-result.json`.

Correspondances RLP/restauration qualifiées dans le worktree : **865 tests Python / 1 ignoré, 9 cas API ciblés et 298 React**, Ruff, TypeScript et build conformes. Les publications et événements exposent leurs correspondances séparément des captures ; l’interface conserve les titres/citations et ouvre les livrables/réunions actuels du projet restauré. Recette clavier, lecteur et mobile sur une nouvelle copie, avec bases exactes après consultation. Preuve : `.ui-preview/xpilot-l4/review-links-result.json`. L4.4 est qualifié sur copies ; L4.5/L4.6 et L5–L9 restent à réaliser, L0–L3 seuls actifs sur 8001. Aucune activation, migration canonique, suppression de données ni commit/push dans cette étape.

Raccordement L4.5 qualifié dans le worktree : **874 tests Python / 1 ignoré, 22 cas ciblés et 298 React**, Ruff, TypeScript et build conformes. Le serveur unique enregistre cockpit/RLP et installe le schéma ERP v8 avec préflight et sauvegarde commune. Un groupe de tables de revue partiel contenant des données est refusé avant toute DDL. Le démarrage à froid sur les dix projets historiques conserve toutes les cellules ; le second lancement est neutre et le retour à la sauvegarde est qualifié sur copie. La recette globale native/restaurée couvre PDF figé, audio WAV décodable, droits lecteur, clavier, mobile et concurrence avec conservation de saisie. Les lectures gardent les deux bases exactes ; les seules quatre cellules préexistantes modifiées pendant les commandes de recette appartiennent au brouillon fictif et à sa révision projet. Preuve : `.ui-preview/xpilot-l4/review-registration-result.json`. La précision de reconnaissance vocale n’est pas évaluée par cette recette fictive. L4.6 et L5–L9 restent à réaliser ; L0–L3 seuls actifs sur 8001. Aucun commit/push ni suppression.

## Démarrage et recette globale L4.5

`app.main` enregistre les routes cockpit et RLP avant le catch-all statique. `init_db` prévalide le groupe de revues avant toute écriture, puis appelle son installateur explicite après L3 avec le même `ensure_backup` et inscrit la version 8. Les tables de revue restent exclues du `create_all` générique. Un groupe absent ou partiel vide peut être complété ; un groupe partiel contenant des données exige une restauration contrôlée. Les publications, événements et PDF restent protégés par leurs six triggers.

Les serveurs de recette utilisent le vrai lifespan et les vrais profils configurés ; seuls les lanceurs de workers sont désactivés. Aucun routeur n’est injecté dans les helpers. Un nouveau WAV silencieux valide est importé avec transcription humaine fictive et adaptateur de synthèse simulé ; les validations réelles puis les restaurations sélective et globale précèdent la lecture HTML audio jusqu’à six secondes. Cette preuve porte sur le transport et le décodage, pas sur la qualité ASR.

Les contrôles HTTP du corpus conservé de 5 003 tâches et 100 jalons prennent au plus 51 ms sur cette machine ; la création concurrente et le refus obsolète prennent environ 40/21 ms. Ces mesures locales ne constituent pas une garantie sur le réseau. Les écrans à 390 et 650 px tiennent dans la largeur utile, avec clavier et lecteurs qualifiés. Le message hérité de l’activité des mails confond encore un refus administrateur 403 et une indisponibilité serveur pour un lecteur restreint : à reprendre lors de L9, sans élargir les droits.

**Livraison L4 — 6 octobre 2026 : cockpit et revue de lancement actifs sur Agent 8001.** Les dix projets historiques sont accessibles, les routes cockpit/RLP sont enregistrées et le schéma ERP est en version 8. L’activation conserve toutes les cellules contrôlées (ERP : 2 145 lignes / 17 759 cellules ; Brain : 13 144 lignes / 108 134 cellules), après sauvegarde coordonnée de 1 397 fichiers et restauration vérifiée sur une nouvelle copie. Les 57 chemins intégrés préservent 276 sources canoniques ; les sources du candidat correspondent aux sources qualifiées par 874 tests Python / 1 ignoré et 298 React, Ruff/TypeScript/build conformes. La navigation réelle confirme le cockpit et la création de revue disponible, sans données de test en production. ReportLab 4.5.1, déjà verrouillé dans les dépendances, est installé seul avec contrôle des empreintes dans le Python du serveur. Preuve : `.ui-preview/xpilot-l4/integration-1006-l4-v2/delivery-result.json`. L’objectif reste actif : L5–L9 sont à réaliser. XPilot/8000, les modules hérités et les données sont conservés ; aucun commit/push.
