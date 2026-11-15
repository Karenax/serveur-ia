# Améliorations opérationnelles — Agent 0.4.0

Point de sauvegarde vérifié du 21 octobre 2026 — audit r76 : 144 692 fichiers
du projet relus par empreintes, 27,94 Go logiques dans deux parties ZIP de 9,29 Go,
dépendances web liées incluses. Les données courantes comprennent 1 805 pièces ;
leur restauration neuve conserve les 19 tables contrôlées, avec intégrités OK et
aucune violation de clé étrangère. Le correctif SQLite produit ce point sans
réparation manuelle du manifeste. Les archives précédentes restent conservées.

L’index choisit les payloads actuels ; les WAL/SHM sont consolidés dans les bases
autonomes et les références de jonctions historiques restent documentées. Les
neuf tests et dix sous-tests du restaurateur passent ; trois fichiers réels sont
extraits et comparés. L’extraction intégrale du projet et le démarrage de la copie
restaurée ne sont pas prétendus. Agent actif reste sain, ses fichiers servis et
les lignes métier préexistantes sont vérifiés. Instructions `RESTORE.md` dans le
point `.ui-preview/backups/current-complete-20261021-63b0d9bb14fc`.

Cette preuve clôture le contrôle de ce point de sauvegarde, sans fermer un lot
audio ou L12 : 9/13 lots, 19/25 fonctions et 15/17 recettes restent qualifiés.
Preuve : `logs/foresight-runtime/CURRENT-COMPLETE-CHECKPOINT-ROOT-20261021.json`.

Historique des observations précédentes :

Sauvegardes SQLite du 21 octobre 2026 — audit r75 : défaut réel reproduit,
les connexions non fermées explicitement laissaient entrer des WAL/SHM temporaires
dans le manifeste. Les copies sont désormais fermées explicitement et autonomes
en mode DELETE ; le mode de journal des bases sources reste inchangé. Les 70 tests
du candidat puis les 70 tests de production passent, dont cinq régressions nouvelles.

Une nouvelle sauvegarde des données actuelles, produite par ce code sans réparation
manuelle du manifeste, se restaure dans une copie neuve : 19 tables vérifiées,
intégrités OK, aucune violation de clé étrangère, notes et pièces validées.
L’archive du projet reste distincte : la partie déjà copiée est conservée et son
verrou de superviseur nécessite une reprise indexée. Aucun fichier ou module
fonctionnel supprimé ; aucun microphone ou modèle ouvert par ces contrôles.
Preuve : `logs/foresight-runtime/PORTABLE-SQLITE-BACKUP-FIX-ROOT-20261021.json`.
État de la copie complète : `.ui-preview/pilots/current-complete-backup-20261021/live-progress.json`.

Historique des observations précédentes :

État courant du 21 octobre 2026 — audit r69 : le Studio signale une capture
native arrêtée ou d’état inconnu même avant la mise à jour SQL, dans le titre
et la ligne sélectionnée. Il ne modifie pas l’état durable et ne déclenche aucune
commande ; le brouillon reste conservé. Deux régressions échouent avant correction,
157 contrôles ciblés puis les 988 tests frontend complets passent après correction.
TypeScript/Vite et les octets servis sur 8001 sont vérifiés, anciens assets conservés.

Le superviseur corrigé est maintenant chargé par une nouvelle instance. Les bases
Brain/ERP sont sauvegardées avec intégrité vérifiée et les lignes préexistantes de
19 tables contrôlées sont conservées. Une nouvelle suite backend complète tourne
sur les 479 sources figées ; son résultat est encore attendu. Le diagnostic audio
Jabra continue dans la même séance initiale autorisée, sans nouvelle lecture
demandée, transcription ou LLM. L’interruption intermittente et le retard de son
état durable ne sont pas déclarés corrigés. L12 reste ouvert ; décomptes inchangés
9/13 lots, 19/25 fonctions, 15/17 recettes.

Preuve : `logs/foresight-runtime/STUDIO-NATIVE-PROCESS-STATE-ROOT-20261021.json`.

Historique des observations précédentes :

## Publication de l’état sous Windows — 21 octobre 2026

Une lecture concurrente de `state.json` peut faire échouer son remplacement
atomique avec `PermissionError`, WinError 5. Le défaut a été reproduit avec un
vrai lecteur Windows maintenu ouvert. `write_state` réessaie désormais uniquement
les refus Windows 5, 32 et 33, toutes les 10 ms pendant au plus cinq secondes.
L’ancien snapshot reste lisible ; les autres erreurs et les refus persistants
remontent toujours. Aucun remplacement non atomique ni élargissement des droits.

Les tests couvrent lecteur réel, remplacement après fermeture, refus persistant
et erreur étrangère. La cohorte de 41 tests passe après correction. Le global
antérieur reste à trois échecs : la disparition de son superviseur peut être liée
à ce défaut, mais son stderr d’origine est indisponible et cette causalité n’est
pas démontrée. Le test conserve maintenant stderr en cas de sortie inattendue.
Le processus canonique déjà lancé n’a pas encore été redémarré avec ce code.
Preuves : `.ui-preview/pilots/backend-terminal-fixes-20261021/` et
`logs/foresight-runtime/HARDWARE-HUMAN-READBACK-ROOT-20261021.json`.

## Supervision du backend

Le 10 octobre 2026, les deux lanceurs Windows passent par
`scripts/agent_runtime.py start`. Le superviseur indépendant lance uniquement
`app.main:app` depuis `C:\Agent`, sur `127.0.0.1:8001`, et attend la sortie du
processus avant sa relance. Les lanceurs transmettent les réglages existants ;
une valeur explicite `AGENT_DOCUMENT_JOBS_ENABLED=0` reste prioritaire.

Le délai de relance part de 5 secondes, augmente en cas d'échecs rapprochés et
reste borné à 60 secondes. Verrou de fichier détenu par le système d'exploitation,
état JSON écrit atomiquement, journaux des PID/codes de sortie et sorties Uvicorn
séparées. Un écouteur préexistant sur 8001 n'est ni arrêté ni adopté : le superviseur
attend sa disparition. XPilot sur 8000 reste indépendant.

`python scripts/agent_runtime.py status` consulte l'état et la disponibilité TCP ;
`stop` envoie une demande liée à l'instance courante afin d'empêcher sa relance
volontaire. La commande arrête uniquement le backend enfant de cette instance.
L'état du processus et du port ne constitue pas un contrôle du résultat des workers.
Les erreurs natives et arrêts forcés seront désormais visibles dans
`logs/runtime/backend.err.log` et `logs/runtime/supervisor.log` ; la cause des
arrêts historiques n'est pas établie par les anciens journaux.

