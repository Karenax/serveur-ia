# Conversations Fred avec Hermes

Les clients Windows 3.5.22 et Android 1.0.6/code 7 envoient leurs demandes à Fred. Le serveur confie chaque conversation à Hermes, qui utilise le Qwen local déjà chargé et les outils autorisés. Le correcteur et les tâches rédactionnelles utilisent également Hermes. Le modèle reste partagé : un compte ne charge pas un autre Qwen.

## Comptes et projets

La création d’un accès Fred crée automatiquement le profil natif `fred-<identifiant>` dans `lanceur/hermes-fred/profiles/`. Les clés restent sur le serveur, protégées par DPAPI et les droits Windows. Une création incomplète est affichée dans la console et peut être reprise sur la même fiche ; le profil conserve son identité et aucun paquet client utilisable n’est distribué avant sa disponibilité.

Chaque projet Fred possède un projet natif Hermes dans le profil du compte. Le nom, les consignes et l’archivage sont synchronisés ; le renommage conserve l’identité native. Le dossier `workspace/projects/<identifiant-projet>/` contient un catalogue des documents. Leur contenu demeure dans l’espace Fred et est lu par MCP avec les droits du compte et du projet. L’association d’une session à son projet passe par les API officielles Hermes et son dossier de travail, sans changer le projet actif de toutes les conversations.

Chaque conversation utilise une session indépendante. Une continuation conserve les appels d’outils et leur résultat. Un changement de projet, une modification de l’historique ou une restauration ouvre une nouvelle session avec l’historique visible accepté.

## Outils et mémoire

Hermes dispose des recherches documentaires Fred, de la mémoire sémantique EG2, de la lecture des passages cités, du calcul arithmétique borné et de la recherche/lecture web selon les autorisations Fred. Ses souvenirs, compétences et listes de tâches sont propres au profil. La recherche native dans toutes les sessions est désactivée : les recherches Fred appliquent le périmètre du projet.

Les outils système Hermes qui exécutent du code, manipulent librement les fichiers hôte ou contrôlent un navigateur ne sont pas activés. Leur ouverture nécessite un environnement d’exécution réellement isolé par compte. Les autorisations ponctuelles transportées par les clients sont limitées à « une fois » et « refuser » et ne constituent pas un droit général sur le serveur.

L’installation automatique de dépendances et les commandes intégrées aux compétences sont également désactivées. Les conversations utilisent le runtime installé sans le modifier.

Le contenu des documents et des pages web est transmis comme données non fiables. Les outils imposent le compte et le périmètre côté serveur, vérifient les droits avant et après l’appel et refusent les URL privées ainsi que les expressions qui exécuteraient du code.

## Coupures et sauvegardes

Chaque envoi possède une identité durable. La coupure du transport laisse l’agent terminer : le client retrouve le résultat accepté à la reconnexion sans répéter ses outils. Une annulation, suspension, révocation ou expiration arrête la demande. Une demande interrompue par l’arrêt du serveur n’est pas rejouée automatiquement.

Les sauvegardes chiffrées Fred incluent le registre d’association, les sessions, souvenirs, compétences, projets et dossiers de travail Hermes. Une sauvegarde attend la fin des conversations, puis arrête brièvement la passerelle Hermes pour produire un instantané cohérent. Les secrets portables sont protégés par l’enveloppe chiffrée de la sauvegarde et rechiffrés avec DPAPI à la restauration. Les clés runtime, journaux, dépendances partagées et tâches cron natives sont exclus. Le journal de restauration couvre également la racine Hermes pour revenir à l’état précédent après une erreur ou un arrêt du processus.

## Fonctionnement sur ce PC

L’installation Hermes personnelle reste distincte. Fred utilise les sources installées au commit `1cb26bf248e150f715ce8a487fdef2a2bef6b541`, leur runtime préparé et une racine de données dédiée. Deux ports privés sur `127.0.0.1` sont utilisés : 8643 pour la passerelle Hermes et 8768 pour le fournisseur Qwen et les outils Fred. Aucun client ne reçoit de clé Hermes et aucune de ces API n’est publiée directement.

La configuration locale `lanceur/hermes-integration.json` contient `{"enabled": true, "port": 8643, "private_port": 8768}`. Elle est sauvegardée avec les réglages Fred et reste exclue de Git. Le démarrage et les redémarrages du service sont supervisés sans arrêter Qwen. Les capacités natives requises sont vérifiées avant d’accepter le service. Une indisponibilité ne détourne pas silencieusement les conversations vers l’ancien parcours.

Quatre conversations Hermes au maximum peuvent avancer en parallèle, avec une seule demande active par accès. La file Fred réserve le GPU seulement pendant chaque appel au modèle. Les outils réseau ou documentaires ne le monopolisent pas. Les limites sont de 12 tours d’agent, 24 appels au fournisseur et 15 minutes par demande. Les clients montrent la progression des outils ; seule la réponse finale est rendue comme réponse et lue par la voix.

## Validation

La validation native se lance explicitement avec `Strata-src\.venv\Scripts\python.exe lanceur\validate_hermes_native.py`. Elle crée des comptes et projets synthétiques dans un dossier temporaire, utilise le Qwen déjà chargé et préserve les données de production. Elle vérifie de vrais appels MCP, la continuité de session, l’isolation entre comptes, les projets natifs et la création automatique d’un profil. Les preuves se trouvent dans `preuves/hermes-fred/`.

Les binaires signés sont distribués par les mécanismes Fred existants. Android peut télécharger la mise à jour depuis l’application ; la confirmation d’installation reste demandée par Android.
