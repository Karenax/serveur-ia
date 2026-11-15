# Intégration d’Agent dans Serveur IA

11 novembre 2026 · Rapport de conception et de migration

Le [plan d’intégration à jour](2026-11-12-plan-integration-agent.md) suit l’état de production, les validations et les étapes restantes.

Mise à jour du 14 novembre 2026. La recherche multimodale locale LiteRT est
obsolète et retirée du périmètre de livraison. La recherche sémantique et les
citations de Kiara reposent sur EmbeddingGemma 2 via EG2 sur la P2200. Le texte
extrait des documents, de l’OCR et des transcriptions peut alimenter cet index.

## Décision proposée

Faire des projets d’Agent les projets de Kiara. Reprendre le cœur métier Python d’Agent, ses deux bases SQLite et son frontend React dans le dépôt actif `F:\Serveur IA`. Exécuter Agent comme service interne supervisé par Kiara. Distribuer le même frontend dans un EXE Windows Tauri 2 et dans une interface web privée. Kiara continue de gérer les accès, la console, les moteurs IA et les interfaces OpenAI compatibles.

La parité complète d’Agent est l’objectif de l’EXE. Le navigateur peut reprendre les opérations métier et leurs données. Les fonctions qui utilisent la machine de l’utilisateur, comme la capture du son système, l’ouverture d’un dossier et le lien Thunderbird, demandent un composant Windows ou un parcours web adapté.

Deux points conditionnent la bascule. Il manque deux originaux CDC référencés dans le dossier ERP de l’ancien PC. Le modèle d’accès d’Agent, conçu pour un poste mono-opérateur, doit être raccordé aux identités Kiara avant d’ouvrir les données métier sur le réseau.

## Sources et état des données

| Composant | État constaté |
| --- | --- |
| Agent | `D:\Agent`, branche `main` propre, commit `0c2e08a`. FastAPI `app/main.py` sert Brain, MiniPilot ERP et l’interface React 19, TypeScript et Vite. Le lanceur Agent utilise le port local 8001. |
| Kiara | `F:\Serveur IA`, branche `main` propre au début de l’étude, commit `756f9ce`. Architecture documentée pour 3.5.62. L’EXE actuel assemble Python, pywebview/WebView2 et le relais local. La passerelle utilise les accès par appareil et le pont Go WireGuard. |
| `minipilot.db` | 8 650 752 octets. 11 projets, 10 liens Brain, 10 fiches détaillées, 178 participations projet, 88 jalons, 3 sources CDC, 70 pages extraites, 305 éléments CDC et 287 ancrages de preuve. |
| `project_brain.db` | 53 600 256 octets. 11 projets Brain, 1 676 sources dont 1 675 mails, 6 416 artefacts, 5 532 propositions, 2 954 informations validées, 2 989 liens de provenance, 2 discussions enregistrées et 2 séances de réunion. |
| `storage.zip` | 1 406 819 387 octets compressés, 2 584 723 651 octets décompressés, 3 032 fichiers. Contient originaux EML, extractions de pièces jointes, OCR, fragments audio, index et fichiers d’exploitation. |

Les trois éléments sont dans `C:\Users\karen\Downloads`. Les deux bases principales renvoient `ok` à `integrity_check`, sans violation détectée par `foreign_key_check` ni WAL/SHM adjacent. Les migrations applicatives enregistrées vont jusqu’à ERP 11 et Brain 7. Le CRC de tous les fichiers du ZIP est valide. Les deux fichiers DB sont les bases canoniques. Les quatre bases contenues dans le ZIP sont des index dérivés.

Les dix liens `brain_links` pointent vers des projets présents dans les deux bases et leurs codes concordent. Il reste un projet ERP et un projet Brain sans lien, avec des codes différents. Conserver les deux. Le portefeuille part des 11 projets ERP et les fonctions Brain continuent de retrouver le projet Brain autonome selon les droits accordés. Un rattachement futur doit être explicite.

### Originaux et index

