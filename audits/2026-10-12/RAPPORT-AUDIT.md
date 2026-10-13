# Audit approfondi du projet Serveur IA — 12 octobre 2026

Le projet possède une suite de régression importante et plusieurs protections bien implantées. L’audit a néanmoins confirmé **sept problèmes**, dont **trois à corriger en priorité** : les exports par client peuvent cesser de fonctionner, une réponse Hermes peut produire un historique refusé par les clients, et les données Hermes peuvent dépasser leurs limites de sauvegarde sans entrer dans les quotas affichés. Les tests existants passent parce que ces cas précis n’y figurent pas.

Référence examinée : `ffe85204729db298ac83848e727e2b9aa10f5548`, branche `main`. Les changements de cet audit sont des rapports, inventaires et reproductions ; les sources applicatives n’ont pas été corrigées. Les essais utilisent des accès synthétiques, des services simulés et des dossiers temporaires. Le contrôle final retrouve la console locale disponible et Qwen IQ4 chargé.

Le [contrôle de production en lecture seule](<D:/Serveur IA/audits/2026-10-12/production-health.json>) retrouve les deux dossiers clients synchronisés sans erreur et la sauvegarde du 12 octobre à 03 h 00 réussie. La base d’intégration Hermes pèse alors 184 320 octets. Aucune conversation n’est encore enregistrée dans la table des conversations de projet, ce qui explique que R01 ne se manifeste pas sur les données actuelles. Les corrections prioritaires préviennent donc des pannes que les reproductions ont déclenchées avec d’autres données autorisées par les contrats.

**Périmètre et preuves.** L’inventaire porte sur 2 624 fichiers suivis, soit 43 779 866 octets. Il distingue les applications actuelles des archives d’expérimentation. Les 351 fichiers de source recensés représentent 37 568 lignes ; environ 19 907 lignes concernent les quatre composants applicatifs hors tests, bibliothèque JavaScript tierce et interface Android générée. Les 196 fichiers Python recensés se compilent syntaxiquement. Les contrats serveur, données, clients, migrations, sauvegardes, outils Hermes, voix, mises à jour, scripts de livraison et documentation ont été examinés. Les six instantanés de moteurs tiers correspondent aux commits et patchs locaux. Les modifications locales Strata ont été consultées ; ce rapport ne constitue pas une certification exhaustive du code amont des moteurs, des poids des modèles ou des bibliothèques tierces.

| Vérification | Résultat |
| --- | --- |
| Tests Python serveur | 431 réussis en 831,134 s |
| Tests Python client Windows | 17 réussis |
| Tests Python voix | 20 réussis |
| Tests Python outils Android | 13 réussis |
| Total Python existant | **481 réussis** |
| Suites JavaScript exécutées | **8 réussies**, dont 5 suites navigateur avec Chrome sans interface visible |
| Contrôles syntaxiques JavaScript, scripts HTML compris | **58 réussis** |
| Interface Android générée | Conforme aux sources communes, contrôle `Prepare-Assets.py --check` réussi |
| Android `lintDebug`, Gradle hors ligne | Réussi ; 0 erreur et 5 avertissements |
| Analyse syntaxique PowerShell | 86 fichiers ; 1 fichier défectueux sous PowerShell 7, détail R07 |
| Cohérence des dépendances installées | `pip check` réussi dans les environnements Strata, EG2, voix serveur et conversation Windows |
| Commits et patchs des moteurs enregistrés | 6/6 correspondent aux installations locales |
| Distribution Windows | Manifeste vérifié, version 3.5.27 |
| Distribution Android | Empreinte vérifiée, version 1.0.10/code 11 |

La couverture de la suite serveur a également été mesurée sur 25 modules centraux : **87,9 % des instructions** et **71,5 % des branches**. Ces chiffres ne couvrent pas toute l’application, les sous-processus natifs et JavaScript. Ils montrent surtout pourquoi une bonne couverture globale peut encore manquer des interactions importantes. Le détail est dans [coverage-server.json](<D:/Serveur IA/audits/2026-10-12/coverage-server.json>).

