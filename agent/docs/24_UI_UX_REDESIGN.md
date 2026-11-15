# Refonte de l’interface Agent

## Popup réservé aux étapes longues — 4 novembre 2026

Cette règle remplace l'affichage immédiat et le seuil de lecture de 800 ms
décrits dans l'historique du 13 octobre. Les lectures ordinaires, la navigation,
le polling et les petites écritures ne déclenchent plus le suivi global HTTP.
Les lectures de notes sont également silencieuses. Les chargements locaux,
erreurs des écrans et compteurs des tâches en arrière-plan sont conservés.

Le suivi automatique concerne les routes d'opérations longues reconnues :
import, analyse IA, transcription/OCR, export/préparation de fichier,
sauvegarde/restauration et tests IA. Les suivis explicitement nommés restent
possibles, notamment pour les opérations qui regroupent plusieurs étapes.
L'indicateur global n'apparaît qu'après deux secondes de suivi continu ; une
opération rapide se termine sans popup. Une opération longue reste suivie
jusqu'à sa fin, sans bloquer les contrôles. Aucun délai réseau, annulation ou
traitement d'erreur n'est changé.

Recette : 63 tests frontend ciblés conformes, TypeScript/Vite et Ruff conformes,
aucun avertissement UX sur l'indicateur. Sur Agent 8001, une vraie lecture du
portefeuille HTTP 200 retardée artificiellement de 3,5 s n'affiche aucun popup.
Les opérations rapides, seuil à deux secondes, fermeture, erreurs et annulations
sont couverts par tests isolés ; aucune génération IA réelle ni import métier.
Preuves privées : `logs/ux-quality/quiet-loading-20261104/`. La suite backend
globale n'a pas été relancée pour ce changement frontend.

## Options de l'assistant sur une ligne — 4 novembre 2026

« Conversation éphémère » et « Inclure les sources à confirmer » sont regroupées
sur une même ligne, au-dessus du choix du projet. Le paragraphe explicatif sous
la case éphémère est retiré dans les deux modes. Les libellés restent complets ;
dans un panneau étroit, leur texte peut se répartir sur plusieurs lignes en
gardant les cases côte à côte. Le défaut éphémère, le contexte, les historiques,
les commandes et les messages d'erreur conservent leur fonctionnement.

Validation : 18 tests ciblés de l'assistant passent, construction TypeScript/Vite
conforme, contrôle UX sans avertissement. Sur Agent 8001, les deux cases restent
à la même hauteur dans les panneaux de 520 et 300 px et sur un écran de 390 px,
sans débordement horizontal ; le paragraphe explicatif est absent.
Captures privées : `logs/ux-quality/assistant-options-20261104-{desktop,mobile}.png`.

## Rubriques regroupées dans Réglages — 4 novembre 2026

La barre latérale principale conserve Accueil, Projets, Mails et Réunions, puis
Réglages en bas. Sources, Informations, Suivi des analyses et Connexions & imports
sont déplacés dans les onglets de Réglages, au même niveau que Général, Mails,
Clients et équipe et Apparence. Aucun menu déroulant supplémentaire.

Une barre partagée indique la rubrique active sur chacun de ces écrans.
Les routes historiques restent disponibles, y compris les liens de citations
vers Sources, et sélectionnent le bon onglet. L'accès rapide conserve aussi
les destinations existantes. Les contextes et filtres, vues en cache,
protections des corrections non enregistrées et polling des traitements restent
inchangés. La navigation de projet et les fonctions métier sont conservées.

Recette : 49 tests ciblés frontend conformes, TypeScript/Vite conforme. Sur
Agent 8001 : parcours des quatre onglets, indication active et barre unique,
barre latérale réduite aux destinations attendues. À 390 px, tous les onglets
restent dans l'écran et passent à la ligne sans débordement horizontal ; le
menu mobile est conservé. Navigation entre onglets au clavier vérifiée.
Captures privées : `logs/ux-quality/settings-tabs-20261104/{desktop,mobile}.png`.
Quatre avertissements heuristiques UX relus sur le composant existant. Aucun
test backend global relancé pour cette modification frontend.

## Suivi des mails dans État du système — 4 novembre 2026

Temporisations ajustées : lecture des services toutes les 60 s, des mails
toutes les 30 s, délais HTTP de 20 s. Les retours de focus/visibilité ne
multiplient pas les lectures. Trois échecs consécutifs de lecture remplacent
un état connu ; une réussite remet le compteur à zéro. Les erreurs métier
reçues dans un statut restent immédiatement visibles. Les sondes backend
sont mises en cache 300 s et tolèrent un échec isolé après un état confirmé,
en conservant sa date d'origine. Un test LLM manuel conserve sa priorité et
relance immédiatement la lecture du témoin, même pendant une lecture en vol.
Les réglages et le panneau Thunderbird lisent la présence toutes les 30 s ;
elle expire après 180 s sans signal, avec la même règle dans les deux API.

Après au moins deux minutes de panne IA, un popup modal propose « Attendre
la connexion » (choix initial au clavier) et « Passer hors ligne ». Échap
enregistre l'attente. Aucun modèle local ne peut se charger avant l'accord,
contrôlé aussi côté serveur. Attendre ne provoque pas de rappels pour la même
panne ; le choix reste accessible dans le popup État du système. Le retour
confirmé du serveur ferme la proposition et réinitialise l'accord. Le choix
en erreur reste affiché et réessayable. Le dialog natif réutilise le style
existant, bloque le focus en arrière-plan et restaure le focus à la fermeture.

Le bloc d'activité des mails est déplacé de la barre latérale vers le popup
supérieur existant. Il conserve synchronisation, analyse, ajout à la recherche,
compteurs, erreurs, dernières activités et accès « Voir les traitements ».
Le suivi reste monté quand le popup est fermé pour conserver son état et son
rafraîchissement. Un échec mail ou une déconnexion remonte dans le témoin global ;
une analyse en cours reste également indiquée. Les détails des services sont
conservés. La navigation métier et les données ne changent pas.

Le popup défile lorsque son contenu dépasse la hauteur disponible. Sur 8001,
vérification réelle à 1280 px et 390 px : aucun bloc d'activité dans la barre
latérale, un seul dans le popup, aucun débordement horizontal sur mobile.
Tab puis Entrée sur « Voir les traitements » ouvre `/app/jobs` et referme le
popup. Les états d'erreur sont visibles dans le contrôle regroupé.

Validation : 45 tests ciblés frontend conformes, compilation TypeScript/Vite,
Ruff et contrôle de diff conformes. Quatre avertissements `ux:check` relus
(boutons nommés par leurs enfants et champ déjà nommé), sans nouveau blocage
identifié dans ce déplacement. Aucun test backend global relancé pour ce
changement frontend. Captures privées :
`logs/ux-quality/system-status-20261104/{desktop,mobile}.png`.

## Assistant éphémère et sources citées — 2 novembre 2026

Le chargé d'affaires peut interroger ses projets sans conserver de discussion.
La case « Conversation éphémère » est activée à chaque ouverture de l'application.
Les échanges restent dans l'état React courant ; aucune lecture ni écriture de
`assistant-threads`, ni stockage navigateur du texte, n'est déclenché. Masquer le
panneau le conserve en mémoire ; « Nouvelle discussion » ou le rechargement de
la page vide cet échange. Le contexte de suivi, la lecture progressive, Stop,
les citations et les relances restent disponibles dans le panneau principal.

Décocher l'option ouvre une nouvelle discussion avec historique local et donne
accès aux discussions déjà enregistrées. Recocher ouvre un échange éphémère vide.
Le changement est désactivé pendant une réponse, une sauvegarde, un chargement
ou une erreur de sauvegarde à résoudre. Aucun historique existant n'est supprimé.

Le lien « Consulter la source citée » d'un mail ou document ouvre désormais
`/app/sources?source=<id>` : le lecteur existant charge les données autorisées et
affiche le mail HTML avec ses styles, tableaux et images embarquées. Les images
distantes restent sur demande. Dans l'assistant principal, le clic simple ouvre
le lecteur sur place ; l'ouverture dans un nouvel onglet garde un lien utilisable.
Les preuves et les réunions utilisent le même lien de lecture. Les références de
versions de notes, les repères, l'audio et le téléchargement original sont conservés.
L'API JSON et les données sources ne sont pas modifiées.

Les tests ciblés couvrent l'absence d'appels à l'historique en mode éphémère,
le contexte des questions suivantes, les changements de mode sans fuite de texte,
le retour au défaut après remontage, la sauvegarde explicite, les citations et
l'ouverture du lecteur HTML depuis un lien direct.

Recette : 176 tests frontend ciblés passent (6 fichiers), TypeScript et Vite
passent, Ruff et `git diff --check` passent. `ux:check` relève 6 avertissements
sur les écrans existants (boutons nommés par leurs enfants ou `aria-label`,
champ de fichier masqué) ; aucun nouveau blocage identifié dans ce périmètre.
La suite backend globale n'a pas été relancée pour ces changements frontend.

Sur Agent 8001, le mail signalé est vérifié à 1280 px et 390 px : HTML et images
embarquées présents, aucune image distante chargée et aucun débordement horizontal.
La case est cochée par défaut, sans appel d'historique au démarrage ; le passage
avec/sans historique fonctionne au clavier. Cette recette navigateur ne qualifie
pas une nouvelle génération IA réelle. Captures privées :
`logs/ux-quality/assistant-ephemeral-20261102-{source,assistant}-{desktop,mobile}.png`.
Le frontend est construit sur place en conservant les anciens assets ; l'index
précédent est sauvegardé sous `.ui-preview/backups/assistant-ephemeral-20261102-165117`.
`/health` confirme Brain et ERP accessibles après activation, sans redémarrage.

## Réunions : boutons et en-tête compacts — 22 octobre 2026

Les boutons Démarrer et Enregistrer utilisent les tokens de couleur des boutons
d’Agent, y compris en thème sombre ; le bleu propre au Studio est retiré.
Les états actifs et le focus utilisent aussi l’accent du thème.

La bibliothèque retire sa description redondante et réduit ses espacements.
Dans le Studio, « Options » garde la préparation, les dispositions et les
exports. « Terminer » conserve son nom accessible « Terminer la prise de
notes ». L’audio alternatif reste disponible depuis « Autre audio » ; le choix
des périphériques regroupe leur diagnostic. Les avertissements sur les pistes
enregistrées, les erreurs et les commandes de récupération sont conservés.
Aucune note, séance ou donnée métier n’est modifiée par cette évolution.

Captures privées, sauvegardes avant modification et journaux de recette :
`logs/ux-quality/meetings-compact-20261022/`. Contrôle navigateur en consultation
sur Agent 8001 ; aucun enregistrement, rattachement ou enregistrement de note
déclenché. Le bundle est copié sans supprimer les anciens assets ; aucun
redémarrage du backend n’est nécessaire pour ces changements frontend.

Recette : l’en-tête du Studio testé à 1440 × 900 passe de 239 à 140 px
(environ 41 % de hauteur en moins). À 390 × 844, il mesure 313 px et la page
ne déborde pas horizontalement ; les outils de séance défilent au clavier.
Thème sombre vérifié par le réglage Apparence puis rétabli sur Clair.
Les options de préparation et le diagnostic des périphériques s’ouvrent sans
déclencher d’écriture métier. Les 1 000 tests frontend passent ; après le
dernier ajustement du texte audio et de l’accès aux revues, les 81 tests des
deux composants concernés passent aussi. Build TypeScript/Vite réussi,
avertissement de taille du bundle conservé. Contrôle UX : 121 fichiers,
61 avertissements heuristiques à relire. Backend inchangé : pas de nouvelle
exécution de sa suite globale pour cette correction de présentation.

## Corrections de l’audit — 22 octobre 2026

Les 20 constats ont leur correction dans le produit. Voir
[59_UX_CORRECTIONS_20261022.md](59_UX_CORRECTIONS_20261022.md) pour la matrice,
les captures privées, les tests et les limites. Confirmation de purge commune,
continuité de navigation, citations du projet, filtres repris dans l’URL,
progression et points CDC, compte rendu centré et états vides clarifiés.
Aucune suppression de module, de donnée active ou de validation humaine.

## Audit transversal initial — 22 octobre 2026

Le [rapport UX complet](58_UX_AUDIT_20261022.md) consigne la couverture réelle,
les preuves privées et 20 constats : 1 P0 de prévention, 3 P1, 13 P2, 3 P3.
Priorités : confirmation commune avant purge d’un mail, navigation disponible
malgré une panne du portefeuille, libellés accessibles et preuves depuis la vue
Informations du projet. Audit seul : aucune correction ou refonte appliquée.
Les modules métier, données et validations humaines sont conservés.

## Gouvernance UX/UI permanente — 22 octobre 2026

Les évolutions futures appliquent les règles de `AGENTS.md` et les skills
sélectifs de `.agents/skills/` : métier, textes utiles, composants existants,
navigation cohérente, clavier et accessibilité. Le contrôle heuristique est
intégré à la CI sans blocage sur les avertissements; Playwright MCP permet une
recette réelle sur données fictives et des captures des écrans concernés.
Cette installation ne modifie aucun écran. Voir
[57_UX_QUALITY_SYSTEM.md](57_UX_QUALITY_SYSTEM.md) pour les deux modes, les
versions, les tests et les limites observées.

## Fin des notes et accès au CR — 15 octobre 2026

**Terminer la prise de notes** est maintenant visible en tête des séances de
notes à préparer, hors de **Préparation**. Le clic conserve la séance puis ouvre
le panneau du compte rendu, sans capture, génération ni publication automatique.
Les brouillons non enregistrés et les captures en cours bloquent cette action.
940 tests frontend dans 89 fichiers, TypeScript, build isolé et Ruff passent.
Le correctif est servi sur Agent 8001 et son bouton a été vérifié dans le
navigateur réel, sans terminer ou modifier la note existante. Cette vérification
ne qualifie pas la capture physique ; L12 reste ouvert.

## Parcours visible vers le CR — 15 octobre 2026

Un bouton **Compte rendu** est maintenant visible dans les outils de la séance,
hors de Préparation. Pour une séance audio liée, le panneau ouvre directement
la transcription si elle manque ou doit être relue, puis le CR si la relecture
est déjà validée. Après **Valider la transcription**, le panneau passe au CR ;
**Préparer le compte rendu** et sa publication restent deux actions explicites.
Aucune capture ou génération n'est lancée par cette navigation.

Les résultats tardifs sont liés au projet et à l'audio sélectionné : ils ne
peuvent pas remplacer une autre séance, même après un aller-retour vers la
première. Les brouillons et la note restent conservés entre les panneaux.

137 tests ciblés dans six fichiers passent. TypeScript et le build passent
après correction d'une option de test incompatible avec ses types. Le build
isolé est publié sur Agent 8001, sans redémarrage, après sauvegarde des sources
et de l'ancien dist. Les anciens assets restent disponibles. Les assets servis
correspondent aux empreintes du build ; le HTML est comparé en texte, car le
serveur normalise ses fins de ligne. L'avertissement Vite sur la taille du JS
reste présent ; aucune nouvelle régression globale complète n'est revendiquée.

Le bouton a été cliqué dans le navigateur réel sur la séance existante
« test 1 » et ouvre le panneau attendu. Cette séance de notes n'est pas terminée :
sa publication reste correctement désactivée. Aucun contenu n'a été modifié,
aucun microphone ni modèle n'a été ouvert, aucun CR n'a été publié par ce clic.
L'ouverture automatique des étapes audio est vérifiée par les tests React ;
ce contrôle navigateur ne remplace pas une capture physique de réunion.
**L12 reste ouvert.**