| Famille | Vérification | Conséquence pour la reprise |
| --- | --- | --- |
| Mails | 1 147 EML correspondent aux empreintes des sources résolues. Les 1 072 chemins gérés concordent avec le contenu et 75 autres originaux ont été retrouvés par SHA-256. Le ZIP contient 51 EML dont l’empreinte ne figure pas dans les sources. Les 528 sources de mail écartées ont leur trace en base, sans original correspondant dans le ZIP. | Rattacher les originaux vérifiés. Garder les fichiers surnuméraires hors index actif et conserver les décisions de rejet. La source documentaire issue d’une note suit son lien ERP. |
| Réunions | Les 98 fragments référencés correspondent en taille et SHA-256. La base contient une séance créée et une séance terminée, avec segments, événements et reçus. | Reloger les fragments, conserver leur historique, neutraliser les anciennes autorités de capture et tester la lecture. |
| CDC | Deux sources ont un chemin géré sous `.minipilot` et une empreinte. Aucune entrée du ZIP ne correspond à ces empreintes. La troisième source ne référence aucun binaire stocké. | Récupérer le sous-dossier `cdc` du `MINIPILOT_HOME` de l’ancien PC et vérifier les deux SHA-256. Sinon, conserver l’existant, signaler la réserve par source et prévoir la réimportation des originaux concernés. |
| Dossiers réseau | 29 entrées, dont 23 chemins avec lettre de lecteur et 1 UNC. | Remapper lecteurs et partages selon les postes et le compte de service. Tester les droits de lecture et de publication. |
| EG2 | Les trois index passent le contrôle SQLite. Celui configuré en base, `storage/eg2/kiara-compatible-20261104/index.db`, contient 37 546 passages à 768 dimensions sur 1 148 sources. Les 1 148 références SQL indexées correspondent au bon projet et à une source résolue. Les deux autres index contiennent 20 322 et 263 passages. | Reprendre l’index configuré après comparaison du profil et des recherches sur le moteur cible. Une incompatibilité du profil impose une reconstruction depuis les sources. |
| Multimodal LiteRT | Index historique de 4 997 entrées dans le ZIP. | Moteur obsolète. L’index dérivé est exclu du déploiement et des restaurations. |

La restauration native Agent attend un manifeste et le répertoire ERP. Les trois éléments fournis demandent un import contrôlé. Si l’ancien PC est disponible, récupérer une sauvegarde Agent coordonnée et vérifiée, ou à défaut les originaux CDC et les fichiers métier référencés hors `storage`. Vérifier également les fichiers réseau et les brouillons stockés dans le navigateur de l’ancien poste. Les clés protégées par DPAPI et les appairages demandent une reconfiguration. [Sauvegarde et reprise d’Agent](<D:/Agent/README_BACKEND.md>)

## Architecture cible

~~~mermaid
flowchart LR
  W["Navigateur HTTPS"] --> A["Accès privé Agent et identité Kiara"]
  T["EXE Tauri et interface React"] --> A
  T --> N["Fonctions du poste Windows"]
  A --> S["FastAPI Agent interne"]
  S --> E["ERP MiniPilot"]
  S --> B["Brain"]
  E --> D["Fichiers métier"]
  B --> D
  S --> K["Passerelle IA Kiara"]
  K --> Q["Qwen et EG2"]
~~~

### Service et identité

- Reprendre dans le dépôt Kiara les modules `app` et `backend`, le frontend, les scripts, extensions, tests, verrous de dépendances et notices. Garder les règles métier et migrations Agent. Installer un environnement Python 3.13 propre au service et un runtime audio séparé. Kiara supervise démarrage, santé, journaux, mises à jour et sauvegardes. Un seul service Agent écrit dans les bases. XPilot et le port 8000 restent hors du chantier.
- Servir l’interface sur une origine HTTPS privée dédiée, avec ses API sous la même origine. Agent utilise `/v1/*` pour Brain, `/api/v1/*` pour l’ERP et `/app/*` pour l’UI. Isoler ces chemins des API OpenAI compatibles et de la console. Préserver uploads, téléchargements, flux d’événements, streaming et annulation. Le relais desktop peut présenter les mêmes chemins relatifs à la WebView.
- Raccorder chaque requête à un utilisateur Kiara authentifié et, pour l’EXE, à un appareil valide. Aujourd’hui `/api/v1/session` fournit un jeton de session locale, tandis que `AGENT_OPERATOR_*` fixe l’opérateur du processus. Fournir à Agent une identité de confiance par requête, avec session web à durée bornée, protections intersites et révocation. Définir les droits de lecture, édition, validation, administration et lancement de traitements.
- Contrôler les droits sur les identifiants ERP et Brain, la recherche transversale, les sources globales et les téléchargements. Revérifier les droits sur une source au moment d’ouvrir une citation ou de publier. Restreindre les réglages, imports, extensions et opérations de maintenance. Associer les jobs et reçus à l’acteur et au périmètre autorisé. Tester les accès croisés et la révocation pendant un flux.
- Déployer sous un compte de service et des ACL adaptés, avec les données hors code. Superviser les migrations et la reprise des workers. Distinguer la santé HTTP, l’accès aux bases, l’inférence, la transcription et l’état des index. [Entrée FastAPI](<D:/Agent/app/main.py>), [protection de la session locale](<D:/Agent/app/security.py>)

