# Intégration Hermes/Fred — 11 octobre 2026

Hermes est activé sur le serveur Fred. Windows **3.5.22** et Android **1.0.6/code 7** sont publiés et signés avec les clés existantes. Un profil natif est créé à chaque nouvel accès ; les comptes déjà autorisés sont migrés. Les conversations, le correcteur et les tâches rédactionnelles passent par Hermes avec le Qwen local partagé. Chaque projet Fred possède son projet natif Hermes, et les sessions y sont associées.

Le [guide](../../lanceur/HERMES-FRED.md) décrit les données, outils, limites et procédures. Le [plan initial](../../PLAN-INTEGRATION-HERMES-FRED.md) conserve l’architecture et les étapes de développement.

## Essais avec Hermes natif et Qwen

La [validation native](native-qwen-validation.json) utilise uniquement des profils et documents synthétiques, dans une racine temporaire, avec le modèle chargé `qwen3.8-flash-next-iq4-xs`. Les dix contrôles réussissent : véritable appel MCP de calcul, recherche documentaire citée, continuité de session avec les appels d’outils conservés, projet natif, isolation entre deux comptes utilisant le même identifiant de conversation, création automatique d’un troisième profil et conservation de la configuration de production.

L’appel natif `mcp__fred__fred_calculate` calcule `(24680+13579)*3 = 114777`. La continuation conserve le résultat sans nouvel appel d’outil. Un autre compte ne retrouve pas le marqueur privé du premier. La recherche du document du projet rend son passage réel et sa référence. Les essais ne mesurent pas un gain de vitesse : les outils enrichissent les capacités, et leurs appels ajoutent parfois du temps de traitement.

Hermes utilise les sources installées au commit `1cb26bf248e150f715ce8a487fdef2a2bef6b541`. Les essais natifs de passerelle couvrent également les clés distinctes, le refus des sessions d’un autre compte, la création à chaud d’un profil, le redémarrage supervisé, la suspension/réactivation et la conservation des données lors d’une migration de configuration.

## Contrats et récupération

La suite finale `python -m unittest discover -p "test_hermes_*.py" -q` exécutée depuis `lanceur/` passe : **59 tests en 83,958 s**.

Les tests couvrent notamment les tours durables, la reconnexion sans réexécution des outils, la protection d’une réponse serveur contre une copie locale partielle, l’absence de résurrection d’une conversation supprimée, les branches après modification de projet/historique, la révocation, l’annulation avant admission, les reçus d’accord opaques à usage unique et leur maintien pendant les heartbeats.

Les tests du fournisseur privé contrôlent compte et demande active, modèle et clé imposés côté serveur, budgets, arrêt, libération du GPU et refus d’un flux tronqué comme réponse réussie. Les consignes du projet entrent dans les instructions ; les documents restent des données non fiables.

Les sauvegardes/restaurations couvrent anciens et nouveaux formats, secrets portables rechiffrés avec DPAPI, cohérence SQLite, arrêt de processus au milieu du journal, retour arrière dans un autre worker, demande interrompue sans rejeu, échec de préparation/redémarrage et conservation de la cible des jonctions runtime. Trois essais de concurrence vérifient l’ordre des verrous et l’attente d’un agent sans bloquer le contrôleur ou Workspace. Les 39 régressions sauvegarde/restauration passent après cette correction ; les 73 régressions accès/espaces/tâches/appareils avaient également réussi.

Le [rapport client](CLIENTS.md) détaille les essais Windows et Android, les contrôles de signature, le format compatible des mises à jour et la reprise d’un accord en attente dans le même projet.

## Mise en service contrôlée

Les [contrôles de livraison](delivery-validation.json) confirment :

- EXE et APK publiés conformes aux empreintes vérifiées ; paquet Windows personnel préparé et profil conservé.
- Ancienne clé de mise à jour identique à la clé actuelle, token et tunnel personnels inchangés.
- Profil Hermes prêt, vu par un accès client existant authentifié ; mise à jour Android annoncée et téléchargement complet de l’APK vérifié par SHA-256.
- Interfaces Hermes privées limitées à `127.0.0.1`, ports 8643 et 8768.
- Modèle et processus Qwen conservés pendant l’activation, le rechargement et la sauvegarde ; registres d’accès, réglages du modèle et programmation des sauvegardes inchangés.
- Nouvelle sauvegarde chiffrée complète vérifiée : un profil Hermes et huit fichiers Hermes inclus ; service prêt après reprise. Aucune restauration sur les données de production.

Le contrôle en lecture seule constate zéro projet Fred et zéro projet natif dans l’accès actuellement présent : aucun projet existant n’était à migrer. La création et la liaison sont vérifiées positivement avec le projet synthétique natif.

Les comptes et conversations réels n’ont reçu aucun message synthétique. Les preuves Git contiennent uniquement des métadonnées publiques et des fixtures. Les secrets, données natives et archives restent dans les répertoires privés exclus de Git.

## Limites effectives

Les outils Fred disponibles sont la recherche documentaire et EG2, la lecture des sources, la recherche/lecture web publique et le calcul borné. Les outils Hermes d’exécution libre, fichiers hôte, navigateur, délégation, cron et recherche native globale de sessions sont désactivés. Les commandes intégrées aux compétences et les installations automatiques de dépendances sont également désactivées. Leur ouverture nécessite une isolation d’exécution par compte.

L’APK est publié ; son installation sur la tablette de l’utilisateur n’est pas exécutée ici. Android exige sa confirmation système. Les essais d’interface utilisent des serveurs synthétiques ; une validation acoustique sur appareil physique reste distincte. Les nouveaux clients sont requis pour le contrat conversationnel Hermes ; les anciens peuvent télécharger leur mise à jour.
