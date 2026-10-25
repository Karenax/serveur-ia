# Rafraîchissements périodiques — 24 octobre 2026

Le signalement concerne Android et Windows : sauts visuels récurrents, estimés
à une trentaine de secondes. Le serveur est prêt, ses processus Qwen restent
chargés et les 148 lignes de journal consultées ne contiennent ni déconnexion,
ni timeout, ni erreur de transport. Le journal réseau en mémoire des clients
distants n’est pas accessible depuis ce poste : aucun client Windows n’écoute
sur ses ports locaux et aucun appareil Android physique n’est connecté.
Cette vérification ne prouve donc pas l’absence d’une coupure côté appareil.
Voir `connection-evidence.json`.

## Causes reproduites dans les interfaces partagées

- Le suivi vocal appelle son actualisation toutes les 200 ms. Il reconstruisait
  aussi la liste des conversations, y compris en dehors de la page Vocal.
  La mesure initiale relève onze remplacements de liste en un court scénario.
- Le catalogue se vérifie toutes les 15 secondes. Une vérification normale
  faisait apparaître « Actualisation des modèles » et pouvait remplacer
  l’indication de connexion par « Vérification HTTPS/WireGuard », alors que
  la connexion restait active.
- Les notifications se synchronisent également toutes les 15 secondes et
  recréaient leur contenu et leur bouton de navigation à données identiques.
  Les projets et tâches se reconstruisaient après chaque contrôle de cinq secondes.
- Un appel de rendu du chat reconstruisait tous ses messages même lorsqu’ils
  étaient identiques, perdant les éléments ouverts et leur identité DOM.

Il ne s’agit pas d’un appel périodique à `location.reload()`. Les cycles observés
expliquent des changements visibles répétés sans nécessiter de rupture réseau.
La cadence exacte sur l’appareil de l’utilisateur n’a pas été mesurée ici.

## Correctif

Les vérifications restent actives. Le suivi vocal ne reconstruit les commandes
communes que lorsque leur état change. Les listes, messages, notifications et
projets inchangés conservent leurs éléments. Une connexion saine reste affichée
pendant une vérification en arrière-plan ; les erreurs et révocations restent
signalées. Le chat conserve sa position de lecture lors d’un rendu du même fil.
Un nom de conversation en cours de saisie reste intact. Les boutons conservés
retrouvent la version actuelle du fil au clic, sans capturer un ancien historique.

## Validation

- `test_refresh_stability.cjs --long`, puis `--android --long` : plus de 32 secondes
  et deux contrôles périodiques réels. Zéro remplacement des messages, de la liste
  ou de la navigation ; défilement 280 → 280 ; brouillon, sélection, focus et
  réflexion ouverte conservés. Documents et tâches inchangés conservent aussi
  leurs contrôles. Une modification réelle de tâche s’affiche correctement.
- Les sept suites UI partagées passent, avec tests de sélection de modèle adaptés
  au maintien du libellé pendant un contrôle normal. Les protections du sélecteur
  natif Android restent vérifiées.
- Parcours Android et conversation Low Android : succès. Dix-neuf tests Python
  de résilience réseau, mises à jour et préférences : succès.
- Contrôle des sources : 325 Python, 70 JavaScript, 93 PowerShell dans les deux
  moteurs. Contrôle UX : neuf avertissements préexistants de textes de console,
  aucun dans les sources modifiées pour ce correctif.
- Vérification Playwright MCP sur fixture locale : identité du message, défilement
  260 → 260, focus et brouillon conservés après contrôles et appel de rendu.
  Capture `stable-chat.png` ouverte et relue. Pas de refonte visuelle.
- Android Release : treize tests de livraison ; lint zéro erreur et cinq
  avertissements existants. Les clés de signature restent celles des versions
  précédentes. Aucun appareil physique n’a été utilisé.

## Livraison

Windows 3.5.43 et Android 1.0.16/code 17 sont construits depuis les mêmes sources.
Les preuves de diffusion sont `production.json` et `android-publication.json`.
Les distributions précédentes sont conservées dans le staging. La publication
Windows utilise la procédure existante avec sauvegarde chiffrée vérifiée,
préservation des profils, clés, données et processus Qwen. Les installations déjà
ouvertes ne sont pas forcées à redémarrer.

Les logs de compilation et de test sont dans `toolchain/refresh-*.log`,
`toolchain/client-3.5.43-*.log` et `toolchain/android-1.0.16-*.log`.
