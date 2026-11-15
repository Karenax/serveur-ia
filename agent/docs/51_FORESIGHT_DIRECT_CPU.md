# Direct CPU : disponibilité rétablie et modèle medium

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


## Diagnostic du bruit stationnaire — 22 octobre 2026

Un seul filtre spectral, paramètres figés avant inférence, est mesuré sur les
quinze Opus fictifs complets avec le même medium CUDA. Il estime le bruit sur les
échantillons, sans recevoir texte attendu, repère de parole ou vocabulaire ajouté.
Les originaux sont conservés par empreinte. Le compteur littéral passe de 28/35
à 29/35 uniquement grâce à « 2 400 euros » au lieu de « 2 400 € » : aucun nouveau
fait métier n’est récupéré. Le mot de sécurité reste incorrect (« configuration »)
et le refus du client en chevauchement reste absent. Le candidat est écarté et
n’est appliqué ni au moteur ni aux captures. Les deux Jobs et le modèle sont fermés.
La suite backend complète continue sur des sources inchangées. L03/L12 restent
ouverts ; aucun nouveau seuil ni critère de réussite n’est introduit.
Preuve : `logs/foresight-runtime/SPECTRAL-ASR-CANDIDATE-ROOT-20261022.json` ; audit courant `acceptance-r84.json`.


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
Preuve : `logs/foresight-runtime/SPEECH-GPU-SELECTION-ROOT-20261022.json` ; audit courant `acceptance-r83.json`.


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

Livraison du 16 octobre 2026. L03 et L12 restent ouverts.

Le diagnostic de préparation révélait un moteur direct installé mais sans reçu
de qualification runtime reconnu. Le worker acceptait déjà les fragments lorsque
le direct était explicitement activé ; l’absence du reçu faussait surtout son
état de disponibilité affiché. La transcription complète des fichiers fonctionnait
déjà avec medium, indépendamment de ce problème.

## Essais réels sur fichiers fictifs

Trois WAV SAPI déjà conservés et annotés sont utilisés : `clean-02`, `clean-03`
et `clean-09`, du corpus `t12-sapi-boundaries-20261013`. Aucun enregistrement de
microphone ou de son système, aucune lecture audible, aucun GPU, LLM ou
téléchargement. Les étiquettes mic/system désignent seulement les pistes fictives.
Les bases et les fichiers dérivés restent dans deux répertoires privés.

Le parcours courant utilise réellement `store_chunk → admission → process_chunk
→ ResidentWhisper → segments SQL → événement transcript.updated`. Les mêmes
acquittements sont rejoués et les segments terminés ne sont ni dupliqués ni
réécrits. Le deuxième fragment mic vérifie aussi le contexte PCM et les repères
absolus ; la piste system conserve son repérage indépendant.

| Observation | small CPU | medium CPU |
|---|---|---|
| Pipeline et persistance | 3fragments terminés, rejeu exact | 3fragments terminés, rejeu exact |
| Puissance attendue1250W | **2250W**, erreur critique | **1250W** |
| Six valeurs annotées | Erreur de puissance conservée dans le rapport | 230V,16A,1250W,350lux,0,2mm et1,5m présentes |
| Premier fragment, traitement/app compris | 8,753s | 11,654s |
| Deux fragments suivants | 4,000s et4,052s | 6,785s et7,176s |
| Essai complet | 17,872s | 27,393s |
| Arrêt du worker | Naturel, code0 | Naturel, code0 |

Les six expressions numériques du contrôle medium sont fixées avant son lancement
dans `.ui-preview/l03-current-direct-20261016/critical-criteria.json`. Elles ne sont
pas transmises au décodeur. Aucune correction manuelle des sorties n’est comptée
comme une réussite du modèle. Les anciens motifs du corpus et les sorties small
restent conservés, y compris un motif ne reconnaissant pas la graphie `16A` ;
ce défaut de motif ne transforme pas ce nombre correct en erreur ASR.

L’essai medium vérifie les valeurs de ces trois phrases propres, pas toutes les
négations, voix, bruits, chevauchements ou valeurs industrielles. Les temps sont
ceux du service sur fichiers, pas une mesure de fin de parole à affichage DOM.
Les temps à chaud dépassent déjà la cible initiale de5s ; aucune qualification de
latence directe n’est accordée. La relecture reste obligatoire avant publication.

## Sélection et reçu de disponibilité

