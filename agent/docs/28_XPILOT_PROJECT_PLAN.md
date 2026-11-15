# Plan de reprise des fonctions projet XPilot dans Agent

**Périmètre corrigé à la demande de l’utilisateur — 7 octobre 2026.** La reprise automatique de tout XPilot est arrêtée. Ne pas développer pour le moment de nouveau parcours de signature, nomenclature/BOM, système de charge/ressources, collaboration, calendrier, qualité, REX ou clôture. Le CDC existant suffit : contrôle de fonctionnement uniquement, sans extension CDC/BE. L’assistance technique L6 ne démarre pas automatiquement dans cette demande réduite. Tous les modules et toutes les données déjà présents sont conservés. Les listes larges ci-dessous décrivent désormais le plan historique ; cette décision prévaut. Documents et L0–L4 restent actifs sur le serveur unique 8001 ; aucun lot exclu n’a été activé pendant ce travail.

**CDC existant vérifié, sans nouvelle fonctionnalité.** 40 tests de régression réussis ; 40 lectures HTTP200 sur les dix projets actifs. Le moteur canonique C:/Agent a traité le CDC fictif avec google/gemma-4-26b-a4b-qat : HTTP200, 17 éléments en65.27s, 17 preuves présentes dans leurs pages selon la règle existante (espaces/casse normalisés), zéro violation FK. Quatre avertissements UNIT_MISSING sont proposés à la revue. Essai isolé : aucune analyse de projet réel, modification canonique ou extension CDC/BE ; aucun redémarrage. Preuve : `.ui-preview/xpilot-l5/cdc-existing-verification-terminal.json`.

**Documents — téléchargement final et démarrage qualifiés, actifs sur Agent 8001.** Le téléchargement des copies de lot utilise la route protégée de l’artefact après vérification du nom, de la taille et du SHA-256 ; le serveur revérifie la copie et les droits à chaque lecture. Sur projet fictif, un lecteur a enregistré une copie de lot et un propriétaire une copie individuelle : les deux fichiers présents dans Downloads correspondent exactement à l’empreinte affichée ; sources et cellules ERP historiques conservées. 456 tests React, 17 tests API/worker, TypeScript et build passent. Les 280 sources Python/contrats restent identiques à la qualification complète 1688 réussis / 1 ignoré. Les lanceurs CMD activent le worker documentaire si AGENT_DOCUMENT_JOBS_ENABLED est absent, et respectent une valeur explicite telle que 0 ; lancement Windows sans fenêtre vérifié dans les deux configurations sur bases fictives. Les chemins réels des trames et des sorties restent à fournir/configurer et le partage SMB réel n’est pas qualifié. Aucune nouvelle fonction reportée ni modification de données réelles. Publication sélective sauvegardée ; build servi et 30 lectures HTTP vérifiés sur dix projets. Recette visuelle de la version active sans erreur console, worker disponible et besoin de configuration réseau visible. Aucun redémarrage ni écriture de base pendant cette publication ; aucun commit/push. Preuve : `.ui-preview/xpilot-l5/document-download-v1/delivery-result.json`.

**Notes activées sur Agent 8001 — ERP10.** Projet → Documents → Notes permet la saisie riche, les brouillons, l’historique, les pièces jointes et les imports explicitement choisis. Qualification complète : 1 688 tests Python réussis / 1 ignoré, 456 React, TypeScript, Ruff et build conformes ; 60 lectures HTTP sur dix projets et recette navigateur de consultation et rechargement sans erreur console. Le serveur part de C:/Agent ; les corrections récentes LLM/mémoire sont conservées. Avant migration : sauvegarde coordonnée du dernier état puis restauration sur copie neuve, 1 419 fichiers vérifiés. La migration préserve exactement les cellules historiques ; après redémarrage, les différences contrôlées concernent uniquement la progression technique du worker de jalons préexistant et l’horodatage du dernier signal Thunderbird. Le contenu de cet état hors last_seen et toutes les autres cellules Brain historiques sont identiques. Aucune note de recette créée dans les projets réels. Les chemins réseau des modèles et copies restent à fournir/configurer ; la préparation documentaire réelle sur SMB et son téléchargement final ne sont pas encore qualifiés. Tous les parcours exclus par l’utilisateur restent reportés. Aucun commit/push. Preuve : `.ui-preview/xpilot-l5/notes-erp10-integration-v1/delivery-result.json`.

**Historique UI — pièces jointes et import avec aperçu qualifiés dans le worktree, non activés.** L’écran ajoute copie explicite de pièces, association à la note et insertion des images gérées. L’import accepte des fichiers, le dossier complet d’une note XPilot ou une seule note choisie dans un lien du projet. Aperçu des versions, confirmation manuelle, explication des contenus incompatibles et choix explicite du texte simple ; aucun HTML source exécuté. Originaux, historique et auteurs source restent conservés ; Office demeure en consultation. Une commande exacte est conservée avant envoi ; POST `/notes/imports/replay` vérifie une confirmation sans réacquérir la source ni créer de doublon. GET `/notes/{id}/source` expose désormais le descripteur et l’inventaire des originaux. Recette navigateur sur données fictives : copies et image réellement enregistrées, imports réseau local et dossier multipart, 17 originaux vérifiés octet pour octet, téléchargement Office réel identique, rechargement et largeurs390/650 sans débordement ni erreur console. 456 tests React (18 cas de transfert),86 Python ciblés, TypeScript, Ruff et build passent. La suite Python complète de l’arbre courant, le démarrage protégé et l’activation Notes restent à terminer ; SMB réel et ouverture dans Office ne sont pas qualifiés. Les lots exclus restent reportés ; aucune base réelle, code canonique, module existant ou port8000 modifié, aucun commit/push. Preuve : `.ui-preview/xpilot-l5/notes-transfer-ui-qualified.json`.

**Historique avant transfert dans l’interface — édition, enregistrement et reprise qualifiés dans le worktree, non activés.** Documents reçoit un onglet Notes chargé à la demande ; les liens réseau et la préparation de documents restent accessibles. Liste recherchable/paginée et éditeur de contenu fermé : titres, cinq styles, liens sûrs, couleurs, alignements, listes/cases, tableaux et images gérées. Aucun HTML source ni image externe n’est rendu. Après une pause de saisie, la note existante est enregistrée avec un état visible ; la création reste explicite. Le brouillon local est isolé par projet/note/opérateur et les commandes exactes sont conservées avant envoi. Frappes pendant la sauvegarde, réponse perdue, rechargement, conflit et rejeu suivi d’une modification tierce conservent la saisie ; une création confirmée reste la même si le stockage local devient indisponible. Une capture locale illisible est conservée ; quota indisponible est annoncé, export et reprise sont proposés. Historique paginé avec aperçu, liaisons d’images courantes et restauration en nouvelle version ; pièces existantes téléchargeables, lecteur et Office en consultation. 438 tests React (dont19 Notes),73 Python ciblés, TypeScript/build et Ruff passent. Recette navigateur isolée : gras/cases/tableaux réellement persistés, restauration, conflit de deux opérateurs, lecture après rechargement, largeur390 sans débordement et fichier de brouillon réellement exporté. Ajout de pièces et import volontaire dans l’interface, consultation des originaux, qualification complète du backend, raccordement du démarrage et activation Notes restent à terminer. Aucun endpoint Notes enregistré sur8001, aucune base réelle modifiée, aucun lot exclu repris, commit/push ou suppression. Preuve : `.ui-preview/xpilot-l5/notes-ui-core-qualified.json`.

**Historique avant interface — transport Notes qualifié.** Le transfert v9 conserve toutes les versions, pièces (même non encore liées), images et originaux importés. Identifiants et liaisons courants sont remappés séparément ; captures, empreintes, acteurs et commandes historiques restent inchangés. Un double aller-retour est qualifié, également avec formulaires/lots documentaires et Brain. La préparation durable utilise des fichiers de notes neufs sans adopter les copies abandonnées ; échec SQL conserve les deux bases existantes et les pièces préparées. Les formats v2–v8 restent compatibles et refusent les tables de notes hors v9. La sauvegarde globale contrôle schéma, captures et fermeture binaire hors ligne avant restauration dans un dossier neuf ; elle conserve les originaux et gèle les anciennes commandes sans acquisition réseau ni import runtime. Lecture par note, indépendante de la limite d’un ZIP projet. 115 puis92 tests ciblés passent (groupes se recouvrant), Ruff conforme. La full1529 est historique et ne qualifie pas l’arbre courant. Interface/éditeur/autosave, recette complète, installation et activation Notes restent à faire. Aucun changement de C:/Agent, base de production ou frontend ; aucun lot exclu, commit/push ou suppression. Le périmètre corrigé le7octobre prévaut toujours. Preuve : `.ui-preview/xpilot-l5/notes-v9-global-qualified.json`.

