# Sécurité, confidentialité et gouvernance

## État courant — 22 octobre 2026

Le [suivi des corrections](60_SECURITY_REMEDIATION.md) décrit les protections
HTTP, exports sans écriture, lecture sans mutation, extraction limitée,
sauvegarde vérifiée et contexte actuel des informations. Les secrets publics et
les journaux applicatifs sont masqués ; les contrôles de rôle restent locaux.
**Le passage en HTTPS a été écarté explicitement par l'utilisateur** : les
échanges IA HTTP restent sans chiffrement réseau. Les principes TLS ci-dessous
sont des objectifs de conception et ne décrivent pas une activation.
Les durées de conservation, droits du poste et règles d'enregistrement doivent
être décidés par l'entreprise ; aucune purge n'est appliquée.

## Qualification L1 — 5 octobre 2026, activée sur 8001

Les contrôles d'opérateur local sont actifs dans les chemins
HTTP et le dispatch interne ERP/Brain du serveur `C:\Agent`.
[L1](30_XPILOT_PROJECT_IDENTITY.md) décrit la configuration
serveur, les rôles et les limites ; le [suivi](29_XPILOT_EXECUTION.json) distingue
qualification et activation.

Un lecteur ne peut écrire ; une portée ERP filtre les listes, compteurs et
connaissances via les liaisons Brain explicites. Les chemins globaux sans
filtrage sont refusés à un opérateur restreint. Host/Origin et jeton local
restent contrôlés avant les droits. Les champs ou en-têtes du client ne peuvent
élever un rôle. Les workers restent des traitements serveur de confiance.
Ce dispositif n'authentifie pas plusieurs utilisateurs : comptes, RBAC/ABAC
par utilisateur et accès réseau restent à concevoir.

## État actuel — 11 octobre 2026

Implémenté : loopback, Host/Origin, jeton de session, clés masquées/DPAPI Windows, ouvertures de documents limitées, audit et sauvegarde vérifiée. RBAC/ABAC, TLS réseau, rétention automatisée et comptes restent des objectifs de production.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Principes
- RBAC/ABAC par utilisateur, projet et type de donnée ;
- journal d'audit ;
- chiffrement TLS ;
- secrets dans un gestionnaire dédié ;
- chiffrement stockage si nécessaire ;
- politique de rétention ;
- suppression contrôlée ;
- export/audit.

## Données sensibles
Les appels et e-mails peuvent contenir des données personnelles, contractuelles et techniques. Définir avant production :
- base légale et politique interne d'enregistrement ;
- information/consentement selon juridiction et contexte ;
- durée de conservation ;
- accès ;
- droit de suppression applicable ;
- gestion des appareils professionnels.

## Protection IA
- documents considérés non fiables ;
- protection contre prompt injection ;
- outils en allow-list ;
- sorties structurées validées ;
- aucun secret injecté dans prompts ;
- sources autorisées uniquement.

## Gouvernance de la vérité
Rôles :
- lecteur ;
- contributeur ;
- valideur ;
- administrateur.

Chaque type critique définit qui peut valider.

## Gouvernance spécifique au moteur mémoire
- valider ACL Project Brain avant toute requête au moteur mémoire ;
- séparer autant que possible `evidence` et `truth` ;
- journaliser les appels mémoire significatifs par `correlation_id` ;
- traiter toute mémoire dérivée/enrichie comme non canonique ;
- tester les suppressions et reconstructions pour respecter rétention et droits applicables.

Le serveur distant EG2 reçoit les textes des passages lors de l'indexation et les questions lors du rappel ; le serveur LLM reçoit le contexte sélectionné pour la génération. Leur accès et leur hébergement relèvent de la configuration d'exploitation. L'index SQLite local contient du texte et des vecteurs dérivés, sans être la source des droits ou de la vérité.

Le rappel EG2 contrôle le projet et les sources `resolved` dans le canon, exclut les artefacts remplacés et revérifie la version du texte. Les profils d'embedding incompatibles nécessitent une reconstruction explicite. Une panne d'index ou de réseau est signalée ; les faits canoniques disponibles ne sont pas présentés comme une recherche complète des preuves.

