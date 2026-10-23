# Audit UX de Fred — 22 octobre 2026

**Suivi : corrections appliquées et vérifiées.** Voir le [compte rendu des corrections](<D:/Serveur IA/audits/2026-10-22-ux/CORRECTIONS.md>). Le rapport ci-dessous conserve les constats initiaux.

**Résultat : 12 constats regroupés, dont 4 P1, 6 P2 et 2 P3. Aucun P0 confirmé dans les parcours exécutés.** L’interface permet de travailler, avec une navigation cohérente dans ses grandes lignes et une récupération des documents convaincante. Les priorités concernent la protection des saisies, le contexte des conversations et l’utilisation au clavier. Une refonte graphique générale ne se justifie pas au vu de cet audit.

Ce rapport analyse les sources de travail, avec leurs modifications en cours. Il ne certifie ni une version livrée, ni une conformité WCAG complète. Aucune correction applicative n’a été faite. Les fichiers ajoutés pour cet audit sont regroupés dans ce dossier.

## Environnement et preuves

- Chrome sans profil personnel, Playwright MCP, version de navigateur observée : 156.0.8078.47.
- Client Windows : sources réelles servies par la fixture existante `lanceur/web/tests/lots6_8_fixture.py`, sur `http://127.0.0.1:60642/chat` pendant l’audit.
- Console : même fixture sur `http://127.0.0.1:60643/#…`, avec stockage temporaire et deux accès fictifs. Aucun démarrage de modèle, changement de pare-feu ou publication de version pour cet audit.
- Android : HTML produit en mémoire par le véritable `Prepare-Assets.py`. Le contenu a été chargé sur l’origine de la fixture Windows par interception Playwright, afin de conserver les contrôles d’origine du serveur. Le proxy d’audit avait initialement provoqué des refus 403 ; ils ont été résolus pour les scénarios et ne sont pas comptés comme défauts Fred.
- Bureau 1440 × 900 ; téléphone 390 × 844 ; tablette 768 × 1024. Client Android : huit vues aux deux dernières tailles. Console : seize rubriques sur bureau et sept rubriques représentatives aux deux tailles réduites. Thèmes clair et sombre examinés sur des écrans représentatifs.
- Hauteur réduite 390 × 470 pour simuler l’espace occupé par un clavier Android. Taille 720 × 450 pour examiner un espace CSS équivalent à un bureau 1440 × 900 à 200 %. Il ne s’agit ni d’un clavier physique testé, ni d’une validation du zoom natif du WebView.
- 91 captures dans `captures/`, complétées par deux captures de chargement synthétique. Captures examinées, avec défilement vers le bas des principaux écrans longs. Les noms des fichiers précisent la surface et la largeur.
- Arbres accessibles : [Windows](<D:/Serveur IA/audits/2026-10-22-ux/windows-screens.json>), [Android](<D:/Serveur IA/audits/2026-10-22-ux/android-screens.json>), [console](<D:/Serveur IA/audits/2026-10-22-ux/console-screens.json>). Résultats de reproduction : [reproductions.json](<D:/Serveur IA/audits/2026-10-22-ux/reproductions.json>). Empreintes des sources et liste des captures : [inventory.json](<D:/Serveur IA/audits/2026-10-22-ux/inventory.json>).

Les données métier sont fictives : projet « Sources et notifications », document « Contrat de référence », messages et mémoires créés uniquement dans la fixture. Les clés locales sont éphémères ; les valeurs des champs de clé ont été masquées dans les fichiers d’arbres accessibles.

## Couverture des parcours