**Historique avant raccordement v9/global — notes internes.** Acquisition réseau explicitement sélectionnée, contrat de graphe pur, référence courante de version restaurée et fermeture binaire des pièces/originaux sont implémentés dans le worktree. Le validateur hors ligne relit tous les originaux retenus en mémoire, recalcule les conversions et les titres source, vérifie MIME/images et refuse les historiques incomplets. 145 puis 142 tests ciblés passent, avec recouvrement ; Ruff conforme. La full1529/1 ignoré est historique et précède ces ajouts. Quatre tables/douze protections restent dormantes. Raccordement archivev9/sauvegarde globale, éditeur/autosave et activation restent à faire ; ils ne sont pas annoncés comme livrés. Aucune modification de C:/Agent, suppression, migration de production, opération XPilot8000 ou commit/push. Preuve : `.ui-preview/xpilot-l5/notes-network-history-binary-current.json`.

**L5.4 — import téléversé entièrement qualifié, encore dormant.** Session35232/PID17716 terminée exit0 :1529tests Python réussis/1ignoré,2165.89s, 263hashes produit/tests exacts, Ruff conforme. HTML effectif, images intégrées, capture source immuable, copies originales et reprise multipart sont inclus. Les46cas du prototype réseau et le contrat d’archive préparé restent séparés, hors de cette suite. Le processus est terminé : ne plus le reprendre/recréer. Raccorder réseau, références de restauration portables, archivev9/restauration globale et éditeur/autosave avant qualification finale/activation. Documents/ERP9 restent actifs sur8001, notes dormantes. L5.5–7 etL6–L9 restent au périmètre ; aucun changement canonique, suppression, commit/push. Preuve : `.ui-preview/xpilot-l5/notes-import-full-terminal.json`.

**L5.4 — acquisition réseau de notes préparée et qualifiée hors sources figées.** Trois fichiers de recette ajoutent sélection explicite d’un fichier HTML/TXT/MD/Office ou du dossier complet d’une seule note moderne depuis un lien de ce projet, avec racines et mappings serveur. Pas de recherche dans les autres projets ni d’import de base XPilot. Droits et lien sont vérifiés avant les probes ; handles Windows, identité native et vérification finale couvrent tous les fichiers et dossiers retenus. Jonctions/redirections, éléments inconnus, historique vide/incomplet, sources modifiées et quotas dépassés empêchent tout résultat partiel. La correction Windows utilise lstat frais plutôt que les métadonnées d’énumération en cache. Deux endpoints JSON de recette proposent aperçu et import ; la commande validée se rejoue même sans configuration réseau, avant acquisition. 46tests réussis, Ruff/diff conformes, sur liens et fichiers fictifs Windows ; SMB réel non qualifié. Le prototype reste dans `.ui-preview/xpilot-l5/notes-network-stage/`, hors des263sources inchangées de la full35232/PID17716 toujours en cours. Ne pas la relancer sur délai. Aucun endpoint réseau de note disponible sur8001. Raccordement, archivev9/restauration, éditeur/autosave, qualification et activation restent requis, ainsi que L5.5–7 et L6–L9. Aucun changement canonique, suppression, commit/push. Preuve : `.ui-preview/xpilot-l5/notes-network-stage46-progress.json`.

**Régression complète de l’import en cours : session35232, PID17716.** Les263sources produit/tests sont figées dans `.ui-preview/xpilot-l5/notes-import-full-running.json`. Conserver ce processus jusqu’au résultat terminal ; ne pas le relancer sur un délai d’observation. Le rapport attendu est `notes-import-full-python.xml`. Aucun résultat complet acquis, aucune activation des notes. Les anciennes sessions10312 et65938 sont terminées et ne doivent pas être reprises.

**L5.4 — import de notes implémenté en recette interne, encore dormant.** La conversion utilise le HTML effectivement sauvegardé par XPilot, conserve le JSON ancien parmi les originaux et couvre barré, cases, tableaux, images dataURI décodées et anciens fichiers HTML/TXT/MD. Quatre tables et douze protections SQL conservent contenu, versions, pièces et provenance. La sélection volontaire multipart propose aperçu, import et téléchargement des originaux sans rendu HTML ; tous les octets et toutes les versions déclarées sont copiés et vérifiés, sans extraction ni écrasement. Les auteurs source restent descriptifs ; les captures Agent portent l’opérateur serveur et les anciennes commandes de versions sont gelées. Une commande validée se rejoue avant acquisition, sans doublon ; annulation/échec conserve les copies et les retries ne les adoptent pas. Office reste en consultation, également protégé en SQL. Qualification ciblée : groupes de162 puis38cas réussis, se recouvrant, Ruff et diff conformes. Le résultat complet1408/1 ignoré concerne l’état précédent et ne qualifie pas ces ajouts. Acquisition réseau bornée, transportv9/restauration globale, éditeur/autosave, régression complète et activation restent à réaliser. Aucun endpoint notes/import enregistré sur8001 ; Documents/ERP9 restent actifs. Aucun changement canonique, suppression, commit/push. Preuve : `.ui-preview/xpilot-l5/notes-import-progress.json`.

**7 octobre 2026 — Documents L5.1–L5.3 activés sur Agent 8001, ERP9.** Catalogue, formulaires versionnés, préférences, lots et publication explicite sont raccordés ; le worker documentaire est actif (`AGENT_DOCUMENT_JOBS_ENABLED=1`). Les dossiers des trames et des copies restent à fournir/configurer : l’écran signale cette limite et les fichiers Office réels restent inaccessibles. Qualification : 1356 Python / 1 ignoré, 419 React, Ruff, TypeScript et build conformes ; 50 lectures HTTP sur dix projets et recette de consultation/rechargement sans erreur console. Sauvegarde coordonnée/restauration sur dossier neuf : 1397 fichiers vérifiés et 125896 cellules contrôlées. La migration conserve exactement les cellules historiques ; après redémarrage, seules vingt cellules de progression du worker de jalons préexistant changent, sans modification des données métier historiques. Le geste final de téléchargement navigateur et le partage SMB réel restent non qualifiés. L5.4–7 (notes, comptes, visas et recette complète) et L6–L9 restent à réaliser ; aucun commit/push. Preuve : `.ui-preview/xpilot-l5/integration-erp9-v1/delivery-result.json`.

Date : **5 octobre 2026**, suivi le **6 octobre 2026**. État : **objectif actif, L0 à L4 livrés sur 8001 ; L5–L9 à réaliser**.

L4 est livré : cockpit relationnel, RLP structurée, révisions et PDF figés, import de réunion local sourcé, restauration v6 et consultation des relations actuelles. Les migrations, recettes et conservation sont qualifiées sur copies ; le serveur unique 8001 et les dix projets historiques sont vérifiés. L5–L9 restent intégralement au plan.
Référence : [audit détaillé](27_XPILOT_PROJECT_AUDIT.md) et
[inventaire figé](27_XPILOT_PROJECT_INVENTORY.json).

