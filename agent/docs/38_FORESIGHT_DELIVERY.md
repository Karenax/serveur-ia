# Fusion Foresight dans Agent — réalisation et preuves

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

La lecture Jabra réelle est transcrite localement avec quatre valeurs/unités
sur quatre. La lecture Realtek reste non qualifiée après interruption ; un
diagnostic ultérieur conserve normalement 426,179 s sans reproduire la panne.
Le retard de propagation de l’interruption Jabra reste à expliquer. Tous les
Jobs audio privés sont fermés, sans publication métier ni LLM.

Le global backend termine avec 2 851 réussites, trois échecs, un ignoré et
54 sous-tests. Après correction du remplacement atomique de l’état Windows,
mise à jour de deux attentes obsolètes et ajout du diagnostic de panne natif,
les cohortes ciblées de 41 et 50 tests passent. Elles se recouvrent et ne
constituent pas une nouvelle suite globale. Le correctif du superviseur reste
à activer dans son processus canonique existant. Frontend : 986 tests réussis.
Qualification inchangée : 9/13 lots, 19/25 fonctions, 15/17 recettes, L12 ouvert.
Audit : `.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r68.json`.
Preuve : `logs/foresight-runtime/HARDWARE-HUMAN-READBACK-ROOT-20261021.json`.

---

Historique des états précédents :

# Fusion Foresight dans Agent — réalisation et preuves

Le statut latéral de la séance sélectionnée suit maintenant sa lecture courante,
sans perdre le brouillon ni accepter un ancien retour réseau :105tests Studio,
986tests frontend et contrôle visuel sans audio réussis. Build et octets servis
sur8001 vérifiés, anciens assets conservés, sans redémarrage backend.
Preuve : `logs/foresight-runtime/STUDIO-LIST-STATE-ROOT-20261021.json`.

Qualification courante : **9/13lots,19/25fonctions,15/17recettes**, audit r67.
F03 est clos : vraie capture système sans projet, finalisation puis attribution
et rejeu identique sans doublon, avec quatre contrats courants de note/droits/rejeu.
Preuve : `logs/foresight-runtime/F03-UNASSIGNED-PHYSICAL-ROOT-20261021.json`.
Les bilans ci-dessous conservent leurs décomptes historiques ; L02/L03/L11/L12
et T03/T16 restent ouverts. Le global backend courant n’est pas terminé.

## Complément matériel Jabra et Realtek — 21 octobre 2026

La séance regroupée autorisée a produit deux captures système réelles, arrêtées
normalement et conservées : cinq fragments Opus et83282octets par sortie.
Transcription CPU locale : six mesures/unités sur six suivies pour Jabra,
cinq sur six pour Realtek. Le contrôle littéral « lux » reste négatif sur les
deux sorties ; les variantes de format déjà admises sont rapportées séparément.
Aucune précision industrielle globale n’est déduite de ces trois phrases.

Le rattachement explicite après capture sans projet et son rejeu conservent
un enregistrement et une commande. La capture micro Jabra préalable a subi
une interruption inexpliquée ; ses86fragments/reçus sont intacts, sans
confirmation de lecture humaine ni faux acquittement d’arrêt normal.
Les trois Jobs sont vides et fermés. La suite attend la disponibilité humaine,
dans l’échéance commune initiale ; aucun microphone ne reste ouvert.