### Catalogue unique et compatibilité Kiara

- Utiliser l’identifiant ERP comme identifiant du projet métier et résoudre le Brain associé via `brain_links`. Rendre création, archivage et rattachement rejouables, avec reprise après un échec entre les deux bases.
- Adapter les consommateurs Kiara de `project_id`, notamment le sélecteur, Workspace, le chat, les mémoires, la recherche, les notifications et Hermes. Un adaptateur peut projeter les champs utiles au contrat historique. Le nom, le code, l’état et la création du projet relèvent d’Agent. Les nouvelles données propres à Kiara se rattachent à l’identifiant Agent. Désactiver la création parallèle de projets Workspace.
- Pour un chat en projet, fournir les preuves Agent par une lecture autorisée, en conservant leurs citations et validations. Préserver le chat général, le correcteur, la voix, Hermes et les intégrations Codex/OpenCode. Prévoir une transition pour Linux et Android avec le contrat historique adapté et le web pour les fonctions disponibles. Qualifier le générateur Android et les nouveaux identifiants. La parité complète demandée concerne Windows. [Architecture Kiara](../ARCHITECTURE-ACTUELLE.md)

## Périmètre fonctionnel et recette de parité

| Domaine Agent | Travail à livrer et à vérifier |
| --- | --- |
| Accueil, projets et portefeuille | Navigation Agent, identité projet, clients, équipe, rôles, recherche, projets actifs et clos. Même portefeuille autorisé dans l’EXE et le web. |
| CDC, CDC & BE et revues | Extraction et analyse, exigences, pages et ancrages, validation humaine, versions, publication et transfert. Tester import, aperçu, annulation, reprise et export. |
| Planning et atelier | Jalons, dates contractuelles/prévues/réelles, tâches, charge, modèles, achats, pointage et nomenclature. Tester les modifications concurrentes. |
| Sage et dossiers réseau | Import, rapprochement, erreurs par ligne et dossiers configurés. Distinguer les fichiers accessibles au service des dossiers accessibles au poste. L’EXE ouvre les chemins autorisés dans l’Explorateur. Le navigateur propose upload, téléchargement ou chemin à copier selon l’opération. |
| Documents, livrables et notes | Versions, révisions, checklists, signatures ou preuves métier, préparation, publication, exports et transferts de projet. Vérifier la version publiée, sa destination et la reprise d’une opération interrompue. |
| Mails, sources et pièces jointes | EML/MIME, HTML isolé, pièces jointes, OCR, déduplication, tri automatique, décisions humaines, références et suivi des jobs. Réappairer Thunderbird pour collecte et brouillons/réponses. Garder l’import des EML Infomaniak par connecteur ou upload. |
| Réunions | Studio, calendrier, capture, pause/reprise, fragments durables, transcription provisoire, transcription complète et diarisation, relecture, validation, compte rendu, exports et création explicite de tâches. EXE avec capture native. Web avec microphone, partage audio selon navigateur et import. |
| Informations, recherche et assistant | Recherche sémantique EG2 sur la P2200, citations, données retenues par défaut et décisions humaines, conversation éphémère par défaut, historique explicite et annulation du flux. Vérifier les preuves sur mails, notes et pièces jointes. |
| Réglages et exploitation | État des connexions, traitements, diagnostics et maintenance selon le rôle. Paramètres machine et secrets côté exploitation. Faire remonter les erreurs d’OCR, d’IA, d’import et de stockage dans leurs parcours. |

## Tauri 2 et fonctions du poste

