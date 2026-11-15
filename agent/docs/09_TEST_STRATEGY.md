# Stratégie de tests

## Qualification courante — corrections du 22 octobre 2026

Les résultats de livraison courants sont centralisés dans
[le suivi des corrections](60_SECURITY_REMEDIATION.md#validation-et-clôture).
Les bilans datés ci-dessous restent historiques. Les commandes maintenues sont
`python -m pytest tests/ -q`, `ruff check app backend/app tests`, les tests
frontend, TypeScript, la compilation et les audits de dépendances de CI.
Le runtime dédié `.venv` inclut désormais les prérequis NumPy et pytest-asyncio ;
les profils audio/multimodal restent séparés. Le test des documents utilise un
véritable processus limité, sans modèle réseau ni base active.

## Contrôles de livraison du 21 octobre 2026

Référence livrée : `4b749c6`. TypeScript/Vite réussis (avertissement de taille).
Ruff réussi avant les derniers changements concurrents. Vitest global :
968 réussites et 1 échec sur 969 ; après actualisation du délai attendu de reprise,
les 19 tests de `meetingSessions.test.ts` passent, sans nouveau global.
Pytest : collecte initiale refusée par les permissions ; relance autorisée puis
interrompue à 2 %, sans bilan final. Les résultats globaux historiques ne valent
pas validation de cette révision. Voir [le contexte](../PROJECT_CONTEXT.md).
Une modification locale de `tests/test_relaxed_limits.py` restait non livrée.


## Statut du direct clarifié dans le Studio — 15 octobre 2026

Le Studio distingue maintenant « désactivé », « indisponible » si le runtime
manque, et « activé en essai, non qualifié » lorsque le runtime installé et
l'option de direct permettent un essai. Une qualification absente n'est plus
présentée comme une impossibilité de démarrer. Aucun moteur, opt-in, valeur
de qualité ou P95 n'est modifié ; la relecture reste nécessaire.

Les **943 tests frontend**, TypeScript et le build isolé passent. Les92tests
Studio ciblés sont inclus dans ce total. Les440sources Python produit/runtime
et tests liées au plan demeurent inchangées : la suite backend2580/1ignoré et
54sous-tests n'est pas relancée pour ce seul libellé. Le wrapper QA a terminé1
après ses trois commandes réussies, à cause du suffixe `?v=1` du favicon pris
comme nom de fichier ; l'extraction des métadonnées est corrigée séparément,
sans rejouer les tests ni effacer cet échec.

Le HTML et ses assets sont publiés et vérifiés en HTTP sur Agent8001. Les
anciens assets sont conservés. Aucun redémarrage backend ni rechargement de
l'onglet contenant la note humaine n'est effectué. La nouvelle présentation
sera prise en compte à la prochaine ouverture ou actualisation choisie.
Le même libellé a été observé ensuite dans un nouvel onglet canonique, volet
Préparation ouvert : note version1, Enregistrer désactivé, aucun contrôle
d'audio ou génération utilisé. Les seuls onglets temporaires sont fermés ;
l'onglet initial reste conservé sans rechargement.
[Observation et capture CUA](../logs/foresight-runtime/live-trial-status-UI-browser-proof-ROOT-20261015.json).
Le T12 arrêté reste échoué et **L12 reste ouvert**.

[Livraison et preuves](../logs/foresight-runtime/live-trial-status-UI-delivery-ROOT-20261015.json).


## Disponibilité et preuves conservées — 15 octobre 2026

La lecture actuelle des capacités d'Agent confirme les séances actives, le
runtime batch disponible et l'option de direct cochée. Les indicateurs
canoniques `live_operational` et `live_ready` valent false ; **ce constat de
métadonnées ne prouve pas un blocage réel du moteur**. Le statut dépend du
rapport de qualification, alors que le worker admet les fichiers avec le
runtime installé. Le libellé du Studio a été corrigé pour distinguer cet essai permis
de la disponibilité qualifiée, sans modifier ces indicateurs serveur.
L'assistant « ready » reflète aussi son paramétrage, sans sonde de génération
dans cet appel. Aucun microphone n'a été ouvert.
La recette T12 privée, arrêtée avant une heure, n'active pas ces capacités en production.

Un inventaire borné des JSON/XML explicitement référencés par le manifeste
retrouve 155 fichiers disponibles et empreintés, 358 absents à leur chemin,
et un fichier dépassant sa limite de lecture de 4 Mio. Ce sont des rapports
de qualification, pas un inventaire des données métier. Les anciens liens
et résultats déclarés ne deviennent pas des preuves actuelles ; aucune cause
de leur absence n'est établie et aucun succès n'est reconstitué.

Les deux rapports originaux du test hors ligne du 11 octobre sont bien
conservés dans `.ui-preview` et leurs SHA correspondent aux empreintes
historiques du manifeste : STT, recherche, réouverture d'index et génération
locale figurent dans cette exécution, avec six observations réseau pendant
l'enfant. Le rapport de revue indépendant ancien manque. Cette relecture
ne rejoue aucune coupure ni modèle, ne qualifie pas le code actuel hors ligne
et conserve les limites des observations réseau et de fermeture d'origine.

[Capacités actuelles](../logs/foresight-runtime/meeting-canonical-capabilities-ROOT-20261015-1935.json) · [Inventaire des rapports](../logs/foresight-runtime/manifest-evidence-presence-inventory-ROOT-20261015.json) · [Relecture du hors ligne conservé](../logs/foresight-runtime/T11-retained-evidence-readback-ROOT-20261015.json).


## Revue des recettes et contrôles corrigés — 15 octobre 2026

La nouvelle suite backend complète réussit : **2580 tests et54sous-tests
réussis, un test ignoré**, sur395 sources Python inchangées (45min17s).
Le frontend réussit **940 tests**, TypeScript et un build isolé dont HTML et
assets référencés sont identiques au canon. Le Ruff produit (`app backend/app
tests`) passe sur les mêmes sources. Les59tests ciblés recouvrent la suite et
ne s'additionnent pas à ces totaux. La première suite avait2578réussites et
deux échecs de configuration des tests ; ces seuls cas ont été corrigés,
sans modification produit. Les échecs de collecte TEMP restent conservés.
Ces contrôles logiciels ne clôturent pas les recettes matérielles/longues.

La recette L09 audio R3 réussit réellement : sortie0 du CLI complet observée
sur son handle retenu en24,673s, Job naturellement vide, SDK fermé sans erreur,
quatre conversions FFmpeg réelles, deux requêtes positives avec citation exacte
au rang1, trois exclusions, réouverture et rejeu sans doublon. Les14contrats purs
et la revue distincte restent liés au même paquet. L'index canonique installé et
son historique annulé sont conservés ; seul un état de calcul inactif est admis.
Les champs passed internes provisoires ne sont pas réécrits : le DTO réel de
sortie complète fait foi pour cette portée. Aucune qualification voix réelle,
ASR, CAO, UI/P95 ou activation de production n'est déduite de ce test.
[Résultat réel L09 audio](../logs/foresight-runtime/L09-audio-R3-actual-ROOT-20261015.json).

T16 reçoit un avis source favorable pour sa préparation, son scénario et
l'observateur du CLI complet. Aucun volume n'est créé ; l'accord humain et
l'intervention administrateur pour le volume vide restent en attente.
La recette T12 V7 dispose maintenant d'un plan exact relu et de 110 contrôles
Python purs, dix tests DOM et cinq cas d'horloge réussis. Son essai réel a commencé le 15 octobre à 19 h 19 UTC, après observation CUA,
puis s'est arrêté vers 19 h 46 UTC sur timeout du collecteur, avant une heure. Les 43 copies V6 restent intactes. **L12 reste ouvert.**

[Preuves et réserves](../logs/foresight-runtime/qualification-review-and-policy-correction-ROOT-20261015.json).

[Suites actuelles et limites](../logs/foresight-runtime/current-whole-cohort-ROOT-20261015.json).

### T16 : scénario de saturation préparé, non exécuté

Le composant d'identité GUID du volume et son observateur en lecture ont reçu
un avis indépendant favorable. Le scénario de remplissage réel est maintenant
préparé dans les sources : journal canonique, SQL privés, refus507, absence de
faux ACK et récupération des deux fragments confirmés. Sa revue distincte est
favorable pour la préparation ; aucun plan scellé ni GO n'existe.
L'observateur du CLI complet est préparé et relu ; aucun plan ni GO d'exécution T16 n'existe. Les12tests
d'identité et9tests du
remplisseur restent des contrôles en RAM, sans preuve de saturation réelle.
Aucun VHD créé/monté/rempli ni appel natif/Storage exécuté. L'accord humain et
l'intervention administrateur pour le volume vide restent en attente ; le
remplissage demandera un accord spécifique. Le producteur prévu est synthétique
et fini : aucun arrêt de flux matériel n'est qualifié par ce scénario.
**T16 et L12 restent ouverts.**

[État et preuves de préparation](../logs/foresight-runtime/T16-prepared-full-scenario-review-adoption-ROOT-20261015.json).

## Réunion longue : V7 arrêtée avant une heure — 15 octobre 2026

Le CLI réel, observé par sa session conservée33718, termine en sortie1. Le
collecteur reçoit un TimeoutError ; le pilote arrête ensuite la cadence.
Le driver couvre 27min25s jusqu'à sa fin, sans atteindre les 60minutes prévues.
La cause du ralentissement HTTP n'est pas établie. Aucun redémarrage ni
réutilisation du nonce n'a lieu.

Les **654 fragments acquittés sont tous présents et intacts**, avec 809segments
stockés ; aucune perte d'acquittement observé n'est constatée. Les 1440fragments
de l'heure ne sont pas produits et la séance n'est pas finalisée. Aucun CR,
action ou tâche métier n'est publié. Le processus privé termine0, le Job est
vide avant fermeture, sans terminaison forcée ; le journal HTTP conserve
néanmoins une tâche annulée après dépassement de sa grâce de fermeture.

Une seule fenêtre LLM est exercée : cinq demandes logiques et trois dispatchs
réels. La question attend12,729s derrière la génération engagée ; le proactif
expire en file et les réponses périmées restent marquées obsolètes. Les fenêtres
30/50minutes ne sont pas exercées. Le P95 ACK→SSE descriptif de6,157s n'est pas
le P95 parole→texte visible.

Les suites actuelles et la revue du plan exact restent conservées. Aucun GPU,
microphone ni LLM local n'a été ouvert. Les données brutes de visibilité, clocks
et versions DTO sont retenues, mais le postflight copié n'assemble automatiquement
ces mesures que pour recipe_version6, pas7. Cet écart de préparation sera traité
sur métadonnées conservées, sans modifier le plan ou inventer une mesure.
**T12 et L12 restent ouverts.**

[Terminal réel et conservation partielle](../logs/foresight-runtime/T12-V7-actual-stop-ROOT-20261015.json).

## Préparations L09 et T16 : état actualisé — 15 octobre 2026

La recette réseau d’une heure conserve son autorisation et ses critères. Son ancien paquet référence toutefois 19 sources Python modifiées et omet 14 ajouts ; trois ressources et 54 entrées frontend ont changé. Le relevé statique du 15 octobre ne lance rien : une nouvelle cohorte revue et ses preuves actuelles sont requises avant exécution.

[Comparaison des sources T12](../logs/foresight-runtime/T12-current-source-gaps-ROOT-20261015-f8c2f91ef10b4f8fa0027faf3db43f7c.json).

Le garde du disque d’essai refuse désormais un disque RAW non vide ou déjà
initialisé, à partir de son compteur natif de partitions. **13 contrôles passent**
(sortie0, aucune commande Storage/DiskPart) ; les dix contrôles initiaux restent
historiques. Aucun VHD créé, monté, formaté ou rempli. La préparation du volume
attend l’accord et l’exécution administrateur ; T16 reste ouvert.

La recherche audio dispose d’un nouveau paquet R3 : 288 copies des sources
produit actuelles, 13 modifications et huit ajouts face au paquet précédent.
L’observateur conserve le véritable code de sortie du lanceur et ses flux bruts ;
**17 contrôles propres à cet observateur passent**, sans modèle ni microphone.
Ils ne remplacent pas les 14 contrats originaux. Revue du paquet exact, QA14 et
GO frais restent nécessaires avant l’essai CPU borné à cinq minutes. Aucun essai
R3 lancé ; l’ancien terminal CLI manquant n’est pas reconstruit. **L12 reste ouvert.**

[Détail R3](../.ui-preview/pilots/l09-audio-current-r3-20261015-0504762087a3/R3_CURRENT_SOURCE_NOTE.md) · [Protocole du volume](../.ui-preview/pilots/t16-isolated-volume-20261015/PROTOCOL.md).

## T16 : préparation initiale historique — 15 octobre 2026

Un script PowerShell prépare un nouveau VHD fixe de256Mio, dans le seul
dossier `.ui-preview/qualification-volumes/t16-6fe8a6052e9c4baabca3bb75ce3098bd`.
Son mode par défaut est informatif. Dix contrôles passent : huit refus de
cibles (disque0, système, démarrage, physique, trop grand/petit, image étrangère
ou détachée), une cible virtuelle conforme et le chemin existant sans redirection. Ce sont des tests de garde, sans commande
Storage/DiskPart exécutée. Le partitionnement et le formatage ne concerneront
que la partition neuve de l’image créée dans cet appel ; le script refuse de
réutiliser un dossier existant. Un détachement distinct conserve l’image.

**Aucune création, montage, formatage ou saturation n’a eu lieu.** Le compte
actuel n’a pas les droits administrateur nécessaires au montage VHD. Un accord
humain et l’exécution par un administrateur sont demandés pour cette seule
préparation. La recette de remplissage et d’erreur d’écriture restera à préparer
et qualifier ensuite ; ni T16 ni L12 ne sont clôturés. Aucun microphone,
modèle, base métier ou réglage réseau concerné. Le protocole précise l’empreinte
à relire et les commandes ; aucune élévation ou suppression automatique.

[Protocole de préparation](../.ui-preview/pilots/t16-isolated-volume-20261015/PROTOCOL.md).

## État actuel — 11 octobre 2026

La configuration `ruff.toml` fixe E4/E7/E9/F, le périmètre de contrôles Python du dépôt, pour conserver le même résultat entre les versions locales et verrouillées de Ruff.

Qualification historique de la migration EG2, antérieure à la fusion du 11 octobre : suite Python globale **1 777 réussis, 1 ignoré, 1 échec** en 2 169,90 s. L'échec préexistant `test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint` concerne le classement des mails ; cette suite historique n'est donc pas entièrement verte. Elle a démarré avant les dernières retouches, ensuite couvertes par les tests ciblés. Les contrats EG2 finaux passent **6/6**, les tests ciblés de chat, reprise et archives passent, Ruff et build passent. Côté React, une suite de **481 tests** puis les **2 tests** du nouveau formulaire ont réussi ; ce sont deux exécutions distinctes.

Sur 8001, la sonde réelle a confirmé indexation, rappel et nettoyage, et un chat réel a produit une réponse avec des références présentes dans le contexte. La migration a indexé 897 sources en 16 180 passages, sans échec restant, avec contrôle de conservation du canon. Ces essais prouvent les chemins vérifiés ; ils ne certifient pas toutes les réponses métier ni les fonctions audio. Mesures et limites : [20_EG2_ENGINE.md](20_EG2_ENGINE.md).

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

La qualification de la fusion sépare résultats globaux et suivis ciblés,
simulations, vrais moteurs et capture matérielle. Les rapports initiaux en
échec restent conservés ; un rerun ciblé réussi n'est pas une nouvelle suite
globale. Les passes React 672/75, suivi de libellé avec deux tests et 97 cas Markdown
se recouvrent et ne se somment pas. Bilans, JUnit, SHA et critères ouverts :
[38_FORESIGHT_DELIVERY.md](38_FORESIGHT_DELIVERY.md).

Chaque test qui persiste un fragment utilise une SQLite/storage cohérents et
isolés ; il ne doit pas polluer la base partagée de tests avec un chemin hors
stockage. Le couplage runtime entier puis mail entier passe 20/20 après cette
isolation. Sous Windows, les recettes utilisent des temporaires courts pour
éviter MAX_PATH ; `AGENT_TESTING=1` empêche les workers de données réelles.
Rejeu, conflits Note/session, versions UTC exactes, droits de provenance et
acceptation humaine se vérifient indépendamment de la présence d'un modèle.
Voir [Notes](34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md) et
[qualifications audio](23_MEETING_AUDIO.md).

## Tests domaine
- staging privé de séance traitable sans faux projet ; une Source admissible à
  la projection d'un projet exige son rattachement final ;
- source brute immuable ;
- versionnement des KnowledgeItems ;
- provenance obligatoire ;
- information retenue par défaut versus confirmation humaine ;
- déclassement/restauration et refus/report préservés ;
- contradiction ;
- déduplication.

## Tests ingestion
- double réception même e-mail ;
- retry upload audio ;
- fichier corrompu ;
- pièce jointe volumineuse ;
- transcription partielle ;
- timeout service IA.

## Tests résolution projet
Créer un corpus réel anonymisé :
- projet explicite ;
- projet absent du sujet ;
- contact sur plusieurs projets ;
- thread ambigu ;
- nouveau projet ;
- faux positif volontaire.

Mesures :
- top-1 accuracy ;
- top-k recall ;
- taux de demandes de validation ;
- erreurs critiques.

## Tests extraction IA
Jeu de référence annoté :
- décisions ;
- actions ;
- dates ;
- contraintes ;
- risques ;
- changements ;
- négations ;
- contradictions.

Mesurer précision/rappel, mais surtout erreurs métier critiques.

## Tests sécurité
- accès croisé projet ;
- IDOR ;
- source inaccessible via MCP ;
- injection dans PDF/mail ;
- tool-call non autorisé ;
- fuite dans logs.

## Tests E2E
Scénario actuel pour la mémoire : source → résolution projet → texte canonique → indexation EG2 → rappel des preuves et des faits SQL → réponse du LLM → citations et consultation des sources. La qualification audio et toute future intégration MCP/XPilot externe sont des recettes séparées, dépendantes des capacités réellement disponibles.

## Tests du port mémoire EG2

- contrats avec faux adaptateur réservé aux tests isolés et client EG2 contrôlé ;
- `remember` evidence puis `recall` ;
- rappel `truth` depuis le canon SQL, distinct du rappel vectoriel `evidence` ;
- aucune pollution croisée entre deux projets ;
- source `resolution_pending` jamais injectée dans l'index projet ;
- purge/reconstruction de l'index sans perte des données canoniques ;
- double ingestion idempotente côté Project Brain ;
- ancien texte exclu dès son remplacement canonique, avant réindexation ;
- échec d'embedding conservant la projection précédente ;
- profil incompatible refusé avec reconstruction explicite ;
- fin des longs paragraphes conservée après découpage ;
- faits SQL disponibles avec avertissement si les preuves n'ont pu être recherchées.

## Qualification de pertinence et de performance
Utiliser un corpus fixé, avec réponses de référence et sources identifiées : documents longs, mails, transcriptions, contradictions, négations, versions et questions sans réponse. Comparer toute la boucle d'ingestion, de recherche et de génération, avec le même LLM et les mêmes questions. Une comparaison de seuls vecteurs ne suffit pas à conclure sur la qualité des réponses.

Mesurer :
- recall@k des éléments pertinents ;
- précision sur recherche de vérité ;
- contamination inter-projet = 0 ;
- temps d'ingestion ;
- temps de rappel ;
- ressources CPU/RAM locales ;
- ressources du serveur distant uniquement si elles sont effectivement mesurées ;
- exactitude des réponses et validité des citations ;
- capacité à s'abstenir lorsque les sources ne suffisent pas ;
- capacité de reconstruction.

Séparer temps d'indexation, rappel et génération ; préciser corpus, nombre de passages, cache, parallélisme et reprises. Les mesures d'une migration réelle ne constituent pas une comparaison contrôlée de modèles. La qualification déjà livrée est décrite dans [36_EMBEDDING_CHANNEL.md](36_EMBEDDING_CHANNEL.md) ; tout essai supplémentaire doit répondre à un besoin de décision identifié.

## Régressions opérationnelles — 0.4.0

`tests/test_operational_improvements.py` couvre conservation des données
financières, RAF/consommation, recherche intégrale avant pagination, coût SQL
du portefeuille, sélection de contexte, checkpoints CDC, annulation, versions
BE et restauration, actions prioritaires et vérification de sauvegarde.
`OperationalPanels.test.tsx` vérifie reprise/annulation et historique BE ;
`MailWorkspace.test.tsx` vérifie qu’un résultat serveur hors aperçu reste visible.
La CI exécute les tests Node Infomaniak et Thunderbird, Python/Ruff et React/build.

## Refonte du 2 octobre 2026

Qualification locale : 141 tests Python réussis, 1 ignoré ; 60 tests React
réussis ; Ruff et TypeScript/Vite validés. Les nouveaux tests couvrent routes
SPA directes et retour navigateur, contexte explicite, brouillons conservés,
pagination et preuves, compteur mail durable, audit atomique/reprise, révisions
conversationnelles, fragments SSE réels et annulation des connexions LLM.
`AGENT_TESTING=1` empêche également le scan automatique des dossiers réels.
L’étude vocale ne constitue pas un essai de conversation temps réel sur le poste.
