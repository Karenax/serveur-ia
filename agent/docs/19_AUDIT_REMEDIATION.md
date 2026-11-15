# Corrections de l’audit — Agent 0.3.0

Révision de travail du 30 septembre 2026, issue de `0245c918e8802a28657b2522583281b4a0fdd868`.
Publication de cette livraison demandée explicitement le 1er octobre 2026 : commit et push sur main après les contrôles. Tous les modules fonctionnels hérités sont conservés ; les données utilisateur ne servent pas aux reproductions.

## Résultats de validation

- Profil Windows/Python 3.13 : environnement neuf installé depuis requirements-dev.txt avec empreintes vérifiées.
- `python -m pytest tests/ -q` : **62 réussis, 1 ignoré** (dossier Infomaniak réel absent). Un avertissement de dépréciation Starlette/httpx, aucun échec.
- Ruff verrouillé : aucun diagnostic sur app, backend/app, tests et scripts ; règles E4/E7/E9/F explicites dans ruff.toml.
- React : **6 tests réussis** ; compilation TypeScript/Vite réussie ; installation pnpm frozen-lockfile réussie.
- Extension : **2 tests Node réussis** ; deux builds produisent le même SHA-256 `e5aaef3ff48691258fd140e8f79646710d9aa0f2683ed809e4029472e71a004f`.
- Archive projet restaurée dans des bases vierges en processus indépendant : sources CDC et mail, connaissance/provenance, relations et cohérence FK.
- Backup global de la copie de test restauré dans un dossier neuf ; intégrité des deux bases et FK vérifiées, fichier brut présent au chemin restauré ; corruption et écrasement refusés par les tests.
- Serveur réel isolé sur 127.0.0.1:18003 : cinq pages HTML 200, health des deux bases OK, écriture sans jeton 403. React crée un projet, reclassifie un mail A → B ; Jinja valide sa proposition. Aucun log navigateur error. Serveur temporaire arrêté.

## Matrice des constats

« Corrigé » correspond à la correction et sa vérification locale. Les qualifications externes et décisions du propriétaire restent explicitement ouvertes. La couverture ne constitue pas une certification de sécurité ou de production.

