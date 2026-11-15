# Agent — exploitation du serveur local 0.4.0

Réunions, 22 octobre 2026 : harmonisation des boutons et en-tête compact,
livrés dans `web/dist`. Aucun changement backend, de schéma ou de service ;
Agent reste sur 8001 et sert le nouveau bundle sans redémarrage. Vérifications
frontend et captures : [docs/24_UI_UX_REDESIGN.md](docs/24_UI_UX_REDESIGN.md).

## Corrections UX — 22 octobre 2026

Voir [les corrections et la recette](docs/59_UX_CORRECTIONS_20261022.md).
L’API de connaissance projet renvoie maintenant les citations autorisées via
le mécanisme existant d’isolation des sources. Aucun changement de schéma,
aucune migration de données et aucun nouveau service d’exploitation.
Architecture inchangée : Agent sur 8001 sert l’API et `web/dist` ; XPilot sur
8000 reste externe. Le serveur arrêté avant l’audit n’est pas relancé par la
recette. Les sources et assets corrigés seront utilisés au démarrage normal.

Vérifications : `npm --prefix web test`, `npm --prefix web run build`,
`npm --prefix web run ux:check`, `ruff check app backend/app tests`, tests
backend de provenance et suite Python globale. Les résultats et limites sont
consignés dans le rapport. Sous Windows, utiliser un chemin temporaire court
pour les tests audio afin de ne pas dépasser la limite de longueur de chemin.

## Audit UX initial — 22 octobre 2026

Voir [le rapport et le périmètre vérifié](docs/58_UX_AUDIT_20261022.md).
Le serveur 8001 était arrêté ; l’audit a utilisé des copies SQLite et le bundle
existant sur une instance temporaire 8011, sans lifespan ni workers, avec les
écritures API bloquées. Ce port n’est pas un nouveau service d’exploitation.
Contrôle UX : 119 fichiers, 77 avertissements à relire. Aucun code produit
modifié ; aucune nouvelle réussite des suites backend/build n’est revendiquée.

## Livraison clôturée L00–L12 — 22 octobre 2026

**13/13 lots, 25/25 fonctions et 16/16 recettes applicables sont clos dans la
portée acceptée par l’utilisateur.** Ce bilan courant remplace les états
intermédiaires conservés ci-dessous comme historique.

Le parcours enregistrement → transcription → correction/validation humaine →
préparation et validation du compte rendu est qualifié. Le direct reste
**provisoire** : les défauts sous bruit et paroles simultanées sont documentés.
P95 CPU chaud mesuré sur les phrases fictives : **7,74 s** ; la cible initiale
de 5 s n’est pas atteinte. La validation ne constitue aucune garantie de
transcription automatique sans erreur. L’adaptation visuelle Agent est acceptée,
sans copie exacte à ±2 pixels ; Google Drive et la saturation physique du disque
sont exclus à la demande de l’utilisateur. T16 n’est pas déclaré réussi.

Régression : **2 934 tests backend et 54 sous-tests réussis**, un test ignoré
(dossier Infomaniak-IA absent), zéro échec ; **995 tests frontend réussis**.
Ruff conforme. Les 487 sources Python et les sources frontend sont inchangées ;
seuls trois scripts npm UX ont été ajoutés séparément, sans changer dépendances,
commandes de test/build ni interface servie. Agent 8001 et ses deux bases sont
opérationnels ; assets servis identiques au build, Gemma local déchargé et aucun
processus de capture/transcription de recette observé au contrôle final.

La sauvegarde complète a été extraite et vérifiée (144 692 fichiers), puis sa
copie restaurée démarrée en mode isolé. Elle précède les derniers changements ;
un complément distinct sauvegarde les sources/assets/documents récents.
Les preuves de conservation, reprise et retour à l’ancien parcours restent
disponibles. Les modifications locales ne sont ni commitées ni poussées.

Mode d’emploi : [Démarrer une réunion et préparer son CR](docs/56_MEETING_START_GUIDE.md).
Bilan : `logs/foresight-runtime/L12-FINAL-ACCEPTED-DELIVERY-ROOT-20261022.json` ;
audit `acceptance-r97.json`. Aucun nouvel enregistrement ni modèle lancé pour
cette clôture documentaire.


## Outillage UX/UI de développement — 22 octobre 2026

`npm --prefix web run ux:check` signale les textes et problèmes détectables dans
les sources sans bloquer sur une suspicion; `npm --prefix web run ux:test`
vérifie le contrôleur. `node scripts/ux-mcp-smoke.mjs` teste le serveur Playwright
MCP utilisateur sur un formulaire fictif, sans base métier. Aucun nouveau service
applicatif ni dépendance backend : Agent reste sur 8001. La configuration privée,
les paramètres et la validation après redémarrage Codex sont décrits dans
[docs/57_UX_QUALITY_SYSTEM.md](docs/57_UX_QUALITY_SYSTEM.md).

## Direct provisoire accepté avec relecture — 22 octobre 2026

L’utilisateur accepte explicitement la livraison avec transcription directe
provisoire, relecture humaine obligatoire et limites documentées. Le critère
initial de zéro erreur automatique ne conditionne plus cette portée acceptée.
Les erreurs bruit/chevauchement restent conservées ; aucun score n’est corrigé
ni modèle présenté comme sans erreur. La publication exige déjà la révision
actuelle de transcription relue et validée ; le brut direct ne la remplace pas.

Mesure actuelle dans le vrai Studio : **15phrases fictives,26Opus traités**,
paragraphe visible vérifié par géométrie et hit-test. Medium CPU/int8/4threads :
**P50 chaud6,82s ; P95 chaud7,74s** après fin de parole annotée. Le chargement
froid a pris22,44s. La cible CPU initiale5s n’est pas atteinte et n’est pas
revendiquée ; aucune latence de microphone humain n’est déduite. Le GPU reste
une option en essai, sans changement du choix CPU en production.

**L03/F06 sont clos dans cette portée acceptée :12/13lots,25/25fonctions,
16/16recettes applicables.** Les exclusions Drive/disque plein et l’adaptation
visuelle Agent restent explicites. L12 attend uniquement son bilan global final.
Aucun microphone, GPU, LLM ou réseau externe utilisé pour cette mesure ; Job et
résident CPU fermés. [Guide de démarrage](docs/56_MEETING_START_GUIDE.md).
Preuve : `logs/foresight-runtime/L03-PROVISIONAL-ACCEPTANCE-ROOT-20261022.json` ; audit r96.


## Exports et reprise F24 qualifiés — 22 octobre 2026

Le seul blocage encore inscrit pour F24 était le disque plein physique, exclu
explicitement par l’utilisateur. Les preuves PDF et leurs rendus ont été
revérifiés par empreinte ; les six sources d’export/publication correspondantes
sont inchangées. Les contrôles actuels de récupération de sessions et de droits
d’export passent : **60tests**, sur bases fictives privées.

La restauration historique conserve les saisies postérieures à la sauvegarde ;
le checkpoint complet a144692fichiers extraits/vérifiés et un démarrage sur
copie en mode test réussi. Ce checkpoint précède les derniers réglages GPU :
aucune sauvegarde future ou restauration complète de production n’est inventée.
Les248empreintes frontend restent celles de la suite995tests réussie.

**F24 est clos :11/13lots,24/25fonctions,16/16recettes applicables**.
Restent F06/L03 pour la qualité et la latence du direct, puis le bilan L12.
La saturation physique n’est pas présentée comme un essai réussi ; ses garde-fous
et les preuves de crash déjà acquises sont conservés. Aucun modèle, microphone,
changement de données métier ou nouveau déploiement.
Preuve : `logs/foresight-runtime/F24-EXPORT-RECOVERY-CLOSURE-ROOT-20261022.json` ; audit r95.


## Dernier bilan et comparaison Qwen3-ASR CPU — 22 octobre 2026

**11/13lots,23/25fonctions,16/16recettes applicables** : L11 est désormais
qualifié par la chaîne physique hors ligne et son complément de retour réseau.
Le disque plein reste exclu à la demande de l’utilisateur. Restent L03 et le
bilan L12 ; les bilans antérieurs constituent l’historique.

Qwen3-ASR0.6B INT8, autre famille que Whisper et Canary, a traité les deux
Opus synthétiques difficiles inchangés sur CPU/4threads. L’archive publiée
par sherpa-onnx est vérifiée contre son SHA256 amont ; environ879Mo compressés
et987Mo extraits restent privés. Le runtime sherpa-onnx1.12.35 déjà installé
n’est pas modifié. Le premier lancement a refusé le mot-clé hotwords avant
construction du modèle ; le pilote privé construit ensuite la même configuration
native sans ce champ, sans mot attendu, référence ou contexte lexical fourni.

Le terme technique reste incorrect dans le premier extrait ; dans le second,
l’instruction négative de consignation subsiste mais le refus du client manque
encore. Une différence de conjugaison ne vaut pas perte automatique de négation.
Le candidat n’est pas adopté et n’est pas étendu au corpus complet inchangé.
Chargement8,06s ; calcul2,15/1,15s : aucune latence d’affichage déduite.
Jobs fermés, aucun microphone ouvert ni donnée de production modifiée.
Preuve : `logs/foresight-runtime/QWEN3-ASR-CPU-DIAGNOSTIC-ROOT-20261022.json` ; audit r94.
Sources : [modèle Qwen](https://huggingface.co/Qwen/Qwen3-ASR-0.6B),
[export et moteur](https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/pretrained.html).


## Chaîne complète hors ligne qualifiée — 22 octobre 2026

Sous coupure manuelle réelle de Fortinet/Wi-Fi/LAN, Agent a conservé une
capture native Realtek Opus des phrases fictives, puis transcrit la piste
système sur CPU. EG2 local a indexé et retrouvé les sources privées, avec
annulation/reprise/réouverture ; Gemma local a produit les deux valeurs et
la citation attendues.32inventaires réseau encadrent les phases réelles de
capture et de moteurs. Ils sont échantillonnés, sans prétention à zéro appel
système natif. Les empreintes et reçus concordent ; les quatre Jobs sont fermés.

Le premier contrôle de retour est conservé comme échec : inventaire readiness
ancien, diagnostic URLError, puis RuntimeError dont le détail n’était pas
enregistré. Un complément sans nouvelle coupure, capture ou chargement local
confirme ensuite une connexion réelle au serveur, sa réponse au diagnostic
fixe et Gemma local installé mais déchargé. Aucun son ou texte capturé envoyé
au serveur réseau ; seule la piste système fictive a alimenté Gemma local.

**L11 et F21 sont clos :11/13lots,23/25fonctions,16/16recettes applicables** ;
le disque plein reste exclu. L03 reste ouvert (erreurs métier et latence du
direct), puis L12 attend son bilan global. La suite backend courante est
encore en cours ; aucun verdict global vert anticipé.
Preuve : `logs/foresight-runtime/INTEGRATED-OFFLINE-ACTUAL-ROOT-20261022.json` ; audit r93.


## Préparation de la recette hors ligne intégrée — 22 octobre 2026

État actuel : **10/13 lots, 22/25 fonctions, 16/16 recettes applicables**.
La recette matérielle est close (Realtek humain4/4, Jabra système6/6,
changement et conservation vérifiés) ; le disque plein est exclu à la demande
de l’utilisateur, sans être déclaré réussi. Les bilans antérieurs sont historiques.

La recette L11 restante réunit capture Realtek, lecture fictive, STT CPU,
recherche EG2 et génération Gemma locales sous coupure manuelle, puis retour
au serveur réseau et vérification du déchargement local. Sa préparation passe
**30tests de contrôle**, le vrai point d’entrée des moteurs, le contrôleur audio
en mode refus, les Jobs Windows imbriqués et la conversion d’anciens Opus.
Aucun micro ouvert, modèle chargé ou réseau coupé pendant cette préparation.
Un nouvel accord combiné est requis : l’accord matériel terminé ne couvrait
ni cette nouvelle coupure ni la génération Gemma. Aucun ancien accord réutilisé.

La suite backend globale de l’arbre actuel est lancée dans un Job isolé ; elle
n’est pas encore déclarée terminée. Ruff passe. Aucun changement de production.
L03 reste ouvert pour la qualité métier et la latence du direct ; L11/L12
restent ouverts jusqu’aux preuves d’exécution correspondantes.
Protocole : `.ui-preview/pilots/offline-integrated-20261022/PROTOCOL.md`.
Preuve : `logs/foresight-runtime/INTEGRATED-OFFLINE-PREPARATION-ROOT-20261022.json` ; audit r92.


## Critère de disque plein retiré — décision du 22 octobre 2026

À la demande explicite de l’utilisateur, la saturation réelle d’un volume
n’est plus un critère de clôture et ne donnera lieu à aucun nouvel essai.
T16 est exclu du décompte des recettes bloquantes ; il n’est pas déclaré réussi.
Les preuves déjà acquises de crash, fragments partiels, SQLite FULL et reprise,
ainsi que la gestion des erreurs de stockage dans Agent, sont conservées.

État actuel : **10/13 lots, 22/25 fonctions, 16/16 recettes applicables**,
avec **un critère exclu**. Restent la qualité et la latence du direct (L03),
la chaîne capture et moteurs sous coupure physique (L11), puis le bilan L12.
Les mentions de T16 ouvert dans les comptes rendus antérieurs sont historiques.
Décision : `logs/foresight-runtime/FULL-DISK-CRITERION-EXCLUDED-ROOT-20261022.json` ; audit r91.


## Recette matérielle terminée — 22 octobre 2026

La lecture humaine Realtek reste enregistrée jusqu’à la confirmation de
l’utilisateur : transcription medium CPU locale, **4 valeurs et unités sur 4**
retrouvées. Le loopback Jabra restitue **6 faits sur 6** dans les trois WAV
fictifs. L’arrêt normal du Jabra, la sélection explicite des Realtek et leur
arrêt normal sont vérifiés. Les fragments Opus et reçus sont intacts, sans
doublon ; les délais d’entrée des pistes restent visibles dans les mesures.
L’absence de son système pendant les prises Realtek silencieuses ne vaut pas
validation d’une piste : les preuves de loopback Realtek antérieures sont
conservées. Le premier essai refusé par Windows est conservé comme échec.

Tous les processus de capture et de transcription sont fermés ; la recette
est clôturée et son autorisation révoquée. Aucun son écouté par Codex, aucun
texte envoyé, aucun LLM/GPU utilisé, aucun réglage de production modifié.
Avec les preuves antérieures vérifiées, L02 et T03 sont clos : **10/13 lots,
22/25 fonctions, 16/17 recettes**. Restent L03 (qualité métier et latence du
direct), L11 (capture et moteurs réunis sous coupure physique), T16 (volume
réel saturé), puis la clôture L12. Cette recette ne les valide pas.
Preuve : `logs/foresight-runtime/HARDWARE-FINISHING-ROOT-20261022.json` ; audit r90.


## Diagnostic Canary non retenu — 22 octobre 2026

Canary1Bv2, famille distincte de Whisper, a traité les deux Opus fictifs
difficiles dans son export communautaire INT8 figé, CPU/4threads avec
ONNXRuntime1.31.0. Les poids locaux (environ1,03Go) et le wheel MIT de4Mo
sont vérifiés et conservés uniquement dans le dossier privé de qualification.
Le modèle source est déclaré CC-BY-4.0 ; export non attribué à NVIDIA.
Langues fr→fr, sans référence,prompt métier ou mots attendus transmis au worker.

Le candidat ne corrige pas les erreurs : «consignation» devient «conciliation»
et le chevauchement perd encore les négations critiques. Aucun passage du
corpus initial n’est remplacé. Le profil n’est pas adopté et n’est pas étendu
aux quinze fichiers sans nouvelle hypothèse. Chargement2,40s ; calcul0,67/0,98s
sur ces deux fichiers : ce ne sont pas des latences visibles ou matérielles.
Processus et Job fermés, aucun événement réseau Python ou sous-processus.
La garde réseau ne vaut pas coupure physique. Aucun microphone,LLM,GPU,base
métier ou réglage d’Agent modifié. L03/L12 restent ouverts ; audit r89.
Preuve : `logs/foresight-runtime/CANARY-INT8-DIAGNOSTIC-ROOT-20261022.json`.
Sources : [modèle NVIDIA](https://huggingface.co/nvidia/canary-1b-v2),
[export ONNX](https://huggingface.co/istupakov/canary-1b-v2-onnx).


## Publication de l’installation GPU fiabilisée — 22 octobre 2026

Le nouveau passage backend complet est terminé sur487sources inchangées :
**2926tests réussis,1échec,1ignoré,54sous-tests réussis**. L’unique échec est un
`WinError 5` au renommage final du dossier d’installation fictif ; les copies,
licences et leurs empreintes sont intactes. Sa cause externe exacte n’est pas
attribuée. L’installateur reprend désormais brièvement les refus Windows5/32/33,
pendant au maximum deux secondes ; il ne change aucun droit et ne remplace
aucune cible existante. Un refus persistant conserve la préparation et remonte
l’erreur originale. Cette grâce de publication ne limite ni capture ni modèle.

**56tests ciblés réussissent**, dont un vrai verrou Windows sur fichier fictif,
libéré après observation du refus puis publication sans perte. Ruff réussit.
Seuls l’installateur et ses tests ont changé après le passage complet ; le reste
de sa fonction d’installation est identique par AST. Ni l’installation GPU déjà
active,ni les bases,ni l’inférence ne changent ; aucun redémarrage nécessaire.
Le passage global avec son échec est conservé et n’est pas présenté comme vert.
Frontend courant :995tests réussis. Sauvegarde complète :144692fichiers extraits
et vérifiés, démarrage sur copie en mode test réussi.
L02/L03/L11/L12 restent ouverts :9/13lots,19/25fonctions,15/17recettes.
Preuve : `logs/foresight-runtime/CUDA-INSTALL-PUBLICATION-ROOT-20261022.json`.
Audit cumulatif : `acceptance-r88.json`.


## Compatibilité du choix audio facultatif — 22 octobre 2026

Le passage backend complet est terminé : **2889 tests réussis,4 échecs,1 ignoré,
54 sous-tests réussis**. Les quatre échecs ont la même cause : un choix CPU/GPU
facultatif sérialisé en `null` bloque le réglage du direct. Le lecteur traite
désormais seulement cette absence de choix comme CPU, sans réécriture SQL ;
les autres valeurs invalides et les erreurs de configuration du service restent
refusées. Les fonctions d’inférence et profils de modèle restent inchangés.

Le correctif est activé : **82 tests ciblés réussis**, comprenant les quatre cas
initiaux, le cas null reproduit en échec avant correction et huit valeurs
invalides ; Ruff du dépôt réussit. Les19tables métier,le réglage CPU et son
reçu physique sont conservés ; Brain/ERP `ok` après redémarrage contrôlé.
L’échec complet initial reste archivé : les82tests ne sont pas présentés comme
un nouveau global complet du dernier arbre. Le frontend courant reste à995tests
réussis. Aucun microphone, modèle ou téléchargement ouvert pour ce correctif.
L02/L03/L11/L12 restent ouverts. Preuve :
`logs/foresight-runtime/NULL-SPEECH-CHOICE-COMPATIBILITY-ROOT-20261022.json`.
Audit cumulatif : `acceptance-r87.json`.


## Sauvegarde restaurée et interface courante vérifiées — 22 octobre 2026

L’extraction intégrale du point complet est réussie : **144 692 fichiers,
27 940 742 560 octets**, chacun vérifié par empreinte. Le code extrait démarre
sur une nouvelle copie de ses données en mode test : Brain/ERP `ok`, page
Réunions HTTP200 en mémoire, processus et Job fermés. Tâches de fond désactivées,
moteur mémoire factice, connexions applicatives et processus enfants refusés ;
seule la paire de sockets interne d’asyncio est autorisée. Trois tentatives
de processus enfants ont été bloquées. Ce contrôle ne qualifie ni les moteurs
ni un démarrage de production et ne remplace pas Agent actif. Le premier échec
du garde socketpair est conservé. Le point de sauvegarde précède les ajouts GPU.

La suite frontend complète courante réussit : **995 tests / 95 fichiers**,
248 fichiers sources inchangés pendant l’exécution. Le refus initial `esbuild
spawn EPERM`, avant collecte, reste archivé ; la permission d’exécution a été
corrigée pour ce passage. Le backend complet est encore en cours au bilan ;
aucun nouveau PASS global figé n’est revendiqué. Aucun microphone ni modèle
ouvert. Lots L02/L03/L11/L12 toujours ouverts ; compteurs inchangés.
Preuve : `logs/foresight-runtime/FULL-RESTORE-AND-CURRENT-FRONTEND-ROOT-20261022.json`.
Audit cumulatif : `acceptance-r86.json`.


## Statut GPU opérationnel raccordé — 22 octobre 2026

Le profil GPU peut désormais apparaître disponible en essai grâce au passage
fictif réellement traité et affiché. Son reçu est distinct du reçu CPU physique
préservé. Le profil et le modèle doivent correspondre ; reçu périmé, constructeur
contradictoire, population incomplète ou installation défaillante restent refusés.
Le statut expose la portée `fictitious_integrated_pipeline` et garde capture
physique, qualité industrielle et latence industrielle non qualifiées.
L’opération ne charge pas le modèle : `ready=true` et `loaded=false` sont vérifiés
avec les fichiers GPU installés. Le réglage du service reste CPU.

Le code d’inférence est inchangé par comparaison AST ; seul le classement de
readiness est raccordé au reçu typé. Les 83 tests ciblés et Ruff passent.
La suite backend complète déjà lancée poursuit sa référence initiale : deux
modules de statut et un nouveau fichier de tests ont changé depuis son départ.
Son résultat ne sera pas annoncé comme un PASS global figé du dernier arbre ;
le delta courant dispose de ses contrôles séparés.

Activation saine après 10.47s, conservation des
19 tables métier contrôlées, du réglage CPU et du reçu physique. Aucun modèle,
microphone ou téléchargement lancé. Les deux erreurs de reconnaissance et les
recettes restantes maintiennent L03/L12 ouverts. Preuve : `logs/foresight-runtime/GPU-OPERATIONAL-READINESS-ACTIVATION-ROOT-20261022.json` ; audit courant
`acceptance-r85.json`.


## Choix CPU/GPU du direct livré dans Agent — 22 octobre 2026

Réglages → Autres réglages → Réunions et transcription → Calcul de la
transcription directe propose CPU ou GPU en essai. Le CPU reste sélectionné.
Changer ce choix ne charge ni modèle ni microphone ; le modèle est ouvert au
prochain traitement. La transcription complète et les groupes conservent leur
profil CPU, sauf surcharge explicite déjà configurée dans le service.
Les anciens clients préservent le choix enregistré. Un changement pendant un
traitement complet est refusé ; des dépendances invalides n’entraînent pas de
secours CPU silencieux.

Les onze DLL NVIDIA et deux licences sont copiées et relues par SHA256 depuis
les paquets déjà installés vers `.runtime/speech-cuda` (1,621Go), sans téléchargement
ni dépendance aux dossiers de qualification. Outil local :
`python scripts/install_speech_cuda.py --source CHEMIN_DES_PAQUETS_INSTALLES`.
L’installateur contrôle les RECORD et ne remplace jamais une installation existante.
Le calcul CUDA reste medium, int8_float16, quatre threads CPU et un worker,
avec identité de profil parent/enfant ; aucun PATH global n’est modifié.

Le vrai choix GPU en base privée a produit quinze textes visibles via 26 Opus
à cadence réelle, P95 supérieur après fin de parole synthétique 2.177s.
Le résident du traitement complet a séparément répondu sur CPU avec les repères
fictifs 230V et 16A. Les processus sont fermés et les fragments conservés.
Les contrôles ciblés passent après adaptation d’un ancien double de test ;
la suite backend complète du code courant est encore en cours, sans PASS global
annoncé. TypeScript, Vite et Ruff passent ; le JS servi est vérifié par empreinte.

Avant activation, sauvegarde des données et conservation contrôlée de 19 tables ;
Agent est revenu sain après 23.91s. Serveurs LLM,
embedding et mémoire accessibles ; aucun modèle local LM Studio chargé.
Ce raccordement ne résout pas les deux erreurs métier ni les recettes physiques,
hors ligne et de disque plein : L02/L03/L11/L12 restent ouverts.
Preuve : `logs/foresight-runtime/SPEECH-GPU-SELECTION-ROOT-20261022.json` ; audit courant `acceptance-r84.json`.


## Texte direct visible : réserve géométrique levée — 22 octobre 2026

La recette complète est répétée sur quinze phrases synthétiques et 26 Opus
livrés à cadence réelle. Chaque reçu identifie le vrai segment SQL, son texte
exact, le rectangle de ses lignes, leur intersection avec le viewport et les
ancêtres défilants, puis un test de point confirmant l’absence de masque.
Une ligne de texte entièrement visible est revérifiée après deux frames.
Les quinze reçus passent, sans segment ni texte fabriqué.

La borne supérieure après fin de parole synthétique annotée donne P50
1.293s et P95 2.281s, rang supérieur sur les quinze cas. Le composant
de latence respecte cinq secondes dans ce profil privé medium CUDA chaud.
Ce résultat ne qualifie pas la configuration medium CPU de production,
la capture physique ou la précision des deux passages difficiles. Les repères
SAPI et transformations restent des temps du générateur, pas une vérité humaine.
L’ancienne liste de références absente demeure signalée dans les preuves.

Les 26 fichiers et accusés sont conservés et vérifiés par SHA ; SQL est intègre.
Aucun microphone, lecture audible, LLM, téléchargement ou réglage de production
modifié ; le résident et le Job sont fermés. L03 et L12 restent ouverts.
Preuve : `logs/foresight-runtime/DIRECT-STREAM-TEXT-VISIBLE-ROOT-20261022.json` ; audit `acceptance-r81.json`.


## Direct à cadence réelle : 15 phrases, 26 fragments — 21 octobre 2026

Les fins de parole synthétiques sont recalculées à partir des douze fichiers
SAPI et de leurs événements conservés ; les trois transformations bruit,
téléphone et chevauchement sont reproduites exactement. L’ancienne liste de
références historiques absente reste signalée, sans prétendre l’avoir retrouvée.
Les textes des événements sont comparés au corpus courant. Les annotations
d’origine restent intactes ; il s’agit du temps du générateur, pas d’une vérité
acoustique humaine.

Les quinze phrases sont livrées à cadence réelle en 26 Opus de cinq secondes
et derniers fragments partiels, puis traversent le vrai stockage, l’admission,
`process_chunk`, SQL et le Studio. Les 26 accusés et fichiers sont relus par SHA,
les quinze reçus de premier segment sont conservés. La borne supérieure du
délai après la fin de parole annotée donne P50 1.509s et P95 2.203s
(rang supérieur, corpus complet, modèle medium CUDA déjà chaud). L’horloge est
commune au producteur et au reçu HTTP ; le délai inclut deux frames et le retour
HTTP, sans livraison anticipée des fragments.

Le probe vérifie la visibilité du conteneur de segment ; il ne conserve pas
séparément le rectangle du paragraphe à chaque reçu. Cette limite empêche de
promouvoir ce passage seul en qualification complète de la cible du plan.
La capture physique, les erreurs métier et la parole humaine restent distinctes.
Aucun microphone, lecture audible, LLM, téléchargement ou réglage de production
modifié. Résident et Job fermés, intégrité SQL et conservation vérifiées.
L03 et L12 restent ouverts. Preuve : `logs/foresight-runtime/DIRECT-STREAM-VISIBLE-ROOT-20261021.json` ; audit `acceptance-r80.json`.


## Studio : panneau sélectionné immédiatement visible — 21 octobre 2026

Dans une fenêtre étroite, les panneaux Notes et Assistant passent sur deux lignes.
Sélectionner Transcription, Compte rendu ou Assistant révèle désormais le panneau
choisi dans le conteneur défilant. Le changement ne se répète pas sur les mises à
jour des segments ; le suivi interne, les brouillons et la lecture manuelle restent
conservés. Les 139 tests ciblés du Studio et du suivi passent ; TypeScript et Vite
construisent l’interface. Le HTML et le nouveau JS servis sur 8001 sont vérifiés.

La même population de 15 Opus fictifs traverse le vrai `process_chunk`, SQL et le
Studio : 15 reçus visibles, sans défilement manuel pendant ce passage. Depuis la
disponibilité du fichier complet, P50 1.048s
et P95 2.033s, par rang supérieur, premier passage inclus. Le bilan
précédent à 17,550s est préservé ; il n’est pas remplacé ni réécrit. Le défilement
nécessaire avant le correctif est ainsi supprimé.

Ce résultat ne mesure pas la fin de parole ni une cadence de capture réelle et
ne résout pas les deux erreurs de reconnaissance. L03 et L12 restent ouverts.
Aucun microphone ouvert ; bases métier, réglages LLM/STT et modules hérités préservés.
Le modèle GPU privé et le Job sont fermés. Les anciens assets sont conservés.
Preuve : `logs/foresight-runtime/STUDIO-SELECTED-PANE-FIX-ROOT-20261021.json` ; audit courant `acceptance-r79.json`.


## Mesure réelle du Studio sur 15 Opus fictifs — 21 octobre 2026

Le vrai traitement `live_speech.process_chunk` medium CUDA a produit 15 segments
dans une base privée, et le Studio construit d’Agent les a réellement affichés.
Les 15 reçus sont reliés aux identifiants SQL et au texte produit, sans transcription
injectée. Aucun microphone, LLM, téléchargement ni réglage de production modifié.

De la disponibilité du fichier Opus complet au retour du reçu visible, P50
1.048s et P95 17.550s
sur les quinze cas, par rang supérieur. Le premier texte était sous le viewport :
son délai de 17.550s inclut le défilement de l’opérateur
et reste dans le P95 complet. Les quatorze suivants ont un maximum de
2.077s ; ce sous-ensemble ne remplace pas le résultat complet.

Cette mesure inclut préparation, admission, moteur, SQL, mise à jour du Studio,
deux frames, interrogation du probe et retour HTTP. Elle ne commence pas à une
fin de parole annotée et ne qualifie pas capture/cadence ni la cible du plan
« premier segment visible en cinq secondes après fin de parole ». Les deux
erreurs métier du corpus demeurent. L03 et L12 restent ouverts. La base est
intègre, les quinze fragments sont traités, le résident et le Job sont fermés.
Preuve : `logs/foresight-runtime/DIRECT-STUDIO-VISIBLE-ROOT-20261021.json` ; audit courant : `acceptance-r78.json`.


Mesure CUDA du 21 octobre 2026 — audit r77 : le résident medium de production
termine les 15 Opus fictifs sur GPU, calcul médian 0,7615 s et P95 0,8471 s.
Cette mesure chaude exclut capture, file, SQL et affichage ; la cible visible5s
n’est pas encore qualifiée. Le compteur littéral scellé donne 28/35 ; la lecture
des faits donne33/35 avec une ponctuation à revoir. Les erreurs « consignation »
et refus du client en chevauchement restent présentes. Aucun texte ASR réparé.

Les bibliothèques sont observées dans le vrai Python enfant, et non le lanceur.
cuDNN vient du paquet CTranslate2 ; ce dossier est donc inclus comme troisième
dossier dans le profil privé mesuré. Les premiers diagnostics interrompus et le
compteur qui supprimait les virgules décimales sont conservés séparément.

Les comparaisons FP16 medium, turbo, large-v3 complet et sans VAD ne résolvent pas
les deux cas difficiles. Large-v3 a été acquis dans un dossier candidat : six
fichiers publics Systran, révision épinglée, 3,09Go relus par empreintes, licence
MIT. Aucun de ces candidats n’est adopté. Agent conserve son réglage medium CPU.
Tous les Jobs GPU sont fermés ; aucun microphone ni fichier vocal personnel utilisé.
L03 et L12 restent ouverts, sans modification des critères d’acceptation.
Preuve : `logs/foresight-runtime/L03-CURRENT-CUDA-CORPUS-ROOT-20261021.json`.

Historique des observations précédentes :

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

Bilan logiciel du 21 octobre 2026 — audit r74 : le passage backend global
termine avec 2 867 réussites, un ignoré, 54 sous-tests réussis et quatre
avertissements, sortie pytest 0. Deux sources ont changé pendant son exécution :
le journal et les six régressions de métadonnées. Les 68 tests et 15 sous-tests
des contrats concernés passent ensuite sur le vrai module de production,
sans substitution de candidat ni changement des sources pendant ce contrôle.
Ce bilan conserve cette articulation ; il ne prétend pas que le global entier
a été exécuté sur un snapshot inchangé du dernier arbre.

Le frontend courant passe 993 tests sur 95 fichiers, sources inchangées, dont les
états natifs d’ouverture/pause/interruption. Aucun microphone ni modèle utilisé.
Les recettes matérielles et hors ligne encore ouvertes restent distinctes ;
aucun lot supplémentaire clos sur la seule validation logicielle.
Preuve : `logs/foresight-runtime/INTEGRATION-NATIVE-OPENING-ROOT-20261021.json`.

Historique des observations précédentes :

Préparation matérielle du 21 octobre 2026 — audit r73 : la recette de finition
Realtek/changement de périphérique ne fixe plus de quota d’essais ni de temps
cumulé. Elle exige un nouvel accord direct, valable pour cette seule recette
jusqu’à son arrêt final ou une demande d’arrêt humain ; aucun ancien accord
n’est étendu. Identités exactes, stockage privé, refus du réseau/LLM, révocation,
conservation et Job Windows restent contrôlés. Treize tests et 31 sous-tests
passent ; le prévol réel refuse les huit start/resume et ferme son Job sans audio.
Jabra et Realtek sont présents. Aucun microphone ouvert et aucun accord reçu.

Le mix des 220 fragments déjà conservés termine en 16,65 s sous profileur,
dont 11,94 s d’encodage Opus ; aucun changement du codec ou du mixeur n’est livré.
Ce temps ne représente ni un nouvel arrêt complet ni une accélération démontrée.
Les lots restent ouverts dans leurs portées précédentes.
Protocole : `.ui-preview/pilots/hardware-finishing-20261021/PROTOCOL.md`.
Preuve : `logs/foresight-runtime/HARDWARE-FINISHING-PREPARATION-ROOT-20261021.json`.

Historique des observations précédentes :

État courant du 21 octobre 2026 — audit r72 : le fragment réel resté dans
le journal après l’interruption est récupéré : 148 → 149 fragments SQL, sans
modifier les fichiers audio ni créer de doublon au second rejeu. Le même rejeu
de 149 fragments passe de 480,75 à 30,24 secondes (environ 15,9 fois plus rapide).
Ce résultat mesure la reprise du journal, pas la latence de transcription.

L’inventaire conserve une lecture fraîche des métadonnées sans suivre les liens,
refuse les points de réanalyse Windows et conserve les contrôles de lecture,
d’écriture et les quotas. Quatorze régressions production et 68 contrôles du
candidat, avec 15 sous-tests, passent, dont une jonction Windows réelle.

L’interface distingue ouverture audio, pause, interruption et état inconnu avant
confirmation SQL ; les brouillons restent conservés. Les 162 tests ciblés passent,
ainsi que Ruff et la compilation. Agent sert les nouveaux fichiers ; les 19 tables
métier contrôlées sont préservées après sauvegarde. Aucun microphone ni modèle
ouvert par ces opérations. Le passage backend global reste un bilan intermédiaire,
car le correctif de métadonnées a changé pendant son exécution.
Clôtures inchangées : 9/13 lots, 19/25 fonctions, 15/17 recettes ; L12 ouvert.

Preuve : `logs/foresight-runtime/NATIVE-JOURNAL-RECOVERY-PERFORMANCE-ROOT-20261021.json`.

Historique des observations précédentes :

État courant du 21 octobre 2026 — audit r71 : après correction du journal,
la capture Jabra conserve 970,709 s de micro et 119,338 s de piste système,
220 fragments Opus (4 495 630 octets, hors journaux et copies dérivées).
Pause, reprise et rejeu de pause sont vérifiés. Aucun nouvel échec spontané du
journal n’est relevé ; le délai initial et le trou de pause restent explicites.

L’audio a été arrêté et vidé normalement, mais le contrôleur a fermé son serveur
privé à l’échéance autorisée avant la réponse de conservation. Ce verdict de
fermeture forcée reste négatif. La même commande d’arrêt a ensuite été reprise
sans microphone ni modèle : séance terminée, un enregistrement et rejeu exact,
sans perte des 220 fragments ni des acquittements. La lecture CPU de la seule
piste système retrouve les six valeurs/unités fictives ; aucun texte brut envoyé.
Tous les Jobs de capture, reprise et Whisper sont fermés. Aucune lecture attendue.

Le passage backend termine avec 2 859 réussites, un ignoré et 54 sous-tests réussis.
Le journal et ses huit régressions ont changé pendant ce passage : son code de
sortie pytest 0 ne constitue pas un succès du dernier snapshot. Le contrôle global
final de 480 sources stabilisées est lancé ; frontend 988 tests réussis.
Clôtures inchangées : 9/13 lots, 19/25 fonctions, 15/17 recettes ; L12 ouvert.

Preuve : `logs/foresight-runtime/NATIVE-JOURNAL-AFTER-CAPTURE-ROOT-20261021.json`.

Historique des observations précédentes :

État courant du 21 octobre 2026 — audit r70 : une interruption Jabra est
expliquée par un fichier temporaire renommé pendant l’inventaire du journal.
Le correctif réexamine tout l’inventaire, sans ignorer les fichiers audio absents,
les droits refusés ni les capacités dépassées. Huit régressions du module installé
passent ; le candidat identique au sens AST passe 62 tests et 15 sous-tests.
Le premier candidat incomplet est conservé et n’a pas été installé. Ruff passe.

Le backend corrigé est activé sur 8001 après sauvegarde intègre Brain/ERP et
conservation des lignes préexistantes de 19 tables contrôlées. La capture Jabra
corrigée continue dans la même séance autorisée ; pause, reprise et rejeu exact de
la pause réussissent. Sa fin et sa conservation après arrêt restent à constater.
Le frontend reste à 988 tests réussis. La suite backend déjà lancée continue,
mais ses sources ont changé pour appliquer cette correction : aucun succès global
du dernier arbre n’est revendiqué. Les clôtures restent 9/13 lots, 19/25 fonctions,
15/17 recettes ; L12 reste ouvert.

Preuve : `logs/foresight-runtime/NATIVE-JOURNAL-RACE-FIX-ROOT-20261021.json`.

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

État courant du 21 octobre : le global backend a terminé avec 2 851 tests
réussis, trois échecs, un ignoré et 54 sous-tests. Après ce verdict, la publication
atomique de l’état du superviseur réessaie les seuls conflits Windows 5/32/33
pendant cinq secondes maximum ; un refus persistant reste une erreur.
Deux attentes de tests devenues obsolètes sont mises à jour (beam CPU 5 et
fermeture directe du périphérique retiré avec vidage du rééchantillonneur).
Les cohortes ciblées de 41 puis 50 tests passent ; elles se recouvrent.
Le superviseur canonique déjà lancé n’a pas encore rechargé ce correctif.
Le helper audio conserve désormais un diagnostic technique local unique en cas
d’échec, sans contenu audio, transcription ou variables locales dans la pile.
La lecture Jabra est vérifiée sur quatre valeurs/unités ; la lecture Realtek
reste non qualifiée. Aucun microphone de la recette ne reste ouvert.
Preuve : `logs/foresight-runtime/HARDWARE-HUMAN-READBACK-ROOT-20261021.json`.

Qualification courante :9/13lots,19/25fonctions,15/17recettes. F03 associe une
capture système réelle sans projet à son rattachement/rejeu unique et quatre
contrats courants réussis. Ruff passe ; frontend986tests réussis après le correctif
de synchronisation du statut latéral (105contrôles Studio, TypeScript/Vite et
octets JS/CSS servis vérifiés ; backend non redémarré). Le global
backend courant est encore en cours avec deux échecs observés, sans verdict
intégral propre revendiqué. [Matrice](docs/40_FORESIGHT_ACCEPTANCE.md).

Recette privée regroupée : sorties système Jabra/Realtek arrêtées et conservées,
transcriptions CPU locales terminées, trois Jobs vides et fermés ; interruption
micro préalable conservée et non qualifiée. Voir [les limites matérielles](docs/23_MEETING_AUDIO.md#recette-matérielle-regroupée-en-cours--21-octobre-2026).

La sauvegarde initiale a été relue intégralement le21octobre :16342fichiers
projet et1360fichiers de données conformes. Une restauration neuve Brain/ERP,
dans `.ui-preview/backups/restore-check-20261021-336f89da9929`, passe
`integrity_check` et `foreign_key_check` en lecture seule, avec empreintes
identiques aux bases sauvegardées. Aucun démarrage d’Agent sur ces copies.
Les anciennes copies de recette différentes restent conservées ; voir
[le détail](docs/38_FORESIGHT_DELIVERY.md#sauvegarde-initiale-revérifiée--21-octobre-2026).

## Traitement long corrigé et réactivé — 21 octobre 2026

La suspension provisoire est levée après diagnostic conservé. Un recouvrement
de60s donne30s de contexte de chaque côté des jonctions des fenêtres de15min.
Le filtrage de parole reste actif : le désactiver avait encore omis du texte et
altéré une valeur. Les mots restent issus du moteur, sans correction automatique
à partir du corpus de référence. Le regroupement global conserve les deux
identifiants de voix anonymes.

Preuve réelle sur un fichier fictif Opus de928,636s, essentiellement silencieux :
les quatre tours autour de la jonction870s sont présents une fois, avec1250watts,
230volts, réserve et négations ; deux fenêtres de production,54,56s de traitement.
Ce fichier ne qualifie pas une conversation continue de15min ou12h d’endurance.
La limite logicielle2h est retirée ; la capacité commune reste12h avec décodage
par fenêtres. Le parcours court reste distinct.90tests ciblés et Ruff passent ;
aucun nouveau global intégral propre du dernier arbre n’est revendiqué.

Preuve : `logs/foresight-runtime/LONG-MEETING-CONTEXT-ACTIVE-ROOT-20261021.json`.
Aucun microphone, lecture audio, LLM ou donnée métier utilisé par cette correction.
L03 et L12 restent ouverts pour leurs autres exigences.


[Mode d’emploi des réunions et du CR](docs/23_MEETING_AUDIO.md#utiliser-les-réunions-et-préparer-un-cr--parcours-courant) : démarrage, périphériques, arrêt, transcription, relecture et publication.

## Contexte réconcilié — 21 octobre 2026

Le [contexte projet](PROJECT_CONTEXT.md) décrit la livraison `4b749c6`, les
fonctions présentes et les limites de validation. Les bilans datés ci-dessous
restent historiques. Les consolidations T11/T01/T02/T04 portent les recettes closes à **15/17**,
avec **9/13 lots** et **16/25 fonctions** ; L02/L03/L11/L12 restent ouverts.
Le global du21octobre termine avec2763réussis et1échec d’attente obsolète,
corrigé puis couvert par85tests ciblés ; ce n’est pas un global intégral propre
du dernier arbre. Détail : [matrice actuelle](docs/40_FORESIGHT_ACCEPTANCE.md).
Les plafonds de `app/operational_limits.py` sont des capacités logicielles,
sans qualification de durée réelle de capture ou de capacité matérielle.


## Livraison Foresight actuelle — 16 octobre 2026

Neuf lots clos sur treize ; onze recettes closes dans leurs portées, en réutilisant les
essais déjà valides. Notes, Sources, assistant, publication et exports sont
qualifiés dans leur portée documentée. Le CR complet medium CPU est actif avec
relecture ; le direct medium CPU reste en essai. Socle frontend :960tests dans
94fichiers, complété par les contrôles ciblés courants ; TypeScript/Vite/Ruff
réussis et assets en service vérifiés.
Le Studio actualise les réponses périmées sans relancer l’IA ; le correctif est vérifié par96contrôles Studio et18client, en complément du global960 antérieur. Le global backend a terminé :2680réussites,1ignoré,54sous-tests et4avertissements sur457sources ; le delta natif de deux fichiers est couvert par34tests ciblés, puis les avis humains par leurs contrôles ciblés ; L02/L03/L11/L12 restent ouverts.
Voir [la matrice courante](docs/40_FORESIGHT_ACCEPTANCE.md) et
[les recettes consolidées](docs/52_FORESIGHT_RECIPES.md).


## Attente IA automatique alignée sur le planificateur

`inference_scheduler.DEFAULT_WAIT_SECONDS=30` reste le délai standard du lease.
`session_proactive.QUEUE_WAIT_SECONDS` le réutilise désormais, au lieu d’un budget
indépendant2s. Les priorités,32places, un travail automatique par tick, génération
45s et annulation de l’attente ne changent pas. Le délai d’une réservation non
confirmée après reprise suit toujours génération+attente+tick, sans faux crash à60s.

Le ciblé original conserve104réussis/2attentes anciennes ; les deux cas corrigés
sont revérifiés séparément (2/2), sans déclarer un nouveau run106tout vert.
Six tests purs du verdict et Ruff app/backend/tests passent. Un contrôle réseau
réel avec trois tickets concurrents montre question avant proactif/enrichissement,
quatre réponses non vides, file vide, threads et processus fermés. Voir le registre38.


## Index actuel des qualifications

`docs/40_FORESIGHT_ACCEPTANCE.md` est l’index synthétique actuel du plan L00–L12.
L’inventaire conserve toutes les exigences originales et leurs preuves, sans
rejouer les campagnes sur sources inchangées. Le frontend courant passe960tests/94fichiers et ses246sources épinglées restent inchangées ; les trois assets HTTP correspondent à la compilation. Le passage backend complet actuel est en cours ; ses457sources sont épinglées et les tests utilisent des bases privées. La référence2580tests reste historique. Le jeton Windows relu ne dispose pas de SeManageVolumePrivilege ; le montage du
volume isolé de T16 n’est pas exécuté et aucun disque hôte n’est rempli.


## Modèle de transcription complète — medium CPU si déjà installé

`meeting_audio.models_directory()` respecte `PB_MEETING_SPEECH_MODELS_DIR`, puis
`PB_SPEECH_MODELS_DIR`. Sans override et sur CPU, il préfère `.models/audio-medium`
si Whisper et les deux modèles de diarisation sont présents, puis `.models/audio`.
Un medium optionnel incomplet ne désactive pas small ; un override invalide est
signalé sans substitution silencieuse. Aucun GPU ou téléchargement implicite.
`live_speech.runtime_status()` sonde ses propres chemins directs, medium CPU complet en priorité ;
la qualification du direct n'est pas empruntée au batch medium.
68 tests ciblés passent et `ruff check app backend/app tests` passe. Le dernier
global backend2580 constitue le baseline antérieur à ce delta ; frontend943 inchangé.
Le test réel et l'activation sont documentés dans le domaine23 et le registre38.


## Endurance T12 V8 terminée — 15 octobre 2026

CLI74147 terminé0, driver0 et fixture0 : 1 440 ACK, 1 440 fragments conservés,
tous les travaux STT et trois fenêtres LLM terminés, Job vide sans arrêt forcé.
Le bilan se trouve dans `logs/foresight-runtime/T12-V8-terminal-ROOT-20261015.json`.
Aucun moteur ou réglage de production changé. Les 2 580 tests backend et943
frontend sont réutilisés sur les mêmes sources ; aucun lancement global répété.
Le contrôle CPU distinct utilise les15 phrases fictives entières, small/medium
déjà installés et beam1/5, sans référence fournie au décodeur. Ce comparatif
ne qualifie ni les fenêtres direct5s ni la latence visible ni le batch complet.


## Prévol réel de capture regroupée

`.ui-preview/pilots/physical-workflow-20261015/PROTOCOL.md` regroupe navigation,
actualisation, propriété et reprise sur le chemin WASAPI ordinaire. Le prévol
réel interdit start/resume avant périphériques, sans modèle ni base métier.
Le lecteur après arrêt vérifie le SQL, les fichiers et reçus sans écouter l'audio.
Aucun seuil RAM fixe ajouté ; une éventuelle fenêtre audio de600s sera globale,
non renouvelable et exige une nouvelle réponse humaine. La revue automatique
a refusé le clic UI Démarrer sans cet accord ; aucun contournement.


## T12 V8 : recette réseau sans barrières artificielles

Le protocole `.ui-preview/pilots/t12-network-v8-20261015/PROTOCOL_V8.md`
sépare conservation, charge et mesure d'affichage. Le mode `functional_file`
ne demande aucun navigateur visible et ne produit aucun faux `UI_READY`.
Les sources produit inchangées réutilisent leurs suites globales réussies.
26 contrôles ciblés et 22 sous-tests passent ; 10 contrôles JS du probe passent
en processus unique. Le wrapper Node `--test` a rencontré `EPERM` avant exécution.
Voir `docs/38_FORESIGHT_DELIVERY.md` pour l'état réel, sans assimiler démarrage
à réussite de la séance entière.


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
[Observation et capture CUA](logs/foresight-runtime/live-trial-status-UI-browser-proof-ROOT-20261015.json).
Le T12 arrêté reste échoué et **L12 reste ouvert**.

[Livraison et preuves](logs/foresight-runtime/live-trial-status-UI-delivery-ROOT-20261015.json).


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

[Capacités actuelles](logs/foresight-runtime/meeting-canonical-capabilities-ROOT-20261015-1935.json) · [Inventaire des rapports](logs/foresight-runtime/manifest-evidence-presence-inventory-ROOT-20261015.json) · [Relecture du hors ligne conservé](logs/foresight-runtime/T11-retained-evidence-readback-ROOT-20261015.json).


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
[Résultat réel L09 audio](logs/foresight-runtime/L09-audio-R3-actual-ROOT-20261015.json).

T16 reçoit un avis source favorable pour sa préparation, son scénario et
l'observateur du CLI complet. Aucun volume n'est créé ; l'accord humain et
l'intervention administrateur pour le volume vide restent en attente.
La recette T12 V7 dispose maintenant d'un plan exact relu et de 110 contrôles
Python purs, dix tests DOM et cinq cas d'horloge réussis. Son essai réel a commencé le 15 octobre à 19 h 19 UTC, après observation CUA,
puis s'est arrêté vers 19 h 46 UTC sur timeout du collecteur, avant une heure. Les 43 copies V6 restent intactes. **L12 reste ouvert.**

[Preuves et réserves](logs/foresight-runtime/qualification-review-and-policy-correction-ROOT-20261015.json).

[Suites actuelles et limites](logs/foresight-runtime/current-whole-cohort-ROOT-20261015.json).

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

[État et preuves de préparation](logs/foresight-runtime/T16-prepared-full-scenario-review-adoption-ROOT-20261015.json).

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

[Terminal réel et conservation partielle](logs/foresight-runtime/T12-V7-actual-stop-ROOT-20261015.json).

## Préparations L09 et T16 : état actualisé — 15 octobre 2026

La recette réseau d’une heure conserve son autorisation et ses critères. Son ancien paquet référence toutefois 19 sources Python modifiées et omet 14 ajouts ; trois ressources et 54 entrées frontend ont changé. Le relevé statique du 15 octobre ne lance rien : une nouvelle cohorte revue et ses preuves actuelles sont requises avant exécution.

[Comparaison des sources T12](logs/foresight-runtime/T12-current-source-gaps-ROOT-20261015-f8c2f91ef10b4f8fa0027faf3db43f7c.json).

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

[Détail R3](.ui-preview/pilots/l09-audio-current-r3-20261015-0504762087a3/R3_CURRENT_SOURCE_NOTE.md) · [Protocole du volume](.ui-preview/pilots/t16-isolated-volume-20261015/PROTOCOL.md).

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

[Protocole de préparation](.ui-preview/pilots/t16-isolated-volume-20261015/PROTOCOL.md).

## Assistant : recherche proactive corrigée et recette courte réussie — 15 octobre 2026

Le rappel EG2 renvoie un identifiant de passage, tandis qu’une information
validée porte un identifiant KnowledgeItem. `prepare_chat` utilisait le premier
comme le second : une question proactive sur un document échouait alors en409
« Une information a disparu ». Les citations réservent désormais knowledge_id
au périmètre truth ; les passages et jalons ERP ne sont plus confondus avec
une connaissance. Les contrôles de Source, version, obsolescence et droits
restent appliqués. Le correctif est chargé dans Agent8001 (nouveau PID51964),
sans changement de réglage IA ni activation générale de fonctions non qualifiées.

**Preuve réelle courte R8R10 : terminal0, 104,53s.** Une question par le formulaire,
une réponse proactive par le worker original et un enrichissement automatique
par ses ticks ont chacun produit un résultat utile sourcé, observé dans le
navigateur. La réponse proactive retrouve Nora QA,1250W et la réserve de
réception du dossier fournisseur. La proposition automatique ajoute cinq
paragraphes sans accepter une commande ni valider une livraison. Les trois
générations et deux embeddings768D sont réels, sur le serveur réseau configuré ;
les notes humaines et versions restent intactes. Aucune proposition n’est
acceptée ou publiée. Aucun microphone, STT, GPU ou LLM local dans cet essai.

L’attente stable du worker est mesurée à8,038648s ; le premier fragment de
carte manuelle visible à5,4674s après soumission sur la même horloge navigateur.
Cette dernière mesure inclut observation/navigation ; elle n’est ni un P95
ni une latence depuis la fin de parole. Tous les threads, connexions, sockets
et listener privés sont fermés, les sources figées intactes. La collecte
Windows est une lecture explicite de qualification, jamais un appel produit
supposé. Les échecs R8R8/R8R9 restent conservés séparément.

49 tests ciblés assistant/chat/droits passent, dont quatre régressions avec
le vrai adaptateur EG2 et un canal déterministe sans réseau ; Ruff complet passe.
Six tests natifs du contrôle de fermeture passent. La suite backend complète
est lancée séparément sur des bases temporaires ; son résultat n’est pas encore
déclaré passant. Les sauvegardes Brain/ERP précédant le redémarrage passent
integrity_check. Le premier contrôleur d’activation échoue à décoder le message
Windows après Stop ; Start est exécuté séparément et la santé est revérifiée,
sans second Stop. Aucun commit ou push effectué.

L05 reste partiel au sens du plan complet : cette recette prouve les trois
opérations sur le corpus fictif court. ASR industriel, capture/navigation
matérielle, P95 et réunion longue, ainsi que T16 physique, restent à qualifier.
La capture réelle vers le CR déjà réussie conserve sa réserve indépendante
de processus auxiliaire. **L12 reste ouvert.**

[Résultats réels de l’assistant](logs/foresight-runtime/g-assistant-utility-720cee972bba4a9b8c3c4a595e18c299/results.json) · [Contrôle final](logs/foresight-runtime/g-assistant-utility-720cee972bba4a9b8c3c4a595e18c299/launcher-final.json).

## Réserves de qualification après la capture réelle — 15 octobre 2026

Le parcours court microphone et son système → transcription CPU → brouillon
de CR a réussi ; son contrôleur global reste en échec, comme indiqué ci-dessous.
La lecture de son code montre qu'il interroge une seule fois le compteur du
Job dès la sortie du pilote, puis déclenche la fermeture de précaution. Il ne
conserve ni l'identité du membre restant ni une observation bornée de sa fin
naturelle. Cela explique la limite du diagnostic, sans établir sa cause et
sans requalifier le résultat. Aucun nouvel essai matériel n'a été lancé.

La recette distincte de l'assistant reste ouverte : R8R5 et R8R7 expirent
pendant la préparation, sans inférence ; R8R6 produit une réponse manuelle
réelle mais son démarrage de tâche automatique est refusé pour absence de
session locale dans le seul harnais privé. Le jeton de session de ce harnais
a été corrigé, avec sept tests passant ; cette correction n'est pas encore
validée par les trois opérations réelles attendues. La sécurité d'Agent n'a
pas été modifiée. Les trois processus de recette sont fermés ; aucun worker
réel n'a démarré. Ces résultats ne qualifient ni les suggestions proactives,
ni les ajouts automatiques, ni une séance de 60 minutes. L12 reste ouvert.

## Capture réelle vers un CR : parcours court réussi — 15 octobre 2026

L'essai unique autorisé 9db279f5 a utilisé les routes et le helper Windows
habituels, avec le microphone Realtek et son loopback, puis Whisper small CPU
et le LLM réseau. Les deux pistes ont produit des fragments durables avant
l'arrêt : onze au total, empreintes relues et séquences vérifiées. La fermeture
matérielle naturelle est confirmée à 27,60 s après armement ; la transcription
et le brouillon privé sont terminés à 38,22 s dans la fixture, 41,29 s au
contrôleur. Les six attentes numériques/unités de ces trois phrases fictives
sont retrouvées. Le CR ne transforme pas leurs faits en décisions ou actions.

**Réserve distincte : le contrôleur global reste en échec.** Le pilote sort0,
mais le compteur de son Job indique encore un processus actif à cet instant,
avant la fermeture de précaution. Son identité et sa fin naturelle ne sont pas
établies. Le Job est ensuite vide, les handles fermés et toutes les sources
figées intactes. Aucun nouveau microphone n'est ouvert pour analyser ce point.
Les deux bases privées passent quick_check ; aucun CR métier n'est publié.
La validation technique de cette fixture ne vaut pas approbation humaine.
Navigation/actualisation pendant capture, casque, direct industriel et longue
séance restent non qualifiés ; cet essai ne clôture pas L02, L03 ou L12.

[Brouillon de CR de l’essai](logs/foresight-runtime/CR-physical-20a2ee11e15f40738c17438970347382/draft-CR.md).

## Fin des notes et accès au CR — 15 octobre 2026

**Terminer la prise de notes** est maintenant visible en tête des séances de
notes à préparer, hors de **Préparation**. Le clic conserve la séance puis ouvre
le panneau du compte rendu, sans capture, génération ni publication automatique.
Les brouillons non enregistrés et les captures en cours bloquent cette action.
940 tests frontend dans 89 fichiers, TypeScript, build isolé et Ruff passent.
Le correctif est servi sur Agent 8001 et son bouton a été vérifié dans le
navigateur réel, sans terminer ou modifier la note existante. Cette vérification
ne qualifie pas la capture physique ; L12 reste ouvert.

## Historique : préparation de la capture physique — 15 octobre 2026

**État antérieur à l’accord 9db279f5, désormais consommé.** Le résultat réel et ses réserves sont décrits en tête de ce document.

Le paquet `.ui-preview/pilots/physical-capture-cr-20261015/PROTOCOL.md`
prépare le chemin de capture Windows habituel vers un brouillon de CR privé.
Il ne remplace pas le moteur par le précédent harnais audio en mémoire.
Onze tests simulés des garde-fous et Ruff passent. Le précontrôle réel des API
crée deux bases isolées, lit l'inventaire Realtek et s'arrête avant toute
ouverture audio ou tout modèle ; les deux contrôles SQLite sont `ok`.
Ce résultat ne qualifie pas la capture physique. Un nouvel accord couvrant
microphone, son système, lecture audible fictive, transcription CPU et envoi
du seul texte au LLM réseau reste requis. Aucun essai matériel de ce paquet
n'est lancé et L12 reste ouvert. Voir [le protocole](.ui-preview/pilots/physical-capture-cr-20261015/PROTOCOL.md).

## Parcours visible vers le CR — 15 octobre 2026

Un bouton **Compte rendu** est maintenant visible dans les outils de la séance,
hors de Préparation. Pour une séance audio liée, le panneau ouvre directement
la transcription si elle manque ou doit être relue, puis le CR si la relecture
est déjà validée. Après **Valider la transcription**, le panneau passe au CR ;
**Préparer le compte rendu** et sa publication restent deux actions explicites.
Aucune capture ou génération n'est lancée par cette navigation.

Les résultats tardifs sont liés au projet et à l'audio sélectionné : ils ne
peuvent pas remplacer une autre séance, même après un aller-retour vers la
première. Les brouillons et la note restent conservés entre les panneaux.

137 tests ciblés dans six fichiers passent. TypeScript et le build passent
après correction d'une option de test incompatible avec ses types. Le build
isolé est publié sur Agent 8001, sans redémarrage, après sauvegarde des sources
et de l'ancien dist. Les anciens assets restent disponibles. Les assets servis
correspondent aux empreintes du build ; le HTML est comparé en texte, car le
serveur normalise ses fins de ligne. L'avertissement Vite sur la taille du JS
reste présent ; aucune nouvelle régression globale complète n'est revendiquée.

Le bouton a été cliqué dans le navigateur réel sur la séance existante
« test 1 » et ouvre le panneau attendu. Cette séance de notes n'est pas terminée :
sa publication reste correctement désactivée. Aucun contenu n'a été modifié,
aucun microphone ni modèle n'a été ouvert, aucun CR n'a été publié par ce clic.
L'ouverture automatique des étapes audio est vérifiée par les tests React ;
ce contrôle navigateur ne remplace pas une capture physique de réunion.
**L12 reste ouvert.**

[Preuve de publication](logs/foresight-runtime/CR-workflow-UI-publication-ROOT-a83e079761f04e4789d024ad035e2672.json), [capture du bouton et du panneau](logs/foresight-runtime/CR-workflow-access-20261015.jpg), [audit de livraison](logs/foresight-runtime/CR-workflow-UI-delivery-ROOT-20261015.json).

## Réunions : raccord GPU vérifié et secours structuré corrigé — 15 octobre 2026

Le parcours réel sur fichier audio a réussi avec Whisper medium CUDA dans
les deux workers canoniques, successivement, puis avec le CR réseau et sa
publication privée sans doublon. L'essai autorisé termine en 34,41 s au
contrôleur, processus fermés ; le GPU reste désactivé en production. Les six
attentes numériques/unités sont retrouvées dans ce seul échantillon de trois
phrases. Aucune capture physique, cadence à deux pistes, latence visible,
endurance ou précision générale n'est déduite de ce résultat : L03/L12 restent
ouverts. Les données fictives restent hors des bases actives.

La bascule des améliorations manuelles structurées est également corrigée et
activée : une panne de transport après connexion peut utiliser le secours
configuré en conservant le schéma et les sources, sans transmettre la clé
réseau. Les demandes automatiques continuent d'interdire ce chargement.
146 tests ciblés passent ; leurs transports sont simulés. Ce correctif ne
prouve pas une nouvelle génération réelle avec le modèle de secours local.

[Audit et limites](logs/foresight-runtime/GPU-product-and-fallback-delivery-ROOT-e0176bcfd58e41e7b6c9d02eb527f9b3.json).

## CR audio importé : parcours réel vérifié et correctif activé — 15 octobre 2026

Le parcours canonique import → transcription → relecture de qualification →
génération du CR → publication projet → rejeu sans doublon termine avec succès
sur trois fichiers vocaux fictifs réunis en 20,25 secondes d'audio. Whisper
small et la diarisation Sherpa fonctionnent réellement sur CPU ; Gemma réseau
produit réellement la synthèse. Deux bases privées passent quick_check ;
aucune séance fictive n'a été créée dans les données actives. Cette validation
utilise les API originales, sans simuler l'ASR ou le LLM ; elle ne valide pas
une capture physique ni les clics du navigateur. La mémoire de cette fixture
est factice : aucune qualification EG2 supplémentaire n'en est déduite.

Le passage après correction des consignes dure 12,08 s dans la fixture,
dont 7,94 s jusqu'à la transcription ; le contrôleur termine en 14,31 s,
Job vide et handles fermés. Ce court échantillon ne prouve ni P95 ni endurance.
La synthèse conserve 230 V, 16 A, 1250 W, 350 lux, ±0,2 mm et 1,5 m ;
les informations techniques ne sont plus classées comme points ouverts dans
ce résultat. Les erreurs de transcription « Ampires » et « luxe » sont
conservées dans la preuve : la relecture reste nécessaire et aucune précision
industrielle générale n'est revendiquée. Onze tests existants de synthèse et
publication passent après cette correction, ainsi que Ruff ; ils recouvrent
les tests précédents et ne s'ajoutent pas aux 155 cas déjà consignés.

Le backend Agent 8001 a été redémarré sous son superviseur existant, après
sauvegarde cohérente séparée des bases Brain, ERP et EG2, contrôle d'intégrité
et restauration dans trois fichiers privés. Aucune restauration sur le canon.
Les six tables Brain et dix-sept tables ERP nommées par le contrôle métier
sont inchangées. La première comparaison observe aussi une variation du
suivi d'analyse projet ; les lectures suivantes l'identifient comme des
horodatages de reprise/retry, sans changement du rapport métier. Les résultats
complets de comparaison restent conservés. Les scans jalons conservent leur
mécanisme de reprise ; aucun nouveau serveur, aucune activation CUDA, aucun
chargement manuel d'un LLM local. XPilot 8000 reste intact.

Le réseau LLM est intermittent : refus de connexion, succès pendant les
générations, puis nouveau refus au contrôle suivant. Les trois modèles locaux
déclarent zéro instance au dernier contrôle ; le secours automatique reste
configuré mais n'est pas qualifié par cet essai réseau. La disponibilité
continue, la capture réelle, le direct, la précision industrielle et les
séances longues restent à qualifier. **L03 et L12 restent ouverts.**

Le premier essai s'arrête sur un 422 dû aux métriques envoyées par le script
de recette ; le client produit les filtre déjà. Le deuxième vérifie la
publication mais montre le défaut de classement des faits ; le troisième
vérifie la consigne corrigée. Ces trois preuves restent distinctes.

[Résultat réel](logs/foresight-runtime/CR-defaultCPU-3972da4f7a1e4b2ab4d56e85f379616f/result.json), [CR obtenu](logs/foresight-runtime/CR-defaultCPU-3972da4f7a1e4b2ab4d56e85f379616f/draft-CR.md), [activation et sauvegardes](.ui-preview/backups/CR-activation-70055a8723a84b6caf707e15ba192084/ROOT-activation.json), [audit de livraison](logs/foresight-runtime/CR-product-delivery-ROOT-42fb44d5c4474ac58d5945541ddb6ada.json).

## Raccord audio dans le produit — 15 octobre 2026

Le code canonique d'Agent prend maintenant en charge un profil CUDA optionnel
commun au direct et à la transcription d'un enregistrement complet. Il vérifie
le profil demandé, les versions et les propriétés natives du modèle avant
d'accepter son chargement. Le chemin des DLL est transmis au seul processus
audio ; les lecteurs et les handles sont fermés à la fin du traitement.
Le mode CPU reste la configuration par défaut, la diarisation reste sur CPU
et les lots groupés restent réservés au CPU (unités individuelles sous CUDA).

**155 tests ciblés et deux sous-tests passent**, ainsi que Ruff. Ils couvrent
les deux entrées audio, les séances, le CR, l'arbitrage CPU et la fermeture.
Les modèles et transports de ces tests sont simulés. La grande suite Python
historique ci-dessous n'a pas été relancée sur ces modifications. Les deux
premiers lancements ciblés interrompus par les droits des dossiers temporaires
restent exclus des résultats favorables.

Au point de contrôle de ces tests ciblés, aucun modèle ni microphone
n'avait été ouvert. Le parcours réel restait alors à vérifier ; la recette
CPU et réseau rapportée ci-dessus complète cette preuve pour l'audio importé.
À cet instantané, le profil CUDA restait désactivé et le raccord produit non qualifié ; la recette ultérieure est décrite en tête. L03 et L12 restent
ouverts. Les preuves privées antérieures décrites ci-dessous restent celles
de leurs instantanés ; leur raccord préparatoire est désormais intégré au code,
sans nouvelle qualification matérielle.

### Paramétrage du profil CUDA optionnel

Dans l'environnement du processus Agent, utiliser `PB_SPEECH_DEVICE=cuda`,
`PB_SPEECH_MODELS_DIR=C:\Agent\.models\audio-medium`, `PB_SPEECH_THREADS=4`
et `PB_SPEECH_CUDA_DLL_DIRS`, une liste JSON de chemins absolus existants
vers les dossiers cuBLAS 12 et cuDNN 9. Ce paramétrage n'a pas été appliqué.
Les versions attendues sont faster-whisper 1.2.1 et CTranslate2 4.8.2 ;
Whisper medium est chargé localement sur CUDA 0 en int8_float16, un worker.
Le direct conserve beam 1 ; l'enregistrement complet conserve beam 5.
Un profil invalide ou un modèle chargé différent provoque un refus explicite,
sans repli CPU silencieux. Les identités de fichiers du profil ne remplacent
pas la preuve des DLL effectivement chargées lors d'une recette matérielle.
Le mode local du modèle ne constitue pas une preuve d'isolation réseau OS.

Le module partagé est `scripts/speech_runtime.py`, utilisé par
`app/services/live_speech.py`, `app/services/meeting_audio.py` et les deux
workers `scripts/transcribe_live.py` et `scripts/transcribe_meeting.py`.
Agent reste le seul serveur du projet sur 8001 ; aucun service supplémentaire.

## Régressions consignées — 15 octobre 2026

La suite Python générale termine avec **2 539 réussites, 1 ignoré, 54 sous-tests
réussis et deux avertissements**, sortie0 en53min25s. Le cas ignoré concerne le
dossier Infomaniak-IA absent. Des modifications sont intervenues pendant cette
suite : **143 tests ciblés supplémentaires passent après import frais** des
zones concernées, sur244 sources backend sans dérive. Les décomptes se
recouvrent et ne sont pas additionnés ; aucun instantané atomique du code
durant toute la grande suite n’est revendiqué.

La suite frontend au point de contrôle consigné passe **928 tests dans89 fichiers**, sans ignoré ni
dérive des238 sources épinglées. Le premier passage925/3 reste conservé ; ses
trois échecs provenaient uniquement de l’ancien libellé de bouton attendu par
un test d’intégration PDF/tableur/audio. Ces trois cas passent après mise à jour
de ce seul libellé, sans changement du parcours produit. TypeScript/build et
Ruff passent. Les quatre fichiers compilés isolément sont byte-identiques aux
quatre fichiers canoniques servis ; aucun asset n’a été remplacé. Des sources de
messagerie et le build ont ensuite évolué : le gel R8R2 les a recopiés et
identifiés. Les résultats de régression ci-dessus restent ceux de leurs
instantanés ; ils ne prouvent pas un nouveau passage global sur ce build.

Le serveur actif est sain, sous le profil utilisateur attendu, et son démarrage
est postérieur aux dernières sources pertinentes. Aucun redémarrage ajouté.
Le catalogue LLM réseau est joignable ; les trois modèles locaux déclarent zéro
instance chargée. Aucun modèle ni microphone ouvert par ces vérifications.
La branche groupée L03 reste désactivée (clé absente). La recette assistant
R8R2–R8R4 conserve trois passages arrêtés avant toute génération ;
le nouvel essai GPU V3 autorisé est **réussi dans sa portée diagnostique** :
16fragments des deux pistes,8arrivées à5s, sortie0 en51,75s. Les six paires
complètes à chaud demandent1,51 à1,79s ; aucun travail précédent ne reste en
attente à l’arrivée suivante sur cette courte cohorte. Le maximum GPU total
échantillonné est1,33Gio, sans garantie de réservation. Les sources, poids et
originaux sont inchangés. Le driver sort0 et le Job externe est déjà vide
avant cleanup ; le résident sort1 lors de sa fermeture contrôlée originale,
ce qui n’est pas une fin gracieuse exit0 de tous les processus.
L’accord unique est consommé. Aucun microphone, publication SQL/UI ou changement
de production. Des unités erronées restent présentes («380mAh», «16Mp») :
aucune précision industrielle, capacité soutenue, latence visible/P95 ou
endurance n’est qualifiée. Le refus cuBLAS précédent13,57s reste conservé.
Le raccord privé du profil GPU au code actuel est rebasé sur13sources
canoniques, avec quatre blocs protégés byte-identiques et la branche groupée
L03 conservée. Ses12unités fictives et sa revue source distincte passent.
Le helper GPU observe les propriétés natives avant loaded ; cette observation
reste à réaliser dans la future fixture complète. Le batch conserve son garde
CPU et refuse CUDA avant décodage.

La fixture de séance est désormais vérifiée avec le vrai stockage SQL privé :
trois cas terminent avec sortie 0, six bases passent leur contrôle d’intégrité.
Le cas nominal conserve quatre fragments et quatre segments provisoires,
sans doublon au rejeu ; les deux profils incorrects sont refusés avant toute
requête ASR. Notes et originaux restent conservés. **Le transport ASR et les
propriétés natives du modèle sont simulés dans ces trois cas.** La revue source
distincte confirme les résultats retenus et les 292 sources canoniques copiées.
Le premier essai de fixture, arrêté sur une erreur de lecture d’acquittement,
reste conservé et exclu de la preuve favorable. Aucun nouveau modèle lancé
ni changement des données actives. **À cet instantané privé, le raccord au GPU réel et au Studio
restait à assembler puis à qualifier** ; cette fixture ne clôture pas L03 ou L12.

Le raccord SQL est maintenant éprouvé sur une cohorte complète : seize
fragments reçus, acquittés, traités par les fonctions originales, puis relus
après commit, avec seize segments provisoires et aucun nouvel appel au rejeu.
Le second cas conserve les deux acquittements malgré une panne ASR simulée
au deuxième appel ; un seul fragment est terminé, l’autre reste en échec.
Le troisième cas ne reçoit aucun ready : le timeout et la deadline originaux
de start sont bornés au budget restant avant tout producteur, fragment ou
requête ASR. Le budget transmis est inférieur à 250 ms ; ce n’est pas une
borne OS sur toute la durée du contrôle, qui comprend aussi la fermeture.
Les trois cas V2 terminent sortie 0 ; six bases privées, dix-huit acquittements
et quarante-huit WAV à motif sont vérifiés après fermeture. Notes, versions et
originaux restent conservés ; les lecteurs et producteurs sont joints.
**Les réponses ASR et propriétés natives sont simulées.** Ces contrôles ne
valident ni la précision, ni le GPU réel, ni l’affichage ou l’endurance. Le
contrôleur matériel externe reste à assembler ; aucune activation dans Agent.
[Audit SQL de la cohorte V2](logs/foresight-runtime/integrated-SQL-cohort-V2-ROOT-541ab17b1dcb4f42aac7e8c563946ae8/ROOT-post-terminal-audit.json), [revue distincte](logs/foresight-runtime/integrated-SQL-cohort-V2-independent-source-review-20261015-cfa76327.json).

[Contrôle SQL réel, ASR simulé et limites](logs/foresight-runtime/integrated-GPU-session-SQL-smoke-ROOT-b15766a857b04160b88956e33beb34c2/ROOT-post-terminal-audit.json).

[Raccord privé vérifié et limites](logs/foresight-runtime/integrated-GPU-current-profile-V2-ready-ROOT-20261015.json).
[Résultat GPU réel et limites](logs/foresight-runtime/direct-two-track-medium-gpu-61cd940dca4947b9bd2ec92975cb0757/ROOT-terminal.json). Audio intégré, qualité/latence,
endurance visible et saturation physique restent à qualifier : **L12 reste ouvert**.

**Interruption de processus : sept frontières réelles vérifiées.** Chaque cas
emploie deux fragments PCM fictifs complets de5s et les vraies fonctions
canoniques de journal, stockage SQL et reprise. Le contrôleur arrête son propre
processus après intention/WAV/manifeste/commit SQL/reçu, avec deux fichiers
partiellement écrits réellement conservés. Une autre instance effectue deux
rejeux : deux fragments, commandes et événements uniques ; note et originaux
inchangés, reçus conformes au SQL. Les14 bases privées passent quick_check et
les14 enfants ont leurs handles fermés. Durée21,05s, sorties19,77Mo, aucun
appareil, modèle, réseau ou donnée active impliqué. La première recette20ms
est conservée séparément. Cela ne qualifie pas un disque physiquement plein,
une coupure électrique ou une capture matérielle : **T16 complet reste ouvert**. Le compte courant ne possède pas le privilège Windows requis pour monter un volume virtuel isolé. Aucun disque créé, monté, formaté ou saturé. [Précondition vérifiée](logs/foresight-runtime/T16-isolated-volume-current-prerequisite-ROOT-20261015.json).
[Preuves des arrêts et reprises](logs/foresight-runtime/T16-process-crash-ROOT-25a790a9208a49698047505bd568ea8a/ROOT-post-terminal-review.json).
[Résultats, empreintes et limites](logs/foresight-runtime/Current-regressions-completed-ROOT-ae3a993a9e074ef3a4fac48e08dcec20.json).



**Assistant : correction privée vérifiée, recette visuelle non qualifiée.**
R8R2 termine sortie 1 en 2,58 s : son garde refusait l’import des seules
définitions de live_speech, nécessaires au statut batch des séances. La copie
R8R3 autorise cet import, en conservant les interdictions de modèles, appareils,
sous-processus et workers audio. Un vrai contrôle SQL privé vérifie séance,
note conservée et statut batch original idle ; huit imports matériels restent
refusés, deux bases passent quick_check. Aucun modèle ni appareil ouvert.
R8R3 atteint son serveur privé puis expire à la préparation après 60,79 s,
le point CUA ayant réellement trouvé l’onglet sélectionné mais masqué.
R8R4 demande explicitement son affichage après ouverture ; le premier point
échoue encore, puis le contrôle suivant voit bien l’onglet visible. ROOT ferme
alors ce passage, sortie 1 en 51,60 s. La visibilité est donc intermittente,
pas déclarée définitivement indisponible. Les trois processus sont terminés,
leurs Jobs vides et handles fermés ; les deux serveurs ont fermé listener et
connexions SQL, leurs quatre self-pipes chacun ont fermé naturellement.
Aucune question, génération, requête d’embedding ou boucle proactive n’a été
lancée ; les trois résultats utiles et leur affichage restent à qualifier.
Les trois gels et revues sont conservés sans transformer ces arrêts en réussite.
Le contrôle final observe une instance locale chargée, puis un délai dépassé
sur le catalogue LLM réseau et le statut IA d’Agent (quatre secondes chacun).
Ces observations ponctuelles ne prouvent pas une indisponibilité permanente.
Le secours local reste sous la politique de déchargement au retour du réseau ;
ROOT ne force aucun déchargement pendant ce constat. [Observation finale](logs/foresight-runtime/ROOT-final-network-observation-e849e9a6938f470eb64abac506f8f10e.json).

[Traces des passages et limites](logs/foresight-runtime/Assistant-current-attempts-ROOT-3e23fb04a6c34093891d097b034126f2.json).

## Recettes privées : revues indépendantes terminées — 15 octobre 2026

La recette assistant R8 et le diagnostic GPU V2R1 ont une revue source distincte
favorable. R8 passe huit unités sur SQLite fictive avec réponses HTTPX simulées ;
le diagnostic GPU passe ses 72 contrôles fictifs. Ces résultats ne qualifient
aucun nouvel essai réel, aucune capture ni le P95. Aucun modèle ni microphone
n’a été ouvert pendant ces vérifications. Un nouvel accord GPU est demandé :
l’autorisation précédente était unique et a été consommée.

R8 prépare une vraie projection EG2 privée avant toute question, avec deux
appels embeddings originaux ; le futur essai reste à faire. Neuf descripteurs
historiques GPU (huit chemins) manquent sur disque : ils sont conservés comme
provenance indisponible, sans prétendre en revérifier les anciens succès.
Les dépendances exécutées et gardes actuels restent exigés avant lancement.

Le Studio contient bien « Démarrer la réunion » et « Périphériques ». Le document
est visible, mais le navigateur reste signalé masqué : aucune mesure de carte
visible n’est validée. Ruff passe sur app, backend/app et tests. La suite générale
L03 n’a pas encore de terminal observé au point 2026-10-15T09:52:12.079941+00:00 ; des sources ont changé
pendant son exécution, ce qui impose de vérifier les sources finales et les
tests concernés. L03, L09 et L12 restent ouverts.
[Preuve et limites](logs/foresight-runtime/Qualification-source-reviews-ROOT-dbee566e51ee41ca87630fe1464507c4.json).


## État courant : activation vérifiée, recette réelle encore ouverte — 15 octobre 2026

Le backend a été redémarré une fois sous le profil utilisateur correct, puis
sa santé et le contrat Toutes / Textes / Images / Audio ont été vérifiés.
Le journal audio R4 est actif côté serveur ; cela ne prouve pas encore une
capture physique ni une transcription opérationnelle. La nouvelle interface
est publiée : ses trois fichiers statiques sont identiques aux fichiers
compilés ; le HTML correspond après la normalisation CRLF/LF existante du serveur.
Le Studio observé présente Démarrer la réunion et les sélecteurs Périphériques.
Aucun enregistrement démarré pendant cette vérification.

**Suite backend complète : 2 475 réussis, 1 ignoré, 15 sous-tests et deux
avertissements, en 50 min 52 s, sortie 0.** Le test ignoré concerne le dossier
Infomaniak-IA absent. Les 54 tests audio, Ruff et les 924 assertions frontend
déjà acquis sont distincts ; leurs décomptes ne sont pas additionnés.

Les comparaisons réelles avant/après redémarrage conservent toutes les cellules
Brain, les autres cellules ERP, les schémas, EG2 et 1 007 originaux métier.
Quatre lignes de suivi des workers présentent des changements précisément
consignés (dates, reprise de statut et remise à zéro de diagnostics de scan) ;
le journal diagnostic progresse séparément. Aucun état global inactif ni
snapshot atomique entre bases n’est revendiqué.

**Recherche multimodale sur nouveau corpus : essai CPU privé réussi.**
Quatre recherches d’images et quatre recherches de texte PDF retrouvent
la citation exacte au rang 1 ; six contrôles d’exclusion passent.
Réouverture de l’index et rejeu sans doublons vérifiés ; encodeur et
pilote terminent naturellement, Job vide et handles fermés. Durée totale
19,76 s, publications comprises. Les huit contrats purs passent aussi.
Cette preuve porte sur des rendus PNG/PDF fictifs, sans recherche audio
ni support CAD natif ni mesure d’affichage. Aucun index actif remplacé.
Le premier refus sur la limite de 64 Mio reste conservé ; la variante
corrigée surveille 512 Mio et exige 1 Gio supplémentaire libre.
[Preuves du corpus et limites](logs/foresight-runtime/L09-heldout-actual-progress-ROOT-20261015-ae41367f0673479498a5529184fc8dea.json).

**Vérification canonique L03 : 64 cas et 39 sous-tests réussis.**
Ruff passe sur le backend, les tests et les nouveaux scripts.
La suite complète du projet est en cours sur bases fictives.
Les cinq retours de recherche audio privée sont corrects : deux
citations au rang 1, trois exclusions vides, réouverture et réimport
sans doublon. Les quatre conversions FFmpeg et le modèle CPU ont
effectivement travaillé ; le Job était naturellement vide.
Le terminal global du lanceur n’est pas observable après interruption :
ces preuves de composant ne clôturent ni L09 ni L12.
[Vérifications, portée et limites](logs/foresight-runtime/L03-canonical-checks-ROOT-f95de1e1288d49bca3e49056250aac5f.json).

**Transcription groupée : code et tests intégrés, voie désactivée.**
La consolidation des fragments PCM contigus à la finalisation par lot
conserve les corrections, les citations et la transaction existante.
Huit fichiers produit et neuf fichiers de tests/fixtures sont livrés.
La copie produit passe 183 cas ciblés et 54 sous-tests. La suite complète
doit encore vérifier cette nouvelle livraison. Le réglage groupé reste
absent ou strictement False ; aucune activation ni migration de données.
**Recettes réelles encore ouvertes.** Medium a chargé en CUDA, puis
échoué au premier fragment ; son autorisation unique est consommée.
La recherche audio a été refusée avant FFmpeg/encodeur par le harnais.
Les derniers échecs de harnais restent conservés ; aucune réussite
audio, GPU, latence ou endurance n’est déduite des tests unitaires.
L’assistant a produit une réponse manuelle citée et un ajout automatique
visible ; sa réponse proactive reste sans preuve et la cohorte est refusée.
[Publication, sauvegardes et portée](logs/foresight-runtime/L03-canonical-publication-ROOT-2e88d524ad9b4f08a838c6e4ec9d6ecf.json).

**Restent à qualifier : capture réelle, ASR industriel, double piste GPU et
délais visibles, assistant utile sous charge, recherche multimodale élargie
(audio et intégration active), incidents physiques/reconnexion LLM et chaîne
intégrée ≥60 min.**
L09, T16 physique et L12 restent ouverts. Adaptation visuelle validée et
exclusion de Drive maintenues. Aucun commit ni push. Les sections précédentes
ci-dessous restent l’historique de leurs essais, et non l’état courant.
[Résultats, sauvegardes et portée](logs/foresight-runtime/Active-delivery-progress-ROOT-20261015-b5a4cb53e57c45e7960142a027cd6ecb.json).


## Sauvegarde réelle et journal audio R4 publié — 15 octobre 2026

La sauvegarde en ligne V4R1 est terminée et vérifiée : Brain, ERP et EG2,
trois restaurations sur copie et 1 008 fichiers gérés (939 008 115 octets).
Les bases sources restent inchangées ; leurs snapshots ne sont pas atomiques
entre bases. Le seul journal diagnostic agent.log est conservé au point de
coupe de 1 419 330 octets ; 260 octets ajoutés sont observés séparément.
Ses anciens refus et les 36 tests privés réussis restent conservés.

Six fichiers audio R4 sont publiés dans le canon avec quatre préimages et
deux absences déclarées avant mutation. Les 54 régressions canoniques passent,
avec 15 sous-tests distincts du décompte ; Ruff global et scripts audio passe.
La première collecte a échoué dans le harnais Popen, avant exécution des
tests ; son résultat est conservé. Le comparateur SQLite passe neuf essais
fictifs ; aucune conservation après redémarrage n’est encore déclarée.

**Rechargement backend, nouveau frontend et suite Python globale finale
encore en attente.** La suite globale est en cours ; son ancienne réussite
n’est pas présentée comme le résultat de cette version. Capture matérielle,
ASR industriel, débit/P95, L09, T16 physique et L12 restent ouverts.
Adaptation visuelle validée et Drive exclu conservés.
[Preuves et portée](logs/foresight-runtime/Backup-audio-actual-progress-ROOT-20261015-24b4f526b6544936954f7b079f42152d.json).


## Journal audio et sauvegarde : vérifications privées réussies — 15 octobre 2026

Le candidat audio R4 passe deux cohortes distinctes : 20 cas SQL/producteur
simulé et 17 cas de fichiers, puis 37 cas de compatibilité adaptés.
Les anciens résultats R3 (26 réussites, 11 échecs) restent conservés.
Les 21 essais de sauvegarde V2 passent sur bases et originaux fictifs ;
aucune sauvegarde métier réelle réalisée par cette recette.
L’interface conserve ses 924 assertions réussies dans 88 fichiers.

**Prochaines étapes : sauvegarde réelle, activation contrôlée, puis qualification
matérielle et intégrée.** Aucun nouveau code audio promu, rechargement
backend ou nouveau frontend servi ici. Capture, ASR industriel, débit GPU,
P95, L09, T16 physique et endurance L12 restent ouverts ; Drive est exclu.
[Preuves et portée](logs/foresight-runtime/R4-backup-private-progress-ROOT-20261015-a982f5ad38a34a7485f3c5dfa7825ef6.json).


## Recettes privées audio et interface ; régressions avant activation — 15 octobre 2026

Le journal audio R3 réussit 20 cas SQL/producteur simulé et 16 cas de fichiers,
avec 15 sous-tests signalés séparément. Quota, écritures partielles de reçu,
rejeu et retrait des droits sont vérifiés sur copies. Les 37 tests natifs
existants révèlent encore 11 échecs pour 26 réussites : fixtures sans séance
SQL et temporaires longs. Aucun correctif audio canonique promu à ce stade.

Les 924 assertions de l’interface passent dans 88 fichiers, avec 921 libellés
uniques (quatre paragraphes distincts partagent un libellé paramétré).
Le build Vite est produit dans un dossier privé ; API à recharger avant
publication. Les 68 contrats GPU/TokenUser passent avec des fakes uniquement.
La préparation de sauvegarde V1 est refusée ; V2 est préparée sans sauvegarde
métier exécutée. La suite Python globale précédente reste historique.
**Activation, audio matériel, ASR/P95, L09, T16 physique et L12 restent ouverts.**
Drive reste exclu. [Preuves et portée](logs/foresight-runtime/Private-audio-frontend-progress-ROOT-20261015-ce5f2ca208c345819bbbedebb96a550d.json).


## Recherche par modalité intégrée dans les sources ; activation en attente — 15 octobre 2026

Les quatre sources du filtre Toutes les preuves / Images / Textes / Audio sont
intégrées et sauvegardées. Le choix explicite filtre le projet autorisé avant
classement, avec citations et exclusion des réponses devenues obsolètes.
19 cas backend privés et 15 cas React/jsdom passent ; après intégration,
46 tests canoniques ciblés, Ruff global et TypeScript passent.
**API à recharger avant publication du nouveau frontend ; aucun nouveau dist servi.**

Le journal audio V1R1 passe 16 méthodes sur fichiers fictifs, avec pannes
simulées et callbacks d'autorité/acquittement simulés. Son intégration SQL reste
à vérifier, notamment les écritures du reçu après commit ; il n'est pas activé.
Cela ne qualifie ni panne physique, capture matérielle, pertinence multimodale
ni délai visible. L'ancien essai CAO toutes modalités garde ses deux échecs.
La suite globale 2458 réussis + 1 ignoré est antérieure à cette intégration ;
aucune nouvelle suite globale exécutée, aucun ajout de ces décomptes.
L09, T16, P95 et L12 restent ouverts. Drive reste exclu.
[Preuves et portée](logs/foresight-runtime/Modality-journal-progress-ROOT-20261015-43d7dc32e96c4423a1136cdf761c151a.json).


## Dessins CAO : PNG et texte PDF traités sur CPU, qualité visuelle encore refusée — 15 octobre 2026

L’essai privé V1R2 a réellement utilisé LiteRT-LM 0.18.0 et EG2 complet sur CPU4/768 pour huit vecteurs de rendus PNG et de texte PDF issus de dessins CAO ; les huit originaux DXF/SVG sont conservés et leur extraction reste non prise en charge. La recette toutes modalités reste refusée : deux citations texte sur deux passent au rang1, mais les deux recherches visuelles renvoient un PDF en premier et échouent au critère image. Les deux contrôles négatifs sont vides, sans fuite de projet/version ; les 16 sources et 16 versions sont conservées au rejeu. Aucune lecture CAO native, activation canonique, P95 ou clôture L09/L12 n’est qualifiée.

La recette a terminé en sortie1 après15,544158 s ; encodeur arrêté naturellement avec exit0/EOF, engine et alias fermés/restaurés, fermeture propriétaire confirmée, mais preuve de Job naturel avant cleanup non qualifiée. Les tests globaux déjà exécutés restent2458 réussis et1 ignoré, sans nouveau pytest ni ajout des37 ciblés ; NativeReceipt sur8001 reste à recharger, GPU10 reste une QA pure et permission NVIDIA en attente.

[Résultat réel et limites](logs/foresight-runtime/CAD-V1R2-progress-ROOT-20261015-b53d0468cd4c4816a558029f07261d94.json).


## Reçus audio corrigés dans les sources ; rechargement en attente — 15 octobre 2026

Le rejeu audio confirme désormais chaque fragment en SQL et répare atomiquement le reçu local, en conservant ses anciens octets ; ses 37 tests ciblés passent séparément du décompte global. Le rechargement d’Agent 8001 reste en attente : l’inactivité des jalons et des travaux documentaires et l’identité du module chargé ne sont pas établies. L’essai CPU CAO V1R1 a été refusé avant admission du moteur, avec 16 sources privées conservées et huit entrées échouées ; une copie V1R2 est en préparation privée, sans nouvelle recette exécutée. La QA du profil GPU privé passe dix contrats purs, sans mesure GPU, capacité, SQL ou appareil ; les droits NVIDIA, la recette couplée et L03/T16 matériel/P95/T12/L12 restent ouverts.

Suite backend globale : 2459 cas uniques, 2458 passés, 0 échecs, 0 erreurs et 1 ignorés ; sortie 0.

[Preuves et limites](logs/foresight-runtime/Native-receipt-progress-ROOT-20261015-b4e62dea8c7f4273810916e806a195a7.json) · [Suivi détaillé](docs/38_FORESIGHT_DELIVERY.md).


## Stop natif : arrêt et historique vérifiés — 14 octobre 2026

Une génération réelle sur le LLM réseau, avec données fictives et bases privées, a été arrêtée par le vrai bouton Stop après le premier texte. **Recette complète : 56,05968 s, sortie 0.** Texte partiel et citation conservés, enregistrés puis rechargés depuis l’historique réel ; aucun message technique trompeur, Réessayer ou erreur d’enregistrement dans ce périmètre Assistant. Notes, versions et sources protégées intactes ; ressources privées et Job fermés.

**L’ancien indicateur `native_Stop_UI_qualified_only` reste false.** Son intervalle de 24,8 ms chevauchait les effets locaux. **Le nouvel indicateur `native_Stop_UI_conservation_causal_addendum_v1` est true**, selon une nouvelle méthode évaluée uniquement sur les fichiers historiques : réception serveur du même clic réel, même UID/document/séquence, intersection de bornes sans modifier la borne inférieure ni les ordres stricts. Aucun nouvel essai et aucune réécriture des anciens résultats.

Conservation des 1 438 caractères appliqués à l’interface, avec citation ; deux caractères consommés côté serveur n’étaient pas appliqués. **Arrêt du calcul distant inconnu**, identité interne de l’erreur native non mesurée. Le correctif activé et les **924/924 tests frontend** restent documentés ; Ruff passe sur `app backend/app tests`, sans nouvelle suite pytest globale.

**Assistant global, L03 global, P95, T12 et L12 restent non qualifiés.** Droits précis NVIDIA en attente d’accord humain après refus automatique avant lancement ; aucun droit changé ni nouvel essai GPU autorisé ou exécuté dans cette progression. Les paragraphes datés suivants restent l’historique des états antérieurs.

- **Capture physique intégrée :** Aucun microphone ouvert par cette recette ; qualification matérielle intégrée ouverte.
- **Qualité transcription et voix :** Précision industrielle, voix et contexte restent à vérifier.
- **Débit deux pistes :** Medium CPU4 échoue à la cadence de 5 s ; candidat GPU préparé, essai réel encore requis.
- **Premier texte réellement visible/P95 :** Les 56,05968 s de recette ne sont pas une mesure de P95.
- **Assistant utile, priorité et annulation :** Stop local et historique vérifiés ici ; utilité représentative, cartes, tick et priorité sous charge intégrée ouverts.
- **Panne stockage pendant capture :** Les contre-épreuves SQL privées de consolidation ne qualifient pas une panne pendant capture.
- **Endurance intégrée :** Une génération courte ne remplace pas la recette complète d’endurance.
- **Audit final et activation qualifiée :** Assistant global, T12 et L12 ouverts ; adaptation visuelle acceptée et Drive exclu conservés.

[Preuves et limites](logs/foresight-runtime/Native-Stop-addendum-status-ROOT-20261014-1f1ee78928c44947b5d0c727ca65818c.json).


## Historique — correctif Stop activé et préparation GPU, état avant la recette native du 14 octobre 2026

Le correctif du bouton Stop est activé dans l’interface du serveur unique Agent, sur 8001. Les simulations vérifient la conservation du texte partiel et des citations et le maintien des vraies erreurs réseau. **924/924 tests frontend passent**, dont 16 cas AssistantPanel ; TypeScript et compilation séparée réussissent. Les anciens assets sont conservés et l’index sauvegardé permet le retour arrière. **Le comportement natif de Stop reste à qualifier dans le navigateur ; Assistant, P95, T12 et L12 restent ouverts.**

[Preuves et limites](logs/foresight-runtime/Assistant-Stop-UI-and-GPU-pure-progress-ROOT-20261014.json).

La préparation GPU a passé 54 contrôles simulés de cadence, provenance, mesures partielles, consentement et limites. Aucun GPU, DLL NVIDIA ou microphone utilisé par ces tests. La revue des sources autorise uniquement cette QA ; les lectures normales des dépendances, les droits précis en attente et un nouvel accord pour l’essai GPU restent requis.


## Assistant réseau V5R4 — priorité et annulation observées, 14 octobre 2026

La recette fictive V5R4 a exécuté six requêtes sur le serveur réseau. Deux demandeurs ont réellement attendu : la question passe avant l’enrichissement. Le vrai bouton Stop interrompt le flux local, avec captures et horodatages cohérents. Les services proactif et automatique retournent une réponse. Notes, versions et sources protégées sont conservées ; ressources privées fermées, sortie 0. **Seule la fermeture de cette recette est qualifiée ; Assistant, P95, T12 et L12 restent ouverts.**

[Résultat et preuves](logs/foresight-runtime/G-ASSISTANT-V5R4-actual-objective-status-ROOT-20261014.json). 111 tests Python et 16 JavaScript réussis ; aucune nouvelle suite globale.


## Direct deux pistes CPU — débit insuffisant constaté, 14 octobre 2026

L’essai réel medium CPU4 a traité les 16 fragments fictifs des deux pistes. Une paire de fragments arrive toutes les 5 s, mais les paires complètes à chaud demandent 10,45 à 11,70 s : la file augmente. Ce profil échoue au débit de cette cohorte. La recette termine aussi en refus de contrôle, sortie 1. **Direct, précision industrielle, P95, T12 et L12 restent ouverts.**

[Résultat et preuves](logs/foresight-runtime/DIRECT-V2-actual-objective-status-ROOT-20261014.json). 28 tests purs réussis ; aucune nouvelle suite globale.


## Recette assistant V5R2 — résultat partiel, 14 octobre 2026

La recette courte V5R2 a réellement ouvert l’assistant sur une copie fictive et obtenu une réponse réseau sourcée conservant 1250 W, les réserves et les négations. La paire concurrente n’a pas démarré ; annulation et services de fond non exécutés. Le thread de fermeture a été refusé : sortie1, cleanup non qualifié. Les ressources privées sont fermées et les données protégées conservées. **G_ASSISTANT, P95, T12 et L12 restent ouverts.**

[Résultat ROOT](logs/foresight-runtime/G-ASSISTANT-V5R2-actual-objective-status-ROOT-20261014.json). QA de cette version :86 cas Python et8 cas JavaScript réussis ; aucune nouvelle suite globale.


## Avancement et portes restantes — 14 octobre 2026

**L12 reste ouvert.** Restent la capture physique intégrée, la qualité et les
voix de la transcription, le débit deux pistes, le premier texte visible,
l'assistant sous charge, les incidents du direct et de stockage pendant capture,
l'endurance complète, l'audit final et l'activation qualifiée. Les interfaces,
notes, sources, recherche et publication disposent de preuves dans leurs portées.
Les indicateurs CDC et généraux sont livrés. Drive reste exclu ; l'adaptation
visuelle est validée.

**Couplage nominal ASR/SQL V4 réussi sur fichiers fictifs et copies privées.**
La nouvelle inférence est enregistrée par les vrais services SessionBatch :
42 mots, cinq segments, trois fragments achevés, note conservée et rejeu sans
doublon. Les ressources sont fermées.
[Preuve nominale](logs/foresight-runtime/L03-coupled-V4-actual-objective-status-ROOT-20261014.json).

**Trois contre-épreuves V2 réellement réussies, chacune sur une nouvelle copie.**

- Correction : un segment produit par le premier groupe est corrigé par le
  handler public pendant la requête du deuxième groupe ; texte, locuteur et
  révision2 sont conservés. Six WAV entiers, dix segments, une note, rejeux sans
  nouveauté. La deuxième réponse est observée5,865s après la fin du handler.
- Annulation : une requête native réellement envoyée est annulée par le handler
  public ; aucune réponse native ni transcription publiée, trois WAV et la note
  conservés, terminal cancelled et rejeu sans doublon.
- Panne SQL : après une réponse native réelle, un trigger SQLite privé refuse
  la deuxième insertion. Une première ligne noncommise est réellement observée,
  puis le rollback original laisse zéro segment/proof/completed/updated durable.
  Le terminal failed est attendu ; originaux et note restent conservés.

Chaque plan a sa revue, ses127 cas purs ROOT (les mêmes cas, pas381 cas uniques),
son nonce/admission et son audit factuel. Les quatre sous-tests supplémentaires
de chaque exécution ne sont pas quatre nouveaux cas collectés. Les vrais
workers/processus/connexions/engines sont fermés et le Job est vide avant le
nettoyage propriétaire ; le node sort à1 par arrêt produit, distinct du driver0.
Les durées jusqu'à publication sont34,487s,17,426s et25,434s ; aucun P95 déduit.
[Résultats et audits des trois contre-épreuves](logs/foresight-runtime/L03-counter-V2-three-actual-objective-status-ROOT-20261014.json).

Ces gestes appellent les vrais handlers Python ; aucun geste UI/HTTP de réunion
ni micro n'est qualifié par eux. Le temps mesure le flux texte observé, jamais
le début du calcul acoustique. La correction ne couvre pas un ancien segment
humain dans le snapshot d'admission. La panne SQL ne qualifie pas la saturation
du disque pendant capture. Direct, multipiste, précision industrielle, affichage
P95, assistant et endurance restent ouverts ; L03/L12 ne sont pas clôturés.

V1 reste refusée en source et non exécutée. Le premier refus ROOT de préfixe
reste conservé, avant modèle/SQL/enfant ; le helper r1 utilise le chemin exact
du contrôleur. Deux délais GET jobs ont précédé des contrôles frais réussis,
sans redémarrage du backend ni relance d'une recette déjà commencée.
Les anciennes preuves ASR V6/SQL V9 et refus SQL V6/V7/V8 restent intactes.
La calibration navigateur antérieure garde zéro fragment livré/aucun P95.
G_ASSISTANT V4 est préparé, pas encore exécuté. Les trois contre-épreuves utilisent
le modèle ASR CPU existant ; aucun poids ni code/base/réglage canonique modifié,
aucun microphone ou GPU ouvert/utilisé. Aucune activation, aucun commit ou push
dans ce complément.


## Transport L03 réel : refus avant modèle — 14 octobre 2026

La préparation V2 passe **20 tests purs** et sa revue indépendante de code.
L'essai réel a ensuite terminé en refus, sortie CLI1, 2,365s avec publication :
le Python speech Windows utilise un processus intermédiaire, absent du contrat
de parenté du pilote. Le contrôle extérieur a aussi observé des descendants
supplémentaires dont l'image n'est pas encore établie. Aucun constructeur ASR
ni demande JSON de transcription n'a été exécuté. Le Job propriétaire est vide
et ses handles fermés ; les délégations sont restaurées. Le reçu consommé est
conservé, sans nouveau passage automatique ni contrôle post complet des poids.

La correction doit passer dans une nouvelle copie et prouver la chaîne réelle
Windows avant un nouvel essai borné. Le raccordement transactionnel reste
**non activé** ; qualité industrielle, débit multipiste, P95, T12 et L12 ouverts.

Le provider CUA direct est disponible : après création de l'onglet privé vide,
ses API ont réellement indiqué visible=true et cet onglet sélectionné. Cela
rétablit la possibilité de préparer la calibration, **sans mesure P95 ni
recette d'assistant effectuée**. Les limites Sky antérieures restent distinctes ;
ALL_TOOLS n'était pas un inventaire exhaustif des namespaces directs.

[Refus terminal ROOT](logs/foresight-runtime/l03-grouped-real-v2-refusal-root-20261014.json) ;
[préparation V2](.ui-preview/pilots/l03-grouped-real-pilot-v2-20261014-41c2c3a710a5/preparation-v2.json) ;
[point navigateur réel](logs/foresight-runtime/cua-direct-provider-point-root-20261014.json).


## Consolidation transactionnelle sur copie — 14 octobre 2026

Le raccordement batch L03 est implémenté dans une copie isolée, **non activée**.
Le plan et le profil/SHA du modèle sont figés dans le reçu durable existant ;
les mots natifs sont rattachés aux fragments et les corrections humaines
conservées. Chaque groupe est sauvegardé atomiquement. Une réponse native
incomplète, une frontière ambiguë, une annulation, des droits/réglages modifiés
ou une collision refusent son application ; les groupes déjà commités restent
acquis. Le traitement individuel est conservé, avec les gardes du profil figé
également appliquées aux plans mixtes.

**61 tests SQLite fictifs réussis** (23 nouveaux et 38 hérités), avec ASR simulé ;
38 tests unitaires simulés et Ruff sur les11 fichiers concernés passent.
Un test HTTP est explicitement non exécuté dans cette QA ; aucun nouveau
passage global Python n'est revendiqué. La revue indépendante confirme cette
portée. Les premiers refus du harnais sont conservés avec leurs reçus.

La copie exige un réglage groupé strictement opt-in, absent/faux par défaut ;
aucun réglage de production n'a été changé. Le diff corrigé vérifié par
`git apply --check` reconstruit uniquement la copie privée, qui contient son
conftest isolé : ce n'est pas un patch d'activation. Le premier diff gelé reste
conservé avec son défaut de séparation. Aucun patch n'a été appliqué au canon.

Aucun modèle, microphone, GPU, serveur ou réseau n'a été utilisé par cette QA.
La nouvelle opération doit encore passer une inférence réelle puis la recette
élargie. La lecture des SHA modèle fait partie de son coût, non mesuré par
les7,58s du diagnostic précédent. **Direct industriel, deux pistes, P95,
T12 et L12 restent ouverts.**
[Protocole L03](.ui-preview/pilots/l03-grouped-transaction-v2-20261014-4c0f31c397fe/PROTOCOL.md) ;
[paquet scellé](.ui-preview/pilots/l03-grouped-transaction-v2-20261014-4c0f31c397fe/preparation-v2.json) ;
[revue indépendante](.ui-preview/pilots/l03-grouped-transaction-v2-20261014-4c0f31c397fe/reviews/independent-transaction-review-assistant-20261014-v1.json).


## Reprise et essai de consolidation — 14 octobre 2026

L'objectif complet L00–L12 est repris. Les mentions de pause du 13 octobre
ci-dessous décrivent l'état antérieur. L'essai privé medium CPU est réellement
terminé : trois réponses séparées et une réponse regroupée, sources/PCM/options
vérifiés, processus et Job fermés, 32,433 s avec publication. Les trois phrases
fictives gardent leurs six valeurs attendues, dont 1250 W ; le modèle medium
reconnaît cette puissance aussi dans le contrôle individuel. La précision
observée ne peut donc pas être attribuée au regroupement.

Les encodages mesurés passent de trois à un et le calcul de 18,000 à 7,580 s
sur cette comparaison unique. Ordre/cache/charge extérieure limitent ce résultat.
Ce profil n'est pas activé dans Agent. Le worker produit ne transmet pas encore
les mots natifs nécessaires à la provenance de segments traversant plusieurs
fragments. Le contrat candidat prévoit une opération batch distincte, avec
conservation des corrections, des sources et de la commande durable.

Le nouveau contrôle de géométrie visuelle passe quatre tests purs ; son
pilotage réel reste à raccorder. **Qualité industrielle générale, débit
multipiste, délai visible/P95, T12 et L12 restent non qualifiés.**
[Essai réel](logs/foresight-runtime/medium-consolidation-success-root-20261014.json) ;
[contrat de consolidation](.ui-preview/pilots/l03-grouped-pcm-contract-20261014-73d64b8cd8d4/CONTRACT.md) ;
[QA pure visuelle](logs/foresight-runtime/ui-visible-geometry-v2r1-root-pure-qa-20261014.json).


## Retour de travail dans l'interface — 13 octobre 2026

Le frontend partage `asyncActivity` et `AsyncActivityIndicator`, monté une fois.
Le client `request` couvre l'attente de session, le transport et le décodage,
avec clôture dans `finally` après succès, erreur ou annulation. Les mutations
sont signalées immédiatement ; les lectures dépassant 800 ms sont signalées.
L'option `activity: false` concerne les lectures périodiques et les fragments
audio de fond. Les appels utilisateur et les lectures initiales restent suivis.
`beginActivity`/`withActivity` couvrent les lectures de fichiers et les suites
commande/actualisation ; les transports de notes, flux IA et fichiers sont suivis.

`AsyncDownloadLink` conserve le nom et les octets reçus, ferme l'attente à la
réception complète/erreur/expiration et nettoie les URL Blob à la fermeture.
Il couvre les ZIP de séances, originaux et pièces jointes à télécharger. Les
liens de consultation, lecteurs audio et fichiers déjà préparés gardent leur
comportement natif. Le statut ne confirme pas une écriture sur disque du PC.

QA UI : 916 tests passent dans 88 fichiers, TypeScript et build passent.
Le premier lancement ciblé a été refusé avant tests par EPERM ; sa reprise
autorisée passe. Le premier passage complet conserve 915 réussites et une
attente devenue obsolète sur les arguments de polling ; le passage final passe
après mise à jour de cette attente. Les reçus restent distincts. Aucune nouvelle
recette Python/backend, génération IA ou capture audio n'est revendiquée.
[Reçu UI](.ui-preview/pilots/async-feedback-20261013/qa/qualification.json).


## État actuel de la livraison — 13 octobre 2026

| Domaine | État établi |
| --- | --- |
| Notes et Studio | **Correctif actif dans Agent**, après publication, reprise du serveur et contrôle de l'interface. Réponses bornées à 12 ajouts, citations strictes, note humaine conservée, absence d'ajout expliquée et suspension STT visible. |
| Régressions logicielles | **2444 cas Python uniques : 2442 réussites, 2 exclusions prévues**, par agrégation vérifiée de deux exécutions. Frontend **916/916 dans 88 fichiers** (indicateurs du 13 octobre), unités fictives 37/37, Ruff, TypeScript et build passent. |
| Enrichissement IA | Pilote réseau : 12 ajouts conformes ; revalidation locale V2 passée. Les erreurs ASR citées restent présentes : format validé, qualité des faits industriels non qualifiée. |
| Transcription CPU fictive | 3 phrases puis 30 résultats sur 15 WAV complets, workers fermés. **1250 W reste transcrit 2250 W** avec ou sans vocabulaire technique. Le diagnostic de précision CPU sur une phrase donne aussi **2250 W en int8_float32 et en float32** ; aucune de ces variantes n'est activée par ce diagnostic. |
| Réunion complète | Recette d'une heure partielle. Transcription physique, multipiste et premier texte visible/P95 non qualifiés ; **T12 et L12 restent ouverts**. |
| Périmètre retenu | Adaptation publique du Studio validée ; Google Drive exclu. Les étapes et reçus historiques sont conservés ci-dessous. |

[Qualification Python nommée](.ui-preview/q/nac3/qa/python-aggregate-notes-ai-v2.json)
; [contrôles frontend/Ruff/TypeScript/build](.ui-preview/pilots/t12-enhancement-schema-candidate-v2-20261013/qa-root-observed-20261013.json)
; [diagnostic CPU](logs/foresight-runtime/t12-cpu-domain-paired-root-interpretation-20261013.json).

Les deux exclusions Python concernent le runtime audio optionnel et le dossier
Infomaniak absents. La qualification couvre les noms des cas sur deux exécutions,
pas un passage monolithique. Les motifs CPU 4/6 et 25/35 contre 23/35 ne sont pas
une précision générale. Ces diagnostics ont tourné pendant la QA logicielle et
ne qualifient pas les performances. Les sélecteurs de source/microphone/sortie
Windows et « Démarrer la réunion » ont été observés dans Agent, sans capture.
Les cinq documents ont été publiés après sauvegarde et vérification.
L'audit des droits de la nouvelle sauvegarde couvre 1 020 éléments : aucun accès
accordé aux groupes Utilisateurs ou Utilisateurs authentifiés.
[Audit des accès](logs/foresight-runtime/notes-structured-data-backup-acl-current-20261013.json).

Les sections de préparation et de recette ci-dessous conservent leurs états
historiques : leurs mentions « candidat non activé » décrivent les étapes
antérieures à la publication du correctif, le 13 octobre 2026.

## Bilan des essais courts — 13 octobre 2026

La recette d'interface de 60 secondes a livré quatre textes fictifs et conservé
leurs exports jusqu'au terminal ; le serveur de test est fermé. Le panneau
Transcription était initialement hors du champ visible : cette calibration
reste partielle et ne qualifie aucun délai d'affichage/P95. Le comparatif CPU
medium n'a produit aucune transcription : V1 a échoué au chargement ; V2 a été
refusée avant démarrage faute de mémoire physique disponible selon son seuil
de 9 GiB. Les protections et le profil de production restent inchangés.
**T12 et L12 restent ouverts ; le suivi automatique est actuellement en pause.**

[Bilan et preuves](docs/38_FORESIGHT_DELIVERY.md) ;
[interprétation CPU](logs/foresight-runtime/t12-medium-consolidation-root-interpretation-20261013.json).


---


État au 13 octobre 2026 : **composite V5 activé et vérifié sur Agent 8001**,
sauvegarde privée et restauration de contrôle réussies. **L12 reste ouvert**
pour la qualification réelle audio/ASR/direct et les compléments de recette.
Voir [la livraison](docs/38_FORESIGHT_DELIVERY.md).

Le candidat composite V5 R1 termine : **2 361 réussis, 2 ignorés, zéro échec**,
JUnit 2 363 cas, sources inchangées et Ruff réussi. Ses processus de test
sont fermés. Les deux cas ignorés et les trois avertissements sont consignés
dans [exploitation](docs/22_OPERATIONAL_IMPROVEMENTS.md). Le candidat reste
non activé ; la sauvegarde finale coordonnée et la recette matérielle restent
ouvertes. La qualification frontend GRAPH (858 tests) est distincte.

Le [guide Réunions](docs/23_MEETING_AUDIO.md#lancer-une-réunion-dans-agent)
décrit les choix de micro, sortie Windows et le bouton de démarrage.

Avant l'activation composite, les [originaux code/interface](.ui-preview/backups/promotion-code-20261012-205450-0d6f7a78/qualification.json)
et les [snapshots Brain/ERP restaurés en copie](.ui-preview/backups/promotion-db-online-20261012-205755-597ae1eb/qualification.json)
sont vérifiés. Sources SQLite ouvertes en `mode=ro`, `query_only=ON` ; toutes
les tables et leur contenu sont comparés, intégrité correcte et zéro anomalie
FK. Les deux snapshots en ligne ne sont pas un jeu coordonné après arrêt.
La tâche automatique de jalons progresse encore ; aucune maintenance engagée.

## Commandes du direct et flux de réveil — qualification du 12 octobre 2026

`foresight.live_transcription_enabled` est un booléen strict, faux s'il est
absent. `enabled=true` seul n'ouvre pas le moteur STT. Préparation présente un
opt-in distinct ; arrêter le direct conserve les fragments et n'arrête pas
une capture native. Les états installé, activé, opérationnel et qualifié
restent distincts. Le worker admet les fragments des séances en capture avant
l'historique, sans préemption ni borne globale du retard de transcription.

`POST /api/v1/meeting-sessions/{sid}/transcription/retry` reçoit
`command_id` et `expected_revision`. Une nouvelle commande remet les seuls
fragments échoués en attente après contrôle d'écriture, de droits, de version
et des opt-ins. Le reçu complété se rejoue même après désactivation, sans
nouvelle mise en file ; audio et corrections ne sont pas remplacés.

`GET /api/v1/meeting-sessions/{sid}/events?follow=true&after=N` suit les
notifications avec reprise du curseur et transactions SQL fermées entre les
lectures. La borne serveur de 30 s est logique, vérifiée entre lectures et
émissions ; un client lent ou une lecture SQL peut retarder la fin physique.
Le SDK ferme sa connexion après 35 s. Sans `follow`, le replay fini de 200
événements reste disponible. Les deux modes exposent id/type/révision/UTC et
`data={}` ; seul `transcript.updated` peut porter le `chunk_id` appartenant à
cette même séance. Les événements stockés sont conservés. L'export ZIP
contrôle les droits actuels des réponses pour les opérateurs restreints ;
les enveloppes masquées n'altèrent ni les originaux DB ni les versions de notes.
Aucun extrait, citation, proposition ou message d'erreur métier n'est émis.

L'interface utilise ces événements uniquement pour réveiller un GET autorisé,
regroupe les notifications et conserve le poll de cinq secondes en repli.
Masquage, changement de séance et démontage annulent l'ancien suivi. Une
correction de segment non sauvegardée ou une commande incertaine protège
aussi la fermeture/recharge du navigateur. Ces mécanismes ne démontrent
aucune latence voix-vers-affichage de cinq secondes.

Preuves ciblées : `live-controls-final-20261012-0340/qualification.json`
(49 tests backend), `live-event-root-controls-20261012-v5/python.xml`
(9 tests de flux SQL), `live-event-studio-targeted-20261012-v1/frontend.xml`
(81 tests d'éditeur). Les groupes sont inclus dans les passes complètes actuelles :
**2 141 Python réussis/1 ignoré** (2 142 cas, zéro échec/erreur) et
**768 React/80 fichiers** ; ils ne s'additionnent pas. TypeScript/build passent.
Le [global Python V3](logs/foresight-runtime/live-controls-global-20261012-v3/qualification.json)
termine à 05:57:16,374 UTC, exit0, sur 369 sources inchangées, et couvre le
correctif de confidentialité de l'export. Les 99 tests ciblés sans plugin staging
et Ruff dans `session-export-privacy-final-20261012-v1/` restent une preuve
recouvrante. Le premier global 2 084/1 ignoré précède ce correctif. Le global Python
V2 conserve 2 123 réussites/18 échecs/1 ignoré : les répertoires privés
`AppData/Temp/minipilot-test-*/storage/raw` sont devenus introuvables, avec
16 erreurs fichier directes et deux scans à zéro. L'acteur de cette disparition
n'est pas attribué ; aucun partage de stockage entre workers n'est démontré.
La [reprise ciblée des 18 cas](logs/foresight-runtime/live-controls-failed18-retake-20261012-v3/qualification.json)
passe 18/18 en 7,21 s. Elle et le global V3 utilisent des TEMP/TMP/TMPDIR,
caches et basetemp distincts et neufs sous `.pytest_work/`, sans changement
de service ou d'assertion ; leurs résultats ne sont pas additionnés.
La livraison canonique est vérifiée :
`backups/foresight-live-controls-delivery-20261012-060833-488129/` conserve
1 359 pièces, les deux restaurations SQLite sont intègres et le build
`B8cwhgBe/BJ0BE6LI` est contrôlé par SHA via HTTP sur8001. Les preuves
`live-controls-canonical-delivery-20261012-v1/` confirment santé, routes et
quatre opt-ins faux, 18 tables métier exactement conservées et 1 340 originaux.
Les trois tables de suivi héritées évoluent ; leur auteur n'est pas tracé.
Le lanceur de livraison ferme explicitement ses connexions SQLite avant le
manifeste ; le service général de sauvegarde n'est pas modifié. Les deux
tentatives précédentes restent archivées : sidecars EG2 temporaires, puis
suffixe URL du favicon traité à tort comme nom disque. Aucune pièce retirée.
Les gels préparatoires sont renouvelés sur 32 ressources matérielles et
13 contrôles T12 ; revue exacte et GO restent distincts. Aucun matériel ouvert
ni accord consommé. Le panneau navigateur est réellement visible depuis
06:10:51 UTC ; cela ne vaut pas encore UI_READY de la future séance.

La première exécution T12 du paquet `t12-realtime-preparation-20261012-061344-977401ad`
sort en échec avant ready/cadence : le harnais appelle `Path(None)` lors de
l'audit normal Windows de `Popen` sans `executable` explicite. Le contrôleur
conserve `driver_exit=null`, sortie fixture1, aucun UI_READY et aucun résultat
60 minutes. Job vide avant fermeture, handles fermés, moniteur et watchdog
sortis : nettoyage confirmé. Le défaut concerne le harnais ; le logiciel
qualifié reste inchangé. Une nouvelle préparation/GO après tests ciblés est requise.

Le correctif d'audit passe 70/70 (53 existants et 17 nouveaux). L'essai du
paquet `t12-realtime-preparation-20261012-062508-21757896` atteint le démarrage
du résident mais pas UI_READY dans180s ; nettoyage naturel confirmé, 0fragment.
Après autorisation humaine explicite, Gemma est rechargé avec8192 tokens avant
le GO du paquet `t12-realtime-preparation-20261012-073309-0c8fb3d0`.
UI_READY réel à07:36:45UTC (onglet22 sélectionné, navigateur et panneau visibles)
est consommé. Resume produit200, puis route privée `/_t12/cadence`422 : zéro ACK,
aucun `cadence.server-start`. L'import local de Request avec annotations différées
est à corriger dans le seul harnais. Stop privé200 ; Job final0/handles fermés,
mais fermeture forcée et `fixture_exit_code=null` : aucune qualification naturelle.
Le budget et les corpus restent inchangés ; aucune fenêtreLLM ou réunion60min exercée.

Le correctif Request et fermeture ASGI du harnais passe80/80 dans
`t12-request-shutdown-final-20261012-074858-164b87ca/`. Les imports FastAPI
restent après l'admission OS ; Uvicorn privé borne sa fermeture ASGI à10s,
dans la grâce originelle. Le quatrième essai du paquet
`t12-realtime-preparation-20261012-075037-f05722cc` atteint resume200 puis
cadence privée200. Après cinq secondes, les deux uploads de séquence0 échouent
avec HTTP500, avant toute conservation durable : `FileNotFoundError` dans
`_write_file`, ouverture de `.wav.pending` de278/281 caractères, parents présents.
Le [contrôleur final](logs/foresight-runtime/t12-realtime-preparation-20261012-075037-f05722cc/controller-final.json)
conserve zéroACK, trois événements SSE initiaux, sortie fixture0, Job vide avant
fermeture, handles/moniteur/watchdog fermés et nettoyage naturel réussi.
La cadence60min, les fenêtresLLM et la latence ne sont pas qualifiées.

Le correctif du seul contrôleur crée désormais `LOGS/t12-fixture-<nonce32>`
comme frère du run_dir, sans déplacer les anciennes pièces. Il exige le parent
exact, un nonce valide et un dossier neuf ; les deux chemins `.wav.pending`
de228/231 caractères sont vérifiés avant Popen/import applicatif.
[88/88 ciblés](logs/foresight-runtime/t12-storage-path-final-20261012-080347-6f3a5345/qualification.json)
et [18/18 contrôles RO](logs/foresight-runtime/t12-realtime-preparation-20261012-080514-4a9929b5/review.json)
passent sur le nouveau paquet `f0d5936d…`. L'essai5 est lancé avec le nonce
`ad9ac55a339e49d3a153cd432d416010` ; UI_READY réel à08:14:20,837UTC confirme
l'onglet24 sélectionné, le navigateur et la transcription visibles.
Le dossier privé est `logs/foresight-runtime/t12-fixture-ad9ac55a339e49d3a153cd432d416010`.
Aucun verdict final de cet essai n'est publié dans ce point d'avancement.
Budgets/corpus/profils et sources produit369/216 restent inchangés ; L12 ouvert.

**Essai5 terminé — échec du seuil de sécurité de recette.** Le driver tourne
de08:14:27,609558 à08:27:12,819225UTC, environ765,21s, puis s'arrête sur
un retard par piste de605000/600000ms. Le seuil600000ms est un arrêt de sécurité
du harnais, pas un quota ni un nouveau critère de qualification produit.
306 nouveaux fragments sont conservés (153 micro/153 système) ; la trace compte
307 ACK avec un seul rejeu micro séquence120. La base conserve32 micro traités/
121 en attente et33 système traités/120 en attente, ainsi que88 segments provisoires.
Les306 WAV totalisent48973464 octets, SHA et tailles exacts, avec765000ms
de couverture par piste ; le seuil est observé à765,106446s de cadence,
distincts de la durée du driver.
Le collecteur reçoit375 événements SSE tandis que la DB en compte377 ; ce
décompte ne démontre pas leur visibilité utilisateur ni une latence≤5s.
Les deux événements finaux `chunk.received`376 et `transcript.interrupted`377
ne sont pas reçus par ce collecteur.

Seule la fenêtre `llm-010` exerce cinq opérations et trois dispatchs effectifs : proactif `InferenceBusy`,
proposition et question devenues obsolètes, deux consommateurs d'annulation
sortis. L'arrêt du calcul externe reste inconnu ; `llm-030`/`llm-050` sont non
exercées. La priorité en file reste non qualifiée. Le profil de copie est
Large-v3-turbo CPU int8/4threads ; aucun profil
produit n'est modifié. Contrôleur final faux, driverexit1, fixtureexit0,
Job vide avant fermeture, handles/moniteur/watchdog fermés et nettoyage naturel
réussi : conservation/fermeture et qualification longue restent distinctes.
Gemma est déchargé après repos à08:29:59,524UTC ; le
[reçu de restauration](logs/foresight-runtime/t12-realtime-preparation-20261012-080514-4a9929b5/lmstudio-restored-unloaded.json)
confirme `loaded_instances=[]` et santé Agent/Brain/ERP `ok`.
La [revue finale RO](logs/foresight-runtime/t12-realtime-preparation-20261012-080514-4a9929b5/review-final.json)
confirme21 points de conformité de l'échec et de conservation, qualification fausse.
Quatre observations navigateur ont leur panneau visible, sans mesure du premier
DOM ; l'export du probe n'est pas observé, sans preuve d'échec de ce probe.
Le résultat60min et la qualité/latence industrielle restent non qualifiés, L12 ouvert.

Les tests Python utilisent `.pytest_work/` pour les chemins temporaires courts,
avec caches et basetemp distincts par passe ; ce dossier est exclu de Git.
La recette navigateur textuelle a douze contrôles API/DB et quatre observations
CUA, sans moteur/audio. L'ERP conserve les versions 1 et 2 de la note ; le
staging Brain est vide pour cette note déjà liée. Le premier lecteur qui
testait à tort ce staging ainsi que son échec d'encodage stdout sont conservés.

## Livraison complémentaire Studio — 12 octobre 2026

Les lectures de séance acceptent les réponses dans un ordre monotone, avec
contrôle de l'identité, de la révision et du curseur. La restauration du brouillon
se fait sur la première réponse acceptée. Un ACK de sauvegarde ancien ne supprime
pas le brouillon d'une note plus récente ; un changement de transcription seul
ne déclenche pas de faux conflit de note. Le backend et les schémas ERP/Brain
ne changent pas dans cette passe.

Le reçu `studio-snapshot-order-final-20261012-v2/qualification.json` couvre
**724/724 React, 75 fichiers**, sources inchangées, puis TypeScript/build.
Les 106 cas ciblés recouvrent ce global. Le premier global 723/724 est conservé :
le test de publication attendait insuffisamment le chargement de son option ;
seule sa synchronisation est corrigée, sans modification de la publication produit.
`studio-snapshot-delivery-20261012/` conserve neuf contrôles navigateur/SQLite
sur copie, la sauvegarde des assets et la preuve HTTP de `CHpAuznx/BJ0BE6LI`.
Le global Python précédent 2 056/1 ignoré n'est pas relancé pour cette passe UI.
Les flags séance/proactif/enrichissement restent faux ; Drive reste désactivé.
La préparation matérielle est rescellée sur le JS courant : 31 ressources,
28 inchangées, 22 contrôles de revue RO. Elle attend toujours la réponse à
l'accord matériel regroupé ; aucun nouvel accord n'est consommé ici.

Le candidat Parakeet CPU à deux threads reste séparé des profils actifs.
Son premier essai contrôlé s'arrête en 1,19 s avant toute phase ASR observable :
le garde de ressources refuse un comptage de Job inattendu. Fermeture forcée
du seul Job, exit92, Job vide et handles fermés, sans qualité/latence qualifiée.
Le brut est conservé ; aucun retry automatique ni changement canonique.
Le diagnostic factice R3 atteste ensuite le principal et son conhost Windows,
avec fermeture naturelle et quinze contrôles RO du résultat. Il ne qualifie
aucune ASR ; le garde adapté et son nouveau GO restent une étape séparée.
La recette longue T12 V2 est préparée : 63 contrôles pure/mock et 32 critères
RO, sans exécution de moteur/serveur. Elle exige un GO distinct et une
transcription réellement visible par CUA avant le début des 60 minutes.
La lecture `production-post-studio-snapshot-20261012.json` conserve les 18 tables
protégées et 1 340 originaux par SHA. Depuis le checkpoint, les suivis comptent
173 inputs ajoutés, sept scans/deux analyses modifiés, sans suppression ; aucune
séance/projet/CR fictif en production. L'attribution aux workers est une inférence.

## Exploitation de la fusion Foresight

Correction des notifications natives en qualification : `NativeCapture.events`
est une file de huit contrôles. Un fragment passe par sa persistance/son reçu
et n’entre jamais dans cette file. EOF et code de sortie 0 sont contrôlés avant
le succès STOP. Le marqueur serveur `_native_drain_confirmed` est commité
avant le reçu parent ; il permet un rejeu après perte de réponse sans déduire
la fin matérielle de la seule présence des WAV. Un arrêt matériel non confirmé
rejette durablement sa commande (409), libère sa réservation de commande et
laisse la séance interrompue. Une nouvelle action explicite peut finaliser
les seuls fragments SQL, avec avertissement conservé dans les lectures futures.
Une réservation native encore enregistrée interdit cette finalisation, même
si son état est déjà stopped/interrupted. Aucun de ces gardes n’ouvre un flux.

Le [reçu courant](logs/foresight-runtime/native-control-queue-20261012/current-evidence.json)
lie les assets actifs `1Pn4h413/B17lYRwK` aux **802 tests React**, TypeScript et
build sur 218 sources inchangées. La revue ciblée valide les gardes natifs.
La V1 Python termine à **2 183 réussis/1 ignoré**, exit0 ; trois sources ont
changé et un test a été ajouté pendant la passe : elle ne qualifie pas l’arbre
final. La V2 `native-control-queue-global-20261012-v2/` termine avec **2 190
réussis/1 ignoré**, exit0, sur 371 sources inchangées, TEMP/bases/cache neufs
(session 47379 terminée, 1 916,10 s). Le
[reçu terminal](logs/foresight-runtime/native-control-queue-20261012/python-v2-terminal.json)
revérifie aussi les sources actuelles. Le candidat d’admission STT isolé n’était
pas inclus. Le processus 8001 a démarré après les modifications natives ;
leur chargement est déduit de cet ordre, sans attestation de hash en mémoire.
Les opt-ins général/direct sont observés actifs, sans qualification nouvelle
de latence, qualité industrielle ou matériel. La file SQL STT reste non bornée.

Le candidat source `.ui-preview/pilots/stt-admission-stage-20261012/` ajoute un
quota direct et un batch explicite sans projet, avec reçus et audio conservés.
Ses preuves restent séparées : frontend V5 816/816 et TypeScript/build ; ciblé
backend 153 réussis/1 ignoré, mélange synthétique vérifié séparément. La V1
globale conserve 2 290 réussis/2 échecs/2 ignorés : ressources Thunderbird
absentes et ancien test de reprise automatique failed, désormais repris.
La V2 termine à **2 300 réussis/2 ignorés**, exit0, en 2 063,96 s à
16:12:01 UTC, sur 377 sources et 56 ressources inchangées. Le
[compagnon terminal V5](.ui-preview/pilots/stt-admission-stage-20261012/qa/staged-checkpoint-v5-python-v2-terminal.json)
revérifie le JUnit et toutes leurs empreintes actuelles ; le checkpoint V5
historique reste conservé. La désactivation
générale du batch est corrigée, avec fermeture même après un autre arrêt
échoué ; le direct seul désactivé laisse le batch. Les erreurs de lecture
résolues disparaissent sans effacer les erreurs de sauvegarde. La cause de
transport initiale n'est pas attribuée. La conservation sous cadence fictive
d'une heure est vérifiée, sans moteur ASR ni acquisition matérielle.
Le candidat n'est pas chargé sur 8001 et ne qualifie aucun seuil industriel.
L12 reste ouvert : l'ancien essai complet de cadence échoué est conservé et
la nouvelle mesure des acquittements est revue. Son smoke fictif de 30 secondes
termine à code 0, six paires et 12 fragments conservés, avec un retour ACK
maximal de 0,047453 s. Le full de 3 600 secondes termine sur le même seal :
720 paires/1 440 fragments et WAV exportés, note/reçus inchangés, ACK maximal
de 0,177379 s, quota 24/120 000 ms, deux engines fermés et aucune inférence.
Le [résultat terminal](logs/foresight-runtime/sqc-run-20261012-163237-ddd94164/qualification.json)
conserve 24 pending, 48 failed simulés et 1 368 retained ; il ne prétend pas
à une transcription achevée. Les sept portes fichiers de promotion sont
vérifiées, avec sauvegarde et absence d'activité restant à contrôler.
La requête CUDA indépendante, limitée à 15 secondes, voit une carte et les
types de calcul dont `int8_float16` ; elle ne charge ni Whisper ni poids.
La compatibilité et les budgets futurs sont distingués dans le
[protocole GPU](.ui-preview/pilots/STT_GPU_QUALIFICATION_PROPOSAL.md).

Un essai GPU séparé charge ensuite Whisper medium, mais le premier encode
échoue sur `cublas64_12.dll` absente ou non chargeable. Aucune transcription
n'est produite ; sortie des processus, Job vide et fermeture NVML sont
confirmés en 7,902 s par le
[reçu d'échec](logs/foresight-runtime/gpu-short-run-20261012-173342-f7bc6d33/qualification.json).
Aucun profil GPU produit n'est activé.

Le candidat regroupé NEXT ajoute aux quotas la récupération native durable.
Les reprises avant ouverture reprennent l'admission CPU ; le commit propriétaire
se fait hors registre, avant ouverture matérielle. Le ciblé passe **70/70** avec
revue indépendante ; le frontend complet passe **858/858**, TypeScript/build.
Le nouvel essai GPU V6, autorisé séparément, refuse l'inventaire avant import CT :
deux handles n'ont pas de chemin disponible. Aucun modèle chargé, aucun cas
transcrit. Les deux observations sont fermées avant le refus ; leur cause reste
inconnue. Processus/Job/NVML fermés en 10,25 s, accord unique consommé, aucun
changement de production. Le
[compagnon terminal V6](logs/foresight-runtime/gpu-short-run-20261012-191119-5f626f87/root-terminal-review.json)
ne requalifie pas l'échec V5 ni T12/L12.

La régression complète NEXT V1 (378 Python, 57 ressources inchangées) termine
à **2 330 réussis, 2 échecs et 2 ignorés**, sortie 1 : export avec droits modifiés
et garde propriétaire natif ont échoué dans cette passe historique.
Les deux fixtures sont corrigées sans modification produit, avec 73 tests ciblés
réussis et revue indépendante. La V2 complète, lancée à 18:46:51 UTC, termine à
**19:24:29 UTC : 2 332 réussis/2 ignorés**, soit 2 334 cas, zéro échec/erreur et
sortie 0 ; les **378 sources Python et 57 ressources** restent inchangées.
Le [global V2](.ui-preview/pilots/native-interruption-next-20261012/qa/python-global-next-v2/qualification.json)
et son [compagnon terminal](.ui-preview/pilots/native-interruption-next-20261012/qa/python-global-next-v2/root-terminal-companion.json)
conservent ces preuves ; le [Ruff global V2](.ui-preview/pilots/native-interruption-next-20261012/qa/ruff-final-20261012-192805-8cc955c5/qualification.json)
termine sortie 0 sur les mêmes 378 sources. Les
[26 fichiers](.ui-preview/pilots/native-interruption-next-20261012/candidate-promotion-manifest-v2.json)
incluent sept nouveaux fichiers. Le correctif responsive externe passe séparément
858 tests/TypeScript/build ; sa [recette navigateur](.ui-preview/pilots/a9-responsive-capsule-20261012-193009-620a51a6/proof/root-ui-qualification.json)
confirme le défilement local à 320/670/1280/1915 px, le clavier et la conversion
réelle Action→Tâche. Son serveur est fermé. Le contraste insuffisant des traits
SVG est corrigé sur une autre copie (six couleurs, 858 tests/TypeScript/build).
Sa [vérification visuelle réelle](.ui-preview/pilots/a9-graph-contrast-capsule-20261012-200758-543f2df4/proof/root-graph-qualification.json)
confirme les traits à 5,269:1 et le focus à 4,936:1 dans le thème clair, les
largeurs 320/670/1915 px et la consultation de la source. Le serveur est fermé ;
le thème sombre réel et l'ensemble de T13 restent distincts de cette portée.
NEXT n'est pas activé ; aucune clôture de T12, T13 ou L12 n'en découle. Le
[dossier composite V3](.ui-preview/pilots/native_next_promotion_plan_v3.md)
associe 29 fichiers (22 remplacements/7 nouveaux) et les sources backend/frontend
qualifiées séparément. Ses [neuf portes de fichiers](.ui-preview/pilots/native-interruption-next-20261012/qa/next-v3-file-gates-before-root.json)
passent ; elles ne prouvent ni maintenance, ni sauvegardes, ni stockage global.
Le contrôle daté observe une analyse de jalons
active et huit en attente, avec les quatre opt-ins Foresight actifs. L'activité
utilisateur et le stockage effectif restent à confirmer ; aucune permutation
canonique n'est réalisée. L'utilisateur autorise séparément les bibliothèques
GPU privées et un seul nouvel essai fictif de cinq minutes.

Cet essai V5 est désormais terminé : 12 phrases SAPI transcrites en CUDA,
27 informations critiques et garde numérique correctes, WER pondéré 0,021739.
La relecture des textes complets par root confirme nombres/unités/négations sur ce
seul corpus propre. Les trois fenêtres [500,5500] ms calculées en 0,584–0,602 s
produisent « 2,5 mm » au lieu de la section complète « 2,5 mm² » : texte incomplet,
non qualifié pour publication métier. La vérification d'origine d'une DLL échoue,
sans conserver son nom/chemin ; elle reste à diagnostiquer. Le
[reçu terminal](logs/foresight-runtime/gpu-short-run-20261012-181408-3771563f/qualification.json)
est false, fermeture processus/Job/NVML confirmée en 22,042 s. Le calcul court
ne mesure pas P95 visible ; aucune activation ni seconde tentative n'est effectuée.

Le parcours de démarrage est accessible dans `/app/meetings` avec **Nouvelle
séance**, y compris lorsque la capacité générale est désactivée. Le formulaire
propose alors **Activer les réunions** : lecture des réglages actuels puis PUT
`/api/v1/workspace/fusion-settings` avec seulement `enabled=true` modifié.
Les autres opt-ins, le mode et l’état de préparation sont conservés ; les droits
du propriétaire restent contrôlés par le serveur. L’ouverture de la séance ne
lance aucune capture. **Source audio** et **Démarrer la réunion** sont visibles
hors du volet Préparation. **Périphériques** expose les sélecteurs ; le micro
est grisé pour le mode son du PC seul, la sortie pour le mode en salle.
Choisir son du PC + ma voix ou en salle autorise le microphone au démarrage.
La liste navigateur utilise uniquement `enumerateDevices` ;
`getUserMedia` reste réservé au clic de démarrage, avec le `deviceId` exact choisi.
La sortie Windows désigne le flux à enregistrer, sans modifier le périphérique
de lecture du système. Pause/Arrêt restent accessibles hors des diagnostics.

Les sessions et le catalogue sont des extensions additives du serveur **8001**.
Brain conserve sessions, commandes idempotentes, fragments, segments et versions
de staging ; ERP conserve les notes, leurs versions, les comptes rendus et les
actions. L'outbox ERP et les reçus Brain assurent une reprise entre les deux
bases. L'index EG2 texte existant reste distinct de l'index multimodal dérivé.
Une note sauvegardée ne dépend d'aucune réponse LLM ; son ancienne version est
immédiatement exclue du rappel courant. Aucune indexation ne valide une décision.

Ouvrir `/app/preparation` pour activer l'espace, choisir PC/réseau et contrôler
séparément capture, STT, recherche et génération. Les questions proactives et
l'enrichissement automatique ont deux réglages distincts, désactivés par défaut :
`proactive_enabled` et `auto_enhancement_enabled`.
`AGENT_MEETING_SESSIONS_ENABLED=0` impose l'arrêt des nouveaux démarrages ;
la récupération des séances existantes demeure accessible. Un redémarrage
n'ouvre jamais un microphone : les captures interrompues sont signalées.

L'arbitrage CPU audio réserve la voie directe pendant une séance en capture,
en pause ou en finalisation, ou tant qu'un propriétaire natif demeure présent.
Il refuse une nouvelle transcription complète ; un batch déjà en file reste
`queued`, avec son audio intact et un motif visible, puis reprend après libération.
Un batch en cours refuse immédiatement un démarrage/reprise navigateur ou native
avec HTTP 409. Le verrou couvre seulement l'admission et le changement d'état,
sans attente derrière un calcul de quatre heures ni préemption du calcul actif.
Le coordinateur voit les travaux Agent, pas les autres applications du PC.

Les priorités de la file IA sont : question explicite, manuel, synthèse,
proactif, complément, fond ; elles ordonnent les demandes en attente seulement.
L'admission proactive partage un budget de **2 s** entre l'activité de fond et
la réservation du moteur, avec annulation avant démarrage lorsque le worker est
arrêté. La recherche préalable reste hors de ce budget. Le worker limite chaque
passage à 20 séances et 12 segments récents, avec attente de 8 s entre passages.
Une seule action IA est admise par passage : question prioritaire, sinon
enrichissement. Pour celui-ci, le même contexte sauvegardé doit avoir été observé
stable pendant au moins **8 s**. Une réservation durable précède la génération ;
le même contexte n'est pas retenté automatiquement, même après un redémarrage.
Le brouillon non enregistré reste exclu de l'analyse. Le texte proposé doit
être accepté explicitement, avec contrôle de version et des droits.

L'appel automatique utilise un transport HTTP configuré à **45 s**, sans seconde
tentative sur contenu vide, repli de fournisseur ni chargement de modèle.
Ce timeout de socket n'est pas une limite de durée totale. Un appel en cours
reste non préemptible ; l'arrêt du worker ferme les nouvelles admissions.
Les appels manuels gardent leurs règles historiques de reprise/repli. Une
tentative interrompue ou sans résultat durable affiche « Tentative à reprendre ».
La file est bornée à 32 attentes par moteur.

Le batch audio historique conserve son moteur et attache son enfant Windows à
un Job Object `KILL_ON_JOB_CLOSE` : disparition d'Agent termine cet enfant.
Le handle est fermé dans `finally` ; un échec d'attachement termine/force l'arrêt
de l'enfant et refuse tout résultat. Le raccordement a passé **5 tests de cycle
de vie à processus/handles simulés**, incluant annulation, erreurs et conservation
exacte de l'original ; cela ne constitue pas un essai de crash matériel du batch.
Procédure, contrats occupé/annulé et limites :
[Réunions audio](docs/23_MEETING_AUDIO.md).

Installations reproductibles dans des runtimes Python isolés :
`powershell -File scripts/setup_audio_runtime.ps1 -Model small` et
`python scripts/setup_multimodal_embeddings.py --help`. Variables audio :
`PB_SPEECH_PYTHON`, `PB_SPEECH_MODELS_DIR` ; multimodal :
`PB_MULTIMODAL_PYTHON`, `PB_MULTIMODAL_MODELS_DIR`.
Les helpers sont des processus enfants supervisés, sans second serveur HTTP.
WASAPI exige une session Windows interactive ; le service en Session 0 n'est
pas qualifié. L'installation d'un modèle ne démontre pas sa qualité sur une réunion.

API : `/api/v1/meeting-sessions` (création, notes, audio, commandes, segments,
assistant, calendrier, publication et export), `/api/v1/workspace/sources`
(catalogue, imports, labels, versions et recherche),
`/api/v1/workspace/fusion-settings`, `/fusion-stats`, `/source-graph` sous ce même
préfixe workspace. Les droits projet sont contrôlés à chaque lecture/écriture.
Les citations conservent note/version, page physique PDF, feuille/plage de
cellules, image ou piste/temps audio réels. Les versions devenues obsolètes sont
signalées après génération.

La tentative T11 du 11 octobre a terminé sur délai d'attente : 158 inventaires
Wi-Fi déconnecté sur 192, F5 virtuel actif sans IP/route visible, zéro enfant
d'inférence lancé. Le contrôle conservateur a gardé cette ambiguïté bloquante.
Le marqueur `RECONNECT_NOW.txt` indique uniquement la fin du contrôleur ; il ne
certifie pas une réussite. Protocole et données brutes :
`.ui-preview/pilots/OFFLINE_PHYSICAL_PROTOCOL.md` et
`.ui-preview/pilots/offline-physical-runs/20261011-213859-2faa854b/`.

`GET /api/v1/meeting-sessions/{sid}/ask` relit l’historique sans appeler le LLM ;
`scope` et les paramètres répétés `source_ids` partitionnent la conversation.
Le serveur vérifie les droits d’origine et les droits actuels de chaque source
citée, y compris après son déplacement. Une réponse devenue inaccessible est
masquée entière. Le tri/dédoublonnage des IDs empêche une conversation distincte
pour le même ensemble de sources. Les messages de contexte sont bornés.
`PUT /{sid}/live-answers/{answer_id}/pin`, sous le même préfixe, reçoit
`{"pinned": true|false}` : état durable et rejouable, lecture seule refusée,
50 cartes épinglées au maximum, aucun événement de réponse réécrit.
`GET /{sid}/note-versions/{version_id}` lit un instantané de staging exact,
avec contenu, SHA et date ; une version étrangère à la séance renvoie 404.
Cette lecture reste disponible lorsque les nouveaux démarrages sont désactivés.
Les dates de staging sont sérialisées en UTC explicite, y compris celles
enregistrées par SQLite sans fuseau. Accepter ou rejeter une proposition passe
par le verrou de séance du processus API : la commande perdante renvoie 409
avant toute création de version ERP. Ce contrat est qualifié pour l'unique
processus API Agent ; plusieurs processus API indépendants exigeraient une
réservation durable supplémentaire.

L’import URL choisit l’extension selon le MIME connu puis le nom fiable ; un
format inconnu demeure explicitement non extractible. Réimporter une ancienne
version mal identifiée peut créer une interprétation additive des mêmes octets,
vérifiés par taille/SHA. L’ancien original et ses artefacts restent conservés ;
le rejeu ne rétablit pas silencieusement une ancienne tête de source.

Limites : fichier importé 50 Mio, capture 512 Mio/120 minutes ; index multimodal
500 sources/5 000 entrées, originaux médias 512 Mio, index 256 Mio, audio 2 h.
Ces quotas n'autorisent aucune purge automatique. Le code conservé d'import Drive
prévoit un jeton choisi et protégé DPAPI ; ce connecteur reste désactivé et hors
de la livraison, sans prétendre fournir un parcours OAuth complet.
Les scans sans texte sont signalés comme nécessitant une extraction adaptée.

La sauvegarde doit être effectuée Agent arrêté : `scripts/agent_backup.py`.
La restauration exige un dossier neuf, vérifie les empreintes et conserve les
nouvelles données. Elle désactive les capacités, fige les commandes anciennes,
remappe les fragments et journaux natifs, et invalide les projections multimodales
avant une reconstruction explicite. Ne pas écraser le canon avec une image ancienne.

L'archive JSON d'un projet conserve son format historique et ses sources
canoniques avec les médias exportables. Elle constitue un transport de projet,
pas une sauvegarde complète de Studio ou du catalogue : séances, fragments,
commandes, identités du catalogue, versions et liaisons fournisseur ne sont pas
inclus dans ce format. Un avertissement explicite est ajouté lorsqu'une séance
ou un catalogue du projet existe. Utiliser le ZIP de séance pour Studio et la
sauvegarde globale coordonnée pour l'ensemble des données et du catalogue.
L'export conserve les données locales ; il ne purge aucune table ni aucun fichier.

Le [plan](docs/37_FORESIGHT_FUSION_PLAN.md), le
[registre de recette](docs/38_FORESIGHT_DELIVERY.md) et les
[références UI](docs/39_FORESIGHT_REFERENCE_UI.md) donnent les preuves exactes et
les critères restant ouverts. Tests : pytest et Ruff du dépôt, npm test,
TypeScript et build ; les essais de recette écrivent dans des bases fictives.

Première qualification globale Python : **1 920 réussis, 1 ignoré** en 1 694,03 s,
rapport `logs/foresight-runtime/global-python-final.xml`. Les treize tests de
minuterie du harnais microphone, ajoutés après collecte de cette suite, passent
séparément avec `--noconftest` ; ils n'ouvrent aucun périphérique. Le microphone
Realtek a fourni cinq WAV/25 s au premier essai. Le second essai autorisé a fermé
normalement le flux à 30,003 s et conservé six WAV/29,900 s. Le rapport brut
reste `passed:false` : le quota strict manque de 100 ms. Aucune écoute ni
transcription de ces fichiers n'a été effectuée. Tout nouvel essai matériel
exige une nouvelle autorisation d'enregistrement. La capture active est bornée
à 30 s depuis START, sans renouvellement au premier paquet ; les buffers acquis
avant la frontière sont vidés après arrêt, sans masquer un quota incomplet. Voir
[test matériel et post-mortem](docs/23_MEETING_AUDIO.md#test-matériel-autorisé-du-microphone-realtek--11-octobre-2026).
Le test Jabra autorisé séparément a ensuite fermé normalement le flux à
START + 30,004 s : six WAV/25,900 s, signal non nul et SHA exacts, premier callback
à +4,166 s, cause non établie. Le quota strict reste incomplet ; aucune nouvelle
ouverture, écoute, transcription ou écriture canonique. Audit et contrôle de
zéro processus dédié dans `qualification/headset-jabra-30s-20261011-191634-13ab015a/`.
Ce test du microphone de casque ne qualifie pas la navigation pendant capture
intégrée, le loopback Jabra ou le remplacement de périphérique.

Sur le canon, les routes et schémas additifs sont chargés ; le flag effectif
de séance et le proactif sont désactivés. Sources et Statistiques sont actifs.
La première coupure Wi-Fi a bloqué l'ancien contrôleur, sans enfant moteur.
Après correction structurelle et revue, la nouvelle recette coordonnée termine
à 20:53 UTC avec transcription, recherche EG2 et génération Gemma réelles sur
quatre sources fictives. La coupure est observée sur neuf inventaires qualifiés,
dont six pendant les 43,91 s de l'enfant, avec un écart maximal de 7,32 s.
Scratch configuré avant import, sortie 0, Job vide et handles fermés sont confirmés.
Rapport brut : `.ui-preview/pilots/offline-physical-runs/20261011-225003-77be78b1/qualification.json`.
Le trafic natif n'est pas compté ; aucun zéro tentative native n'est revendiqué.
Le direct industriel ne
passe pas ses critères de qualité/latence ; le lot L12 demeure ouvert.
L'essai unique Jabra sous la nouvelle autorisation de 45 s ferme normalement
après 26,5344 s et conserve cinq WAV/24,1 s, sans écoute ni transcription.
L'arrêt sur seuil ADC technique de 2 ms n'établit pas une perte physique :
status0 et 4 800 trames sont reçus sur tous les callbacks, mais ne prouvent pas
non plus la continuité matérielle. L'autorisation est consommée ; le rapport
`microphone-data-window-readonly-postmortem-20261011-2050/read-only-diagnostic.json`
préserve l'échec brut et les empreintes. Une nouvelle autorisation unique a
ensuite été reçue pour le harnais v2 : 76 simulations et revue statique indépendantes
passent, sans addition aux 2 051 tests du dépôt. Le seuil ADC de 2 ms reste un diagnostic,
distinct du quota PCM et des erreurs bloquantes de format/status/fermeture.
Le nouvel essai `qualification/headset-jabra-v2-data30-max45-20261011-212458-84da2978/`
réussit le quota nominal de 30 s / 1 440 000 trames par canal, six fichiers et fermeture
normale après 32,6905 s, avant 45 s, sortie 0 et Job vide. Neuf anomalies temporelles restent visibles,
`physical_continuity_qualified:false`. Les tests frontend déjà engagés ont
chevauché l'essai ; aucune performance de latence ou capture intégrée n'est
qualifiée par ce harnais autonome. Aucune écoute/transcription ; cette nouvelle
autorisation est consommée et aucun essai supplémentaire n'est autorisé.
La régression React complémentaire passe **672 tests dans 75 fichiers** en
235,84 s, avec TypeScript/build conformes. Le dernier ajustement du libellé F10
passe deux tests ciblés, TypeScript et un nouveau build, sans réexécuter la suite
globale. Rapports : `frontend-completion-qualification.json` et
`frontend-f10-label-followup-20261011-204228.json` dans `logs/foresight-runtime`.
Le dernier correctif de conversion Markdown compare des structures canoniques
plutôt que l'ordre des propriétés JSON du DTO : 97 tests ciblés, TypeScript et
build passent. Rapport `frontend-markdown-dto-followup-20261011-205428.json`,
asset de cette passe `index-DKlOduK1.js`. Les 97 cas recouvrent la régression précédente ;
ils ne s'ajoutent pas à son total.

Complément de fidélité publique : le catalogue conserve `source_type` et ajoute
`file_format`, déduit d'abord du MIME puis d'un suffixe compatible. Le filtre
précède le total et la pagination ; une note native n'acquiert pas un format de
fichier inventé. L'interface distingue Type de source et Format. Le studio
réutilise `NoteRichEditor` et le moteur ERP de notes hérité de XPilot ; la nouvelle
disposition complète garde notes personnelles, propositions enrichies et
assistant simultanément montés, avec sauvegarde et versions existantes.
En disposition complète sur desktop, les panneaux ont un défilement interne
distinct ; les commandes et diagnostics restent dans une région accessible
au clavier. Sur petite fenêtre, la présentation longue est conservée. Depuis
Sources, Nouvelle séance ouvre le formulaire existant avec le projet accessible
choisi, sans créer de séance ni ouvrir de microphone au clic.
La coque compacte est limitée aux parcours Sources/Réunions ; le seuil du menu
et l'accessibilité du rail sont vérifiés lors du retour aux parcours métier.
La passe globale précédente de l'interface réussit : **694/694 tests, 75 fichiers**,
244,67 s, TypeScript et build conformes. JS `index-DhlxCsWr.js`, CSS
`index-DENGLpaQ.css` ; leurs SHA et les anciens assets sont conservés dans
`logs/foresight-runtime/source-session-layout-followup-20261011-221310/`.
Le complément Studio compact et Sources R01 réussit ensuite **716/716 tests
dans 75 fichiers**, TypeScript et compilation conformes, dans
`logs/foresight-runtime/studio-compact-followup-20261011/qualification.json`.
Les 132 tests ciblés recouvrent cette passe. Le DTO des fragments conserve
`speech_status` et `speech_error` : une file en attente ou en échec reste
visible même sans segment. Les durées sont présentées par piste. Les trois
dispositions du Studio utilisent des panneaux à défilement indépendant sur
desktop ; la préparation contient les commandes secondaires, tandis que
l'arrêt natif reste accessible pendant une acquisition ou un vidage.

Périmètre confirmé le 11 octobre : Google Drive est exclu de cette livraison.
Le connecteur conserve son code et ses données, avec un défaut désactivé ;
aucune connexion ou import Drive n'est autorisé. L'utilisateur valide
l'adaptation visuelle présentée du Studio et des dimensions principales des
Sources : F25/T13 est clos dans cette portée, sans parité exacte à ±2 pixels.
Décision et capture : `logs/foresight-runtime/user-scope-decision-20261011-drive-visual.json`.
Cette décision ne qualifie ni la capture intégrée ni la transcription industrielle.

Le contrat Drive effectif refuse les écritures avec 409 si
`foresight.drive_enabled` n'est pas strictement vrai ; ce contrôle intervient
après les droits et avant protection, révélation ou récupération de secrets.
GET conserve le statut 200 avec `enabled:false`. Le complément réussit 61
tests Python Sources et 29 React ciblés, TypeScript, Ruff et build :
`logs/foresight-runtime/drive-exclusion-followup-20261011-214949/targeted-ts-build-v1/qualification.json`.
Les globales 716/2 051 précèdent ces changements. La reprise Python complète
sur les fichiers gelés passe **2 056 réussis, 1 ignoré, zéro échec**, en
1 536,47 s dans `scope-python-final-20261011-v2`, avec empreintes inchangées ;
le premier lancement, refusé avant collecte par le sandbox, reste conservé.
Cette passe précède le seul correctif ultérieur de minuterie de sortie du
harnais de qualification audio, soumis à des simulations séparées.
Le ciblé de cette promotion passe 169/169 en 20,61 s, avec groupes candidat et
runtime recouvrants ; Ruff complet et ciblé passent. La revue indépendante
des 31 ressources scellées est favorable, sans qualification matérielle.
Le checkpoint `foresight-preactivation-20261011-223302-512328` restaure Brain/ERP
et 1 361 fichiers avant redémarrage. `completion-runtime-scope-20261011-v1.json`
vérifie ensuite santé, assets et GET Drive `enabled:false`. Les trois flags
séance/proactif/enrichissement restent faux ; le mode privé de qualification
n'est pas activé sur les bases canoniques.
Le navigateur du build `Yuj98_lc/BJ0BE6LI` vérifie douze critères Studio/Sources
et, dans une recette distincte, neuf contrôles de citations tableur/audio/image
dans le navigateur et trois contrôles HTTP de leurs liens originaux visibles.
Les trois liens `/v1/sources/{id}/raw` réellement visibles sont vérifiés par SHA.
Aucune génération, acquisition audio ou écriture canonique dans ces recettes.
`production-scope-preservation-20261011-v1.json` vérifie en lecture seule les
18 tables protégées et 1 340 originaux. Trois suivis évoluent sans retrait de ligne ;
leur attribution aux workers hérités reste une inférence, sans trace du thread écrivain.
La V2 de recette batch dispose de 43 simulations et 21 contrôles indépendants.
L'exécution unique sur fichiers fictifs ferme normalement en 17,04 s, avant tout
enfant STT : le guard du harnais refuse la commandline texte Windows. Un `WinError5`
lors du remplacement du heartbeat est aussi conservé ; sa cause n'est pas attribuée.
Les rapports
`legacy-batch-qualification-20261011-225143-4b925ae8/controller.json` et
`qualification.json` restent en échec ; aucun profil batch n'est qualifié sur
cette base. La correction du harnais sera revue et relancée dans un dossier neuf.
La V3 passe 51 contrôles et une revue favorable, puis refuse l'entrée du moteur
avant ML car `Popen.pid` identifie le lanceur venv Windows, tandis que l'attestation
porte un autre PID d'interpréteur ; leur lien OS n'est pas encore attesté.
Le reçu reste en échec, zéro segment,
fermeture normale en 19,2187 s, Job vide et handle fermé. La V4 relie désormais
ces identités par un nonce unique et une preuve OS avant toute approbation.
Elle passe 85 contrôles en 5,65 s, dont le VENV réel sur app/ML factices, puis
22 critères de revue indépendante ; l'ancien probe séparé n'est pas additionné.
Sa seule exécution réelle transcrit 15/15 fichiers fictifs dans
`legacy-batch-qualification-20261011-232941-971be1b2` : 360,8843 s, sortie 0,
15 enfants approuvés et liés par l'OS, Job vide, handle fermé, sans arrêt forcé
ou tardif. Qualité brute : 27/27 attentes originales propres ; bruit 2/2 et
téléphone 2/2 ; voix superposées 2/4, avec perte de consignation et du refus
client. P95 batch complet 24,855 s, comprenant processus, chargement et
diarisation ; ni latence SSE ni premier segment visible direct. Le WER littéral
propre de 24,46 % tokenise nombres/unités et ne se compare pas au WER normalisé
antérieur. Les sept contrôles de relecture/versionnement passent : brut v1
conservé en reçu QA, artefacts produit v2/v3 exacts, ancien v2 retenu et obsolète,
révision périmée refusée. Le bruit étant désormais exact, v2 change surtout
le nom d'intervenant ; v3 ajoute un marqueur QA. Aucun de ces gestes ne répare
les deux erreurs overlap et aucune validation humaine n'est revendiquée.
Zéro CR, action, tâche ou appel LLM ; profils canoniques inchangés. La revue
indépendante du résultat confirme 22 critères et les 33/35 attentes originales ;
le contrôle de conservation post-batch est favorable. Aucun matériel ni audio
ambiant n'y entre. Le Job externe protège cette recette ; le moment du retour
Popen est instrumenté, donc le comportement du Job interne legacy en production
n'est pas qualifié par ce protocole. Les poids et réglages canoniques restent
inchangés ; ces preuves portent seulement sur le batch fictif et ses versions,
sans qualification du direct industriel ou d'une réunion longue.
Le contrôle RO après fermeture, à 23:46 UTC, conserve exactement les 18 tables
protégées et les 1 340 originaux par SHA ; aucune recette n'entre au canon.
`production-post-legacy-batch-v4-20261011-234612-9dec7785.json` décrit depuis le
checkpoint 101 inputs ajoutés, sept scans et deux analyses modifiés, sans retrait
de ligne. L'attribution aux workers demeure une inférence ; les 80 tables ne
sont pas annoncées immuables. L'ancien relevé reste archivé dans le manifest.
Le complément `overlap-review-supplement-20261011-235159-9946ae89` travaille sur
une copie SQLite/métadonnées neuve, stockage vide, sans fichier audio ouvert
ou copié, modèle ou sous-processus. Ses 16 contrôles passent : brut chevauchement
2/4 conservé, insertion automatisée de la référence préannotée 4/4, version 2
relue avant validation QA puis conservée après version 3, conflit de révision
refusé sans changement. SourceID/SHA audio sont vérifiés comme métadonnées,
pas recalculés depuis les WAV. Les DB/reçus V4 sont inchangés et leurs fichiers
WAL/SHM/journal absents avant/après. Zéro CR/action/tâche/LLM ; aucune validation
humaine, amélioration STT ou nouvelle qualification industrielle.
La passe Python complémentaire brute conserve **1 948 réussis, 16 échecs, 1 ignoré** ;
les seize cas passent ensuite sous chemins courts. Quinze erreurs concernaient
des chemins de 262 caractères ; le refus de sauvegarde restant provenait de
deux fragments créés hors du stockage attendu par une autre fixture de test.
L'isolation de ces fixtures et les dernières protections de concurrence sont
qualifiées dans des suppléments séparés. Ce résultat combiné n'est pas annoncé
comme une nouvelle passe globale sans échec. Les preuves antérieures restent
conservées ; [le registre](docs/38_FORESIGHT_DELIVERY.md) donne leurs portées.
Une nouvelle passe complète de l'état final termine ensuite avec **2 051 tests
réussis, un ignoré, zéro échec/erreur**, en 1 737,79 s, sur trois processus
et un répertoire temporaire court neuf :
`logs/foresight-runtime/global-python-public-final-20261011.xml` et son reçu
`global-python-public-final-20261011-run.json`. Les tests ciblés précédents
recouvrent cette suite et ne s'ajoutent pas à son total. Le checkpoint vérifié
`backups/foresight-preactivation-20261011-202403-076435` précède le redémarrage
8001. `completion-runtime-qualification-v4.json` vérifie santé, index, SHA
des assets finaux, paramètre de format et refus 422, sans ouvrir de capture
ou lancer de génération. Le résultat PDF de production est vide : cette lecture
qualifie le contrat, tandis que les formats effectifs sont vérifiés sur fixture.
Les protections F10 et les règles historiques de transport passent 86 cas
distincts dans deux exécutions (84 et 2), dont les courses de droits et de
décision. L'isolation runtime puis mail passe 20 cas ; les cinq tests des
versions de staging qualifient aussi le fuseau UTC. Les rapports JUnit originaux
et leurs agrégats sont séparés.

Le checkpoint `backups/foresight-preactivation-20261011-190123-680964` est
restauré et vérifié : 1 361 fichiers, un fichier de rotation de log supplémentaire
depuis l'inventaire initial. `completion-runtime-qualification-v2.json` confirme
Brain/ERP `ok`, `/app/` 200 et les assets réellement référencés sous `/assets/`
par SHA. Le premier contrôle du harnais utilisait `/app/assets/` et reste
conservé avec son résultat faux. Les flags séance, proactif et enrichissement
automatique demeurent désactivés sur le canon.

`production-completion-preservation-20261011.json` confirme les 18 tables métier
vérifiées et les 1 340 originaux inchangés, sans prétendre auditer toutes les
tables ; trois suivis hérités ont évolué sans suppression. La recette UI finale
utilise les bases fictives séparées de 18003, sans moteur ni capture. La référence
Foresight choisie est publique ; aucun accès privé ni parité au pixel n'est requis
pour ce périmètre documenté, et aucune parité privée n'est revendiquée.

## Navigation et options de l’interface

L’interface épurée du 11 octobre 2026 est servie par `web/dist` sur le serveur
Agent **8001**. Les URLs `/app/projects/{id}/{rubrique}`, leurs retours navigateur
et les API restent compatibles. Le dossier projet dépliable remplace les grands
onglets horizontaux dans l’espace de travail. Le bureau historique conserve sa
navigation. L’alias métier `deliverables` ouvre désormais Documents > À remettre.

Correction de la vue Mails après essai : l’objet et une ligne expéditeur/date
précèdent directement le corps. « Détails du mail », fermé par défaut, contient
les coordonnées complètes, la réponse et l’original. Le classement est déplacé
dans le petit panneau projets ; sous 540 px, ce panneau suit le lecteur. La
navigation partage la barre Mails avec la recherche. Les vignettes utilisent les
scores du mail courant ; sans score, les destinations récentes sont indiquées
comme telles. Le repli des détails d’analyse persiste lors des mises à jour du
compteur. Le hook durable et les appels de classement, d’annulation et de
synchronisation sont conservés.

Qualification de cette correction : **519 tests React réussis dans 62 fichiers**,
TypeScript, compilation Vite et Ruff conformes. Contrôle réel sur 8001 à 670,
1915 et 320 pixels : contenu visible, coordonnées/réponse/original repliables,
lecteur avant projets sur petite fenêtre, aucun débordement ni erreur console.
Agent, Brain et ERP répondent `ok` ; page et assets répondent HTTP 200. Aucun
classement ni analyse de production n’a été lancé. Le backend étant inchangé,
la suite Python de l’épuration générale n’est pas relancée. Résultats et limites :
[qualification Mails](docs/24_UI_UX_REDESIGN.md#correction-mails-après-utilisation).

Réglages expose Général, Mails, Clients et équipe et Apparence. Autres réglages
donne accès à la recherche documentaire, aux modèles de livrables/documents
et aux sauvegardes/maintenance. Les détails de connexion, dossiers de mails et
secours local sont repliables. Un témoin accessible n’est toujours pas une preuve
de génération réussie : le détail conserve les résultats et limites des tests.

Les vues restent montées pour conserver les brouillons. Un refus de navigation
conserve la rubrique et l’URL ; les erreurs et activités réelles restent visibles.
L’arrêt du micro reste disponible dans tous les onglets et dans le bandeau global.
Les contrôles UI utilisent des fixtures, sans classement de mails ni enregistrement
réel. Compiler avec `cd web; npm run build` puis contrôler `/app/` sur 8001 ; aucun
redémarrage du backend n’est requis pour ces assets. Tests :
`cd web; npm test -- --reporter=dot`, `python -m pytest tests/ -q`,
`ruff check app backend/app tests`. Voir [le domaine UI](docs/24_UI_UX_REDESIGN.md#épuration-du-11-octobre-2026).

Qualification frontend : 512 tests complets puis 30 tests ciblés après les
derniers ajustements, TypeScript et build réussis. Ruff conforme. Recette de
consultation desktop/mobile sur 8001 sans erreur console ; `/health` confirme
Brain et ERP disponibles. Le moteur audio n’est pas prêt sur ce poste : la
transcription reste bloquée et ses diagnostics sont dans Options de l’audio.
Suite Python complète : 1 795 réussites, 1 ignoré et l’échec de classement
préexistant `test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`.
Journaux et bilan : `logs/ui-simplification-pytest.log`,
`logs/ui-simplification-frontend-final.log`, `logs/ui-simplification-validation.json`.

## Recherche unifiée

`GET /v1/search?q=...&project_id=...&source_type=all&after=2026-10-01&before=2026-10-11&offset=0&limit=25`
recherche les sources classées et connaissances actives autorisées. `project_id`
est l'identifiant **Brain** ; `source_type` accepte `all`, `email`, `document`,
`meeting`, `phone`, `knowledge`. Dates inclusives : réception pour les sources,
création pour les connaissances. Question de 2 à 500 caractères, limite de 1 à 100.

Un seul vecteur de requête est calculé via la configuration `memory`. L'index EG2
existant est ouvert en lecture ; références exactes et recouvrement de mots
complètent la similarité. La réponse inclut `items`, `total`, `has_next`,
`semantic_status`, `warnings`, `sources` et `indexed_sources`. Une panne distante
(délai maximal 20 secondes) laisse la recherche textuelle disponible avec un
avertissement explicite. Aucun LLM de génération n'est requis. Les connaissances
sont recherchées textuellement ; elles ne sont pas vectorisées par cette route.

Interface : `/app/search`. Tests ciblés :
`python -m pytest tests/test_unified_search.py tests/test_eg2_memory.py tests/test_project_access.py -q`
et `cd web; npm test -- --reporter=dot`. Détails :
[docs/20_EG2_ENGINE.md](docs/20_EG2_ENGINE.md#recherche-unifiée).

Qualification du 11 octobre 2026 : 58 tests Python ciblés de la version finale,
487 tests React, Ruff et build réussis. La suite globale, lancée avant les
derniers ajustements puis complétée par les contrôles ciblés, termine avec
1 786 réussites, 1 ignoré et l'échec préexistant
`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`.
Recette réelle sur 8001 : EG2 accessible, 897 sources indexées, référence exacte
et recherche de retard de livraison, ouverture du texte et lien vers l'original.
Les 11 projets Brain/ERP, 1 410 sources et 2 345 connaissances sont conservés ;
rattachements et statuts des sources comparés à la sauvegarde, inchangés.
Preuves et sauvegardes : `logs/search-activation-20261011-123128/`.

État de référence du **11 octobre 2026**, dans le projet canonique `C:/Agent`.
Agent sert Brain, ERP, CDC et l'interface sur **8001** ; XPilot sur **8000** reste
externe et préservé. Les comptes rendus datés ci-dessous décrivent leurs étapes
historiques ; les sections de fonctionnement courant et le
[contexte du projet](PROJECT_CONTEXT.md) font référence pour cette livraison.

## Mémoire EG2 de production

Le moteur unique est EmbeddingGemma 2 distant via LM Studio, à
`http://192.9.110.115:1234`, modèle `text-embedding-embeddinggemma-2` vérifié
chargé en GGUF **Q8_0**, vecteurs de **768 dimensions**. Les sources classées
sont découpées puis indexées dans `storage/eg2/index.db` ; le LLM de génération
configuré, `google/gemma-4-26b-a4b-qat`, rédige les réponses depuis les passages
retrouvés avec citations. Les faits,
validations et classifications restent dans les bases canoniques. Aucun LLM
n’est utilisé pour l’indexation. Aucun service supplémentaire sur ce PC : Agent 8001.

Réglages → Mémoire configure EG2 et propose un test réel. Les files de reprise,
le filtre de projet et la reconstruction sont conservés. Les passages sélectionnés
et citations sont transmis sans coupure en caractères.
Migration du 11 octobre 2026 : 897 sources classées, 16 180 passages, zéro
indexation en échec. Les sources, connaissances, décisions et provenances ont
été comparées à la sauvegarde avant remise en service : aucune modification.
Sauvegarde complète : `C:/AgentBackups/eg2-migration-20261011-102725`.
Agent, Brain, ERP et `/app/` vérifiés sur 8001.
Voir [architecture et exploitation](docs/20_EG2_ENGINE.md).

Réindexation avec sauvegarde, backend arrêté :
`python scripts/rebuild_eg2.py --backup C:/AgentBackups/eg2-nouveau-dossier`.
Tests : `python -m pytest tests/ -q` ; `ruff check app backend/app tests`.

## Contexte et citations de l'assistant

`POST /api/v1/brain/chat` relaie vers `POST /v1/projects/chat` dans le serveur
unique. Corps : `query`, `project_id` (identifiant Brain facultatif),
`include_evidence` (défaut true), `history` (historique de conversation facultatif).
La réponse fournit `answer`, `citations`, `warnings`, `projects_queried`,
`projects_in_context` et `engine`. Le flux `/v1/projects/chat/stream` expose la
même préparation de contexte puis la génération en SSE.

L'assistant combine les connaissances canoniques retenues avec les passages EG2
retrouvés, filtrés par projet, source résolue et version actuelle du texte.
La sélection classe les extraits et répartit le contexte entre projets, dans la
limite de huit éléments par niveau. Une sélection partielle ou un rappel dégradé
est signalé : aucune exhaustivité du corpus n'est garantie. Les passages
sélectionnés, le contexte transmis et les citations ne sont plus tronqués selon
une limite arbitraire en caractères ; la fenêtre du modèle reste applicable.

Les références `[V1]` désignent les informations retenues, avec `validation_mode`
distinguant rétention par défaut et confirmation humaine. Les références `[P1]`
désignent les preuves proposées. Les citations sont construites côté serveur
depuis les extraits réellement transmis ; une référence présente ne certifie pas
à elle seule l'interprétation faite par le LLM. L'historique de conversation aide
à comprendre la demande, sans servir de preuve pour la question courante.

Le panneau conserve la lecture Markdown, les extraits consultables et la reprise
d'une demande échouée. Les dimensions, la saisie et les contrôles de rendu sont
détaillés dans la section Validation reproductible.

## Qualification du 11 octobre 2026

Contrats EG2 finaux : **6/6**. Suite React : **481 tests réussis**, puis les deux
nouveaux tests du formulaire Mémoire réussis séparément. Build et Ruff conformes.
Suite Python globale : **1 777 réussis, 1 ignoré, 1 échec**, en 2 169,90 secondes.
L'échec préexistant
`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`
concerne une règle de classement des mails non modifiée par cette migration.
La suite globale a démarré avant les dernières retouches ; les contrats EG2 et
les chemins chat, mémoire, reprise et archives ont été revérifiés par les tests
ciblés sur les fichiers finaux. Il n'y a donc pas de réussite globale sans réserve.

Après remise en service, `/health` a confirmé Agent, Brain et ERP et `/app/` a
répondu 200. Le test réel EG2 a confirmé indexation, rappel et nettoyage dans un
index temporaire ; un chat réel a répondu avec des références présentes dans le
contexte. Le bilan d'analyse de tous les projets et la qualité de chaque future
réponse LLM ne sont pas certifiés par ces contrôles.

Mesures de la migration : 21,6 minutes de réindexation avec reprise,
280,87 Mio d'index. Instantané du backend entier après chat : 211,73 Mio de RAM,
pic processus observé 524,85 Mio ; chat réel 13,985 secondes. Ces mesures incluent
ERP et workers et ne mesurent pas EG2 isolément. RAM/VRAM du serveur distant non
mesurées. Voir [les preuves et limites](docs/20_EG2_ENGINE.md).

## Secours IA local LM Studio

Agent conserve le serveur distant comme IA principale. En cas de connexion refusée,
délai réseau dépassé ou erreur HTTP 502/503/504, les appels texte, JSON, classement
et flux avant le premier fragment basculent sur le modèle local configuré. Le retour
au serveur principal est vérifié lors du prochain appel après 30 secondes.
Les erreurs de configuration, refus 401/403 et réponses invalides restent visibles.

Depuis le 12 octobre, une génération principale réussie et non vide déclenche
une décharge asynchrone du modèle de secours. Un port TCP ouvert ou la liste
des modèles ne suffit pas. Texte, JSON, classement, flux terminé et test manuel
principal utilisent ce même mécanisme ; un flux annulé ou partiel n'y déclenche
aucune décharge. Les générations locales réservent le moteur avant son chargement.

La décharge attend le moteur local jusqu'à 420 secondes, sans interrompre les
requêtes en cours. Les alias loopback partagent cette réservation. Elle vise
uniquement les `loaded_instances[].id` de la clé `fallback_model`, via
`POST /api/v1/models/unload`, puis vérifie leur absence. Le serveur LM Studio
et les autres modèles restent disponibles. Une nouvelle panne ou un changement
des réglages annule une attente devenue obsolète. Un principal lui-même local
ne déclenche pas cette décharge.

`GET /v1/settings/ai/routing` expose `local_model_release.state` : `idle`,
`waiting`, `unloading`, `unloaded`, `cancelled` ou `error`. Un échec est journalisé
sans corps fournisseur ni clé ; après 30 secondes, une nouvelle réponse principale
utile permet une reprise. Les applications externes ne sont pas observées par
la réservation Agent. Tests isolés : `tests/test_ai_recovery_unload.py`.

Validation du 12 octobre : décharge réellement observée après une réponse « OK »
du principal sur 8001, 18 nouveaux tests et 29 tests existants réussis, Ruff conforme.
La suite globale termine avec 2 158 réussites, un échec d'isolation du test de
tick proactif et un ignoré. Après reproduction de l'ordre fautif et correction
du seul test, les 99 contrôles liés passent ; le code de production est inchangé.
Le [bilan final](logs/llm-recovery-global-20261012-105917/final-verification.json)
conserve la passe globale et cette reprise séparément.

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

## Analyse périodique des connaissances projet

Le worker est activé dans le serveur unique. Il attend 30 secondes de disponibilité
IA pour traiter ses lots et programme un passage 48 heures après le dernier bilan
réussi. `AGENT_PROJECT_KNOWLEDGE_ENABLED=0` le désactive ; l'intervalle se règle
avec `AGENT_PROJECT_KNOWLEDGE_INTERVAL_HOURS` (48 par défaut, minimum 1).
Les premiers lots et le panneau ont été vérifiés ; aucun bilan complet de tous
les projets n'est annoncé. Voir [couverture et limites](docs/35_PROJECT_KNOWLEDGE_ANALYSIS.md).

État et bilan : `GET /api/v1/projects/{project_id}/knowledge-analysis?offset=0&limit=20`.
Lecture seule, contrôle du périmètre opérateur, limite maximum 50. Le cockpit
affiche état, progression, dernier bilan, prochain passage, propositions et preuves.
La table ERP `project_knowledge_analyses` persiste curseur, lot de connaissances,
travail intermédiaire et bilan. Un arrêt reprend le lot non enregistré ; une
réponse vide/invalide échoue et sera reprise après 15 minutes. Si les connaissances
ou le CDC changent pendant un appel, le résultat est abandonné puis recalculé.
L'ancien bilan reste consultable et est indiqué périmé si ses entrées ont changé.
Les dates canoniques, statuts CDC et validations humaines ne sont pas modifiés.

## Supervision du backend

`start-agent.cmd` et `start-agent-task.cmd` démarrent désormais le superviseur
`scripts/agent_runtime.py` en arrière-plan, sans console persistante. Le raccourci
Windows existant `Agent-Backend.lnk` utilise déjà le second lanceur : la supervision
sera donc également lancée à l'ouverture de session. Aucun nouveau port.

```powershell
python scripts/agent_runtime.py start
python scripts/agent_runtime.py status
python scripts/agent_runtime.py stop
```

Le superviseur relance Uvicorn après toute sortie du processus, même avec code 0.
Délai : 5 secondes, puis 10/20/40/60 secondes si les démarrages échouent rapidement.
Une exécution de plus d'une minute réinitialise ce délai. Un verrou système évite
deux superviseurs ; un port 8001 déjà occupé est attendu sans arrêter son processus.
`stop` demande l'arrêt du superviseur et de son propre backend ; un serveur lancé
manuellement doit être arrêté séparément. Fermer le navigateur ne stoppe pas Agent.
Lancer directement `python -m uvicorn` contourne cette supervision.

Les journaux `logs/runtime/supervisor.log`, `backend.out.log`, `backend.err.log`
conservent les arrêts, codes de sortie et erreurs de démarrage. Le journal du
superviseur est tournant ; les sorties backend dépassant 10 Mio sont déplacées en
`.previous` à la prochaine relance. `status=running` indique un processus vivant,
pas une validation HTTP ni l'achèvement des traitements IA. Le superviseur ne tue
pas un processus vivant sur la seule base d'un contrôle HTTP lent ou en échec.
Un arrêt Windows ou une déconnexion termine la session ; le raccourci relance
Agent à la prochaine connexion. L'arrêt du superviseur lui-même n'est pas surveillé
par un second service. Aucune modification des tables ni suppression de données.

Validation isolée : `python -m pytest tests/test_agent_runtime.py -q` teste de vrais
sous-processus qui échouent, les relances, les doublons, l'arrêt volontaire et la
préservation d'un écouteur existant. Voir aussi
[les améliorations opérationnelles](docs/22_OPERATIONAL_IMPROVEMENTS.md#supervision-du-backend).

**Classement automatique courant.** Le seuil est configurable, 75 % par défaut.
Une suggestion unique de projet réel au seuil est classée avec décision et audit ;
les égalités restent à examiner. Les choix humains, les mails écartés et les
propositions contradictoires sont conservés. La reprise
`python -m scripts.auto_classify_mail --apply` sauvegarde SQLite avant classement. Voir
[le paramétrage du seuil](#seuil-de-classement-automatique-des-mails).

**Historique du 7 octobre 2026.** La première activation retenait uniquement les
suggestions à 100 %. Le seuil configurable décrit ci-dessus remplace cette règle ;
les anciennes décisions et traces d'audit sont conservées.

**Périmètre corrigé à la demande de l’utilisateur — 7 octobre 2026.** La reprise automatique de tout XPilot est arrêtée. Ne pas développer pour le moment de nouveau parcours de signature, nomenclature/BOM, système de charge/ressources, collaboration, calendrier, qualité, REX ou clôture. Le CDC existant suffit : contrôle de fonctionnement uniquement, sans extension CDC/BE. L’assistance technique L6 ne démarre pas automatiquement dans cette demande réduite. Tous les modules et toutes les données déjà présents sont conservés. Les listes larges ci-dessous décrivent désormais le plan historique ; cette décision prévaut. Documents et L0–L4 restent actifs sur le serveur unique 8001 ; aucun lot exclu n’a été activé pendant ce travail.

**CDC existant vérifié, sans nouvelle fonctionnalité.** 40 tests de régression réussis ; 40 lectures HTTP200 sur les dix projets actifs. Le moteur canonique C:/Agent a traité le CDC fictif avec google/gemma-4-26b-a4b-qat : HTTP200, 17 éléments en65.27s, 17 preuves présentes dans leurs pages selon la règle existante (espaces/casse normalisés), zéro violation FK. Quatre avertissements UNIT_MISSING sont proposés à la revue. Essai isolé : aucune analyse de projet réel, modification canonique ou extension CDC/BE ; aucun redémarrage. Preuve : `.ui-preview/xpilot-l5/cdc-existing-verification-terminal.json`.

**Documents — téléchargement final et démarrage qualifiés, actifs sur Agent 8001.** Le téléchargement des copies de lot utilise la route protégée de l’artefact après vérification du nom, de la taille et du SHA-256 ; le serveur revérifie la copie et les droits à chaque lecture. Sur projet fictif, un lecteur a enregistré une copie de lot et un propriétaire une copie individuelle : les deux fichiers présents dans Downloads correspondent exactement à l’empreinte affichée ; sources et cellules ERP historiques conservées. 456 tests React, 17 tests API/worker, TypeScript et build passent. Les 280 sources Python/contrats restent identiques à la qualification complète 1688 réussis / 1 ignoré. Les lanceurs CMD activent le worker documentaire si AGENT_DOCUMENT_JOBS_ENABLED est absent, et respectent une valeur explicite telle que 0 ; lancement Windows sans fenêtre vérifié dans les deux configurations sur bases fictives. Les chemins réels des trames et des sorties restent à fournir/configurer et le partage SMB réel n’est pas qualifié. Aucune nouvelle fonction reportée ni modification de données réelles. Publication sélective sauvegardée ; build servi et 30 lectures HTTP vérifiés sur dix projets. Recette visuelle de la version active sans erreur console, worker disponible et besoin de configuration réseau visible. Aucun redémarrage ni écriture de base pendant cette publication ; aucun commit/push. Preuve : `.ui-preview/xpilot-l5/document-download-v1/delivery-result.json`.

**Notes activées sur Agent 8001 — ERP10.** Projet → Documents → Notes permet la saisie riche, les brouillons, l’historique, les pièces jointes et les imports explicitement choisis. Qualification complète : 1 688 tests Python réussis / 1 ignoré, 456 React, TypeScript, Ruff et build conformes ; 60 lectures HTTP sur dix projets et recette navigateur de consultation et rechargement sans erreur console. Le serveur part de C:/Agent ; les corrections récentes LLM/mémoire sont conservées. Avant migration : sauvegarde coordonnée du dernier état puis restauration sur copie neuve, 1 419 fichiers vérifiés. La migration préserve exactement les cellules historiques ; après redémarrage, les différences contrôlées concernent uniquement la progression technique du worker de jalons préexistant et l’horodatage du dernier signal Thunderbird. Le contenu de cet état hors last_seen et toutes les autres cellules Brain historiques sont identiques. Aucune note de recette créée dans les projets réels. Les chemins réseau des modèles et copies restent à fournir/configurer ; la préparation documentaire réelle sur SMB et son téléchargement final ne sont pas encore qualifiés. Tous les parcours exclus par l’utilisateur restent reportés. Aucun commit/push. Preuve : `.ui-preview/xpilot-l5/notes-erp10-integration-v1/delivery-result.json`.

**Historique UI — pièces jointes et import avec aperçu qualifiés dans le worktree, non activés.** L’écran ajoute copie explicite de pièces, association à la note et insertion des images gérées. L’import accepte des fichiers, le dossier complet d’une note XPilot ou une seule note choisie dans un lien du projet. Aperçu des versions, confirmation manuelle, explication des contenus incompatibles et choix explicite du texte simple ; aucun HTML source exécuté. Originaux, historique et auteurs source restent conservés ; Office demeure en consultation. Une commande exacte est conservée avant envoi ; POST `/notes/imports/replay` vérifie une confirmation sans réacquérir la source ni créer de doublon. GET `/notes/{id}/source` expose désormais le descripteur et l’inventaire des originaux. Recette navigateur sur données fictives : copies et image réellement enregistrées, imports réseau local et dossier multipart, 17 originaux vérifiés octet pour octet, téléchargement Office réel identique, rechargement et largeurs390/650 sans débordement ni erreur console. 456 tests React (18 cas de transfert),86 Python ciblés, TypeScript, Ruff et build passent. La suite Python complète de l’arbre courant, le démarrage protégé et l’activation Notes restent à terminer ; SMB réel et ouverture dans Office ne sont pas qualifiés. Les lots exclus restent reportés ; aucune base réelle, code canonique, module existant ou port8000 modifié, aucun commit/push. Preuve : `.ui-preview/xpilot-l5/notes-transfer-ui-qualified.json`.

**Historique avant transfert dans l’interface — édition, enregistrement et reprise qualifiés dans le worktree, non activés.** Documents reçoit un onglet Notes chargé à la demande ; les liens réseau et la préparation de documents restent accessibles. Liste recherchable/paginée et éditeur de contenu fermé : titres, cinq styles, liens sûrs, couleurs, alignements, listes/cases, tableaux et images gérées. Aucun HTML source ni image externe n’est rendu. Après une pause de saisie, la note existante est enregistrée avec un état visible ; la création reste explicite. Le brouillon local est isolé par projet/note/opérateur et les commandes exactes sont conservées avant envoi. Frappes pendant la sauvegarde, réponse perdue, rechargement, conflit et rejeu suivi d’une modification tierce conservent la saisie ; une création confirmée reste la même si le stockage local devient indisponible. Une capture locale illisible est conservée ; quota indisponible est annoncé, export et reprise sont proposés. Historique paginé avec aperçu, liaisons d’images courantes et restauration en nouvelle version ; pièces existantes téléchargeables, lecteur et Office en consultation. 438 tests React (dont19 Notes),73 Python ciblés, TypeScript/build et Ruff passent. Recette navigateur isolée : gras/cases/tableaux réellement persistés, restauration, conflit de deux opérateurs, lecture après rechargement, largeur390 sans débordement et fichier de brouillon réellement exporté. Ajout de pièces et import volontaire dans l’interface, consultation des originaux, qualification complète du backend, raccordement du démarrage et activation Notes restent à terminer. Aucun endpoint Notes enregistré sur8001, aucune base réelle modifiée, aucun lot exclu repris, commit/push ou suppression. Preuve : `.ui-preview/xpilot-l5/notes-ui-core-qualified.json`.

**Historique avant interface — transport Notes qualifié.** Le transfert v9 conserve toutes les versions, pièces (même non encore liées), images et originaux importés. Identifiants et liaisons courants sont remappés séparément ; captures, empreintes, acteurs et commandes historiques restent inchangés. Un double aller-retour est qualifié, également avec formulaires/lots documentaires et Brain. La préparation durable utilise des fichiers de notes neufs sans adopter les copies abandonnées ; échec SQL conserve les deux bases existantes et les pièces préparées. Les formats v2–v8 restent compatibles et refusent les tables de notes hors v9. La sauvegarde globale contrôle schéma, captures et fermeture binaire hors ligne avant restauration dans un dossier neuf ; elle conserve les originaux et gèle les anciennes commandes sans acquisition réseau ni import runtime. Lecture par note, indépendante de la limite d’un ZIP projet. 115 puis92 tests ciblés passent (groupes se recouvrant), Ruff conforme. La full1529 est historique et ne qualifie pas l’arbre courant. Interface/éditeur/autosave, recette complète, installation et activation Notes restent à faire. Aucun changement de C:/Agent, base de production ou frontend ; aucun lot exclu, commit/push ou suppression. Le périmètre corrigé le7octobre prévaut toujours. Preuve : `.ui-preview/xpilot-l5/notes-v9-global-qualified.json`.

**Historique avant raccordement v9/global — notes internes.** Acquisition réseau explicitement sélectionnée, contrat de graphe pur, référence courante de version restaurée et fermeture binaire des pièces/originaux sont implémentés dans le worktree. Le validateur hors ligne relit tous les originaux retenus en mémoire, recalcule les conversions et les titres source, vérifie MIME/images et refuse les historiques incomplets. 145 puis 142 tests ciblés passent, avec recouvrement ; Ruff conforme. La full1529/1 ignoré est historique et précède ces ajouts. Quatre tables/douze protections restent dormantes. Raccordement archivev9/sauvegarde globale, éditeur/autosave et activation restent à faire ; ils ne sont pas annoncés comme livrés. Aucune modification de C:/Agent, suppression, migration de production, opération XPilot8000 ou commit/push. Preuve : `.ui-preview/xpilot-l5/notes-network-history-binary-current.json`.

**L5.4 — import téléversé entièrement qualifié, encore dormant.** Session35232/PID17716 terminée exit0 :1529tests Python réussis/1ignoré,2165.89s, 263hashes produit/tests exacts, Ruff conforme. HTML effectif, images intégrées, capture source immuable, copies originales et reprise multipart sont inclus. Les46cas du prototype réseau et le contrat d’archive préparé restent séparés, hors de cette suite. Le processus est terminé : ne plus le reprendre/recréer. Raccorder réseau, références de restauration portables, archivev9/restauration globale et éditeur/autosave avant qualification finale/activation. Documents/ERP9 restent actifs sur8001, notes dormantes. L5.5–7 etL6–L9 restent au périmètre ; aucun changement canonique, suppression, commit/push. Preuve : `.ui-preview/xpilot-l5/notes-import-full-terminal.json`.

**L5.4 — acquisition réseau de notes préparée et qualifiée hors sources figées.** Trois fichiers de recette ajoutent sélection explicite d’un fichier HTML/TXT/MD/Office ou du dossier complet d’une seule note moderne depuis un lien de ce projet, avec racines et mappings serveur. Pas de recherche dans les autres projets ni d’import de base XPilot. Droits et lien sont vérifiés avant les probes ; handles Windows, identité native et vérification finale couvrent tous les fichiers et dossiers retenus. Jonctions/redirections, éléments inconnus, historique vide/incomplet, sources modifiées et quotas dépassés empêchent tout résultat partiel. La correction Windows utilise lstat frais plutôt que les métadonnées d’énumération en cache. Deux endpoints JSON de recette proposent aperçu et import ; la commande validée se rejoue même sans configuration réseau, avant acquisition. 46tests réussis, Ruff/diff conformes, sur liens et fichiers fictifs Windows ; SMB réel non qualifié. Le prototype reste dans `.ui-preview/xpilot-l5/notes-network-stage/`, hors des263sources inchangées de la full35232/PID17716 toujours en cours. Ne pas la relancer sur délai. Aucun endpoint réseau de note disponible sur8001. Raccordement, archivev9/restauration, éditeur/autosave, qualification et activation restent requis, ainsi que L5.5–7 et L6–L9. Aucun changement canonique, suppression, commit/push. Preuve : `.ui-preview/xpilot-l5/notes-network-stage46-progress.json`.

**Régression complète de l’import en cours : session35232, PID17716.** Les263sources produit/tests sont figées dans `.ui-preview/xpilot-l5/notes-import-full-running.json`. Conserver ce processus jusqu’au résultat terminal ; ne pas le relancer sur un délai d’observation. Le rapport attendu est `notes-import-full-python.xml`. Aucun résultat complet acquis, aucune activation des notes. Les anciennes sessions10312 et65938 sont terminées et ne doivent pas être reprises.

**L5.4 — import de notes implémenté en recette interne, encore dormant.** La conversion utilise le HTML effectivement sauvegardé par XPilot, conserve le JSON ancien parmi les originaux et couvre barré, cases, tableaux, images dataURI décodées et anciens fichiers HTML/TXT/MD. Quatre tables et douze protections SQL conservent contenu, versions, pièces et provenance. La sélection volontaire multipart propose aperçu, import et téléchargement des originaux sans rendu HTML ; tous les octets et toutes les versions déclarées sont copiés et vérifiés, sans extraction ni écrasement. Les auteurs source restent descriptifs ; les captures Agent portent l’opérateur serveur et les anciennes commandes de versions sont gelées. Une commande validée se rejoue avant acquisition, sans doublon ; annulation/échec conserve les copies et les retries ne les adoptent pas. Office reste en consultation, également protégé en SQL. Qualification ciblée : groupes de162 puis38cas réussis, se recouvrant, Ruff et diff conformes. Le résultat complet1408/1 ignoré concerne l’état précédent et ne qualifie pas ces ajouts. Acquisition réseau bornée, transportv9/restauration globale, éditeur/autosave, régression complète et activation restent à réaliser. Aucun endpoint notes/import enregistré sur8001 ; Documents/ERP9 restent actifs. Aucun changement canonique, suppression, commit/push. Preuve : `.ui-preview/xpilot-l5/notes-import-progress.json`.

**7 octobre 2026 — Documents L5.1–L5.3 activés sur Agent 8001, ERP9.** Catalogue, formulaires versionnés, préférences, lots et publication explicite sont raccordés ; le worker documentaire est actif (`AGENT_DOCUMENT_JOBS_ENABLED=1`). Les dossiers des trames et des copies restent à fournir/configurer : l’écran signale cette limite et les fichiers Office réels restent inaccessibles. Qualification : 1356 Python / 1 ignoré, 419 React, Ruff, TypeScript et build conformes ; 50 lectures HTTP sur dix projets et recette de consultation/rechargement sans erreur console. Sauvegarde coordonnée/restauration sur dossier neuf : 1397 fichiers vérifiés et 125896 cellules contrôlées. La migration conserve exactement les cellules historiques ; après redémarrage, seules vingt cellules de progression du worker de jalons préexistant changent, sans modification des données métier historiques. Le geste final de téléchargement navigateur et le partage SMB réel restent non qualifiés. L5.4–7 (notes, comptes, visas et recette complète) et L6–L9 restent à réaliser ; aucun commit/push. Preuve : `.ui-preview/xpilot-l5/integration-erp9-v1/delivery-result.json`.

Les lots L0–L4, Documents et Notes sont actifs sur le serveur unique `8001` avec ERP10. Comptes/visas et les autres fonctions exclues restent reportés. Les racines des trames et des sorties doivent encore être configurées. Le lancement direct par Uvicorn nécessite `AGENT_DOCUMENT_JOBS_ENABLED=1` ; les lanceurs CMD le renseignent si absent et conservent toute valeur explicite, notamment `0` pour désactiver le worker.
Les verrous de dépendances ajoutent ReportLab 4.5.1 et ses dépendances PDF en
préservant toutes les versions existantes ; la qualification utilise un dossier
PDF de recette isolé, sans modifier le Python ni les données du serveur actif.
Le cockpit prépare des lectures indépendantes dans
`/api/v1/projects/{id}/cockpit`, `/items/tasks`, `/items/deliverables` et `/alerts`.
Recherche normalisée/littérale, pagination bornée, compteurs complets, lecture
neutre, contrôle des relations et détection des révisions mélangées ; les mutations
restent les commandes L2/L3. Les heures reprennent les règles portefeuille/planning.
Qualification cockpit antérieure : 752 tests Python réussis (un ignoré), 277 React, Ruff,
TypeScript et build conformes ; preuve `.ui-preview/xpilot-l4/cockpit-result.json`.
La recette fictive HTTP/browser est distincte de `C:\Agent:8001` ; les nouvelles
routes restent non enregistrées dans le serveur actif. Sur 100 jalons, 5 000 tâches
et 2 500 livrables, lectures et commandes HTTP mesurées restent sous 1,5 s.
La recette confirme clavier, rafraîchissement après création, édition des dates,
accès aux preuves, fiche/équipe conservées et inspecteur empilé sur petit écran.

La rubrique Réunions & revues prépare maintenant l'interface RLP, séparée des
comptes rendus/audio conservés : participants du répertoire/de l'équipe ou externes,
jalon et livrables paginés, sections structurées et relecture explicite. La saisie
reste présente entre vues et après un conflit ; la comparaison à trois versions
applique uniquement les changements choisis, puis exige un enregistrement.
Les réunions admissibles sont lues par `/reviews/recording-choices`, sans télécharger
les transcriptions de toute la liste. Une source choisie est ouverte puis révalidée
à l'import. `/reviews/{review}/history/{event}` expose le contenu avant/après dans
la portée de cette revue. Les publications affichent les noms capturés et le PDF
n'est proposé qu'après contrôle SHA-256 côté navigateur. Les signatures attendues
restent à recueillir ; aucun visa électronique n'est créé par cet écran.
Qualification UI : 292 React, TypeScript/build et 31 tests RLP ciblés. Recette réelle
sur bases fictives : import, relecture, gel/PDF, nouvelle révision, historique,
maintien de la saisie entre vues et conflit planning/RLP résolu explicitement.
À 390 px demandés, fiche de 342 px sans débordement. Preuve :
`.ui-preview/xpilot-l4/rlp-ui-evidence.json`. Le transport v6 et la restauration
coordonnée sont raccordés sur copies. Les liens API/UI et la qualification/
activation globale restent à terminer.

Le [lot L3 Livrables](docs/32_XPILOT_PROJECT_DELIVERABLES.md) est qualifié et actif
dans `C:\Agent` sur `8001`. La liste, les visas, les versions, le catalogue dans
Réglages et les contrôles des jalons partagent les révisions et droits du serveur.
Le candidat passe 706 tests Python (un ignoré), 267 React, Ruff, TypeScript/build.
La sauvegarde complète pré-L3 est dans
`C:/Agent/logs/xpilot-l3-activation-20261006-190820/full-state-before-l3` : 1 397
fichiers vérifiés, restauration sur copie, conservation des 2 098 lignes ERP
(17 429 cellules) et 13 144 lignes Brain (108 134 cellules) à la migration.
Les dix projets historiques et les routes/bundle sont contrôlés sur le serveur.
Preuve : `.ui-preview/xpilot-l3/integration-1006-v2/delivery-result.json`.
Les paragraphes de qualification historique ci-dessous décrivent les étapes
intermédiaires ; L4–L9 restent à intégrer.
La réflexion des contraintes de planning utilise une connexion unique pour
éviter une lecture incohérente après création des tables avec un pool SQLite.
Les contraintes et protections d'historique restent toutes exigées.
Qualification du raccordement backend L3.3 : 702 tests Python réussis, un ignoré,
dont 36 cas HTTP/fichiers et 13 cas de compatibilité, jalons et démarrage.
Ruff conforme ; conservation des 1 456 lignes/12 939 cellules ERP vérifiée sur
copie sauvegardée. Preuve : `.ui-preview/xpilot-l3/registered-integration-result.json`.
L'interface `ProjectDeliverablesPanel.tsx` du worktree reprend Projets → Planning
→ Livrables. Liste filtrée/paginée et formulaire libre partagent les API L3 ;
les modifications de fiche et du statut de travail gardent leurs révisions et
leurs brouillons. La comparaison prépare explicitement une nouvelle sauvegarde.
`DeliverableChecklist.tsx` ajoute recherche/pagination, création de points,
préparation et visas avec preuve humaine. `DeliverableValidation.tsx` propose
soumission, validation, réouverture et archivage explicites sur la dernière
version. Une révision concurrente conserve le brouillon ; le vérificateur doit
confirmer à nouveau avant de reprendre un visa. Les points obligatoires ne
peuvent être désactivés, les documents validés/archivés verrouillent la checklist
et le profil lecteur consulte sans commande. Les heures de preuve SQLite UTC
sans suffixe s'affichent à l'heure locale sans modifier les données stockées.
`DeliverableVersions.tsx` ajoute les versions paginées, publication locale (50 Mio
maximum), copie depuis un lien réseau du projet ou livraison CDC exacte, édition
des seules métadonnées et lecture du manifeste immuable. Toute publication garde
la préparation, retire les visas obligatoires et revient au brouillon.
`DeliverableHistory.tsx` affiche le journal paginé et ses preuves avant/après.
Les téléchargements restent bornés à 60 secondes et annulables ; un lien explicite
conserve le Blob vérifié quand le navigateur bloque l'action automatique.
`DeliverableSelection.tsx` propose catalogue/publis paginés, versions exactes,
choix explicites de jalons/exclusions, cible existante facultative et désélection
conservant les données. L'application reprend exactement les entrées capturées
avec l'empreinte serveur de l'aperçu. Un choix modifié ou une erreur retire aperçu
et confirmation ; la comparaison prépare un nouvel aperçu sur la révision actuelle.
Le profil lecteur calcule un aperçu sans commande d'application. Une version de
type différente de celle du projet ne remplace jamais sa checklist silencieusement.
Réglages → Livrables charge à la demande `DeliverableSettings.tsx` : catalogue,
publications et composition par typologie. `DeliverableDefinitionEditor.tsx`
édite dix contrôles par page et conserve les conditions inconnues/archivées.
L'API GET `/api/v1/deliverable-types/condition-typologies` expose les codes
conditionnels normalisés du serveur, avec recherche, pagination et portée du
lecteur ; aucune création implicite ni modification de référentiel.
Les commandes de catalogue restent réservées au propriétaire global. Création,
publication, métadonnées et composition exigent une confirmation ; un conflit
conserve la saisie et impose comparaison/préparation puis reconfirmation.
Les lectures sont annulables, les commandes attendent leur résultat et verrouillent
la navigation pendant leur exécution. Les publications utilisées par les projets
restent immuables.
`MilestoneDeliverableGates.tsx` expose les blocages et les liens vers leur contrôle
exact dans Planning → Jalons. GET
`/api/v1/projects/{project_id}/deliverable-plan/milestones/{milestone_id}/gates/page`
fournit une page descriptive de 1 à 200 contrôles, filtrée par défaut sur les
blocages ; `include_ready=true` affiche aussi les visas obtenus. Les compteurs et
`can_validate` évaluent toujours tous les contrôles requis, même hors de la page.
La route existante `/gates` et la garde transactionnelle restent inchangées.
La saisie des dates est conservée lors du passage au livrable ; revenir au jalon
relit les visas et exige comparaison/préparation si la révision a changé.
Seul le changement explicite du workflow vers Validé exige ces visas côté UI ;
la date réelle seule conserve sa portée indépendante. Le backend arbitre toujours
les droits, révisions et visas au moment de la commande.
Tests de cette étape : `web/src/components/ProjectDeliverablesPanel.test.tsx`,
`DeliverableChecklist.test.tsx`, `DeliverableValidation.test.tsx` et
`web/src/lib/projectDeliverables.test.ts` ;
suite React complète, TypeScript/build et recette isolée à 390/650/1280 pixels.
Qualification historique checklist/validation : 702 tests Python réussis, un ignoré,
195 tests React réussis (40 cas Livrables), TypeScript/build/Ruff conformes.
La recette fictive à 18232 couvre notamment le conflit réel et la reconfirmation
du visa ; sa preuve est `.ui-preview/xpilot-l3/ui-checklist-result.json`.
Qualification historique versions/historique : 702 tests Python réussis, un ignoré,
219 tests React (64 cas Livrables), TypeScript/build/Ruff conformes. La recette
fictive à 18233 vérifie publications, conflits réels, perte des visas avec préparation
conservée, 44 événements et refus d'un fichier corrompu sans perte du brouillon.
Les 31 fichiers et manifestes ont leurs empreintes vérifiées ; la copie CDC conserve
les octets exacts. À 390/650/1280 pixels, aucun débordement horizontal du document.
Limite de recette : les captures de téléchargement du navigateur intégré expirent
sur les liens Blob ; aucun fichier effectivement sauvegardé par le navigateur n'est
revendiqué. Le lien préparé et les octets HTTP sont vérifiés. Preuve et reste à faire :
`.ui-preview/xpilot-l3/ui-files-result.json`. La recette est fermée ; les fichiers
fictifs et leurs copies sont conservés. Le serveur actif reste L2 sur 8001.
Qualification courante sélection : 234 tests React (79 cas Livrables), puis 37
tests ciblés après ajout des jalons nommés/exclusions dans l'aperçu ; TypeScript,
build et Ruff conformes. La recette fictive à 18234 confirme pagination 27 types,
choix d'une publication ancienne, blocages, adoption, conflit réel 5→6,
désélection 7 puis resélection 8. La fiche, le fichier exact, trois contrôles et
la préparation/commentaire antérieurs restent conservés ; aucun visa automatique.
La suite Python complète confirme 702 réussites, un test ignoré ; la qualification
est enregistrée dans `.ui-preview/xpilot-l3/ui-selection-result.json`.
Qualification historique catalogue : **255 tests React**, dont 99 cas Livrables,
**704 tests Python réussis, un ignoré**, TypeScript/build/Ruff conformes.
La recette fictive vérifie V1 conservée, conflit de publication, archivage/réactivation,
conflit de composition et retrait indépendant du collègue conservé. Les 45 tables
hors catalogue/référentiels (24 lignes / 186 cellules) et le fichier original
restent identiques ; aucune violation FK. Les anciens types/publications/événements
sont conservés. La nouvelle lecture des codes de condition ne change ni schéma,
ni archives, ni restauration ; la suite complète requalifie le backend modifié.
Preuve : `.ui-preview/xpilot-l3/ui-catalogue-result.json`. Le serveur actif reste L2.
Qualification courante des liens de jalons : **267 tests React**, **706 tests
Python réussis, un ignoré**, TypeScript/build/Ruff conformes. Les 52 tests ciblés
API/intégration couvrent notamment la pagination, les noms/version et la portée
sans écriture. Recette fictive à 18235 : contrôle exact, visa humain 6→7,
comparaison du jalon, saisie conservée, validation 7→8 ouvrant le successeur sans
dater sa réalisation ; publication indépendante 8→9 retirant le visa et gardant
la préparation, V1 et les dates. Les 41 autres tables restent identiques
(12 lignes / 78 cellules) ; aucune violation FK. Les trois largeurs de recette
390/650/1280 ne débordent pas horizontalement. Preuve :
`.ui-preview/xpilot-l3/ui-gates-result.json`. Cette extension ne modifie ni DDL,
ni formats d'archives. L'enregistrement navigateur, considéré non qualifié lors
de cette recette, est désormais confirmé par les fichiers réels dans
Téléchargements : `plan-reseau.txt` et `manifest-v31.json` correspondent aux octets
et empreintes de V31 dans la base fictive. Des copies sont retenues dans
`.ui-preview/xpilot-l3/verified-browser-downloads-1006`. Preuve :
`.ui-preview/xpilot-l3/saved-download-result.json`. Les observations des événements
navigateur avaient expiré, mais les fichiers avaient bien été sauvés. L3.5 est
qualifié ; L3.6 reste en cours pour fusion, restauration et activation.
Au contrôle final, 8001 était arrêté (aucun serveur/écoute et connexion refusée).
La version L2 installée a été relancée dans `C:\Agent` : démarrage terminé, santé
`ok`, aucune route L3 active. Journal :
`C:/Agent/logs/runtime-l2-catalogue-check-20261006-181849-190.err.log`.
Le contexte serveur peut associer un éditeur à une personne avec
`AGENT_OPERATOR_PERSON_ID` pour le visa du vérificateur désigné. Ce champ ne
provient jamais d'une commande HTTP. Les tests du socle sont dans
`tests/test_project_deliverables.py`. L'interface et le candidat fusionné L3 sont
désormais qualifiés et actifs sur le serveur unique `8001`.
Le service `deliverable_catalogue.py` propose administration/versionnement,
composition des typologies et aperçu/application de sélection. Les tests sont
dans `tests/test_deliverable_catalogue.py`. Aucun type ni projet n'est créé à la
lecture ; les paramètres de modification exigent révision et empreinte d'aperçu.
La sélection garde les checklists/fichiers et les fiches manuelles. Les profils
de portée prennent aussi en compte les responsables/vérificateurs des livrables.
Le service de sauvegarde globale prépare la portabilité L3 : liaisons
`deliverable_files` vérifiées par version/projet, SHA-256 et taille, puis
relocalisation dans `project_deliverable_version_metadata.storage_path` sur la
copie restaurée. Le chemin original de la version publiée reste immuable. Une
ancienne sauvegarde peut retrouver les pièces par leur empreinte exacte. Les
fichiers absents, altérés ou hors stockage géré refusent une sauvegarde complète.
Les essais sont dans `tests/test_deliverable_backup.py` ; l'ajout de la colonne
aux schémas L3 antérieurs exige une sauvegarde avant DDL et reste idempotent.
Le transport sélectif v5 est raccordé et actif sur le serveur Agent.

Les adaptateurs `backend/app/routers/project_deliverables.py` sont enregistrés
dans `app.main` du serveur actif, testés avec les commandes historiques et les
droits du mono-serveur sur bases fictives. Préfixes : `/api/v1/projects/{id}/deliverable-plan`,
`/api/v1/deliverable-types` et `/api/v1/project-references/{id}/deliverable-types`.
Ils exposent listes paginées, catalogue versionné, sélection avec aperçu,
checklists, transitions, métadonnées, événements et téléchargement de fichiers
et manifestes. Pagination : 1 à 200 résultats ; recherche littérale sans
distinction de casse/accents. Les agrégats de page évitent une requête par livrable.

Les versions s'acquièrent par `versions/upload` (multipart : fichier, révision
attendue, référence, commentaire), `versions/network` (lien enregistré dans le
projet et chemin relatif) ou `versions/cdc` (livraison originale du même projet).
La limite est de 50 Mio. Upload et copie réseau créent une pièce distincte dans
`MINIPILOT_HOME/deliverable-files` ; ils ne réutilisent pas un fichier réseau
mutable comme version. Un lien vers un fichier autorise ce seul fichier, sans
élargir l'accès à son dossier. Une copie interrompue est conservée sans
publication ni suppression de données. Le téléchargement restitue en pièce
jointe les octets vérifiés contre SHA-256 et taille, avec `nosniff` et sans cache.
Le manifeste reste consultable si la pièce est indisponible. Ces API partagent
la révision L2 et les droits serveur. Les commandes historiques `deliverables`
acceptent une révision optionnelle, gardent leur réponse et statut opérationnel,
et enregistrent une trace immuable sans accorder de visa.

`deliverable-plan/milestones/{id}/gates` fournit les contrôles et bloqueurs avant
validation. Les chemins modernes et historiques de modification du jalon
partagent le même contrôle transactionnel avant toute ouverture du successeur.
Un visa doit porter sur la dernière version, avec preuve, acteur, date et octets
inchangés. Les gates d'un autre jalon ne bloquent pas l'étape concernée. Les
gates sans jalon spécifique s'appliquent aux étapes explicitement associées au
livrable ; les livrables désélectionnés restent conservés mais hors sélection
active. Les dates réelles ne sont jamais assimilées à une validation de workflow.

Le démarrage prévalide le schéma L3 existant avant toute DDL, puis appelle son
installateur explicite après les prérequis L1/L2. Les tables L3 sont toujours
exclues du `create_all` général. Une sauvegarde préalable unique protège la
migration ERP 7 ; une installation incompatible ou une sauvegarde échouée
arrête le démarrage. Aucun catalogue ni plan projet n'est généré à la lecture.

Recette ciblée : `python -m pytest tests/test_project_deliverable_api.py -q`.
Raccordement : `python -m pytest tests/test_project_deliverable_integration.py -q`.
Le contrat `project_deliverable_archive.py` prépare la validation des archives
v5 et le remappage typé de leurs lignes. `project_archive.py` lit désormais
v2/v3/v4/v5 et choisit v5 uniquement quand les données de livrables/composition
le nécessitent. Les manifests de fichiers v2 conservent la publication originale v1
verbatim, avec SHA-256 et identité de version source. Le parseur commun
`app/services/deliverable_manifest.py` est utilisé par le contrôle des fichiers
et la restauration globale ; vingt remappages successifs ne construisent pas
de provenance récursive. Les essais du contrat sont dans
`tests/test_project_deliverable_archive_contract.py`, dont une insertion avec
triggers actifs suivie d'une sauvegarde/restauration réelle sur copies.
Le service `project_deliverable_archive_store.py` exporte la fermeture SQL et
prépare la réutilisation des référentiels sous verrou d'import. Il ne commite pas,
ne crée pas de schéma ; le transport l'appelle avant toute pièce écrite. Le contrat doit être
validé et les références L1 réconciliées avant son appel ; `typology_ids` doit
contenir toutes les typologies utilisées, même sans composition dans la source.
La correspondance d'identifiants n'est publiée qu'après tous les contrôles.
Une définition/version, composition ou trace globale divergente bloque l'import ;
une version manquante dans un type existant exige une publication explicite séparée.
Les essais sont dans `tests/test_project_deliverable_archive_store.py`.
Le rejeu des snapshots de checklist compare les champs fixes, les preuves et
les remises à zéro lors de publication/réouverture. Il compare les dates UTC
SQLite/JSON par instant, sans réécrire les preuves. L'aperçu d'adoption montre
un bloqueur si un contrôle manuel masque un gate obligatoire, sans l'écraser.
Le module `project_archive_v5.py` sépare les actions de livrables du validateur
Planning L2, lie chaque pièce aux SHA/taille figés et prépare les empreintes de
manifests remappés avant insertion sous triggers. Les versions CDC utilisent la
pièce `delivery` ; les autres utilisent `deliverable`. Seules leurs métadonnées
reçoivent le nouveau chemin de lecture. Toutes les pièces/destinations sont
contrôlées avant un mkdir ou une écriture. Une source déjà présente dans un autre
cœur canonique entraîne un conflit avant écriture ; aucune déduplication par
écrasement n'est réalisée. Les schémas L3 doivent être installés explicitement :
charger les modèles d'archive n'exécute aucune DDL ; le démarrage du candidat
L3 appelle l'installateur après sauvegarde, indépendamment de cet import.
`project_archive_brain.py` ajoute seulement les parents mail non classés utilisés
par les propositions/preuves du projet et leurs artefacts. Leur `project_id=None`
et statut sont conservés ; une source non classée sans relation au projet est
refusée à l'import. Une preuve liée à un autre projet refuse l'export (409).
La limite de 150 Mio refuse un export incomplet (413) et indique la sauvegarde
globale. Tests de transport : `tests/test_project_deliverable_archive.py`.

Validation : 1698 tests Python réussis / 1 ignoré, 458 React, Ruff, TypeScript et build conformes. Recette navigateur sur données fictives puis contrôle de la version active sans erreur console. Après sauvegarde, 207 suggestions existantes à 100 % classées ; 109 sources déjà traitées, toutes les décisions antérieures et le contenu des mails conservés. Aucun commit/push. Preuve : `.ui-preview/mail-auto100/delivery.json`.

## Reprise projet XPilot — objectif lancé le 5 octobre 2026

L'[audit local](docs/27_XPILOT_PROJECT_AUDIT.md) et le
[plan par lots](docs/28_XPILOT_PROJECT_PLAN.md) recensent les écarts de modèles,
API, documents et interface. L'[inventaire](docs/27_XPILOT_PROJECT_INVENTORY.json)
fige les chemins, lignes et empreintes du code examiné avant le démarrage.
L'[exécution par lots](docs/29_XPILOT_EXECUTION.json) commence par les
[contrats et contrôles de conservation](docs/29_XPILOT_FOUNDATION.md).
L0 livre `scripts/project_migration_check.py` : préflight, capture et comparaison
en lecture seule, avec chemins explicites et rapports ne remplaçant aucun fichier.
Cette fondation n'active aucune nouvelle route ni migration de production.
Le [socle L1](docs/30_XPILOT_PROJECT_IDENTITY.md) ajoute six tables additives,
les règles de fiche/équipe et un routeur actif dans `C:\Agent` sur `8001`.
Sa migration explicite a été répétée sur copies sans modifier de valeur existante.
Les archives v3 ajoutent un bloc `references` limité aux dépendances actuelles
et historiques du projet. Un référentiel existant différent provoque un conflit
409 sans écrasement ; les archives v2 restent importables. Les pièces requises
sont vérifiées avant toute copie de fichier. Cette évolution est activée.
Le contexte d'opérateur et ses contrôles HTTP/internes ERP/Brain sont qualifiés
et actifs dans `C:\Agent`. Le lecteur ne peut écrire ;
les listes, compteurs et contextes de connaissance respectent les UUID ERP et
leurs liaisons Brain explicites. `AGENT_OPERATOR_ID`, `AGENT_OPERATOR_ROLE`
(`owner`, `editor`, `reader`) et `AGENT_OPERATOR_PROJECT_IDS` (liste JSON ; `[]`
est une portée vide) configurent un opérateur local de confiance, pas des comptes
multi-utilisateur. Les référentiels globaux, imports d'archives et modifications
des liaisons Brain restent réservés au propriétaire sans portée restreinte.
Le mode propriétaire local reste la configuration par défaut.
La Vue d'ensemble projet ajoute Fiche, Équipe et Historique ; Réglages ajoute
Référentiels (clients, agences, BU, familles, typologies et personnes). Les
recherches sont paginées, les commandes utilisent la révision chargée et les
brouillons restent présents en cas de conflit ou de changement de réglage.
Le démarrage ERP vérifie le schéma L1 avant `create_all` et sauvegarde une seule
fois avant toute création sur une base existante ; une sauvegarde défaillante
ou des contraintes incohérentes interrompent la migration. Les bases neuves
reçoivent le schéma complet. La recette sur copies de démarrage répété conserve
11 548 lignes / 95 243 cellules. Qualification de la fusion avec les corrections
mails : 332 tests Python réussis, 1 ignoré, 114 tests React réussis, Ruff,
TypeScript et build conformes.
Le contrôle HTTP du parcours réel utilise l'application Agent et des bases
isolées. La recette navigateur couvre fiche, dates, équipe, historique,
référentiels, création manuelle et dossier réseau, sélecteurs et affichage mobile.
L'activation du 5 octobre conserve 12 999 lignes / 107 785 cellules, dont les
données historiques financières ; aucune donnée fictive de recette n'est créée
dans les bases actives. Code, interface et deux bases sont sauvegardés dans
`C:\Agent\logs\xpilot-l1-activation-20261005-174402`. Les recherches de jalons
en cours sont remises en file au redémarrage. Les routes et bundles actifs sont
vérifiés ; les anciens bundles restent disponibles aux onglets déjà ouverts.
Un complément global hors ligne sauvegarde les deux bases et les fichiers gérés
dans `full-state-after-l1` sous ce dossier. La restauration dans une nouvelle
copie contrôle 1 388 fichiers par empreinte, 13 090 lignes / 108 518 cellules,
sans modification inattendue. Seuls les chemins portables et les états de jobs
prévus par le restaurateur sont transformés dans cette copie ; aucun worker
n'y est lancé. Les bases originales restent intactes.
Les extensions prévues restent dans FastAPI sur `8001`, avec SQLite ERP et Brain ;
aucune copie de MariaDB XPilot ni nouveau service `8002` n'est prévue.
Les fonctions financières restent exclues. Chaque lot de code devra vérifier
migrations sur copies, restauration, archives, tests Python/React et qualité
documentaire selon les critères de recette du plan.
Le [socle L2](docs/31_XPILOT_PROJECT_PLANNING.md) est préparé dans le worktree :
règles, sept tables additives et commandes transactionnelles jalons/tâches/
références avec révision attendue et contrôle d'opérateur. La migration explicite
`install_planning_schema(engine, backup=...)` exige une copie ERP avec L1.
Le worktree la raccorde au démarrage sauvegardé ; le serveur actif reste sur L1.
Six triggers empêchent
la modification ou suppression des versions, références et événements publiés.
La migration sur copies conserve 13 090 lignes / 108 518 cellules ; elle est
idempotente et vérifie schéma, contraintes et protections avant écriture.
Test ciblé : `python -m pytest tests/test_project_planning.py tests/test_project_planning_rules.py -q`.
Les routes `/api/v1/projects/{id}/planning/state`, `/items/tasks`,
`/items/milestones`, `/history` et `/baselines` sont actives sur Agent 8001,
avec édition révisionnée, capture complète et comparaison de références.
Les créations/éditions historiques et l'acceptation IA partagent la révision ;
la conversion d'action de réunion acquiert aussi ce verrou. Une ancienne
requête sans `expected_revision` reste compatible et invalide les vues préparées.
Les modèles `/api/v1/planning-templates` ont un catalogue paginé, des versions
publiées immuables et une administration réservée au propriétaire sans restriction.
Le lecteur peut consulter un aperçu de modèle autorisé sans écriture ; l'application
exige la révision et l'empreinte de cet aperçu. Correspondances de jalons, prévisions
et mise à jour des tâches sont explicites. Les UUID, dates contractuelles/réelles et
preuves historiques sont conservés. Les tâches portent une clé de modèle stable
pour empêcher leur duplication lors d'une nouvelle application/version.
Le workflow ouvre le suivant après validation, sans déduire de date réelle ni
franchir un jalon bloqué. La création atomique `/planning/tasks` accepte la hiérarchie,
le responsable et les heures ; les six états XPilot sont repris pour les tâches.
Les archives v4 exportent uniquement les modèles/personnes utilisés par le
planning actuel et ses historiques. La restauration sépare les UUID ERP/Brain,
conserve les textes et recalcule les empreintes des références figées après
remappage. Les versions publiées restent immuables. Les archives v2/v3 restent
compatibles ; la migration L2 doit être active avant import/export v4.
Les écrans Jalons/Tâches sont qualifiés dans le worktree sur données fictives.
Les formulaires envoient les seuls champs modifiés avec leur révision ; un conflit
conserve la saisie et exige une comparaison puis une reprise explicite. Les
relations se chargent par pages ; le détail `/planning/items/{kind}/{id}` est
contrôlé par projet et fournit les libellés des sélections hors page.
Références & écarts et Historique sont aussi qualifiés sur données fictives.
Les références v2 capturent aussi début/fin du projet et budget d’heures ;
les captures v1 restent lisibles sans reconstitution. Modèles UI et recette responsive sont qualifiés à 390, 650 et 1280 pixels ;
L2 est maintenant activé sur le serveur unique 8001.
Qualification : **127 cas L2**, **459 tests Python réussis, 1 ignoré**, **155 tests React**, Ruff conforme.
Les preuves figurent dans le document 31 et le suivi 29.
Les écrans L2 sont actifs sur `8001`. La recette d’écriture a utilisé des
bases fictives sans travailleurs ; la vérification des dix projets historiques
après activation est restée en lecture seule. Migration : 7 tables additives,
6 protections immuables, aucune suppression ni remplacement de jalons.

## Installation et lancement

Profil de référence : Windows, Python 3.13, Node 24 pour compiler React.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

`start-agent.cmd` ouvre aussi le navigateur. Pour un serveur qui survit aux
sessions (sans fenêtre) : `start-agent-task.cmd`, ou
laisser le raccourci `Agent-Backend` du dossier Démarrage Windows le lancer à
l'ouverture de session. `/` sert React ; `/ui` sert les pages
Brain ; `/docs` décrit les API. Le pont utilise les mêmes gestionnaires en mémoire.
Le script `start-agent-task.cmd` utilise `.venv\Scripts\pythonw.exe` s’il existe,
sinon `pythonw` du PATH. Les logs sont dans `PB_STORAGE_DIR/logs/agent.log`,
avec rotation à 5 Mio et trois copies au maximum.
`/health` teste réellement les bases ; un moteur externe absent est annoncé par
`/v1/settings/memory/engines`, indépendamment de la disponibilité SQLite.

## Paramétrage (menu Réglages)

- **IA** : `ollama`, `openai_compatible` ou `none`, URL, modèle, clé et activation ;
  `GET/PUT /api/v1/brain/ai-settings`, test principal
  `POST /api/v1/brain/ai-test`. Les champs de secours local sont décrits plus haut ;
  son bouton vérifie le modèle local séparément.
- **E-mails** : source `thunderbird` (par défaut) ou `folder` (fichiers `.eml`),
  dossiers choisis, scan automatique, intervalle et seuil de classement ;
  `GET/PUT /api/v1/brain/mail-settings`, `POST /api/v1/brain/scan`.
  Thunderbird ouvert exécute les commandes en attente ; le heartbeat de la liaison
  0.2.0 applique les réglages centraux. Les imports hors sélection sont refusés.
- **Mémoire** : EG2 en production ; `GET/PUT /api/v1/brain/memory-settings`,
  test complet `POST /api/v1/brain/memory-test`. Les réglages persistants sont
  `embedding_endpoint`, `embedding_model`, `index_path`, `timeout_s` (120 s par
  défaut) et `batch_size` (8 par défaut, de 1 à 32). Un chemin vide utilise
  `PB_STORAGE_DIR/eg2/index.db`. Le modèle renvoie 768 dimensions ; endpoint,
  modèle et profil de normalisation doivent rester compatibles avec l'index.
  Après modification de profil, reconstruire l'index avec sauvegarde ; les
  vecteurs incompatibles ne sont pas mélangés silencieusement.
- **Apparence** : thème clair/sombre et densité confortable/compacte ; préférences
  par navigateur. Voir [l'interface](docs/24_UI_UX_REDESIGN.md).

L'équivalent `/ui/settings` utilise `GET/PUT /v1/settings/{ai,mail,memory}`.
Les diagnostics `/v1/settings/embedding-channel` utilisent le même profil EG2
que la production ; ils ne configurent pas un second moteur. Une réponse à
`GET /v1/settings/memory/engines` confirme la lecture locale de l'index ; le test
complet vérifie séparément serveur distant, indexation, rappel puis nettoyage.

## Configuration et données

Les jalons utilisent `contractual_date`, `forecast_date`, `actual_date` et un
historique des modifications. La migration ERP sauvegarde la base et conserve
les anciennes échéances comme prévisions. Les nouveaux projets, et les projets
sans jalon au démarrage, reçoivent une trame sans dates inventées. Le worker local
recherche toutes les cinq minutes dans les sources rattachées et les liens réseau
des projets actifs, sans écrire sur le réseau. Il reprend sa file après arrêt ;
les preuves ambiguës, inaccessibles et conflits restent visibles pour validation.
`POST /api/v1/projects/{pid}/milestones/scan` lance une recherche asynchrone ;
`GET .../milestones/review` suit le lot courant et les propositions. Voir
[les contrats, formats, limites et tests](docs/26_PROJECT_MILESTONES.md).
Les nouvelles tables sont incluses dans les sauvegardes/archives du projet.
`AGENT_TESTING=1` désactive également ce worker.

| Variable | Effet |
|---|---|
| `PB_DATABASE_URL` | Base Brain ; défaut `project_brain.db` à la racine du dépôt |
| `PB_STORAGE_DIR` | Stockage Brain, défaut `storage` à la racine du dépôt |
| `MINIPILOT_HOME` | ERP et CDC, défaut `~/.minipilot` |
| `PB_MEMORY_ENGINE` | Moteur de production `eg2` ; `fake` réservé aux tests isolés |
| `PB_API_KEY` | Clé IA injectée par l’environnement, prioritaire sur la base |
| `PB_THUNDERBIRD_TOKEN` | Clé d’appairage de l’extension, alternative à la clé DPAPI Windows |
| `AGENT_OPEN_ROOTS` | Racines autorisées pour ouvrir des documents, séparées par `;` sous Windows |
| `AGENT_TESTING=1` | Bases temporaires de tests ; désactive jeton et workers automatiques, dont le scan des dossiers |

IA, dossier mails et mémoire : app Réglages ou `/ui/settings` ; API
`GET /v1/settings`, `PUT /v1/settings/ai|mail|memory`.

Le réglage mail conserve `folder`, `auto_scan` et `scan_interval_minutes` (1–1440),
et ajoute `source` et `thunderbird_folder_ids`. Une liste vide désélectionne tous
les dossiers ; `null` conserve la sélection initiale de l’extension. Un ancien
client qui enregistre uniquement `folder` active le mode EML. Changer la source
ne supprime aucun mail ni chemin stocké. La configuration utilise la table de
réglages existante, sans migration destructive.

Qualification : `tests/test_mail_sources.py`, `MailSettingsForm.test.tsx` et les
tests Node de la liaison couvrent l’exclusivité des sources, le choix des dossiers,
la suspension automatique et la synchronisation manuelle. Voir aussi
`docs/21_THUNDERBIRD_BRIDGE.md` pour l’installation du XPI local appairé.

Le témoin du menu interroge `GET /api/v1/workspace/mail-activity` toutes les trois
secondes lorsque l’onglet est visible. Cette route lit les réglages, le heartbeat,
le scan, les tâches IA et les projections des mails pour le moteur actif. Aucun
traitement n’est déclenché par sa lecture. L’indexation signale également les
appels directs au moteur mémoire ; son témoin s’arrête même après une exception.
Une progression inconnue reste indéterminée, notamment avec la liaison 0.1.0.
Le journal est borné à quatre changements dans la session du navigateur, sans
répétition des heartbeats inchangés. Tests : `tests/test_mail_activity.py` et
`web/src/components/MailActivity.test.tsx`.
Le moteur CDC et l’ancienne route IA lisent ces réglages dans la base Brain via
`brain_ai_settings()`. Les paramètres `reasoning_effort: none` et
`chat_template_kwargs.enable_thinking: false` sont conservés ; Ollama reçoit
`think: false`, le budget de génération, les options et le schéma JSON.
L’IA est désactivée par défaut. Une clé vide ou absente conserve la clé stockée ;
`clear_api_key: true` l’efface explicitement. Le GET ne révèle aucune clé.
DPAPI lie les clés stockées au compte Windows : une restauration sur un autre
compte exige de réinjecter `PB_API_KEY` ou de renseigner une nouvelle clé.
Une clé d’environnement ne peut pas être effacée en modifiant la base.

## Session API locale

Les écritures demandent `X-Agent-Token`, obtenu par `GET /api/v1/session`.
React et les pages `/ui` le transmettent automatiquement. Exemple PowerShell :

```powershell
$agentUrl = 'http://127.0.0.1:8001'
$agentToken = (Invoke-RestMethod "$agentUrl/api/v1/session").token
Invoke-RestMethod "$agentUrl/v1/projects" -Method Post -Headers @{'X-Agent-Token'=$agentToken} -ContentType 'application/json' -Body '{"code":"P26-TEST","name":"Essai"}'
```

Le jeton change au redémarrage : recharger la page. Host et Origin externes sont
refusés ; le proxy Vite local 5174 est prévu. Le serveur doit rester sur loopback.
Les exécutables/scripts ne sont pas ouvrables via `/api/v1/open-path` ; seuls les
répertoires et documents sous une racine configurée ou un lien projet le sont.

## Sources et validation

1. Déposer les `.eml` dans le dossier configuré ou uploader une source.
2. Scanner (`POST /v1/ingest/scan`) ; taille par source 50 MiB, lot maximal 500 uploads.
   Les doublons ne consomment pas le quota d’import du scan.
3. Trier (`POST /v1/triage/run`) puis valider/réassigner dans Mails.
   Les codes et les suggestions IA restent des candidats. Une référence explicite
   connue dans l’objet ou le corps propose le projet dès l’import (confiance ≥ 90 %),
   y compris dans `PO-26-01872-AIRB25LTH0806-A`. Les alias alphanumériques déclarés
   sont des références alternatives ; aucune équivalence entre codes proches
   n’est déduite automatiquement.
4. `POST /v1/resolution/{source_id}/confirm` rattache explicitement la source.
   Répéter la même confirmation est neutre ; changer de projet conserve les traces.
5. Accepter/rejeter les propositions de connaissance dans `/ui/proposals`.
   Une contradiction renvoie 409 avec les `knowledge_ids` actifs : sélectionner
   explicitement `supersedes_id`, ou conserver/rejeter la proposition.
6. Consulter `GET /v1/sources/{id}` pour le texte intégral et `/raw` pour l’original.

`upload-audio` accepte un transcript manuel : il alimente les propositions.
Le parcours automatique **Revues → Réunion audio** ajoute transcription locale,
séparation des voix, corrections/validation du texte, puis synthèse par le LLM Brain
et publication explicite du CR. Il conserve l’import manuel. Installation du runtime
optionnel, API `/api/v1/projects/{pid}/recordings`, limites 50 MiB/120 minutes,
variables `PB_SPEECH_PYTHON` et `PB_SPEECH_MODELS_DIR`, tests et règles de reprise :
voir [docs/23_MEETING_AUDIO.md](docs/23_MEETING_AUDIO.md).
Aucun service STT automatique n’est branché. Les routes de listings sources,
propositions et connaissance acceptent `offset`/`limit` (maximum 1000). La file
Mails et la page de validation ont des commandes de pagination/reclassement.

L’application Mails conserve les dossiers « À classer / Mails classés / Divers »,
des vignettes et un lecteur : objet, ligne expéditeur/date puis corps. Les
coordonnées complètes se déplient dans « Détails du mail ». Les décisions
restent explicites dans le panneau projets : valider la suggestion, affecter
un autre projet ou déposer une sélection sur une vignette projet. La recherche
et le tri par date portent sur tous les mails du dossier avant pagination, via
`GET /v1/mail/page?scope=pending|resolved&q=...&sort=newest|oldest`. La recherche
ignore casse et accents, porte sur auteur, sujet, code projet et texte intégral ;
`total` et `has_next` décrivent le résultat filtré. Les dossiers projets filtrent
les sources côté serveur via `project_id` (100 mails classés, 200 propositions). `GET /v1/sources/{id}` fournit les destinataires, la date et
le texte ; `/raw` télécharge le mail complet, pièces jointes comprises.
Le style dédié `web/src/mail-workspace.css` suit le thème et les couleurs des
boutons ; sous 540 px de largeur disponible, le lecteur précède le panneau projets.

### Reprendre les suggestions de références explicites

`python -m scripts.refresh_mail_references` audite les suggestions en attente.
Avec `--apply`, le script sauvegarde d’abord SQLite dans `backups/`, puis remplace
les suggestions incorrectes par celles d’un projet explicitement référencé.
Les anciennes propositions deviennent `superseded` et un audit conserve leurs
identifiants. Il n’appelle pas le LLM, ne valide aucun classement et conserve les
décisions humaines. Plusieurs références de projets : aucune reprise automatique.
Relancer est neutre pour les suggestions déjà correctes. Tests :
`tests/test_resolution.py`, `tests/test_mail_reference_refresh.py`, `tests/test_triage.py`.

### Classement multicritère et apprentissage

Chaque import et chaque lot de tri reconstruisent un profil à partir des mails
`resolved` du projet et des connaissances `validated`. Les suggestions en attente,
mails écartés et DIVERS n’entraînent pas le profil. Un reclassement change la
répartition au prochain passage ; aucune ancienne association n’est conservée
dans un cache durable. Le LLM reçoit aussi les expéditeurs et thèmes appris.

L’adresse de l’expéditeur est normalisée (nom affiché/casse), comparée exactement,
et pondérée par le nombre de validations et sa répartition entre projets.
Destinataires spécifiques, contacts déclarés, domaine, conversation, vocabulaire,
nom du projet et noms de pièces jointes complètent le score. Les en-têtes
`In-Reply-To`/`References` sont stockés pour les nouveaux mails et relus dans
l’original des anciens imports si disponible. Une référence dans l’objet prime
sur une référence seulement citée dans le corps. Deux références concurrentes
au même niveau, ou un écart de score inférieur à 0.12 hors référence explicite,
imposent une revue. Le seuil de proposition reste 0.75 ; les scores sont des
indices heuristiques, pas des probabilités calibrées. Un expéditeur partagé et
des destinataires communs exigent un indice discriminant supplémentaire.

`GET /v1/triage/learning` (pont `/api/v1/brain/triage/learning`) expose les nombres
de mails validés, expéditeurs habituels et thèmes par projet. La file `/queue`
fournit les indices détaillés et les candidats, affichés dans « Pourquoi ce projet ? ».
`python -m scripts.refresh_mail_references --learned` audite les suggestions
recalculables sans LLM ; `--apply` les reprend après sauvegarde, sans toucher
aux classements validés. Tests : `tests/test_mail_learning.py` et scénario
de validation/reclassement de bout en bout dans `tests/test_triage.py`.
La reprise de maintenance peut exclure une liste d’IDs sources via le paramètre
`exclude_source_ids` du service, pour préserver un lot déjà en cours d’analyse.

### Progression des analyses de mails

« Tout ré-analyser » affiche `0 / N mails traités`, puis actualise le compteur
après chaque lot de cinq mails. Le total est calculé au lancement sur tous les
mails en attente, indépendamment de la page ou de la recherche affichée. Les
mails classés/écartés sont exclus. « Analyser les nouveaux » utilise le nombre
restant sans suggestion IA pending (`new_sources` de `GET /v1/triage/stats`,
aussi disponible via le pont `/api/v1/brain/triage/stats`).

Un mail en échec compte comme traité dans ce passage, avec un compteur d’échecs
séparé ; son classement reste à reprendre. Interrompre laisse finir le lot en
cours et conserve la progression. Une coupure conserve les lots confirmés ;
le lot dont la réponse est perdue n’est pas compté comme acquis. Si la file change
pendant l’analyse, le compteur peut rester partiel et l’interface le signale.
La limite historique de 300 mails par lancement est retirée.

### Écarter les mails sans intérêt

Dans Mails, choisir **Écarter — spam / sans intérêt**, puis **Écarter ce mail**,
ou déposer une sélection sur la vignette **ÉCARTER** (un clic sur cette vignette
traite la sélection, sinon le mail ouvert). API :
`POST /api/v1/brain/sources/{id}/discard` → `POST /v1/sources/{id}/discard`.

Avant la purge, une sauvegarde SQLite vérifiée et une copie du fichier brut Agent
sont créées dans `backups/before-mail-discard-<horodatage>/`. L’échec de sauvegarde
interrompt la purge. Le fichier du dossier d’origine est conservé.
Le contenu, les pièces jointes de la copie Agent, les propositions/décisions et
les connaissances exclusivement sourcées par ce mail sont supprimés ; les traces
d’audit associées sont expurgées. Les connaissances étayées par d’autres sources
restent conservées. La ligne Source devient `discarded`, sans auteur ni contenu,
avec son UUID et son SHA-256 : les scans/uploads la reconnaissent comme doublon.
Elle est absente des listings, des analyses (y compris forcées) et de la mémoire ;
lecture et téléchargement répondent 410, reclassement 409.

Les projections mémoire deviennent obsolètes puis sont purgées via la file
durable. Si l'index EG2 ou le disque est indisponible, l'exclusion canonique est
immédiate : une source écartée n'est plus rappelée. Le nettoyage physique reste
à reprendre et le résultat expose `memory_cleanup_pending` et
`raw_cleanup_pending`. Répéter l'appel réessaie le nettoyage sans répéter la
suppression canonique. Les sauvegardes conservent volontairement la version
antérieure et ne constituent pas une source pour le chatbot.
Tests : `python -m pytest tests/test_mail_discard.py -q`.

## Liaison Thunderbird

Installer : `python scripts/install_thunderbird.py --install`, puis redémarrer
Thunderbird. Le XPI appairé est généré dans `storage/thunderbird/`, hors Git ;
la migration additive est sauvegardée et les anciens mails reçoivent une
empreinte MIME stable pour préserver doublons et exclusions.

Dans Mails → **Thunderbird**, vérifier la connexion, choisir les dossiers,
demander une synchronisation, créer un brouillon ou ouvrir une réponse.
L’extension importe par lots de 100 avec reprise toutes les 5 minutes et lors
des arrivées. L’import n’appelle pas l’IA et ne valide pas de projet ; la file
Agent conserve les validations humaines. La réception est choisie par défaut.

API `/v1/thunderbird/status|sync|drafts`, et pont authentifié dédié
`/v1/thunderbird/bridge/*`. Les brouillons utilisent le compte Thunderbird,
avec pièces jointes (20 Mio cumulés). L’envoi final se fait dans Thunderbird.
La clé est protégée par DPAPI côté Agent et n’est pas exposée par les réglages.
Tests : `python -m pytest tests/test_thunderbird.py -q` et
`node --test extensions/thunderbird-agent/core.test.cjs extensions/thunderbird-agent/background.test.cjs`.
Documentation complète : `docs/21_THUNDERBIRD_BRIDGE.md`.

## CDC et sorties

Upload 50 MiB, PDF 2000 pages ; conteneur DOCX/XLSX : 100 MiB décompressés,
10000 entrées ; Excel : 200000 cellules. Les PDF corrompus et DOCX invalides
renvoient une erreur métier. Les imports CSV BOM sont limités à 50 MiB et
100000 lignes ; quantités négatives ou non finies refusées ; anciens prix ignorés.
Une source ancienne sans fichier/texte reste `analyzable: false` : la réimporter.

Transfert : `POST /api/v1/projects/{id}/cdc/transfer?draft=true`.
Le mode final exige des éléments confirmés et aucun contrôle bloquant.
Chaque génération produit une nouvelle version immuable : fichier Markdown,
SHA-256 et photographie des exigences, sources et contrôles.
`GET .../cdc/deliveries` liste les versions ; `GET .../cdc/deliveries/{version_id}`
relit le contenu après contrôle de son empreinte. Les exports projet v2 incluent
ces versions et leurs fichiers ; la sauvegarde globale remappe leurs chemins.
Les décisions de revue sont disponibles dans `.../cdc/decisions`.

L’interface crée une analyse via `POST .../cdc/jobs` (202, corps identique à
l’ancienne route `analyze`). `GET .../cdc/jobs` donne l’état et les lots acquis ;
`POST .../cdc/jobs/{job_id}/cancel|retry` annule ou reprend. Un worker unique
traite la file SQLite ; les lots et leur progression sont enregistrés ensemble.
Une interruption du serveur reprend automatiquement au démarrage. Une annulation
prend effet entre deux lots ; une erreur appelle une reprise explicite. Après
restauration/import d’une archive, les jobs actifs deviennent `interrupted` et
exigent une reprise explicite. L’ancienne route synchrone `analyze` reste compatible
et partage le verrou d’analyse. Ce worker ne constitue pas un scheduler général.

Les routes d’offre et de chiffrage ont été retirées, ainsi que les champs financiers
des contrats actifs. Les colonnes historiques et les échanges d’archives les
préservent, sans suppression de lignes ni réécriture des anciennes valeurs.
Les heures restent modifiables. `PATCH /api/v1/projects/{id}` accepte
`remaining_hours` (valeur réestimée ; `null` rétablit le solde calculé).
Le solde par défaut est `max(0, heures prévues CDC ou TDAO - heures consommées)` ;
la consommation additionne saisies manuelles et lignes Sage, sans dédoublonnage
entre ces deux modes : éviter une double saisie du même pointage.
`GET /api/v1/actions` regroupe les actions des projets actifs sur 14 jours.

## Mémoire

L'enregistrement canonique SQL précède toute projection EG2. Les états
`pending`, `failed` et `obsolete` restent visibles dans
`GET /v1/projects/{id}/memory/status`. `truth_items` compte les connaissances
canoniques actives ; `truth_projections` est un compteur technique de suivi,
sans vectorisation ni extraction LLM par connaissance.

`POST /v1/projects/{id}/memory/retry` traite la file du projet ; un succès HTTP
peut contenir des échecs individuels. `POST .../memory/reindex` reconstruit les
projections depuis les sources canoniques et renvoie 503 si la reconstruction
échoue. La reconstruction ne supprime ni source ni fait canonique.

Chaque référence `eg2:` dépend du projet, de la source, du texte et du profil.
Une purge est limitée à la référence du projet demandé. Une nouvelle version est
vectorisée avant le remplacement atomique des passages d'une source ; un échec
d'embedding ne supprime pas l'index précédent. Le rappel recontrôle propriété,
statut et texte courant : les passages de sources déplacées, écartées ou remplacées
sont exclus même avant leur nettoyage physique. Un changement de profil exige
une reconstruction explicite.

En cas de panne EG2, les faits canoniques pertinents peuvent encore être retournés
avec un avertissement indiquant que les preuves n'ont pas été recherchées.
Aucun rappel de preuves par recherche SQL ne remplace silencieusement EG2.
Pour la reconstruction globale hors ligne, les sauvegardes et les tests de contrat,
voir [le moteur EG2](docs/20_EG2_ENGINE.md).

## Sauvegarde et restauration

L’export projet JSON v2 préserve l’ERP, ses relations, les documents CDC et les
objets Brain du projet relié. L’import change les UUID et conserve les liens de
réunion/tâche sans duplication. Dans le même environnement, un projet Brain
encore existant est réutilisé. Un export v1 reste un échange historique incomplet.
Les contacts et réglages globaux, imports Sage et exports produits sont conservés
par la sauvegarde globale. Une archive projet ne garantit pas une transaction
atomique entre deux bases en cas de panne électrique entre leurs commits.

Arrêter Agent et ses éventuels processus secondaires avant la sauvegarde
coordonnée ; la commande refuse un serveur actif sur 8001.

```powershell
python scripts/agent_backup.py backup --output E:\Agent-sauvegardes\lot-neuf
python scripts/agent_backup.py restore --source E:\Agent-sauvegardes\lot-neuf --output E:\Agent-restaure\lot-neuf
```

La sauvegarde utilise l’API SQLite backup, conserve les fichiers et un manifeste
SHA-256. La restauration vérifie les empreintes et l’intégrité avant de créer le
dossier, puis réécrit les chemins de fichiers gérés dans les bases restaurées.
Configurer `PB_DATABASE_URL`, `PB_STORAGE_DIR` et `MINIPILOT_HOME` vers les
sous-dossiers `brain`, `storage`, `erp` avant de lancer cette copie.
Les migrations sont additives et inscrites dans `schema_migrations` ; sauvegarde
Brain avant migration ancienne et ERP uniquement avant une migration nécessaire ;
aucune purge automatique. `GET /api/v1/operations/status` expose espace disque,
copies de migration et dernière sauvegarde globale. Le bouton de vérification
(`POST /api/v1/operations/backup/verify`) contrôle fichiers SHA-256, intégrité SQLite
et clés étrangères. Il ne crée pas de sauvegarde pendant que le serveur tourne.
Les sauvegardes peuvent contenir d’anciennes clés en clair : conserver les accès
Windows du dossier privé. Les originaux et historiques ne sont pas supprimés.

## Validation reproductible

```powershell
python -m pip install --require-hashes -r requirements-dev.txt
python -m pytest tests/ -q
python -m ruff check app backend/app tests scripts
node --test tests/test_extension_core.cjs
node --test extensions/thunderbird-agent/core.test.cjs extensions/thunderbird-agent/background.test.cjs
cd web
pnpm install --frozen-lockfile
npm test
npm run build
```

`ruff.toml` fixe les règles E4/E7/E9/F afin que les contrôles locaux et la version
verrouillée appliquent le même périmètre. Pytest utilise des bases, réglages et
stockages temporaires ; le mode `AGENT_TESTING=1` avec `PB_MEMORY_ENGINE=fake`
est réservé aux fixtures isolées. Il n'active pas de service EG2 ni de worker
automatique. Le test `test_ai_status_and_unreachable` est indépendant d'un Ollama
réel sur 11434. Les tests du client d'embedding simulent leurs réponses ; les
sondes réseau réelles sont des vérifications d'exploitation séparées.

Les locks Python (versions et empreintes) ciblent Windows/Python 3.13 ; les fichiers
`.in` servent aux mises à jour contrôlées. `requirements-benchmark.txt` décrit
les outils optionnels de mesure, sans être nécessaire au moteur de production.
Le workflow Windows `.github/workflows/verify.yml` exécute les contrôles Python,
extension et interface. Son délai maximum est porté à 60 minutes : la suite
Python locale du 11 octobre a pris 36 minutes, avant installation et contrôles
frontend. La publication des changements ne vaut pas réussite de la CI distante
et ne masque pas l'échec préexistant de classement des mails.

## Panneau de l'assistant

Le panneau s'ouvre avec le bouton Assistant ; sa largeur va de 300 à 520 px.
La poignée sur le bord gauche répond à la souris et au toucher ; les flèches
gauche/droite ajustent de 10 px, Maj de 40 px, Début/Fin atteignent les limites.
La largeur est conservée dans le navigateur.

Le panneau (`web/src/components/AssistantPanel.tsx`, `web/src/assistant.css`)
rend le Markdown courant en éléments React, sans exécuter de HTML provenant
des réponses (`ChatMarkdown.tsx`). Les citations [V1]/[P1] ouvrent les preuves.
La recherche textuelle de secours est un statut discret avec détails repliables ;
les échecs de génération gardent une alerte et un bouton Réessayer. La saisie
est multiligne : Entrée envoie, Maj+Entrée ajoute une ligne. Les tests frontend
`AssistantPanel.test.tsx` et `ChatMarkdown.test.tsx` vérifient rendu, preuves et reprise.

Le formulaire du compagnon utilise la classe dédiée `assistant-composer` et
une grille `minmax(0, 1fr) 32px`. Elle évite la collision avec le formulaire
historique `.chat-composer` de l’ERP. Le champ vide revient à 32 px de hauteur,
avec croissance plafonnée à 128 px pendant la saisie.

## Espace de travail et traitements durables

Voir [la refonte livrée](docs/24_UI_UX_REDESIGN.md). `/app/projects/{id}/{tab}`
conserve le contexte ERP ; le rechargement sert le même build React sans masquer
les 404 des API. Les rubriques gardent leurs panneaux en mémoire durant la session.
Le serveur reste FastAPI sur :8001, avec les bases Brain et ERP existantes.
La liste Projets retire les boutons d’import JSON et d’actualisation. L’import
reste disponible dans Imports & connexions → Archives JSON. Le dernier groupe
numérique du code fournit le numéro de dossier ; l’icône en montre les quatre
premiers chiffres sans conversion en entier (0806 conserve son zéro).
Création manuelle et import réseau attendent le rafraîchissement avant retour
au portefeuille, avec recherche effacée et filtre En cours. Les erreurs de
création conservent le formulaire et les clics répétés ne doublent pas l’envoi.
Accueil, Projets et Mails sont actualisés toutes les 10 secondes dans un onglet visible,
ainsi qu’au retour de l’onglet ou de la fenêtre. Les panneaux métier restent montés.
La vue Mails reçoit les changements du portefeuille, même si elle était déjà
ouverte avant une création. Les destinations réunissent ERP et Brain sans doublon,
avec le titre ERP à jour. `POST /api/v1/projects/{id}/brain/ensure` crée ou réutilise
le projet de connaissance et enregistre son lien lors d’une affectation explicite.
Un code ambigu produit un 409 et nécessite le choix du lien dans Connaissance.
Après validation serveur, les lignes sont retirées par identifiant de source,
les compteurs ajustés et les réponses périmées filtrées. Un dépôt multiple
conserve les échecs sélectionnés ; la pagination revient à une page existante.
Le rafraîchissement conserve le lecteur et un sélecteur ouvert. L’erreur réseau
ne remplace plus une boîte déjà chargée par un écran vide.
`useWorkspaceWheel` conserve le défilement natif d’une liste qui peut avancer ;
à sa limite, ou sur une zone sans défilement vertical, la molette déplace la page.
Zoom, Maj + molette, mouvements horizontaux, dialogues et champs de saisie
multiligne/nombre/sélecteur gardent leur comportement natif.

`GET /api/v1/workspace/{meetings,jobs,proposals,knowledge}` expose `items,total`,
`offset,limit` et les filtres applicables. Projets ERP pour réunions/traitements,
projets Brain pour propositions/connaissance ; aucun projet implicite.

`POST /api/v1/workspace/triage-jobs` prend `{force}` et fige les identifiants
des mails à classer. GET liste, `/latest` (travail actif prioritaire), `/{id}`,
POST `/{id}/cancel|retry` permettent suivi et reprise. Le compteur est mis à jour
par lots de cinq. Fermer l’onglet laisse le serveur travailler. L’annulation
attend le lot courant ; le redémarrage reprend les travaux actifs grâce à un
audit par mail enregistré atomiquement. `force` ré-analyse les mails encore à
classer, sans changer les classements humains déjà validés.

`GET/POST /api/v1/workspace/assistant-threads`, GET/PUT `/{id}` stockent les
discussions dans Brain. PUT exige `expected_revision` ; un conflit 409 conserve
le brouillon, avec relecture ou copie explicites. Le projet d’une discussion est
immuable. Une nouvelle cible ouvre une nouvelle discussion.

`POST /v1/projects/chat/stream` utilise un fetch authentifié et des événements
SSE `metadata`, `delta`, `done`, `error`. Le LLM fournit les fragments réels
(Ollama NDJSON ou compatible OpenAI SSE) ; un flux incomplet reste interrompu.
L’annulation ferme la connexion au fournisseur. `history` contient au plus
12 messages `{role,content}` et 12 000 caractères ; il aide la conversation,
sans constituer une preuve. Les citations viennent du rappel courant.
Le contrat JSON historique reste disponible.

La migration additive Brain v6 sauvegarde la base avant création de
`mail_triage_jobs` et `assistant_threads`. Les sauvegardes coordonnées couvrent
ces tables. Une restauration classe les travaux actifs en `interrupted`, avec
reprise humaine explicite. Aucune ligne historique n’est supprimée.

Les tests `test_workspace.py`, `test_chat_stream.py`, `WorkspaceShell.test.tsx`,
`WorkspaceViews.test.tsx`, `useAssistantHistory.test.tsx`,
`useDurableMailTriage.test.tsx` et `assistantStream.test.ts` couvrent les contrats,
la navigation, les réponses obsolètes, les conflits et les interruptions.
`ScanImport.test.tsx`, `App.portfolio.test.tsx`, `WorkspaceShell.test.tsx` et
`useWorkspaceWheel.test.tsx` couvrent aussi création différée, erreurs, filtres,
rafraîchissement au retour et transfert de défilement. `MailApp.test.tsx`,
`MailWorkspace.test.tsx`, `mailProjects.test.ts` et `test_mail_project_targets.py`
couvrent dépôt simple/multiple, erreurs partielles, réponse périmée, actualisation
du lecteur, premières liaisons et conservation du mail classé.
La suite compte 84 tests frontend et 155 tests Python réussis, avec 1 test Python ignoré. Sous Windows,
utiliser un chemin temporaire court pour pytest si les copies de sauvegarde
dépassent la longueur de chemin prise en charge par le système.

L’[analyse vocale](docs/25_REALTIME_VOICE.md) reste documentaire : la voie cloud
payante est écartée ; transcription en direct et synthèse vocale locales ne sont
pas activées. Le parcours audio existant de `docs/23_MEETING_AUDIO.md` reste utilisable.

Les acceptations et affectations de mails via le triage enregistrent leur
classement et un travail `mail_enrichment_jobs` dans la même transaction. Le
reclassement ERP appelle `/v1/resolution/{id}/confirm` avec `defer_enrichment: true` ;
le contrat historique sans ce champ conserve le traitement synchrone.
Le worker du même processus exécute l’IA hors session SQLite, puis les seules
projections concernées. Un changement de classement invalide les résultats
anciens. L’échec d’enrichissement conserve le mail classé ; `/api/v1/workspace/jobs`
expose le moteur `mail`, et POST `/api/v1/workspace/mail-enrichments/{id}/retry`
reprend l’étape en échec sans répéter une extraction déjà enregistrée.
Brain v7 ajoute cette table avec sauvegarde préalable. Les travaux `running`
reprennent au redémarrage ; une sauvegarde restaurée exige une reprise humaine.
`AGENT_TESTING=1` désactive ce worker. `test_mail_enrichment.py` couvre réponse
immédiate, panne mémoire, reprise, reclassement/exclusion concurrents et restauration.

Import dossier : `/api/v1/projects/scan` utilise en priorité le code affaire
reconnu dans le nom du dossier et son titre. Sans code reconnu, l’identité du
document reste le recours. La réponse ajoute `warnings` et `tdao_compatible`.
Les documents dont le code contredit le dossier ne fournissent ni identité ni
heures ; leurs liens sont conservés pour examen. `/projects/import` applique
la même règle et ne crée pas de lignes de charge depuis un TDAO incompatible.
Tests : conflit simultané TDAO/TDSP sur le cas AIRB26LTH0205-A et recours au
document dans un dossier sans référence.

## Remise en service de la refonte — 5 octobre 2026

La copie de lancement est `C:\Agent`, qui réunit la refonte du worktree 264b
et les correctifs mails. Un redémarrage depuis une autre copie peut servir une
interface ou une API différente même sur le même port. Avant activation :
fusionner les évolutions, exécuter pytest/Ruff et les tests/build React, puis
sauvegarder les deux bases SQLite. Conserver `PB_DATABASE_URL`,
`PB_STORAGE_DIR` et `MINIPILOT_HOME` vers les données existantes.

Sur ce poste : Brain `C:/Agent/project_brain.db`, stockage `C:/Agent/storage`,
ERP `%USERPROFILE%/.minipilot/minipilot.db`. Les lanceurs situés dans
`C:\Agent` lancent cette copie ; le lanceur automatique utilise en priorité
le venv, puis Python 3.13 installé localement, puis le PATH. Aucune suppression
de module, de mail ou de décision validée n’est nécessaire pour cette reprise.

Les changements de dates de la fiche invalident la révision du planning une fois
L2 activé. Budget d’heures et charge des tâches sont comparés séparément ; aucune
financiarisation ni modification des anciennes références. Recette et archives
qualifiées sur copies : `docs/31_XPILOT_PROJECT_PLANNING.md`.

Le parcours Modèles propose un catalogue paginé, un éditeur structuré et des
versions immuables. Publier ne modifie aucun projet : correspondances, calendrier,
politique de prévisions et mise à jour des tâches sont vérifiés dans un aperçu
avant application explicite. Les listes/formulaires Planning restent utilisables
sur écran étroit ; la vue existante relit les données à son ouverture. Recette
sur bases fictives sans travailleurs : 123 lignes / 1 088 cellules métier
préexistantes conservées, zéro violation FK. L2 est activé sur 8001 après sauvegarde/restauration qualifiées ;
XPilot 8000 reste intact.

Activation L2 : `C:/Agent/logs/xpilot-l2-activation-20261005-220438`, avec code et
anciens bundles, sauvegarde globale `full-state-before-l2` et preuve de restauration
sur copie. Les 14 033 lignes / 116 204 cellules contrôlées avant migration sont
conservées ; restauration de 1 388 fichiers vérifiée par empreinte et zéro FK.
Le tri paginé reprend l’ordre des huit jalons historiques et leurs alias, puis
respecte les positions L2 explicites, sans écrire de données. Les fixtures des
tests réinstallent le schéma et les protections par `init_db()`. Le serveur actif
est sain après redémarrage ; les anciens bundles restent disponibles aux onglets
déjà ouverts. L’objectif poursuit L3–L9 ; aucun commit/push.

Qualification consolidée RLP/UI : **754 Python / un ignoré, 292 React, Ruff, TypeScript et build**. Les 31 tests RLP sont requalifiés après la dernière validation de synthèse JSON. Preuve : `.ui-preview/xpilot-l4/rlp-result.json`. L4 n’est pas activé ; archive/restauration et qualification globale restent à réaliser.

Le contrat L4.4 préparé contrôle les captures/PDF, références, journaux et extraits
audio historiques avant restauration. Deux colonnes JSON `bindings` séparent les
identifiants restaurés ERP/Brain des valeurs publiées. `install_review_schema`
ajoute ces colonnes seulement après sauvegarde réussie ; elle conserve les
cellules existantes et refuse les schémas incompatibles. Recette ciblée :
`python -m pytest tests/test_project_review_archive_contract.py tests/test_project_reviews.py tests/test_project_review_api.py -q`.
La copie du corpus fictif conserve 17 737 lignes / 146 808 cellules ERP et le
Brain exact. Aucune migration de 8001 : le transport sélectif v6 et la restauration
coordonnée restent à qualifier avant son raccordement. Détails et preuves dans
`docs/33_XPILOT_COCKPIT_REVIEWS.md` ; architecture mono-serveur conservée.

Contrat RLP/restauration préparé : **815 tests Python / un ignoré et 94 tests ciblés**, dont 63 cas de contrat/migration ; Ruff conforme. Les deux derniers cas de refus de schéma sont couverts par la requalification ciblée après collecte de la suite globale. Preuve : `.ui-preview/xpilot-l4/review-archive-contract-result.json`. Le transport sélectif reste à réaliser ; L4.4 et l’objectif L0–L9 demeurent en cours.

Transport sélectif RLP v6 qualifié dans le worktree : **863 tests Python / 1 ignoré et 327 tests ciblés**, Ruff conforme. Les erreurs et arrêts de processus préservent les deux bases ; les pièces préparées restent journalisées. Une restauration globale sur copie conserve les publications et relocalise seulement les chemins mutables. Preuve : `.ui-preview/xpilot-l4/review-transport-result.json`. Les correspondances API/UI et l’activation restent à terminer ; L4.4 et l’objectif L0–L9 restent en cours, L0–L3 seuls actifs sur 8001.

Correspondances RLP/restauration qualifiées dans le worktree : **865 tests Python / 1 ignoré, 9 cas API ciblés et 298 React**, Ruff, TypeScript et build conformes. Les publications et événements exposent leurs correspondances séparément des captures ; l’interface conserve les titres/citations et ouvre les livrables/réunions actuels du projet restauré. Recette clavier, lecteur et mobile sur une nouvelle copie, avec bases exactes après consultation. Preuve : `.ui-preview/xpilot-l4/review-links-result.json`. L4.4 est qualifié sur copies ; L4.5/L4.6 et L5–L9 restent à réaliser, L0–L3 seuls actifs sur 8001. Aucune activation, migration canonique, suppression de données ni commit/push dans cette étape.

Raccordement L4.5 qualifié dans le worktree : **874 tests Python / 1 ignoré, 22 cas ciblés et 298 React**, Ruff, TypeScript et build conformes. Le serveur unique enregistre cockpit/RLP et installe le schéma ERP v8 avec préflight et sauvegarde commune. Un groupe de tables de revue partiel contenant des données est refusé avant toute DDL. Le démarrage à froid sur les dix projets historiques conserve toutes les cellules ; le second lancement est neutre et le retour à la sauvegarde est qualifié sur copie. La recette globale native/restaurée couvre PDF figé, audio WAV décodable, droits lecteur, clavier, mobile et concurrence avec conservation de saisie. Les lectures gardent les deux bases exactes ; les seules quatre cellules préexistantes modifiées pendant les commandes de recette appartiennent au brouillon fictif et à sa révision projet. Preuve : `.ui-preview/xpilot-l4/review-registration-result.json`. La précision de reconnaissance vocale n’est pas évaluée par cette recette fictive. L4.6 et L5–L9 restent à réaliser ; L0–L3 seuls actifs sur 8001. Aucun commit/push ni suppression.

**Livraison L4 — 6 octobre 2026 : cockpit et revue de lancement actifs sur Agent 8001.** Les dix projets historiques sont accessibles, les routes cockpit/RLP sont enregistrées et le schéma ERP est en version 8. L’activation conserve toutes les cellules contrôlées (ERP : 2 145 lignes / 17 759 cellules ; Brain : 13 144 lignes / 108 134 cellules), après sauvegarde coordonnée de 1 397 fichiers et restauration vérifiée sur une nouvelle copie. Les 57 chemins intégrés préservent 276 sources canoniques ; les sources du candidat correspondent aux sources qualifiées par 874 tests Python / 1 ignoré et 298 React, Ruff/TypeScript/build conformes. La navigation réelle confirme le cockpit et la création de revue disponible, sans données de test en production. ReportLab 4.5.1, déjà verrouillé dans les dépendances, est installé seul avec contrôle des empreintes dans le Python du serveur. Preuve : `.ui-preview/xpilot-l4/integration-1006-l4-v2/delivery-result.json`. L’objectif reste actif : L5–L9 sont à réaliser. XPilot/8000, les modules hérités et les données sont conservés ; aucun commit/push.

**Étape L5 — 2026-10-06 : moteur documentaire qualifié dans le worktree.** Les huit trames XPilot disposent d’un catalogue non financier, d’un aperçu borné et d’une préparation de copie en mémoire liée à l’empreinte source. Les styles, signets, namespaces, commentaires et contenus hors cible, dont les parties VBA, sont conservés ; aucune macro ni application Office n’est exécutée. Qualification : **938 tests Python / 1 ignoré, 64 cas ciblés**, Ruff conforme. Les paquets de recette sont fictifs, dont une feuille de 3 000 lignes ; le rendu Office et les trames réelles restent à qualifier. Contrats et suite du lot : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md`. Preuve : `.ui-preview/xpilot-l5/document-packages-result-v2.json`. Aucune route HTTP/UI, migration, activation, écriture réseau ou modification de données de production dans cette étape. L0–L4 seuls restent actifs sur 8001. L5 reste en cours : acquisition contrôlée, valeurs projet, traitements durables, notes, identité des signataires, visas, interface et activation sont à réaliser ; L6–L9 restent au plan. Aucun commit/push ni suppression.

**Étape L5.2 — 7 octobre 2026 : acquisition et champs documentaires qualifiés dans le worktree.** Le nouveau service lit uniquement un lien du projet dans les racines documentaires autorisées, avec mappings de lecteurs explicites et vérification du handle Windows et de la stabilité du fichier. Les champs d’identification sont sourcés depuis le projet, le client et le responsable ; les corrections restent limitées à une copie documentaire et ne changent aucune fiche. Qualification : **975 tests Python / 1 ignoré, 101 cas ciblés**, Ruff conforme. Les dossiers, fichiers et projets de recette sont fictifs ; une vraie jonction Windows vers un autre projet est refusée, comme un fichier changé pendant lecture. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-files-v2-result.json`. Aucune route HTTP/UI, migration, activation, écriture réseau, modification de données de production ou commit/push dans cette étape. L0–L4 seuls restent actifs sur 8001. L5 reste en cours : découverte des modèles, API, traitements durables, notes, comptes/signataires, visas, interface et activation ; L6–L9 restent au plan.

**Étape L5.3 — 7 octobre 2026 : parcours documentaire interactif qualifié dans le worktree.** L’onglet Documents ajoute « Préparer un document » à côté des liens réseau hérités : choix manuel parmi huit trames, lien du projet et fichier relatif, champs sourcés et corrections propres à la copie, aperçu des valeurs existantes/proposées, relecture puis téléchargement vérifié. Les trois routes sont enregistrées dans le serveur Agent unique ; seul l’aperçu POST est accessible au lecteur. La préparation lie trame, lien et données métier par empreinte et relit les références dans une connexion fraîche pour détecter les changements pendant acquisition ou préparation. Qualification : **1006 tests Python / 1 ignoré, 31 cas API, 328 tests React dont 30 ciblés**, Ruff, TypeScript et build conformes ; recette navigateur éditeur/lecteur, clavier et mobile avec téléchargement réellement enregistré. Les 16 trames fictives et les données ERP restent inchangées. Usage et limites : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuves : `.ui-preview/xpilot-l5/document-api-v2-result.json` et `.ui-preview/xpilot-l5/document-browser-recipe.json`. Pas d’activation L5 sur 8001 ni de commit/push. Les copies sont téléchargées sans reçu persistant ni écriture réseau. Découverte, lots durables, stockage Agent, publication explicite, notes, comptes et visas restent à intégrer ; L5 demeure en cours et L6–L9 restent au périmètre.

**L5.3 — découverte contrôlée des trames, 7 octobre 2026.** Documents ajoute une recherche en lecture dans le lien projet explicitement sélectionné : mots de dossier/nom et indice expliqués, exclusions, limites visibles et choix manuel en cas d’ambiguïté. Le fichier choisi passe ensuite par le même aperçu contrôlé. Le lecteur peut chercher et consulter ; préparer reste réservé aux personnes autorisées à modifier. Aucun lien créé, source modifiée ou modèle Office exécuté. Qualification : **1051 tests Python / 1 ignoré, 341 tests React dont 43 ciblés**, Ruff, TypeScript et build conformes ; recette navigateur sur 18 trames fictives conservées, clavier, lecteur et mobile. La molette défile dans la liste des candidats sans déplacer la page, qui ne déborde pas horizontalement. Contrat et limites : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-discovery-result.json`. Worktree seulement : L0–L4 restent actifs sur 8001. Les règles sont celles du catalogue ; préférences persistantes, jobs reprenables, artefacts, publication, notes et visas restent au périmètre de L5. L6–L9 et l’objectif complet restent en cours ; aucun commit/push.

**L5.3 — socle de persistance documentaire, 7 octobre 2026.** Les préférences des huit trames et le formulaire par projet/document disposent de révisions indépendantes, d’un historique immuable et d’une restauration qui ajoute une version. Deux sauvegardes concurrentes ne peuvent écraser la même révision. L’installation explicite des quatre tables et huit protections impose un préflight et une sauvegarde préalable ; le démarrage ERP reste en version 8 et ne les installe pas. Qualification : **1094 tests Python / 1 ignoré, 43 cas de persistance**, Ruff conforme. Sauvegarde SQLite relue dans un nouveau dossier et cellules historiques fictives conservées. Aucun changement React dans cette étape ; les sources du dernier contrôle frontend restent identiques. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-forms-v3-result.json`. Socle interne dans le worktree : raccordement HTTP/UI, archives projet typées L5, jobs, artefacts, publication, notes, comptes et visas restent à intégrer. Une archive antérieure refuse les données documentaires persistantes pour éviter leur perte. L0–L4 seuls restent actifs sur 8001 ; objectif actif, L5–L9 en cours, aucun commit/push.

**L5.3 — archives documentaires, 7 octobre 2026.** L’archive projet v7 conserve les formulaires et toutes leurs versions, y compris les sélections de liens disparus. Les identifiants courants sont remappés séparément ; snapshots, textes, acteurs et empreintes restent intacts. Les préférences communes restent celles de la destination. La restauration globale vérifie schéma, protections et journaux en lecture seule avant de créer le dossier de sortie, sans initialiser le moteur. Qualification : **1135 tests Python / 1 ignoré**, Ruff conforme ; 41 cas ciblés archive/sauvegarde. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-archives-result.json`. Le serveur Agent unique 8001 conserve L0–L4. HTTP/UI persistants, jobs, artefacts, publication, notes, comptes, visas et L6–L9 restent à intégrer ; objectif actif, aucun commit/push.

**L5.3 — formulaires et réglages HTTP/UI, 7 octobre 2026.** Les choix de trame, lien, chemin relatif et corrections se sauvegardent par projet/document avec historique paginé et restauration ajoutant une version. Les conflits conservent la saisie ; comparer et charger la version serveur sont deux actions distinctes. Réglages → Documents permet au propriétaire sans restriction de configurer les recherches des huit trames ; les règles enregistrées s’appliquent aux projets. Qualification : **1154 tests Python / 1 ignoré**, **355 tests React**, Ruff, TypeScript et build conformes. Recette réelle sur copies fictives : 18 sources intactes, cinq versions de formulaire, trois versions de réglages, droits et conflits vérifiés. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md`. Recette mobile non validée : l’outil conserve la largeur 1280 malgré son annonce de redimensionnement. Le serveur unique Agent 8001 conserve L0–L4 ; cette étape L5 n’est pas activée. Jobs, artefacts, publication explicite, notes, comptes/visas et L6–L9 restent à intégrer. Aucun commit/push.

**L5.3 — transport des lots documentaires v8 raccordé dans le worktree.** L’archive individuelle conserve les six tables de lots et leurs fichiers validés, remappe les références courantes et garde les captures, auteurs et anciens journaux intacts. Les lots importés restent suspendus ; le réexport/réimport et la sauvegarde globale sont vérifiés sur copies. 24 cas v8, 64 cas finaux archive/sauvegarde/file et un groupe de 51 cas archive/worker/HTTP/sauvegarde et 135 cas de compatibilité passent ; ces groupes se recouvrent. Ruff conforme. Interface de file, publication explicite et qualification complète restent à terminer avant activation. Le serveur unique Agent 8001 conserve L0–L4 ; L5–L9 restent en cours. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-jobs-archive-focused.json`. Aucune migration de production, suppression, commit ou push.

**L5.3 — interface des lots documentaires qualifiée dans le worktree, 7 octobre 2026.** Documents permet de réunir jusqu’à huit trames relues, de conserver une commande après réponse perdue, et de consulter compteur par fichier, copies et journaux. Arrêt et reprise utilisent la révision lue ; interrompre l’attente conserve la soumission incertaine. Les volets masqués cessent leurs lectures. **398 tests React**, dont un groupe de **71 cas Documents**, TypeScript/build et Ruff conformes. Recette navigateur réelle : deux fichiers, progression 0/2 puis 2/2, rechargement et clavier, droits lecteur ; 18 sources et 129 cellules historiques conservées. Les octets téléchargés par HTTP sont vérifiés ; l’enregistrement final du lien Blob par le navigateur et la recette mobile restent non qualifiés. La publication réseau, la qualification Python complète et l’activation sont à terminer. Agent unique 8001 conserve L0–L4, L5–L9 restent en cours. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuves : `.ui-preview/xpilot-l5/document-jobs-ui-frontend.json` et `document-jobs-ui-browser.json`. Aucune migration de production, suppression, commit ou push.

**L5.3 — aperçu de publication et IO ancrée qualifiés sur copies.** L’aperçu lie une copie validée à un lien du projet, un dossier existant et une empreinte de destination. Les racines d’écriture sont distinctes des racines de lecture. Les créations exclusives et le renommage dans le parent du handle ouvert refusent les collisions et les jonctions ; la reconnaissance après coupure compare identité persistante, taille et SHA, sans adopter un fichier seulement identique. **125 tests ciblés**, dont 42 nouveaux cas IO/aperçu, et Ruff conformes. La commande durable de publication et son interface restent à raccorder ; aucune écriture réseau réelle ni activation sur 8001. Le frontend du précédent contrôle 398 React/TypeScript/build reste inchangé. Le partage SMB réel et la branche Linux ne sont pas qualifiés. Détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md` ; preuve : `.ui-preview/xpilot-l5/document-publication-destination-focused.json`. L0–L4 seuls actifs sur Agent 8001, L5–L9 restent en cours ; aucun commit/push ou suppression.

**L5.3 — publication durable sans remplacement qualifiée dans le worktree, 7 octobre 2026.** L’API enregistre l’intention avant la création exclusive, le reçu préparé avant le renommage, puis le succès après vérification du fichier final. Répéter la même commande vérifie identité persistante, taille et SHA sans recréer les octets ; sans reçu préparé durable, le candidat reste conservé pour inspection. Un verrou OS distinct sérialise les publications. Archives v8 et restauration globale conservent captures et acteurs, remappent les liaisons courantes et bloquent tout rejeu. **168 tests ciblés**, puis **35 cas commande/transport** sur la réponse finale (groupes se recouvrant), et Ruff conformes. Le frontend du contrôle précédent reste inchangé. Remplacement choisi avec sauvegarde, interface de publication et qualification commune restent à terminer avant activation. L0–L4 seuls actifs sur Agent 8001 ; L5–L9 restent au périmètre. Aucun partage métier écrit, aucune migration de production, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/document-publication-commands-focused.json` ; détails : `docs/34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md`.

**L5.3 — remplacement documentaire avec sauvegarde conservée qualifié dans le worktree.** Le choix explicite lie la publication à l’identité, la taille et au SHA de l’original. Une intention de sauvegarde est enregistrée avant son déplacement ancré, puis le reçu de sauvegarde avant la publication de la copie préparée. Les coupures reprennent la même commande sans recréer les octets ; collisions et fichiers modifiés restent conservés. Le contrat v2 garde la lecture des historiques v1. 189 cas de régression et un cas HTTP supplémentaire passent, ainsi que Ruff. Double import v8 et restauration globale restent suspendus, avec reçus de sauvegarde intacts. Interface de publication et résolution explicite des intentions incertaines restent à intégrer, puis qualification commune et activation. L0–L4 seuls actifs sur 8001 ; L5–L9 en cours. Aucune écriture métier, migration de production, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/document-publication-replacement-focused.json`.

**L5.3 — interface de publication et clôture des intentions incertaines, 7 octobre 2026.** Documents permet de choisir la destination, relire, publier ou remplacer avec sauvegarde, puis consulter les reçus de chaque copie. Après réponse perdue, la commande exacte mémorisée est répétée ; une intention sans reçu préparé peut être clôturée explicitement en conservant tous ses fichiers. Droits lecteur, journaux historiques v1 et transport/restauration suspendus sont préservés. Qualification : 419 React, TypeScript, build et Ruff conformes ; 1345 tests Python / 1 ignoré, sortie 0. Recette réelle sur fichiers fictifs : création et remplacement, rechargement, lecteur et clavier, 18 trames intactes et identité de l’original sauvegardé conservée. Débordement des sélecteurs corrigé et vérifié à 390 px. L’enregistrement final du téléchargement Blob et le partage SMB réel restent non qualifiés. Activation L5 sur 8001 encore à réaliser ; L0–L4 seuls y sont actifs, L5.4–7 et L6–L9 restent au plan. Aucune suppression de données, migration de production, écriture métier, commit ou push. Preuve : `.ui-preview/xpilot-l5/publication-ui-common-checks.json`.

**Résultat final de la qualification Python L5.3.** Le même processus 47559 termine avec 1345 tests réussis / 1 ignoré, sortie 0 en 1473.15 s. Les sources du contrôle UI/publication restent identiques. Avec 419 React, TypeScript/build et Ruff conformes, la qualification commune passe ; téléchargement final du navigateur et activation sauvegardée sur 8001 restent à réaliser. L0–L4 actifs, L5–L9 en cours ; aucun commit/push. Preuve : `.ui-preview/xpilot-l5/publication-ui-python-full-terminal.json`.

**L5.3 — raccordement du démarrage ERP9 qualifié sur copies.** Le démarrage explicite valide les deux groupes documentaires avant toute DDL, installe quatre tables de formulaires et six tables de lots avec vingt protections après une sauvegarde commune, puis enregistre ERP9. Imports et création générique ne remplacent pas les installateurs. Aucun formulaire, réglage ou lot n’est créé implicitement. Onze cas de démarrage passent, ainsi que les régressions déjà exécutées et Ruff ; la suite complète du raccordement continue sur la session 12398. La qualification précédente du parcours de publication termine à 1345 Python / 1 ignoré et 419 React. Sur snapshots actuels, les dix projets et 125896 cellules historiques sont conservés ; HTTP et second démarrage sont neutres. Le candidat conserve 377 fichiers canoniques et vérifie l’équivalence de 409 sources produit/tests. Deux écarts de fichiers racine sont explicitement revus : aucun pin/hash existant retiré, une notice de provenance ajoutée. Régression complète, sauvegarde/restauration coordonnée, activation et vérification sur 8001 restent à terminer. Le geste final de téléchargement navigateur et le SMB métier restent non qualifiés. L0–L4 seuls actifs, L5.4–7 et L6–L9 restent au plan ; aucune écriture canonique, suppression de données, opération XPilot8000, commit ou push. Preuve : `.ui-preview/xpilot-l5/erp9-registration-progress.json`.

**Régression complète du raccordement ERP9 terminée.** Le processus12398 termine avec 1356 tests Python réussis / 1 ignoré, sortie0 en 1496.34s ; rapport JUnit et sources vérifiés. Le démarrage et la conservation des données sont déjà qualifiés sur copies, ainsi que Ruff et le frontend inchangé (419 React/TS/build). Sauvegarde/restauration coordonnée et activation vérifiée sur8001 restent à réaliser ; le téléchargement final navigateur reste non qualifié. L0–L4 actifs, L5–L9 en cours, aucun commit/push. Preuve : `.ui-preview/xpilot-l5/erp9-full-python-terminal.json`.

**L5.4 — socle notes et recette HTTP dans le worktree, 7 octobre 2026.** Trois tables et neuf protections SQL conservent notes, versions et références de pièces ; le contenu structuré fermé couvre texte mis en forme, titres, listes/cases, tableaux et références d’images gérées. Création/édition/restauration utilisent une commande stable et une révision ; réponse perdue et concurrence n’ajoutent pas de doublon. Les captures, acteurs et reçus sont immuables ; seul le gel monotone d’une ancienne commande est autorisé pour la restauration. L’historique HTTP est paginé en métadonnées, avec lecture séparée d’une version. 37 cas notes/core/HTTP et Ruff passent ; 244 régressions archives/sauvegardes passent (groupes se recouvrant ; les derniers ajouts du service notes sont couverts par les 37 cas actuels). Sur snapshots des dix projets actuels, démarrage, lectures et refus de création conservent exactement les bases, sans table/ligne de note, backup implicite ou worker ; ERP reste en version9. Suite complète en cours sur65938 (PID30844, JUnit notes-core-full-python.xml). Frontend inchangé, précédent contrôle419 React/TS/build. Les API ne sont pas enregistrées sur le serveur actif ; éditeur/autosave, stockage réel des pièces, import XPilot et transport v9/restauration globale restent à réaliser. Les anciens transports refusent provisoirement les notes peuplées avant sortie, au lieu d’omettre leurs historiques ; ce refus sera remplacé par le transport complet. L0–L4 et le socle Documents restent actifs sur8001 ; notes, comptes, visas et L6–L9 restent en cours. Aucun changement applicatif canonique, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-core-progress.json`.

**L5.4 — pièces jointes de notes en recette, 7 octobre 2026.** Le worktree ajoute stockage géré et API multipart interne : 5 Mio par fichier, 20 pièces/25 Mio par note, copies sans écrasement, empreinte contrôlée et réponse perdue rejouée sans nouveau fichier. Les copies non validées en base restent conservées. PNG/JPEG/WebP sont décodés et bornés (image statique, 16 millions de pixels) avant aperçu ; Office et autres formats restent des téléchargements, avec noms sûrs et en-tête nosniff. 15 tests fichiers/HTTP et Ruff passent. La suite complète65938 signale des échecs : une fixture v5 ajoutait les tables dormantes de notes à un ancien format. La correction garde le validateur strict ; 100 cas v5/core passent (groupes se recouvrant). La suite complète lancée avant cette correction et ces ajouts ne qualifie pas l’arbre courant ; laisser son processus terminer puis contrôler le résultat et lancer une qualification du nouvel état. Aucune API de notes/pièces n’est enregistrée sur8001. Import volontaire XPilot/Office, transportv9/restauration globale, éditeur/autosave et activation restent à réaliser. Documents restent actifs ; racines réseau réelles attendues. Aucun changement canonique, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-files-progress.json`.

**L5.4 — résultat terminal de la régression initiale.** Session65938 terminée : 1335 tests réussis, 58 échecs, 1 ignoré ; les échecs concernent les fixtures v5 de contrat/store, qui ajoutaient les tables dormantes de notes à un ancien format. La correction est qualifiée par100 tests ciblés ; 15 cas fichiers/HTTP passent également. Ce résultat initial ne qualifie pas le code corrigé ni les pièces ajoutées ensuite ; une nouvelle suite complète est requise. Aucune activation des notes, modification canonique, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-initial-full-terminal.json`.

**L5.4 — nouvelle qualification complète lancée.** Après le résultat terminal65938 et la correction des fixtures v5, la suite de l’arbre courant utilise session10312 (PID30592), rapport `notes-corrected-full-python.xml`. Sources figées dans `.ui-preview/xpilot-l5/notes-corrected-full-running.json` ; ne pas arrêter/recommencer ce processus sur un simple délai d’observation. Résultat encore en cours, pas une qualification complète acquise. Import/transport/éditeur et activation des notes restent à réaliser ; Documents restent actifs sur8001. Aucun changement canonique ni commit/push.

**L5.4 — import volontaire préparé hors sources figées.** Prototype de recette dans `.ui-preview/xpilot-l5/notes-import-stage/` : conversion TipTap fermée, aperçu des fichiers explicitement sélectionnés, empreinte source et empreinte de la décision, historique complet déclaré contrôlé, repli texte choisi explicitement. Les blocs/styles non représentables bloquent l’import riche ; aucune URL d’image n’est téléchargée. Les acteurs source restent des descriptions, et les auteurs historiques absents ne sont pas inventés. Un conteneur indépendant conserve tous les octets sélectionnés (JSON/html/txt, versions, pièces), sans extraction et avec inventaire vérifié. Office reste en consultation/téléchargement. Limites préparées : 200 fichiers/50 versions/50 Mio de sources, 2 Mo par contenu, 20 pièces/25 Mio avec5 Mio par pièce ; Office externe seul et originaux sont distincts de cette dernière quota. 54 cas de conversion/aperçu/conteneur et Ruff passent. Ce prototype n’est ni installé ni inclus dans la suite complète10312 : ses247 fichiers runtime restent exactement figés, et le processus PID30592 continue. Il reste à raccorder acquisition bornée, provenance SQL immuable et copie/reprise/idempotence, puis archivev9/restauration, éditeur et activation. Aucun endpoint d’import disponible sur8001, aucune modification canonique ou source XPilot, suppression, commit ou push. Preuve : `.ui-preview/xpilot-l5/notes-import-stage-progress.json`.

**L5.4 — format réel de l’éditeur XPilot vérifié.** `ProjectDocumentsPanels.tsx` utilise contentEditable/execCommand et sauvegarde HTML + texte, sans mettre nécessairement à jour le JSON TipTap généré par le backend. Il insère aussi les images en dataURI et les cases de liste dans le HTML. Le prototype refuse désormais un JSON dont le texte diffère du contenu source actuel ; aucun ancien contenu n’est choisi silencieusement. 55 cas et Ruff passent dans un rapport distinct `notes-import-stage55-python.xml`, qui remplace les 54 cas préparatoires. Le rapport de ces54cas avait été réutilisé pendant la révision : utiliser uniquement le reçu55courant pour les hashes actuels. La conversion HTML fermée, l’acquisition des images intégrées en blobs décodés, le style barré, la provenance/copie SQL et le parcours complet restent à réaliser. Ces prototypes sont hors des247sources figées de la suite complète10312, toujours en cours ; aucune activation ou modification canonique. Preuve : `.ui-preview/xpilot-l5/notes-import-stage55-progress.json`.

**L5.4 — socle notes/fichiers entièrement qualifié, encore dormant.** Session10312 terminée exit0 : 1408 tests Python réussis/1 ignoré,1504.56s ; les247sources figées restent identiques, Ruff conforme. La correction de fixturev5 est incluse, sans assouplir les archives. Le prototype d’import55cas est séparé et n’était pas inclus dans cette suite ; HTML réel/dataURI/style barré, provenance SQL/copie gérée/reprise, archivev9/restauration globale, éditeur/autosave et activation restent à réaliser. Aucune API de notes/pièces/import n’est enregistrée sur8001, qui conserve Documents/ERP9. Aucun changement canonique, suppression, commit/push. Preuve terminale : `.ui-preview/xpilot-l5/notes-corrected-full-terminal.json`.

## Favicon de l’interface

`web/public/assets/agent-favicon.svg` est copié par Vite dans `web/dist/assets/`. Le lien de `web/index.html` utilise le montage `/assets` existant : aucun service supplémentaire. Vérifier une réponse HTTP 200 avec le type `image/svg+xml` et la présence du lien `rel="icon"` dans la page servie.

## Apprentissage de l’écartement

`python -m scripts.learn_discarded_mail` inspecte les sauvegardes d’écartement en lecture seule ; `--apply` sauvegarde SQLite puis enregistre les empreintes manquantes. Aucun contenu de mail n’est restauré. Les prochains écartements mémorisent les empreintes dans la transaction existante. `/v1/mail/page?scope=pending` et `/v1/triage/queue` retournent `discard_suggestion` (probability nullable, discarded_samples, retained_samples, reason, estimated). Tests : `python -m pytest tests/test_mail_discard_learning.py tests/test_mail_discard.py tests/test_triage.py tests/test_mail_auto100.py -q`.

## Usage des projets dans Mails

`GET /v1/mail/project-usage` lit les audits de classements actuels des mails conservés. Chaque source compte une fois, à la date de son dernier classement : poids exp(-jours/30), hors mails écartés et anciennes destinations. Les vignettes proposées utilisent d’abord les scores du mail courant ; le poids d’usage sert au repli sans score et aux départages. Le menu est trié par confiance. Les destinations non évaluées n’affichent pas de pourcentage inventé. Vérification : `tests/test_mail_project_usage.py`, tests frontend `mailFocus`, `MailWorkspace` et `MailApp`, TypeScript et compilation Vite.

### Lecture des mails — 11 octobre 2026

La barre Mails réunit recherche, navigation et analyse. Le lecteur affiche l’objet,
une ligne expéditeur/date puis le corps, sans bloc de classement entre les deux.
« Détails du mail », fermé par défaut, contient les coordonnées complètes,
la préparation d’une réponse et le téléchargement de l’original. Le petit panneau
de droite réunit destination, validation et vignettes. Jusqu’à quatre projets
restent visibles selon les scores du mail courant ; sans score, les destinations
récentes n’affichent pas de pourcentage inventé. Les autres se déplient dans
« Tous les projets ». Sous 540 px de largeur disponible, le lecteur vient avant
les projets. Le mail se glisse depuis son en-tête ou son corps ; cliquer une
vignette sélectionne la destination, « Classer et suivant » valide. Un échec
garde le mail ouvert et affiche l’erreur.

Les coordonnées du mail distinguent De, À et Copie depuis le fichier EML original, avec repli explicite sur les destinataires enregistrés si cet original manque. Le détail expose sender, recipients et attachments (index, filename, mime, previewable). `GET /v1/sources/{id}/attachments/{index}` lit sans extraction sur disque : PDF, images raster et texte brut s’ouvrent dans un onglet ; les autres formats sont téléchargés. `?download=true` force le téléchargement. Les mails écartés répondent 410, les fichiers manquants et index invalides 404. Aucun fichier ni donnée de mail n’est modifié. Tests : tests/test_mail_preview.py.

La vignette DIVERS reste séparée des propositions de projets. « Classer dans Divers », accessible dans Options du mail, affecte directement le mail courant via la même validation que le sélecteur, puis avance après réussite. Un échec garde le mail affiché ; l’action est désactivée pendant une opération ou si DIVERS manque au catalogue.

Le menu « Projet de classement » reste visible en haut du panneau projets,
au-dessus de la destination courante et de « Classer et suivant ». Il propose les
projets ERP/Brain, DIVERS et « Créer un projet… » lorsque la création est disponible.
La sélection prépare la destination ; le bouton confirme le classement.
« Pourquoi cette proposition ? » et « Options du mail » se déplient. L’écartement conserve
son libellé explicite et ses effets sur le contenu. Le suivi d’analyse reste
compact, avec compteur, erreurs et interruption visibles ; Détails/Réduire
conserve son état lors des mises à jour, et Options se referme après le lancement.

## Témoins de connexion des moteurs

La barre globale affiche LLM, Embedding et Mémoire avec état textuel et coloré,
fournisseur/modèle et heure de contrôle. `GET /api/v1/connections/status` retourne
immédiatement les états en cache et déclenche des vérifications indépendantes
en arrière-plan (cache 90 secondes ; interface toutes les cinq secondes lorsqu'elle
est visible). Une modification des réglages invalide le cache ; aucune clé n'est
exposée. Aucun témoin n'est vert par défaut.

Le témoin LLM vérifie que le serveur annonce le modèle configuré, sans tester
l'inférence. Le témoin Embedding demande au serveur EG2 un vecteur sur un texte
neutre et exige 768 valeurs finies formant un vecteur non nul. Le témoin Mémoire
vérifie la lecture locale de l'index et les compteurs de projections en attente
ou en échec, sans tester le rappel distant. Ces contrôles ne modifient pas les
projets ni leurs passages. Le test complet Mémoire dans Réglages reste nécessaire
pour vérifier indexation, rappel et nettoyage. Tests : `test_connection_health.py`
et `ConnectionStatus.test.tsx`.

Le bouton « Tester » des réglages IA actualise immédiatement le témoin LLM, en succès comme en échec. Le résultat manuel est prioritaire pendant 90 secondes pour les réglages testés, même si un ancien contrôle finit ensuite ; un changement de configuration le rend inapplicable. Le test OpenAI compatible confirme une réponse non vide ; le test Ollama confirme la joignabilité du serveur. Les témoins Embedding et Mémoire restent indépendants. Le bouton est désactivé pendant le test. Qualification : 32 tests Python ciblés, 478 tests React, Ruff et build conformes ; clic réel vérifié sur Agent puis retour à l’accueil avec le résultat manuel dans le témoin. La suite Python globale n’a pas été relancée pour cette correction.

## Seuil de classement automatique des mails

Réglages → Mails : seuil modifiable entre 1 et 100 %, 75 % par défaut. Le champ API `mail.auto_classification_threshold` utilise une fraction (0.75 = 75 %) et passe par PUT /v1/settings/mail ou PUT /api/v1/brain/mail-settings. Dès la prochaine analyse/import, une suggestion de projet réel avec confiance supérieure ou égale au seuil est classée automatiquement ; les suggestions inférieures restent à valider. Les choix humains, les mails écartés, Divers et les propositions contradictoires sont préservés. L’audit enregistre le score et le seuil utilisés ; les anciennes traces à 100 % restent intactes. Le classement conserve l’enrichissement différé. Les modifications partielles d’autres paramètres conservent le seuil enregistré. Le script `python -m scripts.auto_classify_mail` consulte les suggestions existantes ; `--apply` les classe selon ce même seuil après sauvegarde SQLite. Changer le réglage seul ne relance pas l’analyse des mails déjà analysés. Tests : test_mail_threshold.py, test_mail_auto100.py (seuil 100 % explicite), MailSettingsForm.test.tsx.

Le choix automatique exige un candidat unique : une égalité entre projets reste
en attente de décision humaine, y compris lorsque les scores atteignent le seuil.

## Reprise globale de la mémoire (2026-10-07)

Réglages → Mémoire et Traitements proposent « Reprendre les indexations en échec »
avec compteurs, progression et bilan. `GET /v1/settings/memory/recovery` lit l'état ;
`POST` sur la même route lance en arrière-plan une tentative par projection en
échec au début du passage. Les décisions canoniques et les projections déjà
indexées ne sont pas réécrites. Une interruption conserve la file SQLite.
Les enrichissements mails en échec au stade mémoire sont réconciliés lorsqu'ils
ont toutes leurs projections indexées. Les erreurs restantes peuvent être reprises
par une nouvelle demande, ou par le worker automatique.

Sous Windows, le backend utilise un Job Object pour terminer ses processus enfants
avec lui ; cette protection générale reste conservée. Elle ne crée pas de moteur
mémoire supplémentaire. Tests : `test_memory_recovery.py` et `MemoryRecovery.test.tsx`.

Reprise mémoire depuis un projet : dans **Connaissance**, **Reprendre les projections** affiche immédiatement une attente et bloque les doubles clics. Le bilan indique les projections indexées, en échec et obsolètes purgées, puis actualise les compteurs sans effacer le bilan. La reprise reste limitée à 100 projections du projet par requête ; un HTTP 200 peut contenir des échecs d’indexation. Une erreur réseau est affichée comme une reprise non confirmée et ne modifie pas les classements.

## Vérification du thème des mails

Après une modification des styles, compiler avec `npm run build` dans `web` : Agent 8001 sert `web/dist`. Vérifier Réglages → Apparence → Sombre, puis Mails (dossiers, lecture, sélection et boutons), et le retour au thème Clair. Aucun redémarrage du backend n'est nécessaire pour cette correction CSS.

Vérifier également la lecture à gauche et les projets à droite sur écran large,
puis leur empilement (mail en premier) sous 540 px. Le corps doit suivre
directement l’objet et la ligne expéditeur/date. Recherche, analyse et
précédent/suivant sont dans la barre Mails ; réponse et original sont dans
« Détails du mail ». Vérifier ces actions après déplacement et le repli des
coordonnées. Les dossiers sont accessibles dans Options.

## Équipes eXcent depuis les mails

L’import rattaché et la confirmation de classement complètent l’équipe ERP après le commit Brain, via le lien BrainLink existant, pour les affaires actives hors Divers. Les membres sont des collaborateurs métier, sans attribution de droits techniques. Expéditeur et destinataires À/Copie `@excent.fr` sont dédoublonnés par email ; les en-têtes originaux fournissent le nom, avec repli sur prénom.nom. Les boîtes génériques, personnes sans nom identifiable et archivages sont ignorés. Chaque affectation conserve le source_id dans l’historique d’identité. Une erreur ERP est journalisée sans annuler le classement ; la reprise est idempotente.

Reprise des mails existants : `python -m scripts.sync_mail_teams` donne les volumes ; `--apply` sauvegarde d’abord la base ERP puis ajoute les membres en transaction. Tests : `python -m pytest tests/test_mail_team.py tests/test_mail_learning.py tests/test_project_identity.py -q`. L’indice `project_team` est minoré pour les correspondants partagés ; il ne double pas les indices expéditeur/destinataire déjà appris et ne remplace pas les références explicites.

## Fiabilité des reprises mails — 7 octobre 2026

L'extraction IA et l'indexation mémoire ont chacune leur worker dans Agent 8001.
Le passage extraction → mémoire est persisté et libère le worker IA : un appel
d'embedding lent ne bloque pas l'extraction suivante. La prise de travail vérifie
statut, révision et étape ; après redémarrage, un travail interrompu reprend
à l'étape enregistrée. Reprendre la mémoire ne répète pas l'extraction déjà acquise.
Tests : `tests/test_mail_enrichment.py`, contrats EG2 et reprise mémoire.

Une absence de réponse IA exploitable dans la file durable est maintenant un échec à l’étape `extraction`, repris explicitement ; elle ne devient plus une extraction heuristique annoncée comme terminée. Les autres résolutions de classement conservent leur repli heuristique existant.

Reprise des anciens scores de tri : `python -m scripts.auto_classify_mail` compte aussi les propositions Divers dont un candidat enregistré est sélectionnable au seuil ; `--apply` sauvegarde SQLite puis rattache via le flux canonique et son audit. Une égalité reste en attente. Test : `python -m pytest tests/test_mail_threshold.py tests/test_resolution.py tests/test_mail_auto100.py tests/test_triage.py -q` (45 réussis).

## Reprise automatique de la mémoire — 8 octobre 2026

Agent reprend au démarrage puis en arrière-plan les projections en attente et en échec, par lots de 20. Les tentatives en échec sont datées en base et espacées d’au moins 60 secondes ; le délai du worker augmente jusqu’à une heure si un lot échoue, puis revient à 10 secondes après un lot réussi. La reprise manuelle reste disponible et les classements validés sont conservés. Aucun service supplémentaire : le worker appartient au serveur unique sur 8001.

## Informations de projet retenues par défaut — 8 octobre 2026

Les informations extraites d’une source résolue et rattachée au même projet deviennent immédiatement utilisables dans la connaissance et l’assistant. Le statut canonique reste `validated`, avec `validated_by=auto-default` et `validation_mode=default` exposé par les API : il exprime une information retenue comme vraie, sans prétendre à une confirmation humaine. La source, la provenance et une décision auditée restent conservées.

Dans **Connaissance**, la vue **Informations retenues** est ouverte par défaut. **Déclasser** retire une information de la vérité active sans supprimer sa source ; **Déclassées** permet de consulter l’historique et de **Rétablir** l’information. Le parcours existe également dans la rubrique Connaissance de chaque projet. Les anciens refus et reports sont préservés. Les propositions `project_attach` et les sources non résolues gardent leur parcours de rattachement. Une réextraction ne réactive pas automatiquement une information déclassée identique. Une contradiction ne remplace jamais silencieusement une confirmation humaine : les valeurs restent traçables et peuvent être déclassées individuellement.

`app/services/knowledge_defaults.py` applique cette règle à l'extraction et reprend
au démarrage les propositions informatives éligibles. Les connaissances canoniques
sont lues directement en SQL pour le rappel `truth` ; leur acceptation n'ajoute
pas un appel LLM ou d'embedding par information. Les sources restent indexées
comme preuves EG2. `truth_items` compte les connaissances canoniques actives ;
`truth_projections` conserve le suivi technique des projections, sans certifier
un index vectoriel de vérité. Les validations CDC et documentaires conservent
leur gouvernance propre.

Commandes : `POST /v1/projects/{pid}/knowledge/{kid}/invalidate` ou `/restore`, avec le corps `{"actor":"validator","comment":"motif facultatif"}`. Le relais ERP est `/api/v1/projects/{erp_pid}/brain/knowledge/{kid}/{action}`. La lecture accepte `status=validated|invalidated|all`. Les contrôles d’opérateur et de portée projet s’appliquent ; restaurer une information dont aucune source ne relève encore du projet renvoie 409. L’assistant exclut les vérités déclassées et les extraits de preuve contenant leur valeur exacte ; une paraphrase sémantique différente reste une limite de ce filtrage.

Vérification : tests de provenance, audit, absence de travaux LLM supplémentaires, refus/report, rattachement, contradictions, déclassement/restauration, source déplacée et filtrage de contexte dans `tests/test_knowledge_defaults.py`. Tests d’interface dans `WorkspaceViews.test.tsx`. Sauvegardes avant activation et rapports dans `logs/knowledge-defaults-20261008/`.

Activation vérifiée sur 8001 : sauvegarde Brain/ERP, 2 275 propositions informatives reprises et 2 249 connaissances distinctes ; 1 387 sources et 11 projets préservés, 1 879 propositions déjà traitées inchangées. Trois propositions informatives de sources non résolues restent à examiner. Le projet permet la pagination par 50 informations ; la recherche mémoire classe tous les résultats pertinents avant de limiter le rappel à 50. Les citations de vérité donnent une source résolue consultable lorsqu’une provenance existe. Réponse LLM utile vérifiée avec références sur une information retenue par défaut. Tests ciblés : 122 premiers tests puis 82 tests mémoire/accès/relais, 53 tests finaux du rappel avec provenance ; interface finale : 475 tests réussis, build réussi. Derniers contrôles de contexte : 21 tests réussis ; interface ciblée assistant/connaissance : 19 tests réussis. Suite Python globale terminée : 1 750 tests réussis, 1 ignoré, 1 échec préexistant (`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`), identique au contrôle précédant cette évolution. Le contrôle global a été lancé avant les derniers ajustements du rappel, de la pagination et du contexte ; ces chemins finaux sont couverts par les tests ciblés et les contrôles API/interface sur 8001. Bilan : `logs/knowledge-defaults-20261008/qualification.json`.

## Qualification historique du secours LM Studio — 10 octobre 2026

57 tests Python ciblés, 5 tests interface,
Ruff et build interface réussis. JSON utile avec serveur principal simulé injoignable ;
arrêt réel du serveur LM Studio puis relance automatique et réponse OK en 6,96 s.
La suite complète a été interrompue ; le test de classement des mails
`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`
reste en échec préexistant, reproduit séparément, dans des fichiers non modifiés.

Le secours vérifie les instances réellement chargées via LM Studio `/api/v1/models`
(`loaded_instances`), et non la simple liste des modèles téléchargés. Un modèle
téléchargé mais absent de la mémoire est explicitement chargé avec `lms load`,
identifiant configuré et contexte de 8192 tokens, avant le premier appel de secours.

La qualification complète de la livraison courante est décrite dans
[le bilan du 11 octobre](#qualification-du-11-octobre-2026).


## Candidat Parakeet CPU2 — résultat isolé du 12 octobre 2026

Le run réel unique a traité les **15 WAV SAPI fictifs déjà scellés** sur CPU2,
avec Sherpa/Parakeet INT8. Le score ORIGINAL reste **28/35 : 23/27 propres et
5/8 dégradés** ; le chevauchement conserve seulement **1/4** attentes. Le pliage
V4 et les motifs sont identiques, sans substitution de transcription ni rescoring.
Deux notations équivalentes ne correspondent pas aux motifs stricts ; cinq autres
champs restent non fidèles ou incertains. Aucun total ajusté ne remplace 28/35.
La phase de fenêtres de cinq secondes n’a pas été exécutée puisque le seuil figé
35/35 sur phrases complètes a échoué. **Candidat NO-GO strict, non activé**.

Chargement : 5,247 s ; deux warmups exclus : 1,184/1,244 s. Sur les quinze phrases
complètes, P50 de calcul 0,717 s et P95 1,284903 s ; durée totale 20,820647 s.
Ces temps de calcul comprennent lecture WAV, features et décodage, et ne mesurent
ni acquisition, file, fenêtre réelle de cinq secondes, SSE, DOM ni séance longue.
Le verdict conditionnel `candidate_compute_latency_passed` reste false ; le seul
P95 mesuré ne le rend pas true lorsque le contrat complet échoue.
Les 89 échantillons portent sur le processus principal : pic RSS OS
1 439 711 232 octets ; les 46,46875 s de CPU cumulé concernent le Job entier,
y compris son conhost Windows, et ne sont pas une durée murale. Exit0/Job0 ont
été attestés naturellement avant fermeture ; handles fermés, erreurs vides.

La [qualification brute](logs/foresight-runtime/parakeet-inference-prepared-20261012-014020-58cab5ae/qualification.json),
l’[analyse descriptive RO](logs/foresight-runtime/parakeet-result-readonly-20261012-015558-d272e0ce/analysis.md)
et la [revue indépendante 22/22](logs/foresight-runtime/parakeet-asr-result-independent-20261012-015550-93a7fc39/review.json)
restent des preuves distinctes : conformité du reçu ne vaut pas qualité industrielle.
L’[échec initial b47](logs/foresight-runtime/parakeet-inference-prepared-20261012-005047-2024a66d/qualification.json)
et ses historiques sont conservés. Le [diagnostic factice R3](logs/foresight-runtime/parakeet-job-probe-prepared-20261012-012044-5a55fba2/qualification.json)
et sa [revue 15/15](logs/foresight-runtime/parakeet-job-probe-r3-result-independent-20261012-014223-774df846/review.json)
qualifient collecte et fermeture de ce Job précis, pas l’ASR, et ne prouvent pas
rétroactivement le comptage absent de b47. Aucun profil produit n’est remplacé.

T12 reste préparatoire : [revue de liaison 8/8](logs/foresight-runtime/manifest-t12-binding-independent-20261012-015631-26544da9/review.json).
Le [précontrôle CUA de visibilité](logs/foresight-runtime/t12-browser-visibility-preflight-20261012.json)
observe false avant puis après `set(true)` : aucun UI_READY, GO, App, STT ou LLM
T12. Une sélection d’onglet masqué ne vaut pas visibilité de transcription ;
le collecteur SSE ne remplace jamais une observation DOM. La réponse à la demande
d’affichage du chat/panneau reste absente à la date de ce reçu. Les portes,
capacités, flags et profils canoniques restent inchangés ; aucun matériel nouveau.


## Candidat Parakeet CPU2/MBS4 — résultat isolé du 12 octobre 2026

Ce complément chronologique concerne un candidat distinct : `modified_beam_search`, quatre chemins actifs, même CPU2/Sherpa/INT8. Il conserve les résultats greedy 28/35 et l’échec initial b47. Les 32 contrôles de préparation du delta restent séparés des 68 historiques.

[Résultat brut](logs/foresight-runtime/parakeet-beam4-inference-prepared-20261012-020751-7a4009e4/qualification.json) : **microrecette refusée dans sa portée technique** ; non rapporté phrases complètes, score original non établi/non établi (propre non établi/27, dégradé non établi/8). Nombre de fenêtres rapporté : non rapporté ; score fenêtres non établi/non établi. Les dénominateurs 27/8 sont les attentes du protocole ; l’absence de synthèse ne signifie ni zéro inférence ni qualité false. Aucun score corrigé ne remplace le brut.

P95 calcul phrases complètes non rapporté dans le reçu brut ; P95 calcul fenêtres non rapporté dans le reçu brut ; durée murale 20,221850 s. Les verdicts conditionnels restent tels quels : qualité full `non établi`, qualité fenêtres `non établi`, calcul `non établi`, cleanup `false`. Un champ absent reste non établi, sans chiffre ni booléen déduit. Le calcul exclut acquisition, attente en file et affichage SSE/DOM ; une microrecette fenêtrée ne vaut pas une séance en cadence réelle.

Le complément [analyse RO JSON](logs/foresight-runtime/parakeet-beam4-result-readonly-20261012-021650/analysis.json) et ses [notes corrigées](logs/foresight-runtime/parakeet-beam4-result-readonly-20261012-021650/analysis-corrected.md) constituent une source descriptive SÉPARÉE : 15 phrases complètes et deux warmups observés avant le refus, score strict 28/35 (23/27 propres, 5/8 dégradés), chevauchement 1/4 ; fenêtres réellement observées 0. Les attentes, motifs et transcriptions brutes restent inchangés. P95 calcul full 1,231468 s, chargement 4,573546 s, 91 échantillons : pic RSS principal OS 1 439 678 464 octets, CPU Job 50,28125 s console comprise. Ces mesures ne remplissent pas les champs absents du reçu failed et ne qualifient ni latence, qualité industrielle ou allocation réelle de deux cœurs au processus. Une passe par décodeur ne démontre aucune causalité de performance.

Le dernier relevé séquentiel avant fermeture observe principal exit0, Job2 listant le principal et son conhost. Le garde refuse cet état ; la cause profonde OS ou modèle n’est pas prouvée. Le close final confirme exit0/Job0/handles fermés et erreurs vides, mais aucune attestation naturelle Job0 AVANT close n’est présente. Le reçu reste `passed=false`, `cleanup_qualified=false` ; absence de preuve ne devient pas affirmation de terminaison naturelle ou de cause du refus.

La [revue indépendante du résultat](logs/foresight-runtime/parakeet-beam4-result-independent-20261012-022026-c9be0811/review.json) vérifie 20 points de conformité RO, sans qualifier la recette échouée. Le reçu conserve les états observés, Job, handles et erreurs tels que mesurés, sans extrapoler un échec partiel. Aucun gate industriel/UI/T12 ni profil canonique n’est modifié ; cette liaison n’exécute ni modèle, audio, matériel ou application.

## Reprise des notes vocales — 12 octobre 2026

Le Studio expose la capture et l'import pour les séances de type `note`,
déjà acceptées par les commandes backend. Le modèle de données reste
identique et aucun rattachement projet n'est nécessaire pour conserver la
note ou sa transcription. La publication métier reste explicite.
L'enrichissement automatique traite séparément le refus d'admission IA
avant génération : état `waiting` et reprises à 15, 30 puis 60 secondes.
Les véritables erreurs d'inférence, de contenu ou de citation restent des
échecs nécessitant une action. Les demandes manuelles sont prioritaires.
Un échec de démarrage MediaRecorder libère le micro et le verrou et remet
au mieux la séance en pause, pour permettre une nouvelle tentative.
La précision industrielle du direct reste à qualifier sur une réunion réelle.

La globale UNION V2 est terminale en échec ENOSPC : rapport final absent, XML tronqué, aucun compte JUnit. Les sources sont inchangées. [Compagnon terminal](.ui-preview/pilots/native-ready-union-20261012/qa/python-global-union-v2/root-terminal-no-space-companion.json). La cause reste inconnue malgré environ 4,9 Go libres après fin ; aucune suppression pour libérer de la place. La V3 surveillée est préparée, sans nouveau lancement.


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


**Complément L12 du 13 octobre 2026, sur copie uniquement :** correctif
d’exclusion des captures Windows/navigateur testé (81 ciblés backend,
873 frontend, TypeScript/compilation). Régression Python globale encore à
exécuter avant activation. Mesure voix → premier texte visible préparée
et testée, sans P95 réel. État dans `docs/38_FORESIGHT_DELIVERY.md`.


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


### Protection des sauvegardes préparatoires — 13 octobre 2026

L’autorisation utilisateur a été appliquée uniquement à
`C:\Agent\.ui-preview\backups` : 66 éléments, dossier racine compris,
trois sauvegardes et 43 fichiers. Les autorisations Allow pour `S-1-5-32-545` (Users) et `S-1-5-11`
(Authenticated Users) ont été retirées. Les droits de Fred (SID terminé par
`6448`), SYSTEM, Administrators et des deux SID techniques sont conservés ;
les propriétaires et les SHA-256 des fichiers de sauvegarde restent identiques.
Les ACL de `project_brain.db`, de la base ERP `.minipilot/minipilot.db` et de
`storage/eg2/index.db` sont inchangées. Les nouvelles archives documentaires
continuent d’utiliser le dossier privé `Documents/AgentBackups` déjà vérifié.
Cette opération n’ajoute aucune sauvegarde de base et ne qualifie pas L12.
Preuve : [reçu final](logs/foresight-runtime/backup-access-protection-20261013-dc8cdf0113eb4120b53b7f1b1275a643.json).


### T12 : choix réseau et premier lancement V6 — 13 octobre 2026

La variante de recette V6 suit le choix utilisateur du primaire
`http://192.9.110.115:1234`, modèle `google/gemma-4-26b-a4b-qat` : mode produit
`network`, profil ASR CPU inchangé, quinze WAV fictifs, 1224 occurrences scellées,
quinze demandes LLM réparties dans trois fenêtres. Le catalogue OpenAI frais
`/v1/models` vérifie l’ID exact : `advertised_catalog_ready=true`,
`remote_loaded_state_measured=false`. La génération doit être constatée par les
demandes réelles ; aucune exigence Native LM Studio distante n’est substituée.

Le [premier reçu terminal V6](logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-075610-78025914/controller-final.json) conserve `passed=false` : délai
d’affichage Transcription dépassé avant le modèle, `driver_exit=null`,
`fixture_exit_code=0`, Job vide et handle fermé, monitor/watchdog terminés.
Le [relevé séparé du retour réseau](logs/foresight-runtime/network-recovery-live-20261013-42465a494ce140b9902f7ab10695302b.json) constate le catalogue
primaire et zéro instance du Gemma local, sans génération ni requête de
chargement/déchargement par l’observateur. La préparation/readiness ne démontre
pas une heure passée ; T12, P95, qualité ASR et L12 restent non qualifiés.


### T12 V6 : exécution partielle terminée — 13 octobre 2026

La [séance réelle](logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-083158-7af6eacb/controller-final.json) a tenu 3600,094 s, de
10 h 36 à 11 h 36 (Paris) : 1440 fragments uniques, six contrôles de conservation
réussis, bases fictives inchangées pendant le postflight en lecture seule et
zéro création de réunion/action/tâche ERP. Le rejeu mic/120 conserve le même
reçu et ne crée aucun fragment supplémentaire. Driver et fixture quittent avec
code 0 ; Job vide, handle fermé, watchdog/monitor/collector terminés, sans arrêt
forcé ni tardif. La gate d’exécution atteste le DOM Transcription ; l’extérieur
reste explicitement `false`, sans changement des critères d’acceptation.

ASR : 99 fragments `completed`, 1341 `retained`, 123 segments bruts. Sur 1224
occurrences, 83 sont notées et 1141 restent inconnues : 192 contrôles de motifs,
108 retrouvés et 84 non retrouvés, couvrent les 35 faits. Ces valeurs ne sont
pas une précision globale ; les valeurs/unités et le débit CPU à deux pistes
ne sont pas qualifiés. P95 : zéro mesure, 1224 manquants. Le workload comporte
15 demandes logiques et neuf dispatchs : trois réponses, six annulations locales,
trois enrichissements rejetés 502, trois expirations proactives attendues après
2 s. La priorité globale et l’arrêt du calcul distant ne sont pas qualifiés.

L’[assemblage séparé après arrêt](logs/foresight-runtime/t12-post-recipe-consolidation-20261013-7af6eacb.json) produit deux WAV de 3600 s,
115200044 octets chacun (230400088 au total), avec les 1440 sources et les
métadonnées inchangées. Le [nouvel observateur](logs/foresight-runtime/network-recovery-live-20261013-c5a92111952943a3a3e5f53e43b3117d.json) confirme zéro instance
Gemma locale et le catalogue primaire exact ; il ne génère rien et ne demande
aucun chargement/déchargement. [Audit terminal](logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-083158-7af6eacb/independent-terminal-partial-audit-v6.json).
T12/L12, ASR industriel et premier texte visible/P95 restent non qualifiés.


### Enrichissements : diagnostic et candidat structuré — 13 octobre 2026

Le diagnostic séparé reçoit 14 ajouts (HTTP 200), puis les refuse ; un nouveau
pilote structuré produit 12 ajouts aux citations verbatim vérifiées en un seul
POST. Ces essais ne reconstruisent pas les trois 502 de l’heure T12. La présence
de valeurs ASR erronées (« 16 MHz », « 2250 W ») limite le résultat au format.

Dans le candidat isolé non activé, `chat_text(response_format=...)` choisit
le transport avant son unique POST, sans retry vide ni second appel de secours.
Le manuel conserve le choix et le chargement du secours autorisés par les
réglages existants ; l’automatique conserve secours et autostart désactivés.
Les appels sans cette option et les autres fournisseurs gardent leur voie
héritée. La validation refuse dépassement de 12, fausses citations et doublons
normalisés, compare la note complète et conserve la récupération des anciens
reçus Notes. Une note seule produit localement zéro ajout, sans génération ;
une nouvelle acceptation vide ne crée aucune version de note. QA et promotion
restent à terminer. [Résultat du pilote](.ui-preview/pilots/t12-structured-additions-probe-20261013/result.json)
; [diagnostic distinct](.ui-preview/pilots/t12-enhancement-502-diagnostic-20261013/one-shot-root-reviewed-v2/diagnostic.json).

### QA logicielle et présentation du candidat V2 — 13 octobre 2026

ROOT a obtenu 887 tests frontend passés (83 fichiers, zéro échec ou test en
attente), TypeScript et compilation passés, ainsi que Ruff sur la copie privée
`app backend/app tests`. Le premier lancement Vitest a échoué avant les tests
avec EPERM ; la reprise réussie est conservée séparément. Les 37 unités fictives
passent. Le premier pytest global conserve 435 réussites et un échec lors de
la création d'un chemin temporaire Windows de 287 caractères, avec le parent
présent et LongPathsEnabled=0. La reprise courte de 2444 cas est encore en cours :
aucun passage global n'est revendiqué. [Reçu ROOT](.ui-preview/pilots/t12-enhancement-schema-candidate-v2-20261013/qa-root-observed-20261013.json).

La [revalidation locale V2](logs/foresight-runtime/t12-structured-response-v2-offline-revalidation-20261013.json)
lie la réponse réelle antérieure et le service candidat `2e044f24…` : messages
et schéma identiques, douze ajouts validés, zéro nouvel appel réseau, aucun SQL.
Elle ne teste pas le callback réseau V2 en exploitation et ne valide pas les
valeurs industrielles reprises de l'ASR.

L'UI candidate explique le résultat vide sans accepter un bloc inexistant,
conserve les états historiques des propositions et distingue le direct suspendu
des passages restant à transcrire après arrêt. Aucun nouveau statut serveur,
démarrage de capture ou relancement STT n'est ajouté. Promotion, qualification
ASR/P95, T12 et L12 restent en attente ; les anciens reçus restent intacts.
### QA Python : état avant continuation, non publié — 13 octobre 2026

V1 conserve 435 réussites nommées dans son XML et l'échec du chemin Windows de
287 caractères. V2 a été arrêté après 1974,77 s (environ 33 min), exit 92,
`disk_reserve_reached`, avec un minimum disque observé de 2077769728 octets.
Ses 382 sources Python et 74 ressources restent inchangées. Le JUnit final
est absent, les imports finaux privés et la vérification finale d'isolation
n'ont pas été validés après interruption. Les points de progression ne sont
pas des réussites nommées ; aucun nombre de cas V2 terminés ni passage global
n'est revendiqué. Le processus appartenant au harnais est terminé et le Job
est vide. [Reçu V2](logs/foresight-runtime/notes-ai-python-v2-disk-stop-root-observed-20261013.json).

La [continuation préparée](.ui-preview/q/nac3/preparation-v1.json)
sélectionne 2009 cas parmi la collection attendue de 2444, en conservant les
435 réussites nommées de V1. À l'état documenté, elle n'a pas été exécutée ;
son résultat et l'agrégation exacte des noms restent à vérifier. La préparation
lie les mêmes 382 sources et 74 ressources, les sélections et les reçus V1.

ROOT a compressé une ancienne QA fictive fermée : 8602 fichiers, zéro
suppression, mêmes empreintes de contenu avant/après (`19d597a3…`). La variation
observée pendant cette opération est précisément 6530973696 → 9470754816 octets
libres. La remontée antérieure et la perte précédente d'environ 4,2 Go ne lui
sont pas attribuées. [Reçu de compression](.ui-preview/pilots/closed-qa-compression-20261013/result.json).

Les preuves logicielles restent : frontend 887/887 dans 83 fichiers, 37 unités
fictives, Ruff, TypeScript et build. Le candidat notes et son UI ne sont pas
activés. Le pilote réel de douze ajouts et sa revalidation locale V2 restent
limités au format du contexte fictif ; les valeurs ASR erronées citées restent
non qualifiées. Aucun résultat logiciel ne clôt la recette historique d'une
heure, la mesure visible/P95 ou la qualité ASR industrielle. T12/L12 restent
ouverts ; les anciens reçus d'heure, CUA, ASR et premiers essais restent intacts.
### Qualification logicielle finale et diagnostics CPU — 13 octobre 2026

La continuation terminée contient 2009 cas nommés : 2007 réussites, 2 exclusions
prévues, zéro échec ni erreur. Elle a duré 2954,329 s, avec 7101038592 octets
libres au minimum. Les 382 sources Python, 74 ressources et 4 auxiliaires restent
inchangés ; imports privés avant/après, garde d'isolation, EOF, lecteurs et Job
fermé sont vérifiés. L'agrégation exacte avec les 435 réussites nommées V1 couvre
2444 noms uniques : 2442 réussites, 2 exclusions prévues, zéro manquant ou nom
inattendu. Ce sont deux exécutions avec les mêmes sources, sans passage
monolithique revendiqué. [Continuation](.ui-preview/q/nac3/qa/python-continuation-notes-ai-v1/qualification.json)
; [agrégation](.ui-preview/q/nac3/qa/python-aggregate-notes-ai-v2.json)
; [audit indépendant des composants](.ui-preview/q/nac3/qa/independent-terminal-notes-ai-continuation-v1.json).

Le premier calcul d'agrégation a refusé le changement de nom d'une garde. La
reprise vérifie uniquement l'alias littéral `owned_pytest_metadata_notes_ai_v1.py`
vers `owned_pytest_metadata_notes_ai_v2.py`, avec les mêmes octets `7cda11b4…`.
Le helper revu `279e8fe0…` a produit l'agrégation ; les gardes restent inchangées.
Les premiers essais V1 (échec de chemin), V2 (réserve disque, exit 92) et le
premier refus d'agrégation restent conservés. Les exclusions nommées sont
`test_finalize_mix_preserves_both_tracks_and_offsets` (runtime audio optionnel
absent) et `test_infomaniak_eml_parses` (dossier Infomaniak absent).

Le premier essai CPU3 a échoué à l'exécution, avec une cause inconnue conservée.
Le nouvel essai traite 3 phrases complètes en 13,442 s : 230 volts, 16A, 0,2 mm
et 1,5 m apparaissent correctement dans les textes choisis, mais 1250 W devient
2250 W. Les 4 motifs acceptés sur 6 ne sont pas un taux de précision : le motif
courant refuse « 16A » et le motif d'éclairement accepte le préfixe de « luxe ».
[Interprétation CPU3](logs/foresight-runtime/t12-cpu3-root-interpretation-20261013.json).

La comparaison suivante reprend les mêmes 15 WAV fictifs dans deux variantes,
avec un vocabulaire industriel sans chiffres attendus injectés : 30 résultats,
zéro demande manquante, 77,704 s, Job fermé et empreintes inchangées. Les motifs
figés donnent 25/35 sans vocabulaire et 23/35 avec vocabulaire, sans mesurer une
précision générale. La graphie « lux » s'améliore dans le cas choisi ; l'erreur
1250 W → 2250 W demeure dans les deux variantes. Le premier précontrôle refusé
pour alias de chemin reste conservé, sans démarrage du modèle. **Le vocabulaire
n'est pas activé et la transcription canonique reste inchangée.**
[Interprétation comparée](logs/foresight-runtime/t12-cpu-domain-paired-root-interpretation-20261013.json)
; [résultats](logs/foresight-runtime/t12-cpu-pair-30c71d2af642453c8f9f821705f8b0fe/diagnostic.json).

Ces WAV complets passent par le décodage AV canonique vers 16 kHz, y compris
l'entrée téléphonique 8 kHz. Ce traitement diffère du flux historique doublé
linéairement. Les diagnostics sont synthétiques, CPU uniquement et concomitants
à la QA Python ; ils ne qualifient ni les performances ni la cause exclusive
des erreurs de l'heure. Physique, multipiste, ASR/P95, T12 et L12 restent non
qualifiés. L'activation du correctif notes/Studio attend encore les preuves ROOT.
### Correctif actif : publication, sauvegarde et interface — 13 octobre 2026

ROOT a publié les sept overlays, le JavaScript `index-6orOloRS.js`, puis le HTML
en dernier. Les 382 sources Python et 220 fichiers frontend correspondent aux
copies qualifiées ; l'ancien JavaScript est conservé et le CSS reste identique.
La sauvegarde officielle avant la reprise contient 1003 fichiers (1272800880 octets),
avec empreintes vérifiées et intégrité des cinq SQLite contrôlée.
[Publication](logs/foresight-runtime/notes-structured-source-publication-20261013.json)
; [sauvegarde](logs/foresight-runtime/notes-structured-current-data-backup-20261013.json).

Le nouveau backend a démarré après publication : santé Brain/ERP correcte,
JavaScript HTTP conforme au build qualifié et HTML conforme après normalisation
des fins de ligne. Le premier contrôle a refusé la comparaison HTML brute et le
chemin `/app/assets` ; sa correction utilise le script réel `/assets` et compare
le texte normalisé. Ce refus de contrôle reste conservé. Les empreintes du code
en RAM ne sont pas attestées indépendamment ; son chargement découle des fichiers
publiés avant le nouveau démarrage. [Reprise vérifiée](logs/foresight-runtime/notes-structured-runtime-restart-20261013.json).

Dans la réunion existante « test 1 », le nouveau build affiche « Aucun ajout
utile », les contrôles Source audio, Périphériques, Microphone, Sortie Windows
et « Démarrer la réunion ». Le mode temporaire mixte active les deux sélecteurs,
puis le mode système initial est restauré. Aucun microphone ni enregistrement
n'a été lancé. Toutes les lignes de notes et versions ERP restent identiques à
la sauvegarde. Cette observation de l'interface ne qualifie pas le P95.
[Contrôle UI et conservation](logs/foresight-runtime/notes-structured-UI-current-verification-20261013.json).

Un observateur des métadonnées voit le primaire exact au catalogue et zéro
instance du Gemma local. Il ne génère rien et ne demande aucun chargement ou
déchargement ; l'échange HTTP de déchargement n'est pas capturé indépendamment.
[État réseau/local](logs/foresight-runtime/network-recovery-live-20261013-49a29f7693ea461080f687b6041c6d50.json).
Le correctif notes/Studio est actif et les cinq documents sont publiés.
Aucun commit ni push à cette étape. Physique, multipiste, ASR/P95, T12 et L12
restent non qualifiés ; les premiers essais et l'historique restent conservés.

Le reçu historique du contrôle UI est encodé en Windows-1252. Son
[compagnon UTF-8](logs/foresight-runtime/notes-structured-UI-current-verification-utf8-20261013.json)
conserve les mêmes faits et lie l'empreinte de l'original, laissé intact.

Le [dernier contrôle direct](logs/foresight-runtime/notes-final-readonly-state-20261013.json)
confirme la santé d'Agent, le build servi, le catalogue primaire exact joignable
et zéro instance Gemma locale. Il ne génère rien. Un contrôle antérieur par
accès par défaut a reçu un refus de connexion ; il n'est pas reproduit lors
de l'accès direct sans proxy, sans cause exclusive établie.


### Lecture des mails — 15 octobre 2026
Sources et À trier partagent MessageContent : HTML filtré dans une iframe isolée, tableaux adaptés à la largeur, scripts et ressources distantes bloqués. Le texte simple conserve ses sauts de ligne et son historique repliable. Vérification ciblée : tests MessageContent et compilation frontend.


### Indexation et navigation — 15 octobre 2026
Statistiques et préparation des réunions : Réglages → Autres réglages, dans deux rubriques distinctes. Sources → Indexation des projets affiche la couverture réelle du moteur EG2 configuré, vérifiée par profil et empreinte de contenu, dans le périmètre accessible.
Le classement des mails et les imports alimentent déjà automatiquement EG2 réseau ; les vecteurs restent stockés dans l’index SQLite local. Aucun dossier réseau n’est parcouru. En mode réseau, la recherche de contenu dans Sources réutilise la recherche EG2 habituelle et ne démarre aucun encodeur local. L’index multimodal local reste réservé au mode local explicite ; il n’est ni démarré ni repris en mode réseau. Sa maintenance avancée reste accessible dans les réglages de recherche. Les anciens signalements de quota restent consultables, sans altérer les sources ni les classements.
L’API GET /api/v1/workspace/indexing est en lecture seule et distingue indexées, en attente, en échec, manquantes et sans texte. Tests ciblés de navigation, recherche et indexation ; compilation frontend.


### Présentation originale des mails — 15 octobre 2026
Sources et À trier affichent le HTML MIME original s’il est conservé, avec styles, polices, dimensions et couleurs du message. Les images CID raster sont incluses depuis l’original (2 Mio/image, 8 Mio au total). Les images distantes sont affichées uniquement sur demande. Le cadre isolé conserve les scripts, formulaires et appels réseau bloqués ; sa hauteur suit le contenu. Les artefacts d’indexation, données et classements restent inchangés.
Vérifications : tests mail_preview, MessageContent et lecteurs concernés ; compilation frontend.

### Contexte de transcription relue — 16 octobre 2026

`scoped_assistant.reviewed_recording_context` relit l'enregistrement lié, les droits
Brain courants et la preuve `SourceArtifact` de même révision avant de préparer
le contexte. Une transcription complète non relue suspend l'ancien contexte
provisoire ; une séance sans transcription complète conserve son direct.
`meeting_audio.save_review` archive l'original avant correction, retire les preuves
périmées dès la sauvegarde et émet `transcript.updated`, sans modifier la révision
des notes. La fraîcheur de l'assistant inclut la révision de l'enregistrement.

Vérification : 107 tests ciblés réussis, puis trois cas complémentaires réussis ;
la dernière vérification de droits comporte 21 réussites dont les 11 cas actuels
du nouveau fichier. Ces ensembles se recouvrent et ne constituent pas une nouvelle
suite globale. Ruff passe. Les routes HTTP originales et le LLM réseau répondent
1250 W après correction d'un provisoire fictif 2250 W ; une nouvelle modification
non relue invalide ce contexte. Aucun nouvel ASR, microphone ou GPU dans cet essai.
Preuves : `logs/foresight-runtime/reviewed-transcript-context-delivery-ROOT-20261016.json`.

### Réunion conservée : transcription complète et CR accessibles directement — 16 octobre 2026

Dans le Studio, les onglets Transcription et Synthèse ouvrent maintenant la
relecture complète et le compte rendu sans seconde barre d'onglets audio.
Le lecteur audio demeure disponible. Après création de l'enregistrement lié,
les anciens passages directs restent dans « Historique du direct (texte provisoire) »,
replié par défaut sous la transcription complète. Le direct courant reste déplié.
Les instantanés de source précédant une correction portent un titre historique explicite.

Les changements d'onglet conservent les saisies. Sauvegarder ou valider une
correction de transcription conserve aussi un brouillon de CR humain non publié.
S'il est devenu périmé, ce brouillon reste visible et sa publication est bloquée
jusqu'à remise à jour. Aucune synthèse ni publication n'est déclenchée en ouvrant
une vue ou en validant la transcription.

Vérification ciblée : le premier ensemble conserve 157 réussites et un échec
d'assertion sur la visibilité du CR périmé ; les deux essais intermédiaires sont
conservés. Le test intégré Studio + panneau audio vérifie ensuite le vrai parcours,
la conservation du brouillon après validation et le blocage de publication.
Sur la version finale du panneau audio, ses 15 tests et ce test intégré passent
(16/16). Les ensembles se recouvrent ; aucune nouvelle suite globale 943 ou backend
n'est revendiquée. TypeScript et Vite passent. Les trois assets servis sur Agent
8001 correspondent aux empreintes compilées ; le HTML correspond au texte lu par
mp_index(), après sa normalisation existante des fins de ligne. L'échec initial
du comparateur binaire HTML est conservé ; aucun second déploiement n'est effectué.

Activation statique après sauvegarde complète de web/dist, anciens assets conservés,
sans redémarrage du backend ni modification SQL. Aucun onglet utilisateur rechargé,
microphone, modèle ou GPU. La validation DOM ne remplace ni la recette matérielle
ni une mesure P95 visible ; L12 reste ouvert.

### L01/L04 qualifiés et reprise Notes sans abandon définitif — 16 octobre 2026

`note_evidence_bridge.process_pending` reprend pending/failed/waiting_project
et les anciens exhausted. Le compteur d'échecs est conservé, sans seuil d'abandon20.
Le backoff (60s exponentiel, au plus une tentative par heure après stabilisation)
et le lot de100événements sont conservés. Aucun reset de file, nouvelle version
ou nouvelle identité de source n'est créé par la correction.

Neuf tests ciblés de projection, cinq de versions/citations et un parcours HTTP
global/projet/staging/rejeu passent. Les contrats historiques applicables sont
réutilisés après contrôle d'identité de leurs sources ; aucune suite globale rejouée.
Les compteurs se recouvrent. Ruff passe. Le fonds Notes courant (une note) est vérifié
en lecture seule jusqu'aux deux passages EG2, avec empreintes de contenu/profil.
Activation après sauvegarde Brain/ERP/EG2 et restauration privée ; lignes comparées
non volatiles exactes. Aucune capture, GPU ou génération.

L01/L04 sont clos selon leurs livrables et sorties du plan. Les essais matériels,
le direct industriel et la qualification globale L12 ne sont pas assimilés à ces
contrats logiciels. Détails : `docs/41_FORESIGHT_L01_L04_QUALIFICATION.md`.

### L10 qualifié ; PDF direct des comptes rendus — 16 octobre 2026

Une route GET `/api/v1/projects/{project_id}/meetings/{meeting_id}/pdf` produit
le CR et ses actions avec le moteur ReportLab/Vera existant. Lecture seule,
droits projet vérifiés, texte échappé, réponse privée non mise en cache.
Le téléchargement réutilise AsyncDownloadLink et son indicateur de préparation.
Les CR projet et globaux proposent le lien ; Markdown et PDF RLP restent conservés.

La publication, le rejeu, la provenance et la création explicite d’une Task sont
vérifiés sur bases privées. Le CR reste unique, aucune tâche n’est créée avant
la commande et une seconde conversion est refusée. Trois tests backend,48frontend,
23contrôles d’accès, TypeScript, Vite et Ruff passent. Les ensembles se recouvrent.
Les deux pages de PDF fictif sont rendues et inspectées sans défaut de lisibilité.

Le parcours audio/LLM réel existant est réutilisé après comparaison AST des fonctions
concernées ; pas de nouvelle transcription, modèle ni microphone. Sauvegardes et
restaurations privées des trois bases vérifiées avant activation ; toutes les lignes
non volatiles comparées Brain/ERP sont exactes. Le service8001 et les assets sont
contrôlés. L10 est clos ; L12 reste ouvert. Détail : domaine42.

### L00/L08 qualifiés — 16 octobre 2026

Le dossier39 et le contrat versionné couvrent9écrans et25fonctions. Trois supports
publics officiels sont archivés avec dimensions/empreintes ; les interactions non
montrées sont des spécifications Agent. Pas de parité Mac privée ni ±2px revendiquée.
Le corpus fictif commun est conservé hors production.

Le parcours Sources privé vérifie dossier choisi, réimport/version, labels,
original ancien, absence de fichier sans purge, PDF illisible conservé, import
HTTPS public et lecture de la copie, puis événement ICS choisi/rejoué sans changer
la date de séance. Drive est refusé avant réseau. Le statut indexé est francisé.
Les61contrats backend sur sources inchangées sont réutilisés ;30tests UI actuels,
TypeScript et Vite passent. Ce n’est ni une nouvelle coupure physique ni une suite
globale répétée. Activation statique, assets HTTP exacts et ancien build sauvegardé ;
aucune écriture métier canonique, modèle ou microphone. Voir domaine43.

### L05/L07 qualifiés ; déduplication des questions en recouvrement — 16 octobre 2026

Le proactif regroupe les textes normalisés identiques lorsque leurs intervalles
audio se chevauchent dans la même séance. Les chiffres/mots restent distincts,
sans fenêtre de temps ajoutée. Les segments sont conservés ; un événement
assistant.proactive-duplicate trace question_token et duplicate_of sans nouveau
contenu privé dans le flux SSE. Répétition ultérieure et autre séance restent admises.

Le ciblé affecté47 et le complément inter-séances1 passent ; les deux doublons
échouaient avant correctif. Scopes/historique/contexte relu et saisie UI sont
réutilisés sur leurs sources/fonctions vérifiées avec leurs JUnit107/21/92, sans
cumul ni nouvelle suite globale. Les réponses utiles réelles et l’arbitrage réseau
restent leurs reçus datés ; aucune nouvelle génération n’est lancée.

La lecture LM Studio actuelle constate le génératif primaire chargé et aucun
génératif local chargé. Correction activée après sauvegarde/restauration privée
des trois bases ; lignes comparées non volatiles Brain/ERP exactes. Ruff passe.
L05/L07 sont clos ; qualité industrielle du direct, P95 visible et L12 restent
distincts et ouverts. Détail : docs/44_FORESIGHT_L05_L07_QUALIFICATION.md.

### Précision de comparaison des questions — 16 octobre 2026

La déduplication ignore les espaces et la casse, avec normalisation Unicode,
mais conserve chaque signe de ponctuation. Elle distingue les références
AIRB…-A et AIRB…/A, ainsi que1,5 et1/5. Les deux cas échouaient avant précision ;
les sept cas de déduplication passent sur la version finale. Les autres43cas
du ciblé47 restent leurs preuves acquises, sans nouvelle exécution ni cumul.
La portée inter-séances et les répétitions ultérieures restent conservées.

Correction activée, sans nouvelle génération ni capture. Les sauvegardes SQL
récentes intactes et leurs restaurations déjà qualifiées sont réutilisées après
comparaison exacte des données non volatiles Brain/ERP avant et après redémarrage.
Ruff passe. L05/L07 restent qualifiés ; L12 reste ouvert.

### Indexation visuelle des pages PDF — 16 octobre 2026

Chaque page PDF est ajoutée aux entrées image, avec numéro physique, SourceArtifact,
version et empreinte de l’original. Le texte natif reste une entrée distincte.
La conversion différée utilise PDFium dans un processus sans modèle ; profil de rendu
et cache PNG sont vérifiés avant encodage. Un cache incompatible est conservé et refusé ;
une tentative interrompue sans reçu est conservée et peut être reprise dans un autre fichier.

Les nouveaux imports distinguent ocr_required, partially_extracted et empty.
L’indexation visuelle ne produit aucun texte OCR et les métadonnées historiques ne sont
pas réécrites. Aucune reconstruction de l’index canonique n’a été lancée.

77 contrats backend existants et les5nouveaux cas PDF passent ; les4échecs PDF initiaux
restent conservés et ont conduit à la correction des chemins longs Windows. Les30tests
frontend, TypeScript, Vite et Ruff passent. Les nouveaux cas rendent réellement les PDF,
mais simulent l’encodeur ; les preuves antérieures de l’encodeur réel sont réutilisées.
Activation et comparaison exacte des lignes non volatiles Brain/ERP vérifiées.
L09 et L12 restent ouverts. Voir docs/45_FORESIGHT_PDF_PAGES.md.

### Images et audio avec le LLM réseau — 16 octobre 2026

La préparation multimodale locale et les recherches explicitement choisies Images/Audio
fonctionnent aussi en mode réseau. Le mode et le modèle de génération ne sont pas modifiés.
Dans Réglages > Mémoire > Recherche locale dans les images et l’audio, choisir le projet
et « Vérifier et compléter ce projet » ; dans Sources, choisir ensuite Images ou Audio.
La recherche générale/texte conserve EG2 réseau. Les démarrages réseau n’activent pas
automatiquement l’indexeur local ; la construction ou la reprise restent explicites.

10contrôles backend ciblés,26frontend, TypeScript, Vite et Ruff passent, avec moteurs
simulés dans ces contrôles. Backend8001 et assets activés, sauvegardes vérifiées et
données non volatiles Brain/ERP comparées exactes. Aucun modèle, GPU ni microphone
lancé dans ce raccordement. Les anciennes preuves réelles de l’encodeur restent acquises.
L09 et L12 restent ouverts ; voir domaine45.

### Relations complètes et compteurs mesurés — 16 octobre 2026

La vue des relations propose les pages précédentes/suivantes au lieu de bloquer
l’exploration après200sources. Toutes les citations enregistrées des sources de
chaque page sont conservées, avec les mêmes droits. Les sources indexées sont
comptées dans les index réellement compatibles et actuels ; un reçu de traitement
ne suffit plus. Index illisible signifie mesure indisponible.

Statistiques ajoute les fragments par piste, l’audio direct en attente et l’âge du
plus ancien fragment. Ces mesures ne sont ni une latence d’affichage ni une note
de qualité. Réponses jugées utiles et tokens restent indisponibles sans mesure.
Activation8001 et parcours HTTP du graphe complet vérifiés ; données non volatiles
Brain/ERP comparées exactes. Détail et preuves dans docs/46_FORESIGHT_INSIGHTS.md.
L09, L11 et L12 restent ouverts ; aucun microphone ou modèle n’a été lancé.

### L06 — Studio commun, responsive et lecture au bon repère — 16 octobre 2026

Le projet conserve ses revues et anciens comptes rendus, avec une entrée vers le même
Studio que Réunions. Le projet reste filtré dans `/app/meetings?project=…`, y compris
après rechargement. Les changements passent par la garde de navigation existante.

Les panneaux sont égaux lorsqu’ils tiennent côte à côte, sinon empilés et défilables.
L’intervalle fractionnaire entre670et671pixels est couvert. Les fenêtres1280,800,
671,670et320pixels sont contrôlées dans le navigateur ; le viewport initial est rétabli.

Le lecteur des fragments est dans Transcription, avec son historique, et non caché
dans Préparation. Le seek attend les métadonnées et garde le dernier repère demandé.
L’API audio prend en charge une plage d’octets avec206/Content-Range et signale416
hors fichier. Droits et empreinte des originaux sont vérifiés avant réponse partielle.
Sur un WAV de silence fictif, le navigateur décode10s et démarre réellement à2s.

59contrôles de navigation/projet et95contrôles du Studio passent. Les15nouveaux cas
HTTP passent ; les25contrats de séance restent couverts par17réussites acquises et
8cas rejoués après correction de leurs chemins temporaires Windows, sans nouveau
total global. TypeScript, Vite et Ruff passent. Les échecs initiaux sont conservés.

Les parcours réels sur copies privées vérifient création, brouillons riches et Markdown,
conversion explicite, correction de transcription sans changer le timecode et accès
à la même note depuis le projet. Les fonctions métier héritées sont conservées.
L06 est clos selon ses critères d’interface ; le plan permet l’audio importé avant L03.
Aucun nouvel essai matériel, ASR, GPU ou LLM : L02/L03/L09/L11/L12 restent ouverts.
Sauvegardes et conservation SQL vérifiées avant activation8001. Détail : domaine47.

### OCR des PDF conservés — 16 octobre 2026

Sources → Détails du PDF → « Reconnaître le texte du scan » ajoute le texte des
pages scannées avec son numéro de page et un état de relecture explicite. Le bouton
est aussi visible en grille. Indicateur de travail en cours, pages déjà traitées
réutilisées après interruption, aucune nouvelle limite de RAM/page/durée totale.
L’original, les anciennes extractions et les versions sont conservés ; le nouveau
texte est mis en attente d’indexation dans le mécanisme EG2 habituel. Les limites
documentaires existantes restent applicables. Aucun module CDC hérité n’est réécrit.

L’OCR Windows français/anglais fonctionne sur CPU, sans modèle génératif ni GPU.
Essai réel via HTTP sur un PDF fictif mixte : 4,14 s, valeurs 1250 W et 230 V et
réserve « ne pas valider » reconnues ; anciens artefacts et téléchargement original
inchangés. 71 tests backend et 44 tests frontend/transport ciblés passent, ainsi que
TypeScript, Vite et Ruff. Les suites globales ne sont pas rejouées.
Backend 8001 et fichiers compilés activés après sauvegardes et comparaison SQL.
Huit lots restent clos ; L02/L03/L09/L11/L12 restent ouverts. Détail :
`docs/48_FORESIGHT_SCAN_OCR.md`. Aucun microphone, téléchargement ou LLM lancé.

### L09 qualifié sur ses corpus fixés — 16 octobre 2026

Recherche réelle du produit courant :11/11questions documentaires retrouvent la
source/version et page ou cellule exactes au rang1, avec4/4exclusions. PDF visuels,
scan OCR et tableurs sont couverts ; les preuves acquises de4images PNG et2requêtes
audio sont réutilisées après contrôle du code et du profil. L’index est rouvert,
l’encodeur CPU s’arrête naturellement et les anciens vecteurs restent conservés.
P95 chaud observé sur11questions :0,302s ; essai38,635s, sans génération ni mesure DOM.
Le graphe courant couvre976sources et3555liens connus sur5pages, sans doublon.
27contrôles ciblés index/profils/PDF/graphe/Word/disponibilité passent, Ruff aussi.

Le reçu de qualification attendu par le runtime est maintenant présent : moteur
installé et qualifié, résident arrêté. Aucun modèle n’est relancé pour corriger
cet état. Le mode réseau et les données métier restent inchangés. Pas de nouvelle
capture, transcription, GPU ou LLM génératif. Aucune réindexation globale lancée.
L09 est clos selon ses exigences de corpus fixé et de provenance ; ce n’est pas
une garantie de lecture native CAO, de tous les formats Office ou de toute donnée
industrielle future. Neuf lots sont clos ; L02/L03/L11/L12 restent ouverts.
Correspondance des exigences et preuves : `docs/49_FORESIGHT_L09_QUALIFICATION.md`.

### Diagnostic de préparation des moteurs — 16 octobre 2026

Réglages → Autres réglages → Réunions et transcription distingue installation,
chargement et réponse réelle, capture/STT/recherche/génération et placement réel.
L’inventaire ne lance pas de génération ; le test de réponse est un clic séparé,
avec le seul texte fictif « Réponds uniquement OK », sans repli implicite vers un
autre modèle. Les résultats datés restent associés à l’identité du moteur et
conservés après un échec. Aucun nouveau seuil de RAM n’est ajouté.

19contrôles backend et37frontend distincts sont couverts ; TypeScript, Vite et
Ruff passent. La recette réelle UI constate un serveur réseau non répondant et
signale l’échec explicitement, sans prétendre à une génération réseau réussie.
La capture et la recherche locale restent reconnues. Le direct est installé mais
sa preuve runtime doit encore être traitée ; la transcription des fichiers reste
disponible. Les sauvegardes, la conservation SQL et les assets servis sont vérifiés.
Neuf lots restent clos ; L02/L03/L11/L12 restent ouverts, dont la recette hors ligne
complète actuelle. Détail : `docs/50_FORESIGHT_READINESS.md`.

### Direct CPU : medium disponible en essai — 16 octobre 2026

Le reçu runtime manquant est rétabli après un véritable parcours de3WAV fictifs
jusqu’aux segments SQL, aux événements et aux acquittements rejoués sans doublon.
Small produit une erreur2250W au lieu de1250W ; medium retrouve les6valeurs
annotées. Le medium complet déjà installé devient le défaut CPU du direct,
avec les réglages explicites conservés, sans téléchargement ni activation GPU.
Le décodeur ne change pas ; la sélection seule est différente du pilote vérifié.

Le résultat est plus précis sur ce corpus mais plus lent : environ6,8–7,2s par
fragment chaud,27,4s pour l’essai ; la cible de latence du direct reste non atteinte.
Disponible en essai ne signifie ni qualité industrielle ni latence qualifiée.
81contrôles ciblés et Ruff passent. Sauvegardes et conservation SQL vérifiées,
backend8001 activé, API : medium prêt en essai et non chargé au repos. Aucun
microphone, GPU, LLM ou réglage de génération utilisé dans ces essais CPU.
L02/L03/L11/L12 restent ouverts ;9lots restent clos. Domaine51 pour les limites,
preuves et modalités de retour : `docs/51_FORESIGHT_DIRECT_CPU.md`.


### Corpus medium CPU et conservation — 16 octobre 2026

Les15WAV fictifs sont maintenant couverts (12nouveaux,3réutilisés) :32/35motifs
gelés, un pluriel sans effet métier et deux erreurs réelles dans bruit/chevauchement.
Le direct reste en essai ; L03 et la latence visible restent ouverts. Les fragments,
rejeux et horodatages sont intacts, worker fermé naturellement. Les sauvegardes
Brain/ERP/EG2 sont restaurées et vérifiées ;89/91tables sont exactes, deux journaux
dérivés sont expliqués séparément, données/validations métier conservées. Le global
backend est encore en cours ; aucun succès complet T15/L12 n’est déduit de ces seuls
résultats. Détail : `docs/53_FORESIGHT_CORPUS_PRESERVATION.md`.


### Consolidation T12/T15 — 16 octobre 2026

T15 est clos : le passage backend courant termine avec 2680 réussites, 1 ignoré
(dossier Infomaniak-IA absent), 54 sous-tests réussis et quatre avertissements.
Les 457 sources Python restent identiques. Les avertissements sont conservés :
dépréciation TestClient, deux décodages de sortie de helpers Windows et un
SAWarning de fixture. Les assertions de jonction sont effectivement réussies.
Les sauvegardes/restaurations privées et la classification des deux journaux
dérivés expliquent les écarts ; données et validations métier sont conservées.
Le frontend conserve son global 960/94 fichiers antérieur au correctif T05,
complété par les contrôles ciblés et TypeScript/Vite déjà acquis, sans addition.

T12 est clos dans la configuration observée, par preuves complémentaires des
quatre résultats du plan : heure réelle small CPU/int8/4 threads + LLM réseau
(1440 fragments acquittés et traités), priorité réellement concurrente du
planificateur, puis file SQL actuelle et affichage réel du retard. Sur 28 WAV
fictifs acquittés, 24 restent admis et 4 sont conservés hors direct ; la vue
affiche les deux pistes et l'ancienneté réelle. Le dernier contrôle n'exécute
aucun modèle. Ce verdict ne qualifie ni une heure medium CPU, ni un P95 DOM,
ni 15 réponses utiles pendant l'heure, ni la capture matérielle restante.
L03 et L12 restent ouverts. Aucun nouveau cycle d'une heure ni global backend
n'est nécessaire tant que leurs chemins restent inchangés.

Pièces : `logs/foresight-runtime/T12-T15-current-consolidation-ROOT-20261016.json`
et `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r23.json`.


### Préparation T16 simplifiée — 16 octobre 2026

Le harnais reprend la suite backend déjà réussie (457 empreintes), sans refaire
le global. Il appelle désormais la vraie boucle de capture avec des adaptateurs
inertes : l'échec du journal doit arrêter/fermer le flux, libérer le parent et
conserver tampon/séquence sans faux acquittement. Deux nouveaux tests passent ;
la première invocation interrompue par les droits du répertoire temporaire reste
conservée, avec ses 26 anciens cas réussis. Le retest comporte un avertissement
de cache pytest, sans modification de droits. La relecture indépendante du delta
reste limitée aux sources et ne vaut pas autorisation d'exécution.

Aucun modèle, microphone ou volume lancé. T16 demeure ouvert pour la saturation
réelle du seul volume isolé, dont la création exige l'intervention administrateur
déjà documentée. La recette audio matérielle reste distincte. Les passages longs
et plafonds RAM déjà écartés ne sont pas réintroduits comme conditions de travail.
Pièce : `logs/foresight-runtime/T16-capture-loop-preparation-ROOT-20261016.json`.


### Décodage complet comparé sur les erreurs restantes — 16 octobre 2026

Un court comparatif CPU medium reprend exactement les paramètres du batch
(beam5, VAD, français, sans contexte précédent), sur les deux WAV dégradés en
échec et un témoin1250W/350lux. Il termine en41,913s, sortie0,6/8faits corrects.
Le témoin numérique reste exact ; « conciliation » et l'omission de la réserve
du client persistent. Les annotations ne sont utilisées qu'après décodage.
Le modèle et les457sources produit/tests/scripts restent inchangés. Le direct
conserve son profil ; aucune nouvelle boucle sur ces mêmes réglages n'est utile.

Le modèle turbo présent n'est pas relancé : la comparaison historique documente
déjà sa difficulté sur ce type de chevauchement ; son ancien reçu brut de corpus
est absent et n'est donc pas utilisé pour revendiquer une qualification actuelle.
Les résultats medium bruts restent conservés ; aucun mot n'est corrigé ou ajouté
automatiquement d'après la référence. L03 reste ouvert, CR avec relecture actif.
Pièce : `logs/foresight-runtime/L03-complete-decoder-comparison-ROOT-20261016.json`.


### Saturation audio : message précis et réemploi des preuves — 16 octobre 2026

L'erreur ENOSPC/Windows39 ou112 du processus de capture affiche maintenant
« Stockage audio saturé : capture interrompue », conservation des fragments
acquittés et action pour libérer de l'espace. Elle ne désigne plus le microphone
comme cause. Le code de sortie1 et l'événement error sont conservés ; les erreurs
de permission et de validation gardent leur traitement. Les fonctions réelles
d'acquisition, journal, inventaire et surveillance du parent restent inchangées.

34 tests ciblés et10sous-tests passent, sans avertissement ; Ruff passe.
La première invocation garde ses32erreurs d'initialisation de dossiers privés
et2réussites. Le même passage isolé réussit hors sandbox après autorisation
automatique, sans modifier les ACL ou la politique de sécurité Windows.
La suite globale2680/1ignoré/4avertissements reste le socle acquis : seuls le
script d'erreur et son nouveau test diffèrent. Le contrôleur T16 admet ce delta
exactement épinglé et testé, avec les autres sources du socle inchangées, au lieu
d'imposer un nouveau global d'une heure. Les cohortes ne sont pas additionnées.

Le script est lu au prochain lancement natif ; aucun backend, microphone ou
modèle n'est relancé. Aucune donnée métier n'est écrite. Le volume isolé et son
essai restent soumis à l'intervention administrateur demandée ; T16 reste ouvert.
Pièce : `logs/foresight-runtime/L02-native-storage-error-ROOT-20261016.json`.


### T16 — droits disponibles confirmés le16octobre2026

L'utilisateur confirme ne pas disposer de droits administrateur. La demande de
création du VHD est donc classée « indisponible avec les droits actuels », sans
nouvelle demande d'élévation. L'inventaire seul confirme : WSL non installé,
moteur Docker Linux inaccessible (pipe absent), WinFsp/Dokan non détectés.
Aucun runtime, service ou pilote n'est démarré/installé, aucun volume créé.

Les preuves existantes d'ENOSPC injecté, des sept crashs réels, de conservation
et d'arrêt logiciel restent acquises. Elles ne deviennent pas une preuve de
volume réellement saturé. T16 et la clôture complète L12 restent ouverts.
L'usage du parcours audio→transcription relue→CR reste disponible. La création
du volume n'est plus une action attendue de cet utilisateur ; sa réalisation
éventuelle demandera un environnement autorisé fourni par l'administration.


### Génération réseau revenue — 16 octobre 2026 à09h45(Paris)

Le diagnostic courant sur le backend8001 confirme l'inventaire du modèle réseau
google/gemma-4-26b-a4b-qat déjà chargé, puis une réponse réelle en0,844s à la
requête fixe « Réponds uniquement OK. ». Le routeur cible exactement le moteur
réseau, secours/autostart désactivés pour cette requête. Le token de session
reste uniquement en mémoire, sans trace dans les reçus.

LM Studio local répond à l'inventaire et n'a aucune instance du secours Gemma
chargée, avant comme après le contrôle réseau. C'est une preuve de maintien à
l'état déchargé, pas une nouvelle transition chargé→déchargé attribuée à cet essai.
Aucun microphone, chargement local, réglage ou base métier modifié. Les458sources
Python du socle et de son delta ciblé restent identiques ; aucune suite répétée.
Le succès vérifie la réponse du moteur, pas un nouveau CR ni sa qualité métier.
L11 reste ouvert pour la chaîne actuelle entièrement hors ligne et sa coupure
physique ; L12 reste ouvert. Les anciens refus URLError sont conservés.
Pièce : `logs/foresight-runtime/L11-network-return-ROOT-20261016.json`.


### Préparation hors ligne actuelle — 16 octobre 2026

Le nouveau paquet `.ui-preview/t11-current-20261016/` réemploie le Job privé et
l'inventaire Windows précédents, dont les fonctions restent identiques par AST.
Il utilise medium CPU actuel, EG2 complet et le secours Gemma déjà installé.
Le précontrôle réel réussit sur484fichiers gelés et un Gemma installé/déchargé ;
18contrôles purs/simulés passent sur la version finale. Aucun moteur lancé.

Deux contradictions du protocole antérieur sont résolues : Gemma n'a plus besoin
d'être chargé avant la coupure ; le VPN Fortinet actif est identifié comme action
manuelle à réaliser, sans exemption pendant le test. Le chargement après coupure
passe par le diagnostic existant d'Agent et son verrou de modèle. STT et EG2 sont
fermés avant Gemma pour limiter les résidences simultanées. Au retour du réseau,
le wrapper vérifie une réponse réelle du moteur réseau puis l'absence d'instance
locale chargée. Le token de session n'est jamais stocké dans les reçus.

Un nouvel accord est requis pour une exécution unique avec coupure manuelle de
15minutes maximum et charge locale. Si Fortinet est imposé et ne peut pas être
déconnecté avec les droits habituels, cette recette demeure indisponible ; aucune
désactivation forcée. Aucun droit administrateur, microphone ou téléchargement.
Le fichier `LIRE_ETAT.txt` montre le signal et la demande de reconnexion pendant
la coupure. Le protocole est préparé, pas exécuté ; T11/L11/L12 restent ouverts.
Les anciennes preuves, erreurs et le protocole historique sont conservés.
Pièce : `logs/foresight-runtime/L11-current-offline-preparation-ROOT-20261016.json`.


Complément de la préparation T11 : le plafond humain de15minutes inclut
maintenant les précontrôles et le retour au réseau dès le lancement du wrapper.
Deux nouveaux contrôles vérifient le temps restant après préparation et le refus
avant moteur quand cette fenêtre est épuisée :20cas purs/simulés réussissent.
Le gel `preparation-r1.json` remplace l'ancien gel pour une future exécution,
conservé intact. Le nouveau précontrôle de fichiers/métadonnées réussit ; aucun
moteur ou réseau n'est modifié et aucune coupure n'est encore autorisée/lancée.


### Tentative hors ligne actuelle et correction du démarrage — 16 octobre 2026

La coupure manuelle est réellement observée :7inventaires hors ligne parmi188,
dont les observations avant et après le processus privé. Le processus termine
avec code1 en4,19s : `ModuleNotFoundError: offline_guard`, avant tout constructeur
STT/EG2/Gemma du harnais. La surveillance signale ensuite l'absence d'inventaire
entièrement couvert pendant cette vie très courte ; le stderr conserve la cause
initiale. Sortie du processus, Job vide et fermeture des handles sont confirmés.
La chaîne n'est pas qualifiée ; aucun rapport moteur n'est inventé.

Le wrapper termine également avec code1, après900,64s au total : le retour réseau
n'est pas confirmé dans sa fenêtre. Une lecture distincte après reconnexion voit
le modèle réseau exact annoncé et zéro instance Gemma locale chargée ; elle ne
transforme pas l'échec en réussite et ne prétend pas à une nouvelle réponse LLM.
Un chargement local transitoire observé après la coupure n'est pas attribué au
harnais, arrêté avant ses moteurs. Aucun microphone ni téléchargement utilisé.

Le chemin `C:/Agent/scripts` manquant est ajouté au seul paquet de qualification.
Son véritable point d'entrée `chain.py --help` termine avec code0 sur répertoires
privés, sans moteur. Les20gardes simulées antérieures ne couvraient pas ce défaut
de démarrage ; elles ne sont pas présentées comme preuve d'exécution intégrée.
Le sceau r2 conserve les484fichiers, avec seulement chain/controller/protocole
modifiés. Les sceaux, logs et résultats d'origine restent conservés. Aucun nouvel
essai, modèle ou coupure lancé après cet échec. T11/L11/L12 restent ouverts.
Pièce : `logs/foresight-runtime/L11-current-offline-attempt-ROOT-20261016.json`.


### Fonctions déjà qualifiées : matrice consolidée — 16 octobre 2026

F01/F09/F10/F11/F12/F14/F15/F22/F23 sont clos par leurs preuves L01/L04/L05/L06/
L07/L08/L10 déjà acquises : listes globale/projet, Notes, enrichissements avec
acceptation humaine, CR complet avec relecture, assistant, catalogue/imports,
calendrier sélectionné et actions explicites. Les reçus sont relus par empreinte ;
les458sources backend du socle courant restent identiques. La preuve navigateur
des brouillons riches/Markdown et des tableaux est réutilisée, sans nouvel essai.
Drive reste exclu par décision utilisateur. Les qualités du direct et du matériel
ne sont pas déduites de ces fonctions.13fonctions sur25 sont formellement closes,
9lots sur13 et11recettes sur17 ; L02/L03/L11/L12 restent ouverts. Aucun modèle,
microphone, test de charge, réglage ou donnée métier modifié par cette consolidation.
Pièce : `logs/foresight-runtime/qualified-feature-consolidation-ROOT-20261016.json`.


### Démarrage réel vérifié avant demande de coupure — 16 octobre 2026

Le contrôleur vérifie maintenant le vrai `chain.py --help` avant de produire le
signal de déconnexion. Les chemins Brain/ERP/stockage/TEMP sont privés, le
chargement local n'est pas autorisé dans ce processus et aucun moteur n'est
construit. Son temps reste inclus dans la fenêtre totale existante. Un échec
d'import ou un point d'entrée inattendu bloque le signal ; aucun nouveau seuil
de RAM, de vitesse, téléchargement ou réglage de sécurité n'est ajouté.

23cas passent en1,40s : les20gardes existantes et3nouveaux cas, dont le vrai
démarrage corrigé, un vrai import absent, puis l'absence de signal sur échec.
La gestion du Job et la lecture Windows restent identiques par AST. Le sceau r3
conserve484fichiers ; aucun nouveau test hors ligne, modèle ou microphone lancé.
Ce contrôle de démarrage ne qualifie pas la chaîne : T11/L11/L12 restent ouverts.
Les statistiques affichent toujours l'utilité humaine comme non instrumentée ;
ce point reste à traiter, sans assimiler le nombre de réponses à leur qualité.
Pièce : `logs/foresight-runtime/L11-entrypoint-admission-ROOT-20261016.json`.


### Avis sur les réponses et statistiques réelles — 16 octobre 2026

Réunions → séance → Assistant propose Utile/Pas utile sur la Discussion et les
Questions en direct. Recliquez pour retirer l'avis. Le dernier avis explicite
compte une fois ; l'auteur et les changements restent enregistrés. La réponse,
les notes, le CR et les validations métier restent distincts. Droits de séance
et citations courantes contrôlés, corps strict, requêtes répétées sans doublon.
Un retour d'historique ancien ne remplace pas l'avis reçu ; brouillons conservés.

La copie privée dans le vrai navigateur confirme 1 utile/2 évaluées puis0/1
après retrait, avec brouillon intact, trois avis SQL et zéro tâche/CR. Preuve DOM
conservée ; capture d'image indisponible à cet instant, aucune mesure pixel déduite.
Le serveur privé et ses onglets sont fermés. Le premier backend conserve32réussites
et2échecs de fixtures ; les6nouveaux cas passent après correction. Frontend121,
retest Stats2 et Studio4 passent, cohortes recouvrantes. L'échec TypeScript initial
sur options de tests reste conservé ; le final, Vite et Ruff réussissent.

Activation8001 après nouvelles sauvegardes Brain/ERP/EG2 et restaurations privées.
Les données comparées restent exactes sauf progression/dates de deux journaux
dérivés explicitement classées, sans retrait d'identifiant. Nouveaux assets
identiques aux octets HTTP, anciens conservés. Aucun modèle/microphone ou nouvelle
coupure. Le sceau hors ligne r4 est rebasé sur460sources, sans relancer la recette.
F19 reste ouvert pour son bilan complet ; tokens non instrumentés et P95 DOM
distincts. L02/L03/L11/L12 restent ouverts. Détail :
`docs/54_FORESIGHT_ANSWER_FEEDBACK.md`.


### Tokens réellement fournis par le moteur — 16 octobre 2026

Les réponses conservées de la Discussion et des Questions en direct gardent les
compteurs du fournisseur. Les tentatives reprises sont conservées, y compris une
absence de mesure. Stats affiche la somme connue et sa couverture complète,
partielle ou absente. Aucun calcul depuis le texte, économie ou prix estimé.
Les quatre réponses historiques restent sans mesure. Ce compteur de réponses
ne devient pas une comptabilité de tous les modules ou des échecs non conservés.

201contrôles ciblés passent avec un avertissement TestClient ; frontend2,
TypeScript, Vite et Ruff réussissent. Le contrôle réel sur notes fictives privées
utilise le modèle réseau déjà chargé :176tokens de contexte+27de réponse=203,
même reçu après rejeu et Stats203. Bases privées intègres, Gemma local déchargé
avant/après, aucun microphone ou téléchargement. Comparaison AST : transport,
paramètres et repli identiques après retrait des seuls contextes d'observation ;
les sept autres fonctions du client sont identiques.

Activation8001 après sauvegardes/restaurations privées Brain/ERP/EG2. Les91tables
non volatiles comparées sont exactes à la vérification après redémarrage. Une
lecture ultérieure distingue les statuts/avertissements/dates de suivi qui
continuent d'évoluer, sans retrait d'identifiant. Assets servis conformes et
anciens conservés. Sceau hors ligne r5 rebasé sur462sources sans nouvelle coupure.

F19 est clos selon la fonction Stats/diagnostics du plan : sources/index, durée/
pistes/retard, avis humains, temps serveur, compteurs fournis et formules.
Il ne qualifie pas le P95 d'affichage ou le fonctionnement hors ligne complet.
9lots sur13,14fonctions sur25 et11recettes sur17 sont clos ; L02/L03/L11/L12
restent ouverts. Détail : `docs/55_FORESIGHT_TOKEN_USAGE.md`.


### Recherche et préparation qualifiées ; lexique non généralisé — 16 octobre 2026

La recherche unifiée est vérifiée sur trois sources fictives privées avec le vrai
encodeur réseau déjà chargé : « retard livraison » retrouve le décalage de trois
semaines par le seul sens ; les mots éclairage/350lux et la référence choisie
retrouvent la bonne fiche. La référence exacte exclut les voisins. L'index reste
identique par SHA pendant les trois recherches, les trois Sources restent
conservées et aucune connaissance validée n'est créée. Les15contrats applicables
du global backend restent acquis sur sources inchangées, sans nouvelle suite.

La préparation privée termine puis relit son état dans une nouvelle session SQL,
se réouvre et garde transcription/proactif/enrichissement désactivés. Le lecteur
ne peut pas la modifier. Les9contrôles UI acquis sont reliés à leurs sources
inchangées ; la sauvegarde et le bloc de préparation restent identiques au
préimage qualifié. Les diagnostics distinguent installation, chargement et
réponse réelle, y compris l'échec et la reprise, sans déduire une qualification
matérielle d'un modèle présent.

F16 et F20 sont clos selon leurs fonctions du plan.16fonctions sur25,9lots sur13
et11recettes sur17 sont clos. L02/L03/L11/L12 restent ouverts.

Le comparatif CPU de lexique dure28,94s sur trois WAV connus et un silence
fictif existant : consignation corrigée dans le bruit, témoin1250W/350lux exact
et silence sans texte ; dans le chevauchement, la réserve client reste omise et
« commande manuelle » disparaît aussi. Il s'agit d'un essai de développement,
pas d'une validation aveugle. Aucune promotion de profil : les défauts anciens
et le nouveau résultat défavorable restent conservés. Aucun microphone, LLM,
GPU, téléchargement ou donnée métier dans cet essai CPU ; il n'a modifié aucun
poids, réglage ou source produit. Aucun autre essai identique à relancer.


### Base audio pleine — 16 octobre 2026

Agent distingue désormais « Stockage de la base saturé » d’une saturation des
fichiers audio. La capture est interrompue, les fragments restent conservés et
la synchronisation peut être rejouée après libération de capacité. Le correctif
est actif sur8001 ;99tests ciblés passent, sans microphone ni modèle.
La preuve utilise une vraie erreurSQLite SQLITE_FULL dans une base privée ;
elle ne remplace pas la recette de volume physique plein T16, toujours ouverte.


### Recette hors ligne du16octobre, essai renouvelé

La coupure réelle a permis de produire la transcription medium (1250W/350lux)
et un index privé de quatre sources texte/image/audio. La génération locale
n’a pas confirmé son diagnostic : T11/L11/L12 restent ouverts. Le retour réseau
et le déchargement de Gemma sont confirmés ; durée totale570,07s, sans microphone.
Le diagnostic IA respecte désormais le délai configuré (60s sur le poste), au
lieu d’ignorer le réglage par un plafond fixe15s.104tests ciblés passent.


### Diagnostic local sans nouvelle coupure — préparation du16octobre2026

Après l'échec du diagnostic Gemma dans la recette physique, un contrôle ciblé
est préparé avec réseau connecté : un seul appel au test fixe d'Agent, puis
inventaire réseau frais et vérification du déchargement géré par Agent.
Il refuse un modèle déjà chargé, une capture/travail audio actif ou un choix
de moteur différent. Six contrôles simulés passent ; aucun modèle réel lancé.
Son exécution attend un nouvel accord humain, distinct de l'essai hors ligne
consommé ; elle ne clôturerait pas à elle seule T11, L11 ou L12.

[Protocole et commande soumis à accord](.ui-preview/gemma-online-diagnostic-20261016/PROTOCOL.md).


### Génération locale confirmée en ligne —16octobre2026

Le diagnostic réel unique autorisé a réussi en200,06s au total : Gemma-e4b
chargé par Agent, réponse non vide au test fixe « OK », modèle exact confirmé,
puis inventaire frais du modèle réseau chargé et absence d’instance Gemma locale.
Le réseau est resté connecté. Aucun microphone, téléchargement, réglage ou
publication métier. Le temps couvre chargement, attente, test et déchargement ;
il ne constitue pas une mesure du seul calcul neuronal ni une latence du CR.

Le délai configuré60s est actif. Le résultat positif ne prouve pas que le seul
ancien délai15s expliquait l’échec précédent. Le modèle local fonctionne dans
cette configuration, mais la chaîne physique entièrement hors ligne actuelle
reste à qualifier. L’accord unique de ce diagnostic en ligne est consommé.
Le contrôle de préparation r7 après essai passe sans charger de moteur ni donner
de signal de coupure. Les464sources Python sont inchangées ; aucune nouvelle
suite globale ou recette d’une heure.

Preuve : `logs/foresight-runtime/L11-online-local-generation-ROOT-20261016.json`.
T11/L11/L12 restent ouverts ;9lots/13,16fonctions/25 et11recettes/17 clos.


### Démarrage STT sous coupure : échec conservé —16octobre2026

La recette20261016-173638-37b5dfa5 est refusée : l’enfant termine en10,65s
sur une erreur de chargement Whisper, avant transcription ou génération de la
chaîne. Huit inventaires déconnectés, dont deux pendant l’enfant, sont conservés.
Le modèle local était chargé lors du contrôle après l’enfant ; son origine et
son éventuel rôle dans cette erreur ne sont pas établis. Le retour réseau et
le déchargement sont confirmés ; total852,13s sous la fenêtre900s autorisée.
Le processus, son Job et les handles sont fermés. L’accord unique est consommé.

Deux démarrages CPU de développement, sans audio ni LLM, réussissent ensuite
environ3s : main original directement puis ResidentWhisper sous Jobs imbriqués,
avec un bootstrap privé conservant les erreurs. Ce ne sont pas des recettes
physiques ni une preuve que l’échec intermittent est corrigé. Le premier essai
de ce bootstrap a réussi le démarrage mais son wrapper de nettoyage a échoué
sur un nom de méthode incorrect ; la correction passe et confirme le Job vide.
Aucune cause mémoire n’est déduite : absence d’événement2004 correspondant,
compteurs WMI inaccessibles et message STT d’origine trop générique.

Le paquet dormant r8 conserve maintenant le traceback technique du démarrage
et un journal de faute native dans le dossier privé. Il appelle le main original
sans modifier le modèle, le GPU, les paramètres ni les sources produit. Une
fenêtre Windows locale demandera la reconnexion à la fin de phase, indépendamment
du réseau Codex ; elle ne change aucun adaptateur. Son lancement est journalisé,
sans prétendre qu’elle a été vue. La capacité WPF/desktop est vérifiée sans
affichage réel ; la présentation reste à qualifier. Les tests de retour réseau
simulent désormais entièrement ce nouveau chemin de notification.

Les31contrôles finaux du harnais passent sans modèle ni fenêtre ; le vrai
chain.py --help et le précontrôle r8 passent. Les464sources Python produit sont
inchangées. Aucun nouveau scénario complet, microphone, téléchargement ou
modèle génératif lancé après l’échec. T11/L11/L12 demeurent ouverts.

Preuve : `logs/foresight-runtime/L11-offline-STT-startup-ROOT-20261016.json`.
9lots/13,16fonctions/25 et11recettes/17 restent clos.


### Chemin STT/recherche actuel vérifié sans coupure —16octobre2026

Le contrôle de développement a exécuté le chemin actuel du paquet en19,23s,
avec les vrais moteurs CPU et les quatre sources fictives privées : transcription
1250W/350lux, annulation après une entrée puis reprise des quatre, recherches
texte/image/audio attendues et réouverture de l’index. Les Jobs et handles sont
fermés. Le bootstrap d’erreur R8 a réellement appelé le main Whisper original.
Un arrêt planifié et deux garde-fous dans ce seul processus ont interdit toute
génération et tout chargement LLM ; aucune réponse fictive de modèle n’est créée.
Le réseau physique est resté présent : **ce résultat ne qualifie pas T11**.

Le modèle et son tokenizer existent localement ; la version installée de
Faster-Whisper ouvre ces chemins locaux. Aucun fichier ou moteur n’est réinstallé.
Le paquet dormant r9 ajoute RAM et commit Windows disponibles à ses observations,
via le psutil installé, sans WMI ni administrateur. Aucune valeur basse ne devient
un nouveau refus ; une mesure indisponible est simplement signalée. Les33contrôles
simulés passent, ainsi que le précontrôle et le vrai CLI --help. Les classes de
Job et la lecture réseau sont identiques par AST ; les464sources Python produit
restent inchangées. Aucun nouveau modèle génératif, microphone ou essai physique.

La cause de l’échec réel sous coupure reste inconnue. Le traceback privé et la
fenêtre locale de reconnexion sont prêts pour une éventuelle nouvelle recette,
qui attendrait un nouvel accord humain. L11 et L12 restent ouverts ;9lots/13,
16fonctions/25 et11recettes/17 clos. Aucun nouveau global ou essai d’une heure.


### Recette T11 hors ligne réussie — 16 octobre 2026, 20 h 01 Paris

La recette autorisée `20261016-195742-b3cd650a` réussit et termine normalement
en 207,74 s, retour réseau inclus. La chaîne enfant prend 40,42 s. Sous coupure
manuelle Fortinet/Wi-Fi/LAN observée, Whisper medium CPU transcrit réellement
le WAV fictif : « La puissance est de 1250 watts pour un éclairement de 350 lux. »
Le calcul STT prend 6,36 s. EG2 local indexe les quatre sources privées, conserve
l'annulation après une entrée puis reprend les quatre ; les recherches texte,
image et audio retrouvent les sources attendues et l'index se rouvre.
Gemma local génère ensuite les valeurs 1250/350 avec citation [1], vérifiées
après génération. Aucun résultat génératif simulé n'est utilisé.

Onze observations réseau qualifiées, dont huit pendant l'enfant, et un écart
maximal de 6,22 s sont conservés. Les inventaires sont échantillonnés : aucune
mesure de zéro appel natif sortant n'est revendiquée. Le harnais garde son champ
physique à false ; c'est le contrôleur externe et ses observations qui prouvent
la coupure. Aucun microphone, téléchargement ou changement de réglage produit.
Les 464 sources Python produit et les fichiers scellés restent identiques.

La notification locale a été lancée ; sa perception par l'utilisateur n'est pas
déduite de ce seul lancement. Après reconnexion, le vrai serveur réseau répond
et le déchargement de Gemma est confirmé, puis recontrôlé en lecture seule.
Le processus enfant, son Job et les handles sont fermés. L'accord unique est
consommé ; aucun deuxième essai n'est lancé.

Un contrôle ultérieur a observé Gemma de nouveau chargé, malgré le premier
déchargement confirmé. L'auteur du rechargement n'est pas identifié. Une sonde
fraîche des connexions Agent confirme le modèle réseau et déclenche le mécanisme
existant de libération ; l'inventaire local redevient vide. Aucun chargement ni
nouvelle génération n'a été demandé pour cette vérification. Cette observation
est conservée et ne prouve pas la stabilité future du routage.

**T11 est clos dans son contrat STT/recherche/génération sur fichiers fictifs.**
Ce résultat ne qualifie ni microphone/casque, ni navigation pendant capture,
ni précision du direct industriel ou latence DOM. L02/L03/L11/L12 restent ouverts
pour ces exigences distinctes ; 9 lots/13, 16 fonctions/25 et 12 recettes/17 clos.
Les cinq recettes restantes sont T01/T02/T03/T04/T16. Aucun nouveau global ni
essai d'une heure ; les anciens échecs et leurs causes non établies sont conservés.
Preuve : `logs/foresight-runtime/L11-offline-success-ROOT-20261016.json`.


Audio des réunions (21/10/2026) : nouvelles captures natives et mix final en
Ogg/Opus 32 kbit/s par piste ; navigateur compressé, imports MP3 conservés.
256 Mio par import, 512 Mio par séance et 12 h ; anciens WAV conservés.
Voir [le fonctionnement et les tests audio](docs/23_MEETING_AUDIO.md).


Continuité Opus activée : contexte direct court décodé en mémoire, sans WAV
intermédiaire. Contrôle vocal CPU sur 15 extraits et 69 tests ciblés conservés
dans `logs/foresight-runtime/L03-OPUS-CPU-ROOT-20261021.json`. Les limites de
qualité du direct restent explicites ; voir `docs/51_FORESIGHT_DIRECT_CPU.md`.


Le direct Opus peut désormais réviser son segment automatique précédent à
réception du suivant, avec préimage conservée et corrections humaines protégées.
Le cas « 350 lb → 350 lux » est corrigé dans la vraie chaîne CPU/SQL et activé
sur 8001. Voir `docs/51_FORESIGHT_DIRECT_CPU.md` et le rapport
`logs/foresight-runtime/L03-ROLLING-OPUS-ROOT-20261021.json`.


Le parcours complet d'un enregistrement Opus jusqu'au CR est vérifié avec une
relecture QA explicite : medium CPU, synthèse réseau et publication idempotente
sur données privées fictives. Le brut ASR et sa correction restent distincts.
Preuve : `logs/foresight-runtime/L03-OPUS-COMPLETE-CR-ROOT-20261021.json`.


Recette matérielle Opus : prévol privé sans ouverture audio réussi ; bilan des
empreintes distinct du diagnostic des trous temporels. Voir le domaine 52 et
`logs/foresight-runtime/L12-OPUS-PHYSICAL-READINESS-ROOT-20261021.json`.


Le stockage Opus est vérifié après cinq arrêts réels de sous-processus :
récupération exacte, reçu rejoué et absence de doublon SQL. Aucune capture
matérielle ou saturation réelle de volume dans ce contrôle. Preuve :
`logs/foresight-runtime/T16-OPUS-CRASH-ROOT-20261021.json`.


Recette physique Opus du 21 octobre : navigation, changement de filtre projet,
actualisation, pause/reprise et arrêt normal vérifiés sur une fixture privée
Realtek. 17 fragments microphone (82,901 s) conservés avec empreintes et reçus
SQL intacts ; quatre doubles captures refusées par les API, même worker.
La fenêtre audio initiale n’a pas été renouvelée lors du passage hors du bac
à sable. Aucun modèle, écoute ni transcription. Le loopback sans fragment
reste non qualifié ; L12 reste ouvert. Preuve :
`logs/foresight-runtime/L12-OPUS-PHYSICAL-ROOT-20261021.json`.


Après conservation d’une séance, la barre audio indique désormais
« Enregistrement terminé et conservé » et invite à créer une nouvelle séance.
Les sélecteurs de démarrage et l’avertissement par défaut sur le microphone
ne décrivent plus faussement la réunion passée. Les commandes de récupération
restent distinctes. 50 tests existants passent ; TypeScript/Vite et vérification
UI privée sans audio réussis. Assets activés sur 8001 sans redémarrage backend.
Preuve : `logs/foresight-runtime/COMPLETED-CAPTURE-UI-ROOT-20261021.json`.


### Signalement des pistes absentes — 21 octobre 2026

Après conservation ou interruption, une piste native démarrée avec succès mais
sans aucun fragment conservé est maintenant signalée explicitement dans la
séance. Exemple observé : « Son du PC : aucun fragment audio conservé… ».
Les événements de démarrage et les fragments conservés font autorité ; ni piste
inventée, ni silence ajouté, ni cause supposée. Les fichiers existants restent
intacts. 32 tests de séances passent, dont sept cas de piste absente/présente ;
Ruff passe et l’avertissement est vérifié dans le navigateur sur métadonnées
privées issues de la capture réelle. Aucune réouverture audio.

Sauvegardes Brain/ERP intègres, redémarrage Agent seul, backend39024 et santé ok.
Le passage global backend déjà en cours reste une référence sur ses sources
initiales ; ce delta ultérieur possède sa régression ciblée distincte.
L02/L12 restent ouverts. Preuve :
`logs/foresight-runtime/MISSING-AUDIO-TRACK-ROOT-20261021.json`.


Comparaison CPU medium beam5 du 21 octobre sur six Opus fictifs existants :
les trois phrases de mesures propres restent correctes, mais le bruit déforme
encore « consignation » et le chevauchement perd encore la négation du client.
Ce changement de décodage n’apporte pas de correction des deux défauts ; le
profil produit beam1 reste inchangé. Aucun microphone, GPU, LLM ou téléchargement.
Les temps des deux passages ne constituent pas un benchmark A/B contrôlé.
L03 reste ouvert ; aucune nouvelle tentative identique n’est nécessaire.
Preuve : `logs/foresight-runtime/L03-OPUS-BEAM5-ROOT-20261021.json`.


Complément de recette Realtek audible préparé : lecture de trois phrases
fictives pour contrôler la piste système, sans modèle, écoute des captures
ou transmission. Prévol réel : playback403, quatre refus start/resume, aucun
accès audio et fermeture normale ; douze tests de garde passent. Aucun ancien
accord audio réutilisé. Jabra toujours absent, L12 reste ouvert. Preuve :
`logs/foresight-runtime/REALTEK-AUDIBLE-PREP-ROOT-20261021.json`.


Filtrage spectral diagnostique du21octobre : sept Opus fictifs déjà conservés,
paramètres génériques fixés, aucun texte attendu transmis au modèle. Le signal
bruité change effectivement (écart L2 relatif7,69%), mais les sept transcriptions
restent textuellement identiques au profil sans filtre. Les deux erreurs
bruit/chevauchement persistent ; aucun filtre n’est activé dans Agent. Le modèle
CPU est fermé, aucune capture ni transmission, originaux intacts. Cette piste
n’apporte pas d’amélioration et n’appelle pas un nouvel essai identique.
Preuve : `logs/foresight-runtime/L03-OPUS-DENOISE-ROOT-20261021.json`.


Préparation du traitement long du21octobre : décodage par fenêtres bornées
en mémoire et regroupement global des empreintes de voix, sans fichier PCM
intermédiaire.13tests et le FastClustering natif sur vecteurs synthétiques
passent. Le composant n’est pas encore raccordé : la transcription complète
garde actuellement son plafond2h, distinct de la capture12h. Aucun modèle ni
microphone ouvert pour cette préparation. Raccordement et preuve vocale réelle
restent nécessaires avant activation.
Preuve : `logs/foresight-runtime/LONG-MEETING-PREPARATION-ROOT-20261021.json`.


### Activation du traitement long puis suspension — historique du 21 octobre 2026

**Activation annulée ensuite : ancien worker et limite2h rétablis.** Les lignes
ci-dessous décrivent uniquement l’étape provisoire antérieure au défaut à deux voix.

La transcription complète ne refuse plus les entrées à2h. Au-delà de15min
ou sans durée connue, elle décode par fenêtres de15min et recouvrement5s,
en mémoire, sans WAV/PCM intermédiaire sur disque. Les voix locales sont
regroupées globalement par le FastClustering Sherpa installé ; aucune identité
humaine n’est inventée. Les horodatages de relecture acceptent la capacité
commune12h. La coupure parent4h est retirée ; annulation et Job Windows restent.

85tests de régression passent, puis21contrôles des fenêtres/horodatages, avec
recouvrement entre ces séries. CPU réel sur un Opus fictif20,25s forcé en trois
fenêtres : résultat en21,72s, même voix regroupée, temps et mots conservés.
Le brut conserve « luxe » et une coupure de «1,5» entre segments : relecture
requise, aucune réparation lexicale comptée comme réussite ASR. Cet essai
ne qualifie pas12hde transcription réelle ni le RSS maximal du modèle.
Sauvegardes Brain/ERP intègres, backend33348, santé et schéma HTTP vérifiés.
Preuve : `logs/foresight-runtime/LONG-MEETING-ACTIVE-ROOT-20261021.json`.

Régression globale initiale terminée :2763réussis,1ignoré,54sous-tests réussis,
1échec sur l’ancienne attente45s face au contrat600s. Cette attente est corrigée
et les85ciblés ci-dessus passent ; l’échec global original est conservé. Aucun
passage global intégral propre sur le dernier arbre n’est inventé et aucune
addition des cohortes n’est faite. L03/L12 restent ouverts. Bilan :
`logs/foresight-runtime/INTEGRATION-OPUS-ROOT-20261021.json`.

### Séance Realtek regroupée — 21 octobre 2026

T02 et T04 sont clos : double clic réel sans double démarrage, second onglet
bloqué, fermeture effective du premier onglet, actualisation, changement de
filtre projet, pause/reprise et arrêt normal. Une seconde séance privée a subi
la panne volontaire du seul serveur de recette ; après sauvegarde, le vrai
`recover_interrupted` puis le bouton **Conserver les fragments acquittés** ont
conservé les 21 fragments et leurs reçus, sans changement de SHA256. La première
séance terminée reste inchangée. Tous les processus audio et de recette sont fermés.

Les fichiers Opus totalisent394491octets : microphone75431ms sur deux séances,
son système20138ms sur la première. Les trois phrases fictives ont été lues une
fois, sans écoute des captures, transcription, modèle ou envoi externe. Une seule
phrase passe le seuil de corrélation de forme d’onde fixé avant calcul ; les deux
autres restent inconclusives. Le casque Jabra absent et le changement physique
restent non qualifiés (T03). Aucun essai de saturation du volume hôte (T16).

Bilan cumulatif : **15/17 recettes**, **9/13 lots**, **16/25 fonctions**.
T03/T16 et L02/L03/L11/L12 restent ouverts. Preuve :
`logs/foresight-runtime/L12-REALTEK-CLOSE-RECOVERY-ROOT-20261021.json` ;
audit courant : `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r43.json`.

**Suspension intermédiaire, levée par le correctif de contexte ci-dessus** : le second corpus fictif à deux voix a révélé
une prise de parole absente des fenêtres courtes. Le décodage intégral et le tour
isolé la reconnaissent. L’ancien worker a été rétabli ; sa limite2h est donc
encore active pour la transcription complète, distincte de la capture12h.
Aucun test12h réel ni correction du défaut n’est revendiqué.


### Comparaison turbo et intégration courante — 21 octobre 2026

Le modèle large-v3-turbo déjà installé a traité les15Opus fictifs sur CPU/int8,
avec la fonction de direct actuelle et beam1. Il ne satisfait pas le corpus :
le bruit transforme « consignation » en « confirmation » ; le chevauchement
retrouve le refus du client mais perd la première consigne de la machine.
Il n’est pas activé. Medium reste le profil courant. Les comparaisons medium
beam5/filtre et les résultats Parakeet antérieurs ne sont pas relancés sans
nouvelle hypothèse. Aucun microphone, écoute, téléchargement, LLM ni base métier.
Preuve : `logs/foresight-runtime/L03-OPUS-TURBO-COMPARISON-ROOT-20261021.json`.

La comparaison spectrale complémentaire des captures Realtek existantes trouve
des corrélations0,982, mais les marges face aux témoins temporels inversés restent
sous le seuil fixé : le diagnostic ne clôture pas T03 et les critères ne sont
pas abaissés après calcul. L’inventaire courant ne détecte toujours pas le Jabra.

Régression complète courante sur713empreintes sources inchangées : frontend
969tests/94fichiers réussis, TypeScript/Vite réussis et JS/CSS servis identiques.
L’index HTML diffère seulement par espaces/fins de ligne, URLs inchangées.
Le nouveau global backend est **en cours**, session51340/PID36400, identité
conservée dans `.ui-preview/integration-context-20261021/progress.json`.
Il ne doit pas être relancé sur un délai d’observation et aucun succès terminal
n’est revendiqué. Les résultats globaux précédents restent datés séparément.
Bilan inchangé :9/13lots,16/25fonctions,15/17recettes ; L03 et L12 restent ouverts.


### Préparation T16 remise au format Opus — 21 octobre 2026

Le paquet `.ui-preview/pilots/t16-opus-full-20261021` conserve séparément le
scénario historique WAV. Les fragments, intention v2, consommateur et copies de
récupération sont désormais Opus. Le test de boucle utilise le vrai Opus encodé
avant les adaptateurs de périphérique/rééchantillonnage inertes ; aucune ouverture
WASAPI n’est prétendue.40tests et66sous-tests simulés passent ; le codec fonctionne
réellement sous `-I -S -B`,5s/20620octets sur un motif sans voix.

Le pilote prépare des délais partagés plus larges :15min au total,14min pour
l’enfant et5min pour le remplisseur. La taille du seul VHD reste256Mio et le
journal conserve la réserve du produit. Son futur plan liera471sources Python
actuelles et536fichiers runtime PyAV/NumPy ; aucun plan exécutable n’est créé.
Le succès backend actuel et son JUnit sont exigés ensemble, avec empreintes
inchangées ; la suite complète est encore en cours. Le refus des anciens reçus,
d’un JUnit en échec ou de sources modifiées est testé.

L’inventaire courant confirme l’absence de volume provisionné, de jeton admin,
de pipe Docker et de WinFsp/Dokan. Aucun montage, formatage, remplissage,
installation ou demande d’élévation n’a eu lieu. L’utilisateur n’a pas les droits
administrateur ; cet obstacle n’est pas contourné en remplissant le disque hôte.
La revue du plan exact, le volume isolé réel et l’accord de remplissage restent
à obtenir avant exécution. **T16 et L12 restent ouverts.** Preuve :
`logs/foresight-runtime/T16-OPUS-PREPARATION-ROOT-20261021.json`.



### Qualification du 21 octobre : voix et corrections, préparation Jabra

F07 est qualifiée sur deux voix fictives réellement transcrites puis relues dans le Studio : noms attribués explicitement, correction de texte et de locuteur, persistance après actualisation, validation explicite en révision 3 et conservation des versions 1 et 2. Cette validation de recette ne constitue pas une validation métier humaine. Preuve : `logs/foresight-runtime/F07-VOICES-REVIEW-ROOT-20261021.json`. Aucun microphone, modèle ou traitement d’indexation supplémentaire n’a été ouvert dans cette fixture de relecture.

État cumulé : **17/25 fonctions, 9/13 lots et 15/17 recettes qualifiés**. L03 et L12 restent ouverts ; le direct industriel et la diarisation physique ne sont pas qualifiés par cette relecture. La suite backend globale actuelle reste en cours ; les 969 tests frontend et le build ont réussi.

Le Jabra Evolve 75 est à nouveau détecté en microphone et loopback. La recette regroupée est préparée dans `.ui-preview/pilots/jabra-consolidated-20261021/PROTOCOL.md` : fenêtre unique de 30 minutes démarrant à la première admission audio, préparation exclue du chronomètre, seuls périphériques nommés admis. Douze tests et 23 sous-tests passent ; le prévol `physical-48a5a9b46e18` ferme normalement le serveur et refuse quatre demandes audio, sans ouverture matérielle. Le branchement ne constitue pas un accord d’enregistrement ; nouvelle réponse explicite attendue. Aucun casque, changement de périphérique ou retrait physique n’est déclaré qualifié avant exécution.


### Séance matérielle Jabra/Realtek du 21 octobre

La séance regroupée autorisée par `call_19b8ad2866cd432184651606cee99a1c` est fermée ; aucune nouvelle ouverture n’est couverte après cette fermeture. Les continuations ont gardé le même accord, le même identifiant de séance de recette et la même échéance initiale de 30 minutes. Les quatre Jobs privés ont été fermés et les quatre lectures de conservation passent. Les captures restent locales en Opus, sans écoute, transcription ni modèle.

Le premier Jabra a conservé 31,872 s de microphone et 20,565 s de son système, avec lecture des trois WAV fictifs dans le casque et arrêt ordinaire. Le passage explicitement choisi vers Realtek a conservé 22,656 s de microphone ; l’absence de fragment système est affichée et ne vaut pas succès de cette piste. Le retrait physique du Jabra a révélé un état « Enregistrement » persistant : anomalie conservée, T03 reste ouvert.

Un candidat de surveillance des flux passe sept tests (flux arrêté, microphone sans callback, silence normal, loopback inactif acoustiquement, pause/reprise). Il a terminé un arrêt ordinaire réel à 38,265 s dans la fixture. L’autre exécution a affiché « Interrompue » avec une erreur de persistance générique ; elle ne prouve pas que la nouvelle surveillance a détecté le retrait. Le fragment natif restant a été rejoué avec succès après sauvegarde SQLite, sans ouverture audio. La cause exacte initiale n’est pas déclarée résolue. Le candidat n’est pas encore activé dans les sources de production pendant la régression globale en cours.

Preuve : `logs/foresight-runtime/JABRA-SWITCH-ROOT-20261021.json`. Aucun lot supplémentaire n’est clôturé par ces observations. Le casque, l’intelligibilité et la transcription réelle restent des qualifications distinctes.


### État courant après contrôle des flux du 21 octobre

Le contrôle des flux est maintenant activé dans `scripts/native_audio_capture.py` pour les prochaines captures : un flux PortAudio arrêté est signalé ; un microphone sans callback contenant des données pendant dix secondes provoque une interruption visible. Ce délai détecte une perte de flux, sans plafonner la durée d’une réunion. Le silence acoustique ne déclenche pas ce contrôle si les callbacks continuent. Un loopback silencieux peut légitimement ne fournir aucun callback ; ce cas reste admis. La pause est exclue et la reprise réarme le délai.

La régression globale du socle a terminé avec **2793 tests réussis, 1 ignoré et 54 sous-tests réussis**, sans échec ni erreur (3515,54 s). Les **713 fichiers sources** étaient inchangés à sa clôture. Le correctif de flux et ses sept nouveaux tests ont été appliqués ensuite : **79 tests ciblés passent**, ainsi que Ruff sur `app`, `backend/app`, `tests` et le helper. La suite globale n’a pas été relancée après ce petit delta ; cette distinction est conservée dans les preuves. Frontend : 969 tests/94 fichiers ; build réussi.

Le candidat, identique au helper activé, a terminé un arrêt ordinaire réel à 38,265 s dans la fixture. Son autre interruption avait une erreur générique de persistance : elle ne qualifie pas la causalité du retrait. Le contrôle de perte du seul loopback encore marqué actif par le pilote et la recette matérielle complète restent à vérifier. T03, L02 et L12 restent ouverts. Les captures de recette sont fermées et n’ont été ni écoutées ni transcrites. Aucun microphone n’a été ouvert pendant l’activation ou ses tests. Agent répond sur 8001, Brain/ERP sont sains et aucun propriétaire audio canonique n’est actif.

Preuves : `logs/foresight-runtime/NATIVE-STREAM-HEALTH-ROOT-20261021.json` et `.ui-preview/integration-context-20261021/terminal.json`. État cumulé inchangé : 17/25 fonctions, 9/13 lots, 15/17 recettes qualifiés. Travail non commité et non poussé.


### Suivi Windows du périphérique réellement choisi — 21 octobre

La capture native contrôle maintenant également la présence Windows des périphériques sélectionnés, avec le module interne `scripts/windows_audio_endpoints.py`. Aucun service ni dépendance supplémentaire : Agent reste sur 8001, XPilot sur 8000 est inchangé. Les métadonnées MMDevice sont lues, sans activation de client audio. L’association initiale exige le nom exact et le sens capture/sortie correspondant à WASAPI ; les vérifications suivantes gardent l’identifiant opaque du même endpoint. Un changement de sortie par défaut ne déplace pas l’enregistrement. L’état est vérifié toutes les secondes en cours de capture et immédiatement avant démarrage/reprise. Un endpoint absent, désactivé ou débranché provoque une interruption visible, même lorsque le loopback ne produit aucun callback. Un loopback silencieux dont l’endpoint reste actif est admis. Nom introuvable ou ambigu : refus explicite avant démarrage, sans substitution. Le contrôle des callbacks microphone reste complémentaire.

Vérification courante : **96 cas ciblés distincts réussis** (passage de 95 cas puis module de 17 cas dont 16 déjà couverts), Ruff réussi. Le test supplémentaire exerce la vraie boucle `capture()` avec un PortAudio simulé encore actif et un endpoint système retiré : interruption et fermeture des ressources vérifiées. Les sondes réellement exécutées sur ce PC associent les quatre endpoints Jabra/Realtek et vérifient leur état ; 50 séries de quatre lectures ont pris au maximum 1,215 ms par série. Une seconde sonde vérifie l’imbrication PortAudio/COM utilisée en production. Ces sondes n’ouvrent aucun flux audio. Le premier lancement pytest dans le bac à sable s’est arrêté sur 23 erreurs de préparation de dossiers temporaires ; les exécutions dans le dossier privé accessible passent. Le socle global de 2793 tests backend reste une preuve antérieure à ce delta, et non une nouvelle régression complète du helper modifié.

Le suivi est activé pour les prochaines captures. Il ne transforme pas l’ancienne interruption générique de recette en détection physique prouvée : aucun nouvel enregistrement ni retrait pendant capture avec ce module n’a été effectué. T03, L02 et L12 restent ouverts ; état cumulé 17/25 fonctions, 9/13 lots, 15/17 recettes. Aucun nouveau modèle, téléchargement, changement de réglage métier, commit ou push. Agent est sain et aucun propriétaire audio n’est actif.

Preuve : `logs/foresight-runtime/WINDOWS-ENDPOINT-HEALTH-ROOT-20261021.json`. Références : [IMMDevice::GetState](https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nf-mmdeviceapi-immdevice-getstate), [propriétés MMDevice](https://learn.microsoft.com/en-us/windows/win32/coreaudio/device-properties).


### Réponses automatiques : progression visible — 21 octobre

Dans « Réunions → Assistant → Questions en direct », une recherche automatique affiche maintenant un indicateur tant que sa tentative durable est en cours. Après dix secondes depuis la réservation de cette tentative, le message indique un retard ; il ne coupe ni capture ni génération. Une fin enregistrée enlève l’indicateur. Erreur, interruption, question révisée et état ancien non confirmé restent distincts. Une lecture serveur défaillante ne laisse pas tourner un indicateur présenté comme certain. Les demandes historiques sans protocole de fin sont indiquées comme inconnues, sans relance ni succès inventé. Aucune réponse brute du fournisseur ou donnée d’un projet inaccessible n’est exposée par le statut.

Le même endpoint de lecture `GET /api/v1/meeting-sessions/{sid}/live-answers` retourne un champ `automatic` optionnel pour les anciens clients. Les événements de tentative portent `progress_version: 1` ; un événement `assistant.proactive-completed` est relié au même jeton de question/révision. La lecture ne lance aucun moteur et n’ajoute aucune tentative. Le délai affiché mesure l’attente depuis la réservation, **pas** le P95 depuis la stabilisation de la parole. Questions explicites et notes restent accessibles pendant l’attente lorsque la génération est disponible ; le cas indisponible ne promet plus une action absente.

Validation : **51 cas backend ciblés distincts** sur deux passages recouvrants ; **983 tests frontend/95 fichiers**, TypeScript/Vite et Ruff réussis. Le premier passage frontend échouait dans le nouveau test qui cliquait avant chargement ; corrigé et conservé dans les preuves. Deux fixtures réellement pilotées dans le navigateur vérifient attente, retard et disparition après fin persistée/rechargement. Leur question et leur fin sont explicitement injectées pour la recette UI : aucun LLM ni microphone. Elles ne qualifient pas une réponse utile réelle ou son P95.

Activation sur Agent 8001 après sauvegarde SQLite intègre des deux bases : `.ui-preview/backups/proactive-progress-20261021-61a90245842f`. Les lignes préexistantes des 19 tables métier et de séance contrôlées restent identiques. Brain/ERP sont sains, nouveau champ servi, JS/CSS identiques aux fichiers construits ; aucune capture active. Les anciens assets sont conservés pour les onglets ouverts. XPilot 8000 et les modules hérités sont inchangés. La suite globale backend de 2793 tests précède les derniers deltas ; les résultats ciblés ne sont pas présentés comme un nouveau global complet.

Preuve : `logs/foresight-runtime/PROACTIVE-QUESTION-PROGRESS-ROOT-20261021.json`. F13 et L12 restent ouverts pour leurs critères complets. État cumulé : 17/25 fonctions, 9/13 lots, 15/17 recettes qualifiés ; travail non commité et non poussé.


### Bilan consolidé du 21 octobre 2026 — diagnostics audio non retenus

État vérifié dans l’audit r52 : **17/25 fonctions, 9/13 lots et 15/17 recettes qualifiés**. L02, L03, L11 et L12 restent ouverts ; T03 et T16 restent ouverts. Le global backend précédent est terminé : 2793 tests réussis, un ignoré et 54 sous-tests. Les derniers correctifs ont leurs contrôles ciblés ; aucun nouveau global complet du dernier arbre n’est revendiqué. Le frontend courant compte 983 tests réussis sur 95 fichiers.

Le débruitage neuronal GTCRN et la séparation Conv-TasNet ont été évalués sur des fichiers vocaux fictifs existants. Ils restent exclus du produit : erreurs persistantes de consignation/négation, et régression d’une réserve « reste à vérifier » en affirmation. Le corpus initial et les sorties défaillantes sont conservés. Medium reste le profil de transcription ; aucun nouvel enregistrement n’est lancé par cette consolidation.

Détail et provenance : `docs/51_FORESIGHT_DIRECT_CPU.md`. Preuve : `logs/foresight-runtime/L03-NEURAL-AUDIO-DIAGNOSTICS-ROOT-20261021.json`.


### Réveil de l’assistant après transcription enregistrée — 21 octobre 2026

L’assistant automatique est désormais réveillé après la sauvegarde d’un segment ou d’une correction. Il n’attend plus uniquement son contrôle périodique de huit secondes pour découvrir ces changements. Les notifications reçues pendant une génération sont regroupées pour le passage suivant, sans créer un second worker. Les réglages d’activation, la file IA, la déduplication et la validation humaine restent applicables.

98 tests ciblés et Ruff passent. Activation sur 8001 après sauvegardes SQLite intègres et conservation des lignes préexistantes de 19 tables ; aucune capture ni génération lancée par la recette. Ce résultat supprime une attente de détection évitable ; il ne mesure pas le P95 de la carte utile. F13 et L12 restent ouverts. Aucun nouveau global backend complet du dernier arbre n’est revendiqué.

Preuve : `logs/foresight-runtime/PROACTIVE-COMMIT-WAKEUP-ROOT-20261021.json`. Audit courant : `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r53.json`.

Exploitation : aucun nouveau réglage ni service. `session_proactive.wake_worker()` pose un signal en mémoire après commit SQL ; ce signal ne démarre pas de worker et ne réserve pas d’inférence. La boucle efface le signal avant son traitement pour conserver une notification reçue pendant une génération. Le contrôle périodique reste le secours pour les écritures provenant d’un autre processus ou une notification perdue. L’arrêt réveille également la boucle inactive ; une génération déjà engagée conserve son comportement d’arrêt existant. `capabilities.proactive_limits.wake_on_transcript_commit` confirme la version active. Les tests de concurrence utilisent un secours volontairement fixé à 60 secondes et des barrières, sans attendre ces 60 secondes ni appeler de moteur.


### Mesure réelle des cartes réseau — 21 octobre 2026

Le vrai worker proactif et le bundle courant ont traité un corpus préparé de quinze questions fictives. Les textes finalisés sont injectés explicitement : aucune capture ni STT n’est revendiquée. Onze réponses correctes et sourcées ont été effectivement affichées. La douzième demande échoue avec HTTP 400 ; les trois suivantes restent non exécutées. Aucun échec supprimé ou relancé automatiquement.

Sur les onze cartes réussies seulement, médiane 1.560 s et P95 14.629 s, par rang supérieur ; trois dépassent dix secondes. Ces statistiques partielles ne qualifient pas le corpus complet. La mesure va du commit à la réception du reçu DOM après deux frames et vérification de visibilité ; elle inclut le retour HTTP du reçu. Elle ne commence pas à la fin de parole et ne mesure pas une chaîne STT complète.

L’inventaire réseau ultérieur répond HTTP 200 avec zéro instance chargée du modèle configuré et zéro LLM chargé. Cela ne prouve pas la cause exacte du refus antérieur, dont le corps n’a pas été conservé. Aucun modèle distant n’a été chargé ni réglage modifié par la recette. Les deux Jobs privés sont fermés avec code 0, sans capture ni résident STT. F13 et L12 restent ouverts ; les compteurs restent 17/25 fonctions, 9/13 lots et 15/17 recettes.

Preuve : `logs/foresight-runtime/F13-NETWORK-VISIBLE-ROOT-20261021.json`. Audit courant : `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r54.json`.


### Réponse automatique vide sans rejeu silencieux — 21 octobre 2026

Les questions proactives utilisent maintenant `retry_empty=False` : une réponse fournisseur vide reste un échec visible, sans seconde requête cachée à budget doublé. Le comportement des questions explicitement posées reste inchangé. 79 tests ciblés et Ruff passent ; le correctif est actif sur 8001 après sauvegardes SQLite intègres et conservation des lignes préexistantes de 19 tables.

Les quinze questions fictives disposent désormais chacune d’une réponse utile réellement affichée : 17 tentatives durables au total, deux échecs historiques conservés et deux reprises explicites par révision de segment. Les onze premiers résultats n’ont pas été régénérés. Sur le dernier passage, trois questions ont produit trois requêtes fournisseur, chacune limitée au budget demandé de 1200 tokens. Les délais restent au-dessus de la cible sur certains cas ; aucun P95 complet du dernier code n’est revendiqué en mélangeant ces passages. Ce sont des textes finalisés injectés, sans capture/STT. Les deux refus HTTP 400 initiaux ne sont pas déclarés expliqués par le défaut de rejeu.

Les copies de recette sont fermées ; aucun microphone ni modèle local, aucune sollicitation GPU du PC de recette. F13 et L12 restent ouverts. Preuve : `logs/foresight-runtime/PROACTIVE-EMPTY-REPLY-ROOT-20261021.json`. Audit courant : `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r55.json`.


### Capture matérielle et transcription CPU locale — 21 octobre 2026

Une seule séance explicitement autorisée, même nonce et même échéance depuis la première ouverture, a exercé les deux pistes Jabra, le retrait/rebranchement puis la sélection explicite des Realtek. Après retrait, le Studio affiche « Interrompue » avec « Périphérique audio interrompu : system ». Les fragments acquittés sont conservés, mais le drain gracieux reste non confirmé : ce résultat n’est pas transformé en arrêt réussi. La validation automatique a refusé le premier changement vers Realtek ; le serveur et son Job ont ensuite été fermés normalement, avec zéro processus restant et handles fermés, avant la continuation dans une nouvelle fixture.

La capture Jabra normale conserve 54,114 s et 302 893 octets en Opus. La transcription medium CPU locale retrouve les cinq repères fictifs dans le son système, mais un seul dans le microphone. La lecture Realtek confirmée conserve 26,990 s et 108 870 octets ; aucun des cinq repères n’est retrouvé. Un signal micro non nul est mesuré : sa présence ne prouve pas l’intelligibilité et la cause de la mauvaise reconnaissance n’est pas établie. Une capture Realtek intermédiaire, arrêtée avant réception de la confirmation, reste séparée du passage confirmé. Aucun fragment système Realtek n’est qualifié par ces passages silencieux.

Trois fixtures et leurs Jobs STT sont fermés ; tous les contrôles de conservation passent. Les transcriptions brutes restent exclusivement locales, sans lecture par Codex, écoute ni envoi audio/texte au LLM. Aucun réglage ou contenu métier de production n’est modifié. Les 16 tests de garde et trois refus de continuation hors fenêtre passent ; aucune nouvelle suite backend globale n’est revendiquée. L02, T03 et L12 restent ouverts. Les compteurs de clôture restent 9/13 lots, 17/25 fonctions et 15/17 recettes. Preuve : `logs/foresight-runtime/FINAL-HARDWARE-LOCAL-STT-ROOT-20261021.json`.


### Qualité du décodage direct et comparaison Windows — 21 octobre 2026

Le fichier physique Realtek conservé est exploitable : le décodage beam5 retrouve les cinq repères fictifs, y compris via le vrai résident/IPC CPU. La préparation de ses six fragments avec le contexte du direct retrouve quatre repères avec beam1 et cinq avec beam5. Sur les fragments Jabra, les deux profils restent à trois sur cinq : aucune correction générale des microphones n’est revendiquée. Ces indicateurs ne valident ni toutes les phrases ni la précision industrielle.

Le direct utilise désormais beam5, comme la transcription complète. Le profil CPU et le profil CUDA live passent au contrat2 ; les anciennes mesures liées à beam1 ne sont pas réutilisées. Le VAD reste actif. Le profil courant est réellement vérifié sur CPU, sans nouvel enregistrement ni envoi audio/texte. Ce réglage augmente le calcul : sur les fragments Realtek de ce diagnostic, le maximum observé est de5,734s ; aucun objectif de latence n’est déclaré atteint. Aucun essai GPU réel n’a eu lieu.

100 tests ciblés et Ruff passent. Activation sur8001 après sauvegardes intègres Brain/ERP et conservation des lignes préexistantes de19tables. Le rapport de disponibilité du résident est renouvelé avec sa portée précise ; qualité industrielle et latence restent non qualifiées. Aucun nouveau global backend complet n’est revendiqué.

Le moteur français Windows déjà installé (`System.Speech`/SAPI8.0) est comparé sur le même fichier en dictée générique, sans phrases fournies au moteur, sans microphone ni téléchargement : un repère retrouvé sur cinq, en0,978s. Ce cas ne justifie pas son remplacement de Whisper et ne constitue pas un classement général. La nouvelle API Windows AI Speech est une autre option locale, encore expérimentale selon Microsoft ; elle n’est ni installée ni testée ici. Le poste couvre son prérequis Windows11 24H2, ce qui ne prouve pas toute la compatibilité.

L02/L03/L11/L12 restent ouverts ; compteurs inchangés (9/13lots,17/25fonctions,15/17recettes). Preuve : `logs/foresight-runtime/LIVE-DECODING-QUALITY-WINDOWS-COMPARISON-ROOT-20261021.json`.


### Contrôle ciblé des deux cas industriels difficiles — 21 octobre 2026

Le modèle turbo déjà installé est comparé avec le nouveau réglage beam5 sur les deux Opus fictifs bruité et chevauché, sans nouveau téléchargement, microphone ou LLM. Il remplace encore « consignation » par « confirmation » dans le bruit et ne conserve que la seconde consigne dans le chevauchement. Il n’est pas adopté. Medium beam5 reste actif ; ce passage n’est pas une nouvelle qualification complète des quinze fichiers du profil medium. Le Job CPU est fermé, sans modèle restant. Preuve : `logs/foresight-runtime/L03-TURBO-QUALITY-ROOT-20261021.json`. Aucun lot supplémentaire clos ; L02/L03/L11/L12 restent ouverts.


### Preuves de l’assistant et panneau étroit — 21 octobre 2026

La question courante, lorsqu’elle est elle-même un segment interrogatif identique, est exclue des preuves de sa réponse ; sa transcription SQL reste conservée. Une affirmation identique à une recherche courte reste une preuve. Le prompt place désormais les extraits avant la question pour permettre la réutilisation du préfixe, sans réduire le budget1200tokens. Les quatre requêtes réseau fictives comparatives réussissent en0,76–1,60s ; cette mesure HTTP ne démontre pas le P95 visible du produit ni une causalité isolée du cache.

À814×668, le panneau Assistant sélectionné pouvait mesurer1,6px de haut quand les colonnes passaient sur deux lignes. Les lignes de grille gardent désormais250px minimum et restent accessibles par le défilement de la colonne. La vue réelle confirme250px de hauteur après correction.58tests backend ciblés,121tests frontend sur deux fichiers et TypeScript/Vite passent. Les assets précédents sont reconstitués à l’identique et conservés pour les onglets ouverts. Activation sur8001 après sauvegardes SQLite intègres et conservation des lignes préexistantes de19tables.

Les racines de calibration F13 sont conservées et fermées : deux contiennent une réponse réseau sans mesure visible qualifiée ; la troisième n’a lancé aucune question. Le navigateur/probe s’est bloqué sur une boucle d’observation de l’attribut disabled ; le setter conditionnel est corrigé hors ligne, sans nouvelle qualification navigateur revendiquée. Aucune mesure P95 actuelle complète, aucune clôture F13/L12 sur cette base. Aucun microphone, modèle local ou donnée métier de recette. Preuve : `logs/foresight-runtime/ASSISTANT-CONTEXT-VISIBLE-PANE-ROOT-20261021.json`.


### Reprise du refus LLM et mesure visible complète — 21 octobre 2026

Le client reprend une seule fois le refus HTTP400 exact `{"error":"Model is unloaded."}`, avec le même modèle, payload, clé et budget de réponse, dans le délai initial restant. Les deux tentatives sont comptées séparément ; les jetons d'un refus restent inconnus. Aucun chargement/déchargement explicite ni repli local pour ce refus. Les erreurs génériques et réponses vides ne bénéficient pas de cette reprise ; un second refus reste visible. Le JSON strict ne déclenche pas ensuite une troisième tentative sans schéma.

117 tests ciblés passent. Activation sur8001 après sauvegardes Brain/ERP intègres, droits hérités protégés et conservation des lignes préexistantes de19tables. Le serveur est sain après redémarrage officiel ; aucune capture active. Aucun microphone, modèle local ou donnée métier de recette.

La nouvelle mesure privée F13 utilise les quinze questions fictives originales, une fois chacune, le worker ordinaire, les citations/version SQL et les paragraphes réellement visibles dans Questions en direct à814×668. Quinze réponses utiles sont affichées, quinze HTTP200, sans reprise nécessaire dans ce passage. Les quinze citations C1 renvoient au segment de faits exact et à sa révision. Le contrôle littéral scellé retrouve14/15 réponses ; la quinzième, « Aucun achat n’est autorisé », est relue comme un refus correct sans modifier le corpus. Le P95 visible au rang ceil(0,95×15) vaut14,1203s : la cible10s n'est pas atteinte. La reprise après refus n'est donc prouvée que par tests isolés ; la cause du déchargement distant reste inconnue. L'ancien passage avec cinq cartes puis HTTP400 et le lancement refusé par le garde proxy sont conservés avec leurs Jobs fermés.

L02/L03/L11/L12 et F13 restent ouverts ; compteurs inchangés :9/13lots,17/25fonctions,15/17recettes. Aucun nouveau global backend complet revendiqué. Rapport : `logs/foresight-runtime/MODEL-UNLOADED-RECOVERY-F13-ROOT-20261021.json`. Audit cumulatif : `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r60.json`.


### F13 qualifiée après stabilisation du serveur réseau — 21 octobre 2026

L'utilisateur signale avoir corrigé le chargement intermittent d'EmbeddingGemma2 et de Gemma4. Cette modification externe n'est pas attribuée à Agent et ses paramètres globaux ne sont pas audités. Une nouvelle mesure complète, avec le même code Agent et le même corpus fictif original, obtient15réponses utiles visibles pour15questions, quinze HTTP200 et aucune reprise. P50visible1,3479s, P95visible1,7657s (rang supérieur, du commit du segment stabilisé au paragraphe visible après deux frames). La cible10s est atteinte dans cette configuration réseau. Le passage précédent à14,1203s et ses résultats bruts restent conservés ; aucune cause générale ni fiabilité continue du serveur n'est déduite de ce seul passage.

Les quinze réponses sont relues, les citations C1 et les révisions des segments SQL sont contrôlées. Le contrôle littéral scellé reste14/15 : « Aucun achat n’est autorisé » est une formulation correcte du refus, confirmée par relecture ; le corpus n'est pas modifié.58tests actuels vérifient contexte, droits/périmètre, déduplication des questions chevauchantes, admission, états obsolètes et réveil du worker. Le Job privé est fermé, sans capture, résident STT ou modèle local restant. Aucun changement des opt-ins de production, modèle distant, clé, budget ou donnée métier.

F13 (« Live Q&A et cartes proactives » après texte stabilisé) est qualifiée sur cette portée, y compris détection, déduplication et réponse sourcée. Cette mesure n'inclut pas la reconnaissance vocale : L03 reste ouvert. Aucun lot supplémentaire clos :9/13lots ;18/25fonctions ;15/17recettes. L02/L03/L11/L12 restent ouverts. Rapport : `logs/foresight-runtime/F13-STABLE-NETWORK-VISIBLE-ROOT-20261021.json`. Audit cumulatif : `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r61.json`.


### Conservation de la fin du tampon après interruption — 21 octobre 2026

Le helper WASAPI ordinaire pouvait quitter sa boucle après erreur de périphérique sans vidanger les callbacks déjà reçus et le résidu du convertisseur. Son nettoyage pouvait également sauter la fermeture si is_active() échouait. Il ferme désormais chaque flux avant la terminaison du contexte PortAudio, puis conserve la file reçue et la fin du tampon via le journal durable existant. L'interruption et la sortie en erreur restent explicites ; aucun faux état stopped, acquittement ou arrêt confirmé n'est ajouté. Une fermeture incertaine bloque la prétention à une vidange ; une saturation reste signalée. L'encodage Opus de production ne change pas.

Le test de régression échoue sur la copie précédente chargée uniquement en mémoire (aucun fragment final), puis passe sur le code courant avec les deux pistes et leurs PCM exacts.33tests ciblés et15sous-tests passent ;69contrats parent/reçus/reprise passent dans un dossier court. La première série parent conserve20échecs et49succès : les chemins temporaires atteignaient287caractères et échouaient à l'ouverture du .wav.pending. Le même contenu est relancé dans une nouvelle racine courte, sans modification Windows. Ruff passe. Les dispositifs et le rééchantillonneur sont simulés ; les tests utilisent le journal WAV existant pour inspecter le PCM, sans prétendre qualifier un nouvel encodage Opus réel.

Ce correctif conserve les données déjà livrées à l'application, pas les échantillons matériels non reçus. Pa_CloseStream abandonne les buffers internes actifs selon la documentation PortAudio : https://portaudio.com/docs/v19-doxydocs/portaudio_8h.html. Aucun nouveau retrait matériel n'a eu lieu et les anciennes captures ne deviennent pas qualifiées par une modification du code. La fixture physique finale utilise le producteur ordinaire, sans substitution par l'ancien producteur privé de qualification. Le parent continue de refuser un drain non confirmé. Aucun microphone, modèle, redémarrage backend, réglage ou donnée métier modifiés ; le prochain lancement ordinaire charge le script courant. Agent reste mono-serveur sur8001.

L02/L03/L11/L12 restent ouverts ;9/13lots,18/25fonctions,15/17recettes. Aucune nouvelle suite globale complète revendiquée. Rapport : `logs/foresight-runtime/NATIVE-INTERRUPTION-TAIL-ROOT-20261021.json`. Audit : `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r62.json`.


### Préparation matérielle regroupée v2 — 21 octobre 2026

Le protocole `.ui-preview/pilots/hardware-consolidated-v2-20261021/PROTOCOL.md`
prépare une fenêtre commune de deux heures après première ouverture audio,
partagée par les démarrages/reprises, sans quota d'essais ni seuil RAM. Aucun
accord ancien copié ; la nouvelle autorisation reste en attente. Le Jabra n'est
pas détecté lors de l'inventaire, les Realtek le sont. Aucun microphone ouvert.

La lecture fictive peut viser explicitement le casque ou les haut-parleurs
Realtek ; le garde vérifie la correspondance avec le loopback actif. La première
séance est sans projet pour vérifier aussi F03, puis l'attribution/rejeu est
limitée aux deux projets fictifs. La transcription CPU des nouvelles captures
reste locale et réservée aux fichiers dont la fermeture/conservation est prouvée.
Aucun LLM, envoi audio/texte, téléchargement, GPU ou coupure réseau dans ce paquet.

18tests de préparation et42sous-tests passent. Le prévol réel de la copie privée
refuse start/resume sans accord, ferme son Job avec zéro processus restant et
handles fermés ; une séance sans projet est vérifiée en SQL privé. Ces preuves
ne qualifient pas le matériel. Aucun lot supplémentaire clos :9/13lots,
18/25fonctions,15/17recettes. Rapport :
`logs/foresight-runtime/HARDWARE-CONSOLIDATED-V2-PREPARATION-ROOT-20261021.json` ;
audit cumulatif `acceptance-r63.json`. Architecture mono-serveur8001 inchangée.


### Comparaison CPU4/8 du profil courant — 21 octobre 2026

Les quinze Opus fictifs scellés sont décodés avec medium beam5 sur CPU/int8,
quatre puis huit threads dans deux Jobs successifs, sans microphone ni réseau,
GPU, téléchargement ou changement de configuration. Le processeur expose12cœurs
et16processeurs logiques. Chaque profil reçoit le même échauffement clean-02 ;
les fichiers sont contrôlés par empreinte et les poids/configurations sont
identiques. Les deux Jobs sont fermés, vides et handles fermés.

Les transcriptions sont strictement identiques. P50calcul4threads7,9371s,
8threads7,0596s ; P95calcul8,2756s contre8,0483s. Ces mesures n'incluent ni
découpage/capture, file, SQL ou affichage. L'ordre fixe et la charge non exclusive
ne permettent pas un classement général. Huit threads n'est pas adopté sur ce
seul passage ; le profil courant reste quatre threads, sans requalification
artificielle de la disponibilité du résident.

La relecture retrouve33/35annotations métier : « consignation » devient encore
« confiniation » dans le bruit, et le refus de l'option automatique est omis avec
chevauchement. Le point d'interrogation ajouté à clean-12 reste à relire. Les
scores littéraux sont conservés séparément :27/35dans le premier compteur de
comparaison qui supprimait la ponctuation décimale,28/35après réemploi local du
compteur scellé, sans nouvelle inférence ni correction de transcription/corpus.
Les formes équivalentes (Alpha24, nombres/unités abrégés, € et hors taxe) sont
relues, sans prétendre à une validation humaine ou à une précision parfaite.

Aucune clôture L03/F06/L12 ;9/13lots,18/25fonctions,15/17recettes. L'accord de la
nouvelle séance matérielle reste en attente. Rapport :
`logs/foresight-runtime/CPU-THREAD-COMPARISON-ROOT-20261021.json` ; audit r64.


### Vérification globale courante — frontend terminé, backend en cours (21 octobre 2026)

La suite frontend complète courante termine avec95fichiers et983tests réussis,
sans échec, erreur ou skip ;248sources restent identiques avant/après. Le passage
jsdom utilise deux workers et dure environ180s. Aucun navigateur réel, microphone
ou modèle. La suite backend complète reste sur son processus initial, sources
Python figées ; aucun résultat terminal global n'est encore revendiqué.

Le troisième cas du premier groupe backend a échoué. Son diagnostic isolé passe,
mais la cause exacte du premier échec et son bilan complet restent à examiner :
ce résultat initial n'est ni effacé ni converti en succès. Aucune nouvelle suite
complète n'est relancée sur simple délai d'observation. L'accord matériel reste
en attente ; aucun lot supplémentaire clos (9/13lots,18/25fonctions,15/17recettes).
Rapport : `logs/foresight-runtime/CURRENT-FRONTEND-GLOBAL-ROOT-20261021.json`.


### Vérification des sauvegardes — 22 octobre 2026

La sauvegarde des données prise avant l’activation du choix CPU/GPU a été
réellement restaurée dans un dossier privé neuf : 19 tables conservées,
intégrité des deux bases valide, aucune violation de clé étrangère. Les notes,
fragments audio, livrables et travaux documentaires sont vérifiés ; les bases
actives et les archives sources restent inchangées. L’extraction intégrale
du point complet de 144 692 fichiers est lancée séparément ; son seul lancement
ne constitue pas une preuve de restauration achevée ni de démarrage du logiciel
restauré. Aucun microphone, modèle ou envoi réseau dans cette vérification.
Preuve : `logs/foresight-runtime/BACKUP-RESTORATION-CURRENT-ROOT-20261022.json`.
Les lots L02/L03/L11/L12 restent ouverts.
