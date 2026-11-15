# Documents, notes et visas internes — lot L5

## Brouillons et accusés de sauvegarde — 12 octobre 2026

Le Studio conserve l'éditeur riche et les versions ERP hérités de XPilot.
Si une note plus récente est reçue avant l'ACK d'une sauvegarde, son snapshot
reste affichable et le brouillon local est conservé pour comparaison. Si seul
le transcript a progressé, l'ACK de la même version de note peut nettoyer le
brouillon confirmé ; toute nouvelle saisie depuis l'envoi reste sauvegardable.
Les réponses GET arrivées dans le désordre ne font plus disparaître les segments
récents. Aucun nouveau moteur de notes ni référentiel de document n'est ajouté.

La [preuve ciblée](../logs/foresight-runtime/studio-snapshot-order-20261012-final/qualification.json)
contient cinq régressions nouvelles, 106 tests distincts avec les contrôles liés.
La [globale React](../logs/foresight-runtime/studio-snapshot-order-final-20261012-v2/qualification.json)
passe 724/724 ; TypeScript et compilation passent. La [recette navigateur et SQLite](../logs/foresight-runtime/studio-snapshot-delivery-20261012/browser-qualification.json)
confirme une seule note, ses versions 1/2 exactes et sa restauration après
navigation/recharge : aucun Recording, fragment, segment, CR, action ou tâche.
Les moteurs sont désactivés dans cette fixture. Ces preuves ne qualifient pas
la capture intégrée, l'IA ni une séance longue.

Dans le Studio, enregistrer une version de note conserve son contenu ; « Terminer
la prise de notes » clôt la séance avant relecture et publication du compte rendu.
La Synthèse distingue cette finalisation requise des corrections réellement non
enregistrées. Son formulaire reste conservé lors d’un changement d’onglet et le
brouillon local retrouve aussi les éléments non encore ajoutés (type, formulation,
bloc/extrait, responsable et échéance) après rechargement. Ces champs ne sont ni
publiés ni approuvés automatiquement ; la relecture est à renouveler après recharge.

## Notes de séance et projection additive — 11 octobre 2026

La fusion Foresight conserve l'autorité de `Note`/`NoteVersion` ERP. Les séances
sans projet ont des versions de staging ; l'attribution crée une seule note
ERP, sans projet ou audio fictif. Chaque version enregistrée/restore/import crée
son entrée d'outbox dans la même transaction ERP ; un reçu Brain idempotent
assure la projection de preuve, puis l'indexation EG2. Les notes identiques de
deux projets ont des identités distinctes. Aucun traitement LLM ne conditionne
la sauvegarde, et aucune projection ne valide une information.

L’éditeur partagé Notes/Studio ajoute un mode Markdown pour les paragraphes,
titres 1–3, listes/cases et les marques gras/italique/code/liens sûrs.
Les structures non convertibles (tableaux, images, couleurs, alignements et
marques sans équivalent pris en charge) refusent la conversion sans toucher
la note riche. Un brouillon local invalide reste conservé, distinct de la
version ERP ; il bloque sauvegarde/autosave, enrichissement manuel,
acceptation de proposition et publication
jusqu’à conversion valide ou abandon explicite. Un changement externe du
contenu de base provoque un conflit visible et conserve les deux contenus.
La conversion ne crée pas de nouvel espace de notes ni de format serveur.

Les citations historiques possèdent un aperçu en lecture seule de la version
exacte, y compris ses liaisons d’images. Les versions de staging se lisent sous
`/api/v1/meeting-sessions/{sid}/note-versions/{version_id}` avec contrôle des
droits de séance, sans substitution par la note courante ni écriture.

Les enrichissements sont des ajouts cités, soumis à acceptation/rejet et à la
vérification de la version humaine. F10 ajoute un opt-in distinct,
`foresight.auto_enhancement_enabled=false` par défaut, indépendant des questions
proactives (`proactive_enabled`). Il attend au moins huit secondes de stabilité
observée du même contexte sauvegardé : révision de séance, version/contenu de
note, segments et contexte calendrier. La réservation de tentative est durable
avant exécution ; un même instantané n’est pas réessayé automatiquement après
erreur ou interruption. Une reprise passe par « Améliorer les notes ».

La proposition conserve la version ou l’instantané de base et ses citations ;
un contexte enregistré devenu différent la rend périmée. Elle reste soumise à
un choix humain et conserve la note existante. Les buffers riches et Markdown
locaux sont exclus de l’analyse automatique : une génération peut porter sur
la dernière version sauvegardée pendant la saisie. Le Studio l’indique et
bloque génération manuelle, acceptation et publication tant que le brouillon
attend sauvegarde ou conversion ; arrêt et récupération audio restent libres.
L’état `failed` affiche « Tentative à reprendre », y compris si le résultat
d’une ancienne exécution n’est pas confirmé. Le timeout de transport de
45 secondes n’est pas un délai total garanti ; un appel HTTP engagé n’est pas
préempté par l’arrêt des nouvelles admissions.

La publication de notes seules fige une
version relue, conserve sa provenance et produit un CR/les actions explicites
sans création automatique de tâche. Les exports de séance conservent staging,
historique ERP, pièces et fragments originaux avec empreintes.

Les archives projet historiques gardent leur format : les extensions de séance
qui ne lui appartiennent pas nécessitent l'export dédié ou la sauvegarde globale,
avec avertissement explicite. Ni module de signature, ni ERP parallèle n'est créé.
Voir [38_FORESIGHT_DELIVERY.md](38_FORESIGHT_DELIVERY.md) pour les preuves de panne,
rejeu et restauration sur copie.

Preuves UI de l'étape précédente : **672/672 tests dans 75 fichiers**, TypeScript et build
avec code 0, dans [le reçu global](../logs/foresight-runtime/frontend-completion-qualification.json).
Les **569/569 tests dans 69 fichiers** du reçu `frontend-qualification.json`
restent une référence historique antérieure aux compléments Notes/Studio.
Le libellé « Tentative à reprendre » est ensuite qualifié par deux tests
ciblés, TypeScript et un nouveau build, tous avec code 0, sans relancer la suite
globale. [Le reçu de suivi](../logs/foresight-runtime/frontend-f10-label-followup-20261011-204228.json)
conserve logs et empreintes, ainsi que la copie vérifiée des quatre assets
précédents. L’asset de ce suivi, `index-NcMllJD2.js`, a pour SHA-256
`2ca3617f47bd1d6828f53208ce5ddf547d5baf9d6f5d306733f2cd9b5b0992d7`.

Un refus Markdown reproduit dans le navigateur venait de l’ordre des
propriétés du DTO ERP. La comparaison utilise maintenant un ordre explicite
des champs paragraphes/titres/listes/éléments ; les contrôles de contenu,
espaces et structures non représentables restent inchangés. Le correctif passe
**97/97 tests ciblés dans cinq fichiers**, puis TypeScript et build avec code 0,
dans [le reçu Markdown](../logs/foresight-runtime/frontend-markdown-dto-followup-20261011-205428.json).
Le build du correctif Markdown `index-DKlOduK1.js` a pour SHA-256
`892c4fb213ae70bcb1160851b25475a892a9af9ddaf5f3cdaf6e43bd10861ebd`.
NcMllJD2 et les reçus antérieurs sont préservés ; les 672 tests globaux, les
deux tests du libellé et les 97 tests ciblés se recouvrent et ne se somment pas.

La recette réelle, sur données fictives isolées et serveur 18003, confirme
ERPNote V2 → Markdown → V3 et V3 conservée après rechargement. La saisie invalide
reste présente après retour/réouverture ; V3 comporte cinq blocs : un titre et
quatre paragraphes, le dernier en gras. Les tableaux Markdown sont refusés,
avec sauvegarde et finalisation désactivées. L’avertissement natif du navigateur
a nécessité une annulation humaine, sans perte du brouillon. La version ERP V1
mentionnant Paul reste visible alors que la tête est V3 ; le staging V1 affiche
toujours 50 euros malgré les 70 euros du contenu courant.
[Le rapport navigateur final](../logs/foresight-runtime/browser-completion-20261011/qualification.json)
valide **21 assertions qualifiées**. L’aperçu historique du build DKlOduK1
ne déborde pas à 1280/670/320 px : client/défilement **1265/1265, 655/655 et
305/305 px**. La première tentative à 670 px ciblait un autre onglet et est
exclue ; les mesures réelles et leurs captures sont distinctes, dont
[la capture finale du Studio](../logs/foresight-runtime/browser-completion-20261011/final-studio-historical-version.png).
Cette passe utilise des réponses simulées, sans LLM, capture audio ou
publication ; Drive connecté et recette physique hors connexion restent
hors de cette qualification. La fixture précède le correctif UTC staging,
qualifié séparément par cinq tests API.
La référence visuelle choisie par l’utilisateur porte sur les écrans publics
documentés ; aucune parité avec une interface privée n’est revendiquée.

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

État : **socle Documents L5.1–L5.3 activé sur 8001, ERP9 ; lot L5 complet en cours**. Les huit trames, formulaires, préférences, lots et publication explicite sont raccordés. Le worker documentaire est actif. Les dossiers des trames et des copies restent à configurer ; le téléchargement final navigateur, les trames Office d’entreprise et le SMB réel restent non qualifiés. Les notes, comptes et visas ne sont pas encore réalisés. Les sections datées ci-dessous conservent l’historique des qualifications, avant et après activation.

## Source et périmètre

Source auditée en lecture : XPilot, commit
`82d47dff8475d32ea18a99e9f81d6409b1c19643`.
Les déclarations de `backend/app/services/document_filling.py` sont extraites
par lecture AST, sans importer son exécution ni sa base. Leur empreinte est
`fd18d50cfedaf4bda1d6b5fb16b75f586a0504a72f60a21fbafeee94dbc932fb`.
Les fichiers Office modèles ne sont pas copiés du dépôt. Les chemins réels et
les modèles de l'entreprise seront sélectionnés explicitement dans Agent.

Le code Rust `web/src-tauri/src/document_filling.rs` manipule ZIP et XML sans
automatiser Office. Agent conserve cette séparation : consulter, préparer une
copie puis publier sont des opérations distinctes. Le repli XPilot sur la
première feuille lorsque la feuille attendue manque n'est pas repris.
Le rapprochement ou remplacement implicite des liens réseau existants n'est
pas repris non plus : leurs données restent conservées.

| Trame | Format | Cibles d'identification |
|---|---|---|
| Offre LT simplifiée | DOCX | 21 signets, dont des variantes équivalentes |
| TDAO | XLSM | 7 cellules, feuille `Accueil` |
| TDSP | XLSM | 7 cellules, feuille `Page d'Accueil` |
| CDC fabrication simple | XLSM | 7 cellules, première feuille déclarée |
| Notice utilisateur | DOCM | Signet `Désignation` |
| Demande CE | DOCX | Signets `Affaire` / `Affaire2` |
| Satisfaction produit | XLSX | 6 cellules |
| Satisfaction forfait | XLSX | 6 cellules |

Les 19 champs du catalogue portent sur l'identité affaire/offre/client,
l'équipement, les contacts, l'agence, la désignation et la date. Le numéro
d'offre identifie un document : aucun prix, taux, marge, vente ou calcul
financier n'est ajouté. Les deux trames de satisfaction restent distinctes.

## Moteur préparé dans le worktree

`backend/app/data/document_templates.json` conserve les mappings et leur
provenance. `document_template_catalogue.py` vérifie leurs contrats, formats,
cibles uniques, coordonnées Excel et substitutions de nom autorisées. Chaque
lecture rend une copie indépendante du catalogue, sans changer un lien projet.

`document_package_preview.py` reçoit exclusivement des octets déjà acquis.
Il n'accepte aucun chemin, ne télécharge aucune relation externe, ne décompresse
pas de fichier sur disque et ne lance ni Office ni macro. Il donne les valeurs
existantes/proposées, champs et cibles manquants, motifs bloquants, feuille
retenue, empreinte source et empreintes des parties VBA.

Une cellule absente peut être créée dans la copie ; une formule ciblée, une
cellule fusionnée hors ancre, une feuille ou un document protégés bloquent la
préparation. Une feuille nommée absente ne provoque aucun repli. Pour Word,
une variante de signet disponible suffit pour son champ ; les noms ambigus,
chevauchements, champs recalculés et emplacements vides incompatibles sont
signalés. Une signature OOXML existante bloque la préparation.

