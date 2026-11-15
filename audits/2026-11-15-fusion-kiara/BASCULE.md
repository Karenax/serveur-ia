# Bascule de Kiara et retour arrière

La première mise en service porte sur les écrans et le routage. Conversations conserve les API et les identifiants des fils existants. Le catalogue de recette laisse les projets et leurs objets dans leurs bases propriétaires. Une migration des données, si elle s’avère nécessaire, fera l’objet de sa propre répétition et de son propre point de reprise.

Sur cette machine, utiliser D: pour les compilations, les caches et les restaurations de recette. E: sert à conserver les archives. Une répétition peut lire une archive sur E: et doit déposer ses fichiers temporaires et ses bases restaurées sur D:.

## Préparer le poste pilote

1. Identifier le commit et les dépendances du serveur, du portail et de chaque client distribué. Construire le paquet serveur avec le nouveau bundle du portail. Relever la version, l’empreinte et l’emplacement de chaque paquet candidat et de la version précédente. Vérifier les signatures des installateurs utilisés en déploiement.
2. Constituer un point de reprise cohérent avec le mécanisme de sauvegarde du lanceur. Relever l’identifiant de l’archive, les empreintes validées et l’heure en UTC. Contrôler la copie hors machine et restaurer en environnement isolé. Vérifier l’ouverture des bases, l’accès aux objets liés et les téléchargements d’originaux. Garder l’accès aux secrets via le mécanisme de restauration prévu pour la machine.
3. Répéter le contrôle du catalogue à partir des trois bases isolées. Comparer les identifiants et les liens de projet, et traiter tout historique orphelin ou changement de propriétaire avant la mise en service.
4. Choisir un poste pilote et des accès de test avec des périmètres distincts. Consigner la version cliente initiale, les raccourcis publiés et les réglages de connexion à rétablir si nécessaire.

Le volet de projet a été retiré du portail candidat. Le nouveau lien utilise la capacité annoncée par le portail ou le relais. Pour les postes de bureau, déployer d’abord un relais qui annonce Conversations avec l’assistant de projet, puis activer le bundle du portail candidat. Pour rétablir le volet, restaurer le bundle précédent en même temps que le paquet serveur correspondant.

Depuis la racine du dépôt et avec le Python de construction du projet, les commandes suivantes préparent le paquet et vérifient le catalogue sur la restauration. Les variables désignent des chemins absolus vers le bundle validé, les trois bases restaurées et des répertoires de recette.

```powershell
& $Python maintenance/package_server.py --output $Paquets --web-dist $BundleWeb
& $Python maintenance/rehearse_project_migration.py --workspace $BaseEspaces --erp $BaseProjets --brain $BaseConnaissances --output $CatalogueRecette
```

## Activer et observer

1. Mettre en place le paquet serveur validé et vérifier l’état du lanceur et des services. Contrôler la session HTTPS du portail, le relais natif et les liens déjà publiés. Rendre le client candidat accessible au pilote et conserver le paquet précédent à portée de main.
2. Sur le pilote, ouvrir les cinq rubriques principales. Depuis une fiche, ouvrir le composeur sur le projet courant. Reprendre un fil existant, enregistrer une suite et rouvrir le brouillon après relance. Exécuter un échange éphémère et vérifier qu’aucune écriture de fil n’en découle. Interrompre une réponse, la relancer et simuler une révision concurrente. Contrôler une citation et l’empreinte de l’original téléchargé. Répéter les refus avec un accès hors périmètre.
3. Suspendre l’élargissement si un accès dépasse son périmètre, si un brouillon ou un fil disparaît, si un échange éphémère est enregistré ou si le retour arrière ne peut plus être exécuté. Noter le parcours, le client, les versions et l’heure. Les guides d’exploitation et les anciens liens restent disponibles durant le pilote.

## Revenir en arrière

### Retour sur la version précédente

