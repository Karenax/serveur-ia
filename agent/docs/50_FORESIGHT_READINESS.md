# Préparation : disponibilité distincte des moteurs

Livraison du 16 octobre 2026 sur Agent `8001`. Complément L11a, sans clôture de L11
ou de L12.

Dans **Réglages → Autres réglages → Réunions et transcription**, le diagnostic
sépare capture, transcription des fichiers/direct, encodeur local et génération.
Il affiche la mémoire et le disque disponibles sans ajouter un seuil de RAM
bloquant. Les choix de préparation et les résultats précédents ne sont pas
effacés quand un contrôle échoue.

## Actions explicites

- **Vérifier les modèles** consulte l’inventaire du moteur de génération
  sélectionné. Aucun microphone, génération, téléchargement ou commande de
  chargement/déchargement n’est lancé par cette action.
- **Tester une réponse** envoie seulement `Réponds uniquement OK.` au moteur
  sélectionné. Aucun document, note ou contenu métier n’est transmis. Le serveur
  peut charger à la demande ce modèle pour répondre ; l’interface l’indique.
  Un échec du serveur réseau ne déclenche pas le secours dans ce test ciblé.
- Consulter ou actualiser le diagnostic ne lance aucune de ces deux actions.

Une réponse non vide prouve une génération réelle pour cette configuration,
pas sa qualité métier. Un inventaire reçu ne prouve pas une réponse. Installation
et chargement restent inconnus quand le serveur expose uniquement la liste
OpenAI `/v1/models`. Les contrôles sont datés : ils décrivent la dernière
observation, pas une disponibilité garantie en permanence.

Pour LM Studio, l’inventaire `/api/v1/models` distingue le modèle installé de ses
`loaded_instances`, y compris les identifiants d’instance personnalisés. Pour
Ollama, `/api/tags` et `/api/ps` distinguent les modèles présents et en mémoire.
Références : [LM Studio](https://lmstudio.ai/docs/developer/rest/list),
[modèles Ollama](https://docs.ollama.com/api/tags),
[modèles en mémoire Ollama](https://docs.ollama.com/api/ps).

## Persistance et contrôle d’accès

Les trois routes globales sont réservées au propriétaire sans restriction de
projet, comme les autres réglages de moteurs :

```text
GET  /api/v1/workspace/fusion-settings/readiness
POST /api/v1/workspace/fusion-settings/readiness/probe
POST /api/v1/workspace/fusion-settings/readiness/generation-test
```

Les tentatives sont conservées sous `storage/runtime/readiness/`, avec un fichier
immuable par résultat et un pointeur atomique vers le dernier. L’identité est
liée au fournisseur, à l’adresse, au modèle et à l’identité du secret utilisé ;
le secret n’est ni stocké dans ces résultats ni exposé par le diagnostic. Un
changement de modèle ou d’identifiants ne récupère pas la preuve du précédent.
Un changement de délai, d’activation du secours ou de préparation ne force pas
à retester le même moteur. Les résultats anciens restent conservés.

Si les réglages changent pendant un contrôle, son résultat reste associé à
l’ancienne identité et la réponse HTTP relit la configuration actuelle. Un
échec d’inventaire ne détruit pas la preuve d’une réponse antérieure. Le test
désactive le repli uniquement pour sa propre requête ; la configuration et le
fonctionnement ordinaire du secours sont conservés. La règle de déchargement
du modèle LM Studio au retour du serveur principal reste inchangée.

Le diagnostic ne constitue pas une qualification hors ligne. La chaîne complète
actuelle doit encore être vérifiée avec Internet et LAN réellement coupés. Les
mesures et les preuves historiques restent distinctes.

## Vérifications et état observé

Validation :18contrôles backend diagnostic/statistiques, puis un cas ciblé
d’identifiant personnalisé LM Studio, soit19cas distincts. Les37contrôles
frontend couvrent préparation, diagnostic et interfaces conservées ; les5cas du
diagnostic sont rejoués après les derniers libellés et ne sont pas ajoutés une
seconde fois au total. TypeScript, Vite et Ruff passent. Les suites globales ne
sont pas présentées comme rejouées.

Les trois routes sont actives dans le backend supervisé. Les sauvegardes SQL
récentes sont vérifiées et réutilisées après comparaison exacte des données non
volatiles ; les tables protégées restent inchangées après redémarrage. Les
anciens actifs frontend sont sauvegardés et conservés, les nouveaux fichiers
servis sont comparés par SHA-256.

Contrôle réel dans un onglet séparé de l’interface : lecture, clic d’inventaire,
indicateur en cours, puis clic du test de réponse. Le serveur réseau configuré
ne répond pas à cet instant : inventaire et génération signalent `URLError` ;
la tentative de réponse dure21,08s. Les boutons redeviennent disponibles et les
états capture/recherche restent conservés. Aucune réussite réseau n’est inventée
à partir des tests simulés. Le contrôle local en lecture seule constate une
instance de secours chargée après l’essai ; son origine n’est pas attribuée à
ce test, dont le code interdit le repli.

La transcription complète des fichiers est disponible. Le direct est installé
mais sa preuve runtime n’est pas reconnue ; ce diagnostic constitue un point à
traiter séparément avant sa qualification. Aucun microphone n’a été ouvert.
Aucun réglage de préparation n’a été sauvegardé par la recette UI et l’onglet
Réunions initial de l’utilisateur n’a pas été rechargé.

Preuves : `.ui-preview/l11-readiness-20261016/`, audit
`logs/foresight-runtime/L11-readiness-delivery-ROOT-20261016.json`.

![Diagnostic actuel dans Agent](../.ui-preview/l11-readiness-20261016/diagnostic-actuel.jpg)


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
