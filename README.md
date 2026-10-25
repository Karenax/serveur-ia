# Serveur IA

L’application et l’assistante s’appellent **Kiara**. Les noms des EXE clients sont
conservés. Le [rapport du renommage](maintenance/2026-10-24-kiara/README.md) décrit
les compatibilités conservées et les paquets reconstruits.

Le 22 octobre 2026, [Phonon français remplace Pocket TTS côté serveur](maintenance/2026-10-22-phonon/README.md), sans mise à jour du client : streaming CPU, interruption et reprise validés, Qwen conservé.

Projet privé de serveur Qwen local, avec un lanceur web, des clients Windows et Android (téléphone/tablette), et des mesures d'inférence sur deux Tesla P100.

## Plan et contexte du projet

Le [plan d’intégration de l’assistant Kiara](PLAN-INTEGRATION-ASSISTANT-KIARA.md)
organise les améliorations : mémoire en conversation, actions vocales,
rappels, bilans de projet, activation mains libres et images pendant le vocal.
Il précise les dépendances, les critères de validation et les limites matérielles ;
une première version est publiée en **serveur/Windows 3.5.52 et Android
1.0.23/code 24**. Le [rapport d’intégration](maintenance/2026-10-25-assistant-integration/README.md)
décrit leur utilisation, les vérifications et les essais matériels restants.
Le [guide de l’assistant](GUIDE-ASSISTANT-KIARA.md) explique les six parcours
depuis Windows et Android.
L’attente de « Bonjour Kiara » reste expérimentale et limitée à l’application
visible ; les alertes Android hors application sont facultatives et non exactes.

Le [plan global](PLAN-GLOBAL-SERVEUR-FRED.md) découpe en lots les sauvegardes, la gestion des appareils, le tableau de bord, la recherche documentaire, la voix, les notifications et les outils de l’assistant. Le [contexte de reprise](CONTEXTE-PROJET.md) conserve les décisions, l’état actuel et les prochaines étapes. Les lots 0 à 4 sont implantés : sauvegardes quotidiennes côté serveur, restauration guidée et gestion des appareils. Consulter le [mode d’emploi](lanceur/SAUVEGARDES-APPAREILS.md) et les [preuves](preuves/lots-0-4/VALIDATION.md). Les **lots 6 et 8 sont également achevés et en service** : recherche avec passages cités et boîte de notifications persistante. Consulter leur [mode d’emploi](lanceur/RECHERCHE-NOTIFICATIONS.md) et les [preuves finales](preuves/lots-6-8/VALIDATION.md), dont 246 tests réussis. Versions de cette livraison historique : serveur/Windows **3.5.34**, Android **1.0.13, code 14**. Le [correctif du 14 octobre](maintenance/2026-10-14-opencode/README.md) rétablit l’affichage du modèle ajouté dans OpenCode 2. Le lot 7 comprend désormais la dictée et la conversation Windows/Android ; les essais physiques restants sont décrits dans les guides actuels. Hermes traite les conversations avec les outils Kiara autorisés ; les trois actions du correcteur utilisent directement Qwen. Le tableau de bord complet du lot 5 et les extensions des lots 9/10 restent planifiés.

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