[Preuve de publication](../logs/foresight-runtime/CR-workflow-UI-publication-ROOT-a83e079761f04e4789d024ad035e2672.json), [capture du bouton et du panneau](../logs/foresight-runtime/CR-workflow-access-20261015.jpg), [audit de livraison](../logs/foresight-runtime/CR-workflow-UI-delivery-ROOT-20261015.json).

## Régressions consignées — 15 octobre 2026

La suite Python générale termine avec **2 539 réussites, 1 ignoré, 54 sous-tests
réussis et deux avertissements**, sortie0 en53min25s. Le cas ignoré concerne le
dossier Infomaniak-IA absent. Des modifications sont intervenues pendant cette
suite : **143 tests ciblés supplémentaires passent après import frais** des
zones concernées, sur244 sources backend sans dérive. Les décomptes se
recouvrent et ne sont pas additionnés ; aucun instantané atomique du code
durant toute la grande suite n’est revendiqué.

La suite frontend au point de contrôle consigné passe **928 tests dans89 fichiers**, sans ignoré ni
dérive des238 sources épinglées. Le premier passage925/3 reste conservé ; ses
trois échecs provenaient uniquement de l’ancien libellé de bouton attendu par
un test d’intégration PDF/tableur/audio. Ces trois cas passent après mise à jour
de ce seul libellé, sans changement du parcours produit. TypeScript/build et
Ruff passent. Les quatre fichiers compilés isolément sont byte-identiques aux
quatre fichiers canoniques servis ; aucun asset n’a été remplacé. Des sources de
messagerie et le build ont ensuite évolué : le gel R8R2 les a recopiés et
identifiés. Les résultats de régression ci-dessus restent ceux de leurs
instantanés ; ils ne prouvent pas un nouveau passage global sur ce build.

Le serveur actif est sain, sous le profil utilisateur attendu, et son démarrage
est postérieur aux dernières sources pertinentes. Aucun redémarrage ajouté.
Le catalogue LLM réseau est joignable ; les trois modèles locaux déclarent zéro
instance chargée. Aucun modèle ni microphone ouvert par ces vérifications.
La branche groupée L03 reste désactivée (clé absente). La recette assistant
R8R2–R8R4 conserve trois passages arrêtés avant toute génération ;
le nouvel essai GPU V3 autorisé est **réussi dans sa portée diagnostique** :
16fragments des deux pistes,8arrivées à5s, sortie0 en51,75s. Les six paires
complètes à chaud demandent1,51 à1,79s ; aucun travail précédent ne reste en
attente à l’arrivée suivante sur cette courte cohorte. Le maximum GPU total
échantillonné est1,33Gio, sans garantie de réservation. Les sources, poids et
originaux sont inchangés. Le driver sort0 et le Job externe est déjà vide
avant cleanup ; le résident sort1 lors de sa fermeture contrôlée originale,
ce qui n’est pas une fin gracieuse exit0 de tous les processus.
L’accord unique est consommé. Aucun microphone, publication SQL/UI ou changement
de production. Des unités erronées restent présentes («380mAh», «16Mp») :
aucune précision industrielle, capacité soutenue, latence visible/P95 ou
endurance n’est qualifiée. Le refus cuBLAS précédent13,57s reste conservé.
Le raccord privé du profil GPU au code actuel est rebasé sur13sources
canoniques, avec quatre blocs protégés byte-identiques et la branche groupée
L03 conservée. Ses12unités fictives et sa revue source distincte passent.
Le helper GPU observe les propriétés natives avant loaded ; cette observation
reste à réaliser dans la future fixture complète. Le batch conserve son garde
CPU et refuse CUDA avant décodage.

La fixture de séance est désormais vérifiée avec le vrai stockage SQL privé :
trois cas terminent avec sortie 0, six bases passent leur contrôle d’intégrité.
Le cas nominal conserve quatre fragments et quatre segments provisoires,
sans doublon au rejeu ; les deux profils incorrects sont refusés avant toute
requête ASR. Notes et originaux restent conservés. **Le transport ASR et les
propriétés natives du modèle sont simulés dans ces trois cas.** La revue source
distincte confirme les résultats retenus et les 292 sources canoniques copiées.
Le premier essai de fixture, arrêté sur une erreur de lecture d’acquittement,
reste conservé et exclu de la preuve favorable. Aucun nouveau modèle lancé
ni changement des données actives. **Le raccord au GPU réel et au Studio reste
à assembler puis à qualifier** ; cette fixture ne clôture pas L03 ou L12.

Le raccord SQL est maintenant éprouvé sur une cohorte complète : seize
fragments reçus, acquittés, traités par les fonctions originales, puis relus
après commit, avec seize segments provisoires et aucun nouvel appel au rejeu.
Le second cas conserve les deux acquittements malgré une panne ASR simulée
au deuxième appel ; un seul fragment est terminé, l’autre reste en échec.
Le troisième cas ne reçoit aucun ready : le timeout et la deadline originaux
de start sont bornés au budget restant avant tout producteur, fragment ou
requête ASR. Le budget transmis est inférieur à 250 ms ; ce n’est pas une
borne OS sur toute la durée du contrôle, qui comprend aussi la fermeture.
Les trois cas V2 terminent sortie 0 ; six bases privées, dix-huit acquittements
et quarante-huit WAV à motif sont vérifiés après fermeture. Notes, versions et
originaux restent conservés ; les lecteurs et producteurs sont joints.
**Les réponses ASR et propriétés natives sont simulées.** Ces contrôles ne
valident ni la précision, ni le GPU réel, ni l’affichage ou l’endurance. Le
contrôleur matériel externe reste à assembler ; aucune activation dans Agent.
[Audit SQL de la cohorte V2](../logs/foresight-runtime/integrated-SQL-cohort-V2-ROOT-541ab17b1dcb4f42aac7e8c563946ae8/ROOT-post-terminal-audit.json), [revue distincte](../logs/foresight-runtime/integrated-SQL-cohort-V2-independent-source-review-20261015-cfa76327.json).

[Contrôle SQL réel, ASR simulé et limites](../logs/foresight-runtime/integrated-GPU-session-SQL-smoke-ROOT-b15766a857b04160b88956e33beb34c2/ROOT-post-terminal-audit.json).

[Raccord privé vérifié et limites](../logs/foresight-runtime/integrated-GPU-current-profile-V2-ready-ROOT-20261015.json).
[Résultat GPU réel et limites](../logs/foresight-runtime/direct-two-track-medium-gpu-61cd940dca4947b9bd2ec92975cb0757/ROOT-terminal.json). Audio intégré, qualité/latence,
endurance visible et saturation physique restent à qualifier : **L12 reste ouvert**.

**Interruption de processus : sept frontières réelles vérifiées.** Chaque cas
emploie deux fragments PCM fictifs complets de5s et les vraies fonctions
canoniques de journal, stockage SQL et reprise. Le contrôleur arrête son propre
processus après intention/WAV/manifeste/commit SQL/reçu, avec deux fichiers
partiellement écrits réellement conservés. Une autre instance effectue deux
rejeux : deux fragments, commandes et événements uniques ; note et originaux
inchangés, reçus conformes au SQL. Les14 bases privées passent quick_check et
les14 enfants ont leurs handles fermés. Durée21,05s, sorties19,77Mo, aucun
appareil, modèle, réseau ou donnée active impliqué. La première recette20ms
est conservée séparément. Cela ne qualifie pas un disque physiquement plein,
une coupure électrique ou une capture matérielle : **T16 complet reste ouvert**. Le compte courant ne possède pas le privilège Windows requis pour monter un volume virtuel isolé. Aucun disque créé, monté, formaté ou saturé. [Précondition vérifiée](../logs/foresight-runtime/T16-isolated-volume-current-prerequisite-ROOT-20261015.json).
[Preuves des arrêts et reprises](../logs/foresight-runtime/T16-process-crash-ROOT-25a790a9208a49698047505bd568ea8a/ROOT-post-terminal-review.json).
[Résultats, empreintes et limites](../logs/foresight-runtime/Current-regressions-completed-ROOT-ae3a993a9e074ef3a4fac48e08dcec20.json).



**Assistant : correction privée vérifiée, recette visuelle non qualifiée.**
R8R2 termine sortie 1 en 2,58 s : son garde refusait l’import des seules
définitions de live_speech, nécessaires au statut batch des séances. La copie
R8R3 autorise cet import, en conservant les interdictions de modèles, appareils,
sous-processus et workers audio. Un vrai contrôle SQL privé vérifie séance,
note conservée et statut batch original idle ; huit imports matériels restent
refusés, deux bases passent quick_check. Aucun modèle ni appareil ouvert.
R8R3 atteint son serveur privé puis expire à la préparation après 60,79 s,
le point CUA ayant réellement trouvé l’onglet sélectionné mais masqué.
R8R4 demande explicitement son affichage après ouverture ; le premier point
échoue encore, puis le contrôle suivant voit bien l’onglet visible. ROOT ferme
alors ce passage, sortie 1 en 51,60 s. La visibilité est donc intermittente,
pas déclarée définitivement indisponible. Les trois processus sont terminés,
leurs Jobs vides et handles fermés ; les deux serveurs ont fermé listener et
connexions SQL, leurs quatre self-pipes chacun ont fermé naturellement.
Aucune question, génération, requête d’embedding ou boucle proactive n’a été
lancée ; les trois résultats utiles et leur affichage restent à qualifier.
Les trois gels et revues sont conservés sans transformer ces arrêts en réussite.
Le contrôle final observe une instance locale chargée, puis un délai dépassé
sur le catalogue LLM réseau et le statut IA d’Agent (quatre secondes chacun).
Ces observations ponctuelles ne prouvent pas une indisponibilité permanente.
Le secours local reste sous la politique de déchargement au retour du réseau ;
ROOT ne force aucun déchargement pendant ce constat. [Observation finale](../logs/foresight-runtime/ROOT-final-network-observation-e849e9a6938f470eb64abac506f8f10e.json).

[Traces des passages et limites](../logs/foresight-runtime/Assistant-current-attempts-ROOT-3e23fb04a6c34093891d097b034126f2.json).

## Recettes privées : revues indépendantes terminées — 15 octobre 2026

La recette assistant R8 et le diagnostic GPU V2R1 ont une revue source distincte
favorable. R8 passe huit unités sur SQLite fictive avec réponses HTTPX simulées ;
le diagnostic GPU passe ses 72 contrôles fictifs. Ces résultats ne qualifient
aucun nouvel essai réel, aucune capture ni le P95. Aucun modèle ni microphone
n’a été ouvert pendant ces vérifications. Un nouvel accord GPU est demandé :
l’autorisation précédente était unique et a été consommée.

R8 prépare une vraie projection EG2 privée avant toute question, avec deux
appels embeddings originaux ; le futur essai reste à faire. Neuf descripteurs
historiques GPU (huit chemins) manquent sur disque : ils sont conservés comme
provenance indisponible, sans prétendre en revérifier les anciens succès.
Les dépendances exécutées et gardes actuels restent exigés avant lancement.

Le Studio contient bien « Démarrer la réunion » et « Périphériques ». Le document
est visible, mais le navigateur reste signalé masqué : aucune mesure de carte
visible n’est validée. Ruff passe sur app, backend/app et tests. La suite générale
L03 n’a pas encore de terminal observé au point 2026-10-15T09:52:12.079941+00:00 ; des sources ont changé
pendant son exécution, ce qui impose de vérifier les sources finales et les
tests concernés. L03, L09 et L12 restent ouverts.
[Preuve et limites](../logs/foresight-runtime/Qualification-source-reviews-ROOT-dbee566e51ee41ca87630fe1464507c4.json).


## État courant : activation vérifiée, recette réelle encore ouverte — 15 octobre 2026

Le backend a été redémarré une fois sous le profil utilisateur correct, puis
sa santé et le contrat Toutes / Textes / Images / Audio ont été vérifiés.
Le journal audio R4 est actif côté serveur ; cela ne prouve pas encore une
capture physique ni une transcription opérationnelle. La nouvelle interface
est publiée : ses trois fichiers statiques sont identiques aux fichiers
compilés ; le HTML correspond après la normalisation CRLF/LF existante du serveur.
Le Studio observé présente Démarrer la réunion et les sélecteurs Périphériques.
Aucun enregistrement démarré pendant cette vérification.

**Suite backend complète : 2 475 réussis, 1 ignoré, 15 sous-tests et deux
avertissements, en 50 min 52 s, sortie 0.** Le test ignoré concerne le dossier
Infomaniak-IA absent. Les 54 tests audio, Ruff et les 924 assertions frontend
déjà acquis sont distincts ; leurs décomptes ne sont pas additionnés.

Les comparaisons réelles avant/après redémarrage conservent toutes les cellules
Brain, les autres cellules ERP, les schémas, EG2 et 1 007 originaux métier.
Quatre lignes de suivi des workers présentent des changements précisément
consignés (dates, reprise de statut et remise à zéro de diagnostics de scan) ;
le journal diagnostic progresse séparément. Aucun état global inactif ni
snapshot atomique entre bases n’est revendiqué.

**Recherche multimodale sur nouveau corpus : essai CPU privé réussi.**
Quatre recherches d’images et quatre recherches de texte PDF retrouvent
la citation exacte au rang 1 ; six contrôles d’exclusion passent.
Réouverture de l’index et rejeu sans doublons vérifiés ; encodeur et
pilote terminent naturellement, Job vide et handles fermés. Durée totale
19,76 s, publications comprises. Les huit contrats purs passent aussi.
Cette preuve porte sur des rendus PNG/PDF fictifs, sans recherche audio
ni support CAD natif ni mesure d’affichage. Aucun index actif remplacé.
Le premier refus sur la limite de 64 Mio reste conservé ; la variante
corrigée surveille 512 Mio et exige 1 Gio supplémentaire libre.
[Preuves du corpus et limites](../logs/foresight-runtime/L09-heldout-actual-progress-ROOT-20261015-ae41367f0673479498a5529184fc8dea.json).

**Vérification canonique L03 : 64 cas et 39 sous-tests réussis.**
Ruff passe sur le backend, les tests et les nouveaux scripts.
La suite complète du projet est en cours sur bases fictives.
Les cinq retours de recherche audio privée sont corrects : deux
citations au rang 1, trois exclusions vides, réouverture et réimport
sans doublon. Les quatre conversions FFmpeg et le modèle CPU ont
effectivement travaillé ; le Job était naturellement vide.
Le terminal global du lanceur n’est pas observable après interruption :
ces preuves de composant ne clôturent ni L09 ni L12.
[Vérifications, portée et limites](../logs/foresight-runtime/L03-canonical-checks-ROOT-f95de1e1288d49bca3e49056250aac5f.json).