`document_package_prepare.py` exige l'empreinte de l'aperçu, relit les mêmes
contrôles puis crée une copie en mémoire. Les modifications XML utilisent les
positions des octets : les déclarations d'espaces de noms, commentaires,
attributs de style, signets, parties VBA et contenus hors cible sont conservés.
Les textes Excel sont des chaînes littérales, même s'ils commencent par `=`.
Les lignes/cellules ajoutées sont ordonnées, les extensions restent en fin de
ligne et les dimensions présentes sont étendues. Le résultat est relu et ses
cibles comparées aux valeurs soumises avant d'être retourné.

Bornes : source et résultat de 50 Mio maximum, 2 048 entrées ZIP, 32 Mio par
entrée et 128 Mio décompressés au total ; compression excessive refusée.
Les chemins internes ambigus, doublons, liens symboliques, chiffrement, CRC
incorrects, DTD/entités, XML excessif ou non UTF-8 sont refusés. Ces bornes
concernent la préparation documentaire ; elles ne définissent pas les droits
d'accès aux fichiers des projets, traités dans la section suivante.

Qualification : 64 cas ciblés passent sur paquets Office fictifs. Ils couvrent
les huit trames, styles et contenus conservés, macros inertes, rich text et
chaînes partagées, cibles bloquées, variantes de signets, empreintes, protections,
ZIP corrompus et entrées hostiles, ainsi qu'une feuille de 3 000 lignes.
La suite complète passe : **938 tests Python / 1 ignoré** ; Ruff conforme. Preuve : `.ui-preview/xpilot-l5/document-packages-result-v2.json`.
Cette vérification structurelle ne prouve pas encore le rendu dans Office ou
la compatibilité de tous les modèles réels de l'entreprise.

## Acquisition contrôlée et champs sourcés — préparation du 7 octobre

`document_file_access.py` ajoute une acquisition en lecture, appelée avec
l'identifiant du projet, celui d'un lien lui appartenant et un chemin relatif.
Les droits projet sont contrôlés avant configuration et sondes de fichiers.
Un lien fichier autorise exclusivement son fichier ; un lien dossier limite
la lecture à sa propre arborescence, indépendamment des racines globales.
Ce service n'appelle pas le GET hérité qui crée les liens obligatoires et
n'ajoute, remplace ou supprime aucune ligne.

Deux variables serveur explicites configurent ce nouveau service :

- `AGENT_DOCUMENT_ROOTS` : tableau JSON des racines documentaires absolues.
- `AGENT_DOCUMENT_DRIVE_MAPPINGS` : objet JSON des substitutions de lecteurs,
  avec clés majuscules comme `V:` et chemins absolus de destination.

Exemple à adapter aux chemins réellement autorisés : racines
`["\\\\serveur\\affaires"]`, mappings `{"V:":"\\\\serveur\\affaires"}`.
Les racines sont exprimées dans le namespace serveur après mapping. Une liste
vide laisse ce nouveau service désactivé avec diagnostic explicite. Ces réglages
ne modifient pas les fonctions héritées d'ouverture de chemins ni leurs variables.
Aucun mapping XPilot ou nom de serveur n'est imposé.

Le lien doit appartenir lexicalement à une racine autorisée avant résolution.
Les racines sans rapport avec le lien choisi ne sont pas sondées et leur
indisponibilité ne bloque pas la lecture d'un autre projet.
La résolution canonique refuse ensuite une sortie de racine ou du dossier du
projet. Sous Windows, le chemin du handle ouvert est contrôlé avec
`GetFinalPathNameByHandleW` ; l'identité, taille et date du fichier, ainsi que
l'emplacement du lien, sont revérifiés après lecture. Les octets sont figés,
limités à 50 Mio et accompagnés d'une empreinte SHA-256. La comparaison d'une
empreinte d'aperçu antérieure est possible sans réécriture du fichier.
Fichier absent, partage/lien indisponible, changement concurrent et configuration
manquante donnent des diagnostics distincts. Un chemin relatif absolu, une
traversée, un flux alternatif Windows ou un alias ambigu sont refusés.

`document_project_values.py` fournit les 19 champs, leurs origines et les
révisions distinctes d'identité et de planning. La fiche L1 complète les champs
historiques ; le responsable déclaré prime sur le membre responsable actif.
Une référence archivée reste identifiable avec avertissement. Les coordonnées
d'agence restent manquantes tant que leur extension n'est pas renseignée.
Les deux contacts client ont leur origine commune explicite. Un descriptif
trop long est signalé sans troncature de la fiche.

Les corrections sont limitées à la copie d'un document et ne changent pas les
référentiels. Le numéro de projet et la date calculée ne sont pas corrigeables
par cette entrée ; les champs financiers sont exclus. Les droits d'accès aux
valeurs suivent ceux du projet et n'accordent aucun privilège métier.

Qualification de cette extension : **101 cas ciblés réussis**, dont
25 sur les fichiers et 12 sur les valeurs, plus les 64 cas du moteur. La recette
utilise de vrais handles et une vraie jonction Windows sur dossiers fictifs,
sans écrire sur le réseau. La suite complète passe : **975 tests Python / 1 ignoré** ; Ruff conforme. Preuve : `.ui-preview/xpilot-l5/document-files-v2-result.json`. Le parcours
HTTP/UI a depuis été qualifié dans la section dédiée ci-dessous. La
découverte des modèles, les jobs et la publication restent à raccorder ;
aucune activation L5 sur 8001 n'a lieu dans cette étape.

## Suite d'intégration obligatoire

1. **Fichiers et chemins.** Vérifier les droits projet avant toute sonde disque.
   Résoudre uniquement des liens du projet et chemins relatifs bornés, avec
   racines autorisées et mappings de lecteurs configurables ; aucun `V:` ou
   serveur UNC codé en dur. Signaler distinctement partage indisponible et
   document absent. Refuser sorties de racine, liens/jonctions hors périmètre
   et changements de fichier pendant acquisition. La consultation n'ajoute
   aucun lien et ne modifie aucun document.
2. **Trames et traitements durables.** Construire les valeurs sourcées depuis
   L1, l'équipe et les données historiques non financières ; afficher l'origine
   et les informations manquantes. Raccorder aperçu, choix de trame, sélection
   par lot, progression traités/total, arrêt, reprise et journal par fichier.
   Préparer d'abord dans le stockage Agent. Toute publication réseau est une
   commande explicite ; remplacement après choix et sauvegarde conservée,
   avec empreinte et contrôle de concurrence au dernier moment.
   Le référentiel d'agence actuel fournit code/libellé, sans adresse, code
   postal, ville ni téléphone : ces valeurs doivent rester manquantes jusqu'à
   une saisie explicite et une extension additive du référentiel, jamais être
   déduites du libellé. XPilot emploie le même contact client pour demandeur et
   responsable : Agent affichera cette origine commune. Une modification de
   champ destinée à un seul document ne met pas implicitement à jour la fiche
   client, personne ou agence.
3. **Notes.** Stockage Agent comme vérité documentaire, contenu structuré et
   représentation texte, HTML assaini, pièces jointes figées et révisions
   immuables. Sauvegarde visible, brouillon durable et conflit sans perte de
   saisie. L'import des notes présentes dans `11-xPilot` est volontaire et
   conservateur : aucune suppression, écriture ou remplacement d'index réseau
   implicitement déclenché par la consultation. Restaurer une version crée une
   nouvelle révision. Le module hérité est conservé.
4. **Identité des signataires.** L'opérateur serveur actuel n'est pas un compte
   utilisateur authentifié. Ajouter une liaison compte/personne fiable et une
   confirmation personnelle avant d'activer les décisions. Une personne
   choisie dans un formulaire, un rôle métier ou un en-tête client ne donnent
   pas le droit de signer à sa place. Aucun compte XPilot n'est importé.
5. **Visa interne.** PDF source figé avec empreinte ; demande, participants
   éligibles, séquence ou parallèle, expiration, acceptation, refus motivé,
   rappel et annulation avec audit. Chaque acteur décide en son nom. Le PDF
   final conserve la source et ajoute une attestation interne vérifiable.
   Ce parcours ne revendique pas une signature qualifiée. RLP et PDF manuels
   partagent le service sans mélanger leurs publications. Notification externe
   uniquement avec canal configuré et commande explicite de l'utilisateur.
6. **Interface et livraison.** Raccorder ces parcours dans les rubriques projet
   existantes, avec menu nommé et bulle de redimensionnement préservés. Qualifier
   lecteur/éditeur, clavier, mobile, chargement et conflits ; migrations
   additives, sauvegarde/restauration fichiers + ERP + Brain, recette sur copies,
   tests complets et activation contrôlée sur le serveur unique 8001.

Critères finaux : aucun chemin hors périmètre, aucun remplacement implicite,
aucune perte après fermeture ou conflit, jobs reprenables sans double écriture,
documents et décisions auditables. L5 reste en cours jusqu'à la qualification
de l'ensemble de ces parcours ; L6–L9 demeurent au plan global.

## Parcours HTTP et interface documentaire — 7 octobre 2026

Étape intermédiaire qualifiée dans le worktree, **non activée sur le serveur
canonique 8001**. L0–L4 restent la version active. Le moteur et les données
historiques des modules hérités restent conservés.

Dans le projet, ouvrir **Documents → Préparer un document** :

1. Choisir l’une des huit trames. Sélectionner un lien du projet et le fichier
   relatif à ce lien ; laisser le chemin vide si le lien désigne le fichier.
   La liste des liens est paginée et sa lecture ne crée aucun lien.
2. Lire les champs et leurs origines. Une correction s’applique uniquement à
   cette copie ; « Revenir à la donnée projet » retire cette correction.
   Le numéro de projet et la date sont en lecture seule. Une nouvelle trame
   réinitialise les corrections ; changer de projet réinitialise le parcours.
3. Afficher l’aperçu : cellules ou signets, texte actuel/proposé, provenance,
   champs manquants, protections et signets incompatibles. Les fichiers à
   macros signalent leur conservation sans exécution. Le tableau défile
   horizontalement sur mobile, sans élargir la page.
4. Confirmer la relecture puis préparer la copie. Le navigateur vérifie son
   empreinte avant de proposer le lien de téléchargement. La source reste
   intacte. Toute nouvelle saisie ou relecture des données invalide l’aperçu
   et l’ancien lien de copie. Les erreurs conservent les corrections locales.

Les boutons affichent la phase en cours et permettent d’annuler la requête.
La préparation client a une durée maximale de 120 secondes. L’annulation de
la requête ne garantit pas l’interruption immédiate d’une lecture système
sur un partage indisponible ; aucun fichier n’est écrit par cette opération.
Un brouillon de corrections est conservé entre sous-vues dans la session
ouverte, **pas après rechargement ou fermeture du navigateur**. Le futur
stockage et les jobs durables doivent traiter cette persistance.

### Contrat et concurrence

- `GET /api/v1/projects/{project_id}/documents?offset=0&limit=100` : valeurs,
  origines, révisions identité/planning, trames, liens et statut des racines
  documentaires. Pas de sonde disque ni d’insertion implicite.
- `POST .../documents/preview` : `document_id`, `link_id`, `relative_path`,
  `overrides`. Requête de consultation autorisée au lecteur dans sa portée,
  avec jeton local et contrôle d’origine conservés.
- `POST .../documents/prepare-copy` : même choix, plus
  `expected_source_sha256`, `expected_link_sha256`, `expected_values_sha256`,
  `expected_identity_revision`, `expected_planning_revision`. Editeur ou
  propriétaire autorisé requis. Réponse binaire avec nom de téléchargement,
  ETag de copie, trois empreintes de contexte et `X-Agent-Network-Published:
  false`. La réponse ne crée ni fichier géré ni reçu persistant.

Le hash métier inclut valeurs, origines, avertissements et révisions : un
contact ou client modifié ne passe pas inaperçu parce que la révision projet
reste identique. Le lien est lié à son projet et son chemin. Une connexion
fraîche relit métier et lien après lecture/préparation pour éviter une
validation sur le cache ORM précédent. Un lien retiré ou modifié pendant
l’opération provoque un conflit. Les erreurs ne changent aucune fiche.

Les champs financiers, l’acteur et la politique de chemins ne sont pas
acceptés dans les commandes. Droits projet vérifiés avant toute sonde.
`403` indique un rôle ou chemin refusé, `404` un objet hors portée/absent,
`409` un contexte modifié ou un accès indisponible, `422` une saisie/trame
incompatible ; `413` conserve la limite de 50 Mio. La configuration des
racines et mappings décrite précédemment reste exclusivement côté serveur.