| Surface | Écrans examinés | Interactions et états réellement vérifiés |
| --- | --- | --- |
| Conversations | Accueil vide, conversation avec réponse, choix de modèle, historique, diagnostic | Envoi avec réponse synthétique ; nouvelle conversation ; suppression puis annulation ; message non envoyé au rechargement ; changement de contexte ; panne de catalogue injectée et reprise |
| Projets | Liste, Documents, Discussions, Mémoire, Consignes | Ouverture du projet et d’un document ; édition et sauvegarde ; échec 503 injecté ; récupération du brouillon après rechargement ; création et suppression d’une mémoire ; consignes non enregistrées ; import déclenché au clavier |
| Sources | Fenêtre d’un passage cité dont le document a changé | Version citée conservée, avertissement de modification, ouverture et fermeture par Échap ; ouverture via la fonction de l’application pour atteindre cet état |
| Tâches | Liste vide, formulaire, tâche terminée | Création d’une tâche fictive, exécution avec modèle synthétique, résultat terminé visible ; filtres et options inspectés |
| Notifications | Boîte avec notifications et préférences | Actualisation, marquage de toutes les notifications comme lues ; lecture des états et noms accessibles |
| Correcteur | Deux colonnes sur bureau, empilement sur mobile | États initial et désactivé examinés visuellement ; succès, interruption, erreurs et persistance couverts par les suites UI existantes |
| Réglages Windows | Accès/apparence, connexion, mises à jour, API/intégrations | Navigation entre rubriques ; changement de thème ; lecture de la configuration ; aucune installation ni modification d’intégration |
| Android | Accueil, projets, correcteur, tâches, notifications, accès, connexion, API | Mêmes écrans dans le HTML Android ; premier démarrage sans profil injecté ; Échap ne contourne pas l’import obligatoire ; hauteur de clavier simulée |
| Console | Vue d’ensemble, calcul, fichiers, clients, appareils, accès distant, API, mises à jour, espaces, connaissances, web, tâches, sauvegardes, démarrage, notifications, journaux | Navigation, onglets clavier, défilement, états vides ; modification locale d’un champ puis rechargement sans sauvegarde ; lecture des formulaires d’administration |
| Catalogue et chargement | Catalogue Hermes, progression du chargement, erreur et validation | 20 contrôles du catalogue synthétique ; 10 contrôles de parsing et 12 contrôles navigateur du chargement, dont mouvement réduit et largeur mobile |

Les formulaires d’administration ont été parcourus et lus. L’audit ne prétend pas avoir exécuté toutes les commandes administratives, toutes les combinaisons de filtres ou toutes les options repliées.

## P1 — à traiter en premier

### UX-01 — Saisies perdues au rechargement sans avertissement

**Constat reproduit.** Saisir une consigne de projet, constater « Consignes à enregistrer », puis recharger : le texte disparaît sans boîte d’avertissement. Même résultat pour un message de conversation non envoyé. Dans la console, un contexte modifié à `12000` revient à `32768` au rechargement, sans avertissement.

**Impact :** perte de travail non enregistré et protection différente selon les zones de saisie. Les documents, eux, récupèrent correctement leur brouillon après une erreur.

**Emplacements :** [chat.html:13](<D:/Serveur IA/client-qwen/chat.html:13>), [workspace.html:59](<D:/Serveur IA/client-qwen/workspace.html:59>), formulaire de calcul dans [app.js](<D:/Serveur IA/lanceur/web/app.js>). Preuve fonctionnelle : `reproductions.json`, entrée `draftLoss` ; état initial des consignes : `captures/windows-project-instructions.png`.

**Correction proposée :** conserver les brouillons de messages par conversation ; conserver les consignes en attente ou avertir avant un départ avec modifications ; signaler explicitement la récupération. Pour la console, garder l’enregistrement explicite mais avertir en cas de fermeture ou rechargement avec modifications. Vérifier aussi l’événement natif de fermeture Windows/Android, non testé ici.

**Critère de recette :** un rechargement permet de retrouver la saisie ou affiche un avertissement avant sa perte. Une erreur de sauvegarde reste visible.

### UX-02 — Le message en préparation suit une nouvelle conversation

**Constat reproduit.** Écrire « Message fictif destiné uniquement à la discussion A. », puis cliquer « Nouvelle conversation » : l’identifiant de conversation change, mais le champ de message conserve ce texte.

**Impact :** risque d’envoyer une demande préparée dans le mauvais contexte, notamment en passant d’un projet à un autre. Le champ donne l’impression d’appartenir à la conversation affichée.

**Emplacements :** [chat.html:254](<D:/Serveur IA/client-qwen/chat.html:254>) et gestion du changement de conversation autour de la ligne 99.

**Correction proposée :** rattacher chaque brouillon à son identifiant de conversation. La nouvelle conversation commence avec un champ vide ; revenir à l’ancienne restaure sa saisie. Prévoir explicitement le transfert si cet usage est souhaité, sans perdre le texte.

**Critère de recette :** deux conversations conservent chacune leur brouillon et leur contexte de projet, y compris après rechargement.

### UX-03 — Le focus passe derrière la navigation latérale ouverte

**Constat reproduit sur les dispositions étroites du client et de la console.** Ouvrir la navigation au clavier laisse le focus sur le bouton d’ouverture. Les Tab suivants atteignent le contenu derrière le voile. Dans le client, la recherche de projet et ses commandes reçoivent le focus alors qu’elles sont masquées par le menu. Après activation d’une rubrique, le focus peut rester brièvement dans la navigation devenue `inert` ; Échap ne restaure pas systématiquement le bouton d’ouverture.