**Problèmes confirmés, classés par conséquence.** P1 signifie correction prioritaire pour préserver le fonctionnement et les données ; P2 signifie défaut réel à corriger ensuite. Toutes les reproductions Python sont regroupées dans [reproduce.py](<D:/Serveur IA/audits/2026-10-12/reproduce.py>) et leurs résultats dans [reproductions.json](<D:/Serveur IA/audits/2026-10-12/reproductions.json>).

**R01 — P1 : enregistrer une conversation dans un projet bloque la génération des dossiers clients.**

Emplacement : [client_storage.py:153](<D:/Serveur IA/lanceur/client_storage.py:153>), [workspace.py:44](<D:/Serveur IA/lanceur/workspace.py:44>) et [workspace.py:278](<D:/Serveur IA/lanceur/workspace.py:278>).

La base principale ajoute la colonne `conversations.archived` lors de son initialisation. La base individuelle reconstruite par `ClientStorage.database()` utilise seulement `SCHEMA`, qui ne contient pas cette colonne. Dès qu’une conversation de projet existe, sa copie tente d’insérer le champ absent.

Reproduction : une première synchronisation réussit ; une conversation est enregistrée dans un projet ; la synchronisation suivante échoue avec `table conversations has no column named archived`. Le worker périodique transforme cette erreur en message générique concernant les droits ou l’espace disque. L’opérateur peut donc chercher la mauvaise cause. La boucle traite tous les clients successivement : un client défectueux peut également retarder ceux placés après lui. La base principale reste l’autorité, mais les copies individuelles promises deviennent périmées.

Correction : partager une initialisation de schéma actuel et ses migrations entre la base principale et les bases exportées. Préserver la reconnaissance des anciens formats de sauvegarde. Ajouter un scénario avec conversation de projet active puis archivée, vérification de la base individuelle et poursuite des exports des autres clients.

**R02 — P1 : une réponse Hermes peut enregistrer un historique incompatible avec Windows et Android.**

Emplacement : [hermes_conversations.py:315](<D:/Serveur IA/lanceur/hermes_conversations.py:315>) et [history_store.py:21](<D:/Serveur IA/client-qwen/history_store.py:21>).

`_project()` ajoute la réponse et vérifie le quota de stockage, mais ne valide pas le nouvel historique avec les limites du contrat client : 1 000 messages par conversation et 9 Mio pour l’historique complet. Ces limites sont indépendantes du quota de 20 Mio par accès.

Deux reproductions réussissent côté agent puis échouent côté client : un historique accepté de 1 000 messages devient un historique de 1 001 messages ; un historique de 8 388 839 octets devient un historique de 9 961 813 octets. Dans les deux cas, la validation locale refuse le résultat. La réponse peut donc bloquer la synchronisation et la reprise de l’historique alors que le journal annonce une demande terminée.

Correction : contrôler la capacité avant admission et appliquer la validation commune avant l’écriture de la projection. Définir un comportement explicite à la limite, par exemple demander une nouvelle conversation, tout en conservant la réponse acceptée et la copie locale. Ne pas tronquer silencieusement les conversations. `history_write()` revalide déjà l’historique après `merge_completed()` ; ce contrôle fournit un précédent à réutiliser pour la projection directe, avec des essais aux limites.

**R03 — P1 : les copies de conversations Hermes contournent les quotas et finissent par bloquer les sauvegardes.**

Emplacement : [hermes_conversations.py:255](<D:/Serveur IA/lanceur/hermes_conversations.py:255>), [workspace.py:317](<D:/Serveur IA/lanceur/workspace.py:317>) et [hermes_backup.py:187](<D:/Serveur IA/lanceur/hermes_backup.py:187>).