Le raccourci existant du dossier Démarrage Windows pointe vers
`C:\Agent\start-agent-task.cmd` et bénéficie de ce changement à la connexion.
Cette livraison n'ajoute ni service Windows ni supervision du superviseur lui-même.
Les tests `tests/test_agent_runtime.py` utilisent des enfants et un port fictifs,
sans ouvrir les bases de production. Ils vérifient deux sorties avec code 7,
la troisième exécution, le refus d'une seconde instance et l'arrêt sans relance.

Activation vérifiée : serveur HTTP et bases Brain/ERP disponibles, démarrage
répété sans doublon, 4 tests ciblés réussis, Ruff et `git diff --check` conformes.
Sauvegarde hors ligne : 1 356 empreintes revérifiées et intégrité des deux copies
SQLite. Preuve : `logs/runtime-activation-20261010/verification.json`.
La suite générale a été interrompue après l'échec préexistant reproduit séparément
de `test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint` :
le test attend aucun classement alors que le candidat à 0,75 est sélectionné.
Les fichiers de tri concernés sont identiques à HEAD ; aucun changement de règle
mail n'est inclus et aucune réussite de la suite complète n'est revendiquée.

Livraison locale du 2 octobre 2026. Changements non committés et non poussés.
Un seul serveur Agent sur 127.0.0.1:8001 ; XPilot :8000 reste externe.

## Périmètre et conservation

Sur décision explicite de l’utilisateur, le code financier dédié est retiré :
taux horaires, marges, calculs de prix, chiffrage des éléments, onglet Ventes,
génération d’offres et montants des vues Atelier. Les anciens endpoints d’offre
et de chiffrage sont absents ; les champs financiers sont refusés par les PATCH
actifs. Les colonnes historiques, payloads Sage, archives, anciens fichiers et
données des deux bases sont conservés. Aucune suppression de lignes n’a lieu.
CDC, CDC & BE, Revues, Atelier et Import Sage restent disponibles.

## Changements vérifiables

| Domaine | Résultat |
|---|---|
| Pilotage | Heures prévues, consommées, RAF calculé ou réestimé ; éléments rejetés/remplacés exclus |
| Actions | Tâches en retard, échéances et jalons à 14 jours, revues, points ouverts, analyses à reprendre, décisions de connaissance |
| Analyse CDC | File SQLite durable, worker unique, sauvegarde atomique du lot et de son checkpoint, annulation entre lots et reprise |
| Transfert BE | Nouvelle version à chaque génération, fichier distinct, snapshot technique et SHA-256 ; historique relisible |
| Mails | Recherche auteur/sujet/code/texte intégral sans accents, tri stable côté serveur et total filtré avant pagination |
| Assistant | Classement pertinent des extraits, répartition entre projets, avertissement de couverture partielle |
| Performances | Requêtes SQL groupées du portefeuille, preuves CDC chargées en lot, détails projet parallélisés, liens Brain issus du portefeuille |
| React | Revue CDC, réglages, Atelier et nouveaux panneaux extraits ; contrats API typés et protection contre réponses périmées |
| Exploitation | Sauvegarde ERP uniquement avant migration, état des copies/espace disque, vérification SHA-256/SQLite, logs bornés et lanceur portable |
| CI | Tests des deux extensions inclus dans le workflow Windows |

## Usage et limites

Le RAF automatique représente un solde de charge, pas une nouvelle estimation
du travail restant. Le champ de réestimation dans Modifier remplace ce solde ;
le laisser vide rétablit le calcul. Les pointages Sage et manuels s’additionnent :
ne pas saisir deux fois le même temps. Les heures fractionnaires sont conservées.

La fermeture d’une fenêtre n’arrête pas une analyse. Une erreur ou une annulation
affiche Reprendre ; les lots validés ne sont pas rejoués. Après redémarrage du
serveur, les analyses interrompues reprennent automatiquement. Les archives et
restaurations marquent les jobs actifs `interrupted` pour exiger une reprise
humaine. Une requête LLM en cours finit ou expire avant la prise en compte de
l’annulation. Le worker est prévu pour un seul processus serveur.

Le transfert final conserve les règles de revue et les contrôles bloquants ; un
brouillon est marqué comme tel. Modifier les exigences puis régénérer ne change
aucun ancien livrable. Les exports projet et sauvegardes globales incluent les
versions. Les anciens fichiers créés avant cette évolution restent sur disque,
sans être convertis automatiquement en versions.

Les copies de migration ne remplacent pas une sauvegarde coordonnée. Le bouton
des Réglages vérifie la dernière sauvegarde créée hors ligne par
`scripts/agent_backup.py`. Aucune rotation ni suppression automatique des données
ou sauvegardes n’est introduite. Les logs tournent à 5 Mio, trois copies maximum.

## Validation

Les tests utilisent uniquement des bases et fichiers temporaires. Les preuves
couvrent les heures/RAF et la conservation financière, les requêtes indépendantes
du nombre de projets, la recherche avant pagination, le contexte multiprojets,
la reprise des lots et l’annulation, les versions immuables et leur portabilité,
le tableau d’actions, l’absence de sauvegarde à chaque démarrage et la détection
de corruption d’une sauvegarde.

Résultats locaux :

- `python -m pytest tests/ -q` : 102 passés, 1 ignoré ; avertissements de dépréciation des dépendances.
- Après la correction des timestamps UTC constatée à l’écran : 11 tests opérationnels repassés avec succès.
- `python -m ruff check app backend/app tests scripts` : réussi.
- `npm test` : 16 tests React réussis.
- `node --test tests/test_extension_core.cjs extensions/thunderbird-agent/core.test.cjs extensions/thunderbird-agent/background.test.cjs` : 6 réussis.
- `npm run build` : TypeScript et Vite réussis ; `web/dist` mis à jour.
- Contrôle visuel sur 18003, avec deux bases fictives et IA désactivée : actions,
  heures 16 prévues / 4 consommées / 12 restantes, modules conservés, file CDC,
  génération d’un brouillon versionné. Correction du tableau trop large et des
  timestamps UTC (SQLite perd l’information de fuseau horaire).

Les ports 8000 et 8001 et les données de production n’ont pas été utilisés par
ces vérifications. À la fin des tests, l’application en cours d’exécution n’avait pas été redémarrée.