**Impact :** navigation difficile pour les personnes au clavier, avec loupe ou avec une technologie d’assistance. Le défaut touche une fonction utilisée sur tous les écrans.

**Emplacements :** [ui.js:17](<D:/Serveur IA/client-qwen/ui.js:17>), lignes 18, 71 et 75 ; [interface.js:10](<D:/Serveur IA/lanceur/web/interface.js:10>) à 16.

**Correction proposée :** à l’ouverture, placer le focus dans la navigation ; si le voile correspond à un panneau modal, rendre le contenu arrière inerte et contenir le focus. À Échap, rétablir le bouton d’ouverture. Après choix d’une rubrique, déplacer le focus vers son titre ou sa première commande utile.

**Critère de recette :** parcours complet au clavier sur 390 et 768 px, sans cible masquée et avec retour du focus. Le panneau ne doit pas empêcher la fermeture ni la lecture du contenu choisi.

### UX-04 — Une mémoire se supprime immédiatement sans récupération proposée

**Constat reproduit deux fois sur des mémoires fictives.** Un clic sur « Supprimer » retire la mémoire du snapshot serveur. Aucun dialogue n’est émis et aucun bouton d’annulation n’est proposé dans cette rubrique.

**Impact :** suppression accidentelle d’une information métier sans retour disponible dans l’écran. Le comportement diffère des conversations, qui proposent une annulation, et des documents, qui demandent confirmation.

**Emplacement :** [workspace.html:56](<D:/Serveur IA/client-qwen/workspace.html:56>). Capture de l’action et de son retour trompeur : `captures/windows-memory-delete-stale.png`.

**Correction proposée :** proposer une annulation fiable, ou une confirmation nommant la mémoire. Ne pas limiter le correctif à masquer la ligne : la récupération doit être réelle.

**Critère de recette :** un clic involontaire peut être annulé ou n’exécute pas directement la suppression ; l’échec serveur laisse le contenu accessible.

## P2 — accessibilité, compréhension et retours d’action

| Référence | Constat et preuve | Impact | Correction proposée |
| --- | --- | --- | --- |
| **UX-05 — Contraste clair insuffisant pour des textes secondaires** | Couleur calculée `#73736d` sur `#f7f7f5` : **4,447:1**. Texte du compteur sur `#f0f0ed` : **4,178:1**. Exemples mesurés : noms de navigation et version du client. Variables et composants : `client-qwen/ui.css:1`, `:5` ; palette analogue dans `lanceur/web/interface.css:2`. | Les petits textes concernés n’atteignent pas le seuil de 4,5:1 ; l’écart est faible pour la navigation, plus net pour le compteur. Le classement P2 tient compte de cette amplitude. | Ajuster la variable de texte secondaire en vérifiant ses différents fonds ; mesurer à nouveau clair et sombre. Conserver les distinctions de statut. |
| **UX-06 — Noms accessibles manquants dans les mémoires et les sources** | Les champs de mémoire existante sont exposés comme `textbox` sans nom ; la fenêtre de citation comme `dialog` sans nom, même avec un titre visible. `workspace.html:56`, `:88–89`. Preuves : `captures/windows-memory-created.png`, `captures/windows-source-dialog.png`. | Plus difficile de savoir quel contenu est édité et quelle fenêtre vient de s’ouvrir. | Ajouter un label propre à chaque mémoire et relier la fenêtre à son titre par `aria-labelledby`. Les labels peuvent être visuellement discrets sans supprimer les titres métier. |
| **UX-07 — Sélection des rubriques mal exposée aux aides techniques** | Les boutons Documents/Discussions/Mémoire/Consignes portent `aria-selected` sans rôle compatible ; le snapshot les annonce comme de simples boutons. Les filtres de tâches s’appuient sur une classe visuelle. `ui.js:77`, `workspace.html:7`, `:18`. | L’état choisi est clair visuellement mais mal communiqué autrement. | Employer une navigation avec `aria-current`, ou un vrai ensemble d’onglets avec rôles et navigation clavier ; pour les filtres, utiliser `aria-pressed` si ce sont des boutons de filtrage. Ne pas ajouter seulement des rôles sans leur comportement attendu. |
| **UX-08 — Aucun repère principal actif hors conversation** | Dans Projets Android, `getByRole('main').count()` retourne **0**. Le seul `<main>` du client contient les messages et devient caché sur les autres vues. `chat.html:10–12`, `workspace.html:2`. | Les personnes naviguant par repères n’ont pas d’accès direct au contenu principal de Projets, Tâches ou Réglages. | Donner un repère principal stable au contenu actif et prévoir un accès clavier direct au contenu ; éviter plusieurs repères principaux simultanés. |
| **UX-09 — Le bouton d’envoi change de ligne et de position sur téléphone** | À 390 px, le bouton Envoyer passe sous les outils, à gauche ; le contrôle Réflexion occupe encore une autre ligne. Position mesurée : `x=22`, largeur `44`. Voir `captures/android-chat-390.png` et `captures/android-dark-chat-390.png`. `client-android/mobile-ui/android.css:49–50`, disposition partagée `.send-row`. | L’action principale est moins facile à repérer et la barre de composition prend davantage de hauteur, surtout avec le clavier. Elle reste accessible dans la simulation testée. | Réserver un emplacement stable à l’envoi dans la grille de composition ; faire revenir les options secondaires sur une ligne dédiée. Conserver pièce jointe, projet et réflexion. |
| **UX-10 — La mémoire supprimée reste affichée** | Après suppression : **0 mémoire côté snapshot, 1 champ encore affiché**. La ligne disparaît après sortie du focus puis actualisation. `workspace.html:47`, `:56`. Reproduction enregistrée dans `reproductions.json`, entrée `memoryGhost`. | L’utilisateur peut croire que la suppression a échoué, recliquer ou tenter de modifier un objet disparu. | Limiter la protection contre le rafraîchissement aux champs réellement en cours d’édition ; appliquer immédiatement le résultat d’une action locale réussie et annoncer son succès, sans détruire un autre brouillon. |