### Preuves et limites de cette étape

**1006 tests Python réussis / 1 ignoré**, Ruff conforme ; **328 tests
React**, TypeScript et build conformes. Preuves : `.ui-preview/xpilot-l5/document-api-v2-result.json`,
`.ui-preview/xpilot-l5/document-api-frontend.json` et
`.ui-preview/xpilot-l5/document-browser-recipe.json`.

La recette utilise des stores et trames fictifs, de vrais handles Windows et
le build du worktree sur ports privés de recette. Le téléchargement CE a
réellement été enregistré, ses deux signets et ses parties non ciblées
vérifiés ; les 16 sources et l’ERP restent identiques. Lecteur : aperçu
autorisé et préparation refusée côté serveur. Clavier et mobile sont vérifiés.
Le correctif mobile et l’exception exacte du test générique lecteur sont
repris dans la qualification finale ; l’essai initial est conservé comme
preuve en échec, sans être présenté comme la validation finale.

Les trames réelles d’entreprise et leur rendu Office restent à qualifier.
Cette étape ne remplace ni la découverte des modèles, ni les traitements par
lots et artefacts gérés, ni la publication avec sauvegarde/empreinte réseau,
ni les notes et les comptes/visas. Aucun lot L5 complet ni activation n’est
revendiqué par ce téléchargement interactif.

## Découverte contrôlée des trames — 7 octobre 2026

Cette extension est qualifiée **dans le worktree**, sans activation L5 sur 8001.
Dans Documents, choisir une trame et un lien, puis **Rechercher les trames dans
ce lien**. Les résultats indiquent fichiers observés, dossiers parcourus,
emplacements et mots du nom correspondants, indice détecté et son origine.
La recherche ne choisit pas de fichier. **Choisir cette trame** remplit le chemin
relatif et invalide aperçu/copie précédents ; l’aperçu reste nécessaire pour
vérifier réellement format, contenu, cellules/signets et protections.

`POST /api/v1/projects/{project_id}/documents/discover` accepte exclusivement
`document_id` et `link_id`. Les règles par défaut des huit trames sont reprises
du catalogue audité, indépendamment des mappings de champs. `SearchRule` et
son empreinte définissent déjà le contrat des futures préférences enregistrées,
mais **leur édition, historique et persistance ne sont pas encore raccordés**.
Le client n’envoie ni racines, acteur, règle arbitraire ni limites serveur.
L’exception de consultation lecteur porte sur cette route POST exacte ; les
contrôles d’origine et jeton local restent actifs, comme pour l’aperçu.

### Correspondances et bornes

- Les accents, séparateurs et casse sont normalisés. Tous les mots d’un motif
  doivent être présents comme mots entiers. Les segments de dossier sont
  recherchés dans l’ordre ; plusieurs motifs sont des alternatives.
- Les indices explicites `V10`, `version 10` ou `Rev2` priment. Sinon les nombres
  isolés de un à trois chiffres sont une **heuristique du nom**, affichée comme
  telle ; aucun indice réel Office n’est certifié. Les autres nombres, comme
  l’année 2026, ne servent pas d’indice. Le rang favorise la proximité de l’indice
  préféré ; les meilleurs rangs égaux restent ambigus et sans recommandation.
- Un lien dossier limite la recherche à son arborescence ; un lien fichier
  autorise seulement ce fichier, sans prétendre à une correspondance de dossier.
  Les branches sans premier segment pertinent, dossiers de données d’entrée,
  exclusions et points de réanalyse/jonctions descendants sont écartés.
- Bornes par défaut : 5 000 entrées, 500 dossiers, profondeur 12, 80 candidats,
  20 secondes. Les fichiers vides ou de plus de 50 Mio sont écartés. La recherche
  ne lit pas leurs octets. Elle n’affirme pas qu’un candidat est un paquet Office
  valide. Les résultats partiels indiquent les limites atteintes et ne proposent
  pas de meilleure correspondance globale.
- Le total de l’énumération reste `null` ; aucun pourcentage fictif n’est affiché.
  L’interface présente une recherche animée, respecte la réduction de mouvement,
  propose l’annulation et borne la requête à 30 secondes. Le callback interne
  fournit observations/phase/total inconnu pour les futurs jobs persistants.
  Une annulation HTTP ne peut pas interrompre immédiatement un appel SMB bloqué
  par le système ; les limites sont contrôlées entre les appels.

### Périmètre et changements concurrents

Les droits projet/lien précèdent configuration et sondes. Seules les racines
lexicalement compatibles sont résolues, avec les mappings serveur explicites
déjà décrits. Le chemin canonique doit rester dans une racine autorisée.
Sous Windows, chaque dossier parcouru est conservé ouvert en lecture sans
partage de suppression, son chemin de handle et son identité sont contrôlés.
Sous Linux, l’énumération utilise le descripteur du dossier, sans suivre le lien.
Les identités et chemins de tous les dossiers sont revérifiés ; le lien est relu
dans une connexion ORM fraîche. Un changement détecté donne `409` et invalide
tous les résultats de cette recherche. Les handles sont toujours fermés.
Référence Win32 : [CreateFileW et modes de partage](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).

La recette Windows a détecté et corrigé l’ouverture initiale limitée aux
attributs, qui permettait encore le renommage. Le handle de lecture qualifié
empêche le renommage du dossier fictif pendant sa détention. Cela ne constitue
pas une certification de tous les serveurs SMB ou systèmes de fichiers réseau :
leur disponibilité et les modèles réels d’entreprise restent à qualifier.
Un fichier peut changer après l’observation ; son acquisition et aperçu sont
donc toujours refaits après choix. Aucun document n’est créé ni publié ici.

### Qualification et suite

**1051 tests Python réussis / 1 ignoré**, Ruff conforme ; **341 tests React**,
TypeScript et build conformes. 45 nouveaux cas couvrent huit règles, accents,
ordre/exclusions, indices, ambiguïtés, liens directs et sous-dossiers, racines
inaccessibles sans rapport, vrai handle et vraie jonction Windows, limites,
annulation et changements du lien/arborescence. Le groupe API/droits/documents
passe avec 112 tests ; les 43 cas React ciblés couvrent recherche, choix,
invalidation, erreurs, réponses tardives et délai avec signal de vue.

Preuves : `.ui-preview/xpilot-l5/document-discovery-result.json`, `.ui-preview/xpilot-l5/document-discovery-frontend.json`
et `.ui-preview/xpilot-l5/document-discovery-browser.json`. Recette réelle sur
18 sources fictives et ERP inchangés : deux candidats de même rang, choix et
aperçu au clavier, lecteur HTTP 200/200 et préparation 403, projet étranger 404,
origine étrangère 403. Mobile 390 px : page client/scroll 375/375 et liste 277/277 ;
molette dans la liste de 0 à 44,8 px, position de page inchangée. Les deux serveurs
de recette sont arrêtés, onglets fermés et viewport rétabli.

La suite L5.3 doit encore enregistrer des préférences versionnées et associations
documentaires explicites, ajouter stockage Agent, jobs/essais/reçus persistants,
progression traités/total, arrêt/reprise sans double adoption et publication
réseau séparée avec empreinte et sauvegarde conservée. Notes, comptes/personnes,
visas, sauvegarde/restauration et activation du lot complet restent obligatoires.

## Socle de formulaires et préférences persistants — 7 octobre 2026

Cette étape qualifie les services internes `document_forms.py`, leurs commandes
strictes et quatre tables documentaires avec huit triggers SQLite. Elle ne rend
pas encore ces formulaires persistants dans l’interface et n’installe rien sur
8001. L’ERP reste en version 8 ; son démarrage prévalide les tables documentaires
éventuellement présentes et les exclut de `create_all`. L’installation future
passe explicitement par `install_document_schema(engine, backup=...)` après
qualification des archives et du raccordement complet. Le callback de sauvegarde
doit réussir avant toute DDL ; aucun nettoyage, import XPilot ou amorçage implicite.

### Préférences communes

`search_preferences`, `save_search_preferences`, `search_history` et
`restore_search_preferences` sont réservés au propriétaire sans portée limitée.
La lecture retourne les valeurs par défaut sans créer une ligne. Chaque commande
enregistre les huit identités distinctes, avec libellé, ordre, activation et
critères de recherche bornés. Formats, champs/cellules/signets et racines restent
hors des réglages. Les chemins sont relatifs ; la sémantique de recherche est
celle des mots et segments de `SearchRule`, sans expressions régulières exécutées.
`effective_preferences` vérifie le projet avant de fournir ses règles applicables
à un lecteur ou éditeur autorisé, sans exposer le journal commun.

La tête commune pointe vers une version JSON canonique empreintée et immuable.
Le catalogue audité possède une empreinte séparée ; une évolution incompatible
demande une réconciliation explicite. La révision attendue et le verrou SQLite
empêchent un écrasement concurrent, y compris à la première création.

### Formulaire du projet et versions

`draft`, `save_draft`, `draft_history` et `restore_draft` conservent, pour un seul
projet/document, le lien par identifiant, le chemin relatif normalisé et les
corrections non financières déjà autorisées. Aucun accès au partage, aperçu
Office, copie, approbation ou modification d’une fiche projet/client/personne ne
résulte de la sauvegarde. Des liens ayant le même code restent distincts.

Une sélection dont le lien a disparu garde ses versions et affiche
`selected_link_missing`. Une nouvelle sauvegarde ou restauration doit choisir
un lien encore présent dans ce projet, ou effacer explicitement le choix. Les
anciens snapshots ne sont jamais réécrits. Les correspondances d’identifiants
restent séparées dans un dictionnaire plat, prévu pour une future archive typée.

Le lecteur ne peut pas sauvegarder ; la portée projet et les droits précèdent
l’accès au schéma. Les commandes ne prennent ni acteur ni privilège du client.
L’identifiant opérateur serveur est un auteur de journal, pas une signature ou
une authentification humaine. Les transactions appartiennent à l’appelant :
committer une commande réussie, effectuer un rollback après un refus.
Un schéma absent ou vide non protégé reste dormant en lecture ; une écriture ou
restauration y retourne `409`. Un groupe partiel avec données ou des contraintes
incompatibles est refusé. Une version illisible, empreinte invalide ou incohérente
avec la tête est également refusée. Restaurer crée une nouvelle révision, sans
supprimer ni modifier une version précédente.

### Sauvegarde, archives et qualification

Le test utilise une vraie sauvegarde SQLite puis rouvre la base dans une nouvelle
racine : valeurs, historique et triggers conservés. Il vérifie les lignes/cellules
des tables projets et liens fictifs avant/après installation. **État de cette qualification initiale, désormais complétée par la v7 ci-dessous :
l’archive projet typée L5 n’était pas encore implémentée** : les anciennes versions v2–v6 n’exportent
pas de placeholders documentaires et refusent un projet ayant des données de ce
socle, plutôt que produire une archive incomplète. Les données globales communes
ne sont jamais admises par la validation d’une archive projet ancienne.

Qualification : **1094 tests Python / 1 ignoré**, Ruff conforme ; 43 nouveaux
cas ciblés couvrent installation/sauvegarde/idempotence, schémas et triggers
endommagés, contraintes inter-projets réelles, réouverture, historique,
restauration, lien absent, droits, révision mise en cache et deux sessions SQLite
concurrentes. Preuve : `.ui-preview/xpilot-l5/document-forms-v3-result.json`. Aucun changement de frontend ; son dernier
contrôle reste celui de la découverte, avec sources inchangées.

Suite obligatoire : archive typée/restauration des correspondances, HTTP et
interface avec conservation de saisie sur conflit, règles effectives en découverte,
jobs/essais/artefacts/reçus persistants, progression et publication séparée,
notes, comptes/personnes et visas, recette globale puis activation du lot complet.
L5 reste en cours, avec L6–L9 toujours au périmètre.

## Archives documentaires v7 et restauration hors ligne — 7 octobre 2026

Le transport réel `project_archive.py` exporte la v7 lorsqu’un projet possède
des formulaires. La section `document_references` déclare les liens absents et
les deux tables projet conservent les têtes et versions. Les anciens projets
sans données documentaires gardent les enveloppes v2–v6. Ces versions anciennes
refusent des tables ou références documentaires injectées, même vides.

