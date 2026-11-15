# Qualité UX/UI permanente de Codex

Configuration du 22 octobre 2026, pour les prochaines interventions dans ce dépôt.
Cette installation ne refond aucun écran et ne change ni serveur applicatif,
ni base, ni bundle servi. Agent conserve son architecture FastAPI + React sur
8001; XPilot externe 8000 n'est pas utilisé.

## Environnement observé

- Codex Desktop Windows : package `OpenAI.Codex_26.1016.6573.0_x64`; moteur embarqué
  `codex-cli 0.163.0-alpha.11` (le numéro Electron du binaire n'est pas celui de l'app).
- Configuration utilisateur : `%USERPROFILE%\.codex\config.toml`;
  instructions personnelles existantes : `%USERPROFILE%\.codex\AGENTS.md`, conservées.
- Projet approuvé `C:\Agent`, instructions `AGENTS.md`, skills `.agents/skills/`.
- Node `22.23.1`, npm/npx `10.9.8`, pnpm déclaré `11.18.0`;
  React 19, TypeScript 5, Vite 7, Vitest 5, Testing Library.
- Edge déjà installé. Aucun téléchargement de navigateur, nouvelle bibliothèque
  graphique ou dépendance applicative. MCP est installé dans le cache npm utilisateur.
- Design existant : `web/src/styles.css` (tokens, DM Sans, contrôles),
  `themes.css`, `components/ui.tsx`, `WorkspaceShell.tsx` et CSS des domaines.

## Skills et déclenchement

| Skill | Usage |
|---|---|
| `frontend-human-centered` | Toute création/modification d'interface, avec contexte métier |
| `ux-writing-cleaner` | Textes visibles créés/modifiés; tri essentiel, long, technique, redondant |
| `professional-ui-design` | Composition, composants, responsive et accessibilité d'un changement significatif |
| `ux-visual-audit` | Nouvelle page, refonte, modification importante ou audit complet demandé |
| `ux-consistency-review` | Changements transversaux et cohérence entre écrans |
| `web-design-guidelines` | Audit de bonnes pratiques, clavier, formulaires, lisibilité, accessibilité |
| `frontend-design` | Ressource officielle de composition et finition, adaptée au logiciel métier |

Les sept dossiers sont dans `.agents/skills/`, sans doublon utilisateur.
La détection et l'invocation implicite sont permises; `AGENTS.md` impose une
sélection proportionnée, sans charger tous les skills à chaque conversation.
Les skills sont utilisables explicitement par `$nom-du-skill`.

Les recommandations externes ne remplacent pas les besoins métier ni le design
existant : aucune landing page, nouvelle police, décoration ou suppression
fonctionnelle automatique. Les modules et validations humaines restent protégés.

## Sources officielles et provenance