## P3 — finition et cohérence

| Référence | Constat | Proposition |
| --- | --- | --- |
| **UX-11 — Textes d’aide très petits et réglage de lecture partiel** | Plusieurs aides, informations de contexte et légendes utilisent 9–10 px. Les options 14–19 px concernent surtout les conversations et le correcteur ; elles n’agrandissent pas tous les réglages. `ui.css:5–6`, `interface.css:4`, `android.css:17–20`. Ce constat est un jugement de lisibilité, pas une non-conformité déduite de la seule taille. | Relever les informations nécessaires à la décision et proposer une densité confortable sur téléphone. Conserver une densité de travail utile sur ordinateur. Tester l’agrandissement système sur appareil. |
| **UX-12 — Terminologie et aides parfois désalignées** | « Modèle et calcul » dans la navigation devient « Calcul & lancement » dans le titre. « Fichiers du modèle » devient « Modèle & fichiers ». L’aide des discussions parle de glisser et de « clic droit » dans la version Android. « sans login » apparaît dans Mon accès. | Aligner les noms des destinations et adapter les aides à l’appareil, sans retirer les informations techniques utiles aux rubriques API et administration. |

### Relecture des textes visibles

| Source | Texte actuel | Catégorie | Proposition |
| --- | --- | --- | --- |
| `workspace.html:12` | « Glissez une conversation sur un projet pour la déplacer. Clic droit pour déplacer, archiver ou supprimer. » | Utile ; dépend de l’appareil | Android : « Ouvrez le menu ⋯ d’une conversation pour la déplacer, l’archiver ou la supprimer. » Bureau : conserver l’aide au clic droit et son alternative clavier. |
| `workspace.html:52` | « 1 nouveau(x) résultat(s) disponible(s). » | Utile ; formulation à simplifier | Adapter le pluriel : « 1 nouveau résultat disponible. » / « 2 nouveaux résultats disponibles. » |
| `chat.html:16` | « EXE personnel · sans login » | Technique sans utilité dans le badge | « Accès personnel ». Garder l’explication du fichier personnel et de sa confidentialité dans le texte d’aide. |
| `interface.js:6`, `index.html` | « Modèle et calcul » / « Calcul & lancement » | Même destination, deux noms | Utiliser « Modèle et calcul » dans la navigation et dans le titre. |
| `chat.html:16` | « Ouvrez votre EXE : le tunnel sécurisé se connecte au serveur. » | Essentiel mais trop spécifique au transport | « Ouvrez votre application : elle se connecte au serveur avec votre accès personnel. » Garder le nom du transport dans Connexion. |

Les neuf avertissements automatiques de longueur sont des pistes de relecture. Plusieurs concernent des avertissements de sécurité ou des explications d’administration nécessaires : ils ne sont pas comptés comme neuf défauts et ne justifient aucune suppression automatique.

## Ce qui fonctionne et doit être préservé

