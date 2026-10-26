# Kiara — architecture et versions actuelles

Référence courante au 26 octobre 2026. Les rapports datés conservent leur valeur historique ; cette page décrit le code et les procédures de la livraison 3.5.54 / Android 1.0.25.

## Versions et responsabilités

| Composant | Version ou contrat | Rôle |
|---|---|---|
| Serveur et Windows | 3.5.54, dans `shared/kiara_shared/version.py` | Application et distribution Windows |
| Android | 1.0.25, code 26 | Enveloppe Java/WebView et interface partagée |
| Contrat agent | 4 | Conversation, outils et approbations existants |
| Identifiants de commandes | Version 2 négociée par `/v1/status` | Rétention bornée et refus du rejeu après expiration |
| Base Workspace | Schéma 2 | Données canoniques et migrations versionnées |
| Paquet partagé | `kiara-shared` 0.1.0 | Validation, HTTP, fichiers protégés, signatures et contrôleur vocal |
| Go du pont | 1.27.3 | Transport WireGuard et proxies bornés |
| Moteur de production | Strata 0.1.45.3 | Moteur CUDA ; serveur Python 0.1.43.1 corrigé et encodeur P2200 conservés |
| Hermes privé | Commit `79651b71bd56efd76d06f3de1df64dde09b58ff3`, patch et verrous locaux | Agent natif et outils autorisés |
| Synthèse | Phonon 0.4.1, voix Tiphaine | Voix française sur CPU |
| Reconnaissance Low Windows | Parakeet v3 | Dictée et conversation locales |
| Reconnaissance Android | Whisper Small | Reconnaissance locale dans l’application |
| Pack Max actuel | Format 2, `runtime_api` 6 | Whisper Turbo Q5 Vulkan et Phonon CPU |

L’état effectivement installé et les empreintes des livrables sont dans les manifestes de construction et de déploiement. Cette table ne remplace pas leurs preuves de publication.

## Organisation du code

Le serveur reste un monolithe modulaire, avec des processus séparés pour les moteurs. `lanceur/app.py` pilote la console et `remote.py` la passerelle. Workspace garde la transaction et le contrôle d’accès ; les opérations sont réparties dans `workspace_project.py`, `workspace_document.py`, `workspace_conversation.py`, `workspace_job.py`, `workspace_memory.py` et `workspace_knowledge.py`.

`memory_service.py` porte les règles de mémoire des deux protocoles. `assistant_commands.py` orchestre les commandes ; `assistant_repository.py` fournit les primitives de stockage et `command_journal.py` leur idempotence. Les adaptateurs historiques n’inventent pas de révision pour un brouillon.

`shared/kiara_shared` est un paquet installé explicitement dans les environnements serveur et constructeur. Le serveur importe ses primitives directement. Les anciens noms de modules Windows restent des alias de compatibilité. Aucun chargement dynamique du contrôleur vocal depuis un fichier du client n’est nécessaire.

Les sources HTML/CSS/JS Windows restent la base de l’interface. Android fournit ses capacités et ses vues natives dans `client-android/mobile-ui`. Les régions de code adaptées ont des noms stables, déclarés dans `platform-adapters.json` ; le générateur vérifie leur présence et leur unicité. Les remplacements de libellés servent uniquement aux différences de vocabulaire de plateforme. Les assets Android sont générés, puis vérifiés, et ne se modifient pas à la main.

## Autorités des données

- Workspace SQLite : projets, documents, souvenirs, conversations publiées, tâches, commandes et notifications.
- Historique protégé du client : copie locale et brouillons pour le fonctionnement hors ligne ; les conflits se résolvent par synchronisation.
- Sessions Hermes : état natif du moteur et projection liée au périmètre Kiara.
- Index EG2, chunks et exports : données dérivées, invalidables ou reconstructibles.
- Sauvegardes chiffrées : récupération et portabilité, avec les procédures de clés existantes.

Les caches et sauvegardes ont donc une fonction propre. Une opération métier possède une implémentation canonique, même lorsqu’elle dispose de plusieurs adaptateurs.

## Concurrence, saturation et migrations

