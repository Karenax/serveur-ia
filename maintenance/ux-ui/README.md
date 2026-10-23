# Qualité UX/UI permanente de Fred

Installation du 22 octobre 2026, portée du dépôt `D:\Serveur IA` et de ses
sous-dossiers. Les autres projets ne reçoivent pas automatiquement ces règles locales.
Playwright MCP est configuré au niveau utilisateur et peut servir aux autres projets.

## Fonctionnement courant

`AGENTS.md` charge les règles permanentes du dépôt. Les sept skills de
`.agents/skills/` sont découvrables automatiquement ; ne lire que ceux adaptés à la
tâche. Les cinq skills locaux complètent `frontend-design` d'Anthropic et
`web-design-guidelines` de Vercel, conservés sans modification. Le langage métier,
le design existant et la demande utilisateur priment sur les préférences esthétiques
amont. Les écrans API/admin gardent les paramètres techniques réellement utiles.

Le client utilise HTML/CSS/JavaScript sans framework UI, Segoe UI/system-ui et des
variables clair/sombre dans `client-qwen/ui.css`. Android réutilise ces sources via
`client-android/scripts/Prepare-Assets.py`, avec `mobile-ui/android.css`. La console
est dans `lanceur/web`. Les tests UI existants et Playwright 1.62.1 sont conservés.

Les petites corrections demandent des vérifications proportionnées. Sur « audit UX
complet », suivre `ux-visual-audit` : parcours accessibles, captures, clavier, états,
rapport P0–P3, propositions puis corrections demandées et nouvelles vérifications.
L'installation elle-même n'est pas une refonte ni un audit complet de Fred.

## Contrôle automatique léger

Depuis la racine :

```powershell
npm.cmd --prefix client-qwen run ux:check
npm.cmd --prefix client-qwen run ux:check:all
npm.cmd --prefix client-qwen test
```

La première commande examine les sources frontend modifiées, indexées et nouvelles.
La seconde examine toutes les sources du périmètre. `npm test` exécute les cinq suites
UI existantes puis le contrôle léger via `posttest`. Aucune dépendance applicative
supplémentaire. `run-check.cjs` choisit `PYTHON_EXE`, le Python du projet, puis Python
>= 3.10 dans le PATH ; en son absence, il signale explicitement le contrôle non fait.

Le script Python standard `maintenance/ux_check.py` produit des avertissements
fichier:ligne : textes techniques visibles, textes longs, terminologie configurable,
quelques problèmes statiques d'accessibilité, transitions CSS et blocs HTML identiques
à examiner. Il accepte des chemins explicites et `--json`. Exemple :

```powershell
node maintenance/ux-ui/run-check.cjs client-qwen/chat.html --json
```

Le périmètre et le seuil de longueur (180 caractères) sont dans `ux-check.json`.
Les fichiers ignorés par Git, tiers, tests et générés sont exclus. Les logs ne sont
pas considérés comme du texte UI ; les termes techniques de la console et des sections
API/diagnostic sont exemptés de cette seule règle. Leur accessibilité reste examinée.
Une exclusion locale `ux-ignore: raison explicite` sur la ligne ou la précédente
permet de documenter un faux positif. Ne pas en ajouter pour cacher un vrai défaut.

Ces contrôles sont heuristiques : ils ne résolvent pas toutes les interpolations JS,
les appels indirects, les composants React, les traductions ou les labels dynamiques.
La duplication repère seulement de grands blocs HTML identiques. Contrastes réels,
focus, clavier, reflow, nom accessible calculé et WCAG AA nécessitent le navigateur.
Les avertissements retournent 0, ne suppriment rien et ne bloquent pas la compilation.
Une erreur d'exécution du contrôle reste distincte d'une suspicion UX.

## Playwright MCP et validation après redémarrage

