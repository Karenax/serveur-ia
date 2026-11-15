# EmbeddingGemma 2 — moteur unique

## Kiara — retrait du moteur multimodal local

Le moteur multimodal LiteRT sur CPU est obsolète dans Kiara. L’index, les
commandes et le moteur locaux ont été retirés du parcours de recherche.
La recherche sémantique utilise EG2 sur la P2200. Les sections historiques
ci-dessous décrivent les essais antérieurs au retrait.

## File EG2 et attente prolongée — 4 novembre 2026

Cette section actualise la politique de reprise courte décrite plus bas.
Les appels EG2 de production, recherche et diagnostic réutilisent la file IA
par adresse de serveur. Une seule inférence d'Agent est envoyée à la fois sur
cette adresse, y compris avec plusieurs boucles asyncio ou threads. Les clients
externes et l'indexation interne du serveur ne sont pas contrôlés par cette file.
Une annulation ou expiration retire son ticket et libère toute réservation.

Réglages activés : 600 s pour le LLM et la mémoire, lots EG2 de deux textes.
Maximum 600 s par lot d'embeddings, file et reprises comprises. Les réponses
429 et 503 provoquent une reprise du même lot et du même modèle : jusqu'à 20
tentatives dans ce budget, délai croissant jusqu'à 30 s par défaut ; un
`Retry-After` numérique est borné à 0,25–60 s. Aucun basculement d'encodeur.
La recherche abandonne son ancien plafond de 20 s ; le témoin EG2 attend aussi
dans la file avec son délai configuré. Les API Brain/diagnostic acceptent 600 s.

Selon l'état communiqué par l'utilisateur, EG2 est sur CPU, deux threads,
float32, et accepte une requête à la fois tous clients confondus. Ce matériel
n'a pas été mesuré par Agent. Le test réel d'un lot de huit passages de mail
(11 288 caractères) échoue à 30,06 s ; les mêmes textes par deux réussissent
en 11,00 / 14,48 / 6,64 / 4,89 s. Augmenter le délai d'Agent ne modifie pas cette
coupure observée dans le relais : les lots de deux restent la configuration
opérationnelle. `mail-batch-diagnosis.json` conserve la preuve dans les logs Kiara.

Validation : 136 tests ciblés conformes, dont concurrence entre canaux, exclusion
mutuelle avec un appel synchrone, annulation, expiration et reprise 429/503.
Deux tests PCM sans rapport avec EG2 exclus après un FileNotFoundError lors de
la création d'un WAV temporaire ; cette erreur n'a pas été corrigée ici.
La suite globale n'est pas qualifiée par cette évolution. Sources, classements,
validations et index existant sont conservés ; sauvegarde avant les réglages.
La reprise réelle termine avec `running=false`, six mails indexés et zéro échec
restant. La preuve finale figure dans
`logs/kiara-config-20261104-100510/queue-final-qualification.json`.

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
ni changement des données actives. **Le raccord au GPU réel et au Studio reste
à assembler puis à qualifier** ; cette fixture ne clôture pas L03 ou L12.

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


## Dessins CAO : PNG et texte PDF traités sur CPU, qualité visuelle encore refusée — 15 octobre 2026

L’essai privé V1R2 a réellement utilisé LiteRT-LM 0.18.0 et EG2 complet sur CPU4/768 pour huit vecteurs de rendus PNG et de texte PDF issus de dessins CAO ; les huit originaux DXF/SVG sont conservés et leur extraction reste non prise en charge. La recette toutes modalités reste refusée : deux citations texte sur deux passent au rang1, mais les deux recherches visuelles renvoient un PDF en premier et échouent au critère image. Les deux contrôles négatifs sont vides, sans fuite de projet/version ; les 16 sources et 16 versions sont conservées au rejeu. Aucune lecture CAO native, activation canonique, P95 ou clôture L09/L12 n’est qualifiée.

Piste future non testée : un filtre Images/Textes choisi explicitement par l’utilisateur dans la Bibliothèque de sources, recherchant toutes les sources autorisées du projet selon cette modalité. Il ne change ni les annotations, ni les questions ou critères de l’essai conservé et ne valide pas rétroactivement les deux images ; la cause initiale V1R1 reste inconnue.

[Résultat réel et limites](../logs/foresight-runtime/CAD-V1R2-progress-ROOT-20261015-b53d0468cd4c4816a558029f07261d94.json).


EG2 reste le moteur mémoire de production. La configuration `memory` et les
routes `/v1/settings/embedding-channel` concernent le même profil texte et
`storage/eg2/index.db` ; ces diagnostics ne créent pas d'index alternatif pour
ce profil.

## Profil multimodal local séparé — 11 octobre 2026

Le Studio complète le profil texte par l'encodeur EG2 complet dans un runtime
LiteRT isolé. Son profil SHA exact et `storage/multimodal/index.db` sont distincts
du profil/index texte ; ils ne les remplacent pas et ne permettent pas de
mélanger arbitrairement leurs vecteurs. Texte, PNG/JPEG et fenêtres audio WAV
16 kHz sont des projections dérivées, sans nouveau référentiel canonique.
Sources, Notes ERP et décisions restent l'autorité ; droits, version, empreinte
et localisateurs sont revérifiés au rappel. Le mode local de l'assistant peut
combiner SQL et cet index ; un repli SQL est annoncé, sans recherche complète
prétendue. Aucun OCR ou interprétation CAO n'est garanti par cet encodeur.
Profil, quotas, reprise et preuves : [moteur EG2](20_EG2_ENGINE.md) et
[livraison et limites](38_FORESIGHT_DELIVERY.md).

## Essais historiques du profil texte

