# Moteur d'analyse CDC — repris de XPilot

## État actuel — 2 octobre 2026, Agent 0.4.0

Sorties finales : éléments confirmés, rejetés/remplacés exclus, contrôles bloquants refusés ; brouillon explicite marqué. Heures fractionnaires conservées ; calcul financier retiré, données historiques préservées. Page physique cohérente avec les preuves ; journal de revue ; imports bornés.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

Analyse d'un eCDC (cahier des charges) lié à un projet : extraction
document → IA → fonctions / contraintes / exigences / données / interfaces /
points ouverts, chacun **prouvé** par une citation du document source.

Code d'origine : `Documents/ChatGPT/Xpilot/backend/app/services/`
(`cdc_document_extraction.py`, `cdc_analysis_generation.py`, `cdc_checks.py`,
`domain/cdc_analysis.py`, `cdc_worker.py`). Aucun import de XPilot : port
fidèle des règles, branché sur la couche IA d'Agent (serveur local).

## Flux

```
upload CDC → stockage MINIPILOT_HOME/cdc/<projet>/<sha16>-<nom>
           → extraction page par page (cdc_source_pages)
           → batching de pages (2 par défaut)
           → LLM (JSON strict si le serveur l'accepte, sinon validé localement)
           → filtre citation mot-pour-mot  ← garde-fou central
           → CdcItem (FCT/CST/EXG/DAT/INT/QST-001) + CdcEvidenceAnchor
           → contrôles déterministes (CdcCheck)
```

## Formats acceptés

`.pdf` `.docx` `.xlsx/.xlsm` `.csv` `.txt` `.md` — 50 Mo max.
Extraction : PDF page par page, Word (texte barré marqué `[BARRE]`), Excel
(feuilles avec coordonnées de cellules, 200 000 cellules max), CSV/texte.
Qualité par page : `>=200` car. → 1.0, `>=30` → 0.5, sinon 0.2 ; sous 0.5 la
source passe en `review_required` (revue visuelle).

## Garde-fous conservés de XPilot

1. **Citation obligatoire** : un élément dont la citation n'apparaît pas mot
   pour mot dans la page source est rejeté (compteur `rejected`).
2. **Typage strict** : `kind`, `modality`, `priority` validés par Pydantic.
3. **Confiance normalisée** : « très haute » → 0.98, « 90 % » → 0.9, 0.5 → 0.5.
4. **Prompt durci** : documents non fiables, pas d'invention, une option /
   préférence / exemple ne devient jamais une exigence obligatoire ; les
   lacunes deviennent des `open_point`.
5. **Déduplication** (kind + wording normalisé) et identifiants humains
   `FCT-001`, `CST-001`, `EXG-001`, `DAT-001`, `INT-001`, `QST-001`.
6. **Contrôles déterministes** après génération : `ANALYSIS_EMPTY`,
   `EVIDENCE_MISSING`, `CONTRADICTION_OPEN`, `INACTIVE_SOURCE` (texte barré),
   `UNIT_MISSING`, `POSSIBLE_DUPLICATE`.
7. **Audit** : `CdcLlmRun` (modèle, empreinte de requête, durée, retournés /
   acceptés / rejetés, erreur).
8. **Idempotence** : un document au même SHA-256 n'est pas réenregistré ;
   rejouer une analyse ne duplique pas les éléments.

## Différences assumées

- L'appel LLM passe par `app/services/ai_client.py` (Ollama ou API
  OpenAI-compatible, réglage dans l'app Réglages) au lieu du client XPilot figé.
- `reasoning_effort: none` + `chat_template_kwargs.enable_thinking: false`
  sont envoyés comme chez XPilot : sans cela, un modèle à raisonnement épuise
  le budget en `reasoning_content` et renvoie un contenu vide.
- Le schéma JSON strict est tenté, puis abandonné si le serveur le refuse ou
  renvoie du vide ; la validation reste assurée par le schéma Pydantic.
- File SQLite durable et worker unique : progression par lots, annulation aux
  frontières de lots, reprise automatique après arrêt du serveur. Les erreurs et
  annulations nécessitent une reprise explicite ; les lots acquis restent conservés.

## API

