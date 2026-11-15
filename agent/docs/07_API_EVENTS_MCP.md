# API, événements et MCP

## État actuel — 11 octobre 2026

Les API REST Brain et ERP sont en service sur 8001 avec jeton local pour les écritures. La mémoire de production est EG2 et le pont mono-serveur reste interne. Les événements ci-dessous décrivent un contrat d'intégration futur : l'audit interne n'est pas un bus externe. Aucun serveur MCP Agent ni service de webhooks n'est livré.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Complément Studio et bibliothèque — 11 octobre 2026

Les nouvelles familles REST restent sur le serveur Agent 8001 :

- `/api/v1/meeting-sessions` : capacités, séances, fragments, notes/segments,
  attribution, commandes pause/reprise/finalisation, capture native, événements
  et export ZIP de récupération ;
- `/{sid}/ask`, `/live-answers` et `/enhancements` sous cette famille : assistant,
  historique partitionné, épingles et propositions à décision humaine ;
- `POST /api/v1/meeting-sessions/{sid}/publish-notes` : publication relue de notes
  seules, avec provenance, CR/actions et aucune création automatique de tâche ;
- `/api/v1/workspace/sources` : bibliothèque, imports fichier/dossier/URL explicitement
  choisis, originaux et passages ; `/sources/search`, `/fusion-settings`,
  `/source-graph` et `/fusion-stats` sous `/api/v1/workspace` complètent recherche,
  réglages et consultation. Les routes multimodales de build/annulation/reprise
  sont sous `/api/v1/workspace/fusion-settings/multimodal`.

L'historique `GET /{sid}/ask` distingue `session|project|sources|global` et
l'ensemble normalisé de `source_ids` répétés. Historique et épingles se relisent
sans LLM ; `PUT /{sid}/live-answers/{answer_id}/pin` exige les droits d'écriture
et se rejoue sans doublon. Les droits de séance, du projet d'origine de la
citation et de son projet courant sont revérifiés : changer de scope n'élargit
pas les droits. Révisions attendues, commandes stables et reçus protègent
concurrence/rejeu ; la fraîcheur du contexte est vérifiée avant et après calcul.

`GET /api/v1/meeting-sessions/{sid}/note-versions/{version_id}` lit exactement
une version de staging autorisée, avec date UTC explicite. Le chemin ERP
`/api/v1/projects/{pid}/notes/{nid}/versions/{vid}` reste la lecture d'une version
canonique : aucun aperçu ne substitue la tête courante. Les événements durables
de séance sont un journal interne ; ils ne livrent pas le bus externe ou MCP
envisagés ci-dessous. La présence des routes ne vaut pas disponibilité activée.
Contrats détaillés : [Notes](34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md),
[audio](23_MEETING_AUDIO.md) et [état, preuves et limites](38_FORESIGHT_DELIVERY.md).

Drive Foresight est exclu à la demande de l'utilisateur. Les routes restent
présentes pour conserver le code et l'historique, avec `drive_enabled` absent
ou différent du booléen `true` considéré désactivé. `GET /sources/connectors/drive`
sous `/api/v1/workspace` répond 200 avec `enabled:false`, sans requête Google
ni révélation du jeton ; `configured:true` peut seulement indiquer un jeton
historique conservé. `PUT /sources/connectors/drive` et `POST /sources/imports/drive`
refusent avec 409 après les contrôles de droits existants, avant transformation
de secret, écriture de réglage ou fetch. La présence d'un ancien jeton ne vaut
pas activation. L'interface n'affiche ni connexion ni import Drive sans
capacité explicitement active. Aucun effacement de données n'est autorisé par
cette [décision de périmètre](../logs/foresight-runtime/user-scope-decision-20261011-drive-visual.json).

Le catalogue `GET /api/v1/workspace/sources` conserve `source_type` et ajoute
`file_format` indépendant : `all`, `unknown` ou un format normalisé (`pdf`,
`png`, `jpeg`, `txt`, `docx`, `xlsx`, `csv`, `wav`, etc.). Une valeur inconnue
est refusée avec 422. Chaque ligne expose `file_format` reconnu ou `null`, sans
inventer de format pour une Note structurée. Le filtre s'applique avant le total
et la pagination, dans les projets autorisés ; identités, versions, originaux
et actions restent ceux des Sources existantes. Voir les règles MIME/suffixe
dans [ingestion](04_INGESTION_PIPELINES.md).

L'entrée **Nouvelle séance** de Sources navigue vers le formulaire Réunions en
respectant la garde des brouillons et les projets accessibles. Elle ne lance
aucun appel de création ni commande audio. La validation du formulaire réemploie
`POST /api/v1/meeting-sessions` ; le démarrage du micro reste distinct et explicite.

