# Conversations Fred avec Hermes

Les clients Windows 3.5.26 et Android 1.0.9/code 10 envoient leurs demandes à Fred. Le serveur confie chaque conversation à Hermes avec le modèle sélectionné et les outils autorisés. Le modèle Qwen local reste disponible ; les fournisseurs connectés dans Hermes sur le serveur peuvent être partagés entre les comptes Fred. Les tâches rédactionnelles gardent le modèle serveur par défaut. Les trois actions du correcteur — Corriger, Reformuler professionnel et Reformuler amical — utilisent directement Qwen.

Le correcteur utilise la route authentifiée `/v1/chat/completions` avec
`text_transform: {mode, text}`. Le serveur impose la consigne du mode choisi
et traite le texte comme une entrée à transformer. Ce parcours conserve les
autorisations Fred, la file du modèle et l’annulation ; il ne crée pas de session
Hermes et n’appelle pas ses outils. Les conversations ordinaires conservent
leurs sessions, leurs projets et les outils Hermes.

## Comptes et projets

La création d’un accès Fred crée automatiquement le profil natif `fred-<identifiant>` dans `lanceur/hermes-fred/profiles/`. Les clés restent sur le serveur, protégées par DPAPI et les droits Windows. Une création incomplète est affichée dans la console et peut être reprise sur la même fiche ; le profil conserve son identité et aucun paquet client utilisable n’est distribué avant sa disponibilité.

Chaque projet Fred possède un projet natif Hermes dans le profil du compte. Le nom, les consignes et l’archivage sont synchronisés ; le renommage conserve l’identité native. Le dossier `workspace/projects/<identifiant-projet>/` contient un catalogue des documents. Leur contenu demeure dans l’espace Fred et est lu par MCP avec les droits du compte et du projet. L’association d’une session à son projet passe par les API officielles Hermes et son dossier de travail, sans changer le projet actif de toutes les conversations.

Chaque conversation utilise une session indépendante. Une continuation conserve les appels d’outils et leur résultat. Un changement de modèle, de projet, une modification de l’historique ou une restauration ouvre une nouvelle session avec l’historique visible accepté.

## Choix du modèle et abonnements

Le sélecteur de Windows et Android affiche les modèles utilisables du profil actif Hermes pour les accès autorisés. Sous Windows, ce profil est résolu dans le dossier natif `%LOCALAPPDATA%\hermes`. Les modèles indisponibles et ceux dont le contexte annoncé est inférieur à 64 000 tokens sont masqués, car cette version de Hermes les refuse. Le choix est conservé avec chaque conversation dans l’historique chiffré et synchronisé. Une disparition du modèle ou une perte d’accès bloque les nouveaux messages jusqu’à un autre choix explicite ; aucun modèle de secours n’est substitué. La conversation vocale utilise le même choix. Les actualisations conservent les options existantes et attendent la fin de la sélection pour appliquer les changements du catalogue.

Dans **Clients → Modèles disponibles dans Hermes**, la console affiche le profil actif, son modèle courant et les modèles utilisables. Elle permet de les proposer tous automatiquement ou de sélectionner ceux affichés dans les clients, avec recherche et liste défilante. Qwen local reste proposé. Retirer un modèle de cette liste retire aussi son autorisation côté serveur ; les modèles temporairement hors ligne restent dans la sélection enregistrée et reviennent quand leur connexion est rétablie. Le bouton **Actualiser les modèles** redécouvre le catalogue natif immédiatement.

Les cases **Fournisseurs proposés aux clients** sélectionnent ou retirent tout un groupe en une seule action : décocher **Nous Portal** retire ses modèles utilisables, en conservant les autres choix. Un état intermédiaire signale un fournisseur partiellement sélectionné. Le bouton **Tout désélectionner** retire tous les modèles externes, y compris les choix enregistrés temporairement hors ligne ; Qwen local reste proposé. Ces actions passent en sélection manuelle et enregistrent immédiatement le résultat. La recherche dans la liste ne limite pas leur portée. Pour inclure automatiquement les nouveaux modèles, réactivez **Proposer tous les modèles utilisables de Hermes**.

La console permet aussi le partage global ou l’autorisation compte par compte. Le partage global vaut pour les nouveaux comptes. Une connexion du serveur partagée utilise le même abonnement, les mêmes crédits et les mêmes limites pour tous ces comptes ; les données des profils Fred restent séparées. Une connexion dans un navigateur ou une autre application du PC n’est pas en soi un accès Hermes.

Les clients reçoivent des identifiants de modèles et des capacités publiques, jamais des clés ou des jetons du fournisseur. Le serveur contrôle le modèle et les droits à chaque envoi. Les connexions externes sont résolues et rafraîchies dans le magasin Hermes central ; les jetons de renouvellement ne sont pas dupliqués entre profils. Les demandes cloud ne dépendent pas du chargement du Qwen local. Leur jauge de contexte est une estimation explicite de l’historique visible, sans appel facturé de comptage ; une capacité inconnue n’est pas inventée.