Le validateur typé impose projet parent unique, choix de tête cohérent, révisions
continues, JSON canonique et empreintes exactes, correspondances plates et liens
dans le projet. Un lien disparu demeure déclaré et remappé sans créer de lien
réseau fictif. La réimportation, puis la réexportation et une seconde importation,
gardent les captures brutes et les auteurs historiques. Une restauration locale
du formulaire importé ajoute une nouvelle version. Les préférences communes ne
voyagent pas dans l’archive d’un projet et celles du destinataire restent intactes.

La v7 utilise le coordinateur existant ERP + Brain : schémas protégés vérifiés
avant insertion, validation typée avant écriture, commit coordonné et rollback
sur échec. La combinaison réelle formulaires + RLP/PDF/audio est vérifiée. Les
correspondances typées sont remappées ; aucun remplacement de UUID dans le texte,
les snapshots, les empreintes ou les identifiants d’auteurs historiques.

`app/services/document_backup.py` vérifie les journaux depuis une connexion SQLite
en lecture seule, sans importer les moteurs/configurations de l’application,
créer le répertoire de données ou parcourir les partages. Le contrat structural
`backend/app/data/document_forms_schema.json` est confronté aux déclarations des
modèles par un test dédié ; contraintes et huit protections sont contrôlées.
La sauvegarde globale valide sa copie SQLite. La restauration valide après
empreintes et intégrité SQLite, avant création du dossier neuf. Un journal
endommagé avec manifeste recalculé est donc refusé ; la sauvegarde reste intacte.

Qualification : **1135 tests Python / 1 ignoré**, Ruff conforme ; 18 cas du
contrat pur, 15 cas du transport réel et 8 cas du contrôle hors ligne. Cas couverts :
double import, liens manquants, collisions, parent étranger, empreinte incorrecte,
révision absente, enveloppe rétrogradée, injection de réglages globaux, défaut
d’insertion et rollback ERP/Brain, destination non protégée, réouverture après
sauvegarde globale et corruption recalculée. Preuve : `.ui-preview/xpilot-l5/document-archives-result.json`. Aucun changement
React ni activation ; les sources frontend restent identiques à la qualification
de découverte. Les données de production et le port XPilot 8000 sont inchangés.

L5.3 reste en cours : raccordement HTTP/UI des préférences et formulaires avec
pagination et conservation de saisie sur conflit, puis jobs, essais, artefacts,
reçus et publication explicite. Notes, comptes/personnes et visas sont encore
à intégrer. L’ERP reste en version 8 ; le démarrage ne procède pas à l’installation
du socle documentaire. L0–L4 seuls sont activés sur 8001 ; L5–L9 restent au périmètre.

## Choix sauvegardés et préférences communes HTTP/UI — 7 octobre 2026

Le serveur mono-service enregistre les routes `GET/PUT /api/v1/projects/{project_id}/documents/forms/{document_id}`,
`GET .../history` et `POST .../restore`, ainsi que les routes communes `GET/PUT /api/v1/document-settings`,
`GET .../history` et `POST .../restore`. Les lectures ne créent aucune ligne et n’installent aucun schéma.
Les lectures/écritures communes exigent un propriétaire sans restriction projet. Les formulaires restent soumis au parent et aux droits projet ;
le lecteur peut consulter, mais ne sauvegarde ni ne restaure. Session locale et contrôle d’origine restent obligatoires.
Les commandes strictes excluent acteur, rôle, racines et champs financiers. Une écriture réussie est commitée ; une erreur est rollbackée.

Les deux historiques sont paginés en SQL, ordre décroissant stable de révision, limite 1–200 et offset 0–1 000 000.
La révision attendue évite d’écraser une sauvegarde concurrente. Une restauration ajoute une version, sans modifier les captures historiques.
Le lien sélectionné est résolu par son identifiant dans le même projet, indépendamment de la page des liens, sans parcourir de partage.
Un lien historique absent est conservé et signalé ; l’aperçu nécessite une nouvelle sélection valide.

Dans Documents, la sauvegarde des choix reste distincte de l’aperçu et de la copie. Après conflit, le texte local demeure ;
Comparer montre la version distante et Charger la version serveur la reprend explicitement, en actualisant aussi le journal ouvert.
La navigation protège les modifications ; masquer puis réafficher le volet conserve son brouillon. Les réponses tardives d’un ancien projet
sont ignorées. Une restauration demande confirmation si elle remplace des choix modifiés localement. Le lecteur ne voit pas Save/Restore.

Réglages → Documents conserve les huit identités et formats audités. Libellé, ordre, alternatives de dossiers relatifs et mots du nom,
exclusions, indice préféré et activation sont éditables. Les critères multilignes sont normalisés au moment de l’enregistrement.
La découverte applique ces préférences et retourne leur révision, identifiant de version et l’empreinte de la règle utilisée.
Une trame inactive refuse la découverte avant tout accès fichier ; sélection manuelle, choix enregistrés et aperçu restent utilisables.
Les anciennes observations restent des preuves versionnées ; elles ne valent pas sélection ou approbation automatique.

Qualification figée : **1154 Python / 1 ignoré**, Ruff conforme, **355 React**, TypeScript et build conformes,
sources et assets vérifiés par SHA-256. Les 19 nouveaux cas HTTP incluent vraie application mono-serveur, droits/scopes, CSRF/origine,
transactions, pagination, version périmée et règles effectives. Les 14 nouveaux cas UI couvrent conflits, chargement explicite, historique,
navigation, lien absent et permissions. Recette navigateur/HTTP sur bases fictives : rechargement, conflit deux onglets, conservation du brouillon,
comparaison sans remplacement, restauration formulaire 1 → 5 et réglages 1 → 3, libellé et recherche inactive effectifs, lecteur sans commande,
aperçu fonctionnel et défilement central 631 → 1092. Les 18 fichiers sources et les 121 cellules antérieures hors mutations de tête autorisées
restent intacts. Le mobile est **non qualifié** : l’API viewport annonce le redimensionnement, mais DOM et captures restent à 1280 pixels,
y compris après rechargement et nouvel onglet. Ne pas présenter la capture de cet essai comme une preuve mobile.

Preuves : `.ui-preview/xpilot-l5/document-forms-ui-backend.json`, `.ui-preview/xpilot-l5/document-forms-ui-frontend.json`, `.ui-preview/xpilot-l5/document-forms-ui-browser.json` ; captures bureau, conflit, réglages et lecteur dans le même dossier.
L’ERP reste en version 8, installation documentaire explicite avec sauvegarde avant DDL ; aucune installation au démarrage.
Cette qualification ne migre ni ne redémarre Agent 8001. L0–L4 seuls y sont actifs. XPilot et 8000 sont inchangés.
L5.3 reste en cours pour jobs/items/essais/reçus/événements, artefacts gérés, reprise/annulation et publication explicite.
L5.4–7 et L6–L9 restent obligatoires ; l’objectif reste actif.

## File documentaire — worker, HTTP et sauvegarde globale en cours, 7 octobre 2026

Les six tables additives conservent lots, fichiers ordonnés, tentatives, copies, reçus et événements.
L’installation explicite vérifie colonnes, contraintes, index et douze protections et sauvegarde avant DDL.
Le démarrage effectue seulement le préflight, avant les autres migrations ; il n’installe pas la file.
L’ERP reste en version 8. Une soumission contient une à huit trames distinctes, vérifie l’aperçu et la révision
du formulaire, et valide la taille de toutes les captures avant la première écriture. La répétition d’une
commande renvoie le lot existant ; deux requêtes identiques concurrentes ne créent qu’un lot.

`document_job_worker.py` est un coordinateur facultatif, désactivé par défaut. Sur une base explicitement
installée, `AGENT_DOCUMENT_JOBS_ENABLED=1` autorise son lancement ; `AGENT_TESTING=1` le neutralise.
Son opérateur vient de la configuration serveur : rôle lecteur exclu, périmètre projet appliqué en SQL.
`document_worker_lease.py` maintient un véritable verrou OS sur le fichier associé à la base SQLite canonique.
Les jonctions, liens symboliques et alias par lien dur de la base sont refusés. Un fichier de PID ou une
date ancienne ne servent jamais de preuve. Une seconde instance reste en attente de disponibilité.
Après prise du verrou, une tentative inachevée reçoit un reçu d’interruption ; le lot nécessite une reprise
explicite. Le cas d’un arrêt entre deux fichiers est aussi traité. Un arrêt dont le délai expire conserve
le verrou jusqu’à la fin réelle de l’opération système. Le nettoyage de démarrage s’exécute aussi si un
service échoue après le lancement des autres workers.

API enregistrée sous `/api/v1/projects/{project_id}/documents` :

| Méthode | Route relative | Usage |
|---|---|---|
| GET / POST | `/jobs` | Liste bornée avec état worker / soumission contrôlée |
| GET | `/jobs/{job_id}` | Compteur de fichiers traités/total, états et capacités |
| GET | `/jobs/{job_id}/events` et `/attempts` | Journaux paginés en SQL |
| POST | `/jobs/{job_id}/cancel` et `/retry` | Commande avec `expected_revision` entière |
| GET | `/artifacts/{artifact_id}` | Copie avec reçu de succès, taille/empreinte vérifiées |

Jeton/origine, droits et périmètre précèdent les accès ; aucun acteur, stockage, cible réseau ou champ
financier n’est accepté du client. Un worker indisponible refuse création/reprise, tout en permettant
consultation et arrêt des lots ordinaires. Les téléchargements ne publient rien sur le réseau.
La progression compte les fichiers terminés, indépendamment du nombre de tentatives.

`document_job_schema_rules.py` et le contrat JSON vérifient le schéma hors runtime. `document_job_history.py`
contrôle les captures canoniques, empreintes, auteurs, relations, ordre des fichiers, tentatives, reçus,
copies et continuité du journal. Cette validation concerne les identifiants de la sauvegarde globale ;
le transport individuel avec remappage reste à raccorder. `document_jobs_backup.py` vérifie l’historique
et l’inventaire des fichiers avant la création du dossier de restauration, sans import d’ORM/configuration.
La sauvegarde globale conserve aussi les copies candidates non validées ; elles ne deviennent pas des résultats.
Une copie modifiée ou manquante, un inventaire incomplet ou un reçu incohérent refusent la restauration.

Dans le nouveau dossier restauré, les réussites et captures restent intactes. Une tentative active reçoit
un reçu d’interruption ; les fichiers en attente deviennent interrompus. Chaque lot est marqué
`execution_blocked`, et un événement `store_restored` s’ajoute sans réécrire son auteur ni sa capture.
Ces anciens lots restent consultables et téléchargeables ; reprise et prise en charge sont refusées.
Une nouvelle génération demandera un nouvel aperçu et une nouvelle commande. Les verrous de la machine
source ne sont pas transportés. La source et les pièces de sauvegarde demeurent intactes.
Le premier raccordement refusait l’export individuel des lots ; le transport v8 ci-dessous remplace ce garde temporaire.
Les archives v2–v7 des projets sans lots conservent leur fonctionnement.

Preuve ciblée : `.ui-preview/xpilot-l5/document-jobs-worker-backup-focused.json`.
63 tests worker/HTTP/queue/sauvegarde passent, puis 14 tests finaux de sauvegarde, et 136 cas de compatibilité
des formulaires, archives et sauvegardes existantes. Ruff conforme. Cas réels sur copies fictives : lease
entre processus, worker concurrent, opération encore vivante, processus mort après prise en charge,
conservation d’une réussite, reprise explicite, scopes, lecteur, commandes concurrentes, téléchargement,
restauration portable, candidats conservés, altération et captures falsifiées avec empreinte recalculée.
Les groupes se recouvrent. Le précédent résultat complet interrompu reste historique ; aucun nouveau
résultat complet Python, React, TypeScript/build ou navigateur n’est déclaré.

**L5.3 reste en cours** : interface de sélection/suivi par lot,
publication explicite, qualification complète et activation. Aucun changement frontend dans cette étape.
La file n’est pas activée sur 8001. L0–L4 y restent actifs, XPilot 8000 est intact.
L5.4–7 et L6–L9 restent obligatoires. Aucune suppression de données, import implicite, commit ou push.

## Archives des lots documentaires v8 — raccordement ciblé, 7 octobre 2026

`project_document_job_archive.py` ajoute une section typée `document_job_references` :
les six tables de la file et les identifiants des liens disparus. `project_archive.py` produit la **v8**
uniquement lorsqu’un projet contient des lots ; les autres projets conservent leurs formats v2–v7.
Les préférences documentaires communes restent hors archive. Une tentative active peut être exportée
sans présenter une copie non validée comme une réussite. Seules les copies liées à un reçu de succès
voyagent comme pièces `document-job`, avec propriétaire, taille et empreinte vérifiés.
Les captures et les autres pièces entrent dans la limite globale de l’archive. La taille encodée d’une
copie est bornée avant décodage. Les copies candidates sans reçu restent du ressort de la sauvegarde globale.