| Route | Rôle |
|---|---|
| `POST /api/v1/projects/{id}/cdc/sources/upload` | upload + extraction (200/400/413) |
| `GET /api/v1/projects/{id}/cdc/sources` | sources (réf, révision, état, pages) |
| `GET /api/v1/projects/{id}/cdc/sources/{sid}/pages` | texte extrait par page |
| `POST /api/v1/projects/{id}/cdc/analyze` | compatibilité synchrone (409 IA, 400 source, 502 réponse) |
| `POST /api/v1/projects/{id}/cdc/jobs` | mise en file durable, HTTP 202 |
| `GET /api/v1/projects/{id}/cdc/jobs` | état et progression |
| `POST /api/v1/projects/{id}/cdc/jobs/{job}/cancel` ou `/retry` | annulation ou reprise |
| `GET /api/v1/projects/{id}/cdc/deliveries` | historique des transferts versionnés |
| `GET /api/v1/projects/{id}/cdc/items` | matrice + preuves + statuts |
| `GET /api/v1/projects/{id}/cdc/checks` | contrôles déterministes |
| `GET /api/v1/projects/{id}/cdc/runs` | traces d'appels IA |

## UI

Onglet **CDC & BE** → quatre sous-onglets :

- **Sources** : bouton **Analyser** par document prêt, avec le bilan
  (`créés / rejetés / durée`). L'upload accepte tous les formats CDC.
  Une source sans texte exploitable est signalée `analyzable: false` avec
  l'invite à ré-importer.
- **Revue** : validation élément par élément, mise en page 3 colonnes
  (équivalent XPilot `ProjectCdcAnalysisPanel`, styles `project-cdc-analysis.css`
  + `cdc-review.css`). Barre de progression segmentée par statut
  (`validés/total`, restants, affichés) ; pastilles de filtre par type et par
  statut **avec comptes** (type + statut actifs en un clic) ; recherche plein
  texte avec surlignage `<mark>`.
  - Colonne 1 : liste dense (id humain, titre, statut, priorité), case à cocher
    pour la validation en série, barre de sélection groupée.
  - Colonne 2 : preuves cliquables + texte de la page source avec la citation
    surlignée (résolu via `source_id`, plus de confusion preuve/page).
  - Colonne 3 : éditeur complet (titre, formulation, modalité, priorité,
    critère, unité, acceptation, responsable, heures, fourniture) + barre de
    décisions sticky avec raccourcis clavier.
  - Clavier : `j/k` naviguer, `c` confirmer, `t` à confirmer, `n` non fourni,
    `x` contradiction, `r` rejeter — la validation **avance automatiquement**
    à l'élément suivant. Mode **Compact** : éditeur sous les deux colonnes.
  - Cinq décisions : **Confirmer**, **À confirmer**, **Non fourni**,
    **Contradiction**, **Rejeter**. Sélection multiple + validation en série.
- **Synthèse** : matrice brute et saisie manuelle.
- **Contrôles** / **Transfert BE** : génération de versions finales ou brouillons ;
  consultation des versions précédentes sans écrasement, avec snapshot et SHA-256.

## API de revue

| Route | Rôle |
|---|---|
| `GET /api/v1/projects/{id}/cdc/review` | avancement : total, validés, restants, répartition |
| `PATCH /api/v1/projects/{id}/cdc/items/{item_id}` | statut + retouches ; rejoue les contrôles |
| `POST /api/v1/projects/{id}/cdc/items/bulk-status` | même statut pour plusieurs ids |

`knowledge_status` : `candidate` (généré, non revu), `confirmed`, `to_confirm`,
`not_provided`, `contradictory`, `rejected`, `superseded`. Toute modification
relance `run_deterministic_checks` : confirmer un élément sans preuve crée donc
un bloqueur `EVIDENCE_MISSING`, et un élément rejeté sort des contrôles actifs.

## Tests

`tests/test_operational_improvements.py` vérifie checkpoints, annulation, reprise,
versions immuables et portabilité des archives.

`tests/test_cdc_engine.py` — extraction, normalisation de confiance, nettoyage
`<think>`/```json, garde-fou citation (un élément fabriqué est rejeté),
pipeline complet, 409 sans IA, format refusé, contrôle `UNIT_MISSING`.

`scripts/cdc_live_check.py` — preuve réelle contre le serveur IA local
(gemma-4-26b) : 17 éléments extraits d'un CDC de démonstration en ~61 s, tous
adossés à leur citation.