La politique sans secrets `hermes-models.json` est incluse dans les sauvegardes chiffrées. Sur un autre PC, les connexions aux fournisseurs doivent être rétablies dans Hermes : les abonnements personnels du PC source ne sont pas copiés par une sauvegarde Fred.

## Outils et mémoire

Hermes dispose des recherches documentaires Fred, de la mémoire sémantique EG2, de la lecture des passages cités, du calcul arithmétique borné et de la recherche/lecture web selon les autorisations Fred. Ses souvenirs, compétences et listes de tâches sont propres au profil. La recherche native dans toutes les sessions est désactivée : les recherches Fred appliquent le périmètre du projet.

Les outils système Hermes qui exécutent du code, manipulent librement les fichiers hôte ou contrôlent un navigateur ne sont pas activés. Leur ouverture nécessite un environnement d’exécution réellement isolé par compte. Les autorisations ponctuelles transportées par les clients sont limitées à « une fois » et « refuser » et ne constituent pas un droit général sur le serveur.

L’installation automatique de dépendances et les commandes intégrées aux compétences sont également désactivées. Les conversations utilisent le runtime installé sans le modifier.

Le contenu des documents et des pages web est transmis comme données non fiables. Les outils imposent le compte et le périmètre côté serveur, vérifient les droits avant et après l’appel et refusent les URL privées ainsi que les expressions qui exécuteraient du code.

## Coupures et sauvegardes

Chaque envoi possède une identité durable. La coupure du transport laisse l’agent terminer : le client retrouve le résultat accepté à la reconnexion sans répéter ses outils. Une annulation, suspension, révocation ou expiration arrête la demande. Une demande interrompue par l’arrêt du serveur n’est pas rejouée automatiquement.

Les sauvegardes chiffrées Fred incluent le registre d’association, les sessions, souvenirs, compétences, projets et dossiers de travail Hermes. Une sauvegarde attend la fin des conversations, puis arrête brièvement la passerelle Hermes pour produire un instantané cohérent. Les secrets portables sont protégés par l’enveloppe chiffrée de la sauvegarde et rechiffrés avec DPAPI à la restauration. Les clés runtime, journaux, dépendances partagées et tâches cron natives sont exclus. Le journal de restauration couvre également la racine Hermes pour revenir à l’état précédent après une erreur ou un arrêt du processus.

## Fonctionnement sur ce PC

Les sessions, projets et mémoires Hermes de Fred restent dans une racine dédiée. Les accès fournisseurs de l’installation Hermes du PC sont utilisés uniquement suivant la politique de partage. Fred utilise les sources installées au commit `1cb26bf248e150f715ce8a487fdef2a2bef6b541` et leur runtime préparé. Deux ports privés sur `127.0.0.1` sont utilisés : 8643 pour la passerelle Hermes et 8768 pour le fournisseur Qwen, les outils Fred et la résolution des accès fournisseurs. Aucun client ne reçoit de clé Hermes et aucune de ces API n’est publiée directement.

La configuration locale `lanceur/hermes-integration.json` contient `{"enabled": true, "port": 8643, "private_port": 8768}`. Elle est sauvegardée avec les réglages Fred et reste exclue de Git. Le démarrage et les redémarrages du service sont supervisés sans arrêter Qwen. Les capacités natives requises sont vérifiées avant d’accepter le service. Une indisponibilité ne détourne pas silencieusement les conversations vers l’ancien parcours.

Quatre conversations Hermes au maximum peuvent avancer en parallèle, avec une seule demande active par accès. La file Fred réserve le GPU seulement pendant les appels à Qwen local. Les outils réseau ou documentaires et les fournisseurs externes ne le monopolisent pas. La limite est de 12 tours d’agent et 15 minutes par demande, avec un maximum de 24 appels au fournisseur Qwen privé. Les appels externes consomment les quotas de la connexion Hermes partagée. Les clients montrent la progression des outils ; seule la réponse finale est rendue comme réponse et lue par la voix.

## Validation

La validation native se lance explicitement avec `Strata-src\.venv\Scripts\python.exe lanceur\validate_hermes_native.py`. Elle crée des comptes et projets synthétiques dans un dossier temporaire, utilise le Qwen déjà chargé et préserve les données de production. Elle vérifie de vrais appels MCP, la continuité de session, l’isolation entre comptes, les projets natifs et la création automatique d’un profil. Les preuves se trouvent dans `preuves/hermes-fred/`.

Les binaires signés sont distribués par les mécanismes Fred existants. Android peut télécharger la mise à jour depuis l’application ; la confirmation d’installation reste demandée par Android.
