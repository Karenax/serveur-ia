# Absorption MiniPilot par Agent (2026-09-29, màj 2026-09-30)

## État actuel — 30 septembre 2026, Agent 0.3.0

Agent est le projet unique ; tous les modules hérités sont conservés. Le pont appelle les gestionnaires en processus, sans HTTP vers son propre pool. README_BACKEND et ADR-0007 décrivent l’exploitation actuelle ; aucune suppression de dossier externe n’est programmée.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

MiniPilot n'est plus un projet séparé : son code vit dans ce dépôt et son
serveur unique tourne sur le port **8001**. L'ancien dossier
`Documents/MiniPilot` est historique et extérieur au périmètre de ces corrections.

## Contenu absorbé

- `backend/` — routers ERP MiniPilot (`projects`, `cdc`, `scan`, `sage`,
  `workshop`, `meetings`, `ai`, `portfolio_tools`, `network_links`, `brain`),
  modèles + SQLite `MINIPILOT_HOME/minipilot.db` (données intactes).
  Ancien `backend/app/main.py` **supprimé** : `app/main.py` est l'unique
  entrypoint. Les règles de travail d'origine sont conservées dans
  `docs/minipilot-AGENTS.md`.
- `web/` — frontend React (sources + `dist/` buildé, `node_modules/` exclu :
  `cd web && pnpm install && pnpm build` pour reconstruire).
- `tests/test_minipilot.py`, `tests/test_minipilot_brain.py` (+ `conftest.py`
  d'isolation) — branchés sur l'app fusionnée.
- `start-agent.cmd` — lanceur unique.

## Serveur unique (`app/main.py`)

| Espace | Contenu |
|---|---|
| `/v1/*`, `/ui`, `/docs` | Project Brain (mails, validation, mémoire, IA) |
| `/api/v1/*` | MiniPilot ERP (projets, CDC, Sage, atelier…) + pont Brain |
| `/`, `/static`, `/assets` | UI React MiniPilot |
| `/health` | fusionné `{status, service: project-brain, app: minipilot}` |

Bases séparées, préservées : `./project_brain.db` (Brain) et
`~/.minipilot/minipilot.db` (MiniPilot). Le pont `brain.py` appelle Brain en
processus via les gestionnaires Brain ; MINIPILOT_BRAIN_URL ne concerne que le transport HTTP historique optionnel.

## Pont Brain (`backend/app/routers/brain.py`)

Lecture seule côté MiniPilot, aucune duplication de vérité :

- `GET /api/v1/brain/status` — joignabilité + URL Brain.
- `GET /api/v1/brain/projects` — projets Brain (rattachement).
- `GET /api/v1/brain/overview` — pilotage : IA, dossier mails, compteurs
  pending/propositions (clé API jamais exposée).
- `GET /api/v1/brain/proposals` — file de validation (lecture).
- `POST /api/v1/brain/scan` — scan global du dossier mails.
- `GET /api/v1/brain/ai-settings`, `PUT`, `POST /api/v1/brain/ai-test` —
  réglage IA (clé non réaffichée, non écrasée si vide).
- `GET/PUT /api/v1/brain/mail-settings` — dossier e-mails + scan au
  démarrage, avec le nombre de `.eml` détectés.
- `GET/PUT /api/v1/brain/memory-settings` — profil mémoire EG2,
  endpoint et modèle distants, chemin d’index SQLite et état de l’adaptateur.
- `GET/PUT/DELETE /api/v1/projects/{id}/brain` — mapping explicite
  (`BrainLink`, suggestion auto par code) ; 409 si non relié.
- `GET .../brain/knowledge|actions|risks|timeline`,
  `POST .../brain/scan` — lecture projet relié.

## UI : deux apps globales + onglets projet

Apps globales (fenêtres dédiées, ouvertes depuis le Dock / Launchpad /
menu Applications — `openModule` court-circuite sur elles) :

- **Connaissance** (`BrainApp`, icône `AppIcon.notes`) — vue tous projets :
  pilotage (IA, dossier, compteurs), scan, matrice des liens projet,
  file de validation. Onglet **Connaissance** conservé dans chaque fenêtre
  projet (lien, faits validés, actions, risques).
- **Réglages** (`SettingsApp`, icône `AppIcon.settings`) — **tout** le
  paramétrage, auparavant réparti entre le menu Réglages (côté Brain) et
  la fenêtre Connaissance. Accès :
  Dock/Launchpad/Applications ou menu **Aller → Réglages…**. Aucune
  duplication : la fenêtre Connaissance renvoie ici.

Icônes modules retirées du dock/Launchpad/menu (Pilotage, CDC & BE, Ventes,
Planification, Atelier) : elles n'ouvraient qu'une fenêtre projet et
restent accessibles en onglets. Épinglage par défaut : Connaissance.
`AppIcon.newdoc` reste réservé à Nouveau projet.

## Commandes

```powershell
pip install -r requirements.txt
python -m pytest tests/ -q   # + ruff check app backend/app tests
start-agent.cmd   # ou : python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Port **8002** (ancien Brain seul) : retiré.
Échec connu : `test_ai_status_and_unreachable` suppose aucun LLM local ;
un serveur répond sur `:11434` sur ce poste → échec environnemental,
antérieur à la fusion.
