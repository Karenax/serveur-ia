# Serveur IA

Projet privé de serveur Qwen local, avec un lanceur web, des clients Windows et Android (téléphone/tablette), et des mesures d'inférence sur deux Tesla P100.

## Plan et contexte du projet

Le [plan global](PLAN-GLOBAL-SERVEUR-FRED.md) découpe en lots les sauvegardes, la gestion des appareils, le tableau de bord, la recherche documentaire, la voix, les notifications et les outils de l’assistant. Le [contexte de reprise](CONTEXTE-PROJET.md) conserve les décisions, l’état actuel et les prochaines étapes. Les lots 0 à 4 sont implantés : sauvegardes quotidiennes côté serveur, restauration guidée et gestion des appareils. Consulter le [mode d’emploi](lanceur/SAUVEGARDES-APPAREILS.md) et les [preuves](preuves/lots-0-4/VALIDATION.md). Les **lots 6 et 8 sont également achevés et en service** : recherche avec passages cités et boîte de notifications persistante. Consulter leur [mode d’emploi](lanceur/RECHERCHE-NOTIFICATIONS.md) et les [preuves finales](preuves/lots-6-8/VALIDATION.md), dont 246 tests réussis. Versions publiées : serveur/Windows **3.5.27**, Android **1.0.10, code 11**. Le lot 7 comprend la dictée Windows/Android et la conversation vocale Windows ; la conversation Android reste différée. Hermes traite les conversations avec les outils Fred autorisés ; les trois actions du correcteur utilisent directement Qwen. Le tableau de bord complet du lot 5 et les extensions des lots 9/10 restent planifiés.

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

Les conversations Windows/Android et les tâches rédactionnelles sont intégrées à **Hermes** : profil créé automatiquement pour chaque accès, session par conversation et projet natif associé à chaque projet Fred. Les trois actions du correcteur utilisent directement Qwen, avec une consigne imposée côté serveur. Le Qwen local est partagé ; les recherches documentaires EG2 et outils web conservent les droits Fred. Coupures, annulation, sauvegarde et restauration sont raccordées. [Fonctionnement et limites](lanceur/HERMES-FRED.md), [preuves](preuves/hermes-fred/VALIDATION.md).

Windows **3.5.23** corrige l’arrêt de la conversation vocale pendant la synchronisation normale de l’historique ; la lecture et le microphone restent actifs, et le tour suivant attend la fin de l’enregistrement. [Validation](preuves/conversation-fix-20261011/VALIDATION.md).

Windows **3.5.26** et Android **1.0.9/code 10** corrigent le sélecteur de modèle par conversation : profil actif Hermes natif Windows, modèles indisponibles masqués et menu stable pendant les actualisations. La console **Clients → Modèles disponibles dans Hermes** permet de choisir les modèles proposés aux clients. Le partage des connexions reste activé pour tous les comptes Fred, avec quotas communs et données séparées. Qwen reste utilisable et le correcteur le conserve en direct. [Guide](lanceur/HERMES-FRED.md), [validation et publication](preuves/model-picker-fix-20261011/VALIDATION.md).

La console propose aussi des cases par fournisseur et **Tout désélectionner**, pour retirer notamment tous les modèles Nous Portal en une action. Le choix est enregistré côté serveur et appliqué aux deux clients ; Qwen local reste disponible. [Validation](preuves/provider-selector-20261011/VALIDATION.md).

Windows/serveur **3.5.27** et Android **1.0.10/code 11** règlent la réflexion selon les niveaux disponibles pour chaque modèle et gardent ce choix par modèle. Nemotron Ultra OpenRouter propose Sans/Moyen/Élevé ; Maximum apparaît seulement si la route l’accepte. Le serveur refuse les niveaux incompatibles et préserve les valeurs exactes. Les rafraîchissements de bibliothèque ne modifient plus le sélecteur utilisé. [Audit, tests et publication](preuves/reasoning-models-20261011/VALIDATION.md).
