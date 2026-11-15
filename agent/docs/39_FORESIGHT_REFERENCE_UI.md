# Référence publique Foresight et adaptations Agent

Référence figée le 11 octobre 2026. Source primaire :
[Google AI Edge Foresight](https://developers.google.com/edge/foresight).
Périmètre retenu par l'utilisateur : **« Utiliser les écrans publics documentés »**.
Le contrat de référence porte donc sur les supports publics R01–R03 ci-dessous,
déjà examinés et documentés. Aucun exemplaire Mac installé n'a été manipulé.
Les écrans privés, menus masqués, police exacte et états absents de ces supports
restent des inconnues ; leur acquisition ne conditionne pas la recette du
périmètre public choisi. Aucune parité visuelle à ±2 px n'est déclarée.
Le choix de ces supports ne vaut ni renoncement à la reproduction exacte
demandée, ni validation des écarts visibles de l'interface Agent.

## Écrans observés et dimensions

| ID | Support primaire | Dimensions naturelles | État et gestes visibles |
|---|---|---|---|
| R01 | [Sources](https://developers.google.com/static/edge/foresight/assets/knowledge-sources.png) | 1280 × 800 | File list actif ; bouton Graph view visible, contenu du graphe non montré ; recherche, labels, formats, A–Z, liste/grille, ajout, réimport Drive, nouvelle capture |
| R02 | [Séance et assistant](https://developers.google.com/static/edge/foresight/assets/foresight-retrieval-live-and-chat.gif) | 850 × 479 | Notes à gauche ; Chat, Summary, Transcript, Live Q&A à droite ; capsule audio, pause, fermeture assistant, taille du texte, Live Enhance |
| R03 | [Notes enrichies](https://developers.google.com/static/edge/foresight/assets/enhanced-notetaking.gif) | 786 × 474, mesurées dans le navigateur après l'étude initiale | Notes originales et propositions enrichies côte à côte ; barre riche, Live Enhance, Standard, état de calcul, copie |

R01, R02 et R03 ont été réouverts dans le navigateur pendant la réalisation.
R01 est une capture statique ; R02 montre une variante de navigation Meetings,
alors que R01 montre Feed. Elles ne constituent pas une seule version démontrée
du produit. La copie exacte de menus non montrés reste indéterminée et n'est
pas un critère de conformité au périmètre public retenu.

La vérification documentaire locale retrouve ces trois liens officiels et
les observations associées dans
`.ui-preview/foresight-analysis-20261011/analyse.md`, sections 1 et 2.
Ce rapprochement préserve les preuves de l'étude initiale ; il ne prétend
pas constituer une nouvelle manipulation des écrans non publiés.

Repères visuels R02 à sa taille naturelle : rail environ 48 px ; contenu de
notes de x54 à x440, assistant de x449 à x842 ; intervalle environ 9 px.
La zone de titre et capture occupe environ 100 px, puis les panneaux environ
367 px. Ces repères sont des lectures de l'image, avec une précision de quelques
pixels ; ils ne constituent pas un contrôle différentiel à ±2 px.

R01 utilise un fond gris bleuté, des surfaces blanches arrondies, des sélections
bleu clair et des contrôles turquoise. La zone de contenu va approximativement
de x104 à x1264 ; les lignes documentaires sont proches de 48 px de haut.
Les étiquettes colorées représentent des formats. Aucun nombre du support
Google n'est réutilisé comme une statistique réelle d'Agent.

Une comparaison avant correctif, conservée dans
`logs/foresight-runtime/public-fidelity-measurement-20261011.json`, associe les
captures officielles affichées à leur taille naturelle aux rectangles DOM
d'Agent. R01 : contenu Agent x260/largeur 972,8 px, contre environ x104/1160 px
dans le support Google ; lignes simples Agent 78,45–78,85 px contre environ
48 px (la ligne publique à trois labels atteint environ 104 px). R02 : les
deux panneaux Agent commencent à y555,2 px dans un viewport de hauteur 479 px,
contre environ y100 px dans Google. Les PNG et métadonnées des trois supports
sont dans `public-fidelity-20261011/`. Les repères dans les images Google sont
des lectures visuelles, pas des mesures de leur DOM natif ou un différentiel ±2 px.

Deux lacunes fonctionnelles sont également identifiées : « Format » filtrait
le type générique de source au lieu du format de fichier ; la disposition avec
assistant masquait les notes enrichies. Les correctifs sont séparés des mesures
de densité et de coque ; leur qualification et le build correspondant sont
suivis dans le registre 38. Le moteur de notes repris de XPilot reste l'autorité
ERP, sans remplacement des notes historiques.

La mesure après correctifs du build `index-DhlxCsWr.js` est conservée dans
`logs/foresight-runtime/public-fidelity-final-20261011/DhlxCsWr/` et le rapport
AFTER distinct. R01 : Sources x104/largeur1160, tableau y384,1, lignes simples
51,35 px ; le cadre horizontal rejoint le support public, mais le tableau et
ses commandes restent décalés. R02 : en disposition complète, trois régions
visibles à 850 × 479, notes personnelles de 117 px et enrichies de 78 px,
assistant y254,5/hauteur204, page486 px. Ces dimensions ne reproduisent pas les
deux panneaux publics. R03 : la disposition enrichie à deux panneaux commence
à y386,7 sur 1105,8 px de hauteur à 786 × 474 ; une grande partie du contenu
reste hors de la première vue. Les différences sont observées et restent à
corriger ; aucun seuil ±2 px n'est déclaré atteint.

Le reçu navigateur DhlxCsWr passe séparément 16 contrôles de formats, préparation
depuis Sources, note ERP version2 et cinquième bloc après rechargement, préférence
de disposition, défilement clavier, menu/navigation ERP et présentation à 320.
Il ne lance ni capture ni moteur. Les observations pendant chargement et celles
englobant le tableau ERP masqué sont conservées et explicitement exclues du
compte, au profit des mesures limitées à la région visible. Les suites complètes
correspondantes passent 694 React et 2 051 Python/un ignoré ; leurs nombres
ne s'additionnent pas aux contrôles navigateur et ne qualifient pas les pixels.

## Contrat d'adaptation

| Zone | Reprise dans Agent | Écart ou proposition Agent explicités |
|---|---|---|
| Rail | Réunions, assistant, Sources, Stats, Préparation | Les projets et CDC & BE, Planning, Atelier, Documents, Mails restent accessibles dans le shell d'Agent |
| Séance | Notes + assistant à deux panneaux, onglets, capsule de capture | Identités ERP/Brain, conflit de version, attribution de projet et provenance sont exposés quand nécessaires |
| Notes enrichies | Original conservé et propositions avec citations | Acceptation ou rejet humain ; une proposition périmée ne peut pas remplacer une note récente |
| Sources | Recherche, labels, formats, tri, liste/grille, ajout, Drive | Le filtre projet applique les droits existants ; Drive demande une connexion propre à Agent |
| Graphe | Adaptation Agent : vue navigable des liens de projet et de provenance | R01 montre le bouton, sans publier le contenu ni les interactions du graphe ; Agent affiche uniquement les relations enregistrées |
| Stats | Adaptation Agent : mesures du fonds, captures, index et réponses | L'entrée Stats est visible dans le rail public ; son écran détaillé n'est pas montré. Formules propres à Agent et valeurs inconnues explicites |
| Préparation / Settings | Adaptation Agent : état des moteurs, activation, placement local/réseau | L'entrée Settings est visible ; ses écrans détaillés et son premier lancement ne sont pas montrés. Runtime Windows et profils d'index propres à Agent ; présence d'un modèle différente de son fonctionnement réel |
| Calendrier | Événement ICS choisi comme contexte | Pas de modification implicite de date contractuelle, pas de scheduler général |

## États à vérifier dans Agent

Pour chaque parcours : vide, chargement, prêt, erreur, indisponibilité moteur,
reprise, contexte périmé et lecture seule. Pour une séance : créée, en capture,
pause, interruption, finalisation, terminée et annulée avec fichiers conservés.
Pour les imports : en cours, reçu, extraction impossible, attente d'indexation,
réimport identique, nouvelle version et source distante absente.

Accessibilité : navigation clavier, noms des contrôles, focus visible,
notifications d'erreur, arrêt accessible à 670 et 320 px. La vérification de
ces états et ses captures relève du registre de recette L12.

Recette navigateur réalisée sur le poste le 11 octobre : Studio notes seules,
Sources et Préparation mesurés à 1280, 670 et 320 pixels. La largeur défilable
de la page égale sa largeur utile à chaque taille ; le tableau Sources garde
son propre défilement. Les mesures et captures sont dans
`logs/foresight-runtime/browser/*-responsive.json` et les images voisines.
Changement de disposition/onglet, rechargement du brouillon, clavier des onglets,
ouverture du PDF, fermeture du dialogue par Échap et ouverture d'un nœud Relations
ont été vérifiés. Publication et action sont consultées dans le projet fictif.
Ces preuves ne couvrent pas la navigation pendant capture matérielle ni une
comparaison Mac différentielle à ±2 pixels.

Une recette complémentaire sur l'interface réellement servie et des données
fictives isolées a ensuite exercé la note ERP version 3 : conversion Markdown,
sauvegarde et rechargement ; aperçu en lecture seule de la version historique
ERP 1 et du staging 1 ; conservation de la page physique citée dans l'inspecteur
PDF ; épinglage entre séances ; garde et récupération du buffer Markdown
invalide. Le [rapport UI final](../logs/foresight-runtime/browser-completion-20261011/qualification.json)
valide 21 contrôles qualifiés, sur le build servi `index-DKlOduK1.js`.
Pour les largeurs demandées 1280/670/320 px, les mesures réelles
client/défilement de page sont 1265/1265, 655/655 et 305/305 px.
Une vingt-deuxième entrée conserve l'essai initial à 670 px sur un autre
onglet ; elle est explicitement exclue du compte qualifié. Les captures,
états intermédiaires et anciens rapports restent conservés.

Le [contrôle SQLite après cette recette](../logs/foresight-runtime/browser-completion-20261011/database-after-ui.json)
valide séparément 29 contrôles en lecture seule sur les deux bases fictives :
intégrité, trois versions ERP et leurs SHA de snapshots, deux versions de
staging distinctes et épinglage durable. Aucun fichier de ces bases n'a été
modifié pendant ce contrôle. Il ne dispose pas d'une empreinte complète de
toutes les colonnes avant le parcours UI : il ne prouve donc pas leur
immutabilité historique globale. Ces contrôles de base ne s'additionnent pas
aux 21 gestes UI pour former une seule recette navigateur.

Les réponses de cette fixture étaient simulées ; ce passage n'a lancé ni LLM,
capture audio, publication, Drive connecté ou coupure réseau physique.
La confirmation native de départ a nécessité une annulation humaine, puis le
brouillon invalide a été restauré. Le processus de fixture précédait le
correctif UTC du staging ; ses cinq tests API de fuseau horaire sont une preuve
séparée. Cette recette de notes et de preuves ne qualifie pas la capture
matérielle ni la qualité industrielle de transcription.

## Limite de clôture visuelle

Ce document fixe les références officielles du périmètre public choisi.
La structure et les parcours d'accessibilité d'Agent ont des preuves de
recette. La comparaison des positions et tailles principales avec R01–R03
à ±2 px, aux dimensions de référence et avec contenu fictif identique selon
le plan 37, reste non qualifiée. La clôture de fidélité exacte publique
F25/T13 demeure ouverte, sans accès Mac privé requis. La présence des
contrôles et l'absence de débordement ne suffisent pas à atteindre ce critère.
Les variantes Feed/Meetings restent signalées. Graph, Stats et Settings sont
des adaptations Agent lorsque leur détail est absent des supports publics ;
leur documentation ne vaut pas approbation de tous les écarts visibles.

Les inconnues de l'application Mac complète demeurent des limites de
connaissance, sans exigence supplémentaire d'accès privé. Elles ne sont
jamais remplacées par une affirmation de reproduction exacte. Le lot L12
reste ouvert sur la mesure de fidélité publique, ses recettes matérielles et
de qualité industrielle connues ; l'absence d'écrans privés n'ajoute pas une
condition d'accès à cette recette.

## Complément public compact — build du 11 octobre 2026 à 21:34 UTC

La passe regroupe la hiérarchie intérieure R01 de Sources et les trois
dispositions du Studio. Sources présente titre/projet visible, onglets,
recherche, labels puis résumé/tri/liste-grille, avec filtres repliables
annonçant leurs valeurs actives. Les quatre colonnes principales conservent
les métadonnées complémentaires dans des détails de ligne. Les formats restent
des filtres réels, sans faux totaux par format ; la commande de labels ouvre
un remplacement explicitement confirmé sur la sélection existante.

Le Studio place le titre et **Préparation** sur une ligne compacte et borne
les trois dispositions desktop. Les notes et enrichissements empilés à gauche
avec l’assistant à droite reprennent la composition visible de R02 ; la
formulation antérieure disant qu’aucune référence publique à trois zones
n’était attestée est donc historique. Les commandes et métadonnées propres
à Agent restent des extensions visibles, sans suppression de modules hérités.
Un éditeur unique, buffers riches/Markdown, versions et navigation protégée
sont conservés ; Pause/Arrêt et la capture Windows active restent accessibles
hors du volet de préparation. Sous 671 px CSS, les panneaux restent en flux
mobile naturel. La file STT s’affiche aussi sans premier segment, sans
transformer état moteur, durée de fragments ou texte provisoire en qualification.

[Le reçu build](../logs/foresight-runtime/studio-compact-followup-20261011/qualification.json)
qualifie **716/716 tests React, 75 fichiers, TypeScript et build code 0**, avec
`index-Dj5PdhkQ.js` (SHA-256
`bba0ee0195a4865955fa82e624fcd946827727a694879f2c5f82d06d04dcbeca`)
et `index-CU6ZruIv.css`. Les 132 ciblés, anciens globals et contrôles navigateur
sont recouvrants et ne sont pas additionnés. Le premier global-v1 échoué et
les assets Dhl/DENGL demeurent conservés. Ce reçu ne prouve pas de géométrie UI.

La nouvelle recette utilise seulement des données fictives et des magasins
isolés sur localhost18003, sans micro, STT ou LLM. La séance T12 conserve des
WAV silencieux synthétiques avec états de file/échec préparés ; ses réponses
d’historique sont simulées. Elle ne qualifie ni la capture matérielle, ni la
qualité de transcription, ni une génération réelle. Aucun backend ou flag
canonique n’est modifié par ce complément frontend.

[Sources R01 — première mesure](../logs/foresight-runtime/public-fidelity-compact-20261011/Dj5PdhkQ/sources-r01-1280x800-bounds.json)
donne titre y92,5/h32, onglets y144,5/h36, recherche y190,5/h49, labels
y254,5/h40, résumé y310,5/h40, tableau y362,5 et trois lignes de fichiers de
48 px. [Studio R02 — première mesure](../logs/foresight-runtime/public-fidelity-compact-20261011/Dj5PdhkQ/studio-complete-r02-850x479-bounds.json)
donne panneau gauche x54/y100/largeur389,2/hauteur371, deux moitiés de185,5 px
et assistant x455,2/y100/largeur389,2/hauteur371, sans débordement de page à
850 × 479. Préparation ouverte est mesurée dans son état visible ; les rects
de descendants d’un détail fermé ne sont pas pris pour un popup réel.

Ces relevés sont intermédiaires. Dans R02 public, les largeurs/x et la barre
d’enrichissement diffèrent encore (environ y298 public contre285,5 Agent),
ainsi que les barres d’éditeur. Les supports publics n’exposent pas leur DOM ;
leurs repères sont des mesures visuelles approximatives. R03 et les usages
restent à compléter à ce stade. **F25/T13 à ±2 px reste non qualifié** : la
proximité des bandes et l’absence de débordement ne constituent pas une
reproduction exacte ni une dérogation aux écarts visibles.

### Suivi CSS seul — 11 octobre 2026 à 21:43 UTC

Le relevé R03 avant correction plaçait les panneaux à y112,8 : une règle
héritée de minimum 44 px sous 850 px augmentait la barre haute et l'en-tête.
Le [build CSS seul](../logs/foresight-runtime/studio-compact-followup-20261011/cascade-css-build-v2/qualification.json)
borne ce correctif au desktop fusion ≥671 px, avec minimum 32 px pour
Recherche et les commandes du Studio. La largeur actuelle est conservée :
la référence publique R03 est un repère visuel approximatif, pas une mesure
DOM autorisant un padding droit arbitraire. Le mobile ≤670 px reste à 44 px.
Le partage gauche de R02 et le JSX ne changent pas dans ce suivi.

Les assets actuels sont `index-B0MSJycO.js` et `index-OmDJ_fGw.css` ; le contenu
JS reste identique à Dj5. La [preuve des phases séparées](../logs/foresight-runtime/studio-compact-followup-20261011/cascade-css-build-v2/inherited-checks-and-css-build.json)
relie le global 716/75 et TypeScript réussis au build CSS suivant, sans annoncer
un nouveau global. L'[HTTP de fixture](../logs/foresight-runtime/studio-compact-followup-20261011/fixture-css-assets-v2/qualification.json)
confirme seulement les assets servis : JS/CSS/favicon exacts et HTML conforme
à sa normalisation de fin de ligne. Un HTTP 200 n'est pas un aperçu humain
ni une qualification visuelle.

R03 public montre une coque commune arrondie et une barre d'outils partagée
avant ses deux colonnes intérieures ; les deux cartes Agent restent une
différence visible à examiner. Le relevé après correction de cascade et les
barres intérieures de R02/R03 restent à comparer. **F25/T13 à ±2 px reste
ouvert**. Le [contrôle SQLite de recette](../logs/foresight-runtime/studio-compact-followup-20261011/fixture-postbrowser-readonly-v1/qualification.json)
qualifie la conservation des données fictives et les états T12 préparés,
sans capture, transcription réelle ni génération IA.

### Portée visuelle explicitement acceptée — 11 octobre 2026 à 21:49 UTC

La [décision utilisateur](../logs/foresight-runtime/user-scope-decision-20261011-drive-visual.json)
choisit **« Valider cette adaptation à Agent »** à partir du
[Studio réellement affiché](../logs/foresight-runtime/public-fidelity-compact-20261011/B0MSJycO/studio-complete-1280x800.png).
Les panneaux distincts, le partage notes/enrichissement égal et l'éditeur riche
XPilot sont acceptés dans cette adaptation, ainsi que les dimensions principales
de Sources. **F25/T13 est donc clos dans cette portée adaptée** ;
`exact_plus_minus_2px_claimed:false` et `private_mac_parity_claimed:false`
restent explicites. Les mesures antérieures et les différences visibles
conservées ci-dessus ne deviennent pas une égalité de pixels. Aucun autre
critère de qualification n'est levé par cette acceptation.

La même décision exclut Google Drive du périmètre livré, sans autoriser
connexion, import ou suppression de code/données. La capacité Foresight est
désactivée par défaut ; aucun ancien jeton n'affiche ou n'autorise la connexion.
Les commandes Drive sont masquées, les routes d'écriture/import refusent avant
réseau, et l'historique reste conservé. Les autres imports et modules XPilot
restent accessibles. Aucun redesign de coque R03 n'est engagé après cette
acceptation.

Le [reçu Drive/mobile](../logs/foresight-runtime/drive-exclusion-followup-20261011-214949/targeted-ts-build-v1/qualification.json)
réunit 61/61 ciblés Python Sources et 29/29 React dans deux fichiers, puis
TypeScript, Ruff et build code 0. Le global 716/75 est antérieur à Drive,
pas une couverture globale actuelle ni un nombre à cumuler. Les assets actuels
`index-Yuj98_lc.js` et `index-BJ0BE6LI.css` succèdent au B0/OmDJ sauvegardé.
Le seul complément géométrique est le minimum 44 px du bouton d'ajout d'élément
de liste dans le Studio mobile ; sa mesure CUA reste une preuve distincte.

### Dossier de référence complet L00 — 16 octobre 2026

Les trois supports publics sont de nouveau archivés avec SHA-256, dimensions naturelles et animations complètes. Les images intermédiaires ont été inspectées. Le contrat fige les9écrans et les25fonctions ; les fonctions absentes des supports sont nommées « spécification Agent ».
Le corpus fictif version1 fixe les mêmes identités/textes/états pour les comparaisons Agent de dispositions et de tailles. Il n’est pas injecté dans le projet métier. Les images Google restent des supports publics fixes ; aucune application Mac éditable ou nouvelle égalité au pixel n’est supposée.

| Écran | Référence et statut | Contrat Agent |
|---|---|---|
| UI-01 · Liste et navigation | R01 rail et R02 entrée Meetings ; liste détaillée : spécification Agent | Liste globale/projet, recherche et filtres ; ne pas inventer les menus Google absents |
| UI-02 · Créer, importer, démarrer et arrêter | R01 bouton Start a new recording ; R02 capsule ; configuration : Agent | Séance durable avant capture, projet optionnel, micro/système choisis, états et arrêt explicites |
| UI-03 · Notes et enrichissement | R03 et R02, adaptation XPilot acceptée | Notes personnelles et enrichies ; éditeur riche, Markdown et copie ; propositions distinctes du texte humain |
| UI-04 · Assistant et citations | R02 | Onglets Discussion/Synthèse/Transcription/Questions ; source/instant/version ; inconnues de menus nommées Agent |
| UI-05 · Bibliothèque | R01 | Formats/labels/recherche/tri/liste-grille ; pagination et projet selon contrats Agent ; Drive exclu |
| UI-06 · Graphe | Bouton R01 ; contenu et gestes : spécification Agent | Nœuds source/projet et liens de provenance enregistrés ; navigation clavier/zoom, aucune causalité inventée |
| UI-07 · Statistiques | Entrée Stats R02/R03 ; contenu : spécification Agent | Formules documentées, mesures réelles ; tokens et P95 inconnus restent indisponibles |
| UI-08 · Préparation et réglages | Entrée Settings R01/R02/R03 ; contenu : spécification Agent | Readiness séparée, opt-in, mode PC/réseau et premier lancement réouvrable ; aucun modèle installé déclaré opérationnel sans preuve |
| UI-09 · États transverses | États publics présents et spécification Agent pour les absents | Vide, chargement, calcul, prêt, erreur, indisponibilité, reprise, conflit, lecture seule et sortie périmée ; focus/clavier et arrêt mobile |

| Fonction | Écran | Référence ou spécification nommée |
|---|---|---|
| F01 · Liste des séances globale et par projet | UI-01 | R01/R02 + liste Agent |
| F02 · Nouvelle séance : note seule, import, capture | UI-02 | R01/R02 + création/import Agent |
| F03 · Démarrage immédiat sans projet choisi | UI-02 | Spécification Agent : staging sans projet |
| F04 · Capture micro | UI-02 | R02 capsule + choix des entrées Windows Agent |
| F05 · Capture audio système et voix distantes | UI-02 | Spécification Agent : loopback et voix distantes |
| F06 · Transcription en direct | UI-04 | R02 Transcript + moteur/horloge Agent |
| F07 · Voix, noms et corrections | UI-04 | Spécification Agent : relecture, voix provisoires et versions |
| F08 · Lecture et citations au bon instant | UI-04 | R02 sources/carte + localisateurs et lecteur Agent |
| F09 · Notes riches et Markdown | UI-03 | R03 éditeur + XPilot riche/Markdown accepté |
| F10 · Enrichissement automatique des notes | UI-03 | R03 Live Enhance + propositions sourcées Agent |
| F11 · Synthèse et compte rendu | UI-04 | R02 Summary + CR relu Agent |
| F12 · Ask global et chat ciblé | UI-04 | R01 Ask/R02 Chat + scopes Agent |
| F13 · Live Q&A et cartes proactives | UI-04 | R02 Live Q&A + proactif Agent |
| F14 · Catalogue, formats, labels, tri, liste/grille | UI-05 | R01 + pagination et droits Agent |
| F15 · Imports dossiers, fichiers, Drive et URL | UI-05 | R01 Add Source + imports choisis Agent ; Drive exclu |
| F16 · Recherche exacte, mots et sens | UI-05 | R01 recherche + EG2 et références Agent |
| F17 · Recherche images, schémas et audio | UI-05 | R02 source image + modalités Agent |
| F18 · Exploration par graphe | UI-06 | Spécification Agent derrière le bouton Graph de R01 |
| F19 · Statistiques et diagnostics | UI-07 | Spécification Agent ; écran Stats public absent |
| F20 · Réglages et premier lancement | UI-08 | Spécification Agent ; écrans Settings publics absents |
| F21 · Traitement local et hors ligne | UI-08 | Spécification Agent : chaîne locale et profils compatibles |
| F22 · Contexte de calendrier importé | UI-05 | Spécification Agent : événement ICS choisi, contexte uniquement |
| F23 · Informations et actions du projet | UI-04 | Spécification Agent : publication métier et tâches explicites |
| F24 · Export, récupération et reprise | UI-09 | Spécification Agent : exports, reprise et récupération |
| F25 · Fidélité visuelle et usage au clavier | UI-09 | R01/R02/R03 + adaptation Agent acceptée, sans parité privée/±2px |

Typographie Agent :14px/1.55 system-ui,-apple-system,Segoe UI,sans-serif dans meeting-studio.css ; icônes existantes de web/src/os/icons.tsx et de l’éditeur XPilot. La police exacte et les SVG de Google ne sont pas exposés et ne sont pas inventés.
Les métriques et différences géométriques historiques ci-dessus restent datées de leur build ; cette qualification de référence n’est pas une nouvelle recette de géométrie ni de capture. L’adaptation visuelle et l’exclusion Drive reposent sur les réponses humaines présentes dans cette conversation.
L’ancien fichier user-scope-decision-20261011-drive-visual.json cité plus haut est absent ; il n’est pas recréé comme preuve historique. Le nouveau contrat conserve explicitement cette limite.
[Contrat et corpus figés](../.ui-preview/l00-l08-qualification-20261016/reference-contract.json) · [Supports primaires](../.ui-preview/l00-l08-qualification-20261016/public-references.json).

### L06 — Studio commun, responsive et lecture au bon repère — 16 octobre 2026

Le projet conserve ses revues et anciens comptes rendus, avec une entrée vers le même
Studio que Réunions. Le projet reste filtré dans `/app/meetings?project=…`, y compris
après rechargement. Les changements passent par la garde de navigation existante.

Les panneaux sont égaux lorsqu’ils tiennent côte à côte, sinon empilés et défilables.
L’intervalle fractionnaire entre670et671pixels est couvert. Les fenêtres1280,800,
671,670et320pixels sont contrôlées dans le navigateur ; le viewport initial est rétabli.

Le lecteur des fragments est dans Transcription, avec son historique, et non caché
dans Préparation. Le seek attend les métadonnées et garde le dernier repère demandé.
L’API audio prend en charge une plage d’octets avec206/Content-Range et signale416
hors fichier. Droits et empreinte des originaux sont vérifiés avant réponse partielle.
Sur un WAV de silence fictif, le navigateur décode10s et démarre réellement à2s.

59contrôles de navigation/projet et95contrôles du Studio passent. Les15nouveaux cas
HTTP passent ; les25contrats de séance restent couverts par17réussites acquises et
8cas rejoués après correction de leurs chemins temporaires Windows, sans nouveau
total global. TypeScript, Vite et Ruff passent. Les échecs initiaux sont conservés.

Les parcours réels sur copies privées vérifient création, brouillons riches et Markdown,
conversion explicite, correction de transcription sans changer le timecode et accès
à la même note depuis le projet. Les fonctions métier héritées sont conservées.
L06 est clos selon ses critères d’interface ; le plan permet l’audio importé avant L03.
Aucun nouvel essai matériel, ASR, GPU ou LLM : L02/L03/L09/L11/L12 restent ouverts.
Sauvegardes et conservation SQL vérifiées avant activation8001. Détail : domaine47.