Le préflight exige les schémas protégés de la destination, sans installation implicite. Une archive ancienne
injectant des lots, une section manquante, une version de formulaire absente, un journal incomplet ou
un fichier remplacé puis ré-empreinté sont refusés avant préparation des fichiers. La source capturée doit correspondre au projet, au lien et au chemin de la commande ; l’empreinte des valeurs est recalculée. Une correction financière injectée dans la capture est refusée même après recalcul de ses SHA. L’accès au projet précède
la lecture du stockage, y compris sans HTTP. L’import v8 requiert un propriétaire sans restriction,
comme l’administration de l’import HTTP existant ; le lecteur et l’éditeur ne peuvent importer un projet.

Les identifiants plats — projet, lot, fichier, tentative, reçu, copie, lien et version de formulaire — sont
remappés. Les clés de stockage des copies deviennent de nouveaux UUID. Les captures brutes, SHA, provenance,
auteurs et détails des événements déjà présents restent **verbatim**. Un événement immuable `archive_imported`
déclare les nouvelles liaisons des fichiers ; la validation hors ligne sait ainsi contrôler une archive
réimportée sans transformer ses captures historiques. Un lien disparu est conservé sous un nouvel identifiant
non résolu, distinct des autres objets du projet. Les textes contenant d’anciens UUID ne sont pas remplacés.

L’import clôture une tentative active par un reçu d’interruption, conserve les fichiers réussis et marque
les autres fichiers actifs interrompus. Tous les lots importés portent `execution_blocked` ; ils restent
consultables/téléchargeables, mais ne peuvent être pris en charge ni repris. Une nouvelle génération exigera
un nouvel aperçu et une nouvelle commande. Le réexport d’un projet importé, un deuxième import et sa sauvegarde
globale sont vérifiés. Les lots déjà bloqués restent bloqués lors de la restauration globale, sans événement
de restauration dupliqué. Aucun import ne lance de génération ou de publication réseau.

La v8 utilise le coordinateur ERP/Brain et son commit unique, avec le journal durable de préparation des
fichiers existant. Un échec après copie et insertion Brain rollbacke les deux bases ; le fichier préparé et
le journal restent conservés pour diagnostic. Il n’y a pas d’atomicité prétendue entre SQL et filesystem.
La destination d’une copie est refusée si occupée ou liée ; les pièces sont créées sans écraser des fichiers.
Les contrôles croisés conservent aussi revues PDF figées, livrables et enregistrements de réunion.

**Qualification ciblée, pas livraison complète :** 24 cas v8 ; 64 cas finaux archive/sauvegarde/file ; groupe de 51 tests archive/worker/HTTP/sauvegarde ;
64 tests des contrats documentaires, transactions et sauvegardes ; 135 tests des archives L1–L4 et de portabilité.
Les groupes se recouvrent. Trois cas finaux vérifient l’indexation des pièces ; un cas combiné transporte
document Office, revue PDF, livrables et audio Brain. Ruff conforme. Preuve :
`.ui-preview/xpilot-l5/document-jobs-archive-focused.json`. Aucun nouveau résultat complet Python ou
frontend/navigateur n’est revendiqué. Interface par lot, publication explicite, qualification complète et
activation restent à terminer. L5.4–7 et L6–L9 restent obligatoires ; L0–L4 seuls restent actifs sur Agent 8001.

## Préparation par lot — interface et recette sur copies, 7 octobre 2026

Le parcours reste dans **Projets → Documents → Préparer un document**. Après chaque aperçu,
confirmer les informations puis « Ajouter la trame vérifiée au lot ». Le lot conserve la sélection,
les corrections et les empreintes de cet aperçu ainsi que la révision actuelle du formulaire. Une
autre trame peut ensuite être choisie ; une même trame se remplace explicitement. Limite : huit
trames distinctes. Le lot ne sauvegarde pas implicitement les choix du formulaire.

« Lancer le lot » conserve un identifiant de commande et un contenu stables jusqu’à réception du
résultat. Après une réponse perdue ou un conflit, « Réessayer la même soumission » évite un doublon
et garde les choix. Leur abandon est explicite ; consulter l’historique avant de créer un nouveau
lot. « Interrompre l’attente » annule uniquement l’attente locale : le serveur peut avoir enregistré
la commande. L’arrêt du traitement reste une autre action, avec révision vérifiée.

Le compteur est celui des **fichiers traités sur les fichiers du lot**, sans compter les essais comme
de nouveaux fichiers. Chaque copie prête reste disponible ; les fichiers en erreur montrent leur
motif. La reprise conserve les réussites. Les essais et événements sont paginés. Une lecture tardive
ne remplace pas une révision plus récente reçue après commande. Le lecteur consulte et télécharge ;
les lots importés/restaurés suspendus restent consultables sans reprise. Un worker indisponible bloque
soumission/reprise, mais conserve lecture et arrêt. La disponibilité réelle vient de `GET /jobs`.

`DocumentBatchPanel.tsx` est activé uniquement par `workspace.batch_available` ; un schéma dormant ne
déclenche aucun appel de file. Les requêtes du volet masqué s’arrêtent et les réponses tardives sont
ignorées. Les choix non soumis participent à l’alerte de navigation. `projectDocumentJobs.ts` borne
les lectures à 15 secondes et les commandes/téléchargements à 120 secondes, même avec signal parent.
Les réponses de lots sont vérifiées contre le projet courant. Les copies exigent reçu non publié,
nom UTF8 sûr et SHA-256 réel des octets ; les URL Blob sont libérées.

Qualification : **398 React**, groupe ciblé **71 cas Documents**, TypeScript et build conformes,
Ruff conforme. Aucune source Python de production modifiée dans cette étape ; la qualification Python
complète commune est prévue après publication. Recette réelle sur deux nouveaux serveurs fictifs,
avec le vrai worker : deux trames relues, 0/2 en cours puis 2/2 terminées, deux essais et cinq événements,
réouverture clavier après rechargement, lecteur sans commandes. Répéter le même POST conserve un seul
lot. HTTP vérifie les octets des deux copies pour propriétaire/lecteur, refus 403 des écritures et
404 du projet hors périmètre. Les 18 sources, 18 lignes et 129 cellules historiques sont intactes.

Limites de recette : le lien Blob est affiché après vérification, mais l’outil IAB n’a pas confirmé
l’événement d’enregistrement final après clic (délai de 15 secondes). Aucune recette mobile validée
dans cette étape. Ces limites ne sont pas présentées comme des résultats acquis. Preuves :
`.ui-preview/xpilot-l5/document-jobs-ui-frontend.json`, `document-jobs-ui-browser.json` et captures JPEG.

La publication réseau explicite reste à implémenter avant la qualification globale et l’activation.
Le serveur Agent 8001 conserve L0–L4 ; XPilot 8000 est inchangé. L5.4–7 et L6–L9 restent au périmètre.

## Publication : aperçu et IO ancrée — qualification ciblée, 7 octobre 2026

Le nouvel aperçu POST `/api/v1/projects/{project_id}/documents/artifacts/{artifact_id}/publication-preview`
reçoit seulement `link_id` et `relative_directory`. Il vérifie le projet avant toute configuration/sonde,
la copie gérée et son reçu de réussite, le lien de destination propre au projet et un dossier déjà présent.
Il ne crée aucun dossier, fichier ou événement. Le nom de sortie provient de la copie figée, jamais du corps
de commande. Capture : révision de lot, SHA/taille de copie, lien et son empreinte, dossier/identité persistante,
nom de sortie, occupation et empreinte de politique. `preview_sha256` lie ces éléments à la relecture.
Le lecteur consulte l’aperçu avec jeton/origine habituels ; il reste interdit de publication. Les historiques
importés/restaurés restent suspendus. Le POST d’aperçu est expressément classé comme consultation dans le garde
commun ; les autres commandes restent protégées, vérifiées par le contrôle des routes enregistrées.

**Paramétrage distinct :** `AGENT_DOCUMENT_WRITE_ROOTS` est une liste JSON de dossiers absolus serveur,
vide par défaut. Les racines `AGENT_DOCUMENT_ROOTS` de lecture n’accordent aucune permission d’écriture.
`AGENT_DOCUMENT_DRIVE_MAPPINGS` conserve les mappings explicites de lecteurs. Aucun disque ou partage n’est
codé en dur. Un lien/fichier hors racine, chemin relatif traversant, dossier absent ou lié est refusé.
`can_publish` exprime seulement l’éligibilité de l’aperçu ; le routeur annonce encore
`publication_command_available: false`, car les intentions/reçus durables ne sont pas raccordés.
L’interface ne propose encore aucun bouton de publication.

`document_publication_io.py` ouvre les dossiers existants par handles. Sous Windows, tous les ancêtres restent
ouverts en lecture de répertoire sans partage WRITE/DELETE ; renommage, remplacement et jonctions sont refusés
pendant l’opération. La copie candidate est créée exclusivement par `NtCreateFile` relatif au handle du dossier,
écrite puis fsyncée et vérifiée. Les points de réanalyse de fichier sont refusés. La promotion utilise
`NtSetInformationFile` avec un nom simple, parent courant du fichier ouvert et remplacement désactivé. Elle ne
réouvre pas le parent pour écrire et n’utilise pas un chemin absolu recomposé. Une collision conserve le fichier
existant et le candidat, même avec des octets identiques. Les handles sont invalidés à la fermeture du contexte.

Le reçu préparé bas niveau contient l’identité persistante native, la taille et le SHA-256 réel. La reconnaissance
après promotion/coupure exige ces trois éléments ; un fichier seulement copié avec le même contenu est refusé.
Une panne de fsync conserve le candidat diagnostique. Les noms UTF16 accentués et hors BMP sont vérifiés sur NTFS.
La branche Linux utilise des descripteurs de dossiers sans suivi de liens et relie le descripteur ouvert via
`/proc/self/fd` ; elle conserve le candidat pour éviter une suppression sous course. Cette branche n’est pas
revendiquée qualifiée dans l’environnement Windows actuel. Un filesystem sans identité stable échoue explicitement.

Contrats Microsoft consultés pour l’ABI et le renommage dans le même parent :
[FILE_RENAME_INFORMATION](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information),
[OBJECT_ATTRIBUTES](https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes).
Ces références ne remplacent pas les essais réels ni la recette du partage SMB de l’entreprise.

Qualification ciblée : **125 tests**, dont 22 IO réels Windows et 20 cas d’aperçu/HTTP, avec 83 cas de garde,
HTTP de file, archive v8 et sauvegarde. Ruff conforme. Sources frontend inchangées par empreintes depuis les
398 React/TypeScript/build précédents. Aucune recette UI de publication, aucun nouveau résultat Python complet,
aucune migration de production ou écriture dans un dossier d’affaire réel. Preuve :
`.ui-preview/xpilot-l5/document-publication-destination-focused.json`.

À terminer : intentions et reçus SQL durables, commande idempotente et reconnaissance explicite après coupure,
remplacement choisi avec sauvegarde de l’original et contrôle d’identité au dernier moment, transport typé de
ces historiques sans rejeu, interface de relecture/publication, puis qualification commune et activation
sauvegardée sur 8001. Le refus de collision actuel ne remplace pas le parcours de remplacement prévu au plan.
L5.4–7 et L6–L9 restent obligatoires ; Agent 8001 conserve L0–L4, XPilot 8000 est inchangé.

## Publication durable et transport — qualification ciblée, 7 octobre 2026

Le POST `/api/v1/projects/{project_id}/documents/artifacts/{artifact_id}/publish` reçoit `link_id`,
`relative_directory`, `command_id`, `expected_revision`, `expected_preview_sha256` et `reviewed: true`.
La relecture est un booléen strict : ni `1` ni une chaîne ne suffisent. Le chemin relatif est normalisé avant
capture. Aucun nom de sortie, chemin absolu, politique, auteur ou champ financier n’est accepté du client.
Le nom de fichier vient de la copie validée. L’aperçu annonce désormais `publication_command_available: true`
dans le worktree, sous réserve d’éligibilité et de racines d’écriture explicites ; l’interface n’est pas raccordée.

