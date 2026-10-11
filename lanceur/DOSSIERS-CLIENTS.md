# Dossiers des clients sur le serveur

Chaque accès client possède un dossier privé et stable :

```text
D:\Serveur IA\lanceur\donnees-clients\<identifiant-client>\
├── client.json                 Fiche, nom et état de l’accès
├── configuration.json          Paramètres et limites connus du serveur
├── historique.json             Historique synchronisé, révision et sélection
├── conversations\             Conversations en fichiers JSON
├── projets\<id-projet>\
│   ├── projet.json              Instructions et état du projet
│   └── documents\<id-document>\
│       ├── document.json        Titre, type et version
│       ├── contenu.txt          Texte extrait
│       └── original.<extension> Fichier original, lorsqu’il existe
├── memoires.json                Souvenirs du projet et personnels
├── taches.json                  Tâches, consignes et résultats
├── notifications.json           Notifications et reçus
├── evenements.json              Événements de cet accès
├── references.json              Sources, index et exclusions
├── profil-connexion.dpapi       Profil personnel chiffré, s’il est disponible
├── donnees.sqlite3              Base individuelle complète
└── dossier.json                 Inventaire, empreintes et date de mise à jour
```

L’identifiant est celui de l’accès personnel, pas le nom d’affichage. Renommer « Alice » ne déplace donc pas son dossier. Un client archivé/révoqué conserve ses conversations, documents et dossier. Un nouvel accès possède un nouvel identifiant et un autre dossier.

## Emplacement dans la console

Dans [Clients](http://127.0.0.1:8765/#clients) et [Appareils](http://127.0.0.1:8765/#devices), chaque fiche indique **Dossier des données sur le serveur**, le chemin complet, la dernière mise à jour et le bouton **Copier le chemin**. Les fiches archivées conservent cette information.

Dans [Espaces et fichiers](http://127.0.0.1:8765/#spaces), le bloc **Dossiers des clients sur le serveur** affiche la racine, le dossier de l’accès sélectionné et le bouton **Mettre les dossiers à jour**.

## Fonctionnement du stockage

Les dossiers sont alimentés automatiquement à partir des données validées et enregistrées par le serveur. Les modifications de conversations, fichiers, souvenirs et autorisations déclenchent leur mise à jour ; un contrôle périodique assure aussi la reprise après interruption. Les fichiers générés sont écrits par remplacement atomique et leurs empreintes figurent dans le manifeste. La base individuelle est un instantané SQLite autonome et cohérent contenant uniquement les lignes de cet accès. Les autres fichiers permettent une consultation directe.

La base commune `lanceur\espaces-prives\espaces.sqlite3` reste la source transactionnelle utilisée par le backend, les tâches, EG2 et la sauvegarde globale. Les dossiers individuels sont des représentations synchronisées de cette base et des registres d’accès ; ils ne sont pas utilisés pour réinjecter automatiquement des modifications manuelles. Éditer un export ne modifie pas une conversation dans Fred : il sera rétabli à la prochaine synchronisation.

La configuration comprend les paramètres effectivement présents sur le serveur : identité, autorisations, durée de validité, informations d’appareil, quotas et préférences de notifications. Les réglages d’interface, brouillons et données restés uniquement sur l’appareil ne sont pas transmis par cette fonction. Les fichiers binaires des applications et les modèles restent dans leurs emplacements actuels.

## Droits, suppression et récupération

Les dossiers privés sont accessibles au compte Windows du serveur, au système et aux administrateurs. Les profils personnels sont protégés par DPAPI ; leurs jetons et clés privées ne sont pas écrits dans les fichiers JSON lisibles. Le chemin du dossier est exposé dans la console locale d’administration. Les noms d’affichage et titres de documents ne servent jamais à construire des chemins.

Un document supprimé est retiré des exports gérés. Les fichiers ajoutés manuellement par l’administrateur restent conservés. Les jonctions et liens sont refusés dans cette arborescence pour éviter une écriture hors du dossier du client. Si un fichier est absent, altéré ou verrouillé par un lecteur SQLite, le serveur conserve ses données originales et retente la synchronisation ; l’erreur est affichée dans la console.

La sauvegarde chiffrée habituelle contient déjà les données originales et configurations nécessaires. Elle évite de dupliquer ces exports et leurs modèles ; après restauration ou suppression d’un dossier généré, ils se reconstruisent depuis l’état serveur. DPAPI reste lié au compte Windows : les archives chiffrées portables demeurent le moyen de récupération sur une autre installation.

Les anciens dossiers d’identités absentes d’un registre restauré sont conservés sur disque, sans réactivation d’accès ni réimportation de leur contenu. Une restauration globale porte sur la base originale et les registres, pas sur les fichiers manuels des dossiers.

Preuves : [validation des dossiers clients](../preuves/dossiers-clients-20261011/VALIDATION.md).
