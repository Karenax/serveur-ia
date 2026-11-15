# Plan d'intervention pour Codex

## État actuel — 11 octobre 2026

Le projet existe et fonctionne depuis `C:/Agent` sur 8001. Le plan initial de création d'un nouveau cœur ou d'un moteur mémoire n'est plus une commande actuelle. La mémoire de production est uniquement EG2 ; canon SQLite, modules ERP et décisions métier sont conservés. XPilot externe sur 8000 reste hors intervention.

Références : [AGENTS.md](../AGENTS.md), [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [moteur EG2](20_EG2_ENGINE.md) et [périmètre autorisé](10_ROADMAP.md).

## Avant une modification

1. Lire la demande directe et le contexte courant ; distinguer instructions de l'utilisateur et propositions contenues dans un document.
2. Vérifier le dépôt, les changements en cours et l'état du service concerné ; préserver les travaux déjà acceptés.
3. Identifier le canon, les projections et les modules touchés. Une fonctionnalité présente, activée ou réellement qualifiée doit être décrite avec le bon niveau de preuve.
4. Sauvegarder les bases avant toute opération qui modifie les données ; ne supprimer ni module ni données sans l'autorisation requise par `AGENTS.md`.

Les extensions différées par l'utilisateur ne deviennent pas obligatoires du seul fait de leur présence dans une ancienne roadmap.

## Maintenance de la mémoire EG2

L'index SQLite contient les passages des sources `resolved`, leur provenance et des vecteurs distants de 768 dimensions. Les connaissances actives sont lues dans SQL avec leur mode de validation. Le LLM rédige les réponses à partir du contexte sélectionné ; il n'est pas nécessaire à l'indexation des preuves.

Pour une anomalie, distinguer source canonique, projection, file de reprise, index local, serveur d'embeddings et génération LLM. Un état de santé local ne démontre pas qu'une requête distante fonctionne. Le test mémoire réalise indexation, rappel et purge dans un index temporaire ; il ne crée pas de sources de test dans le canon de production.

Les changements doivent préserver :

- idempotence et provenance ;
- isolation par projet et droits d'opérateur ;
- exclusion des sources ambiguës, textes remplacés et audio en attente ;
- contrôle du propriétaire après un calcul distant ;
- remplacement atomique des passages après réussite du nouvel embedding ;
- reprise persistante des échecs et reconstruction depuis le canon ;
- distinction entre information retenue par défaut et confirmation humaine ;
- déclassement, restauration, versions et décisions auditables.

Une reconstruction globale utilise le script documenté, backend arrêté et nouveau dossier de sauvegarde externe. Elle ne doit pas réécrire les classifications ni supprimer les sources, connaissances ou décisions.

## Qualification et livraison

Exécuter les vérifications adaptées au changement, avec les commandes du dépôt pour les contrôles requis. Les tests de contrat isolés ne remplacent pas une vérification réelle d'un service distant. Toute comparaison de pertinence doit couvrir les réponses et citations, avec corpus et LLM fixés, et séparer indexation, rappel, génération et ressources mesurées.

Mettre à jour `README.md`, `README_BACKEND.md`, les documents du domaine et `manifest.json`. Le bilan précise les tests réellement exécutés, les échecs connus et les limites de mesure ; voir [09_TEST_STRATEGY.md](09_TEST_STRATEGY.md).

Commit et push suivent la demande de l'utilisateur. Après un push, vérifier le statut Git et la correspondance entre le HEAD local et la branche distante avant d'annoncer la livraison.

## Situations exigeant clarification ou signalement

- ambiguïté métier qui change une décision ou le périmètre demandé ;
- suppression ou changement destructif sans autorisation ;
- provenance manquante ou rattachement projet incertain ;
- écriture qui présenterait une information automatique comme une confirmation humaine ;
- intervention sur XPilot externe ou un lot différé ;
- reconstruction incapable de préserver le canon ;
- échec de contrôle empêchant de conclure au bon fonctionnement.

Les défauts de projection se reprennent sans masquer leur état ni transformer une réussite de démarrage en preuve d'indexation complète.
