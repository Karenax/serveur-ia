# Recherche documentaire et notifications

Les lots 6 et 8 ajoutent la consultation des passages utilisés par Fred et une boîte de notifications conservée sur le serveur. Les clients Windows, Android téléphone et tablette utilisent les mêmes documents, résultats et préférences pour leur accès personnel.

## Retrouver et vérifier un passage

1. Ouvrir **Projets**, sélectionner un projet puis développer **Rechercher un passage dans les documents**.
2. Saisir une question ou quelques mots précis et cliquer sur **Chercher**.
3. Cliquer sur **Ouvrir le passage cité**. La fenêtre montre le texte exact, la révision et, pour un PDF lorsque l’extraction la fournit, la page réelle.

Les sources affichées avec une réponse ou un résultat de tâche disposent du même bouton. Le serveur conserve l’extrait et la révision utilisés : si le document a changé, la fenêtre le signale et propose son document actuel. S’il a été supprimé, l’extrait cité reste consultable avec la mention **indisponible**. Une note texte n’a pas de numéro de page inventé. Une ancienne référence dépourvue de version vérifiable est identifiée comme telle.

L’état d’indexation et le nombre de passages sont indiqués à la consultation du document. La recherche respecte le propriétaire et le projet. Si aucun passage ne correspond à une question précise, Fred le signale. Les TXT, Markdown, DOCX et PDF contenant du texte restent pris en charge dans les limites existantes : 2 Mo par fichier, 500 000 caractères de texte et 150 pages PDF. Les PDF scannés sans texte nécessitent une extraction OCR préalable ; ce lot n’ajoute pas de moteur OCR ni de recherche sémantique externe.

## Consulter les notifications

Dans le client, ouvrir **Notifications**. Les éléments annoncent une tâche terminée ou échouée, ou un document prêt pour la recherche. Une tâche interrompue par une panne est signalée et attend une relance manuelle ; chaque nouvelle tentative échouée reçoit sa propre notification. **Ouvrir** consulte le résultat correspondant après contrôle des droits ; **Marquer lu** et **Tout marquer lu** synchronisent la lecture avec le serveur. Les préférences permettent de choisir les types annoncés. Les éléments restent consultables même lorsque leur annonce est désactivée.

La boîte est stockée côté serveur et incluse dans les sauvegardes. À la reconnexion, le client récupère les éléments manqués sans les dupliquer. La conservation est limitée à 90 jours, 1 000 notifications par accès et 20 000 sur le serveur. Une restauration renouvelle la génération de synchronisation ; le client repart du bon curseur. Une révocation bloque les consultations et retire l’abonnement de l’appareil.

Sur Android, activer les notifications système depuis les réglages du client puis autoriser la demande Android. Un refus laisse la boîte utilisable dans l’application. Le réglage **Alertes discrètes** choisit des annonces silencieuses ; en le décochant, le canal standard peut émettre un son selon les réglages Android. Le texte système reste générique et privé dans les deux modes, sans extrait de document ni de conversation. Un rattrapage peut annoncer une seule fois le dernier résultat ; toute la liste reste disponible dans la boîte.

La livraison actuelle fonctionne lorsque le client est ouvert et connecté, puis par rattrapage à sa prochaine ouverture. Le réveil d’une application Android totalement arrêtée demanderait un sous-lot supplémentaire de push ou de service Android, décrit dans le plan global.

## Alertes dans la console d’administration

La rubrique **Notifications** de la console est réservée aux alertes d’exploitation : échec de sauvegarde, seconde copie en erreur, manque d’espace détecté lors d’une sauvegarde ou échec de restauration. Elle propose la lecture et les préférences par type. Les notifications personnelles des clients restent dans leurs boîtes respectives.

Le journal nécessaire à ces événements est intégré au stockage existant. La refonte complète du tableau de bord du lot 5 reste planifiée. La transcription prête est un type prévu pour le futur lot 7 ; ce lot ne crée pas de fonction vocale.

## Ce que permettra le lot 9

Le lot 9 permettra à Fred de proposer une action précise, puis de l’exécuter après validation. Par exemple : « Mets le budget à 2 500 € » afficherait le document concerné et la modification proposée. Le clic sur **Valider la modification** autoriserait cette seule modification. Si le document a changé entre-temps, Fred devrait préparer une nouvelle proposition. Ce lot reste planifié.

## Vérifications et exploitation

Le [rapport de validation](../preuves/lots-6-8/VALIDATION.md) rassemble les essais serveur, interfaces, transport WireGuard, clients compilés et état de mise en service. Le [plan global](../PLAN-GLOBAL-SERVEUR-FRED.md) et le [contexte](../CONTEXTE-PROJET.md) conservent les décisions et limites de cette livraison.
