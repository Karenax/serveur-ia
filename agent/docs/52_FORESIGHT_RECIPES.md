# Recettes Foresight : consolidation du 16 octobre 2026

Neuf lots sont clos : L00, L01, L04, L05, L06, L07, L08, L09 et L10.
L02, L03, L11 et L12 restent ouverts. Cette consolidation ferme sept recettes dans son premier bilan
logicielles en utilisant leurs pièces brutes déjà réussies, après contrôle de
leurs empreintes et du code concerné. Elle ne répète aucun modèle, aucune heure
de capture ni aucun essai matériel.

| Recette close | Résultat démontré |
|---|---|
| T05 | Saisie riche/Markdown conservée pendant une génération ; correction versionnée, ancien résultat obsolète |
| T06 | Note ERP sauvée pendant panne Brain/EG2, événement durable, reprise sans doublon |
| T07 | Notes identiques dans deux projets séparées, droits et staging contrôlés |
| T09 | Rejeu après commit ERP : un CR, actions et provenance uniques pour audio et notes seules |
| T10 | Réimport identique/changé versionné ; copie URL encore lisible après désactivation du fetch dans la fixture |
| T14 | Ancien parcours Notes utilisable après désactivation ; nouvelles écritures et récupération conservées |
| T17 | Notes seules sans audio inventé ; capture non attribuée puis rattachement/finalisation rejoués sans doublon |

La recette T14 est fraîche : vrais handlers HTTP, sauvegarde SQLite puis édition
de la note, export ZIP et restauration dans un dossier neuf. La production n’est
pas utilisée. La source conserve sa révision2 et son texte350lux ; la copie
restaurée contient la révision1 et1250W. L’audio fictif est identique par SHA256,
la capture restaurée est interrompue et les automatismes sont désactivés.
Les premiers échecs du harnais (URI SQLite et forme de réponse HTTP mal prises
en compte) sont conservés ; ils ne sont pas comptés comme réussites.

Frontend actuel : **960 tests dans94fichiers réussis**, TypeScript réussi et Vite
réussi. Les246fichiers sources/configuration épinglés sont inchangés. Le premier
contrôleur a échoué à afficher le symbole Unicode de Vite ; les tests et
TypeScript étaient déjà terminés avec code0. Seule la compilation a été reprise.
Les trois assets compilés correspondent aux fichiers et octets HTTP d’Agent8001.
Aucun nouvel asset n’a besoin d’être publié. Ruff app/backend/tests réussit.

Le passage global backend sur457sources est **en cours**, une seule exécution
avec bases et répertoire temporaire privés. Aucun succès global frais n’est
annoncé avant sa sortie réelle. La référence précédente2580réussis/1ignoré reste
historique. Aucun contrôle RAM forfaitaire ou temporisateur d’observation ne
transforme l’attente de cette exécution en échec ou en demande de relance.

T01/T02/T03/T04 dépendent encore de la recette matérielle regroupée déjà demandée.
T08 et T13 ont été complétés ci-dessous. T11 dépend encore de la qualification
de la chaîne hors ligne actuelle, T12 de ses mesures, et T15 du contrôle
global courant, et T16 du volume réellement plein dans un environnement adapté.
Ces recettes ne sont pas déclarées closes par cette livraison.

Le direct medium CPU reste disponible en essai : les six valeurs des trois phrases
propres sont correctes, mais cela ne qualifie pas le corpus industriel complet
ni la latence visible. Le parcours audio complet vers CR avec relecture est déjà
actif. Drive reste exclu et l’adaptation Agent aux écrans publics est acceptée.

Pièces : `.ui-preview/recipes-current-20261016/software-recipes.json`,
`v/return-44fa53f1e73f/result.json`,
`.ui-preview/integration-current-20261016/frontend-91a93dbc7ed544b688c8c497973fffe0/terminal.json`.
La matrice courante est `docs/40_FORESIGHT_ACCEPTANCE.md` ; ses index antérieurs
sont conservés. Cette étape ne clôture pas L12 et ne produit aucun commit/push.

### Citations, arrêt mobile et fraîcheur des réponses — 16 octobre 2026

