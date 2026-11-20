# Compatibilités et conditions de retrait

Référence de travail du 18 novembre 2026. Les versions ci-dessous décrivent les livraisons documentées ; elles ne prouvent pas que chaque appareil a été mis à jour. Les changements de l’audit restent en recette tant qu’une nouvelle distribution n’a pas été qualifiée et activée. Voir [architecture](../ARCHITECTURE-ACTUELLE.md), [bascule et retour](../audits/2026-11-15-fusion-kiara/BASCULE.md) et [reconstruction](../RECONSTRUIRE-FRED.md).

| Compatibilité | Responsable dans le dépôt | Utilité et preuve connue | Conditions à réunir avant retrait |
|---|---|---|---|
| Client classique Windows 3.5.63 → Kiara 4 | `client-qwen/`, `client-tauri/`, `lanceur/releases.py` | Transition documentée dans `client-tauri/README.md` ; profil et brouillons sont repris par le relais. | Inventorier les postes encore sur le client classique et vérifier leur migration ainsi que la conservation de leurs brouillons. |
| Client Windows Kiara 4 | `client-tauri/`, relais et canal Windows | La version active du canal figure dans [le catalogue des versions](../lanceur/releases.py). Le paquet Tauri Linux 4.0.12 reste en recette. | Vérifier l’installation et la mise à jour depuis un profil fictif, ainsi que la conservation des données et des clés. |
| Android 1.0.26/code 27 | `client-android/`, sources partagées `client-qwen/` | APK publié le 11 novembre ; les sources ont évolué. Un paquet d’assets à jour ne constitue pas une livraison APK. | Construire et qualifier séparément mise à jour, profil, historique, voix et appareils réels ; établir la version de remplacement et les appareils migrés. |
| Linux historique | `client-linux/`, sources partagées `client-qwen/` | L’architecture documente 3.5.62 ; la qualification Linux reste séparée. | Identifier les installations et leurs versions, puis qualifier le remplaçant sur les architectures réellement utilisées. |
| Préfixe web `/agent/` | `lanceur/agent_web.py`, `agent_gateway.py`, routes client | `/kiara/` et `/agent/` partagent la session sur la passerelle ; les anciens liens documents continuent à fonctionner. | Inventorier et migrer liens et clients, vérifier téléchargements et autorisations, mettre à jour la documentation ; conserver le préfixe durant la fenêtre de retour. |
| Routes console `/api/agent-service` | `lanceur/app.py`, scripts d’exploitation | Alias des routes `/api/project-service`, avec les mêmes contrôles ; utilisé par les outils et lanceurs antérieurs. | Rechercher les appelants suivis et les scripts opérateurs externes ; migrer et tester permissions, erreurs et retour du lanceur. |
| `agent-service.json` et variables `KIARA_AGENT_*` | `lanceur/agent_service.py` | Fallback historique ; `project-service.json` et `KIARA_PROJECT_*` ont priorité. | Inventorier les installations, copier et vérifier chaque valeur et secret sans les afficher ; répéter activation et retour sur une copie isolée avant retrait. |
| Identifiants de commandes historiques | `lanceur/command_journal.py`, adaptateurs et clients | Le serveur négocie le format v2 ; les identifiants opaques restent reconnus avec une réserve bornée. | Vérifier les clients et reçus encore dépendants, sauvegarder et répéter la migration ; ne pas purger les reçus opaques à l’aveugle. |
| Bases Workspace / ERP / Brain et archives anciennes | modules de migration et restauration de chaque domaine | Autorités distinctes ; les versions de sauvegarde historiques sont explicitement reconnues. | Répéter la restauration et le retour sur copies, comparer les objets et droits, garder les archives et clés nécessaires. Une compatibilité ne se retire pas par simple renommage. |

## Relevé pour le retrait de la barre classique

- Le registre du compte Windows courant signalait Kiara 4.0.16 avant la bascule. La tâche `Kiara - ouverture de session` lance PowerShell et son action ne contient aucune des anciennes URL recensées.
- Les nouveaux liens utilisent `/app/projets`, `/app/meetings`, `/app/mail` et `/app/settings?settings=preparation`. Les signets historiques sont reconnus à l’entrée. Le préfixe privé historique et le repli du script de démarrage vers `/api/agent-service` et les clients déjà distribués justifient de conserver les entrées compatibles.
- Le relevé couvre le dépôt et le compte Windows courant. Les installations des autres postes, les signets personnels et les automatisations hors dépôt restent à recenser avant une suppression de canal ou de redirection.

## Avant de ranger les scripts historiques

L’[inventaire des scripts suivis à la racine](../audits/2026-11-16-architecture-interface/INVENTAIRE-SCRIPTS.md) relève les références littérales connues dans le dépôt et un examen local partiel des tâches, raccourcis, processus et chemins calculés. Il ne couvre pas tous les appelants externes ni tous les chemins construits dynamiquement.

1. Distinguer sources actives, générateurs, lanceurs, fichiers de configuration, preuves et archives ; inventorier références suivies **et** raccourcis, tâches Windows et procédures externes.
2. Répéter chaque déplacement dans une copie isolée, vérifier les chemins et le retour ; garder un lien ou une redirection documentée lorsqu’un appelant subsiste.
3. Ne déplacer ni supprimer les données, clés, modèles, sauvegardes ou preuves au titre du rangement du code. Aucune date ni suppression automatique n’est fixée par cette matrice.

Les noms internes `agent` et `minipilot` ne sont pas une raison suffisante pour renommer les bases, modules ou chemins de données. Le retrait reste une intervention distincte, appuyée par l’inventaire réel et les tests ci-dessus.