Le service vérifie portée et droit d’écriture avant le verrou ou toute sonde de fichiers. Il refuse une session
SQL portant des modifications étrangères à cette commande. Le lot doit être terminé ou interrompu et non
suspendu. Un verrou OS `document-publication.lock`, dérivé de la base SQLite persistante et distinct du verrou
du worker, sérialise les publications entre processus ; un fichier ou PID de verrou seul n’accorde aucun droit.
L’aperçu courant, sa révision, le lien, la politique d’écriture, l’identité du dossier et les octets de la copie
gérée sont revérifiés. Aucun dossier n’est créé ; une destination occupée est refusée.

Trois événements immuables sont ajoutés aux six tables existantes, sans DDL ni nouvelle base :
`publication_requested` capture la commande exacte, son empreinte, l’aperçu et le nom serveur du candidat ;
il est commité **avant** la création exclusive du fichier. `publication_prepared` contient identité native,
taille et SHA réels après fsync ; il est commité **avant** promotion. `publication_succeeded` contient le même
reçu, après vérification du fichier final. Chaque événement avance la révision CAS du lot. SQL et système de
fichiers ne constituent pas une transaction atomique ; candidats et fichiers sont conservés lors d’une panne.

La même commande exacte après réponse perdue ou coupure ne régénère rien. Avec un reçu préparé durable, elle
vérifie le fichier final ou promeut le candidat déjà préparé, uniquement si identité, taille et SHA concordent.
Un succès historique dont le fichier final est absent ou remplacé est signalé, jamais recréé. Des octets
identiques dans un autre fichier ne suffisent pas. Sans reçu préparé commité, l’intention reste `requested` :
inspection requise, candidat conservé et nouvelle commande vers cette copie/destination refusée tant que la
situation est incertaine. Aucune récupération au démarrage ni reprise automatique d’écriture réseau.

Le GET `/api/v1/projects/{project_id}/documents/jobs/{job_id}/publications` est paginé et borné. Il consulte
les intentions, états et reçus sans sonde réseau ni verrou. La commande figée et l’aperçu historique sont rendus
pour permettre une reprise explicite après rechargement. `needs_inspection` distingue une intention sans reçu.
`can_resume` dépend du droit courant, de l’état du lot et de sa suspension ; le service recontrôle ces conditions.
`network_published` dans un journal indique un reçu historique de succès, pas une vérification actuelle du réseau.
Lecteurs et projets hors portée restent protégés par les gardes HTTP et internes, avec jeton/origine habituels.

Le validateur offline exige formes fermées, empreintes canoniques, liaison à une copie avec reçu de génération,
séquence intention/préparé/succès, reçu final égal au reçu préparé et candidat unique. Les événements postérieurs
à une importation ou restauration sont refusés, même avec des empreintes recalculées. L’archive v8 conserve
les textes et acteurs d’origine ; le dernier `archive_imported` porte, quand nécessaire, `publication_bindings`
séparant les références courantes d’artefact/lien des captures historiques. Le lien de destination est transporté
indépendamment du lien source de génération, y compris dans la déclaration des liens disparus. Deux imports
successifs et la sauvegarde/restauration globale sont vérifiés sur des stores fictifs ; tous les lots restent
`execution_blocked` et ne reprennent aucune publication. Les fichiers de verrou ne sont pas copiés en sauvegarde.

Les coupures avant création, avant commit du reçu préparé, avant/après renommage et avant commit de succès sont
qualifiées sur de vrais fichiers Windows fictifs, ainsi qu’une panne réelle de commit SQL simulée, les collisions,
fichiers modifiés/absents/recopiés, verrou interprocessus, droits et HTTP, et les journaux falsifiés. Aucun dossier
d’affaire réel n’est écrit. Le partage SMB métier et la branche Linux restent non qualifiés.

À terminer dans L5.3 : remplacement **explicitement choisi avec sauvegarde conservée de l’original** et contrôle
de son identité au dernier moment, interface de relecture/publication et consultation des reçus, puis qualification
commune Python/Ruff/React/TypeScript/build, mobile/téléchargement navigateur et activation sauvegardée sur 8001.
Le refus de collision actuel ne remplace pas ce parcours de remplacement. L5.4–7 et L6–L9 restent obligatoires.

**L5.3 — publication durable sans remplacement qualifiée dans le worktree, 7 octobre 2026.** L’API enregistre l’intention avant la création exclusive, le reçu préparé avant le renommage, puis le succès après vérification du fichier final. Répéter la même commande vérifie identité persistante, taille et SHA sans recréer les octets ; sans reçu préparé durable, le candidat reste conservé pour inspection. Un verrou OS distinct sérialise les publications. Archives v8 et restauration globale conservent captures et acteurs, remappent les liaisons courantes et bloquent tout rejeu. **168 tests ciblés**, puis **35 cas commande/transport** sur la réponse finale (groupes se recouvrant), et Ruff conformes. Le frontend du contrôle précédent reste inchangé. Remplacement choisi avec sauvegarde, interface de publication et qualification commune restent à terminer avant activation. L0–L4 seuls actifs sur Agent 8001 ; L5–L9 restent au périmètre. Aucun partage métier écrit, aucune migration de production, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/document-publication-commands-focused.json` ; détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md`.

## Remplacement explicite avec original conservé — 7 octobre 2026

Les aperçus v2 et commandes ajoutent `replace_existing`, booléen strict et faux par défaut. Quand ce choix
est vrai, l’aperçu contient `existing_receipt` : identité native, SHA et taille de l’original régulier borné à
50 Mio. Original absent ou système sans déplacement natif Windows bloque le remplacement. Sans ce choix,
une destination occupée reste refusée. L’empreinte d’aperçu capture ce choix et le reçu de l’original ; le
service recontrôle l’original avant l’intention de publication et juste avant son déplacement par handle.

L’intention v2 fige un nom serveur `.agent-backup-<uuid>.bak` propre à cette publication. Après préparation
durable de la nouvelle copie, `publication_backup_requested` est commité avant le déplacement de l’original
vers ce nom, sans remplacement possible. Le même original est ensuite vérifié dans la sauvegarde ;
`publication_backup_saved` est commité avant le déplacement de la copie préparée vers le nom final. Le succès
requiert le reçu de sauvegarde correspondant à l’original relu et le reçu final correspondant à la copie.
La sauvegarde reste conservée dans le dossier de destination, sans suppression ni rotation implicite.

Ces deux déplacements ne sont pas atomiques ensemble. Entre eux, le nom final peut être absent ; si un tiers
y crée un fichier, la publication est refusée et les fichiers du tiers, la sauvegarde et le candidat restent
intacts. La même commande peut reconnaître la sauvegarde par identité/taille/SHA après coupure avant son reçu,
puis reprendre le candidat déjà préparé. Toute collision de nom de sauvegarde, identité différente même avec
les mêmes octets, original modifié ou sauvegarde perdue interdit l’adoption, l’écrasement ou la recréation.
Le succès historique exige encore la sauvegarde et le fichier final vérifiés pour une répétition de commande.

Le journal expose `backup` et `backup_receipt` ; les états intermédiaires sont `backup_requested` et
`backup_saved`. Ils peuvent être repris explicitement sous les mêmes contrôles de droits/politique/portée.
Le validateur fermé exige la séquence complète et les reçus correspondants, refuse candidats/originaux
confondus et noms de sauvegarde dupliqués. Le contrat v1 reste lisible avec ses anciens champs exacts, sans
ajouter de valeurs par défaut aux captures historiques. Archives v8 et restauration globale transportent
les preuves brutes sans accéder aux sauvegardes réseau et désactivent toute reprise après import/restauration.

Qualification sur vrais fichiers Windows fictifs : original conservé avec la même identité et les mêmes
octets, sept frontières de coupure/commit/renommage, collisions au dernier moment, original modifié après
relecture ou préparation, sauvegarde absente/recopiée, journaux falsifiés, historique v1, HTTP strict,
double import de projet et restauration globale avec reçus de sauvegarde. Aucun partage métier écrit.
Le remplacement est explicitement indisponible sur la branche Linux, où la promotion actuelle conserve un
lien candidat et ne déplace pas l’original ; ne pas présenter cette branche comme qualifiée pour remplacer.

Restent dans L5.3 : résolution manuelle explicite des intentions sans reçu préparé en conservant les candidats,
interface complète de destination/relecture/publication/reçus, qualification commune Python/Ruff/React/TS/build
et navigateur/mobile, puis activation sauvegardée sur 8001. L5.4–7 et L6–L9 restent au périmètre.

