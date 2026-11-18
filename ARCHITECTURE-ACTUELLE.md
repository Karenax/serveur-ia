# Kiara — architecture et versions actuelles

Référence du 18 novembre 2026. Kiara 4.0.11 est le client Windows publié avec le portail privé unifié. Le canal de transition du client classique utilise la 3.5.63. Les qualifications Linux et Android suivent un calendrier distinct.

## Versions et responsabilités

| Composant | Version ou contrat | Rôle |
|---|---|---|
| Lanceur et client Windows de transition | 3.5.63 | Services Kiara et passage vers Kiara 4 |
| Client Windows Kiara 4 | 4.0.11 | Application Tauri, téléchargements et mises à jour Windows. Référence de retour 4.0.10. |
| Linux | 3.5.62, dernière référence documentée | Client Linux historique |
| Android | 1.0.26, code 27 | Enveloppe Java/WebView et interface partagée |
| Contrat de conversation | 4 | Conversations, outils et approbations existants |
| Identifiants de commandes | Version 2 négociée par `/v1/status` | Rétention bornée et refus du rejeu après expiration |
| Base Workspace | Schéma 2 | Données canoniques et migrations versionnées |
| Paquet partagé | `kiara-shared` 0.1.0 | Validation, HTTP, fichiers protégés, signatures et contrôleur vocal |
| Go du pont | 1.27.3 | Transport WireGuard et proxies bornés |
| Inférence locale | Strata, selon la configuration du lanceur | Exécution des modèles et état du moteur séparés du portail et du client |
| Hermes privé | Commit `79651b71bd56efd76d06f3de1df64dde09b58ff3`, patch et verrous locaux | Agent natif et outils autorisés |
| Synthèse | Phonon 0.4.1, voix Tiphaine | Voix française sur CPU |
| Reconnaissance Low Windows | Parakeet v3 | Dictée et conversation locales |
| Reconnaissance Android | Whisper Small | Reconnaissance locale dans l’application |
| Pack Max actuel | Format 2, `runtime_api` 6 | Whisper Turbo Q5 Vulkan et Phonon CPU |

L’état effectivement installé et les empreintes des livrables sont dans les manifestes de construction et de déploiement. Cette table ne remplace pas leurs preuves de publication.

Le [profil GPU du 3 novembre](maintenance/2026-11-03-rtx4080/default-mode/README.md)
documente la configuration de test à quatre cartes et ses anciens chemins. Les
emplacements actifs dépendent de la configuration locale du lanceur. Sur le poste
Fred, les compilations, caches et recettes sont sur D:. E: est réservé aux archives
et aux preuves conservées.
Dans ce profil historique, le contexte était de 393 216 tokens avec YaRN ×1,5 et un cache KV INT8. Le KV complet résidait en RAM avec
20480 cellules par couche d'attention conservées en VRAM. Le cache d'experts du
GPU principal et ceux des deux P100 étaient automatiques. DFlash2 remplaçait la couche
MTP, avec fenêtre 6 et seuil 0,8 dans cette configuration.
Les [essais de performance](maintenance/2026-11-03-rtx4080/ESSAIS-0156.md)
documentent ce choix et le rôle de la P2200 pour l’encodage des images.

## Projets et Conversations

