# Extension Firefox — Infomaniak Auto Local

Enregistre localement l'original `.eml` des messages ouverts dans Infomaniak Mail,
vers le dossier surveillé par Project Brain.

## Qualification actuelle — 30 septembre 2026

Les sources courantes sont la référence de développement. Les ZIP/XPI de Divers
restent historiques : le XPI 0.1.1 ne contient pas les corrections 0.2.0.
Tests purs : `node --test tests/test_extension_core.cjs` depuis la racine.
Packaging : `python scripts/package_extension.py --output <nouveau ZIP>` ;
JSON d’empreintes voisin. Le ZIP reconstruit est non signé. Tests Firefox et
compte Infomaniak réel requis avant de qualifier l’automatisation.
L’extension conserve les EML et clés de déduplication localement ; pas de purge
automatique. Le bouton ON/OFF contrôle la capture. Les téléchargements, leur
conservation et les accès au poste relèvent de l’utilisateur.

## Sources

- `manifest.json`, `core.js`, `background.js`, `content.js` = version **0.2.0**
  (dézippée depuis `Divers/infomaniak-auto-local-0.2.0.zip`).
- `Divers/extension firefox DL mail infomaniak.xpi` = build **0.1.1 signé**
  (installable en stable) ; `content.js` plus court, sans bouton manuel.
- `Divers/infomaniak-auto-local-0.1.1.zip` = sources 0.1.1.

## Fonctionnement

1. `content.js` observe les appels réseau Infomaniak
   (`/api/mail/<mailbox>/folder/<folder>/message/<id>?prefered_format=...`)
   et les métadonnées du message affiché.
2. `background.js` vérifie l'original via `.../download`, contrôle que c'est
   bien un EML (`core.js: eml()`), puis le télécharge avec :
   `Infomaniak-IA/<date>-<sujet assaini>-<hash16>.eml`
   (`core.js: filename()`), `conflictAction: uniquify`.
3. Déduplication côté extension : `done:<sha256(key)>` en `storage.local`
   + garde-fou `inflight`.
4. Bouton manuel 0.2.0 : « Télécharger ce mail (.eml) » injecté dans
   `app-message-header-actions` quand un seul message est affiché.
5. Badge ON/OFF, clic sur l'icône = activer/couper.

Aucune donnée mailbox ne sort de l'extension (helpers purs, `credentials:
include` vers Infomaniak uniquement).

## Installation

- **Historique signé (0.1.1), sans corrections actuelles** : `about:addons` → ⚙ → Installer depuis un fichier →
  `Divers/extension firefox DL mail infomaniak.xpi`.
- **Dev (0.2.0)** : `about:debugging#/runtime/this-firefox` → Charger un
  module temporaire → `extensions/infomaniak-auto-local/manifest.json`.
  À recharger à chaque redémarrage de Firefox (temporaire).

## Flux vers Project Brain

```
Infomaniak Mail --(extension)--> ~/Downloads/Infomaniak-IA/*.eml
  --(scan auto au démarrage + POST /v1/ingest/scan)--> Source (sha256 idempotent)
  --> résolution projet --> propositions [heuristique|IA] --> validation (/ui)
```

Le nom de fichier (`date-sujet-hash16`) est indicatif : l'idempotence réelle
est le `sha256` du contenu, et le rattachement projet se fait sur
sujet/corps/expéditeur (+ hints IA), jamais sur le nom de fichier.
Voir `docs/15_INFOMANIAK_EXTENSION.md`.