**Transcription groupée : code et tests intégrés, voie désactivée.**
La consolidation des fragments PCM contigus à la finalisation par lot
conserve les corrections, les citations et la transaction existante.
Huit fichiers produit et neuf fichiers de tests/fixtures sont livrés.
La copie produit passe 183 cas ciblés et 54 sous-tests. La suite complète
doit encore vérifier cette nouvelle livraison. Le réglage groupé reste
absent ou strictement False ; aucune activation ni migration de données.
**Recettes réelles encore ouvertes.** Medium a chargé en CUDA, puis
échoué au premier fragment ; son autorisation unique est consommée.
La recherche audio a été refusée avant FFmpeg/encodeur par le harnais.
Les derniers échecs de harnais restent conservés ; aucune réussite
audio, GPU, latence ou endurance n’est déduite des tests unitaires.
L’assistant a produit une réponse manuelle citée et un ajout automatique
visible ; sa réponse proactive reste sans preuve et la cohorte est refusée.
[Publication, sauvegardes et portée](../logs/foresight-runtime/L03-canonical-publication-ROOT-2e88d524ad9b4f08a838c6e4ec9d6ecf.json).

**Restent à qualifier : capture réelle, ASR industriel, double piste GPU et
délais visibles, assistant utile sous charge, recherche multimodale élargie
(audio et intégration active), incidents physiques/reconnexion LLM et chaîne
intégrée ≥60 min.**
L09, T16 physique et L12 restent ouverts. Adaptation visuelle validée et
exclusion de Drive maintenues. Aucun commit ni push. Les sections précédentes
ci-dessous restent l’historique de leurs essais, et non l’état courant.
[Résultats, sauvegardes et portée](../logs/foresight-runtime/Active-delivery-progress-ROOT-20261015-b5a4cb53e57c45e7960142a027cd6ecb.json).


## Sauvegarde réelle et journal audio R4 publié — 15 octobre 2026

La sauvegarde en ligne V4R1 est terminée et vérifiée : Brain, ERP et EG2,
trois restaurations sur copie et 1 008 fichiers gérés (939 008 115 octets).
Les bases sources restent inchangées ; leurs snapshots ne sont pas atomiques
entre bases. Le seul journal diagnostic agent.log est conservé au point de
coupe de 1 419 330 octets ; 260 octets ajoutés sont observés séparément.
Ses anciens refus et les 36 tests privés réussis restent conservés.

Six fichiers audio R4 sont publiés dans le canon avec quatre préimages et
deux absences déclarées avant mutation. Les 54 régressions canoniques passent,
avec 15 sous-tests distincts du décompte ; Ruff global et scripts audio passe.
La première collecte a échoué dans le harnais Popen, avant exécution des
tests ; son résultat est conservé. Le comparateur SQLite passe neuf essais
fictifs ; aucune conservation après redémarrage n’est encore déclarée.

**Rechargement backend, nouveau frontend et suite Python globale finale
encore en attente.** La suite globale est en cours ; son ancienne réussite
n’est pas présentée comme le résultat de cette version. Capture matérielle,
ASR industriel, débit/P95, L09, T16 physique et L12 restent ouverts.
Adaptation visuelle validée et Drive exclu conservés.
[Preuves et portée](../logs/foresight-runtime/Backup-audio-actual-progress-ROOT-20261015-24b4f526b6544936954f7b079f42152d.json).


## Journal audio et sauvegarde : vérifications privées réussies — 15 octobre 2026

Le candidat audio R4 passe deux cohortes distinctes : 20 cas SQL/producteur
simulé et 17 cas de fichiers, puis 37 cas de compatibilité adaptés.
Les anciens résultats R3 (26 réussites, 11 échecs) restent conservés.
Les 21 essais de sauvegarde V2 passent sur bases et originaux fictifs ;
aucune sauvegarde métier réelle réalisée par cette recette.
L’interface conserve ses 924 assertions réussies dans 88 fichiers.

**Prochaines étapes : sauvegarde réelle, activation contrôlée, puis qualification
matérielle et intégrée.** Aucun nouveau code audio promu, rechargement
backend ou nouveau frontend servi ici. Capture, ASR industriel, débit GPU,
P95, L09, T16 physique et endurance L12 restent ouverts ; Drive est exclu.
[Preuves et portée](../logs/foresight-runtime/R4-backup-private-progress-ROOT-20261015-a982f5ad38a34a7485f3c5dfa7825ef6.json).


## Recettes privées audio et interface ; régressions avant activation — 15 octobre 2026

Le journal audio R3 réussit 20 cas SQL/producteur simulé et 16 cas de fichiers,
avec 15 sous-tests signalés séparément. Quota, écritures partielles de reçu,
rejeu et retrait des droits sont vérifiés sur copies. Les 37 tests natifs
existants révèlent encore 11 échecs pour 26 réussites : fixtures sans séance
SQL et temporaires longs. Aucun correctif audio canonique promu à ce stade.

Les 924 assertions de l’interface passent dans 88 fichiers, avec 921 libellés
uniques (quatre paragraphes distincts partagent un libellé paramétré).
Le build Vite est produit dans un dossier privé ; API à recharger avant
publication. Les 68 contrats GPU/TokenUser passent avec des fakes uniquement.
La préparation de sauvegarde V1 est refusée ; V2 est préparée sans sauvegarde
métier exécutée. La suite Python globale précédente reste historique.
**Activation, audio matériel, ASR/P95, L09, T16 physique et L12 restent ouverts.**
Drive reste exclu. [Preuves et portée](../logs/foresight-runtime/Private-audio-frontend-progress-ROOT-20261015-ce5f2ca208c345819bbbedebb96a550d.json).


## Recherche par modalité intégrée dans les sources ; activation en attente — 15 octobre 2026

Les quatre sources du filtre Toutes les preuves / Images / Textes / Audio sont
intégrées et sauvegardées. Le choix explicite filtre le projet autorisé avant
classement, avec citations et exclusion des réponses devenues obsolètes.
19 cas backend privés et 15 cas React/jsdom passent ; après intégration,
46 tests canoniques ciblés, Ruff global et TypeScript passent.
**API à recharger avant publication du nouveau frontend ; aucun nouveau dist servi.**

Le journal audio V1R1 passe 16 méthodes sur fichiers fictifs, avec pannes
simulées et callbacks d'autorité/acquittement simulés. Son intégration SQL reste
à vérifier, notamment les écritures du reçu après commit ; il n'est pas activé.
Cela ne qualifie ni panne physique, capture matérielle, pertinence multimodale
ni délai visible. L'ancien essai CAO toutes modalités garde ses deux échecs.
La suite globale 2458 réussis + 1 ignoré est antérieure à cette intégration ;
aucune nouvelle suite globale exécutée, aucun ajout de ces décomptes.
L09, T16, P95 et L12 restent ouverts. Drive reste exclu.
[Preuves et portée](../logs/foresight-runtime/Modality-journal-progress-ROOT-20261015-43d7dc32e96c4423a1136cdf761c151a.json).


## Reçus audio corrigés dans les sources ; rechargement en attente — 15 octobre 2026

Le rejeu audio confirme désormais chaque fragment en SQL et répare atomiquement le reçu local, en conservant ses anciens octets ; ses 37 tests ciblés passent séparément du décompte global. Le rechargement d’Agent 8001 reste en attente : l’inactivité des jalons et des travaux documentaires et l’identité du module chargé ne sont pas établies. L’essai CPU CAO V1R1 a été refusé avant admission du moteur, avec 16 sources privées conservées et huit entrées échouées ; une copie V1R2 est en préparation privée, sans nouvelle recette exécutée. La QA du profil GPU privé passe dix contrats purs, sans mesure GPU, capacité, SQL ou appareil ; les droits NVIDIA, la recette couplée et L03/T16 matériel/P95/T12/L12 restent ouverts.

Suite backend globale : 2459 cas uniques, 2458 passés, 0 échecs, 0 erreurs et 1 ignorés ; sortie 0.

[Preuves et limites](../logs/foresight-runtime/Native-receipt-progress-ROOT-20261015-b4e62dea8c7f4273810916e806a195a7.json) · [Suivi détaillé](38_FORESIGHT_DELIVERY.md).


## Stop natif : arrêt et historique vérifiés — 14 octobre 2026

Une génération réelle sur le LLM réseau, avec données fictives et bases privées, a été arrêtée par le vrai bouton Stop après le premier texte. **Recette complète : 56,05968 s, sortie 0.** Texte partiel et citation conservés, enregistrés puis rechargés depuis l’historique réel ; aucun message technique trompeur, Réessayer ou erreur d’enregistrement dans ce périmètre Assistant. Notes, versions et sources protégées intactes ; ressources privées et Job fermés.

**L’ancien indicateur `native_Stop_UI_qualified_only` reste false.** Son intervalle de 24,8 ms chevauchait les effets locaux. **Le nouvel indicateur `native_Stop_UI_conservation_causal_addendum_v1` est true**, selon une nouvelle méthode évaluée uniquement sur les fichiers historiques : réception serveur du même clic réel, même UID/document/séquence, intersection de bornes sans modifier la borne inférieure ni les ordres stricts. Aucun nouvel essai et aucune réécriture des anciens résultats.

Conservation des 1 438 caractères appliqués à l’interface, avec citation ; deux caractères consommés côté serveur n’étaient pas appliqués. **Arrêt du calcul distant inconnu**, identité interne de l’erreur native non mesurée. Le correctif activé et les **924/924 tests frontend** restent documentés ; Ruff passe sur `app backend/app tests`, sans nouvelle suite pytest globale.

**Assistant global, L03 global, P95, T12 et L12 restent non qualifiés.** Droits précis NVIDIA en attente d’accord humain après refus automatique avant lancement ; aucun droit changé ni nouvel essai GPU autorisé ou exécuté dans cette progression. Les paragraphes datés suivants restent l’historique des états antérieurs.

- **Capture physique intégrée :** Aucun microphone ouvert par cette recette ; qualification matérielle intégrée ouverte.
- **Qualité transcription et voix :** Précision industrielle, voix et contexte restent à vérifier.
- **Débit deux pistes :** Medium CPU4 échoue à la cadence de 5 s ; candidat GPU préparé, essai réel encore requis.
- **Premier texte réellement visible/P95 :** Les 56,05968 s de recette ne sont pas une mesure de P95.
- **Assistant utile, priorité et annulation :** Stop local et historique vérifiés ici ; utilité représentative, cartes, tick et priorité sous charge intégrée ouverts.
- **Panne stockage pendant capture :** Les contre-épreuves SQL privées de consolidation ne qualifient pas une panne pendant capture.
- **Endurance intégrée :** Une génération courte ne remplace pas la recette complète d’endurance.
- **Audit final et activation qualifiée :** Assistant global, T12 et L12 ouverts ; adaptation visuelle acceptée et Drive exclu conservés.

[Preuves et limites](../logs/foresight-runtime/Native-Stop-addendum-status-ROOT-20261014-1f1ee78928c44947b5d0c727ca65818c.json).


## Historique — correctif Stop activé et préparation GPU, état avant la recette native du 14 octobre 2026

Le correctif du bouton Stop est activé dans l’interface du serveur unique Agent, sur 8001. Les simulations vérifient la conservation du texte partiel et des citations et le maintien des vraies erreurs réseau. **924/924 tests frontend passent**, dont 16 cas AssistantPanel ; TypeScript et compilation séparée réussissent. Les anciens assets sont conservés et l’index sauvegardé permet le retour arrière. **Le comportement natif de Stop reste à qualifier dans le navigateur ; Assistant, P95, T12 et L12 restent ouverts.**

[Preuves et limites](../logs/foresight-runtime/Assistant-Stop-UI-and-GPU-pure-progress-ROOT-20261014.json).

La préparation GPU a passé 54 contrôles simulés de cadence, provenance, mesures partielles, consentement et limites. Aucun GPU, DLL NVIDIA ou microphone utilisé par ces tests. La revue des sources autorise uniquement cette QA ; les lectures normales des dépendances, les droits précis en attente et un nouvel accord pour l’essai GPU restent requis.

Stop utilise un motif propre à chaque demande et masque uniquement l’erreur portant exactement ce même objet. Une erreur native distincte reste visible : les tests simulés ne prouvent pas la propagation du motif par le lecteur natif. Le fichier pnpm-workspace.yaml déclare le seul frontend racine ; les règles existantes de compilation esbuild sont conservées. La suite backend globale n’a pas été relancée pour cette seule modification frontend.


## Travail en cours : principe commun — 13 octobre 2026

Chaque action utilisateur lente doit donner un retour dès son lancement. Un
indicateur non bloquant, animé sans pourcentage inventé, reste présent pendant
les opérations suivies. Il s'annonce via `role=status`/`aria-live=polite` et
respecte la préférence de réduction des animations. Une lecture rapide ne
clignote pas : le seuil est 800 ms. Une requête terminée ne masque pas une autre
requête encore active. Les contrôles périodiques ne créent pas d'animation
permanente ; les tâches asynchrones gardent les compteurs métier déjà existants.

CDC : sélection → importation/extraction → actualisation → document rendu.
Le double clic est bloqué. L'identifiant importé est vérifié dans la liste ;
une erreur de relecture propose une actualisation sans doublon d'import.
Imports JSON, lectures de pièces jointes, notes, réponses IA progressives,
détection de périphériques et commandes audio ont un suivi sur leurs attentes.
Les ZIP de séances et téléchargements internes restent indiqués jusqu'aux
octets complets, avec reprise manuelle si le navigateur bloque l'enregistrement.

Validation : 916/916 tests frontend et 88 fichiers, TypeScript et build passés.
Le navigateur a montré l'indicateur immédiat et sa disparition lorsque le CDC
fictif apparaît. Le contrôle utilise le build réel et une API en mémoire avec
délais simulés, plus un contrôle de sélection de File virtuel propre à cette
recette. Le sélecteur de fichier natif n'est pas qualifié : son pilotage avait
dépassé la durée de la première recette. Aucun import dans les bases réelles,
microphone ou modèle utilisé. L'étape intermédiaire est vérifiée par les tests
différés, sans capture visuelle intermédiaire revendiquée.

[QA](../.ui-preview/pilots/async-feedback-20261013/qa/qualification.json) ;
[preuve navigateur](../logs/foresight-runtime/async-feedback-browser-verification-20261013.json).
Cette évolution reste dans Agent sur 8001, sans changement des règles métier.


## Notes et démarrage de réunion — état courant du 12 octobre 2026

Le Studio reprend la disposition de travail XPilot : liste des notes à gauche,
page de saisie large, barre de mise en forme compacte et sauvegarde en haut.
L’éditeur riche, les versions et les brouillons restent conservés. Notes
enrichies, transcription et assistant restent accessibles dans leurs vues.
Cette adaptation ne constitue pas une nouvelle preuve de fidélité à ±2 pixels.

Pour commencer : **Réunions → Nouvelle séance → Ouvrir la séance**. Si l’espace
est désactivé, le formulaire propose **Activer les réunions** en conservant
les autres réglages. **Source audio** choisit la salle (microphone), le son du
PC, ou le son du PC avec la voix. **Périphériques** expose les deux sélecteurs ;
le sélecteur sans rôle dans le mode choisi est grisé. **Démarrer la réunion**
reste visible. Choisir une source ou ouvrir une séance ne lance pas la capture.
La sortie choisie désigne le son à conserver ; elle ne change pas la lecture
Windows.

Après un arrêt Windows non confirmé, le Studio garde une alerte et propose
**Vérifier l’arrêt Windows** si sa réservation existe encore, sinon
**Conserver les fragments acquittés**. Cette seconde action est une conservation
partielle explicite, jamais une attestation de fin matérielle. Le bouton
générique de finalisation est masqué lorsqu’une récupération native est présente.