Configuration : `C:\Users\karen\.codex\config.toml`, section
`mcp_servers.playwright`. Serveur `@playwright/mcp` **0.0.83** installé et verrouillé
hors application dans `C:\Users\karen\.codex\tools\playwright-mcp`. Node absolu,
Chrome existant, `--headless --isolated` : aucun profil Chrome personnel réutilisé.
Les artefacts par défaut vont dans `C:\Users\karen\.codex\cache\ux-ui-playwright`.
Le package embarque Playwright `1.64.0-alpha-1790635538000` ; les tests du projet
continuent d'utiliser leur version distincte 1.62.1.

La configuration et les skills sont validés sur disque et via le moteur Codex.
Le processus de cette conversation ne peut pas ajouter à chaud de nouveaux outils
MCP à son catalogue. Redémarrer complètement Codex pour rendre les outils `playwright`
disponibles dans une nouvelle conversation. Les skills seront disponibles au prochain
tour/rechargement du catalogue ; le redémarrage recommandé couvre aussi ce point.

Validation déjà exécutée et rejouable :

```powershell
codex mcp get playwright --json
node maintenance/ux-ui/discover_skills.cjs
node maintenance/ux-ui/playwright_smoke.cjs
```

Le premier confirme la déclaration active. Le deuxième appelle l'API réelle
`skills/list` du moteur Codex, sans lancer une tâche ou un modèle. Le troisième lit
la déclaration enregistrée, initialise ce même serveur en stdio, liste ses outils,
ouvre une fixture locale jetable, saisit un nom, teste Tab et le clic, vérifie le
succès, prend des captures 1440×900 et 390×844, puis ferme ses propres processus.
Il utilise le Python du projet ou `PYTHON_EXE` pour lire le TOML.

Après redémarrage, dans une nouvelle conversation de ce dépôt, demander :
« Utilise Playwright MCP pour ouvrir une fixture locale de test, vérifier le clavier
et prendre une capture. Vérifie aussi que frontend-human-centered est disponible. »
Ce test validera l'exposition dans l'interface Codex ; le test de transport/browser
est déjà réussi. Aucun test de production ni appareil Android physique n'est impliqué.

## Sauvegarde et traçabilité

Sauvegarde avant modification :
`C:\Users\karen\.codex\backups\ux-ui-20261022-101036\` contient l'ancien
`config.toml` et `client-qwen-package.json`. Aucune authentification copiée dans le
dépôt. Les configurations antérieures ont été comparées structurellement : seule
la section MCP a été ajoutée ; les autres valeurs sont conservées.

`AGENTS.md` n'existait ni à la racine du projet ni dans les emplacements parents
inspectés : il a été créé. Les instructions et skills système/plugins existants
restent en place. Pas de changement de modèle, permissions, plugins ou outillage UI.

Sources et révisions exactes dans `installation.json`. L'installation officielle
des deux skills utilise le helper `skill-installer` de Codex avec `--dest .agents/skills`
et des commits figés ; aucun renommage ni copie personnalisée du skill Vercel.
Le dossier Anthropic et sa licence Apache 2.0 ont été examinés avant téléchargement ;
`LICENSE.txt` est conservé. Mettre à jour ces ressources explicitement et refaire
la validation, plutôt que modifier leur contenu amont sur place.

Sources consultées : [guidance frontend OpenAI](https://developers.openai.com/api/docs/guides/frontend-prompt),
[skills Codex](https://learn.chatgpt.com/docs/build-skills),
[MCP Codex](https://learn.chatgpt.com/docs/extend/mcp?surface=cli),
[Vercel](https://github.com/vercel-labs/agent-skills),
[Anthropic](https://github.com/anthropics/skills/tree/main/skills/frontend-design),
[Playwright MCP](https://github.com/microsoft/playwright-mcp) et
[WCAG 2.2](https://www.w3.org/TR/WCAG22/).

Résultats et limites : `validation/RESULTATS.md`. Les captures utilisent uniquement
des fixtures de test. Les neuf avertissements de texte long conservés dans
`validation/ux-report.json` sont des pistes de relecture, pas neuf défauts confirmés.