Sur le PC serveur, le [chat Strata](http://127.0.0.1:8080/) permet de discuter directement avec Qwen local ; la [console Kiara](http://127.0.0.1:8765/) propose aussi **Ouvrir le chat**. Ces interfaces écoutent sur `127.0.0.1`. Le PC est configuré en IP fixe **192.168.1.41/24**, DHCP IPv4 désactivé, passerelle et DNS `192.168.1.1`. WireGuard utilise le port UDP **51820** ; les profils corrigés privilégient `192.168.1.41:51820` sur le réseau local. [Configuration et vérification](maintenance/2026-10-13-ip-fixe/README.md).

Le moteur actuel est Strata officiel **0.1.45.3**, installé dans `dependances/strata-0.1.45.3/engine-cuda12`, avec le **serveur Python 0.1.43.1 corrigé et l’encodeur P2200 conservés** dans `dependances/strata-0.1.43.1`. Ne pas supprimer ce dernier dossier. Les réglages et la preuve de mise en service sont dans [le dossier de maintenance du 19 octobre](maintenance/2026-10-19-strata-0.1.45.3/README.md). L’ancien moteur personnalisé et ses références restent conservés.

Les moteurs Strata et llama.cpp restent des dépôts distincts. Leurs sources, outils CUDA et environnements Python doivent être installés séparément. Les références et patchs enregistrés dans `dependances/` permettent de retrouver les versions et modifications locales.

## Périmètre de sauvegarde Git

Ce dépôt conserve les sources du projet, les scripts, configurations de modèle, protocoles et résultats textuels. Les poids des modèles, logiciels téléchargés, binaires compilés et journaux de fonctionnement sont exclus.

Les comptes, clés et paramètres d'accès WireGuard, fichiers chiffrés DPAPI, bases de données et historiques de conversations restent sur le poste. Leur sauvegarde doit être organisée séparément ; ils ne sont pas inclus dans ce dépôt privé.

Les performances consignées correspondent aux versions et au matériel indiqués dans chaque rapport. Elles ne constituent pas une garantie pour d'autres configurations.

La dictée et la conversation sont disponibles sur Windows et Android. Low utilise
Parakeet sur Windows, Whisper Small sur Android et la voix française Phonon du
serveur. Le complément Windows Max utilise Whisper Turbo Q5 sur le GPU choisi et
Phonon français Q8 sur CPU. Voir le [guide vocal](client-voice/README.md),
le [guide Windows](client-voice/CONVERSATION-WINDOWS.md) et les
[mesures du 25 octobre](maintenance/2026-10-25-vocal-realtime/README.md).
Les [preuves Small](preuves/voix-small-20261011/VALIDATION.md) et
[preuves de la première conversation Windows](preuves/conversation-windows-20261011/VALIDATION.md)
décrivent les anciennes livraisons et leurs moteurs de l’époque.

La mémoire sémantique **EmbeddingGemma 2** est installée et activée sur le serveur : moteur CPU indépendant de Qwen/Strata, base de connaissances par projet et base hors projet séparées par accès. Les conversations synchronisées sont indexées automatiquement. [Utilisation et limites](lanceur/MEMOIRE-EG2.md), [validation](preuves/eg2-20261011/VALIDATION.md).

Les données connues du serveur sont également regroupées dans un dossier privé par client, sous `lanceur/donnees-clients/<identifiant>/` : base individuelle, historiques, conversations, documents, souvenirs et configuration. Les chemins et dates de mise à jour sont affichés dans la console. [Organisation et fonctionnement](lanceur/DOSSIERS-CLIENTS.md).

Les conversations Windows/Android et les tâches rédactionnelles sont intégrées à **Hermes** : profil créé automatiquement pour chaque accès, session par conversation et projet natif associé à chaque projet Kiara. Les trois actions du correcteur utilisent directement Qwen, avec une consigne imposée côté serveur. Le Qwen local est partagé ; les recherches documentaires EG2 et outils web conservent les droits Kiara. La recherche web des conversations utilise les outils et connexions natifs Hermes du serveur. Coupures, annulation, sauvegarde et restauration sont raccordées. [Fonctionnement et limites](lanceur/HERMES-FRED.md), [preuves](preuves/hermes-fred/VALIDATION.md).

Windows **3.5.23** corrige l’arrêt de la conversation vocale pendant la synchronisation normale de l’historique ; la lecture et le microphone restent actifs, et le tour suivant attend la fin de l’enregistrement. [Validation](preuves/conversation-fix-20261011/VALIDATION.md).

Windows **3.5.26** et Android **1.0.9/code 10** corrigent le sélecteur de modèle par conversation : profil actif Hermes natif Windows, modèles indisponibles masqués et menu stable pendant les actualisations. La console **Clients → Modèles disponibles dans Hermes** permet de choisir les modèles proposés aux clients. Le partage des connexions reste activé pour tous les comptes Kiara, avec quotas communs et données séparées. Qwen reste utilisable et le correcteur le conserve en direct. [Guide](lanceur/HERMES-FRED.md), [validation et publication](preuves/model-picker-fix-20261011/VALIDATION.md).

La console propose aussi des cases par fournisseur et **Tout désélectionner**, pour retirer notamment tous les modèles Nous Portal en une action. Le choix est enregistré côté serveur et appliqué aux deux clients ; Qwen local reste disponible. [Validation](preuves/provider-selector-20261011/VALIDATION.md).

Windows/serveur **3.5.27** et Android **1.0.10/code 11** règlent la réflexion selon les niveaux disponibles pour chaque modèle et gardent ce choix par modèle. Nemotron Ultra OpenRouter propose Sans/Moyen/Élevé ; Maximum apparaît seulement si la route l’accepte. Le serveur refuse les niveaux incompatibles et préserve les valeurs exactes. Les rafraîchissements de bibliothèque ne modifient plus le sélecteur utilisé. [Audit, tests et publication](preuves/reasoning-models-20261011/VALIDATION.md).

Les sept défauts confirmés lors de l’audit du 12 octobre sont corrigés et publiés : historiques, exports clients, quotas et conservation Hermes, outils liés au tour, images et scripts. Les mesures montrent une réduction proche de 45 % du pic de mémoire sur le test de sauvegarde/restauration de 16 Mio. [Validation complète](audits/2026-10-12/VALIDATION-CORRECTIONS.md), [reconstruction et tests](RECONSTRUIRE-FRED.md), [index des archives](ARCHIVES-ET-PREUVES.md).

L’API des clients Windows et Android expose aussi [EmbeddingGemma 2](maintenance/2026-10-21-api-embeddings/README.md) pour les applications utilisant des embeddings compatibles OpenAI.