## Mise en service locale

Sur demande de l’utilisateur, le serveur a été relancé le 2 octobre 2026 avec
le code 0.4.0 de ce worktree, en conservant la base Brain et le stockage de
`C:\Agent`, ainsi que la base ERP existante. Une sauvegarde coordonnée de 302
fichiers a été créée hors ligne dans `%LOCALAPPDATA%\Agent\backups`, puis vérifiée
par SHA-256, intégrité SQLite et clés étrangères. Le serveur fonctionne sur
127.0.0.1:8001 : `/health` annonce les deux bases saines, OpenAPI annonce 0.4.0
et l’interface compilée correspond à cette livraison. Deux projets conservés
dans chaque base. XPilot :8000 reste inchangé.

Le processus est lancé sans fenêtre avec `python.exe` et redirection des sorties
dans `%LOCALAPPDATA%\Agent\logs`. L’ancienne configuration de lancement automatique
Windows n’est pas modifiée ; le prochain démarrage automatique utilisera encore
son checkout habituel tant que cette livraison n’y est pas intégrée. Les
changements de code restent non committés et non poussés.

## Identité du dossier affaire — 5 octobre 2026

Le nom du dossier sélectionné est prioritaire pour l’identité du projet.
`V:\06 - AIRBUS LT\AIRB26LTH0205-A - LED 2026` fournit le code
`AIRB26LTH0205-A` et le titre `LED 2026`. Un ancien TDAO contenant
`AIRB23LTH3146-A` ne peut plus les remplacer. Le scan affiche les incohérences
TDAO/TDSP ; l’identité et les heures d’un document contradictoire sont ignorées
à l’import, tout en conservant son lien. Le recours au document reste disponible
si le nom du dossier ne contient pas de code affaire reconnu.

Le scan du dossier réel a été vérifié sur le serveur 8001 : code
AIRB26LTH0205-A, titre LED 2026, avertissement sur le TDAO AIRB23LTH3146-A.
Le projet existant a été rectifié avec son même identifiant après sauvegarde
SQLite dans `.ui-preview/project-identity-safety-1005/erp-before.db` ; aucune
ligne ni donnée métier supprimée. Les heures déjà présentes sont conservées.
Validation backend : 155 tests réussis, 1 ignoré ; Ruff et build réussis.

## Secours IA local LM Studio

Agent conserve le serveur distant comme IA principale. En cas de connexion refusée,
délai réseau dépassé ou erreur HTTP 502/503/504, les appels texte, JSON, classement
et flux avant le premier fragment basculent sur le modèle local configuré. Le retour
au serveur principal est vérifié lors du prochain appel après 30 secondes.
Les erreurs de configuration, refus 401/403 et réponses invalides restent visibles.

### Décharger le secours au retour du LLM réseau — 12 octobre 2026

Une génération distante réussie, non vide, confirme le retour du principal.
Agent décharge alors les instances du seul modèle de secours configuré, après
les générations locales en cours. Le modèle principal, les autres modèles
locaux et le serveur LM Studio restent disponibles. Le même modèle local peut
être rechargé normalement si le réseau tombe de nouveau.

Le gestionnaire utilise l'[API officielle LM Studio](https://lmstudio.ai/docs/developer/rest/unload)
`POST /api/v1/models/unload` avec chaque `instance_id` obtenu pour la clé exacte
`fallback_model` dans `/api/v1/models`. Il confirme ensuite `loaded_instances=[]`.
Il n'envoie pas la clé du serveur distant à LM Studio. Les appels de gestion
ont un délai de cinq secondes ; l'attente du moteur est bornée à 420 secondes.

Les appels texte/JSON/classement, le flux terminé avec du texte utile et le test
manuel principal déclenchent la décharge. Une connexion TCP, un catalogue de
modèles, une réponse vide, un flux incomplet ou une annulation ne suffisent pas.
Le moteur est réservé avant tout chargement local et pendant la génération ;
`localhost`, `127.0.0.1` et `::1` utilisent la même réservation pour un même port.

Chaque génération observe une version de panne. Une nouvelle panne ou une
sauvegarde des réglages invalide les anciens succès et les décharges en attente.
La sauvegarde des réglages IA est sérialisée avec la gestion locale : un modèle
devenu principal local ne peut pas être déchargé par une ancienne attente.
Un échec de décharge conserve le résultat distant et reste visible dans les
logs et `local_model_release` du diagnostic de routage ; la prochaine réponse
distante utile permet une reprise après trente secondes. Un nouvel usage local
après une décharge reste couvert par les succès distants suivants.

La protection des requêtes concerne Agent ; les usages des autres applications
ne sont pas observés. Les tests `tests/test_ai_recovery_unload.py` couvrent les
instances ciblées, le contenu utile, les annulations, les longues générations,
les changements de réglages, les reprises et la conservation des autres modèles,
sans ouvrir de microphone ni appeler un LLM réel.

Validation du 12 octobre : 18 nouveaux tests et 29 tests existants de
routage/streaming/admission réussis ; Ruff conforme. Après activation sur 8001,
un test réel à 09:08 UTC observe Gemma E4B chargé, la réponse distante « OK »,
puis `loaded_instances=[]` et le diagnostic `unloaded`, sans décharge manuelle.
Le [reçu de recette](../logs/llm-recovery-global-20261012-105917/live-release-with-session.json)
conserve ces états. Le premier essai avait été refusé par le contrôle de session
locale : sa trace et son nettoyage manuel sont conservés ; aucune protection
d'API n'a été retirée. La suite Python globale termine avec 2 158 réussites,
un échec et un test ignoré en 2 700,19 secondes. L'échec du test de tick proactif
est une interférence d'état global : une fermeture de lifespan précédente a
laissé le worker arrêté. L'enchaînement de deux tests reproduit cet échec ;
l'isolation temporaire de son Event d'arrêt le corrige sans toucher au produit.
La reprise du même enchaînement, du routage, du streaming et de l'enrichissement
passe **99 tests**. Les sources de production sont inchangées depuis la passe
globale ; aucune nouvelle passe globale verte n'est annoncée.
Voir le [bilan final](../logs/llm-recovery-global-20261012-105917/final-verification.json).

