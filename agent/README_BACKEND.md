# Exploitation et vérification d'Agent

## Contrôles de connexion espacés — 4 novembre 2026

`ConnectionStatus` lit le cache toutes les 60 s et `MailActivity` toutes les
30 s, avec un délai HTTP de 20 s. Focus et retour de visibilité respectent
ces intervalles ; aucune lecture supplémentaire ne s'accumule pendant une
requête, sauf après un test manuel explicite. Les onglets masqués suspendent
les lectures. Trois erreurs de lecture consécutives confirment la perte d'un
état connu (les mails attendent aussi trois erreurs au démarrage).

`connection_health` conserve les sondes pendant 300 s (60 s après un échec),
attend jusqu'à 20 s
pour le réseau et borne aussi le calcul d'embedding à 20 s, attente de file
comprise (ou au délai configuré s'il est inférieur). Après un état `ok` ou
`warning`, deux sondes en erreur sont nécessaires pour afficher l'erreur ;
le premier échec conserve la date de la dernière vérification réussie. Une
configuration différente invalide ce cache. Le test LLM manuel reste immédiat
et prioritaire pendant 300 s. Les délais des traitements métier restent ceux
de leurs réglages. Une panne réelle peut donc apparaître plus tard dans le
témoin : environ 90 s à 3 min pour les lectures, et jusqu'à cinq minutes
avant la première sonde en échec puis une minute avant sa confirmation.
La présence Thunderbird tolère 180 s sans signal, au lieu de 90 s ; les
réglages et le panneau Thunderbird lisent son statut toutes les 30 s. Le
seuil de fraîcheur permettant de libérer le modèle de secours reste à 6 s.

Recette : `tests/test_connection_health.py`, `tests/test_ai_recovery_ready.py`,
`web/src/components/ConnectionStatus.test.tsx` et `MailActivity.test.tsx`.

### Autorisation du mode hors ligne

`ai_routing` attend 120 s depuis le premier échec de transport du serveur IA,
puis demande un choix explicite dans un popup global.
`POST /v1/settings/ai/offline-decision` reçoit `outage_id` et `decision` (`offline`
ou `wait`) ; un choix précoce ou périmé est refusé en 409. Le serveur garde
l'accord en mémoire, lié au fournisseur, serveur, modèle, clé et cible locale.
Il est perdu au redémarrage, au changement de réglages ou au retour confirmé
du principal. Un simple contact TCP ne prouve pas le retour du modèle.

Sans accord, ni génération locale, ni démarrage LM Studio, ni chargement de
modèle ne sont autorisés, y compris depuis un traitement en arrière-plan ou
le streaming. L'accord autorise le modèle pour les prochaines demandes, sans
relancer automatiquement une demande déjà échouée. `wait` interdit le local
et supprime les rappels pour la même panne ; « Choisir le mode hors ligne »
reste disponible dans État du système. Échap équivaut à attendre. Le popup
se ferme seulement après enregistrement du choix ; une erreur reste visible.
Les lectures de routage sont passives et n'ouvrent plus de connexion TCP.
La temporisation avant nouvelle tentative TCP est portée de 30 à 60 s.

Tests d'admission : `tests/test_offline_consent.py` et
`web/src/components/OfflineModeDialog.test.tsx`. Les recettes historiques de
transport/CLI simulent un accord préalable ; celles de déchargement isolent
la gestion des ressources après admission. Les tests d'admission utilisent
le verrou réel, un temps contrôlé et des appels HTTP simulés.

Validation du 4 novembre : 116 tests backend ciblés, 1 020 tests frontend,
Ruff et compilation conformes. La suite Python globale lancée avant l'ajout
du consentement a été interrompue à 25 % ; elle ne qualifie pas la version
finale. Popup vérifié au clavier, à 1280 × 900 et 390 × 844 avec des réponses
simulées, sans provoquer de panne ni charger de modèle réel. Captures dans
`logs/ux-quality/offline-consent-*-final.png`. Les avertissements UX de texte
long sont conservés : ils expliquent le délai et l'effet du consentement.
Agent 8001 a été redémarré après sauvegarde Brain/ERP/index vérifiée
(`backups/connection-consent-20261104-142144/report.json`) ; santé Brain/ERP
conforme et routage sans consentement hors ligne au démarrage.

## Reprise automatique des suggestions mails — 4 novembre 2026

`run_auto_scan_once()` appelle `auto_classify_pending()` avant le scan et
l'inférence. Les mails déjà analysés, exclus du tri non forcé, sont ainsi
repris au seuil enregistré, notamment après sa baisse. Le verrou de tri et
le contrôle d'analyse durable évitent deux traitements concurrents. Aucun
nouvel appel LLM n'est nécessaire pour valider une suggestion acquise ;
l'extraction et l'indexation restent différées et auditables. Les automatismes
désactivés le restent. Le résultat du passage expose `auto_classification`
avec les compteurs et erreurs. Voir [tri des mails](docs/18_MAIL_TRIAGE.md).
Tests : `python -m pytest tests/test_mail_threshold.py tests/test_mail_auto100.py tests/test_mail_sources.py tests/test_triage.py tests/test_workspace.py -q`.

## Indicateur de chargement discret — 4 novembre 2026

Le suivi HTTP automatique est réservé aux routes d'opérations longues reconnues
(import, analyse, transcription/OCR, export, sauvegarde/restauration, test IA).
Lectures GET/HEAD, polling et petites écritures restent silencieux, y compris
les lectures de notes par leur transport spécialisé. Un libellé `activity`
explicite reste possible et `activity:false` reste silencieux. Le popup global
attend 2 000 ms de suivi continu avant affichage. Aucun délai réseau,
mécanisme d'annulation ou traitement d'erreur n'est modifié.

Validation : 63 tests ciblés frontend, TypeScript/Vite et Ruff conformes, zéro
avertissement UX sur l'indicateur. Lecture réelle de portefeuille HTTP 200
retardée de 3,5 s dans le navigateur sur 8001 : aucun popup. Opérations rapides,
seuil, fermeture et annulations vérifiés par tests isolés. Aucun traitement IA
réel ni import métier lancé. Preuves et sauvegarde de l'index frontend :
`logs/ux-quality/quiet-loading-20261104/`. Les anciens assets sont conservés.

État courant : [correctifs de l'audit](docs/60_SECURITY_REMEDIATION.md), activés
sur 8001 après sauvegarde coordonnée vérifiée du 22 octobre à 19 h 53.
Ce guide décrit le serveur unique Agent ; XPilot sur 8000 reste externe.
L'[ancien guide](docs/history/README_BACKEND_BEFORE_SECURITY_20261022.md) est
conservé intégralement pour ses recettes, réglages et preuves historiques.

## Relais Kiara authentifié — 4 novembre 2026

Interface assistant : « Conversation éphémère » et « Inclure les sources à
confirmer » sont alignées au-dessus du projet, sans paragraphe explicatif.
Les règles de conservation et les appels backend restent identiques.
Vérification ciblée : `npm --prefix web test -- src/components/AssistantPanel.test.tsx`
et `npm --prefix web run ux:check -- web/src/components/AssistantPanel.tsx`.

### Pièces jointes des mails

La projection d’un mail résolu appelle `mail_attachments.prepare` avant EG2.
L’extraction isolée réutilise les lecteurs de documents existants, ajoute PPTX,
ICS et les ZIP bornés, puis tente l’OCR Windows des images/PDF sans texte.
Les `SourceArtifact` `attachment_text` portent `attachment_index`, `filename`,
`attachment_sha256` et les repères de page/feuille/diapositive. Leur contenu
entre dans la recherche et les embeddings du mail, dans son seul projet.
`attachment_status` et `source_metadata.attachment_extraction` consignent les
limites : `unsupported`, `failed`, `ocr_required`, `empty`, `encrypted`,
`too_large`. Ces états ne prétendent pas que le fichier a été intégralement lu.
L’analyse LLM de propositions reste un traitement distinct.

Reprise des mails déjà classés, après sauvegarde Brain **et** index actif :

```powershell
.venv/Scripts/python.exe scripts/index_mail_attachments.py --backup backups/mail-attachments-YYYYMMDD-HHMMSS
```

Le script extrait et met en attente uniquement les projections dont le texte
change ; la reprise mémoire du serveur Agent traite ensuite les embeddings.
`progress.json` décrit l’extraction, pas la fin des embeddings. Contrôler aussi
les projections `pending`/`failed` et les références du profil EG2 actif.
`--project-id` limite le périmètre ; `--retry` revérifie les interprétations,
avec réutilisation des reçus réussis. Les erreurs d’extraction temporaires et
OCR incomplets ne sont pas mis en cache comme réussites.
La révision d’interprétation est enregistrée dans le reçu par mail ; une
nouvelle révision force la revue des anciens reçus réussis. Les clés de
cache Office distinguent l’extraction incluant les images incorporées.
Les passages inchangés du même mail/profil réutilisent leurs vecteurs ; une
panne EG2 conserve l’ancien index et la projection à reprendre.
`embedding_cache` dans l’index EG2 conserve les vecteurs par profil/empreinte
de texte, sans texte ni rattachement de projet. Chaque lot réussi est acquis
avant le suivant ; la substitution des passages de la Source reste atomique.
Les textes strictement identiques de pièces transférées peuvent ainsi réutiliser
leurs vecteurs, avec une provenance et un filtrage propres à chaque mail.
Recettes : `tests/test_mail_attachments.py`, `tests/test_eg2_memory.py`,
`tests/test_mail_enrichment.py`, `tests/test_memory_recovery.py`.
Sous Windows, les tests audio de la suite complète peuvent dépasser la
longueur de chemin permise sous le dossier temporaire du profil. Pour cette
recette, `TEMP`/`TMP` sont placés sous `C:\Agent\.pytest_work\mail-attachments-temp`
et Pytest utilise `--basetemp=C:\Agent\.pytest_work\mail-attachments-global-01`.
Les bases restent temporaires et isolées ; aucun test n’utilise les données
de production. Les 144 tests ciblés des pièces jointes, lecteurs, recherche,
embeddings et protections passent ; voir le manifeste pour la suite globale.

IA compatible OpenAI : `base_url=http://127.0.0.1:17841` (sans `/v1`, ajouté
par le client LLM), `model=fred-qwen`, clé de ce PC dans les réglages IA.
La clé reste chiffrée via DPAPI ; aucune clé ne doit être ajoutée au dépôt.
Pour EG2 : `embedding_endpoint=http://127.0.0.1:17841`,
`embedding_model=google/embeddinggemma-2`, `batch_size=8`, `timeout_s=600`.
La reprise des pièces jointes est passée de deux à huit après un test
entièrement synthétique réussi en 5,33 s. Un retour à deux reste possible
si des passages réels dépassent la coupure du relais ; ni le modèle ni le
profil vectoriel ne changent avec la taille des lots.
Le LLM utilise également `timeout_s=600`. Le canal de production,
son diagnostic et le témoin de connexion réutilisent la clé IA uniquement si
la base API correspond exactement, avec ou sans suffixe `/v1`.

Un changement de serveur/alias modifie le profil technique EG2. Si l'encodeur
reste compatible, les vecteurs peuvent être conservés après contrôle explicite,
sauvegarde et adaptation des références du profil dans une copie de l'index.
Le 4 novembre : comparaison de 263 vecteurs de 11 sources, cosinus minimal
0,999354 ; 20 322 vecteurs réutilisés, 1 070 références de projection adaptées,
données canoniques identiques. Index actif :
`storage/eg2/kiara-compatible-20261104/index.db` ; original conservé dans
`storage/eg2/index.db`. Preuve : `logs/kiara-config-20261104-100510/reuse-result.json`.
Ce contrôle échantillonné ne démontre pas l'identité numérique de tout calcul.
Reconstruire depuis le canon seulement si l'espace vectoriel change.
Un modèle annoncé dans `/v1/models` peut encore répondre 503 ; cela ne valide
pas les embeddings. Garder Accès serveur Kiara ouvert pendant l'utilisation.
Tests ciblés : `tests/test_embedding_channel.py`, `tests/test_eg2_memory.py`,
`tests/test_connection_health.py`, `tests/test_unified_search.py`,
`tests/test_ai_routing.py`, `tests/test_security_remediation.py`.
Ces 82 tests ciblés passent, ainsi que Ruff. La suite globale exploratoire a été
interrompue après plusieurs échecs ; elle n'est pas validée par ce raccordement.

Complément file EG2 : 136 tests ciblés passent, deux tests de capture PCM exclus
après un FileNotFoundError lors de la création d'un WAV temporaire. Les réservations asynchrones EG2 et les
réservations synchrones du LLM/diagnostic partagent `inference_scheduler` par
adresse de serveur. Les requêtes sont sérialisées dans le processus Agent,
sans bloquer sa boucle HTTP ; annulation et expiration libèrent la place.
Un lot dispose de 600 s au total (file, HTTP et reprises). Jusqu'à 20 tentatives
sur 429/503, avec délai croissant plafonné à 30 s par défaut et `Retry-After`
numérique borné entre 0,25 et 60 s. La recherche n'impose plus sa coupure à 20 s.
Le diagnostic EG2 respecte aussi la file et le délai configuré.
Les autres clients restent hors de cette file locale et peuvent occuper EG2.
Les 600 s côté Agent ne changent pas une éventuelle limite du relais Kiara.
Les réglages de durée et de lot ne changent pas le profil vectoriel : aucune
reconstruction générale. Sauvegardes avant reprise :
`logs/kiara-config-20261104-100510/{brain,index}-before-queue.db`.
Recette réelle finale : reprise terminée, six mails indexés, zéro échec restant.
Preuve : `logs/kiara-config-20261104-100510/queue-final-qualification.json`.

## Rubriques regroupées dans Réglages — 4 novembre 2026

La navigation `WorkspaceShell` regroupe désormais Sources, Informations,
Suivi des analyses et Connexions & imports dans les onglets de Réglages.
Leurs routes `/app/sources`, `/app/knowledge`, `/app/jobs` et `/app/imports`
restent valides pour les citations et liens existants ; la barre d'onglets est
commune à ces écrans. Les vues en cache, filtres, garde des brouillons et polling
limité à la vue active sont conservés. Aucun schéma ni service backend modifié.
Recette : 49 tests ciblés (WorkspaceShell, ProjectNavigation,
ProjectMeetingNavigation, SourceMultimodalEvidence, ConnectionStatus), build
TypeScript/Vite, contrôle UX ciblé et navigation réelle sur 8001 à 1280/390 px.
Captures et sauvegarde de l'index frontend :
`logs/ux-quality/settings-tabs-20261104/`. Les anciens assets sont conservés.

## Suivi regroupé dans État du système — 4 novembre 2026

Le suivi des mails est désormais monté une seule fois dans le popup
`ConnectionStatus`, avec ses compteurs, alertes et dernières activités.
`WorkspaceShell` fournit la navigation vers les traitements ; cette action
referme le popup. Les routes et données backend restent inchangées. Le statut
mail contribue au témoin global, même lorsque le popup est fermé. Les délais
de lecture existants et le rafraîchissement en arrière-plan sont conservés.
Recette du 4 novembre : 45 tests frontend ciblés réussis (ConnectionStatus,
MailActivity, SourceMultimodalEvidence, WorkspaceViews), TypeScript/Vite et Ruff
conformes. Contrôle navigateur réel sur 8001 à 1280 et 390 px, lien des
traitements activé avec Tab/Entrée. Quatre avertissements heuristiques UX relus.
Captures : `logs/ux-quality/system-status-20261104/`. Build sans suppression des
anciens assets ; index frontend antérieur sauvegardé dans ce même dossier.

## Assistant éphémère et lecture des citations — 2 novembre 2026

Le frontend désactive `useAssistantHistory` par défaut. Le contexte courant reste
transmis au chat progressif ; aucun appel `assistant-threads` n'est effectué en
mode éphémère. Changer de mode démarre un échange vide pour éviter toute sauvegarde
rétroactive. Les conversations existantes ne sont ni modifiées ni supprimées.
Les routes du chat restent sans écriture d'historique ; aucun schéma ou service
backend n'est ajouté. Ce mode concerne l'historique Agent, sans modifier la
politique de journalisation du fournisseur IA.

Les liens `/app/sources?source=<id>` ouvrent le lecteur existant et chargent la
source via l'API ; `/v1/sources/{id}` reste inchangé pour les clients JSON.
Les versions exactes de notes et les téléchargements originaux sont conservés.
La mise à jour frontend se construit sans supprimer les anciens assets :
`npm --prefix web run build -- --emptyOutDir false`.

Recette ciblée : `npm --prefix web test -- src/components/AssistantPanel.test.tsx
src/components/SourceMultimodalEvidence.test.tsx src/lib/citationLinks.test.ts
src/hooks/useAssistantHistory.test.tsx src/components/WorkspaceViews.test.tsx
src/components/MeetingStudio.test.tsx`. Détails :
[interface et limites](docs/24_UI_UX_REDESIGN.md).

## Installation reproductible

Python 3.13 sous Windows. Utiliser un environnement propre au dépôt, sans
modifier le Python global ni les environnements des autres applications.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install --require-hashes -r requirements-dev.txt
```

Pour une installation d'exploitation sans les outils de test, remplacer le
profil de développement par `requirements.txt`. Le profil de développement
inclut explicitement NumPy et pytest-asyncio, nécessaires à la suite complète.

```powershell
npm exec --yes --package=pnpm@11.18.0 -- pnpm --dir web install --frozen-lockfile
```

`web/pnpm-workspace.yaml` ne référence que le package frontend existant. Il
configure le correctif transitif de source-map-js et autorise seulement le
script esbuild requis pour la construction. Il ne crée pas de sous-projet.
L'ancienne jonction de ce poste reste sous
`web/node_modules-before-audit-20261022` et n'est plus utilisée.

Le runtime audio utilise `.venv-speech` et `requirements-audio.txt`. Le rendu
PDF utilise PDFium avec `requirements-pdf.txt`. La recherche sémantique passe
par EG2 dans Kiara. Le moteur local LiteRT est obsolète et ses dépendances
ont été retirées. Les dépendances audio sont verrouillées avec empreintes.
Les fichiers `.in` définissent les dépendances directes. Ne pas utiliser une
synchronisation destructive qui retirerait des extensions installées du runtime.

## Lancement et santé

- `start-agent.cmd` ouvre l'interface et appelle le lanceur de service.
- `start-agent-task.cmd` lance le superviseur avec `.venv` en priorité.
- `scripts/agent_runtime.py status` distingue superviseur, PID et port.
- `/health` contrôle Brain et ERP ; il ne garantit ni génération IA,
  transcription, qualité de recherche ou indexation terminée.
- Le serveur normal reste sur `127.0.0.1:8001` et enlève `AGENT_TESTING` de
  l'environnement enfant. Les essais utilisent des bases et dossiers isolés.

Le démarrage normal initialise les schémas et reprend les traitements activés.
Pour une recette de consultation, utiliser une copie avec lifespan/écritures
bloqués ; ne pas pointer une seconde instance vers les bases actives.

## Données et configuration

| Élément | Configuration |
|---|---|
| Brain | `PB_DATABASE_URL`, défaut `project_brain.db` dans le dépôt |
| Fichiers gérés | `PB_STORAGE_DIR`, défaut `storage` |
| ERP | `MINIPILOT_HOME`, défaut `~/.minipilot` |
| Opérateur | `AGENT_OPERATOR_ID`, `AGENT_OPERATOR_ROLE`, portée JSON `AGENT_OPERATOR_PROJECT_IDS` |
| Clé IA | Paramètre protégé DPAPI ou `PB_API_KEY` |
| Audio | Voir les variables et recettes des documents de domaine |

Le client ne choisit pas son rôle. Le jeton de session protège les actions
locales ; ce n'est pas une authentification individuelle. Avant tout partage
réseau, concevoir les comptes, habilitations et révocations. Ne pas exposer ce
serveur en changeant simplement son adresse d'écoute.

Les moteurs réseau restent en **HTTP sur décision de l'utilisateur**. Aucune
sécurisation TLS n'est revendiquée. L'indexation envoie des passages et la
génération du contexte aux destinations configurées. Le mode local et le
secours local gardent leurs réglages explicites.

Les informations retenues par défaut portent `validation_mode=default` ; une
confirmation humaine porte `human`. Les valeurs critiques, contradictions et
versions de preuve sont exposées par `context` dans les listes de connaissance.
Le filtre `review_only=true` est disponible dans `/api/v1/workspace/knowledge`.
L'action `POST /v1/projects/{pid}/knowledge/{kid}/confirm` exige une preuve
actuelle unique et un opérateur autorisé ; elle conserve la valeur et l'identité.
Les anciennes décisions humaines restent consultables, même historiques.

## Imports, extraction et réserves

- Documents : 50 Mio ; audio importé : 256 Mio ; les familles de route gardent
  leurs limites métier. Le middleware compte les octets même sans taille annoncée.
- Extraction documentaire : enfant séparé, 90 secondes, 1 Gio mémoire,
  16 Mio maximum de résultat IPC. Une erreur conserve l'original.
- OCR : rendu 60 secondes, reconnaissance 90 secondes par appel,
  15 minutes par document ; reçus de page réutilisables et annulation entre pages.
- Les imports et sauvegardes exigent l'espace prévu plus 2 Gio de réserve.
  La maintenance avertit dès que l'espace libre passe sous 10 Gio.
- La capture possède ses propres limites et journaux de secours ; les plafonds
  logiciels ne prouvent pas douze heures de capture réelle.

L'annulation OCR est `POST /api/v1/workspace/sources/{source_id}/ocr/cancel`.
Elle ne supprime ni l'original ni les pages terminées. Une page en cours peut
aller jusqu'à son délai avant de rendre la main.

## Exports et accès en lecture

GET de liens réseau n'écrit plus dans les bases. Les lignes requises absentes
sont présentées comme non configurées jusqu'à leur enregistrement explicite.

GET `/api/v1/projects/{pid}/meetings/{mid}/export` renvoie `markdown`, `file`,
`filename`, `sha256`, `download_url`. `file` est un nom, **plus un chemin serveur**.
Le téléchargement `/markdown` est une pièce jointe sans écriture disque ; deux
réunions du même jour ne partagent pas le même fichier. Les anciens exports ne
sont pas effacés. L'export PDF reste disponible.

## Sauvegarde et reprise

Arrêter Agent avant une sauvegarde coordonnée. Choisir un nouveau répertoire,
extérieur aux données sources ; ne jamais écraser une sauvegarde existante.

```powershell
.venv/Scripts/python.exe scripts/agent_backup.py backup --output C:/AgentBackups/NOUVEAU_DOSSIER
.venv/Scripts/python.exe scripts/agent_backup.py verify --source C:/AgentBackups/DOSSIER_EXISTANT
.venv/Scripts/python.exe scripts/agent_backup.py restore --source C:/AgentBackups/DOSSIER_EXISTANT --output C:/AgentRestore/NOUVELLE_COPIE
```

La création vérifie automatiquement les empreintes en flux et l'intégrité des
deux bases avant d'inscrire son état `verified`. Une vérification seule est
possible sans restaurer ni modifier les fichiers de sauvegarde. La maintenance
peut aussi vérifier la dernière sauvegarde enregistrée et actualiser son marqueur.

Une restauration se fait dans une copie neuve avec ses propres variables Brain,
ERP et stockage. Elle gèle les anciennes autorités de capture/commandes et
suspend les traitements restaurés concernés ; elle ne ferme pas un microphone
sur l'installation originale et n'autorise pas sa réouverture.

Définir avec le responsable la perte maximale de travail et le délai de reprise
acceptables, la copie externe et la fréquence de restauration de recette. Une
clé DPAPI reste liée au compte Windows : prévoir une nouvelle saisie si besoin.
Les fichiers réseau externes ne sont pas automatiquement inclus.

## Journaux et rétention

Le journal applicatif est borné et expurge les motifs de secrets des messages
et traces formatées. Les paramètres publics masquent les secrets de toutes les
sections, y compris les blobs protégés. Cela ne chiffre pas les documents,
bases, captures ou exports ; les droits du poste et son chiffrement sont à
qualifier avec l'IT.

```powershell
.venv/Scripts/python.exe scripts/agent_storage_inventory.py --output logs/inventaire-NOUVELLE_DATE.json
```

Cet inventaire est en lecture seule. Des erreurs d'accès rendent ses tailles
minimales. Aucun fichier n'est déclaré supprimable sur son âge ; aucune purge
n'est programmée sans décision explicite, distinction code/données et sauvegarde.
Conserver contexte, Markdown, instructions, validations et preuves uniques.
Les données actives `storage/`, captures `.playwright-mcp/` et copies de test
`v/` sont exclues de Git ; leur sauvegarde reste indépendante du code.

## Contrôles

```powershell
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m ruff check app backend/app tests scripts
.venv/Scripts/python.exe -m pip_audit --disable-pip --no-deps --require-hashes -r requirements.txt -r requirements-audio.txt
npm --prefix web test -- --maxWorkers=4
npm --prefix web run ux:check
npm exec --yes --package=pnpm@11.18.0 -- pnpm --dir web audit
npm --prefix web run build
```

Sous bac à sable Windows, `PermissionError` sur TEMP ou `spawn EPERM` peuvent
empêcher le banc de test de démarrer. Utiliser un dossier temporaire court neuf
et les accès nécessaires, sans assimiler ce blocage à un défaut produit.
Ne pas relancer pytest sur un `--basetemp` contenant des données à préserver.

La CI conserve les codes de sortie, les installations verrouillées, les actions
épinglées et les droits minimaux. Les audits couvrent les profils déclarés, sans
certifier toutes les bibliothèques natives incorporées aux roues binaires.
Le bilan courant et ses limites figurent dans
[docs/60_SECURITY_REMEDIATION.md](docs/60_SECURITY_REMEDIATION.md).

La livraison Git du 23 octobre 2026 reprend les sources qualifiées ci-dessus.
Les résultats globaux et les vérifications ciblées après les finitions restent
distincts ; cette livraison ne constitue pas une nouvelle recette matérielle.
Les bases, sauvegardes et journaux privés ne sont pas publiés avec le code.