`agent_runs` conserve les messages de chaque demande, son entrée et sa sortie ; `agent_conversations` conserve une autre copie visible. Aucune rétention de ces deux tables n’est implantée. `Workspace.usage()` ne les compte pas. La répétition d’un historique complet à chaque tour provoque également une croissance cumulative disproportionnée pour une longue discussion. Les profils et sessions natifs s’ajoutent à ce stockage.

Reproduction sans sauvegarde d’historique client : six demandes de 2 Mio produisent une base d’intégration de **39 923 712 octets**, tandis que l’utilisation canonique de cet accès reste à **0 octet**. L’export Hermes refuse ensuite cette base, car la limite est de 32 Mio par fichier et de 64 Mio pour l’ensemble. Les archives Fred incluent Hermes : cette condition peut donc faire échouer une sauvegarde serveur complète. Il s’agit d’un échec de capacité et de sauvegarde, pas seulement de quelques fichiers inutiles.

Correction : intégrer l’espace Hermes au calcul et à l’admission des quotas ; conserver un journal d’idempotence borné et dédupliquer les transcriptions ; définir une conservation documentée pour les sessions et conversations supprimées ; adapter le format de sauvegarde à la capacité réellement autorisée. Augmenter uniquement la limite de 32 Mio reporterait le problème. Prévoir la compaction SQLite après nettoyage, car supprimer des lignes ne réduit pas nécessairement immédiatement la taille du fichier.

**R04 — P2 : un ancien appel MCP peut recevoir le contexte du tour suivant.**

Emplacement : [hermes_inference.py:78](<D:/Serveur IA/lanceur/hermes_inference.py:78>) et [hermes_accounts.py:178](<D:/Serveur IA/lanceur/hermes_accounts.py:178>).

Les appels `tools/call` utilisent une clé persistante du profil et le contexte actif du propriétaire à leur arrivée. Ils ne portent pas une identité de tour vérifiée. Le raccordement web natif contrôle déjà son `run_id` ; les outils documentaires Fred n’ont pas le même contrôle.

Reproduction avec un même accès et deux projets : le premier tour est annulé ; un second tour commence dans un autre projet ; l’appel ancien `fred_workspace_info` arrive avec la clé du profil. Il reçoit HTTP 200 et les informations du **nouveau projet**. Le problème concerne ici l’isolation entre conversations et projets d’un accès, ainsi que la fidélité des sources et de l’annulation.

Correction : lier chaque appel documentaire et d’inférence au tour natif accepté, avec une identité vérifiée avant et après exécution. Vérifier le comportement avec le transport MCP réel d’Hermes, y compris les appels retardés, plutôt que de se fier uniquement à l’existence d’un contexte actif.

**R05 — P2 : les images des messages précédents disparaissent lorsqu’une session Hermes est reconstruite.**

Emplacement : [hermes_conversations.py:57](<D:/Serveur IA/lanceur/hermes_conversations.py:57>) et [hermes_conversations.py:268](<D:/Serveur IA/lanceur/hermes_conversations.py:268>).

`visible_messages()` transforme les contenus multimodaux en texte. Cette projection est ensuite utilisée comme `conversation_history` d’une nouvelle session native. L’image du dernier message est préservée, mais les images des messages antérieurs sont perdues. La reconstruction intervient notamment après import, changement de modèle ou changement de périmètre. La comparaison utilisée pour décider de continuer une session ignore également les différences entre images lorsque leur texte reste identique.

Reproduction : Fred reçoit une conversation dont un message précédent contient texte et image ; le corps remis au service natif contient **0 image historique** et seulement « Décris cette image ». La réponse suivante ne peut plus relire cette pièce jointe.

Correction : séparer la projection textuelle destinée à l’historique affiché du transcript multimodal destiné au modèle. Conserver les pièces jointes autorisées dans les reconstructions et inclure leurs empreintes dans la décision de continuité. Tester un changement de modèle compatible avec les images, puis une reconstruction après import.

**R06 — P2 : modifier une mémoire de projet facture à nouveau tout son contenu dans le quota.**

