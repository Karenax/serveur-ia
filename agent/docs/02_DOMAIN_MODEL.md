# Modèle de domaine

## État actuel — 11 octobre 2026

Canon SQLite conservé : sources, connaissances versionnées, provenance exacte ou contexte explicitée, journal de décisions CDC et file mémoire persistante. Les passages et vecteurs EG2 sont une projection reconstructible séparée ; les connaissances actives sont lues directement dans le canon. Contacts/réglages globaux relèvent du backup global.

Le Studio ajoute `MeetingSession`, fragments, segments, événements, commandes
et versions de staging dans Brain. Une séance peut exister sans projet, sans
créer un projet fictif : son staging privé n'est pas une Source canonique de
projet. Une Source admissible à la projection d'un projet conserve son
rattachement résolu ; un brouillon de bibliothèque n'en tient pas lieu.
L'attribution utilise les identités ERP et Brain distinctes et explicites.
`Note`/`NoteVersion` ERP restent l'autorité des notes rattachées ; ERP11 ajoute
l'outbox transactionnelle, puis un reçu Brain idempotent porte la projection.
Les index et propositions IA restent dérivés, sans validation automatique de
la note humaine. Voir [Notes et projection](34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md)
et [livraison et limites](38_FORESIGHT_DELIVERY.md).

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Entités principales

Les listes ci-dessous décrivent le vocabulaire métier et les champs attendus.
Les schémas livrés sont définis dans `app/models.py`,
`app/meeting_session_models.py`, `app/source_library_models.py` et les modèles
ERP, notamment `backend/app/project_note_models.py`. Les champs de conception
ne valent pas déclaration d'une API ou d'une colonne disponible.

### Project
Identifiant canonique des informations rattachées à un projet. Les séances et
leurs brouillons de staging peuvent précéder ce rattachement ; ils ne deviennent
pas des preuves de projet par un identifiant implicite.

Champs minimaux :
- `id`
- `external_refs[]`
- `code`
- `name`
- `status`
- `customer_id`
- `aliases[]`

### Contact
- identité ;
- société ;
- téléphones normalisés ;
- e-mails ;
- rôles par projet ;
- aliases.

### Source
Une unité de preuve reçue par le système.
- `source_id`
- `project_id` obligatoire après résolution
- `source_type`
- `captured_at`
- `received_at`
- `author/contact`
- `participants`
- `original_uri`
- `sha256`
- `mime_type`
- `metadata`
- `retention_policy`

### SourceArtifact
Représentation dérivée :
- transcription ;
- texte extrait ;
- OCR ;
- miniatures ;
- métadonnées CAO ;
- représentation JSON.

### KnowledgeItem
Objet générique structuré.
- `id`
- `project_id`
- `kind`
- `subject`
- `value`
- `unit`
- `status`
- `confidence`
- `valid_from`
- `valid_to`
- `criticality`
- `created_by`
- `validated_by`
- `validated_at`
- `supersedes_id`

### ProvenanceLink
Relie un KnowledgeItem à une source :
- `source_id`
- `knowledge_item_id`
- `locator` (timestamp audio, page, paragraphe, cellule, objet CAO)
- `quote_or_excerpt_hash`
- `extraction_run_id`

### Proposal
- création ;
- modification ;
- invalidation ;
- rattachement projet ;
- fusion/déduplication.

### ValidationDecision
- accept ;
- reject ;
- edit-and-accept ;
- defer ;
- conflict.

## Types initiaux de connaissance
- `fact`
- `decision`
- `action`
- `requirement`
- `constraint`
- `risk`
- `issue`
- `commitment`
- `milestone`
- `cost`
- `budget`
- `quality_item`
- `technical_reference`
- `document_reference`
- `contact_role`
- `free_information`

Le schéma doit permettre d'ajouter des types sans refonte majeure.

### MemoryDatasetMapping
Métadonnée de suivi des portées mémoire par projet, conservée pour la reprise et les archives. Le moteur de production est `eg2` ; `truth` désigne les connaissances actives SQL et `evidence` les passages vectorisés. Ces portées ne constituent pas deux bases externes indépendantes.

- `id`
- `project_id`
- `purpose` = `evidence | truth`
- `dataset_name`
- `engine` = `eg2`
- `engine_version`
- `created_at`
- `last_rebuilt_at`
- `status`

Contrainte unique : `(project_id, purpose, engine)`.

### MemoryProjection
Trace ce qui a été envoyé au moteur mémoire :
- `id`
- `project_id`
- `source_id` ou `knowledge_item_id`
- `purpose`
- `dataset_mapping_id`
- `content_hash`
- `external_ref` (`eg2:…` pour les preuves, `truth:…` pour les connaissances)
- `projection_version`
- `projected_at`
- `status`
- `last_error`

La file garde les états `pending`, `indexed`, `failed`, `obsolete` et `forgotten`. Un échec d'indexation laisse les sources et décisions canoniques intactes. Le projet, le statut et la version du propriétaire sont revérifiés après le calcul distant ; une source déplacée ou une connaissance remplacée ne peut être réactivée par un travail ancien. La purge et la reconstruction portent uniquement sur l'index et ses projections.

### MemoryIngestionRun
Objet de conception pour un suivi détaillé d'exécution, sans table dédiée livrée à ce jour. Le suivi opérationnel actuel utilise `MemoryProjection`, l'audit et l'état du worker de reprise.