| Constat initial | État | Correction / amélioration | Preuve |
|---|---|---|---|
| F01 — Les éléments CDC rejetés restent dans le devis et le transfert BE | Corrigé | Sorties finales filtrées, revue/contrôles bloquants, brouillon marqué | cdc_output.py ; test_cdc_final_output_respects_rejection_review_and_evidence |
| F02 — L’export/import projet ne permet pas une restauration fidèle | Corrigé localement | Archive v2 : relations/files/Brain ; sauvegarde globale SHA-256 et restauration neuve | test_archive_portability.py ; test_global_backup_restores_new_directory_and_rejects_corruption |
| F03 — Un mail ambigu peut être affecté automatiquement au mauvais projet | Corrigé | Codes délimités ; indices IA et égalités restent candidats ; décision humaine | test_ambiguous_and_ai_classification_remain_pending |
| F04 — Une proposition de rattachement peut devenir une « vérité » sans rattacher la source | Corrigé | project_attach interdit à la promotion de vérité ; cohérence source/projet | tests/test_audit_regressions.py |
| F05 — Les confirmations et reclassements ne sont pas idempotents | Corrigé ; purge externe à qualifier | Confirmation neutre ; reclassement invalide les dérivations et programme la purge, historique conservé | tests/test_audit_regressions.py ; preuve navigateur UI |
| F06 — Le versionnement de la vérité existe dans le modèle, pas dans l’acceptation | Corrigé | Contradiction 409, supersedes_id explicite, versions et verrou local de validation concurrente | test_duplicate_truth_is_not_created_by_concurrent_acceptance |
| F07 — Le rapprochement Sage mélange les codes voisins et accepte le code vide | Corrigé | Affaire Sage exacte, insensible à la casse, code vide sans résultat | test_sage_matching_is_exact |
| F08 — Une panne du moteur mémoire annule l’enregistrement canonique | Corrigé | Canon commité avant projection ; file pending/failed ; reprise visible | tests/test_audit_regressions.py ; projections.py |
| F09 — Les écrans Jinja documentés échouent avec les dépendances résolues | Corrigé | TemplateResponse nommé avec request/context ; chemins absolus ; jeton pour les pages Jinja | test_html_contracts_foreign_keys_and_dataset_isolation ; validation navigateur |
| F10 — La clé IA est exposée par l’API et peut être effacée lors d’une sauvegarde | Corrigé sous Windows | GET/PUT masqués, vide conserve la clé, effacement explicite, DPAPI ; remplacement d’une clé illisible | test_secret_is_write_only_and_empty_input_preserves_it ; test_unreadable_secret_can_be_replaced_without_decryption |
| F11 — Le service local accepte une commande d’ouverture trop large | Corrigé pour usage local | Host/Origin/session ; allowlist de racines/types ; exécutables refusés | test_local_session_host_origin_and_executable_protection |
| F12 — Les limites de scan et de tri peuvent bloquer définitivement la progression | Corrigé | Quotas après doublons ; tri sélectionne les sources non déjà triées ; pagination et compteurs complets | test_queues_progress_beyond_duplicate_first_batch |
| F13 — Le pont HTTP vers le même processus sature les travailleurs | Corrigé | Pont interne, sans auto-appels HTTP aux workers du même serveur | test_internal_bridge_remains_available_under_parallel_calls : 45 appels |
| F14 — La santé du service ne reflète pas sa capacité à fonctionner | Corrigé | Health réel des bases/intégrité ; IA unifiée ; moteur actif et files en erreur visibles | tests/test_minipilot_brain.py ; tests/test_memory.py ; runtime-results.json |
| F15 — Le traitement documentaire comporte deux erreurs d’entrée évitables | Corrigé | PDF corrompus, DOCX invalides, dépendance defusedxml et bornes conteneurs | test_invalid_pdf_and_docx_are_handled_and_ollama_payload_is_complete |
| F16 — La page de l’exigence CDC peut contredire sa preuve | Corrigé | physical_page du CdcItem renseignée depuis la page qui porte la preuve | cdc_generation.py ; tests/test_cdc_engine.py |
| F17 — Deux handlers PATCH exposent des contrats différents pour la même route | Corrigé | PATCH retouche et PATCH .../pricing distincts ; vérification de toutes les routes incluses | test_html_contracts_foreign_keys_and_dataset_isolation |
| F18 — Le client Ollama perd les paramètres de raisonnement et de génération | Corrigé | Ollama : think=false, options/budget, schéma JSON ; paramètres de raisonnement préservés | test_invalid_pdf_and_docx_are_handled_and_ollama_payload_is_complete |
| F19 — Intégrité SQLite, migrations et sauvegarde globale restent insuffisantes | Corrigé localement | FK/busy_timeout, migrations additives/ledger, backup SQLite, aucune purge automatique | test_html_contracts_foreign_keys_and_dataset_isolation ; restauration globale |
| F22 — La provenance consultable est plus faible que la provenance promise | Corrigé pour les formats livrés | Transcript exploité ; texte complet, original, artefact/locator exact ou contextuel et hash | test_transcript_is_extracted_and_raw_is_downloadable ; archive portable |
| F23 — Certains états de l’interface ne suivent pas les opérations métier | Corrigé | Refresh complet, raccourcis fenêtre active, maintien sur échec, ErrorBoundary, erreurs HTTP, mails reclassables | 6 tests Vitest ; UI React/Jinja réelle |
| F24 — Les traitements longs et les entrées volumineuses ne sont pas suffisamment bornés | Amélioré ; scheduler durable hors livraison | Bornes uploads/CSV/ZIP/PDF/requêtes ; worker pour I/O ; runs/counters et interruption visible ; reprise manuelle | security.py ; cdc_extraction.py ; cdc_generation.py ; limites README_BACKEND |
| F25 — Les décisions ERP sont modifiables sans historique métier suffisant | Corrigé pour revue/chiffrage | BusinessDecision, validations de dates/statuts/nombres ; offre Decimal et heures fractionnaires | test_cdc_decisions_and_numeric_date_validation ; test_offer_preserves_fractional_hours_before_cent_rounding |
| F26 — Les tests actuels laissent passer les principaux défauts métier | Corrigé ; CI distant à exécuter | Deux bases et réglages isolés, test IA hermétique, mocks restaurés, Vitest et workflow Windows | 62 tests Python réussis ; 6 tests Vitest ; verify.yml |
| F28 — L’extension Infomaniak demande une qualification et une politique de conservation | Traçabilité corrigée ; qualification externe ouverte | Versions historiques explicites, ZIP source reproductible non signé, tests helpers et conservation locale | 2 tests Node ; deux ZIP de même SHA-256 ; README extension |
| F29 — Identité du produit et provenance des composants doivent être clarifiées | Contexte corrigé ; licence propriétaire ouverte | Identité Agent 0.3.0, manifeste, contexte actuel/vision, inventaire dépendances/provenance | PROJECT_CONTEXT.md ; THIRD_PARTY_NOTICES.md ; dependencies.json |