Emplacement : [workspace.py:622](<D:/Serveur IA/lanceur/workspace.py:622>).

`memory_save` vérifie l’ajout de la taille complète de la nouvelle mémoire. La mémoire précédente est déjà comptée. Les autres opérations comparables, dont les mémoires personnelles, calculent correctement la différence de taille.

Reproduction : une mémoire de 1 500 octets existe, il reste 1 000 octets disponibles, puis son contenu identique est enregistré. Le serveur refuse l’opération pour dépassement de quota alors que la variation réelle vaut **0 octet**. Une réduction de contenu peut également être refusée.

Correction : vérifier `max(0, taille_nouvelle - taille_ancienne)`. Tester une modification identique, une réduction et une augmentation près du quota.

**R07 — P2 : `Install-EG2.ps1` ne se parse pas sous PowerShell 7.**

Emplacement : [Install-EG2.ps1:8](<D:/Serveur IA/Install-EG2.ps1:8>).

Le message `'Création de l’environnement EG2 impossible.'` contient une apostrophe typographique que PowerShell reconnaît comme délimiteur. Le parseur PowerShell 7.6.5 relève quatre erreurs, dont un jeton inattendu et une chaîne non terminée. Le script ne peut pas démarrer sous ce moteur, même lorsque le chemin de création de l’environnement ne sera pas exécuté.

Nuance vérifiée : `powershell.exe` 5.1 parse actuellement le fichier sans erreur, du fait de son interprétation de l’encodage du fichier. Le défaut observé concerne PowerShell 7 et la lecture explicite de la source UTF-8. L’audit a analysé le script sans lancer son installation.

Correction : employer une chaîne à guillemets doubles ou échapper correctement l’apostrophe, et tester systématiquement les scripts avec les versions PowerShell officiellement prises en charge.

**Optimisations utiles après les corrections.** Ces éléments ont été séparés des défauts reproduits pour éviter de présenter une hypothèse de performance comme une panne certaine.

1. **Réduire les copies en mémoire pendant sauvegarde et restauration.** Le test de volume existant, relancé pendant l’audit, restaure correctement 16 Mio de documents, mais mesure une augmentation maximale de RAM d’environ **395 Mio** sur l’ensemble sauvegarde/restauration. Il passe son seuil actuel d’un Gio. Les sérialisations SQLite, JSON, base64, chiffrement et points de retour créent plusieurs représentations complètes. Examiner leur durée de vie et mesurer des jeux de 64/128 Mio avant de changer le format cryptographique. Cette mesure ne justifie pas une extrapolation linéaire à tous les volumes.

2. **Réduire les reconstructions périodiques complètes.** [ClientStorage.snapshot():123](<D:/Serveur IA/lanceur/client_storage.py:123>) lit les tables de chaque client ; l’index de [Knowledge.source_records():99](<D:/Serveur IA/lanceur/knowledge.py:99>) relit les sources. Ces opérations se répètent environ toutes les quinze secondes et acquièrent des verrous du stockage principal. Une invalidation par propriétaire et par révision permettrait de diminuer les lectures et le hachage. Le besoin de snapshots cohérents doit être conservé. Le coût réel en production reste à mesurer.

3. **Appliquer une conservation au cache des mises à jour Android.** [AndroidUpdates.java:52](<D:/Serveur IA/client-android/app/src/main/java/net/karenax/fred/AndroidUpdates.java:52>) oublie l’APK déjà installé dans son état, sans supprimer les anciens fichiers du dossier privé `updates`. Chaque empreinte crée un nouveau fichier. L’APK publié actuel pèse 18 903 316 octets. Garder seulement le paquet en attente d’installation et, si nécessaire, un retour explicitement choisi empêcherait cette accumulation. Ce constat vient du code ; les cycles de mise à jour n’ont pas été rejoués sur un appareil physique pendant l’audit.