Préparation complémentaire du 12 octobre, 21:12 UTC : le contrôle de connexion
est raccordé en copie à la libération du secours sans nouvelle génération.
Un GET neuf de `/v1/models`, en six secondes au plus, doit annoncer exactement
le principal configuré ; cache, simple TCP et ancien réglage restent exclus.
L'[API de catalogue LM Studio](https://lmstudio.ai/docs/developer/openai-compat/models)
peut annoncer des modèles téléchargés avec JIT : ce signal ne prouve ni leur
chargement ni une génération utile. Les requêtes locales en cours gardent leur
réservation avant décharge. L'invalidation au commit protège aussi une lecture
commencée pendant l'enregistrement des réglages, y compris une clé d'epoch
créée pendant cette transaction. Le [reçu final ciblé](../.ui-preview/pilots/llm-ready-recovery-stage-20261012/qa/green-211245-47ee2463/qualification.json)
passe 45/45 simulations (18 anciens tests intacts, 27 nouveaux), Ruff et deux
relectures. Le premier candidat 43/43 et ses deux régressions rouges sont
conservés. Le correctif n'est pas activé ; sa globale combinée et sa nouvelle
voie réelle de reconnexion restent à qualifier. La preuve réelle précédente
porte exclusivement sur le retour après une génération utile.

Réglages persistants Brain : `fallback_enabled`, `fallback_base_url`
(`http://127.0.0.1:1234`), `fallback_model` (`google/gemma-4-e4b`),
`fallback_autostart`. L'adresse de secours est limitée au PC ; aucune clé distante
n'est transmise à LM Studio. Le formulaire Réglages IA permet de modifier et tester
le secours séparément du serveur principal. Les sauvegardes des réglages principaux
par les anciens clients préservent les champs de secours.

Le démarrage automatique utilise le CLI installé dans `%USERPROFILE%/.lmstudio/bin/lms.exe`
avec une fenêtre masquée ; le modèle doit déjà être téléchargé. Agent vérifie le serveur
et demande son démarrage/chargement au premier besoin local. Cela ne constitue pas
une installation de LM Studio ni un téléchargement automatique. Les délais d'inférence
existants sont conservés, notamment 45 secondes pour un lot d'analyse projet.

Diagnostic : `GET /v1/settings/ai/routing` (fournisseur/modèle choisis sans clé),
`POST /v1/settings/ai/fallback/test` (réponse réelle du modèle local).
Le bouton de test principal continue à vérifier uniquement le distant.

Le secours vérifie les instances réellement chargées via LM Studio `/api/v1/models`
(`loaded_instances`), et non la simple liste des modèles téléchargés. Un modèle
téléchargé mais absent de la mémoire est explicitement chargé avec `lms load`,
identifiant configuré et contexte de 8192 tokens, avant le premier appel de secours.

## Préparation T11 — coupure physique LAN/Internet, 11 octobre 2026

Un [protocole contrôlé](../.ui-preview/pilots/OFFLINE_PHYSICAL_PROTOCOL.md) et son
contrôleur hors ligne ont d'abord été préparés sans exécution. Les fichiers/runtimes ont
leurs SHA relevés et Gemma-e4b est chargé selon les seules métadonnées locales.
Une approbation humaine séparée est nécessaire avant une coupure manuelle ;
l'essai autorisé ensuite est consigné ci-dessous, sans reprise automatique.
Le script ne modifie ni adaptateur, pare-feu, configuration globale, serveur ou
flags ; il attend puis surveille la coupure LAN/Internet IPv4/IPv6 avant de
reprendre la recette STT/EG2/Gemma sur les seuls fichiers fictifs autorisés.
VPN/PAN ou transport ambigu encore actif bloque le démarrage. Des logs et un
marqueur local indiquent quand reconnecter manuellement, sans dépendre de Codex
pendant la coupure. L'ancien rapport Python est conservé ; aucun résultat de
coupure physique ni « zéro tentative réseau native » n'est annoncé à ce stade.

### Essai autorisé terminé — contrôleur exécuté, aucun moteur lancé

Le contrôleur a été lancé après l'autorisation humaine `call_a6cd279b6ba64dc980ffa7ac6ea77508`.
Le [rapport brut](../.ui-preview/pilots/offline-physical-runs/20261011-213859-2faa854b/qualification.json)
porte `status=aborted`, `passed=false` : délai d'attente de coupure atteint entre
19:38:59 et 19:54:02 UTC, soit 902,83 s avec précheck et polling. Les 192
inventaires sont restés en phase `waiting`, sans gate qualifiée. Le Wi-Fi est
réellement observé déconnecté dans 158 inventaires, de 19:39:35 à 19:52:13 UTC,
puis connecté dans les derniers ; il n'est donc pas resté actif durant tout
l'essai. F5 VPN apparaît Up/Connected dans 192/192 inventaires, sans interface IP
ni route visible : ce transport ambigu bloque le contrôleur conservateur,
sans prouver qu'un accès Internet existait pendant la coupure Wi-Fi.

Aucun enfant de recette, scratch ou rapport STT/EG2/Gemma n'a été créé ; aucune
capture micro/audio système ni génération n'a été lancée par cet essai.
`RECONNECT_NOW.txt` indique explicitement « Aucun enfant n'a été créé ».
La lecture CIM après arrêt ne retrouve ni le PID PowerShell propriétaire 13936
ni ses enfants immédiats ; le code de sortie historique n'a pas été capturé.
Le [reçu de lecture seule](../.ui-preview/pilots/offline-physical-runs/20261011-213859-2faa854b/read-only-timeout-audit-final.json)
conserve les SHA du brut et du JSONL, contrôlés inchangés après audit. Il garde
aussi la première hypothèse d'audit réfutée par le journal complet. Le contrôleur
n'a modifié aucun adaptateur ni réglage applicatif ; aucun redémarrage automatique
n'est effectué. T11 reste **non qualifié** : l'exécution des moteurs sous coupure
physique et les appels natifs n'ont pas été mesurés. La branche WinAPI d'enfant
reste seulement relue statiquement, puisqu'elle n'a pas été atteinte.

### Préparation corrigée — garde structurelle et budget cumulé

La collecte corrigée examine interfaces, adresses et routes dans tous les
compartiments Windows. L'identité virtuelle dormante est explicitement relue
par GUID/PnP/pilote et bindings, avec absence d'IP/interface/route associées ;
le nom F5 ne crée aucune exception automatique. Les transports inconnus restent
refusés. Les routes conservées sur une interface déconnectée restent dans la
preuve ; elles ne suffisent pas à démontrer une connexion. Le constat actuel
ne qualifie pas rétrospectivement les 158 observations historiques, qui ne
collectaient pas tous les compartiments.

