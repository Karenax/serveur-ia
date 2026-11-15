# Vision et périmètre

## État actuel — 11 octobre 2026

La mémoire EG2 est active sur Agent, port 8001 : index vectoriel SQLite des sources résolues, vérité canonique SQL et réponses rédigées par le LLM configuré. Les capacités disponibles et les objectifs non livrés sont distingués dans PROJECT_CONTEXT.md ; un objectif de capture ne constitue pas une intégration en service.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Problème
Le chargé d'affaires reçoit des informations dispersées par téléphone, réunion, e-mail et documents. Une partie importante du travail consiste à rechercher, reformuler, classer, vérifier, relier au bon projet et transformer ces informations en décisions, actions, risques, exigences et documents.

## Vision
Créer une mémoire projet commune, indépendante des interfaces, où :
- les sources restent consultables ;
- les informations structurées sont exploitables par machine ;
- les agents distinguent la vérité validée du reste ;
- l'humain conserve le contrôle sur les engagements importants ;
- plusieurs applications utilisent le même état de connaissance.

## Hors périmètre initial
- remplacement complet d'XPilot2 ;
- autonomie totale des agents sur les décisions engageantes ;
- génération CAO autonome ;
- remplacement d'un GED complet ;
- indexation sémantique comme source de vérité.

## Acteurs
- utilisateur principal / valideur ;
- collaborateurs autorisés ;
- agent e-mail ;
- agent téléphone ;
- agent réunion ;
- agent documents ;
- agent offre/chiffrage ;
- agent préparation de revue ;
- XPilot2 ;
- administrateur système.

## Résultats attendus
- zéro information importante perdue ;
- provenance explicite ;
- résolution projet systématique ;
- recherche fiable ;
- historique complet ;
- réduction du temps de comptes rendus et de recherche ;
- base réutilisable par de futurs agents.

## Positionnement du moteur mémoire
Le moteur de production est uniquement EG2. Agent conserve les sources et leurs textes dans le canon SQL, découpe les textes en passages, demande leurs vecteurs de 768 dimensions au serveur LM Studio et les stocke dans un index SQLite reconstructible. Lors d'une question, il contrôle le projet et la version des sources, recherche les passages pertinents, ajoute les connaissances actives lues dans SQL puis transmet ce contexte au LLM de génération.

L'indexation des preuves n'appelle aucun LLM d'extraction. Les analyses métier qui produisent des informations structurées restent des traitements distincts, avec provenance et décisions auditables. La similarité vectorielle ne modifie ni le rattachement projet ni le statut d'une connaissance. Voir [20_EG2_ENGINE.md](20_EG2_ENGINE.md).

La valeur spécifique de Project Brain reste :
- le rattachement obligatoire au projet ;
- la gouvernance de la vérité ;
- la distinction entre information retenue par défaut et confirmation humaine ;
- la provenance métier jusqu'à la source originale ;
- les connecteurs téléphone/e-mail/réunion/CAO ;
- les règles d'autorisation ;
- l'expérience de supervision et les agents spécialisés.