- Les vues principales sont faciles à retrouver ; les réglages techniques restent largement séparés du travail quotidien. Les conventions visuelles Windows/Android/console sont proches.
- Le document affiche une sauvegarde en cours puis son résultat. En cas de 503 simulé, l’erreur reste visible et le brouillon réapparaît après rechargement : `captures/windows-document-save-error.png`.
- La conversation supprimée peut être restaurée par « Annuler la suppression » ; les messages retrouvent leur contenu.
- Le modèle indisponible bloque l’envoi et affiche un message utile. Les tests existants vérifient qu’une actualisation du catalogue ne remplace pas le choix en cours ni le focus du sélecteur.
- Les passages cités conservent la version réellement utilisée et avertissent quand le document a changé.
- La progression de chargement précise les étapes et l’avancement mesuré ; le mouvement réduit est pris en compte dans les contrôles rejoués.
- Aucun débordement horizontal global mesuré sur les vues parcourues à 390 et 768 px. Quelques contrôles de défilement internes dépassent leur conteneur ; cela n’a pas été classé comme défaut de page sans conséquence utilisateur démontrée.
- Les noms accessibles des boutons à icône principaux, les avertissements d’export non chiffré et les informations utiles de connexion sont présents. Ils doivent être conservés.

## Vérifications et limites

| Vérification | Résultat | Portée réelle |
| --- | --- | --- |
| `npm.cmd --prefix client-qwen test` | **5 suites réussies** | Conversation vocale simulée, correcteur Windows/Android, événements Hermes, sélecteur de modèles, réflexion ; ne valide ni microphone ni serveur de modèle réel |
| `npm.cmd --prefix client-qwen run ux:check:all` | 46 fichiers, **9 avertissements**, aucune exclusion locale | Analyse heuristique des sources ; ne mesure ni contraste ni focus |
| `node lanceur/web/tests/hermes_models_ui.cjs --proof …` | **20 contrôles réussis** | Partage de modèles et comptes synthétiques ; rapport `hermes-models.json` |
| Test de chargement adapté dans ce dossier | **10 contrôles de parsing + 12 navigateur réussis** | Fixture locale, états injectés, tailles 1440 et 390 ; `model-loading/validation.json` |
| Audit manuel Playwright MCP | Constats ci-dessus reproduits | Clavier, arbres accessibles, captures, dimensions, erreurs injectées et données fictives |

Une première exécution du test de chargement existant a effectué des requêtes **GET** sur la console locale `127.0.0.1:8765`, car cette adresse est codée dans ce test. Aucune écriture ni commande de production n’a été exécutée. Le test a ensuite été adapté et rejoué sur la fixture ; les deux captures conservées dans `model-loading/` ont été remplacées par celles de la fixture. Le résultat final porte sur cette exécution isolée.

Les sources de la console ont évolué pendant l’audit, notamment l’ajout de la carte « Qwen sur le réseau local ». Le serveur de fixture, chargé avant cet ajout, n’exposait pas le nouveau script. L’état de chargement de cette carte n’est donc **pas** présenté comme un défaut produit. Son fonctionnement avec le backend courant, les autorisations Windows et le pare-feu reste à vérifier. Les empreintes enregistrées à la fin servent à identifier les sources relues, sans faire croire que toutes ont été figées pendant l’ensemble de la session.

Non vérifiés matériellement : WebView Android, TalkBack/NVDA, toucher réel, clavier logiciel réel, microphone, lecture audio, permissions de notifications, import natif de profil, installation et retour arrière des mises à jour. Les mises à jour n’ont pas été installées. Les sauvegardes/restaurations, révocations d’accès, démarrages de moteurs et changements de réseau n’ont pas été exécutés pour vérifier l’UX. Aucun benchmark de latence avec un modèle réel, ni test utilisateur d’utilisabilité n’a été réalisé.

## Ordre proposé pour les corrections

1. **Protection du travail : UX-01, UX-02, UX-04.** Harmoniser les brouillons et les suppressions, en réutilisant la récupération des documents et l’annulation des conversations.
2. **Navigation et accessibilité : UX-03, UX-05 à UX-08.** Corriger le focus et les informations exposées, puis mesurer les couleurs sur leurs fonds réels.
3. **Retours d’action et téléphone : UX-09, UX-10.** Stabiliser la composition et mettre à jour les lignes après une action réussie.
4. **Finition : UX-11, UX-12.** Améliorer la lisibilité et les textes après stabilisation du comportement.

Après correction, rejouer les reproductions de chaque constat, les cinq suites partagées, le contrôle UX sur les sources touchées et les captures concernées. Ajouter des tests ciblés sur la récupération des saisies et le focus des panneaux ; ces comportements ne sont pas couverts par le simple contrôle statique.

Références utilisées : [WCAG — contraste](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [ordre du focus](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html), [taille des cibles et exceptions](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md). Les recommandations génériques ont été adaptées au français, à la densité métier de Fred et aux composants existants.