## REST Project Brain — source d'intégration principale

### Sources
- `POST /v1/sources`
- `GET /v1/sources/{id}`
- `GET /v1/projects/{id}/sources`

### Résolution
- `GET /v1/resolution/pending`
- `POST /v1/resolution/{source_id}/confirm`

### Connaissance
- `GET /v1/projects/{id}/knowledge`
- `GET /v1/projects/{id}/timeline`
- `GET /v1/projects/{id}/open-actions`
- `GET /v1/projects/{id}/risks`
- `POST /v1/projects/{id}/knowledge/{knowledge_id}/invalidate`
- `POST /v1/projects/{id}/knowledge/{knowledge_id}/restore`

La lecture des connaissances accepte `status=validated|invalidated|all` et expose le mode de validation, notamment les informations retenues par défaut.

### Recherche mémoire
- `POST /v1/projects/{id}/memory/recall`
- `POST /v1/projects/{id}/memory/reindex`
- `GET /v1/projects/{id}/memory/status`
- `POST /v1/projects/{id}/memory/retry`
- `GET /v1/settings/memory/engines`
- `POST /v1/settings/memory/test`
- `GET /v1/settings/memory/recovery`
- `POST /v1/settings/memory/recovery`
- `POST /v1/projects/chat`
- `POST /v1/projects/chat/stream`

`GET /v1/settings/memory/engines` décrit l'index local et ne prouve pas la disponibilité du serveur distant. Le test mémoire réalise indexation, rappel puis purge dans un index temporaire. Le statut projet distingue projections, connaissances actives, attente, échecs et travaux obsolètes.

### Propositions/validation
- `GET /v1/proposals`
- `POST /v1/proposals/{id}/accept`
- `POST /v1/proposals/{id}/reject`
- `POST /v1/proposals/{id}/edit-and-accept`

## Adaptateur mémoire interne

Contrat minimal :
```python
class KnowledgeMemoryPort(Protocol):
    async def remember_evidence(self, project_id, content, metadata): ...
    async def remember_truth(self, project_id, knowledge_item): ...
    async def recall(self, project_id, query, scopes): ...
    async def forget_projection(self, project_id, projection_id): ...
    async def rebuild_project(self, project_id): ...
    async def health(self): ...
```

L'adaptateur de production `EG2MemoryAdapter` implémente ce contrat. `remember_evidence` indexe les passages avec leur source ; `remember_truth` conserve une référence de suivi et le rappel `truth` lit directement le canon SQL. La purge est limitée au projet et à la référence ; la reconstruction ne supprime ni sources ni connaissances. Le faux adaptateur est réservé aux tests isolés.

## Événements — conception future
Contrat proposé d'événements versionnés :
- `source.received.v1`
- `source.processed.v1`
- `project.resolution_required.v1`
- `memory.evidence_indexed.v1`
- `memory.truth_projected.v1`
- `memory.rebuild_completed.v1`
- `memory.projection_failed.v1`
- `proposal.created.v1`
- `knowledge.validated.v1`
- `knowledge.superseded.v1`
- `conflict.detected.v1`

Chaque event contient :
- id ;
- type ;
- timestamp ;
- project_id ;
- actor ;
- payload minimal ;
- correlation_id.

## MCP Project Brain — façade future pour agents
Outils envisagés, sans serveur livré à ce jour :
- `search_project_knowledge`
- `search_project_evidence`
- `get_validated_facts`
- `get_project_timeline`
- `get_open_actions`
- `get_requirements`
- `get_risks`
- `get_source_excerpt`
- `propose_knowledge_item`
- `request_validation`

MCP ne doit pas exposer une écriture directe sur la vérité.

Toute future façade doit passer par les mêmes contrôles de projet, d'opérateur et de provenance que REST. Elle ne doit pas offrir d'accès direct à l'index EG2 ou aux écritures SQL qui contournerait la distinction `evidence` / `truth` et les décisions métier.

### Sauvegarde de relecture et invalidation des réponses

`PUT /api/v1/projects/{project_id}/recordings/{recording_id}/transcript` invalide
les preuves antérieures dès une correction sauvegardée, y compris validate=false.
La validation rend la nouvelle preuve de transcription utilisable par Ask séance,
avec recording_id, artifact_id, revision, segment_id et bornes audio.
L'événement de séance `transcript.updated` porte recording_id, recording_revision,
reviewed_revision et mode=complete-recording-review. Il réveille le suivi existant
sans incrémenter la révision des notes. L'historique des réponses vérifie également
la version d'enregistrement courante pour exposer une réponse devenue obsolète.
Les droits Brain et la concordance projet/source/enregistrement sont revérifiés
avant toute préparation du texte ; une preuve incohérente provoque un refus 409.