**802/802 tests React dans 81 fichiers** passent sur 218 sources inchangées,
TypeScript/build et Ruff conformes. Les assets actifs sur 8001 correspondent
au candidat vérifié. La [recette fictive courante](../logs/foresight-runtime/native-control-queue-20261012/current-evidence.json)
observe les sélecteurs, le démarrage, une seule action de conservation et
l’alerte, sans enregistrement, écoute ni modification de note. La régression
Python complète V2 termine à **2 190 réussis/1 ignoré** sur sources inchangées ;
le candidat STT isolé n’était pas inclus. Capture matérielle intégrée, qualité/latence
industrielles et tenue en charge L12 restent ouvertes.

Le candidat isolé d'admission STT ajoute une alerte de suspension, des compteurs
distincts et **Transcrire l'audio conservé** pour les imports personnels sans
projet. Sa durée zéro est affichée **Durée inconnue**. Son frontend V5 passe
816/816 et TypeScript/build sur 218 sources inchangées ; aucune activation
canonique n'en découle. La recette fictive confirme neuf éléments, dont les deux
sélecteurs actifs, sans acquisition ni traitement. Les erreurs de lecture
résolues disparaissent après reprise, sans masquer les refus de sauvegarde ;
neuf régressions couvrent ces gardes. La cause de transport initiale n'est pas
attribuée. La désactivation générale du batch est corrigée et relue. La
régression Python V2 termine à **2 300 réussis/2 ignorés**, exit0, sur 377
sources et 56 ressources inchangées, revérifiées dans le
[compagnon terminal V5](../.ui-preview/pilots/stt-admission-stage-20261012/qa/staged-checkpoint-v5-python-v2-terminal.json).
La conservation sous cadence fictive reste nécessaire avant promotion ;
le candidat reste isolé et L12 ouvert, sans qualification matérielle ou P95.

## Actualisation du direct et protection des corrections — 12 octobre 2026

Le Studio suit un flux local de notifications quand son panneau est visible.
Il regroupe les réveils, relit la séance par l'API autorisée et applique les
mêmes gardes de révision/curseur que les lectures périodiques. Le contenu des
événements n'est jamais appliqué aux notes ou aux segments. Une reconnexion
relit immédiatement l'état courant ; un échec de lecture garde le réveil à
reprendre. Le poll de cinq secondes reste un repli. Masquage/changement de
séance annulent le suivi et empêchent les réponses tardives de l'ancien flux
de remplacer la séance affichée.

Les corrections de texte ou de locuteur protègent aussi la fermeture/recharge
tant qu'elles sont différentes, en cours de sauvegarde ou incertaines. Un
volet masqué conserve son brouillon. Le bouton « Reprendre les fragments en
échec » utilise la commande durable et une révision relue ; il n'ouvre aucune
nouvelle capture. Préparation propose le direct séparément de la capture.

81 cas ciblés de l'éditeur passent ; le nouveau flux possède dix scénarios
de concurrence distincts et l'éditeur de correction quatre cas de fermeture.
La régression globale atteint 768/768 dans 80 fichiers, TypeScript/build passent.
Une recette textuelle fictive retrouve le segment et la note ERP v2 après
Sources/recharge (douze contrôles API/DB, quatre observations CUA). Le panneau
navigateur reste masqué et aucune latence événement/poll n'est attribuée.
Disposition validée
et moteur de notes XPilot conservés ; ces tests simulés ne mesurent pas la
latence réelle de transcription visible ni une réunion longue.

## Lectures concurrentes du Studio — 12 octobre 2026

Une réponse GET ancienne ne remplace plus une séance déjà reçue avec une
révision ou un curseur plus récent. Le brouillon est restauré sur la première
réponse acceptée, même si elle vient de l'actualisation périodique. Les saisies
restent conservées pendant les lectures et lors d'un ACK de sauvegarde ancien.
La disposition acceptée et la feuille de style `BJ0BE6LI` ne changent pas.

Cinq régressions reproduisent les courses avec des réponses différées : lecture
initiale/poll, deux polls inversés, note ERP plus récente avant ACK et deux
variantes de transcription seule avant ACK. Le [ciblé](../logs/foresight-runtime/studio-snapshot-order-20261012-final/qualification.json)
passe 106 cas ; la [globale](../logs/foresight-runtime/studio-snapshot-order-final-20261012-v2/qualification.json)
passe 724/724 dans 75 fichiers, sans addition des compteurs. TypeScript/build
passent. La [recette CUA/SQLite](../logs/foresight-runtime/studio-snapshot-delivery-20261012/browser-qualification.json)
retrouve la note ERP v2 exacte après Sources, recharge et réouverture, sur une
fixture 1280×720 avec tous moteurs/matériels désactivés ; neuf contrôles passent.
Les délais inversés restent des tests simulés, sans mesure de latence STT.
`CHpAuznx/BJ0BE6LI` est servi sur 8001, les trois capacités de séance restant
désactivées. Le build précédent est sauvegardé et aucun asset n'est supprimé.

## Épuration du 11 octobre 2026

### Correction Mails après utilisation

Le lecteur commence par l’objet, une seule ligne expéditeur/date, puis le corps
du mail. Le grand en-tête avec avatar et coordonnées ainsi que le bloc de
classement ne précèdent plus le contenu. « Détails du mail », fermé par défaut,
regroupe les coordonnées complètes, la réponse et l’original. La navigation
précédent/suivant rejoint la barre Mails avec la recherche et l’analyse.

Le classement reste dans le petit panneau de projets à droite : destination,
« Classer et suivant », vignettes et options. Les meilleurs candidats du mail
courant sont visibles pour le glisser-déposer, triés selon leurs scores existants.
Les autres destinations se déplient ; sans score, les destinations récentes sont
présentées sans probabilité inventée. Sous 540 px de largeur disponible, le
lecteur vient avant le panneau projets pour que les commandes ne repoussent pas
le contenu du mail.

Le suivi d’analyse était composé de blocs toujours affichés dès qu’un compteur
existait, y compris après traitement. Il devient compact : compteur, erreurs
et interruption restent accessibles, tandis que les détails peuvent se réduire.
Une mise à jour de progression ne rouvre pas les détails choisis par l’utilisateur.
Le menu Options se referme après le lancement d’une analyse.
Classement humain, dépôts de mails déjà classés, dossiers, pièces jointes et
traitement durable sont conservés. Aucun changement de moteur ou de données.

Qualification de la première correction de disposition, avant le dernier
ajustement centré sur le corps du mail : **518 tests React réussis** ; TypeScript,
build Vite et Ruff conformes. Vérification réelle sur Agent 8001 à 670, 1280 et
320 pixels, avec accès aux autres projets et repli, sans débordement de page ni
erreur console. Les gestes de classement et l’analyse sont testés sur fixtures,
sans lancer de traitement ni changer de décision dans les mails de production.
La suite Python de l’épuration générale ci-dessous reste la qualification du
backend inchangé ; elle n’a pas été relancée pour cette correction frontend.
Résultats : `logs/mail-layout-frontend.log`, `logs/mail-layout-validation.json`.
Les assets précédents sont sauvegardés dans `logs/mail-layout-original-dist`.

Qualification du dernier ajustement donnant la priorité au contenu : **519 tests
React réussis dans 62 fichiers**, dont les scénarios ciblés de lecture, détails,
navigation et classement sur fixtures. TypeScript, build Vite et Ruff conformes.
La vérification réelle sur Agent 8001 couvre les fenêtres 670 × 668, 1915 × 900
(dimensions de la capture utilisateur) et 320 × 800. Le corps commence
respectivement à 286,9, 255,5 et 364,8 pixels du haut de la fenêtre ; l’en-tête du
mail mesure 61,1 pixels sur les deux premières tailles. « Détails du mail » est
fermé au chargement ; son ouverture et sa fermeture ne déplacent pas le corps.
Coordonnées, préparation d’une réponse et original sont accessibles. À 320 pixels,
le lecteur précède les projets. Aucun débordement de page ni erreur console.

`/health` confirme Agent, Brain et ERP `ok` ; `/app/` et les deux assets du build
répondent HTTP 200. Aucun mail de production n’est classé ni analysé pour ces
contrôles. Le backend inchangé conserve la qualification Python de l’épuration
générale ; la suite n’a pas été relancée. Les modifications restent locales,
sans commit ni push. Preuves : `logs/mail-content-frontend.log` et
`logs/mail-content-validation.json` ; capture : `logs/mail-content-after.jpg`.
Les assets avant ce dernier ajustement sont sauvegardés dans
`logs/mail-content-original-dist`.

### Organisation générale

L’organisation retenue est **Projet dépliable** : les grandes rubriques restent
dans le menu de gauche et le projet sélectionné s’y déplie. Ses sept rubriques
conservent leurs URLs et fonctions. Recherche est accessible dans l’en-tête,
avec la navigation rapide au clavier par Ctrl K. Les favoris se déplient à la
demande ; l’activité mails et l’état système ne présentent plus en permanence
les journaux et les diagnostics techniques.

| Zone | Premier niveau | Détails et options |
|---|---|---|
| Accueil | Priorités et projets en cours | Liste complète des priorités, chiffres des projets |
| Projet | Travail, prochaines étapes, informations utiles | Fiche et équipe, sauvegarde, réglages d’affichage |
| Planning | Échéances et tâches | Modèles, planning de référence, comparaisons, historique |
| Documents | À remettre, fichiers/dossiers, notes | Préparation documentaire, versions et historique |
| Livrable | Fiche, fichiers, contrôles et validation | Historique, paramètres secondaires |
| Mails | Objet, expéditeur/date puis contenu ; projets et validation à droite | Détails du mail, autre projet, explication, score, dossiers et commandes |
| Réunion audio | Audio, transcription, compte rendu | Options d’enregistrement et d’analyse |
| Réglages | Général, Mails, Clients et équipe, Apparence | Recherche documentaire, modèles, sauvegardes et maintenance |

Les livrables ont une seule instance dans Documents > À remettre ; les accès
depuis cockpit, jalons et revues conservent le projet, document et contrôle ciblés.
Les outils du Planning gardent un raccourci vers les documents à remettre.
Chaque échéance conserve Modifier au premier niveau ; son historique et les
visas des livrables s’ouvrent dans Options. La saisie manuelle d’un compte rendu
se déplie à la demande, à côté du parcours audio.
Les vues sont cachées sans être démontées afin de garder brouillons et opérations.
Les éditeurs de création de livrable restent montés pendant le rafraîchissement.
Un refus de la confirmation de navigation ne change ni l’onglet local ni l’URL.

Les termes visibles deviennent concrets : Cockpit → Vue d’ensemble, Connaissance
→ Informations, BOM → Nomenclature, Exploitation → Sauvegardes et maintenance.
La sélection des dossiers Mails reste dans Options, avec un seul sélecteur.
Thunderbird distingue rédaction et suivi de la synchronisation ; les options
de classement et commandes destructives gardent leur conséquence explicite.

Les panneaux compacts n’annoncent pas une disponibilité fictive : accessibilité
IA, test de recherche, indexation, analyse et réception des mails restent distincts.
Progression réelle et erreurs restent visibles. `runtime.ready` bloque toujours
la transcription si nécessaire. Pendant un enregistrement, l’arrêt reste présent
au-dessus des trois onglets et dans le bandeau global ; revenir ouvre Audio.
Les corrections du responsable et de l’échéance d’une action audio marquent aussi
le compte rendu comme modifié avant de changer d’enregistrement.

L’évolution reste exclusivement dans le frontend React du même serveur 8001.
Aucun module, API, classement accepté ni donnée de production n’est supprimé.
La qualification porte sur conservation des brouillons, navigation, accès aux
options, disponibilité audio, compilation, tests et lecture navigateur. Les
sections datées ci-dessous décrivent les étapes antérieures de la refonte.

Qualification de l’interface : **512 tests React réussis**, puis **30 tests de
régression ciblés réussis** après les derniers libellés audio et le rangement
de la saisie manuelle. TypeScript, build Vite et Ruff conformes. Consultation
réelle sur 8001 : projet dépliable, outils et options des échéances, documents,
dossiers et explication des mails, réglages secondaires et état des services.
Le menu mobile et les réglages sont vérifiés à 320 pixels, sans débordement de
page ; aucune erreur console sur ces parcours. `/health` confirme les deux
bases disponibles et `/app/` répond HTTP 200. L’audio de ce poste reste
indisponible pour la transcription ; le message est explicite et les diagnostics
restent accessibles dans Options de l’audio. Les tests microphone sont simulés.

Suite Python complète : **1 795 réussites, 1 ignoré, 1 échec préexistant**,
`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`
(`tests/test_mail_learning.py:97`). Le bilan précédent de la recherche unifiée
documentait déjà cet échec de classement. Cette passe ne modifie pas son moteur.
Résultats conservés dans `logs/ui-simplification-pytest.log` et
`logs/ui-simplification-frontend-final.log` ; qualification structurée dans
`logs/ui-simplification-validation.json`.

Les assets précédents sont conservés dans
`logs/ui-simplification-original-dist` avant compilation. Aucun commit ni push.

Statut : **implémentée**, 2 octobre 2026. Le menu latéral est intégré à React
dans le serveur Agent sur :8001. Aucun module métier, moteur ou donnée n’est supprimé.
La refonte vise le frontend du même projet et du même serveur FastAPI ; elle
n’introduit ni sous-projet OpenDots, ni nouveau service de production.

## Cadre retenu

Le bureau simulé, le dock et les fenêtres flottantes cèdent la place à un espace de
travail stable : menu latéral avec libellés, en-tête de contexte, contenu central
et panneau facultatif de détail/assistant. Deux variantes sont proposées dans
la maquette interactive : **Menu latéral**, recommandé, et **Menu supérieur**,
plus adapté à une application ayant peu de rubriques.

Le dock actuel double le menu Applications, les raccourcis et le Launchpad.
Certaines destinations métier choisissent implicitement le projet au premier
plan, dernier ouvert ou unique (`Desktop.openModule`, `web/src/App.tsx`).
La modification doit éliminer cette ambiguïté, pas simplement changer les couleurs.
La place occupée par les fenêtres et le panneau assistant de 25 % réduit aussi
la lisibilité des tableaux. Les actions usuelles doivent être visibles, accessibles
en un clic, avec le projet clairement identifié.

## Navigation globale

| Rubrique | Contenu et objectif |
|---|---|
| Accueil | Priorités à traiter, échéances proches, état des traitements, accès aux projets récents |
| Projets | Portefeuille, favoris, filtres actifs/archives, création, import/export |
| Mails | À classer, classés, divers, écartés ; recherche, lecture, classement, pièces jointes, Thunderbird |
| Réunions | Accès transversal aux réunions, sélection explicite du projet, CR existants et réunion audio |
| Connaissance | Propositions à examiner et faits validés ; sources et provenance ; filtre de projet explicite |
| Traitements | Suivi des analyses mails, CDC et audio, progression, annulation et reprise selon le moteur |

Deux entrées de gestion en bas du menu : **Imports & connexions** (Sage,
Thunderbird, dossiers réseau) et **Réglages** (IA, mémoire, exploitation,
sauvegardes, apparence). L’assistant est un bouton de l’en-tête et un panneau
contextuel ; son ouverture ne change pas la rubrique courante.

Le menu complet conserve des libellés visibles sur ordinateur. Une réduction
volontaire peut être proposée ensuite, sans imposer un rail d’icônes. Sur mobile,
le menu devient un tiroir nommé « Menu », avec accès aux mêmes fonctions.
Les compteurs désignent un objet précis : mails à classer, propositions à examiner,
travaux en cours. Les états fermés deviennent « Archives », pas « Corbeille ».