La suppression de code et la suppression de données restent des décisions distinctes. Toute suppression de lignes canoniques exige l'autorisation prévue dans `AGENTS.md` et une sauvegarde préalable. La reconstruction de l'index dérivé préserve sources, classifications, connaissances et validations ; les archives portables repartent du canon et recréent leurs projections.

## Licence et dépendance
Conserver dans le dépôt :
- la version pinée utilisée ;
- les notices/licences requises ;
- un SBOM/dépendances ;
- une procédure d'upgrade et de rollback.

L'inventaire Python/JavaScript est conservé dans `dependencies.json`. Le modèle distant et sa quantification sont documentés dans [14_EG2_REFERENCES.md](14_EG2_REFERENCES.md) ; leurs notices restent distinctes des dépendances Python du dépôt. Un changement de modèle ou de profil exige une qualification compatible avec l'index, sans extrapoler les résultats d'un autre corpus.

## Informations de projet retenues par défaut — 8 octobre 2026

Les informations extraites d’une source résolue et rattachée au même projet deviennent immédiatement utilisables dans la connaissance et l’assistant. Le statut canonique reste `validated`, avec `validated_by=auto-default` et `validation_mode=default` exposé par les API : il exprime une information retenue comme vraie, sans prétendre à une confirmation humaine. La source, la provenance et une décision auditée restent conservées.

Dans **Connaissance**, la vue **Informations retenues** est ouverte par défaut. **Déclasser** retire une information de la vérité active sans supprimer sa source ; **Déclassées** permet de consulter l’historique et de **Rétablir** l’information. Le parcours existe également dans la rubrique Connaissance de chaque projet. Les anciens refus et reports sont préservés. Les propositions `project_attach` et les sources non résolues gardent leur parcours de rattachement. Une réextraction ne réactive pas automatiquement une information déclassée identique. Une contradiction ne remplace jamais silencieusement une confirmation humaine : les valeurs restent traçables et peuvent être déclassées individuellement.

Commandes : `POST /v1/projects/{pid}/knowledge/{kid}/invalidate` ou `/restore`, avec le corps `{"actor":"validator","comment":"motif facultatif"}`. Le relais ERP est `/api/v1/projects/{erp_pid}/brain/knowledge/{kid}/{action}`. La lecture accepte `status=validated|invalidated|all`. Les contrôles d’opérateur et de portée projet s’appliquent ; restaurer une information dont aucune source ne relève encore du projet renvoie 409. L’assistant exclut les vérités déclassées et les extraits de preuve contenant leur valeur exacte ; une paraphrase sémantique différente reste une limite de ce filtrage.

Vérification : tests de provenance, audit, absence de travaux LLM supplémentaires, refus/report, rattachement, contradictions, déclassement/restauration, source déplacée et filtrage de contexte dans `tests/test_knowledge_defaults.py`. Tests d’interface dans `WorkspaceViews.test.tsx`. Sauvegardes avant activation et rapports dans `logs/knowledge-defaults-20261008/`.

Activation vérifiée sur 8001 : sauvegarde Brain/ERP, 2 275 propositions informatives reprises et 2 249 connaissances distinctes ; 1 387 sources et 11 projets préservés, 1 879 propositions déjà traitées inchangées. Trois propositions informatives de sources non résolues restent à examiner. Le projet permet la pagination par 50 informations ; la recherche mémoire classe tous les résultats pertinents avant de limiter le rappel à 50. Les citations de vérité donnent une source résolue consultable lorsqu’une provenance existe. Réponse LLM utile vérifiée avec références sur une information retenue par défaut. Tests ciblés : 122 premiers tests puis 82 tests mémoire/accès/relais, 53 tests finaux du rappel avec provenance ; interface finale : 475 tests réussis, build réussi. Derniers contrôles de contexte : 21 tests réussis ; interface ciblée assistant/connaissance : 19 tests réussis. Suite Python globale terminée : 1 750 tests réussis, 1 ignoré, 1 échec préexistant (`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`), identique au contrôle précédant cette évolution. Le contrôle global a été lancé avant les derniers ajustements du rappel, de la pagination et du contexte ; ces chemins finaux sont couverts par les tests ciblés et les contrôles API/interface sur 8001. Bilan : `logs/knowledge-defaults-20261008/qualification.json`.