Sur CPU, `live_speech.runtime_paths()` préfère désormais le medium **déjà installé
et complet** dans `.models/audio-medium`. Les réglages explicites
`PB_SPEECH_MODELS_DIR` et `PB_SPEECH_PYTHON` restent prioritaires. Le réglage
`PB_MEETING_SPEECH_MODELS_DIR` demeure propre à la transcription complète et ne
reconfigure pas le direct. Une installation medium absente, partielle ou invalide
conserve l’ancien chemin `.models/audio` ; aucun poids n’est téléchargé ou supprimé.
La sélection n’active pas CUDA et ne change pas les paramètres du décodeur.

Le moteur medium CPU est testé avec le même profil que celui sélectionné :
faster-whisper1.2.1, CTranslate2 4.8.2, int8,4threads, français, beam1, VAD et
horodatages de mots, contexte PCM500ms. Le code de traitement du produit est
identique à celui de l’essai ; seule la fonction de sélection du répertoire a
changé, ce qui est contrôlé par comparaison AST.

Le reçu manquant `logs/foresight-runtime/audio-qualification.json` est créé avec
le profil, la taille/date et l’empreinte des poids et de la configuration, ainsi
que la référence au résultat réel. Il autorise le témoin **disponible en essai**.
`qualified_live_latency=false` et `industrial_quality_qualified=false` restent
explicites. Un modèle, profil ou réglage de threads différent ne récupère pas
automatiquement cette preuve. Le reçu ne constitue ni une recette de capture
matérielle ni une preuve de déconnexion physique du réseau.

81contrôles ciblés sélection/profils/direct/admission passent, Ruff aussi. Avant
activation du backend8001, sauvegardes et absence de capture active sont vérifiées.
Les données protégées Brain/ERP sont comparées inchangées. Après redémarrage,
l’API confirme medium CPU, disponible en essai, **non chargé au repos**, avec
qualité et latence globales non qualifiées. Aucun modèle n’est chargé pour cette
activation de métadonnées ; il le sera au prochain traitement explicitement lancé.

L’ancien small, les paramètres explicites, les fichiers et les anciennes preuves
sont conservés. Pour un retour technique, arrêter le direct à un point sûr puis
réactiver l’ancien chemin via le réglage explicite ; ne pas restaurer une ancienne
base sur de nouvelles saisies. Le reçu medium ne qualifie pas le modèle small.

## Preuves

- small réel : `C:\Agent\v\direct-d09c51bd7ef4\result.json` ;
- medium réel : `C:\Agent\v\direct-47465179c225\result.json` ;
- contrats : `.ui-preview/l03-current-direct-20261016/contracts.xml` ;
- activation : `.ui-preview/backups/L03-medium-direct-activation-4e55d5486c4343c3bafae9cebdfcb36b/ROOT-activation.json` ;
- audit : `logs/foresight-runtime/L03-medium-direct-delivery-ROOT-20261016.json`.


### Corpus medium CPU et conservation — 16 octobre 2026

Les15WAV fictifs sont maintenant couverts (12nouveaux,3réutilisés) :32/35motifs
gelés, un pluriel sans effet métier et deux erreurs réelles dans bruit/chevauchement.
Le direct reste en essai ; L03 et la latence visible restent ouverts. Les fragments,
rejeux et horodatages sont intacts, worker fermé naturellement. Les sauvegardes
Brain/ERP/EG2 sont restaurées et vérifiées ;89/91tables sont exactes, deux journaux
dérivés sont expliqués séparément, données/validations métier conservées. Le global
backend est encore en cours ; aucun succès complet T15/L12 n’est déduit de ces seuls
résultats. Détail : `docs/53_FORESIGHT_CORPUS_PRESERVATION.md`.



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


Comparaison CPU medium beam5 du 21 octobre sur six Opus fictifs existants :
les trois phrases de mesures propres restent correctes, mais le bruit déforme
encore « consignation » et le chevauchement perd encore la négation du client.
Ce changement de décodage n’apporte pas de correction des deux défauts ; le
profil produit beam1 reste inchangé. Aucun microphone, GPU, LLM ou téléchargement.
Les temps des deux passages ne constituent pas un benchmark A/B contrôlé.
L03 reste ouvert ; aucune nouvelle tentative identique n’est nécessaire.
Preuve : `logs/foresight-runtime/L03-OPUS-BEAM5-ROOT-20261021.json`.


