# Corrections de l’audit global Kiara — 26 octobre 2026

Ce dossier applique les 17 constats de [l’audit du 25 octobre](../../audits/2026-10-25-global/RAPPORT.md). Les corrections portent sur le produit, ses constructions, les contrôles et la documentation. Les observations initiales restent conservées dans l’audit ; les preuves ci-dessous décrivent le nouvel état.

## Changements par constat

| Constat | Correction apportée | Preuve principale |
|---|---|---|
| F01 | Une seule implémentation des souvenirs pour les deux protocoles. Révision obligatoire pour modifier/supprimer ; brouillon conservé en cas de conflit et rechargement explicite. | `lanceur/test_command_boundaries.py`, `client-qwen/test_ux_recovery_ui.cjs` |
| F02 | Journal daté borné, limite durable empêchant le rejeu des reçus compactés, réserve séparée pour les anciens identifiants. Oubli et annulation restent possibles à quota plein. | `test_command_boundaries.py`, `test_assistant_voice.py`, `test_hermes_tools.py` |
| F03 | Mise à jour des paquets Python concernés dans les environnements effectivement utilisés ; inventaire et six verrous renouvelés. | `validation-final/python-security.json`, `validation-final/dependencies-2.txt` |
| F04 | Go 1.27.3 épinglé et vérifié, pont reconstruit et inclus dans le nouveau client. Synthèse des avis selon les fonctions appelées. | `validation-final/go-security.json`, manifestes de construction |
| F05 | Constructeur Windows isolé, retrait de PyInstaller de Strata, suppression de l’héritage implicite des paquets Codex, vérification agrégée des six profils. | `validation-final/runtimes-1.txt`, `dependances/verrous/manifest.json` |
| F06 | Six domaines Workspace extraits ; transaction et accès restent centraux. Adaptateurs HTTP séparés pour commandes, embeddings et flux vocaux. | `lanceur/workspace_*.py`, `lanceur/gateway_*.py`, tests serveur |
| F07 | Paquet installable `kiara-shared` ; imports directs du serveur, alias Windows compatibles. Inclusion explicite dans l’exécutable et vérification du paquet gelé. | `shared/pyproject.toml`, `maintenance/check_windows_artifact.py`, test natif Windows |
| F08 | Adaptations Android déclaratives par emplacements nommés, contrôle d’unicité et capacités de plateforme explicites. | `client-android/tests/test_platform_contract.py`, 15 suites UI partagées |
| F09 | Schéma 2 et migrations connues ; marqueur absent sans effacement des données valides. Cache inconnu conservé dans une archive protégée de récupération. | `test_audit_lifecycle.py`, `test_history_migrations.py`, restauration isolée |
| F10 | Runtime privé Hermes résolu avant le bootstrap personnel ; dépendances conservées explicitement référencées. | `test_audit_lifecycle.py`, `hermes-runtime.json` |
| F11 | Garde d’intention renforcé pour les négations, citations et expressions idiomatiques françaises. | `test_audit_lifecycle.py`, tests des outils et commandes |
| F12 | Snapshots par lots, index composites, mesures bornées de verrou/transaction/snapshot avec médiane et p95. | `test_observability.py`, preuve de volume de la suite serveur |
| F13 | Diagnostics de workers bornés, références de corrélation et catégories d’erreurs ; aucune sortie brute ni contenu de document enregistré. | `test_observability.py`, `runtime_diagnostics.py` |
| F14 | Manifestes par composant, contrôle de cohérence sources/binaires, paquet serveur sans données privées, chemins de données/runtime configurables. Reconstruction et restauration sur dossier isolé. | `maintenance/deployment_manifest.py`, `reconstruction-isolated.json` |
| F15 | Commande de validation unique, résultats agrégés, preuves UI par exécution, arrêt explicite des workers de fixtures. Conservation des échecs initiaux et de leurs contrôles correctifs. | `validation-final/validation.json`, `maintenance/server_evidence.py` |
| F16 | Réception/annulation communes aux deux workers Max ; exigences Phonon canoniques et matrice des compatibilités conservées. | `test_worker_protocol.py`, `client-voice/COMPATIBILITE.md` |
| F17 | Index courant d’architecture et versions, reconstruction actualisée ; deux outils ponctuels dangereux archivés avec entrées historiques inoffensives. | `ARCHITECTURE-ACTUELLE.md`, `historical/`, `RECONSTRUIRE-FRED.md` |

## Compatibilité et décisions

Les anciens clients restent reconnus par négociation. Ils doivent être actualisés pour modifier les souvenirs avec une révision. Le passage aux identifiants datés est annoncé par le serveur et l’horloge du client est corrigée avec son heure. Les reçus opaques existants restent conservés ; ils ne sont pas convertis en identifiants réémis à chaque tentative.

Les sauvegardes de générations connues sont validées avant migration. Les modèles, caches utiles, clés et anciens packs ne sont pas supprimés pour nettoyer l’arborescence. Le partage de répertoires de dépendances Hermes reste documenté : leur existence est un prérequis, même si le bootstrap personnel n’est plus appelé.

