# Sauvegardes et appareils — mode d’emploi

La console locale est disponible sur <http://127.0.0.1:8765>. Ces fonctions sont exécutées par le serveur et administrées dans les rubriques **Sauvegardes** et **Appareils**.

## Sauvegardes en service

Depuis le 10 octobre 2026, une sauvegarde chiffrée est programmée **chaque jour à 03 h**, heure du serveur, dans `D:\Serveur IA\lanceur\sauvegardes`. La conservation des points automatiques est de **7 jours, 4 semaines et 6 mois** : un même point peut satisfaire plusieurs catégories. Les points manuels sont conservés hors de ce nettoyage. Les points de retour de restauration et le dernier point vérifié sont protégés. La deuxième copie est disponible dans la console ; son emplacement reste vide selon le choix de l’utilisateur de commencer sur le serveur.

Une sauvegarde initiale a été créée et déchiffrée pour vérifier son contenu après la mise à jour. Le modèle déjà chargé a conservé les mêmes processus pendant cette opération. Le rapport `preuves/lots-0-4/production-validation.json` contient les dates, tailles et empreintes, sans les valeurs secrètes.

Le secret d’automatisation est protégé par Windows DPAPI, sous le compte qui exécute le serveur. La phrase permettant de restaurer sur une autre machine se trouve dans le fichier privé `D:\Serveur IA\lanceur\sauvegardes\phrase-recuperation.txt`. Conserver une copie indépendante de ce fichier et des archives pour pouvoir récupérer les données après perte du disque. Le dossier est accessible au compte Windows courant, aux administrateurs et au système ; il est exclu de Git.

Pour lancer un point supplémentaire, ouvrir **Sauvegardes**, puis **Sauvegarder maintenant**. Si la phrase n’est pas saisie, le serveur utilise le secret automatique déjà enregistré. Le catalogue présente la date, la taille, le contenu, l’empreinte et la vérification. Les paramètres de planification et de conservation se modifient dans la même rubrique.

Le processus de la console serveur doit fonctionner à l’échéance. Une échéance manquée est rattrapée au redémarrage, avec un seul travail. Le lancement actuel dépend de l’ouverture d’une session Windows. La sauvegarde ne nécessite ni navigateur ni client ouvert.

## Données couvertes

Les archives contiennent les conversations et préférences synchronisées, projets, documents et originaux, mémoire, tâches, quotas, comptes, réglages du serveur, configuration des accès, secrets WireGuard, profils personnels disponibles et clé de signature des mises à jour Windows. La programmation est incluse ; le secret DPAPI de la machine est conservé localement et la programmation est désactivée après restauration pour permettre sa vérification.

Les brouillons et réglages qui sont restés uniquement sur un client ne sont pas présents sur le serveur. Les modèles, caches, environnements de compilation, exécutables reconstructibles et sauvegardes sont exclus. Les clés de signature Android sont récupérables dans un paquet chiffré séparé ; voir `RECUPERATION-SIGNATURES.md`.

Les anciens fichiers `.qwenbackup` restent lisibles. Le format actuel chiffre et authentifie le contenu, puis vérifie l’archive par relecture avant publication de son succès. Le traitement se fait en mémoire avec des limites : stockage applicatif global de 128 Mio, restauration SQLite de 256 Mio, archive chiffrée de 400 Mio. L’essai de huit DOCX totalisant 16 Mio a mesuré un pic de mémoire de 398 Mio ; la consommation au volume maximal n’a pas été mesurée.

## Restaurer une archive

1. Dans **Sauvegardes**, sélectionner **Vérifier / restaurer** sur un point du catalogue, ou indiquer le chemin d’une archive présente sur le serveur.
2. Saisir sa phrase si elle diffère du secret automatique, puis lancer la vérification. Lire le contenu et les effets annoncés.
3. Confirmer la restauration. Les accès et écritures sont arrêtés, ainsi que le modèle ; un point de retour est créé avant de remplacer les données.
4. Attendre le résultat. Les tâches restaurées ne reprennent pas automatiquement. Vérifier les réglages, la programmation et les appareils avant de réactiver l’accès distant et de relancer le modèle dans la console.
5. Sur les clients Windows 3.5.17 et Android 1.0.1, confirmer **Reprendre l’historique du serveur**. Une copie chiffrée de l’historique local précédent est conservée avant sa reprise. Un ancien client reçoit un refus d’écriture explicite et doit être mis à jour.

Une interruption pendant le remplacement déclenche un retour à l’état précédent avant ouverture des clients au redémarrage. Si ce retour échoue lui aussi, le serveur garde les accès bloqués. Après correction du stockage, utiliser **Réessayer le retour à l’état précédent**. Les essais couvrent une coupure réelle du processus et ce parcours de réparation.

Une révocation reste valable après restauration d’une archive ancienne. Sur un serveur d’origine différente, les appareils restaurés sont suspendus jusqu’à validation. Les essais de restauration ont utilisé des installations isolées ; aucune restauration n’a remplacé les données de production pendant cette livraison.

## Gérer les appareils

Dans **Appareils**, créer un accès **Android** ou **Windows** et renseigner son nom, son type (PC, téléphone, tablette) et son propriétaire administratif. Chaque appareil possède une identité, une clé API et un pair WireGuard distincts. Les espaces existants sont conservés ; le champ propriétaire sert au classement et ne fusionne pas les données.

Pour Android, télécharger le **profil Android** `.fred-android` dans la fiche puis l’importer dans l’application. L’APK signé se trouve dans `client-android/dist/Acces-serveur-Fred-Android.apk`. Un EXE Windows personnel peut également être importé par Android. Les profils contiennent des accès privés ; les remettre seulement au destinataire de l’appareil.

La fiche affiche la version et le type déclarés par le client, la dernière activité authentifiée, la suspension et l’expiration. Les valeurs déclarées servent au suivi ; elles ne donnent aucun droit supplémentaire. Une dernière activité ne garantit pas que l’appareil est encore connecté.

- **Suspendre** coupe temporairement l’accès ; la réactivation conserve les clés et la date d’expiration.
- **Révoquer** ferme l’accès et ses travaux en cours, retire le pair WireGuard et conserve les données. Cette décision est durable.
- **Remplacer** révoque l’ancien accès et crée un nouvel accès. Les conversations et documents de l’ancien restent sur le serveur ; le nouvel appareil commence avec un espace distinct.
- **Archiver** retire l’appareil de la liste active, révoque son accès et conserve ses données.

Les essais vérifient également que la révocation d’un appareil laisse l’autre accès fonctionner et interrompt un flux de réponse déjà ouvert.

## Versions et preuves

Livraison serveur / Windows : **3.5.17**. Android : **1.0.1**, code 2, Android 8+, ARM64 et x86_64. Les deux formats d’écran ont été vérifiés sur émulateurs Android 16 x86_64 ; les appareils ARM64 physiques restent à vérifier.

Le rapport principal est `preuves/lots-0-4/VALIDATION.md`. Il relie les journaux, captures, mesures, tests de restauration et empreintes des fichiers livrés. Le plan global et le contexte de reprise sont conservés à la racine du projet.
