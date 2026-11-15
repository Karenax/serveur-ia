# Intégration future avec XPilot2

## Orientation ajoutée le 5 octobre 2026

L'utilisateur demande désormais la reprise des fonctions projet d'XPilot dans
Agent. L'[audit des écrans et actions](27_XPILOT_PROJECT_AUDIT.md) et le
[plan de reprise](28_XPILOT_PROJECT_PLAN.md) sont les références pour ce travail.
Ils prévoient l'enrichissement des modules existants d'Agent sur `8001`, sans
absorption du dépôt XPilot, copie de sa base ni réactivation des finances.
L'audit initial était documentaire. L'utilisateur a depuis lancé l'objectif ;
voir le [suivi d'exécution](29_XPILOT_EXECUTION.json) et les
[contrats de reprise](29_XPILOT_FOUNDATION.md). Le démarrage L0 ne modifie pas
le service externe ni ses données.
Le [socle L1](30_XPILOT_PROJECT_IDENTITY.md) est maintenant activé sur `8001` :
identité additive, référentiels, équipe historisée et archives v3 sélectives,
avec import des anciennes archives v2. Les droits HTTP/internes, formulaires et
routes ont été qualifiés avec les correctifs mails conservés et une recette
navigateur sur bases fictives. L2 poursuit les fonctions de planning.
Les ACL mentionnées dans les sections historiques ci-dessous
sont une cible de conception, pas une authentification multi-utilisateur déjà
implémentée dans Agent.
Les sections ci-dessous décrivent l'ancienne conception de liaison entre deux
applications ; elles restent pertinentes pour une future interopérabilité,
mais ne constituent pas le plan d'exécution de la reprise fonctionnelle.

## État actuel — 30 septembre 2026, Agent 0.3.0

XPilot sur 8000 reste externe. Agent sur 8001 conserve la liaison ERP/Brain ; aucune modification du service XPilot ni intégration XPilot2 complète n’est revendiquée.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Principe
Le cœur de connaissance reste autonome.

XPilot2 :
- conserve ses propres projets, tâches, jalons, planning, livrables et finances ;
- consomme le cœur en lecture ;
- reçoit éventuellement des propositions ;
- garde ses propres règles métier.

## Mapping
Créer `external_project_mapping` :
- `knowledge_project_id`
- `system`
- `external_project_id`
- `external_project_code`
- `verified_at`

## V1
XPilot2 interroge :
- faits validés ;
- décisions ;
- risques ;
- actions ouvertes ;
- timeline ;
- sources.

## V2
Le cœur propose :
- créer tâche ;
- modifier jalon ;
- créer note ;
- rattacher livrable.

XPilot2 valide selon ses propres permissions avant écriture.

## Interdit
- accès direct à la DB XPilot2 ;
- accès direct de XPilot2 à la DB du cœur ;
- partage de tables ;
- duplication silencieuse de la vérité.

## Recherche enrichie
Un client appelle les API Agent, qui passent par le cœur de connaissance pour que :
- les ACL soient appliquées ;
- le `project_id` soit résolu ;
- la réponse distingue vérité validée et évidence ;
- les citations/provenances pointent vers les sources Project Brain ;
- le moteur mémoire puisse être remplacé sans modifier XPilot2.