T08 et T13 sont maintenant clos dans la portée documentée. T08 utilise de vrais
handlers et fichiers fictifs, avec une réponse textuelle simulée : note historique
v1 consultable après écriture v2, audio fictif à1s avec segment1–4s/révision2,
PDF versionné à la page physique2 (repère imprimé7), feuille Banc electrique et
cellulesA2:C2, PNG entière avec légende manuelle de fixture. Les trois originaux
observés dans l’inspecteur sont récupérés par HTTP et vérifiés par SHA256 ;
l’ancien PDF est également intact. Aucune reconnaissance ou qualité ASR n’est
déduite de cette recette de citations.

T13 complète les dispositions et la navigation L06 par le vrai navigateur :
Tab/Entrée sur Arrêter et conserver à670px clair/enregistrement et320px
sombre/pause, après passage à Sources. Le bouton entier reste dans le viewport,
avec focus visible et sans débordement horizontal de page ; les deux POST STOP
simulés retournent200 et la barre disparaît. Les DTO et l’arrêt sont simulés,
aucun microphone/processus de capture physique n’est utilisé. La référence
publique et l’adaptation acceptée restent la portée ; aucune parité privée ou
conformité générale d’accessibilité n’est revendiquée.

La même recette a révélé un défaut T05 : une ancienne réponse ne portait pas
spontanément son avertissement après une modification externe de note. Le Studio
relit maintenant l’historique toutes les3s lorsqu’une discussion non vide est
visible, avec une seule lecture en vol. Cette lecture silencieuse ne relance
aucune IA. Le serveur décide de la fraîcheur et des droits ; les brouillons
restent intacts. Une réponse devenue inaccessible est retirée de l’affichage,
sans suppression de son historique serveur. L’erreur de lecture reste visible
avec possibilité de reprise. Les requêtes anciennes sont invalidées après une
nouvelle réponse ou un changement de contexte.

Trois cas reproduisaient le défaut ;96contrôles du Studio passent après correction,
ainsi que18contrôles du client. Les trois nouveaux cas passent à nouveau après
correction de deux options de types dans les tests ; ces cohortes se recouvrent.
TypeScript et Vite réussissent. Le premier contrôle TypeScript en échec est
conservé ; sa commande avait tout de même poursuivi Vite et n’est pas présentée
comme une chaîne entièrement verte. La vérification TypeScript distincte finale
termine avec code0. Les assets sont sauvegardés puis publiés sur8001 et comparés
aux octets HTTP, sans redémarrage backend.

Le navigateur confirme le correctif : une réponse sur la notev2 devient ancienne
après l’écriture v3, sans effacer la question encore en saisie ni produire une
quatrième réponse simulée. Les deux serveurs privés se ferment normalement
(codes0), les onglets temporaires sont fermés et le viewport est restauré.

Neuf recettes sont closes : T05/T06/T07/T08/T09/T10/T13/T14/T17. Neuf lots restent
clos ; L02/L03/L11/L12 restent ouverts. Le global frontend960 demeure la référence
antérieure au correctif, complétée par le ciblé96/18 et le retest3 ; aucun nouveau
global963 n’est annoncé. Le global backend actuel poursuit son unique passage.


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


Complément de recette Realtek audible préparé : lecture de trois phrases
fictives pour contrôler la piste système, sans modèle, écoute des captures
ou transmission. Prévol réel : playback403, quatre refus start/resume, aucun
accès audio et fermeture normale ; douze tests de garde passent. Aucun ancien
accord audio réutilisé. Jabra toujours absent, L12 reste ouvert. Preuve :
`logs/foresight-runtime/REALTEK-AUDIBLE-PREP-ROOT-20261021.json`.


### T16 — support isolé indisponible

Réponse utilisateur du 21 octobre : aucune clé USB vide disponible. Le poste n’a pas les droits administrateur nécessaires au VHD préparé. Aucun volume hôte n’est saturé ; T16 reste ouvert pour le disque plein physique. Les preuves SQLite FULL et les simulations ENOSPC restent distinctes de cette qualification.


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