1. Stopper le déploiement et faire fermer le client pilote après enregistrement des brouillons. Exporter les conversations utiles si un client les indique comme non synchronisées.
2. Rétablir le paquet serveur, son bundle web et sa configuration issus du même inventaire. Remettre la version précédente du client pilote suivant sa procédure de retour. Garder les bases actuelles tant que la compatibilité de lecture et d’écriture est démontrée.
3. Confirmer la connexion, le périmètre des accès, le fil créé pendant le pilote et l’ouverture des projets. Reprendre le service après ces contrôles.

### Restauration des données si nécessaire

1. Geler les écritures et établir un inventaire des opérations intervenues depuis le point de reprise. Faire une copie de l’état incident complet pour permettre leur récupération. Contrôler que les écritures à préserver disposent d’un export ou d’une procédure de rejeu vérifiée.
2. Restaurer l’ensemble cohérent dans un emplacement isolé. Comparer les bases, les accès, les liens, les révisions et les empreintes avec l’inventaire du point de reprise. Tester le rejeu sur cette restauration.
3. Réouvrir les écritures après confirmation de l’intégrité et de la récupération des opérations à préserver. Tant que leur récupération reste indémontrée, garder l’état incident en lecture seule et différer la reprise.

Pour une sauvegarde appairée, partir de l’archive principale `.qwenbackup` et vérifier l’empreinte du fichier `.kiara-agent` associé. Restaurer le lanceur et les espaces personnels, puis utiliser la restauration des Projets vers un dossier isolé pour le fichier associé. Vérifier les trois bases et les originaux avant de rattacher les données et de rouvrir les accès.

## Répétition du portail

Le bundle précédent est conservé dans `E:\Kiara-Integration\Build\fusion-kiara\reference-portail-avant-retrait` avec les empreintes de ses fichiers. Cette référence couvre le portail web.

Le test `test_portal_rollback_preserves_writes_and_project_scopes` sert successivement le portail précédent, le candidat, puis le précédent et le candidat à nouveau. Il utilise le véritable stockage SQLite de recette. Il compare le HTML et le JavaScript servis à chaque phase, crée un fil sur le candidat, le relit et le prolonge après retour arrière, puis vérifie la suite sur le candidat. Un compte limité à un autre projet reçoit un refus. Le test est passé avec les deux bundles de recette.

Les deux ZIP serveur ont aussi été extraits et leur service métier lancé dans quatre processus distincts avec les mêmes bases de recette. Le rapport `E:\Kiara-Integration\Build\fusion-kiara\recette-retour-paquets.json` consigne les empreintes et les écritures relues après chaque redémarrage. Le script utilise le Python du service métier et crée lui-même les bases fictives.

```powershell
& $PythonMetier maintenance/rehearse_portal_packages.py --previous $PaquetPrecedent --candidate $PaquetCandidat --report $RapportRecette
```

La suite isolée du lanceur a passé 62 tests de sauvegarde, de restauration et de reprise après interruption. Le contrôle de volume a restauré huit originaux totalisant 16 Mio avec des empreintes identiques. La répétition sur une paire d’archives du serveur réel et le contrôle des opérateurs de production restent à qualifier.

## Pilote Windows

Le rapport `E:\Kiara-Integration\Build\fusion-kiara\recette-pilote-natif.json` identifie par empreinte le relais précédent et le relais candidat. La recette lance Kiara avec son hôte Tauri et WebView2, quatre fois, sur un même profil fictif et un stockage DPAPI isolé. L’ordre est précédent, candidat, retour au précédent, puis candidat. Le tunnel WireGuard de recette est renouvelé entre les phases. Les deux brouillons et le fil enregistré pendant le pilote sont retrouvés après retour et après réactivation. Les deux demandes de réponse ont produit une seule écriture de fil, celle de l’échange enregistré.

Cette répétition échange le relais sous un même hôte Windows. La mise à niveau et le retour par l’installateur signé restent à qualifier sur un poste pilote.

## Paquets Linux

Les archives Linux candidates pour amd64 et arm64 sont dans `E:\Kiara-Integration\Build\fusion-kiara\candidat-linux`. Les empreintes des 80 fichiers de chaque archive, la présence du composeur commun et l’architecture du relais ELF ont été contrôlées. Le démarrage avec un WebView sur un poste Linux reste à tester.
