# Agent — connaissance projet et ERP local

Réunions : boutons harmonisés avec le thème Agent et haut de page compact.
Options, périphériques et diagnostic restent accessibles ; notes, audio et
validations sont conservés. Voir [la recette](docs/24_UI_UX_REDESIGN.md).

## Corrections UX — 22 octobre 2026

Les [20 corrections de l’audit](docs/59_UX_CORRECTIONS_20261022.md) sont
appliquées : suppression de mails confirmée, navigation disponible en cas de
panne du portefeuille, preuves accessibles depuis le projet, reprise des
filtres, parcours CDC et comptes rendus simplifiés. Modules, données et
validations humaines conservés. L’architecture reste mono-serveur Agent sur
8001 ; XPilot 8000 reste externe. Le bundle corrigé est livré localement pour
le prochain démarrage normal. Voir le rapport pour les tests et leurs limites.

## Audit UX initial — 22 octobre 2026

[Rapport transversal et plan de correction](docs/58_UX_AUDIT_20261022.md) :
20 constats priorisés, captures privées et limites de vérification explicites.
Audit du bundle existant sur copies isolées, sans modification de l’interface
ni des données métier actives. L’architecture reste un serveur Agent sur 8001.

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


## Qualité UX/UI permanente de Codex — 22 octobre 2026

Les règles de `AGENTS.md` et sept skills dans `.agents/skills/` encadrent les
prochaines modifications d'interface selon les usages métier. Contrôle léger :
`npm --prefix web run ux:check`; audit visuel complet sur demande. Playwright MCP
est configuré côté utilisateur et testé dans Edge. L'architecture mono-serveur
Agent sur 8001 reste inchangée. Installation, validation, sauvegardes et
redémarrage Codex : [système qualité UX/UI](docs/57_UX_QUALITY_SYSTEM.md).

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

Dernier contrôle matériel du 21 octobre : la lecture humaine au microphone Jabra
retrouve les quatre valeurs et unités attendues par transcription CPU locale.
La lecture Realtek reste non qualifiée : la capture était interrompue à la
confirmation. Un diagnostic Realtek ultérieur s’arrête normalement avec 426,179 s
conservées ; il ne prouve pas la résolution de l’interruption antérieure.
Toutes ces captures privées sont fermées, sans publication métier ni LLM.
Le global backend est terminé : 2 851 réussites, trois échecs et un test ignoré.
Les corrections suivantes passent deux cohortes ciblées de 41 et 50 tests
(avec recouvrement), sans nouveau verdict global. Les décomptes restent
9/13 lots, 19/25 fonctions, 15/17 recettes ; L12 reste ouvert.
[État courant](docs/40_FORESIGHT_ACCEPTANCE.md).