- **Accès** — Le lanceur supervise le service Projets. Le portail privé Kiara s’ouvre sous `/kiara/` depuis le pilote du 16 novembre. Les anciens liens sous `/agent/` restent compatibles. Les accès utilisent le code Kiara et les habilitations par projet. Le contrôle de production a retrouvé les 11 projets.
- **Données** — Les bases ERP et Brain et les fichiers de projet sont côté serveur. Les nouveaux documents rejoignent les dossiers clients sur D:. La sauvegarde chiffrée inclut les deux bases et les dossiers clients. Une copie NAS a été restaurée dans un dossier isolé.
- **Recherche.** Qwen local répond avec des citations tirées des sources autorisées. EG2 calcule les embeddings sur la P2200. Les images et l’audio sont recherchés à partir du texte extrait. Les deux anciens runtimes LiteRT ont été retirés.
- **Mails et réunions.** La liaison Thunderbird collecte les dossiers sélectionnés sur le poste associé. Les imports, le classement manuel, le rejet et le brouillon ont été validés sur le poste Fred. Le classement automatique s’applique à partir d’un score de 75 %. Réunions dans Kiara 4.0.5 a passé la recette de capture, transcription, relecture et publication du compte rendu.
- **Interface.** Conversations réunit le composeur, l’historique et l’assistant de projet. Les brouillons personnels et de projet et le mode éphémère sont accessibles depuis le même espace. Projets conserve la liste et la fiche à quatre rubriques dans le style Kiara. Le panneau d’assistance historique a été retiré.
- **Notes.** Le portail réunit les notes privées de l’opérateur et les notes des projets actifs auxquels il a accès. L’éditeur riche permet le collage direct d’images. Les pièces jointes et l’historique des notes de projet relèvent de l’ERP, qui conserve également les versions et images des notes personnelles. [Guide d’utilisation](GUIDE-ASSISTANT-KIARA.md#prendre-des-notes-dans-kiara)
- **Vocal.** La conversation vocale et la dictée sont disponibles dans le composeur Windows. Le web privé indique où ouvrir le client Windows pour utiliser le microphone.
- **Réglages.** Le portail expose les rubriques serveur, projets et appareil. Sous Windows, Conversations ouvre les réglages de l’appareil en local. Les mises à jour utilisent le relais du client et le canal signé. [Audit des réglages](audits/2026-11-15-fusion-kiara/BASCULE.md#audit-des-réglages-de-kiara-4011)
- **Distribution.** La console sert la 4.0.11 avec son manifeste Ed25519 et son installateur sans Authenticode. La 4.0.10 est conservée pour le retour. Les clients classiques utilisent la 3.5.63.

Le [plan global](PLAN-GLOBAL-SERVEUR-FRED.md) reprend les vérifications qui restent à faire et le report des imports Sage.

## Organisation du code

Le serveur reste un monolithe modulaire, avec des processus séparés pour les moteurs. `lanceur/app.py` pilote la console et `remote.py` la passerelle. Workspace garde la transaction et le contrôle d’accès ; les opérations sont réparties dans `workspace_project.py`, `workspace_document.py`, `workspace_conversation.py`, `workspace_job.py`, `workspace_memory.py` et `workspace_knowledge.py`.

`memory_service.py` porte les règles de mémoire des deux protocoles. `assistant_commands.py` orchestre les commandes ; `assistant_repository.py` fournit les primitives de stockage et `command_journal.py` leur idempotence. Les adaptateurs historiques n’inventent pas de révision pour un brouillon.

`shared/kiara_shared` est un paquet installé explicitement dans les environnements serveur et constructeur. Le serveur importe ses primitives directement. Les anciens noms de modules Windows restent des alias de compatibilité. Aucun chargement dynamique du contrôleur vocal depuis un fichier du client n’est nécessaire.

Les sources HTML/CSS/JS Windows restent la base de l’interface. Android fournit ses capacités et ses vues natives dans `client-android/mobile-ui`. Les régions de code adaptées ont des noms stables, déclarés dans `platform-adapters.json` ; le générateur vérifie leur présence et leur unicité. Les remplacements de libellés servent uniquement aux différences de vocabulaire de plateforme. Les assets Android sont générés, puis vérifiés, et ne se modifient pas à la main.

## Autorités des données

- ERP et Brain portent le portefeuille de projets Kiara et ses données métier.
- Workspace SQLite porte les espaces privés Kiara, les accès, les souvenirs, les conversations publiées, les commandes et les notifications.
- Historique protégé du client : copie locale et brouillons pour le fonctionnement hors ligne ; les conflits se résolvent par synchronisation.
- Sessions Hermes : état natif du moteur et projection liée au périmètre Kiara.
- Index EG2, chunks et exports : données dérivées, invalidables ou reconstructibles.
- Sauvegardes chiffrées : récupération et portabilité, avec les procédures de clés existantes.

La console distingue l’archive Projets, la sauvegarde globale, la copie secondaire
et la dernière restauration vérifiée. Une sauvegarde automatique interrompue
reprend au prochain horaire configuré. Les retraits de rétention disposent d’un
journal pour terminer ou reprendre une opération interrompue.

La [matrice des autorités et échanges](maintenance/CONTRATS-DONNEES.md) précise identités, révisions et projections. Les caches et sauvegardes ont donc une fonction propre. Une opération métier possède une implémentation canonique, même lorsqu’elle dispose de plusieurs adaptateurs.

## Concurrence, saturation et migrations

Chaque modification ou suppression d’un souvenir fournit sa révision. Une version périmée provoque un conflit ; l’éditeur conserve le brouillon et propose de recharger explicitement la version du serveur. Les anciens clients qui ne transmettent aucune révision doivent être mis à jour pour modifier leurs souvenirs.

Les nouvelles demandes de commandes portent un identifiant `v2_` avec date et nonce. Le client choisit ce format uniquement lorsque le serveur l’annonce et compense son horloge avec l’heure du serveur. Les clients et API historiques continuent à utiliser leurs identifiants opaques. Les adaptateurs conservent l’identité d’une demande lors d’un nouvel essai.

Le journal conserve au maximum 5 000 reçus datés par accès, avec une rétention de 30 jours. Lors du compactage, une limite durable interdit de rejouer les demandes retirées ; elle est incluse dans les sauvegardes et exports clients. Les reçus opaques anciens ne sont pas supprimés à l’aveugle : leur réserve de compatibilité est bornée à 5 000 et exige ensuite un client actuel. Oubli et annulation utilisent une voie de récupération qui reste disponible à quota plein pour les nouvelles commandes.

Le schéma 2 ajoute les index de lecture et le registre de migration. L’absence d’un ancien marqueur de réinitialisation n’efface plus les conversations. Un cache chiffré valide est conservé ; un cache inconnu reste disponible dans un fichier protégé de récupération. Les anciens schémas de sauvegarde restent reconnus explicitement avant migration ; le SQL fourni par une archive n’est pas exécuté comme une nouvelle définition de schéma.

## Environnements et déploiement

Sept profils sont verrouillés : Strata, EG2 CPU de secours, EG2 CUDA, voix serveur, conversation Windows, Hermes privé et construction Windows. EG2 utilise la P2200 en float32/SDPA, avec choix explicite de carte et repli CPU visible ; `lanceur/eg2-runtime.json` déclare le runtime et les budgets. La vision partage cette carte. Sur le poste Fred, l’inventaire Windows du 16 novembre 2026 relève une RTX 4080 et une Quadro P2200 ; les deux P100 appartiennent au profil historique décrit plus haut. Vérifier le moteur et les cartes effectivement utilisés avant toute modification. Le constructeur est dans `toolchain/build-python` ; PyInstaller n’est plus nécessaire dans le runtime Strata. Strata n’hérite plus des bibliothèques de l’outillage Codex.

Le runtime Hermes privé est sélectionné avant toute consultation de l’installation personnelle. Le pointeur déclare ses sources, Python, dépendances et outils. Les répertoires de dépendances partagés conservés lors de la migration restent des prérequis explicites ; retirer l’installation personnelle ne doit pas entraîner la suppression de ces répertoires tant qu’ils sont référencés.

`KIARA_DATA_DIR` permet d’utiliser un répertoire de données distinct, avec le chemin historique `lanceur` comme valeur par défaut. `KIARA_RUNTIME_PYTHON` permet de choisir le Python d’exécution. Changer un emplacement de données exige une sauvegarde vérifiée et une restauration par la procédure existante ; définir un dossier vide ne déplace pas les accès ni leurs clés.

Les manifestes distinguent `server`, `windows`, `android` et, si nécessaire, `voice`. Le manifeste d’ensemble refuse un binaire ou des sources modifiés depuis la construction et exige tous les groupes de validation. Le paquet serveur de sources exclut les données privées, modèles et secrets. Les distributions signées et les anciennes versions restent gérées par les procédures de reconstruction et de retour existantes.

## Diagnostic et performance

Les lectures de l’espace utilisent des requêtes par lots ; leur nombre ne dépend plus du nombre de projets. Les index couvrent propriétaire, projet et date. Les quotas restent vérifiés sur les données réelles dans la transaction.

La console expose les mesures d’attente du verrou, de transaction et de snapshot : nombre d’échantillons, médiane et p95. Les diagnostics sont bornés et limités aux catégories, durées, composants et références ; les prompts, documents et sorties brutes des workers n’y sont pas enregistrés. Les erreurs restent visibles dans les parcours utilisateur et leurs références dans le journal administratif.

## Validation et documentation

Le point d’entrée est `maintenance/verify_project.py`. Il agrège les résultats et écrit les preuves dans un répertoire d’exécution. Les tests UI utilisent tous ce répertoire et ne remplacent plus les captures historiques. Voir [RECONSTRUIRE-FRED.md](RECONSTRUIRE-FRED.md) pour les commandes, puis [la matrice des compatibilités vocales](client-voice/COMPATIBILITE.md).

Les [audits](audits/2026-10-25-global/RAPPORT.md), recherches et dossiers de maintenance datés décrivent les décisions et états passés. Le [suivi des corrections](maintenance/2026-10-26-correctifs-audit-global/AVANCEMENT.md) indique les validations et les limites de cette livraison.

La [matrice des compatibilités](maintenance/COMPATIBILITE.md) indique les responsabilités et les conditions de retrait des anciens clients, routes et formats.