Le [complément préparatoire](../.ui-preview/pilots/offline-physical-total-budget-20261011/qualification.json)
garde les anciens reçus intacts : **45/45 tests purs**, Ruff et parsing PowerShell
passent. La [revue indépendante](../logs/foresight-runtime/t11-independent-total-budget-review-20261011-2044/review.json)
reprend ces mêmes 45 méthodes et 38 sous-cas sans défaut actionnable ; les
compteurs ne sont pas additionnés. Aucun `main`, collecteur Windows, modèle,
microphone ou processus enfant réel n'est exécuté par ce complément.

Le budget total de **840 s commence avant `WAITING`**, sans remise à zéro au
démarrage de l'enfant. Les contrôles demandent l'arrêt des travaux à 820 s,
avec 20 s réservées pour inventaire, polling et fermeture du seul Job.
La [commande préparée](../.ui-preview/pilots/offline-physical-total-budget-20261011/root-commands.md)
demande `-RunSeconds 720`, également bornées au temps total restant.
Les opérations bloquantes et l'ordonnancement Windows ne sont pas une garantie
temps réel : l'utilisateur doit **reconnecter au plus tard à 15 min de coupure,
même sans marqueur**, et ce recours refuse la recette. Aucune prolongation de
coupure ou reprise automatique n'est prévue. Le protocole et les 32 empreintes
préparées restent gelés pour le prochain précheck.

À **20:43 UTC**, root a exécuté séparément le
[préflight réseau de lecture seule](../.ui-preview/pilots/offline-physical-preflights/20261011-204306-1fa5cab0/preflight.json)
avec `passed=true` et `global_offline_gate=false`, réseau connecté : identité et
inventaire sont lisibles avant le geste humain. Le
[précheck fichiers et métadonnées LM Studio](../.ui-preview/pilots/offline-physical-preflights/20261011-204306-1fa5cab0/model-and-files-readonly.json)
passe également : 39 relevés d'empreintes vérifiés, dont des contrôles répétés,
et Gemma-e4b possède une instance réellement chargée. Ces lectures n'ont lancé
ni inférence, ni `WAITING`, ni capture ou coupure physique. Leur
[reçu séparé](../.ui-preview/pilots/offline-physical-total-budget-20261011/root-readonly-preflight-supplement.json)
ne garantit pas l'état au prochain lancement, qui revérifiera les fichiers et
l'inventaire. L'autorisation déjà donnée est conservée ; le nouveau créneau et
le signal manuel attendaient encore la disponibilité de l'utilisateur. À l'issue
de ces seules lectures préparatoires, **T11 restait non qualifié**.

### T11 réussi — moteurs locaux pendant la coupure physique observée

Le nouvel essai autorisé
[`20261011-225003-77be78b1`](../.ui-preview/pilots/offline-physical-runs/20261011-225003-77be78b1/qualification.json)
est terminé le 11 octobre à **20:53:11 UTC**, avec `passed=true`, enfant exit 0.
Il utilise l'autorisation de coupure existante, désormais consommée ; aucune
reprise automatique ni nouvelle capture n'en découle. Le timeout précédent et
ses 192 observations restent intacts.

L'[audit indépendant de lecture seule](../logs/foresight-runtime/t11-success-independent-20261011/qualification.json)
passe **18 contrôles**. Le journal contient exactement 33 inventaires : 24 en
attente, un avant l'enfant, sept pendant et un après. Les neuf inventaires de
qualification ont une gate hors ligne valide ; six sont entièrement observés
avec l'enfant vivant avant et après la collecte. Les interfaces/adresses/routes
IPv4/IPv6 de tous les compartiments sont collectées, sans transport bloquant,
interface IP non-loopback connectée ou route capable/inconnue dans ces neuf
inventaires. Le plus grand intervalle observé est **7,3212 s**, inférieur à 15 s.
L'identité virtuelle dormante relue reste reconnue structurellement ; aucune
exclusion par le nom F5 n'est ajoutée. La coupure est observée par échantillons,
sans trace continue de chaque changement entre deux inventaires.

Le [harness brut](../.ui-preview/pilots/offline-physical-runs/20261011-225003-77be78b1/harness-raw.json)
conserve une vraie transcription Whisper `small` de la voix SAPI fictive scellée,
**5,5914 s de calcul sur 18,592 s d'audio**. EG2 encode et retrouve les quatre
sources fictives texte/image/audio ; le même job annulé après une entrée reprend
à quatre entrées terminées, puis l'index est rouvert avec un résultat conforme.
Gemma `google/gemma-4-e4b`, réellement chargé selon les métadonnées locales,
produit les deux actions utiles de la transcription : Marie prépare le devis
jeudi ; Paul vérifie le matériel vendredi, avec référence `[1]`. Ce résultat
qualifie le fonctionnement local sous la coupure observée ; il ne qualifie
ni une voix industrielle, plusieurs interlocuteurs, ni le P95 du premier segment
visible à cinq secondes ou une réunion matérielle longue.

Les trois préchecks conservent chacun **39 relevés d'empreintes**, portant sur
35 chemins distincts : mêmes SHA avant et après, également vérifiés à l'audit.
L'empreinte du harness brut est
`f08a505f66133a3bdf5550dcb06aeb22332cbdb48654ef9097ce57dc90d92a48`.
Les chemins Brain/ERP/stockage/temporaire sont configurés dans le scratch neuf
avant les imports ; les deux SQLite de fixture/index sont ouverts uniquement
en lecture seule pour l'audit, intègres, avec quatre sources/quatre entrées et
originaux par SHA concordants. Cet audit ne lit pas les bases canoniques et ne
remplace pas leur bilan de conservation séparé.

Le budget cumulé observé est **182,1300 s sur 840 s**, sans remise à zéro ;
l'enfant dure **43,9076 s**. Le reçu confirme sortie enfant, Job vide
(`active_processes=0`) et fermeture des handles. La lecture CIM réussie des
seuls PID 39492/38884/34820 ne les retrouve pas au moment de l'audit. Le refus
initial de cette lecture dans le sandbox est conservé séparément, sans être
interprété comme preuve d'absence. Les fichiers bruts restent inchangés.

