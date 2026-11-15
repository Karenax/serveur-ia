# Réunions audio : transcription, interlocuteurs et synthèse LLM

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

Mode d’emploi : [Démarrer une réunion et préparer son CR](56_MEETING_START_GUIDE.md).
Bilan : `logs/foresight-runtime/L12-FINAL-ACCEPTED-DELIVERY-ROOT-20261022.json` ;
audit `acceptance-r97.json`. Aucun nouvel enregistrement ni modèle lancé pour
cette clôture documentaire.


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
résident CPU fermés. [Guide de démarrage](56_MEETING_START_GUIDE.md).
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


## Préparation des statuts opérationnels par profil — 22 octobre 2026

Le reçu actif est propre au profil CPU éprouvé sur un échantillon physique.
Un profil GPU différent ne peut pas reprendre ce PASS. Les quinze textes et
26 Opus du passage GPU déjà terminé disposent désormais d’un reçu séparé,
relié au profil actuel et au même binaire medium relu par SHA256. Il atteste
le fonctionnement de cette chaîne fictive ; qualité industrielle, latence
humaine et capture matérielle restent explicitement non qualifiées.

Le lecteur candidat passe vingt tests de refus d’identité périmée, constructeur
contradictoire, population incomplète et confusion de portée. Il n’est pas
raccordé au serveur actif. Le reçu CPU demeure intact. Aucun modèle, microphone
ou réseau n’a été ouvert pour cette préparation ; aucune source applicative
n’a changé pendant la suite backend complète toujours en cours. L03/L12 restent
ouverts. Preuve : `logs/foresight-runtime/GPU-OPERATIONAL-EVIDENCE-PREPARATION-ROOT-20261022.json` ; audit `acceptance-r84.json`.


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

## Lecture humaine et arrêt Realtek — résultat courant du 21 octobre 2026

Le préfixe de lecture humaine du Jabra, arrêté à la confirmation et avant toute
diffusion des WAV fictifs, retrouve **230 volts, 16 ampères, 1 250 millimètres et
350 lux** par transcription CPU locale : quatre contrôles sur quatre, trois
segments entièrement dans la fenêtre confirmée de 69 959 ms. Le texte attendu
n’est pas fourni au moteur. Aucun audio n’a été écouté par Codex ; le texte brut
reste local, sans LLM ni envoi réseau. Cette preuve ne qualifie pas toute parole
industrielle ni l’endurance.

La confirmation humaine Realtek arrive alors que la capture est déjà interrompue.
Les 242,470 s conservées restent intègres, mais cette lecture n’est pas qualifiée.
Une capture de diagnostic ultérieure, sans nouvelle lecture demandée, s’arrête
normalement : 426,179 s, 1 838 323 octets, 86 fragments micro et cinq fragments
système. Tous les fragments et reçus durables sont intacts, sans trou interne
observé sur chaque piste ; les délais initiaux restent distincts. L’interruption
antérieure n’est pas reproduite et sa correction n’est pas démontrée.

Le retrait Jabra a aussi révélé un retard d’environ 70,584 s entre l’observation
du processus audio arrêté et l’événement persistant d’interruption. La cause
reste à établir. Ce retard est distinct du correctif d’affichage de la ligne
sélectionnée décrit ci-dessous. Toutes ces captures et leurs Jobs sont fermés.

Le helper natif écrit désormais un `capture-failure-<uuid>.json` local exclusif
en cas d’exception : catégorie, codes système, chaîne des causes et coordonnées
de pile, sans source des lignes ni variables locales. Un stockage plein ne doit
pas masquer l’erreur initiale si ce diagnostic ne peut pas être écrit. Le journal
audio ignore ces fichiers de diagnostic. La cohorte ciblée de 50 tests passe,
ainsi que Ruff. Le nouveau helper a été utilisé dans le diagnostic Realtek privé ;
aucune erreur n’y a produit de fichier de panne. Aucun succès global backend
après ces modifications n’est revendiqué.

Preuve courante : `logs/foresight-runtime/HARDWARE-HUMAN-READBACK-ROOT-20261021.json`.
Les paragraphes suivants conservent les étapes précédentes ; leurs mentions
« global en cours » sont historiques. L12 reste ouvert.

## Statut latéral de la séance synchronisé — 21 octobre 2026

Après un arrêt, une pause ou une interruption, l’en-tête pouvait avancer alors
que la ligne **Notes et séances** conservait l’ancien état de la liste parent.
La ligne sélectionnée utilise désormais le snapshot déjà accepté par le Studio,
y compris sa date. Les autres séances ne sont pas modifiées ; une réponse de
lecture ancienne ne peut pas rétablir un état périmé, et le brouillon reste conservé.

Trois régressions reproduisent le défaut avant correction ;105contrôles Studio
et le global frontend986tests/95fichiers passent après correction. TypeScript et
Vite passent. Une recette visuelle sans audio, avec état fictif injecté après
chargement de la liste, montre **Conservée** aux deux endroits. Cette recette
d’affichage n’est pas une nouvelle capture réelle. Son Job est fermé sans audio.

Le correctif est servi par8001 : JS/CSS/favicon identiques aux octets compilés,
HTML conforme à la normalisation de fins de ligne existante de `mp_index`.
Le premier contrôle HTML brut négatif est conservé. Les anciens assets restent
présents ; aucun redémarrage backend, modèle ou accès aux données métier.
Les479sources Python du global backend en cours restent inchangées.
Preuve : `logs/foresight-runtime/STUDIO-LIST-STATE-ROOT-20261021.json`.

## Recette matérielle regroupée en cours — 21 octobre 2026

Les sorties système Jabra et Realtek viennent d’être capturées par WASAPI puis
arrêtées normalement, avec cinq fragments Opus par sortie et83282octets chacun.
Les reçus SQL et les SHA256 sont intacts après fermeture des Jobs. Le son utile
conservé dure20138ms par sortie, après un délai initial distinct ; aucune
continuité depuis l’instant zéro n’est prétendue. Les trois phrases fictives
ont été diffusées sur chaque sortie explicitement sélectionnée.

La transcription medium CPU locale restitue les six mesures/unités suivies
pour Jabra et cinq sur six pour Realtek selon les critères de format déjà
présents avant la capture. Le critère d’éclairement échoue sur Realtek ; il reste
à vérifier. Le contrôle littéral initial du mot « lux » échoue sur les deux
sorties et reste conservé séparément. Ces mesures ne qualifient pas la précision
industrielle globale, la voix humaine ou la latence directe.

Une capture préalable micro+système Jabra s’est interrompue sans retrait demandé,
avec une erreur générique ; ses86fragments micro et leurs reçus restent intacts.
La cause exacte n’est pas établie. L’interface affiche l’interruption et la piste
système absente. Aucune confirmation de lecture humaine n’a été reçue pendant
cette capture. Elle ne vaut ni arrêt normal ni qualification du microphone.

F03 est qualifié : la capture système Jabra a commencé sans projet, a été conservée puis rattachée
au seul projet fictif choisi : rejouer la même commande conserve un enregistrement,
une commande et la même révision. Aucun texte de note n’a été édité dans cet essai.
Quatre contrats courants réussis couvrent séparément le transfert de note,
les fragments, le rejeu et les droits ; preuve complémentaire
`logs/foresight-runtime/F03-UNASSIGNED-PHYSICAL-ROOT-20261021.json`.
Tous les flux audio et les processus de ces trois copies privées sont fermés.
La suite de la séance autorisée attend la disponibilité humaine pour la lecture
des microphones et le retrait/rebranchement ; son échéance commune n’est pas renouvelée.

Preuve : `logs/foresight-runtime/HARDWARE-CONSOLIDATED-V2-SYSTEM-ROOT-20261021.json`.
Les textes bruts restent privés et locaux ; seules les mesures sont exposées.
L02/L03/L11/L12 et T03/T16 restent ouverts.

## Utiliser les réunions et préparer un CR — parcours courant

1. Ouvrir **Réunions → Nouvelle séance**, saisir le titre et choisir le projet.
   Choisir **Enregistrer une réunion**, puis **Ouvrir la séance**.
2. Dans **Source audio de la réunion**, choisir **En salle · microphone** ou
   **À distance · son du PC + ma voix**. Le choix **son du PC** seul exclut votre voix.
3. Déplier **Périphériques**, choisir **Microphone à utiliser** et la
   **Sortie Windows à enregistrer** effectivement utilisée par la visioconférence.
4. Cliquer **Démarrer la réunion**. **Notes** permet d’écrire pendant la capture ;
   **Transcription** indique les fragments sauvegardés et l’état du direct.
   La sauvegarde audio reste utile lorsque le direct est désactivé ou en retard.
5. Cliquer **Arrêter Windows et conserver la séance** et attendre **Conservée**.
   Une alerte de piste manquante signifie que cette piste n’a aucun fragment :
   vérifier ce point avant de considérer l’enregistrement comme complet.
6. Dans **Transcription**, choisir l’enregistrement puis **Transcrire et séparer
   les voix**. Relire les valeurs, noms et négations ; corriger puis cliquer
   **Valider la transcription**. Si aucun projet n’était choisi, rattacher d’abord
   la séance à son projet pour accéder au parcours de CR du projet.
7. Cliquer **Préparer le compte rendu**, relire le brouillon et les actions,
   puis **Valider et enregistrer le compte rendu**. La publication reste explicite.

Les nouvelles captures sont compressées en Opus ; les anciens WAV restent
consultables. Le parcours complet sur fichiers fictifs avec relecture a réussi.
Le direct industriel, l’audibilité de toute configuration et L12 restent en
qualification : ils ne sont pas garantis par la seule présence des boutons.

Libellés relus le21octobre2026 dans les composants actifs ; cette mise en avant
du guide n’ouvre aucun microphone et ne relance aucun modèle. Les sections
datées suivantes conservent l’historique des essais et leurs limites.

## Budget des travaux IA de séance

Le16octobre2026, l’attente du proactif et des enrichissements est alignée sur
le délai standard30s du planificateur. La question garde la priorité devant
les automatiques en attente ; un contrôle réseau réel le vérifie. Modèles,
capture et relecture du CR restent inchangés. Détails et limites dans le domaine25.


## Transcription complète medium CPU livrée — 15 octobre 2026

Le parcours habituel d'enregistrement complet, également présenté dans le Studio
via `MeetingAudioPanel` après rattachement/conservation, préfère désormais medium
CPU quand ses fichiers sont déjà installés. La capture et le direct gardent leur
profil small ; le traitement par fragments conservés de séance n'est pas migré.
Les overrides `PB_MEETING_SPEECH_MODELS_DIR`, puis `PB_SPEECH_MODELS_DIR`, restent
prioritaires. Sans medium complet, le runtime small habituel reste disponible.
Le simple statut ne charge aucun modèle ; le worker de transcription complète
le charge sur demande et termine après le traitement. Aucun GPU, téléchargement
ou chargement de LLM local ajouté. Aucun nouveau serveur ni changement de port.

Le parcours API réel import → Whisper medium CPU → diarisation Sherpa CPU →
validation technique privée → Gemma réseau → publication privée → rejeu réussit
en16,039s sur20,25s d'audio fictif. Les six valeurs230V,16A,1250W,350lux,0,2mm et
1,5m sont présentes dans la transcription et le brouillon. Un seul CR privé,
zéro action automatique, deux quick_check réussis ; Job naturellement vide avant
fermeture et handles fermés. Cette validation fictive ne vaut pas validation métier
humaine et ne qualifie ni toutes les35 annotations, ni le direct5s, ni sa latence.

68 tests ciblés et Ruff app/backend/tests passent. Avant activation, Brain, ERP
et EG2 sont sauvegardés avec integrity_check et restaurés dans des copies privées.
Agent8001 est redémarré une seule fois sans capture ou traitement audio actif.
Le statut HTTP annonce medium CPU pour le fichier complet et small CPU pour le
direct. La lecture statistique initiale dépasse le délai d'observation4s du pilote ;
ce rapport reste conservé. La relecture suivante réussit sans second redémarrage.
Toutes les tables non volatiles Brain/ERP comparées sont identiques, y compris
les6/17tables protégées sélectionnées ; aucun ajout métier ni restauration source.

Le global backend2580 est antérieur à ce petit delta de sélection/statut et ne
devient pas artificiellement un nouveau global ; frontend943 et assets inchangés.
La précision industrielle du direct, la recette matérielle regroupée et le vrai
disque plein isolé restent distincts. L12 n'est pas déclaré clos.


## Endurance réseau réelle terminée et contrôle CPU ciblé — 15 octobre 2026

Une heure de cadence réelle sur deux pistes fictives, CPU/int8/quatre threads :
1 440 fragments acquittés et présents, séance finalisée, tous les travaux STT
et trois fenêtres LLM terminés (neuf dispatchs réels). Driver et fixture sortent0,
Job naturellement vide, handles fermés, aucun arrêt forcé ni erreur. Aucun micro.
Le panneau Transcription observé après32min n'apporte pas une mesure P95 visible.

Comparaison sur les15 phrases entières et35 motifs originaux, sans texte attendu
fourni aux moteurs ; pas une qualification des fragments5s ou du batch diarisation.

| Modèle CPU | Beam | Phrases exercées | Motifs originaux retrouvés | Temps de décodage cumulé |
|---|---:|---:|---:|---:|
| small | 1 | 15/15 | 24/35 | 28.2 s |
| small | 5 | 15/15 | 27/35 | 32.0 s |
| medium | 1 | 15/15 | 29/35 | 86.3 s |
| medium | 5 | 15/15 | 30/35 | 94.9 s |

Les motifs peuvent refuser une ponctuation ou une formulation correcte : ce score
n'est ni WER ni taux d'exactitude métier. Les sorties brutes sont conservées.
Le premier lancement du comparatif est refusé avant modèle par le PID du lanceur
venv Windows ; le second utilise le même interpréteur de base que T12 avec -S.
Aucune activation de modèle/configuration de production sur ce seul comparatif.

Les seuils RAM fixes et arrêts sur retard/backlog ne bloquent plus cette recette.
Restent les vérifications réelles de conservation, identité, droits et arrêt demandé.
La recette capture/navigation/reprise attend l'accord audio regroupé déjà demandé ;
le vrai disque plein attend un volume isolé, indisponible au jeton Windows actuel.
La précision industrielle du direct reste à établir. L12 n'est pas déclaré clos.


## Prévol UI/API regroupé sans enregistrement — 15 octobre 2026

Deux projets et séances fictifs, navigation entre projets, actualisation et
deux onglets ont été manipulés dans le navigateur. Les sélecteurs Realtek sont
lisibles et sélectionnables ; aucun enregistrement n'a été démarré. Les quatre
POST start/resume de prévol sont refusés403 avant ouverture. Le serveur termine0,
Job naturellement vide, lecteur de conservation réussi et aucune piste créée.
La tentative de clic UI Démarrer est rejetée par l'approbation automatique,
car les anciens accords audio uniques sont consommés. Aucun repli/contournement.
Le paquet prépare une seule séance de recette de10min maximum, sans écoute,
transcription ou envoi réseau. Le Jabra est absent de l'inventaire actuel.
T01–T04 matériels restent non qualifiés par ce seul prévol. Voir le registre38.


## Résilience de la recette T12 V8

La recette privée écrit et synchronise chaque fragment avant l'envoi. Chaque
piste dispose d'un expéditeur FIFO ; les reprises HTTP gardent corps et commande
identiques. Le retard, le backlog et la RAM sont observés sans coupure forfaitaire.
Un refus d'accès, une identité invalide, une panne réelle d'écriture ou une
annulation restent des erreurs. Ces changements concernent le protocole de
qualification, pas les réglages audio de production. Aucune nouvelle acquisition
matérielle. Voir [la livraison](38_FORESIGHT_DELIVERY.md).


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

[Résultats réels de l’assistant](../logs/foresight-runtime/g-assistant-utility-720cee972bba4a9b8c3c4a595e18c299/results.json) · [Contrôle final](../logs/foresight-runtime/g-assistant-utility-720cee972bba4a9b8c3c4a595e18c299/launcher-final.json).

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

[Brouillon de CR de l’essai](../logs/foresight-runtime/CR-physical-20a2ee11e15f40738c17438970347382/draft-CR.md).

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
n'est lancé et L12 reste ouvert. Voir [le protocole](../.ui-preview/pilots/physical-capture-cr-20261015/PROTOCOL.md).

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

[Preuve de publication](../logs/foresight-runtime/CR-workflow-UI-publication-ROOT-a83e079761f04e4789d024ad035e2672.json), [capture du bouton et du panneau](../logs/foresight-runtime/CR-workflow-access-20261015.jpg), [audit de livraison](../logs/foresight-runtime/CR-workflow-UI-delivery-ROOT-20261015.json).

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

### Portée de la recette GPU dans le produit

L'accord 99a5c9bc couvre un seul essai de cinq minutes maximum ; il est
consommé. Les anciens accords n'ont pas été réutilisés. Le paquet préparé
épingle les sources canoniques, les poids et les bibliothèques ; leurs
empreintes ne changent pas pendant l'essai. Aucun téléchargement, microphone,
pilote, modèle LLM local ou paramètre de production n'est impliqué.

Les trois WAV fictifs clean-02, clean-03 et clean-09 représentent 20,25 s avec
les séparations ajoutées. La transcription complète et sa diarisation réelles
terminent en 9,47 s dans la fixture. Après fermeture du worker complet, le
résident original transcrit les trois phrases entières : CUDA 0,
int8_float16, quatre threads CPU, un worker, faster-whisper 1.2.1 et
CTranslate2 4.8.2, propriétés natives observées avant acceptation. La synthèse
réseau et la publication privée terminent en 23,82 s ; le contrôleur, ses
vérifications et sa fermeture terminent en 34,41 s.

Les six motifs annotés tension/courant/puissance/éclairement/tolérance/longueur
sont retrouvés sur les deux chemins. Cette vérification de trois phrases
entières ne remplace pas le corpus industriel complet, les fenêtres à 5 s,
les négations, engagements, interlocuteurs multiples ou leur relecture.
Les trois listes décisions/actions/points ouverts sont vides pour ces faits.

