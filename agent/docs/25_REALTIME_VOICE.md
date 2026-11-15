# Voix temps réel : fonctionnement, limites et adaptation à Agent

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


## Séparation du statut direct et de la transcription complète

Le15octobre2026, la transcription complète d'un enregistrement préfère medium
CPU installé. Le statut du direct interroge explicitement ses propres chemins :
small, beam1, contexte500ms et mêmes drapeaux de qualification. Ni le moteur
de capture ni le batch par fragments conservés ne changent de modèle par ce choix.
Le parcours complet avec diarisation et CR est exercé séparément ; voir le
domaine23. Aucun résultat complet n'est reporté comme qualification du direct.


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

Le prochain profil de transcription doit tenir la cadence avant une nouvelle mesure intégrée SQL et Studio. Ces horloges ne clôturent aucun seuil d’affichage.


## Recette assistant V5R2 — résultat partiel, 14 octobre 2026

La recette courte V5R2 a réellement ouvert l’assistant sur une copie fictive et obtenu une réponse réseau sourcée conservant 1250 W, les réserves et les négations. La paire concurrente n’a pas démarré ; annulation et services de fond non exécutés. Le thread de fermeture a été refusé : sortie1, cleanup non qualifié. Les ressources privées sont fermées et les données protégées conservées. **G_ASSISTANT, P95, T12 et L12 restent ouverts.**

[Résultat ROOT](../logs/foresight-runtime/G-ASSISTANT-V5R2-actual-objective-status-ROOT-20261014.json) ; [audit indépendant](../logs/foresight-runtime/G-ASSISTANT-V5R2-partial-actual-independent-audit-remaining-20261014.json).

Le premier delta backend ne vaut ni une carte utile visible ni un P95. Priorité de deux vrais demandeurs et annulation via le bouton produit restent à observer ; arrêt du calcul distant inconnu.


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


Analyse du **2 octobre 2026**. Statut : **analyse et architecture proposée**.
Décision utilisateur : la voie vocale par API cloud payante est écartée.
Une éventuelle réalisation Agent privilégiera une chaîne locale ; aucun achat,
appel Realtime cloud ou installation de moteur vocal supplémentaire n’est réalisé.
Aucun assistant vocal temps réel, fournisseur cloud ou nouveau service n’est
activé par ce document. Le serveur Agent reste unique sur :8001.