4. **Uniformiser les limites des serveurs HTTP locaux.** La passerelle distante et le client Windows disposent d’un délai de trente secondes et d’un nombre de workers borné. [app.py:522](<D:/Serveur IA/lanceur/app.py:522>) et [hermes_inference.py:185](<D:/Serveur IA/lanceur/hermes_inference.py:185>) utilisent un `ThreadingHTTPServer` sans protection équivalente. Une connexion locale qui ne termine pas ses en-têtes peut immobiliser un thread sans échéance applicative. Réutiliser les limites existantes, en tenant compte des flux SSE longs. Ces deux services écoutent sur loopback ; ce point n’est pas présenté comme une exposition anonyme sur Internet.

5. **Découper les chemins complexes autour des contrats.** `serve_gateway` compte 554 lignes, son `do_POST` 374, et `Workspace._action` 172. Isoler progressivement lecture/validation JSON, autorisation, admission et réponses par domaine faciliterait les vérifications. Il faut conserver l’ordre des verrous, les contrôles de révocation et les traitements d’annulation : une réécriture globale présenterait plus de risques qu’une extraction progressive couverte par les tests actuels.

**Code inutile ou hérité à traiter.** Ruff relève 33 imports inutilisés et 7 variables locales inutilisées dans les 99 fichiers Python applicatifs et utilitaires examinés, plus des remarques de style et de gestion des exceptions. Les détails sont dans [ruff.json](<D:/Serveur IA/audits/2026-10-12/ruff.json>). Aucun nom indéfini n’est relevé dans ce périmètre.

Les candidats simples comprennent `mimetypes` dans `app.py`, `urlsplit` et `validate_endpoint` dans le client, `base64` dans `accounts.py`, et plusieurs anciens imports de gestion de processus dans `operations.py`, `remote.py` et `releases.py`. Leur suppression doit être vérifiée individuellement : une importation peut servir à une compatibilité publique ou à un effet d’initialisation. Vulture signale aussi le paramètre `unused` d’un callback WinMM ; son emplacement dans la signature est requis par l’API native et ne doit pas être supprimé comme un simple argument facultatif.

L’ancien système [Accounts.login():47](<D:/Serveur IA/lanceur/accounts.py:47>), `valid()` et `logout()` n’est plus appelé par les chemins applicatifs actuels. La passerelle accepte l’accès personnel et ignore la session `X-Qwen-Session`, conformément au fonctionnement décrit pour les clients sans login. L’objet sert encore à la métadonnée, à l’invalidation et à la compatibilité des sauvegardes. Simplifier cette couche pourrait supprimer le calcul scrypt factice à chaque initialisation et clarifier le contrat ; supprimer les comptes sauvegardés sans migration serait une mauvaise correction.

Plusieurs scripts de génération ou de livraison ancienne demeurent dans les dossiers applicatifs : `deploy_v2.py`, `refondre_interface.py`, `integrate_workspace_assets.py`, `finalize_workspace_sources.py`, ainsi que `client-qwen/ui-syntax-check.js`, qui contient une ancienne copie du chat. Les déplacer vers un dossier de maintenance daté et documenté, après inventaire des appels, réduirait le risque de rejouer une transformation dépassée. Préférer une extraction syntaxique des sources actuelles, comme le fait l’outil de cet audit, à une copie manuelle du JavaScript.

Les dossiers `recherche`, `comparatifs` et `preuves` regroupent 1 926 des 2 624 fichiers suivis. Ils servent à la traçabilité et aux essais antérieurs ; leur présence ne prouve pas que du code mort s’exécute en production. Un index des expériences actives et historiques est plus utile qu’une suppression générale. Le dépôt suivi représente environ 42 Mio : son encombrement Git n’est pas le problème prioritaire.