**L5.3 — remplacement documentaire avec sauvegarde conservée qualifié dans le worktree.** Le choix explicite lie la publication à l’identité, la taille et au SHA de l’original. Une intention de sauvegarde est enregistrée avant son déplacement ancré, puis le reçu de sauvegarde avant la publication de la copie préparée. Les coupures reprennent la même commande sans recréer les octets ; collisions et fichiers modifiés restent conservés. Le contrat v2 garde la lecture des historiques v1. 189 cas de régression et un cas HTTP supplémentaire passent, ainsi que Ruff. Double import v8 et restauration globale restent suspendus, avec reçus de sauvegarde intacts. Interface de publication et résolution explicite des intentions incertaines restent à intégrer, puis qualification commune et activation. L0–L4 seuls actifs sur 8001 ; L5–L9 en cours. Aucune écriture métier, migration de production, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/document-publication-replacement-focused.json`.

## Publication par copie et clôture explicite — 7 octobre 2026

Dans Documents → lot terminé/interrompu → copie prête, « Publier ou consulter les reçus » ouvre
le parcours de destination. Choisir un lien courant du même projet et, éventuellement, un sous-dossier
existant, puis « Vérifier la destination ». Un changement de dossier ou du choix de remplacement
invalide la relecture. La publication reste bloquée tant que l’aperçu et la confirmation humaine ne
correspondent pas. Le remplacement est opt-in ; le nom de sauvegarde et ses preuves figurent au reçu.

Avant POST, la commande exacte est enregistrée dans le stockage local du navigateur, sous une clé
projet/copie. Une réponse perdue, l’arrêt de l’attente ou un rechargement conserve cette commande.
« Réessayer la même publication » renvoie le même identifiant, révision et empreinte, sans nouvelle
création. Les historiques v1 gardent l’absence de `replace_existing` dans leur commande originale.
Un stockage local invalide bloque une nouvelle publication ; son abandon local est une action séparée
avec avertissement. Le reçu serveur constitue l’autorité, même si le navigateur a perdu sa commande.

GET `jobs/{job_id}/publications?artifact_id=...` filtre la copie avant pagination (20 lignes dans l’UI),
avec contrôle projet/lot/copie. Lecteurs, lots actifs et historiques importés/restaurés n’ont pas de
commande de publication/reprise. Le volet inactif arrête son polling et abandonne les attentes réseau.
Les écritures verrouillent les autres commandes du lot et conservent les saisies en cas d’erreur.

Une intention encore `requested` peut être clôturée via POST
`jobs/{job_id}/publications/{command_id}/abandon`, corps fermé
`{expected_revision: N, retain_files: true, reviewed: true}`. Les booléens doivent être littéralement
vrais ; la révision doit correspondre. Droits, origine et CSRF sont contrôlés avant toute action.
Le même verrou OS de publication exclut une clôture concurrente à l’écriture. L’événement immuable
`publication_abandoned` réserve définitivement l’identifiant de commande. Répéter la même confirmation
est idempotent ; une autre confirmation ou une clôture après préparation est refusée.

Cette clôture ne sonde, ne renomme, n’adopte et ne supprime aucun candidat ou fichier métier.
Après inspection, une nouvelle publication exige un nouvel aperçu, une nouvelle relecture et une
nouvelle commande. Le journal fermé et les archives v8 transportent également cette clôture ; import
et restauration globale continuent à suspendre toute exécution historique.

Recette navigateur sur nouveaux magasins fictifs : écrasement implicite refusé, remplacement explicite
avec sauvegarde native de même identité/taille/SHA, création d’une notice, reçus conservés après
rechargement, consultation lecteur sans reprise et ouverture des preuves au clavier. Les 18 trames
sources sont intactes ; seules révision et date du lot préexistant changent, avec huit nouveaux événements
de publication. Le sélecteur réseau long est contenu dans sa colonne : largeur réelle 390 px,
document 375 px après correction (1080 px avant). Le téléchargement Blob a été déclenché, mais l’outil
n’a pas fourni de fichier enregistré : ce dernier geste reste non qualifié. Aucun partage SMB métier
écrit. Serveurs fictifs arrêtés et onglets temporaires fermés ; Agent 8001 reste inchangé.

**L5.3 — interface de publication et clôture des intentions incertaines, 7 octobre 2026.** Documents permet de choisir la destination, relire, publier ou remplacer avec sauvegarde, puis consulter les reçus de chaque copie. Après réponse perdue, la commande exacte mémorisée est répétée ; une intention sans reçu préparé peut être clôturée explicitement en conservant tous ses fichiers. Droits lecteur, journaux historiques v1 et transport/restauration suspendus sont préservés. Qualification : 419 React, TypeScript, build et Ruff conformes ; 1345 tests Python / 1 ignoré, sortie 0. Recette réelle sur fichiers fictifs : création et remplacement, rechargement, lecteur et clavier, 18 trames intactes et identité de l’original sauvegardé conservée. Débordement des sélecteurs corrigé et vérifié à 390 px. L’enregistrement final du téléchargement Blob et le partage SMB réel restent non qualifiés. Activation L5 sur 8001 encore à réaliser ; L0–L4 seuls y sont actifs, L5.4–7 et L6–L9 restent au plan. Aucune suppression de données, migration de production, écriture métier, commit ou push. Preuve : `.ui-preview/xpilot-l5/publication-ui-common-checks.json`.

**Résultat final de la qualification Python L5.3.** Le même processus 47559 termine avec 1345 tests réussis / 1 ignoré, sortie 0 en 1473.15 s. Les sources du contrôle UI/publication restent identiques. Avec 419 React, TypeScript/build et Ruff conformes, la qualification commune passe ; téléchargement final du navigateur et activation sauvegardée sur 8001 restent à réaliser. L0–L4 actifs, L5–L9 en cours ; aucun commit/push. Preuve : `.ui-preview/xpilot-l5/publication-ui-python-full-terminal.json`.

## Installation au démarrage ERP9 — candidat du 7 octobre 2026

`backend.app.db.init_db()` appelle explicitement `install_document_schema()` et
`install_job_schema()` après les installateurs précédents. Avant toute DDL, les
validateurs des deux groupes vérifient colonnes, defaults, contraintes, indices
et protections ; un groupe partiel avec des données, ou une protection remplacée
par une instruction vide, est refusé. Les tables documentaires restent exclues
du `Base.metadata.create_all` générique. Importer les modèles ou lire une API
sur une base non installée ne crée donc toujours aucune table ni donnée.

Les deux installateurs partagent `ensure_backup()` avec les anciennes migrations :
une seule copie SQLite avant les modifications, aucune purge ou seed documentaire.
Version ERP9 enregistrée après installation. Le second lancement complet est
neutre et ne crée pas de sauvegarde supplémentaire. Le coordinateur existant peut
alors prendre son verrou OS et traiter les lots ; une identité lecteur ne lance
pas de traitement. Aucun démarrage ne publie un document sur le réseau.

Qualification sur copies : ancienne base ERP8 conservée cellule par cellule,
sauvegarde indisponible refusée avant DDL, formes/lots partiels ou incompatibles
refusés, vingt protections installées, consultations HTTP neutres, worker propriétaire
au repos sous verrou et worker lecteur désactivé. Le premier groupe compte 71
régressions réussies et un échec d’URL dans un nouveau test HTTP ; cette fixture
est corrigée, puis les onze nouveaux cas passent. Une nouvelle suite complète
est lancée sur le même code (session12398, rapport JUnit persistant à son terme).

Le candidat est distinct de C:/Agent. Ses 409 sources produit/tests correspondent
au worktree, et 377 sources déjà présentes dans l’installation restent exactes.
Sur une copie des données actuelles ouverte en lecture seule pour l’acquisition,
ERP9 conserve 17762 cellules ERP et 108134 cellules Brain, dix projets ; le
second démarrage et cinquante consultations Documents/Cockpit/Revues sont neutres.
Cette copie en ligne n’est pas la sauvegarde coordonnée préalable à l’activation :
un arrêt contrôlé, une sauvegarde des deux bases et fichiers gérés, une restauration
hors ligne qualifiée, la publication des seules modifications vérifiées et la
vérification du serveur unique 8001 restent nécessaires. XPilot8000 reste intact.

**L5.3 — raccordement du démarrage ERP9 qualifié sur copies.** Le démarrage explicite valide les deux groupes documentaires avant toute DDL, installe quatre tables de formulaires et six tables de lots avec vingt protections après une sauvegarde commune, puis enregistre ERP9. Imports et création générique ne remplacent pas les installateurs. Aucun formulaire, réglage ou lot n’est créé implicitement. Onze cas de démarrage passent, ainsi que les régressions déjà exécutées et Ruff ; la suite complète du raccordement continue sur la session 12398. La qualification précédente du parcours de publication termine à 1345 Python / 1 ignoré et 419 React. Sur snapshots actuels, les dix projets et 125896 cellules historiques sont conservés ; HTTP et second démarrage sont neutres. Le candidat conserve 377 fichiers canoniques et vérifie l’équivalence de 409 sources produit/tests. Deux écarts de fichiers racine sont explicitement revus : aucun pin/hash existant retiré, une notice de provenance ajoutée. Régression complète, sauvegarde/restauration coordonnée, activation et vérification sur 8001 restent à terminer. Le geste final de téléchargement navigateur et le SMB métier restent non qualifiés. L0–L4 seuls actifs, L5.4–7 et L6–L9 restent au plan ; aucune écriture canonique, suppression de données, opération XPilot8000, commit ou push. Preuve : `.ui-preview/xpilot-l5/erp9-registration-progress.json`.

**Régression complète du raccordement ERP9 terminée.** Le processus12398 termine avec 1356 tests Python réussis / 1 ignoré, sortie0 en 1496.34s ; rapport JUnit et sources vérifiés. Le démarrage et la conservation des données sont déjà qualifiés sur copies, ainsi que Ruff et le frontend inchangé (419 React/TS/build). Sauvegarde/restauration coordonnée et activation vérifiée sur8001 restent à réaliser ; le téléchargement final navigateur reste non qualifié. L0–L4 actifs, L5–L9 en cours, aucun commit/push. Preuve : `.ui-preview/xpilot-l5/erp9-full-python-terminal.json`.

**L5.4 — socle notes et recette HTTP dans le worktree, 7 octobre 2026.** Trois tables et neuf protections SQL conservent notes, versions et références de pièces ; le contenu structuré fermé couvre texte mis en forme, titres, listes/cases, tableaux et références d’images gérées. Création/édition/restauration utilisent une commande stable et une révision ; réponse perdue et concurrence n’ajoutent pas de doublon. Les captures, acteurs et reçus sont immuables ; seul le gel monotone d’une ancienne commande est autorisé pour la restauration. L’historique HTTP est paginé en métadonnées, avec lecture séparée d’une version. 37 cas notes/core/HTTP et Ruff passent ; 244 régressions archives/sauvegardes passent (groupes se recouvrant ; les derniers ajouts du service notes sont couverts par les 37 cas actuels). Sur snapshots des dix projets actuels, démarrage, lectures et refus de création conservent exactement les bases, sans table/ligne de note, backup implicite ou worker ; ERP reste en version9. Suite complète en cours sur65938 (PID30844, JUnit notes-core-full-python.xml). Frontend inchangé, précédent contrôle419 React/TS/build. Les API ne sont pas enregistrées sur le serveur actif ; éditeur/autosave, stockage réel des pièces, import XPilot et transport v9/restauration globale restent à réaliser. Les anciens transports refusent provisoirement les notes peuplées avant sortie, au lieu d’omettre leurs historiques ; ce refus sera remplacé par le transport complet. L0–L4 et le socle Documents restent actifs sur8001 ; notes, comptes, visas et L6–L9 restent en cours. Aucun changement applicatif canonique, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-core-progress.json`.

**L5.4 — pièces jointes de notes en recette, 7 octobre 2026.** Le worktree ajoute stockage géré et API multipart interne : 5 Mio par fichier, 20 pièces/25 Mio par note, copies sans écrasement, empreinte contrôlée et réponse perdue rejouée sans nouveau fichier. Les copies non validées en base restent conservées. PNG/JPEG/WebP sont décodés et bornés (image statique, 16 millions de pixels) avant aperçu ; Office et autres formats restent des téléchargements, avec noms sûrs et en-tête nosniff. 15 tests fichiers/HTTP et Ruff passent. La suite complète65938 signale des échecs : une fixture v5 ajoutait les tables dormantes de notes à un ancien format. La correction garde le validateur strict ; 100 cas v5/core passent (groupes se recouvrant). La suite complète lancée avant cette correction et ces ajouts ne qualifie pas l’arbre courant ; laisser son processus terminer puis contrôler le résultat et lancer une qualification du nouvel état. Aucune API de notes/pièces n’est enregistrée sur8001. Import volontaire XPilot/Office, transportv9/restauration globale, éditeur/autosave et activation restent à réaliser. Documents restent actifs ; racines réseau réelles attendues. Aucun changement canonique, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-files-progress.json`.

**L5.4 — résultat terminal de la régression initiale.** Session65938 terminée : 1335 tests réussis, 58 échecs, 1 ignoré ; les échecs concernent les fixtures v5 de contrat/store, qui ajoutaient les tables dormantes de notes à un ancien format. La correction est qualifiée par100 tests ciblés ; 15 cas fichiers/HTTP passent également. Ce résultat initial ne qualifie pas le code corrigé ni les pièces ajoutées ensuite ; une nouvelle suite complète est requise. Aucune activation des notes, modification canonique, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-initial-full-terminal.json`.

**L5.4 — nouvelle qualification complète lancée.** Après le résultat terminal65938 et la correction des fixtures v5, la suite de l’arbre courant utilise session10312 (PID30592), rapport `notes-corrected-full-python.xml`. Sources figées dans `.ui-preview/xpilot-l5/notes-corrected-full-running.json` ; ne pas arrêter/recommencer ce processus sur un simple délai d’observation. Résultat encore en cours, pas une qualification complète acquise. Import/transport/éditeur et activation des notes restent à réaliser ; Documents restent actifs sur8001. Aucun changement canonique ni commit/push.

