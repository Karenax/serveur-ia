# Connexion affichée en rouge après rétablissement — Windows 3.5.60

La version **serveur/Windows 3.5.60** corrige le message rouge
« Connexion au serveur IA… » qui pouvait rester affiché alors que le catalogue
était accessible et que le client fonctionnait.

Une vérification concurrente pendant le démarrage peut renvoyer temporairement
le code `connecting`. Le chargement du catalogue affichait cette erreur, mais
son code ne figurait pas parmi ceux dont le bandeau était effacé au
rétablissement. Le chargement marque désormais son propre échec comme lié au
catalogue ; sa réussite suivante efface ce bandeau. Une erreur ultérieure de
sauvegarde reste indépendante et visible. Les accès révoqués restent signalés
en rouge jusqu’à une nouvelle vérification authentifiée réussie.

Le test navigateur `client-qwen/test_connection_banner.cjs` reproduit le message
temporaire, vérifie sa disparition après récupération du catalogue, la couleur
du voyant, la conservation d’une erreur d’enregistrement et le refus d’accès.
La première exécution sur l’ancien code échouait sur la persistance du bandeau ;
elle passe avec le correctif. La vérification ciblée porte sur Windows. Les
assets Android partagés sont régénérés, sans publier de nouvel APK.

## Validation et publication

- 104 tests Python du client et 19 suites UI réussis.
- Stabilité du rafraîchissement : navigation, sélection, brouillon, défilement
  et messages conservés lors des vérifications de fond.
- Syntaxe : 528 fichiers Python, 95 scripts JavaScript, 98 scripts PowerShell
  vérifiés avec chacun des deux interpréteurs.
- Contrôle UX réussi ; les cinq avertissements de textes longs de la console
  restent ceux des livraisons précédentes. Aucun texte UI n’est réécrit ici.
- Auto-tests natifs du binaire et des quatre EXE personnels, contenu de l’EXE
  comparé aux sources et pont WireGuard conservé.
- Sauvegarde chiffrée préalable vérifiée, avec copie NAS. La publication utilise
  la procédure existante et conserve les accès, clés, données, réglages,
  programmation des sauvegardes et processus Qwen chargés.

Les preuves sont dans `test-connection-banner.log`, `tests-client.log`,
`tests-ui.log`, `check-sources.log`, `frozen-validation.json`, `publication.json`
et `production.json`. Le manifeste est dans
`toolchain/releases-staging/windows-3.5.60/build-manifest.json` depuis la racine.
La version précédente et les informations de retour sont conservées.

Installer **3.5.60** par **Réglages → Mises à jour** pour remplacer le code du
client déjà ouvert. Les limites EG2 de 3.5.59 restent identiques : CPU à deux
threads, 32 textes maximum, seize demandes en attente et un calcul actif.
La limite de durée des longs lots reste décrite dans
[le guide EG2](../../lanceur/MEMOIRE-EG2.md).

Ne pas rejouer `publish.py prepare` ou `publish.py publish` sans examiner les
preuves existantes. `publish.py activate` permet uniquement de terminer un
redémarrage différé si une requête a repris pendant les auto-tests personnels.