Le frontend Agent existe en React/Vite. Tauri 2 peut embarquer le même build et utilise WebView2 sous Windows. La cible est un EXE avec assets locaux et une interface Agent commune au web. Pendant la transition, conserver dans le même EXE les parcours Kiara actuels via un adaptateur. Le coût principal se situe dans le transport, les fonctions natives et la reprise des profils locaux. [Configuration Vite de Tauri](https://v2.tauri.app/start/frontend/vite/), [versions des WebViews](https://v2.tauri.app/reference/webview-versions/)

| Option | Évaluation |
| --- | --- |
| Tauri avec assets embarqués et web issu du même build | Cible. Un frontend métier, un contrat d’API et des capacités natives ciblées. Le backend doit négocier sa compatibilité avec les clients installés. |
| pywebview avec Agent intégré pendant la transition | Étape possible si le pilote Tauri révèle une régression matérielle ou de mise à jour. Les travaux serveur, accès et restauration restent réutilisables. |
| Tauri affichant le site distant | Suffisant pour démontrer la navigation. Les fonctions natives de production doivent être accessibles depuis un frontend embarqué de confiance, avec permissions limitées. |

- **Transport.** Réutiliser d’abord le pont WireGuard et les fonctions du relais Python comme composants supervisés. Préserver le relais OpenAI local utilisé par Codex et les outils existants. Protéger les clés avec les mécanismes du poste. Appairer la WebView au relais local, limiter les routes et origines, et tester la fermeture des auxiliaires. Les contenus de mails et pièces jointes s’affichent sans privilèges Tauri. [Capacités Tauri](https://v2.tauri.app/security/capabilities/), [binaires auxiliaires](https://v2.tauri.app/develop/sidecar/)
- **Audio.** Garder le helper WASAPI interactif et les reçus de fragments. Déplacer le propriétaire de la capture sur le poste Tauri et synchroniser les fragments vers Brain. Tester périphérique retiré, coupure, reprise, arrêt et double envoi. Garder les runtimes hors ligne et les packs vocaux Kiara Low/Max. En navigateur, le microphone exige un contexte sécurisé et une permission. Le partage audio dépend du navigateur et de la surface choisie. [Microphone web](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia), [partage d’écran et d’audio](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia)
- **Fichiers et extensions.** Limiter les commandes natives à des actions ciblées et autorisées. Ouvrir les partages dans le contexte du poste, avec liste de racines et types de fichiers permis. Le pont Thunderbird garde un appairage par poste et des droits dédiés. Les navigateurs ne disposent pas tous du sélecteur de répertoires. [Sélection de dossier en navigateur](https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker)
- **Installation.** Qualifier Rust/MSVC, WebView2 et l’installateur NSIS EXE. Tester installation neuve et mise à niveau depuis 3.5.62 avec le profil chiffré, l’identité d’appareil, les historiques et brouillons, les packs vocaux et les intégrations. Prévoir un import contrôlé des données WebView lors d’un changement de profil ou d’origine. Qualifier le canal de distribution signé Kiara. L’updater Tauri, s’il est retenu, exige sa propre signature. [Installateur Windows](https://v2.tauri.app/distribute/windows-installer/), [updater Tauri](https://v2.tauri.app/plugin/updater/)

## IA, indexation et exploitation

- Raccorder Agent à la passerelle Kiara avec une identité de service autorisée pour le LLM et EG2. L’export cible `fred-qwen` et `google/embeddinggemma-2`, avec des lots de huit. Les traitements serveur doivent fonctionner indépendamment du relais EXE `127.0.0.1:17841`. Reconfigurer les secrets protégés et le secours local selon le contexte.
- Vérifier le modèle, la dimension, le préfixe, la normalisation et le profil de rappel avant de réutiliser l’index. Kiara limite chaque texte à 8 192 jetons, préfixe inclus. Préserver la provenance lors du découpage et les paramètres CDC de génération sans réflexion. Tester simultanément chat, mails, analyse CDC, recherche et réunions.
- Reprendre les planificateurs avec un seul responsable par type de traitement. Démarrer la restauration de recette sans tâches automatiques. Fixer priorités et budgets pour les demandes interactives, les mails et les reconstructions. Qualifier OCR, STT et diarisation, ainsi que la saturation de la P2200 partagée par vision et EG2.
- Intégrer une sauvegarde post-bascule qui coordonne Brain, ERP et fichiers métier. Chiffrer les archives selon la politique Kiara et tester une restauration neuve. Les fichiers externes doivent figurer à l’inventaire. Les index et anciens marqueurs de sauvegarde ne déterminent pas les chemins et tâches actifs. [Canal EG2 Agent](<D:/Agent/docs/36_EMBEDDING_CHANNEL.md>), [sauvegarde SQLite](https://www.sqlite.org/backup.html)

## Migration et retrait des projets Kiara

1. **Restaurer Agent dans un répertoire privé isolé sur F:.** Garder les trois sources d’import en lecture seule. Créer les espaces Brain, ERP et stockage hors code. Vérifier capacité disque, chemins normalisés et empreintes. Exécuter les migrations sur les copies avec les workers, imports automatiques et sorties réseau suspendus.
2. **Reloger les fichiers et reconfigurer les dépendances.** Réutiliser les mécanismes Agent de restauration pour les chemins gérés et la neutralisation des opérations interrompues. Contrôler CDC, audio, OCR, EML, index et liens réseau. Reconnecter les secrets et extensions. Présenter la liste des preuves indisponibles et des traitements à reprendre.
3. **Recetter le portefeuille et l’adaptateur Kiara.** Comparer les comptages et liaisons à l’inventaire. Vérifier le projet ERP isolé et le projet Brain isolé, les droits, la création, les modifications concurrentes, les citations et les téléchargements. Valider le fonctionnement hors projet et l’invalidation des anciens identifiants avant la bascule.
4. **Retirer les anciens projets Kiara sans créer de sauvegarde de ces projets.** Le Workspace inspecté, `F:\Serveur IA\lanceur\espaces-prives\espaces.sqlite3`, contient 0 projet, 0 document projet et 2 lignes d’historique client. Vérifier le `KIARA_DATA_DIR` effectif et refaire le comptage au moment de la bascule. Si des projets sont présents, geler les écritures de l’ancien catalogue et les sauvegardes automatiques susceptibles de le copier. Préparer une purge ciblée et rejouable des projets Kiara et de leurs dépendances, avec contrôles des cascades, historiques liés, FTS/EG2, projections Hermes, commandes, notifications et caches. Conserver les accès, réglages et conversations hors projet. Si le résultat confirmé est zéro, la purge des lignes projet est sans objet. Empêcher leur réapparition par synchronisation ou restauration.
5. **Basculer de façon coordonnée.** Activer le catalogue Agent, publier l’EXE signé, ouvrir le web privé et réactiver les workers un par un. Le retour après purge porte sur le code, le routage, les clients et les données Agent. La suppression sans sauvegarde de l’ancien catalogue est irréversible. Les sauvegardes Kiara préexistantes restent hors de la purge active. Si elles doivent aussi être supprimées, établir leur périmètre, car elles peuvent contenir des données hors projet.

## Lots de réalisation et conditions de livraison

| Lot | Résultat | Condition de passage |
| --- | --- | --- |
| 1. Reprise Agent | Importeur, relogement, synthèse par famille et restauration répétable. | Bases, liaisons, originaux présents et index concordants. Originaux CDC récupérés ou réserve documentée pour la bascule. |
| 2. Accès et service | Agent supervisé, authentification, habilitations, accès IA et sauvegarde. | Tests des droits, limites d’import, streaming, annulation, révocation, redémarrage et restauration réussis. |
| 3. Catalogue | Agent fournit les projets à l’UI et aux services Kiara. Compatibilité des anciens clients traitée. | Création, archivage, recherche et chat utilisent le même identifiant. Aucun ancien catalogue ne se recrée. |
| 4. Tauri et web | Interface React commune, EXE installable, profils migrés, API natives et connecteurs. | Installation et mise à niveau sur Windows réels. Recettes de capture, dossiers réseau, Thunderbird, voix et fonctionnement en coupure. |
| 5. Bascule | Publication progressive et retrait ciblé de l’ancien catalogue. | Recette sur deux comptes, deux postes et un navigateur. Concordance des projets, sources, index et jobs. Retour logiciel et restauration Agent vérifiés. |

Exécuter les suites backend, frontend et UX existantes des deux dépôts. Compléter par des parcours de bout en bout sur données fictives et une restauration privée. Prioriser capture du microphone et de la sortie Windows, téléchargement volumineux, partage réseau, appairage Thunderbird et mise à jour depuis l’EXE déployé. Exécuter la recherche, le CDC et la génération sur le moteur Kiara cible. Vérifier clavier, focus, états d’erreur et usage sur écran étroit.

Ordre de grandeur pour un développeur, hors délai d’obtention des originaux et des accès. Prévoir 3 à 5 jours pour la reprise, 7 à 12 pour le service et les accès, 5 à 9 pour le catalogue, 10 à 18 pour la parité Tauri et 4 à 7 pour la recette et la bascule. Réviser cette estimation après les pilotes de capture, de transport et de mise à jour.

## Périmètre de la vérification

Les contrôles portent sur les sources versionnées, les fichiers fournis et le Workspace trouvé à l’emplacement standard. Les index SQLite ont été vérifiés sur des copies temporaires ensuite retirées. Les bases et l’archive fournies sont intactes. La qualification du service de production, de l’EXE Tauri compilé, des parcours navigateur connectés et de la restauration complète de l’ancien PC relève de la recette.

Références de mise en œuvre. [Restauration Agent](<D:/Agent/app/services/backup.py>), [capture de réunion](<D:/Agent/docs/56_MEETING_START_GUIDE.md>), [liaison Thunderbird](<D:/Agent/docs/21_THUNDERBIRD_BRIDGE.md>), [reconstruction Kiara](../RECONSTRUIRE-FRED.md).

