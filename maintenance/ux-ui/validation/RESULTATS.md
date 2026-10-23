# Résultats de l'installation UX/UI — 22 octobre 2026

Configuration permanente terminée pour le dépôt Fred. Aucune refonte de l'application
et aucune dépendance applicative ajoutée. Les modifications préexistantes ont été
laissées en place. Redémarrage complet de Codex recommandé pour exposer le nouveau
MCP dans les conversations ; la déclaration et le serveur sont déjà fonctionnels.

## Environnement constaté

- Codex Desktop sous Windows, CLI embarquée `0.163.0-alpha.11`. Version Desktop
  déclarée dans la configuration du runtime : `26.1016.51333` ; chemin du package
  Windows déclaré : `OpenAI.Codex_26.1016.6573.0_x64__2p2nqsd0c76g0`.
- Configuration utilisateur `C:\Users\karen\.codex\config.toml`. Pas de
  `AGENTS.md`, `.agents/skills` ou configuration projet préexistants détectés.
  Skills système et plugins présents et préservés. MCP préexistants node_repl
  actif et cua_repl désactivé conservés.
- Node `22.23.2`, npm/npx `10.9.8`, Chrome installé. L'alias `python` du PATH
  renvoie au Microsoft Store ; utilisation du Python 3.12.14 déjà présent dans
  `toolchain/eg2-python/Scripts/python.exe`, avec YAML et TOML disponibles.
- HTML/CSS/JavaScript partagé Windows/Android, WebView Android natif, console web,
  thèmes clair/sombre, Segoe UI/system-ui et variables CSS existantes.
- Playwright projet `1.62.1`, cinq suites UI et vérificateur de sources existants.
  Absence des sept skills demandés et de Playwright MCP avant l'installation.

## Ressources installées

| Outil / skill | Statut | Emplacement | Déclenchement | Limite / problème |
| --- | --- | --- | --- | --- |
| frontend-human-centered | Configuré, validé, détecté actif | `.agents/skills/frontend-human-centered` | Interface nouvelle/parcours modifié | Aucun |
| ux-writing-cleaner | Configuré, validé, détecté, exercé | `.agents/skills/ux-writing-cleaner` | Texte visible créé/modifié | Exercice manuel, pas un test statistique de sélection |
| professional-ui-design | Configuré, validé, détecté actif | `.agents/skills/professional-ui-design` | Changement significatif du design | Vérification navigateur requise pour AA |
| ux-visual-audit | Configuré, validé, détecté actif | `.agents/skills/ux-visual-audit` | Page/refonte importante ou audit UX complet | Aucun audit exhaustif de l'application pendant l'installation |
| ux-consistency-review | Configuré, validé, détecté actif | `.agents/skills/ux-consistency-review` | Cohérence/changement transversal | Aucun |
| web-design-guidelines officiel | Installé, validé, détecté actif | `.agents/skills/web-design-guidelines` | Audit bonnes pratiques | Recharge ses recommandations amont à chaque audit |
| frontend-design officiel | Installé, licence examinée et conservée, validé, détecté actif | `.agents/skills/frontend-design` | Composition/refonte via professional-ui-design | Adapter les préférences marketing au métier et à l'existant |
| Playwright MCP 0.0.83 | Installé, déclaré actif, navigateur testé | `%USERPROFILE%/.codex/tools/playwright-mcp` et `config.toml` | Audit visuel | Redémarrer Codex pour exposition dans son catalogue d'outils |
| Contrôle UX léger | Configuré et testé | `maintenance/ux_check.py` et `maintenance/ux-ui/` | `npm test` posttest, `npm run ux:check` ou `ux:check:all` | Heuristique, avertissements non bloquants |
| Règles persistantes | Configurées | `AGENTS.md` | Toute tâche dans ce dépôt | Portée projet, pas les autres dépôts |

Les conventions métier locales préviennent les conflits avec la typographie, les
compositions marketing et les règles de casse anglaise proposées par les sources
amont. Aucun nouveau framework, serveur applicatif, hook Git ou pipeline CI ajouté.

## Fichiers créés et modifiés

Créés :

- `AGENTS.md` ; cinq `SKILL.md` personnalisés sous `.agents/skills/`.
- Deux skills officiels sous `.agents/skills/`, avec `frontend-design/LICENSE.txt`.
- `maintenance/ux_check.py` ; `maintenance/test_ux_check.py`.
- `maintenance/ux-ui/ux-check.json`, `run-check.cjs`, `playwright_smoke.cjs`,
  `discover_skills.cjs`, `README.md`, `installation.json`.