**L5.4 — import volontaire préparé hors sources figées.** Prototype de recette dans `.ui-preview/xpilot-l5/notes-import-stage/` : conversion TipTap fermée, aperçu des fichiers explicitement sélectionnés, empreinte source et empreinte de la décision, historique complet déclaré contrôlé, repli texte choisi explicitement. Les blocs/styles non représentables bloquent l’import riche ; aucune URL d’image n’est téléchargée. Les acteurs source restent des descriptions, et les auteurs historiques absents ne sont pas inventés. Un conteneur indépendant conserve tous les octets sélectionnés (JSON/html/txt, versions, pièces), sans extraction et avec inventaire vérifié. Office reste en consultation/téléchargement. Limites préparées : 200 fichiers/50 versions/50 Mio de sources, 2 Mo par contenu, 20 pièces/25 Mio avec5 Mio par pièce ; Office externe seul et originaux sont distincts de cette dernière quota. 54 cas de conversion/aperçu/conteneur et Ruff passent. Ce prototype n’est ni installé ni inclus dans la suite complète10312 : ses247 fichiers runtime restent exactement figés, et le processus PID30592 continue. Il reste à raccorder acquisition bornée, provenance SQL immuable et copie/reprise/idempotence, puis archivev9/restauration, éditeur et activation. Aucun endpoint d’import disponible sur8001, aucune modification canonique ou source XPilot, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-import-stage-progress.json`.

**L5.4 — format réel de l’éditeur XPilot vérifié.** `ProjectDocumentsPanels.tsx` utilise contentEditable/execCommand et sauvegarde HTML + texte, sans mettre nécessairement à jour le JSON TipTap généré par le backend. Il insère aussi les images en dataURI et les cases de liste dans le HTML. Le prototype refuse désormais un JSON dont le texte diffère du contenu source actuel ; aucun ancien contenu n’est choisi silencieusement. 55 cas et Ruff passent dans un rapport distinct `notes-import-stage55-python.xml`, qui remplace les 54 cas préparatoires. Le rapport de ces54cas avait été réutilisé pendant la révision : utiliser uniquement le reçu55courant pour les hashes actuels. La conversion HTML fermée, l’acquisition des images intégrées en blobs décodés, le style barré, la provenance/copie SQL et le parcours complet restent à réaliser. Ces prototypes sont hors des247sources figées de la suite complète10312, toujours en cours ; aucune activation ou modification canonique. Preuve : `.ui-preview/xpilot-l5/notes-import-stage55-progress.json`.

**L5.4 — socle notes/fichiers entièrement qualifié, encore dormant.** Session10312 terminée exit0 : 1408 tests Python réussis/1 ignoré,1504.56s ; les247sources figées restent identiques, Ruff conforme. La correction de fixturev5 est incluse, sans assouplir les archives. Le prototype d’import55cas est séparé et n’était pas inclus dans cette suite ; HTML réel/dataURI/style barré, provenance SQL/copie gérée/reprise, archivev9/restauration globale, éditeur/autosave et activation restent à réaliser. Aucune API de notes/pièces/import n’est enregistrée sur8001, qui conserve Documents/ERP9. Aucun changement canonique, suppression, commit/push. Preuve terminale : `.ui-preview/xpilot-l5/notes-corrected-full-terminal.json`.

Écran Notes interne : `web/src/components/ProjectNotesPanel.tsx`, `NoteRichEditor.tsx`, `web/src/lib/projectNotes.ts` et `project-notes.css`. Les droits de liste proviennent de l’opérateur serveur (`can_edit`, `operator_id`), jamais du brouillon local. Une liste dormante conserve son contrat précédent sans création de schéma. La validation fermée des brouillons refuse les versions booléennes, commandes altérées et liens exécutables. Le collage introduit seulement le texte sélectionné ; les commandes de mise en forme restent locales au navigateur. Les API Notes demeurent non enregistrées ; la recette8797 est temporaire et utilise uniquement une nouvelle base fictive.

## Complément du 11 octobre 2026 — raccordement du Studio et conservation des Notes

Ce complément décrit l'interface de fusion actuelle ; les statuts dormants et
recettes de worktree ci-dessus conservent leur portée historique. Le Studio
réutilise l'éditeur partagé Notes, sans réécrire les modules Documents/Notes
hérités. Sa nouvelle disposition montre Notes personnelles et propositions dans
le groupe gauche, avec l'assistant à droite ; les deux dispositions précédentes
restent disponibles. Les panneaux restent montés lors du changement de
disposition, avec un seul éditeur, et s'empilent à 670 px et moins. Une préférence
locale conserve le choix de disposition.

La note liée à la séance reste la Note ERP canonique, avec ses identifiants,
révisions et versions. Les brouillons riches et Markdown gardent l'identité
stable de séance ; l'éditeur de projet garde ses clés projet/note/opérateur.
La conversion Markdown est explicite : un buffer invalide ou non appliqué
bloque sauvegarde, amélioration et publication, sans émettre de contenu invalide.
Une version externe modifiée ne remplace pas silencieusement ce buffer.
Les onglets Documents visités restent montés et le cache du Shell reste séparé
par identité de projet ; les sous-modules XPilot ne sont ni retirés ni absorbés
par le Studio. Le rail compact Sources/Réunions ne s'applique pas à ces projets.

Dans Sources, une Note canonique ou un texte de transcription sans fichier
reste sans format de fichier reconnu. Type de source et Format sont distincts,
sans modifier la source/version visée par un téléchargement ou une citation.
[Le reçu du complément](../logs/foresight-runtime/source-format-followup-20261011/combined-final.json)
qualifie 80 cas frontend, puis un sous-ensemble Shell de 15 cas après le dernier
ajustement de focus ; ces passages se recouvrent. Les 102 cas backend,
TypeScript/build et l'API fictive isolée sont des preuves séparées. Les rapports
historiques restent intacts ; aucune nouvelle suite globale n'est revendiquée.
Ce complément ne qualifie pas la fidélité publique à ±2 px, le matériel, une
réunion longue ni une exécution des moteurs sous coupure réseau physique.

## Suivi final du 11 octobre 2026 — Notes et disposition complète

Depuis Sources, **Nouvelle séance** ouvre le formulaire existant avec le projet
ERP accessible proposé ; un projet absent ou devenu inaccessible est écarté.
La garde des brouillons reste appliquée. Le clic prépare le formulaire, sans
création automatique de séance ni lancement du micro. La recette fictive
QA-FUSION-L12 a vérifié son ouverture et le projet proposé, sans soumission.

La disposition complète borne ses zones au viewport desktop et propose des
défilements clavier indépendants pour Notes, enrichissements et commandes.
Les trois dispositions gardent un seul éditeur partagé ; le brouillon riche
ou Markdown, ses conflits et la version canonique ne sont pas remplacés lors
du changement de disposition. La recette finale confirme la Note ERP version 2,
son cinquième bloc et la préférence complète après rechargement. Le menu et
le focus suivent les seuils CSS réels, avec navigation ERP conservée ; le flux
normal mobile à 320 px reste sans débordement horizontal (305/305 px).

[Le reçu global final](../logs/foresight-runtime/source-session-layout-followup-20261011-221310/qualification.json)
qualifie **694/694 tests frontend dans 75 fichiers**, TypeScript et build code 0,
avec `index-DhlxCsWr.js` / `index-DENGLpaQ.css` et les quatre SHA. Les 57 cas
ciblés d'entrée Sources et les suites précédentes se recouvrent ; les
[16 contrôles CUA](../logs/foresight-runtime/public-fidelity-final-20261011/DhlxCsWr/qualification.json)
restent une preuve séparée, sans micro, LLM, transcription ou publication.
Les assets Cqj et tous les reçus antérieurs sont préservés.

[Le rapport public après complément](../logs/foresight-runtime/public-fidelity-after-measurement-20261011.md)
documente les limites visibles : les cadres R02 à 850 × 479 mesurent seulement
117/78/204 px de hauteur, l'assistant commence à y254,5 contre environ 100 dans
la référence, et le document conserve 7 px de défilement global. R03 à deux
notes demeure non borné et commence à y396,7 contre environ 141. Ces zones sont
utilisables avec défilement ; leur présence ne qualifie pas une reproduction
publique exacte à ±2 px. Les observations de chargement ou de lignes ERP
cachées sont conservées et exclues ; aucune parité privée n'est revendiquée.

[La qualification runtime finale](../logs/foresight-runtime/completion-runtime-qualification-v4.json)
confirme le backend actualisé, **2051 tests Python réussis / 1 ignoré**, assets
servis identiques et trois flags renvoyés `false` (Studio, proactif, enrichissement
automatique). Le checkpoint `foresight-preactivation-20261011-202403-076435`
est vérifié. [La preuve de conservation](../logs/foresight-runtime/production-public-final-preservation-20261011.json)
compare exactement 18 tables métier protégées et 1340 originaux SHA ; elle
déclare 142 nouveaux inputs et trois inputs historiques modifiés par les
workers hérités, sans suppression, et ne prétend pas à l'égalité des 80 tables.
Capture matérielle, réunion longue et réseau physiquement coupé restent des
qualifications distinctes.

## Complément du 11 octobre 2026 à 21:34 UTC — Notes dans le Studio compact

**Préparation** porte les commandes secondaires et le retour projet protégé,
avec fermeture Échap et restitution du focus. Les trois dispositions desktop
gardent un seul éditeur, les mêmes notes/enrichissements et le même historique ;
leurs régions défilent indépendamment. Les brouillons riches/Markdown,
conflits, versions exactes, exports et gardes de publication sont conservés.
Les buffers locaux continuent de bloquer sauvegarde/amélioration/acceptation
et publication tant qu’ils restent à appliquer ou enregistrer ; ils ne
bloquent pas Pause/Arrêt et la conservation audio. La capture Windows unique
reste hors Préparation et ses commandes actives ne sont pas repliables.
Le flux naturel sous 671 px CSS demeure distinct du bornage desktop.

Sources garde le projet visible et les filtres montés dans un volet repliable.
Les quatre colonnes principales Format/Nom/Import/Labels conservent les
métadonnées type/projet/version/traitement dans des détails accessibles, avec
Original/version exact toujours disponible. L’éditeur de labels existant
exige une sélection et confirme un remplacement explicite ; aucun ajout
atomique aux anciens labels n’est annoncé. Ces changements de présentation
ne changent ni la Note ERP canonique, ni son outbox, ni ses snapshots cités.

[Le reçu de cette passe](../logs/foresight-runtime/studio-compact-followup-20261011/qualification.json)
qualifie **716/716 cas frontend dans 75 fichiers**, TypeScript/build code 0,
avec `index-Dj5PdhkQ.js` / `index-CU6ZruIv.css` et les quatre SHA. Les 132 ciblés
et les globals historiques se recouvrent ; le brut global-v1 avec un échec
de précondition asynchrone reste conservé. Les assets Dhl/DENGL et leurs
recettes constituent la baseline antérieure immuable.

[La preuve API de recette](../logs/foresight-runtime/studio-compact-followup-20261011/fixture-initial-api-and-assets-v3/qualification.json)
confirme uniquement la conservation de trois WAV silencieux synthétiques et
les états préparés de la séance fictive T12 : deux mic en attente/8 s, un
système en échec/5 s, zéro texte. Les durées par piste ne sont pas additionnées
comme retard mural ; une STT traitée ne devient pas une vérité relue. Aucun
micro, moteur STT ou LLM n’est appelé par ce passage. Les lectures de versions
et la recette navigateur de notes restent à vérifier sur ce build avant
clôture des usages ; la fidélité publique à ±2 px reste ouverte.

### Suivi CSS et conservation des Notes — 11 octobre 2026 à 21:43 UTC

Le [build CSS seul](../logs/foresight-runtime/studio-compact-followup-20261011/cascade-css-build-v2/qualification.json)
corrige la cascade de minimums de boutons à 786 px dans le desktop fusion
≥671 px, sans changement JSX, largeur ou partage des panneaux. Le mobile
≤670 px conserve ses minimums de 44 px. Le JS actuel `index-B0MSJycO.js`
a le même contenu SHA que Dj5 ; le CSS est `index-OmDJ_fGw.css`. Les 716/75
et TypeScript réussis sont des preuves antérieures liées dans un
[reçu distinct](../logs/foresight-runtime/studio-compact-followup-20261011/cascade-css-build-v2/inherited-checks-and-css-build.json),
sans nouveau passage de ces tests après ce changement CSS.

Le [contrôle SQLite neuf de la fixture](../logs/foresight-runtime/studio-compact-followup-20261011/fixture-postbrowser-readonly-v1/qualification.json)
retrouve la Note ERP en version 2 exacte après sauvegarde Markdown, avec
quatre blocs heading/paragraphe/liste/paragraphe, ses SHA et la version 1.
Les quatre IDs de séance et les trois fragments STT fictifs restent présents,
avec deux états pending, un failed et aucun segment. Aucun Recording, source
audio, compte rendu, action ou tâche n'est créé. Le label TXT reste exactement
`QA-` suivi de 77 `X`. Les SHA Brain/ERP et WAL sont identiques avant/après
la lecture seule. Ces 15 assertions recouvrent les contrôles de recette et
ne sont pas 15 tests React supplémentaires. La fixture ne fait appel à aucun
micro, moteur STT ou LLM ; la mesure de fidélité publique reste distincte.

### Portée acceptée — 11 octobre 2026 à 21:49 UTC

La [réponse utilisateur directe](../logs/foresight-runtime/user-scope-decision-20261011-drive-visual.json)
valide l'adaptation du Studio à Agent, avec l'éditeur riche XPilot, les panneaux
distincts et le partage notes/enrichissement égal. F25/T13 est clos **dans cette
portée adaptée**, sans affirmation d'exactitude ±2 px ou de parité privée Mac.
Les comparaisons historiques restent datées et consultables ; cette décision
ne dispense pas des autres recettes de capture, citations ou qualité IA.
Google Drive est exclu à la demande de l'utilisateur : capacité absente/false
masquée, connexion/import refusés avant réseau ou secret, aucun jeton, original,
version ou module hérité supprimé. Les Notes ERP et leurs snapshots conservent
leur autorité unique ; les imports locaux/URL et ICS restent disponibles.

Le [reçu ciblé Drive/mobile](../logs/foresight-runtime/drive-exclusion-followup-20261011-214949/targeted-ts-build-v1/qualification.json)
porte sur 61 tests Python Sources et 29 React, tous réussis, puis TypeScript,
Ruff et build code 0. Il recouvre les suites antérieures, sans nouveau global
frontend ; le global 716/75 précède ces changements. Les assets actuels sont
`index-Yuj98_lc.js` / `index-BJ0BE6LI.css`. Le bouton d'ajout d'élément de liste
du Studio mobile a un minimum CSS de 44 px, sans modification de l'éditeur
legacy hors Studio ou des minimums desktop ; le contrôle CUA est séparé.