**T11 est qualifié dans la portée du plan : STT, recherche et génération locales
sur corpus fictif pendant la coupure physique observée.** Le comptage d'appels
réseau natifs n'est pas mesuré (`native_outbound_attempt_count=null`) et aucune
absence absolue de tentative n'est revendiquée ; cette limite n'ajoute pas une
nouvelle condition à T11. Le champ historique
`physical_network_disconnected=false` du harness, borné à sa garde Python, reste
conservé : la preuve physique `true` est distincte dans le rapport contrôleur.
L12 demeure ouvert sur ses autres critères de matériel, qualité/latence et
fidélité publique. Aucun nouveau moteur ou essai n'a été lancé par l'audit.

### État du 13 octobre — correction de reconnexion, non activée

Le candidat V4 passe 47 tests simulés (18 antérieurs, 29 readiness), Ruff et
revue indépendante. L'identité interne du principal inclut SHA256(api_key),
sans publier cette empreinte ni la clé ; un ancien contrôle lancé après le
changement de seule clé ne peut plus décharger le secours.

La [globale V4](../.ui-preview/pilots/native-ready-union-v4-20261012/qa/python-global-union-v4/qualification.json),
SHA49b5fb91…, termine le 12 octobre à22:04:13UTC : exitpytest2, erreur de collecte
ModuleNotFoundError sur l'import test_ai_recovery_unload depuis le nouveau test.
Ce défaut d'import est corrigé en copie ; les47 simulations ne sont pas une
réussite globale. Les cartes379/57/224 restent inchangées. Le Job possédé est
fermé, zéro processus actif/handles fermés, stdout complet ; six relevés disque
restent au-dessus de4,88Go, sans erreur de capacité lors de cet essai.

Les [deux originaux LLM](../.ui-preview/backups/promotion-code-ready-v4-20261012-220030-b179386a/qualification.json),
SHAe9100b00…, sont sauvegardés (18027octets) et le nouveau test est absent du
canonique. Ce complément de code n'est pas la sauvegarde finale coordonnée des
données. Aucune promotion, capture, qualification matérielle/P95 ou clôture L12
n'est déduite de ces contrôles. Le nouvel essai GPU unique et la protection ACL
des nouvelles sauvegardes attendent leurs réponses humaines déjà demandées.

### Reprise V5 — import résolu, capacité insuffisante

Le [candidat V5](../.ui-preview/pilots/llm-ready-recovery-stage-v5-20261012/candidate-manifest-v5.json)
passe47 simulations ; seul l'import du test change depuisV4. La collecte
normale trouve2363 cas, exit0. La [globale V5](../.ui-preview/pilots/native-ready-union-v5-20261012/qa/python-global-union-v5/qualification.json),
SHA4e8ad254…, s'arrête le12 octobre à22:25:59UTC sur la réserve disque :
713,67s,709 relevés, minimum1912016896octets, exit92, aucune réussite globale.
Les points de progression atteignent21%, sans erreur de test signalée ; le
nombre de tests terminés n'est pas attesté par un JUnit. Les2363 cas sont ceux
collectés. Job vide/fermé, stdout complet et cartes379/57/224 inchangées.

Le [contrôle de compression des temporaires fermés](../.ui-preview/pilots/native-ready-union-v5-20261012/qa/python-global-union-v5/root-closed-temporaries-compression.json),
SHAe73d3478…, conserve2341 fichiers,733337742octets logiques : toutes empreintes
et tailles avant/après concordent. Aucune suppression, modification de droits
ou cible métier. L'espace libre observé passe de2271346688 à2920284160octets.
Cette différence n'explique pas toute la consommation du volume ; le diagnostic
reste borné à des métadonnées. La reprise préparée marque un parent temporaire
neuf avant le lancement pour hériter de la compression dès la création des cas.
Les prédicats, le Job, les sources et le seuil2Gio restent inchangés.

Le [composite V5](../.ui-preview/pilots/native_next_promotion_composite_manifest_v5.json)
recense32 cibles,24 remplacements et8 nouveaux. Les preuves GRAPH858 et les
originaux sont distincts. Aucune activation, nouvelle voie réelle LM Studio,
qualification matérielle/P95 ou clôture L12 n'est déduite de ces contrôles.


## Qualification logicielle complète du candidat — 13 octobre 2026

La reprise V5 R1 termine à **2 361 réussis, 2 ignorés, zéro échec et zéro erreur**,
exit 0, en 3 389,95 secondes. Le JUnit contient exactement 2 363 cas.
Les 379 sources Python, 57 ressources NEXT et 224 auxiliaires sont inchangés ;
Ruff passe sur `app backend/app tests`. Le Job privé, ses descendants et les
lecteurs sont fermés. La réserve minimale observée est de 2 724 450 304 octets.

Les deux cas ignorés sont le mixage audio sans runtime optionnel isolé et
le dossier fictif Infomaniak absent. Trois avertissements restent consignés :
une dépréciation Starlette/httpx et deux décodages UTF-8 de sorties Windows
dans les fixtures de jonctions. Aucun échec n'est masqué par ces mentions.

Le premier essai V5 arrêté sur la réserve disque reste conservé. La reprise
utilise un parent temporaire vide compressé avant création des fixtures.
Les anciens temporaires fermés NEXT (9 078 fichiers, 3 887 283 425 octets
logiques) ont aussi été compressés : tailles et SHA-256 avant/après égaux,
cinq liens ignorés et conservés. Aucun fichier de preuve n'a été supprimé ;
la variation globale d'espace libre n'est pas entièrement attribuée.

Le composite conserve **32 cibles : 24 remplacements et 8 nouveaux fichiers**.
Leurs sources et baselines canoniques sont revérifiées. Les **858 tests React**,
TypeScript/build et la preuve navigateur GRAPH restent une qualification
distincte : la globale Python utilise les anciennes ressources NEXT.

Cette réussite qualifie le candidat logiciel, pas son activation. La sauvegarde
finale coordonnée, la reconnexion réelle au LLM, les essais audio matériels,
la qualité ASR, le P95 du direct, T13 complet et T15 restent à terminer ;
**L12 reste ouvert**. Aucun redémarrage, changement de droits ou nouvel essai
microphone/GPU n'est exécuté par cette publication. Drive reste exclu.

