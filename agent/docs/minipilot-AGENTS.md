# AGENTS.md — règles de travail sur MiniPilot

> Archive des règles MiniPilot avant absorption. Les instructions actives sont
> celles de AGENTS.md à la racine. Commandes actuelles : README_BACKEND.md.
> L’ancien entrypoint backend.app.main et l’installation éditable ci-dessous
> ne sont plus les commandes de ce dépôt mono-serveur.

## 1. Objectif et périmètre

Mini ERP local (dérivé simplifié de XPilot), sans login : pilotage projets industriels.
Backend FastAPI + SQLite local (`MINIPILOT_HOME/minipilot.db`), frontend React+Vite servi via `web/dist`.
Ne jamais transformer en multi-utilisateur, auth, ou base serveur sans demande explicite.

## 2. Commandes de référence

- Lancement API : `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001`
- Tests : `python -m pytest -q` (testpaths = `tests`)
- Frontend dev : `cd web; pnpm dev` (port 5174) ; build : `cd web; pnpm build` (`tsc -b && vite build`)
- Install : `python -m pip install -e ".[dev]"` ; lint Python : `ruff` si disponible

Vérifier une correction par exécution : lancer les tests concernés, et si frontend touché, `pnpm build`.

## 3. Architecture à respecter

- `backend/app/main.py` : assemblage routers uniquement, pas de logique métier.
- `backend/app/db.py` : `init_db()` + `_backup()` + migrations légères `PRAGMA table_info` + `ALTER TABLE`. Pas d'Alembic. Toujours ajouter une migration légère si nouveau champ modèle.
- `backend/app/models.py` : modèles SQLAlchemy seuls. Champs projet sensibles : `hourly_rate` (défaut 85), `margin_pct` (défaut 10), `client_name`, `offer_number`, `tdao_prix_vente`, `tdao_budget_h`.
- Routers : `projects` (CRUD + portfolio + planning + tâches/jalons/livrables), `cdc` (PDF + matrice + offre + transfert), `scan` (TDAO/TDSP), `sage` + `workshop` (achats/pointage/BOM), `meetings` (CR → tâches), `ai` (Ollama), `portfolio_tools` (search avec `project_id` optionnel/export/import), `network_links` (GET/PUT + `POST /open-path` ouverture OS).
- Frontend : `web/src/App.tsx` (bureau façon macOS : app Projets en liste avec jalon/échéance, fenêtres projet `CODE — Titre`, dock, Spotlight), `web/src/os/icons.tsx` (icônes maison), `web/src/lib/api.ts` (client `/api/v1`). Les `*.js` à côté des `*.tsx/*.ts` sont des artefacts, éditer uniquement les sources TS/TSX.
- Ne pas committer `node_modules/`, `__pycache__/`, `.pytest_cache/`, `web/dist/` sauf demande.

## 4. Garde-fous métier (bloquants)

- CDC : `kind` strict (`function|constraint|requirement|data|interface|open_point`), `modality` stricte, `source_quote` non vide. `POST /cdc/transfer` : 400 si matrice vide ou citation vide. Message transfert contient `NC - A CHIFFRER PAR LE BE`.
- Offre : `total_ht = (Σ h×taux + fournitures) × (1+marge/100)`. 400 si matrice vide.
- Liens réseau : code unique par projet (409 si doublon), liens obligatoires jamais supprimés (400 si manquant).
- Scan TDAO/TDSP : profondeur max 3, extensions `.xlsm/.xlsx/.xls`, marqueur `J135 == TOTAL HEURES PREVUES`, prix `N123`. Ignorer placeholders (`-`, `XXXX`, `A remplir…`) via `_is_real`/`_clean_identity`. Import 409 si code existe, `budgets-from-tdao` idempotent (400 si déjà chargé).
- Sage : CSV séparateur `;`, encodage `utf-8-sig` puis `cp1252`, dernier fichier par dossier requis (`Achats`, `Pointages` uniquement — `SageBudget`/`SageVente` conservés en base pour compatibilité). Rattachement affaire par égalité ou inclusion. Erreurs : 400 config manquante, 422 dossier/fichier inaccessible.
- IA : texte 50–60000 caractères, citation mot-pour-mot obligatoire dans le texte source sinon `rejected++`. 409 si LLM injoignable, 502 si JSON inexploitable. Ne jamais inventer de données, ne jamais promouvoir option/préférence/exemple en obligatoire.
- Recherche : `q` min 2 caractères (400 sinon), `project_id` optionnel pour restreindre au projet (jamais de hit `project` dans ce cas, 404 si projet inconnu). Export format `minipilot-export` v1, import 409 si code existe, 400 si format inconnu.
- Tâches/jalons : `done`/`cancelled` exclus des retards. Dates en `YYYY-MM-DD` string.

## 5. Données et sécurité locale

- Ne jamais toucher la vraie base `~/.minipilot/minipilot.db` : les tests utilisent `tests/conftest.py` (`MINIPILOT_HOME` temp). Ne pas modifier `conftest.py` pour pointer vers la vraie base.
- Uploads PDF : 50 Mo max, détection scanné (`<20` caractères/page → `review_required`).
- Chemins réseau UNC (`\\serveur\…`, `V:\…`) : les traiter comme chaînes opaques, ne jamais les normaliser en chemins POSIX.
- Exports Markdown écrits sous `MINIPILOT_HOME/exports` : `offre-{code}.md`, `transfert-be-{code}.md`.

## 6. Conventions de code

- Backend : Python 3.11+, `from __future__ import annotations`, Pydantic v2 pour payloads, HTTPException avec messages FR explicites, tests FastAPI `TestClient`.
- Frontend : TypeScript strict, composants fonctionnels, `api.ts` seule couche d'accès (`BASE = /api/v1`), messages FR, tableaux `data-table compact`, badges par statut.
- Préférer éditer les fichiers existants, changements minimaux, pas de refacto opportuniste. Vérifier `pyproject.toml` avant toute nouvelle dépendance.

## 7. Workflow agent

1. Lire `README.md`, le router concerné, et `tests/test_minipilot.py` avant d'éditer.
2. Reproduire par test ou appel API avant de corriger.
3. Éditer backend + frontend + tests ensemble si le contrat API change.
4. Exécuter `python -m pytest -q` et `cd web; pnpm build` si frontend touché.
5. Ne commit/push que sur demande explicite.
