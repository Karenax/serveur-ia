# Qualification L01 et L04 — 16 octobre 2026

L01 et L04 sont qualifiés dans leur périmètre complet de modèles, contrats, Notes et projection.
La qualification réutilise les tests acquis sur les fichiers vérifiés inchangés et complète les cas manquants sur le code actuel.
Elle ne clôture pas les lots de capture matérielle, de direct industriel ou la recette globale L12.

## L01

| Exigence du plan | Preuve inspectée |
|---|---|
| Modèles de session/fragments/bindings et états séparés | Modèles et contraintes inchangés depuis le global ; cas completed_speech_processing_does_not_claim_final_transcript |
| Versions, citations et API/événements | 5 tests actuels note-versions ; contrats SSE ordonnés/cursor/reconnect et identités stables du global |
| Liaison finale MeetingRecording et staging sans projet | Parcours HTTP actuel : audio fictif et notes conservés sans Source avant attribution, liaison unique après attribution |
| Clés de rejeu, transitions et collisions | Parcours HTTP actuel : attribution et finalisation rejouées ; clé réutilisée vers un autre projet valide rejetée 409 |
| Même séance par accès global et projet | Parcours HTTP actuel : mêmes identités par meeting-sessions et workspace/meetings ; CR historique conservé |
| Migrations additives sauvegardées avant DDL | Contrat test_additive_schema_backup_first_invalid_schema_and_retry ; sources du schéma inchangées ; sauvegardes et restaurations privées actuelles |
| Collisions notes/projets et propriété de staging | Contrats identiques entre projets, staging privé, opérateurs et attribution ; 5 tests actuels de version historique |

## L04

| Exigence du plan | Preuve inspectée |
|---|---|
| Même ProjectNote dans Documents et séance, éditeur existant | Contrat concurrent_documents_edit, mêmes note_id/version ; éditeur riche conservé et navigation UI qualifiée séparément |
| Outbox ERP atomique et reçu Brain idempotent | Ciblé actuel : rollback outbox, crash après commit Brain puis même reçu au rejeu |
| Projection evidence et localisateurs de blocs | Contrats versions/citations de notes actuels ; SourceArtifact versionné avec blocs ; aucune promotion en vérité |
| Migration historique progressive et sans perte | Ciblé actuel historical_backfill : curseur par lots et versions immuables ; note canonique actuelle reçue avec 2 passages EG2 de contenu/profil actuels |
| Notes restaurées, pièces remplacées, sans liaison Brain | Nouveau cas restauration et liaison différée ; contrats Notes/files/history inchangés pour pièces immuables et restauration par nouvelle version |
| Texte/version/pièces historiques inchangés | Contrats SQLite de notes/histoire/pièces du global sur sources inchangées ; comparaison actuelle de toutes les lignes non volatiles Brain/ERP exacte |
| Notes identiques entre projets séparées | Ciblé actuel identical_note_text_in_two_projects_stays_separate ; capsule note/projet distincte du hash de texte |
| Invalidation avant réindexation | Ciblé actuel notes_latest_version_projection_and_source_identity et canonical_unavailable ; relecture courante avant contexte |
| Sauvegarde ERP indépendante des pannes Brain/EG2 | Nouveau cas : V2 sauvée pendant panne ; événement durable ; V1 obsolète et V2 reçue au retour ; ancienne limite 20 supprimée avec backoff maintenu |

## Reprise des notes après panne

Le worker conserve désormais le statut failed au-delà de 20 échecs, avec compteur et délai progressif plafonné à une heure entre tentatives.
Les anciens événements exhausted redeviennent éligibles quand leur délai est atteint. Aucun événement ni contenu humain n’est recréé.
Un projet sans liaison Brain garde ses versions dans ERP ; la projection attend une liaison explicite. Une restauration crée une nouvelle version avec outbox dans la même transaction.
Les pièces jointes restent des originaux immuables : remplacer une pièce crée une nouvelle référence/version, sans réécrire les anciennes captures de note.
Un changement explicite de liaison Brain exige une résolution du binding existant ; il ne déclenche pas de réaffectation implicite.

## Résultats et limites

Les deux nouveaux cas de panne prolongée échouaient avant correction. Neuf cas ciblés de projection et reprise passent après correction ; cinq cas de citation et un parcours HTTP d’identité passent également.
Les tests historiques Notes/histoire/pièces/SSE sont relus dans le JUnit global et leurs sources concernées restent identiques. Les ensembles se recouvrent ; aucun nouveau global n’est déclaré.
Le parcours HTTP utilise TestClient et les handlers originaux sur des bases SQLite privées, sans microphone ni génération. Il ne constitue pas une capture réelle.
Le fonds canonique actuel contient une note : sa version ERP, le reçu, le binding Brain et ses deux passages EG2 correspondent aux empreintes de contenu et de profil actuelles. Ce constat n’est pas une mesure sur un grand corpus.
Activation après sauvegardes des trois bases et restaurations sur copies ; toutes les lignes non volatiles comparées Brain/ERP sont exactes. Ruff passe.
Les premiers refus de stockage temporaire de test et l’essai HTTP 404/409 sont conservés ; ils ne sont pas déclarés réussis. Le second test utilise un autre projet valide pour isoler la collision de commande.
L12 reste ouvert : matériel, direct industriel et volume réellement plein notamment restent distincts.

[Audit, JUnit, empreintes et activation](../logs/foresight-runtime/L01-L04-software-qualification-ROOT-20261016.json).