- `id`
- `project_id`
- `dataset_mapping_id`
- `started_at`
- `finished_at`
- `status`
- `correlation_id`
- `metrics`
- `error`

## Informations de projet retenues par défaut — 8 octobre 2026

Les informations extraites d’une source résolue et rattachée au même projet deviennent immédiatement utilisables dans la connaissance et l’assistant. Le statut canonique reste `validated`, avec `validated_by=auto-default` et `validation_mode=default` exposé par les API : il exprime une information retenue comme vraie, sans prétendre à une confirmation humaine. La source, la provenance et une décision auditée restent conservées.

Dans **Connaissance**, la vue **Informations retenues** est ouverte par défaut. **Déclasser** retire une information de la vérité active sans supprimer sa source ; **Déclassées** permet de consulter l’historique et de **Rétablir** l’information. Le parcours existe également dans la rubrique Connaissance de chaque projet. Les anciens refus et reports sont préservés. Les propositions `project_attach` et les sources non résolues gardent leur parcours de rattachement. Une réextraction ne réactive pas automatiquement une information déclassée identique. Une contradiction ne remplace jamais silencieusement une confirmation humaine : les valeurs restent traçables et peuvent être déclassées individuellement.

Commandes : `POST /v1/projects/{pid}/knowledge/{kid}/invalidate` ou `/restore`, avec le corps `{"actor":"validator","comment":"motif facultatif"}`. Le relais ERP est `/api/v1/projects/{erp_pid}/brain/knowledge/{kid}/{action}`. La lecture accepte `status=validated|invalidated|all`. Les contrôles d’opérateur et de portée projet s’appliquent ; restaurer une information dont aucune source ne relève encore du projet renvoie 409. L’assistant exclut les vérités déclassées et les extraits de preuve contenant leur valeur exacte ; une paraphrase sémantique différente reste une limite de ce filtrage.

Vérification : tests de provenance, audit, absence de travaux LLM supplémentaires, refus/report, rattachement, contradictions, déclassement/restauration, source déplacée et filtrage de contexte dans `tests/test_knowledge_defaults.py`. Tests d’interface dans `WorkspaceViews.test.tsx`. Sauvegardes avant activation et rapports dans `logs/knowledge-defaults-20261008/`.

Activation vérifiée sur 8001 : sauvegarde Brain/ERP, 2 275 propositions informatives reprises et 2 249 connaissances distinctes ; 1 387 sources et 11 projets préservés, 1 879 propositions déjà traitées inchangées. Trois propositions informatives de sources non résolues restent à examiner. Le projet permet la pagination par 50 informations ; la recherche mémoire classe tous les résultats pertinents avant de limiter le rappel à 50. Les citations de vérité donnent une source résolue consultable lorsqu’une provenance existe. Réponse LLM utile vérifiée avec références sur une information retenue par défaut. Tests ciblés : 122 premiers tests puis 82 tests mémoire/accès/relais, 53 tests finaux du rappel avec provenance ; interface finale : 475 tests réussis, build réussi. Derniers contrôles de contexte : 21 tests réussis ; interface ciblée assistant/connaissance : 19 tests réussis. Suite Python globale terminée : 1 750 tests réussis, 1 ignoré, 1 échec préexistant (`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`), identique au contrôle précédant cette évolution. Le contrôle global a été lancé avant les derniers ajustements du rappel, de la pagination et du contexte ; ces chemins finaux sont couverts par les tests ciblés et les contrôles API/interface sur 8001. Bilan : `logs/knowledge-defaults-20261008/qualification.json`.

### Historique des transcriptions corrigées

`SourceArtifact.kind=transcription_snapshot` conserve la révision ASR précédant
une première correction enregistrée si aucune preuve ne la conserve déjà.
Son `content_json` garde recording_id, revision, segments, speaker_names,
reviewed, superseded=true et snapshot_reason=before_saved_edit. Cet historique
est exclu du contexte courant. Les preuves `transcription` de révisions précédentes
sont également marquées périmées dès une modification, même non validée.
Aucune table ni migration destructive : historique et segments directs conservés.

### L01/L04 qualifiés et reprise Notes sans abandon définitif — 16 octobre 2026

`note_evidence_bridge.process_pending` reprend pending/failed/waiting_project
et les anciens exhausted. Le compteur d'échecs est conservé, sans seuil d'abandon20.
Le backoff (60s exponentiel, au plus une tentative par heure après stabilisation)
et le lot de100événements sont conservés. Aucun reset de file, nouvelle version
ou nouvelle identité de source n'est créé par la correction.

Neuf tests ciblés de projection, cinq de versions/citations et un parcours HTTP
global/projet/staging/rejeu passent. Les contrats historiques applicables sont
réutilisés après contrôle d'identité de leurs sources ; aucune suite globale rejouée.
Les compteurs se recouvrent. Ruff passe. Le fonds Notes courant (une note) est vérifié
en lecture seule jusqu'aux deux passages EG2, avec empreintes de contenu/profil.
Activation après sauvegarde Brain/ERP/EG2 et restauration privée ; lignes comparées
non volatiles exactes. Aucune capture, GPU ou génération.

L01/L04 sont clos selon leurs livrables et sorties du plan. Les essais matériels,
le direct industriel et la qualification globale L12 ne sont pas assimilés à ces
contrats logiciels. Détails : `docs/41_FORESIGHT_L01_L04_QUALIFICATION.md`.
