# Ajout de modèles dans OpenCode 2

Le signalement client est : fournisseur « Serveur Fred » présent, ajout confirmé,
mais aucun modèle proposé après le passage d’OpenCode 1 à OpenCode 2.

Deux défauts ont été reproduits :

- OpenCode 2 transforme la date absente d’un modèle personnalisé en `1970-01-01`.
  Le sélecteur masque alors ce modèle par défaut. L’écriture du fournisseur et du
  modèle dans la configuration ne suffit donc pas à le rendre visible.
- Lorsque `opencode.json` et `opencode.jsonc` coexistent, Fred modifiait le premier.
  OpenCode donne pourtant priorité au second ; une ancienne adresse ou clé pouvait
  rester effective malgré la confirmation d’ajout.

Fred choisit maintenant le JSONC prioritaire et active uniquement le modèle ajouté
dans les préférences du sélecteur OpenCode Desktop 2. Les autres modèles, favoris,
modèles récents, variantes et brouillons sont conservés. Une copie exacte de la
configuration et une sauvegarde de la préférence modifiée sont accessibles dans
le résultat de l’ajout. Les bases existantes ne sont ni créées ni migrées par Fred.
Avant le premier lancement d’OpenCode, le format de préférences antérieur pris en
charge par son importeur prépare cette activation.

Si OpenCode est ouvert, Fred enregistre sa configuration puis demande de fermer
complètement OpenCode et de refaire l’ajout. Il ne modifie pas une préférence
encore en cache dans l’application. Si le magasin est inconnu ou illisible, la
confirmation indique l’action manuelle restante dans **Paramètres > Modèles**.

Sur le PC client : mettre Fred à jour en **3.5.29**, fermer OpenCode, cliquer sur
**Ajouter à OpenCode 2**, puis rouvrir OpenCode et sélectionner le modèle sous
**Serveur Fred** dans `/models`. Garder Fred ouvert pendant son utilisation.

## Vérifications

- 18 tests de configuration et de préférences, dont sauvegardes exactes,
  idempotence, conservation des autres lignes SQLite/brouillons, application
  ouverte et préférences invalides ; 10 tests d’authentification et de mise à jour.
- Cinq suites de l’interface commune Windows/Android. L’interface Android générée
  reste identique ; son APK 1.0.11/code 12 n’est pas reconstruit pour ce correctif.
- OpenCode **2.0.22** installé et **2.0.29** officiel téléchargé dans `toolchain`
  depuis le paquet npm `@opencode/cli-windows-x64`, intégrité SHA-512 vérifiée.
  Configurations, préférences, API et données OpenCode temporaires.
- Ancien EXE 3.5.28 : erreur de priorité reproduite. Nouvel EXE : configuration,
  visibilité, adresse et clé effectives, puis une requête OpenCode réussie sur une
  API synthétique authentifiée. La règle de visibilité exécutée est celle du
  sélecteur officiel ; ces tests ne pilotent pas le poste client distant.
- Autotest de l’EXE, ressources embarquées, signature de livraison et préservation
  des processus Qwen, clés, données et programmation des sauvegardes à la publication.

Preuves : `verification-2.0.22.json`, `verification-2.0.29.json`, `artifact.json`,
`production-corrections.json`. Reconstruction et publication : scripts dans ce dossier,
manifeste dans `client-qwen/dist/build-manifest.json` et précédente distribution sous
`toolchain/releases-staging/opencode-20261014/previous` (hors Git).

Références primaires : [filtre du sélecteur](https://github.com/anomalyco/opencode/blob/dev/packages/app/src/providers/models/models.tsx),
[conversion du catalogue](https://github.com/anomalyco/opencode/blob/dev/packages/app/src/runtime/server/global-sync/utils.ts),
[préférences Desktop](https://github.com/anomalyco/opencode/blob/dev/packages/desktop/src/main/storage/state.ts),
[configuration prioritaire](https://github.com/anomalyco/opencode/blob/dev/packages/core/src/config.ts),
[documentation des modèles](https://dev.opencode.ai/v2/docs/models/).