Le découpage conserve un monolithe modulaire. Les frontières et les duplications identifiées sont corrigées ; cela ne signifie pas que toute fonction longue ou tout couplage du dépôt a disparu. Les mesures ajoutées permettent de suivre la contention avant de choisir une nouvelle optimisation.

## Validation et incidents trouvés pendant la livraison

Les résultats consolidés sont dans `validation-final/validation.json`. Les journaux d’échecs et les premiers essais restent conservés pour rendre les corrections vérifiables.

Le premier exécutable reconstruit omettait `kiara_shared`, malgré une construction PyInstaller réussie. Le test de l’exécutable a détecté l’erreur également signalée par l’utilisateur. La construction utilise désormais un chemin de paquet explicite, collecte ses modules et vérifie l’archive embarquée avant de lancer le test natif. Ce contrôle bloque la signature d’un client incomplet.

Le nouveau format d’identifiant a aussi révélé une validation de 32 caractères restée dans l’aide d’authentification Hermes. Elle accepte maintenant les deux générations. Un véritable appel natif avec transport MCP vérifie le format daté ; les autres tests conservent la génération historique.

La suite complète de 579 tests serveur a signalé deux échecs dans son dernier passage : vérification d’une distribution précédente devenue incohérente avec la nouvelle version, et attente de tâche limitée à dix secondes pendant des synchronisations disque lentes. Le premier contrôle est rejoué avec le nouvel exécutable dans une distribution de test isolée ; l’attente fonctionnelle dispose d’un délai adapté, sans modifier les seuils du benchmark de volume. Le bilan conserve le résultat initial et exige la réussite nominative de chaque contrôle rejoué. Une suite interrompue ou un échec non couvert restent bloquants.

## Limites de qualification

- Reconstruction et restauration sur un dossier et un environnement Python neufs du même hôte ; aucune panne matérielle réelle ni restauration destructive de production simulée.
- Pas de nouvelle qualification au microphone, sur téléphone Android physique ou en Bluetooth. Les tests du pack et du client n’ouvrent pas le microphone.
- Aucun test d’intrusion depuis Internet ni garantie générale d’absence de vulnérabilité. L’analyse de dépendances concerne les versions réellement inventoriées à la date du contrôle.
- Le filtrage linguistique couvre les cas testés ; il ne constitue pas une compréhension exhaustive de toute formulation française.
- Les interventions concomitantes concernant la résidence des modèles en RAM ont leurs propres preuves dans `maintenance/2026-10-26-ram-verrouillee`. Leurs changements sont conservés.

## Retour et historique

Les changements utilisateur déjà présents ont été contrôlés par empreintes (`preexisting-files.json`, `line-endings.json`). Aucun commit ou nettoyage global n’a écrasé ces travaux. Les distributions précédentes et les clés existantes doivent être conservées lors de la publication. Une base déjà migrée ne doit pas être confiée à un ancien serveur sans restauration de sa sauvegarde compatible.

Les scripts `extract_*`, `apply_memory_consolidation.py` et `migrate_ui_platform_slots.py` retracent des transformations ponctuelles déjà appliquées : **ne pas les relancer** sur les sources actuelles. Les commandes réutilisables sont dans `maintenance/verify_project.py`, `package_server.py`, `deployment_manifest.py` et `RECONSTRUIRE-FRED.md`.

## Livraison vérifiée

Kiara et Windows **3.5.53**, Android **1.0.24 / code 25** et le pack vocal **vocal-rt-de5e67a320a06b1f** sont publiés. Le pack Max déjà installé sur le serveur a également été actualisé par son installateur. Son test natif de reconnaissance et de synthèse est fonctionnel ; ses workers ont ensuite été déchargés. Le microphone et les haut-parleurs ne sont pas utilisés par ce contrôle.

La sauvegarde chiffrée préalable a été vérifiée et copiée sur le NAS. Les clés, profils, données, programmation des sauvegardes et processus du modèle ont été comparés avant/après : ils sont conservés. Les distributions précédentes et la configuration antérieure du pack serveur sont conservées pour le retour.

Preuves : [activation](production.json), [publication](publication.json), [téléchargements réellement servis](served-release-validation.json), [sauvegarde préalable](sauvegarde-avant.json), [qualification du pack serveur](server-voice-installation.json), [intégrité des deux ponts de l’APK](android-native-validation.json), [reconstruction avec extraction et restauration](reconstruction-isolated.json) et [manifestes et validation](deployment.json).

Les quinze suites UI fonctionnelles sont validées. Le lanceur Node affiche seize fichiers réussis car son inventaire inclut aussi le module d’aide aux répertoires de preuves ; celui-ci n’est pas compté comme une suite fonctionnelle dans ce rapport. Les avertissements UX existants restent des points de revue, sans suppression automatique de contenu.

La première reprise stricte du lint Android a atteint son délai pendant des lectures de bibliothèques Java. Son journal est conservé. Après correction de la préparation PowerShell, du délai et de l’arrêt des processus de vérification expirés, la reprise termine correctement en 80 secondes. Cela ne constitue pas un test de charge représentatif de tous les usages.