**Contexte, documentation et reproductibilité.** Le README et le contexte principal indiquent correctement Windows 3.5.27 et Android 1.0.10/code 11, ce qui correspond aux manifestes contrôlés. En revanche, [lanceur/LISEZ-MOI.txt:144](<D:/Serveur IA/lanceur/LISEZ-MOI.txt:144>) présente encore 3.2.1 comme version actuelle et [PLAN-GLOBAL-SERVEUR-FRED.md:13](<D:/Serveur IA/PLAN-GLOBAL-SERVEUR-FRED.md:13>) décrit la livraison 3.5.24/Android 1.0.7 comme publiée. Marquer ces passages comme historiques ou les actualiser éviterait des reprises sur une information contradictoire. Le contexte actuel mêle également état en service et nombreuses étapes de livraison : conserver en tête une fiche courte du fonctionnement actuel et déplacer le journal détaillé dans un historique faciliterait sa lecture.

Les dépendances Python directes sont épinglées et les patchs des moteurs sont fidèles, ce qui est positif. La reconstruction complète dépend néanmoins de chemins et outils locaux exclus du dépôt. Plusieurs essais navigateur référencent `C:/Users/karen/.cache/...`, et les builds supposent des runtimes, NDK, CUDA et compilateurs déjà présents. Une procédure vérifiable de préparation et un manifeste des versions réellement utilisées par chaque livraison, y compris Hermes, amélioreraient la reproductibilité. L’absence de conflits signalés par `pip check` ne constitue pas un audit des vulnérabilités publiées de toutes les dépendances ; aucune conclusion d’absence de CVE n’est tirée ici.

**Protections examinées.** Les données et secrets privés sont exclus du dépôt ; les copies Windows utilisent DPAPI et Android utilise le keystore/AES-GCM. Les mises à jour Windows contrôlent le manifeste Ed25519 et l’empreinte du binaire ; Android contrôle empreinte, identité du paquet, version et certificat de signature. Les routes de client et de passerelle contrôlent les origines et les clés, les révocations persistent à travers les restaurations, et les sauvegardes vérifient les archives avant publication. L’extraction des documents est isolée avec bornes de temps et de mémoire. Les lectures web héritées fixent l’adresse IP vérifiée et les outils natifs ajoutent des protections de destination et de redirection. Le rendu Markdown et les politiques CSP sont couverts par des scénarios réussis.

La recherche de formes courantes de jetons dans les fichiers textuels suivis, hors données de tokenizer, n’a retourné aucun candidat. Cette recherche ne garantit pas l’absence de tout secret, notamment dans les images et l’historique Git. Bandit a produit 270 signalements bruts, dont 54 classés moyens ; ils ne sont pas 270 vulnérabilités confirmées. Les concaténations SQL utilisent dans les chemins examinés des tables et champs contrôlés et des valeurs liées, `UniqueLoader` dérive de `yaml.SafeLoader`, et les `exec` observés chargent des adaptations locales déterministes. Les résultats bruts restent disponibles dans [bandit.json](<D:/Serveur IA/audits/2026-10-12/bandit.json>).

**Ordre de correction proposé.**

1. Corriger R01 et vérifier que chaque dossier client est remis à jour, y compris ceux comprenant une conversation de projet archivée.
2. Corriger R02 et proposer une récupération explicite des historiques éventuellement déjà hors contrat, avec conservation préalable des données.
3. Corriger R03 : inventorier les tailles et définir quotas, déduplication, conservation et sauvegarde Hermes avant tout nettoyage.
4. Corriger R04 et R05 en vérifiant le transport natif et les conversations multimodales réelles.
5. Corriger R06 et R07, puis nettoyer les imports et les anciens scripts.
6. Mesurer et optimiser ensuite mémoire des sauvegardes, reconstruction des index et caches de mises à jour.

Les rapports complets, compteurs, journaux et captures produits pendant cet audit sont dans [le dossier de preuves](<D:/Serveur IA/audits/2026-10-12>). Les limites restantes concernent notamment les essais Android sur appareil physique, un rebuild complet des binaires publiés, une nouvelle mesure d’inférence GPU et un examen exhaustif du code tiers. Aucun arrêt du modèle ou changement des comptes de production n’était nécessaire à ces vérifications.