Filtrage spectral diagnostique du21octobre : sept Opus fictifs déjà conservés,
paramètres génériques fixés, aucun texte attendu transmis au modèle. Le signal
bruité change effectivement (écart L2 relatif7,69%), mais les sept transcriptions
restent textuellement identiques au profil sans filtre. Les deux erreurs
bruit/chevauchement persistent ; aucun filtre n’est activé dans Agent. Le modèle
CPU est fermé, aucune capture ni transmission, originaux intacts. Cette piste
n’apporte pas d’amélioration et n’appelle pas un nouvel essai identique.
Preuve : `logs/foresight-runtime/L03-OPUS-DENOISE-ROOT-20261021.json`.

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
pas abaissés après calcul. À la date de cette observation, le Jabra était absent ; il a ensuite été rebranché et testé (rapport JABRA-SWITCH du 21 octobre).

Régression complète courante sur713empreintes sources inchangées : frontend
969tests/94fichiers réussis, TypeScript/Vite réussis et JS/CSS servis identiques.
L’index HTML diffère seulement par espaces/fins de ligne, URLs inchangées.
Ce passage backend (ancienne session 51340) est terminé avec succès : 2793 tests, un ignoré et 54 sous-tests ; voir `.ui-preview/integration-context-20261021/terminal.json`.
Il précède les deltas ultérieurs de surveillance audio et de statut des questions.
Les 969 tests frontend décrivent ce passage historique ; le résultat courant est 983 tests/95 fichiers.
Bilan courant : 9/13 lots, 17/25 fonctions, 15/17 recettes ; L03 et L12 restent ouverts.



### Bilan consolidé du 21 octobre 2026 — diagnostics audio non retenus

État vérifié dans l’audit r52 : **17/25 fonctions, 9/13 lots et 15/17 recettes qualifiés**. L02, L03, L11 et L12 restent ouverts ; T03 et T16 restent ouverts. Le global backend précédent est terminé : 2793 tests réussis, un ignoré et 54 sous-tests. Les derniers correctifs ont leurs contrôles ciblés ; aucun nouveau global complet du dernier arbre n’est revendiqué. Le frontend courant compte 983 tests réussis sur 95 fichiers.

Le débruitage neuronal GTCRN et la séparation Conv-TasNet ont été évalués sur des fichiers vocaux fictifs existants. Ils restent exclus du produit : erreurs persistantes de consignation/négation, et régression d’une réserve « reste à vérifier » en affirmation. Le corpus initial et les sorties défaillantes sont conservés. Medium reste le profil de transcription ; aucun nouvel enregistrement n’est lancé par cette consolidation.

Détail et provenance : `docs/51_FORESIGHT_DIRECT_CPU.md`. Preuve : `logs/foresight-runtime/L03-NEURAL-AUDIO-DIAGNOSTICS-ROOT-20261021.json`.

GTCRN : modèle de 535 638 octets provenant de la publication sherpa-onnx ; empreinte locale conservée, aucun digest éditeur disponible. Il laisse « consignation » incorrect et dégrade une consigne en chevauchement. Aucun alignement temporel du signal filtré n’est qualifié.

Conv-TasNet : export communautaire ONNX de 20 154 131 octets, révision `da50e0fa7789356790994bc898290134fef5d42d`, SHA LFS vérifié ; licence déclarée CC-BY-SA-4.0. La sortie brute présente un gain aberrant. Les essais ultérieurs conservent séparément une calibration acoustique globale puis par source/polarité, sans texte attendu donné au moteur. La reconstruction acoustique ne prouve pas la fidélité linguistique : le chevauchement initial reste erroné.

Un cas supplémentaire à deux voix distinctes a été annoté et scellé avant sa transcription, à partir de tours fictifs préexistants puis recompressé en Opus. Il complète le corpus initial sans le remplacer. La séparation récupère partiellement le second propos mais transforme une vérification encore attendue en vérification acquise. Aucun assemblage automatique de variantes d’après la référence n’est adopté.

Tous les processus privés de ces diagnostics sont terminés avec code 0, Job vide et poignées fermées ; ce code prouve la fin du diagnostic, pas la réussite qualité. CPU uniquement, sans microphone, lecture audio, GPU, LLM ou base métier. Deux téléchargements privés de modèles ont eu lieu ; aucun ajout de dépendance ou distribution produit. La garde Python de sockets ne constitue pas une coupure réseau physique.