Preuve terminale : `.ui-preview/pilots/union-v5-terminal-publication-b499accb/terminal-verification.json` (SHA-256 `1ceec1152556f2ddc5def7eb42278c2a57bc9621664fb35b34cb38f4fbe4a90a`).
Reçu complet : `.ui-preview/pilots/native-ready-union-v5-20261012/qa/python-global-union-v5-capacity-retry-v1/qualification.json` (SHA-256 `bdc20e4c9d4c0ff6d7ddcd9b49abf2ef0aa8b19a09b354bac3a444b56c85e057`).
Compression NEXT : `.ui-preview/pilots/native-ready-union-v5-20261012/qa/python-global-union-v5-capacity-retry-v1/root-closed-next-temporaries-compression.json`
(SHA-256 `6955092f5bb5254773a638df539bf32f317e57c54111a650decb3fa07437227a`).


## Activation logicielle vérifiée — 13 octobre 2026

Les 32 sources du composite V5 et ses 3 fichiers compilés sont maintenant
actifs dans Agent, sur le seul port 8001. Les 25 originaux remplacés et
les anciens assets sont conservés. Les 379 sources Python actives concordent
avec la globale du candidat : 2 361 réussis et 2 ignorés ; 858 tests React,
TypeScript/build et Ruff sont qualifiés. Les contrôles après copie, les
ressources servies et la santé Brain/ERP passent.

La sauvegarde du code/Git et la sauvegarde finale des données sont privées
dans `Documents/AgentBackups`, sans changement de droits. La dernière
sauvegarde contient 992 fichiers et 5 bases SQLite ; sa restauration réelle
dans un dossier neuf passe. Tous les identifiants, notes, sources et
décisions conservées sont préservés. Deux tables de travaux automatiques
reprennent après redémarrage ; leurs écarts sont consignés séparément.
L’archive historique du 1er octobre, enregistrée avant nettoyage des
orphelins CDC, garde ses 26 références orphelines exactement sur source,
sauvegarde et restauration. Brain et ERP actifs ont zéro écart FK.

La limitation SQL du direct, la conservation des fragments différés,
leur traitement batch explicite et les correctifs de capture native sont
activés. Le déchargement du secours LM Studio accepte désormais un
catalogue récent annonçant exactement le modèle réseau configuré, avec
respect des générations en cours. Le serveur réseau est actuellement
injoignable : Gemma local reste chargé en secours ; cette nouvelle voie
n’est pas encore qualifiée par une reconnexion réelle.

Vérification navigateur sur la séance existante : **Démarrer la réunion**
est visible et actif ; **Périphériques** expose la sortie Windows et le
microphone. En mode « son du PC », le sélecteur microphone est désactivé ;
choisir « son du PC + ma voix » ou « En salle · microphone » pour l’utiliser.
Aucun démarrage audio, enregistrement, création de séance ou édition de
note n’a été effectué par cette vérification.

Les 14 contrôles réels de l’import ICS sur copie isolée et les contrastes
du graphe sombre avec navigation clavier sont consignés séparément.
L12 reste ouvert : audio matériel intégré, qualité ASR/direct/P95, séance
longue. T13, T14 et T15 sont qualifiés ci-dessous.
Les autorisations GPU/microphone consommées ne sont pas réutilisées.
Drive reste exclu ; aucun commit ou push n’est effectué.

Reçu d’activation : `logs/foresight-runtime/v5-software-activation-20261013.json`.
Sauvegarde finale : `Documents/AgentBackups/final-offline-20261013-003559-67eb76ab/qualification.json`
(SHA-256 `2eb184580cc910137ad84d115f1a4ce67aac568d4f9ae78bfd37bed3e6c52152`).


### Clôture T14 et T15 dans leur portée logicielle V5

**T14 est qualifié** pour la désactivation après nouvelles écritures et
leur récupération : cinq cas déjà réussis dans le JUnit global vérifié
couvrent notes/versions, fragments, corrections, exports, copie restaurée
avec les quatre flags éteints et reçus batch conservés sans rejeu. Leurs
sources sont identiques au code actif ; aucune répétition de tests ni
inférence supplémentaire n’est nécessaire pour rattacher cette preuve.

**T15 est qualifié** pour les modules métier et les décisions historiques
de cette livraison. La sauvegarde finale et sa restauration réelle, la
comparaison fraîche avant/après reprise, les 379 sources actives identiques
à la globale et les vérifications du service/du frontend sont reliées.
Tous les anciens identifiants et les champs métier sont conservés. Les
seuls écarts sont les colonnes de reprise des deux traitements existants
de jalons et d’analyse de connaissances, expliqués et consignés.
Les deux tests ignorés et l’archive historique FK26 restent explicitement
documentés ; les bases actives ont zéro écart FK.

Ces clôtures ne qualifient pas le matériel, le direct/P95 ni la longue
réunion. L12 reste ouvert sur les recettes matérielles, ASR et de longue séance.
Les anciens reçus indiquant T14/T15 ouverts restent des états historiques.

Preuves courantes : `logs/foresight-runtime/T14-current-v5-software-qualification-20261013.json`
et `logs/foresight-runtime/T15-current-v5-software-qualification-20261013.json`.


### Clôture T13 — interface dans la portée validée

T13 est qualifié pour les références publiques et l’adaptation Agent
acceptée par l’utilisateur : les preuves responsive, notes/clavier et
graphe clair/sombre sont complétées par le contrôle critique d’arrêt.
À 670 pixels en clair/enregistrement et à 320 pixels en sombre/pause,
après navigation vers Sources, Tab place le focus visible sur
« Arrêter et conserver », entièrement dans le viewport. Entrée produit
deux POST 200 distincts dans le journal fictif ; la barre disparaît ensuite.
Aucun débordement horizontal de page ; contraste texte 13,143 et 12,559.
Les deux captures d’écran ont été observées dans le navigateur.

Les DTO de capture et le handler STOP de ce complément sont explicitement
simulés. Il qualifie l’interface, sans microphone ni inférence, et ne
qualifie pas l’arrêt physique/EOF, la conservation audio ou le P95.
Le serveur de recette, ses deux connexions SQL et son processus sont
fermés ; sources/frontend/3 assets inchangés. L’interruption demandée
se termine par KeyboardInterrupt/exit1 consigné. Le viewport est remis
à sa valeur normale et l’onglet de recette est fermé.

**T13, T14 et T15 sont clos dans leurs portées logicielles documentées.**
**L12 reste ouvert** pour les recettes matérielles/intégrées, l’ASR et
la longue séance/direct/P95. La reconnexion LLM réseau réelle attend
un serveur joignable. Aucun nouvel essai GPU/microphone n’est engagé.

Preuve courante : `logs/foresight-runtime/T13-current-v5-accepted-UI-qualification-20261013.json`.


### Complément T04 et mesure du direct — candidat du 13 octobre 2026

