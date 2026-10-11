# Serveur IA

Projet privé de serveur Qwen local, avec un lanceur web, des clients Windows et Android (téléphone/tablette), et des mesures d'inférence sur deux Tesla P100.

## Plan et contexte du projet

Le [plan global](PLAN-GLOBAL-SERVEUR-FRED.md) découpe en lots les sauvegardes, la gestion des appareils, le tableau de bord, la recherche documentaire, la voix, les notifications et les outils de l’assistant. Le [contexte de reprise](CONTEXTE-PROJET.md) conserve les décisions, l’état actuel et les prochaines étapes. Les lots 0 à 4 sont implantés : sauvegardes quotidiennes côté serveur, restauration guidée et gestion des appareils. Consulter le [mode d’emploi](lanceur/SAUVEGARDES-APPAREILS.md) et les [preuves](preuves/lots-0-4/VALIDATION.md). Les **lots 6 et 8 sont également achevés et en service** : recherche avec passages cités et boîte de notifications persistante. Consulter leur [mode d’emploi](lanceur/RECHERCHE-NOTIFICATIONS.md) et les [preuves finales](preuves/lots-6-8/VALIDATION.md), dont 246 tests réussis. Versions actuelles : serveur/Windows **3.5.21**, Android **1.0.5, code 6**. Le lot 7 comprend la dictée Windows/Android et la conversation vocale Windows ; la conversation Android reste différée. Le tableau de bord complet du lot 5 et les lots 9 et 10 restent planifiés.

## Organisation

- `lanceur/` : pilotage du serveur, interface web, comptes, espaces de travail et accès distant.
- `client-qwen/` : client Windows, interface de conversation, historique et mises à jour.
- `client-android/` : client Android téléphone/tablette, APK signé, guide et validation.
- Les scripts `Start-*.ps1`, `Stop-*.ps1`, `Build-*.cmd` et les scripts Python à la racine servent au lancement, à la compilation et aux comparatifs.
- `analyses/`, `comparatifs/`, `recherche/` et les rapports à la racine conservent les protocoles et résultats.
- `contribution-strata-p100/` contient la proposition expérimentale soumise à Strata : https://github.com/Niko1221/Strata/pull/527.
- `dependances/` conserve les références des moteurs tiers et leurs adaptations locales sous forme de patchs.

## Utilisation locale

Le poste d'origine utilise Windows et le dossier `D:\Serveur IA`. Certains scripts et configurations contiennent les chemins de ce poste : les adapter avant une installation ailleurs.

`Serveur Qwen.cmd` lance `Start-Interface-Qwen.ps1`. Consulter `lanceur/LISEZ-MOI.txt`, `client-qwen/LISEZ-MOI.txt` et les rapports `RESULTATS-*.txt` pour les commandes et configurations mesurées. Les prérequis Python du lanceur et du client sont dans leurs fichiers `requirements*.txt`.

Les moteurs Strata et llama.cpp restent des dépôts distincts. Leurs sources, outils CUDA et environnements Python doivent être installés séparément. Les références et patchs enregistrés dans `dependances/` permettent de retrouver les versions et modifications locales.

## Périmètre de sauvegarde Git

Ce dépôt conserve les sources du projet, les scripts, configurations de modèle, protocoles et résultats textuels. Les poids des modèles, logiciels téléchargés, binaires compilés et journaux de fonctionnement sont exclus.

Les comptes, clés et paramètres d'accès WireGuard, fichiers chiffrés DPAPI, bases de données et historiques de conversations restent sur le poste. Leur sauvegarde doit être organisée séparément ; ils ne sont pas inclus dans ce dépôt privé.

Les performances consignées correspondent aux versions et au matériel indiqués dans chaque rapport. Elles ne constituent pas une garantie pour d'autres configurations.

La dictée locale Whisper Small est intégrée aux clients Windows et Android : [utilisation](client-voice/README.md), [preuves et mesures](preuves/voix-small-20261011/VALIDATION.md). Windows **3.5.21** ajoute la conversation : transcription locale progressive, envoi automatique après la fin du tour, voix française Pocket TTS sur le CPU serveur et interruption quand l’utilisateur reprend la parole. [Guide](client-voice/CONVERSATION-WINDOWS.md), [preuves](preuves/conversation-windows-20261011/VALIDATION.md). Android **1.0.5/code 6** conserve la dictée manuelle et ajoute le téléchargement automatique des mises à jour.

La mémoire sémantique **EmbeddingGemma 2** est installée et activée sur le serveur : moteur CPU indépendant de Qwen/Strata, base de connaissances par projet et base hors projet séparées par accès. Les conversations synchronisées sont indexées automatiquement. [Utilisation et limites](lanceur/MEMOIRE-EG2.md), [validation](preuves/eg2-20261011/VALIDATION.md).

Les données connues du serveur sont également regroupées dans un dossier privé par client, sous `lanceur/donnees-clients/<identifiant>/` : base individuelle, historiques, conversations, documents, souvenirs et configuration. Les chemins et dates de mise à jour sont affichés dans la console. [Organisation et fonctionnement](lanceur/DOSSIERS-CLIENTS.md).