- `maintenance/ux-ui/validation/` : présent rapport, exercice du skill, rapport
  heuristique, résultat de découverte du moteur Codex, résultat et transcript MCP,
  schémas d'outils découverts, captures de la fixture MCP et des tests UI existants.
- Hors dépôt : installation npm isolée et verrouillée sous
  `C:\Users\karen\.codex\tools\playwright-mcp` ; sauvegarde sous
  `C:\Users\karen\.codex\backups\ux-ui-20261022-101036`.

Modifiés :

- `client-qwen/package.json` : commandes UX et hook `posttest` uniquement.
- `C:\Users\karen\.codex\config.toml` : ajout du serveur Playwright.

Les fichiers projet nécessaires sont ajoutés à l'index Git, sans commit. Les
changements préexistants ne sont ni indexés ni inclus dans cette installation.

## Tests effectivement exécutés

| Test | Résultat / preuve |
| --- | --- |
| `quick_validate.py` du skill-creator sur les sept skills | 7/7 valides |
| `node maintenance/ux-ui/discover_skills.cjs` | API réelle Codex `skills/list`, 7/7 skills de portée repo actifs, aucune erreur ; `skills-discovery.json` |
| `codex mcp get playwright --json` | Déclaration active avec chemins absolus, Chrome isolé headless |
| `node maintenance/ux-ui/playwright_smoke.cjs` | Initialisation stdio réelle et 25 outils ; saisie, Tab/focus, clic, succès, captures 1440×900 et 390×844, absence de débordement horizontal sur la fixture ; `mcp/result.json` |
| `npm.cmd --prefix client-qwen test` | 5 suites UI existantes réussies, puis posttest UX réussi : conversation, correcteur, Hermes, sélecteur de modèle et réflexion, transports/données simulés Windows/Android |
| `python -X utf8 -m unittest maintenance.test_ux_check -v` avec le Python du projet | 8/8 tests réussis : textes visibles vs logs, diagnostics, accessibilité, exclusions, suppressions motivées, non-modification, duplication, lignes HTML/JS, UTF-16 et découverte Git |
| Contrôle complet `node maintenance/ux-ui/run-check.cjs --json` | 46 fichiers analysés, 9 avertissements de texte long, sortie 0 ; `ux-report.json` |
| Contrôle des modifications `npm.cmd --prefix client-qwen run ux:check` | 1 fichier UI préexistant modifié examiné, aucun avertissement |
| Syntaxe Node des trois scripts `.cjs` et Python des nouveaux scripts | Réussie |
| Comparaison TOML avant/après et package JSON avant/après | Valeurs Codex préexistantes conservées, dépendances applicatives identiques |
| Exercice `ux-writing-cleaner` | Quatre classes appliquées, texte de migration réel conservé ; `skill-exercise.md` |
| Examen des captures | Capture mobile de la fixture MCP et écran Android du sélecteur réellement ouverts et lus ; aucune conclusion d'audit complet |
| Contrôle Git | Fichiers nécessaires non ignorés, ajout ciblé à l'index, contrôle des espaces |

La commande `python` abrégée dans ce tableau désigne
`D:\Serveur IA\toolchain\eg2-python\Scripts\python.exe`.
Les premiers essais du nouveau scanner ont permis de corriger un décalage de lignes,
une exemption de diagnostic trop large et un parcours incluant les fichiers générés.
Le test MCP a été adapté aux schémas réellement découverts : `target`, captures avec
`scale` et snapshots sous forme de fichiers. Les résultats ci-dessus sont ceux après
correction, pas ceux des premiers essais.

## Reste à faire

Redémarrer Codex puis utiliser le test guidé de `README.md` dans une nouvelle
conversation pour valider l'exposition des outils dans le catalogue de l'application.
Le transport MCP et le navigateur sont déjà testés ; seule cette exposition après
rechargement n'est pas vérifiable à chaud depuis la conversation actuelle.

Les neuf textes longs sont des suggestions de relecture : aucune suppression ni
refonte n'est effectuée. Un audit complet, une vérification WCAG intégrale, un test
sur téléphone physique et une validation de production restent hors du périmètre
de cette installation.