Chaque modification ou suppression d’un souvenir fournit sa révision. Une version périmée provoque un conflit ; l’éditeur conserve le brouillon et propose de recharger explicitement la version du serveur. Les anciens clients qui ne transmettent aucune révision doivent être mis à jour pour modifier leurs souvenirs.

Les nouvelles demandes de commandes portent un identifiant `v2_` avec date et nonce. Le client choisit ce format uniquement lorsque le serveur l’annonce et compense son horloge avec l’heure du serveur. Les clients et API historiques continuent à utiliser leurs identifiants opaques. Les adaptateurs conservent l’identité d’une demande lors d’un nouvel essai.

Le journal conserve au maximum 5 000 reçus datés par accès, avec une rétention de 30 jours. Lors du compactage, une limite durable interdit de rejouer les demandes retirées ; elle est incluse dans les sauvegardes et exports clients. Les reçus opaques anciens ne sont pas supprimés à l’aveugle : leur réserve de compatibilité est bornée à 5 000 et exige ensuite un client actuel. Oubli et annulation utilisent une voie de récupération qui reste disponible à quota plein pour les nouvelles commandes.

Le schéma 2 ajoute les index de lecture et le registre de migration. L’absence d’un ancien marqueur de réinitialisation n’efface plus les conversations. Un cache chiffré valide est conservé ; un cache inconnu reste disponible dans un fichier protégé de récupération. Les anciens schémas de sauvegarde restent reconnus explicitement avant migration ; le SQL fourni par une archive n’est pas exécuté comme une nouvelle définition de schéma.

## Environnements et déploiement

Six profils sont verrouillés : Strata, EG2, voix serveur, conversation Windows, Hermes privé et construction Windows. Le constructeur est dans `toolchain/build-python` ; PyInstaller n’est plus nécessaire dans le runtime Strata. Strata n’hérite plus des bibliothèques de l’outillage Codex.

Le runtime Hermes privé est sélectionné avant toute consultation de l’installation personnelle. Le pointeur déclare ses sources, Python, dépendances et outils. Les répertoires de dépendances partagés conservés lors de la migration restent des prérequis explicites ; retirer l’installation personnelle ne doit pas entraîner la suppression de ces répertoires tant qu’ils sont référencés.

`KIARA_DATA_DIR` permet d’utiliser un répertoire de données distinct, avec le chemin historique `lanceur` comme valeur par défaut. `KIARA_RUNTIME_PYTHON` permet de choisir le Python d’exécution. Changer un emplacement de données exige une sauvegarde vérifiée et une restauration par la procédure existante ; définir un dossier vide ne déplace pas les accès ni leurs clés.

Les manifestes distinguent `server`, `windows`, `android` et, si nécessaire, `voice`. Le manifeste d’ensemble refuse un binaire ou des sources modifiés depuis la construction et exige tous les groupes de validation. Le paquet serveur de sources exclut les données privées, modèles et secrets. Les distributions signées et les anciennes versions restent gérées par les procédures de reconstruction et de retour existantes.

## Diagnostic et performance

Les lectures de l’espace utilisent des requêtes par lots ; leur nombre ne dépend plus du nombre de projets. Les index couvrent propriétaire, projet et date. Les quotas restent vérifiés sur les données réelles dans la transaction.

La console expose les mesures d’attente du verrou, de transaction et de snapshot : nombre d’échantillons, médiane et p95. Les diagnostics sont bornés et limités aux catégories, durées, composants et références ; les prompts, documents et sorties brutes des workers n’y sont pas enregistrés. Les erreurs restent visibles dans les parcours utilisateur et leurs références dans le journal administratif.

## Validation et documentation

Le point d’entrée est `maintenance/verify_project.py`. Il agrège les résultats et écrit les preuves dans un répertoire d’exécution. Les tests UI utilisent tous ce répertoire et ne remplacent plus les captures historiques. Voir [RECONSTRUIRE-FRED.md](RECONSTRUIRE-FRED.md) pour les commandes, puis [la matrice des compatibilités vocales](client-voice/COMPATIBILITE.md).

Les [audits](audits/2026-10-25-global/RAPPORT.md), recherches et dossiers de maintenance datés décrivent les décisions et états passés. Le [suivi des corrections](maintenance/2026-10-26-correctifs-audit-global/AVANCEMENT.md) indique les validations et les limites de cette livraison.