## Limites et suite nécessaire

- Infomaniak : test Firefox avec un compte autorisé, concurrence/changement de message/download et qualification du paquet actuel ; signature Mozilla distincte de la compilation.
- Analyses longues : délai LLM borné et runs persistés, reprise manuelle après interruption. Scheduler durable et annulation client ne sont pas livrés.
- Réseau/multi-utilisateur : comptes/ACL/TLS et rétention automatisée restent dans la vision ; le service livré est local. Les labels d’acteur du journal ne prouvent pas une identité authentifiée.
- Stockage : backup global hors ligne, fichiers gérés seulement ; les fichiers externes pointés par des liens réseau ne sont pas copiés. Les clés DPAPI exigent le même compte Windows ou une nouvelle saisie. Pas de transaction distribuée entre Brain et ERP.
- Licence Agent : décision du propriétaire nécessaire ; aucune licence arbitraire appliquée aux modules. L’inventaire liste les métadonnées de dépendances observées.
- Les résultats ci-dessus sont ceux des validations locales. Après publication, le statut du workflow distant est consultable dans GitHub Actions ; il constitue une vérification distincte.

## Preuves locales conservées

Les répertoires sont extérieurs au dépôt et ne sont pas requis pour lancer Agent :

- Audit initial : `E:/Agent-audit/2026-09-30-0245c91/audit-complet.html`.
- Installation verrouillée : `E:/Agent-audit/remediation-locked-venv`.
- Corpus mémoire : `E:/Agent-audit/remediation-corpus-20260930/results.json`.
- Vérification réelle : `E:/Agent-audit/remediation-runtime-20260930/runtime-results.json` et `ui-reclassement.png`.
- Sauvegarde/restauration réelles des données synthétiques : `E:/Agent-audit/remediation-global-backup-20260930` et `remediation-global-restored-20260930`.
- Paquets extension A/B et manifestes d’empreintes : `E:/Agent-audit/extension-0.2.0-remediation-*.zip`.

## Documents de référence

[Contexte](../PROJECT_CONTEXT.md), [usage et restauration](../README_BACKEND.md), [ADR-0007](adr/0007-local-runtime-and-durable-projections.md), [provenance](../THIRD_PARTY_NOTICES.md).

## Évolution du 2 octobre 2026 — 0.4.0

Les preuves financières F01–F29 ci-dessus décrivent la livraison historique.
Sur demande explicite, le code financier est désormais retiré et les données
conservées ; les routes d’offre/chiffrage sont absentes. La nouvelle livraison
[opérationnelle](22_OPERATIONAL_IMPROVEMENTS.md) remplace les anciennes limites
sur analyse synchrone CDC, recherche de mails limitée à la page, écrasement BE,
RAF sans consommation et sauvegarde ERP à chaque démarrage.