- [OpenAI Frontend Guidance](https://developers.openai.com/api/docs/guides/frontend-prompt) :
  principes adaptés et synthétisés dans `frontend-human-centered`.
- [Découverte des skills Codex](https://learn.chatgpt.com/docs/build-skills) :
  dossiers projet `.agents/skills`, nom/description YAML, chargement progressif.
- [Vercel agent-skills](https://github.com/vercel-labs/agent-skills/tree/063bee94c3f4df8453406c830b0a7df0f2860278/skills/web-design-guidelines) :
  installé sans modification, commit `063bee94c3f4df8453406c830b0a7df0f2860278`.
  Le skill récupère les règles actuelles de `vercel-labs/web-interface-guidelines`
  à chaque revue; si le réseau manque, déclarer cette limite.
  Aucun fichier LICENSE n'était présent à la racine de ce dépôt à ce commit.
- [Anthropic frontend-design](https://github.com/anthropics/skills/tree/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/frontend-design) :
  installé sans modification, commit `dbd4588f9e1033efb41dad4bef2f7947c8993d44`;
  `LICENSE.txt` Apache 2.0 inspecté avant installation et conservé à côté du skill.
- [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) : package
  `@playwright/mcp@0.0.83`, licence Apache 2.0; serveur testé
  `Playwright 1.64.0-alpha-1790635538000`.
- [Configuration MCP partagée par les clients Codex](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

Les deux skills tiers sont installés avec le script officiel `skill-installer`,
avec `--ref` figé et `--dest C:\Agent\.agents\skills`, plutôt qu'une seconde
copie ou un renommage. Les deux `SKILL.md` tiers et la licence Anthropic ont été
comparés octet par octet aux sources figées : identiques. Preuve locale :
`logs/ux-quality/upstream-verification.json`.
Toute mise à jour est explicite et revérifiée.

## Playwright MCP

Le serveur utilisateur `playwright` est activé en transport stdio. Il lance le
Node existant et son `npx-cli.js`, avec les arguments :

```text
-y @playwright/mcp@0.0.83 --browser msedge --isolated --headless
```

Les chemins absolus vers Node/npx évitent les problèmes de résolution `.cmd`
sous Windows. Un changement de runtime Node nécessite d'actualiser ces chemins.
Le profil est isolé et les captures restent possibles en mode sans fenêtre.
Le serveur MCP `node_repl` et tous les autres réglages sont préservés.
La configuration globale n'est pas copiée dans Git (chemins et paramètres privés).

Validation locale reproductible, depuis la racine :

```powershell
codex mcp get playwright
node scripts/ux-mcp-smoke.mjs
# Option : consultation seule de l'accueil réel, sans interaction métier
node scripts/ux-mcp-smoke.mjs --app http://127.0.0.1:8001/app
```

Le script utilise réellement le protocole MCP du serveur déclaré, découvre ses
outils, ouvre une fixture locale fictive, remplit le formulaire, vérifie le focus
par Tab, valide avec Entrée et contrôle le message de succès. L'option `--app`
ouvre ensuite Agent sans remplir ni cliquer sur ses contrôles et capture les
viewports 1440×900 et 390×844. Il ferme le navigateur et la fixture.
Rapports, snapshots et images : `logs/ux-quality/` (hors Git).
Les images peuvent contenir des informations métier : ne pas les publier par défaut.

**Redémarrer Codex après cette installation pour charger le nouveau serveur MCP
dans une conversation.** Le test externe ne prouve pas sa présence dans le
catalogue d'outils de la conversation déjà ouverte. Après redémarrage, demander
« utilise Playwright MCP pour ouvrir l'accueil Agent en lecture seule et prendre
une capture »; vérifier l'appel réel aux outils `playwright`. Les skills devraient
apparaître au tour suivant; redémarrer également s'ils n'apparaissent pas.

## Contrôle automatique léger

```powershell
npm --prefix web run ux:check
# Depuis la racine : périmètre ciblé et sortie machine
npm --prefix web run ux:check -- web/src/components/ui.tsx
node scripts/ux-quality-check.mjs --json
npm --prefix web run ux:test
```

Le contrôleur utilise l'AST TypeScript déjà installé. Il examine texte JSX,
attributs visibles et objets de libellés, repère jargon/diagnostics, textes longs,
terminologie historique, contrôles sans nom accessible repéré, clics non natifs
sans clavier, images sans alt et vues JSX longues identiques entre fichiers.
Chaque avertissement fournit fichier:ligne et catégorie; aucune modification
automatique et sortie 0 pour de simples suspicions. Les erreurs d'exécution
(dépendance ou chemin absent) restent visibles avec une sortie non nulle.

Exclusions : tests, stories, fixtures, fichiers générés, dist, node_modules,
dossiers admin/diagnostic, fonctions explicitement de diagnostic et blocs marqués
`data-ux-scope="diagnostic"`. Une exception revue s'écrit dans un commentaire
`ux-ignore: raison métier précise` sur la ligne ou juste au-dessus du constat.
Ne pas ajouter d'exclusion pour masquer une erreur utilisateur importante.

Limites : ce contrôle ne suit pas tous les flux de données, traductions et
composants personnalisés; il ne mesure pas les contrastes, performances ou focus
réels et ne remplace pas un audit WCAG 2.2 AA. Les composants dupliqués ne sont
repérés que pour du JSX identique suffisamment long. Une référence métier n'est
pas un identifiant de debug. Relire les résultats avant de proposer une correction.
La CI existante exécute `ux:test` puis `ux:check` après installation frontend;
les tests et le build existants sont conservés.

## Deux modes

**Normal** : appliquer les skills pertinents au changement, vérifier le parcours
touché et ses états, sans audit complet pour les petites corrections sans impact
visuel. La vérification est proportionnée.

**« audit UX complet »** : parcourir les écrans accessibles du périmètre, inspecter
snapshots et images, vérifier formulaires, menus, clavier, chargement/vide/erreur
sur données fictives; fournir gravité, impact, preuve et proposition. Appliquer
les corrections demandées et répéter les tests. P0 = blocage critique/perte de
données; P1 = ergonomie/accessibilité importante; P2 = texte/cohérence/hiérarchie;
P3 = finition. Aucun audit seul n'autorise une refonte ou une suppression.

## Validation effectivement réalisée

- Sept skills valides avec `skill-creator/scripts/quick_validate.py`.
- Découverte réelle par `codex app-server`, appel `skills/list` : les sept skills
  sont activés avec portée `repo`, sans erreur. Preuve locale
  `logs/ux-quality/codex-skills-discovery.json`.
- Tests du contrôleur : six cas initiaux réussis après correction d'une exception
  sans motif; les tests sont rejoués après toute évolution du contrôleur.
- Contrôle du frontend : 77 avertissements initiaux à relire, non corrigés
  automatiquement; `components/ui.tsx` ne déclenche aucun avertissement statique.
- Test d'usage `ux-writing-cleaner` : libellés réels de `components/ui.tsx`
  relus; « Chargement des données », « Impossible de charger cette vue » et
  « Réessayer » conservés pour leur rôle; l'expression dynamique `message`
  nécessite le contexte de son producteur avant tout changement. Rapport local
  `logs/ux-quality/skill-usage.md`. Aucune modification du produit.
- MCP : 25 outils découverts; 16 appels réussis, dont formulaire fictif au clavier,
  lecture Agent et captures desktop/mobile. Rapport
  `logs/ux-quality/2026-10-22T08-16-42-417Z-mcp-report.json`.
- Captures réellement inspectées. À 390 px, la navigation existante chevauche le
  contenu et apparaît tronquée; constat P1 si usage mobile requis, à confirmer
  sur le parcours mobile complet lors d'un audit demandé. Aucun correctif UI
  dans cette mission. La capture desktop a été prise pendant des chargements :
  elle ne qualifie pas tous les états ni tous les écrans.
- Ruff `app backend/app tests` réussi. Aucun résultat de suite Python globale,
  de conformité WCAG intégrale ou d'audit complet du produit n'est déduit.
- TypeScript `--noEmit` réussi; test frontend existant
  `MeetingQuestionProgress.test.tsx` : 12 tests réussis. Le bundle servi n'a pas
  été reconstruit. La résolution des chemins du contrôleur a aussi été vérifiée
  avec `npm --prefix web`, qui change le répertoire de travail.

## Sauvegardes et partage

Configuration privée avant modification :
`%USERPROFILE%\.codex\config.toml.ux-before-20261022-100954.bak`.
Les fichiers projet concernés avant modification et leurs SHA256 sont dans
`backups/ux-quality-20261022/project-before/`; les références des sources tierces
sont dans `backups/ux-quality-20261022/`. Sauvegardes privées hors Git.

À versionner avec le projet : `AGENTS.md`, `.agents/skills/`, les trois scripts UX,
`web/package.json`, `.github/workflows/verify.yml`, cette documentation,
`docs/24_UI_UX_REDESIGN.md`, les deux README et `manifest.json`.
Les douze nouveaux fichiers de cette installation sont ajoutés à l'index Git;
les fichiers déjà suivis conservent leurs modifications en cours, sans ajout
global à l'index. Aucun commit ni push effectué par cette installation. Les changements antérieurs
du dépôt restent à part et ne sont ni réinitialisés ni publiés.