**Complément du 11 octobre 2026.** Le Studio ajoute une capture de réunion
directe durable, navigateur et Windows micro/système, avec transcription locale
provisoire avant l'arrêt et consolidation/relecture ensuite. Ce parcours est
distinct du dialogue vocal/TTS étudié ici ; il conserve le moteur batch hérité.
La qualité et la latence industrielles du direct ne sont pas qualifiées par
la seule disponibilité du runtime. Scopes, notes versionnées et publication
humaine n'entraînent aucune tâche automatique. Voir
[le parcours audio et ses limites](23_MEETING_AUDIO.md),
[Notes canoniques](34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md) et
[l'état de livraison](38_FORESIGHT_DELIVERY.md).

**Complément du 13 octobre 2026 après publication des indicateurs.** La QA
frontend actuelle passe 916 tests. La comparaison CPU d'une même phrase en
int8_float32 et float32 conserve l'erreur 1250 W → 2250 W. Le nouveau raccord
isolé des preuves UI/CUA passe quatre tests purs ; sa calibration réelle et
le P95 restent à vérifier. Aucun nouveau dialogue vocal n'est activé.
Les recettes antérieures restent conservées dans
[l'état de livraison courant](38_FORESIGHT_DELIVERY.md).


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

Cette étude complète le [parcours réunion audio existant](23_MEETING_AUDIO.md)
et la [refonte de l’interface](24_UI_UX_REDESIGN.md). Elle examine OpenDots au
commit `b01ac1f6a903e5e56c119d960901353ac0a3d171`. Le fichier serveur vocal de
la branche par défaut avait la même empreinte Git lors de la vérification.
Les contraintes OpenAI ont été vérifiées dans sa documentation officielle à la
date de l’analyse ; disponibilité, tarifs et politiques peuvent évoluer.

## 1. Deux besoins vocaux différents

**Dialoguer avec Agent.** L’utilisateur demande, par exemple : « Quels sont les
points ouverts du CDC de ce projet ? » L’assistant doit comprendre la question,
consulter les bonnes sources et expliquer la réponse à voix haute. Il doit être
possible de l’interrompre, de poursuivre en texte et de voir les preuves.

**Prendre un compte rendu de réunion.** Plusieurs personnes parlent, parfois en
même temps. Il faut conserver l’audio, identifier les interventions, corriger
le texte et les noms, puis valider décisions et actions. La priorité est la
fidélité du compte rendu et sa provenance. Une réponse automatique de
l’assistant après chaque prise de parole ne convient pas à ce parcours.

| Aspect | Conversation vocale OpenDots | Réunion audio héritée d’Agent (batch) |
|---|---|---|
| Entrée | Microphone envoyé en continu pendant l’appel | Fichier importé ou enregistrement micro, envoyé après arrêt |
| Traitement | Compréhension et réponse audio par un modèle Realtime | Transcription Faster-Whisper puis attribution aux voix Sherpa |
| Participants affichés | Utilisateur et assistant | Interlocuteurs regroupés par voix, noms corrigés humainement |
| Sortie | Réponse parlée, sous-titres et reçu d’appel | Transcription révisée, brouillon LLM puis CR validé |
| Original audio | Pas de fichier audio conservé par le code vocal étudié | Original conservé avec la source du projet |
| Publication métier | Résumé ajouté au fil de conversation | Publication explicite dans Revues et connaissance sourcée |

Les légendes « You » et « Dot » ne constituent donc pas une diarisation de
réunion. La diarisation regroupe les passages qui semblent appartenir à la même
voix ; elle ne reconnaît pas automatiquement l’identité réelle d’une personne.
Sources : [interface d’appel OpenDots](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/CallView.tsx),
[client vocal](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/useVoice.ts),
[réunions Agent](23_MEETING_AUDIO.md).

## 2. Comment fonctionne un appel OpenDots

### Connexion et circulation de l’audio

1. Un clic de l’utilisateur déclenche la permission microphone du navigateur.
   Le client crée une `RTCPeerConnection`, ajoute les pistes audio et ouvre le
   canal d’événements `oai-events`.
2. Le navigateur produit une offre SDP décrivant la connexion et la transmet
   à la route OpenDots `/api/voice/calls`, avec l’identifiant de conversation.
3. Le serveur vérifie le fil, la configuration et l’état de pause, puis crée
   un reçu local. Il transmet le SDP et la configuration de session à
   `https://api.openai.com/v1/realtime/calls` avec `VOICE_API_KEY`.
4. OpenAI retourne un SDP de réponse et un identifiant de session contrôlable.
   Le serveur retourne au navigateur le SDP et l’identifiant local de l’appel.
5. Le navigateur applique la réponse. Les pistes WebRTC transportent l’audio
   vers le fournisseur et la voix de réponse vers le haut-parleur. Le canal
   d’événements porte les états, transcriptions et demandes d’outils.

La clé fournisseur reste côté serveur. **Le code étudié utilise la négociation
SDP relayée par le serveur, sans délivrer de token éphémère au navigateur.**
La documentation OpenAI décrit aussi une autre approche, avec token éphémère ;
il faut distinguer cette possibilité API de l’implémentation réelle d’OpenDots.
Sources : [client](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/useVoice.ts),
[serveur](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/voice.ts),
[WebRTC officiel OpenAI](https://developers.openai.com/api/docs/guides/realtime-webrtc).

### Compréhension, sous-titres et prise de parole

`VOICE_MODEL` choisit le modèle vocal ; l’essai publié du dépôt utilise
`gpt-realtime-2.1`. `VOICE_NAME` choisit la voix, avec `marin` par défaut.
Le modèle Realtime reçoit directement l’audio. En parallèle,
`gpt-4o-mini-transcribe` transcrit l’entrée pour afficher le texte utilisateur ;
le texte de la réponse provient des événements audio de l’assistant.
Il ne s’agit pas d’une chaîne où ce seul texte transcrit serait obligatoirement
l’entrée du modèle vocal. Sources : [configuration d’appel](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/voice.ts),
[évaluation audio officielle](https://developers.openai.com/cookbook/examples/realtime_eval_guide).

OpenDots configure `semantic_vad` : le fournisseur tente de déterminer si la
phrase est terminée, puis déclenche une réponse. `interrupt_response: true`
permet de reprendre la parole pendant que l’assistant parle. Avec WebRTC,
le fournisseur gère la partie d’audio générée qui n’a pas encore été jouée.
La détection dépend du signal et du contenu : un silence, une hésitation ou
du bruit peuvent modifier la prise de tour. Sources : [VAD officiel](https://developers.openai.com/api/docs/guides/realtime-vad),
[interruptions Realtime](https://developers.openai.com/api/docs/guides/realtime-conversations).

### Délégation des travaux longs

Le modèle vocal reçoit une consigne de réponses courtes et un seul outil,
`ask_compute`. Pour rechercher ou raisonner avec des preuves, il formule une
demande de calcul. Le navigateur la relaie à `/api/voice/calls/{id}/compute`.
Le serveur lance l’agent spécialiste dans le même fil Intelligence, puis le
résultat est renvoyé comme sortie d’outil au modèle vocal.

Le moteur de calcul utilise le fournisseur `OPENAI_MODEL` / `OPENAI_BASE_URL`
et les outils permis au spécialiste. Un calcul peut donc utiliser un fournisseur
différent de la voix. Les capacités éventuelles de navigation, fichiers ou shell
concernent le système isolé d’OpenDots et ses permissions, pas automatiquement
le poste de l’utilisateur. Sources : [pont vocal](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/voice.ts),
[agent spécialiste](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/dot-agent.ts),
[exécution dans le fil](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/headless.ts).

**Interrompre la parole ne signifie pas annuler le calcul.** Dans ce code,
un événement de début de parole n’annule pas la requête `ask_compute` déjà
lancée. Le calcul s’arrête notamment à la fin de l’appel, à l’expiration ou
sur sa propre limite de temps. Cette distinction doit être visible dans Agent.
Source : [gestion client et retour d’outil](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/useVoice.ts).

## 3. Limites codées et limites du fournisseur

| Limite vérifiée | Portée | Effet pratique |
|---|---|---|
| Un seul appel dans la map du service | OpenDots, toute l’instance | Ne suffit pas à une utilisation simultanée par plusieurs collaborateurs |
| 20 s pour initialiser ; expiration si non activé sous 30 s | OpenDots | Un réseau lent ou une découverte d’historique lente peut empêcher l’appel |
| 15 min, timers côté client et serveur | OpenDots | Appel clos ; nouvelle session nécessaire pour continuer |
| Six demandes `ask_compute` distinctes | OpenDots | Limite les recherches répétées ; les doublons de même identifiant sont dédupliqués |
| 90 s par calcul | OpenDots | Les analyses longues doivent passer par une file durable |
| 12 derniers messages, bornés à 12 000 caractères | Contexte initial OpenDots | Ne transmet pas tout l’historique ni toute la connaissance du projet |
| Demande de calcul ≤ 4 000 caractères ; contexte d’appel ≤ 12 000 | API OpenDots | Le calcul reçoit un contexte partiel |
| Reçu final ≤ 20 000 caractères | Client et API OpenDots | Le client conserve les premiers caractères ; une fin dépassant la borne est écartée |
| 45 s pour synchroniser le reçu ; 5 s pour raccrocher le fournisseur | OpenDots | Un reçu local peut exister avec une erreur de synchronisation ou de raccrochage |
| 60 min maximum de session | API Realtime, documentation actuelle | Ce plafond ne remplace pas la borne OpenDots de 15 min |

Sources : [limites du service](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/voice.ts),
[contrats HTTP](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/workspace-routes.ts),
[contexte initial](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/platform.ts),
[client](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/useVoice.ts),
[cycle de session API](https://developers.openai.com/api/docs/guides/realtime-conversations).

Les quotas API dépendent aussi du modèle et du niveau d’usage du compte.
Une configuration de clé présente ne prouve ni l’accès au modèle, ni un appel
réussi. Aucune latence chiffrée sur notre poste ne peut être déduite d’une vidéo
accélérée. Sources : [modèle vocal officiel](https://developers.openai.com/api/docs/models/gpt-realtime-2.1),
[notes de démonstration](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/docs/demos/README.md).

## 4. Sauvegarde, preuve et reprise

Pendant l’appel, le client accumule les textes reçus dans un tableau en mémoire.
Il envoie le texte à la clôture, ou tente un envoi `keepalive` lors du démontage
du composant. Il ne stocke pas l’audio original. Le serveur conserve un reçu
SQLite avec fil, dates, statut, texte et erreur ; il demande ensuite un court
résumé au même fil CopilotKit Intelligence. Une réponse tardive peut remplir
un reçu vide sans modifier son statut final. Sources : [client](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/client/useVoice.ts),
[stockage](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/workspace.ts),
[synchronisation](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/voice.ts).

**Inférences issues du code, incidents non reproduits ici :**

- Une fermeture brutale du navigateur peut perdre un texte encore non envoyé.
  `keepalive` est une tentative de clôture, pas une sauvegarde incrémentale.
- Les textes sont ajoutés dans l’ordre d’arrivée des événements ; le client ne
  reconstruit pas les tours par `item_id`. Le fournisseur précise que l’ordre de
  fin de transcription entre tours n’est pas garanti. Une chronologie fiable
  demande des identifiants, horodatages et une réconciliation.
- Le reçu n’est pas une preuve de ce que chaque personne a dit ou de toute la
  réponse réellement entendue, notamment lors d’une interruption.
- Le contrôle des appels actifs et leurs identifiants fournisseur se trouvent
  dans une map en mémoire. La récupération après redémarrage doit être durcie :
  le cycle d’arrêt étudié ne relie pas explicitement le service vocal à une
  clôture de tous les appels.

Sources complémentaires : [ordre des transcriptions](https://developers.openai.com/api/docs/guides/realtime-transcription),
[arrêt du serveur](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/index.ts),
[cycle de plateforme](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/platform.ts).

SQLite conserve les pages et reçus ; Intelligence conserve l’historique des
conversations. Une copie SQLite seule ne sauvegarde donc pas tout OpenDots.
Agent conservera ses données canoniques dans ses moteurs existants, avec les
sauvegardes du [parcours réunion](23_MEETING_AUDIO.md), sans ajouter ce deuxième
stockage de conversation par simple reprise du composant vocal.
Source : [sauvegardes OpenDots](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/docs/SETUP.md).

## 5. Réseau, confidentialité et coût

### Ce qui reste local et ce qui sort

Le frontend et le serveur OpenDots peuvent être hébergés localement, mais
l’adaptateur vocal étudié appelle **OpenAI cloud**. `OPENAI_BASE_URL` ne change
que le calcul ; il ne redirige pas la voix. Être compatible avec
`/chat/completions` ne signifie pas supporter WebRTC et l’API Realtime.
Audio et contexte sont transmis au fournisseur vocal, et l’historique passe
par le service Intelligence configuré. L’hébergement local de l’application
ne suffit donc pas à un parcours entièrement hors ligne. Source :
[configuration officielle du dépôt](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/docs/SETUP.md).

OpenAI indique que les données API ne servent pas à entraîner ses modèles par
défaut, sauf partage volontaire. Pour `/v1/realtime`, la documentation annonce
des journaux de surveillance pouvant être conservés jusqu’à 30 jours, avec
exceptions ; les contrôles Modified Abuse Monitoring / Zero Data Retention
dépendent d’une approbation et de leurs conditions. Ces paramètres ne couvrent
pas automatiquement un autre fournisseur ou le stockage Intelligence.
Ils ne constituent pas à eux seuls une garantie de conformité pour une réunion
client. Source : [contrôles de données OpenAI](https://developers.openai.com/api/docs/guides/your-data).

OpenDots fixe `api.openai.com` : choisir une région européenne demanderait une
adaptation et la vérification de l’éligibilité réelle du compte et des services.
Le dépôt est mono-propriétaire et ne revendique pas un audit de sécurité.
Sources : [code vocal](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/src/server/voice.ts),
[limites de sécurité](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/SECURITY.md).

Pour Agent, la transcription et la diarisation actuelles utilisent les modèles
locaux sans envoyer l’audio à un service de transcription. La synthèse utilise
le fournisseur LLM configuré : son caractère local ou distant dépend de ce
réglage. Source : [paramétrage des réunions](23_MEETING_AUDIO.md).

### Tarifs vérifiés, pas de coût par réunion mesuré

Au 2 octobre 2026, les tarifs affichés pour `gpt-realtime-2.1` sont :

| Modalité | Entrée / million de tokens | Entrée en cache | Sortie / million de tokens |
|---|---:|---:|---:|
| Audio | 32 $ | 0,40 $ | 64 $ |
| Texte | 4 $ | 0,40 $ | 24 $ |

La transcription `gpt-4o-mini-transcribe` est également facturée ; la page
indique une estimation de 0,003 $/minute. Le calcul délégué, les services et
l’infrastructure suivent leur propre facturation. Source :
[tarifs officiels OpenAI](https://developers.openai.com/api/docs/pricing).

Un appel de 15 minutes n’a pas un coût fixe déductible de ces seuls tarifs :
le volume de parole, les réponses, le contexte, le cache et les calculs comptent.
Le code vocal étudié n’enregistre pas un suivi complet de consommation.
Un prototype Agent devra mesurer le coût réel et fournir une limite de durée
et de dépense configurée, sans promettre un montant avant essai.

## 6. Adaptation proposée pour Agent

### Assistant vocal contextuel

Parcours proposé dans le panneau Assistant de la [nouvelle interface](24_UI_UX_REDESIGN.md) :

1. Afficher le projet interrogé et le mode local/cloud avant connexion.
2. Écouter la question, afficher les sous-titres et permettre l’interruption.
3. Interroger les API de connaissance, mails, CDC ou réunions du même serveur
   FastAPI, avec des outils explicitement autorisés pour ce projet.
4. Expliquer une réponse courte et ouvrir les sources dans le panneau de détail.
5. Créer un brouillon pour une action métier ; sa publication reste validée
   dans l’interface. Une parole ambiguë ne change pas une donnée de référence.

La séparation OpenDots entre voix rapide et calcul spécialisé est à reprendre.
Les travaux longs restent dans les files durables d’Agent, avec progression
et annulation réelles ; ils ne dépendent pas de la durée de l’appel. Un
changement de question doit pouvoir annuler ou écarter un résultat devenu
obsolète. L’autorisation se vérifie dans FastAPI, pas seulement dans le prompt.

Deux architectures ont été examinées ; la voie locale est retenue pour une
éventuelle réalisation, après la décision utilisateur :

- **Cloud vocal + calcul Agent — écarté** : connexion Realtime et voix naturelle,
  outils de calcul reliés au moteur existant. Cela demande un fournisseur vocal
  et une configuration explicite de confidentialité, quotas et dépenses.
- **Chaîne locale** : ASR continu, LLM configuré, puis synthèse vocale locale.
  La maîtrise des données est meilleure si tous ces moteurs sont locaux, mais
  la latence et la prise de tour résultent de plusieurs traitements à coordonner.
  Sherpa propose de l’ASR français continu et du TTS ; leurs modèles doivent
  être sélectionnés et testés, avec leurs licences et performances propres.
  Sources : [ASR français Sherpa](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html),
  [TTS Sherpa](https://k2-fsa.github.io/sherpa/onnx/tts/index.html).

### Réunion avec texte en direct

Une évolution distincte peut afficher des sous-titres pendant l’enregistrement :
audio sauvegardé par parties, transcription provisoire, puis traitement complet
et réconciliation à la fin. Les identifiants de voix en direct resteraient
provisoires. La relecture, les citations et la publication du CR conserveraient
les règles du [moteur réunion actuel](23_MEETING_AUDIO.md).

Cette évolution n’est pas obtenue en ajoutant un bouton d’appel : le script
actuel décode le fichier complet, lance `OfflineSpeakerDiarization`, puis
Faster-Whisper. Il faut concevoir transport, sauvegarde progressive, reprise,
gestion des doublons et révisions. Une fenêtre de transcription plus courte
réduit l’attente mais laisse moins de contexte au modèle ; le compromis doit
être mesuré sur nos enregistrements.

## 7. Vérifications réalisées et travail restant

**Réalisé pour cette étude :** lecture du code OpenDots, comparaison du fichier
serveur courant au commit épinglé, lecture des onze tests serveur vocaux et
des notes de démonstration, vérification des sources officielles API, tarifs,
données et alternatives locales. Les tests OpenDots ont été consultés, pas
exécutés ; leurs services sont simulés.

Le dépôt indique des essais réels d’audio, sous-titres, commandes de micro et
haut-parleur, raccrochage et persistance au 30 septembre 2026. Il précise que
la délégation déclenchée oralement et le comportement complet d’interruption
nécessitent encore des vérifications live. Sources :
[tests serveur](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/tests/voice.test.ts),
[périmètre des essais](https://github.com/CopilotKit/OpenDots/blob/b01ac1f6a903e5e56c119d960901353ac0a3d171/docs/demos/README.md).

**Non réalisé dans Agent :** aucun appel Realtime, essai matériel de conversation
vocale en français, mesure de latence, benchmark local ASR/TTS ou facture vocale.
L’essai antérieur du parcours réunion avec voix fictives ne valide pas ces
nouveaux usages.

Avant livraison d’un moteur temps réel, vérifier :

- Français technique : noms, codes projet, dimensions, unités, négations et dates.
- Micro casque et salle, distance, bruit, écho et interventions qui se recouvrent.
- Délai de sous-titre, de première réponse audio et de retour d’outil, avec
  distribution des mesures ; aucune promesse tirée d’une vidéo accélérée.
- Interruption de parole, annulation de calcul et résultat tardif ; permissions
  et validation métier identiques à celles du parcours texte.
- Déconnexion, fermeture d’onglet, expiration et redémarrage serveur ; audio et
  texte récupérables, état final explicite, fournisseur réellement raccroché.
- Consommation réelle, plafonds de dépenses, visibilité local/cloud et absence
  de données de réunion transmises sans le mode choisi.

La documentation officielle recommande des essais représentatifs plutôt qu’un
choix de latence fondé uniquement sur de l’audio synthétique. Sources :
[évaluation Realtime](https://developers.openai.com/cookbook/examples/realtime_eval_guide),
[compromis de transcription](https://developers.openai.com/api/docs/guides/realtime-transcription).

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