### L10 qualifié ; PDF direct des comptes rendus — 16 octobre 2026

Une route GET `/api/v1/projects/{project_id}/meetings/{meeting_id}/pdf` produit
le CR et ses actions avec le moteur ReportLab/Vera existant. Lecture seule,
droits projet vérifiés, texte échappé, réponse privée non mise en cache.
Le téléchargement réutilise AsyncDownloadLink et son indicateur de préparation.
Les CR projet et globaux proposent le lien ; Markdown et PDF RLP restent conservés.

La publication, le rejeu, la provenance et la création explicite d’une Task sont
vérifiés sur bases privées. Le CR reste unique, aucune tâche n’est créée avant
la commande et une seconde conversion est refusée. Trois tests backend,48frontend,
23contrôles d’accès, TypeScript, Vite et Ruff passent. Les ensembles se recouvrent.
Les deux pages de PDF fictif sont rendues et inspectées sans défaut de lisibilité.

Le parcours audio/LLM réel existant est réutilisé après comparaison AST des fonctions
concernées ; pas de nouvelle transcription, modèle ni microphone. Sauvegardes et
restaurations privées des trois bases vérifiées avant activation ; toutes les lignes
non volatiles comparées Brain/ERP sont exactes. Le service8001 et les assets sont
contrôlés. L10 est clos ; L12 reste ouvert. Détail : domaine42.

### L00/L08 qualifiés — 16 octobre 2026

Le dossier39 et le contrat versionné couvrent9écrans et25fonctions. Trois supports
publics officiels sont archivés avec dimensions/empreintes ; les interactions non
montrées sont des spécifications Agent. Pas de parité Mac privée ni ±2px revendiquée.
Le corpus fictif commun est conservé hors production.

Le parcours Sources privé vérifie dossier choisi, réimport/version, labels,
original ancien, absence de fichier sans purge, PDF illisible conservé, import
HTTPS public et lecture de la copie, puis événement ICS choisi/rejoué sans changer
la date de séance. Drive est refusé avant réseau. Le statut indexé est francisé.
Les61contrats backend sur sources inchangées sont réutilisés ;30tests UI actuels,
TypeScript et Vite passent. Ce n’est ni une nouvelle coupure physique ni une suite
globale répétée. Activation statique, assets HTTP exacts et ancien build sauvegardé ;
aucune écriture métier canonique, modèle ou microphone. Voir domaine43.

### L05/L07 qualifiés ; déduplication des questions en recouvrement — 16 octobre 2026

Le proactif regroupe les textes normalisés identiques lorsque leurs intervalles
audio se chevauchent dans la même séance. Les chiffres/mots restent distincts,
sans fenêtre de temps ajoutée. Les segments sont conservés ; un événement
assistant.proactive-duplicate trace question_token et duplicate_of sans nouveau
contenu privé dans le flux SSE. Répétition ultérieure et autre séance restent admises.

Le ciblé affecté47 et le complément inter-séances1 passent ; les deux doublons
échouaient avant correctif. Scopes/historique/contexte relu et saisie UI sont
réutilisés sur leurs sources/fonctions vérifiées avec leurs JUnit107/21/92, sans
cumul ni nouvelle suite globale. Les réponses utiles réelles et l’arbitrage réseau
restent leurs reçus datés ; aucune nouvelle génération n’est lancée.

La lecture LM Studio actuelle constate le génératif primaire chargé et aucun
génératif local chargé. Correction activée après sauvegarde/restauration privée
des trois bases ; lignes comparées non volatiles Brain/ERP exactes. Ruff passe.
L05/L07 sont clos ; qualité industrielle du direct, P95 visible et L12 restent
distincts et ouverts. Détail : docs/44_FORESIGHT_L05_L07_QUALIFICATION.md.

### Précision de comparaison des questions — 16 octobre 2026

La déduplication ignore les espaces et la casse, avec normalisation Unicode,
mais conserve chaque signe de ponctuation. Elle distingue les références
AIRB…-A et AIRB…/A, ainsi que1,5 et1/5. Les deux cas échouaient avant précision ;
les sept cas de déduplication passent sur la version finale. Les autres43cas
du ciblé47 restent leurs preuves acquises, sans nouvelle exécution ni cumul.
La portée inter-séances et les répétitions ultérieures restent conservées.

Correction activée, sans nouvelle génération ni capture. Les sauvegardes SQL
récentes intactes et leurs restaurations déjà qualifiées sont réutilisées après
comparaison exacte des données non volatiles Brain/ERP avant et après redémarrage.
Ruff passe. L05/L07 restent qualifiés ; L12 reste ouvert.