Les essais antérieurs sont archivés hors du projet dans `C:/AgentBench`. La qualification sur six dossiers fictifs longs donnait 22/24 réponses satisfaisantes, dont 20 complètes, et six abstentions correctes pour six questions sans preuve. Deux limites observées : une question FAT/SAT ne retrouvait que le FAT ; une question de support retrouvait le mauvais contexte. Ces résultats ne garantissent pas la complétude sur tous les projets réels.

Le déploiement de production utilise un découpage adapté aux documents longs, le filtre de projet et la provenance canonique. Les chiffres d’indexation de laboratoire ne préjugent pas de la durée des 897 sources réelles. RAM/VRAM du serveur distant non mesurées. Voir [moteur EG2](20_EG2_ENGINE.md).

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
## Relais Kiara authentifié — 4 novembre 2026

Le canal EG2 accepte une clé Bearer. Lorsque les bases API LLM et embeddings
correspondent exactement (schéma, hôte, port, chemin ; suffixe `/v1` facultatif),
il réutilise la clé IA stockée avec DPAPI. Aucun secret n'entre dans le profil
vectoriel ni dans la représentation du canal. Une rotation de clé ne nécessite
donc pas de reconstruction. Aucun transfert de clé vers un autre serveur ni
suivi de redirection HTTP n'est autorisé par ce canal.

Paramètres Kiara : serveur `http://127.0.0.1:17841`, modèle LLM `fred-qwen`,
embeddings `google/embeddinggemma-2`, 768 dimensions, lots de huit au maximum.
Les diagnostics `/v1/settings/embedding-channel/test`, le test mémoire et le
témoin de connexion utilisent cette authentification. Le relais local doit
rester ouvert ; le calcul est effectué sur le serveur Kiara.

La migration doit attendre un calcul réel réussi : un HTTP 503 signifie que
l'encodeur est indisponible ou occupé. Le serveur et le nom de modèle font
partie du profil technique EG2, mais changer d'accès ne change pas forcément
l'espace vectoriel. Vérifier la compatibilité avant de décider une reconstruction.

Le 4 novembre, 263 passages identiques de 11 sources ont été calculés via Kiara
et comparés aux vecteurs existants : cosinus minimal 0,999354, médian 0,999828,
écart maximal par composante 0,004738. Les vecteurs sont très proches mais ne
sont pas numériquement identiques ; la cause précise de cet écart n'est pas
établie. Ce contrôle échantillonné justifie ici la réutilisation, sans promettre
une identité de classement pour toute requête.

Les 20 322 vecteurs de 1 070 sources ont été conservés à l'identique dans
`storage/eg2/kiara-compatible-20261104/index.db` : seule l'identité du profil
et ses références ont été adaptées après vérification de chaque empreinte
canonique. Les références des 1 070 projections ont été alignées. Les tables
projets, sources, artefacts, connaissances, propositions, décisions humaines et
provenances sont identiques avant/après. Base sauvegardée ; index original
`storage/eg2/index.db` conservé. Preuve :
`logs/kiara-config-20261104-100510/reuse-result.json`.

La reconstruction complète initialement commencée a été arrêtée ; son index
partiel `storage/eg2/kiara-20261104/index.db` n'est pas actif. Pour un futur
changement d'encodeur incompatible, reconstruire depuis le canon après sauvegarde.
Le relais renvoie HTTP 429 lorsque EG2 est déjà occupé. Le canal reprend alors
le même lot jusqu'à cinq tentatives, en respectant un `Retry-After` numérique
borné entre 0,25 et 5 secondes (2 secondes par défaut). Le modèle reste identique ;
si le relais demeure occupé, l'échec est explicite. Éviter les reconstructions
concurrentes.

Validation du raccordement : 82 tests Python ciblés réussis et Ruff conforme,
dont une recherche HTTP authentifiée sur index privé dont les octets restent
identiques. La recherche unifiée transmet aussi les réglages IA au canal.
La suite globale exploratoire a été interrompue après plusieurs échecs ; aucune
qualification globale n'est annoncée. Le test LLM réel depuis Agent répond OK ;
un vrai vecteur Kiara de 768 dimensions a été reçu. Les contrôles locaux de profil
reconnaissent l'index réutilisé. Le premier essai de recherche pendant la reprise
automatique des documents en attente utilisait le secours lexical ; le chemin
spécifique de transmission de clé a ensuite été corrigé et testé. Après la fin
d'un lot automatique, le contrôle HTTP réel de recherche sur Agent 8001 renvoie
`semantic_status=ok`, trois résultats demandés et 1 079 sources indexées ; neuf
sources avec texte restent à indexer. Ce résultat valide le raccordement et
l'utilisation de l'index conservé, sans promettre la pertinence de toute requête.
Preuve : `logs/kiara-config-20261104-100510/search-final.json`.

## Pièces jointes — reprise du 4 novembre 2026

Les preuves extraites des pièces jointes rejoignent les passages du mail
dans son seul projet. `attachment_status` est exclu du texte et de son
empreinte : un format non pris en charge ne rend pas le corps déjà indexé
périmé. Les passages inchangés sont réutilisés par Source et profil.
`embedding_cache` conserve chaque lot réussi par profil/empreinte du texte,
sans texte ni affectation de projet ; seules les lignes `passages`, toujours
vérifiées contre le canon, participent aux résultats. Le remplacement des
passages de la Source attend le calcul de tous ses nouveaux vecteurs.

La reprise utilise `batch_size=8`, après un test entièrement synthétique
de huit passages/9 072 caractères en 5,33 s sur le relais configuré. Cette
mesure ne garantit pas la durée d’un document réel. Le modèle, le serveur
et le profil restent les mêmes ; revenir à deux en cas de coupures du relais.
Voir [les états et limites d’extraction](04_INGESTION_PIPELINES.md).