## Navigation dans un projet

En-tête : **code + titre + client + état**, fil d’Ariane et sélecteur du projet.
Une URL stable restaure le projet et sa rubrique ; les boutons précédent/suivant
du navigateur fonctionnent. Route : `/app/projects/{id}/cdc`, également
rechargeable directement. Les anciennes API et pages `/ui` restent accessibles.

| Rubrique projet | Panneaux conservés |
|---|---|
| Vue d’ensemble | Pilotage, avancement, charge en heures, reste à faire, décisions attendues |
| Exigences & BE | CDC : Sources, Revue, Synthèse, Contrôles, Transferts BE versionnés |
| Planning | Planning, Jalons, Tâches et Livrables |
| Atelier | Achats, Pointage et Nomenclature |
| Réunions & revues | CR manuels, actions, export Markdown, conversion en tâches, parcours audio |
| Documents | Documents et accès réseau du projet |
| Connaissance | Liaison Brain, faits, actions, risques, propositions et état de synchronisation |

Le nom « Exigences & BE » est une amélioration de libellé : le module CDC & BE
et ses fonctions restent conservés. Import Sage devient global, comme son
traitement actuel. Les réunions accessibles depuis le menu global et depuis un
projet utilisent le même écran avec un périmètre différent, sans deux implémentations.

Les vues transversales possèdent leur filtre de projet explicite. Le sélecteur
de l’en-tête ouvre un projet ; il ne modifie pas les formulaires d’un autre projet. Dans un projet, le contexte de travail est son
identifiant ERP, associé explicitement à Brain. Un projet non lié affiche une
action de liaison ; il n’est jamais rattaché automatiquement. Le périmètre de
l’assistant est visible et indépendant lorsqu’on choisit « Tous les projets ».

## Direction visuelle

Une interface de travail sobre : surfaces claires légèrement teintées, menu bleu
encre, accent bleu pétrole, typographie système lisible, mode sombre équivalent.
Les couleurs de statut portent un libellé, et le rouge reste réservé aux erreurs
ou blocages. Pas de faux boutons de fenêtre ni de fond d’écran occupant la page.

- Échelle d’espacement commune : 4, 8, 12, 16, 24 et 32 px.
- Texte métier : 14–15 px ; titre de page : 26–28 px ; annotations au moins 12 px.
- Boutons usuels : 36–40 px sur ordinateur, 44 px sur écran tactile.
- Rayons limités : 6–10 px pour champs et panneaux ; ombres réservées aux overlays.
- Une action principale par zone de travail ; actions secondaires discrètes et nommées.
- Tables pour comparer, listes pour traiter une file, cartes seulement pour les synthèses utiles.
- Nombres et heures alignés ; unités visibles ; densité compacte/confortable au choix.
- Transitions courtes de 150–200 ms pour les détails et changements d’état ; aucune
  animation continue décorative et respect de `prefers-reduced-motion`.

Ces valeurs sont des choix de design proposés. Elles ne constituent pas une
certification d’accessibilité. La cible de production est WCAG 2.2 AA : contraste
du texte courant ≥ 4,5:1, clavier, focus visible/non masqué, labels, annonces
utiles, erreurs explicites, zoom et reflow. Le minimum WCAG pour les cibles est
24 × 24 CSS px avec exceptions ; les 44 px tactiles sont notre objectif de confort.

## Parcours à revoir

**Mails.** Dossiers repliables, liste et lecteur ; classement manuel toujours
explicite. Le lecteur montre le mail complet, les pièces jointes, la proposition
IA et son motif. La recherche et la pagination restent côté serveur. Le compteur
« traités / total » et les erreurs partielles sont visibles pendant et après analyse.

**CDC & BE.** Liste d’exigences, filtres métier et panneau de preuve. Sélection
d’une exigence → citation, page, révision, origine et décision. Les validations
groupées et les transferts gardent leurs contrôles ; brouillon et livrable final
sont distingués. Aucun score décoratif ne remplace un contrôle technique.

**Réunions.** Trois étapes distinctes : audio/transcription, texte par interlocuteur
et relecture, synthèse/CR. Le texte reste éditable ; une correction invalide la
validation et la synthèse antérieures. Les décisions/actions sont modifiables avant
publication ; responsable, échéance et preuve sont lisibles. La publication reste
une action humaine explicite, idempotente, dans les moteurs existants.

**Connaissance.** File de propositions intégrée au frontend ; faits validés et
sources non validées restent distincts. Recherche paginée, état de projection
discret, preuve accessible sans quitter le travail. Les limites actuelles de la
file de 30 éléments et les renvois vers `/ui` sont à traiter par des contrats API
paginés ; changer le menu ne les résout pas.

**Assistant.** Panneau ouvert à la demande, redimensionnable, conservant sa
discussion lors de la navigation. Projet interrogé visible, citations ouvrant un
inspecteur, distinction validé/à confirmer, progression et reprise explicites.
Le rendu progressif réel utilise `/v1/projects/chat/stream` et l’historique
persistant utilise `/api/v1/workspace/assistant-threads`. Les révisions contrôlent
les écritures concurrentes ; une erreur garde le brouillon affiché. La vérité
canonique reste dans Brain ; EG2 retrouve les passages des sources classées.

**Traitements.** Réunir les états des moteurs avec leur granularité réelle :
pages/lots CDC, mails traités/total, étapes et durée audio. Unifier le vocabulaire
en attente/en cours/terminé/échec/interrompu. Ne proposer « Pause » que si le moteur
la garantit ; sinon « Annuler » et « Reprendre ». La maquette simule une progression,
elle n’exécute pas de traitement. Le suivi durable des mails et les vues globales réunions/travaux sont intégrés
dans `/api/v1/workspace`, en utilisant les files CDC et audio existantes.

**Formulaires.** Montrer modifié/enregistrement/enregistré/échec/conflit ; conserver
les brouillons et protéger les données contre un changement de projet ou une réponse
asynchrone périmée. Étendre la sauvegarde automatique uniquement aux domaines ayant
un contrôle de révision côté serveur. Enregistrement micro et fichiers non envoyés
demandent aussi une protection de navigation.

## Ce qu’OpenDots apporte réellement

Audit en lecture seule au commit
`b01ac1f6a903e5e56c119d960901353ac0a3d171` : version 0.1.0, React 19.3,
Vite 8.3, TypeScript, Node ≥ 24/Hono et SQLite. La proximité React facilite la
reprise ciblée d’idées ou de composants, sans migrer FastAPI.

| Élément vérifié | Application à Agent | Mode de reprise |
|---|---|---|
| App.tsx : sidebar et navigation | Menu nommé, contexte visible, responsive | Pattern ; éviter son rail d’icônes supplémentaire |
| ResultPane.tsx | Exigence + preuve ; mail + lecture ; transcript + synthèse | Structure React à adapter aux API Agent |
| SpaceLibrary.tsx | Bibliothèque de documents, CR et livrables | Présentation et états ; garder recherche serveur pour nos grands volumes |
| PageReviewCard.tsx | Propositions IA corrigeables et validation explicite | Interaction ; retirer les dépendances au runtime CopilotKit |
| editor/autosave.ts | État d’enregistrement, brouillon et gestion des conflits | Logique après contrôle de révision FastAPI |
| TaskPresentation.tsx | Traitements et activités compréhensibles | Présentation ; adapter aux capacités de nos files |
| Tiptap | Éditeur de CR/documents éventuel | Dépendance optionnelle à évaluer séparément, sans priorité sur la navigation |

La licence MIT autorise une reprise de code avec maintien des notices requises.
Aucun code d’OpenDots n’est copié ; ses composants servent de références
d’interaction. L’implémentation et les contrats API sont propres à Agent.

OpenDots se présente comme un point de départ mono-propriétaire en développement
précoce, pas comme un ERP mature. Son README indique des intégrations encore à
vérifier et l’absence de partage, multi-utilisateur et uploads. Les conversations
durables passent par CopilotKit Intelligence ; sa voix WebRTC est un parcours
Realtime distinct de notre transcription locale. Slack, ordinateurs d’agents,
Automatic Learning, Hono et ce stockage externe ne sont pas nécessaires à la
refonte. Le dépôt est une bonne source d’interactions, sans preuve ici de stabilité
métier ni de conformité WCAG complète. Sa CI est consultée, pas exécutée.

Sources primaires :

