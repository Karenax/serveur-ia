# Analyse périodique des connaissances projet

## But et fonctionnement

À la demande de l'utilisateur, un worker du serveur unique 8001 complète le
tableau de bord des projets actifs à partir des connaissances retenues du projet
Brain lié. Première analyse dès qu'Agent dispose de temps IA libre, puis toutes
les 48 heures après le dernier bilan réussi. Chaque projet termine ses lots avant
le passage au suivant ; un projet en erreur est différé de 15 minutes et laisse
la place aux autres. Les projets hors périmètre opérateur et les opérateurs lecteurs
ne déclenchent pas d'analyse. Aucun service, tâche Windows ou port supplémentaire.

## Entrées, couverture et preuves

Tout le texte retenu est parcouru par morceaux d'au plus 6000 caractères avec
recouvrement, regroupés par lots d'environ 6500 caractères. Chaque morceau est
comparé à chaque groupe de 12 fonctions, contraintes ou exigences CDC encore
actives. Aucun classement lexical ne supprime les connaissances jugées peu pertinentes.
L'analyse croisée complète peut demander beaucoup de lots ; elle attend le temps
libre et ne promet pas qu'un passage terminera exactement à une heure donnée.

Un constat n'est retenu qu'avec un identifiant de cible du lot, un identifiant de
connaissance du lot et un extrait littéralement présent dans ce lot. Les contenus
importés sont traités comme données et jamais comme instructions. Le modèle reçoit
les critères CDC et doit distinguer exigence déclarative et réalisation/essai.
Ses états restent des **évaluations IA proposées**, pas des certifications :
`satisfied`, `partial`, `not_satisfied`, `unclear`. Une absence de preuve donne
`unknown`, sans conclure à une non-conformité. Des états contradictoires sur une
même cible produisent `unclear`, avec conservation des justificatifs.

Les dates proposées exigent un jour/mois/année explicite, un jalon nommé et une
nature contractuelle/prévisionnelle/réelle dans l'extrait, avec les mêmes vérifications
locales que le moteur de jalons. Elles apparaissent dans le bilan et ne remplacent
aucune date planning. Le bilan n'ouvre pas automatiquement une MilestoneCandidate :
le circuit existant de proposition/validation des dates reste disponible séparément.
Les statuts épistémiques CDC et validations métier restent conservés.

## Persistance, API et affichage

`backend/app/project_knowledge_models.py` ajoute une table dérivée ERP
`project_knowledge_analyses`, créée par l'initialisation normale avec sauvegarde
du schéma existant. Snapshot, curseur, résultats partiels et ancien bilan sont
persistants. Les entrées et réglages fournisseur/modèle sont contrôlés à nouveau
avant enregistrement. Une modification relance le parcours depuis le début.
Un arrêt pendant l'appel n'enregistre pas le lot ; le prochain démarrage le reprend.
Une réponse vide, JSON invalide ou ne comportant que des preuves irrecevables
produit un échec visible, sans enregistrer un faux bilan terminé.

`GET /api/v1/projects/{project_id}/knowledge-analysis` expose état et bilan,
offset/limit (20 par défaut, 50 maximum) pour les cibles. Les 50 premiers points
et dates sont affichés avec les totaux ; le rapport persistant conserve le tout.
Le panneau du cockpit actualise l'état toutes les 15 secondes uniquement lorsqu'il
est affiché. Les preuves montrent identifiants de connaissance/source et extrait.
Un bilan dont les connaissances, sources ou CDC ont changé est signalé périmé.

Les sauvegardes globales SQLite incluent cette table. Les archives projet portables
excluent ce cache dérivé qui référence les identifiants Brain d'origine ; le projet
importé sera réanalysé, les connaissances et données métier restant dans l'archive.

## Réglages et vérification

- `AGENT_PROJECT_KNOWLEDGE_ENABLED` : 1 par défaut, 0 pour désactiver.
- `AGENT_PROJECT_KNOWLEDGE_INTERVAL_HOURS` : 48 par défaut, minimum 1.
- Le modèle et son activation viennent de `brain_ai_settings()`.
- Si IA désactivée, état `waiting_model`. Pas de téléchargement de modèle local.
- Tests : `tests/test_project_knowledge_analysis.py`, `tests/test_chat_stream.py`,
  tests React du panneau et du cockpit.

Ce changement ne remplace aucun module hérité et ne modifie pas XPilot sur 8000.

## Qualification et activation du 10 octobre 2026

Sauvegarde coordonnée avant activation : 1356 fichiers contrôlés par SHA-256,
bases Brain et ERP intègres. Worker actif dans le backend supervisé, panneau
vérifié dans le cockpit réel sans erreur console. Le retour du LLM a été confirmé
par une réponse réelle `OK`. Après suppression des valeurs complètes et métadonnées
redondantes de la requête LLM (les preuves restent contrôlées localement), les deux
premiers lots AIRB25LTH0806-A ont enregistré 3 constats et 1 point important.
Le bilan de ce projet n'est pas encore terminé : 209 lots dans ce passage initial.
Le lot suivant a été rejeté faute de justificatif recevable ; le curseur reste à
2, les constats déjà enregistrés sont conservés et une reprise après 15 minutes
est programmée. La connexion LLM réussie ne vaut donc pas validation de tout
le bilan ; les réponses sont contrôlées lot par lot.

60 tests Python ciblés passent avant le dernier allégement du payload ; ses chemins
finaux sont revérifiés par 32 tests incluant priorité, preuves, streaming et absence
de duplication du texte. 481 tests React, TypeScript/build et Ruff passent.
La suite Python générale est interrompue après l'échec préexistant
`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`, reproduit
séparément dans les fichiers de tri mails inchangés ; aucune réussite globale
de cette suite n'est annoncée pour cette qualification du 10 octobre.

Preuves d'exploitation : `logs/knowledge-analysis-activation-20261010/`,
`logs/knowledge-analysis-targeted.log`, `logs/knowledge-analysis-web-tests.log`,
`logs/knowledge-analysis-baseline-failure.log`.

## Livraison du 11 octobre 2026

Le worker et son panneau font partie de la même application livrée avec EG2.
Le bilan partiel ci-dessus est un constat daté, pas une preuve de fin de tous les
projets. La suite globale exécutée pour la migration s’est terminée avec 1 777
tests Python réussis, 1 ignoré et le même échec préexistant de classement mail.
Les vérifications finales du moteur, du chat et des archives sont documentées
dans [le moteur EG2](20_EG2_ENGINE.md).