Un défaut logiciel T04 est confirmé sur V5 : le navigateur peut demander le micro
avant son admission serveur, et sa pause conserve des pistes sans empêcher
une capture Windows concurrente. Le correctif est testé sur une copie complète,
sans activation dans Agent : réservation explicite avant tout média, exclusion
atomique Windows/navigateur, maintien pendant pause et libération après fermeture.
Les commandes, réponses perdues, refus durables, pistes tardives et récupération
d’un autre onglet sont contrôlés. Une copie restaurée gèle cette autorité
sans déclarer un arrêt physique du canon ni supprimer les événements historiques.

Le partage système au navigateur comporte préparation puis confirmation par un
geste frais ; l’annulation globale reste accessible pendant l’attente. La
[spécification de capture écran](https://www.w3.org/TR/screen-capture/#dom-mediadevices-getdisplaymedia)
impose cette activation pour getDisplayMedia. Le parcours Windows reste distinct.

**81 tests backend ciblés et 873 tests frontend passent**, ainsi que TypeScript
et la compilation isolée. Les ciblés backend utilisaient des imports d’appoint
désormais archivés ; le candidat complet n’utilise plus ces shims. La suite
Python complète reste à exécuter sur ce candidat : catalogue attendu 2403 cas,
dont les deux skips historiques, contrôlé avant les corps de tests. Ces preuves
ne remplacent ni deux onglets avec capture physique, ni navigation/crash matériel.

Le supplément postflight voix → premier segment visible passe 24 tests purs et
une revue indépendante. Il exige la population exacte, des annotations de fin
de parole et des observations viewport liées, avec horloges/incertitudes explicites.
ACK, SSE, temps de calcul, fin de WAV ou proxy RMS ne remplacent pas cette mesure.
**Aucun P95 réel n’est reconstruit ou qualifié. T12 et L12 restent ouverts.**

Candidat : `.ui-preview/pilots/browser-capture-ownership-v1-20261013/`.
Métrique : `.ui-preview/pilots/t12-speech-visible-metric-20261013/README.md`.
Preuves et états : `logs/foresight-runtime/T04-metric-candidate-documentation-20261013.json`.
Aucun nouveau microphone, GPU, modèle, téléchargement ou port XPilot n’est utilisé.


### Réservation audio et suivi du direct — livraison du 13 octobre 2026

La réservation navigateur précède maintenant la demande de microphone ou
d’audio partagé. Elle reste détenue pendant la pause et est libérée explicitement
après fermeture des flux, ou après refus sans flux ouvert. L’admission conserve
l’exclusion Windows/navigateur et les fragments déjà acquittés.

Dans Transcription, le suivi du direct garde le nouveau texte accessible sans
déplacer une lecture antérieure ni une correction en cours. « Revenir au direct »
permet de reprendre ce suivi. Si le composant Windows est absent, la conservation
des fragments reste proposée séparément de la disponibilité du périphérique.

La couverture backend vérifiée comprend 2403 cas : **2401 réussis et 2 ignorés**,
en deux séquences documentées (1680 résultats réutilisés à sources produit
inchangées, puis 723 résultats de continuation). L’échec initial de fixture est
conservé ; un test hérité a été corrigé et ses 19 cas revalidés. Aucun passage
global unique réussi n’est revendiqué. **879 tests frontend**, TypeScript,
compilation et Ruff passent sur les sources qualifiées.
Les 223 entrées frontend hors configuration sont identiques à la copie testée ;
les deux configurations de qualification ajoutent uniquement un cacheDir local.
Ces chemins de cache restent propres à la recette et ne sont pas promus.

L’activation logicielle et la sauvegarde privée figurent dans les vrais reçus
liés ci-dessous : 24 fichiers livrés, dont 21 sources et 3 assets ; les 16
originaux remplacés sont conservés. Cette publication se fonde sur leurs résultats
effectifs ; les préparations et les anciens reçus restent conservés séparément.

Un nouveau corpus fictif français annoté est préparé pour la recette complète.
Il conserve quinze cas et trente-cinq faits ; sa population sera celle du
schedule scellé avec ses durées réelles, sans imposer les 1216 occurrences de
l’ancien corpus. Les annotations moteur concernent ces nouvelles sources et
ne sont pas projetées sur les anciens WAV différents. Elles ne démontrent pas
un P95 réel ou une qualité ASR industrielle.

**L12 reste ouvert**, avec T04 matériel/intégré, T12 premier texte visible/P95,
qualité ASR et recette longue. T13 visuel conserve l’adaptation Agent aux écrans
publics déjà validée par l’utilisateur ; T13, T14 et T15 ne sont pas requalifiés
par cette publication. Drive reste exclu. Aucun microphone, modèle, serveur,
port XPilot, donnée métier ou opération Git n’est lancé par cet outil.

Preuves d’activation, sauvegarde et validation :

- `C:\Agent\.ui-preview\pilots\browser-capture-qa-continuation-v1-20261013\qa\python-aggregate-v1.json` (SHA-256 `e4317cbebb6d1f12d85e618703c210b50170ab42825ebaf1bf3f42c284884984`).
- `C:\Agent\.ui-preview\pilots\t12-transcript-follow-20261013\qa\qualification-final-v3.json` (SHA-256 `d87e692a102b44927fc2bd3aa60d30670226b84378ecfe62bf8a041990a68130`).
- `C:\Agent\.ui-preview\pilots\browser-capture-ownership-v1-20261013\activation\ruff-root-observed-v2.json` (SHA-256 `796df4209ed4ff172705bbc4e775c1ddbb9d02eaecc3fa796a0ac78ce7ca3891`).
- `C:\Agent\logs\foresight-runtime\browser-ownership-current-activation-20261013.json` (SHA-256 `9d32e00a31f2a78396d0ed8a997a9dbc696ea193b3ad49bd8846915235b017cd`).
- `C:\Users\Frederic.LEFRANCOIS\Documents\AgentBackups\browser-ownership-active-stores-v2-520f9269\qualification.json` (SHA-256 `2788a89b4b2296a048d8efc1b9841227cf1b5891f8daacb5febb8ee2c8c3435a`).
- `C:\Users\Frederic.LEFRANCOIS\Documents\AgentBackups\promotion-browser-ownership-v3-20261013-035745-b73870d6\qualification.json` (SHA-256 `37f3158f6b04f01bf24416158dc06bd0335bf1eb277d067e2d4cedadcb6ef1fd`).