Le maximum GPU total échantillonné est 1293 Mio, sans réservation garantie ;
le pic de mémoire engagée du Job est 2 610 663 424 octets, sous sa borne de
4 Gio (ce n'est pas une mesure de RAM physique). Les chemins réellement
observés de cuBLAS, cuBLASLt et cuDNN correspondent aux empreintes préparées.
Le Job est vide et les handles fermés après l'essai ; les deux bases privées
passent quick_check. Le lecteur du résident est joint. Le protocole de
fermeture original peut terminer ses sous-processus ; aucune fin gracieuse
exit 0 de chaque sous-processus n'est revendiquée.

[Audit et limites](../logs/foresight-runtime/GPU-product-and-fallback-delivery-ROOT-e0176bcfd58e41e7b6c9d02eb527f9b3.json).

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

[Résultat réel](../logs/foresight-runtime/CR-defaultCPU-3972da4f7a1e4b2ab4d56e85f379616f/result.json), [CR obtenu](../logs/foresight-runtime/CR-defaultCPU-3972da4f7a1e4b2ab4d56e85f379616f/draft-CR.md), [activation et sauvegardes](../.ui-preview/backups/CR-activation-70055a8723a84b6caf707e15ba192084/ROOT-activation.json), [audit de livraison](../logs/foresight-runtime/CR-product-delivery-ROOT-42fb44d5c4474ac58d5945541ddb6ada.json).

### Utiliser le parcours de compte rendu

Dans **Réunions → Nouvelle séance**, renseigner un titre et le projet, choisir
**Importer un audio**, puis **Ouvrir la séance**. Dans la séance, ouvrir
**Autre option : navigateur ou fichier audio** et choisir le fichier. Le CR
se prépare par le bouton **Compte rendu** en tête de séance, via le parcours audio : transcrire,
corriger les interventions et les noms, **Valider la transcription**, puis
**Préparer le compte rendu** et **Valider et enregistrer le compte rendu**.
La sauvegarde publie dans les Revues et la connaissance du projet ; les tâches
restent une conversion explicite. Choisir le projet dès la création facilite
l'accès à ce parcours ; une séance sans projet doit d'abord y être rattachée.

Pour la capture Windows, le panneau **Audio de la réunion** propose la source
son du PC / son du PC + voix / microphone, les périphériques, puis
**Démarrer la réunion**. Ces contrôles ont été observés dans l'interface active
sans être déclenchés. Aucun accord microphone antérieur n'a été réutilisé.

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
[Audit SQL de la cohorte V2](../logs/foresight-runtime/integrated-SQL-cohort-V2-ROOT-541ab17b1dcb4f42aac7e8c563946ae8/ROOT-post-terminal-audit.json), [revue distincte](../logs/foresight-runtime/integrated-SQL-cohort-V2-independent-source-review-20261015-cfa76327.json).

[Contrôle SQL réel, ASR simulé et limites](../logs/foresight-runtime/integrated-GPU-session-SQL-smoke-ROOT-b15766a857b04160b88956e33beb34c2/ROOT-post-terminal-audit.json).

[Raccord privé vérifié et limites](../logs/foresight-runtime/integrated-GPU-current-profile-V2-ready-ROOT-20261015.json).
[Résultat GPU réel et limites](../logs/foresight-runtime/direct-two-track-medium-gpu-61cd940dca4947b9bd2ec92975cb0757/ROOT-terminal.json). Audio intégré, qualité/latence,
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
une coupure électrique ou une capture matérielle : **T16 complet reste ouvert**. Le compte courant ne possède pas le privilège Windows requis pour monter un volume virtuel isolé. Aucun disque créé, monté, formaté ou saturé. [Précondition vérifiée](../logs/foresight-runtime/T16-isolated-volume-current-prerequisite-ROOT-20261015.json).
[Preuves des arrêts et reprises](../logs/foresight-runtime/T16-process-crash-ROOT-25a790a9208a49698047505bd568ea8a/ROOT-post-terminal-review.json).
[Résultats, empreintes et limites](../logs/foresight-runtime/Current-regressions-completed-ROOT-ae3a993a9e074ef3a4fac48e08dcec20.json).



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
ROOT ne force aucun déchargement pendant ce constat. [Observation finale](../logs/foresight-runtime/ROOT-final-network-observation-e849e9a6938f470eb64abac506f8f10e.json).

[Traces des passages et limites](../logs/foresight-runtime/Assistant-current-attempts-ROOT-3e23fb04a6c34093891d097b034126f2.json).

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
[Preuve et limites](../logs/foresight-runtime/Qualification-source-reviews-ROOT-dbee566e51ee41ca87630fe1464507c4.json).


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
[Preuves du corpus et limites](../logs/foresight-runtime/L09-heldout-actual-progress-ROOT-20261015-ae41367f0673479498a5529184fc8dea.json).

**Vérification canonique L03 : 64 cas et 39 sous-tests réussis.**
Ruff passe sur le backend, les tests et les nouveaux scripts.
La suite complète du projet est en cours sur bases fictives.
Les cinq retours de recherche audio privée sont corrects : deux
citations au rang 1, trois exclusions vides, réouverture et réimport
sans doublon. Les quatre conversions FFmpeg et le modèle CPU ont
effectivement travaillé ; le Job était naturellement vide.
Le terminal global du lanceur n’est pas observable après interruption :
ces preuves de composant ne clôturent ni L09 ni L12.
[Vérifications, portée et limites](../logs/foresight-runtime/L03-canonical-checks-ROOT-f95de1e1288d49bca3e49056250aac5f.json).

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
[Publication, sauvegardes et portée](../logs/foresight-runtime/L03-canonical-publication-ROOT-2e88d524ad9b4f08a838c6e4ec9d6ecf.json).

**Restent à qualifier : capture réelle, ASR industriel, double piste GPU et
délais visibles, assistant utile sous charge, recherche multimodale élargie
(audio et intégration active), incidents physiques/reconnexion LLM et chaîne
intégrée ≥60 min.**
L09, T16 physique et L12 restent ouverts. Adaptation visuelle validée et
exclusion de Drive maintenues. Aucun commit ni push. Les sections précédentes
ci-dessous restent l’historique de leurs essais, et non l’état courant.
[Résultats, sauvegardes et portée](../logs/foresight-runtime/Active-delivery-progress-ROOT-20261015-b5a4cb53e57c45e7960142a027cd6ecb.json).


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
[Preuves et portée](../logs/foresight-runtime/Backup-audio-actual-progress-ROOT-20261015-24b4f526b6544936954f7b079f42152d.json).


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
[Preuves et portée](../logs/foresight-runtime/R4-backup-private-progress-ROOT-20261015-a982f5ad38a34a7485f3c5dfa7825ef6.json).


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
Drive reste exclu. [Preuves et portée](../logs/foresight-runtime/Private-audio-frontend-progress-ROOT-20261015-ce5f2ca208c345819bbbedebb96a550d.json).


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
[Preuves et portée](../logs/foresight-runtime/Modality-journal-progress-ROOT-20261015-43d7dc32e96c4423a1136cdf761c151a.json).


## Reçus audio corrigés dans les sources ; rechargement en attente — 15 octobre 2026

Le rejeu audio confirme désormais chaque fragment en SQL et répare atomiquement le reçu local, en conservant ses anciens octets ; ses 37 tests ciblés passent séparément du décompte global. Le rechargement d’Agent 8001 reste en attente : l’inactivité des jalons et des travaux documentaires et l’identité du module chargé ne sont pas établies. L’essai CPU CAO V1R1 a été refusé avant admission du moteur, avec 16 sources privées conservées et huit entrées échouées ; une copie V1R2 est en préparation privée, sans nouvelle recette exécutée. La QA du profil GPU privé passe dix contrats purs, sans mesure GPU, capacité, SQL ou appareil ; les droits NVIDIA, la recette couplée et L03/T16 matériel/P95/T12/L12 restent ouverts.

Suite backend globale : 2459 cas uniques, 2458 passés, 0 échecs, 0 erreurs et 1 ignorés ; sortie 0.

[Preuves et limites](../logs/foresight-runtime/Native-receipt-progress-ROOT-20261015-b4e62dea8c7f4273810916e806a195a7.json) · [Suivi détaillé](38_FORESIGHT_DELIVERY.md).


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

[Preuves et limites](../logs/foresight-runtime/Native-Stop-addendum-status-ROOT-20261014-1f1ee78928c44947b5d0c727ca65818c.json).


## Historique — correctif Stop activé et préparation GPU, état avant la recette native du 14 octobre 2026

Le correctif du bouton Stop est activé dans l’interface du serveur unique Agent, sur 8001. Les simulations vérifient la conservation du texte partiel et des citations et le maintien des vraies erreurs réseau. **924/924 tests frontend passent**, dont 16 cas AssistantPanel ; TypeScript et compilation séparée réussissent. Les anciens assets sont conservés et l’index sauvegardé permet le retour arrière. **Le comportement natif de Stop reste à qualifier dans le navigateur ; Assistant, P95, T12 et L12 restent ouverts.**

[Preuves et limites](../logs/foresight-runtime/Assistant-Stop-UI-and-GPU-pure-progress-ROOT-20261014.json).

La préparation GPU a passé 54 contrôles simulés de cadence, provenance, mesures partielles, consentement et limites. Aucun GPU, DLL NVIDIA ou microphone utilisé par ces tests. La revue des sources autorise uniquement cette QA ; les lectures normales des dépendances, les droits précis en attente et un nouvel accord pour l’essai GPU restent requis.

Stop utilise un motif propre à chaque demande et masque uniquement l’erreur portant exactement ce même objet. Une erreur native distincte reste visible : les tests simulés ne prouvent pas la propagation du motif par le lecteur natif. Le fichier pnpm-workspace.yaml déclare le seul frontend racine ; les règles existantes de compilation esbuild sont conservées. La suite backend globale n’a pas été relancée pour cette seule modification frontend.


## Assistant réseau V5R4 — priorité et annulation observées, 14 octobre 2026

La recette fictive V5R4 a exécuté six requêtes sur le serveur réseau. Deux demandeurs ont réellement attendu : la question passe avant l’enrichissement. Le vrai bouton Stop interrompt le flux local, avec captures et horodatages cohérents. Les services proactif et automatique retournent une réponse. Notes, versions et sources protégées sont conservées ; ressources privées fermées, sortie 0. **Seule la fermeture de cette recette est qualifiée ; Assistant, P95, T12 et L12 restent ouverts.**

[Résultat et preuves](../logs/foresight-runtime/G-ASSISTANT-V5R4-actual-objective-status-ROOT-20261014.json). 111 tests Python et 16 JavaScript réussis ; aucune nouvelle suite globale.

Le contrôle final ROOT dans le navigateur n’a pas été atteint avant la fin de la fenêtre de travail ; le serveur a effectué son arrêt automatique propre. Les cartes proactives affichées, le tick automatique, les réponses utiles et leurs délais représentatifs restent à qualifier. Un message technique trompeur apparaît après Stop ; son correctif reste à vérifier. Aucun microphone, ASR, GPU ou modèle LM Studio local utilisé dans cet essai.

Les droits des 15 fichiers publics NVIDIA et de leurs neuf dossiers, racine incluse, ont été lus. La réparation proposée sur 23 éléments a été rejetée avant lancement par le contrôle automatique d’approbation : l’accord d’installation précédent ne couvre pas l’extension précise des permissions. L’accord humain demandé porte sur ces seuls accès ; aucun droit modifié, aucun nouvel essai GPU autorisé ou lancé.


## Direct deux pistes CPU — débit insuffisant constaté, 14 octobre 2026

L’essai réel medium CPU4 a traité les 16 fragments fictifs des deux pistes. Une paire de fragments arrive toutes les 5 s, mais les paires complètes à chaud demandent 10,45 à 11,70 s : la file augmente. Ce profil échoue au débit de cette cohorte. La recette termine aussi en refus de contrôle, sortie 1. **Direct, précision industrielle, P95, T12 et L12 restent ouverts.**

[Résultat et preuves](../logs/foresight-runtime/DIRECT-V2-actual-objective-status-ROOT-20261014.json). 28 tests purs réussis ; aucune nouvelle suite globale.

Les 8 paires totalisent 37,5 s par piste, 75 s au total ; les deux pistes reprennent les mêmes voix fictives. Les horloges du driver donnent une moyenne de 10,964 s par paire complète à chaud, de 2 à 10 demandes encore en cours ou en attente juste après chaque arrivée, et 53,383 s pour terminer après la dernière arrivée. Il ne s’agit ni du seul calcul neuronal ni du délai après fin de parole jusqu’à l’affichage. Les 16 demandes/réponses et leurs empreintes sont conservées ; les originaux et fragments restent intacts. La réutilisation du fichier PCM dérivé est distincte d’une perte des originaux.

Le contrôle final reste en échec après les refus d’accès à NUL consignés au journal et ne fournit pas de reçu terminal naturel dédié. Le processus extérieur est sorti, le Job est vide et les handles sont fermés. Après ce terminal, 392 fichiers sources et poids ont été relus avec empreintes exactes ; cela ne transforme pas le refus initial en réussite. Aucun micro, GPU, service LM Studio, stockage SQL ou affichage Studio utilisé par ce diagnostic. Aucun profil de production changé. Les préparations des sections antérieures restent des éléments historiques.


## Recette assistant V5R2 — résultat partiel, 14 octobre 2026

La recette courte V5R2 a réellement ouvert l’assistant sur une copie fictive et obtenu une réponse réseau sourcée conservant 1250 W, les réserves et les négations. La paire concurrente n’a pas démarré ; annulation et services de fond non exécutés. Le thread de fermeture a été refusé : sortie1, cleanup non qualifié. Les ressources privées sont fermées et les données protégées conservées. **G_ASSISTANT, P95, T12 et L12 restent ouverts.**

[Résultat ROOT](../logs/foresight-runtime/G-ASSISTANT-V5R2-actual-objective-status-ROOT-20261014.json) ; [audit indépendant](../logs/foresight-runtime/G-ASSISTANT-V5R2-partial-actual-independent-audit-remaining-20261014.json).

Aucun microphone, capture physique, ASR ou GPU utilisé dans cet essai. Le diagnostic CPU deux pistes reste une préparation distincte, sans qualification du débit.


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
[Preuve nominale](../logs/foresight-runtime/L03-coupled-V4-actual-objective-status-ROOT-20261014.json).

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
[Résultats et audits des trois contre-épreuves](../logs/foresight-runtime/L03-counter-V2-three-actual-objective-status-ROOT-20261014.json).

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

[Refus terminal ROOT](../logs/foresight-runtime/l03-grouped-real-v2-refusal-root-20261014.json) ;
[préparation V2](../.ui-preview/pilots/l03-grouped-real-pilot-v2-20261014-41c2c3a710a5/preparation-v2.json) ;
[point navigateur réel](../logs/foresight-runtime/cua-direct-provider-point-root-20261014.json).


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
[Protocole L03](../.ui-preview/pilots/l03-grouped-transaction-v2-20261014-4c0f31c397fe/PROTOCOL.md) ;
[paquet scellé](../.ui-preview/pilots/l03-grouped-transaction-v2-20261014-4c0f31c397fe/preparation-v2.json) ;
[revue indépendante](../.ui-preview/pilots/l03-grouped-transaction-v2-20261014-4c0f31c397fe/reviews/independent-transaction-review-assistant-20261014-v1.json).


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
[Essai réel](../logs/foresight-runtime/medium-consolidation-success-root-20261014.json) ;
[contrat de consolidation](../.ui-preview/pilots/l03-grouped-pcm-contract-20261014-73d64b8cd8d4/CONTRACT.md) ;
[QA pure visuelle](../logs/foresight-runtime/ui-visible-geometry-v2r1-root-pure-qa-20261014.json).


## État actuel de la livraison — 13 octobre 2026

| Domaine | État établi |
| --- | --- |
| Notes et Studio | **Correctif actif dans Agent**, après publication, reprise du serveur et contrôle de l'interface. Réponses bornées à 12 ajouts, citations strictes, note humaine conservée, absence d'ajout expliquée et suspension STT visible. |
| Régressions logicielles | **2444 cas Python uniques : 2442 réussites, 2 exclusions prévues**, par agrégation vérifiée de deux exécutions. Frontend **916/916 dans 88 fichiers** (indicateurs du 13 octobre), unités fictives 37/37, Ruff, TypeScript et build passent. |
| Enrichissement IA | Pilote réseau : 12 ajouts conformes ; revalidation locale V2 passée. Les erreurs ASR citées restent présentes : format validé, qualité des faits industriels non qualifiée. |
| Transcription CPU fictive | 3 phrases puis 30 résultats sur 15 WAV complets, workers fermés. **1250 W reste transcrit 2250 W** avec ou sans vocabulaire technique. Le diagnostic de précision CPU sur une phrase donne aussi **2250 W en int8_float32 et en float32** ; aucune de ces variantes n'est activée par ce diagnostic. |
| Réunion complète | Recette d'une heure partielle. Transcription physique, multipiste et premier texte visible/P95 non qualifiés ; **T12 et L12 restent ouverts**. |
| Périmètre retenu | Adaptation publique du Studio validée ; Google Drive exclu. Les étapes et reçus historiques sont conservés ci-dessous. |

[Qualification Python nommée](../.ui-preview/q/nac3/qa/python-aggregate-notes-ai-v2.json)
; [contrôles frontend/Ruff/TypeScript/build](../.ui-preview/pilots/t12-enhancement-schema-candidate-v2-20261013/qa-root-observed-20261013.json)
; [diagnostic CPU](../logs/foresight-runtime/t12-cpu-domain-paired-root-interpretation-20261013.json).

Les deux exclusions Python concernent le runtime audio optionnel et le dossier
Infomaniak absents. La qualification couvre les noms des cas sur deux exécutions,
pas un passage monolithique. Les motifs CPU 4/6 et 25/35 contre 23/35 ne sont pas
une précision générale. Ces diagnostics ont tourné pendant la QA logicielle et
ne qualifient pas les performances. Les sélecteurs de source/microphone/sortie
Windows et « Démarrer la réunion » ont été observés dans Agent, sans capture.
Les cinq documents ont été publiés après sauvegarde et vérification.
L'audit des droits de la nouvelle sauvegarde couvre 1 020 éléments : aucun accès
accordé aux groupes Utilisateurs ou Utilisateurs authentifiés.
[Audit des accès](../logs/foresight-runtime/notes-structured-data-backup-acl-current-20261013.json).

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

[Bilan et preuves](../docs/38_FORESIGHT_DELIVERY.md) ;
[interprétation CPU](../logs/foresight-runtime/t12-medium-consolidation-root-interpretation-20261013.json).


---

## Lancer une réunion dans Agent

1. Dans le menu de gauche, ouvrir **Réunions**, puis **Nouvelle séance**.
2. Saisir **Titre de la séance** et choisir le projet si connu. Dans **Préparation**,
   sélectionner **Enregistrer une réunion**, puis **Ouvrir la séance**. Si l'espace
   est désactivé, **Activer les réunions** permet d'ouvrir ce parcours.
3. Dans le Studio, choisir **Source audio de la réunion** :
   **En salle · microphone** pour les personnes présentes, ou
   **À distance · son du PC + ma voix** pour une visioconférence avec sa propre voix.
   **À distance · son du PC** conserve uniquement le son des applications.
4. Déplier **Périphériques** : choisir **Microphone à utiliser**, puis
   **Sortie Windows à enregistrer** pour le son du PC. Cette sortie doit correspondre
   au casque ou aux haut-parleurs utilisés par la visioconférence.
5. Cliquer **Démarrer la réunion**. La création de la séance seule n'ouvre pas le
   microphone. Le bouton est sous les choix audio, hors du panneau Préparation.
6. Utiliser **Transcription** pour consulter le texte reçu et **Notes** pour écrire.
   L'état du direct est indiqué dans Préparation ; sa disponibilité et le retard
   de traitement peuvent varier selon le moteur et les ressources du poste.
7. Pour terminer, cliquer **Arrêter Windows et conserver la séance**, attendre la
   confirmation, puis relire les textes avant de préparer et publier le compte rendu.

Si Démarrer est grisé, lire le message du bloc audio : capture Windows indisponible,
autre séance en cours ou audio navigateur restant à conserver. L'option
**Autre option : navigateur ou fichier audio** permet d'accéder au microphone du
navigateur et à l'import. Les noms des périphériques du navigateur peuvent
n'apparaître qu'après autorisation.

Parcours relu dans les composants actifs WorkspaceViews, MeetingStudio et
NativeMeetingCapture le13 octobre2026 ; cette lecture des commandes ne qualifie
pas à elle seule le microphone, le son du PC ou la transcription matérielle.


Livraison locale du 2 octobre 2026, serveur Agent unique sur `127.0.0.1:8001`.
Les comptes rendus manuels du module Revues sont conservés.

## Notifications et arrêt natif — correction du 12 octobre 2026

Un fragment est sauvegardé et acquitté par `_persist` sans rester dans une
deuxième file de notifications. La file des contrôles native est bornée à huit
messages ; elle contient ready/state/error et le handshake privé. Un contrôle
invalide ou une saturation interrompt explicitement la capture, avec journaux
conservés. Le verrou court rend atomiques erreur, état et notification, sans
englober les sauvegardes, accès SQL ni attentes de processus.

STOP vérifie les derniers fragments, EOF et sortie 0 du helper. Les attentes
EOF/processus utilisent le budget restant du délai ; cela ne constitue pas
une borne murale pour les accès SQL. Le raccord HTTP utilise la réservation enregistrée, y compris
après un état stopped automatique. Il commite `_native_drain_confirmed` avant
le reçu parent. Un arrêt non confirmé produit un rejet durable 409 et une
séance interrompue ; rejouer le même UUID ne transforme pas l’erreur en succès.
Une preuve de drainage non commise n’est pas déduite des WAV présents.

L’utilisateur peut alors choisir **Conserver les fragments acquittés** : cette
finalisation distincte regroupe uniquement les fragments SQL et conserve une
alerte durable, même après rechargement ou finalisation. Une réservation
native encore enregistrée bloque ce geste côté serveur. Le Studio propose
d’abord **Vérifier l’arrêt Windows** lorsque le propriétaire est encore présent.
La barre globale conserve son erreur d’arrêt et son lien de récupération après
disparition de la réservation native. Cela ne qualifie pas tous les scénarios
de perte spontanée d’un périphérique. Aucun geste de conservation n’ouvre un micro.

Les vérifications simulées couvrent 10 000 notifications de fragments sans
accumulation, drainage, handshake, débordement, EOF manquant, sortie en erreur,
course état/erreur, rejeu et pertes de commit. Le dernier ciblé natif/routes
passe **38/38** ; React passe désormais **802/802 dans 81 fichiers**, avec 218
sources inchangées, TypeScript/Vite et Ruff conformes. Les assets actifs sur
8001 correspondent au build vérifié. Le processus a démarré après les éditions
natives ; leur chargement est déduit de cet ordre, sans attestation en mémoire.
L’opt-in général et le direct sont actuellement actifs, sans changement de
réglages lors de cette vérification.

La régression Python V1 termine à **2 183 réussis/1 ignoré**, exit0, mais trois
sources ont changé et un test a été ajouté pendant la passe. Elle ne qualifie
pas l’état final. La V2 termine à **2 190 réussis/1 ignoré**, exit0, en
1 916,10 s, sur 371 sources inchangées dans
`logs/foresight-runtime/native-control-queue-global-20261012-v2/`, avec ses propres
bases/TEMP/cache neufs. Le
[reçu terminal](../logs/foresight-runtime/native-control-queue-20261012/python-v2-terminal.json)
revérifie les sources courantes ; le candidat STT isolé n’était pas inclus.
Le [reçu courant](../logs/foresight-runtime/native-control-queue-20261012/current-evidence.json)
conserve les différences de V1 et lie les preuves UI/build/source de V2.
La recette UI utilise des bases fictives, inventaire simulé, acquisition bloquée
et aucun clic d’enregistrement/conservation ; elle observe un seul bouton de
conservation partielle et l’alerte persistante. Son serveur privé a été fermé.
Les autres passages restent historiques ; cette correction ne borne pas la
file SQL de STT, ne mesure aucune latence réelle et ne clôture pas T12/L12.

La suite logicielle nécessaire est préparée dans le
[protocole d’admission STT](../.ui-preview/pilots/STT_ADMISSION_NEXT_PROTOCOL.md) :
séparer audio conservé et travail admis, limiter le stock global, maintenir une
reprise explicite par petits lots et fermer les contournements du worker.
Le statut retained et les quotas sont **implémentés en copie isolée seulement**. Une
réconciliation documentée du backlog historique est nécessaire avant toute
affirmation de borne ; les imports longs restent conservés pour le traitement
complet. La copie `.ui-preview/pilots/stt-admission-stage-20261012/` réalise ce
candidat, avec états retained/batch et un traitement complet explicite sans
projet. Ses tests/revues sont distincts de la V2 native ; elle n’est pas activée.
Son frontend final V5 passe **816/816**, TypeScript/build sur 218 sources
inchangées. La V1 Python termine à **2 290 réussis/2 échecs/2 ignorés** sur 377
sources inchangées : ressource Thunderbird absente et ancien test de reprise
automatique failed. La ressource est ajoutée, le test passe par la commande
explicite et conserve les assertions de correction humaine. La reprise ciblée
passe **153 réussis/1 ignoré** ; le mélange synthétique ignoré est vérifié
séparément. La V2 complète termine à **2 300 réussis/2 ignorés**, exit0, en
2 063,96 s à 16:12:01 UTC, sur 377 sources et 56 ressources inchangées. Le
[compagnon terminal V5](../.ui-preview/pilots/stt-admission-stage-20261012/qa/staged-checkpoint-v5-python-v2-terminal.json)
revérifie le JUnit et toutes les empreintes actuelles ; le checkpoint historique
V5 n’est pas remplacé. L’ancien essai complet de cadence échoué reste conservé ;
la nouvelle mesure des acquittements est revue. Le smoke fictif de 30 secondes
réussit avec 12 fragments conservés et un retour ACK maximal de 0,047453 s.
La cadence fictive d'une heure est terminée sur le même seal : 720 paires,
1 440 fragments et WAV exportés, deux pistes continues de 3 600 000 ms et
note/reçus conservés. Le retour ACK maximal est de 0,177379 s ; le dernier
revient à 3 600,0556 s. Le quota reste à 24 fragments/120 000 ms lors des
2 236 vérifications. La fermeture des deux engines est confirmée, sans enfant,
thread, acquisition ou inférence. Le
[résultat terminal](../logs/foresight-runtime/sqc-run-20261012-163237-ddd94164/qualification.json)
est relu indépendamment, dont les 1 440 SHA du ZIP. Les 48 failed sont des
échecs simulés explicites ; 1 368 fragments restent conservés hors admission.
Ni T12 ni L12 ne sont clos : cette preuve concerne conservation/quota/export.
Le raccord de désactivation générale du batch passe ses huit régressions dans
ce ciblé et une revue indépendante : interruption demandée même si un arrêt
existant échoue, sans `_shutdown` permanent ni perte de reçu/audio. Le direct
désactivé seul laisse le batch explicite disponible. Les erreurs de lecture
résolues ne restent plus affichées et n'effacent pas les erreurs de sauvegarde.
La recette fictive V5 observe les neuf éléments attendus, dont les deux
sélecteurs actifs et le batch personnel de durée inconnue ; aucun microphone,
lecture audio ou modèle utilisé. La cause du transport initial n'est pas
attribuée. Aucun verdict de capture ou direct industriel n'en découle.

Le [probe CUDA indépendant](../logs/foresight-runtime/gpu-compatibility-readonly-20261012-164023-ae80b5fe/qualification.json)
termine sans modèle ni ASR : CTranslate2 4.8.2 voit une carte et annonce notamment
`int8_float16`. Le garde couvre les événements Python, pas tous les appels
natifs des DLL. Un essai GPU distinct charge effectivement Whisper medium,
puis échoue au premier encode : `cublas64_12.dll` absente ou non chargeable.
Aucune transcription n'est produite. Il termine en 7,902 s, avec processus
sorti, Job vide, handles fermés et NVML fermé, selon le
[reçu d'échec](../logs/foresight-runtime/gpu-short-run-20261012-173342-f7bc6d33/qualification.json)
et son compagnon terminal. Le profil produit reste CPU/int8 ; dépendances,
qualité, débit et P95 visible restent à vérifier selon le
[protocole préparatoire](../.ui-preview/pilots/STT_GPU_QUALIFICATION_PROPOSAL.md).

## Candidat regroupé NEXT — non activé

Les propriétaires natifs enregistrés et les interruptions SQL restent visibles
hors Studio, avec le même filtrage des droits dans workspace/capabilities/séance.
Le client conserve les commandes natives sur erreur de lecture ou 404 masquant
une séance. Un STOP restant paused n'est pas confirmé ; les réponses malformées
ou tardives ne font pas disparaître le propriétaire. Une reprise interrompue
rejette durablement son UUID exact et conserve les fragments. La reprise avant
prise de propriété conserve l'ouverture explicite avec admission CPU. Le commit
propriétaire se fait hors registre ; une panne SQL retire uniquement sa réservation
sans ouvrir de périphérique. Le cycle SQL/registre pendant sauvegarde est retiré.

Le [ciblé backend final](../.ui-preview/pilots/native-interruption-next-20261012/qa/native-targeted-v4-8cb9e571/qualification.json)
passe 70/70 avec revue indépendante ; le
[frontend complet](../.ui-preview/pilots/native-interruption-next-20261012/qa/frontend-global-next-v1/qualification.json)
passe 858/858, TypeScript/build, sur 221 sources/configurations inchangées.
La régression complète Python V1 termine à 18:29:42 UTC sur 378 sources/57
ressources inchangées : **2 330 réussis, 2 échecs et 2 ignorés**, sortie 1.
Les échecs concernent l'export avec changement de droits et la garde propriétaire
natif dans cette passe historique. Les deux fixtures sont corrigées,
avec 73 tests ciblés réussis et revue indépendante, sans modifier le produit.
La V2 complète, lancée à 18:46:51 UTC, termine à **19:24:29 UTC : 2 332 réussis/2
ignorés**, soit 2 334 cas, zéro échec/erreur, sortie 0 et **378 sources Python/57
ressources inchangées**. Le [global V2](../.ui-preview/pilots/native-interruption-next-20261012/qa/python-global-next-v2/qualification.json)
et son [compagnon terminal](../.ui-preview/pilots/native-interruption-next-20261012/qa/python-global-next-v2/root-terminal-companion.json)
conservent le verdict ; le [Ruff global V2](../.ui-preview/pilots/native-interruption-next-20261012/qa/ruff-final-20261012-192805-8cc955c5/qualification.json)
termine sortie 0 sur les mêmes 378 sources. Le correctif responsive externe
passe séparément 858 tests/TypeScript/build ; sa vérification navigateur reste
ouverte. NEXT n'est pas activé, et ces preuves ne clôturent ni T12, ni T13, ni L12.
La preuve d'une heure reste celle de
la copie STT scellée, sans ASR ni matériel : elle ne qualifie pas une heure des
nouvelles interruptions natives. Les 26 fichiers de promotion V2 sont recensés.

La [porte opérationnelle datée](../logs/foresight-runtime/promotion-operational-ro-20261012-174847-563b7cd0/qualification.json)
observe une analyse de jalons active et huit queued, avec quatre opt-ins vrais.
Les deux bases sont attestées par leurs propriétaires Windows ; stockage et
activité utilisateur restent à confirmer. Aucune permutation canonique n'est
effectuée. L'utilisateur autorise les deux bibliothèques NVIDIA en dossier privé
et un seul nouvel essai GPU fictif de cinq minutes ; aucun microphone n'est autorisé.

L'essai V5 autorisé est terminé en 22,042 s, avec fermeture complète des processus,
Job, handles et NVML. Douze phrases propres SAPI sont transcrites en CUDA ; 27/27
informations critiques, garde numérique et revue des textes complets passent.
Les fenêtres courtes restent incomplètes sur la section mm² et ne sont pas
publiables comme faits métier. Le contrôle d'origine d'une DLL chargée échoue,
sans nom/chemin sauvegardés ; le
[verdict terminal reste false](../logs/foresight-runtime/gpu-short-run-20261012-181408-3771563f/qualification.json).
L'accord unique est consommé. Aucun réglage de production n'a changé et aucun
autre modèle n'est chargé pour le diagnostic statique.

## Séances progressives et capture Windows — 11 octobre 2026

Le parcours historique d'import/transcription/relecture/publication est conservé.
Le Studio ajoute une séance durable, indépendante d'un projet jusqu'à son
attribution, avec notes, segments corrigibles, questions sourcées et export ZIP.
Les détails de lot et les preuves sont dans [38_FORESIGHT_DELIVERY.md](38_FORESIGHT_DELIVERY.md).

### Export de revue et droits actuels — 12 octobre 2026

L'export ZIP conserve notes, versions historiques, segments et fichiers avec
leurs empreintes. Pour un opérateur restreint, les événements de réponse ou
de proposition ne conservent leur contenu que si leurs sources, connaissances
et références de séance restent autorisées. Une citation directe de note doit
appartenir à la note liée à cette séance ; une ancienne version de cette note
reste exportable. Une Source publiée d'une autre séance peut rester visible
si ses droits d'origine et actuels le permettent. Les payloads inconnus ou
non autorisés deviennent des enveloppes marquées `redacted`, sans contenu.
Les événements originaux en base ne sont pas modifiés ; l'archive d'un
opérateur sans restriction conserve le format intégral historique.

Les droits et rattachements sont relus avant le manifeste et après fermeture
du ZIP. Une révocation détectée refuse le retour du fichier. Les candidats
privés et les preuves restent conservés ; aucune suppression n'est effectuée.
Le correctif passe 57 tests isolés de staging et une revue indépendante.
Sur le produit appliqué, 99 tests d'export, séances, reprise et versions passent
sans plugin de staging, avec Ruff ; les groupes se recouvrent et ne s'ajoutent
pas. La régression complète et la livraison restent des preuves distinctes.

La capture navigateur conserve chaque fragment dans IndexedDB avant envoi.
L'acquittement contrôle séance, piste, séquence, SHA-256 et taille. Les onglets
utilisent un verrou ; une actualisation récupère le tampon et annonce une
interruption sans rouvrir le microphone. Les entêtes du conteneur sont conservées
pour la consolidation. Les pistes brutes mic/système restent séparées ; le mix
est dérivé. Navigation et changement d'onglet ne détruisent pas la capture.

Le helper WASAPI Windows fournit le loopback de la sortie réellement choisie et
un microphone choisi explicitement. Il écrit fichier/journal avec fsync avant
transmission, draine avant pause/arrêt et appartient au processus Agent avec
`KILL_ON_JOB_CLOSE`. Le reçu HTTP d'arrêt et la finalisation sont rejouables.
La recette Realtek a utilisé une voix fictive sur la sortie système, sans ouvrir
le micro. Les essais microphone/casque/réunion réelle restent distincts.

Le worker STT local utilise des fragments PCM et un contexte contigu borné ;
les pauses ne sont pas effacées. Une correction humaine et sa révision priment
sur le rejeu du moteur. Le texte direct est provisoire jusqu'à relecture ;
traitement terminé ne signifie pas contenu validé. Un speaker est une piste ou
une étiquette technique, jamais une personne déduite automatiquement.

Installer avec `scripts/setup_audio_runtime.ps1`. Readiness, modèle, chargement,
essai réel et performance sont affichés séparément. Les mesures froid/chaud,
erreurs sur valeurs/unités et limites industrielles sont conservées dans le
registre de recette. Les tests de conservation 60/120 min utilisent des WAV
synthétiques et ne démontrent pas une capture matérielle de deux heures.

## Arbitrage CPU entre capture directe et transcription complète

Le coordinateur du serveur Agent refuse le démarrage simultané du batch audio
historique et d'une capture directe. Une séance en enregistrement, en pause ou
en finalisation, ainsi qu'un propriétaire natif encore présent, réserve la voie
directe. Une nouvelle demande de transcription complète reçoit une erreur
explicite ; l'original est conservé et l'utilisateur peut la relancer après
l'arrêt de la capture. Un batch déjà en file reste `queued` avec un motif visible
et reprend lorsque la ressource se libère, sans calcul ni boucle d'attente active.

Réciproquement, un batch en cours refuse immédiatement les commandes de démarrage
ou de reprise navigateur/native avec HTTP **409**. L'utilisateur peut terminer
ou annuler ce batch avant de démarrer la capture. Les fragments directs déjà
durables restent en attente lorsqu'un batch possède le moteur. Le verrou protège
l'admission et le changement d'état, puis est libéré avant le calcul : aucune
capture n'attend derrière une réservation de quatre heures. Un calcul déjà lancé
n'est pas préempté. Cette coordination couvre le processus Agent et les états
canoniques de ses travaux ; elle ne surveille pas les autres applications du PC.

Sous Windows, le sous-processus du batch historique est attaché à un Job Object
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` par le helper partagé avec les autres moteurs
audio. Il meurt si le processus parent Agent disparaît. Le handle est fermé dans
`finally` sur succès, annulation
ou erreur ; si l'attachement échoue, l'enfant est terminé, puis tué si nécessaire,
et aucun résultat n'est accepté. Le moteur Whisper/diarisation existant est conservé.

Le raccordement legacy est vérifié par **5 tests de cycle de vie avec processus
et handles simulés** : succès, refus d'isolation avec arrêt forcé, annulation,
événement JSON invalide et sortie en échec. Ils contrôlent fermeture du handle,
fin du processus et conservation exacte du fichier original. Cette preuve ne
constitue pas un essai de crash matériel du batch : la protection au décès du
parent repose sur le mécanisme Windows utilisé par le helper.

## Priorités IA et budget du proactif

Le proactif reste une option explicite, désactivée par défaut. Le worker examine
au plus 20 séances et leurs 12 segments récents, avec une seule question par
passage et une attente de 8 secondes entre passages. Une réservation durable
par segment/révision empêche les doublons après reprise ; un échec reste visible
et nécessite une question explicite ou une révision du segment pour réessayer.
Il ne modifie pas automatiquement les notes.

Les demandes en attente d'un même moteur sont ordonnées ainsi : question
explicite, appel manuel, synthèse, proactif, complément, traitement de fond.
Les demandes déjà démarrées continuent. L'admission d'une tentative proactive
dispose de **2 secondes**, partagées entre l'attente de l'activité de fond et la
file du moteur ; l'arrêt du worker annule cette attente avant démarrage.
Ce budget ne comprend pas la recherche du contexte et ne garantit pas une réponse
en deux secondes. La file du moteur est bornée à 32 demandes en attente.

Chaque tentative HTTP de génération proactive utilise un timeout de **45 secondes**.
Un appel HTTP en cours n'est pas préemptible ; son timeout ne garantit pas l'arrêt
du calcul côté fournisseur. Une nouvelle tentative sur réponse vide ou un repli
de transport peut allonger la durée totale au-delà de 45 secondes. L'arrêt empêche
les admissions suivantes ; il ne coupe pas une requête déjà partie. La synthèse
legacy conserve également son annulation entre appels LLM.

## Parcours

Dans **Projets → projet → Revues → Réunion audio** :

1. Importer un fichier ou enregistrer au microphone. Renseigner titre, date,
   et éventuellement le nombre d’interlocuteurs (0 = détection automatique).
   Le projet ERP doit être explicitement relié au projet Brain dans Connaissance.
2. Cliquer **Transcrire et séparer les voix**. Le traitement en arrière-plan
   affiche sa phase et sa progression ; la page peut être fermée puis rouverte.
3. Relire les interventions chronologiques : horodatage, interlocuteur et texte.
   Les voix portent des étiquettes, pas des identités reconnues automatiquement.
   Renseigner les noms, réaffecter les interventions et corriger le texte.
   Les boutons d’horodatage permettent d’écouter le passage original.
4. **Enregistrer les corrections** conserve une relecture inachevée.
   **Valider la transcription** enregistre une version sourcée dans la mémoire
   evidence et autorise la synthèse. Les versions antérieures sont conservées,
   marquées comme remplacées, et exclues de l’indexation active.
5. **Générer la synthèse LLM** utilise les réglages IA du cœur Brain. Le brouillon
   contient synthèse, décisions, actions avec pilote/échéance et points ouverts.
   Chaque élément structuré cite un segment vérifiable ; les citations absentes
   sont rejetées et leur nombre est affiché. Responsable/date non explicites
   restent vides. Une relecture humaine reste nécessaire, notamment pour les
   noms, chiffres techniques, voix qui se recouvrent et formulation des décisions.
6. Corriger le brouillon, écarter des éléments, puis **Valider et enregistrer le
   compte rendu**. Le CR apparaît dans Revues ; ses informations validées rejoignent
   la mémoire truth du même projet, avec provenance vers l’audio et la transcription.
   Les actions sont convertibles en tâches par les boutons existants, sans création
   automatique de tâches. Le CR publié et sa transcription sont ensuite figés.

Modifier une transcription annule sa validation et rend son ancienne synthèse
obsolète. Une synthèse obsolète ne peut pas être publiée. L’annulation préserve
l’audio et la transcription ; une interruption/erreur nécessite une relance explicite.
La transcription est relancée depuis le début, la synthèse depuis le texte validé.
Les corrections de brouillon sont enregistrées lors de la publication ; les corrections
de transcription disposent de leur propre bouton d’enregistrement.

## Moteurs locaux et installation Windows

- Faster-Whisper **1.2.1**, modèle multilingue `small`, français, CPU INT8, 4 threads.
- Sherpa-ONNX **1.12.35** : segmentation Pyannote 3.0 INT8 et empreintes de voix
  WeSpeaker ResNet34. Les modèles publics sont téléchargés depuis les distributions
  officielles ; aucun compte Hugging Face n’est nécessaire à ce parcours.
- PyAV **16.1.0**, épinglé pour la compatibilité avec Faster-Whisper 1.2.1.

Les dépendances audio sont isolées du serveur dans `.venv-speech`. Elles sont
optionnelles : sans elles, les réunions manuelles et le reste d’Agent fonctionnent.

```powershell
python -m venv .venv-speech
.venv-speech\Scripts\python.exe -m pip install -r requirements-audio.txt
.venv-speech\Scripts\python.exe scripts\setup_meeting_audio.py
```

Les modèles sont stockés sous `.models/audio` et exclus de Git. Le manifeste
`models.json` référence les chemins locaux et les empreintes des modèles ONNX.
Le script peut être relancé sans retélécharger les fichiers ONNX déjà présents.
`--model base|small|medium` choisit le modèle Whisper lors de l’installation.
L’exécution de la transcription utilise exclusivement les modèles locaux et
désactive les téléchargements Hugging Face. L’audio n’est pas envoyé à un service
de transcription. La synthèse utilise le fournisseur LLM configuré dans Agent.

Pour un runtime installé ailleurs :

```powershell
$env:PB_SPEECH_PYTHON = 'C:\chemin\runtime\Scripts\python.exe'
$env:PB_SPEECH_MODELS_DIR = 'C:\chemin\modeles-audio'
```

Limites : **50 MiB par fichier et 120 minutes** ; WAV, MP3, M4A, MP4, OGG, OPUS,
WebM, FLAC, AAC, WMA. Pour les réunions longues, utiliser un format compressé ou
plusieurs parties. Le microphone utilise MediaRecorder et l’autorisation du navigateur.
La durée de traitement dépend du matériel, du bruit et de la longueur du fichier.

## API et persistance

| Route `/api/v1` | Rôle |
|---|---|
| `GET /meeting-audio/status` | Disponibilité du runtime local |
| `GET/POST /projects/{pid}/recordings` | Liste / import audio |
| `GET /projects/{pid}/recordings/{rid}` | État, transcription, noms et brouillon |
| `GET /projects/{pid}/recordings/{rid}/audio` | Lecture de l’original |
| `POST …/{rid}/transcribe` | Mise en file transcription + séparation des voix |
| `PUT …/{rid}/transcript` | Corrections, révision attendue, `validate: true` pour validation |
| `POST …/{rid}/synthesize` | Mise en file synthèse, après validation du texte |
| `POST …/{rid}/cancel` | Demande d’arrêt ; LLM arrêté entre appels |
| `POST …/{rid}/publish` | Publication explicite, révision + synthèse corrigée |

`meeting_recordings` est dans `project_brain.db`, avec FK projet/source ; audio
original dans `PB_STORAGE_DIR/raw`, compte rendu et actions dans l’ERP existant.
Une seule file audio traite les travaux en arrière-plan ; aucun port supplémentaire.
Le sous-processus audio communique sa progression par JSON ; il peut être arrêté
pendant un calcul. La synthèse traite toutes les parties des transcriptions longues,
puis consolide leurs résumés sans tronquer la fin de la réunion.
Les paramètres `reasoning_effort: none` et `enable_thinking: false` sont conservés.

La publication fige le brouillon avant d’écrire le CR ERP, puis les informations
Brain. Les identifiants déterministes rendent une reprise après arrêt entre les
deux commits idempotente : aucune duplication de CR, d’action ou de connaissance.
Les erreurs d’indexation ne suppriment pas les données ; la file de projections
existante permet leur reprise. Aucun envoi de mail automatique.

Les sauvegardes globales et archives projet conservent audio, interventions,
révisions, CR et états de traitement. Une restauration ne relance pas les travaux
en cours automatiquement. Les modèles et le runtime sont réinstallables et ne
font pas partie des données métier à sauvegarder.

## Vérification

```powershell
python -m pytest tests/test_meeting_audio.py tests/test_meeting_audio_lifecycle.py tests/test_audio_cpu_arbitration.py tests/test_proactive_admission.py -q
ruff check app backend/app tests scripts/setup_meeting_audio.py scripts/transcribe_meeting.py
cd web
npm test
npm run build
```

Les tests isolent les bases et simulent les appels audio/LLM pour vérifier les
phases, révisions, annulations, échecs, citations, publications et reprises.
Le lot final batch/cycle de vie/arbitrage du 11 octobre a passé **24 tests** ;
les **4 tests** d'admission proactive vérifient séparément délai, retrait de la
file et annulation avant démarrage. Ces résultats ciblés ne remplacent pas le
bilan de la suite globale du dépôt.
Un essai audio réel utilise une réunion fictive avec deux voix Windows ; aucune
donnée utilisateur n’est nécessaire aux tests.

Validation de cette livraison : **114 tests Python réussis, 1 ignoré ; 27 tests
React réussis ; Ruff, TypeScript et compilation Vite réussis**. Essai complet dans
deux bases temporaires sur :18004 : transcription réelle, correction des noms/texte,
synthèse avec le LLM configuré (`google/gemma-4-26b-a4b-qat`), citations vérifiées,
publication du CR et de ses deux actions. Aucun enregistrement fictif n’est ajouté
aux bases de production.

Activation locale le 2 octobre 2026 : arrêt de l’analyse des mails demandé par
l’utilisateur, sauvegarde globale hors ligne vérifiée (empreintes et intégrité
des deux bases), puis redémarrage sur :8001. Les deux projets existants sont
conservés ; les contrôles de santé Brain/ERP et du runtime audio sont positifs.
Les classements de mails déjà enregistrés restent conservés. Cette version est
lancée depuis le worktree ; les changements restent locaux, sans commit ni push.
Le démarrage Windows habituel utilise encore le checkout principal `C:\Agent` :
l’intégration dans ce checkout sera nécessaire pour conserver cette version
après un redémarrage du poste.

Références : [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper),
[Sherpa-ONNX](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html).

## Navigation dans le nouvel espace de travail

Les Réunions sont accessibles globalement, avec projet explicitement choisi,
ou par `/app/projects/{id}/reviews`. Le panneau audio reste monté lors du
changement de rubrique et de sous-onglet. Un bandeau global signale le microphone
actif et permet de revenir à la réunion. Le navigateur protège les fichiers
non importés et les corrections en cours avant fermeture ou rechargement.
Ces brouillons restent en mémoire jusqu’à enregistrement ; ils ne constituent
pas une sauvegarde incrémentale de l’audio. Le direct local est étudié dans
[25_REALTIME_VOICE](25_REALTIME_VOICE.md) ; la voie cloud payante est écartée.

## Qualification des modèles locaux et état du direct industriel — 11 octobre 2026

**Le direct industriel L03 reste NO-GO.** La capture et le traitement local
fonctionnent dans les parcours qualifiés, mais aucun modèle essayé ne satisfait
simultanément la restitution des valeurs critiques et la cible provisoire de
5 secondes sur les fragments directs. Le texte direct est provisoire : toute
valeur, unité, date ou négation utilisée dans un CR doit être vérifiée. Le profil
actif par défaut reste `small`, CPU `int8`, quatre threads ; les installations
`medium` et `large-v3-turbo` conservent leurs répertoires séparés.

### Qualité et latence mesurées

Le corpus comparable comprend **12 phrases fictives françaises**, prononcées
par une seule voix SAPI Microsoft Hortense, avec **27 champs critiques** déclarés
(nombres, unités, dates, codes et négations). Les trois modèles traitent les
mêmes fichiers WAV, vérifiés par SHA-256. Le WER pondéré ci-dessous normalise
les accents, la ponctuation, les nombres écrits et les équivalences de symboles
d'unités explicitement déclarées. Les champs critiques sont contrôlés par les
motifs enregistrés dans le rapport ; ce contrôle reste une recette de corpus,
sans validation sémantique générale ni preuve sur une réunion industrielle réelle.

| Modèle réellement chargé | WER sur les 12 phrases complètes | Champs critiques corrects | Requête préchauffée sur une fenêtre de 5 s, CPU4 | Somme RSS maximale échantillonnée |
|---|---:|---:|---:|---:|
| `small` | 5,43 % | 25/27 | 2,30–2,69 s | 584,2 MiB |
| `medium` | 2,17 % | 27/27 | 6,08–6,51 s | 1 265,6 MiB |
| `large-v3-turbo` | 1,63 % | 27/27 | 9,67–11,14 s | 1 260,4 MiB |

Chaque intervalle de latence porte sur **trois requêtes de la même fenêtre**,
après chargement du modèle. Il ne constitue ni un P95 représentatif, ni un délai
d'affichage navigateur. La somme RSS observe le lanceur et ses descendants
Python toutes les 200 ms ; des pages partagées peuvent être comptées plusieurs
fois. Il s'agit d'une mesure d'inférence courte, sans qualification de la mémoire
sur deux heures de capture matérielle. L'utilisation CPU moyenne correspond
respectivement à environ 3,83, 3,86 et 3,92 cœurs pendant ces requêtes.

`small` a notamment transcrit **1 250 W en 2 250 W** et **« hors taxes » en
« au Ortax »** sur les phrases complètes. Sur les trois fenêtres courtes,
il a rendu une section de câble de **2,5 mm²** sous la forme **« 2,5 mètres »**.
Les modèles plus grands ont rendu `2,5 mm` sur le premier fragment, le carré
arrivant sur le fragment suivant. Réussir 27/27 sur une phrase complète ne
garantit donc pas la valeur utilisable pendant sa transcription fragmentée.

Le worker réel a été exécuté avec deux fragments dans une base isolée :

| Modèle | Premier fragment, démarrage à froid jusqu'à événement durable | Deuxième fragment, modèle chargé jusqu'à événement durable |
|---|---:|---:|
| `small` | 6,47 s | 3,30 s |
| `medium` | 15,37 s | 8,62 s |
| `large-v3-turbo` | 13,31 s | 7,64 s |

Ces deux observations par modèle prouvent le parcours `pending` → transcription
persistée, les timecodes dans l'audio d'origine et la conservation d'une
correction humaine lors d'une reprise réelle. Elles ne mesurent pas la réception
SSE et l'affichage dans le navigateur. Les P50/P95 `compute_s` des rapports de
corpus couvrent des populations différentes : 27 cas pour `small` (12 industriels,
12 de référence et 3 dégradés), 15 pour chaque grand modèle (12 industriels et
3 dégradés). Ils ne doivent pas être comparés comme une latence directe homogène.

Les conditions supplémentaires restent synthétiques : bruit blanc à SNR 12 dB,
rééchantillonnage téléphonique à 8 kHz et chevauchement de deux phrases de la
même voix avec un décalage de 200 ms. Sur ce chevauchement, le WER atteint
65,38 % pour `medium` et 46,15 % pour `large-v3-turbo`. Aucun résultat ne qualifie
la diarisation de plusieurs personnes, une réunion Teams réelle, la visibilité
du texte en direct ou une capture matérielle de 120 minutes.

Le passage à huit threads a été essayé sur les mêmes trois fenêtres préchauffées :
`medium` prend 8,54–8,97 s et `large-v3-turbo` 10,92–13,02 s. Il est plus lent
que quatre threads dans cette recette. Le préchauffage retire le chargement
initial ; il ne ramène pas ces deux modèles sous la cible de 5 s. Aucun essai
GPU ni déchargement d'un modèle LM Studio n'a été effectué pour cette qualification.

### Choisir explicitement `medium` et lier la qualification au profil

Le choix `medium` est un candidat pour la consolidation de phrases complètes,
avec contrôle humain des valeurs. Il n'est pas activé automatiquement. Le script
ci-dessous installe les dépendances dans `.venv-speech` et le modèle dans
`.models/audio-medium`, puis produit un rapport distinct sur le WAV fictif local.
Cette procédure est documentée pour une exécution volontaire ; elle n'a pas été
relancée lors de la rédaction de cette section.

```powershell
Set-Location C:\Agent
.\scripts\setup_audio_runtime.ps1 -Model medium
$env:PB_SPEECH_MODELS_DIR = 'C:\Agent\.models\audio-medium'
$env:PB_SPEECH_THREADS = '4'
$env:PB_SPEECH_QUALIFICATION_REPORT = 'C:\Agent\logs\foresight-runtime\audio-qualification-medium.json'
python scripts\qualify_live_speech.py logs\foresight-runtime\qualification\reunion-fictive.wav --report logs\foresight-runtime\audio-qualification-medium.json
```

Le WAV de cette commande appartient aux preuves locales de qualification.
Un clone du dépôt doit disposer de ce fichier fictif, ou fournir un autre WAV
fictif français adapté aux cinq mots contrôlés par le script : `alpha`,
`éclairage`, `devis`, `matériel`, `lundi`. Ce test valide un fonctionnement réel
minimal (au moins quatre mots présents), sans valider la qualité industrielle.
Pour reproduire le corpus critique existant, avec un nouveau rapport et sans
écraser les observations précédentes :

```powershell
python scripts\qualify_speech_corpus.py --industrial-manifest logs\foresight-runtime\speech-corpus-6d9f47530a5e429ebe63a2c4ade9a9e7\industrial-phrases.json --models .models\audio-medium --threads 4 --report logs\foresight-runtime\speech-corpus-medium-new.json
```

Le `qualification_profile` est enregistré sous les champs JSON
`runtime_profile` et `runtime_profile_key`. Sa clé SHA-256 couvre le runtime
Faster-Whisper 1.2.1, le modèle et son chemin, CPU `int8`, le nombre de threads,
le français, `beam_size=1`, les timecodes de mots, la VAD et son silence minimal
de 250 ms, le contexte PCM de 500 ms, les seuils et la révision du contrat.
Le rapport contient aussi le SHA-256 du binaire et son identité
(taille, date de modification et SHA-256 de `models.json`). Changer le modèle,
le fichier, son répertoire ou les paramètres exige une nouvelle qualification
compatible ; un rapport réussi pour `small` ne rend pas `medium` prêt.

`installed` décrit les dépendances et fichiers disponibles, `loaded` un résident
effectivement chargé avec le profil courant, et `ready`/`real_test_passed` un
essai réel compatible avec le profil et l'identité actuels. Les indicateurs
`qualified_live_latency` et `industrial_quality_qualified` restent **false**.
La disponibilité du runtime ne lève donc pas le NO-GO industriel.

Les variables ci-dessus ne configurent que le processus et ses descendants.
Pour un choix durable, elles doivent être transmises au processus Agent lors
d'un redémarrage maîtrisé, après arrêt des captures et traitements audio en cours.
`PB_SPEECH_MODELS_DIR` concerne le résident direct et le moteur batch existant ;
ce n'est pas un sélecteur par réunion. Les enregistrements déjà traités ne sont
pas retranscrits automatiquement. Le batch historique utilise `beam_size=5`,
alors que les mesures comparatives ci-dessus utilisent le résident à
`beam_size=1` : il faut vérifier son résultat et sa latence dans le parcours batch
réel avant de déclarer cette consolidation qualifiée.

### Preuves locales conservées

Les rapports JSON conservent audio, références, transcriptions, empreintes,
contrôles critiques, timecodes et erreurs. Ils sont locaux et ne remplacent pas
des fichiers distribués avec le dépôt :

- [Corpus `small`](../logs/foresight-runtime/speech-corpus-qualification.json),
  [corpus `medium`](../logs/foresight-runtime/speech-corpus-medium.json) et
  [corpus `large-v3-turbo`](../logs/foresight-runtime/speech-corpus-turbo.json).
- [Fenêtres préchauffées et ressources CPU4](../logs/foresight-runtime/speech-resource-qualification.json)
  et [essais CPU8](../logs/foresight-runtime/speech-resource-threads8.json).
- [Essai de fonctionnement du profil `small`](../logs/foresight-runtime/audio-qualification.json).

Les SHA-256 des binaires réellement testés sont :

| Modèle | SHA-256 du `model.bin` |
|---|---|
| `small` | `3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671` |
| `medium` | `9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae` |
| `large-v3-turbo` | `e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da` |

Les premières mesures de ressources qui ne suivaient que le lanceur du venv
sont marquées invalides et remplacées par l'observation de son arbre de processus.
Le premier essai destiné à `medium` avait sélectionné `small` : il est conservé
sous `speech-corpus-misselected-small.json` et exclu du bilan `medium`.
Les rapports bruts antérieurs à la normalisation des unités restent conservés.

### Dernier essai isolé : `small` avec `beam_size=5`

Le harnais `scripts/qualify_speech_beam.py` a repris les mêmes 12 WAV normalisés,
avec les références et empreintes vérifiées, CPU `int8`, quatre threads et un
seul worker. Il réutilise le découpage, la VAD et les timecodes de
`transcribe_live.transcribe` ; seul `beam_size` passe de 1 à 5 dans un proxy
interne au processus de qualification. Aucun défaut du runtime Agent, variable
persistante ou enregistrement métier n'est changé.

Le WER des phrases complètes descend à **3,80 %**, avec **24/27 contrôles par
motifs**. Les rejets détaillés sont `16 Ampires` (nombre conservé, unité mal
orthographiée), `2250W` pour la référence **1 250 W** (erreur de valeur), et
`hors-tax` (variante lexicale non admise par le motif `hors taxe(s)`). Ces trois
rejets n'ont donc pas la même portée sémantique. La puissance incorrecte reste
une erreur critique, même si les variantes lexicales étaient normalisées.

Les trois fenêtres préchauffées de cinq secondes prennent **2,88 s, 2,49 s et
2,88 s**, mais rendent toutes encore **« câble de 2,5 mètres »**. Le test conserve
le texte du fragment comme provisoire ; une unité non encore terminée dans la
fenêtre ne doit pas être déduite. Toutes les températures des segments complets
et courts sont `0.0` : ces observations ne résultent pas du fallback de sampling
qui repasse à `beam_size=1` à température positive. Le rapport reste
`microrecipe_passed=false` et `industrial_direct_qualified=false`.

Le profil expérimental distinct a pour SHA-256
`b57fbd53eadbea35eef18fcb43cf54964b3c1f87c2e296f425b56d63fc09e821`.
L'enfant utilise Faster-Whisper 1.2.1 et CTranslate2 4.8.2, un modèle déjà installé
et `local_files_only=True`. La garde de connexions Python refuse effectivement
la connexion de contrôle TEST-NET ; elle ne prouve pas un blocage réseau au niveau
du système d'exploitation. Le Job Object Windows ferme l'enfant à la sortie du
parent et le délai total de calcul est borné à 600 secondes.

[Rapport de cet essai](../logs/foresight-runtime/small-beam5-qualification.json).
Le harnais refuse d'écraser un rapport existant : une reproduction doit choisir
un nouveau nom, par exemple :

```powershell
python scripts\qualify_speech_beam.py --models .models\audio --beam-size 5 --threads 4 --timeout 600 --report logs\foresight-runtime\small-beam5-reproduction.json
```

Ce dernier essai confirme le **NO-GO du direct industriel** sur cette recette.
Il ne déclenche aucun remplacement du profil actif.

## Test matériel autorisé du microphone Realtek — 11 octobre 2026

L'utilisateur a autorisé une fenêtre de 30 secondes sur
**« Réseau de microphones (2- Realtek Audio) »**, conservée uniquement sur ce PC
dans les preuves locales de qualification. L'inventaire WASAPI identifie ce même
périphérique sous le libellé du pilote **« Réseau de microphones (2- Realtek(R)
Audio) »**, index **9**, deux canaux, 48 kHz, sans loopback. Seul le marqueur
commercial `(R)` est retiré pour comparer les libellés. L'identité est vérifiée
avant l'ouverture ; aucun casque ou autre microphone n'est essayé.

Le premier processus, dans le contexte Windows restreint, échoue avant ouverture
avec `OSError -9996: Invalid device` : zéro trame et aucun WAV sonore. Les formats
PCM16 à 48 kHz sont pourtant reconnus en mono et stéréo, et les réglages Windows
microphone et `NonPackaged` sont lus à `Allow`. Une unique reprise autorisée dans
le contexte normal du poste (`restricted_process_token=false`, session Windows 1)
ouvre effectivement le périphérique. Aucun réglage de confidentialité, clé de
registre ou périphérique par défaut n'est modifié.

**Le résultat reste partiel : 25,000 secondes durables, pas 30 secondes.**
L'ouverture a pris 13,134 secondes. Le contrôleur initial utilisait un délai
global de 45 secondes qui incluait cette ouverture ; il a interrompu le processus
pendant le dernier fragment. Le démarrage du stream est enregistré à
`2026-10-11T17:25:23.633637Z` et la fin du parent à
`2026-10-11T17:25:53.664228Z`. Cet intervalle de 30,031 secondes comprend l'arrêt
forcé ; il ne constitue pas une preuve de 30 secondes d'audio sauvegardé.

Les cinq parties conservées sont des WAV **bruts PCM16 stéréo à 48 kHz**, chacune
de 5,000 secondes, 240 000 trames par canal et 960 044 octets avec son en-tête.
Elles totalisent **1 200 000 trames par canal**. Chaque fichier a été fermé,
`fsync` exécuté, puis son reçu local enregistré. Les cinq SHA-256 ont été
recalculés et correspondent aux reçus. Le signal n'est pas nul : les RMS par
canal et fragment sont compris entre 507 et 1 190 en unités PCM16, avec **zéro
échantillon écrêté**. Ces métriques ne qualifient ni le sens de l'ambiance, ni la
qualité de transcription, ni l'indépendance acoustique des deux canaux.

Le parent et son enfant sont confirmés terminés, et le Job Object fermé : aucune
capture ne reste dans les processus de ce test. L'arrêt a été imposé par le
contrôleur ; **la fermeture normale et le parcours complet de 30 secondes restent
non qualifiés**. Aucune pause/reprise n'y est testée.
Ce constat décrit la clôture du premier essai ; le test distinct ci-dessous
nécessite et reçoit ensuite une nouvelle autorisation humaine.
Les cinq reçus prouvent la récupération des fragments durables d'une capture
interrompue ; ce sont des reçus locaux du harnais, sans upload dans l'API Réunions.

Aucune écoute du contenu, transcription, recherche externe ou import de source
n'est effectué. Les bases ERP/Brain et l'activation proactive ne sont pas
sollicitées. Les WAV restent dans `logs/foresight-runtime/qualification`, exclu
de Git par la règle `logs/`, avec le
[rapport initial d'échec](../logs/foresight-runtime/qualification/microphone-real-30s-6a861f34/qualification.json),
le [rapport brut de capture partielle](../logs/foresight-runtime/qualification/microphone-real-30s-normal-471093bd/qualification.json)
et le [post-mortem avec empreintes et métriques](../logs/foresight-runtime/qualification/microphone-real-30s-normal-471093bd/postmortem.json).

Le harnais `scripts/qualify_microphone_30s.py` est corrigé pour un éventuel prochain
essai explicitement autorisé : ouverture bornée à 45 secondes, handshake `ready`
après ouverture du stream inactif, puis fenêtre active de **30 secondes depuis
START sur une horloge monotone, sans renouvellement au premier paquet**. Un
watchdog indépendant de l'écriture des WAV demande l'arrêt du stream à cette
frontière. Les **5 secondes de fermeture** servent au vidage des buffers déjà
acquis, au `fsync` et à la sortie de l'enfant. Les horodatages ADC coupent les
échantillons hors de la fenêtre autorisée ; le quota sauvegardé est plafonné à
1 440 000 trames par canal, sans padding. Les heures de demande et de fin d'arrêt
sont rapportées : un blocage du pilote reste un échec, avec terminaison bornée
par le contrôleur et son Job Object.

Un démarrage ou une livraison WASAPI tardive peut laisser moins de 30 secondes
durables : le rapport reste alors explicitement partiel, le worker termine avec
un code d'échec, et le harnais ne prolonge ni ne rouvre la capture. **Treize tests
à horloge simulée passent**, sans ouvrir de microphone, notamment premier paquet
tardif, fenêtre non renouvelable, vidage après arrêt d'un buffer acquis avant la
frontière, rejet après celle-ci et découpage des buffers aux deux bornes. La
compilation Python et Ruff passent. Ces tests ne remplacent pas une nouvelle
qualification matérielle autorisée ; aucune nouvelle capture n'est exécutée
pendant leur préparation. Aucun code du moteur natif de production n'est modifié
pour ce défaut propre au harnais.

### Nouvelle autorisation : arrêt normal dans la fenêtre, 29,900 secondes conservées

Une seconde autorisation humaine explicite permet au coordinateur de lancer
**une seule nouvelle fenêtre nominale de 30 secondes** sur ce même microphone
Realtek, index 9. L'audit ultérieur lit seulement les fichiers et les métadonnées
des processus ; il ne rouvre aucun périphérique, n'écoute pas le son et ne
réalise ni transcription, recherche externe, import ou accès ERP/Brain.

Le périphérique s'ouvre en 3,133 secondes dans la session Windows 1 normale.
START intervient le `2026-10-11T18:27:53.476514Z`. Le watchdog demande l'arrêt à
START + **30,000565 secondes**, et `stop_stream` se termine à + **30,002996
secondes**. Le stream est fermé à `18:28:23.644982Z`, puis PyAudio terminé et le
Job Object fermé ; le parent finit à `18:28:23.719319Z`, avant son délai de
fermeture. Une vérification indépendante trouve **zéro processus** de cette
capture. Contrairement à l'interruption forcée du premier test, **l'arrêt et la
fermeture normale à la frontière prévue sont ici vérifiés**.

Le quota exact d'audio reste cependant incomplet : **29,900 secondes**,
**1 435 200 trames par canal**, en six WAV PCM16 stéréo 48 kHz, cinq de
5,000 secondes et le dernier de 4,900 secondes. Les six fichiers totalisent
5 741 064 octets avec leurs en-têtes. Leurs SHA-256, tailles, en-têtes WAV,
nombres de trames et offsets contigus sont recalculés et correspondent au
rapport brut. Le RMS global est 83,238 et 83,238 unités PCM16 selon le canal,
les crêtes absolues sont 8 632 sur les deux canaux, et aucun échantillon n'est
écrêté. Ces mesures indiquent des données non nulles, sans interpréter l'ambiance
ni qualifier l'acoustique ou une future transcription.

Les 299 callbacks totalisent en moyenne 100 ms de PCM chacun ; il manque donc
4 800 trames par canal pour atteindre exactement 30 secondes. Le premier ADC
commence 56,194 ms après la borne START et le dernier se termine 43,141 ms avant
la borne finale. Le premier callback est reçu 136,288 ms après START. L'intervalle
entre les deux bornes ADC est 29,900664 secondes, cohérent avec les 29,900 secondes
de PCM à 0,664 ms près. Ces marges sont **compatibles avec un bloc de 100 ms
manquant à la fenêtre fixe**, mais ne prouvent pas sa cause. Les horodatages
individuels des callbacks ne sont pas conservés : l'absence de toute discontinuité
ADC interne ne peut donc pas être établie indépendamment.

Le rapport brut conserve `passed=false`, `partial_capture=true`, le code enfant
1 et son erreur de quota incomplet. **Le critère de 30,000 secondes de données
reste non acquis**, alors que l'arrêt normal est qualifié sur cet essai. Aucun
buffer n'est complété par du silence et la capture n'est ni prolongée ni rouverte.
Pause/reprise, loopback système, capture Teams, trajet API Réunions et durée
matérielle de deux heures ne sont pas mesurés par ce test.

[Rapport brut conservé](../logs/foresight-runtime/qualification/microphone-real-30s-second-authorized-20261011/qualification.json),
[audit indépendant des six fichiers et des bornes](../logs/foresight-runtime/qualification/microphone-real-30s-second-authorized-20261011/postmortem-verified-20261011.json),
[vérification des processus](../logs/foresight-runtime/qualification/microphone-real-30s-second-authorized-20261011/process-check-20261011.json).
L'empreinte du rapport brut reste
`ba81269d0e7a4e1841e799c64e82c54829680850c9cc69c649ba5fd81755ce1d`.

## Variante medium avec horodatages de segments — comparaison isolée

Une seule hypothèse supplémentaire est testée le 11 octobre 2026 : supprimer
l'alignement mot par mot (`word_timestamps=False`) pour mesurer son coût, tout
en conservant les horodatages de segments réellement produits par Whisper puis
restaurés par le VAD. Le modèle reste **medium CPU4 int8, beam_size=1** ; le VAD,
ses 250 ms de silence minimal, les seuils et l'absence de contexte précédent
restent identiques. Aucune référence, valeur attendue ou annotation n'est
transmise au décodeur, et aucune erreur de valeur n'est corrigée après génération.

Le protocole réutilise les **12 WAV fictifs scellés**, avec les mêmes SHA-256 que
la première recette. Leurs phrases complètes durent 4,050 à 7,384 secondes.
Après un échauffement par condition, exclu des mesures, les 12 paires sont
exécutées sur le même modèle résident, en alternant l'ordre A/B puis B/A.
Les options effectives du moteur sont comparées : seul `word_timestamps` change.
Ce protocole confronte des phrases complètes identiques ; il ne compare pas une
phrase complète à un fragment de cinq secondes.

| Mesure sur 12 phrases complètes | Mots, contrôle | Segments, variante |
|---|---:|---:|
| Champs critiques exacts | 27/27 | 27/27 |
| WER pondéré, règles existantes inchangées | 2,17 % | 2,17 % |
| Temps moyen de requête | 9,926 s | 8,978 s |
| P50 / P95 observés | 10,931 / 11,909 s | 10,091 / 10,586 s |
| Minimum / maximum observés | 7,326 / 11,953 s | 6,155 / 10,687 s |
| Requêtes sous 5 secondes | 0/12 | 0/12 |

Le gain moyen observé est **9,55 %**. L'instrumentation du moteur installé
explique cette limite : l'encodage prend encore environ **7,36 secondes** en
moyenne dans les deux conditions ; l'alignement des mots supprimé prend environ
**0,98 seconde**, le VAD **0,02 seconde**, et le décodage **1,55 seconde** dans la
variante. Le chemin installé applique `pad_or_trim` avant l'encodage. Supprimer
le VAD ou quelques millisecondes de contexte ne traiterait donc pas le coût
dominant constaté ; aucune seconde variante n'est essayée. L'arbre du worker
consomme en moyenne 3,90 cœurs pendant les 227,16 secondes d'inférence mesurées,
avec un pic RSS échantillonné de 1 338 486 784 octets. Ces valeurs décrivent
l'essai sur ce poste, sans garantie de performance future.

Tous les repères temporels conservés se trouvent dans les bornes de leur WAV.
La variante reprend directement `part.start`, `part.end` et `part.text`, sans
répartir artificiellement des mots sur toute la durée audio ni rabattre un
horodatage invalide sur une borne inventée. **La précision temporelle par rapport
à un alignement humain n'est pas évaluée.** Le chemin direct canonique consomme
actuellement `part.words` pour filtrer les 500 ms de chevauchement : changer
seulement le réglage lui ferait perdre ses lignes de transcription. La recette
expérimentale ne qualifie ni ce dédoublonnage, ni les fragments courts, ni le
parcours SSE ou une réunion industrielle réelle.

Le profil expérimental des segments est distinct, SHA-256
`d470cc45a48d1bcb11a9ad99cf9a6e52bb91ec46042fe26c62f18832810918bc`.
Les WAV et le code du harnais conservent les empreintes inscrites au rapport.
L'enfant est terminé et son Job Object fermé. Aucun microphone, GPU, pilote,
modèle LM Studio, profil actif ou base de production n'est modifié ou sollicité
pour cette comparaison. La garde de connexions Python est testée ; elle ne
constitue pas une coupure réseau physique du poste.

[Rapport A/B réel](../logs/foresight-runtime/medium-segments-paired-20261011-v2.json).
Une reproduction isolée exige un nouveau nom de rapport et reste bornée à
600 secondes :

```powershell
python scripts\qualify_speech_segments.py --models .models\audio-medium --baseline-report logs\foresight-runtime\speech-corpus-medium.json --report logs\foresight-runtime\medium-segments-paired-reproduction.json --timeout 600
```

Cinq tests sans modèle vérifient la préservation et le rejet des horodatages
invalides ; Ruff et la compilation Python passent. La qualité critique de ces
phrases complètes est conservée, mais cette variante ne permet pas d'atteindre
la cible de latence : **le NO-GO du direct industriel est maintenu**, sans
activation canonique ni nouveau benchmark.

### Essai isolé du mel court : compatible avec le moteur, variante rejetée

Une lecture du code primaire de **CTranslate2 4.8.2**, version installée,
établit que l'encodeur accepte un temps mel variable jusqu'au maximum de son
modèle. Le contrôle porte sur un dépassement du maximum et les positions sont
ajoutées sur la longueur effective, sans obligation d'égalité à 3000 :
[encodeur](https://github.com/OpenNMT/CTranslate2/blob/v4.8.2/src/layers/whisper.cc#L25-L48),
[contrat des dimensions](https://github.com/OpenNMT/CTranslate2/blob/v4.8.2/include/ctranslate2/layers/whisper.h#L19-L38),
[positions](https://github.com/OpenNMT/CTranslate2/blob/v4.8.2/src/layers/common.cc#L139-L159).
Faster-Whisper 1.2.1 remplit cependant ses fenêtres courtes à 3000 trames avant
encodage. La compatibilité de dimensions ne prouve pas la qualité du décodage.

Le harnais distinct `scripts/qualify_speech_mel.py` a comparé le contrôle au mel
court, en conservant **medium CPU4 int8, beam1, VAD et word_timestamps=True**.
Toutes les options effectives sont identiques. Seul le remplissage mel à 3000
change dans le processus enfant isolé : les trames utiles restent intégrales,
avec au maximum une trame nulle ajoutée pour le pas de convolution de deux.
Une entrée vide ou supérieure à 3000 est refusée sans troncature. Aucun package
installé, profil actif ou code de transcription canonique n'est modifié.

Le protocole prévu était de 12 paires sur les mêmes WAV scellés, ordre A/B puis
B/A alterné, après deux échauffements exclus des latences. **Il a été arrêté
après la première paire mesurée**, à la demande du coordinateur, car le résultat
falsifie déjà la cible de cinq secondes. La paire suivante commencée n'a aucun
résultat exploitable. Les valeurs ci-dessous concernent donc une seule phrase
complète de 7,261 secondes, et seulement **2 des 27 champs critiques prévus**.

**Contexte de charge :** la régression pytest globale à trois workers, lancée
le 11 octobre 2026 à 18:14:17 UTC, est restée active durant les deux conditions
de cet essai, selon le relevé du coordinateur. La paire partage ce fond de
charge, dont l'intensité instantanée peut varier. **Ses latences absolues ne
qualifient pas un PC au repos.** Le résultat défavorable s'appuie notamment sur
le repli de température, les répétitions du warmup et le décodage prolongé ; il
n'entraîne aucune activation ni nouvel essai.

| Première paire mesurée, hors échauffements | Contrôle mel3000 | Mel court |
|---|---:|---:|
| Temps de requête | 12,504 s | 79,862 s |
| Encodage | 9,658 s | 1,525 s |
| Décodage avec ses replis de température | 1,823 s | 77,870 s |
| Alignement des mots | 0,943 s | 0,418 s |
| Champs critiques, recalculés sur cette phrase | 2/2 | 2/2 |
| WER recalculé, normalisation existante inchangée | 0 % | 0 % |
| Température finale réellement employée | 0 | 1 |
| Pic RSS échantillonné, arbre des processus | 1 339 080 704 octets | 1 556 652 032 octets |
| CPU moyen, équivalent d'un cœur | 372,14 % | 286,68 % |

L'encodage diminue de **84,21 %**, mais la requête totale devient **6,39 fois
plus lente**. Les fenêtres mel courtes observées sont 673 vers 674 trames puis
57 vers 58 ; tous leurs contenus utiles sont préservés. Le warmup court prend
77,275 secondes et répète la phrase trois fois, avec un WER recalculé de 200 %.
Ces échauffements restent exclus du tableau des latences mesurées. Les repères
des 11 mots de la phrase mesurée sont ceux du moteur et restent dans les bornes
du WAV ; leur précision par rapport à un alignement humain n'est pas mesurée.

Le profil expérimental court est distinct :
`7a7ae7fc2561ff7df8e87aaa9a9b063d138e6f977b9d40c30eb9a4aa6bd6cf5f`.
Les empreintes du WAV, du harnais et de `transcribe_live.py` sont vérifiées après
l'arrêt. Le rapport brut partiel garde ses champs hérités de la recette de
référence : **ils ne constituent pas de nouveaux scores** ; le rapport de
décision contient les scores recalculés et le périmètre exact de cette paire.
Les enfants dédiés ont été arrêtés, le parent a fermé le Job Object dans son
`finally`, et une vérification indépendante trouve zéro processus du harnais.

Preuves conservées :
[rapport brut interrompu](../logs/foresight-runtime/medium-mel-paired-20261011.json),
[décision et scores recalculés](../logs/foresight-runtime/medium-mel-decision-20261011.json),
[demande d'arrêt ciblée](../logs/foresight-runtime/medium-mel-stop-request-20261011.json),
[absence des processus dédiés](../logs/foresight-runtime/medium-mel-process-check-20261011.json),
[contexte de concurrence](../logs/foresight-runtime/medium-mel-concurrency-context-20261011.json).
Quatorze tests sans modèle couvrent les limites, la conservation des trames et
le pas de convolution ; Ruff et la compilation Python passent. **Cette variante
est NO-GO** : pas de qualification supplémentaire des fenêtres de cinq secondes,
pas d'activation canonique, pas d'autre variante, GPU, microphone ou modèle
LM Studio sollicité. La garde réseau Python testée reste distincte d'une coupure
physique du réseau.

### Protocole casque Jabra : autorisation consommée

Ce protocole a été exécuté **une seule fois le 11 octobre 2026**, après
l'autorisation humaine « Autoriser le test Jabra de 30 secondes », confirmée
par `call_ce61f9db8765403ebbd19b33d7da29a3`, pour le microphone
**« Casque (Jabra Evolve 75) »**, avec conservation des WAV uniquement sur ce PC.
**Cette autorisation est consommée : aucune nouvelle capture n'est autorisée.**
Le résultat séparé ci-dessous garde la distinction entre ouverture/arrêt du
périphérique et quota de données complet. Une nouvelle exécution des commandes
requiert une nouvelle autorisation humaine.

Le relevé `completion-runtime-qualification-v2.json` identifie ce microphone
WASAPI à l'index **15**, 48 kHz, deux canaux d'entrée. La sortie Jabra est à
l'index 13 et son loopback à 17. **Ces indices sont un relevé historique, pas des
identifiants stables.** Avant l'ouverture autorisée, un inventaire neuf doit
sélectionner exactement le libellé Jabra, avec entrée disponible et
`isLoopbackDevice=false`, puis vérifier l'unicité et la session Windows
interactive. La sortie et le loopback ne font pas partie de ce test. En cas
d'absence, d'ambiguïté ou de changement de format, arrêter la préparation sans
essayer un autre microphone ni modifier les réglages Windows.

Commandes préparées pour revue, **à exécuter seulement après cette nouvelle
autorisation** depuis `C:\Agent`. L'inventaire n'ouvre pas de stream. Le
répertoire de capture reste neuf ; le harnais refuse un répertoire existant.

```powershell
$jabraStamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$jabraPython = 'C:\Agent\.venv-speech\Scripts\python.exe'
$jabraInventoryFile = "C:\Agent\logs\foresight-runtime\qualification\headset-jabra-inventory-$jabraStamp.json"
$jabraDirectory = "C:\Agent\logs\foresight-runtime\qualification\headset-jabra-30s-$jabraStamp"
if ((Test-Path -LiteralPath $jabraInventoryFile) -or (Test-Path -LiteralPath $jabraDirectory)) { throw 'Dossier/preuve déjà présent : ne pas réutiliser.' }
$jabraInventoryText = & $jabraPython C:\Agent\scripts\native_audio_capture.py --inventory
if ($LASTEXITCODE -ne 0) { throw 'Inventaire WASAPI impossible : aucune ouverture.' }
$jabraInventoryText | Set-Content -LiteralPath $jabraInventoryFile -Encoding utf8
$jabraInventory = $jabraInventoryText | ConvertFrom-Json
$jabraMic = @($jabraInventory.devices | Where-Object { $_.name -eq 'Casque (Jabra Evolve 75)' -and $_.maxInputChannels -gt 0 -and -not $_.isLoopbackDevice })
if (-not $jabraInventory.interactive_session -or $jabraMic.Count -ne 1 -or $jabraMic[0].defaultSampleRate -ne 48000 -or $jabraMic[0].maxInputChannels -lt 2) { throw 'Identité/session/format non conforme : aucune ouverture.' }
$jabraMicIndex = [int]$jabraMic[0].index
python C:\Agent\scripts\qualify_microphone_30s.py --directory $jabraDirectory --device-index $jabraMicIndex --authorized-device-name 'Casque (Jabra Evolve 75)'
```

Le harnais existant, couvert par **13 tests à horloge simulée**, revalide le nom,
l'index, WASAPI, les canaux et la fréquence immédiatement avant l'ouverture.
L'enfant doit être attaché au Job Object Windows avant `OPEN`. `READY` puis
`START` déclenchent une fenêtre active monotone non renouvelable de 30 secondes ;
le watchdog demande `stop_stream` à cette borne. Le délai de grâce du contrôleur
sert uniquement au vidage de buffers déjà acquis, au fsync des WAV et à la
sortie de l'enfant. Ni prolongation ni seconde ouverture automatique, et aucune
pause/reprise pendant cet essai. À 48 kHz, le quota strict reste
**1 440 000 trames, 30,000 secondes de données**. Si 29,9 secondes sont conservées,
le résultat reste partiel : conserver l'erreur et les fichiers, sans abaisser ce
critère ni recommencer sans autorisation.

Après fermeture, produire un rapport neuf en lecture seule : identité et index
réel, session/PID, heures `OPEN/READY/START/STOP/CLOSED`, durée active et durée
des données séparées, six parties de cinq secondes si le quota est atteint,
séquences et trames par canal, tailles, SHA-256, fsync attesté, RMS/crêtes et
écrêtage sans interprétation du son. Vérifier les erreurs, la fermeture du
stream, la terminaison PyAudio, la sortie de l'enfant, la fermeture du Job Object
et zéro processus dédié restant. Préserver le rapport brut même en échec.
Aucune écoute, transcription, recherche audio externe, génération LLM,
création de source, base ERP/Brain ou activation proactive dans ce parcours.

Il s'agit d'un **complément matériel limité de T03**, sur le microphone du
casque, et non d'une reprise du Realtek motivée par ses 100 ms manquantes. Ce
parcours autonome ne qualifie ni le loopback du casque, ni un changement de
périphérique pendant capture, ni T01 (navigation avec capture active), ni T04
(onglets/clics et parcours intégré), ni la capture native dans l'application.

### Test Jabra du 11 octobre 2026 : 25,9 secondes conservées, quota incomplet

L'inventaire frais a trouvé une entrée WASAPI unique **Casque (Jabra Evolve 75)**,
index 15, 48 kHz, deux canaux, non-loopback, dans la session Windows interactive
1. Le harnais a effectué une seule ouverture, un seul `READY`, un seul `START`
et une seule fermeture ; aucune sortie système, loopback, reprise ou seconde
capture n'a été lancée. L'ouverture est attestée à **19:16:55,364107 UTC**,
`START` à **19:16:55,366381 UTC**.

L'arrêt matériel est demandé à **19:17:25,368391 UTC**, soit `START +30,002005 s`,
et terminé à **+30,004283 s**. Ces écarts mesurés comprennent la latence du
scheduler et de l'API ; ils ne constituent pas une garantie de zéro dépassement
à la microseconde. Le flux est fermé à 19:17:26,057849 UTC. La grâce sert au
vidage des données déjà acquises et aux fichiers, sans prolongation de la
fenêtre d'acquisition.

Les **six WAV PCM16 stéréo** contiennent cinq parties de cinq secondes et une de
0,9 seconde : **1 243 200 trames par canal, 25,9 secondes, 4 973 064 octets**.
Chaque taille, SHA-256, compteur de trames et offset de fichier est recalculé
depuis les WAV. Les accusés durables du harnais attestent fsync. RMS agrégé par
canal : environ **77,344 et 77,344**, crête absolue **3 346/3 346**, zéro échantillon
écrêté. Ces seules métriques confirment des données non nulles ; aucun son n'est
écouté, interprété ou transcrit.

Le premier callback arrive **4,166 secondes après START** ; le premier temps ADC
accepté commence à **+4,076254 s** dans la fenêtre fixe. Le dernier temps ADC
finit 22,763 ms avant sa borne. Les deux extrémités ADC couvrent 25,900983 s,
compatibles avec 25,9 s de WAV à environ 1 ms près. **La cause du délai initial
n'est pas établie**, et les horodatages de chaque callback n'étant pas conservés,
la continuité ADC interne ne peut pas être certifiée indépendamment.

Le quota strict reste **1 440 000 trames/30,000 secondes** : il manque 4,1 secondes
de données. `passed=false`, `partial_capture=true` et le code de sortie 1 sont
conservés avec l'erreur « Quota incomplet ; le délai matériel reste limité à
30 s sans prolongation ». L'ouverture Jabra, les fichiers non vides et l'arrêt
normal sont attestés ; **la capture complète de 30 secondes reste non qualifiée**.

L'enfant PID 21612 est sorti, PyAudio terminé et le Job Object fermé. Un contrôle
de processus Windows en contexte normal trouve **zéro Python dédié**. La première
requête CIM sous sandbox a échoué par accès refusé ; son rapport brut est
préservé, et son compteur zéro n'est pas retenu comme preuve d'inventaire réussi.
Les scripts de capture conservent leurs SHA préalables. Aucune base ERP/Brain,
source, génération LLM, transcription, recherche externe ou activation
proactive n'est sollicitée. L'audit des fichiers et processus est en lecture
seule et n'ouvre aucun périphérique. La garde testée couvre les sockets Python,
pas une coupure physique du réseau ni tous les appels natifs.

Preuves nouvelles, toutes locales :
[inventaire frais](../logs/foresight-runtime/qualification/headset-jabra-inventory-20261011-191634-13ab015a.json),
[rapport brut conservé](../logs/foresight-runtime/qualification/headset-jabra-30s-20261011-191634-13ab015a/qualification.json),
[audit WAV et fermeture](../logs/foresight-runtime/qualification/headset-jabra-30s-20261011-191634-13ab015a/postmortem-verified-20261011.json),
[contrôle des processus réussi](../logs/foresight-runtime/qualification/headset-jabra-30s-20261011-191634-13ab015a/process-check-normal-20261011.json).
L'audit vérifie 16 critères, Ruff passe pour son helper ; aucun code canonique
n'est modifié. Ce complément de T03 ne clôt pas les recettes du loopback casque,
du remplacement de périphérique, de T01/T04 ou du parcours natif intégré.

### Futur protocole Jabra : ouverture limitée à 45 s, quota de données de 30 s

**État historique de la préparation : non exécuté et sans nouvelle autorisation
à cette étape.** Les essais autorisés ensuite sont documentés plus bas.
Les autorisations Realtek et Jabra précédentes ont été consommées. Le nouveau
harnais [qualify_microphone_data_window.py](../scripts/qualify_microphone_data_window.py)
exige `--approved-data-window` et une référence de **nouvelle autorisation humaine**.
Ce flag atteste une décision donnée ailleurs ; il ne donne aucune permission à
lui seul. L'accord devra couvrir explicitement l'ouverture du seul microphone
**Casque (Jabra Evolve 75)** pendant au maximum 45 secondes, dont une courte
stabilisation acquise puis immédiatement écartée en RAM, et au plus 30 secondes
de PCM conservées sur ce PC. Aucune sortie système ou loopback, autre microphone,
écoute, transcription, recherche, génération LLM, base ERP/Brain ou source n'est
utilisée. Aucun `main`, inventaire réel, processus de capture ou périphérique n'a
été exécuté pour préparer ce complément.

Un inventaire WASAPI frais de métadonnées doit donner un nom unique, une session
interactive non nulle, 48 kHz et au moins deux canaux d'entrée. L'index 15 observé
précédemment n'est pas fixé : prendre celui de cet inventaire et le revérifier.
Un doublon de nom, un index changé, un autre format ou un loopback refuse
l'ouverture. Le worker refait ce contrôle avant `OPEN`, puis vérifie une nouvelle
fois le nom, WASAPI et le format immédiatement avant `audio.open`. Il n'emploie
aucun périphérique par défaut ni solution de repli automatique.

Commande reviewable **seulement après une nouvelle autorisation explicite**,
avec un dossier neuf et l'index frais unique déjà vérifié :

```powershell
$dataMicAuthorization = '<REFERENCE DE LA NOUVELLE AUTORISATION HUMAINE>'
$dataMicDeviceIndex = <INDEX FRAIS UNIQUE VERIFIE>
$dataMicStamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$dataMicDirectory = "C:\Agent\logs\foresight-runtime\qualification\headset-jabra-data30-max45-$dataMicStamp"
python C:\Agent\scripts\qualify_microphone_data_window.py --approved-data-window --authorization-reference $dataMicAuthorization --directory $dataMicDirectory --device-index $dataMicDeviceIndex --authorized-device-name 'Casque (Jabra Evolve 75)'
```

Le contrôleur ancre son budget monotone **avant de publier `OPEN`**. L'ouverture
du pilote, le démarrage et la stabilisation sont compris dans les 45 secondes ;
`READY`, un callback, une partie WAV ou un changement de phase ne renouvellent
jamais cette borne. Cinq callbacks successifs de 100 ms avec statut zéro et
horodatages ADC monotones/cohérents sont écartés en RAM ; le premier buffer de
données doit arriver dans les dix secondes suivant `OPEN`, sinon l'essai échoue.
Le contrôleur applique également cette borne de démarrage ; un `audio.open` ou
`START` bloqué ne peut reporter le délai de dix secondes jusqu'à la borne de 45 s.
Les incohérences pendant cette stabilisation remettent seulement le compteur
de bons callbacks à zéro, jamais les délais. Une discontinuité ADC après
stabilisation échoue sans ajouter de silence ou recoller artificiellement les
temps. La tolérance technique de 2 ms est explicite et **pas encore qualifiée
sur matériel**.

Le quota est **1 440 000 trames par canal, PCM16 stéréo à 48 kHz**, soit 30,000
secondes nominales de PCM. Les horodatages ADC réels de chaque callback,
leurs extrémités, leur différence avec la durée nominale et les heures du
contrôleur sont conservés séparément. Un dernier buffer est limité au nombre
de trames restant, sans tronquer les fichiers déjà durables. Le retard initial
Jabra de 4,1 secondes observé précédemment est compatible arithmétiquement avec
ce budget augmenté ; il ne garantit ni le prochain retard, ni une future réussite.

Le watchdog enfant demande l'arrêt à `OPEN +44,75 s` pour réserver 250 ms aux
appels et à l'ordonnancement. Indépendamment, le parent demande l'arrêt du seul
Job Object propriétaire à `OPEN +45 s` si la fermeture n'a pas été attestée.
L'enfant est créé suspendu, affecté à ce Job puis repris, selon le helper
`OwnedChild` existant relu et épinglé par SHA. Aucun processus préexistant,
LM Studio ou service Agent n'est ajouté au Job ou ciblé. La fermeture du stream
et la terminaison PyAudio doivent être confirmées avant la borne physique ;
un reçu `STOPPED` complet publié atomiquement permet ensuite **cinq secondes
de vidage et fsync, microphone fermé**, sans prolongation d'acquisition.

**Limite de la borne physique :** `audio.open`, `stop_stream`, le scheduler
Windows et la terminaison d'un Job ne sont pas des mécanismes temps réel.
Les deux watchdogs n'attestent donc pas une garantie absolue de fermeture
à 45,000 s. Un arrêt tardif, une fermeture non confirmée, un timeout, un appel
de fermeture en erreur ou une terminaison forcée refuse la qualification,
même avec le quota entier. La mesure conserve ces écarts et erreurs, sans
prolongation, baisse du quota, pause/reprise ou seconde ouverture automatique.
Une nouvelle tentative exigerait un nouvel accord humain.

Chaque WAV de cinq secondes est acquitté après fsync et SHA-256 ; les preuves
intermédiaires sont publiées atomiquement dans ce dossier neuf. Les données
partielles et erreurs restent conservées. Après arrêt, un rapport distinct
recalcule les SHA, tailles, formats, trames, offsets, RMS, crêtes et écrêtage,
sans écouter ou interpréter le son. Il vérifie aussi que le rapport brut n'a
pas changé et conserve le reçu de sortie enfant, Job vide et handles fermés.
L'audit se fait également lorsqu'un résultat partiel existe ; il ne transforme
jamais ce résultat en réussite. Les anciens scripts, tests et résultats de
30 secondes restent intacts.

La préparation passe **61 tests purs** : horloges simulées, métadonnées fictives,
PCM fabriqué et erreurs d'API simulées ; Ruff et compilation Python passent.
Une vérification indépendante refait **61/61 en 0,84 s**, avec `PYTHONPATH`,
`TEMP`, `TMP` et base temporaire neufs, sans `main`, inventaire ou capture.
Ces tests résident dans `.ui-preview/pilots` et restent **hors de la collecte
globale `tests/` de référence de 2 051 cas** ; les compteurs ne sont pas additionnés.
Le premier passage sous sandbox a rencontré `WinError 5` sur les dossiers
temporaires ; cette erreur est conservée, puis le passage en contexte normal
a réussi. Aucun de ces tests ne qualifie un périphérique, le pilote, un arrêt
physique à 45 secondes, ni la durée réelle ADC sur matériel. Preuves :
[préparation et fichiers préservés](../logs/foresight-runtime/microphone-data-window-preparation-20261011-201812-97bc5732/before.json),
[résultat des tests simulés](../logs/foresight-runtime/microphone-data-window-preparation-20261011-201812-97bc5732/pure-tests-startup-final.xml).
[vérification indépendante](../logs/foresight-runtime/microphone-data-window-independent-20261011-203940-701b2453/pure-independent.xml).
Une [relecture indépendante des sources](../logs/foresight-runtime/microphone-data-window-fusion-readonly-review-20261011.json)
ne relève pas de défaut actionnable dans ce périmètre préparatoire ; SHA-256 de
ce reçu : `5b5a1d8a81a4dd6ed2dc0bb6d3ef5e0c67e2aa91c577a6f2cd202b05796875a9`.
Cette revue n'importe ni le module, ni les tests, et ne répète aucun compteur.
Le [nouvel inventaire de métadonnées RO](../logs/foresight-runtime/microphone-data-window-metadata-20261011-204047-142ab833/inventory.json)
retrouve un microphone Jabra unique, index 15, 48 kHz, deux canaux, non-loopback,
dans la session interactive 1 : `capture_started=false`, `permissions_probed=false`.
Il ne prouve ni l'autorisation d'ouverture, ni une capture ; l'index sera encore
revalidé avant tout futur `OPEN`. **L'autorisation humaine de ce nouveau protocole
45 s reste en attente à cette préparation. Aucun flux n'est ouvert.**
Ce protocole autonome reste un futur complément de T03 ; T01/T04, la capture
native intégrée, le loopback casque et une capture matérielle de longue durée
restent à qualifier séparément.

### Essai Jabra de 45 s autorisé : résultat partiel et diagnostic ADC

La préparation ci-dessus décrit l'état avant l'essai. La nouvelle autorisation
humaine `call_78733e7908d341b6b5fbd900a2273679` a ensuite couvert **une seule
ouverture** du microphone Jabra ; elle est désormais **consommée**. Le
[rapport brut](../logs/foresight-runtime/qualification/headset-jabra-data30-max45-20261011-204752-8993bed8/qualification.json)
reste en échec, avec **1 156 800 trames par canal, soit 24,1 s nominales**
conservées en cinq parties durables. Le quota de 30 s n'est pas atteint.
L'ouverture mesurée est bornée à **26,5344149 s** ; stream et PyAudio sont
fermés à `2026-10-11T20:48:20.010660Z`. L'enfant est sorti, le Job propriétaire
est vide et ses handles sont fermés. Le watchdog parent n'a pas déclenché de
terminaison forcée à l'échéance. Un contrôle CIM du seul PID 9912 confirme son
absence. Ces preuves attestent un arrêt complet de cet essai partiel ; elles
ne le transforment pas en réussite du quota ni en recette de capture intégrée.

Les **247 callbacks, numérotés 0 à 246**, déclarent chacun 4 800 trames et un
statut zéro. Cinq servent à la stabilisation, 241 sont enregistrés et le dernier
est refusé : son delta ADC de **+2,3058 ms** dépasse le seuil technique de 2 ms.
Sur les données acceptées, l'étendue ADC vaut 24,099738 s, soit -0,262 ms par
rapport aux 24,1 s de PCM. Au dernier callback, l'intervalle de réception et
l'intervalle ADC diffèrent de 14,2 µs. Cette observation est compatible avec
une variation d'horodatage ; **une perte physique de trames n'est pas prouvée**.
La continuité physique n'est pas davantage attestée par le seul statut zéro.
L'[audit indépendant RO](../logs/foresight-runtime/microphone-data-window-readonly-postmortem-20261011-2050/read-only-diagnostic.json)
conserve ces limites, vérifie les SHA et tailles déclarées sans décoder ni
écouter les WAV, et confirme que les fichiers bruts restent inchangés.

### Harnais v2 : quota PCM distinct des diagnostics d'horodatage

La correction suivante a d'abord été **préparée et testée sans nouveau
périphérique**, avant l'essai matériel rapporté plus bas.
Le seuil ADC de **2 ms reste inchangé**. Après stabilisation, un écart est
journalisé avec les horodatages réels au lieu d'être, à lui seul, interprété
comme une perte de PCM. Aucun silence, interpolation ou audio supplémentaire
n'est créé. Un ADC non monotone, un statut non nul, un nombre de trames ou de
bytes incorrect, un premier buffer hors des dix secondes, une fermeture tardive
ou non confirmée, le quota incomplet et un échec du Job restent bloquants.
Les bornes physiques de 45 s, le quota de 1 440 000 trames et les budgets de
vidage ne sont pas renouvelés ni augmentés.

Le schéma `bounded-pcm-quota-and-timing-v2` borne explicitement `passed` au
**quota PCM, à l'ouverture bornée et au nettoyage propriétaire**.
`timestamp_coherence_passed` fournit séparément le diagnostic des horodatages.
`physical_continuity_qualified=false` et `physical_continuity_status=unknown`
restent explicites, même si aucun écart n'est détecté. Un ancien rapport sans
ce schéma ne peut pas être requalifié par la nouvelle porte. La limite de
temps réel Windows exposée ci-dessus reste entière.

La [nouvelle preuve préparatoire](../logs/foresight-runtime/microphone-timing-quota-correction-20261011-211544-599e571c/qualification.json)
porte **74 tests purs réussis en 0,26 s**. Deux anciens tests lisant des WAV
synthétiques sont volontairement exclus de ce passage : aucun WAV n'a été
décodé. Les horloges et métadonnées fictives vérifient notamment les écarts ADC,
les retours arrière, les erreurs de statut/trames, les échéances et la portée
des résultats. Ruff et compilation Python passent. Ces tests restent hors de
la collecte globale ; les anciens résultats de 61 tests et les erreurs
environnementales initiales sont conservés séparément.

Le [rejeu des 247 métadonnées](../logs/foresight-runtime/microphone-timing-quota-correction-20261011-211544-599e571c/metadata-replay.json)
compte hypothétiquement 242 buffers acceptables selon la nouvelle décision,
soit 24,2 s de **métadonnées de trames**. Il ne lit aucun PCM et ne recrée pas
le dernier buffer refusé : **la capture réelle reste à 24,1 s et en échec**.
Les scripts et tests avant correction sont sauvegardés avec leurs SHA ; les
anciens scripts de 30 s et tous les résultats matériels restent intacts.
À cette étape préparatoire, cette version n'avait pas été exécutée sur
microphone. Toute nouvelle ouverture nécessite une nouvelle autorisation
humaine, une identité fraîchement vérifiée et un dossier neuf.

Une [revue indépendante des sources v2](../logs/foresight-runtime/microphone-v2-independent-readonly-20261011/review.json)
ne relève pas de défaut actionnable dans les gardes et la portée préparatoires.
Son SHA-256 est `ae30260e6dd23f71eef5f4a845b638833b7c1a32cf992cd93896523120666af6`.
Elle confirme les SHA du script et de ses tests, sans importer le harnais,
réexécuter les tests, lire le PCM ou ouvrir un périphérique. Ce complément
n'ajoute aucune qualification matérielle ni autorisation de capture.

### Essai matériel Jabra v2 : quota PCM de 30 s et fermeture confirmés

Une nouvelle autorisation humaine, `call_4240a9f8823740ff8e6f17d8024be261`, a
couvert **une seule ouverture** du microphone **Casque (Jabra Evolve 75)**,
index frais 15, session interactive 1, 48 kHz stéréo non-loopback. Cet accord
est désormais **consommé**. L'essai du 11 octobre 2026 conserve exactement
**1 440 000 trames par canal, soit 30,000 s nominales de PCM**, en six parties
de cinq secondes. Le contrôleur et le worker sortent en réussite du schéma
`bounded-pcm-quota-and-timing-v2` : quota PCM, ouverture bornée et nettoyage
propriétaire uniquement. L'ancien résultat de 24,1 s reste en échec et intact.

La fermeture du stream et de PyAudio est attestée à
`2026-10-11T21:25:32.268455Z`, après **32,6904626 s** depuis l'ancrage `OPEN`,
avant la borne de 45 s. Le premier buffer de données arrive après 2,156712 s,
dans la limite de dix secondes. L'enfant PID 26660 est sorti avec le code 0,
le Job est vide, les handles sont fermés et le watchdog parent n'a pas
déclenché son arrêt à l'échéance. Un contrôle CIM en contexte normal, limité
à ce seul PID, confirme son absence ; le refus initial du sandbox est conservé.

Les 305 callbacks déclarent chacun 4 800 trames et un statut zéro : cinq sont
écartés pour la stabilisation et 300 fournissent les données conservées.
**Neuf anomalies d'horodatage ADC** dépassent le seuil inchangé de 2 ms et
restent journalisées. L'étendue ADC vaut 29,9989481 s, soit -1,0519 ms par
rapport au quota nominal de PCM. `timestamp_coherence_passed=false`,
`physical_continuity_qualified=false` et `physical_continuity_status=unknown`
restent explicitement exposés : cette réussite ne certifie pas une continuité
physique sans perte. Le statut zéro ne suffit pas à l'attester.

L'[audit indépendant en lecture seule](../logs/foresight-runtime/microphone-v2-success-readonly-20261011-212650-fe66ccd4/success-readonly.json)
vérifie **29 critères** : schéma et SHA des sources conformes à la revue,
quota déclaré, SHA/tailles des six fichiers, offsets et acquittements fsync
déclarés, budgets, reçus et fermeture propriétaire. Les 13 fichiers bruts
restent inchangés. Cet audit ne décode aucun WAV, ne lit aucun échantillon PCM,
n'écoute ni ne transcrit le son, ne réexécute aucun moteur et n'ouvre aucun
périphérique. Le contrôle de format déjà produit par le harnais n'est pas
réexécuté ; les empreintes et tailles sont vérifiées sur les fichiers seuls.

Le journal d'un passage frontend ciblé indique un démarrage à 23:24:37,
heure de Paris, et une durée de 37,17 s, chevauchant cet essai. **Le PC n'est
pas présenté comme au repos** ; aucune relation causale avec les anomalies ADC
n'est établie. Ce résultat ne qualifie ni la performance d'une STT industrielle,
ni une garantie temps réel Windows, le loopback, le changement de périphérique,
la capture native intégrée ou une séance matérielle de longue durée.

Une [vérification indépendante préalable](../logs/foresight-runtime/microphone-v2-root-independent-20261011-2324/qualification.json)
passe **76/76 tests**, incluant deux audits de WAV **synthétiques**, sans capture
ni décodage du son ambiant. Elle reste distincte du passage de 74 tests et hors
de la collecte globale ; ces compteurs ne sont pas additionnés. Les rapports
matériels bruts sont conservés dans le
[dossier neuf de l'essai](../logs/foresight-runtime/qualification/headset-jabra-v2-data30-max45-20261011-212458-84da2978/controller.json).
La réussite a consommé l'autorisation unique : **aucune nouvelle ouverture de
microphone n'est actuellement autorisée**.

### Capture Jabra intégrée : préparation isolée, non exécutée (11 octobre 2026)

La recette suivante prépare le véritable parcours UI → routes natives →
`NativeCapture` → helper WASAPI → `store_chunk`, dans une **nouvelle fixture**
Brain/ERP sans projet attribué. Elle ne remplace ni ne requalifie le succès
standalone précédent : ses 29 contrôles n'attestent pas ce parcours intégré,
la navigation ni un deuxième onglet. Les anciens accords sont consommés.
**Aucun microphone, loopback ou stimulus de sortie n'a été ouvert/exécuté
pendant cette préparation ; une nouvelle autorisation regroupée est requise.**

Le raccord optionnel dans `app/services/native_audio.py` est privé et refuse
une configuration hors fixture dédiée, hors `AGENT_TESTING=1`, ou si Brain/ERP
ne sont pas tous deux dans cette fixture. L'admission du nonce/SID est conservée
avant création de l'enfant ; deux onglets, un échec puis un rejeu ou un restart
ne donnent pas un deuxième accès. `scripts/native_audio_capture.py` conserve
son parcours ordinaire et délègue seulement la politique privée à
`scripts/native_capture_qualification.py`. Les fichiers sont gelés ; aucune
activation du backend canonique n'est réalisée par cette préparation.

La politique exige le micro et la sortie exacts **« Casque (Jabra Evolve 75) »**,
ainsi que **« Casque (Jabra Evolve 75) [Loopback] »**, uniques, 48k/stéréo.
L'inventaire frais puis chaque ouverture vérifient ces identités et indices ;
aucun défaut, rapprochement de nom ou repli sur un autre périphérique.
Un OPEN privé intervient après attachement au Job, puis fixe **45s maximales
d'ouverture**, sans renouvellement par pause, reprise, navigation ou ACK.
Chaque piste stabilise cinq callbacks puis conserve au plus **1440000 trames
48k par canal** ; premier buffer utile dans10s. Le seuil diagnostique ADC2ms
reste inchangé, la continuité physique inconnue. Statut non nul, ADC arrière,
taille/format invalide et erreur de fermeture restent bloquants.

Le contrôleur `.ui-preview/pilots/integrated_capture_controller.py` possède un
Job privé contenant uniquement le backend fixture neuf et ses descendants.
Son watchdog s'arme **avant** le reçu autorisant OPEN et travaille sur un
thread indépendant de stdout, CUA, HTTP, SQL et des écritures audio. Le helper
ferme préventivement à44,75s ; faute de fermeture attestée dans45s, le
contrôleur termine ce seul Job et refuse la recette. Windows n'offre pas ici
une garantie temps réel : une fermeture tardive/inconnue/forcée ne devient
jamais un succès. Exit/Job vide/handles fermés sont attestés séparément.

L'acquisition reste en RAM bornée ; la fermeture des streams et de PyAudio
précède la conversion réelle mono16k, les WAV, fsync, SHA, journaux et ACK du
service existant. Un flush **inactif** de5s maximum n'étend pas l'ouverture.
La séance sans projet retourne avant mix/import de Source/Recording ; STT,
LLM, MM, proactive et les13 workers sont interdits dans la fixture.
`integrated_capture_fixture.py` bloque également les API média navigateur
**avant le bundle**, sur toutes les URL SPA, avec Permissions-Policy et garde
getUserMedia/getDisplayMedia. Le refus serveur seul serait trop tardif.

Un stimulus **optionnel, synthétique et fictif**, deux tons440/880Hz à faible
amplitude, est préparé exclusivement pour la sortie Jabra explicitement
sélectionnée. Aucun fichier vocal ni sortie par défaut n'est utilisé.
Sa durée nominale de PCM reste≤30s, avec une échéance monotone distincte
avant START, arrêt préventif à29,75s et fermeture attestée≤30s ; pause/reprise
ne la réarme pas. **Il n'a jamais été diffusé pendant la préparation.**
Présenter ce stimulus et ses callbacks ne prouve pas, à soi seul, que le
loopback contient effectivement les tons : aucun contenu ambiant n'est
écouté, transcrit ou analysé, et cette fidélité acoustique reste hors preuve.

Preuves de préparation : un ciblé natif/handshake **76/76** en7,04s ; puis
le complément final **65/65 tests purs** en1,65s, incluant les trois nouveaux
cas de borne de sortie, et Ruff0. Ces passages recouvrent des cas communs et
ne s'additionnent pas. Les premiers échecs WinError5/chemins Windows trop longs
restent conservés ; la reprise en TEMP neuf court est verte. Le global2051
est une baseline antérieure aux deux raccords Python ; le nouveau global est
suivi séparément par root. Aucune performance matérielle n'est déduite de ces
tests fictifs. Le
[protocole concret et reçu de gel](../logs/foresight-runtime/integrated-jabra-preparation-20261011-214025-c322dfa0/PROTOCOL.md)
précise les portes SHA/revue/inventaire/nouvel accord et les commandes futures.
La **revue indépendante reste en attente** ; aucun GO matériel n'est délivré.

La relecture préparatoire a ensuite identifié un risque précis : START sortie
tenait le verrou matériel, ce qui pouvait empêcher sa garde interne de fermer
à29,75s si le pilote bloquait. Le contrôleur ne vérifiait alors les30s qu'après
STOPPED global. Un correctif est préparé **dans une copie hors runtime actif** :
reçu START sortie exclusif/fsync avant démarrage, reçu CLOSED indépendant et
borne externe START+30 sur le seul Job privé, sans attendre le verrou ou HTTP.
Les trois fichiers de l'empreinte du global en cours restent inchangés ; ce
global n'atteste pas la copie. Le
[protocole correctif](../logs/foresight-runtime/integrated-output-bound-correction-20261011-220326-1e578419/CORRECTION_PROTOCOL.md)
conserve le défaut, la sauvegarde et les portes d'activation/tests/revue. Le
manifeste initial est invalide après ce changement de contrôleur : aucun
lancement ne doit utiliser cet ancien manifeste. Aucun matériel ni stimulus
n'est autorisé ou exécuté ; les tests candidat et la revue restent séparés.

La [revue statique indépendante du candidat](../logs/foresight-runtime/integrated-output-bound-independent-review-20261011/review.json)
est ensuite favorable, sans défaut actionnable supplémentaire :10 contrôles,
SHA du rapport `7f2e972c1d289c83c64e851d06ba5b318f40fa85f8298b1589a02934cbe1d805`.
Elle ne lance ni test, inventaire, enfant ou matériel. Le
[supplément neuf](../logs/foresight-runtime/integrated-output-bound-correction-20261011-220326-1e578419/candidate-peer-review-supplement.json)
confirme que la copie et les trois fichiers protégés sont inchangés. Promotion,
tests ciblés adaptés et manifeste neuf restent nécessaires ; aucun GO matériel.

Après clôture vérifiée du global v2 **2056pass/1skip**, le seul
`scripts/native_capture_qualification.py` est promu à l'identique du candidat
relu (SHA `19e9c02d0b501208c666d4bd4c350a2b253d4403b4e469e1b050ca8474d2eec0`).
Les deux raccords natifs existants restent inchangés. Le global est
explicitement **antérieur à cette seule correction de qualification**.
Les [cibles post-promotion](../logs/foresight-runtime/integrated-jabra-promoted-20261011-222602-edd836f7/tests-and-freeze.json)
passent **169/169 en20,61s** :14 historiques,7 admissions et deux groupes
recouvrants de74 pour copie et runtime promu ; ne pas additionner ces groupes
comme preuves indépendantes de qualité. Ruff complet et scripts/pilots0.
Le premier échec30/139 de la factory temps simulé reste conservé, corrigé
uniquement dans les tests, sans affaiblir la garde OPEN réelle.

Un [inventaire RO unique](../logs/foresight-runtime/integrated-jabra-metadata-20261011-223016-877ab6a9/metadata.json)
revalide Jabra exact mic15/sortie13/loopback17, WASAPI48k/stéréo, session1,
exit0, `capture_started=false` et `permissions_probed=false`. Aucun flux ou
stimulus ; cet inventaire ne prouve ni permission ni ouverture et les indices
seront revérifiés après nouvel accord avant le futur essai.
Le [nouveau protocole et manifeste](../logs/foresight-runtime/integrated-jabra-promoted-20261011-222602-edd836f7/PROTOCOL.md)
décrivent START sortie durable + CLOSED distinct + borne externe immuable,
fixture sans STT/LLM et observations UI séparées. Revue exacte finale,
checkpoint/redémarrage par root et **nouvel accord humain regroupé** restent
nécessaires ; aucun contrôleur, serveur fixture, capture ou modèle lancé.

## Direct opt-in et reprise explicite — 12 octobre 2026

Le réglage `foresight.live_transcription_enabled` est un booléen séparé,
**False par défaut**. Son absence dans les anciennes configurations vaut False.
La lecture du réglage exige le booléen enregistré `True` : un entier `1` ou
une chaîne `"true"` hérités ne constituent pas cet accord. Le direct exige
également `foresight.enabled=True`. Activer Foresight ou démarrer une capture
ne déclenche donc pas à lui seul la transcription. Les contrôles de capture,
de proactive et d'enrichissement automatique restent distincts.

`PUT /api/v1/workspace/fusion-settings` enregistre explicitement le nouveau
champ. Désactiver uniquement le direct arrête le consommateur STT et son
processus résident propriétaire ; cela n'appelle pas l'arrêt de capture.
La désactivation générale conserve son comportement d'arrêt de capture.
Au démarrage, `app/main.py` et `start_worker()` vérifient l'accord du direct
avant toute remise de fragments `running` à `pending`, consommation ou
chargement de modèle. `warm_up()` exige aussi cet accord. La restauration
d'une copie remet les quatre drapeaux général/direct/proactive/enrichissement
automatique à False ; elle n'active pas le direct sur la production.

Les capacités distinguent `transcription.enabled` (accord effectivement
actif), `installed` (installation renseignée par le runtime),
`live_operational` et `live_ready` (qualification). Une installation ou une
activation ne vaut pas qualification de qualité industrielle ou de latence.

### Reprendre des fragments en échec

`POST /api/v1/meeting-sessions/{sid}/transcription/retry` réutilise le cadre de
commandes durable, via `retry_transcription(db, sid, Command|dict)`. Le corps
contient `command_id` (UUID canonique) et `expected_revision`. La réponse est
`{session, retried_chunks, chunk_ids}`. Une nouvelle commande exige les droits
actuels d'écriture sur la séance, sa révision attendue, les accords général
et direct actifs, et une séance non annulée.

Seuls les fragments `failed` deviennent `pending`. Les fragments `pending`,
`running` et `completed`, les WAV et leurs empreintes, les segments corrigés
et les segments finalisés sont conservés. La commande produit l'événement
durable `transcript.retry_requested`, avec les identifiants concernés et
`requested_at_utc`. Le réveil du worker intervient après le commit ; ce
service ne charge pas lui-même de modèle.

Le rejeu d'une commande terminée rend son résultat d'origine, même si les
accords général ou direct ont depuis été désactivés. Il revérifie les droits
d'écriture actuels ainsi que séance, opérateur, type de commande, UUID et
digest du corps ; une identité ou un contenu différent est refusé. Ce rejeu
ne réveille pas le worker et ne remet pas en file un nouvel échec apparu
depuis. Pour une nouvelle reprise, il faut un nouvel UUID et la révision
actuelle. Une erreur SQL après préparation conserve le reçu préparé et les
fragments pour récupération ; elle ne devient pas un succès partiel.

### Un consommateur, priorité aux séances en cours

Le cycle arrêt/réactivation conserve un seul thread consommateur. Une
génération de cycle empêche un ancien tour ayant observé le direct désactivé
d'annuler une activation plus récente. L'admission est revérifiée sous le
verrou d'écriture avant `pending → running`, puis avant publication du
résultat ; un arrêt ou une annulation intervenu pendant le traitement ne
publie pas un résultat de l'ancienne génération. La fermeture du résident
est sérialisée et idempotente. Un arrêt peut encore signaler un worker en
cours de fermeture ; les cinq secondes de `join` ne sont pas une garantie
temps réel d'arrêt Windows.

La sélection donne priorité stricte aux fragments `pending` des séances
`recording`. Dans chaque classe, l'ordre stable est
`created_at, sequence, id`, entre pistes et séances ; une ancienne séance
n'est choisie que lorsqu'aucune séance en cours n'a de fragment en attente.
Les requêtes utilisent `LIMIT 1`. Une inférence déjà engagée n'est pas
préemptée et les anciens fragments restent durables. Le DTO des fragments
expose `created_at` en UTC afin de rendre leur ancienneté observable.

**La file SQL globale reste non bornée en nombre, âge et retard.** Les quotas
de capture par séance et la limite des demandeurs de ressources IA ne bornent
pas ce stock durable. Cette priorité améliore l'admission ; elle n'atteste
pas une charge longue à deux pistes. `compute_s` mesure le décodage audio et
l'ASR, sans attente de file, initialisation, admission IA, commit, livraison
SSE ou affichage navigateur. L'objectif P95 du premier segment visible ≤5s
reste non mesuré et le direct industriel reste **NO-GO**.

Les [cibles backend de ce lot](../logs/foresight-runtime/live-controls-final-20261012-0340/qualification.json)
passent **49/49 en41,72s**, avec Ruff ciblé0, en bases et runtimes fictifs.
Les premiers échecs de fixtures, de persistance booléenne et de chemins
Windows restent historiques. Aucun modèle, matériel ou base canonique n'a
été activé par ces tests. Le global **2056pass/1skip** précède ces changements
produit ; il ne les qualifie pas.

### Préparations T12 et Jabra à regeler

La fixture T12 enregistre maintenant explicitement le direct à True dans
sa **seule base privée**, après les portes SHA/nonce/Job/revue/GO existantes.
Les treize workers de démarrage restent neutralisés ; le seul worker STT est
démarré explicitement après l'échauffement prévu. Budgets, modèles, corpus,
motifs de score, fichiers vocaux fictifs et interdictions matérielles restent
inchangés. Ce raccord préparatoire ne lance ni fixture ni inférence.

Les paquets T12 et le manifeste Jabra de31 ressources conservés avant ce lot
sont historiques : les sources produit, ce document et le frontend ont
changé. Ils doivent être liés à nouveau aux sources et au build figés, puis
relus indépendamment avant un nouveau GO. Aucun ancien reçu n'est réécrit,
aucune permission matérielle consommée n'est réutilisée. Les helpers natifs
ne sont pas modifiés par ce lot et aucun flux n'est ouvert.

## Correction de la prise de notes vocale — 12 octobre 2026

Les notes personnelles disposent maintenant des mêmes commandes audio que
les réunions. Le choix Windows distingue `system` (son du PC), `mic`
(réunion en salle) et les deux. La sélection est explicite et un démarrage
seul ouvre les périphériques ; une reprise conserve la commande initiale.
Le statut global de capture empêche une autre séance de démarrer en parallèle.
La transcription devient visible dès le démarrage, dans un panneau adjacent.
Le brouillon reste dans l'éditeur et une amélioration manuelle le sauvegarde
avant de construire la proposition. Une saisie survenue pendant la sauvegarde
reste un brouillon et empêche une amélioration sur un texte plus ancien.

Un refus d'admission IA avant l'inférence ne bloque plus définitivement
l'enrichissement automatique. Il expose une attente et une reprise espacée
(15/30/60 s). Les résultats d'inférence invalides et les tentatives interrompues
ne sont pas rejoués automatiquement. Audio, corrections et validations
humaines restent conservés. Un test vocal synthétique vérifie le moteur local ;
il ne qualifie pas la précision ni la latence d'une réunion industrielle réelle.


### Validation de cette correction

Build TypeScript/Vite et Ruff réussis. Les 802 tests frontend (81 fichiers)
et les 39 tests backend ciblant enrichissement et notes audio passent.
La suite backend complète a été interrompue avant sa fin ; elle n'est pas
annoncée comme passée. La chaîne réellement exécutée sur une voix synthétique
conserve une transcription et une proposition Gemma avec citation exacte,
sans modifier la note initiale. Le microphone réel n'a pas été démarré.
L'interface a été relue dans le navigateur, sur ordinateur et à 390 px,
sans débordement horizontal. Les séances, leur historique et les décisions
de validation canoniques sont identiques à la sauvegarde prise avant relance.


## Qualification GPU V6 et interface fictive — 12 octobre 2026

Le nouvel essai GPU V6, autorisé séparément, est terminé avec refus avant
import CT et chargement du modèle : deux handles Windows ne disposent pas de
chemin identifiable. Les observations sont enregistrées avant l'erreur, sans
attribution de cause ou de fournisseur. Aucun modèle chargé ni transcription
produite ; processus, Job et NVML fermés en 10,25 s. L'accord unique est consommé.
Le [compagnon terminal](../logs/foresight-runtime/gpu-short-run-20261012-191119-5f626f87/root-terminal-review.json)
préserve cette limite ; aucun profil GPU de production n'est activé.

La recette A9 utilise deux bases fictives : graphe global 6 nœuds/4 liens,
périmètres A 4/3 et B 2/1, zoom et consultation du texte réel, statistiques
5 secondes/320088 octets pour deux pistes conservées non finalisées. Une action
est convertie via l'interface en tâche avec responsable/échéance ; une deuxième
conversion réelle est refusée en 409 et conserve la tâche originale.
Les fichiers [avant](../.ui-preview/pilots/a9-ui-capsule-20261012-185111-70f9bb0d/proof/api-real-before-3313faca.json),
[après](../.ui-preview/pilots/a9-ui-capsule-20261012-185111-70f9bb0d/proof/api-real-after-33e77f12.json)
et [observations UI](../.ui-preview/pilots/a9-ui-capsule-20261012-185111-70f9bb0d/proof/ui-functional-observations.json)
séparent réponses réelles, lectures SQL et gestes du navigateur.

Stats et graphe ne débordent pas la page aux largeurs 1280/670/320 px observées.
Le tableau d'actions hérité déborde à 670/320 : une correction privée ajoute
des conteneurs de défilement locaux accessibles aux tableaux actions/tâches,
sans modifier cellules ni handlers. Son frontend passe 858 tests, TypeScript
et build. La [recette navigateur du correctif](../.ui-preview/pilots/a9-responsive-capsule-20261012-193009-620a51a6/proof/root-ui-qualification.json)
confirme les largeurs 320/670/1280/1915 px, le défilement local au clavier et
l'accès au bouton de la tâche créée dans le planning. Le processus et les deux
bases fictives sont fermés ; les sources et le build restent inchangés.
Une autre copie corrige six couleurs SVG après une mesure des traits à 1,412:1 ;
ses 858 tests, TypeScript et build passent. Le
[contrôle visuel réel](../.ui-preview/pilots/a9-graph-contrast-capsule-20261012-200758-543f2df4/proof/root-graph-qualification.json)
mesure les traits à 5,269:1, les bordures normales à au moins 5,021:1 et le
focus source à 4,936:1 ; texte à au moins 13,143:1. Les largeurs 320/670/1915 px,
la sélection par Entrée, le zoom et la consultation du texte sont observés.
Il s'agit des couleurs CSS calculées du thème clair, pas de tous les pixels
anticrénelés ni du thème sombre réel. Serveur et deux engines fermés, aucun
modèle ou microphone ouvert ; T13 complet reste non qualifié.
Les ratios de texte calculés ne suffisent pas à qualifier le SVG, les composants
ou les états clavier. T13, T12 et L12 restent ouverts. Aucune modification de
production ou nouvelle capture microphone n'est effectuée par cette recette.

Le [relevé opérationnel du 12 octobre à 20:31 UTC](../logs/foresight-runtime/promotion-operational-ro-fresh-20261012-203140-525354f6/qualification.json)
confirme les deux bases ouvertes par le processus 8001 exact. Une analyse de
jalons est déclarée running et quatre queued ; les états SQL des séances ne
montrent ni enregistrement ni traitement audio. L'ownership natif, les brouillons
du navigateur et l'ensemble du stockage restent inconnus. Aucune maintenance,
sauvegarde ou activation n'a été lancée. Les
[neuf contrôles de fichiers V3](../.ui-preview/pilots/native-interruption-next-20261012/qa/next-v3-file-gates-before-root.json)
passent, sans ouvrir ces portes opérationnelles.

Le prochain [protocole GPU R2](../.ui-preview/pilots/qualify_stt_gpu_short_v7_r2_protocol.md)
est préparé avec 55 simulations et deux revues. Le marqueur exclusif est fermé
avant la garde du run, puis NVML intervient sous cette garde ; aucun chemin
autorisé n'est élargi. Le contrôle distingue le profil exact des fichiers image
CT/NVIDIA des régions anonymes non attestées. Les corpus, budgets et refus sont
conservés ; la qualité des fenêtres coupées reste non qualifiée. Aucun essai
R2 n'est effectué sans nouvel accord humain unique. V6 et V7 restent conservés.

Le 12 octobre à 20:57 UTC, la préparation d'activation dispose de deux jeux
neufs : [34 originaux code/interface](../.ui-preview/backups/promotion-code-20261012-205450-0d6f7a78/qualification.json)
et [snapshots Brain/ERP avec restauration privée vérifiée](../.ui-preview/backups/promotion-db-online-20261012-205755-597ae1eb/qualification.json).
Toutes les tables et leurs contenus sont identiques à leurs transactions source
en lecture seule, intégrité correcte et zéro anomalie FK. Les pièces/index
et le jeu final coordonné après arrêt restent à préparer. Aucune capture,
modification de base source, maintenance ou activation n'en découle.

La régression combinée capture/STT/reconnexion est lancée en copie à 21:26 UTC,
avec 379 Python et des bases/TEMP fictifs. Les 45 simulations de reconnexion
et leur revue ne prouvent pas la nouvelle voie LM Studio réelle. Aucune capture
ou activation n'est lancée. La protection des nouvelles sauvegardes attend une
autorisation ACL précise après refus du contrôle automatique ; leurs sources
et droits restent inchangés.

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


### Protection des sauvegardes préparatoires — 13 octobre 2026

Les trois sauvegardes préparatoires de `.ui-preview/backups` ont reçu la
protection d’accès Windows autorisée : 66 éléments, dont 43 fichiers, avec
contenus et propriétaires conservés. Seules leurs autorisations Allow Users et
Authenticated Users sont retirées ; Fred, SYSTEM, Administrators et les deux
identités techniques gardent leurs droits. Les ACL des trois bases sources
restent inchangées. Le [reçu final](../logs/foresight-runtime/backup-access-protection-20261013-dc8cdf0113eb4120b53b7f1b1275a643.json)
conserve la portée et les vérifications exactes. Aucun microphone, transcription,
modèle ou nouvel essai n’est lancé par cette protection ou sa documentation.
Les recettes matérielles et le P95/T12 restent ouverts.


### T12 : choix réseau et premier lancement V6 — 13 octobre 2026

La recette fictive de 60 minutes est désormais préparée pour le primaire
réseau choisi par l’utilisateur, `google/gemma-4-26b-a4b-qat` sur
`http://192.9.110.115:1234`. Elle conserve le profil ASR CPU, quinze fichiers
fictifs annotés, trente-cinq faits, les 1224 occurrences du nouveau schedule
et trois fenêtres de cinq demandes LLM. Aucun microphone ou loopback n’est
concerné par ce choix.

Le [premier lancement V6](../logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-075610-78025914/controller-final.json) n’a pas franchi l’attente
initiale d’affichage du panneau Transcription : aucun driver ni admission du
modèle ; fixture exit 0, Job vide/fermé et deux observateurs terminés. Ce reçu
échoué et les préparations antérieures restent conservés ; aucune durée de
60 minutes ou latence voix → premier texte visible n’est qualifiée.
L’[observation réseau indépendante](../logs/foresight-runtime/network-recovery-live-20261013-42465a494ce140b9902f7ab10695302b.json) voit le modèle primaire
au catalogue et zéro instance du secours local, sans génération. **T04 matériel,
T12/P95, qualité ASR et L12 restent ouverts.**


### T12 V6 : heure fictive et assemblage après arrêt — 13 octobre 2026

La cadence réelle de **10 h 36 à 11 h 36 (Paris)** a duré 3600,094 s : 720
fragments par piste, soit 1440 acquittés et conservés. Les deux pistes originales
sont complètes ; le rejeu mic/120 n’ajoute aucune ligne. Les six contrôles de
conservation passent et les processus/Job se ferment normalement. Cette séance
utilise les quinze WAV fictifs neufs, sans microphone ni loopback.

Le profil CPU n’a pas soutenu la transcription directe des deux pistes :
99 fragments `completed`, 1341 `retained`, 123 segments bruts. `retained` signifie
audio conservé. Les 83 occurrences notées fournissent 192 contrôles booléens
(108 motifs retrouvés, 84 non retrouvés), sur les 35 faits des quinze cas ;
1141 occurrences restent inconnues. Les contrôles de courant, puissance et
température ne retrouvent pas leurs motifs sur les occurrences notées. Les
valeurs/unités, la qualité ASR et les locuteurs industriels ne sont pas qualifiés ;
aucune précision globale ou sélection du meilleur cas n’est calculée.

Dans trois fenêtres, les quinze demandes logiques produisent neuf dispatchs :
trois questions répondues, six consommateurs d’annulation locale terminés,
trois enrichissements rejetés 502 pour format/citation et trois `InferenceBusy`
proactifs attendus après une attente bornée de 2 s. L’ordre global des priorités
et l’arrêt effectif du calcul distant ne sont pas qualifiés. La mesure voix →
premier texte visible conserve 1224 manquants (30 visibilité non qualifiée,
1194 sans première présence) et zéro mesure P95. **T12 et L12 restent ouverts.**

Après fermeture, un [assemblage distinct](../logs/foresight-runtime/t12-post-recipe-consolidation-20261013-7af6eacb.json) a vérifié les
1440 WAV sources avant/après et produit deux WAV de 3600 s / 57600000 trames,
115200044 octets chacun. Il ne constitue pas une consolidation pendant l’heure
ni une nouvelle transcription. L’[audit terminal historique](../logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-083158-7af6eacb/independent-terminal-partial-audit-v6.json)
reste intact ; sa mention de consolidations non observées précède cet assemblage.
Le [relevé réseau après séance](../logs/foresight-runtime/network-recovery-live-20261013-c5a92111952943a3a3e5f53e43b3117d.json) voit zéro instance du Gemma
local et le primaire au catalogue ; l’observateur ne génère rien. Les trois
réponses réseau réelles proviennent de la séance. [Bilan complet](../logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-083158-7af6eacb/root-actual-result-summary.json).


### Enrichissements : diagnostic et candidat structuré — 13 octobre 2026

Le [diagnostic séparé](../.ui-preview/pilots/t12-enhancement-502-diagnostic-20261013/one-shot-root-reviewed-v2/diagnostic.json)
reçoit 14 ajouts et les refuse. Le [nouveau pilote structuré](../.ui-preview/pilots/t12-structured-additions-probe-20261013/result.json)
effectue un seul POST au primaire `google/gemma-4-26b-a4b-qat` : HTTP 200,
12 ajouts acceptés par les contrôles de format et de citations verbatim. Les
valeurs « 16 MHz » et « 2250 W » reprennent des erreurs de transcription : ce
résultat n’atteste pas la qualité métier des propositions. Aucun SQL, microphone,
chargement local ou changement de code canonique n’est effectué par ce pilote.
Il ne décrit pas les trois réponses 502 historiques de l’heure.

Le correctif V2 est un candidat non activé : schéma fermé limité à 12,
références distinctes de la note courante, comparaison locale de tous ses blocs,
refus des doublons normalisés dans la note et dans la réponse. L’évitement des
reformulations sémantiques reste une consigne au modèle, non une garantie.
Une note seule donne zéro ajout sans appel IA ; le Studio prévu affiche « Aucun
ajout utile » et ne propose pas d’acceptation vide. Les reçus Notes historiques
prepared/completed restent récupérables. Le manuel conserve son secours configuré
avant l’unique POST ; l’automatique ne démarre pas de secours. Régressions et
promotion restent à réaliser ; T12, ASR/P95 et L12 demeurent ouverts.

### Candidat V2 : présentation et preuves logicielles — 13 octobre 2026

Le Studio candidat affiche « Aucun ajout utile à proposer pour cette note »
quand la proposition est vide et masque l'acceptation. Une proposition obsolète
ou rejetée conserve son état ; une ancienne réponse vide n'est pas présentée
comme analyse automatique du contexte actuel. L'affichage de la suspension
explique que les passages capturés sont conservés en attente. Les libellés
« Direct suspendu » et « Transcription des passages en attente » dépendent de
l'état réel et du stock ; ils ne redémarrent ni capture ni transcription.

[QA ROOT](../.ui-preview/pilots/t12-enhancement-schema-candidate-v2-20261013/qa-root-observed-20261013.json) :
887 tests frontend passent dans 83 fichiers, sans échec ni test en attente ;
TypeScript, build et Ruff passent. Les 37 unités fictives passent. Le premier
pytest global a conservé 435 réussites et un échec sur un chemin temporaire
Windows de 287 caractères ; la reprise courte de 2444 cas est encore en cours,
sans réussite globale revendiquée.

La [revalidation locale du format V2](../logs/foresight-runtime/t12-structured-response-v2-offline-revalidation-20261013.json)
accepte les douze ajouts du précédent pilote réel, avec messages/schéma identiques,
sans nouvelle génération ni ouverture SQL. La note fictive courte est la seule
portée de ce pilote ; des valeurs ASR erronées restent citées. Le routing V2 en
exploitation et la qualité industrielle ne sont pas qualifiés par cette preuve.
Aucune source candidate n'est activée. ASR/P95, T12 et L12 restent ouverts ;
ces résultats logiciels ne remplacent pas la recette d'endurance partielle.
### QA Python : état avant continuation, non publié — 13 octobre 2026

V1 conserve 435 réussites nommées dans son XML et l'échec du chemin Windows de
287 caractères. V2 a été arrêté après 1974,77 s (environ 33 min), exit 92,
`disk_reserve_reached`, avec un minimum disque observé de 2077769728 octets.
Ses 382 sources Python et 74 ressources restent inchangées. Le JUnit final
est absent, les imports finaux privés et la vérification finale d'isolation
n'ont pas été validés après interruption. Les points de progression ne sont
pas des réussites nommées ; aucun nombre de cas V2 terminés ni passage global
n'est revendiqué. Le processus appartenant au harnais est terminé et le Job
est vide. [Reçu V2](../logs/foresight-runtime/notes-ai-python-v2-disk-stop-root-observed-20261013.json).

La [continuation préparée](../.ui-preview/q/nac3/preparation-v1.json)
sélectionne 2009 cas parmi la collection attendue de 2444, en conservant les
435 réussites nommées de V1. À l'état documenté, elle n'a pas été exécutée ;
son résultat et l'agrégation exacte des noms restent à vérifier. La préparation
lie les mêmes 382 sources et 74 ressources, les sélections et les reçus V1.

ROOT a compressé une ancienne QA fictive fermée : 8602 fichiers, zéro
suppression, mêmes empreintes de contenu avant/après (`19d597a3…`). La variation
observée pendant cette opération est précisément 6530973696 → 9470754816 octets
libres. La remontée antérieure et la perte précédente d'environ 4,2 Go ne lui
sont pas attribuées. [Reçu de compression](../.ui-preview/pilots/closed-qa-compression-20261013/result.json).

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
monolithique revendiqué. [Continuation](../.ui-preview/q/nac3/qa/python-continuation-notes-ai-v1/qualification.json)
; [agrégation](../.ui-preview/q/nac3/qa/python-aggregate-notes-ai-v2.json)
; [audit indépendant des composants](../.ui-preview/q/nac3/qa/independent-terminal-notes-ai-continuation-v1.json).

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
[Interprétation CPU3](../logs/foresight-runtime/t12-cpu3-root-interpretation-20261013.json).

La comparaison suivante reprend les mêmes 15 WAV fictifs dans deux variantes,
avec un vocabulaire industriel sans chiffres attendus injectés : 30 résultats,
zéro demande manquante, 77,704 s, Job fermé et empreintes inchangées. Les motifs
figés donnent 25/35 sans vocabulaire et 23/35 avec vocabulaire, sans mesurer une
précision générale. La graphie « lux » s'améliore dans le cas choisi ; l'erreur
1250 W → 2250 W demeure dans les deux variantes. Le premier précontrôle refusé
pour alias de chemin reste conservé, sans démarrage du modèle. **Le vocabulaire
n'est pas activé et la transcription canonique reste inchangée.**
[Interprétation comparée](../logs/foresight-runtime/t12-cpu-domain-paired-root-interpretation-20261013.json)
; [résultats](../logs/foresight-runtime/t12-cpu-pair-30c71d2af642453c8f9f821705f8b0fe/diagnostic.json).

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
[Publication](../logs/foresight-runtime/notes-structured-source-publication-20261013.json)
; [sauvegarde](../logs/foresight-runtime/notes-structured-current-data-backup-20261013.json).

Le nouveau backend a démarré après publication : santé Brain/ERP correcte,
JavaScript HTTP conforme au build qualifié et HTML conforme après normalisation
des fins de ligne. Le premier contrôle a refusé la comparaison HTML brute et le
chemin `/app/assets` ; sa correction utilise le script réel `/assets` et compare
le texte normalisé. Ce refus de contrôle reste conservé. Les empreintes du code
en RAM ne sont pas attestées indépendamment ; son chargement découle des fichiers
publiés avant le nouveau démarrage. [Reprise vérifiée](../logs/foresight-runtime/notes-structured-runtime-restart-20261013.json).

Dans la réunion existante « test 1 », le nouveau build affiche « Aucun ajout
utile », les contrôles Source audio, Périphériques, Microphone, Sortie Windows
et « Démarrer la réunion ». Le mode temporaire mixte active les deux sélecteurs,
puis le mode système initial est restauré. Aucun microphone ni enregistrement
n'a été lancé. Toutes les lignes de notes et versions ERP restent identiques à
la sauvegarde. Cette observation de l'interface ne qualifie pas le P95.
[Contrôle UI et conservation](../logs/foresight-runtime/notes-structured-UI-current-verification-20261013.json).

Un observateur des métadonnées voit le primaire exact au catalogue et zéro
instance du Gemma local. Il ne génère rien et ne demande aucun chargement ou
déchargement ; l'échange HTTP de déchargement n'est pas capturé indépendamment.
[État réseau/local](../logs/foresight-runtime/network-recovery-live-20261013-49a29f7693ea461080f687b6041c6d50.json).
Le correctif notes/Studio est actif et les cinq documents sont publiés.
Aucun commit ni push à cette étape. Physique, multipiste, ASR/P95, T12 et L12
restent non qualifiés ; les premiers essais et l'historique restent conservés.

Le reçu historique du contrôle UI est encodé en Windows-1252. Son
[compagnon UTF-8](../logs/foresight-runtime/notes-structured-UI-current-verification-utf8-20261013.json)
conserve les mêmes faits et lie l'empreinte de l'original, laissé intact.

Le [dernier contrôle direct](../logs/foresight-runtime/notes-final-readonly-state-20261013.json)
confirme la santé d'Agent, le build servi, le catalogue primaire exact joignable
et zéro instance Gemma locale. Il ne génère rien. Un contrôle antérieur par
accès par défaut a reçu un refus de connexion ; il n'est pas reproduit lors
de l'accès direct sans proxy, sans cause exclusive établie.

### Transcription corrigée et assistant reliés — 16 octobre 2026

Ask séance privilégie désormais la transcription complète relue et sa preuve de
même révision. Le lien de citation conserve segment, révision et instant audio.
Une correction sauvegardée retire immédiatement l'ancienne preuve du contexte ;
en attendant relecture, le direct ancien n'est pas réintroduit comme vérité.
L'original et les segments directs restent conservés. Les droits Brain courants
sont contrôlés avant préparation, les notes gardent leur révision propre.

Le contrôle HTTP privé sur le vrai LLM réseau répond 1250 W, avec citation de la
preuve corrigée, malgré le provisoire fictif 2250 W. Une modification ultérieure
1500 W non relue rend la réponse obsolète. Le fichier audio servi conserve son
empreinte. Les bases privées restent intègres ; aucune publication métier.
Ce contrôle réutilise le WAV et le résultat medium CPU déjà acquis : ce n'est
ni une nouvelle transcription, ni une recette matérielle ou une mesure P95.

Correction activée après sauvegardes Brain/ERP/EG2 et restauration sur copies ;
toutes les lignes non volatiles comparées restent exactes. Le dernier ciblé
droits/contexte passe 21 cas, dont les 11 cas du nouveau fichier ; les 107 cas
de régression antérieurs et trois compléments sont conservés séparément.
Les ensembles se recouvrent. Ruff passe ; aucune campagne globale répétée.

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


### Base audio pleine — 16 octobre 2026

Agent distingue désormais « Stockage de la base saturé » d’une saturation des
fichiers audio. La capture est interrompue, les fragments restent conservés et
la synchronisation peut être rejouée après libération de capacité. Le correctif
est actif sur8001 ;99tests ciblés passent, sans microphone ni modèle.
La preuve utilise une vraie erreurSQLite SQLITE_FULL dans une base privée ;
elle ne remplace pas la recette de volume physique plein T16, toujours ouverte.

Le test réduit `PRAGMA max_page_count` sur la seule connexion de sa petite base
privée puis remplit sa table d’événements fictifs. SQLite retourne réellement
le code13, sans exception d’I/O fabriquée. Le lecteur natif réel appelle un
handle producteur inerte : état interrompu persistant en mémoire, aucun reçu
du fragment refusé, aucune avance de séquence et aucun faux arrêt réussi.
Une notification « stopped » tardive ne rétablit pas une capture saine.
Le handle confirme seulement l’appel d’arrêt ; il ne prouve pas l’arrêt d’un
périphérique physique. L’écriture du journal d’interruption peut elle-même
échouer tant que la base est pleine ; le signal d’erreur reste en mémoire.

Une fois la limite privée relevée, le journal d’interruption est conservé et le
rejeu réel SQL/fichiers, répété deux fois, donne exactement deux fragments,
deux commandes et deux événements reçus. Les WAV, manifestes, premier reçu et
note humaine fictive sont inchangés ; `integrity_check` est `ok`.
La réserve fictive est conservée. Le disque hôte n’est jamais rempli.

Le classificateur reconnaît les codes SQLite, ENOSPC, Windows39/112 et le refus
HTTP507 ; aucun chemin, requête SQL ou contenu d’exception technique n’est
affiché. Les autres erreurs gardent leur message précédent. Aucune modification
de l’acquisition, des transactions, des acquittements ou du protocole de rejeu.
Les462sources Python précédentes sont reliées par empreinte : seule
`native_audio.py` diffère, et son AST ne change que pour ce choix de message
et le petit classificateur ajouté ; le nouveau test porte le manifeste à463.
Les99tests ne sont pas additionnés au précédent global2680 car les cohortes
se recoupent. Un avertissement Starlette/httpx existant reste consigné.

Preuves : `logs/foresight-runtime/L02-sqlite-full-ROOT-20261016.json`.
L02/L03/L11/L12 restent ouverts ;9lots/13,16fonctions/25 et11recettes/17 clos.


### Recette hors ligne du16octobre, essai renouvelé

La coupure réelle a permis de produire la transcription medium (1250W/350lux)
et un index privé de quatre sources texte/image/audio. La génération locale
n’a pas confirmé son diagnostic : T11/L11/L12 restent ouverts. Le retour réseau
et le déchargement de Gemma sont confirmés ; durée totale570,07s, sans microphone.
Le diagnostic IA respecte désormais le délai configuré (60s sur le poste), au
lieu d’ignorer le réglage par un plafond fixe15s.104tests ciblés passent.

La phase enfant a duré57,91s. Les17inventaires déconnectés incluent11observations
pendant sa vie ; écart maximal8,13s. Ils prouvent l’état physique échantillonné,
pas zéro appel réseau natif. Le traceback situe l’échec après transcription,
construction de l’index, recherches et réouverture ; leurs classements n’ayant
pas été journalisés, ils ne sont pas déclarés corrects rétrospectivement.
L’index conservé passe `integrity_check` et contient un job terminé et quatre
entrées terminées (deux images, un texte, un audio). Ces fichiers sont fictifs
et privés ; aucun succès de la chaîne entière n’est déduit de leur présence.

Le modèle local s’est chargé, puis `/v1/settings/ai/fallback/test` a renvoyé un
échec ou une identité inattendue au harnais. Sa réponse exacte n’a pas été
conservée : la cause précise demeure inconnue. Le délai fixe15s est un défaut
distinct confirmé par le test rouge ; rien ne prouve qu’il explique à lui seul
cet échec réel. Le correctif garde prompt, paramètres sans raisonnement,
réservation et déchargement identiques. Il est actif sur8001, avec sauvegardes
SQLite et contrôles des tables protégées. La seule différence de code produit
avec les463sources précédentes est cette expression de délai ; le nouveau test
porte le manifeste à464sources. Aucun nouvel appel LLM réel pour ce correctif.

Le harnais conserve désormais un point d’étape avant la génération, puis un
diagnostic d’échec filtré (catégorie, statut HTTP, identité conforme, réponse
présente), y compris si le transport lève une exception. Ni jeton, réponse
brute, motif serveur brut ni secret ne sont écrits dans ce diagnostic.
Ses30contrôles simulés passent, distincts des104tests backend et du global
historique, sans les additionner. Un avertissement Starlette/httpx reste acquis.
L’accord unique renouvelé est consommé ; aucun nouvel essai ou coupure lancé.

Preuves : `logs/foresight-runtime/L11-offline-renewed-attempt-ROOT-20261016.json`
et `logs/foresight-runtime/L11-diagnostic-timeout-ROOT-20261016.json`.
9lots/13,16fonctions/25 et11recettes/17 restent clos ; L02/L03/L11/L12 ouverts.


### Diagnostic local sans nouvelle coupure — préparation du16octobre2026

Après l'échec du diagnostic Gemma dans la recette physique, un contrôle ciblé
est préparé avec réseau connecté : un seul appel au test fixe d'Agent, puis
inventaire réseau frais et vérification du déchargement géré par Agent.
Il refuse un modèle déjà chargé, une capture/travail audio actif ou un choix
de moteur différent. Six contrôles simulés passent ; aucun modèle réel lancé.
Son exécution attend un nouvel accord humain, distinct de l'essai hors ligne
consommé ; elle ne clôturerait pas à elle seule T11, L11 ou L12.

[Protocole et commande soumis à accord](../.ui-preview/gemma-online-diagnostic-20261016/PROTOCOL.md).


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


## Audio compressé — 21 octobre 2026

Les nouvelles captures natives conservent des fragments indépendants Ogg/Opus,
mono à 32 kbit/s constants. Le navigateur demande également 32 kbit/s par piste
(Opus/WebM selon ses codecs disponibles). Les imports MP3 restent acceptés.
Le PCM sert au traitement en mémoire ; les anciens WAV et journaux restent
lisibles et ne sont ni supprimés ni convertis automatiquement.

Ordre de grandeur : 14,4 Mo par heure et par piste, soit environ 29 Mo/h pour
microphone + son système, auxquels s'ajoutent le mix final et les copies du
journal de récupération. Le plafond porte sur l'audio des pistes, pas sur une
allocation disque préalable : 256 Mio par import, 512 Mio par séance, durée
maximale 12 heures. Les documents et archives retrouvent respectivement leurs
plafonds de 50 et 150 Mio. Les délais de traitement assouplis restent conservés.

La consolidation encode directement un mix Ogg/Opus en blocs d'une seconde ;
elle ne crée pas de WAV intermédiaire couvrant toute la réunion. Les fragments
sont horodatés, contrôlés par SHA-256 et CRC Ogg. Le journal v2 conserve les octets
compressés et les reçus SQL ; la reprise historique WAV v1 reste disponible.
Une nouvelle ouverture de microphone n'a pas été réalisée pour cette évolution.
La qualité de transcription de paroles réelles après compression reste à évaluer.

Contrôles reproductibles sans matériel ni modèle :
`python -m pytest tests/test_audio_compression.py tests/test_native_chunk_journal.py tests/test_foresight_runtime.py -q`.
Le runtime existant `.venv-speech` fournit PyAV/libopus, sans téléchargement.
Les tests couvrent encodage/décodage, fin courte, identité des retries, reprise,
refus de corruption, reçu SQL et mixage de deux pistes avec décalage.
Les résultats de cette évolution sont conservés dans
`.ui-preview/audio-compression-20261021/` ; ils ne clôturent pas les recettes
matérielles restantes du lot 12.

Activation sur 8001 confirmée après sauvegarde SQLite Brain/ERP et contrôle
`integrity_check=ok`. Capacités servies : import 256 Mio, séance 512 Mio/12 h,
Opus 32 kbit/s. TypeScript, compilation Vite, 54 tests frontend et les six
contrôles finaux codec/reçu/reprise/mix/export passent ; Ruff passe. Les essais
plus larges et leur ancien échec de valeur de reprise sont conservés dans le
rapport, avec la vérification de la correction. Aucun global complet n'est
revendiqué pour cette évolution.
Rapport : `logs/foresight-runtime/AUDIO-compression-ROOT-20261021.json`.


### Continuité Opus et contrôle vocal — 21 octobre 2026

Le direct conserve maintenant jusqu'à 500 ms du fragment Opus précédent admis,
décodés uniquement en mémoire. Les originaux compressés restent inchangés ; aucun
WAV dérivé n'est créé pour cette continuité. Un fragment retenu, échoué ou réservé
au batch ne sert pas de contexte. Le début conservé reste celui du fragment
courant, pour éviter de republier les mots du contexte. Les anciennes captures
WAV gardent leur parcours existant. 69 tests de codecs, reprise, délais, mixage
et admission passent ; Ruff passe. Activation 8001 et sauvegardes Brain/ERP
vérifiées, sans capture ni réglage utilisateur modifié.

Un essai CPU medium réel a transcrit les 15 extraits fictifs existants après
compression, en 82,6 s avec chargement. Les fichiers passent de 2 627 932 à
347 046 octets. Les sorties brutes et les motifs d'origine sont conservés : cinq
différences de graphie/ponctuation sont distinguées des deux erreurs réelles
(bruit sur « consignation », négation perdue en chevauchement). Cette lecture
technique n'est ni une approbation humaine du contenu ni une qualification du
direct industriel. Aucune correction de sortie n'est comptée comme réussite ASR.

Sur trois phrases réellement découpées à cinq secondes, le direct restitue
« 350 lb » au lieu de « 350 lux ». La comparaison d'un seul cas avec l'ancien
parcours WAV produit exactement la même erreur ; la phrase Opus complète
restitue bien « 350 lux ». Le défaut de fin de fragment reste ouvert. Aucun P95
DOM ni séance longue nouvelle n'a été mesuré. Tous les workers de ces essais
sont fermés, sans microphone, GPU ou téléchargement.

Preuve : `logs/foresight-runtime/L03-OPUS-CPU-ROOT-20261021.json`.
L02/L03/L11/L12 ne sont pas clôturés par ces contrôles.


### Révision du direct Opus après réception du fragment suivant — 21 octobre 2026

L'état courant remplace le contexte Opus fixe de 500 ms par le fragment admis
précédent complet, au maximum cinq secondes, décodé en mémoire. La fenêtre
courante reste d'au plus dix secondes. Le moteur sépare les mots du contexte
de ceux du nouveau fragment et peut réviser le texte automatique précédent.
Cela n'augmente ni le débit stocké de 32 kbit/s, ni les plafonds de fichiers.

Une révision ne touche que des segments encore provisoires, de révision 1,
du même fragment terminé, de la même piste et séance, avec les mêmes identités
et cardinalité. Une correction humaine, un segment finalisé ou une géométrie
incohérente est conservé. Aucun segment n'est supprimé. Les anciens textes,
intervenants, révisions et horodatages sont conservés exactement dans l'événement
`transcript.context-revised`. Une réponse IA fondée sur l'ancien instantané
est signalée périmée. Les différences de segmentation restent à relire.

Le vrai parcours `store_chunk → admission → process_chunk → ResidentWhisper → SQL`
sur trois phrases fictives produit 230 V/16 A, 1250 W/350 lux et conserve la
négation de consignation. Cinq fragments sont terminés, leurs octets vérifiés,
leurs acquittements rejoués sans doublon. Le premier fragment du cas d'éclairement
a réellement produit « 350 lb » ; après le suivant, la base contient « 350 lux »
réparti correctement entre les deux segments. L'ancien texte reste dans l'audit.
Ces segments restent tous provisoires, sans validation humaine créée par l'IA.

La commande de recette finit avec un code 1 parce qu'une postcondition attendait
les deux mots dans le seul segment précédent. Le rapport brut est conservé.
La relecture SQL distincte vérifie le résultat complet correctement réparti,
l'historique, les empreintes et les cinq états terminés ; aucun modèle n'a été
relancé pour corriger cette assertion. Les tests couvrent désormais cette
répartition et la priorité d'une correction humaine concurrente.

78 tests de régression passent ; dix tests ciblés, dont celui de répartition,
passent également, ainsi que le contrôle d'obsolescence. Ces décomptes se
recouvrent et ne s'additionnent pas. Ruff passe. Activation 8001 confirmée après
sauvegardes SQLite Brain/ERP vérifiées. Pas de microphone, GPU, téléchargement
ou donnée fictive introduite dans les bases métier. Tous les workers de recette
sont fermés. Les erreurs en bruit/chevauchement et les recettes matérielles
restantes ne sont pas clôturées par ce correctif.

Preuve courante : `logs/foresight-runtime/L03-ROLLING-OPUS-ROOT-20261021.json`.


### Parcours complet Opus jusqu'au CR relu — 21 octobre 2026

Le parcours existant de l'enregistrement consolidé est vérifié avec trois phrases
vocales fictives, encodées en Opus CBR 32 kbit/s mono : 82 747 octets au lieu de
648 044 octets en WAV, pour 20,25 secondes. Whisper medium CPU et la diarisation
CPU produisent réellement la transcription complète. Le brut conserve les six
valeurs numériques mais écrit « 350 luxe » ; cette erreur reste dans le rapport
initial, dont la commande a terminé avec le code 1 sur le contrôle d'unité.

La suite reprend ces mêmes bases privées, sans relancer l'ASR. Une relecture QA
scriptée corrige explicitement « luxe » en « lux » d'après le corpus annoté puis
valide la transcription fictive. Ce n'est pas une validation humaine d'un contenu
métier réel. Les six contrôles d'unités/valeurs passent alors. Le serveur réseau
configuré produit réellement le brouillon : 230 V, 16 A, 1250 W, 350 lux, ±0,2 mm
et 1,5 m. Il ne propose ni décision ni action inexistante. La publication rejouée
crée un seul CR fictif et zéro action, uniquement dans la base ERP privée.

La chaîne fichier compressé → transcription complète → relecture → synthèse
réseau → publication privée fonctionne dans cette portée. Aucun microphone,
GPU, téléchargement, chargement de LLM local ou écriture de données de recette
dans les bases métier. Aucun lot matériel ou qualité dégradée n'est clôturé sur
ce seul résultat. Le direct et son historique restent distincts du compte rendu
relu de l'enregistrement consolidé.

Preuve : `logs/foresight-runtime/L03-OPUS-COMPLETE-CR-ROOT-20261021.json`.
Exemple fictif : `logs/foresight-runtime/CR-Opus-20261021-48f87b54d0/reviewed-CR.md`.


### Prévol matériel avec le produit Opus courant — 21 octobre 2026

La fixture privée du produit courant démarre et ferme normalement : quatre POST
start/resume sont refusés avec 403 avant tout accès audio. Aucun microphone,
résident ASR, LLM ou transfert de fichier ; Job vide et handles fermés. Les
quinze tests de politique/chronologie et treize sous-tests passent. Aucun seuil
RAM de 5/9 Gio et aucun plafond de préparation n'ont été réintroduits.

Le collecteur lit les octets et empreintes indépendamment du codec. Il distingue
maintenant le décalage initial, les séquences manquantes, les trous temporels et
les chevauchements. Un décalage initial positif n'est pas une perte de fichier
acquitté. Tous les trous restent visibles et demandent une interprétation du
parcours observé ; ils ne sont pas arbitrairement qualifiés comme pauses.
Une séquence manquante, un chevauchement, une empreinte ou un reçu incohérent
restent des échecs. L'intégrité des fichiers ne prouve ni une capture sans trou,
ni une navigation réussie, ni l'audibilité d'une piste.

La procédure matérielle regroupée reste celle de
`.ui-preview/pilots/physical-workflow-20261015/PROTOCOL.md` : plusieurs démarrages,
pause/reprise, navigation/reload et refus de double propriétaire dans une seule
fenêtre audio autorisée. La préparation ne consomme pas cette fenêtre. Aucun
nouvel accord audio n'a été utilisé ici ; aucune capture n'a commencé.
T01/T02/T03/T04/T16 et L12 ne sont pas clôturés par le prévol.
Preuve : `logs/foresight-runtime/L12-OPUS-PHYSICAL-READINESS-ROOT-20261021.json`.


### Reprise Opus après cinq arrêts réels de processus — 21 octobre 2026

Cinq enfants distincts sont effectivement arrêtés avec `os._exit` après les
barrières de publication : intention durable, fichier audio, manifeste, commit
SQL, reçu durable. Les codes de sortie 71 à 75 sont observés ; il ne s'agit pas
de simples exceptions simulées dans un processus qui continue.

Sur chaque répertoire privé, `iter_reconcile → store_chunk → publish_receipt`
récupère les mêmes octets et la même empreinte Opus, conserve une seule ligne
audio et une seule commande de fragment SQL, puis rejoue le même acquittement.
Le décalage initial de 1 343 ms reste inchangé. Les cinq processus sont terminés ;
l'intégrité des deux bases privées est vérifiée. Les preuves sur disque restent
conservées, sans purge ni écriture dans les bases métier.

Le flux contient cinq secondes de silence synthétique réellement encodé en
Opus. Les enfants réutilisent ce payload encodé figé pour isoler la persistance
de la dépendance PyAV de l'autre environnement Python. Le nom interne de phase
`wav` reste historique : les fichiers publiés sont bien `.ogg`. Le premier
préparateur avait refusé les séances désactivées dans les réglages privés ; il
s'est arrêté avant création des séances et des enfants, puis le réglage a été
explicitement activé uniquement dans ces bases de recette.

Aucun microphone, capture WASAPI, ASR, LLM, téléchargement ou remplissage du
volume hôte. Ce contrôle qualifie la reprise du stockage/projection Opus après
arrêt de processus. Il ne remplace pas une coupure électrique, la fermeture du
navigateur ou la saturation réelle d'un système de fichiers : T02/T16 et L12
restent ouverts pour leurs exigences restantes. L'accord matériel demandé
reste en attente et n'a pas été utilisé.
Preuve : `logs/foresight-runtime/T16-OPUS-CRASH-ROOT-20261021.json`.


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

**Suspension intermédiaire, levée par le correctif de contexte en fin de document** : le second corpus fictif à deux voix a révélé
une prise de parole absente des fenêtres courtes. Le décodage intégral et le tour
isolé la reconnaissent. L’ancien worker a été rétabli ; sa limite2h est donc
encore active pour la transcription complète, distincte de la capture12h.
Aucun test12h réel ni correction du défaut n’est revendiqué.


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

Le contrôle lexical scellé trouve 14 réponses sur 15. Pour qa15, il attendait « non » ou « pas » ; la réponse réelle « Aucun achat n’est autorisé [C2]. » reprend exactement le refus présent dans les faits scellés. Cet échec du contrôleur lexical est conservé séparément de la relecture QA de Codex ; le corpus n’est pas réécrit et aucune validation métier humaine n’est revendiquée.


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