- [README et limites](https://github.com/CopilotKit/OpenDots/tree/b01ac1f6a903e5e56c119d960901353ac0a3d171).
- [Dépendances](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/package.json).
- [Navigation](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/App.tsx).
- [Panneau de résultats](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/ResultPane.tsx).
- [Bibliothèque](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/SpaceLibrary.tsx).
- [Carte de validation](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/PageReviewCard.tsx).
- [Autosave](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/editor/autosave.ts).
- [Activités](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/TaskPresentation.tsx).
- [Paramétrage](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/docs/SETUP.md).
- [Licence MIT](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/LICENSE).
- [NN/g — navigation latérale](https://www.nngroup.com/articles/vertical-nav/).
- [WCAG — contraste](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
- [WCAG — cibles](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
- [WCAG — focus non masqué](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html).

## Étapes de réalisation retenues

1. **Cadre et navigation.** Design tokens, menu, routes, contexte et assistant
   repliable ; intégrer les panneaux existants. Vérifier les CSS liés aux fenêtres
   et restaurer les préférences utiles sans imposer le fond d’écran historique.
2. **Accueil et portefeuille.** Priorités, recherche, archives et tableau technique.
   Les codes, clients, jalons, heures et actions existants restent la référence.
3. **Mails et réunions.** Lisibilité maître-détail, sources, parcours audio, brouillons,
   navigation protégée et progression réelle.
4. **CDC, BE et connaissance.** Inspecteur de preuve, validation intégrée, pagination,
   transferts et écrans d’Atelier/Planning/Documents harmonisés.
5. **Qualité et contrats manquants.** Suivi global durable, historique assistant si
   retenu, gestion des conflits, responsive, clavier et vérifications de bout en bout.

Réutiliser `MailWorkspace`, `MeetingAudioPanel`, `CdcReviewPanel`, `CdcJobsPanel`,
`TransferPanel`, `WorkshopPanels`, `AssistantPanel`, `OperationsPanel`, `SettingsForms`,
les API/hooks/tests. La séparation `AppShell`, pages globales, `ProjectLayout` et
panneau de détail doit réduire `App.tsx`, sans réécrire les règles métier.

Critères de livraison : toutes les fonctions actuelles accessibles ; aucune action
sur un projet implicite ; URL et retour navigateur fiables ; aucune perte de
brouillon/micro/traitement lors d’un changement de rubrique ; preuves avant validation ;
pas de défilement horizontal global à 320 px ; tableaux défilants seulement dans
leur conteneur ; zoom à 200 %, clavier et réduction des animations vérifiés.
Les analyses restent locales et la publication demeure explicitement validée.
Les tests métier actuels sont conservés et complétés par quelques parcours de
navigation/transcription/validation justifiés par cette refonte.

## Maquette de proposition

La maquette utilise exclusivement des projets, noms, messages et chiffres fictifs.
Elle illustre les rubriques, la navigation projet, les citations, la relecture,
la synthèse et le suivi de progression. Aucun appel à Agent ou au LLM, aucun
enregistrement en base et aucun changement du serveur actif ne sont effectués.
Les boutons hors parcours illustré signalent leurs limites. Son état est local
à la visualisation ; ce n’est pas le futur stockage applicatif.

Vérification de la proposition : comparaison des deux dispositions, ouverture de
NOVA avec son contexte propre, recherche filtrée, correction de texte/interlocuteur
invalidant la validation, exemple de publication en lecture seule et progression
avec arrêt. Contrôle visuel à 1024 px et 360 px, sans débordement horizontal global
dans les vues contrôlées ; accès Imports/Réglages conservé sur petit écran.
Syntaxe JavaScript, contrat du fragment, JSON du manifeste et `git diff --check`
validés. Il ne s’agit ni d’un test de tous les modules d’Agent, ni d’un audit WCAG
exhaustif ; cette maquette initiale reste distincte de l’application désormais implémentée.

## Implémentation et qualification

- `WorkspaceShell` porte menu nommé, contexte, favoris, recherche Ctrl+K,
  thèmes clair/sombre, densité et assistant facultatif de 300 à 520 px.
  Sa largeur s’ajuste via une poignée discrète sur le bord du volet, à la souris,
  au toucher ou au clavier ; aucun curseur de largeur n’encombre son en-tête.
  Le formulaire Mémoire présente EG2, son serveur et l’état de son index local.
  La liste Projets garde recherche et filtres, sans import JSON
  ni bouton Actualiser ; les archives restent dans Imports & connexions.
  Les icônes de dossier présentent les quatre premiers chiffres du numéro,
  extrait du dernier groupe numérique du code : AIRB25LTH0806-A → 0806.
- `workspaceNavigation` porte les URLs `/app/*` et le retour navigateur.
  Les rubriques et projets visités restent montés dans la session : les champs,
  fichiers et captures micro survivent au changement de rubrique ou de sous-onglet.
  Le microphone actif apparaît dans un bandeau permettant de revenir à la réunion.
  Les brouillons en mémoire ne remplacent pas une sauvegarde après fermeture du navigateur.
- `WorkspaceViews` porte réunions transversales, connaissances/propositions
  paginées, décisions explicites, preuves et traitements globaux. Une liaison
  manquante ne devient jamais une interrogation silencieuse de tous les projets.
- Les discussions sont enregistrées dans Brain, avec révisions et résolution
  explicite des conflits. Le LLM reçoit au plus 12 messages / 12 000 caractères
  d’historique conversationnel ; les preuves proviennent du rappel courant.
  Les paramètres de raisonnement désactivé sont conservés.
- Le compteur mail a un instantané serveur stable. Le navigateur observe la
  progression au lieu de conduire les lots. Fermeture de page et reprise de
  serveur ne perdent pas les propositions déjà enregistrées. La restauration
  d’une sauvegarde exige une reprise explicite des travaux interrompus.
- CDC, Planning, Atelier, Documents, Revues, Sage et les moteurs audio restent
  les composants existants, intégrés au nouveau cadre. Les formulaires métier
  gardent leur enregistrement explicite ; la sauvegarde automatique ne s’étend
  pas à des domaines dépourvus de contrôle de révision.

Contrôles automatisés : 153 tests Python réussis, 1 ignoré ; 83 tests React
réussis ; Ruff et compilation TypeScript/Vite réussis. Les fixtures sont isolées
et `AGENT_TESTING=1` désactive aussi le scan automatique de dossiers locaux.
Les contrôles navigateur portent sur menu, projet explicite, URLs, retour,
brouillon réunion, palette, assistant, vues globales et responsive. Il ne s’agit
pas d’une certification WCAG de tous les panneaux historiques.
Les derniers ajustements ont été contrôlés sur la version active : glissement
350 → 470 → 350 px, numéro 0806 dans le dossier, libellé mémoire actif simplifié.
À 320 px, les pages Projets et Mémoire gardent une largeur globale de 320 px ;
seul le tableau du portefeuille défile horizontalement. Les styles des vues
globales restent limités à leurs composants, et l’accueil vide de l’assistant
ne défile plus automatiquement vers le bas.

Le lecteur Mails permet maintenant de créer une destination directement dans
son sélecteur : formulaire intégré, projet aussitôt sélectionné et présent dans
les dossiers. La création n’affecte pas le mail sans validation. Le dépôt et le
reclassement mettent à jour la liste et les compteurs dès l’enregistrement ;
l’enrichissement IA/mémoire poursuit son travail en arrière-plan dans le même
serveur, avec suivi et reprise dans Traitements. Voir `docs/18_MAIL_TRIAGE.md`.

Correction du parcours de création et de la molette :
- Manuel et dossier réseau notifient le cadre après confirmation du serveur.
  Le rechargement du portefeuille est attendu avant le retour à Projets ;
  recherche et filtre Archives/En retard/À examiner ne masquent plus le nouveau projet.
  L’envoi est protégé contre les doubles clics et les erreurs restent lisibles.
- La liste visible se rafraîchit toutes les 10 secondes et au retour dans la fenêtre ;
  le polling s’arrête en arrière-plan. Les brouillons métier restent montés.
- Le défilement interne garde la priorité lorsque la liste peut avancer.
  Les limites et les zones de défilement uniquement horizontal rendent la molette
  à la page. Les mouvements horizontaux, le zoom et les contrôles de formulaire
  ne sont pas détournés.
- Vérification navigateur sur bases fictives : création TEST-0807 visible dès
  le retour, malgré recherche ORION et filtre Archives préalables ; défilement
  vertical effectif au-dessus du tableau et du menu. Aucune création de test
  ni suppression n’a touché les bases actives.

La page Mails reçoit aussi le portefeuille courant et son état de visibilité :
les cartes et destinations du lecteur sont actualisées après création, au retour
à la rubrique et pendant son affichage. Les projets sans lien deviennent
classables à la première décision humaine, grâce à une liaison idempotente.
Les réussites du dépôt sont retirées immédiatement après validation, les
réponses anciennes sont filtrées, les échecs partiels restent sélectionnés.
Le lecteur reste ouvert pendant une actualisation du catalogue. Voir
[le parcours de classement](18_MAIL_TRIAGE.md).

Vérification navigateur sur bases fictives : CLASS0808 créé après ouverture
d’un mail, présent dans son sélecteur au retour ; geste réel de dépôt, compteur
2 → 1, message conservé et lisible dans CLASS0808. Activation du correctif Mails :
deux bases actives saines, 2 704 identifiants présents avant cette activation
toujours présents, Xproji proposé dans le lecteur actif. Aucun mail réel n’a été
classé pour cette vérification.

Activation initiale de la refonte le 2 octobre 2026 sur :8001 : les deux bases répondent.
La sauvegarde coordonnée de 303 fichiers a été vérifiée ; les 2 950 identifiants
de lignes présents avant l’activation sont toujours présents. Le serveur LLM
configuré est injoignable au contrôle d’activation : la génération réelle reste
à requalifier quand cet endpoint répondra. Les tests de flux utilisent des fixtures.

L’[analyse vocale](25_REALTIME_VOICE.md) est documentaire : la voie cloud payante
est écartée par l’utilisateur. Le direct local ne fait pas partie de cette
activation ; le parcours réunion audio existant reste disponible.

## Activité des mails dans le menu — 5 octobre 2026

Le bloc permanent « Activité des mails » se trouve sous les rubriques, avant
les favoris. Il distingue synchronisation, analyse IA et indexation mémoire.
Chaque étape dispose de son état et de sa barre ; un compteur connu affiche
une progression réelle, sinon le traitement actif utilise une barre animée.
Le témoin pulse uniquement pendant un traitement, avec respect du réglage
système de réduction des animations. En attente, déconnecté, au repos et erreur
restent fixes et explicites. Un heartbeat ancien n’est pas une activité actuelle.

Les quatre derniers changements observés sont horodatés dans un petit journal.
La navigation conserve ce journal ; le rechargement reconstitue l’état courant.
Les heartbeats identiques ne remplissent pas le journal. « Voir les traitements »
ouvre la rubrique permettant de consulter/reprendre les tâches. Les animations
s’arrêtent en cas d’indisponibilité du serveur ; l’onglet masqué suspend les polls.

Qualification : 165 tests Python passés, 1 ignoré ; 90 tests React passés ;
Ruff et TypeScript/Vite réussis. Sur bases fictives, passage observé de 12 à
27/80, indexation active et journal conservé en naviguant vers Traitements.
Activation sur 8001 : analyse automatique réellement en cours, liaison
Thunderbird sans heartbeat récent, 9 mails indexés ; 4 807 identifiants existants
conservés et sauvegardes Brain/ERP intègres. La lecture du suivi a pris 17 ms
lors du contrôle ; elle ne déclenche ni import, ni analyse, ni indexation.

## Copie activée et prévention du retour à l’ancien bureau

Le 5 octobre 2026, un redémarrage de 8001 depuis `C:\Agent`, alors que la
refonte restait dans le worktree 264b, a réaffiché le bureau historique.
La remise en service réunit les sources de la refonte et le classement mails
multicritère dans `C:\Agent`, avec sauvegarde des fichiers et des bases,
fusion à trois voies, tests sur copie isolée et compilation React. Les
worktrees restent des espaces de préparation ; leur activation doit préserver
les correctifs déjà présents dans la copie de lancement. Les modules métier
et les chemins des données Brain/ERP restent conservés.

Qualification de la version réunie : 227 tests Python réussis, 1 ignoré,
95 tests React réussis ; Ruff et compilation TypeScript/Vite conformes.
Les tests utilisent des bases jetables.

## Icône de l’onglet — 7 octobre 2026

Le favicon reprend les trois couches du symbole Agent, en blanc sur le vert `#00796c`, dans un carré arrondi. Son format SVG conserve la netteté dans les onglets. Le fichier public est inclus dans les compilations Vite et servi par `/assets` sur Agent 8001.

## Thème sombre des mails — 7 octobre 2026

La palette de `.maildesk` hérite des variables du workspace : fond, surfaces, texte, bordures et accent. Le thème actuel est porté par `data-workspace-theme`, tandis que l'ancien bureau utilisait `body[data-theme="graphite"]`. Les avatars, les indicateurs d'écartement et les boutons de validation disposent de couleurs adaptées au sombre. La lecture et les dossiers suivent immédiatement le changement d'apparence, sans modifier les données des mails.

Sur écran large, le mail occupe la colonne de gauche et les dossiers/vignettes projets la colonne de droite. Sur écran étroit, le mail précède les vignettes dans une seule colonne. Le glisser-déposer et les commandes de classement restent disponibles.
Le fil d’Ariane, la barre Mails/recherche, les commandes Thunderbird/analyse, les notifications, le tri et la navigation précédent/suivant ainsi que les commandes réponse/original sont regroupés au-dessus des vignettes projets. La colonne de lecture commence directement par l’objet et l’expéditeur du mail.
Le bloc Boîte de réception (onglets et sélecteur de dossier) est retiré de cette colonne. Les vignettes projets suivent directement les commandes ; l’accès aux dossiers est conservé dans le menu « Autres actions ».

Cette disposition de commandes décrit l’étape du 7 octobre ; elle est remplacée
par la [lecture du 11 octobre](#correction-mails-après-utilisation), qui donne
la priorité au corps du mail et déplace le classement dans le panneau projets.

## Studio de réunion et bibliothèque — 11 octobre 2026

Le [plan de fusion Foresight](37_FORESIGHT_FUSION_PLAN.md) conserve le serveur
Agent sur 8001 et tous les modules métier. Le Studio propose les deux
dispositions observées : notes personnelles et notes enrichies côte à côte,
ou notes et assistant avec Discussion, Synthèse, Transcription et Questions.
Les panneaux équilibrés reprennent un espacement de 9 px, un remplissage de
12 px et des coins arrondis de 18 px. La police reste celle d’Agent ; une copie
au pixel près de Foresight n’est pas attestée. Les ajustements métiers et les
fonctions qualifiées sont décrits dans [la livraison](38_FORESIGHT_DELIVERY.md)
et les [références et la recette visuelle](39_FORESIGHT_REFERENCE_UI.md).
L’utilisateur a retenu les écrans publics documentés comme référence ; aucune
parité avec une interface privée de Foresight n’est revendiquée.

La capture navigateur utilise un contrôleur hors des vues : changer de
rubrique conserve l’enregistrement. Les fragments sont sauvegardés dans
IndexedDB avant transfert ; un acquittement vérifié autorise le retrait de la
copie locale. Une erreur de stockage arrête la capture et garde le fragment
en mémoire avec un avertissement de conservation. La capture Windows demande
les pistes et périphériques explicitement, sans microphone coché par défaut.
Les barres globales permettent de revenir à la séance, de mettre en pause et
d’arrêter. L’export de récupération reste disponible après désactivation des
nouvelles séances. Préparation refuse la désactivation si une capture navigateur
est en cours ou attend une synchronisation ; la barre globale indique les
commandes d’arrêt, de conservation et de finalisation à utiliser d’abord.

La note du Studio utilise l’identité et la version ERP canoniques. Un conflit
préserve la saisie et permet de comparer la version enregistrée. Les notes
enrichies sont des propositions versionnées dont l’acceptation est explicite.

L’enrichissement automatique F10 est un opt-in distinct des questions
proactives : `foresight.auto_enhancement_enabled=false` par défaut, indépendant
de `proactive_enabled`. Le worker attend qu’un même instantané enregistré
(révision de séance, version/contenu de note, segments et contexte calendrier)
reste inchangé pendant au moins huit secondes depuis son observation. Ce seuil
de stabilité ne garantit pas une génération huit secondes après la saisie.
Une seule tentative est réservée durablement pour cet instantané avant
exécution ; erreur ou interruption ne déclenchent aucun retry automatique.
« Améliorer les notes » permet une reprise explicite.

Le Studio montre attente, génération, proposition disponible, proposition
périmée et erreur détaillée. L’état `failed` porte le libellé « Tentative à
reprendre » : après une interruption, l’absence de résultat confirmé ne prouve
pas que l’ancienne exécution est terminée. Les 45 secondes configurées sont un
timeout de transport, sans garantie de durée totale ni préemption d’un appel
HTTP déjà engagé ; l’arrêt empêche les nouvelles admissions.

Chaque proposition conserve ses citations et sa version ou son instantané de
base ; une modification enregistrée du contexte la rend périmée. La saisie
locale riche ou Markdown est exclue de l’analyse automatique, qui peut encore
porter sur la dernière version sauvegardée. Le message est explicite : « Vos
modifications non enregistrées ne participent pas à l’analyse. » Ces brouillons
bloquent génération manuelle, acceptation et publication ; ils ne bloquent pas
l’arrêt audio. Aucune proposition ne réécrit ni n’approuve seule la note humaine.

Le compte rendu issu des notes exige une relecture et des citations exactes
dans la version publiée. Il conserve les actions sans créer automatiquement
des tâches. Le parcours audio ouvre l’enregistrement exact de la séance.
Une note enregistrée dans une séance encore ouverte indique « Terminez la prise
de notes avant de publier », avec la commande de finalisation en haut de la
séance. « Corrections à enregistrer » désigne uniquement une saisie non sauvegardée.
La finalisation, la relecture et la publication restent trois gestes distincts.
Le formulaire de synthèse reste monté entre les onglets ; type d’élément,
formulation, bloc cité, extrait, responsable et échéance non encore ajoutés sont
aussi conservés dans le brouillon local après rechargement. Ce brouillon ne vaut
ni ajout au compte rendu ni approbation ; recharger impose une nouvelle relecture.
« Ouvrir le compte rendu » cible directement Réunions et audio et le compte rendu
publié via une URL rechargeable ; seule une réunion présente dans les données du
projet courant peut être ouverte par cette cible.
Discussion relit les réponses sauvegardées pour la séance et le périmètre
choisis, y compris lorsque le moteur IA est indisponible. Le choix du périmètre
et de l’ensemble de sources survit au rechargement ; changer de séance ne
réutilise pas une réponse arrivée tardivement. Questions permet d’épingler
explicitement une carte et retrouve cet état après rechargement.

« Lire la version citée » ouvre un aperçu en lecture seule du contenu exact,
avec version et date ; il ne remplace jamais une ancienne version par la tête
actuelle. Les images utilisent les liaisons historiques de cette version.
Une erreur de droits ou de contenu est affichée avec une commande de reprise.
« Examiner la source citée » ouvre l’inspecteur existant avec la citation et
sa localisation, en gardant le Studio monté. La recherche multimodale transmet
également ces repères à l’inspecteur. Le téléchargement original reste séparé.

L’éditeur commun propose Riches et Markdown pour les structures convertibles.
La conversion accepte paragraphes, titres 1–3, listes/cases, gras, italique,
code et liens sûrs. Tableaux, images et styles non représentables refusent le
passage avant toute modification ; aucun contenu riche n’est effacé.
Le buffer Markdown reste local et distinct de la note enregistrée. Une saisie
invalide ou en conflit avec un contenu changé est conservée, signalée et doit
être corrigée/convertie ou abandonnée explicitement. Sauvegarde, enrichissement
manuel et publication sont bloqués tant que ce buffer attend une décision ;
l’arrêt et la récupération audio restent disponibles. La conversion valide
passe par le schéma NoteContent et le parcours de sauvegarde existant.

Les panneaux de relecture restent montés quand l’onglet ou la disposition
change ; une correction non enregistrée reste présente. La fermeture de la
séance signale une relecture qui serait perdue.

Sources réunit la liste, les labels, les imports choisis et les relations
connues. Les notes ERP en attente de projection ouvrent Documents et restent
exclues de la sélection de preuves et des labels jusqu’à projection. La
recherche multimodale affiche ses sources et ses localisations. Préparation
expose l’état des moteurs, le mode d’exécution et les lots d’indexation avec
interruption et reprise. Les statistiques distinguent métriques absentes,
configuration et disponibilité vérifiée. Les vues Relations et Statistiques
sont des adaptations Agent, leur comportement Foresight n’ayant pas été observé.
Les compteurs de passages EG2 et multimodaux affichent « Indisponible » si leur
index est illisible. Le lien d’une note versionnée est nommé « Télécharger la
version de note » et conserve la source exacte, y compris hors du rappel courant.

Les panneaux se superposent sous 670 px ; les tableaux conservent un défilement
local. Les onglets acceptent les flèches gauche/droite, Début et Fin ; les
nœuds du graphe sont consultables avec Entrée ou Espace. Les thèmes et les
préférences de réduction des animations restent hérités du workspace.
La qualification frontend est consignée dans
`logs/foresight-runtime/frontend-qualification.json` avec le nombre exact de
tests, TypeScript et le build. La recette HTTP et visuelle reste distinguée
des tests sur fixtures.

Les passages précédents de 546, 549 et 553 tests sont historiques. Après les
derniers correctifs, une passe intermédiaire a réussi 563 tests/68 fichiers
en 173,52 s ; elle précède le raccordement direct au compte rendu publié.
Deux échecs de préparation asynchrone ont été conservés dans leurs rapports :
MailApp attend désormais son lecteur initial, Planning attend les visas avant
de cliquer le bouton réellement activé. Les assertions métier restent inchangées.
La passe de référence **569/569 tests, 69 fichiers**, en 195,71 s, est désormais
historique : elle suit le raccordement au compte rendu exact et précède les
ajouts Markdown, historique partitionné, aperçus de citations et F10.
TypeScript et build y étaient réussis ;
assets `index-BHuQuZfz.js` et `index-BpOo83wS.css`, tailles/empreintes dans
`logs/foresight-runtime/frontend-qualification.json`.
L’avertissement de taille du paquet JavaScript ne bloque pas le build.

La qualification globale de cette étape antérieure réussit **672/672 tests, 75 fichiers**, en
235,84 s ; TypeScript et build terminent avec le code 0. Son rapport et ses
assets `index-OJ887VWy.js` restent conservés dans
[le reçu global](../logs/foresight-runtime/frontend-completion-qualification.json)
et [le journal React](../logs/foresight-runtime/frontend-completion-vitest.log).
Un premier correctif complémentaire remplace le libellé F10 par « Tentative à reprendre » :
**deux tests ciblés réussissent**, puis TypeScript et le nouveau build terminent
avec le code 0. Ce suivi complète la passe globale sans annoncer une nouvelle
suite complète. L’asset de ce suivi, `index-NcMllJD2.js`, a pour SHA-256
`2ca3617f47bd1d6828f53208ce5ddf547d5baf9d6f5d306733f2cd9b5b0992d7`.
[Le reçu de suivi](../logs/foresight-runtime/frontend-f10-label-followup-20261011-204228.json)
réunit commandes, codes, logs, tailles et empreintes ; les quatre assets
précédents sont préservés avec leurs SHA vérifiés. Cette passe ne touche ni base
ni matériel et ne constitue pas une recette navigateur supplémentaire.

La recette navigateur a ensuite reproduit un refus Markdown sur un vrai DTO
ERP : l’ordre des clés JSON différait, sans différence de contenu. La
normalisation compare désormais les champs explicites des paragraphes, titres,
listes et éléments, en conservant les contrôles de texte, espaces et styles
non représentables. **97/97 tests ciblés dans cinq fichiers**, TypeScript et
build passent après ce correctif. Le build final est `index-DKlOduK1.js`, SHA-256
`892c4fb213ae70bcb1160851b25475a892a9af9ddaf5f3cdaf6e43bd10861ebd`.
[Le reçu Markdown](../logs/foresight-runtime/frontend-markdown-dto-followup-20261011-205428.json)
conserve la reproduction, les résultats et les empreintes ; l’asset NcMllJD2
et les rapports précédents restent intacts. Les passes globales et ciblées se
recouvrent : leurs nombres ne s’additionnent pas en une nouvelle suite globale.

Sur données fictives isolées, dans le navigateur relié au serveur 18003, une
note ERP V2 passe en Markdown puis est sauvegardée en V3 ; V3 reste présente
après rechargement. Cette V3 comporte cinq blocs : un titre et quatre
paragraphes, avec le dernier paragraphe en gras. Une saisie invalide est
conservée au retour puis à la
réouverture ; les tableaux Markdown sont refusés, avec « Enregistrer » et
« Terminer » désactivés. L’avertissement natif du navigateur a demandé une
annulation humaine ; le brouillon a été conservé. L’aperçu historique ERP V1
contenant Paul reste lisible malgré la tête V3 ; l’aperçu de staging V1 conserve
50 euros alors que le contenu courant indique 70 euros.
[Le rapport navigateur final](../logs/foresight-runtime/browser-completion-20261011/qualification.json)
valide **21 assertions qualifiées** sur ces données fictives, avec réponses
simulées. Cette passe ne déclenche ni LLM, ni capture audio, ni publication et
ne qualifie pas Drive connecté ou une recette physique hors connexion. La
fixture précède le correctif UTC de l’API staging ; ce point est qualifié
séparément par cinq tests API.

La recette navigateur précédente a confirmé Studio, Sources et Préparation à
1280/670/320 sans débordement horizontal de page. Le tableau Sources conserve
son défilement local ; son en-tête destiné aux lecteurs d'écran reste contenu
dans ce tableau. Les citations affichent la page physique et, si connue, la
page imprimée, la feuille/plage, les temps audio ou la version et le bloc de
note. Un numéro ordinal d'artefact ne devient jamais une page PDF inventée.
Les localisations internes de fichiers et les profils techniques sont masqués.
Preuves : `logs/foresight-runtime/browser/*-responsive.json` et captures voisines.
Ce contrôle précède le dernier correctif Markdown. La recette finale du build
DKlOduK1 vérifie aussi l’aperçu historique à 1280, 670 et 320 px : les mesures
client/défilement sont respectivement **1265/1265, 655/655 et 305/305 px**, sans
débordement horizontal de page. Une première tentative à 670 px avait ciblé
un autre onglet et reste exclue de la qualification ; les mesures et captures
réelles suivantes sont conservées séparément. Voir
[la capture finale du Studio](../logs/foresight-runtime/browser-completion-20261011/final-studio-historical-version.png).

### Complément du 11 octobre 2026 — formats, navigation et trois zones

Sources distingue désormais **Type de source** (Document, Note, Mail, Réunion)
et **Format** (PDF, PNG, TXT, formats Office ou audio reconnus). Le MIME reconnu
est prioritaire ; un suffixe compatible distingue Markdown/CSV du texte brut.
Un MIME absent ou générique peut utiliser le nom conservé ; un MIME explicitement
non reconnu reste inconnu. Cette présentation décrit les métadonnées du fichier,
pas la validité de ses octets ni la réussite d'extraction. Notes et transcriptions
sans fichier ne reçoivent aucun format inventé. Le filtre s'applique aux sources
accessibles avant pagination, total et labels ; le protocole `source_type`, les
identifiants/version et les téléchargements existants sont conservés.

Le rail compact appartient uniquement à Sources et Réunions au-dessus de 670 px.
Les autres rubriques, notamment les projets hérités, gardent le seuil de menu
850 px. Le menu fermé est `aria-hidden` et `inert` ; le contenu devient inert
pendant son ouverture. Le menu se ferme lors du retour au rail large, et les
gardes de focus visent une commande visible lorsque le rail est masqué ou que
le menu se ferme. La vérification navigateur de ce dernier complément reste
distincte des tests de composant. Le cache par identité de projet et les
sous-rubriques montées conservent les brouillons Documents/Notes.

Le Studio ajoute la disposition **Notes, enrichissement et assistant** : Notes
et propositions sont regroupées à gauche, l'assistant reste visible à droite.
Les deux dispositions précédentes sont conservées. Les trois panneaux gardent
leurs nœuds montés ; leur visibilité change sans recréer l'éditeur, l'onglet,
la question ou la proposition. Les brouillons riches/Markdown, leurs conflits,
les commandes et les guards de sauvegarde restent liés à la séance. À 670 px
et moins, les zones s'empilent. Cette disposition est une adaptation Agent ;
elle ne constitue pas une reproduction attestée d'un écran public à trois zones.

[Le reçu ciblé](../logs/foresight-runtime/source-format-followup-20261011/combined-final.json)
consigne **80/80 tests frontend dans cinq fichiers**, puis **15/15 Shell** après
la dernière correction de focus : ces quinze cas répètent un sous-ensemble,
ils ne forment pas 95 cas distincts. Les **102 tests backend** restent séparés.
TypeScript, build et Ruff ciblé terminent avec le code 0 ; l'API des formats est
vérifiée sur la fixture fictive isolée. Le build de ce complément est
`index-CqjQtHrm.js` (SHA-256
`5b8a882ff81bb2913a455f157b235ae8340208b5b0d41b80e151647dbf8e8f99`),
avec `index-Bu523YUz.css`. Les preuves précédentes, dont global672 et Markdown97,
restent historiques et ne sont pas additionnées. Ces preuves n'ont invoqué
aucun micro ou LLM ; la fixture est isolée. La comparaison des positions/tailles publiques
à **±2 px reste non qualifiée** : ce complément ne clôt pas F25/T13.

### Suivi final du 11 octobre 2026 — entrée Sources et panneaux bornés

Sources affiche **Nouvelle séance** et ouvre le formulaire Réunions existant,
avec le projet ERP accessible proposé ou « À rattacher ». La navigation garde
la protection des brouillons ; le clic seul ne crée aucune séance et ne démarre
aucun micro. Le formulaire a réellement été ouvert depuis Sources sur la
fixture QA-FUSION-L12, sans valider sa création.

La vue complète du Studio borne ses panneaux au viewport à partir du même
seuil CSS `min-width:671px`. Notes, enrichissements, assistant et commandes
gardent leurs nœuds ; les zones défilables sont accessibles au clavier. Le
Shell emploie `matchMedia` pour aligner menu, `inert` et focus avec le CSS,
y compris lorsqu'une largeur fractionnaire diffère de `innerWidth`.

[Le reçu final](../logs/foresight-runtime/source-session-layout-followup-20261011-221310/qualification.json)
qualifie **694/694 tests frontend dans 75 fichiers**, TypeScript et build avec
code 0. Le JS est `index-DhlxCsWr.js`, SHA-256
`c4416b2615feab848c3ad630fb46e1f49eeb75d4575995ef4e185fe0cf66ca9c`,
et le CSS `index-DENGLpaQ.css`, SHA-256
`d9de4c7d6eb87fb5e237de1fb9b9c6db33ffb8046f6eaced0d4f48817a03bdb7`.
Les 57 cas ciblés, les anciens 80 et global672 se recouvrent avec cette suite,
sans cumul ; les assets Cqj et les rapports antérieurs restent conservés.

[La recette CUA finale](../logs/foresight-runtime/public-fidelity-final-20261011/DhlxCsWr/qualification.json)
valide **16/16 contrôles locaux** : filtres PDF/PNG, formulaire préparé,
conservation de la Note ERP version 2 et du cinquième bloc après rechargement,
préférence complète, défilements clavier indépendants et retour 670 → 850 avec
focus Recherche puis navigation ERP. À 320 px, client/défilement sont 305/305.
Ces contrôles sur données fictives isolées ne lancent ni micro, ni LLM,
transcription, publication ou service externe.

[La mesure publique après complément](../logs/foresight-runtime/public-fidelity-after-measurement-20261011.md)
garde les écarts ouverts : R01 retrouve x104/largeur1160, mais le tableau reste
à y384,1 contre environ 364 ; R02 montre les trois cadres dès le premier écran,
avec seulement 117/78/204 px de hauteur et un assistant à y254,5 contre environ 100.
Le document atteint encore 486 px pour 479 px de viewport. R03 à 786 × 474
garde ses deux notes non bornées, à y396,7 contre environ 141. Les frames de
chargement et lignes ERP cachées sont conservées mais exclues des mesures
qualifiées. F25/T13 à ±2 px reste non qualifié ; aucune parité privée ni
dérogation à l'exactitude publique n'est revendiquée.

[Le reçu canonique final](../logs/foresight-runtime/completion-runtime-qualification-v4.json)
confirme le backend actualisé, les assets servis identiques et **2051 tests
Python réussis / 1 ignoré**, sans échec ni erreur. Les trois flags Studio,
proactif et enrichissement automatique sont renvoyés `false`.
[La conservation](../logs/foresight-runtime/production-public-final-preservation-20261011.json)
porte sur 18 tables métier protégées exactes et 1340 originaux SHA ; les
142 nouveaux inputs et trois inputs historiques modifiés des workers hérités
restent déclarés, sans suppression. Elle ne signifie pas que les 80 tables
sont toutes immuables. Matériel, réunion longue et coupure réseau physique
restent des qualifications distinctes.

### Complément du 11 octobre 2026 à 21:34 UTC — Studio compact et Sources R01

Le Studio rassemble le titre, les métadonnées et l’accès **Préparation** dans
un en-tête compact. Les commandes secondaires et le fil d’Ariane protégé
restent montés dans ce volet ; Échap le ferme et rend le focus au déclencheur.
Pause/Arrêt du navigateur, récupération des fragments et capture Windows
active restent hors de ce volet. La capture Windows garde un composant unique
et son détail ne peut pas se replier lorsqu’une commande urgente est active.
Les trois dispositions desktop sont maintenant bornées au viewport, en tenant
compte du padding bas et des barres de capture insérées au-dessus sans resize.
Un seul éditeur et les buffers riches/Markdown sont conservés. À moins de
671 px CSS, le flux mobile reste naturel. Des commandes urgentes ou erreurs
peuvent prendre de la hauteur ; elles ne sont pas cachées pour tenir une image.

Sources sépare les rangées titre/projet, onglets, recherche, labels et
résumé/tri/liste-grille. Le total est celui du serveur. Les raccourcis de format
n’inventent aucun comptage global à partir des 25 éléments chargés. Le volet
**Périmètre et filtres** garde les champs montés et annonce ses valeurs actives.
Le type, le projet, la version et le traitement restent dans les détails de
ligne ; l’Original conserve son identité et reste accessible. **Ajouter un
label** ouvre l’éditeur existant après sélection ; sa confirmation est
explicitement **Remplacer les labels**, sans promesse d’union atomique. Un
label valide de 80 caractères reste intégral et peut revenir à la ligne.

La transcription montre la file avant même le premier segment : fragments
en attente, en traitement ou à reprendre, première erreur et durées séparées
par piste. Ces durées ne sont pas une mesure de retard mural. Un traitement
STT terminé peut rester sans segment ou avec texte provisoire. Le direct
opérationnel mais non qualifié est annoncé comme un essai nécessitant
relecture, y compris si le batch est prêt ; aucune latence industrielle
maximale n’est promise.

[Le reçu regroupé](../logs/foresight-runtime/studio-compact-followup-20261011/qualification.json)
qualifie **716/716 tests React dans 75 fichiers**, TypeScript et build code 0.
Le JS `index-Dj5PdhkQ.js` a le SHA-256
`bba0ee0195a4865955fa82e624fcd946827727a694879f2c5f82d06d04dcbeca` ;
le CSS est `index-CU6ZruIv.css`. Les 132 ciblés et les anciens globals 694/672
sont des passages recouvrants, sans cumul. Le brut global-v1 **710 réussis /
1 échec** reste conservé : le test de citations cliquait pendant la lecture
d’historique ; la précondition de bouton activé est désormais exercée avec
un historique volontairement différé. Les assets Dhl/DENGL restent sauvegardés.

[La fixture neuve](../logs/foresight-runtime/studio-compact-followup-20261011/fixture-launch.json)
est isolée sur localhost18003, avec IA, proactif, enrichissement automatique
et workers désactivés. Sa séance **FICTIVE — file STT sans moteur** conserve
du PCM synthétique silencieux : deux fragments mic en attente (8 s) et un
fragment système en échec préparé (5 s), zéro segment. Elle ne prouve aucune
capture, transcription ou génération réelle. Le complément ne modifie ni
backend ni flags canoniques.

Les premières mesures CUA donnent Sources : onglets y144,5/h36, recherche
y190,5/h49, labels y254,5/h40, résumé y310,5/h40 et tableau y362,5. Le Studio
complet à 850 × 479 place ses panneaux à y100/h371, avec deux moitiés gauches
de 185,5 px. Ces [relevés intermédiaires](../logs/foresight-runtime/public-fidelity-compact-20261011/Dj5PdhkQ/studio-complete-r02-850x479-bounds.json)
ne clôturent pas F25/T13 : la référence publique est mesurée visuellement,
l’enrichissement reste environ 12,5 px trop haut et les barres d’éditeur
diffèrent. La recette des usages et R03 restent à compléter à ce stade.

#### Suivi CSS du 11 octobre 2026 à 21:43 UTC

La règle héritée de boutons à 44 px sous 850 px augmentait la barre haute
et l'en-tête du Studio à 786 px. La correction est limitée aux vues fusion
desktop à partir de 671 px : Recherche et boutons/selects du Studio ont un
minimum de 32 px. Le mobile garde ses 44 px, la largeur des panneaux et leur
partage ne changent pas. Le [build CSS seul](../logs/foresight-runtime/studio-compact-followup-20261011/cascade-css-build-v2/qualification.json)
est réussi, sans nouveau test React ou passage TypeScript. La
[traçabilité distincte](../logs/foresight-runtime/studio-compact-followup-20261011/cascade-css-build-v2/inherited-checks-and-css-build.json)
référence le global 716/75 et TypeScript réussis avant cette correction ; elle
ne présente pas ces trois phases comme un nouveau runner unique. Les assets
actuels sont `index-B0MSJycO.js` (contenu JS identique à Dj5) et
`index-OmDJ_fGw.css`. Le brut EPERM avant compilation et les anciens builds
restent conservés. Le relevé CUA après correction et la coque commune de R03
restent à qualifier ; aucune exactitude à ±2 px n'est déduite du build.

Le [contrôle SQLite après les usages navigateur](../logs/foresight-runtime/studio-compact-followup-20261011/fixture-postbrowser-readonly-v1/qualification.json)
confirme 15 assertions dans la seule fixture : quatre séances sans création
supplémentaire, Note ERP v2 exacte avec quatre blocs
heading/paragraphe/liste/paragraphe et historique v1, label TXT exact de
80 caractères, trois items/versions, zéro Recording/source audio/CR/action/tâche.
Les trois fragments T12, leurs SHA et zéro segment sont conservés ; les SHA
des deux bases et WAL sont identiques avant/après cette lecture. Ce contrôle
ne qualifie ni micro, STT réelle, LLM, ni fidélité visuelle.

#### Décision utilisateur du 11 octobre 2026 à 21:49 UTC — adaptation et Drive

L'utilisateur a choisi **« Valider cette adaptation à Agent »** après examen
du Studio : éditeur riche hérité XPilot, panneaux distincts et partage gauche
égal sont acceptés dans cette portée. **F25/T13 est clos pour cette adaptation
validée**, avec les dimensions principales de Sources ; l'exactitude ±2 px
et la parité privée Mac restent explicitement non revendiquées. Les mesures
et écarts datés ci-dessus restent conservés. Cette acceptation ne clôture
aucune autre qualification matérielle, de qualité industrielle ou de citations.
La [décision directe](../logs/foresight-runtime/user-scope-decision-20261011-drive-visual.json)
consigne aussi **l'exclusion de Google Drive**. Connexion, import et statut Drive
sont masqués lorsque sa capacité n'est pas explicitement active ; une ancienne
connexion ne l'active pas. Fichiers, dossiers, URL et ICS restent accessibles,
avec conservation du code, des jetons et de l'historique Drive.

Le [suivi ciblé](../logs/foresight-runtime/drive-exclusion-followup-20261011-214949/targeted-ts-build-v1/qualification.json)
réussit **61/61 Python Sources, 29/29 React dans deux fichiers**, TypeScript,
Ruff et build code 0. Le global 716/75 est **antérieur** aux changements Drive
et ne constitue pas une couverture globale actuelle ; aucun total n'est
additionné. Les assets actuels sont `index-Yuj98_lc.js` et `index-BJ0BE6LI.css`.
Une correction CSS limitée au bouton riche **Ajouter un élément** dans le
Studio mobile ≤670 px impose 44 px ; le desktop et l'éditeur legacy hors
Studio ne changent pas. Sa vérification navigateur reste distincte des tests.

## Démarrer une réunion — 12 octobre 2026

Le bouton **Nouvelle séance** reste visible quand l’espace est désactivé.
Le formulaire, également ouvert depuis Sources ou un projet, affiche alors
**Activer les réunions**. Cette action explicite conserve le mode, l’état de
préparation et les trois réglages distincts de transcription, de proactif et
d’enrichissement. Un refus d’autorisation est affiché et ne crée aucune séance.

Après **Ouvrir la séance**, la section **Choisir l’audio et démarrer** affiche
la sortie Windows à enregistrer, le sélecteur microphone et **Démarrer la
réunion**. Le microphone est décoché initialement et son sélecteur grisé jusqu’au
choix explicite. La sortie choisie est un flux à enregistrer ; la sortie de
lecture se règle dans Windows. Les choix sont figés pendant une commande de
démarrage conservée. Pause et Arrêt restent hors du volet Préparation et des
diagnostics, y compris avec un brouillon de note non appliqué.

Le navigateur et l’import audio sont dans une alternative distincte hors
Préparation, ouverte par défaut sans capture Windows installée. L’inventaire
navigateur ne demande pas d’accès au microphone. Le clic de démarrage transmet
le périphérique choisi exactement ; l’ouverture et les sélections seules ne
lancent aucun enregistrement. Ce changement de parcours ne clôture pas les
recettes matérielles, de transcription industrielle ni de durée du lot 12.

Vérification de ce parcours : **780/780 tests React dans 80 fichiers**, TypeScript,
build Vite et Ruff réussis. Le nouveau formulaire désactivé est vérifié sur
Agent **8001** ; les commandes du Studio sont vues sur des bases fictives avec
inventaire simulé et acquisition interdite. Le microphone réel n’a pas été
ouvert et les flags de production restent faux. Assets livrés :
`index-By33yhqn.js` et `index-DaoAx8MJ.css`. Reçu et captures :
[`logs/meeting-launch-ui-20261012/delivery.json`](../logs/meeting-launch-ui-20261012/delivery.json).
Sauvegarde préalable des fichiers modifiés et du build :
`backups/meeting-launch-ui-20261012-120052`.

## Éditeur de notes inspiré de XPilot — 12 octobre 2026

La disposition par défaut est une page de notes pleine largeur. Titre,
état de version, sauvegarde et copie sont réunis en tête. La barre compacte
regroupe style, gras, italique, listes, cases à cocher, insertion et annulation.
Les commandes de blocs, de tableaux et les formats secondaires restent dans
le menu d'insertion. Les blocs JSON existants forment visuellement un document
continu ; la compatibilité Markdown et les protections des brouillons restent
conservées. Entrée crée la suite du document, Retour arrière rejoint les blocs
vides et Tab gère les retraits ou la navigation dans les tableaux.
Les outils Notes enrichies, Transcription et Assistant ouvrent les panneaux
secondaires sans remonter l'éditeur ni perdre sa saisie. La préférence de
disposition utilise `agent-meeting-layout-v2` pour présenter cette page lors
du premier accès après mise à jour. Le menu principal et le contexte projet
restent disponibles.


### Lecture des mails — 15 octobre 2026
Sources et À trier partagent MessageContent : HTML filtré dans une iframe isolée, tableaux adaptés à la largeur, scripts et ressources distantes bloqués. Le texte simple conserve ses sauts de ligne et son historique repliable. Vérification ciblée : tests MessageContent et compilation frontend.


### Indexation et navigation — 15 octobre 2026
Statistiques et préparation des réunions : Réglages → Autres réglages, dans deux rubriques distinctes. Sources → Indexation des projets affiche la couverture réelle du moteur EG2 configuré, vérifiée par profil et empreinte de contenu, dans le périmètre accessible.
Le classement des mails et les imports alimentent déjà automatiquement EG2 réseau ; les vecteurs restent stockés dans l’index SQLite local. Aucun dossier réseau n’est parcouru. En mode réseau, la recherche de contenu dans Sources réutilise la recherche EG2 habituelle et ne démarre aucun encodeur local. L’index multimodal local reste réservé au mode local explicite ; il n’est ni démarré ni repris en mode réseau. Sa maintenance avancée reste accessible dans les réglages de recherche. Les anciens signalements de quota restent consultables, sans altérer les sources ni les classements.
L’API GET /api/v1/workspace/indexing est en lecture seule et distingue indexées, en attente, en échec, manquantes et sans texte. Tests ciblés de navigation, recherche et indexation ; compilation frontend.


### Présentation originale des mails — 15 octobre 2026
Sources et À trier affichent le HTML MIME original s’il est conservé, avec styles, polices, dimensions et couleurs du message. Les images CID raster sont incluses depuis l’original (2 Mio/image, 8 Mio au total). Les images distantes sont affichées uniquement sur demande. Le cadre isolé conserve les scripts, formulaires et appels réseau bloqués ; sa hauteur suit le contenu. Les artefacts d’indexation, données et classements restent inchangés.
Vérifications : tests mail_preview, MessageContent et lecteurs concernés ; compilation frontend.

### Réunion conservée : transcription complète et CR accessibles directement — 16 octobre 2026

Dans le Studio, les onglets Transcription et Synthèse ouvrent maintenant la
relecture complète et le compte rendu sans seconde barre d'onglets audio.
Le lecteur audio demeure disponible. Après création de l'enregistrement lié,
les anciens passages directs restent dans « Historique du direct (texte provisoire) »,
replié par défaut sous la transcription complète. Le direct courant reste déplié.
Les instantanés de source précédant une correction portent un titre historique explicite.

Les changements d'onglet conservent les saisies. Sauvegarder ou valider une
correction de transcription conserve aussi un brouillon de CR humain non publié.
S'il est devenu périmé, ce brouillon reste visible et sa publication est bloquée
jusqu'à remise à jour. Aucune synthèse ni publication n'est déclenchée en ouvrant
une vue ou en validant la transcription.

Vérification ciblée : le premier ensemble conserve 157 réussites et un échec
d'assertion sur la visibilité du CR périmé ; les deux essais intermédiaires sont
conservés. Le test intégré Studio + panneau audio vérifie ensuite le vrai parcours,
la conservation du brouillon après validation et le blocage de publication.
Sur la version finale du panneau audio, ses 15 tests et ce test intégré passent
(16/16). Les ensembles se recouvrent ; aucune nouvelle suite globale 943 ou backend
n'est revendiquée. TypeScript et Vite passent. Les trois assets servis sur Agent
8001 correspondent aux empreintes compilées ; le HTML correspond au texte lu par
mp_index(), après sa normalisation existante des fins de ligne. L'échec initial
du comparateur binaire HTML est conservé ; aucun second déploiement n'est effectué.

Activation statique après sauvegarde complète de web/dist, anciens assets conservés,
sans redémarrage du backend ni modification SQL. Aucun onglet utilisateur rechargé,
microphone, modèle ou GPU. La validation DOM ne remplace ni la recette matérielle
ni une mesure P95 visible ; L12 reste ouvert.

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

### Citations, arrêt mobile et fraîcheur des réponses — 16 octobre 2026

T08 et T13 sont maintenant clos dans la portée documentée. T08 utilise de vrais
handlers et fichiers fictifs, avec une réponse textuelle simulée : note historique
v1 consultable après écriture v2, audio fictif à1s avec segment1–4s/révision2,
PDF versionné à la page physique2 (repère imprimé7), feuille Banc electrique et
cellulesA2:C2, PNG entière avec légende manuelle de fixture. Les trois originaux
observés dans l’inspecteur sont récupérés par HTTP et vérifiés par SHA256 ;
l’ancien PDF est également intact. Aucune reconnaissance ou qualité ASR n’est
déduite de cette recette de citations.

T13 complète les dispositions et la navigation L06 par le vrai navigateur :
Tab/Entrée sur Arrêter et conserver à670px clair/enregistrement et320px
sombre/pause, après passage à Sources. Le bouton entier reste dans le viewport,
avec focus visible et sans débordement horizontal de page ; les deux POST STOP
simulés retournent200 et la barre disparaît. Les DTO et l’arrêt sont simulés,
aucun microphone/processus de capture physique n’est utilisé. La référence
publique et l’adaptation acceptée restent la portée ; aucune parité privée ou
conformité générale d’accessibilité n’est revendiquée.

La même recette a révélé un défaut T05 : une ancienne réponse ne portait pas
spontanément son avertissement après une modification externe de note. Le Studio
relit maintenant l’historique toutes les3s lorsqu’une discussion non vide est
visible, avec une seule lecture en vol. Cette lecture silencieuse ne relance
aucune IA. Le serveur décide de la fraîcheur et des droits ; les brouillons
restent intacts. Une réponse devenue inaccessible est retirée de l’affichage,
sans suppression de son historique serveur. L’erreur de lecture reste visible
avec possibilité de reprise. Les requêtes anciennes sont invalidées après une
nouvelle réponse ou un changement de contexte.

Trois cas reproduisaient le défaut ;96contrôles du Studio passent après correction,
ainsi que18contrôles du client. Les trois nouveaux cas passent à nouveau après
correction de deux options de types dans les tests ; ces cohortes se recouvrent.
TypeScript et Vite réussissent. Le premier contrôle TypeScript en échec est
conservé ; sa commande avait tout de même poursuivi Vite et n’est pas présentée
comme une chaîne entièrement verte. La vérification TypeScript distincte finale
termine avec code0. Les assets sont sauvegardés puis publiés sur8001 et comparés
aux octets HTTP, sans redémarrage backend.

Le navigateur confirme le correctif : une réponse sur la notev2 devient ancienne
après l’écriture v3, sans effacer la question encore en saisie ni produire une
quatrième réponse simulée. Les deux serveurs privés se ferment normalement
(codes0), les onglets temporaires sont fermés et le viewport est restauré.

Neuf recettes sont closes : T05/T06/T07/T08/T09/T10/T13/T14/T17. Neuf lots restent
clos ; L02/L03/L11/L12 restent ouverts. Le global frontend960 demeure la référence
antérieure au correctif, complétée par le ciblé96/18 et le retest3 ; aucun nouveau
global963 n’est annoncé. Le global backend actuel poursuit son unique passage.



### Preuves de l’assistant et panneau étroit — 21 octobre 2026

La question courante, lorsqu’elle est elle-même un segment interrogatif identique, est exclue des preuves de sa réponse ; sa transcription SQL reste conservée. Une affirmation identique à une recherche courte reste une preuve. Le prompt place désormais les extraits avant la question pour permettre la réutilisation du préfixe, sans réduire le budget1200tokens. Les quatre requêtes réseau fictives comparatives réussissent en0,76–1,60s ; cette mesure HTTP ne démontre pas le P95 visible du produit ni une causalité isolée du cache.

À814×668, le panneau Assistant sélectionné pouvait mesurer1,6px de haut quand les colonnes passaient sur deux lignes. Les lignes de grille gardent désormais250px minimum et restent accessibles par le défilement de la colonne. La vue réelle confirme250px de hauteur après correction.58tests backend ciblés,121tests frontend sur deux fichiers et TypeScript/Vite passent. Les assets précédents sont reconstitués à l’identique et conservés pour les onglets ouverts. Activation sur8001 après sauvegardes SQLite intègres et conservation des lignes préexistantes de19tables.

Les racines de calibration F13 sont conservées et fermées : deux contiennent une réponse réseau sans mesure visible qualifiée ; la troisième n’a lancé aucune question. Le navigateur/probe s’est bloqué sur une boucle d’observation de l’attribut disabled ; le setter conditionnel est corrigé hors ligne, sans nouvelle qualification navigateur revendiquée. Aucune mesure P95 actuelle complète, aucune clôture F13/L12 sur cette base. Aucun microphone, modèle local ou donnée métier de recette. Preuve : `logs/foresight-runtime/ASSISTANT-CONTEXT-VISIBLE-PANE-ROOT-20261021.json`.
