# Kiara 4.0.16 · Audit du code hérité

Audit du 18 novembre 2026. Le canal Windows et le client installé annoncent
tous deux la 4.0.16. L’examen couvre les parcours Windows et web privé,
les sources partagées avec les autres clients et les compatibilités du serveur
qui conditionnent leur retrait.

## Conclusions

L’ancienne barre fait toujours partie du document Conversations livré par
Kiara 4. La version 4.0.16 donne à la page autorisée le bon état de démarrage,
puis le JavaScript réorganise les éléments historiques pour construire la
navigation actuelle. L’ancienne disposition peut encore être choisie lorsque
la session Projets et la préférence locale de navigation manquent. Le retrait
à viser est celui de la barre classique du rendu Kiara 4, tout en gardant un
accès aux données anciennes et aux fonctions locales encore utilisées.

Deux effets sont reproductibles avec le code actuel. Le panneau Historique
reste invisible lorsque la barre est repliée. Sur le portail, ouvrir un projet
géré depuis l’historique amène encore à l’ancienne fiche locale.

## Constats et décisions de retrait

### P1 · Deux barres dans la page Conversations

- **Preuve.** Le document initial contient la marque classique, les boutons
  d’accès local et l’historique dans la barre. `applyUnifiedDom` déplace
  notamment Nouvelle conversation, Historique et Notifications, puis recrée
  les entrées de l’espace de travail. Le choix dépend de l’attribut reçu,
  de `fred-unified-navigation` ou du catalogue chargé ensuite. Le relais Windows
  installé renvoie un `<body>` simple sans session Projets et
  `data-kiara-unified-navigation="true"` avec la session. Une préférence déjà
  enregistrée peut stabiliser le premier cas. [Document initial](../../client-qwen/chat.html#L2) · [Assemblage de la barre](../../client-qwen/ui.js#L37) · [Relais Windows](../../client-qwen/client.py#L717) · [Relevé du relais](<D:/KRecette/audit-heritage-416/relais.json>)
- **À retirer de Kiara 4.** Produire un seul emplacement pour chaque entrée
  et rendre la barre Kiara dès le document initial. L’état de la connexion
  doit changer la disponibilité des destinations, sans choisir une autre
  navigation. Extraire le rendu classique derrière l’entrée de distribution
  qui le réclame, la 3.5.63 et les autres clients concernés restant à inventorier.
- **À conserver.** Le contenu de l’historique, la reprise de session, les
  brouillons et le repli de la barre. La récupération de la connexion et les
  mises à jour locales doivent rester possibles sans catalogue distant.

### P1 · L’historique est masqué quand la barre est repliée

- **Preuve.** Une règle générique masque `.history-navigation` sur tout le
  document dès que `sidebar-collapsed` est présent. Le conteneur est pourtant
  déplacé dans la barre d’outils du composeur. Le correctif CSS des descendants
  rétablit les libellés et la recherche mais laisse leur parent masqué.
  En 720p, 1080p et 1440p, le menu est ouvert et le conteneur a
  `display:none` avec zéro rectangle. Barre déployée, il s’affiche.
  [Styles historiques et actuels](../../client-qwen/ui.css#L209) · [Résultats et reproduction](<D:/KRecette/audit-heritage-416/historique.json>) · [Capture repliée](<D:/KRecette/audit-heritage-416/historique-replie-1280.png>)
- **À retirer.** Remplacer la règle globale par une règle qui cible uniquement
  l’emplacement classique tant qu’il est distribué. Dans Kiara 4, l’ouverture
  d’Historique doit afficher la liste quelle que soit la largeur de la barre.

### P1 · Une ancienne fiche Projets reste atteignable depuis le portail

- **Preuve.** Le bouton Ouvrir le projet dans l’historique ouvre la fiche Kiara
  seulement si `wsUsesUnifiedProjectPage` reconnaît Windows et le contrat
  `projects-v1`. Sous le web privé, un projet géré retombe donc sur
  `showView('projects')`. La recette reste à `/kiara/app/conversations`
  et présente les onglets Discussions et Mémoire au lieu d’ouvrir la fiche
  du projet. La navigation principale Projets dispose déjà de la destination
  serveur. [Choix du lien](../../client-qwen/workspace.html#L206) · [Bouton dans l’historique](../../client-qwen/workspace.html#L441) · [Capture de l’ancienne fiche](<D:/KRecette/audit-heritage-416/projet-ancien-1280.png>)
- **À retirer.** Faire pointer toutes les entrées d’un projet géré vers la
  même fiche, sur Windows et sur le portail. Garder l’ancienne vue
  uniquement derrière un parcours identifié tant que des projets privés
  ou des brouillons du stockage Workspace en dépendent. Le stockage
  serveur distingue encore projets gérés et projets privés.
  [Contrat de catalogue et stockage](../../lanceur/workspace.py#L313)

### P2 · Réglages charge un document Conversations complet

- **Preuve.** Le panneau intégré charge `/device-settings` ou
  `/app/device-settings`, qui servent le même modèle que Conversations
  avec un attribut et des styles de masquage. Le corps livré par le relais
  contient encore le composeur et la liste locale de projets. Le rendu
  synthétique web mesure 532 080 octets avant compression pour le panneau
  et 532 070 pour Conversations. Le démarrage du chat lit encore
  l’historique et l’adaptateur web peut initialiser un historique vide
  quand le compte n’en possède pas.
  [Cadre Réglages](../../agent/web/src/components/DeviceSettingsPanel.tsx#L5) · [Rendu web](../../lanceur/web_conversations.py#L27) · [Démarrage du chat](../../client-qwen/chat.html#L316) · [Adaptateur d’historique](../../client-qwen/web_conversations.js#L22)
- **À retirer.** Donner aux formulaires intégrés leur propre entrée légère.
  Garder les API existantes de connexion, mise à jour, vocal et notifications,
  les contrôles de session et la protection des modifications en cours.
  Préserver l’import et l’export de l’historique via des actions explicites
  sur Mon accès. L’ancien menu Réglages Windows reste testé comme repli
  lors d’un échec Projets. Il doit céder la place à un accès local ciblé
  avant de disparaître du client courant.
  [Recette du repli](../../client-qwen/test_ux_recovery_ui.cjs#L539)

### P2 · Dix redéfinitions de la même fonction de navigation

- **Preuve.** `showView` est défini dans `chat.html`, puis redéfini cinq
  fois dans `workspace.html` et une fois dans chacun de `ui.js`,
  `conversation.js`, `project-conversation.js`, `corrector.js` et
  `selection.js`. Le comportement dépend de l’ordre d’inclusion.
  Windows, Android et le portail assemblent leurs versions du même
  document à partir de ces scripts.
  [Fonction d’origine](../../client-qwen/chat.html#L318) · [Premières redéfinitions](../../client-qwen/workspace.html#L35) · [Assemblage Windows](../../client-qwen/client.py#L723) · [Assemblage Android](../../client-android/scripts/Prepare-Assets.py#L67)
- **À retirer.** Supprimer les redéfinitions au fil de l’extraction de la
  navigation classique. Le point d’entrée restant doit préserver la
  sélection, le focus, l’état des brouillons, le correcteur et le vocal.
  Le test de la destination atteinte doit passer par les boutons réels.

### P2 · Les anciennes URL sont encore créées par du code courant

- **Preuve.** Conversations émet `/app/reunions` tandis que la fiche projet
  et les filtres React utilisent `/app/meetings`. L’aide Réunions envoie
  encore à `/app/preparation` alors que le menu Réglages utilise
  `/app/settings?settings=preparation`. Les deux formes sont reconnues
  et certaines sont utilisées dans les tests. Le web et le client
  émettent aussi deux formes de liens vers une fiche projet.
  [Normalisation React](../../agent/web/src/lib/workspaceNavigation.ts#L25) · [Liens de réunions](../../agent/web/src/lib/meetingWorkspace.ts#L3) · [Lien depuis la préparation](../../agent/web/src/components/WorkspaceViews.tsx#L241)
- **À retirer.** Cesser de générer les anciennes formes dans les écrans
  courants. Choisir un lien canonique par destination et laisser un seul
  adaptateur à l’entrée pour les signets et les versions déjà installées.
  Vérifier les paramètres de projet, les filtres et le retour arrière.

### P2 · L’ancienne politique de rendu Jinja est toujours active en repli

- **Preuve.** `HTTPProtection` vérifie l’existence du bundle et autorise
  `unsafe-inline` pour les anciens chemins `/ui` ou quand le bundle manque.
  Les chemins `/ui` du service renvoient des redirections et l’absence du
  bundle renvoie un 503. La recherche dans les modules applicatifs ne trouve
  ni `Jinja2Templates`, ni `TemplateResponse`, ni import direct de `jinja2`.
  Les règles de la documentation API restent explicites et indépendantes.
  [Politique de réponse](../../agent/app/http_protection.py#L60) · [Routes de redirection et gestion du 503](../../agent/app/main.py#L246)
- **À retirer.** Confirmer que les consommateurs internes passent par ces
  redirections, appliquer la politique du rendu courant à ces réponses
  et vérifier séparément si Jinja est encore nécessaire au paquet.
  Garder la vérification de fonctionnement de la documentation API.

### P3 · Styles orphelins et versions dupliquées dans la documentation

- **Preuve.** Les neuf déclarations de `.workspace-project-menu` ne sont
  référencées que dans la feuille de style. La clause
  `.workspace-shell:not([data-kiara-navigation="true"])` vise une variante
  que le seul composant qui instancie `.workspace-shell` ne rend plus.
  `.workspace-favorites` et `ProjectFolder` ont encore des usages.
  Le guide Windows annonce 4.0.13 et la matrice de compatibilité 4.0.12,
  alors que le canal et le client contrôlés sont en 4.0.16.
  [Styles hérités](../../agent/web/src/workspace-shell.css#L24) · [Barre rendue](../../agent/web/src/components/WorkspaceShell.tsx#L449) · [Guide Windows](../../client-tauri/README.md#L1) · [Matrice de compatibilité](../../maintenance/COMPATIBILITE.md#L5)
- **À retirer.** Supprimer les sélecteurs orphelins après vérification visuelle.
  Faire pointer les guides courants vers la même référence de version et
  laisser les numéros précédents dans les notes de livraison datées.

## Compatibilités encore justifiées

| Élément | Preuve et condition de retrait |
| --- | --- |
| Client classique Windows 3.5.63 | Le parcours Passer à Kiara 4 et la reprise des profils chiffrés sont documentés et raccordés à `/client/update/kiara4`. Identifier les postes qui passent encore par ce canal avant d’en retirer le rendu. [Transition Windows](../../client-tauri/README.md#L6) · [Route de migration](../../client-qwen/client.py#L954) |
| Préfixe privé `/agent/` et routes `/ui` | Le premier est servi et testé pour des liens existants. Les secondes redirigent dans le service et leur comportement est testé. Vérifier les appelants de chaque famille avant de les retirer. [Passerelle privée](../../lanceur/agent_web.py#L68) · [Tests des redirections](../../agent/tests/test_audit_regressions.py#L189) |
| Routes console et configuration Projets | Le script de démarrage tente encore l’alias `/api/agent-service` et le serveur accepte l’ancienne configuration. Recenser les lanceurs et les installations qui l’utilisent avant de les retirer. [Démarrage](../../Start-Interface-Qwen.ps1#L12) · [Configuration](../../lanceur/agent_service.py#L34) |
| Android, Linux et données historiques | L’assemblage partagé sert plusieurs cibles. Les historiques, les brouillons, les reçus de commande, les sauvegardes et les clés ont leur propre compatibilité. La qualification d’un nouveau client et les restaurations sur copie précèdent le retrait de ces contrats. [Matrice de compatibilité](../../maintenance/COMPATIBILITE.md#L5) |

## Ordre de réalisation

1. Rendre l’historique utilisable barre repliée et corriger le lien du projet
   géré depuis l’historique. Rejouer les deux cas aux trois résolutions de
   recette et conserver les droits du compte.
2. Rendre la barre Kiara unique sous Windows 4 et sur le portail privé.
   Vérifier le démarrage à froid, le thème sombre, la barre repliée,
   le chargement lent, une session Projets indisponible, le clavier,
   les brouillons et le menu de récupération locale. Séparer le rendu
   classique à la construction avant de supprimer ses emplacements du
   client courant.
3. Alléger le panneau Réglages, réduire les redéfinitions de navigation
   et retirer les sélecteurs orphelins et le repli Jinja. Vérifier
   l’enregistrement, la reprise après échec et les actions locales sur
   les écrans concernés.
4. Cesser d’émettre les anciennes URL et mettre les guides à jour. Recenser
   les appareils, raccourcis et automatisations qui appellent encore les
   anciennes entrées. Qualifier le retour avant de retirer un ancien canal
   ou une redirection qui a encore des appelants.

## Vérifications et limites

- Lecture des chemins rendus et appelants dans les sources Windows, web,
  Android, Linux et serveur. Vérification de la version du canal et du
  rendu HTTP du relais Windows installé.
- Reproduction Chromium avec historique et projet fictifs en 720p, 1080p
  et 1440p. Le cas Historique ouvert mais invisible et le passage à
  l’ancienne fiche sont documentés dans les mêmes observations.
  [Script de recette](<D:/KRecette/audit-heritage-416/historique.cjs>) · [Observations](<D:/KRecette/audit-heritage-416/historique.json>)
- La recette Windows `test_ux_recovery_ui.cjs --windows-only` passe.
  Elle couvre notamment la reprise des brouillons et le repli de Réglages
  quand le service Projets refuse d’ouvrir une session.
- L’usage des anciennes versions sur les autres postes, les signets
  enregistrés et les scripts hors dépôt reste à établir avant leur retrait.

## Mise en œuvre dans Kiara 4.0.17

1. Historique et ouverture de la fiche projet corrigés côté Windows et portail. La recette couvre 720p, 1080p et 1440p, ainsi que l’ouverture et la fermeture de l’historique au clavier.
2. Conversations reçoit la barre Kiara dès la première réponse HTTP. Les commandes de récupération restent accessibles dans Réglages du client Windows quand l’espace de travail est indisponible. Le navigateur ne reconstruit plus la navigation à l’arrivée du catalogue.
3. Notifications dispose d’une page indépendante et réutilise le formulaire de la boîte de réception. Elle conserve les choix en cas de conflit et recharge la révision avant une nouvelle tentative. Les autres réglages de l’appareil utilisent le panneau partagé avec un démarrage allégé. Seule la rubrique Mon accès charge l’historique de ce panneau pour les transferts. La navigation a un point d’entrée, les styles orphelins et le repli CSP de Jinja ont été retirés. L’extraction des autres formulaires de l’appareil reste à faire.
4. Les liens courants convergent vers les mêmes destinations. Les anciens signets sont acceptés et leurs paramètres sont conservés à la normalisation. Le relevé des appelants et les conditions de retrait figurent dans la [matrice de compatibilité](../../maintenance/COMPATIBILITE.md).

Le paquet Windows 4.0.17 a passé la recette WebView2 et a été installé sur le poste courant. Le canal Windows sert le paquet vérifié par son manifeste Ed25519. Le portail privé sert le nouvel index et la bascule a retrouvé les 11 projets attendus. Les suites ont validé 1 232 tests web, 21 tests Agent et les parcours navigateur Windows, Android et Linux. Les vérifications Android et Linux ont porté sur le rendu de recette.

[Qualification Windows](<D:/KRecette/nettoyage-417/candidat-verifie.json>) · [Vérification du relais installé](<D:/KRecette/nettoyage-417/client-portail-verifie.json>) · [Contrôle de production](<D:/KRecette/nettoyage-417/production-verifiee.json>)

### Stabilisation dans Kiara 4.0.18

La recette du premier affichage a détecté que l’arrivée du catalogue ajoutait une ligne au-dessus des conversations. Assistant de projet est désormais intégré à la barre d’outils dès le rendu initial et s’active lorsque le catalogue est prêt. La hauteur initiale de la zone de saisie tient compte de ses commandes.

La barre d’outils et le champ de message restent stables pendant le chargement aux trois résolutions, en thème clair puis en thème sombre avec la barre repliée. L’historique et la fiche projet ont été rejoués aux trois résolutions. Les six boutons de la barre ont été vérifiés sur le portail avec les nouvelles destinations.

La 4.0.18 est publiée et installée sur le poste Windows courant. Le relais installé a servi la nouvelle barre et le panneau Notifications sous session locale. Le portail privé est en service avec les 11 projets attendus.

[Qualification WebView2](<D:/KRecette/nettoyage-418/candidat-verifie.json>) · [Recette de l’historique](<D:/KRecette/nettoyage-418/historique/historique.json>) · [Contrôle de production](<D:/KRecette/nettoyage-418/production-verifiee.json>)

### Fin du lot Réglages dans Kiara 4.0.19

Sur Windows, Conversation vocale, Dictée, Connexion au serveur, Mises à jour et API locale et intégrations chargent chacune un formulaire dans la même page Réglages. Le menu reste visible et l’historique de navigation retrouve la rubrique sélectionnée. Les formulaires de l’appareil réutilisent les commandes locales du client. Ils sont servis par le relais Windows.

Lorsque la session Projets ne peut pas être ouverte, Réglages de cet appareil donne accès aux cinq rubriques. La fenêtre Conversations propose aussi Réglages de connexion dans son diagnostic. L’adresse peut être enregistrée et une nouvelle tentative lancée hors connexion. L’écran Mises à jour indique l’échec d’une vérification lorsque le serveur est injoignable.

La recette WebView2 couvre les trois résolutions, le clavier, le rechargement des réglages et la reprise après un refus d’enregistrement vocal. Le relais de test a écrit les préférences et l’adresse dans le fichier chiffré d’un profil de recette. L’interface a aussi été vérifiée avec des réponses simulées pour l’installation du modèle de dictée, l’intégration API et la mise à jour. [Menu Réglages et Connexion](<D:/KRecette/reglages-419/visuel/menu-connexion-1280.png>) · [Récupération hors connexion](<D:/KRecette/reglages-419/visuel/recuperation-sombre-1280.png>)

La 4.0.19 est publiée sur le canal Windows et installée sur le poste courant. Les cinq formulaires et la page de récupération ont répondu sur le relais installé. Le portail a retrouvé les 11 projets après la bascule. [Contrôle de production](<D:/KRecette/reglages-419/production-verifiee.json>) · [Vérification du client installé](<D:/KRecette/reglages-419/client-portail-verifie.json>)
