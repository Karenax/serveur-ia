# Intégration extension Infomaniak ↔ Project Brain

## État actuel — 30 septembre 2026, Agent 0.3.0

Sources 0.2.0 courantes ; ZIP/XPI de Divers historiques. Packaging reproductible non signé et empreintes, tests purs Node ; Firefox avec compte Infomaniak et nouvelle signature restent à qualifier. Aucun transfert de mails à une IA externe n’est imposé par l’extension.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Contrat de nommage (indicatif)

L'extension écrit : `Infomaniak-IA/<AAAA-MM-JJ>-<sujet assaini ≤90c>-<hash16>.eml`

- `date` = date de téléchargement (`toISOString().slice(0,10)`), pas la date du mail.
- `sujet assaini` = NFKC, sans `\/:*?"<>|`, espaces condensés.
- `hash16` = 16 premiers hex du SHA-256 de `<mailbox>:<msg_id>`.

Ce nom n'est **jamais** une clé métier : doublons gérés par `conflictAction:
uniquify` côté Firefox et par `sha256` contenu côté backend.

## Garanties backend

- `parse_eml()` accepte les EML Infomaniak (multipart, pièces jointes listées
  en métadonnées, corps texte/HTML normalisé).
- Idempotence `sha256` : re-scan sans doublons (`duplicate`).
- Brut immuable : `storage/raw/<sha256>.eml`, `original_uri` + `origin_path`
  (chemin `Infomaniak-IA/...`) conservés en provenance.
- Résolution projet : `[CODE]`/alias dans sujet+corps (+ `ai_hint` si IA
  activée), sinon `resolution_pending` — jamais d'affectation arbitraire.
- Scan : auto au démarrage (`mail.folder`, `auto_scan`) + `POST
  /v1/ingest/scan` + import navigateur `POST /v1/sources/upload-eml-bulk`.

## Versions

| Artefact | Version | Usage |
|---|---|---|
| `Divers/extension firefox DL mail infomaniak.xpi` | 0.1.1 signée | install stable |
| `Divers/infomaniak-auto-local-0.1.1.zip` | 0.1.1 sources | référence |
| `Divers/infomaniak-auto-local-0.2.0.zip` | 0.2.0 sources | référence |
| `extensions/infomaniak-auto-local/` | 0.2.0 dézippé | dev / chargement temporaire |

## Évolutions possibles (non implémentées)

- Endpoint `POST /v1/sources/raw-eml` avec clé API locale pour envoi direct
  extension → backend (aujourd'hui : via dossier + scan).
- Extraction texte des pièces jointes PDF/Office (aujourd'hui : métadonnées
  nom/mime seulement).
- Watcher temps réel du dossier (aujourd'hui : scan au démarrage + manuel).