Le statut de la séance sélectionnée se synchronise maintenant aussi dans la
liste latérale après arrêt, pause ou interruption. Correctif actif sur8001,
vérification visuelle sans audio et986tests frontend réussis ; les anciens
assets restent disponibles. [Détail](docs/23_MEETING_AUDIO.md#statut-latéral-de-la-séance-synchronisé--21-octobre-2026).

État courant de qualification : **9/13lots,19/25fonctions et15/17recettes**.
F03 (capture immédiate sans projet puis rattachement rejouable) est qualifié.
L02/L03/L11/L12 et T03/T16 restent ouverts ; le global backend courant continue,
avec deux échecs observés à examiner au terme du processus.
[Matrice actuelle](docs/40_FORESIGHT_ACCEPTANCE.md).

La [recette matérielle courante](docs/23_MEETING_AUDIO.md#recette-matérielle-regroupée-en-cours--21-octobre-2026)
a conservé les pistes système Jabra et Realtek avec arrêt normal ; la lecture
humaine des microphones reste attendue. Aucun microphone de recette ne reste ouvert.

La sauvegarde complète d’avant fusion a été revérifiée le21octobre :
17702fichiers conformes aux SHA256, restauration neuve des bases Brain/ERP
intègre et sans violation de clé étrangère. Cela vérifie le point de retour
initial ; ce n’est pas une nouvelle copie du travail courant.
[Preuves et limites](docs/38_FORESIGHT_DELIVERY.md#sauvegarde-initiale-revérifiée--21-octobre-2026).

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


## IA en attente : priorité des questions et budget automatique corrigés

Les travaux automatiques réutilisent maintenant le budget d’attente du
planificateur,30s, au lieu d’expirer au bout de2s devant un serveur sain occupé.
Une question arrivée après deux automatiques passe effectivement en premier,
avant le proactif et l’enrichissement, dans le contrôle réel du client réseau.
L’annulation et la protection des notes restent vérifiées ; correction activée
sur Agent8001 après sauvegarde/restauration privée des trois bases.
Voir `docs/40_FORESIGHT_ACCEPTANCE.md` ; précision du direct et L12 restent ouverts.


## État de la fusion Foresight — matrice d’acceptation

La [matrice actuelle](docs/40_FORESIGHT_ACCEPTANCE.md) relie les13lots,25fonctions
et17recettes aux preuves conservées. Le CR complet medium CPU est actif et
vérifié ; l’endurance conserve1440fragments sur une heure. La capture intégrée,
la précision du direct, la concurrence et le volume réellement saturé restent
distincts. L12 reste ouvert. Les cibles de délai ne coupent plus la conservation.


## Réunion : transcription complète medium CPU activée

Les enregistrements complets préfèrent maintenant Whisper medium lorsqu'il est
déjà installé. Le parcours du Studio vers la relecture et le brouillon de CR
utilise cette préférence ; le direct préfère aussi medium CPU déjà installé, dans le mode essai. Les réglages explicites
restent prioritaires, sans téléchargement ou nouveau service. Agent reste
sur8001 et XPilot externe sur8000. Le modèle est chargé à la demande de traitement.
Le parcours réel medium CPU → diarisation → CR réseau → publication/rejeu privés
réussit sur20,25s d'audio fictif, avec les six valeurs techniques conservées.
La relecture reste nécessaire ; voir `docs/23_MEETING_AUDIO.md`. L12 reste ouvert.


## Réunion : endurance réelle d'une heure réussie

La recette réseau sur deux pistes fictives conserve les 1 440 fragments acquittés,
traite toutes les transcriptions et termine ses trois fenêtres LLM. Le serveur
et ses enfants se ferment normalement. Les anciens plafonds forfaitaires RAM,
retard et backlog de recette sont retirés. Les suites déjà passées sont réutilisées
sur sources inchangées. La précision du direct et sa latence visible restent
distinctes du parcours audio → brouillon de CR déjà exercé ; relecture nécessaire.
Résultats actuels dans `docs/38_FORESIGHT_DELIVERY.md` ; L12 reste ouvert.


## Recette matérielle regroupée préparée

La navigation et les sélecteurs micro/son système sont vérifiés sur deux projets
fictifs, sans audio ni modèle. Un seul accord groupé sera demandé pour les
contrôles matériels restants, au lieu de nouvelles permissions par fragment.
Le test réseau d'endurance reste séparé. Voir `docs/38_FORESIGHT_DELIVERY.md`.


## Recette réunion simplifiée — 15 octobre 2026

Les plafonds arbitraires de la recette T12 sont retirés : un retard HTTP ou
une mesure indisponible ne coupe plus les fragments déjà conservés. La copie
V8 utilise une boîte d'envoi durable et des reprises idempotentes. Aucun
changement des moteurs ou bases métier. État réel et limites dans
[la livraison Foresight](docs/38_FORESIGHT_DELIVERY.md). L12 reste ouvert.


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

Essai privé sur rendus PNG et texte PDF de dessins CAO : modèle CPU réellement utilisé, huit vecteurs produits ; recette toutes modalités refusée, texte 2/2 et images 0/2 au rang1. Les huit DXF/SVG restent conservés/non pris en charge ; aucune lecture CAO native, activation canonique ou clôture L09/L12.

[Résultat réel et limites](logs/foresight-runtime/CAD-V1R2-progress-ROOT-20261015-b53d0468cd4c4816a558029f07261d94.json).


## Reçus audio corrigés dans les sources ; rechargement en attente — 15 octobre 2026

Rejeu et reçus audio corrigés, 37 tests ciblés réussis ; rechargement du backend 8001 en attente. Essai CPU CAO V1R1 refusé avant admission du moteur ; V1R2 en préparation privée. Suite backend globale : 2459 cas uniques, 2458 passés, 0 échecs, 0 erreurs et 1 ignorés ; sortie 0.

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


## Indicateurs de travail — 13 octobre 2026

Agent signale les opérations utilisateur en cours dans toutes les rubriques :
imports, recherche, analyses, notes, réunions, réglages, sauvegardes et fichiers.
L'indicateur commun apparaît immédiatement pour une écriture, après 800 ms pour
une lecture lente. Les mises à jour automatiques restent discrètes ; les travaux
de fond conservent leur progression métier dans les panneaux concernés.

La sélection d'un CDC affiche l'importation/extraction puis la mise à jour de
la liste. Le bouton reste désactivé jusqu'à la présence du document ; une erreur
d'actualisation permet de relire la liste sans réimporter un CDC déjà enregistré.
Les téléchargements internes suivent la réception complète et proposent un lien
manuel vers les octets préparés. L'enregistrement sur disque reste au navigateur.

Validation : 916/916 tests frontend, TypeScript et build passés ; contrôle visuel
sur un CDC fictif avec le même build, sans base réelle ni qualification du
sélecteur natif. Le serveur unique reste Agent 8001 ; XPilot 8000 est inchangé.
[Détails](docs/24_UI_UX_REDESIGN.md) ; les reçus précédents sont conservés plus bas.


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

Le candidat composite termine sa régression complète : **2 361 tests Python
réussis, 2 ignorés**, Ruff réussi, sources inchangées. Il reste non activé ;
la sauvegarde finale coordonnée et les recettes matérielles du lot 12
restent à terminer. Voir le [bilan](docs/38_FORESIGHT_DELIVERY.md).

Pour démarrer une réunion, consulter le [parcours pas à pas](docs/23_MEETING_AUDIO.md#lancer-une-réunion-dans-agent) :
dans le Studio, déplier **Périphériques** pour choisir le micro et la sortie
Windows, puis cliquer **Démarrer la réunion**.

## Capture Windows — gardes d'arrêt vérifiés logiciellement

Une correction conserve chaque fragment natif sans dupliquer sa notification
dans une file mémoire. Les contrôles sont bornés à huit messages. Un arrêt
réussi exige la fin du lecteur et la sortie correcte du helper ; une erreur
reste prioritaire, y compris lors d’un rejeu. Si l’arrêt n’est pas confirmé,
une action distincte permet de **conserver les fragments acquittés**, avec
avertissement durable de conservation partielle. La barre globale garde
l’erreur et un accès à la séance après un arrêt échoué, même lorsque la
réservation native a disparu. Le serveur 8001 a été relancé dans le parcours
notes ; les assets actifs correspondent au candidat vérifié : **802 tests
React**, TypeScript/build et Ruff réussis. La régression Python V1 termine
à **2 183 réussis/1 ignoré**, mais des sources ont changé pendant son exécution.
La V2 termine à **2 190 réussis/1 ignoré**, exit0, sur 371 sources inchangées.
Le [reçu terminal](logs/foresight-runtime/native-control-queue-20261012/python-v2-terminal.json)
sépare ces preuves du candidat STT en copie isolée. Le stock SQL de transcription
de la version active reste non borné et L12 ouvert.

Un candidat isolé borne l'admission STT et ajoute la transcription explicite
d'un audio personnel sans projet. Son frontend V5 passe 816 tests et le build ;
la reprise backend passe 153 tests/1 ignoré. Désactivation du batch et alertes
de lecture persistantes sont corrigées et relues. La première passe globale
conserve deux échecs désormais repris ; la V2 Python termine à **2 300 réussis/2
ignorés**, exit0, sur 377 sources et 56 ressources inchangées. Le
[compagnon terminal V5](.ui-preview/pilots/stt-admission-stage-20261012/qa/staged-checkpoint-v5-python-v2-terminal.json)
revérifie leurs empreintes actuelles sans modifier le checkpoint historique.
La conservation sous cadence fictive est vérifiée en copie isolée ; L12
reste ouvert. Le [protocole](.ui-preview/pilots/STT_ADMISSION_NEXT_PROTOCOL.md)
distingue ce candidat de la version actuellement servie. Le smoke fictif de
30 secondes est réussi sur la mesure ACK revue ; la cadence fictive d'une heure
termine avec 720 paires et 1 440 fragments conservés et exportés, retour ACK
maximal de 0,177379 s et quota maintenu à 24 fragments/120 secondes. Le
[résultat terminal](logs/foresight-runtime/sqc-run-20261012-163237-ddd94164/qualification.json)
ne qualifie ni transcription, ni matériel, ni latence d'affichage. Le
[reçu de lancement](logs/foresight-runtime/sqc-prepared-20261012-162929-679659ce/root-launch.json)
conserve les références exactes et les échecs antérieurs.

La correction responsive privée passe 858 tests, TypeScript/build et une
[recette réelle du navigateur](.ui-preview/pilots/a9-responsive-capsule-20261012-193009-620a51a6/proof/root-ui-qualification.json)
à 320/670/1280/1915 px : défilement local au clavier, conversion Action→Tâche
et accès à la tâche conservés. Le serveur fictif est fermé. Le contraste des
traits du graphe est insuffisant dans ce premier build ; une autre copie corrige
six couleurs SVG et passe 858 tests/TypeScript/build. Sa
[recette visuelle réelle](.ui-preview/pilots/a9-graph-contrast-capsule-20261012-200758-543f2df4/proof/root-graph-qualification.json)
mesure les traits à 5,269:1 et le focus clavier à 4,936:1 dans le thème clair,
avec zoom et consultation de source conservés ; le serveur fictif est fermé.
Ces copies ne sont pas activées ; T13 et L12 restent ouverts. Le
[dossier composite de mise à jour](.ui-preview/pilots/native_next_promotion_plan_v3.md)
recense 29 fichiers ; ses neuf contrôles de fichiers passent. L'état opérationnel,
les sauvegardes et la compatibilité des données restent à vérifier avant activation.

Une requête de compatibilité séparée voit la carte CUDA et `int8_float16`.
Le [protocole GPU](.ui-preview/pilots/STT_GPU_QUALIFICATION_PROPOSAL.md) décrit
les vérifications restantes ; le profil Agent demeure CPU et aucun modèle
GPU n'a été chargé par cette requête. Un essai GPU séparé charge ensuite le
modèle, mais échoue avant toute transcription sur `cublas64_12.dll` absente
ou non chargeable ; le [reçu d'échec et de fermeture](logs/foresight-runtime/gpu-short-run-20261012-173342-f7bc6d33/qualification.json)
confirme la fin du processus privé. L'essai suivant, autorisé après installation
privée NVIDIA, transcrit les douze phrases fictives (27 informations critiques
préservées), mais échoue au contrôle d'origine d'une DLL chargée. Il ferme son
processus en 22,042 s. Ses fenêtres courtes calculées en environ 0,6 s restent
incomplètes sur mm² : aucun verdict de direct industriel ou d'affichage n'en
découle. Le [reçu et la revue des textes](logs/foresight-runtime/gpu-short-run-20261012-181408-3771563f/root-semantic-review.json)
conservent ces limites ; le profil GPU reste non activé et l'accord unique est consommé.

Le candidat regroupé NEXT passe **858 tests React**, TypeScript/build et
**70 tests backend ciblés**, avec revue indépendante. Sa régression complète
Python V1 termine à **2 330 réussis, 2 échecs et 2 ignorés** sur 378 sources
et 57 ressources inchangées : export avec droits modifiés et garde propriétaire
natif ont échoué dans cette passe historique.
Les deux fixtures sont corrigées avec refus et conservation des données inchangés :
73 tests ciblés passent, avec revue indépendante. La V2 complète, lancée à
18:46:51 UTC, termine à **19:24:29 UTC : 2 332 réussis/2 ignorés**, soit 2 334 cas
sans échec ni erreur, sortie 0, sur **378 sources Python et 57 ressources inchangées**.
Le [reçu global V2](.ui-preview/pilots/native-interruption-next-20261012/qa/python-global-next-v2/qualification.json),
son [compagnon terminal](.ui-preview/pilots/native-interruption-next-20261012/qa/python-global-next-v2/root-terminal-companion.json)
et le [Ruff global V2](.ui-preview/pilots/native-interruption-next-20261012/qa/ruff-final-20261012-192805-8cc955c5/qualification.json)
confirment ce résultat et Ruff sortie 0 sur les mêmes sources. Les 26 fichiers de promotion sont
explicitement listés ; le contrôle daté de 17:48 UTC observe une analyse de jalons active et huit en attente, fermant alors
la porte opérationnelle. Aucune activation ni interruption de ces travaux
n'est effectuée. Le correctif responsive externe conserve sa recette distincte de
858 tests/TypeScript/build ; sa vérification navigateur reste ouverte. NEXT n'est
pas activé et ce résultat ne clôt ni T12, ni T13, ni L12.
Les deux bibliothèques NVIDIA dans un dossier privé et un
seul nouvel essai fictif de cinq minutes ont été autorisés par l'utilisateur ;
installation et essai sont terminés, sans nouvel essai implicite.

Un nouvel essai GPU V6, autorisé séparément, s'arrête avant import CT et
chargement du modèle : deux handles Windows restent sans chemin. Les observations
sont cette fois enregistrées avant le refus. Processus, Job et NVML fermés en
10,25 s ; aucun cas transcrit, aucun profil activé. Le
[reçu terminal](logs/foresight-runtime/gpu-short-run-20261012-191119-5f626f87/root-terminal-review.json)
conserve cette limite. Cet accord unique est consommé ; le diagnostic reste en lecture.

## Contrôle du direct et synchronisation — 12 octobre 2026

Une passe complémentaire ajoute un interrupteur **Transcription directe**
distinct de la capture et désactivé par défaut. La reprise des seuls fragments
en échec conserve audio et corrections humaines. Le Studio reçoit des
notifications pour actualiser ses lectures, tout en gardant le contrôle des
versions et des brouillons. Le flux n'envoie aucun texte métier ou citation ;
les lectures dédiées revérifient les droits actuels.

La qualification complète historique V3 passe **2 141 tests Python réussis/1 ignoré**
(2 142 cas, zéro échec/erreur, 369 sources inchangées) et **768 tests React**,
avec TypeScript/build conformes. Le [global Python V3](logs/foresight-runtime/live-controls-global-20261012-v3/qualification.json)
couvre aussi le correctif des droits de l'export. La recette fictive conserve
note et segment après navigation/recharge. La livraison canonique est vérifiée
sur 8001 : sauvegarde de 1 359 fichiers, restauration des deux bases avec
intégrité SQLite correcte et empreintes HTTP du build `B8cwhgBe/BJ0BE6LI`.
Les 18 tables métier contrôlées et les 1 340 originaux initiaux sont conservés.
Les quatre opt-ins restent faux. La version précédemment
servie ci-dessous reste un résultat historique distinct. Drive reste exclu,
l'adaptation visuelle validée et le moteur de notes XPilot conservé. Le lot L12
reste ouvert pour capture intégrée, direct industriel et tenue en charge.

Le global V2 conserve son résultat historique : **2 123 réussis/18 échecs/1 ignoré**.
Les répertoires privés `AppData/Temp/minipilot-test-*/storage/raw` avaient disparu,
sans acteur attribué ni stockage partagé démontré. Les [18 cas repris](logs/foresight-runtime/live-controls-failed18-retake-20261012-v3/qualification.json)
passent séparément ; le global V3 utilise ensuite TEMP/TMP/TMPDIR dédiés sous
`.pytest_work/`. Ces reprises ne s'ajoutent pas au total actuel.

## Studio — vérification complémentaire du 12 octobre 2026

Le Studio protège maintenant les segments et brouillons contre des réponses
de lecture arrivées dans le désordre. Un accusé de sauvegarde ancien conserve
une note plus récente et les modifications encore saisies. Le moteur de notes
ERP hérité de XPilot reste l'autorité. **724/724 tests React dans 75 fichiers**,
TypeScript et build réussissent ; les 106 tests ciblés sont inclus dans ce total.
Une recette navigateur sur bases fictives retrouve la note ERP version 2 après
navigation/rechargement et passe neuf contrôles. Le build `CHpAuznx/BJ0BE6LI`
est servi et vérifié par SHA sur **8001**, avec sauvegarde du build précédent.
Les capacités séance/proactif/enrichissement restent désactivées et Drive exclu.
La capture intégrée, le direct industriel et la réunion longue restent à qualifier
dans le [registre](docs/38_FORESIGHT_DELIVERY.md). Aucun commit ni push effectué.

Un candidat Parakeet INT8 testé séparément traite quinze phrases fictives avec
un P95 de calcul de **1,285 s**, hors chargement et affichage. Il obtient **28/35**
attentes métier, avec des erreurs d'unités et de clauses sous chevauchement de voix.
Ce résultat ne qualifie pas le direct : les fenêtres de cinq secondes n'ont pas
été exécutées et aucun profil du logiciel n'est remplacé. La recette de 60 minutes
reste à qualifier ; le panneau navigateur est désormais réellement visible.
Son premier lancement réel s'est arrêté avant la cadence sur un défaut du
harnais de contrôle Windows (`subprocess.Popen` avec `executable=None`).
Le correctif passe 70 tests ciblés. Le second essai conserve un délai UI_READY
dépassé, avec fermeture naturelle. Le troisième reçoit une vraie attestation
d'affichage mais échoue sur la route privée du harnais avant le premier fragment.
La cadence 60 minutes reste non qualifiée ; ces refus et leurs nettoyages sont conservés.
Le correctif HTTP du harnais passe ensuite 80/80. Le quatrième essai atteint
la cadence privée, mais les deux premiers uploads échouent avec HTTP500 : les
chemins temporaires Windows atteignent 278/281 caractères, zéro fragment est
acquitté. La fermeture naturelle est attestée : sortie0, Job vide et handles fermés.
Le correctif des seuls chemins privés passe [88/88 tests ciblés](logs/foresight-runtime/t12-storage-path-final-20261012-080347-6f3a5345/qualification.json).
Le cinquième paquet, relu favorablement sur18/18 points, est lancé avec une
véritable attestation UI_READY à08:14:20,837UTC ; son dossier privé est frère
du dossier de preuve. **Ce point d'avancement n'a pas de résultat de qualification** :
60minutes, latence, qualité industrielle et L12 restent ouverts.

**Résultat ultérieur de l'essai5 — 08:27UTC : arrêt de sécurité, non qualifié.**
Le driver dure environ765,21s, avec306 nouveaux fragments conservés
(153 par piste) et un rejeu supplémentaire. Le retard atteint605s sur micro
et600s sur système ; la borne de sécurité de recette est dépassée, sans valoir
quota produit. Le worker Turbo CPU int8/4threads termine65 fragments et conserve
88 segments provisoires. Une fenêtreLLM exerce cinq opérations et trois envois
effectifs ; la priorité en file reste non qualifiée, les deux fenêtres suivantes
non exercées.
Le nettoyage naturel réussit (sortie0/Job vide/handles fermés), mais ni60minutes,
ni latence industrielle ne passent. Gemma est déchargé après repos, avec Agent
et ses deux bases sains. Le [registre](docs/38_FORESIGHT_DELIVERY.md) conserve
ce résultat, sa revue RO conforme (21 points), le point d'avancement précédent
et toutes les réserves L12. La revue ne transforme pas cet échec en qualification.
Le seul essai supplémentaire à quatre hypothèses conserve le score strict
28/35. Son P95 descriptif de 1,231 s est calculé depuis les bruts ; le contrôle
de terminaison échoue et ce candidat reste non qualifié. Les résultats et
échecs restent séparés dans le registre.

## Fusion fonctionnelle Foresight — 11 octobre 2026

Le nouvel espace Réunions réunit notes, capture progressive, transcription,
assistant sourcé et publication relue. Sources rassemble les documents conservés,
leurs versions, labels, recherche et liens de provenance. Statistiques et
Préparation exposent les mesures et l'état des moteurs. L'ensemble utilise le
serveur unique **8001**, les projets et les modules métier existants.

Pour lancer une réunion : **Réunions → Nouvelle séance**, puis **Activer les
réunions** si l’espace est désactivé. Saisir un titre, choisir éventuellement
un projet et cliquer sur **Ouvrir la séance**. Dans **Source audio**, choisir
**En salle · microphone**, **À distance · son du PC**, ou **son du PC + ma voix**.
Le volet **Périphériques** permet de choisir le microphone et la sortie Windows
à enregistrer, puis **Démarrer la réunion** lance la capture. Le choix de sortie
sélectionne le son enregistré ; la sortie de lecture se règle dans Windows.
L’activation de l’espace ne démarre aucune capture et conserve les réglages
distincts de transcription, de proactif et d’enrichissement. Le navigateur et
l’import audio restent disponibles comme alternatives. Ce parcours est livré
sans changer les verdicts de qualification matérielle ou de transcription L12.

Une séance peut commencer sans projet puis être attribuée : une seule note ERP
est créée, et un enregistrement n'existe que si un véritable audio est conservé.
Les propositions IA restent distinctes du texte humain ; les actions deviennent
des tâches uniquement sur demande explicite. La capture Windows propose les
pistes microphone/système séparément. Le mode navigateur conserve ses fragments
localement avant leur acquittement par le serveur.

Le [plan L00–L12](docs/37_FORESIGHT_FUSION_PLAN.md), les
[preuves et limites de recette](docs/38_FORESIGHT_DELIVERY.md) et les
[références visuelles](docs/39_FORESIGHT_REFERENCE_UI.md) distinguent développement,
activation et vérification réelle. Sauvegarde préalable complète vérifiée :
`C:\AgentBackups\foresight-before-20261011-173855`. Les capacités sont désactivables
dans Préparation ; exports et récupération des séances existantes restent
accessibles. Aucun module métier ni donnée historique n'est supprimé.

État de recette : Sources et Statistiques sont disponibles sur 8001 ; le nouvel
espace de séance et le proactif restent désactivés pendant la qualification.
Sur bases fictives, notes/version, synthèse relue, action citée et publication
sont vérifiées dans le navigateur, à 1280/670/320 pixels. Le second essai Realtek
autorisé a fermé normalement le microphone à 30 s et conservé 29,9 s en six WAV ;
le quota de ce premier protocole reste incomplet. Après deux essais Jabra
partiels, le harnais v2 conserve exactement 30 s PCM en six fragments et ferme
normalement le matériel après 32,69 s, dans l'ouverture autorisée de 45 s.
La navigation pendant capture intégrée et le remplacement du périphérique
restent à qualifier ; la continuité physique n'est pas certifiée par ce quota.
Le direct industriel reste non qualifié sur ce PC, avec des
erreurs de valeurs/unités et une latence excessive selon le profil.
Le lot L12 demeure ouvert ; la liste précise des critères est dans le registre.
Décision utilisateur du 11 octobre : Google Drive est exclu et reste désactivé.
L'adaptation visuelle présentée est validée, avec le moteur de notes XPilot
conservé ; aucune copie exacte à ±2 pixels n'est revendiquée. Ces deux points
ne constituent plus des conditions de clôture de cette livraison. Les recettes
matérielles, la qualité du direct et l'activation restent distinctes.
Première régression complète : **1 920 tests Python réussis/1 ignoré**, **569 tests React
réussis**. La passe complémentaire React atteint **672 tests/75 fichiers**,
TypeScript/build conformes. La passe Python complémentaire brute conserve 1 948
réussites, 16 échecs de chemins/isolation de tests et un ignoré ; les 16 cas
repris passent sous chemins courts, avec des suppléments pour les correctifs.
Le registre distingue ces passages d'une passe globale unique. Treize tests simulés du harnais
microphone passent séparément. Les données métier et validations humaines sont
conservées ; les changements des trois tables de suivi historiques sont détaillés
dans le registre. Aucun commit ni push demandé.

La recette complémentaire couvre l’historique des questions par séance et
périmètre, l’épinglage durable des cartes, les liens vers les versions exactes
des notes et l’interprétation des fichiers PDF/tableurs importés par URL.
L'enrichissement automatique est un opt-in distinct : contexte sauvegardé stable
au moins huit secondes, une tentative durable et acceptation humaine explicite.
Les rapports de cette passe restent distincts de la première régression.

La référence visuelle retenue par l'utilisateur est celle des écrans publics
documentés de Google. Les vues non observables restent des adaptations Agent.
La passe Markdown corrige la conversion des notes reçues du serveur :
97 tests ciblés passent, puis la note version 3, l'ancienne version citée et
l'épingle sont retrouvées dans le navigateur après rechargement. Le contrôle
final sur 8001 vérifie les empreintes des assets ; 18 tables métier et 1 340
originaux sont conservés à l'identique. Ces contrôles antérieurs ne clôturaient
pas les critères matériels et de direct industriel de L12 ; Drive est depuis
exclu par l'utilisateur. La nouvelle preuve de réseau coupé est distinguée
ci-dessous.

Le moteur de notes hérité de XPilot reste la référence ERP : éditeur riche,
versions et sauvegarde. La disposition complète ajoute les notes personnelles
et enrichies empilées à gauche de l'assistant, sans créer un second référentiel.
Le catalogue sépare désormais « Type de source » et « Format » : PDF, PNG,
texte, Office et autres formats sont filtrés avant la pagination, dans les droits
du projet. Les contrôles visuels aux dimensions publiques suivent un registre
distinct ; les captures de structure seules ne valent pas conformité à ±2 px.

La première tentative de qualification hors ligne a observé le Wi-Fi déconnecté pendant
158 des 192 inventaires. Le contrôleur a refusé de démarrer les moteurs :
l'adaptateur virtuel F5 restait déclaré actif, sans adresse ni route dans
l'inventaire disponible. Le délai d'attente a expiré et aucun enfant n'a été
lancé. Cette coupure réelle ne qualifie donc pas encore les calculs hors ligne ;
le rapport brut est conservé dans le registre de recette.

Le nouvel essai coordonné termine avec succès le 11 octobre à 20:53 UTC :
transcription Whisper, index EG2 et génération Gemma sur quatre sources fictives,
avec coupure physique observée avant, pendant et après les calculs. Neuf
inventaires qualifiés, dont six pendant l'enfant, ont un écart maximal de 7,32 s ;
les processus possédés sont fermés. Le rapport reste distinct du premier échec :
`.ui-preview/pilots/offline-physical-runs/20261011-225003-77be78b1/qualification.json`.
Cette preuve ne mesure pas les appels réseau natifs et ne qualifie pas la qualité
ou la latence du direct industriel.

L'essai Jabra nouvellement autorisé avec une ouverture maximale de 45 s conserve
24,1 s PCM et ferme normalement le matériel après 26,53 s. Le seuil technique
de 2 ms a arrêté l'acquisition sur un écart d'horodatage ADC de 2,3058 ms ; une
perte physique d'échantillons n'est pas démontrée. Le quota de 30 s reste ouvert,
l'autorisation est consommée et aucun fichier ambiant n'est écouté ou transcrit.
Le harnais v2 passe ensuite 76 simulations et une revue indépendante. Sous une
nouvelle autorisation unique, l'essai du 11 octobre à 21:24 UTC conserve exactement
**30 s PCM/1 440 000 trames par canal**, en six fichiers, et ferme normalement
après **32,6905 s**. Le rapport de quota est réussi ; neuf écarts d'horodatage
restent diagnostiqués et la continuité physique reste inconnue. Des tests
frontend étaient déjà engagés pendant cet essai : aucune qualification de
latence ou de PC au repos n'en est tirée. Preuve distincte :
`logs/foresight-runtime/qualification/headset-jabra-v2-data30-max45-20261011-212458-84da2978/controller.json`.
Aucune écoute, transcription, capture système ou nouvelle ouverture après cet essai.

La régression complète précédente de l'interface passe **694 tests dans 75 fichiers**
en 244,67 s ; TypeScript et le build passent. Elle couvre le bouton Nouvelle
séance depuis Sources, les formats réels, les trois dispositions des notes et
les seuils de navigation. Le reçu est conservé dans
`logs/foresight-runtime/source-session-layout-followup-20261011-221310/qualification.json`.

Le complément Studio et Sources passe ensuite **716 tests dans 75 fichiers**,
avec TypeScript et compilation réussis. Les 132 tests ciblés sont inclus dans
ce total. Le reçu est dans
`logs/foresight-runtime/studio-compact-followup-20261011/qualification.json`.
La préparation du Studio se replie dans un panneau accessible ; les commandes
de capture et les états STT conservent leur propre visibilité. Les mesures
publiques et la recette de notes sur copie restent distinctes de ces tests.

La passe Python complète précédente termine avec **2 051 réussis, un ignoré,
aucun échec ni erreur**, en 1 737,79 s. Le nouveau checkpoint
`backups/foresight-preactivation-20261011-202403-076435` est restauré et vérifié.
Le contrôle `completion-runtime-qualification-v4.json` confirme les assets
finaux et les routes de formats sur 8001, avec les trois capacités de séance
toujours désactivées. La recette navigateur du build précédent DhlxCsWr passe 16 contrôles sur
données fictives : formats, préparation depuis Sources, note ERP et disposition
retrouvées après rechargement, défilement clavier et navigation. Elle ne qualifie
pas la fidélité exacte : à 850 × 479 les trois panneaux sont visibles mais
restent plus compacts que la référence ; la vue enrichie à deux panneaux reste
longue à 786 × 474. Ces écarts historiques sont conservés. Le complément
compact corrige depuis la hauteur disponible ; l'adaptation présentée sur
le build B0MSJycO a ensuite été validée par l'utilisateur, sans parité exacte
revendiquée. L12 reste ouvert sur ses autres recettes applicables.

Le complément de portée Drive réussit **61 tests Python Sources et 29 tests
React ciblés**, TypeScript et build conformes. Les suites complètes précédentes
de 716 React et 2 051 Python sont antérieures à ce complément ; les compteurs
ne s'additionnent pas. Drive est masqué dans Sources et son import est refusé
avant transformation des secrets ou appel réseau. Le bouton de liste du Studio
mesure désormais 44 px sur mobile. Le build `Yuj98_lc/BJ0BE6LI` passe douze
contrôles navigateur de structure, restauration des notes et clavier sur copie.
Une recette distincte passe neuf contrôles de citations tableur/audio/image dans
le navigateur et trois contrôles HTTP des liens originaux visibles
et vérifie les octets des trois liens originaux réellement proposés. L'image
entière reste un fichier cité, sans aperçu intégré ; l'audio est un silence
synthétique annoté manuellement, sans lecture ni transcription. Les reçus
datés figurent dans le registre. La nouvelle régression Python complète passe
**2 056 tests, 1 ignoré, zéro échec**, en 1 536,47 s dans
`logs/foresight-runtime/scope-python-final-20261011-v2/`, avec sources inchangées
pendant la passe. Le correctif ultérieur de minuterie du harnais audio est
soumis à des simulations séparées ; ce compteur ne lui est pas attribué.

Le checkpoint `backups/foresight-preactivation-20261011-223302-512328` conserve
1 361 fichiers de données et restaure les deux SQLite avec intégrité `ok`.
Après redémarrage, `completion-runtime-scope-20261011-v1.json` confirme sur 8001
la santé, les assets `Yuj98_lc/BJ0BE6LI` et Drive désactivé. Les trois flags séance,
proactif et enrichissement automatique restent faux. Le contrôle en lecture seule
`production-scope-preservation-20261011-v1.json` conserve les 18 tables métier
protégées et les 1 340 originaux ; les suivis historiques évoluent sans suppression.
Le correctif de qualification audio passe 169 simulations ciblées recouvrantes
et Ruff, avec revue exacte de 31 ressources. Aucun nouvel essai matériel n'a
été lancé dans ce passage ; la préparation attend un nouvel accord regroupé.

La recette batch fictive est préparée avec 43 simulations et une revue
indépendante favorable. Son premier lancement réel V2 s'arrête avant le moteur
STT : le contrôle d'arguments du harnais refuse la forme texte utilisée par
Windows. L'échec et la fermeture propre des processus sont conservés ; aucune
transcription ni qualité batch n'est qualifiée par cet essai.
La V3 corrige ce format et ferme proprement en 19,22 s, mais le lanceur Python
Windows et son interpréteur ont des PID différents : le contrôle d'attestation
refuse l'entrée produit avant l'IA. Cette limite du harnais est conservée en échec.
La V4 passe 85 contrôles, dont un lancement du VENV Windows réel sur des modules
factices, puis 22 critères de revue indépendante. Elle relie les deux PID par
un identifiant unique et les contrôles OS avant l'entrée du moteur. Son unique
exécution transcrit les 15 fichiers fictifs en 360,88 s et ferme normalement
tous ses processus. Les 27 contrôles métier propres passent ; deux attentes
sur huit sont perdues dans les cas dégradés, toutes deux dans les voix superposées.
Le parcours de relecture/versionnement passe sept vérifications, sans réparer
ces deux erreurs de fond. Le P95 de 24,86 s porte sur le batch complet avec
chargement et diarisation, pas sur l'affichage direct. La revue indépendante
confirme le résultat sur 22 critères ; aucune qualification industrielle,
matérielle ou longue n'en découle.
Le contrôle post-batch à 23:46 UTC confirme encore les 18 tables métier protégées
et les 1 340 originaux, sans séance/CR/action fictif en production. Depuis le
checkpoint, les suivis comportent 101 inputs ajoutés, sept scans et deux analyses
modifiés, sans suppression ; leur attribution aux workers reste une inférence.
Un complément sur copie SQLite neuve passe ensuite 16 contrôles : les deux
omissions de chevauchement sont corrigées par insertion automatisée de la
référence annotée, relues avant validation et conservées en versions 2/3.
Le brut et les fichiers V4 restent inchangés ; aucun audio n'est ouvert et
cette vérification ne constitue ni validation humaine ni amélioration STT.

## Interface épurée — 11 octobre 2026

Les grandes rubriques restent à gauche. Le projet choisi s’y déplie pour ouvrir
Vue d’ensemble, CDC & BE, Planning, Atelier, Réunions & revues, Documents et
Informations. La recherche reste dans l’en-tête ; les paramètres secondaires,
diagnostics et historiques s’ouvrent à la demande.

Mails : l’objet et une ligne expéditeur/date précèdent directement le corps du
message. « Détails du mail », fermé par défaut, donne accès aux coordonnées
complètes, à la réponse et à l’original. Le classement et les vignettes de projets
restent dans le petit panneau de droite ; sur petite fenêtre, ce panneau suit
le mail. Recherche et précédent/suivant partagent la barre Mails. Le suivi
d’analyse reste compact et ses détails peuvent se réduire pendant le traitement.

Planning présente Échéances et Tâches, avec modèles et comparaisons dans Outils.
Documents regroupe les documents à remettre, fichiers/dossiers et notes ; les
liens depuis les jalons et revues ouvrent le document concerné. Dans Mails, le
panneau projets contient « Classer et suivant » ; les raisons se déplient à la
demande. Les réglages courants sont séparés des options de connexion et de
maintenance. Les états actifs, erreurs, sources et validations restent accessibles.

Cette évolution concerne le frontend du serveur unique Agent **8001** ; les API,
modules métier et données sont conservés. Voir [organisation et vérification](docs/24_UI_UX_REDESIGN.md#épuration-du-11-octobre-2026).

Qualification UI de l'étape d'épuration, antérieure à la fusion : 512 tests React, puis 30 tests ciblés des derniers ajustements,
TypeScript, Ruff et build réussis. Navigation et options vérifiées dans le
navigateur sur 8001, avec le menu mobile à 320 pixels. Les deux bases répondent
`ok` ; à cette étape, transcription indisponible sur ce poste, signalée dans l’interface.
Suite Python : 1 795 réussites, 1 ignoré, seul échec préexistant du classement
`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`.

Dernière correction Mails : **519 tests React réussis**, TypeScript, build et
Ruff conformes. Lecture vérifiée sur 8001 à 670, 1915 et 320 pixels : contenu
visible immédiatement, détails repliables et lecteur avant les projets sur
petite fenêtre. Aucun classement ni lancement d’analyse en production pendant
la vérification ; backend inchangé. Voir [la qualification Mails](docs/24_UI_UX_REDESIGN.md#correction-mails-après-utilisation).

## Recherche unifiée EG2

La barre supérieure ouvre `/app/search` : recherche
par le sens dans les passages EG2, mots et références exacts dans les sources
classées, et recherche textuelle des connaissances retenues. Filtres par projet,
type et date, extraits, pagination et consultation de la source. Le moteur utilise
le même index EG2 et le serveur Agent **8001**. Une panne EG2 ou une couverture
incomplète est affichée ; les droits de projet et les décisions restent appliqués.
Voir [fonctionnement et limites](docs/20_EG2_ENGINE.md#recherche-unifiée).

Activation vérifiée sur 8001 le 11 octobre 2026 : recherche EG2 réelle, filtres et
consultation de source ; 897 sources indexées, classifications et données
préservées. Validation finale ciblée : 58 tests Python, 487 tests React, Ruff et
build conformes. Suite Python globale : 1 786 réussis, 1 ignoré, 1 échec
préexistant de classement des mails ; lancée avant les derniers ajustements,
ensuite couverts par les tests ciblés. Bilan :
`logs/search-activation-20261011-123128/qualification.json`.

## Livraison du 11 octobre 2026 — mémoire EG2

Le moteur unique est EmbeddingGemma 2 distant via LM Studio. Les sources classées
sont découpées puis indexées dans `storage/eg2/index.db` ; le LLM configuré
rédige les réponses depuis les passages retrouvés avec citations. Les faits,
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
La qualification globale compte 1 777 tests Python réussis, 1 ignoré et un échec
préexistant de classement mail. Les contrats EG2 finaux, Ruff et le build passent ;
481 tests React de la suite puis les 2 tests du formulaire mémoire passent.
Les comptes rendus datés ci-dessous décrivent les étapes historiques ;
[le contexte du projet](PROJECT_CONTEXT.md) et cette livraison décrivent l'état actuel.

## Secours IA local LM Studio

Agent conserve le serveur distant comme IA principale. En cas de connexion refusée,
délai réseau dépassé ou erreur HTTP 502/503/504, les appels texte, JSON, classement
et flux avant le premier fragment basculent sur le modèle local configuré. Le retour
au serveur principal est vérifié lors du prochain appel après 30 secondes.
Les erreurs de configuration, refus 401/403 et réponses invalides restent visibles.

Après une réponse utile du serveur principal, Agent décharge automatiquement
le modèle de secours dans LM Studio pour libérer la mémoire du PC. Il attend
la fin des générations locales en cours et conserve les autres modèles.
Le serveur LM Studio reste disponible pour une nouvelle panne réseau.
Voir [le fonctionnement et les tests](docs/22_OPERATIONAL_IMPROVEMENTS.md).

Décharge vérifiée réellement après une réponse du LLM réseau. Les 99 contrôles
liés passent après correction d'une isolation de test ; le bilan global et
sa reprise sont [consignés séparément](logs/llm-recovery-global-20261012-105917/final-verification.json).

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

**Analyse automatique des connaissances projet — 10 octobre 2026.** Un worker du
serveur unique `8001` complète le cockpit avec un bilan documentaire : dates de
jalons proposées, fonctions/contraintes/exigences évaluées, points importants et
preuves. Passage toutes les 48 h après le dernier bilan, un projet actif à la fois,
seulement après 30 secondes sans appel IA dans Agent. Reprise persistante entre
lots ; validations humaines et planning conservés. Voir
[analyse des connaissances](docs/35_PROJECT_KNOWLEDGE_ANALYSIS.md).

**Relance automatique du backend — 10 octobre 2026.** Les lanceurs Windows utilisent
un superviseur indépendant en arrière-plan pour le serveur unique sur `8001`.
Un arrêt du processus entraîne une relance après 5 secondes ; les échecs répétés
espacent les tentatives jusqu'à 60 secondes. Verrou système contre les doublons,
journaux dans `logs/runtime`, commandes de statut et d'arrêt explicite :
voir [exploitation](docs/22_OPERATIONAL_IMPROVEMENTS.md#supervision-du-backend).

**Classement automatique des mails.** Le seuil de confiance est configurable dans
les réglages (`mail.auto_classification_threshold`), 0,75 par défaut. Une suggestion
unique au-dessus du seuil peut être classée avec décision et audit ; les égalités,
les références contradictoires et les décisions humaines sont préservées.
Les candidats enregistrés derrière un ancien repli Divers peuvent être repris.
La règle initiale à 100 % du 7 octobre est un jalon historique remplacé par ce seuil.
Voir [classement des mails](docs/18_MAIL_TRIAGE.md).

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

Version applicative **0.4.0**, état documentaire revu le **7 octobre 2026**.
Inclut les corrections de l’audit du 30 septembre, le compagnon mémoire,
la nouvelle interface Mails et la liaison Thunderbird, puis les améliorations
de pilotage décrites dans [la livraison 0.4.0](docs/22_OPERATIONAL_IMPROVEMENTS.md).
Les Revues proposent aussi un [parcours réunion audio](docs/23_MEETING_AUDIO.md) :
transcription locale, texte horodaté par interlocuteur à relire, puis synthèse LLM
et compte rendu validé enregistré dans la même connaissance projet.
Inclut aussi la correction des références explicites et le classement multicritère appris des validations humaines.
Ce dépôt constitue un seul projet. Les modules Projets, CDC, CDC & BE, Revues,
Atelier et Import Sage hérités de MiniPilot sont conservés.

La reprise des fonctions projet d'XPilot a fait l'objet d'un
[audit local des 19 rubriques possibles](docs/27_XPILOT_PROJECT_AUDIT.md), avec
[un plan de livraison par lots](docs/28_XPILOT_PROJECT_PLAN.md). Le plan enrichit
les modules du serveur unique `:8001` ; XPilot `:8000` reste externe et inchangé.
L'[objectif de reprise est lancé](docs/29_XPILOT_EXECUTION.json) : le premier
lot fixe les [contrats et contrôles de migration](docs/29_XPILOT_FOUNDATION.md),
avant l'identité projet, l'équipe et le workflow. Le
[socle L1 d'identité et d'équipe](docs/30_XPILOT_PROJECT_IDENTITY.md) est activé
dans `C:\Agent` sur `8001`, après tests et recette navigateur. Les archives v3
de la fiche et de l'équipe sont qualifiées,
avec lecture des anciennes archives v2. Les contrôles HTTP et internes sont
actifs dans le mono-serveur. La fiche, l'équipe, l'historique et les référentiels
sont raccordés aux routes du mono-serveur, avec migration additive sauvegardée
au démarrage. Le sélecteur de l'assistant reprend les projets du portefeuille ;
une sélection explicite prépare leur liaison de connaissance si nécessaire.
Le [lot Livrables L3](docs/32_XPILOT_PROJECT_DELIVERABLES.md) est qualifié et
actif dans `C:\Agent` sur le serveur unique `8001`. Projets → Planning → Livrables
propose liste paginée, création, sélection depuis une publication exacte du
catalogue, fiche, checklist, visas humains, validation documentaire, versions
et historique. Réglages → Livrables gère les définitions et la composition des
typologies. Les jalons exposent leurs blocages nommés et ouvrent le contrôle
exact, en conservant les brouillons et en comparant les révisions concurrentes.
La date réelle reste indépendante du workflow ; aucune lecture ne crée de
catalogue, de sélection ou de visa. Les types standard sont des propositions.

Les publications de fichiers locaux, réseau et CDC conservent leurs octets,
empreintes et manifestes immuables. Une nouvelle publication retire les visas
sans perdre la préparation. Les archives sélectives v5 et la restauration globale
préservent versions, preuves et relations ; la restauration déplace les
emplacements de lecture sans réécrire les publications. Les fichiers réellement
sauvés par le navigateur et leurs manifestes sont vérifiés sur la recette fictive.

Le candidat fusionné passe **706 tests Python (un ignoré), 267 React**, Ruff,
TypeScript et build. La sauvegarde complète pré-L3 de **1 397 fichiers** a été
restaurée sur copie. La migration conserve les **2 098 lignes ERP / 17 429 cellules**
et **13 144 lignes Brain / 108 134 cellules** contrôlées. Les dix projets historiques,
les routes et le nouveau bundle sont vérifiés sur le serveur, puis dans le
navigateur. Sauvegarde :
`C:/Agent/logs/xpilot-l3-activation-20261006-190820/full-state-before-l3`.
Preuve : `.ui-preview/xpilot-l3/integration-1006-v2/delivery-result.json`.
Le menu latéral, la bulle de l'assistant, les heures et tous les modules hérités
sont conservés. **L4–L9 restent à intégrer**. Le [socle RLP du lot L4](docs/33_XPILOT_COCKPIT_REVIEWS.md)
est préparé et qualifié sur bases fictives : révisions figées, PDF et propositions
audio sourcées à vérifier. Le cockpit est maintenant qualifié dans le worktree :
jalons reliés aux tâches/livrables, recherche, couches, inspection, dates et
commandes de planification communes. Les compteurs couvrent toutes les données,
avec listes paginées et conservation des brouillons. La préparation passe
752 tests Python et 277 React ; la recette utilise un projet fictif de 5 000 tâches
et 2 500 livrables. L'interface RLP est préparée dans Réunions & revues : brouillon
structuré, participants/jalon/livrables, citations par interlocuteur, comparaison
des modifications concurrentes, publication figée, PDF vérifié et historique.
Les comptes rendus et l'audio restent dans « Réunions et audio ». La qualification
UI passe 292 tests React et les 31 tests RLP ciblés passent aussi. Le transport
sélectif v6 est qualifié dans le worktree ; les liens restaurés dans l'interface,
la recette finale et l'activation restent en cours. Ces routes ne sont pas
encore disponibles sur 8001. Preuve : `.ui-preview/xpilot-l4/rlp-ui-evidence.json`.

L0 à L3 sont livrés. Le [planning L2](docs/31_XPILOT_PROJECT_PLANNING.md)
est actif sur le serveur unique `8001` : jalons à trois dates, tâches avec parents,
responsables et heures, modèles versionnés, aperçu/application explicite,
références figées et historique. Les révisions sont partagées avec les éditions
historiques, propositions IA et conversions d’actions de réunion. Les jalons
existants gardent leurs données et leur ordre métier ; publier un modèle ne
modifie aucun projet. Les archives v4 préservent planning, preuves et relations,
avec compatibilité v2/v3. Les références v2 capturent dates et budget d’heures du
projet ; les captures v1 restent lisibles sans reconstitution. L’interface est
qualifiée à 390, 650 et 1280 pixels. Migration et restauration sont vérifiées sur
copies puis à l’activation : 14 033 lignes / 116 204 cellules métier conservées,
1 388 fichiers de sauvegarde contrôlés. Qualification : 459 tests Python / 1
ignoré, 155 tests React, Ruff, TypeScript et build conformes. L3 poursuit les
livrables et versions ; les fonctions financières restent exclues.

Chaque projet dispose d'un [tableau de jalons](docs/26_PROJECT_MILESTONES.md) avec
dates **contractuelle, prévisionnelle et réelle**, écarts et historique. L'agent
recherche des dates dans les mails classés, pièces jointes lisibles, CDC, comptes
rendus, transcriptions et documents des liens réseau du projet. Ses propositions
citent leur source et attendent validation ; un report ne remplace pas
automatiquement une date contractuelle. Le worker et son suivi restent dans
le serveur unique `:8001`, avec recherche périodique et lancement manuel.

Dans **Réglages → Mails**, la source se choisit entre **Thunderbird** et
**Dossier de fichiers EML**. La liaison Thunderbird 0.2.0 expose les comptes et
dossiers, avec recherche, sélection multiple et progression des transferts.
La synchronisation automatique et son intervalle sont pilotés par Agent ;
une synchronisation manuelle reste possible lorsqu’elle est désactivée.
Thunderbird doit être ouvert ; le chemin EML et les mails existants sont conservés.
Voir [la liaison locale](docs/21_THUNDERBIRD_BRIDGE.md).

Le menu de gauche affiche en permanence l’activité des mails : synchronisation,
analyse IA et indexation mémoire, avec progression quand le moteur fournit un
compteur, témoin animé pendant un traitement réel et journal des quatre derniers
changements observés. Les attentes, coupures et erreurs sont visibles séparément.

À la création depuis un dossier affaire, le code et le titre de son nom sont
prioritaires : `AIRB26LTH0205-A - LED 2026` donne `AIRB26LTH0205-A` et `LED 2026`.
Un TDAO/TDSP d’une autre affaire est signalé ; son identité et ses heures ne
sont pas importées automatiquement.

La [refonte UI/UX](docs/24_UI_UX_REDESIGN.md) remplace le bureau à dock par un
menu nommé : Accueil, Projets, Mails, Réunions, Connaissance et Traitements.
Imports et Réglages restent accessibles en bas du menu. Les liens `/app/*`,
le retour navigateur, les favoris, les thèmes clair/sombre et la densité sont
intégrés au même serveur. Les panneaux métier et toutes les données sont conservés.
La liste Projets conserve la recherche et les filtres ; les archives JSON sont
dans Imports & connexions. Les dossiers affichent les quatre premiers chiffres
du numéro de projet, zéro initial compris (0806 pour AIRB25LTH0806-A).
Le réglage mémoire présente le moteur EG2, son index local et son serveur distant.
Après création manuelle ou import d’un dossier, le portefeuille est rechargé
avant le retour à Projets et les filtres susceptibles de masquer le nouveau
projet sont levés. La liste ouverte se rafraîchit aussi automatiquement.
La molette conserve le défilement des listes et passe à la page à leurs limites.
L’[étude vocale](docs/25_REALTIME_VOICE.md) distingue conversation et réunion ;
la voie cloud payante est écartée. Le direct local reste une évolution à réaliser.

Validation : 1698 tests Python réussis / 1 ignoré, 458 React, Ruff, TypeScript et build conformes. Recette navigateur sur données fictives puis contrôle de la version active sans erreur console. Après sauvegarde, 207 suggestions existantes à 100 % classées ; 109 sources déjà traitées, toutes les décisions antérieures et le contenu des mails conservés. Aucun commit/push. Preuve : `.ui-preview/mail-auto100/delivery.json`.

## Architecture en service

L’assistant mémoire s’ouvre depuis l’en-tête dans un panneau facultatif,
redimensionnable de 300 à 520 px en attrapant la petite poignée sur son bord gauche
(également utilisable au clavier). Il interroge un projet ou tous les projets, puis
synthétise les extraits avec l’IA configurée. Les badges distinguent les
informations validées [V] des sources non validées [P]. Voir
`docs/20_EG2_ENGINE.md` pour le rôle des embeddings et les réglages.

Les réponses affichent titres, listes et texte en gras ; les références
numérotées ouvrent les extraits sources. La saisie multiligne, la copie et
les diagnostics mémoire repliables sont intégrés au panneau. Les réponses sont
diffusées progressivement par le LLM configuré ; arrêt et erreurs partielles
sont explicites. Les discussions sont conservées dans Brain avec contrôle de
révision et historique conversationnel borné. Les brouillons restent présents
lors de la navigation dans la session ; un microphone actif est signalé globalement.

La zone de saisie du compagnon dispose de styles dédiés : elle occupe toute
la largeur disponible à côté du bouton d’envoi et reste compacte lorsqu’elle
est vide.

Un processus FastAPI lié à `127.0.0.1:8001` sert React et les API.
L’application Mails propose une boîte à trois panneaux : dossiers et vignettes
projets, cartes de messages avec aperçu, et lecture intégrale avec validation IA,
reclassement et pièces jointes. Le glisser-déposer accepte plusieurs mails.
Les références explicites dans l’objet ou le corps sont proposées dès l’import,
y compris après un préfixe de commande `PO-…-`. Les références alternatives
déclarées dans les alias ont la même priorité que le code principal.
Le classement croise aussi expéditeur, destinataires, fil de discussion, thèmes
et noms des pièces jointes. Les profils sont recalculés depuis les mails classés
par l’humain et les connaissances validées : chaque validation/reclassement
affine les prochaines suggestions. « Pourquoi ce projet ? » présente les indices
retenus et les alternatives ; les cas trop proches restent à décider.

Un classement confirmé retire immédiatement le mail de « À classer » et met
à jour les compteurs ; les échecs restent sélectionnés. Les projets nouvellement
créés apparaissent aussi dans les destinations du lecteur déjà ouvert.
Le premier classement vers un projet ERP crée ou réutilise son lien de connaissance.
Le sélecteur du lecteur propose « Créer un projet… » : code facultatif, nom
obligatoire, destination sélectionnée après création, puis affectation explicite.
Le classement humain est enregistré sans attendre l’extraction IA ni l’indexation
mémoire. Ces étapes continuent dans une file persistante du même serveur ; leur
état et la reprise d’un échec sont accessibles dans Traitements. Le mail reste
lisible dans son projet pendant l’enrichissement.
La destination **Écarter** purge les spams et mails sans intérêt après sauvegarde,
et conserve une empreinte empêchant leur réimportation et leur réanalyse.
La liaison locale Thunderbird importe les dossiers choisis et prépare des
brouillons/réponses avec pièces jointes via une extension installable en XPI.
Elle réutilise le serveur :8001 et le compte déjà configuré dans Thunderbird.
Voir [le connecteur Thunderbird](docs/21_THUNDERBIRD_BRIDGE.md).
Le pont ERP → Brain appelle les gestionnaires dans ce processus ; il ne dépend
pas d’un deuxième serveur. Le port 8000 appartient à XPilot ; 8002 est retiré.

| Route | Usage |
|---|---|
| `/`, `/app/*` | Espace React et liens directs des rubriques/projets |
| `/api/v1/workspace/*` | Vues globales paginées, triage durable, discussions |
| `/v1/projects/chat/stream` | Assistant progressif SSE avec citations |
| `/ui`, `/ui/pending`, `/ui/proposals`, `/ui/settings` | Validation et réglages Brain |
| `/v1/*` | Connaissance, sources, décisions, mémoire |
| `/api/v1/*` | ERP, CDC, BE, Atelier, Sage et pont Brain |
| `/health` | Vérification des deux bases ; HTTP 503 si dégradé |
| `/api/v1/session` | Jeton local nécessaire pour les écritures |

Deux bases SQLite sont conservées : `project_brain.db` pour la connaissance,
`MINIPILOT_HOME/minipilot.db` pour l’ERP. Une liaison explicite `BrainLink`
associe leurs projets. Les fichiers originaux restent dans leurs stockages.

## Démarrage Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements.txt
start-agent.cmd
```

Profil vérifié : Python 3.13 sous Windows. Le frontend compilé est inclus.
Pour le reconstruire : Node 24, pnpm 11.18.0, puis dans `web` :
`pnpm install --frozen-lockfile`, puis `npm test` et `npm run build`
(commandes de vérification effectivement exécutées sur le poste).

## Garanties mises en œuvre

- Une suggestion de classement reste à valider ; l’IA ne rattache pas un mail.
  Un projet explicitement choisi à l’import constitue une décision humaine.
- Un reclassement conserve l’historique, invalide les anciennes connaissances
  issues de la source et remet les dérivations en revue.
- La connaissance validée est canonique dans SQLite, avec versions et provenance.
  Une panne mémoire conserve cette décision et une projection à reprendre.
- Un transfert BE final exclut les éléments rejetés/remplacés et
  bloque les éléments non confirmés ou les contrôles bloquants. Un brouillon
  explicite reste disponible et porte la mention BROUILLON.
- Les clés API sont masquées et chiffrées par DPAPI sous le compte Windows.
  Une saisie vide conserve la clé ; son effacement est explicite.
- Les sauvegardes globales vérifient les empreintes et restaurent dans un dossier neuf.

## Pilotage technique 0.4.0

Le tableau de bord regroupe les échéances, revues CDC, points ouverts et analyses
à reprendre. Les heures prévues, consommées (Sage et saisie manuelle) et le reste
à faire réestimable remplacent les indicateurs financiers. Le code de calcul
des taux, marges, prix et offres est retiré sur demande ; toutes les données
historiques, colonnes SQLite et archives sont conservées. Atelier et Sage restent
disponibles pour le suivi technique.

Les analyses CDC utilisent une file SQLite durable : fermer la fenêtre ne les
arrête pas ; la reprise repart du dernier lot enregistré. Les transferts BE sont
versionnés avec leur photographie technique et leur empreinte. La recherche et
le tri des mails sont effectués côté serveur sur tout le dossier avant pagination.
Les réglages présentent l’état des sauvegardes et l’espace disque.
Dans Mails, les analyses affichent « mails traités / total à traiter » et une
barre de progression, conservées après interruption ou erreur.

## État et limites

La recherche EG2, la réindexation des sources classées et une réponse réelle du
LLM avec citations ont été vérifiées. Les essais fictifs conservent des cas de
rappel incomplet ; la pertinence et la complétude restent à contrôler sur chaque
usage métier. Les mesures, résultats et limites sont dans
[le moteur EG2](docs/20_EG2_ENGINE.md) et
[la qualification](docs/36_EMBEDDING_CHANNEL.md).

La liaison Thunderbird 0.1.0 est installée et vérifiée sur Thunderbird 157.0.1 :
connexion réelle, import de mails et création d’un brouillon avec pièce jointe.
L’envoi final reste dans Thunderbird. Voir `docs/21_THUNDERBIRD_BRIDGE.md`.
L’extension Infomaniak source 0.2.0 possède des tests de helpers et un paquet
reproductible non signé ; son fonctionnement avec un compte réel et Firefox reste
à qualifier. Le XPI historique 0.1.1 ne contient pas les corrections 0.2.0.
La transcription automatique, l’OCR, l’ingestion CAO, le serveur MCP, les events
et l’intégration XPilot2 complète ne sont pas attestés opérationnels par cette
livraison ; leur implémentation et leur qualification se vérifient séparément.
La protection locale ne constitue pas une authentification multi-utilisateur.

## Références

- [Contexte et état du projet](PROJECT_CONTEXT.md)
- [Usage, paramètres, sauvegarde et tests](README_BACKEND.md)
- [Corrections F01–F29 et preuves](docs/19_AUDIT_REMEDIATION.md)
- [Vision](docs/00_VISION_SCOPE.md), [moteur CDC](docs/17_CDC_ENGINE.md),
  [tri des mails](docs/18_MAIL_TRIAGE.md), [décisions d’architecture](docs/adr/)
- [Inventaire des dépendances et provenance](THIRD_PARTY_NOTICES.md)
- `ruff.toml` fixe les contrôles Python utilisés localement et dans la CI.
- `manifest.json` : documents et services actuels. `AGENTS.md` : gouvernance.

## Interface et copie de lancement

Le 5 octobre 2026, la refonte claire avec menu latéral a été réunie dans
`C:\Agent` avec les corrections de références et le classement multicritère
des mails. Le serveur unique sur 8001 doit être lancé depuis ce dossier ;
les worktrees servent à préparer les évolutions, puis leurs changements sont
fusionnés et testés avant activation. Le build React est issu des sources
réunies. Les bases Brain et ERP ainsi que les fichiers importés sont conservés.

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

Qualification consolidée RLP/UI : **754 Python / un ignoré, 292 React, Ruff, TypeScript et build**. Les 31 tests RLP sont requalifiés après la dernière validation de synthèse JSON. Preuve : `.ui-preview/xpilot-l4/rlp-result.json`. L4 n’est pas activé ; archive/restauration et qualification globale restent à réaliser.

L4.4 prépare maintenant le contrat de restauration des revues : publications et
PDF conservés à l'identique, correspondances ERP/Brain séparées, liens et
transcriptions historiques contrôlés. La migration additive est qualifiée sur
une copie du corpus de recette ; le transport sélectif reste à raccorder.
Le serveur Agent unique sur 8001 reste sur L3. Voir
[Cockpit et revues](docs/33_XPILOT_COCKPIT_REVIEWS.md).

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

## Icône du navigateur

L’onglet Agent utilise le symbole blanc sur fond vert de l’interface. Le favicon SVG est servi par le serveur unique 8001 sous `/assets/agent-favicon.svg`.

## Probabilité d’écartement des mails

La liste de tri présente une probabilité estimée à partir des mails similaires déjà écartés, pondérée par les mails similaires conservés. Elle reste indicative et exige une décision manuelle. L’apprentissage conserve uniquement des empreintes de comparaison, sans réindexer le contenu purgé.

## Tri des mails centré sur le message

L’onglet Mails affiche un seul message avec navigation précédent/suivant. Les projets proposés occupent un petit panneau à droite ; le texte est limité à 78 caractères typographiques environ. Le meilleur candidat disponible est présélectionné, les scores disponibles sont visibles et une seule action valide la destination.

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

Le bouton « Tester » des réglages IA actualise immédiatement le témoin LLM, en succès comme en échec. Le résultat manuel est prioritaire pendant 90 secondes pour les réglages testés, même si un ancien contrôle finit ensuite ; un changement de configuration le rend inapplicable. Le test OpenAI compatible confirme une réponse non vide ; le test Ollama confirme la joignabilité du serveur. Les témoins Embedding et Mémoire restent indépendants. Le bouton est désactivé pendant le test. Qualification : 32 tests Python ciblés, 478 tests React, Ruff et build conformes ; clic réel vérifié sur Agent puis retour à l’accueil avec le résultat manuel dans le témoin. La suite Python globale n’a pas été relancée pour cette correction.

## Seuil de classement automatique des mails

Réglages → Mails : seuil modifiable entre 1 et 100 %, 75 % par défaut. Le champ API `mail.auto_classification_threshold` utilise une fraction (0.75 = 75 %) et passe par PUT /v1/settings/mail ou PUT /api/v1/brain/mail-settings. Dès la prochaine analyse/import, une suggestion de projet réel avec confiance supérieure ou égale au seuil est classée automatiquement ; les suggestions inférieures restent à valider. Les choix humains, les mails écartés, Divers et les propositions contradictoires sont préservés. L’audit enregistre le score et le seuil utilisés ; les anciennes traces à 100 % restent intactes. Le classement conserve l’enrichissement différé. Les modifications partielles d’autres paramètres conservent le seuil enregistré. Le script `python -m scripts.auto_classify_mail` consulte les suggestions existantes ; `--apply` les classe selon ce même seuil après sauvegarde SQLite. Changer le réglage seul ne relance pas l’analyse des mails déjà analysés. Tests : test_mail_threshold.py, test_mail_auto100.py (seuil 100 % explicite), MailSettingsForm.test.tsx.

## Reprise globale de la mémoire (2026-10-07)

Reprise mémoire depuis un projet : dans **Connaissance**, **Reprendre les projections** affiche immédiatement une attente et bloque les doubles clics. Le bilan indique les projections indexées, en échec et obsolètes purgées, puis actualise les compteurs sans effacer le bilan. La reprise reste limitée à 100 projections du projet par requête ; un HTTP 200 peut contenir des échecs d’indexation. Une erreur réseau est affichée comme une reprise non confirmée et ne modifie pas les classements.

## Apparence des mails

La page Mails suit le thème Clair/Sombre choisi dans Réglages → Apparence, y compris les dossiers, les commandes et la zone de lecture. L'interface compilée reste servie par le serveur unique Agent sur 8001.

Le mail est présenté à gauche, les vignettes projets à droite ; sous 540 px de
largeur disponible, le mail précède les projets. Le corps commence juste après
l’objet et une ligne expéditeur/date. Les coordonnées complètes, la réponse et
l’original sont dans « Détails du mail », fermé par défaut. Le sélecteur de projet,
toujours visible, précède la destination et « Classer et suivant » dans le panneau
projets ; les autres vignettes et les explications restent repliables.
Les dossiers restent accessibles dans Options.

Les correspondants personnels `@excent.fr` (expéditeur, À, Copie) des mails classés dans une affaire active sont ajoutés à son équipe comme collaborateurs. Les rôles et archivages existants sont préservés ; l’équipe fournit ensuite un indice explicable de classement.

## Fiabilité des reprises mails — 7 octobre 2026

Une absence de réponse IA exploitable dans la file durable est maintenant un échec à l’étape `extraction`, repris explicitement ; elle ne devient plus une extraction heuristique annoncée comme terminée. Les autres résolutions de classement conservent leur repli heuristique existant.

Classement automatique des mails : un indice IA de contenu peut départager les projets même si l’expéditeur intervient sur plusieurs affaires. Les anciens replis Divers sont repris depuis leurs candidats enregistrés, au seuil configuré, sans nouvel appel LLM. Les égalités et références contradictoires restent à valider. Validation : 45 tests ciblés de tri et résolution.

## Reprise automatique de la mémoire — 8 octobre 2026

Agent reprend au démarrage puis en arrière-plan les projections en attente et en échec, par lots de 20. Les tentatives en échec sont datées en base et espacées d’au moins 60 secondes ; le délai du worker augmente jusqu’à une heure si un lot échoue, puis revient à 10 secondes après un lot réussi. La reprise manuelle reste disponible et les classements validés sont conservés. Aucun service supplémentaire : le worker appartient au serveur unique sur 8001.

## Informations de projet retenues par défaut — 8 octobre 2026

Les informations extraites d’une source résolue et rattachée au même projet deviennent immédiatement utilisables dans la connaissance et l’assistant. Le statut canonique reste `validated`, avec `validated_by=auto-default` et `validation_mode=default` exposé par les API : il exprime une information retenue comme vraie, sans prétendre à une confirmation humaine. La source, la provenance et une décision auditée restent conservées.

Dans **Connaissance**, la vue **Informations retenues** est ouverte par défaut. **Déclasser** retire une information de la vérité active sans supprimer sa source ; **Déclassées** permet de consulter l’historique et de **Rétablir** l’information. Le parcours existe également dans la rubrique Connaissance de chaque projet. Les anciens refus et reports sont préservés. Les propositions `project_attach` et les sources non résolues gardent leur parcours de rattachement. Une réextraction ne réactive pas automatiquement une information déclassée identique. Une contradiction ne remplace jamais silencieusement une confirmation humaine : les valeurs restent traçables et peuvent être déclassées individuellement.

Commandes : `POST /v1/projects/{pid}/knowledge/{kid}/invalidate` ou `/restore`, avec le corps `{"actor":"validator","comment":"motif facultatif"}`. Le relais ERP est `/api/v1/projects/{erp_pid}/brain/knowledge/{kid}/{action}`. La lecture accepte `status=validated|invalidated|all`. Les contrôles d’opérateur et de portée projet s’appliquent ; restaurer une information dont aucune source ne relève encore du projet renvoie 409. L’assistant exclut les vérités déclassées et les extraits de preuve contenant leur valeur exacte ; une paraphrase sémantique différente reste une limite de ce filtrage.

Vérification : tests de provenance, audit, absence de travaux LLM supplémentaires, refus/report, rattachement, contradictions, déclassement/restauration, source déplacée et filtrage de contexte dans `tests/test_knowledge_defaults.py`. Tests d’interface dans `WorkspaceViews.test.tsx`. Sauvegardes avant activation et rapports dans `logs/knowledge-defaults-20261008/`.

Activation vérifiée sur 8001 : sauvegarde Brain/ERP, 2 275 propositions informatives reprises et 2 249 connaissances distinctes ; 1 387 sources et 11 projets préservés, 1 879 propositions déjà traitées inchangées. Trois propositions informatives de sources non résolues restent à examiner. Le projet permet la pagination par 50 informations ; la recherche mémoire classe tous les résultats pertinents avant de limiter le rappel à 50. Les citations de vérité donnent une source résolue consultable lorsqu’une provenance existe. Réponse LLM utile vérifiée avec références sur une information retenue par défaut. Tests ciblés : 122 premiers tests puis 82 tests mémoire/accès/relais, 53 tests finaux du rappel avec provenance ; interface finale : 475 tests réussis, build réussi. Derniers contrôles de contexte : 21 tests réussis ; interface ciblée assistant/connaissance : 19 tests réussis. Suite Python globale terminée : 1 750 tests réussis, 1 ignoré, 1 échec préexistant (`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`), identique au contrôle précédant cette évolution. Le contrôle global a été lancé avant les derniers ajustements du rappel, de la pagination et du contexte ; ces chemins finaux sont couverts par les tests ciblés et les contrôles API/interface sur 8001. Bilan : `logs/knowledge-defaults-20261008/qualification.json`.

Le secours vérifie les instances réellement chargées via LM Studio `/api/v1/models`
(`loaded_instances`), et non la simple liste des modèles téléchargés. Un modèle
téléchargé mais absent de la mémoire est explicitement chargé avec `lms load`,
identifiant configuré et contexte de 8192 tokens, avant le premier appel de secours.

## Prise de notes et vocal — 12 octobre 2026

L'éditeur reprend la disposition de XPilot : page large, titre et sauvegarde
en tête, barre de mise en forme compacte. Notes enrichies, transcription et
assistant s'ouvrent depuis les outils de séance. Une note personnelle peut
enregistrer ou importer du vocal sans rattachement préalable à un projet.
La capture Windows propose explicitement le son du PC, le microphone en
salle ou les deux. Le microphone s'ouvre uniquement au démarrage demandé.
L'amélioration manuelle sauvegarde d'abord le brouillon courant ; les
propositions conservent leur validation humaine. Un moteur occupé provoque
une attente avec reprise bornée, sans rejouer une génération déjà commencée.
Voir [le parcours audio](docs/23_MEETING_AUDIO.md).


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

Les accès Windows des trois sauvegardes préparatoires conservées dans
`C:\Agent\.ui-preview\backups` sont maintenant restreints aux identités
conservées. Les 43 fichiers et les propriétaires des 66 éléments sont inchangés.
Cette protection, limitée à ce dossier, est distincte des recettes audio/ASR
du lot 12, qui restent ouvertes. Voir le [reçu et sa portée](docs/38_FORESIGHT_DELIVERY.md#protection-des-sauvegardes-préparatoires--13-octobre-2026).


### T12 : choix réseau et premier lancement V6 — 13 octobre 2026

L’utilisateur a choisi la recette fictive T12 de 60 minutes avec le primaire réseau
`google/gemma-4-26b-a4b-qat` sur `http://192.9.110.115:1234`, en conservant quinze
cas, trente-cinq faits et les trois fenêtres de charge prévues. Le premier
[lancement V6](logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-075610-78025914/controller-final.json) s’arrête à l’attente d’affichage du panneau
Transcription, avant admission du modèle et démarrage du driver ; la fixture
se ferme correctement. Aucune heure de recette n’est accomplie.

L’[observation séparée du retour réseau](logs/foresight-runtime/network-recovery-live-20261013-42465a494ce140b9902f7ab10695302b.json) confirme le modèle
primaire annoncé au catalogue et zéro instance du Gemma de secours local. Elle
n’effectue aucune génération. **T12/P95, qualité ASR et L12 restent ouverts** ;
la préparation et la disponibilité du catalogue ne valent pas qualification.


### T12 : séance réseau d’une heure — 13 octobre 2026

La séance fictive a réellement parcouru **60 minutes, de 10 h 36 à 11 h 36
(Paris)**, avec 1440 fragments acquittés et conservés, puis arrêt propre du Job
et des processus. Les trois questions ont reçu une réponse du primaire réseau ;
les six annulations attestent la sortie des consommateurs locaux. Les trois
enrichissements ont été rejetés (502) et les trois demandes proactives ont
atteint leur attente bornée de deux secondes. La transcription n’est pas
qualifiée : 99 fragments terminés, 1341 conservés sans transcription terminée.
Le profil CPU observé ne soutient pas encore les deux pistes en direct. Le P95
a zéro occurrence mesurée sur 1224 ; **T12 et L12 restent ouverts**.

Deux WAV d’une heure ont été [assemblés et vérifiés après la recette](logs/foresight-runtime/t12-post-recipe-consolidation-20261013-7af6eacb.json),
dans un dossier distinct ; cette dérivation n’a pas eu lieu pendant l’heure.
L’[observateur après séance](logs/foresight-runtime/network-recovery-live-20261013-c5a92111952943a3a3e5f53e43b3117d.json) voit le primaire au catalogue et zéro
instance du Gemma local, sans effectuer de génération. La génération réelle
provient des questions de la séance. [Résultats et limites](logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-083158-7af6eacb/root-actual-result-summary.json)
et [audit indépendant](logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-083158-7af6eacb/independent-terminal-partial-audit-v6.json).


### Enrichissements : diagnostic et candidat structuré — 13 octobre 2026

Un diagnostic distinct de la séance d’une heure a reçu 14 ajouts, refusés par
le validateur. Un nouveau pilote sur le même contexte fictif a envoyé une seule
requête structurée au primaire réseau : HTTP 200, 12 ajouts et citations exactes
validés. Ce résultat contrôle le format ; des erreurs ASR (« 16 MHz », « 2250 W »)
restent citées et ne deviennent pas des faits fiables. Il n’explique pas les trois
502 historiques de l’heure et ne qualifie ni T12 ni L12.

Le correctif est encore un candidat isolé, non activé. Il borne la réponse à
12 ajouts, conserve les blocs humains et affiche une réponse vide comme absence
d’ajout utile. Voir le [pilote réel](.ui-preview/pilots/t12-structured-additions-probe-20261013/result.json)
et la [portée de livraison](docs/38_FORESIGHT_DELIVERY.md#enrichissements--diagnostic-et-candidat-structuré--13-octobre-2026).

### Qualification logicielle du candidat V2 — 13 octobre 2026

Le candidat isolé réunit les enrichissements structurés et l'affichage explicite
« Aucun ajout utile à proposer pour cette note », sans bouton d'acceptation.
Le Studio explique aussi la suspension du direct et les passages conservés en
attente, selon l'état réel de la séance ; ces textes ne relancent ni capture
ni transcription. Agent reste une application sur le port 8001.

La qualification ROOT passe sur 887 tests frontend (83 fichiers), TypeScript,
la compilation et Ruff. Le JavaScript construit est `index-6orOloRS.js` ; le CSS
reste identique. La copie Python courte de 2444 cas est encore en cours, sans
résultat global revendiqué. La première tentative a conservé 435 réussites et
un échec sur un chemin Windows de 287 caractères. [Reçu logiciel ROOT](.ui-preview/pilots/t12-enhancement-schema-candidate-v2-20261013/qa-root-observed-20261013.json).

Une [revalidation locale](logs/foresight-runtime/t12-structured-response-v2-offline-revalidation-20261013.json)
des douze ajouts du pilote antérieur passe avec les helpers V2, sans nouvel
appel réseau ni SQL. Elle porte sur le format, avec les erreurs ASR conservées.
Le code candidat n'est pas activé ; T12 et L12 restent ouverts.
### QA Python : deux essais conservés, continuation préparée — 13 octobre 2026

Le candidat notes/Studio reste non activé. Les 887 tests frontend, les 37 unités
fictives, Ruff, TypeScript et le build restent validés dans leurs portées.
L'essai Python V1 conserve 435 réussites nommées et un échec de chemin Windows.
L'essai V2 s'est arrêté après environ 33 minutes sur la réserve disque (exit 92),
sans JUnit final ni nombre de cas terminés prouvé ; aucun passage global n'est
revendiqué. Une continuation de 2009 cas est seulement préparée, avec les 435
cas nommés antérieurs et une agrégation à vérifier après exécution.
[État V2 observé](logs/foresight-runtime/notes-ai-python-v2-disk-stop-root-observed-20261013.json)
; [préparation de continuation](.ui-preview/q/nac3/preparation-v1.json).

La compression d'une ancienne QA fictive fermée conserve les empreintes des
8602 fichiers et ne supprime rien ; seule la variation mesurée de 6,53 à
9,47 Go est liée à cette opération. La perte précédente de 4,2 Go reste
inexpliquée. Le pilote de douze ajouts reste une preuve de format avec erreurs
ASR citées. La recette d'une heure et ses limites restent intactes ; T12/L12,
ASR/P95 et activation restent ouverts.
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

### Assistant de réunion : transcription relue prise en compte

La transcription complète relue alimente désormais les questions de séance,
avec citations et position audio. Une correction rend les anciennes réponses
obsolètes immédiatement ; le texte provisoire reste conservé comme historique.
Correction activée sur le serveur unique Agent 8001 après sauvegarde vérifiée.
Voir [le suivi de recette](docs/40_FORESIGHT_ACCEPTANCE.md).

### Navigation de réunion simplifiée

Les onglets Transcription et Synthèse ouvrent directement la relecture complète
et le CR. Le direct provisoire est conservé dans un historique dépliable.
Les brouillons sont protégés lors des changements d'onglet et de la validation
de transcription ; un CR périmé ne peut pas être publié. Interface compilée et
activée sur Agent 8001. Voir le suivi de recette du domaine 40.

### Qualification des séances et des notes

L01 (identités, staging, attribution et rejeu) et L04 (notes, historique, outbox
et projection) sont qualifiés selon leurs critères complets. Une panne prolongée
de Brain n'abandonne plus la projection après 20 échecs : reprise avec délai progressif,
y compris pour les anciens événements exhausted. Sauvegardes et intégrité vérifiées
avant activation. La recette matérielle et L12 restent ouverts.
Voir [la qualification détaillée](docs/41_FORESIGHT_L01_L04_QUALIFICATION.md).

### Compte rendu de réunion : export PDF

L’export PDF du CR est disponible depuis le projet et la liste globale des réunions,
avec indicateur de préparation. Le parcours publication → action → tâche explicite
et les exports sont qualifiés pour L10. Le CR publié, les sources et les anciens
exports sont conservés. Voir [la qualification L10](docs/42_FORESIGHT_L10_QUALIFICATION.md).
L12 reste ouvert.

### Références publiques et bibliothèque qualifiées

L00 et L08 sont clos : références UI-01…09 et fonctions F01…25 explicites,
imports choisis, versions, labels et contexte calendrier vérifiés. Un import
public réel est conservé puis relu localement sur base privée. L’interface distingue
« Texte extrait » et « Indexée ». Drive reste désactivé. Voir domaine43 ; L12 reste ouvert.

### Assistant et enrichissements qualifiés

L05 et L07 sont clos : scopes et citations contrôlés, notes humaines protégées,
priorité des questions et propositions soumises à acceptation. Un écho de question
sur des pistes audio qui se recouvrent ne déclenche plus deux générations ; une
question ultérieure ou une autre valeur reste distincte. Serveur réseau disponible,
aucun génératif local chargé lors du contrôle. Voir domaine44 ; L12 reste ouvert.

La comparaison des échos conserve aussi les séparateurs de références et de valeurs : AIRB…-A diffère de AIRB…/A, et1,5 de1/5. Sept cas ciblés passent sur la version activée ; voir domaine44.

### PDF scannés — 16 octobre 2026

L’index multimodal prépare désormais chaque page PDF comme image avec sa page physique,
en conservant aussi le texte natif. Les nouveaux scans sans texte sont signalés comme
texte à reconnaître. Cette recherche visuelle n’est pas de l’OCR. Correction activée
sur le serveur unique8001 ; détail et limites dans docs/45_FORESIGHT_PDF_PAGES.md.

### Images et audio avec le LLM réseau — 16 octobre 2026

La préparation multimodale locale et les recherches explicitement choisies Images/Audio
fonctionnent aussi en mode réseau. Le mode et le modèle de génération ne sont pas modifiés.
Dans Réglages > Mémoire > Recherche locale dans les images et l’audio, choisir le projet
et « Vérifier et compléter ce projet » ; dans Sources, choisir ensuite Images ou Audio.
La recherche générale/texte conserve EG2 réseau. Les démarrages réseau n’activent pas
automatiquement l’indexeur local ; la construction ou la reprise restent explicites.

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


Le décodage beam5 comparé au profil direct courant ne résout pas les défauts
bruit/chevauchement du corpus Opus ; le profil reste inchangé. Voir le domaine51.


Complément de recette Realtek audible préparé : lecture de trois phrases
fictives pour contrôler la piste système, sans modèle, écoute des captures
ou transmission. Prévol réel : playback403, quatre refus start/resume, aucun
accès audio et fermeture normale ; douze tests de garde passent. Aucun ancien
accord audio réutilisé. Jabra toujours absent, L12 reste ouvert. Preuve :
`logs/foresight-runtime/REALTEK-AUDIBLE-PREP-ROOT-20261021.json`.


Le filtre audio générique évalué sur sept fichiers fictifs n’améliore pas
les transcriptions. Aucun filtrage automatique ajouté ; voir le domaine51.


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


### Assistant de réunion — 21 octobre 2026

Agent reste un seul serveur sur8001. Le client LLM reprend une fois le refus explicite « Model is unloaded », sans augmenter le budget ni charger un modèle local ;117tests ciblés passent. Les quinze réponses fictives sont maintenant mesurées dans l'interface avec leurs citations, mais le P95 de14,1203s dépasse la cible10s. Aucun lot supplémentaire clos (9/13). Détails et limites : `docs/38_FORESIGHT_DELIVERY.md`, rapport `logs/foresight-runtime/MODEL-UNLOADED-RECOVERY-F13-ROOT-20261021.json`.


### F13 qualifiée après stabilisation du serveur réseau — 21 octobre 2026

L'utilisateur signale avoir corrigé le chargement intermittent d'EmbeddingGemma2 et de Gemma4. Cette modification externe n'est pas attribuée à Agent et ses paramètres globaux ne sont pas audités. Une nouvelle mesure complète, avec le même code Agent et le même corpus fictif original, obtient15réponses utiles visibles pour15questions, quinze HTTP200 et aucune reprise. P50visible1,3479s, P95visible1,7657s (rang supérieur, du commit du segment stabilisé au paragraphe visible après deux frames). La cible10s est atteinte dans cette configuration réseau. Le passage précédent à14,1203s et ses résultats bruts restent conservés ; aucune cause générale ni fiabilité continue du serveur n'est déduite de ce seul passage.

Les quinze réponses sont relues, les citations C1 et les révisions des segments SQL sont contrôlées. Le contrôle littéral scellé reste14/15 : « Aucun achat n’est autorisé » est une formulation correcte du refus, confirmée par relecture ; le corpus n'est pas modifié.58tests actuels vérifient contexte, droits/périmètre, déduplication des questions chevauchantes, admission, états obsolètes et réveil du worker. Le Job privé est fermé, sans capture, résident STT ou modèle local restant. Aucun changement des opt-ins de production, modèle distant, clé, budget ou donnée métier.

F13 (« Live Q&A et cartes proactives » après texte stabilisé) est qualifiée sur cette portée, y compris détection, déduplication et réponse sourcée. Cette mesure n'inclut pas la reconnaissance vocale : L03 reste ouvert. Aucun lot supplémentaire clos :9/13lots ;18/25fonctions ;15/17recettes. L02/L03/L11/L12 restent ouverts. Rapport : `logs/foresight-runtime/F13-STABLE-NETWORK-VISIBLE-ROOT-20261021.json`. Audit cumulatif : `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r61.json`.


### Capture interrompue — 21 octobre 2026

Le helper Windows existant conserve désormais la file audio déjà reçue et la fin du tampon de conversion après interruption, tout en gardant l'erreur visible.33tests et15sous-tests ciblés ainsi que69contrats de reprise passent ; aucune nouvelle capture matérielle. Encodage Opus et serveur unique8001 inchangés. Portée et limites : `docs/23_MEETING_AUDIO.md`, rapport `logs/foresight-runtime/NATIVE-INTERRUPTION-TAIL-ROOT-20261021.json`. Aucun lot supplémentaire clos.


Recette matérielle regroupée v2 préparée (21octobre) : une seule fenêtre proposée
de deux heures après première ouverture, sans quota d'essais. Prévol sans audio
réussi ; accord humain en attente et Jabra absent. Aucun lot clos sur cette
préparation. Voir `docs/23_MEETING_AUDIO.md` et le protocole v2 qui y est lié.


Comparaison CPU4/8 du21octobre : corpus fictif complet identique, faible gain sur
le délai de calcul haut et mêmes deux erreurs de fond. Le profil quatre threads
reste inchangé ; aucune qualification de latence visible. Détails dans
`docs/23_MEETING_AUDIO.md` et `logs/foresight-runtime/CPU-THREAD-COMPARISON-ROOT-20261021.json`.


Vérification globale du21octobre : frontend complet983/983tests sur95fichiers,
sources inchangées ; backend complet encore en cours, avec un échec initial
conservé. Aucun résultat global backend ni clôture L12 anticipés. Voir
`logs/foresight-runtime/CURRENT-FRONTEND-GLOBAL-ROOT-20261021.json`.


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
