# Recherche web native Hermes dans les conversations Fred

Livraison serveur du 12 octobre 2026. Windows **3.5.27** et Android **1.0.10/code 11** restent utilisables sans nouvelle installation.

## Correction

Les deux derniers appels web échouaient sur le droit Web du compte. Les profils Fred ne proposaient pas les outils web natifs ; leur ancien outil de recherche dépendait de Brave Fred, sans clé configurée sur ce PC.

Les conversations utilisent désormais `web_search` et `web_extract` natifs. Un pont privé appelle les fonctions de l’installation Hermes dans le profil personnel actif. Les connexions web restent centrales et leurs secrets ne sont pas copiés dans les profils Fred. Les recherches documentaires, les mémoires et le calcul conservent leurs outils Fred et leurs périmètres.

Chaque appel porte l’identité de son tour Hermes, capturée dans son contexte interne. Le serveur exige une correspondance exacte avec le tour admis. Un appel retardé d’un tour annulé ne peut pas exécuter un outil ou ajouter des sources au message suivant. Les droits du compte, l’annulation et la maintenance sont contrôlés avant, pendant et après le traitement. Les URL privées, les identifiants dans les URL et les redirections privées sont refusés ; la voie Firecrawl sans clé doit fournir une destination finale vérifiable.

Les sources natives sont collectées avant la troncature de l’aperçu des outils, puis conservées dans le résultat, son historique et sa reprise. Les anciennes tâches de type Web gardent Brave ou leur lecture d’URL publique ; la console distingue maintenant ce réglage de la configuration web native des conversations.

## Vérifications

- **151 tests réussis**, sans erreur ni test ignoré, en **285,657 s**. Les sources sont restées identiques durant la suite finale : modèles, réflexion, comptes, isolation, projets, sauvegardes/restauration, outils, conversations, transport et correcteur direct. [Résultat](backend-validation.json), [journal](backend-tests.txt).
- **11 tests web**, inclus dans cette suite : véritable passerelle Hermes, recherche puis extraction via son SDK natif sur un transport HTTP synthétique, sources, secrets entre profils, limites, annulation, tour retardé et redirections. [Preuve native](native-web-validation.json).
- Recherche réelle par la connexion Hermes **Perplexity** : deux résultats en **2,281 s**. Lecture réelle par **Firecrawl** : une page et 2 062 caractères en **3,281 s**. Ces essais n’ont lancé aucun modèle de conversation ni créé d’historique de production.
- **27 tests ciblés** de conversations/outils : sources conservées après reprise et redémarrage, comptes/projets séparés et rejet d’un ancien tour. Une reproduction indépendante avec le véritable pont et l’entrée privée `/mcp` confirme zéro exécution et zéro source après annulation. [Preuve](conversation-native-web.json).
- Console : syntaxe et huit contrôles de structure/rendu réussis, à 1 180 et 390 px ; formulaires et identifiants conservés. [Preuve](console-validation.json), [grand écran](console-web-1180.png), [écran étroit](console-web-390.png).

## Mise en service

Le service Fred/Hermes a été redémarré et les profils migrés en configuration **5**. Les outils natifs web proposés sont exactement `web_search` et `web_extract`. Les anciens outils web MCP Fred ont été retirés des conversations. Un appel web hors d’un tour actif est refusé sur l’entrée privée réelle. Un [contrôle indépendant après redémarrage](publicregistration-validation.json) confirme l’activation et la configuration des outils natifs, ainsi que ce refus.

Le droit Web est activé uniquement pour le compte actuel. Ses limites de stockage, projets et tâches restent identiques. Les identités de profils, les clés, les paramètres d’accès, la politique de partage et la sélection des quatre modèles externes sont préservés. Qwen conserve ses processus et reste chargé. Les contrôles authentifiés confirment la disponibilité de l’agent, de la voix et du correcteur direct.

Les fichiers publiés Windows et Android ont les mêmes empreintes qu’avant cette correction. Aucun outil terminal ou navigateur n’est ouvert et aucune conversation de production n’a été générée par la validation. [Contrôles de livraison](delivery-validation.json).