[Détail et limites](23_MEETING_AUDIO.md#recette-matérielle-regroupée-en-cours--21-octobre-2026).
Preuve : `logs/foresight-runtime/HARDWARE-CONSOLIDATED-V2-SYSTEM-ROOT-20261021.json`.
Aucun lot supplémentaire clos ; le global backend courant reste en cours.

## Sauvegarde initiale revérifiée — 21 octobre 2026

Le point de retour `C:\AgentBackups\foresight-before-20261011-173855`
reste disponible. Le manifeste initial conserve son empreinte connue ; la
relecture intégrale confirme les16342fichiers projet (14741900930octets) et
les1360fichiers de données (1377623795octets), sans erreur de taille ou SHA256.
Ce snapshot est celui d’avant fusion, pas une sauvegarde nouvellement prise
du travail courant.

Le premier contrôle conserve un verdict global négatif : les anciennes copies
`restore-check` sont intègres mais leurs empreintes diffèrent des bases du
manifeste. Leur contenu et la cause de cette différence ne sont pas inférés.
Aucune de ces copies n’a été corrigée, remplacée ou effacée.

Pour vérifier le point de retour lui-même, deux nouvelles copies exactes des
bases sauvegardées ont été créées dans le dossier protégé
`.ui-preview/backups/restore-check-20261021-336f89da9929`. Les empreintes avant/après
restent celles du manifeste ; Brain et ERP passent `PRAGMA integrity_check`
(`ok`) et `PRAGMA foreign_key_check` (zéro violation), respectivement19et70tables.
La lecture SQLite était immuable et sans écriture ; aucun serveur, modèle ou
worker n’a démarré sur ces copies. Les accès larges Utilisateurs/Utilisateurs
authentifiés restent absents des droits hérités de ce nouveau dossier.

Preuves :
`.ui-preview/backup-availability-20261021/retained-snapshot-verification.json`
et `fresh-restoration-verification.json` dans le même dossier ; rapport scellé
`logs/foresight-runtime/RETAINED-BACKUP-REVERIFICATION-ROOT-20261021.json`.
Cela renouvelle la preuve de disponibilité/restaurabilité du snapshot initial,
sans clôturer de nouveau lot Foresight ni prétendre à un test de disque plein.

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

## État courant — 21 octobre 2026

Neuf lots/13, seize fonctions/25 et quinze recettes/17 clos, avec leurs limites
et pièces datées. T01 est clôturé après capture microphone Opus réelle,
navigation, filtre projet, rechargement, pause/reprise et arrêt normal ; ses
17 fragments et reçus sont intacts. T02/T04 sont désormais clos ; T03/T16 restent ouverts.

Le stockage courant est Opus32kbit/s. Le CR complet sur fichiers fictifs Opus
avec relecture QA est vérifié ; cela ne qualifie pas le direct industriel.
Les pistes natives démarrées sans aucun fragment sont signalées explicitement.
La comparaison beam5 ne corrige pas les deux erreurs bruit/chevauchement ;
le profil produit reste inchangé. Aucun casque Jabra détecté, aucun volume
physique plein testé sans administrateur. Drive reste exclu par l’utilisateur.

Frontend global969/94fichiers acquis avant le dernier correctif d’affichage,
puis ciblé capture50 ; TypeScript/Vite et octets servis vérifiés. Backend global
du21terminé :2763réussis,1ignoré,54sous-tests et1attente obsolète en échec,
corrigée puis couverte par85tests ciblés. Les deltas ultérieurs restent
identifiés séparément ; aucun global intégral propre du dernier arbre annoncé.

[Audit cumulatif r42](../.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r42.json)
· [Matrice actuelle](40_FORESIGHT_ACCEPTANCE.md).
Les sections datées suivantes conservent les résultats et incidents historiques.

## Priorité IA réelle et attente automatique corrigée — 16 octobre 2026

Le premier contrôle court conserve son échec : les deux automatiques expirent
après2s, avant la réponse normale du leader. L’ordre leader/question seul ne
prouve pas la priorité, car les concurrents ont disparu. La limite produit est
donc corrigée : les automatiques utilisent le budget standard30s du planificateur,
sans modifier l’ordre des priorités ni préempter un calcul distant engagé.

Le nouveau contrôle utilise les vrais modules `inference_scheduler`, `ai_client`
et le même budget importé de `session_proactive`. Les trois tickets sont observés
avant libération du leader, la question est arrivée en dernier, et l’ordre réel
de dispatch est leader → question → proactif → enrichissement. Les quatre appels
au LLM réseau répondent avec du contenu. Le Job est naturellement vide avant
fermeture, les threads sortent, les handles sont fermés et les sources sont stables.
Le témoin du transport ne remplace ni octets ni réponses. Ce résultat qualifie
le composant d’ordonnancement ; il ne représente pas un clic Ask du navigateur,
une mesure P95 visible ou un remplacement du résultat de l’heure T12.

Les règles d’opt-in, une action automatique par tick, déduplication, stabilité,
protection du texte humain et annulation sont conservées. Le ciblé initial est
104réussis/2échecs sur les anciennes attentes2s/60s ; les deux attentes deviennent
30s et génération+attente+tick, assertions maintenues, puis retest2/2réussi.
Les104autres cas ne sont pas rejoués. Six tests purs du verdict et Ruff passent.

Après trois sauvegardes SQL avec integrity_check et restauration sur copies,
un seul redémarrage Agent8001 active le budget30s confirmé par HTTP. Toutes les
tables non volatiles Brain/ERP comparées restent exactes, dont6/17protégées.
Aucun micro, GPU, LLM local ou donnée métier fictive n’est créé par ce contrôle.
Le direct industriel et la recette matérielle restent distincts ; L12 reste ouvert.

[Preuves et sources](../logs/foresight-runtime/automatic-queue-priority-delivery-ROOT-20261016.json).


## Index de clôture au16octobre2026

La [matrice d’acceptation](40_FORESIGHT_ACCEPTANCE.md) couvre désormais les13lots,
25fonctions et17recettes du plan sans réduire leur portée. Les sources frontend
et assets servis sont inchangés ; les seuls anciens fichiers backend modifiés
depuis le dernier global sont les deux services audio et le test de statut,
couverts par les68tests ciblés et la recette réelle medium CPU/CR.

L’endurance réelle de60min conserve1440ACK/1440fragments et termine ses travaux
STT sans arrêt forcé. Ses trois fenêtres LLM sont terminées, mais le proactif
expire dans chacune en attente : cela ne qualifie pas la priorité complète ou
quinze réponses utiles. Les anciens chiffres sont conservés dans leur portée.
Le jeton courant ne permet toujours pas le montage du volume isolé préparé.
Aucune capture, inférence, coupure réseau ou élévation n’est lancée par cet audit.
L12 reste ouvert ; l’accord audio regroupé déjà demandé reste sans réponse.


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

[Résultats livrés et empreintes](../logs/foresight-runtime/meeting-medium-CPU-delivery-ROOT-20261015.json).


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

[Résultats et empreintes](../logs/foresight-runtime/simplified-endurance-delivery-ROOT-20261015.json).


Point de poursuite T12 V8 (2026-10-15T21:10:55.401794+00:00) : processus74147 confirmé actif
sur son handle, 896 fragments acquittés et deux fenêtres LLM terminées.
Le panneau Transcription a été ouvert après32min : texte rendu, suivi du
direct et retard par piste observés ; aucune visibilité extérieure/P95 déduite.
Les703 sources produit et7 fichiers de build sont inchangés. La fenêtre native
affiche un avertissement car ses GET sont interdits par la fixture sans matériel ;
ce n'est pas un résultat de capture physique. Verdict terminal encore absent.
[Point non terminal](../logs/foresight-runtime/t12-realtime-preparation-root-ready-v8-20261015-c9d32939/ROOT-midpoint-UI-checkpoint.json).


## Recette matérielle regroupée : prévol réel prêt, audio non autorisé

Le nouveau paquet `physical-workflow-20261015` réutilise le chemin WASAPI
ordinaire, avec deux projets et deux séances privés. Neuf tests et13sous-tests
passent ; Ruff et syntaxe passent. Deux prévols réels terminent0, sans modèle
ni capture, avec quatre refus start/resume403 avant périphériques chacun.
Le second prévol est aussi utilisé dans le navigateur : sélection Realtek,
navigation entre projets, actualisation, second onglet et retour à la séance.
Les deux onglets temporaires sont fermés ; l'onglet utilisateur reste intact.

Le clic UI « Démarrer la réunion » est refusé par la revue automatique : les
anciens accords uniques ne couvrent pas une nouvelle ouverture micro/système.
Aucun enregistrement ni contournement ; un nouvel accord groupé couvrira une
fenêtre totale600s et ses pauses/reprises, sans renouvellement par tentative,
sans écoute/transcription/envoi réseau. Le Jabra n'est actuellement pas détecté.
Le contrôleur ne confond pas succès du cycle de vie et qualification matérielle.
T01–T04 matériels et L12 restent ouverts ; T12 réseau continue séparément.

[Préparation et observations](../logs/foresight-runtime/physical-workflow-preflight-ROOT-20261015-c6c0dd50.json).


## T12 V8 : reprise et plafonds simplifiés — 15 octobre 2026

Instruction humaine appliquée : limiter les plafonds arbitraires et avancer.
La capture fictive dispose maintenant d'une boîte d'envoi locale synchronisée,
d'un FIFO par piste et de reprises HTTP avec commande/corps identiques. Les
anciens arrêts forfaitaires sur retard, backlog, RAM et stockage sont retirés.
Les observations sont séparées de la conservation ; le navigateur visible
n'est plus un prérequis fonctionnel. L'échéance globale existante de 4 200 s
et l'arrêt explicite restent conservés. Aucun nouveau microphone, GPU ou LLM local.

26 tests ciblés et 22 sous-tests passent, dont l'exécution simulée de la vraie
route warmup sans fichier UI_READY ; 10 tests du probe JS passent en processus
unique. Les suites produit 943 frontend et 2580 backend restent réutilisées sur
sources inchangées. La revue distincte porte sur le protocole et son delta.
Le premier démarrage V8 s'est arrêté avant modèle sur une lecture UI_READY
résiduelle, corrigée ; son résultat reste conservé (Job vidé naturellement).

État au 2026-10-15T20:33:55.377878+00:00 : **démarré, cadence réelle observée**, 8 ACK uniques observés.
Ce point n'est pas un résultat terminal. Le verdict final sera dans
`logs/foresight-runtime/t12-realtime-preparation-root-ready-v8-20261015-c9d32939/controller-final.json`.
L'ancienne tentative V7 reste échouée ; la lecture corrigée de ses métadonnées
retrouve ses 654 ACK conservés et garde les 1 224 occurrences attendues, sans
inventer de latence visible qualifiée. **L12 reste ouvert.**

[État réel et preuves](../logs/foresight-runtime/T12-V8-resilience-actual-start-ROOT-20261015-a82d42c8.json).


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

## Priorité de livraison : un CR utilisable

Après le retour utilisateur du 15 octobre sur la durée excessive des essais,
le prochain jalon produit est un parcours complet : enregistrer, transcrire,
relire, générer un compte rendu modifiable et l’enregistrer dans le projet.
Les contrôles privés ci-dessous préparent ce jalon ; ils ne constituent pas
une livraison du parcours. Aucun délai fiable n’est annoncé sans essai intégré
réel concluant. La portée L00–L12 reste entière et ses critères restent ouverts
jusqu’aux preuves correspondantes.

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


## Dessins CAO : PNG et texte PDF traités sur CPU, qualité visuelle encore refusée — 15 octobre 2026

L’essai privé V1R2 a réellement utilisé LiteRT-LM 0.18.0 et EG2 complet sur CPU4/768 pour huit vecteurs de rendus PNG et de texte PDF issus de dessins CAO ; les huit originaux DXF/SVG sont conservés et leur extraction reste non prise en charge. La recette toutes modalités reste refusée : deux citations texte sur deux passent au rang1, mais les deux recherches visuelles renvoient un PDF en premier et échouent au critère image. Les deux contrôles négatifs sont vides, sans fuite de projet/version ; les 16 sources et 16 versions sont conservées au rejeu. Aucune lecture CAO native, activation canonique, P95 ou clôture L09/L12 n’est qualifiée.

La recette a terminé en sortie1 après15,544158 s ; encodeur arrêté naturellement avec exit0/EOF, engine et alias fermés/restaurés, fermeture propriétaire confirmée, mais preuve de Job naturel avant cleanup non qualifiée. Les tests globaux déjà exécutés restent2458 réussis et1 ignoré, sans nouveau pytest ni ajout des37 ciblés ; NativeReceipt sur8001 reste à recharger, GPU10 reste une QA pure et permission NVIDIA en attente.

Q01 place l’équerre PDF devant la plaque attendue : mauvais dessin et mauvaise modalité au premier rang. Q02 retrouve la bonne équerre, mais en PDF avant son PNG : mauvaise modalité selon le critère scellé. Le classement restreint après coup aux images est seulement un diagnostic ; aucun filtre n’a été exécuté dans R2 et aucune réussite images2/2 n’est qualifiée.

Piste future non testée : un filtre Images/Textes choisi explicitement par l’utilisateur dans la Bibliothèque de sources, recherchant toutes les sources autorisées du projet selon cette modalité. Il ne change ni les annotations, ni les questions ou critères de l’essai conservé et ne valide pas rétroactivement les deux images ; la cause initiale V1R1 reste inconnue.

[Résultat réel et limites](../logs/foresight-runtime/CAD-V1R2-progress-ROOT-20261015-b53d0468cd4c4816a558029f07261d94.json).


## Reçus audio corrigés dans les sources ; rechargement en attente — 15 octobre 2026

Le rejeu audio confirme désormais chaque fragment en SQL et répare atomiquement le reçu local, en conservant ses anciens octets ; ses 37 tests ciblés passent séparément du décompte global. Le rechargement d’Agent 8001 reste en attente : l’inactivité des jalons et des travaux documentaires et l’identité du module chargé ne sont pas établies. L’essai CPU CAO V1R1 a été refusé avant admission du moteur, avec 16 sources privées conservées et huit entrées échouées ; une copie V1R2 est en préparation privée, sans nouvelle recette exécutée. La QA du profil GPU privé passe dix contrats purs, sans mesure GPU, capacité, SQL ou appareil ; les droits NVIDIA, la recette couplée et L03/T16 matériel/P95/T12/L12 restent ouverts.

Suite backend globale : 2459 cas uniques, 2458 passés, 0 échecs, 0 erreurs et 1 ignorés ; sortie 0.

Le décompte global vient de son JUnit réel ; aucun ajout des 37 ciblées. Ancien indicateur Stop false et addendum distinct true conservés, calcul distant inconnu. La recette CAO V1R1 réelle a importé 16 sources et 16 versions privées, mais les huit entrées ont échoué, aucun node n’a été admis et aucun chargement du modèle n’est prouvé : sortie 1 en 7,6873437 s, originaux intacts, fermeture propriétaire confirmée. La cause initiale reste inconnue derrière l’erreur générique ; V1R2 prépare sa collecte sur une copie distincte, sans nouvel essai réel. Une faute ENOSPC injectée sur reçu ne qualifie pas le manifeste natif amont ni une saturation physique.

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

Le nouvel écrivain synchronise réellement PAIR_ARMED avant ACK et Start. Le refus source V5R3 reste conservé. Deux engines, huit connexions SQL privées et dix self-pipes sont fermés ; les cinq boucles originales sont fermées. L’évaluation déterministe après terminal confirme la chaîne locale, sans mesure de P95 ni preuve d’arrêt du calcul distant. Le profil CPU deux pistes reste insuffisant ; le prochain profil GPU reste une préparation distincte.


## Direct deux pistes CPU — débit insuffisant constaté, 14 octobre 2026

L’essai réel medium CPU4 a traité les 16 fragments fictifs des deux pistes. Une paire de fragments arrive toutes les 5 s, mais les paires complètes à chaud demandent 10,45 à 11,70 s : la file augmente. Ce profil échoue au débit de cette cohorte. La recette termine aussi en refus de contrôle, sortie 1. **Direct, précision industrielle, P95, T12 et L12 restent ouverts.**

[Résultat et preuves](../logs/foresight-runtime/DIRECT-V2-actual-objective-status-ROOT-20261014.json). 28 tests purs réussis ; aucune nouvelle suite globale.

Les 8 paires totalisent 37,5 s par piste, 75 s au total ; les deux pistes reprennent les mêmes voix fictives. Les horloges du driver donnent une moyenne de 10,964 s par paire complète à chaud, de 2 à 10 demandes encore en cours ou en attente juste après chaque arrivée, et 53,383 s pour terminer après la dernière arrivée. Il ne s’agit ni du seul calcul neuronal ni du délai après fin de parole jusqu’à l’affichage. Les 16 demandes/réponses et leurs empreintes sont conservées ; les originaux et fragments restent intacts. La réutilisation du fichier PCM dérivé est distincte d’une perte des originaux.

Le contrôle final reste en échec après les refus d’accès à NUL consignés au journal et ne fournit pas de reçu terminal naturel dédié. Le processus extérieur est sorti, le Job est vide et les handles sont fermés. Après ce terminal, 392 fichiers sources et poids ont été relus avec empreintes exactes ; cela ne transforme pas le refus initial en réussite. Aucun micro, GPU, service LM Studio, stockage SQL ou affichage Studio utilisé par ce diagnostic. Aucun profil de production changé. Les préparations des sections antérieures restent des éléments historiques.


## Recette assistant V5R2 — résultat partiel, 14 octobre 2026

La recette courte V5R2 a réellement ouvert l’assistant sur une copie fictive et obtenu une réponse réseau sourcée conservant 1250 W, les réserves et les négations. La paire concurrente n’a pas démarré ; annulation et services de fond non exécutés. Le thread de fermeture a été refusé : sortie1, cleanup non qualifié. Les ressources privées sont fermées et les données protégées conservées. **G_ASSISTANT, P95, T12 et L12 restent ouverts.**

[Résultat ROOT](../logs/foresight-runtime/G-ASSISTANT-V5R2-actual-objective-status-ROOT-20261014.json) ; [audit indépendant](../logs/foresight-runtime/G-ASSISTANT-V5R2-partial-actual-independent-audit-remaining-20261014.json).

QA ROOT liée au plan V5R2 :86 cas Python et8 JavaScript réussis ; les anciens cas identiques ne sont pas additionnés comme nouveaux tests. Le préflight réel couvre949 jobs sur cinq pages, une séance et les processus connus, sans audio actif. Un seul POST owner-browser,2559 caractères,181 observations du vrai propriétaire et zéro POST pair. L’armement lexical n’a pas de témoin durable : sa cause n’est pas reconstruite. Le refus Thread-1 (_do_shutdown) concorde avec la source asyncio ; la cible/stack réelle n’a pas été capturée. Deux engines/sept connexions, listener, quatre self-pipes, threads/SSE et Job sont réellement fermés. Durée89,943s avec publication ; aucun critère d’assistant ou de performance clôturé. Les refus prélaunch V5/V5R1 restent conservés. Aucune activation, aucun code/SQL/réglage canonique, modèle local, commit ou push dans ce complément.


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


## Complément courant après les indicateurs — 13 octobre 2026

Le [nouvel audit des exigences](../.ui-preview/pilots/l12-current-audit-20261013-after-ui/audit.md)
conserve les 77 critères originaux : 51 preuves bornées, 24 incomplètes,
une indirecte et une manquante. Ce classement n'est pas un pourcentage
d'achèvement. Les huit familles ouvertes y sont identifiées ; les recettes
déjà closes dans leur portée restent closes. **T12 et L12 restent ouverts.**

La QA frontend publiée le 13 octobre est 916/916 dans 88 fichiers. La version servie contient
les indicateurs et le parcours CDC, vérifiés avec une API fictive et le build
réel. Les 887 tests plus bas correspondent à la publication antérieure.
[QA actuelle](../.ui-preview/pilots/async-feedback-20261013/qa/qualification.json) ;
[publication et HTTP](../logs/foresight-runtime/async-feedback-current-verification-20261013.json).

Le diagnostic CPU de précision a réellement rendu deux réponses sur le même
WAV fictif : calcul chargé int8_float32 puis float32, PCM décodé, VAD et options
identiques, deux Jobs fermés, 9,658 s avec publication. Les deux réponses gardent
1250 W → 2250 W. Une seule phrase ne qualifie ni une précision générale ni un
gain de performance ; le profil de production reste inchangé.
[Interprétation ROOT](../logs/foresight-runtime/t12-cpu-precision-root-interpretation-20261013.json).

La recette historique ne transmettait pas la preuve extérieure de visibilité
au collecteur. La copie isolée V4R2 raccorde les exports UI/CUA, exige leur
identité avant warmup puis leur export terminal avant fermeture, dans le budget
existant. Ses quatre tests purs passent après revue indépendante. Elle exige
encore une préparation fraîche et une calibration UI réelle ; aucun nouveau
serveur, moteur ou essai long n'a été lancé par ces tests.
[Contrat](../.ui-preview/pilots/t12-visible-bindings-controller-v4r2-20261013-bd9f046265ab/PLAN_CONTRACT_V4.md) ;
[QA pure](../logs/foresight-runtime/t12-visible-bindings-v4r2-root-pure-tests-20261013.json).

L'heure antérieure garde ses résultats : 62 premières présences DOM, dont 25
ambiguës ; 37 segments univoques correspondent à 30 occurrences, exclues faute
de preuve extérieure. Les 1 194 autres occurrences comprennent 1 141 sans STT
et 53 traitées sans première présence univoque. Le P95 reste non qualifié ;
aucune observation n'est reconstruite. Les nouvelles preuves sont des
compléments distincts, sans réécriture des reçus précédents.


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

## Recettes courtes réellement effectuées — 13 octobre 2026

Le premier serveur UI a réellement refusé le départ (HTTP 409), faute de
préflight extérieur rattaché à son installation, puis a été fermé sans livraison.
[Reçu négatif](../logs/foresight-runtime/t12-ui-calibration-99174bd5575849f9a0a7476e61ff741c/ROOT-negative-preflight-and-stop.json).

La recette distincte V1R2 a livré quatre textes fictifs pendant 60 secondes.
Le terminal a réellement raccordé six échantillons uniques, retenus dans
14 lignes d'exports. Quatre premières présences ont été observées, dont trois
rattachées à des constats CUA/captures ; une reste sans ce rattachement.
Le panneau Transcription était initialement sous les notes, hors du viewport.
Le scroll et les changements de dimensions ultérieurs sont conservés. La
liaison des exports est vérifiée, mais la calibration initiale reste non
qualifiée ; aucun délai parole→texte ni P95 n'est produit.
[Interprétation UI](../logs/foresight-runtime/t12-ui-calibration-bea3b93297674911bc1ed8d60d60596d/ROOT-terminal-partial-review.json).

Le processus, son Job, ses handles, le socket et les handlers ont été fermés.
Le constat extérieur après publication borne le total à 764,845 secondes,
inférieur au plafond de 900 secondes. Aucun microphone, modèle ou SQL de
production n'a été utilisé par ces fixtures d'interface.
[Borne et fermeture](../logs/foresight-runtime/t12-ui-calibration-bea3b93297674911bc1ed8d60d60596d/ROOT-terminal-duration-proof.json).

Le comparatif medium CPU V1 a réellement échoué avec une erreur d'allocation
avant constructeur/ready et avant toute réponse. Son Job est fermé. Le pic
près de son quota de 3 GiB soutient une hypothèse de quota trop faible, sans
prouver une cause exclusive. V2 change seulement le quota à 6 GiB et le seuil
de mémoire physique libre à 9 GiB, avec les mêmes entrées/options et 180 secondes
maximum. Son lancement réel a été refusé par ce seuil avant tout worker, en
0,0149593 seconde avec publication. La valeur exacte de mémoire disponible
n'a pas été retenue avant le refus. Aucun résultat de transcription, d'encodage,
de qualité ou de gain de performance n'est établi ; aucun seuil n'est abaissé.
[Interprétation CPU ROOT](../logs/foresight-runtime/t12-medium-consolidation-root-interpretation-20261013.json).

L'ancien préflight CPU annonçait `pending_session_chunks=0` depuis un champ
`chunks` absent du DTO de liste : ce compteur n'était pas observé. Le reçu
original est préservé. Le préflight V2 corrigé lit strictement les compteurs
réels `transcription_admission.admitted_chunks` et les états de batch ; il
constate zéro admission directe et zéro batch actif à cet instant seulement.
Il ne prouve aucune exclusivité continue.

Les préparations suivantes restent sans qualification ni activation.
**T12/L12 restent ouverts. Le suivi automatique de l'objectif a été constaté
en pause ; les nouvelles préparations/recettes sont arrêtées.** Ce complément
consigne les essais déjà effectués sans réécrire les audits/reçus historiques.


---

Objectif autorisé le 11 octobre 2026 : sauvegarder l'état courant puis réaliser
les lots L00 à L12 du [plan](37_FORESIGHT_FUSION_PLAN.md). Les fonctions sont
qualifiées séparément : développées, activées, réellement vérifiées.

## Correction de charge des contrôles natifs — régression logicielle qualifiée

L’audit de longue séance trouve une duplication mémoire des notifications
`chunk`, déjà conservées avec fichiers, journaux et reçus SQL. La correction
retire cette duplication et limite la file à huit contrôles, avec erreur
prioritaire et interruption explicite en cas de saturation. Le STOP est confirmé
après EOF et sortie 0. Le reçu serveur de drainage protège la reprise ; un arrêt
non confirmé est rejeté durablement, sans faux succès au deuxième appel.
Une conservation partielle distincte garde son avertissement après finalisation.
Les contrôles et la barre globale rendent sa récupération accessible.

Sauvegarde des sources avant modification :
`backups/native-control-queue-20261012-133005/`. Dernier ciblé natif/routes
**38/38**, React désormais **802/802 dans 81 fichiers**, TypeScript/build et Ruff
réussis. La V1 globale termine à **2 183 réussis/1 ignoré**, exit0, mais trois
sources ont changé et un test a été ajouté : elle ne qualifie pas l’état final.
La V2 `native-control-queue-global-20261012-v2/` termine à **2 190 réussis/1
ignoré**, exit0, en 1 916,10 s sur 371 sources inchangées, bases/TEMP/cache neufs
(session 47379 terminée). Le
[reçu terminal](../logs/foresight-runtime/native-control-queue-20261012/python-v2-terminal.json)
revérifie les sources courantes ; il exclut le prochain candidat STT isolé.

Le parcours notes XPilot a relancé le processus 8001 ; ses assets
`1Pn4h413/B17lYRwK` correspondent au build vérifié sur 218 sources frontend
inchangées. Le chargement des gardes natifs est déduit du démarrage après leurs
modifications, sans attestation de hash en mémoire. Les opt-ins général/direct
sont maintenant observés actifs ; aucune nouvelle qualification industrielle
n’en découle. Sur bases fictives, le Studio courant présente un seul geste de
conservation partielle, son avertissement, les sélecteurs et le démarrage.
Aucun microphone ni modèle n’a été lancé par cette vérification, et son serveur
privé est fermé. Le [reçu courant](../logs/foresight-runtime/native-control-queue-20261012/current-evidence.json)
relie tests, sources, assets HTTP, observations et capture.
**T12 et L12 restent ouverts**, notamment le stock SQL STT non borné et les
essais industriels/matériels. Aucun commit/push effectué par ce lot.

L’admission bornée du direct et le traitement complet personnel sont réalisés
sur la copie source `.ui-preview/pilots/stt-admission-stage-20261012/`, sans
écriture canonique ni modèle/matériel. Le premier frontend y passe 806/806 ;
le frontend final V5 passe **816/816**, TypeScript/build sur 218 sources
inchangées (`qa/frontend-final-v5/qualification.json`). La V4 conserve ses
816 tests réussis mais son échec de typage du test ; la V5 inclut la correction.
La V1 Python termine à **2 290 réussis/2 échecs/2 ignorés**, 377 sources
inchangées. Les ressources Thunderbird manquantes sont ajoutées et le test de
correction humaine passe désormais par la reprise explicite. Le ciblé final
passe **153 réussis/1 ignoré** ; le mélange synthétique ignoré est vérifié
séparément. La V2 complète termine à **2 300 réussis/2 ignorés**, exit0, en
2 063,96 s à 16:12:01 UTC (session 18749 terminée). Ses 377 sources et 56 ressources
sont inchangées pendant la passe et correspondent encore aux empreintes
revérifiées. Le [compagnon terminal V5](../.ui-preview/pilots/stt-admission-stage-20261012/qa/staged-checkpoint-v5-python-v2-terminal.json)
relie rapport, JUnit et contrôle courant sans remplacer le checkpoint V5
historique, qui indiquait alors une passe en cours.
Le batch général-off est corrigé et relu, avec huit nouvelles régressions dans
le ciblé : rejouer/consulter/annuler reste accessible, le direct seul désactivé
ne coupe pas le batch, et un échec d'autre arrêt n'empêche pas sa fermeture.
Les alertes de lecture résolues sont corrigées avec neuf régressions, sans
effacer les refus de sauvegarde. La recette fictive V5 observe neuf éléments
attendus, deux sélecteurs actifs et aucun « Failed to fetch » résiduel ; elle
ne lance ni acquisition ni traitement. La cause du transport initial n'est
pas attribuée. La conservation sous cadence fictive est qualifiée : l'ancien
essai complet de cadence échoué reste conservé et la nouvelle mesure des acquittements
est revue. Son smoke fictif de 30 secondes est réussi : six paires/12 fragments,
note/export/reçus inchangés et retour ACK maximal de 0,047453 s. Le full de
3 600 secondes est terminé sur le même seal : 720 paires/1 440 fragments,
ACK maximal 0,177379 s, dernier ACK à 3 600,0556 s, note et tous les SHA des
WAV exportés préservés. Le quota reste à 24 fragments/120 000 ms. Les 48
failed sont simulés ; 1 368 retained demeurent conservés hors admission,
sans transcription faussement terminée. Le
[résultat terminal](../logs/foresight-runtime/sqc-run-20261012-163237-ddd94164/qualification.json)
et sa relecture indépendante confirment les deux engines fermés, aucun
enfant/thread ni inférence. Les sept portes fichiers de promotion passent ;
l'absence d'activité et les sauvegardes restent à contrôler. Le candidat
reste non activé ; T12/L12, capture intégrée,
qualité industrielle et P95 visible ne sont pas qualifiés par ces tests.
Ce candidat ne change aucun verdict de
la version active ni les seuils industriels. Un essai GPU distinct échoue
au premier encode, après chargement du modèle, sur `cublas64_12.dll` absente
ou non chargeable. Son
[reçu de fermeture](../logs/foresight-runtime/gpu-short-run-20261012-173342-f7bc6d33/qualification.json)
confirme sortie et Job vide en 7,902 s, sans transcription produite. Aucun
profil GPU produit n'est activé. La sélection personnelle évite
d'imposer un projet ou de retirer la transcription d'un import long/inconnu.

Le contrôle daté `native-control-queue-20261012/preservation-before.json` retrouve
à 11:33 UTC un mail écarté via l’API à 09:06 UTC, avec deux propositions, une
décision de rejet automatique et un artefact retirés. L’utilisateur confirme
directement que cet écartement était volontaire. Le backup dédié reste intègre
et l’EML de 16 198 octets conserve son SHA exact. Le
[`receipt de décision`](../logs/foresight-runtime/native-control-queue-20261012/user-retention-decision.json)
borne cette confirmation à ce mail ; aucun rétablissement n’est effectué.
L’activité Mail continue ensuite de modifier le canon : ce relevé historique
ne prétend pas à une égalité exacte des bases actuelles. L’input de réseau
indépendant est vérifié par PDF/hash/racine NetworkLink et clé de producteur,
sans ID Brain attendu ni attribution d’auteur/date d’écriture inventée.

## Candidat regroupé NEXT — non activé

Les [26 fichiers V2](../.ui-preview/pilots/native-interruption-next-20261012/candidate-promotion-manifest-v2.json)
regroupent admission STT et récupération native : 19 remplacements à sauvegarder,
sept nouveaux fichiers. Le ciblé backend final passe 70/70 avec revue indépendante ;
le frontend complet passe 858/858, TypeScript/build, sur 221 sources/configurations
inchangées. La régression complète Python V1, lancée à 17:57:10 UTC, termine à
18:29:42 UTC : **2 330 réussis, 2 échecs et 2 ignorés**, sortie 1, sur 378 sources
et 57 ressources inchangées. Le [reçu terminal](../.ui-preview/pilots/native-interruption-next-20261012/qa/python-global-next-v1/qualification.json)
conserve les échecs de l'export avec changement de droits et de la garde propriétaire
natif. Les deux fixtures sont corrigées sans modifier le produit : le hook ZIP est
limité à la vraie fermeture du candidat courant, et le double natif utilise
le garde propriétaire actuel. Les refus 404/409/403 et la conservation restent
exigés. Le ciblé passe 73/73 avec revue indépendante. La V2 complète, lancée à
18:46:51 UTC, termine à **19:24:29 UTC : 2 332 réussis/2 ignorés**, soit 2 334 cas,
zéro échec/erreur, sortie 0 et **378 sources Python/57 ressources inchangées**.
Le [global V2](../.ui-preview/pilots/native-interruption-next-20261012/qa/python-global-next-v2/qualification.json)
et son [compagnon terminal](../.ui-preview/pilots/native-interruption-next-20261012/qa/python-global-next-v2/root-terminal-companion.json)
conservent ce résultat ; le [Ruff global V2](../.ui-preview/pilots/native-interruption-next-20261012/qa/ruff-final-20261012-192805-8cc955c5/qualification.json)
termine sortie 0 sur les mêmes 378 sources. Le correctif responsive externe passe
séparément 858 tests/TypeScript/build ; sa vérification navigateur reste à réaliser.
NEXT n'est pas activé, et ces preuves ne clôturent ni T12, ni T13, ni L12. Le
[manifest V2 de 26 fichiers](../.ui-preview/pilots/native-interruption-next-20261012/candidate-promotion-manifest-v2.json)
conserve sept fichiers nouveaux et compte dix-neuf remplacements.
La porte opérationnelle datée de 17:48 UTC observe une analyse de jalons en cours
et huit en attente. Les quatre opt-ins Foresight sont actifs ; aucune qualification
industrielle n'en découle. Aucun arrêt de ces travaux, permutation ou modification
des réglages n'est effectué. Un nouvel accord utilisateur autorise les bibliothèques
NVIDIA privées et un seul nouvel essai fictif de cinq minutes ; le précédent échec
GPU reste conservé. Le verdict de la production et L12 restent distincts.

L'essai GPU V5 est maintenant terminé, avec verdict opérationnel false :
douze phrases fictives transcrites, 27 informations critiques préservées dans
les phrases complètes, mais contrôle d'origine d'une DLL non validé et fenêtres
courtes incomplètes sur mm². Sa
[revue des textes sauvegardés](../logs/foresight-runtime/gpu-short-run-20261012-181408-3771563f/root-semantic-review.json)
sépare ces faits du débit affiché, de la qualité industrielle et de T12.
Fermeture processus/Job/NVML confirmée en 22,042 s ; l'accord unique est consommé,
sans activation ni nouvelle tentative. Le diagnostic suivant est statique.

## Livraison historique du parcours de réunion — 12 octobre 2026

La livraison `logs/meeting-launch-ui-20261012/delivery.json` vérifie les assets
`By33yhqn/DaoAx8MJ`, la santé Agent/Brain/ERP et le formulaire de création sur
**8001**. **780 tests React dans 80 fichiers**, TypeScript, Vite et Ruff passent.
Nouvelle séance reste visible lorsque l’espace est désactivé ; l’activation
est explicite et conserve les autres réglages. Microphone, sortie Windows et
Démarrer la réunion sont exposés hors Préparation ; Pause et Arrêt restent
accessibles. Le Studio est contrôlé sur des bases fictives avec inventaire
simulé et acquisition interdite. Les flags canon sont faux à ce checkpoint, aucune séance
fictive ni capture réelle n’a été créée. Sauvegarde :
`backups/meeting-launch-ui-20261012-120052/`.

Cette livraison améliore L06/T13 et l’accès à L02 ; elle ne qualifie ni la
capture matérielle intégrée, ni le direct industriel, ni la cadence T12.
L’interface actuelle et ses tests ne sont plus ceux du global React 768
historique ci-dessous. Après le changement de déchargement LLM au retour
réseau, le global Python distinct a terminé **2 158 réussis/1 échec/1 ignoré**
en 2 700,19 s. L’échec d’isolation de `session_proactive._stop`, reproduit en
ordre, est corrigé dans le seul test ; la reprise de 99 cas réussit. Ces
reprises ne constituent pas une nouvelle suite globale verte. Reçus :
`logs/llm-recovery-global-20261012-105917/final-verification.json` et
`.pytest_work/lr-final-targeted-114812/junit.xml`. **L12 reste ouvert.**

## Complément logiciel du direct — 12 octobre 2026, régression qualifiée

La revue a conduit à séparer l'opt-in de transcription directe de l'activation
générale, rendre la reprise des seuls fragments échoués explicite et protéger
les corrections non enregistrées contre une recharge. Le suivi d'événements
réveille les lectures canoniques, sans appliquer de texte événementiel au
brouillon. Une enveloppe minimale supprime un risque d'extrait interprojets
dans les anciens événements de réponse ; les événements DB restent intacts.
Le SDK borne chaque frame, indépendamment du regroupement des lectures réseau.

49 tests backend, neuf tests de replay/suivi SQL et 81 tests de l'éditeur
passent dans leurs rapports distincts. La qualification complète V3 historique passe
**2 141 Python réussis/1 ignoré**, soit 2 142 cas sans échec ni erreur, en
1 804,97 s, exit0, sur 369 sources inchangées. Le reçu
[global V3](../logs/foresight-runtime/live-controls-global-20261012-v3/qualification.json)
termine à 05:57:16,374 UTC. React atteint
**768/768 dans 80 fichiers**, TypeScript/build passent sur 216 sources inchangées.
Le premier global Python `live-controls-global-20261012-v1/` conserve son
résultat historique **2 084 réussis/1 ignoré**, 1 824,44 s, 368 sources inchangées,
avant le correctif d'export. Le rapport React
`live-controls-frontend-global-20261012-v1/` reste distinct ; les ciblés
recouvrent ces globals et ne s'ajoutent pas à leurs totaux.

Une recette textuelle isolée ouvre le suivi HTTP, affiche un segment fictif
sans audio, conserve le brouillon puis la note ERP v2 après Sources/recharge.
Douze contrôles API/SQLite et quatre observations CUA sont distingués dans
`live-controls-browser-fixture-20261012-033457-4672efd2/browser-qualification-v2.json`.
Le panneau navigateur masqué et l'absence d'attribution chronométrée événement/
poll interdisent toute mesure de latence. Les deux erreurs du lecteur de preuve
(encodage stdout puis mauvaise recherche de la note ERP dans le staging Brain)
sont archivées, sans changement produit pour les corriger. La fixture est fermée.

La revue complémentaire confirme un contournement des droits dans l'export
des anciens événements de réponse : lecture de la séance seule puis payloads
bruts de projets devenus inaccessibles. Le correctif V3 est appliqué après
le premier global, avec 57 tests de staging et 18 contrôles RO favorables.
Il conserve les anciennes versions de la note liée à la séance, les Sources
publiées autorisées d'autres séances et le calendrier humain attaché. Les
payloads non autorisés sont masqués dans l'archive restreinte ; les événements
DB originaux restent intacts. La cible sur produit sans plugin staging passe
99/99 et Ruff. Le global Python V3 réussi couvre ce delta ; le premier global
ne le couvrait pas. Les reçus V1/V2 et la réserve V2 restent historiques.
La livraison canonique est maintenant vérifiée sur8001 :
`backups/foresight-live-controls-delivery-20261012-060833-488129/` sauvegarde
1 359 pièces et restaure Brain/ERP avec intégrité SQLite correcte. Les preuves
HTTP `live-controls-canonical-delivery-20261012-v1/{runtime,controls}.json`
confirment le build `B8cwhgBe/BJ0BE6LI`, la santé et les quatre opt-ins faux.
Le contrôle de conservation retrouve exactement les 18 tables métier protégées
et les 1 340 originaux initiaux. Trois tables de suivi héritées évoluent,
sans suppression de lignes ; l'attribution à leurs workers reste une inférence.
Les deux essais de checkpoint antérieurs restent conservés : sidecars EG2
temporaires devenus absents, puis suffixe URL du favicon traité comme nom disque.
Le seul lanceur de livraison ferme ses connexions SQLite avant le manifeste
et extrait les chemins des URL. Le service général de sauvegarde reste inchangé ;
aucune pièce ni entrée de manifeste n'est retirée pour faire passer le contrôle.

La passe complète V2 conserve 2 123 réussites, 18 échecs et un ignoré en
2 294,42 s sur 369 sources inchangées. Seize traces signalent un stockage
privé `AppData/Temp/minipilot-test-*/storage/raw` introuvable ; deux scans
rapportent zéro import à la suite de cette erreur. Deux racines de workers
sont concernées, sans preuve d'un stockage partagé ou de l'acteur de la
disparition. Le lanceur ne fixait pas TEMP/TMP. La
[reprise ciblée](../logs/foresight-runtime/live-controls-failed18-retake-20261012-v3/qualification.json)
passe **18/18 en 7,21 s**, sans changement produit ni assertion. La V3 utilise
ensuite des TEMP/TMP/TMPDIR courts sous `.pytest_work/`, avec des dossiers ENV,
basetemp, caches et rapports distincts de cette reprise. Les échecs V2 ne sont
pas effacés et les 18 reprises ne s'ajoutent pas aux 2 141 réussites du global.

La priorité aux séances en capture ne borne pas la file globale ni sa durée.
Le suivi SSE de 30 s est une borne logique, sans garantie d'arrêt mural d'une
lecture SQL ou d'un client lent ; le SDK limite sa connexion à 35 s. Aucun de
ces changements ne qualifie le délai voix-vers-premier-segment, la qualité
industrielle, le matériel ou T12. Le nouveau gel préparatoire de06:09:42 UTC
lie 32 ressources matérielles et 13 contrôles T12 aux sources et assets livrés.
Revue exacte et GO restent distincts. Le navigateur est désormais réellement
visible (observation CUA06:10:51 UTC), sans UI_READY de séance créée à ce stade.
Ces gels seuls ne créent aucun GO et ne consomment aucun accord matériel.

### Premier essai T12 sur le logiciel livré

Le paquet d'exécution `t12-realtime-preparation-20261012-061344-977401ad`
est lié à `ff77e064…` et à la revue exacte `5df80d92…`. Un GO technique root
distinct lance le contrôleur ; il se termine à06:20:19 UTC avant ready/cadence.
Le harnais d'audit traite l'argument Windows normal `executable=None` comme
un chemin et lève `TypeError`. `driver_exit=null`, fixtureexit1, aucun UI_READY,
aucune fenêtre LLM ni cadence60min n'est exercée. Les vérifications d'identité
ont lu les poids locaux ; aucune qualification d'inférence n'est acquise.
Le Job est vide avant fermeture, sans terminaison forcée ; handles, moniteur
et watchdog sont fermés/sortis. Les rapports, console et sentinel d'essai sont
conservés. Le correctif du harnais, ses tests ciblés, un nouveau paquet et
une revue/GO distincts sont requis ; les sources produit369/216 restent inchangées.

Le correctif d'audit None passe70/70 dans
`t12-audit-guard-qualification-20261012-062324-e5818364/`.
Le deuxième paquet `t12-realtime-preparation-20261012-062508-21757896` démarre
le résident mais le panneau devient visible après le délai de180s ; aucun
UI_READY n'est fabriqué et le nettoyage naturel passe. Le rechargement préalable
de Gemma et le lancement de la recette sont explicitement autorisés
(`call_30ec712ce7374298859f95395eafc0ec`). Le modèle est rechargé8192 hors budget
du contrôleur ; la fixture conserve l'interdiction d'auto-chargement.

Le troisième paquet `t12-realtime-preparation-20261012-073309-0c8fb3d0`
reçoit UI_READY réel à07:36:45UTC, onglet22 sélectionné/navigateur/panneau visibles.
La trace confirme resume produit200 puis `/_t12/cadence` privé422 ; aucun
`cadence.server-start`, zéroACK et aucune cadence réelle. L'annotation Request
différée avec import local concerne le seul harnais. Stop privé200, Job final0,
handles/moniteur/watchdog terminés ; fermeture forcée et sortie fixture inconnue
gardent le verdict de nettoyage naturel faux. Les trois essais ne qualifient
ni60minutes ni latence voix/affichage. Le correctif HTTP et la fermeture bornée
du flux restent à tester puis à requalifier réellement.

### Quatrième essai arrêté aux premiers uploads ; cinquième essai lancé

Le correctif du harnais Request/fermeture ASGI passe80/80 dans
`t12-request-shutdown-final-20261012-074858-164b87ca/`. Le paquet
`t12-realtime-preparation-20261012-075037-f05722cc`, SHA `6499c8eb…`, atteint
resume produit200 et cadence privée200. Cinq secondes plus tard, les deux
premiers uploads de séquence0 échouent avec HTTP500 : la console conserve
`FileNotFoundError` dans `_write_file`, ouverture des fichiers `.wav.pending`
de278/281 caractères dont les parents existent. Les observateurs appellent
le vrai store ; aucun défaut de signature commit n'est retenu.
Le [reçu final](../logs/foresight-runtime/t12-realtime-preparation-20261012-075037-f05722cc/controller-final.json)
et le driver conservent **zéroACK**, trois événements SSE initiaux et zéro segment.
La sortie fixture0, le Job vide avant CloseHandle, les handles fermés et les
threads contrôleur sortis attestent cette fois une fermeture naturelle propre.
Ce succès de nettoyage ne qualifie ni60minutes, ni ASR, ni latence d'affichage.
Les bases privées, console, traces et données antérieures restent intactes.

La correction bornée du contrôleur crée un dossier frère sous LOGS, lié au
nonce32, exclusif et vérifié avant Popen : `.wav.pending` mic228/system231
caractères, seuil de compatibilité Windows inférieur à260. La fixture,
les budgets60min/70min, corpus, motifs et profils produit ne changent pas.
Les [88/88 ciblés](../logs/foresight-runtime/t12-storage-path-final-20261012-080347-6f3a5345/qualification.json)
(80 précédents et huit nouveaux, sans cumul de passes) et
[18/18 contrôles RO](../logs/foresight-runtime/t12-realtime-preparation-20261012-080514-4a9929b5/review.json)
réussissent. Le cinquième paquet SHA `f0d5936d…` est lancé par un GO root distinct,
nonce `ad9ac55a339e49d3a153cd432d416010`. UI_READY réel à08:14:20,837UTC
confirme onglet24 sélectionné, navigateur et ongletTranscription visibles.
La fixture sœur est `logs/foresight-runtime/t12-fixture-ad9ac55a339e49d3a153cd432d416010`.
**Ce relevé constate un lancement en cours, sans résultat final de qualification.**
Les remaining_gates et le statut L12 ouvert sont conservés ; aucun succès de
préparation, de revue ou de visibilité initiale ne remplace la recette longue.

### Cinquième essai terminé — arrêt de sécurité à environ12min45s

Le précédent relevé de lancement reste un instantané historique. Le
[driver final](../logs/foresight-runtime/t12-realtime-preparation-20261012-080514-4a9929b5/driver-40a3821d/driver.json)
termine à08:27:12,819225UTC, après un départ à08:14:27,609558UTC : environ
765,21s de driver, pas60minutes. Le collecteur déclenche l'arrêt de
sécurité du harnais lorsque le retard micro atteint605000ms ; système600000ms.
Le seuil est observé à765,106446s de cadence ; la couverture conservée est
765000ms par piste. Ces durées ne sont pas interchangeables. La borne600000ms
reste distincte des quotas produit et des critères de recette.

La DB conserve **306 nouveaux fragments, 153 par piste**. Les307 ACK tracés
incluent un seul rejeu micro séquence120 ; il ne crée pas un307e fragment.
Micro :32 traités/121 en attente. Système :33 traités/120 en attente.
88 segments provisoires sont conservés. Les306 WAV totalisent48973464 octets,
tailles et SHA conformes aux ACK/DB. Le collecteur reçoit375 événements SSE, contre
377 événements DB : ce sont deux mesures distinctes, sans affirmation de
visibilité exhaustive : les derniers événements `chunk.received`376 et
`transcript.interrupted`377 ne sont pas collectés. Cette charge utilise les seuls WAV SAPI fictifs scellés,
le worker Large-v3-turbo CPU int8/4threads de la copie et ses deux pistes ;
aucun profil produit, seuil, annotation ou corpus n'est modifié a posteriori.

Une seule fenêtreLLM (`llm-010`) exerce cinq opérations et trois dispatchs effectifs. La proposition et la
question sont obsolètes, le proactif retourne `InferenceBusy`, les deux
consommateurs d'annulation sortent. Cela ne qualifie pas cinq générations utiles
ni l'arrêt du calcul externe, qui reste inconnu. Les fenêtres `llm-030` et
`llm-050` ne sont pas exercées ; elles ne sont pas comptées comme charge réussie.
La priorité en file reste non qualifiée.
La mesure de latence voix-vers-premier-DOM et la qualité industrielle restent
non qualifiées : ni compute, ni SSE, ni visibilité initiale ne les remplacent.

Le [contrôleur final](../logs/foresight-runtime/t12-realtime-preparation-20261012-080514-4a9929b5/controller-final.json)
reste faux, driverexit1, fixtureexit0. Il atteste Job vide avant CloseHandle,
handles fermés, moniteur/watchdog sortis et fermeture naturelle réussie.
Cette preuve de conservation/fermeture n'efface pas l'échec de tenue en charge.
Gemma est déchargé après repos à08:29:59,524UTC ; le
[reçu](../logs/foresight-runtime/t12-realtime-preparation-20261012-080514-4a9929b5/lmstudio-restored-unloaded.json)
confirme l'absence d'instance chargée et la santé Agent/Brain/ERP.
Les essais antérieurs, pièces, bruts et l'instantané de lancement sont conservés.
La [revue finale](../logs/foresight-runtime/t12-realtime-preparation-20261012-080514-4a9929b5/review-final.json),
SHA `0619b454…`, passe21 points RO de conformité de cet échec/conservation,
avec qualification fausse. Quatre observations navigateur attestent le panneau
visible, sans mesure du premier DOM. L'export du probe n'est pas observé ;
cela ne prouve pas un échec du probe et ne remplace pas sa mesure manquante.
**T12 longue séance non qualifié, L12 ouvert ; remaining_gates inchangés.**

## Sauvegarde préalable vérifiée

Répertoire : `C:\AgentBackups\foresight-before-20261011-173855`.

- `project/` : 16 342 fichiers, 14 741 900 930 octets, copie et SHA-256 comparés
  avec l'original. Inclut `.git`, modifications et fichiers non suivis.
- `data/` : sauvegarde coordonnée de Brain, ERP et pièces gérées, 1 360 fichiers
  avec manifeste et empreintes, Agent arrêté sur 8001 pendant la copie.
- `restore-check/` : restauration dans un dossier neuf ; contrôle d'intégrité
  SQLite `ok` pour les deux bases et validation des pièces/versionnements.
- `full-backup.json`, `git-status.txt`, `git-head.txt`, `working-tree.patch` :
  inventaire, empreintes et état de travail avant réalisation.
- Deux jonctions `node_modules` sont décrites dans le manifeste ; les paquets
  reconstruisibles ne sont pas dupliqués. `package-lock.json` est sauvegardé.
  Recréer les dépendances avec `npm ci` dans une copie restaurée si nécessaire.

Agent a été relancé par son superviseur ; `/health` et `/app/` répondent 200.
Le port 8000 n'a pas été manipulé. Ne jamais restaurer cette ancienne image
sur une production ayant reçu de nouvelles écritures : restauration sur copie
puis réconciliation et désactivation des seules nouvelles capacités.

## État des lots

| Lot | État | Preuve / travail restant |
|---|---|---|
| L00 | Référence publique retenue | Choix utilisateur : écrans publics documentés. [39_REFERENCE_UI](39_FORESIGHT_REFERENCE_UI.md) : Sources PNG, séance GIF et enrichissements ; Graph/Stats/Settings Agent identifiés comme adaptations, sans parité privée revendiquée |
| L01 | Développé, tests réussis | Identités ERP/Brain distinctes, sessions sans projet, révisions, commandes et schémas additives ; aucune donnée fictive créée dans le canon |
| L02 | Développé, qualification partielle | Loopback Realtek réussi ; ancien micro Realtek de 29,9 s conservé ; dernier Jabra : 30 s PCM durables, fermeture en 32,69 s avant 45 s, quota qualifié dans le harnais autonome ; intégration/navigation/loopback casque/remplacement restent ouverts, continuité physique inconnue |
| L03 | Développé, deux workers produit CUDA vérifiés sur trois phrases ; direct industriel complet non qualifié | Batch V4 Turbo CPU beam5 : 15/15, 27/27 attentes propres, 6/8 dégradées, P95 batch complet 24,855 s ; relecture/versions 7/7 sans réparer les omissions. Candidat Parakeet CPU2 séparé : 15/15 phrases, 28/35 strict, P95 calcul 1,285 s, zéro fenêtre5s ; aucun profil produit remplacé. Essais antérieurs conservés |
| L04 | Développé, tests réussis | Version ERP/outbox dans une transaction, reçu Brain, reprise sans doublon, ancienne version exclue du rappel immédiatement |
| L05 | Développé, bascule structurée manuelle corrigée et activée ; tests et admission CPU réussis | Scopes, historique durable partitionné, fraîcheur et droits d’origine/actuels ; index local + SQL ; admission atomique batch/direct, files conservées, budget proactif borné et enfants protégés |
| L06 | Développé, adaptation visuelle validée ; accès direct au CR publié | Trois dispositions dont notes personnelles/enrichies/assistant ; moteur de notes ERP hérité de XPilot, riche/Markdown, versions et brouillons conservés ; recette de notes et clavier sur copie réussie ; navigation pendant capture matérielle encore à qualifier |
| L07 | Développé, tests et essai réel réussis | Question sourcée, proposition d'ajout, acceptation/rejet, conflit et rejeu ; proactif opt-in, désactivé par défaut |
| L08 | Développé, périmètre Drive exclu par l'utilisateur | Catalogue fédéré, labels, originaux/versions, filtres type et format MIME/suffixe distincts avant pagination ; fichiers/dossiers/URL et réinterprétation additive ; ICS conservé. Drive reste désactivé et ne fait plus partie de la livraison |
| L09 | Développé, encodeur/index et corpus annoté réussis | Texte/image/audio 768 dimensions ; 12 questions, Recall@5 sources/citations 1,0, zéro version périmée ou résultat hors projet ; couverture CAO/voix réelles non démontrée |
| L10 | Développé, publication réelle isolée réussie | Un CR/une action/zéro tâche automatique après rejeu, provenance exacte ; audio réel et notes seules, exports historiques préservés |
| L11 | Développé, exécution sous coupure physique qualifiée sur corpus fictif | Nouvelle recette réussie : Whisper + EG2 + Gemma, inventaires avant/pendant/après, sortie0/Job vide ; première tentative F5 conservée ; trafic natif et direct industriel non qualifiés |
| L12 | Recette en cours, CR réels CPU et GPU vérifiés via API privées ; non clôturé | Tests de dépôt, preuve HTTP, conservation, restauration sur copie ; écarts et critères ouverts ci-dessous |

Le choix initial des supports publics a fixé la référence accessible. Après
présentation de la capture du Studio B0MSJycO, l'utilisateur a explicitement
validé l'adaptation à Agent : éditeur riche XPilot, panneaux distincts et
séparation égale des notes. F25/T13 est clos dans cette portée acceptée, sans
parité exacte à ±2 pixels ni accès Mac privé requis. Les mesures et écarts
historiques restent conservés. Google Drive est aussi explicitement exclu et
reste désactivé ; cette recette ne bloque plus L12. Décision directe :
`logs/foresight-runtime/user-scope-decision-20261011-drive-visual.json`.

## Compléments après la première régression

L’audit du plan a reproduit des écarts logiciels : absence de relecture des
conversations et d’épinglage durable, import PDF/tableur par URL identifié HTML,
citations de notes ouvrant une tête actuelle ou du JSON sans aperçu lisible,
et absence du mode Markdown prévu en F09. Ces points font l’objet d’une passe
complémentaire ; les rapports précédents restent conservés et datés.

L’historique est partitionné par séance, périmètre et ensemble de sources ;
sa lecture ne lance pas de génération. L’épinglage est explicite, idempotent,
limité à 50 cartes, conservé hors des 100 cartes récentes. Les droits d’origine
et actuels sont revérifiés, y compris lors d’un déplacement de source. Les
événements de réponse originaux sont immuables. 34 cas ciblés distincts passent
(9 historique, 19 assistant, 3 reprise, 3 preuve courante). Le premier passage
a conservé deux échecs liés aux chemins temporaires Windows de 260 caractères ;
les trois cas de reprise passent ensuite sous un chemin court. Rapports :
`history-audit-final-20261011-824bd199/` et `history-recovery-short-20261011-c7ab/`.

La lecture exacte des versions de staging a passé cinq tests distincts dans
`session-note-versions.xml` : v1 relue après v2 et attribution projet, SHA intact,
404 interséance/absent, droits propriétaire/reader/projet et lecture flag off.
La préparation des citations pointe cette version exacte, sans substitution
de la tête actuelle et sans mutation de note ou d’événement.

Les imports URL passent 26 tests dans `completeness-url-after.log`. La correction
utilise le MIME et un suffixe compatible. Une réinterprétation explicitement
demandée de mêmes octets ajoute une Source dérivée identifiée, garde la version
du catalogue et ses originaux, vérifie SHA/taille et protège le rejeu contre
le retour d’une ancienne tête. Les rapports reproduisant les défauts sont gardés.

`browser-fixture-20261011-182515-3176eac0/citation-links-api-qualification.json`
conserve 53 contrôles HTTP isolés de citations, historique et cartes : originaux
SHA, notes v1/v2, scopes et sources ordonnées/dédoublonnées, restauration sans
LLM, épinglage/rejeu et 404 interséance. La génération y est simulée et indiquée
comme telle ; ce rapport ne qualifie ni audio ni latence du LLM. Le passage
précédent de 48 contrôles reste conservé dans son dossier distinct.

L'enrichissement automatique utilise `auto_enhancement_enabled`, opt-in distinct
des questions proactives. Il observe le même contexte sauvegardé pendant au
moins huit secondes et réserve durablement une tentative avant le LLM. Une
seule action IA est admise par passage ; réponse vide et redémarrage ne lancent
pas de nouvelle tentative automatique sur ce contexte. Une proposition n'écrit
jamais le texte humain avant acceptation. Le délai HTTP de 45 s concerne le
transport et ne borne pas la durée totale de calcul. Le buffer non enregistré
reste exclu ; l'interface indique sa version de base et « Tentative à reprendre »
en l'absence de résultat durable. La qualification de concurrence contrôle les
droits frais, l'origine des citations et l'ordre acceptation/rejet.
Le verrou de séance couvre toute la décision acceptation/rejet dans l'unique
processus API, y compris l'écriture ERP : le perdant obtient 409 sans version
supplémentaire. Plusieurs processus API indépendants nécessiteraient une
réservation durable distincte ; ce déploiement n'est pas qualifié. Les 86 cas
distincts du rapport `completion-supplement-f10.xml` proviennent de deux
exécutions réelles conservées (84 + 2), dont droits retirés, retour de cache,
deux ordres de décision et règles historiques du transport.

Les droits de l'assistant sont revérifiés après rafraîchissement du contexte
et avant retour/écriture d'une réponse. Le déplacement concurrent d'une séance
ou d'une source hors du périmètre provoque 404 sans conservation du résultat.
Le supplément `completion-supplement-assistant-rights-final.xml` passe 34 cas
(six nouveaux de révocation/préparation, 19 assistant, neuf historique).

Le second essai microphone, autorisé explicitement pour une nouvelle fenêtre,
a fermé normalement le flux à START + 30,003 s. Six WAV conservent 29,900 s
(1 435 200 trames par canal). Le quota strict de 30 s manque de 4 800 trames,
soit 100 ms ; `passed:false` et l’erreur de quota restent dans le rapport brut.
Le délai n’a pas été prolongé et le microphone n’a pas été rouvert. Ce résultat
qualifie séparément l’arrêt normal et garde la durée complète ouverte ; il
ne vaut ni écoute ni transcription, ni test casque/changement de périphérique.
Preuve : `qualification/microphone-real-30s-second-authorized-20261011/qualification.json`.

Une nouvelle autorisation explicite a permis un unique test du microphone
`Casque (Jabra Evolve 75)`, après inventaire frais : index 15, 48 kHz stéréo,
non loopback, session interactive 1. START à 19:16:55,366 UTC ; arrêt demandé
à +30,002 s et terminé à +30,004 s. Six WAV (5 × 5 s + 0,9 s) conservent
25,900 s, soit 1 243 200 trames par canal ; le quota manque de 196 800 trames.
Le premier callback arrive à +4,166 s, le premier ADC à +4,076 s ; la cause n'est
pas établie. Le brut `passed:false`, `partial_capture:true` et l'exit 1 sont
conservés. L'audit RO recalcule SHA/tailles/trames des six fichiers, signal non
nul sur les deux canaux (RMS 77,344, crête 3346, aucun écrêtage), fermeture du
flux/PyAudio/Job et sortie de l'enfant 21612. Le contrôle Windows réussi confirme
zéro processus dédié ; la première requête CIM refusée n'est pas utilisée comme
preuve de zéro processus. Cette autorisation est consommée, sans nouvel essai,
écoute, transcription, génération, source ou accès ERP/Brain. Aucun loopback
Jabra ni changement de périphérique en cours de capture n'est testé.
Preuves distinctes : `qualification/headset-jabra-30s-20261011-191634-13ab015a/`.

Les variantes STT supplémentaires ne lèvent pas la porte industrielle. Sur
12 paires, retirer l’alignement des mots garde 27/27 contrôles mais gagne environ
9,6 % seulement, avec un minimum de 6,155 s. Le mel court accélère l’encodage
mais dégrade le décodage : une paire mesurée, 79,862 s contre 12,504 s, repli de
température et répétitions à l’échauffement. L’essai est arrêté tôt ; seuls
2/2 champs de cette phrase ont été remesurés, pas les 27 prévus. La régression
pytest à trois workers était active pendant cette paire : les latences ne
qualifient pas un PC au repos. Aucun profil actif n’a changé. Les rapports
`medium-segments-paired-20261011-v2.json` et `medium-mel-decision-20261011.json`
et [la procédure audio](23_MEETING_AUDIO.md) conservent les limites.

La revue en lecture seule `stt-scope-review-20261011-222213-d9a34c7c/qualification.json`
vérifie les empreintes et la portée des résultats antérieurs ; ses douze contrôles
réussis ne qualifient aucun moteur. Medium et turbo en beam 1 atteignent 27/27
champs sur les douze phrases propres selon leur grille effective, avec P95 de
calcul respectifs de 10,56 s et 9,81 s. Les motifs originaux et les rescoring
différents restent conservés. Sous bruit synthétique, les deux modèles confondent
la consignation avec la continuation ; en chevauchement, une négation disparaît.
Les fenêtres chaudes de cinq secondes dépassent aussi la cible du direct. Aucun
délai de segment visible dans le navigateur n'est établi. Ces essais ne
qualifient pas le parcours batch hérité en beam 5 avec sa diarisation ; sa recette
et la relecture doivent être évaluées séparément, sans effacer les erreurs STT.

La régression React complémentaire passe **672/672 tests, 75 fichiers** en
235,84 s ; TypeScript et build passent. Le dernier changement de libellé F10
passe deux tests ciblés, TypeScript et un nouveau build : `index-NcMllJD2.js`,
SHA-256 `2ca3617f47bd1d6828f53208ce5ddf547d5baf9d6f5d306733f2cd9b5b0992d7`.
Ces deux cas recouvrent la suite précédente ; ils ne s'ajoutent pas à son total.
Ce build précède le correctif Markdown trouvé dans le navigateur : l'ordre des
clés du DTO empêchait la conversion d'une note pourtant représentable. Deux cas
ont été reproduits en échec puis corrigés par une normalisation explicite des
clés, sans élargir le sous-ensemble Markdown admis. Les **97 tests ciblés** passent,
ainsi que TypeScript/build. JS de cette passe : `index-DKlOduK1.js`, SHA-256
`892c4fb213ae70bcb1160851b25475a892a9af9ddaf5f3cdaf6e43bd10861ebd`.
Le rapport `frontend-markdown-dto-followup-20261011-205428.json` conserve la
preuve rouge, les anciens assets et les nouvelles empreintes. Les suites se
recouvrent : aucun nouveau total global n'est fabriqué par addition.

Le passage Python complémentaire brut conserve **1 948 réussis, 16 échecs,
1 ignoré** en 1 719,12 s. Quinze chemins de WAV temporaires mesuraient 262
caractères, dépassant la limite Windows appliquée dans ce contexte. Le seizième
échec est un refus correct de sauvegarde : deux tests du worker STT avaient
écrit des fragments hors du stockage attendu dans la base commune des tests.
Le post-mortem en lecture seule conserve ces deux chemins et leurs fichiers
existants. Les **16 cas repris passent en 43,91 s** avec des chemins courts.
L'isolation des deux tests est corrigée et vérifiée séparément dans l'ordre
runtime puis mail. Les dernières protections F10 ont leurs propres suppléments.
Ces résultats combinés ne constituent pas une passe globale unique sans échec.
La reprise runtime puis mail passe **20/20 cas** en 11,26 s. Les cinq tests
historiques de staging repassent en 13,35 s après sérialisation UTC explicite,
sans modification des dates stockées. La recette visuelle complémentaire est
terminée dans son périmètre de notes seules. Les preuves ci-dessous
à 1 920/569 décrivent explicitement la première passe historique.

`browser-completion-20261011/qualification.json` conserve **21 assertions UI
réussies** sur les seules bases fictives de 18003 : A/B/A et scopes séparés,
épingle après reload, page PDF physique, ancienne note ERP v1 malgré tête v3,
staging v1 à 50 euros malgré tête à 70, Markdown reçu du backend, conversion
explicite vers v3 et persistance après reload. Un tableau Markdown invalide
bloque sauvegarde et finalisation, puis son texte exact est retrouvé après
retour/reouverture. L'avertissement natif de sortie a nécessité une annulation
humaine, consignée ; aucune perte du brouillon n'est masquée. L'opt-in automatique
est sauvegardé/rechargé indépendamment du proactif, puis remis à désactivé dans
la fixture. Aucun moteur ni capture n'est lancé par cette recette.
Le contrôle SQLite RO `database-after-ui.json` passe 29 critères : trois versions
ERP par SHA, cinq blocs en v3 (un titre et quatre paragraphes, dernier en gras),
staging 50/70, une épingle et réponses originales conformes au seed reconstruit.
Les bases sont intègres et inchangées pendant l'audit ; l'absence de snapshot
complet pré-UI limite l'affirmation d'immuabilité historique de chaque colonne.
Zéro CR, action, tâche, enregistrement, fragment ou segment audio est créé dans
ce passage. `shutdown.json` confirme l'arrêt du seul PID possédé 29424/18003,
les bases conservées et Agent 8001 toujours `ok`. Les onglets temporaires sont
fermés, la taille du navigateur et sa visibilité remises à leur état normal.

Les mesures de l'aperçu historique donnent 1265/1265, 655/655 et 305/305 pixels
client/défilement pour les fenêtres 1280/670/320. Un premier réglage 670 avait
touché l'onglet secondaire ; cette tentative est exclue de la qualification et
les captures réellement à 670 et 320 portent le suffixe `-actual`. Le processus
de fixture précède le correctif UTC : l'affichage UTC de staging est qualifié
par les cinq tests API séparés, pas attribué à ces captures anciennes.

## Preuves reproductibles

### Complément Sources, notes XPilot et réseau du 11 octobre

Le catalogue distingue le type métier de source de son format réel. Le MIME
connu prime ; un suffixe compatible distingue notamment texte/Markdown/CSV,
et un MIME générique permet le repli sur le nom. Les notes natives sans fichier
ne deviennent pas artificiellement PDF ou TXT. Les droits et les versions
courantes sont contrôlés avant le filtre et la pagination. La qualification
backend `source-format-followup-20261011/backend-final.xml` passe **102/102 cas**.
La passe interface correspondante passe **80/80 cas sur cinq fichiers** ;
le dernier ajustement de focus repasse **15/15**, sous-ensemble de ces 80 et
jamais présenté comme 95 tests distincts. TypeScript, build et Ruff réussissent.
Le reçu `source-format-fidelity-followup-20261011-215700.json` associe cette
passe à `index-CqjQtHrm.js`, SHA
`5b8a882ff81bb2913a455f157b235ae8340208b5b0d41b80e151647dbf8e8f99`,
et `index-Bu523YUz.css`, SHA
`13f2b86edbc06ff0dec953aa30f239d8827212b34f097ad380bccf8cf0353892`.
Ces assets précèdent les derniers ajustements de hauteur et de navigation.

Dans le navigateur isolé de 18003, PDF puis PNG rendent chacun uniquement leur
fichier fictif, puis le rétablissement de tous les formats retrouve trois
documents. Sur R01 à 1280 × 800, la bibliothèque occupe x104/1160 px et le rail
88 px ; les lignes sont à 50,95–51,35 px. Le tableau commence à y384,1 px,
contre environ y364 px sur l'image publique : aucun verdict ±2 px n'est donné.
À 850 × 479, la première vue complète conserve les trois régions dans le DOM,
mais l'enrichissement commence à y1259,2 px, hors du viewport. Cette présence
DOM n'est pas présentée comme trois panneaux simultanément visibles.

La note reprend `NoteRichEditor`, le versionnement et la sauvegarde ERP de
XPilot. Un seul éditeur subsiste en changeant entre les trois dispositions.
Un nouveau paragraphe Markdown fictif survit aux changements, puis sa conversion
explicite crée la version ERP 2. Après rechargement, le texte et la disposition
complète sont retrouvés, et une réponse basée sur la version 1 est signalée
ancienne. Ces gestes n'ouvrent aucun microphone et ne génèrent aucune réponse.
Le reçu intermédiaire `public-fidelity-final-20261011/checks-CqjQtHrm-before-media-fix.json`
garde **8 contrôles réussis sur 9**, dont le défaut clavier reproduit à une
largeur CSS fractionnaire de 850,2 px. Le seuil de navigation est ensuite
aligné sur les media queries CSS plutôt que sur la largeur entière JavaScript ;
**16/16 tests** passent dans `shell-media-query-final-20261011.xml`.
La nouvelle recette après rebuild demeure distincte de ce reçu intermédiaire.

La recette T11 a été autorisée par la réponse à
`call_a6cd279b6ba64dc980ffa7ac6ea77508`. Le contrôleur a attendu de
19:39:01 à 19:54:01 UTC, puis terminé après 902,83 s avec `passed:false`,
`status:aborted`, délai expiré. Le Wi-Fi est réellement déconnecté sur **158
des 192 inventaires**, entre 19:39:35 et 19:52:13 UTC ; l'utilisateur confirme
la coupure manuelle. F5 est déclaré actif sur 192 inventaires, sans interface IP
ni route visible dans cette collecte. Ce signal ambigu a bloqué la garde :
**zéro enfant, zéro transcription/indexation/génération pendant la coupure**.
Il ne démontre pas que l'accès Internet restait disponible. Le contrôleur n'a
modifié ni adaptateur ni base et aucun microphone n'a été ouvert.
`RECONNECT_NOW.txt` marque la fin de l'attente, sans succès des moteurs.
Le contrôle Windows après arrêt ne retrouve ni le contrôleur possédé 13936
ni un enfant immédiat ; l'exit code du wrapper n'a pas été capturé.
Les rapports bruts sont conservés dans
`.ui-preview/pilots/offline-physical-runs/20261011-213859-2faa854b/` ;
SHA du rapport `08504f5df0d9823262be0eacd286582d1f70c70d8b903935533cf25cbc7f89fb`,
audit final `read-only-timeout-audit-final.json`. Aucun nouvel essai n'est lancé
automatiquement. La qualification physique de calcul et du trafic natif reste ouverte.

Le contrôle du prochain essai est ensuite corrigé et gelé : collecte tous
compartiments, identité GUID/PnP/pilote/bindings de l'interface virtuelle passive,
refus des connexions physiques ou IP inconnues. Le budget total de 840 s commence
avant le signal WAITING et ne se renouvelle pas au lancement des moteurs : travail
jusqu'à 820 s avec réserve de fermeture de 20 s, enfant demandé à 720 s et borné
au temps restant. L'utilisateur doit reconnecter au plus tard à 15 minutes,
même sans marqueur ; ce recours refuse la recette. Les 45 tests purs et leur
revue indépendante passent, sans addition aux 38 précédents.
Le reçu `offline-physical-total-budget-20261011/final-receipt.json` reste une
préparation, sans nouvelle qualification physique. Le préflight réel root à
20:43 réussit avec réseau connecté et gate hors ligne fausse ; la lecture suivante
vérifie 39 relevés SHA/35 chemins distincts et Gemma chargé, sans génération.
Ces preuves séparées sont dans
`.ui-preview/pilots/offline-physical-preflights/20261011-204306-1fa5cab0/`.
Cette préparation est historique ; le créneau a ensuite été confirmé par
`call_C0omChctAz9lVxSHEvqzezV0`, dans l'autorisation existante.

Le nouveau contrôleur termine à **20:53:11 UTC**, en **182,13 s** depuis WAITING,
avec `passed:true`. Le harnais réussit sur quatre sources fictives : STT
Whisper en **5,5914 s**, index EG2 annulé/repris puis rouvert, recherche
texte/image/audio et génération utile de Gemma chargé localement. La coupure
est observée sur **neuf inventaires qualifiés, dont six pendant l'enfant**,
avec un écart maximal de **7,3213 s**. Scratch Brain/ERP/storage est configuré
avant les imports ; aucune capture audio ni changement d'adaptateur.
L'enfant 34820 termine en 43,91 s, sortie 0, Job vide et handles fermés. Le marqueur
de reconnexion est créé après ces confirmations. Rapport neuf immuable :
`.ui-preview/pilots/offline-physical-runs/20261011-225003-77be78b1/qualification.json`,
harnais SHA `f08a505f66133a3bdf5550dcb06aeb22332cbdb48654ef9097ce57dc90d92a48`.
L'ancien échec n'est ni écrasé ni requalifié. La preuve porte sur une coupure
échantillonnée, sans mesure des appels natifs ; elle ne démontre pas le critère
de cinq secondes ni l'exactitude industrielle du direct.
La revue indépendante `t11-success-independent-20261011/qualification.json`
réussit ses 18 contrôles : recalcul de garde sur 33 inventaires, trois préchecks
SHA concordants, scratch/SQLite intègres, résultats utiles et fermeture des
seuls PID 39492/38884/34820. T11 est qualifié dans la portée du plan accepté ;
le compteur natif absent reste une limite, sans nouvelle porte de clôture.

Un nouveau harnais audio autonome est également préparé, sans acquisition :
ouverture demandée au maximum 45 s incluant stabilisation écartée en RAM, quota
strict 30 s PCM/1 440 000 trames par canal, arrêt et fermeture confirmés avant
flush. Ses 61 tests simulés et deux relectures passent ; ils sont hors de la
collecte globale Python. L'inventaire RO récent confirme le Jabra unique, index 15,
48 kHz stéréo, session 1, `capture_started=false`. Le protocole exact est dans
le document 23. Toute ouverture tardive ou non confirmée refuse la qualification ;
aucune garantie de temps réel Windows n'est revendiquée. Cette préparation est
suivie de l'essai unique autorisé par `call_78733e7908d341b6b5fbd900a2273679` :
cinq WAV/**24,1 s PCM**, fermeture normale après **26,5344 s**, quota de 30 s non atteint.
Le seuil ADC technique de 2 ms déclenche l'arrêt sur un delta de 2,3058 ms ; les 247
callbacks ont un statut 0 et 4 800 trames. Ce delta est compatible avec un jitter
d'horodatage/arrivée ; ni perte physique ni continuité matérielle ne sont prouvées.
Le brut `passed:false` et les SHA restent intacts dans
`qualification/headset-jabra-data30-max45-20261011-204752-8993bed8/` ; audit RO
`microphone-data-window-readonly-postmortem-20261011-2050/read-only-diagnostic.json`.
La nouvelle autorisation est consommée. Aucun audio ambiant n'est écouté ou
transcrit, aucune nouvelle ouverture n'est autorisée. Ce test ne qualifie à lui seul
ni T01/T04 navigateur, ni loopback casque, ni direct industriel.

Après correction du diagnostic ADC, **76 simulations** et revue indépendante
du schéma `bounded-pcm-quota-and-timing-v2` passent. Le seuil de 2 ms est conservé
comme diagnostic ; statut/format/trames, ADC non monotone, démarrage sous 10 s,
ouverture limitée à 45 s, quota et fermeture possédée restent contrôlés. Aucun ancien brut
n'est requalifié. Sous la nouvelle autorisation unique
`call_4240a9f8823740ff8e6f17d8024be261`, le Jabra redétecté à l'index 15 fournit
**1 440 000 trames par canal / 30 s PCM nominales en six fragments**, avec fermeture
normale après **32,6904626 s**, sortie 0, Job vide et handles fermés. Le contrôleur et le
rapport de quota sont `passed:true` dans
`qualification/headset-jabra-v2-data30-max45-20261011-212458-84da2978/` ;
SHA du brut `c20aac0570e52e9fb0bb5c38ec85dafd35bae9b2fb1e2561cd6ff182d1867aca`.
Les neuf écarts ADC restent conservés ; l'intervalle ADC est de 29,9989481 s pour 30 s nominales ;
`timestamp_coherence_passed:false`, continuité physique explicitement inconnue.
Ce résultat qualifie quota/fermeture et ne revendique ni audition des participants,
ni navigation intégrée, ni latence. Les 131 tests ciblés frontend puis TypeScript étaient
déjà engagés de 21:24:35,787 à 21:25:35,676 UTC et chevauchent l'essai : le PC n'est
pas décrit au repos. Aucune écoute/STT/sortie système, aucune nouvelle capture
autorisée après cet essai. Les 76 simulations recouvrent les 74 tests purs précédents,
plus deux audits WAV synthétiques, et ne s'ajoutent pas aux 2 051 tests du dépôt.

La régression Python globale précédente termine dans un environnement temporaire
court et isolé : **2 051 réussis, un ignoré, zéro échec/erreur**, 2 052 cas en
1 737,79 s, sur trois processus. Le rapport
`global-python-public-final-20261011.xml`, SHA
`c5c582e236e4db704f9324332ab75ecf2b224839cbbbc8a854307e17b2791c7a`,
et le reçu `global-python-public-final-20261011-run.json` sont conservés.
Ce passage complet est distinct des rapports bruts antérieurs ; les reprises
ciblées ne s'ajoutent pas à ses 2 051 réussites.

Le complément de panneau et d'entrée depuis Sources est ensuite gelé après
relecture indépendante. Une **passe React globale unique réussit 694/694 tests
dans 75 fichiers, en 244,67 s**, puis TypeScript et le build réussissent.
Le reçu neuf est
`source-session-layout-followup-20261011-221310/qualification.json` ; JS
`index-DhlxCsWr.js`, SHA
`c4416b2615feab848c3ad630fb46e1f49eeb75d4575995ef4e185fe0cf66ca9c`,
CSS `index-DENGLpaQ.css`, SHA
`d9de4c7d6eb87fb5e237de1fb9b9c6db33ffb8046f6eaced0d4f48817a03bdb7`.
Les 57 ciblés de l'entrée Sources, les 48 du studio et les 16 de seuil du menu
recouvrent ce passage global ; ils ne s'ajoutent pas aux 694. Le formulaire
Nouvelle séance réutilise le parcours existant, préremplit seulement un projet
ERP accessible et ne crée ni séance, ni commande, ni capture au clic.

La recette finale `public-fidelity-final-20261011/DhlxCsWr/qualification.json`
passe **16 contrôles navigateur** sur la fixture fictive du build DhlxCsWr :
formats PDF/PNG, ouverture du formulaire avec projet prérempli, note ERP version
2 et cinquième bloc conservés après rechargement, préférence de disposition,
défilement clavier des panneaux et diagnostics, menu 670 vers 850 puis navigation
ERP par Entrée, présentation verticale à 320 sans débordement horizontal de page.
Elle ne lance ni capture ni LLM. Les captures et mesures incorrectement prises
pendant le chargement ou englobant le tableau ERP masqué sont gardées et exclues,
avec leurs successeurs limités à la région visible.

Les trois panneaux complets à 850 × 479 sont bien simultanément visibles, mais
les notes personnelles n'ont que 117 px de hauteur et les notes enrichies 78 px ;
le document conserve 486 px de hauteur. À 1280 × 800, les hauteurs sont 304,8 et
203,2 px, assistant 517 px. Sources conserve x104/largeur1160/tabley384,1 avec
en-tête68 et toolbar113,1. La disposition enrichie historique à 786 × 474 a ses
panneaux à y386,7 sur 1105,8 px de hauteur. Ces écarts observés avec les références
publiques R01–R03 ne satisfont pas le critère exact ±2 px. Le rapport AFTER
complète la comparaison sans requalifier les anciennes captures.

Le complément Studio compact et Sources R01 est ensuite qualifié par une
**passe React unique de 716/716 tests, 75 fichiers**, TypeScript et compilation
réussis. Les 132 tests ciblés sont inclus. Le reçu est
`studio-compact-followup-20261011/qualification.json`, build JS
`index-Dj5PdhkQ.js`. Les mesures navigateur du build, la sauvegarde ERP version 2
et les fragments STT fictifs sont conservés dans
`public-fidelity-compact-20261011/Dj5PdhkQ/` ; leur portée est distincte de la
preuve matérielle Jabra et de la comparaison exacte publique encore en cours.
La recette affiche deux fragments microphone en attente, un fragment système
en échec, zéro segment, 8 s et 5 s par piste ; aucune durée murale de 13 s ni
transcription complète n'est inventée. À 320 px, le label fictif de 80 caractères
reste contenu et le tableau défile localement, sans débordement de page.

Les tests utilisent des bases temporaires. Le sandbox Windows refusant la
création de leurs sous-dossiers, leur exécution utilise le contexte autorisé
par l'approbation automatique. Aucun résultat de mock n'est une preuve audio.

| Preuve | Résultat et portée |
|---|---|
| `logs/foresight-runtime/frontend-final-vitest.json` et `frontend-final.log` | Première suite interface après lien direct CR : 569/569 tests, 69 fichiers, aucun échec en 195,71 s, deux workers ; baseline historique avant compléments |
| `logs/foresight-runtime/frontend-completion-qualification.json` | Régression complémentaire 672/672, 75 fichiers, 235,84 s ; TypeScript/build réussis |
| `logs/foresight-runtime/frontend-f10-label-followup-20261011-204228.json` | Deux tests ciblés, TypeScript/build réussis ; build intermédiaire NcMllJD2, anciens assets conservés |
| `logs/foresight-runtime/frontend-markdown-dto-followup-20261011-205428.json` | 97/97 ciblés, TypeScript/build réussis ; JS historique de cette passe DKlOduK1, preuve DTO reproduite puis corrigée |
| `logs/foresight-runtime/completion-supplement-f10.xml` et `.json` | 86 cas distincts : 84 et 2 dans deux exécutions brutes conservées ; verrou API unique et droits frais |
| `logs/foresight-runtime/completion-supplement-note-version-timezone.xml` | 5/5 cas de version staging, intégrité/droits/fuseau UTC, 13,35 s |
| `logs/foresight-runtime/completion-supplement-runtime-mail-isolation.xml` | 20/20 cas runtime puis mail, 11,26 s ; fixtures locales ne contaminent plus la sauvegarde mail |
| `logs/foresight-runtime/browser-completion-20261011/qualification.json` | 21 assertions UI réelles, notes seules, réponses simulées, bases fictives ; aucune génération/capture/publication dans ce passage |
| `logs/foresight-runtime/global-python-completion.xml` et `.log` | Résultat brut conservé : 1 948 réussis, 16 échecs, 1 ignoré ; causes de chemins/isolation décrites ci-dessus |
| `logs/foresight-runtime/completion-supplement-global-failed-short.xml` | Seize cas échoués repris, 16/16 réussis, 43,91 s ; aucun changement produit pour ce passage |
| `logs/foresight-runtime/global-mail-backup-failure-postmortem.json` | Deux fragments de fixtures hors stockage attendu ; contrôle en lecture seule, aucun fichier supprimé |
| `logs/foresight-runtime/frontend-qualification.json` | TypeScript et build réussis ; 155 modules, build Vite 3,35 s ; JS `index-BHuQuZfz.js` et CSS `index-BpOo83wS.css`, tailles et SHA exacts dans le rapport |
| `tests/test_meeting_sessions.py`, `test_session_assistant.py`, `test_native_capture_router.py` | Suite finale des trois fichiers : 52 tests réussis, 252,34 s ; scopes, conflits, UUID, drain concurrent et reprises |
| Admission CPU et enfants Windows | 27 tests arbitrage/proactif/runtime réussis ; suite finale batch/arbitrage/lifecycle : 24 tests réussis, dont 5 cas arrêt/isolation/erreur du processus enfant |
| `logs/foresight-runtime/studio-end-to-end.json` | 17 appels FastAPI, 23,114 s, Whisper et Gemma réellement exécutés, destinations Python limitées à 127.0.0.1 ; réponse préserve négation et 250 W, nouvel ajout cité accepté sans modifier le texte humain, publication puis rejeu |
| `logs/foresight-runtime/session-qualification.json` | 12 scénarios WAV distincts et 60/120 min deux pistes ; 120 min = 240 chunks/460 810 560 octets, mix final 26,318 s ; conservation et rejeu réussis, capture matérielle longue non testée |
| `logs/foresight-runtime/audio-qualification.json` | Voix fictive 18,592 s réellement transcrite ; modèle/profil/empreinte de configuration conservés |
| `logs/foresight-runtime/native-audio-qualification.json` | 4 WAV système durables, pause/reprise/arrêt, STT réel ; aucun microphone ouvert ; erreur sur « devis » conservée dans les résultats |
| `logs/foresight-runtime/qualification/headset-jabra-30s-20261011-191634-13ab015a/qualification.json` et `postmortem-verified-20261011.json` | Une capture autorisée du microphone Jabra, arrêt normal à 30,004 s, six WAV/25,9 s, SHA/signal conformes ; quota strict 30 s non atteint, aucune écoute/STT/reprise |
| `logs/foresight-runtime/qualification/microphone-real-30s-normal-471093bd/postmortem.json` | Microphone Realtek réellement ouvert après autorisation : cinq WAV PCM16 stéréo 48 kHz, 25,000 s/1 200 000 trames par canal, cinq SHA concordants, signal non nul sans écrêtage. Ancien délai du harnais interrompant le dernier fragment ; arrêt normal et 30 s durables NON QUALIFIÉS |
| `logs/foresight-runtime/browser/` | Notes seules sur serveur fictif 18003 : note ERP version 2, brouillon avec action/citation/responsable/date conservé entre onglets et après reload, relecture remise à zéro, publication confirmée puis CR/action ouverts dans le projet ; captures 1280/670/320 pour Studio, Sources et Préparation |
| `logs/foresight-runtime/browser/published-review-direct.json` | Build final : le lien de publication recharge le bon projet avec `?meeting=<id>`, sélectionne Réunions et audio et ouvre le CR exact ; action Paul/16 octobre et aucun clic de conversion en tâche |
| `logs/foresight-runtime/browser-fixture-20261011-171638-a6c3c921/originals-export-qualification.json` | 58 contrôles HTTP : originaux TXT/PDF/PNG et octets SHA exacts ; page PDF physique, deux versions de note dans le ZIP et aucune durée, piste ou transcription inventée pour la séance sans audio ; aucun original XLSX dans cette recette |
| `logs/foresight-runtime/speech-corpus-qualification.json` | Corpus industriel annoté, erreurs et latences froid/chaud ; résultat opérationnel distinct de la porte qualité industrielle |
| `logs/foresight-runtime/multimodal-qualification.json` | Encodeur officiel LiteRT/EmbeddingGemma 2, vecteurs normalisés 768, texte/image/audio réellement exécutés et profil exact |
| `logs/foresight-runtime/index-offline-qualification.json` | Index séparé sur quatre sources fictives, annulation/reprise/relecture persistée, recherche image/audio/texte puis Gemma local ; garde réseau Python, sans preuve de coupure physique |
| `logs/foresight-runtime/retrieval-industrial-located-20261011/retrieval-qualification.json` | Corpus scellé avant encodage : 10 sources, 12 questions, deux PDF paginés, tableur/plages, schémas et audio synthétique ; 11 réponses au rang 1, un périmètre négatif vide, 0 fuite/ancienne version ; requêtes chaudes P50 0,196 s/P95 0,209 s, premier processus 2,400 s |
| Tests source, fraîcheur, chat et reprise | 23 tests ciblés réussis ; droits/archive projet/Notes/workspace : 83 tests ciblés réussis après corrections |
| Sauvegarde/index/documentaires | 85 tests réussis après ajout des contrôles de schéma Sources, statistiques actuelles et gel/remap des copies restaurées ; 38 tests classement/résolution réussis avec contrat historique corrigé |
| `logs/foresight-runtime/global-python-final.xml` et `.log` | Première suite Python globale : 1 920 réussis, 1 ignoré, aucun échec/erreur en 1 694,03 s ; baseline historique avant compléments |
| `logs/foresight-runtime/microphone-timer-final.log` | Treize tests de minuterie simulée, ajoutés après collecte de la suite globale, réussis séparément avec `--noconftest` en 0,14 s ; aucun microphone ouvert |
| Ruff global | `ruff check app backend/app tests` réussi après admission CPU et protection du batch |
| `logs/foresight-runtime/final-runtime-qualification.json` | Contrôle final en lecture seule : JUnit/SHA, `/health` Brain/ERP `ok`, `/app/` 200, texte de l'index servi identique au build, assets par empreinte ; flags effectifs séance/proactif désactivés |
| `logs/foresight-runtime/completion-runtime-qualification-v2.json` | Contrôle historique du build DKlOduK1 servi sous `/assets/` lors de cette passe, santé et index conformes, flags désactivés ; les 16 échecs globaux sont tous repris verts, sans prétendre à une passe globale unique |
| `logs/foresight-runtime/production-completion-preservation-20261011.json` | 18 tables protégées et 1 340 originaux intacts, aucun objet de recette dans le canon ; 3 tables de suivi différentes sans suppression, 21 tables auditées seulement |

Les rapports peuvent être actualisés après un nouvel essai : leur modèle,
configuration, corpus et date font foi. Ne pas additionner des passages de tests
répétés pour annoncer une couverture globale.

Deux scénarios interface ont exposé des prérequis de préparation asynchrone :
le lecteur initial de MailApp et le chargement des visas avant activation du
bouton Enregistrer de Planning. Leurs attentes explicites ont été corrigées,
sans modifier le moteur mail/planning ni les assertions métier. Les deux
rapports initiaux à 562/563 et le passage intermédiaire à 563/563 sont conservés.
La première passe à 569/569 couvre aussi le lien vers le CR publié et les IDs
étrangers/absents, après ce dernier correctif applicatif.

La suite Python globale initiale a exécuté 1 843 cas : 1 788 réussis, 16 échecs,
38 erreurs et un ignoré, en 3 285,39 s. Démarrée avant les derniers correctifs,
elle a relevé des assertions de version ERP 10
devenues anciennes avec l'outbox additive ERP 11, ainsi qu'un test mail déjà
signalé par les qualifications précédentes. Les assertions de migration suivent
maintenant ERP 11, avec leurs garanties de conservation inchangées. Le test mail
vérifie encore l'abstention sur expéditeur partagé seul, puis le candidat IA
unique à 0,75 selon la règle existante documentée dans
[18_MAIL_TRIAGE.md](18_MAIL_TRIAGE.md). Le moteur de classement et les décisions
réelles n'ont pas été modifiés pour rendre ces tests conformes.

La première recette globale a réexécuté les fichiers présents à la collecte sur trois processus
isolés avec `pytest-xdist --dist loadfile`. Chaque processus conserve ses propres
bases temporaires définies par `tests/conftest.py`. Le plugin 3.8.0 est installé
uniquement dans `.ui-preview/pytest-parallel`, sans modifier les dépendances
de production. Résultat : 1 920 réussis, 1 ignoré, aucun échec/erreur en
1 694,03 s. Le rapport JUnit et la sortie intégrale sont conservés. Les treize tests
de minuterie ajoutés ensuite sont qualifiés séparément, sans les additionner
au nombre de la suite globale.

## Couverture fonctionnelle F01–F25

| Fonctions du plan | Réalisation et limite |
|---|---|
| F01 liste des séances, F02 création, F03 sans projet | Routes uniques Agent, préparation réouvrable, staging sans projet et attribution rejouable |
| F04 mic, F05 système | API/chunks/navigateur et helper WASAPI, pause/reprise/récupération ; système Realtek qualifié matériellement ; quota Jabra autonome de 30 s PCM et fermeture en 32,69 s qualifiés. Les essais partiels antérieurs restent conservés ; capture intégrée, loopback casque, audibilité et remplacement restent ouverts |
| F06 direct, F07 voix/corrections, F08 lecture/citations | Segments révisés, temps réels, corrections prioritaires ; voix anonymes/pistes techniques, qualité industrielle du direct encore ouverte |
| F09 notes, F10 enrichissement | Autorité ERP, versions, brouillon riche/Markdown à conversion explicite ; v3 conservée en UI et historique v1 exact ; automatique après stabilité, tentative durable et décision sérialisée qualifiés par 86 cas, sans activation sur le canon |
| F11 CR, F12 Ask, F13 Live Q&A | Publication relue, historique Ask par séance/périmètre/sources, cartes épinglées persistées ; proactif opt-in ; performances des cartes non qualifiées sur réunion longue |
| F14 catalogue, F15 imports, F16 recherche texte | Canon fédéré, formats/labels/tri/liste/grille, imports versionnés, texte exact/lexical/EG2 ; Drive exclu et désactivé sur décision utilisateur |
| F17 multimodal, F18 graphe | Index local séparé, texte/image/audio ; graphe d'appartenance/provenance conservée, sans lien sémantique inventé |
| F19 statistiques, F20 réglages, F21 local | Comptages visibles actuels et formules, readiness séparée ; chaîne locale STT/EG2/Gemma qualifiée sous coupure physique observée sur corpus fictif, avec garde Python. Trafic natif non mesuré et direct industriel non qualifié |
| F22 calendrier, F23 actions | ICS/UID choisi comme contexte, jamais date contractuelle automatique ; conversion explicite en tâche existante |
| F24 export/reprise, F25 fidélité/clavier | ZIP de séance et exports historiques ; fichiers/versions originaux conservés ; structure/accessibilité vérifiées. Adaptation visuelle présentée validée par l'utilisateur, sans parité exacte à ±2 pixels revendiquée |

## Recettes T01–T17 : critères ouverts et preuves

| Recette | Résultat actuel |
|---|---|
| T01 navigation/capture | Singleton navigateur et barre permanente testés ; notes et brouillon conservés en navigation réelle ; navigation pendant capture matérielle non qualifiée |
| T02 crash/reload | Tampon IndexedDB, journaux natifs, fragments acquis et commandes rejouables ; reprise ne rouvre pas le micro |
| T03 mic/système/casque | Loopback Realtek réussi ; quota Jabra autonome de 30 s PCM et fermeture en 32,69 s avant 45 s réussis, continuité matérielle inconnue et essais historiques conservés ; audibilité humaine, capture intégrée, loopback casque et remplacement en cours non testés |
| T04 deux onglets/clics | Web Locks, UUID et concurrence backend ; tests réussis, recette réelle deux onglets à compléter |
| T05 corrections pendant IA | Tests de saisie/version/conflit/segment et preuve HTTP ; textes humains conservés et réponse ancienne signalée |
| T06 panne Notes/Brain | Outbox et reçu idempotent ; version ERP survit, rejeu après commit Brain testé |
| T07 identités/scopes | Notes identiques projets distincts ; périmètres et refus de droits testés |
| T08 citations | Note versionnée et page PDF physique vérifiées dans les recettes antérieures ; nouveau parcours Ask → citation → Examiner → Preuve 1 pour XLSX/feuille/plage, audio/piste/révision/1–4 s et PNG entière : neuf contrôles navigateur et trois contrôles HTTP des originaux visibles réussis, octets vérifiés par SHA. Critère qualifié sur ces cinq modalités du corpus fictif ; aucune exhaustivité de formats, reconnaissance d'image ou STT revendiquée |
| T09 publication interrompue | Essai HTTP/rejeu : un CR, une action, provenance exacte, aucune tâche automatique |
| T10 import/version/distance | Réimport initial et modifié, version/labels conservés, extraction ratée visible ; Drive connecté non exécuté, explicitement exclu et désactivé par décision utilisateur |
| T11 coupure Internet/LAN | Nouvelle recette physique réussie : STT/EG2/Gemma sur sources fictives, neuf inventaires avant/pendant/après dont six pendant l'enfant, gapmax7,32s, exit0/Job vide ; premier timeout conservé. Appels natifs non mesurés, exactitude/latence industrielle hors portée |
| T12 charge/longue réunion | 60/120 min conservation/mix synthétiques réussis ; admission CPU batch/direct et cycle de vie réussis ; latence et charge de vraie réunion longue ouvertes |
| T13 visuel/clavier/670/320 | Qualifié dans la portée publique/adaptation validée : responsive et graphe clair/sombre, clavier et focus ; complément réel UI Stop à 670 clair/recording et 320 sombre/paused après Sources, Tab/Entrée et deux réponses STOP200 simulées. Aucune qualification audio physique ou parité exacte/private revendiquée |
| T14 ancien parcours | Qualifié dans la portée désactivation/récupération après nouvelles écritures : cinq cas API/SQLite/fichiers passent dans R1, code identique actif ; notes/versions, exports, fragments et reçus conservés |
| T15 modules/canon | Qualifié sur V5 actif : sauvegarde finale/restauration 992 fichiers et 5 bases, tous anciens identifiants et champs métier conservés après reprise ; seuls deux traitements automatiques reprennent avec écarts expliqués. Python 2361/2 ignorés, frontend 858, Ruff, santé et assets vérifiés. Archive historique FK26 inchangée, bases actives FK0 |
| T16 disque/ACK/fichier partiel | Quotas, SHA/taille, fsync, tests corruption et écritures interrompues ; aucun faux ACK admis, pas de purge |
| T17 notes seules/staging | Scénarios sans projet, attribution/rejeu, notes-only CR et audio réel réussis sans faux projet/audio/timecode |

Le contrôle en lecture seule `post-browser-publication.json` confirme un CR,
une action, zéro tâche, séance terminée révision 5 après commande attendue en
révision 4, note version 2 et citation exacte du bloc 3. Il conserve un attendu
strict non atteint : la synthèse manuelle approuvée dit que la livraison reste
à confirmer, sans répéter « 23 octobre ». Cette date incertaine demeure dans
la note originale et la citation complète. Le rapport n'est donc pas présenté
comme intégralement vert ; aucun texte publié n'a été réécrit après contrôle.

## Activation et retour arrière

L'application conserve un seul serveur 8001. Les captures ou écritures de recette
utilisent des bases fictives ; aucun CR fictif n'est publié dans un projet réel.
Les migrations sont additives, avec sauvegarde et validation du schéma préalable.
Le serveur fictif 18003 a été arrêté après vérification de son script et du PID
3928 ; ses bases, exports et preuves sont conservés. Le relevé `shutdown.json`
de la fixture confirme qu'Agent 8001 reste `ok`. Aucun port 8000/8002 manipulé.

Deux checkpoints supplémentaires ont été restaurés et vérifiés :
`backups/foresight-preactivation-20261011-165523-878641`, puis
`backups/foresight-preactivation-20261011-171046-304281` : 1 360 fichiers de données
et code par empreinte. Les derniers correctifs UI sont postérieurs au second.
Agent a redémarré sur 8001 ; `/health` confirme Brain/ERP `ok`, les routes et
schémas additifs sont chargés. Le flag effectif de séance et le proactif restent
désactivés pendant la recette ; la clé persistée du flag est absente, son repli
est désactivé. Sources et Statistiques sont accessibles. Le premier essai de checkpoint
a échoué sur l'encodage du texte du superviseur ; Agent a été relancé
immédiatement, puis le script corrigé et le checkpoint repris avec succès.

Les compléments précédents sont couverts par deux checkpoints vérifiés,
`backups/foresight-preactivation-20261011-185124-308574` puis
`backups/foresight-preactivation-20261011-190123-680964` : chacun conserve
1 361 fichiers, SQLite restaurés `ok` et code par SHA. Le fichier supplémentaire
depuis les 1 360 initiaux est la rotation `storage/logs/agent.log.2`, sans retrait
de pièce. Le second inclut le build DKlOduK1 et le correctif de fuseau staging.
Le superviseur est actif, zéro relance après ce redémarrage. Le contrôle
`completion-runtime-qualification-v2.json` confirme le service et les assets
référencés par l'index sous `/assets/`. Le rapport précédent reste faux parce
que le harnais vérifiait `/app/assets/`, qui renvoyait l'index HTML ; il n'est ni
effacé ni présenté comme un défaut d'asset actuel.

Le relevé RO précédent à 19:04:17 UTC, `production-completion-preservation-20261011.json`,
vérifie 18 tables protégées, 1 410 sources, 1 340 artefacts et 1 340 fichiers
originaux par SHA. Aucun projet, séance, CR ou action fictif n'est dans le canon.
Depuis l'initial, trois suivis montrent 128 nouveaux inputs, trois inputs
historiques, sept scans et deux analyses modifiés, sans suppression. Depuis le
dernier checkpoint, seuls sept scans évoluent. L'attribution aux workers reste
une inférence, leur code étant inchangé, sans trace du thread écrivain.
`protection_gate_passed:true` est distinct de l'égalité globale fausse des
cellules suivies ; seules les 18 + 3 tables indiquées sont auditées.

Le checkpoint précédent `backups/foresight-preactivation-20261011-202403-076435`
conserve 1 361 fichiers, restaure les deux SQLite avec intégrité `ok` et garde
le code par SHA avant redémarrage. `completion-runtime-qualification-v4.json`
confirme ensuite sur 8001 les assets DhlxCsWr/DENGLpaQ, santé et index, routes
de formats et refus invalide 422 ; les trois flags restent faux. Le contrôle
PDF de production retourne zéro source et ne vaut donc pas une preuve de contenu
PDF positif ; celle-ci appartient aux tests et à la fixture.

Le relevé RO à 20:28:49 UTC, `production-public-final-preservation-20261011.json`,
conserve exactement les 18 tables protégées et 1 340 originaux par SHA, 1 410
sources et 1 340 artefacts ; aucune recette canonique. Depuis l'initial : 142
inputs ajoutés, trois inputs historiques, sept scans et deux analyses modifiés,
aucune suppression. Depuis le dernier checkpoint : aucun input ajouté/modifié,
sept scans et une analyse évolués. L'attribution aux workers reste une inférence
de leur code et de leurs références inchangés, sans trace du thread écrivain.
Ce contrôle reste limité aux 18 + 3 tables et ne prétend pas figer les 80 tables.

Le relevé après migrations ne prétend pas à un gel des workers hérités :
`production-preservation-after-migrations.json` reste `passed:false` sur trois
tables de suivi. `production-worker-differences.json`, relevé en lecture seule
du 11 octobre à 17:29:41 UTC, décrit chaque cellule : 86 nouveaux IDs dans
`milestone_inputs` et trois lignes historiques modifiées, sept lignes de scans
et deux lignes d'analyses modifiées, aucune suppression. Les sources, artefacts,
calculs de clés et trois services hérités correspondent aux empreintes initiales.
27 ajouts et trois corrections précèdent le premier checkpoint ; 24 ajouts et
une ligne modifiée sont postérieurs au second checkpoint. L'attribution aux
workers hérités est étayée par ces éléments, sans trace identifiant le thread
écrivain : elle reste une inférence. Toutes les colonnes des 88 jalons, CDC, sources,
propositions et validations humaines restent identiques. Les champs de dates
des 88 jalons étaient vides initialement : ce relevé prouve leur conservation,
sans inventer une recette de dates renseignées.

Le retour au parcours historique désactive l'espace/proactif sans supprimer
les séances ou pièces. Préparation refuse la désactivation pendant une capture
navigateur ou un tampon non synchronisé ; le helper natif est drainé/finalisé
avant la désactivation. Les API de récupération d'une séance existante gardent
correction, finalisation et export disponibles. L'interface désactivée garde
l'export, mais demande la réactivation de l'espace pour modifier une séance.
Les Notes ERP et leurs versions restent l'autorité.

Sauvegarde/restauration : SQLite cohérents pour Brain/ERP et index dérivés,
empreintes de pièces/fragments, restauration dans un dossier neuf. Les chemins
sont remappés dans la seule copie restaurée ; les anciens travaux multimodaux
sont conservés mais annulés et leurs entrées marquées obsolètes avant un nouveau
build explicite. Les journaux natifs sont remappés vers leurs originaux vérifiés.
Une restauration ne reprend jamais automatiquement un périphérique audio.

Aucun commit ni push demandé. Le code et les fichiers générés restent dans
l'arbre de travail jusqu'à livraison Git explicitement demandée.

Le dernier checkpoint est désormais
`backups/foresight-preactivation-20261011-223302-512328` : 1 361 fichiers de données,
restauration des deux SQLite `ok`, code copié et vérifié par SHA. Agent seul a
redémarré sur 8001. `completion-runtime-scope-20261011-v1.json` confirme santé,
index et assets `Yuj98_lc/BJ0BE6LI`, routes de formats, refus invalide 422 et
GET Drive désactivé. Séance/proactif/enrichissement restent faux. Le nouveau
superviseur est actif, zéro relance, et le contrôle de statut ne conserve que
des champs autorisés, sans jeton interne.

Le relevé RO à 22:34:10 UTC, `production-scope-preservation-20261011-v1.json`,
vérifie exactement les 18 tables métier protégées, 1 410 sources, 1 340 artefacts
et 1 340 originaux par SHA, sans projet, séance, CR ou action fictif dans le canon.
Depuis l'initial : 157 inputs ajoutés, trois inputs historiques, sept scans et
deux analyses modifiés, sans suppression. Depuis ce checkpoint : aucun input
ajouté/modifié, sept scans et une analyse évolués. Attribution aux workers
hérités par inférence seulement ; audit limité aux 18 + 3 tables désignées.

Le ciblé après promotion du seul harnais audio passe 169/169 en 20,61 s, Ruff
complet et ciblé conformes. Les groupes candidat et runtime de 74 cas chacun
se recouvrent ; ils ne s'ajoutent pas à la globale 2 056, antérieure à cette
promotion. L'erreur initiale de chronologie des fixtures et ses rapports sont
conservés. La revue finale vérifie 31 empreintes et 18 contrôles statiques.
L'inventaire Jabra unique confirme mic/sortie/loopback sans ouverture de flux.
`integrated-jabra-promoted-20261011-222602-edd836f7/PROTOCOL.md` décrit une recette
courte intégrée encore en attente d'un nouvel accord regroupé. Cette préparation
ne qualifie ni la capture réelle, ni le direct STT, ni la charge d'une réunion longue.
Le contrôle RO complémentaire `integrated-jabra-pid-readonly-20261011-232309-a32911f4/audit.json`
exige pour cette recette l'invocation absolue du Python313 principal, empreinte
`a2a4eff8d0b0c845284c607d50a3b5b966ac5a3121736a2e38e165bd6644d9fe`.
Le backend reprend `sys.executable` ; un autre interpréteur appelant pourrait
introduire un lanceur intermédiaire et serait refusé avant ARM/OPEN. Le helper
venv ne suppose pas `Popen.pid == os.getpid()`. Les 31 ressources restent
inchangées ; la preuve autonome ne qualifie pas une égalité de PID interne.

Recette batch héritée : préparation V2 gelée avec 43 simulations (2,38 s),
Ruff conforme et 21 contrôles indépendants ; les 15 WAV SAPI fictifs et les
27 attentes originales propres sont inchangés. Le GO technique autorise une
seule exécution dans `legacy-batch-qualification-20261011-225143-4b925ae8`.
Elle échoue avant lancement du moteur STT : l'audit `subprocess.Popen` Windows
transmet une commandline texte que le guard compare comme une liste de caractères.
Le premier cas possède zéro segment et aucun enfant transcripteur n'a été lancé.
Un `WinError5` lors de `heartbeat.tmp` → `heartbeat` est aussi conservé dans le reçu ;
sa cause n'est pas attribuée indépendamment.
Fermeture normale en 17,0359 s, Job vide, `CloseHandle` réussi, aucun arrêt forcé
ou tardif. Les deux rapports restent en échec ; ces résultats ne qualifient ni
le batch, ni sa qualité. La V3 du seul harnais est ensuite gelée dans
`legacy-batch-qualification-20261011-230549-ad2098bb`, avec 51 contrôles réussis
en 4,33 s, dont l'événement d'audit Windows réel et un verrou lecteur de fichier
réel sur des processus/modules factices. La comparaison exacte de commande et
d'exécutable conserve la liste autorisée ; les commandes altérées sont refusées.
Les erreurs primaires et de télémétrie restent distinctes, le retry IO est borné.
Une nouvelle revue indépendante précède son GO. Le moteur et les réglages
canoniques restent inchangés ; ces contrôles ne constituent pas une transcription.
Sous nouveau GO, la V3 admet bien la commande mais refuse l'entrée produit :
le PID `Popen` est celui du lanceur venv Windows, distinct du PID de l'interpréteur
qui a écrit l'attestation exacte. Leur lien OS n'est pas attesté dans ce schéma V3.
Aucune approbation transcripteur n'est donnée, zéro segment et aucune inférence.
Fermeture normale en 19,2187 s, Job vide,
`CloseHandle` réussi, aucune terminaison forcée/tardive ; heartbeat durable.
Les reçus restent en échec. La V4 du seul harnais relie les deux PID par un nonce
unique, une attestation unique, les images/temps de création et le parent OS
vivant, puis l'appartenance au Job propre à cette recette. Les handles de requête
sont fermés et leur fermeture vérifiée avant l'approbation du PID réel. La
relecture finale conserve le même nonce et les deux identités distinctes.
Les 85 contrôles passent en 5,65 s ; ils incluent le VENV Windows installé sur
app/ML factices, sans cumuler l'ancien probe séparé. La revue indépendante
`legacy-batch-independent-v4-final-20261011/review.json` est favorable sur
22 critères et 60 liaisons SHA/tailles, pour 54 chemins distincts.
Le nouveau GO technique autorise une seule exécution sur les 15 WAV fictifs
inchangés dans `legacy-batch-qualification-20261011-232941-971be1b2` ; cette
exécution termine en 360,8843 s, sortie 0. Les 27 attentes propres, le profil CPU Turbo beam5/Sherpa,
l'isolation, les bornes 120 s/cas et 900 s absolues restent inchangés.
Le Job externe protège la recette ; le retour Popen instrumenté précède
l'affectation au Job interne legacy, dont le comportement normal en production
n'est donc pas qualifié ici. La préparation et la revue ne qualifient aucune
STT réelle, capture, latence navigateur ou réunion longue à elles seules.

Le résultat V4 durable compte 15/15 transcriptions complètes, 15 enfants réellement
approuvés et leurs liens OS exacts ; fermeture normale, Job vide, `CloseHandle`
réussi, aucun arrêt forcé ou tardif. Les 27 attentes critiques originales sur
les douze extraits propres passent. Dégradations : bruit 2/2, téléphone 2/2,
voix superposées 2/4 ; la consignation et le refus client sont perdus dans ce
dernier extrait. L'amélioration du bruit par rapport aux essais beam1 antérieurs
ne gomme pas leurs résultats. Le P95 de 24,855 s, minimum 21,227 et maximum
24,855 s, comprend le batch complet, chargement et diarisation ; aucun délai
de premier segment visible SSE/navigateur n'est mesuré. Le WER propre littéral
de 24,46 % conserve la tokenisation des nombres/unités et n'est pas directement
comparable aux WER normalisés antérieurs.

La relecture QA simulée passe sept contrôles de sauvegarde/relecture, versions
exactes, conservation du reçu brut v1, identité Source/audio et refus de révision
périmée. Le brut v1 n'est pas un artefact produit ; validation simulée v2 puis
v3 produisent deux artefacts exacts, v2 conservé et marqué obsolète. Le bruit
étant déjà exactement transcrit, v2 change surtout le nom d'intervenant et v3
ajoute le marqueur QA ; aucune réparation des deux omissions de chevauchement
ni validation métier humaine n'est démontrée. La copie contient 15 sources et
enregistrements, zéro CR/action/tâche/appel LLM ; rien n'est publié au canon.
La revue indépendante `legacy-batch-independent-v4-result-20261011/review.json`
confirme ces faits sur 22 critères, avec 98 liaisons pour 92 chemins distincts.
Ses lectures SQLite sont `mode=ro`/`query_only` ; aucun WAV, poids ou moteur
n'est ouvert pendant cette revue de résultat. L'avis favorable porte sur
conformité des preuves, pipeline fictif et fermeture, pas sur une qualité
industrielle globale : 33/35 attentes originales passent avant correction.
Un erratum distinct corrige le reçu préparatoire V4, dont le champ
`model_weights_rehashed_by_reviewer:false` était inexact : deux vrais recalculs
des poids avaient été effectués historiquement. L'ancien reçu et son SHA sont
conservés ; aucune nouvelle inférence ou modification de résultat n'en découle.

Le contrôle post-batch ferme ensuite le volet conservation à 23:46 UTC :
`production-post-legacy-batch-v4-20261011-234612-9dec7785.json` conserve exactement
les 18 tables métier protégées, 1 410 sources, 1 340 artefacts et 1 340 originaux
par SHA ; aucune séance, action ou CR fictif au canon. Depuis le checkpoint
223302 : 101 inputs ajoutés, aucun input modifié, sept scans et deux analyses
modifiés, zéro suppression. Depuis l'initial : 258 inputs ajoutés, trois anciens
inputs modifiés, sept scans et deux analyses modifiés, zéro suppression. Les
258 nouvelles références sont vérifiées. Les services hérités restent aux mêmes
empreintes ; leur attribution comme écrivains est une inférence, sans trace
causale du thread. La portée demeure les 18 tables et trois suivis désignés,
pas l'ensemble des 80 tables. SQLite est ouvert en lecture seule avec
`query_only` ; anciens reçus et pièces restent inchangés. Les trois flags
séance/proactif/enrichissement restent désactivés.

Un complément distinct de correction effective suit sur une copie SQLite et
métadonnées neuve : `overlap-review-supplement-20261011-235159-9946ae89/qualification.json`,
16 contrôles réussis, environ 2,44 s. Le chevauchement brut reste 2/4 ; insertion
automatisée de la référence préannotée rétablit les quatre attentes dans la
version corrigée. La version 2 est sauvée et relue exactement avant validation
QA simulée ; après une seconde annotation en version 3, les deux artefacts
exacts restent présents, v2 conservé et obsolète, révision 1 refusée sans
modification. SourceID/SHA audio restent identiques dans les seules métadonnées.
Stockage neuf vide, aucune ouverture/copie/décodage de WAV, aucun modèle,
sous-processus, LLM, CR, action ou tâche. Les treize starts restent neutralisés.
Les DB/reçus V4 originaux gardent leurs SHA avant/après ; leurs WAL/SHM/journal
restent absents. Le reçu brut QA est conservé octet pour octet. Cette insertion
de référence prouve correction, validation simulée et versionnement ; le moteur
STT garde 27/27 propres et 6/8 dégradées, sans validation humaine ou amélioration
de qualité revendiquée. La revue indépendante
`overlap-review-supplement-independent-20261011/review.json` confirme les seize
contrôles et les versions exactes par SQLite en lecture seule ; aucune nouvelle
exécution de service, modèle ou lecture audio. Ses références sont distinctes
du résultat V4 original dans le manifest. Les 16 contrôles ne s'ajoutent pas
à la régression globale et le score corrigé n'est pas une nouvelle mesure STT.

## Complément du 12 octobre — ordre des snapshots et sauvegarde

Le Studio protège désormais les lectures et ACK arrivant dans le désordre.
Une ancienne réponse ne remplace plus un segment récent, et un ACK de note
ancien conserve le brouillon lorsqu'une note ERP plus récente est déjà reçue.
Le cas de simple progression de transcription n'est pas confondu avec un
conflit de note. L'éditeur/versionnement ERP XPilot reste inchangé dans son rôle.
Les deux reçus rouges GET et celui du ACK restent conservés dans
`studio-snapshot-order-20261012-red/` et `studio-snapshot-order-20261012-save-red/`.

Le ciblé final passe **106 cas distincts/7 fichiers**, dont cinq régressions
nouvelles. Le premier global conserve **723 réussis/1 échec sur 724** : le test
de publication choisissait une option avant son chargement asynchrone. La
synchronisation du seul test est corrigée, ses assertions conservées ; le
composant de publication ne change pas. La nouvelle globale passe **724/724,
75 fichiers**, avec 208 empreintes source stables, puis TypeScript/build code0 :
`studio-snapshot-order-final-20261012-v2/qualification.json`. Le ciblé recouvre
ce total. Le global Python antérieur 2 056/1 ignoré n'est pas répété ici.

Sur une fixture neuve, sans moteur ni matériel, le navigateur réel modifie une
note riche, consulte Transcription, enregistre v2, navigue vers Sources puis
recharge/réouvre la séance. Neuf contrôles DOM/SQLite passent ; versions1/2
exactes, une note/une séance et zéro audio/CR/action/tâche. Les courses de
réponses différées sont prouvées séparément par tests simulés, sans injection
de délai dans ce navigateur. `studio-snapshot-delivery-20261012/` conserve
recette, capture 1280×720, sauvegarde du précédent dist et promotion réversible.
La preuve HTTP confirme Brain/ERP `ok`, index/assets `CHpAuznx/BJ0BE6LI` exacts,
flags séance/proactif/enrichissement faux et Drive désactivé sur 8001. Aucun
asset existant, module ou donnée métier n'est supprimé. La préparation intégrée
31 ressources liée à l'ancien index/JS est conservée. Un nouveau manifeste
`integrated-jabra-frontend-refresh-20261012/prepared-final-shas.json` lie le build
courant, avec 28 ressources inchangées et seuls index/JS/protocole actualisés.
La revue `integrated-frontend-refresh-independent-20261012-005828-11015b8d/`
passe 22 contrôles en lecture seule. Elle ne lance aucune capture ni inventaire
et ne remplace pas la réponse encore attendue à l'accord matériel regroupé.

Le contrôle RO `production-post-studio-snapshot-20261012.json`, terminé à
01:01:55 UTC, confirme encore les 18 tables protégées et 1 340 originaux exacts
par SHA, zéro séance/projet/CR fictif et aucune suppression des suivis.
Depuis le checkpoint 22:33, 173 inputs sont ajoutés, zéro input historique
modifié, sept scans et deux analyses modifiés. Depuis la sauvegarde initiale,
330 inputs sont ajoutés et trois anciens modifiés. L'attribution aux workers
hérités reste une inférence ; aucune immutabilité des 80 tables n'est revendiquée.

Un candidat de transcription distinct est acquis dans
`.models/audio-parakeet-tdt-v3-int8-candidate-20261012/`, sans changer les profils
Whisper ni installer de paquet. Les quatre composants INT8 totalisent
670 478 772 octets ; l'archive de 487 170 055 octets et ses SHA sont conservées.
Attribution : [NVIDIA Parakeet TDT 0.6B v3, CC-BY 4.0](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3),
export ONNX INT8 des mainteneurs [sherpa-onnx](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/nemo-transducer-models.html).
La revue acquisition/extraction passe 14 contrôles de préparation, sans charger
les poids. La préparation V1 a révélé une attestation de fermeture insuffisante ;
le harnais corrigé passe 54 simulations, puis 27 critères indépendants en RO.
Sous un GO root distinct, son unique lancement dans
`parakeet-inference-prepared-20261012-005047-2024a66d/qualification.json` échoue
en **1,1943 s**, avant phase chargement ou résultat ASR observable. Le garde de
ressources refuse un comptage de processus inattendu. Sa valeur exacte n'est
pas enregistrée dans ce brut ; aucun descendant réel ou défaut d'offset n'est
affirmé rétrospectivement. Le seul Job est fermé de force : exit92, Job vide,
handles fermés, sans erreur de fermeture, mais cleanup non qualifié. Les logs
vides, boot/ARM et le reçu d'échec restent conservés. Un premier probe factice
atteste ensuite deux membres réels du Job, sans relever leur seconde identité ;
il ferme de force en 0,3579 s et reste en échec. Le probe R3 observe cette fois
Python38420 et `C:\Windows\System32\conhost.exe`30500, parent38420, créé après
le principal et membre du même Job, avant/après la borne mémoire. Après release,
principal exit0 et Job0/list vide sont attestés avant fermeture des handles,
sans erreur, en 0,4612 s. Les quinze contrôles RO de revue du résultat passent.
Les preuves `parakeet-job-probe-prepared-20261012-012044-5a55fba2/` et
`parakeet-job-probe-r3-result-independent-20261012-014223-774df846/` qualifient
uniquement cette collecte et le cycle de vie factice : contrat single-PID et
ASR toujours faux. Elles ne réattribuent pas rétrospectivement la cause du premier
essai b47. Aucun modèle, audio ou app dans ces probes. Un nouveau harnais ASR
admet précisément le principal et au plus son conhost Windows attesté ; sa revue
et son GO restent distincts. Aucune qualité/vitesse ou intégration produit
n'est qualifiée par le seul diagnostic Windows.

Le nouveau gel `parakeet-inference-prepared-20261012-014020-58cab5ae/` passe
68 contrôles pure/mock, puis 26 critères RO de préparation. Son GO root distinct
autorise une seule recette CPU2. Elle exécute réellement les quinze phrases
fictives en **20,820647 s**, après un chargement de **5,247078 s**. Les deux
warmups de 1,184371/1,243737 s sont conservés et exclus des percentiles :
P50 calcul 0,717022 s et **P95 1,284903 s**. Ces mesures incluent la lecture du
petit WAV, les features et le décodage ; elles n'incluent ni file serveur, ni SSE,
ni apparition dans le navigateur, ni capture matérielle.

Le score strict reste **28/35**, soit 23/27 sur les phrases propres et 5/8 sur
les cas dégradés, dont 1/4 sous chevauchement. Les sept attentes en échec sont
décrites sans changer les critères : deux notations compactes plausibles
(`2,5 mm carrés`, `230V`) ne correspondent pas aux motifs figés ; `16 mp`,
`80<unk>C` et trois clauses de consignation/client restent non fidèles ou
incertaines. Le fold/scorer est identique au V4 primaire, confirmé par AST et
recalcul des quinze résultats ; aucun bug de calcul ni score corrigé n'est
substitué. Le WER littéral est 64/232 et pénalise également les notations
numériques. Le critère préalable 35/35 échoue : **zéro fenêtre de cinq secondes
exécutée**, aucun GO industriel ou changement des profils canoniques.

Le principal Python30524 et son conhost29644 sont identifiés dans le seul Job
privé. Exit0 naturel et Job0 sont attestés avant close ; erreurs de fermeture
vides et handles fermés. Le peak RSS de **1 439 711 232 octets** porte sur le
principal seul ; CPU 46,46875 s au dernier échantillon porte sur le Job, conhost
compris. Le reçu `qualification.json`, SHA
`c85805512a2f0b06caf378d2d0682618afe525b89ef0a197846f52279c6adcf4`,
les textes/tokens/timings bruts et tous les échecs antérieurs sont conservés.
La revue indépendante `parakeet-asr-result-independent-20261012-015550-93a7fc39/`
passe 22 contrôles RO de conformité, **avec NO-GO du candidat**. L'analyse
descriptive `parakeet-result-readonly-20261012-015558-d272e0ce/` est distincte ;
elle ne relance aucun moteur et ne retouche pas les textes.

Une seule variante supplémentaire CPU2, `modified_beam_search` avec quatre
chemins, est préparée dans
`parakeet-beam4-inference-prepared-20261012-020751-7a4009e4/`. Le helper distinct
préserve le greedy, les poids, les quinze sources et les 35 motifs. Seuls le
mode de décodage et le nombre de chemins changent. Les 32 contrôles purs du
delta passent séparément des 68 historiques ; la revue de préparation passe
22 critères RO. Les deux petits textes C++ officiels du tag Sherpa1.12.35 sont
scellés dans `sherpa-mbs-versioned-public-sources-20261012-020611-37921403/`.
Ce support du mode n'est pas une preuve de qualité ; beam search ne sépare pas
deux locuteurs mélangés. Sous un nouveau GO root, un seul essai est exécuté,
sans nouveau modèle installé, microphone, app ou LLM.

Son reçu brut, SHA
`75a214b71e00fdb749cc9f7a82ae99eeeb1691706fd381f6f48b3065958c5d59`,
reste **en échec** après le refus `Principal liveness/terminal state is
inconsistent`. Le dernier journal observe le principal37316 terminal0 encore
listé, avec son conhost34456 et JobActive2. Ces appels OS sont séquentiels ;
leur observation ne prouve pas la cause d'un comportement Windows ou modèle.
La fermeture finale confirme exit0, Job0, handles fermés et erreurs vides en
20,221850 s ; elle n'atteste pas la sortie naturelle avant close.
**cleanup_qualified=false** est conservé. Aucun nouveau run, correctif du garde
ou requête sur des PID terminés ne suit cet essai.
Le refus précède également les recontrôles SHA finaux des modèles et du conhost ;
ils restent non atteints et aucun succès post-run n'est déduit des liens préparés.

L'analyse RO séparée `parakeet-beam4-result-readonly-20261012-021650/` vérifie
que les quinze phrases et deux warmups ont fini avant ce refus. Le score strict
recalculé est encore **28/35 : 23/27 propres et 5/8 dégradés, overlap1/4**.
La température gagne un motif ; `1,5 mètre` perd le motif strict de longueur
qui acceptait `1,5 m`, sans constituer une longueur sémantiquement différente.
Le courant et trois clauses sous chevauchement restent non fidèles/incertains.
Le WER littéral est 62/232. **Zéro fenêtre courte exécutée** est dérivé des
bruts, et non d'une valeur par défaut pour un champ absent.

Le P95 descriptif de calcul 1,231468 s, le chargement 4,573546 s, les 91
échantillons, le peak RSS principal 1 439 678 464 octets et le CPU Job
50,28125 s proviennent également de cette analyse RO. Le reçu échoué n'a pas
les champs de synthèse score/compteurs/latence/verdicts conditionnels : leur
absence reste « non rapporté », jamais transformée en zéro/false ou remplacée
par ces calculs descriptifs. Un seul essai par mode ne démontre pas une
supériorité de performance. Aucun gate de direct, matériel ou T12 ni profil
canonique n'est changé par cette comparaison. Cette exploration est terminée.

Le contrôle HTTP RO du 12 octobre à 02:25:19 UTC,
`http-post-parakeet-mbs4-20261012-corrected.json`, confirme ensuite Brain/ERP
`ok`, index conforme après normalisation des fins de ligne, trois assets servis
aux SHA attendus, Drive exclu et flags séance/proactif/enrichissement toujours
faux. Aucun moteur, capture, écriture canonique ou port8000 dans ce contrôle.
Le premier reçu `http-post-parakeet-mbs4-20261012.json` reste conservé : le
contrôleur root avait utilisé `/app/assets/...` au lieu des liens `/assets/...`
du vrai index, et comparé ses octets CRLF à la réponse HTML normalisée en LF.
La comparaison correcte suit les fins de ligne universelles de `read_text()`,
y compris les CR seuls ; les octets du fichier et le HTML rendu restent distincts.
Le catchall `/app/{path}` renvoyait donc l'index aux trois demandes. Il s'agit
d'un défaut de ce contrôle, pas d'un défaut démontré de livraison ; aucun asset
ou code n'est modifié pour la reprise avec le lecteur existant correct.
Le champ Python « pending » de ce lecteur signifie reçu Python non fourni :
aucun nouveau runner Python actif, ni réexécution des 2 056 tests antérieurs.

La recette T12 de 60 minutes est préparée sans lancement réel : 1 440 fragments
prévus sur deux pistes en vraie cadence, quinze demandes logiques LLM à trois
fenêtres fixes et compte des dispatchs physiques distinct. La première revue
V1 refuse quatre défauts du harnais (interpréteur/site, erreur collector tardive,
double comptage HTTP, fold de score différent du V4). Le gel V2
`t12-realtime-preparation-20261012-013637-011f5b7b/` passe 63 contrôles pure/mock
puis 32 critères RO indépendants, sans addition aux 49 antérieurs. Il attend
toujours GO root et UI_READY CUA avec transcription réellement visible avant T0.
Gemma E4B est seulement identifié chargé en lecture de métadonnées ; les
générations réelles et annulations seront mesurées pendant l'essai. Le Turbo CPU
séquentiel peut atteindre la borne d'abandon avant la première fenêtre LLM ;
des demandes non exercées ne seront pas comptées comme charge réussie.
Un relevé RMS 20 ms/−40 dBFS fixe sur les quinze SAPI fictifs donne environ 71,1 %
d'activité acoustique par piste ; cette énergie, bruit compris, ne vaut ni voix
réelle/VAD ni fin phonétique humaine. Le proxy et les SHA sources/dérivés restent
distincts des mesures de latence et ne démontrent pas le critère industriel 5 s.
Sans modèle/audio ambiant ni charge longue qualifiée dans cette préparation,
L12 demeure ouvert sur ses trois familles restantes.

La liaison du gel T12 V2 au manifeste passe huit contrôles RO supplémentaires
dans `manifest-t12-binding-independent-20261012-015631-26544da9/`, sans lancement.
Le contrôle CUA du 12 octobre relève `browserVisible=false`, puis encore false
après une demande documentée `visibility.set(true)`. Aucun UI_READY ni GO root
n'est créé : aucun app, warmup, STT ou LLM T12 ne démarre pour ce précontrôle.
L'affichage du chat et du panneau navigateur a été demandé à l'utilisateur.
Ce blocage d'affichage ne constitue ni un essai de 60 minutes, ni un défaut
démontré du moteur, ni une dispense du critère de latence visible.

## Limites observées et règles de clôture

Le runtime audio local initialement absent est maintenant installé isolément.
Les deux autorisations Realtek et celle du microphone Jabra ont chacune consommé
leur fenêtre de 30 secondes. Deux nouvelles autorisations Jabra de 45 s ont ensuite
été consommées : 24,1 s conservées, fermeture en 26,53 s et quota incomplet ; puis 30 s PCM
conservées, fermeture en 32,69 s et quota réussi dans le schéma v2. Aucune écoute,
transcription ou nouvelle ouverture n'a suivi le dernier essai distinct.
L'ancien harnais strict `qualify_microphone_30s.py`, conservé historiquement,
borne la capture à 30 s depuis START et la capture/vidage à 35 s depuis READY ;
un quota manquant reste partiel. Ses treize tests de minuterie simulée passent,
sans constituer une nouvelle preuve matérielle. Le schéma v2 et le protocole
intégré fixent séparément une borne OPEN de 45 s immuable avant l'ouverture ;
le stimulus de sortie est borné à 30 s depuis son START. Le vidage inactif est
limité à 5 s après fermeture physique et n'autorise aucune nouvelle acquisition. Voir
[23_MEETING_AUDIO.md](23_MEETING_AUDIO.md#test-matériel-autorisé-du-microphone-realtek--11-octobre-2026).
Le mode images/audio emploie un encodeur complet qualifié pour l'exécution et un
profil d'index séparé. Le corpus industriel annoté obtient Recall@5 sources et
citations de 1,0 sur douze questions ; il ne représente pas l'ensemble des plans
CAO, des documents d'entreprise ni des appels réels. Son empreinte est
`1361b0a321d7a6452ddc878693711954d8c53bc639eb69a6ef7438d473942199`.
Les écrans Google Graph/Stats/Settings ne sont pas intégralement observables
dans les références publiques : les adaptations Agent sont identifiées.
L'utilisateur a choisi ces écrans publics comme périmètre de référence ; les
vues privées manquantes ne constituent plus une condition supplémentaire de
recette de ce périmètre. La comparaison reste bornée aux vues visibles et ne
revendique aucune équivalence au pixel avec une application native privée.
La comparaison exacte des zones visibles sur les supports publics n'est pas
qualifiée. L'utilisateur a ensuite validé l'adaptation présentée : cette
acceptation clôt F25/T13 dans la portée adaptée, sans transformer les essais
de structure, de conservation ou de tailles responsives en parité exacte.
La compatibilité fonctionnelle développée n'est pas une preuve de copie visuelle
exacte. Aucune porte de qualité n'est close sur la seule présence du code ou d'un
modèle installé ; L12 demeure ouvert tant que ses critères applicables restent
non atteints ou nécessitent une validation utilisateur du poste/de l'adaptation.


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

Le [dossier composite V3](../.ui-preview/pilots/native_next_promotion_plan_v3.md)
recense 29 fichiers : 22 remplacements et 7 nouveaux. Les 646 références de
code/ressources et les sources candidates sont revérifiées sans dérive. Ses
[neuf portes de fichiers](../.ui-preview/pilots/native-interruption-next-20261012/qa/next-v3-file-gates-before-root.json)
passent. Le [relevé opérationnel frais](../logs/foresight-runtime/promotion-operational-ro-fresh-20261012-203140-525354f6/qualification.json)
du 12 octobre, 20:31 UTC, confirme les deux bases ouvertes par le processus 8001
exact, une analyse de jalons déclarée running et quatre queued. Aucun état SQL
audio actif ; ownership natif et données navigateur non synchronisées inconnus.
Stockage global, sauvegardes coordonnées et maintenance restent à établir ;
ready_to_promote reste false et aucune activation n'est réalisée.

Le [protocole GPU R2](../.ui-preview/pilots/qualify_stt_gpu_short_v7_r2_protocol.md)
est prêt : 55 simulations, Ruff et deux revues favorables. Une garde de fichiers
mal placée dans V7 aurait refusé le marqueur anti-rejeu avant NVML ; R2 ferme
ce marqueur avant d'installer la même garde, immédiatement avant NVML. Le test
de composition et le refus du rejeu sont vérifiés, sans activité GPU. Profil
CT/NVIDIA, corpus 12/27 et budgets conservés ; régions anonymes non attestées,
fenêtres coupées non qualifiées. Un nouvel accord humain unique est demandé.
Aucun essai R2, changement GPU de production ou clôture L12 n'est inféré.

### Sauvegardes préparatoires du 12 octobre, 20:54–20:58 UTC

[Code/interface](../.ui-preview/backups/promotion-code-20261012-205450-0d6f7a78/qualification.json) :
34 originaux, 3 015 892 octets, SHA copie/source égaux ; sept nouvelles cibles
confirmées absentes. [Brain/ERP](../.ui-preview/backups/promotion-db-online-20261012-205755-597ae1eb/qualification.json) :
deux snapshots `mode=ro; query_only=ON`, intégrité correcte, zéro anomalie FK,
toutes tables/contenus et restaurations privées identiques. Aucun import
applicatif, changement des sources SQLite ou arrêt du runtime. Ce jeu en ligne
n'est pas distribué atomiquement ; pièces/index et sauvegarde finale après
arrêt restent nécessaires. Le scan de jalons progresse réellement, de 10/30
à 18/30 entre 20:53 et 20:57 ; il n'a pas été interrompu.

L'audit de la demande LM Studio identifie un écart : la disponibilité fraîche
du modèle principal via `/v1/models` ne déclenche pas encore le déchargement
local sans nouvelle génération. Seul le chemin « réponse distante utile » est
qualifié par l'ancien essai réel. Le raccord à la readiness exacte est préparé
en copie, avec les gardes configuration/epoch/leases ; aucune nouvelle capacité
active ou clôture L11/L12 n'est déclarée sur la seule intention.

### Reconnexion sans nouvelle question — candidat V3 non activé

Le [manifest final](../.ui-preview/pilots/llm-ready-recovery-stage-20261012/candidate-manifest-v3.json)
épingle deux sources et un nouveau test. Le [reçu final ciblé](../.ui-preview/pilots/llm-ready-recovery-stage-20261012/qa/green-211245-47ee2463/qualification.json)
passe 45/45 (18 anciens, 27 nouveaux), Ruff et deux relectures. L'invalidation
des epochs au commit exclut le probe démarré pendant la sauvegarde du seul
modèle principal. La version 43/43 et les deux régressions rouges sont conservées.
Le catalogue peut annoncer un modèle JIT installé, sans prouver une génération ;
voir [la portée d'exploitation](22_OPERATIONAL_IMPROVEMENTS.md).

L'UNION privée contient 379 sources Python, 57 ressources NEXT historiques et
224 auxiliaires. Le frontend GRAPH 858/858 reste qualifié séparément. Ruff
global ROOT passe. La première globale Python termine avant collecte sur un
PermissionError de pytest ; zéro JUnit, maps inchangées. La V2 démarre le
12 octobre à 21:26:12 UTC avec des TEMP/cache/report neufs. Aucun succès global,
nouvelle voie réelle LM Studio ou clôture L12 n'est déduit du seul lancement.

La sauvegarde incrémentale utile est préparée : 975 originaux inchangés vérifiés
dans l'archive initiale, onze deltas et trois snapshots SQLite, environ 325 Mo.
Le verrou technique de 1 octet reste explicitement à copier après arrêt. Huit
contrôles purs et la revue indépendante passent, sans copie data. Les 300 s
concernent copie/hash/SQLite après préflight, pas tous les inventaires.
Le changement ACL des seules nouvelles sauvegardes a été refusé par le contrôle
automatique car les accès durables n'étaient pas explicitement autorisés ; une
question humaine précise est en attente. Aucun contournement ou ACL source modifiée.

Une édition échouée a laissé README vide à 21:27:29 UTC. ROOT l'a restauré depuis
les 34 originaux vérifiés (116 894 octets, SHA exact) avant cette publication atomique,
qui conserve à son tour tous les originaux documentaires. Aucun module ou
donnée métier n'est supprimé.

### Complément terminal UNION V2

Le [compagnon terminal](../.ui-preview/pilots/native-ready-union-20261012/qa/python-global-union-v2/root-terminal-no-space-companion.json), SHA 8c4fc658…, confirme les maps 379/57/224 exactes et 646 références canoniques sans dérive. La session 73835 termine exit1 sur ENOSPC lors de la création du reçu ; le code pytest et les comptes restent inconnus. XML de 38 octets tronqué, E/F non attribuables à un défaut produit sans traceback. Le [diagnostic RO](../logs/foresight-runtime/union-v2-capacity-diagnosis-ro-20261012-213952-54175ef9/qualification.json), SHA cf5b0c45…, trouve 139 Mo temporaires et aucun processus de cette exécution dans la fenêtre de création. Environ 4,9 Go libres après fin ; aucun pic physique ou quota établi. Aucune nouvelle globale lancée, purge ou qualification déduite ; une reprise à un worker, surveillance de capacité et première erreur détaillée est préparée.

Le [contrôle RO du fonds Notes](../logs/foresight-runtime/notes-fund-snapshot-ro-20261012-214553-6aec6265/qualification.json) couvre les snapshots vérifiés de 20:57 UTC : une note ERP/version courante et un lien/projection Brain au contenu exact, aucun head non relié ni événement courant manquant. Deux versions préparatoires sont conservées ; aucune pièce jointe présente. Aucune migration ni publication exécutée. Ce petit fonds historique ne dispense pas de la comparaison fraîche avant activation et ne clôture pas T15.

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

Après autorisation utilisateur, ROOT a protégé uniquement
`C:\Agent\.ui-preview\backups` : 66 éléments, dossier racine compris, couvrent
trois sauvegardes préparatoires et 43 fichiers. Les droits Allow de Users
(`S-1-5-32-545`) et Authenticated Users (`S-1-5-11`) sont retirés. Les droits
non ciblés, dont Fred (SID `6448`), SYSTEM, Administrators et les deux SID
techniques, sont conservés. Les propriétaires des 66 éléments et les SHA-256
des 43 fichiers restent identiques, y compris après comparaison avec l’état
précédant la première tentative. Les ACL de Brain, ERP et EG2 sources restent
inchangées ; cette protection ne s’étend pas aux autres dossiers de sauvegarde.

La première tentative `Set-Acl` échoue sur la résolution du domaine ; la seconde
conversion des ACE laisse encore un accès large. Ces deux résultats historiques
restent conservés. La V3 exécutée par ROOT utilise `SetNamedSecurityInfoW`
sur la DACL uniquement ; elle réussit. Le [reçu final](../logs/foresight-runtime/backup-access-protection-20261013-dc8cdf0113eb4120b53b7f1b1275a643.json)
est lié à son inventaire avant modification (SHA-256 dans le reçu).
Les deux [tentatives historiques](../logs/foresight-runtime/backup-access-protection-20261013-96e5bb23e8cb4b10b35ebdb9d9ec0e4a.json)
et [leur reprise](../logs/foresight-runtime/backup-access-protection-20261013-ada86cfcf0ac402fa1fa3cd5e780b401.json)
sont préservées. Cette étape porte sur les accès aux sauvegardes ; L12 demeure
ouvert pour les qualifications matérielles, ASR et premier texte visible.


### T12 : choix réseau et premier lancement V6 — 13 octobre 2026

Le choix utilisateur porte sur la recette fictive T12 de 60 minutes avec le
primaire réseau `http://192.9.110.115:1234`, modèle
`google/gemma-4-26b-a4b-qat`. La variante V6 conserve quinze cas/trente-cinq faits,
les 1224 occurrences scellées, l’ASR CPU et quinze demandes LLM dans trois
fenêtres. Le catalogue OpenAI annonce l’ID exact ; ce constat ne mesure ni le
chargement distant ni la génération.

Le [premier lancement V6](../logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-075610-78025914/controller-final.json) se termine avec `passed=false`
après le délai d’attente du panneau Transcription, avant admission du modèle
et démarrage du driver (`driver_exit=null`). La fixture quitte avec code 0,
le Job est vide avant fermeture du handle, et monitor/watchdog sont terminés.
Le lancement préparatoire est réel ; la séance d’une heure n’a pas commencé.
Le protocole et la readiness ne sont pas comptés comme une heure réussie.

L’[observation séparée du retour réseau](../logs/foresight-runtime/network-recovery-live-20261013-42465a494ce140b9902f7ab10695302b.json) confirme
`fresh_catalog_exact_id_present=true`, `remote_loaded_state_measured=false`
et `generation_performed=false`, avec zéro instance du Gemma local et un état
de libération rapporté par le backend. L’échange HTTP de déchargement lui-même
n’est pas capturé indépendamment. Aucun résultat de génération ou de P95 n’est
ajouté par ce relevé. **L12, T04 matériel et T12/P95/qualité ASR restent ouverts** ;
les historiques sont préservés, Drive reste exclu et l’adaptation visuelle publique
T13 déjà acceptée conserve sa portée.


### T12 V6 : endurance réelle, portée partielle — 13 octobre 2026

L’exécution de **10 h 36 à 11 h 36 (Paris)** atteint 3600,094 s et 1440 fragments
uniques conservés. Six contrôles postflight passent, sans modification des bases
fictives en lecture seule ni création de réunion/action/tâche ERP. Driver et
fixture quittent avec code 0 ; Job vide et fermé, watchdog/monitor/collector
terminés, aucun arrêt forcé ou tardif. Le rejeu mic/120 conserve son reçu sans
doublon. Cette heure utilise uniquement les quinze fichiers vocaux fictifs
neufs et le primaire réseau ; aucun microphone ou loopback n’est ouvert.

La [dérogation d’exécution](../logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-083158-7af6eacb/ROOT_PARTIAL_EXECUTION_DECISION.json)
concerne uniquement la gate visuelle : DOM Transcription réellement rendu,
extérieur `false` et non qualifié. Les critères P95/T12 originaux restent intacts.
L’ASR termine 99 fragments et en conserve 1341 sans transcription terminée ;
le profil CPU de cet essai ne soutient pas encore deux pistes en direct. Les
123 segments bruts donnent 83 occurrences notées, 1141 inconnues. Les 35 faits
produisent 192 contrôles observés (108 motifs retrouvés, 84 non retrouvés) ;
aucune précision globale n’en est déduite. Les échecs de valeurs/unités restent
présents. P95 : zéro mesure sur 1224 occurrences, 30 manquants pour visibilité
non qualifiée et 1194 sans première présence. **T12, ASR et L12 restent ouverts.**

Les trois fenêtres comportent quinze demandes logiques, neuf dispatchs physiques
et aucun extra : trois réponses réelles, six annulations de consommateurs locaux,
trois enrichissements rejetés 502 et trois `InferenceBusy` proactifs attendus
après 2 s. La complétude du workload n’atteste pas le succès de chaque fonction,
la priorité globale, l’annulation dans le navigateur ou l’arrêt GPU distant.
[Résumé réel](../logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-083158-7af6eacb/root-actual-result-summary.json) et
[audit indépendant](../logs/foresight-runtime/t12-realtime-preparation-root-ready-20261013-083158-7af6eacb/independent-terminal-partial-audit-v6.json)
(SHA-256 `04fdb820ee8d0026db12844770c25d494fb71f0816accf0eaa88143cb494db39`).

Deux WAV d’une heure ont ensuite été [assemblés séparément](../logs/foresight-runtime/t12-post-recipe-consolidation-20261013-7af6eacb.json),
115200044 octets chacun / 230400088 au total, après vérification des 1440 sources
et des métadonnées avant/après. Ce résultat post-recette ne remplace pas la
preuve historique d’absence de consolidations longues pendant l’heure.
L’[observation fraîche après séance](../logs/foresight-runtime/network-recovery-live-20261013-c5a92111952943a3a3e5f53e43b3117d.json) confirme primaire annoncé,
secours local `unloaded` et zéro instance Gemma ; elle ne génère rien et ne
capture pas indépendamment l’échange HTTP de déchargement. Les réponses réelles
restent liées au workload. Les premiers essais sont conservés ; Drive reste
exclu et l’adaptation publique T13 garde sa validation antérieure.


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

[Preuves, empreintes et sauvegardes](../logs/foresight-runtime/reviewed-transcript-context-delivery-ROOT-20261016.json).

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

[Preuves de navigation et activation statique](../logs/foresight-runtime/studio-transcript-navigation-delivery-ROOT-20261016.json).

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


### T01 clôturé sur capture microphone Opus réelle — 21 octobre 2026

La navigation vers la liste, le filtre du second projet, le retour à la même
séance et l’actualisation ont conservé la capture Windows. Après pause/reprise
et arrêt normal, les 17 fragments microphone (82,901 s, 341873 octets) et leurs
reçus SQL sont intacts, sans doublon. Le trou mesuré de 9,947 s correspond au
parcours pause/reprise observé et reste explicitement présent dans le bilan.
T01 est clos dans ce contrat ; T02/T03/T04/T16 restent ouverts. Les quatre
refus de double capture sont prouvés par appels API réels, pas par des doubles
clics dans le second onglet. Le loopback n’a fourni aucun fragment. Aucun
audio écouté/transcrit, aucun modèle ; tous les processus de recette sont clos.
Inventaire cumulatif : 13 recettes/17 closes, sans requalification fraîche
des verdicts historiques. Audit :
`.ui-preview/pilots/l12-acceptance-audit-20261016/acceptance-r42.json`.


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


### Traitement long raccordé — 21 octobre 2026

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