L'utilisateur a demandé de lancer l'objectif le 5 octobre 2026. Le
[suivi d'exécution](29_XPILOT_EXECUTION.json) distingue les travaux préparés,
implémentés, testés et activés. Les contrats de reprise et de conservation sont
définis dans [L0 — contrats et migrations](29_XPILOT_FOUNDATION.md).
Le [socle L1](30_XPILOT_PROJECT_IDENTITY.md) et ses archives sélectives sont
qualifiés sur copies. Les contrôles HTTP et internes sont qualifiés dans le
mono-serveur. Fiche, équipe, historique et référentiels sont actifs dans
`C:\Agent` sur `8001`, après fusion préservant les corrections mails, recette
navigateur et migration sauvegardée. L2 poursuit jalons, tâches, modèles et
références sans réinitialiser les jalons et dates existants.
Le [socle L2](31_XPILOT_PROJECT_PLANNING.md) est actif sur `8001` : jalons,
tâches, workflow, modèles versionnés, références et historique. Les interfaces
et leurs conflits sont qualifiés, y compris à 390/650/1280 pixels. Les archives
v4 et la restauration globale sont vérifiées sur copies, puis la migration
préserve 14 033 lignes / 116 204 cellules et les dix projets historiques.
Qualification finale : 459 tests Python / 1 ignoré, 155 React, Ruff, TypeScript
et build. L3 poursuit catalogue, gates et versions des livrables ; L4–L9 restent
au périmètre. Aucun service supplémentaire ni modification d’XPilot 8000.
L'audit 27 reste une photographie de l'état avant ce démarrage, pas un état
d'avancement courant. Le choix d'interface **Menu latéral** est conservé.

## Résultat attendu

Une fiche projet complète dans Agent, couvrant les fonctions opérationnelles
actives d'XPilot et conservant la connaissance alimentée par les mails,
réunions et documents. Chaque livraison ajoute un parcours utilisable de bout
en bout : données, règles, API, interface, sauvegarde et recette.

Le périmètre financier reste exclu. Les six types de revues désactivés et le
tutoriel AppKD indisponible dans XPilot sont des extensions futures, pas des
fonctions déjà opérationnelles à recopier. Le découpage technique des
calculateurs Tubes est également un lot spécialisé ultérieur.

## Navigation cible

Conserver le menu global d'Agent et la bulle de redimensionnement de l'assistant.
Dans un projet, proposer des rubriques nommées et des sous-menus persistants :

| Rubrique | Sous-menus |
|---|---|
| Pilotage | Vue d'ensemble, cockpit, alertes, projets similaires |
| Planification | Jalons, tâches, références et écarts, planning et charge |
| Exigences & BE | Sources, revue Agent, synthèses versionnées, contrôles, transfert BE : demande/réponse/revue |
| Livrables | Catalogue/selection, checklists, versions, assistance, vérifications AF/AR, ACV |
| Atelier | Nomenclature : lignes/classification/fournisseurs, achats opérationnels, pointage et RAF heures |
| Réunions & revues | Réunions audio, RLP, décisions, actions, publications |
| Documents | Liens réseau, recherche, modèles et remplissage, notes, import TDAO opérationnel |
| Équipe | Membres et rôles, discussion |
| Clôture | Conditions de clôture, bilan et REX, archivage, réouverture |

Les rubriques actuelles restent accessibles pendant les ajouts. Éviter une barre
de 19 onglets : les fonctions gardent leur identité mais sont regroupées selon
le travail de l'utilisateur. Prévoir liens directs, retour à la liste, état
vide utile, commandes clavier et sauvegarde visible. Les actions supprimées du
portefeuille (actualiser / importer JSON) ne sont pas réintroduites.

## Ordre et dépendances

Tailles relatives : **S** = lot borné, **M** = plusieurs parcours, **L** = domaine
avec persistance, fichiers ou règles complexes. Ce sont des tailles de travail,
pas des durées garanties. L0 permet de transformer chaque lot en estimation
réaliste ; aucun calendrier arbitraire n'est fixé à partir du seul audit.

| Lot | Priorité | Taille | Dépendances | Livrable concret |
|---|---|---|---|---|
| L0 — Contrats et migrations | P0 | M | — | Mapping métier, sauvegarde/restauration et stratégie de compatibilité |
| L1 — Identité et équipe | P0 | M | L0 | Fiche complète, référentiels, rôles métier et portée d'accès |
| L2 — Jalons, tâches, modèles et écarts | P0 | L | L1 | Workflow structuré et comparaison de références |
| L3 — Livrables | P0 | L | L1, L2 | Catalogue, jalons, checklists, versions, transitions |
| L4 — Cockpit et revues | P1 | L | L2, L3 | Pilotage visuel, RLP et publication des réunions |
| L5 — Documents, notes et signatures | P1 | L | L1, L3 ; L4 pour signatures RLP | Manipulation locale contrôlée et versions documentaires |
| L6 — Assistance et vérifications techniques | P1 | L | L3, L5 ; contrat CDC existant | AF/AR/calcul/notice/ACV et constats validables |
| L7 — CDC & transfert BE complet | P1 | L | L2, L3, L5 | Révisions, gel, réponse BE, QA et émission |
| L8 — Atelier, BOM et charge | P1 | L | L1, L2, L3 | BOM versionnée, sourcing, RAF par lot et planning |
| L9 — Collaboration et fin de projet | P2 | L | L4, L5, L7, L8 selon fonction | Discussion, calendrier, qualité/Kaizen, similarité, clôture et REX |

Chemin recommandé : **L0 → L1 → L2 → L3 → L4 → L5 → L6 → L7 → L8 → L9**.
Après L3, certains travaux peuvent être menés indépendamment : l'atelier n'exige
pas d'attendre les vérifications documentaires. Cela n'implique pas de créer des
sous-projets ni des serveurs supplémentaires.

## Contenu et recette des lots

### L0 — Préparer une reprise réversible

- Figer les contrats d'identité et de relations projet/Brain ; relever les
  doublons et ambiguïtés sans les supprimer.
- Définir les extensions additives : référentiels, rôles, états, versions,
  relations, provenance et contrôle de concurrence.
- Définir les adaptateurs pour services XPilot et les règles que l'on peut
  reprendre telles quelles. Conserver les modules et routes Agent existants.
- Distinguer reprise de fonctionnalités et migration de données XPilot : aucun
  import de la base externe n'est implicite. Un import ultérieur sera simulé,
  tracé par identifiant externe et approuvé sur un bilan lisible.
- Établir corpus de recette autorisé, sauvegardes des deux bases/fichiers,
  restauration et compatibilité des archives JSON anciennes.

**Acceptation :** migration et retour à l'état précédent testés sur copies,
comptages et identifiants conservés ; aucune dépendance à MariaDB XPilot pour
faire fonctionner Agent ; liste des règles métier décidées et des contrats figés.

### L1 — Identité complète et équipe

- Client, agence, CAF, BU, famille, typologie, référence client/outillage,
  description, dates début/fin, standby et rôles métier.
- Référentiels légers dans Réglages ; personnes identifiées, recherche et
  synchronisation responsable/membre projet.
- Alignement ERP/Brain des droits, sans confondre responsabilité et visibilité.
- Réutiliser création manuelle/dossier, extraction correcte du code et
  rafraîchissement des listes/sélecteurs après mutation.

**Acceptation :** projet créé depuis `V:\06 - AIRBUS LT\AIRB26LTH0205-A - LED 2026`
conserve `AIRB26LTH0205-A` ; tous les sélecteurs voient le projet immédiatement ;
aucun projet existant ne perd un lien Brain ; un rôle lecteur ne peut modifier
les fonctions protégées ; date de fin antérieure au début rejetée.

### L2 — Jalons, tâches et références

- Codes stables et ordre des jalons ; modèle de 14 étapes configurable ; modèles
  par typologie avec révision, tâches et dates en jours ouvrés.
- Migration des 8 jalons Agent par propositions de correspondance ; aucun
  remplacement automatique du planning existant.
- États/commentaires/ordre, parents de tâches, responsable, priorité, début/fin,
  charge en heures et flags BE/fabrication ; listes filtrées et paginées.
- Références initiale/contractuelle/revue/avenant ; instantanés immuables et
  comparaison avant/après, sévérité, delta de charge.
- Préserver les propositions de dates d'Agent, historique et vérification des
  preuves au moment de l'acceptation.

**Acceptation :** un changement de modèle n'affecte pas un projet existant ;
cycle de tâches refusé ; date réelle et état ne sont pas confondus ; conflit
entre édition et proposition visible ; référence conservée après modification ;
archive/restauration préserve dates, preuves et relations.

### L3 — Livrables complets

Le [lot L3](32_XPILOT_PROJECT_DELIVERABLES.md) est qualifié et actif sur `8001`.
Catalogue/sélection, checklists/visas, versions/fichiers/historique et contrôles
des jalons sont disponibles. Le candidat fusionné passe 706 tests Python
(un ignoré), 267 React, Ruff, TypeScript et build. La sauvegarde complète de
1 397 fichiers a été restaurée sur copie ; la migration conserve les 2 098
lignes ERP et 13 144 lignes Brain contrôlées, avec zéro FK invalide. Les dix
projets historiques, les routes, le bundle et l'interface active sont vérifiés.
Preuve : `.ui-preview/xpilot-l3/integration-1006-v2/delivery-result.json`.
Les paragraphes suivants rappellent les étapes historiques de préparation.

Le socle L3 a été implémenté dans le worktree :
neuf tables additives, catalogue de onze types/67 points, commandes CAS,
checklists et visas par version, métadonnées séparées et raccordement CDC sans
régénération. Migration qualifiée sur copie de sauvegarde Agent : 14 033 lignes
et 116 204 cellules anciennes conservées, six protections immuables et zéro FK
invalide. Les archives et la restauration des fichiers sont raccordées dans le
worktree ; API/gates sont raccordés, UI et activation restent à réaliser. Le runtime `8001`
reste L2. Le périmètre L3–L9 ne change pas.
L3.2 complète les services de catalogue et composition des typologies avec CAS,
les lectures paginées, l'applicabilité des points conditionnels et la sélection
liée à un aperçu. L'adoption de fiches manuelles est explicite et conserve leurs
versions/checklists ; l'administration ne remplace pas les définitions déjà
utilisées. Le raccordement HTTP est réalisé dans L3.3 ; l'interface reste dans L3.5.
L3.4 implémente la restauration globale des fichiers : les versions et visas
immuables sont conservés, l'emplacement de lecture est relocalisé dans les
métadonnées de la copie, et les pièces sont vérifiées par projet/empreinte/taille.
L'ajout de cette colonne est sauvegardé avant DDL. L'archive sélective v5 conserve
la fermeture des dépendances, les fichiers et le remappage typé avant import.
Le contrat de validation/remappage v5 est désormais développé : types utilisés,
anciennes versions et compositions de typologie, personnes historiques,
visas et révisions partagées. Les manifests v2 conservent la publication v1
d'origine. Les services SQL d'export des dépendances et de réconciliation des
référentiels sont développés et testés sur bases fictives et copies historiques ;
le transport v5 est raccordé et ses parcours sont testés sur bases fictives et
copies historiques. L'activation complète L3 attend encore UI et
qualification du candidat fusionné.
L'adoption refuse les collisions de contrôle masquant un visa obligatoire, et
le contrat vérifie les snapshots de checklist avec les événements et resets de visa.
L3.3 ajoute les adaptateurs HTTP et l'acquisition de fichiers dans le worktree :
listes paginées et filtres, catalogue, sélection, versions, checklists, visas et
historique. Les commandes historiques et gates sont raccordés, les routers
sont enregistrés dans le candidat et le démarrage migre explicitement après
sauvegarde. Les parcours du mono-serveur sont testés sur copies ; aucune
activation de ce candidat sur `8001` à ce stade.

- Catalogue par typologie et livrables personnalisés ; rattachement aux jalons,
  checklist, gates, calcul d'avancement et statut documentaire.
- Versions et fichiers avec empreintes, métadonnées et manifestes ; édition des
  métadonnées sans réécriture d'une version publiée.
- Connexion des livraisons CDC existantes au catalogue, sans les recréer.

**Acceptation :** document généré ne devient pas automatiquement validé ; gate
obligatoire empêche une validation prématurée ; ancienne version reste lisible ;
fichier et métadonnées restaurables ; filtres et sélection restent cohérents.

### L4 — Cockpit et RLP

Livré le 6 octobre 2026 : [cockpit et RLP](33_XPILOT_COCKPIT_REVIEWS.md) actifs sur 8001 après qualification et restauration sur copies. Commandes partagées, révisions/PDF figés, transcription par interlocuteur et relations restaurées sont qualifiés. Validation : 874 tests Python / 1 ignoré, 298 React ; corpus mesuré de 100 jalons / 5 003 tâches / 2 500 livrables. Les modules et données hérités restent conservés.
- Cockpit alimenté par les mêmes agrégats ERP que portefeuille et planning :
  jalons, tâches, livrables, heures et alertes opérationnelles.
- Inspection, recherche, couches, actions ciblées et chargement indépendant.
- RLP structurée avec participants, vigilance, fonctions, contraintes,
  décisions et livrables ; publication PDF et révisions figées.
- Réinjecter la synthèse des réunions locales dans un brouillon de RLP, avec
  provenance et correction humaine. Prévoir catalogue extensible pour les
  revues encore désactivées dans XPilot, sans fausses commandes actives.

**Acceptation :** modification depuis l'inspecteur visible dans la liste ;
transcription accessible par interlocuteur ; synthèse proposée ne publie pas
seule ; RLP publiée immuable, nouvelle révision indépendante ; états de
chargement/erreur et navigation clavier vérifiés. Objectif de structure/actions
utilisables sous 1,5 s sur le corpus défini, à mesurer plutôt qu'à supposer.

### L5 — Documents, notes et signatures

- Service local de résolution/analyse des fichiers, racines autorisées et
  mappings de lecteurs ; opérations réseau distinctes des scans en lecture.
- Reprise des huit trames XPilot ; remplissage borné, aperçu, champs manquants,
  sélection par lot, progression, annulation et journal par fichier.
- Qualifier formats avec macros, signets et cellules. Distinguer bibliothèques
  de fichiers et automatisation Office ; préserver macros/trames, aucune
  exécution implicite. Reprendre uniquement les champs non financiers.
- Notes riches, brouillons, sauvegarde visible, pièces jointes et historique.
  Choisir la vérité documentaire Agent et un import volontaire des notes client.
- Signature interne : demande, signataires, éligibilité, refus, rappel,
  annulation, document final et audit. Les notifications externes nécessitent
  un canal et une action utilisateur explicites.

**Acceptation :** aucun chemin hors racine ; fichier existant non remplacé sans
choix explicite et sauvegarde ; reprise après arrêt ; note conservée après
fermeture ; document signé figé et empreinte vérifiable. Préparer les documents
sur copies avant toute écriture dans les dossiers d'affaires réels.

### L6 — Assistance métier

- AF depuis CDC avec aperçu/choix des domaines et preuves ; modèles AR, notice,
  ACV et note d'hypothèses de calcul.
- Vérifications AF/CDC et AR/AF/CDC avec sélection de versions, traitements
  durables, constats, gravités, décisions et validation humaine.
- Analyse ACV, mesures et résultats versionnés ; questionnaires Soudure/EXC
  depuis les livrables, sans leur attribuer une certification automatique.
- Brouillon destiné au vérificateur ; pas d'envoi automatique ; liens normatifs
  configurables et clairement indisponibles lorsqu'ils ne sont pas renseignés.

**Acceptation :** aucune validation avec constat critique non traité ; preuve
consultable ; analyse périmée signalée après changement de source ; timeout IA
et absence de modèle expliqués, travail manuel possible ; génération de
documents contrôlée structurellement et visuellement.

### L7 — CDC et transfert BE

- Étendre le moteur existant : révisions d'analyse et de transfert, transitions,
  contrôle de concurrence, gel et conservation des preuves.
- Transfert : demande client, réponse BE et revue/arbitrage ; matrice par
  exigence, réserves, heures, planning et capacité.
- Génération DOCX/PDF distincte de l'émission ; contrôles et QA bloquants,
  téléchargement de l'artefact exact émis.
- Préserver paramètres IA du Brain et comportement explicite des sources
  anciennes non analysables ; OCR éventuel comme extension qualifiée séparée.

**Acceptation :** source non approuvée bloque l'approbation du transfert ;
exigence non confirmée/non sourcée bloque son inclusion approuvée ; artefact
sans QA réussie non émis ; reprise de job après arrêt sans doublon ; sortie
financière absente, heures estimées conservées.

### L8 — Atelier et planification des ressources

- BOM importée/versionnée, sections, anomalies, classification, mémoire de
  décisions et sourcing fournisseurs ; maintenir les lignes manuelles.
- Référentiel Supply opérationnel, familles/capacités ; choix humain avec
  provenance de proposition ou choix manuel.
- Pointage Sage/manuels, périodes, détail par personne ; prévisions et RAF par
  lot, import TDAO en heures et aperçu de remplacement.
- Besoins d'achats sans prix ; charge/capacité, planning affecté et calendrier
  des ressources nécessaires aux tâches projet.

**Acceptation :** réimport identique sans duplication ; gros XLSX paginé et
borné ; décision humaine distincte de l'IA ; fournisseur manuel jamais présenté
comme recommandé ; heures Sage et manuelles comptées sans doublons ; nouveau
RAF par lot ne détruit pas la réestimation globale héritée.

### L9 — Collaboration, capitalisation et clôture

- Discussion humaine et notifications projet ; abonnements calendrier
  révocables avec identifiants d'événements stables.
- Raccordement qualité/Kaizen : tickets, actions, preuves, mesures et alertes ;
  capitalisation dans la connaissance avec lien vers l'objet métier.
- Similarité asynchrone réutilisant la couche d'embeddings d'Agent si adaptée,
  avec contrôle d'accès, invalidation et résultats conservés en base métier.
- Bilan/REX, conditions de clôture, traitement explicite des tâches ouvertes,
  date réelle, archivage et réouverture motivée.
- Adapter le contrôle dossier XPilot : une panne réseau ne doit ni prouver
  l'archivage ni annuler les tâches. Aucun déplacement/suppression implicite.

**Acceptation :** résultats similaires jamais inter-projets interdits ; aucun
message humain confondu avec réponse IA ; révocation calendrier immédiate ;
clôture conserve les dates prévues, bloque les conditions manquantes et ne
supprime aucun enregistrement ; motif de réouverture tracé.

## Contrôles à chaque livraison de code

1. Tests de comportement ciblés puis contrôles imposés :
   `python -m pytest tests/ -q` et `ruff check app backend/app tests`.
2. Tests React appropriés, TypeScript/build et recette des parcours concernés.
3. Migration sur copies et restauration, contrôle des identifiants existants,
   archives anciennes et nouveaux fichiers.
4. Performance mesurée sur le corpus ; pagination, états de progression et
   erreurs ; vérification visuelle claire/sombre et navigation clavier.
5. README, README_BACKEND, documentation du domaine et manifest mis à jour.
6. Activation sur **8001** seulement, vérification santé des deux bases et du
   chargement de la version ; XPilot **8000** préservé.

La livraison d'audit précédente était documentaire. À partir du démarrage de
l'objectif, les contrôles ci-dessus s'appliquent aux lots de code. Rien n'est
commité ou poussé sans demande explicite.

## Première étape à exécuter

Commencer par **L0 puis L1** : figer les relations et la migration, puis enrichir
la fiche projet et l'équipe. Le premier jalon de livraison est un projet créé,
édité et visible partout, avec identité et rôles persistants, sans perte de
données ni retour de la finance. L2 poursuit ensuite le besoin déjà exprimé sur
les jalons et leur alimentation depuis les sources.

## Avancement L2 — archives qualifiées

Les modèles, références figées et archives portables v4 sont qualifiés dans le
worktree : restauration typée ERP/Brain, historique, dépendances sélectives et
compatibilité v2/v3. La recette sur copies conserve 13 170 lignes / 109 127 cellules
après préparation du projet fictif ; la paire sauvegardée source reste identique.
427 tests Python réussissent (1 ignoré), Ruff est conforme. L2.1 à L2.4 sont
qualifiés côté backend ; L2.5 et L2.6 restent à réaliser. Le serveur actif demeure
sur L1. Le périmètre L0 à L9 et ses critères de livraison restent inchangés.

## Avancement L2 — premiers écrans qualifiés

L2.5 est en cours : Jalons et Tâches disposent de listes paginées, formulaires
complets, sélecteurs recherchables et conflits conservant les brouillons. La
recette navigateur sur bases fictives valide la création et l’actualisation,
la pagination, les charges de groupe et deux modifications concurrentes.
429 tests Python réussissent (1 ignoré), 127 tests React, Ruff, TypeScript et
Vite sont conformes. Modèles, Références figées, Historique et recette responsive
restent à compléter. Le serveur `8001` reste sur L1 ; L2.6 et les lots L3–L9
restent à réaliser.

## Avancement L2 — références et historique

Les références capturent les jalons/tâches complets ; nom, commentaire et
archivage sont modifiables par événements immuables sans changer l’instantané.
La comparaison et le journal exposent révisions, opérateur, avant/après, sources,
sévérités, filtres, pagination et delta de charge sans double comptage.
La recette des archives sur copies conserve 13 171 lignes / 109 135 cellules
après préparation ; les fichiers source restent identiques. Les tests comptent
436 réussites Python / 1 ignoré et 139 réussites React.

Le contrôle de fidélité à XPilot a relevé que sa référence capture également
les dates de début/fin et budget heures du projet. Ce complément opérationnel
n’est pas encore dans les instantanés Agent ; L2.4 est donc remis en cours.
Modèles UI, ce complément, la recette responsive et activation L2.6 restent
à réaliser. Le périmètre L0–L9 demeure actif, sans finances ni suppression.

## Avancement L2 — engagements projet (suite)

Le complément de L2.4 est qualifié : les captures v2 incluent début, fin
prévisionnelle et budget d’heures enregistré du projet. Les comparaisons et le
journal distinguent ces engagements de la charge des tâches. Une date de fiche
modifiée invalide la révision commune une fois les protections L2 installées.
Les références v1 restent lisibles, exportables et restaurables ; leurs valeurs
projet absentes ne sont pas inventées. Les archives sur copies préservent
13 176 lignes / 109 185 cellules après préparation, les deux fichiers source et
le projet original. Suite : 457 tests Python / 1 ignoré, 142 React, Ruff,
TypeScript et build conformes. L2.4 est terminé dans le worktree ; L2.5 reste en
cours pour Modèles et recette responsive ; L2.6 n’est pas activé. 8001 reste L1,
le port 8000 est intact et le périmètre L3–L9 reste actif.

## Avancement L2 — Modèles et recette responsive

L2.5 est qualifié dans le worktree : catalogue/version/édition structurée,
préparation explicite, correspondances paginées et aperçu lié à la révision.
Publier v1/v2 ne touche pas au projet ; l’application volontaire de v1 puis v2
préserve les tâches manuelles, dates, sources et engagements. La mise à jour des
tâches issues du modèle reste désactivée par défaut. Avec choix explicite, 8 →
12 h donne +4 h, sans double compte du groupe. Les six vues Planning et leurs
formulaires/écarts sont vérifiés à 390 pixels ; Modèles et la navigation sont
aussi vérifiés à 650 et 1280. Les tableaux défilent dans leur propre conteneur.
Suite : 458 Python / 1 ignoré, 155 React / 28 fichiers, Ruff, TypeScript et build
conformes. L2.6 reste à réaliser : candidat canonique, qualification globale,
sauvegarde/restauration puis activation 8001. L3–L9 restent au périmètre actif.

## Livraison L2 — activation globale terminée

Le candidat fusionné préserve 194 fichiers canoniques hors L2, dont les corrections
mails. 56 chemins sont livrés avec sauvegarde du code, des anciens bundles et de
l’état géré complet. Restauration sur copie : 1 388 empreintes vérifiées,
14 033 lignes / 116 204 cellules contrôlées, zéro changement inattendu/violation FK.
Migration additive : 7 tables et 6 triggers immuables, données préexistantes
conservées. Vérification API en lecture sur les dix projets et recette visuelle
sur 8001 ; aucun projet/modèle de test créé en production. Le complément de tri
des jalons historiques et alias est qualifié (459 Python / 155 React) et dispose
de sa sauvegarde de code. L2.1–L2.6 sont terminés ; l’objectif reste actif pour
L3–L9. Les mentions d’attente des étapes précédentes sont historiques.

## Avancement L4.4 — contrat de restauration préparé

Le contrat typé de RLP et la migration additive de correspondances ERP/Brain sont
qualifiés sur bases fictives. Publications, PDF et journal restent inchangés ;
les dépendances documentaires et transcriptions historiques sont contrôlées.
Vingt remappages successifs ne produisent aucune origine imbriquée ni modification
de texte. La copie du corpus UI conserve 17 737 lignes / 146 808 cellules ERP et
le Brain exact, avec les deux colonnes ajoutées et les six protections intactes.

L4.4 reste **en cours** : transport sélectif v6, dépendances historiques et import
coordonné sont qualifiés dans le worktree ; la lecture API/UI des correspondances
et la recette finale restent à terminer.
L4.5, L4.6 et le périmètre complet L5–L9 restent au plan. L0–L3 seuls sont actifs
sur 8001 ; ni port 8000, ni processus de recette, ni données utilisateurs modifiés.

Transport sélectif RLP v6 qualifié dans le worktree : **863 tests Python / 1 ignoré et 327 tests ciblés**, Ruff conforme. Les erreurs et arrêts de processus préservent les deux bases ; les pièces préparées restent journalisées. Une restauration globale sur copie conserve les publications et relocalise seulement les chemins mutables. Preuve : `.ui-preview/xpilot-l4/review-transport-result.json`. Les correspondances API/UI et l’activation restent à terminer ; L4.4 et l’objectif L0–L9 restent en cours, L0–L3 seuls actifs sur 8001.

Correspondances RLP/restauration qualifiées dans le worktree : **865 tests Python / 1 ignoré, 9 cas API ciblés et 298 React**, Ruff, TypeScript et build conformes. Les publications et événements exposent leurs correspondances séparément des captures ; l’interface conserve les titres/citations et ouvre les livrables/réunions actuels du projet restauré. Recette clavier, lecteur et mobile sur une nouvelle copie, avec bases exactes après consultation. Preuve : `.ui-preview/xpilot-l4/review-links-result.json`. L4.4 est qualifié sur copies ; L4.5/L4.6 et L5–L9 restent à réaliser, L0–L3 seuls actifs sur 8001. Aucune activation, migration canonique, suppression de données ni commit/push dans cette étape.

Raccordement L4.5 qualifié dans le worktree : **874 tests Python / 1 ignoré, 22 cas ciblés et 298 React**, Ruff, TypeScript et build conformes. Le serveur unique enregistre cockpit/RLP et installe le schéma ERP v8 avec préflight et sauvegarde commune. Un groupe de tables de revue partiel contenant des données est refusé avant toute DDL. Le démarrage à froid sur les dix projets historiques conserve toutes les cellules ; le second lancement est neutre et le retour à la sauvegarde est qualifié sur copie. La recette globale native/restaurée couvre PDF figé, audio WAV décodable, droits lecteur, clavier, mobile et concurrence avec conservation de saisie. Les lectures gardent les deux bases exactes ; les seules quatre cellules préexistantes modifiées pendant les commandes de recette appartiennent au brouillon fictif et à sa révision projet. Preuve : `.ui-preview/xpilot-l4/review-registration-result.json`. La précision de reconnaissance vocale n’est pas évaluée par cette recette fictive. L4.6 et L5–L9 restent à réaliser ; L0–L3 seuls actifs sur 8001. Aucun commit/push ni suppression.

**Livraison L4 — 6 octobre 2026 : cockpit et revue de lancement actifs sur Agent 8001.** Les dix projets historiques sont accessibles, les routes cockpit/RLP sont enregistrées et le schéma ERP est en version 8. L’activation conserve toutes les cellules contrôlées (ERP : 2 145 lignes / 17 759 cellules ; Brain : 13 144 lignes / 108 134 cellules), après sauvegarde coordonnée de 1 397 fichiers et restauration vérifiée sur une nouvelle copie. Les 57 chemins intégrés préservent 276 sources canoniques ; les sources du candidat correspondent aux sources qualifiées par 874 tests Python / 1 ignoré et 298 React, Ruff/TypeScript/build conformes. La navigation réelle confirme le cockpit et la création de revue disponible, sans données de test en production. ReportLab 4.5.1, déjà verrouillé dans les dépendances, est installé seul avec contrôle des empreintes dans le Python du serveur. Preuve : `.ui-preview/xpilot-l4/integration-1006-l4-v2/delivery-result.json`. L’objectif reste actif : L5–L9 sont à réaliser. XPilot/8000, les modules hérités et les données sont conservés ; aucun commit/push.

**Étape L5 — 2026-10-06 : moteur documentaire qualifié dans le worktree.** Les huit trames XPilot disposent d’un catalogue non financier, d’un aperçu borné et d’une préparation de copie en mémoire liée à l’empreinte source. Les styles, signets, namespaces, commentaires et contenus hors cible, dont les parties VBA, sont conservés ; aucune macro ni application Office n’est exécutée. Qualification : **938 tests Python / 1 ignoré, 64 cas ciblés**, Ruff conforme. Les paquets de recette sont fictifs, dont une feuille de 3 000 lignes ; le rendu Office et les trames réelles restent à qualifier. Contrats et suite du lot : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md`. Preuve : `.ui-preview/xpilot-l5/document-packages-result-v2.json`. Aucune route HTTP/UI, migration, activation, écriture réseau ou modification de données de production dans cette étape. L0–L4 seuls restent actifs sur 8001. L5 reste en cours : acquisition contrôlée, valeurs projet, traitements durables, notes, identité des signataires, visas, interface et activation sont à réaliser ; L6–L9 restent au plan. Aucun commit/push ni suppression.

**Étape L5.2 — 7 octobre 2026 : acquisition et champs documentaires qualifiés dans le worktree.** Le nouveau service lit uniquement un lien du projet dans les racines documentaires autorisées, avec mappings de lecteurs explicites et vérification du handle Windows et de la stabilité du fichier. Les champs d’identification sont sourcés depuis le projet, le client et le responsable ; les corrections restent limitées à une copie documentaire et ne changent aucune fiche. Qualification : **975 tests Python / 1 ignoré, 101 cas ciblés**, Ruff conforme. Les dossiers, fichiers et projets de recette sont fictifs ; une vraie jonction Windows vers un autre projet est refusée, comme un fichier changé pendant lecture. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-files-v2-result.json`. Aucune route HTTP/UI, migration, activation, écriture réseau, modification de données de production ou commit/push dans cette étape. L0–L4 seuls restent actifs sur 8001. L5 reste en cours : découverte des modèles, API, traitements durables, notes, comptes/signataires, visas, interface et activation ; L6–L9 restent au plan.

**Étape L5.3 — 7 octobre 2026 : parcours documentaire interactif qualifié dans le worktree.** L’onglet Documents ajoute « Préparer un document » à côté des liens réseau hérités : choix manuel parmi huit trames, lien du projet et fichier relatif, champs sourcés et corrections propres à la copie, aperçu des valeurs existantes/proposées, relecture puis téléchargement vérifié. Les trois routes sont enregistrées dans le serveur Agent unique ; seul l’aperçu POST est accessible au lecteur. La préparation lie trame, lien et données métier par empreinte et relit les références dans une connexion fraîche pour détecter les changements pendant acquisition ou préparation. Qualification : **1006 tests Python / 1 ignoré, 31 cas API, 328 tests React dont 30 ciblés**, Ruff, TypeScript et build conformes ; recette navigateur éditeur/lecteur, clavier et mobile avec téléchargement réellement enregistré. Les 16 trames fictives et les données ERP restent inchangées. Usage et limites : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuves : `.ui-preview/xpilot-l5/document-api-v2-result.json` et `.ui-preview/xpilot-l5/document-browser-recipe.json`. Pas d’activation L5 sur 8001 ni de commit/push. Les copies sont téléchargées sans reçu persistant ni écriture réseau. Découverte, lots durables, stockage Agent, publication explicite, notes, comptes et visas restent à intégrer ; L5 demeure en cours et L6–L9 restent au périmètre.

**L5.3 — découverte contrôlée des trames, 7 octobre 2026.** Documents ajoute une recherche en lecture dans le lien projet explicitement sélectionné : mots de dossier/nom et indice expliqués, exclusions, limites visibles et choix manuel en cas d’ambiguïté. Le fichier choisi passe ensuite par le même aperçu contrôlé. Le lecteur peut chercher et consulter ; préparer reste réservé aux personnes autorisées à modifier. Aucun lien créé, source modifiée ou modèle Office exécuté. Qualification : **1051 tests Python / 1 ignoré, 341 tests React dont 43 ciblés**, Ruff, TypeScript et build conformes ; recette navigateur sur 18 trames fictives conservées, clavier, lecteur et mobile. La molette défile dans la liste des candidats sans déplacer la page, qui ne déborde pas horizontalement. Contrat et limites : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-discovery-result.json`. Worktree seulement : L0–L4 restent actifs sur 8001. Les règles sont celles du catalogue ; préférences persistantes, jobs reprenables, artefacts, publication, notes et visas restent au périmètre de L5. L6–L9 et l’objectif complet restent en cours ; aucun commit/push.

**L5.3 — socle de persistance documentaire, 7 octobre 2026.** Les préférences des huit trames et le formulaire par projet/document disposent de révisions indépendantes, d’un historique immuable et d’une restauration qui ajoute une version. Deux sauvegardes concurrentes ne peuvent écraser la même révision. L’installation explicite des quatre tables et huit protections impose un préflight et une sauvegarde préalable ; le démarrage ERP reste en version 8 et ne les installe pas. Qualification : **1094 tests Python / 1 ignoré, 43 cas de persistance**, Ruff conforme. Sauvegarde SQLite relue dans un nouveau dossier et cellules historiques fictives conservées. Aucun changement React dans cette étape ; les sources du dernier contrôle frontend restent identiques. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-forms-v3-result.json`. Socle interne dans le worktree : raccordement HTTP/UI, archives projet typées L5, jobs, artefacts, publication, notes, comptes et visas restent à intégrer. Une archive antérieure refuse les données documentaires persistantes pour éviter leur perte. L0–L4 seuls restent actifs sur 8001 ; objectif actif, L5–L9 en cours, aucun commit/push.

**L5.3 — archives documentaires, 7 octobre 2026.** L’archive projet v7 conserve les formulaires et toutes leurs versions, y compris les sélections de liens disparus. Les identifiants courants sont remappés séparément ; snapshots, textes, acteurs et empreintes restent intacts. Les préférences communes restent celles de la destination. La restauration globale vérifie schéma, protections et journaux en lecture seule avant de créer le dossier de sortie, sans initialiser le moteur. Qualification : **1135 tests Python / 1 ignoré**, Ruff conforme ; 41 cas ciblés archive/sauvegarde. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-archives-result.json`. Le serveur Agent unique 8001 conserve L0–L4. HTTP/UI persistants, jobs, artefacts, publication, notes, comptes, visas et L6–L9 restent à intégrer ; objectif actif, aucun commit/push.

**L5.3 — formulaires et réglages HTTP/UI, 7 octobre 2026.** Les choix de trame, lien, chemin relatif et corrections se sauvegardent par projet/document avec historique paginé et restauration ajoutant une version. Les conflits conservent la saisie ; comparer et charger la version serveur sont deux actions distinctes. Réglages → Documents permet au propriétaire sans restriction de configurer les recherches des huit trames ; les règles enregistrées s’appliquent aux projets. Qualification : **1154 tests Python / 1 ignoré**, **355 tests React**, Ruff, TypeScript et build conformes. Recette réelle sur copies fictives : 18 sources intactes, cinq versions de formulaire, trois versions de réglages, droits et conflits vérifiés. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md`. Recette mobile non validée : l’outil conserve la largeur 1280 malgré son annonce de redimensionnement. Le serveur unique Agent 8001 conserve L0–L4 ; cette étape L5 n’est pas activée. Jobs, artefacts, publication explicite, notes, comptes/visas et L6–L9 restent à intégrer. Aucun commit/push.

**L5.3 — transport des lots documentaires v8 raccordé dans le worktree.** L’archive individuelle conserve les six tables de lots et leurs fichiers validés, remappe les références courantes et garde les captures, auteurs et anciens journaux intacts. Les lots importés restent suspendus ; le réexport/réimport et la sauvegarde globale sont vérifiés sur copies. 24 cas v8, 64 cas finaux archive/sauvegarde/file et un groupe de 51 cas archive/worker/HTTP/sauvegarde et 135 cas de compatibilité passent ; ces groupes se recouvrent. Ruff conforme. Interface de file, publication explicite et qualification complète restent à terminer avant activation. Le serveur unique Agent 8001 conserve L0–L4 ; L5–L9 restent en cours. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-jobs-archive-focused.json`. Aucune migration de production, suppression, commit ou push.

**L5.3 — interface des lots documentaires qualifiée dans le worktree, 7 octobre 2026.** Documents permet de réunir jusqu’à huit trames relues, de conserver une commande après réponse perdue, et de consulter compteur par fichier, copies et journaux. Arrêt et reprise utilisent la révision lue ; interrompre l’attente conserve la soumission incertaine. Les volets masqués cessent leurs lectures. **398 tests React**, dont un groupe de **71 cas Documents**, TypeScript/build et Ruff conformes. Recette navigateur réelle : deux fichiers, progression 0/2 puis 2/2, rechargement et clavier, droits lecteur ; 18 sources et 129 cellules historiques conservées. Les octets téléchargés par HTTP sont vérifiés ; l’enregistrement final du lien Blob par le navigateur et la recette mobile restent non qualifiés. La publication réseau, la qualification Python complète et l’activation sont à terminer. Agent unique 8001 conserve L0–L4, L5–L9 restent en cours. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuves : `.ui-preview/xpilot-l5/document-jobs-ui-frontend.json` et `document-jobs-ui-browser.json`. Aucune migration de production, suppression, commit ou push.

**L5.3 — aperçu de publication et IO ancrée qualifiés sur copies.** L’aperçu lie une copie validée à un lien du projet, un dossier existant et une empreinte de destination. Les racines d’écriture sont distinctes des racines de lecture. Les créations exclusives et le renommage dans le parent du handle ouvert refusent les collisions et les jonctions ; la reconnaissance après coupure compare identité persistante, taille et SHA, sans adopter un fichier seulement identique. **125 tests ciblés**, dont 42 nouveaux cas IO/aperçu, et Ruff conformes. La commande durable de publication et son interface restent à raccorder ; aucune écriture réseau réelle ni activation sur 8001. Le frontend du précédent contrôle 398 React/TypeScript/build reste inchangé. Le partage SMB réel et la branche Linux ne sont pas qualifiés. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-publication-destination-focused.json`. L0–L4 seuls actifs sur Agent 8001, L5–L9 restent en cours ; aucun commit/push ou suppression.

**L5.3 — publication durable sans remplacement qualifiée dans le worktree, 7 octobre 2026.** L’API enregistre l’intention avant la création exclusive, le reçu préparé avant le renommage, puis le succès après vérification du fichier final. Répéter la même commande vérifie identité persistante, taille et SHA sans recréer les octets ; sans reçu préparé durable, le candidat reste conservé pour inspection. Un verrou OS distinct sérialise les publications. Archives v8 et restauration globale conservent captures et acteurs, remappent les liaisons courantes et bloquent tout rejeu. **168 tests ciblés**, puis **35 cas commande/transport** sur la réponse finale (groupes se recouvrant), et Ruff conformes. Le frontend du contrôle précédent reste inchangé. Remplacement choisi avec sauvegarde, interface de publication et qualification commune restent à terminer avant activation. L0–L4 seuls actifs sur Agent 8001 ; L5–L9 restent au périmètre. Aucun partage métier écrit, aucune migration de production, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/document-publication-commands-focused.json` ; détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md`.

**L5.3 — remplacement documentaire avec sauvegarde conservée qualifié dans le worktree.** Le choix explicite lie la publication à l’identité, la taille et au SHA de l’original. Une intention de sauvegarde est enregistrée avant son déplacement ancré, puis le reçu de sauvegarde avant la publication de la copie préparée. Les coupures reprennent la même commande sans recréer les octets ; collisions et fichiers modifiés restent conservés. Le contrat v2 garde la lecture des historiques v1. 189 cas de régression et un cas HTTP supplémentaire passent, ainsi que Ruff. Double import v8 et restauration globale restent suspendus, avec reçus de sauvegarde intacts. Interface de publication et résolution explicite des intentions incertaines restent à intégrer, puis qualification commune et activation. L0–L4 seuls actifs sur 8001 ; L5–L9 en cours. Aucune écriture métier, migration de production, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/document-publication-replacement-focused.json`.

**L5.3 — interface de publication et clôture des intentions incertaines, 7 octobre 2026.** Documents permet de choisir la destination, relire, publier ou remplacer avec sauvegarde, puis consulter les reçus de chaque copie. Après réponse perdue, la commande exacte mémorisée est répétée ; une intention sans reçu préparé peut être clôturée explicitement en conservant tous ses fichiers. Droits lecteur, journaux historiques v1 et transport/restauration suspendus sont préservés. Qualification : 419 React, TypeScript, build et Ruff conformes ; 1345 tests Python / 1 ignoré, sortie 0. Recette réelle sur fichiers fictifs : création et remplacement, rechargement, lecteur et clavier, 18 trames intactes et identité de l’original sauvegardé conservée. Débordement des sélecteurs corrigé et vérifié à 390 px. L’enregistrement final du téléchargement Blob et le partage SMB réel restent non qualifiés. Activation L5 sur 8001 encore à réaliser ; L0–L4 seuls y sont actifs, L5.4–7 et L6–L9 restent au plan. Aucune suppression de données, migration de production, écriture métier, commit ou push. Preuve : `.ui-preview/xpilot-l5/publication-ui-common-checks.json`.

**Résultat final de la qualification Python L5.3.** Le même processus 47559 termine avec 1345 tests réussis / 1 ignoré, sortie 0 en 1473.15 s. Les sources du contrôle UI/publication restent identiques. Avec 419 React, TypeScript/build et Ruff conformes, la qualification commune passe ; téléchargement final du navigateur et activation sauvegardée sur 8001 restent à réaliser. L0–L4 actifs, L5–L9 en cours ; aucun commit/push. Preuve : `.ui-preview/xpilot-l5/publication-ui-python-full-terminal.json`.

**L5.3 — raccordement du démarrage ERP9 qualifié sur copies.** Le démarrage explicite valide les deux groupes documentaires avant toute DDL, installe quatre tables de formulaires et six tables de lots avec vingt protections après une sauvegarde commune, puis enregistre ERP9. Imports et création générique ne remplacent pas les installateurs. Aucun formulaire, réglage ou lot n’est créé implicitement. Onze cas de démarrage passent, ainsi que les régressions déjà exécutées et Ruff ; la suite complète du raccordement continue sur la session 12398. La qualification précédente du parcours de publication termine à 1345 Python / 1 ignoré et 419 React. Sur snapshots actuels, les dix projets et 125896 cellules historiques sont conservés ; HTTP et second démarrage sont neutres. Le candidat conserve 377 fichiers canoniques et vérifie l’équivalence de 409 sources produit/tests. Deux écarts de fichiers racine sont explicitement revus : aucun pin/hash existant retiré, une notice de provenance ajoutée. Régression complète, sauvegarde/restauration coordonnée, activation et vérification sur 8001 restent à terminer. Le geste final de téléchargement navigateur et le SMB métier restent non qualifiés. L0–L4 seuls actifs, L5.4–7 et L6–L9 restent au plan ; aucune écriture canonique, suppression de données, opération XPilot8000, commit ou push. Preuve : `.ui-preview/xpilot-l5/erp9-registration-progress.json`.

**Régression complète du raccordement ERP9 terminée.** Le processus12398 termine avec 1356 tests Python réussis / 1 ignoré, sortie0 en 1496.34s ; rapport JUnit et sources vérifiés. Le démarrage et la conservation des données sont déjà qualifiés sur copies, ainsi que Ruff et le frontend inchangé (419 React/TS/build). Sauvegarde/restauration coordonnée et activation vérifiée sur8001 restent à réaliser ; le téléchargement final navigateur reste non qualifié. L0–L4 actifs, L5–L9 en cours, aucun commit/push. Preuve : `.ui-preview/xpilot-l5/erp9-full-python-terminal.json`.

**L5.4 — socle notes et recette HTTP dans le worktree, 7 octobre 2026.** Trois tables et neuf protections SQL conservent notes, versions et références de pièces ; le contenu structuré fermé couvre texte mis en forme, titres, listes/cases, tableaux et références d’images gérées. Création/édition/restauration utilisent une commande stable et une révision ; réponse perdue et concurrence n’ajoutent pas de doublon. Les captures, acteurs et reçus sont immuables ; seul le gel monotone d’une ancienne commande est autorisé pour la restauration. L’historique HTTP est paginé en métadonnées, avec lecture séparée d’une version. 37 cas notes/core/HTTP et Ruff passent ; 244 régressions archives/sauvegardes passent (groupes se recouvrant ; les derniers ajouts du service notes sont couverts par les 37 cas actuels). Sur snapshots des dix projets actuels, démarrage, lectures et refus de création conservent exactement les bases, sans table/ligne de note, backup implicite ou worker ; ERP reste en version9. Suite complète en cours sur65938 (PID30844, JUnit notes-core-full-python.xml). Frontend inchangé, précédent contrôle419 React/TS/build. Les API ne sont pas enregistrées sur le serveur actif ; éditeur/autosave, stockage réel des pièces, import XPilot et transport v9/restauration globale restent à réaliser. Les anciens transports refusent provisoirement les notes peuplées avant sortie, au lieu d’omettre leurs historiques ; ce refus sera remplacé par le transport complet. L0–L4 et le socle Documents restent actifs sur8001 ; notes, comptes, visas et L6–L9 restent en cours. Aucun changement applicatif canonique, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-core-progress.json`.

**L5.4 — pièces jointes de notes en recette, 7 octobre 2026.** Le worktree ajoute stockage géré et API multipart interne : 5 Mio par fichier, 20 pièces/25 Mio par note, copies sans écrasement, empreinte contrôlée et réponse perdue rejouée sans nouveau fichier. Les copies non validées en base restent conservées. PNG/JPEG/WebP sont décodés et bornés (image statique, 16 millions de pixels) avant aperçu ; Office et autres formats restent des téléchargements, avec noms sûrs et en-tête nosniff. 15 tests fichiers/HTTP et Ruff passent. La suite complète65938 signale des échecs : une fixture v5 ajoutait les tables dormantes de notes à un ancien format. La correction garde le validateur strict ; 100 cas v5/core passent (groupes se recouvrant). La suite complète lancée avant cette correction et ces ajouts ne qualifie pas l’arbre courant ; laisser son processus terminer puis contrôler le résultat et lancer une qualification du nouvel état. Aucune API de notes/pièces n’est enregistrée sur8001. Import volontaire XPilot/Office, transportv9/restauration globale, éditeur/autosave et activation restent à réaliser. Documents restent actifs ; racines réseau réelles attendues. Aucun changement canonique, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-files-progress.json`.

**L5.4 — résultat terminal de la régression initiale.** Session65938 terminée : 1335 tests réussis, 58 échecs, 1 ignoré ; les échecs concernent les fixtures v5 de contrat/store, qui ajoutaient les tables dormantes de notes à un ancien format. La correction est qualifiée par100 tests ciblés ; 15 cas fichiers/HTTP passent également. Ce résultat initial ne qualifie pas le code corrigé ni les pièces ajoutées ensuite ; une nouvelle suite complète est requise. Aucune activation des notes, modification canonique, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-initial-full-terminal.json`.

**L5.4 — nouvelle qualification complète lancée.** Après le résultat terminal65938 et la correction des fixtures v5, la suite de l’arbre courant utilise session10312 (PID30592), rapport `notes-corrected-full-python.xml`. Sources figées dans `.ui-preview/xpilot-l5/notes-corrected-full-running.json` ; ne pas arrêter/recommencer ce processus sur un simple délai d’observation. Résultat encore en cours, pas une qualification complète acquise. Import/transport/éditeur et activation des notes restent à réaliser ; Documents restent actifs sur8001. Aucun changement canonique ni commit/push.

**L5.4 — import volontaire préparé hors sources figées.** Prototype de recette dans `.ui-preview/xpilot-l5/notes-import-stage/` : conversion TipTap fermée, aperçu des fichiers explicitement sélectionnés, empreinte source et empreinte de la décision, historique complet déclaré contrôlé, repli texte choisi explicitement. Les blocs/styles non représentables bloquent l’import riche ; aucune URL d’image n’est téléchargée. Les acteurs source restent des descriptions, et les auteurs historiques absents ne sont pas inventés. Un conteneur indépendant conserve tous les octets sélectionnés (JSON/html/txt, versions, pièces), sans extraction et avec inventaire vérifié. Office reste en consultation/téléchargement. Limites préparées : 200 fichiers/50 versions/50 Mio de sources, 2 Mo par contenu, 20 pièces/25 Mio avec5 Mio par pièce ; Office externe seul et originaux sont distincts de cette dernière quota. 54 cas de conversion/aperçu/conteneur et Ruff passent. Ce prototype n’est ni installé ni inclus dans la suite complète10312 : ses247 fichiers runtime restent exactement figés, et le processus PID30592 continue. Il reste à raccorder acquisition bornée, provenance SQL immuable et copie/reprise/idempotence, puis archivev9/restauration, éditeur et activation. Aucun endpoint d’import disponible sur8001, aucune modification canonique ou source XPilot, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-import-stage-progress.json`.

**L5.4 — format réel de l’éditeur XPilot vérifié.** `ProjectDocumentsPanels.tsx` utilise contentEditable/execCommand et sauvegarde HTML + texte, sans mettre nécessairement à jour le JSON TipTap généré par le backend. Il insère aussi les images en dataURI et les cases de liste dans le HTML. Le prototype refuse désormais un JSON dont le texte diffère du contenu source actuel ; aucun ancien contenu n’est choisi silencieusement. 55 cas et Ruff passent dans un rapport distinct `notes-import-stage55-python.xml`, qui remplace les 54 cas préparatoires. Le rapport de ces54cas avait été réutilisé pendant la révision : utiliser uniquement le reçu55courant pour les hashes actuels. La conversion HTML fermée, l’acquisition des images intégrées en blobs décodés, le style barré, la provenance/copie SQL et le parcours complet restent à réaliser. Ces prototypes sont hors des247sources figées de la suite complète10312, toujours en cours ; aucune activation ou modification canonique. Preuve : `.ui-preview/xpilot-l5/notes-import-stage55-progress.json`.

**L5.4 — socle notes/fichiers entièrement qualifié, encore dormant.** Session10312 terminée exit0 : 1408 tests Python réussis/1 ignoré,1504.56s ; les247sources figées restent identiques, Ruff conforme. La correction de fixturev5 est incluse, sans assouplir les archives. Le prototype d’import55cas est séparé et n’était pas inclus dans cette suite ; HTML réel/dataURI/style barré, provenance SQL/copie gérée/reprise, archivev9/restauration globale, éditeur/autosave et activation restent à réaliser. Aucune API de notes/pièces/import n’est enregistrée sur8001, qui conserve Documents/ERP9. Aucun changement canonique, suppression, commit/push. Preuve terminale : `.ui-preview/xpilot-l5/notes-corrected-full-terminal.json`.
