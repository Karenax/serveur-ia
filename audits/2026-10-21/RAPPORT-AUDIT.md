# Audit approfondi du projet Serveur IA / Fred

Date : **21 octobre 2026**, fuseau Europe/Paris. Référence Git : `749b6adcb068382d1d3255c548d05567b5d41efe`, branche `main`, **avec les modifications locales déjà présentes** lors de l’audit.

Ce rapport décrit l’état initial audité. Les corrections autorisées ensuite, leur mise en service et leurs validations figurent dans le [rapport des corrections du 21 octobre](../../maintenance/2026-10-21-correctifs-audit/RAPPORT-CORRECTIONS.md). Le constat A09 ci-dessous a été rectifié après vérification avec l’analyseur Python.

## Avis général

Le projet dispose de protections sérieuses pour un serveur personnel : séparation des données par propriétaire, révocation persistante des accès, sauvegardes chiffrées vérifiées, mises à jour signées, extraction documentaire isolée et tests d’intégration nombreux. Les corrections des précédents audits sont visibles dans le code actuel.

Les risques prioritaires concernent aujourd’hui **les permissions Windows du code et du registre d’accès**, **la maintenance de sécurité des dépendances** et **la concentration des sauvegardes sur le serveur**. Les tests fonctionnels réussis ne suffisent pas à couvrir ces risques. Aucun élément recueilli ne démontre une compromission ; cet audit ne constitue pas une recherche forensique de compromission.

| Priorité | Référence | Constat | Nature de la preuve |
| --- | --- | --- | --- |
| P1 | A01 | D’autres utilisateurs Windows peuvent modifier le lanceur et le registre d’accès | ACL effectives déclarées sur les chemins contrôlés |
| P1 | A02 | Magasins Certifi antérieurs au retrait de certificats emSign compromis | Versions installées, OSV et avis de l’éditeur |
| P2 | A03 | Bibliothèques de traitement et runtime Hermes concernés par des avis de sécurité | Versions identifiées ; exposition à qualifier par fonction |
| P2 | A04 | Aucune seconde destination de sauvegarde configurée | État de production lu pendant l’audit |
| P2 | A05 | Ressources Android générées désynchronisées des sources communes | Échec reproductible du contrôle officiel et diff de 27 lignes |
| P2 | A06 | Serveur HTTP EG2 sans plafond de threads ni délai avant lecture des en-têtes | Code actuel, comparaison avec la frontière HTTP commune |
| P2 | A07 | Reconstruction insuffisamment verrouillée et état déployé partiellement hors commit | Exigences, versions installées, manifestes et état Git |
| P3 | A08 | Documentation d’entrée contradictoire sur le moteur et les versions | README comparé au contexte et aux preuves de livraison |
| P3 | A09 | Alertes d’analyse statique sur deux scripts historiques ; syntaxe Python valide | Rectification lors des correctifs du 21 octobre |

P1 : traiter en premier, avec préparation et validation de compatibilité. P2 : correction planifiée nécessaire pour la sécurité, la continuité ou la reproductibilité. P3 : dette de maintenance. La priorité reflète le contexte du projet ; elle n’est pas une reprise automatique du score CVSS d’un composant.

## Périmètre et méthode

L’audit couvre l’organisation du dépôt, les sources actuelles serveur/Windows/Android/voix, la frontière HTTP, les accès, le stockage, les sauvegardes, les outils Hermes, le rendu web, les mises à jour, les scripts de construction et les références des moteurs. Il combine lecture de code, inventaire, analyse statique, tests existants, comparaison d’artefacts et consultations d’avis de sécurité publics.

L’inventaire Git comprend **3 254 fichiers suivis**, soit **50 647 593 octets, environ 48,3 Mio**. Dans les quatre composants applicatifs, l’inventaire retient **278 fichiers de code, interface et scripts, 33 680 lignes**, tests compris, hors ressources Android générées et bibliothèques JavaScript embarquées. Ces chiffres ne sont pas un comptage de tout le disque : moteurs externes, outils, poids, environnements, données privées et nouveaux dossiers non suivis sont distingués du dépôt.

Les sept modifications suivies déjà présentes au départ et les dossiers non suivis de la livraison Strata du 19 octobre ont été conservés. Les écritures de l’audit sont regroupées ici ; les tests peuvent produire des caches et rapports de compilation. Une capture suivie réécrite par les tests navigateur a été remise à son contenu Git initial, après vérification qu’elle n’était pas modifiée au départ. Aucune correction applicative, publication, modification des ACL, rotation de clé, restauration de production ou relance du modèle n’a été effectuée.

Les essais applicatifs utilisent les fixtures et dossiers temporaires des suites existantes. La production n’a été consultée qu’en lecture : santé, version, sauvegardes et ports. Les seuls renseignements envoyés à OSV sont les noms et versions de paquets ; aucun contenu privé ni secret n’y est envoyé.

Preuves principales : [inventaire.json](inventaire.json), [synthese.json](synthese.json), [production-lecture-seule.json](production-lecture-seule.json), [osv.json](osv.json), [dependances-installees.json](dependances-installees.json).

## Architecture et structure des fichiers

```text
D:\Serveur IA
├── lanceur/           Console, passerelle, droits, données, sauvegardes, Hermes
│   ├── app.py         Administration locale 127.0.0.1:8765
│   ├── remote.py      Passerelle authentifiée 127.0.0.1:8766
│   ├── workspace.py   Autorité SQLite, projets/documents/historiques/quotas
│   ├── hermes_*.py    Profils, tours, modèles, outils, conservation
│   ├── backups.py    Sauvegarde chiffrée, calendrier, conservation
│   ├── restoration.py Restauration et retour après échec
│   └── web/           Interface d’administration
├── client-qwen/       Client Windows, HTTP local, interface commune, updater
├── client-android/    Client natif Java et WebView, ressources générées
├── client-voice/      ASR/AEC et conversation, composants Python/C++
├── dependances/       Références/patchs et moteurs téléchargés séparément
├── maintenance/       Interventions datées et preuves de mise en service
├── audits/            Rapports et vérifications
├── preuves/           Validations et captures de livraison
├── recherche/         Expériences et instantanés historiques
├── comparatifs/       Protocoles et résultats de performances
├── Strata-src/        Runtime Python local, hors Git principal
├── toolchain/         SDK, compilateurs, modèles auxiliaires, hors Git
└── scripts racine     Lancement, arrêt, construction et anciens essais
```

| Ensemble suivi | Fichiers | Volume approximatif |
| --- | ---: | ---: |
| Racine | 203 | 2,68 Mio |
| `lanceur` | 182 | 1,67 Mio |
| `client-qwen` | 124 | 1,38 Mio |
| `client-android` | 114 | 4,29 Mio |
| `client-voice` | 31 | 84 Kio |
| `recherche` | 1 322 | 10,63 Mio |
| `comparatifs` | 705 | 12,56 Mio |
| `preuves` | 303 | 10,59 Mio |
| `maintenance` | 140 | 1,33 Mio |
| Autres | 130 | 3,08 Mio |

La séparation par produit et la traçabilité des interventions sont utiles. En revanche, le même espace physique contient sources, exploitation, SDK et archives. Les 203 fichiers suivis de la racine et les scripts historiques rendent la distinction « commande actuelle / ancien essai » moins évidente. Le volume Git reste raisonnable ; une suppression massive d’archives n’est pas justifiée.

Organisation recommandée, progressivement : `apps/` pour les quatre produits, `scripts/` pour les commandes actuelles, `experiments/` pour les essais, et surtout un **répertoire de déploiement privé distinct du checkout de développement**. Prévoir un adaptateur de chemins et les tests avant de déplacer les fichiers : beaucoup de scripts utilisent encore les chemins actuels.

Les interfaces s’enchaînent ainsi : Windows/Android ou API tierce → HTTPS/WireGuard → passerelle Fred → contrôle propriétaire/modèle/tour → Hermes ou Qwen direct → moteur local. La voix Windows et le correcteur contournent volontairement Hermes pour utiliser Qwen directement. SQLite constitue l’autorité ; les dossiers clients sont des copies exportées, pas une seconde autorité d’écriture.

## Résultats des vérifications

| Vérification effectuée | Résultat |
| --- | --- |
| Tests Python serveur | **475 réussis**, en 822,361 s |
| Tests Python client Windows | **19 réussis** |
| Tests Python voix | **20 réussis** |
| Tests Python outils Android | **13 réussis** |
| Suites navigateur de `npm test` | **5 réussies** |
| Syntaxe des sources actuelles et scripts retenus par `check_sources.py` | **203 Python, 61 JavaScript/scripts HTML, 90 PowerShell**, sans erreur |
| Compatibilité syntaxique PowerShell | **90 fichiers**, sous PowerShell 7 et Windows PowerShell 5.1 |
| Ruff, règles F, 81 fichiers Python applicatifs/utilitaires actuels | **Aucun signalement** |
| Bandit, mêmes 81 fichiers | **138 signalements bruts : 92 faibles, 46 moyens, 0 élevé** |
| Cohérence des paquets installés | `pip check` réussi dans les **4 environnements Fred** ; indisponible dans le runtime Hermes sans pip |
| Dépendances et avis OSV | **230 couples paquet/version**, 5 environnements, **0 erreur de consultation** |
| Android `lintDebug`, Gradle hors ligne | **Réussi : 0 erreur, 5 avertissements** |
| Android `Prepare-Assets.py --check` | **Échec : ressources périmées**, A05 |
| Livraison Windows locale | Manifeste vérifié, **3.5.30** |
| Livraison Android locale | Empreinte vérifiée, **1.0.11 / code 12**, APK de 18 903 316 octets |
| Moteur Strata | Empreinte de l’exécutable conforme à la preuve du 19 octobre |
| Recherche de formes courantes de secrets dans les textes suivis | **Aucun candidat**, limites précisées plus bas |

Le nombre brut de signalements statiques ne constitue pas un nombre de vulnérabilités. Les 31 alertes Bandit B608 concernent les constructions SQL ; les chemins examinés utilisent des noms contrôlés et des paramètres liés pour les valeurs. Les alertes YAML portent notamment sur `UniqueLoader`, qui dérive de `yaml.SafeLoader`. Les `exec` de l’intégration chargent des adaptations locales déterministes. Ces choix restent sensibles à la maintenance, mais ne démontrent pas une injection exploitable.

Au total, **527 tests Python et 5 suites d’interface réussissent**. Le contrôle de production final retrouve les mêmes processus sur les cinq ports contrôlés, le modèle chargé et les images disponibles : [production-fin.json](production-fin.json).

Les avertissements Android portent sur un attribut lié à l’API 33, JavaScript dans la WebView, un dossier de ressources redondant, l’API d’estimation d’espace libre et l’icône monochrome absente. L’alerte JavaScript appelle une revue des frontières, réalisée ici ; elle ne prouve pas une XSS. La WebView refuse les ressources distantes, l’accès aux fichiers et le contenu mixte ; l’interface utilise une CSP avec nonce.

Journaux : `tests-serveur.txt`, `tests-windows.txt`, `tests-voix.txt`, `tests-android.txt`, `tests-ui.txt`, `syntaxe.txt`, `android-lint.txt`, `ruff-applications.json`, `bandit-applications.json`. Les résultats étendus `ruff.json` et `bandit.json` incluent aussi des archives ; ne pas les confondre avec le périmètre applicatif actuel.

## Constats détaillés

### A01 — P1 : droits Windows trop larges sur le lanceur et le registre d’accès

**Confirmé.** Les ACL de `lanceur`, `lanceur/app.py` et `lanceur/acces-distants.json` accordent **Modify** au groupe `AUTORITE NT\Utilisateurs authentifiés`, et lecture/exécution à `BUILTIN\Utilisateurs`.

Un autre utilisateur authentifié du poste peut donc altérer le code exécuté au prochain démarrage ou modifier le registre d’accès. Dans [remote.py](../../lanceur/remote.py), l’authentification de la passerelle repose sur le SHA-256 du jeton enregistré pour le client ; la couche de comptes/mots de passe ancienne n’est pas requise sur ce chemin. Pour un accès actif, modifier ce hash peut substituer un jeton choisi par l’attaquant. Le registre de révocation protège les accès révoqués, mais n’authentifie pas l’intégrité de toute la configuration des accès actifs.

Les dossiers `wireguard-prive`, `espaces-prives`, `clients`, `hermes-fred`, `sauvegardes`, `donnees-clients` et `toolchain/android-signing` ont des ACL plus restrictives, limitées au propriétaire, à SYSTEM et aux administrateurs. Cette protection est positive, mais un code applicatif modifiable peut ensuite s’exécuter sous l’identité du propriétaire et accéder à ses secrets DPAPI.

La console sur loopback et ses jetons anti-CSRF protègent contre des pages web étrangères ; ils n’isolent pas les utilisateurs Windows entre eux. Des lectures administratives de la console, dont le téléchargement d’EXE personnels, reposent aussi sur la confiance dans le poste local. Le modèle annonce `api_key=false` sur loopback. Ces comportements renforcent la nécessité d’un périmètre d’exploitation privé.

**Condition d’exploitation :** présence d’un autre compte ou processus exécuté sous une identité locale non fiable ; aucune exploitation distante anonyme n’est démontrée. Aucun autre compte n’a été utilisé et aucun fichier de production n’a été modifié pour tester ce scénario.

**Correction :** installer code et configuration active dans un répertoire dont l’écriture est réservée au compte de service/propriétaire, à SYSTEM et aux administrateurs ; séparer développement et exploitation. Vérifier aussi les permissions des parents et les droits de suppression/remplacement. Si plusieurs comptes locaux non fiables doivent cohabiter, protéger également l’administration par une authentification liée au compte ou un transport local à ACL : un token rendu dans une page loopback accessible à tous ne réalise pas cette séparation. Inventorier les dépendances avant tout changement récursif des ACL. Valider avec un compte standard distinct : impossibilité d’écrire le code ou le registre et d’administrer Fred, puis fonctionnement normal des mises à jour et sauvegardes.

Preuves : [acl.json](acl.json), [acl-detail.json](acl-detail.json).

### A02 — P1 : mettre à jour les magasins Certifi après l’incident emSign

**Versions concernées confirmées.** Certifi `2026.7.22` est installé dans Strata, EG2 et le serveur vocal ; Hermes utilise `2026.5.20`. L’avis de l’éditeur publié le **20 octobre 2026** signale le retrait de racines emSign associées à des intermédiaires dont les clés ont été compromises. Une chaîne acceptée à tort peut permettre une interception TLS si les autres conditions d’attaque réseau sont réunies. [Avis primaire Certifi](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2).

Il existe un écart de version dans les métadonnées publiques : l’avis primaire cite `2026.10.18`, tandis que la plage OSV retient `2026.10.19` comme correctif. **Cible conservatrice : Certifi au moins `2026.10.19`, après validation avec le runtime concerné.**

**Portée :** les clients Python utilisant Certifi, notamment dans les adaptateurs réseau Hermes, sont à examiner. Les connexions HTTPS du client Windows basées sur `urllib` utilisent par défaut le magasin du contexte SSL ; la présence de Certifi dans son environnement de construction ne prouve pas qu’il est utilisé dans cette connexion. Les workers EG2 et voix hors ligne présentent une exposition réseau plus faible. Aucune interception n’a été tentée.

**Correction :** préparer une mise à jour contrôlée des runtimes concernés, vérifier les appels aux fournisseurs, la recherche web et l’authentification, puis publier les artefacts qui embarquent effectivement le paquet. Mettre à jour uniquement le venv de construction ne corrige pas un EXE déjà distribué.

### A03 — P2 : dépendances vulnérables, avec exposition différente selon les fonctions

Le croisement des versions installées avec OSV retourne des avis pour **11 noms de paquets, 12 couples paquet/version**. Les alias GHSA/PYSEC/CVE ont été regroupés dans `synthese.json`. Il faut encore distinguer « version dans une plage affectée » et « fonction exploitable dans Fred ».

| Paquet installé | Environnements | Avis distincts par version | Correctif/cible issu des avis | Évaluation dans ce projet |
| --- | --- | ---: | --- | --- |
| Certifi, deux versions | Strata, EG2, voix serveur, Hermes | 1 pour chaque version | ≥ 2026.10.19, cible conservatrice | A02, prioritaire pour les clients TLS concernés |
| pypdf 6.10.0 | Strata / lanceur | 31 | 6.19.0 couvre les correctifs recensés | Extraction de PDF effectivement utilisée ; priorité de traitement |
| Pillow 12.3.0 | Strata, EG2, Hermes | 9 | 13.0.0 | Décodage d’images utilisé côté Strata ; atteignabilité de chaque fonction à vérifier |
| PyJWT 2.13.0 | Hermes | 14 | 2.15.0 pour l’ensemble recensé | Fonctions JWT/JWK spécifiques ; aucun contournement de Fred démontré |
| aiohttp 3.14.3 | Hermes | 8 | 3.14.4 | Client/serveur et cookies selon l’avis ; qualifier les chemins natifs |
| mcp 2.0.0 | Hermes | 1 | 2.2.0 pour la branche 2.x | Accumulation de sessions StreamableHTTP ; Fred expose son propre handler MCP |
| multidict 6.7.1 | Hermes | 1 | 6.9.1 | Fuite de références pour certaines opérations de vues |
| oauthlib 3.3.1 | Hermes | 2 | 4.0.0 | Certaines fonctions d’un serveur OAuth ; pas de serveur OAuth Fred identifié |
| urllib3 2.7.0 | Hermes | 3 | 2.8.0 | Proxy HTTPS, décompression et transport ; selon usage |
| pip 25.0.1 | EG2, voix serveur, conversation Windows | 6 | 26.2 / 26.2.0 pour l’ensemble recensé | Risque d’installation/extraction, pas du chat courant |
| hermes-agent 0.0.0 | Hermes | 10 candidats | **Ne pas conclure depuis ce numéro** | Version de développement ; vérifier le commit réel |

Pour `pypdf`, l’avis **CVE-2026-102995 / GHSA-fp3h-c4fm-7vvf** concerne la consommation mémoire pendant l’extraction des correspondances de police `/ToUnicode`, corrigée dans 6.18.1. Le chemin `workspace.extract()` appelle bien `page.extract_text()`. [Avis primaire pypdf](https://github.com/py-pdf/pypdf/security/advisories/GHSA-fp3h-c4fm-7vvf).

Fred atténue ce risque par un sous-processus d’extraction limité à **25 secondes**, surveillé à **384 Mio de RSS**, avec bornes sur les entrées et le texte. La surveillance périodique n’est pas une limite mémoire imposée par le noyau : une allocation peut dépasser le seuil avant l’arrêt. Plusieurs avis concernent des fonctions différentes, par exemple le mode incrémental ou les labels de pages ; ils ne sont pas tous atteints par l’extraction actuelle. Aucun PDF offensif n’a été exécuté sur la production.

Pour Pillow, l’avis de dépassement de tampon JPEG **GHSA-8g5g-8vmr-9782** exige notamment une réduction via `draft()`/`thumbnail()`. Le code Strata examiné utilise `Image.open`, `load` et `ImageOps.exif_transpose`, sans ce redimensionnement dans le chemin observé. La version affectée est présente, mais **cet exploit précis n’est pas démontré sur ce chemin**. D’autres formats/fonctions restent à analyser. Les clients Fred n’acceptent que des images PNG/JPEG/WebP intégrées et bornées ; ce filtre réduit la surface, sans remplacer les correctifs du décodeur. [Avis primaire Pillow](https://github.com/python-pillow/Pillow/security/advisories/GHSA-8g5g-8vmr-9782).

Hermes est installé au commit **`79651b71bd56efd76d06f3de1df64dde09b58ff3`**. Sa métadonnée Python `0.0.0` provoque des rapprochements automatiques avec des plages anciennes ; ces dix résultats ne sont pas dix vulnérabilités confirmées de ce commit. Le runtime ne contient pas pip : son échec de `pip check` signifie « outil absent », pas « dépendances incohérentes ». L’inventaire a utilisé `importlib.metadata` sans installer d’outil.

**Correction :** préparer des environnements de remplacement, appliquer les correctifs par familles compatibles, relancer les tests et conserver le retour arrière. Ne pas mettre à niveau arbitrairement les dépendances internes du runtime Hermes géré : privilégier sa génération de dépendances compatible et vérifier le commit. Les cibles du tableau ne promettent pas une compatibilité avec les contraintes actuelles ni l’absence d’autres avis futurs.

### A04 — P2 : les sauvegardes restent dans le même domaine de panne

**Confirmé en production.** Sauvegardes activées à 03 h ; dernière réussite observée le **21 octobre à 08:48:14**, archive d’environ **2,63 Mio**, vérifiée par l’application, sans erreur. Le catalogue contient 28 entrées. La seconde destination est vide et les entrées récentes portent `secondary.status=disabled`.

Les archives résident dans `D:\Serveur IA\lanceur\sauvegardes`. Elles couvrent les erreurs applicatives, mais une panne du disque, une destruction du poste ou un chiffrement malveillant sous le compte propriétaire peut toucher données et sauvegardes ensemble. Chiffrement et conservation ne remplacent pas une copie indépendante.

**Correction :** configurer une copie chiffrée sur un support ou hôte distinct, avec droits et conservation séparés, et une copie hors ligne ou immuable adaptée au besoin. Effectuer un exercice de restauration sur un environnement isolé, vérifier conversations, documents, accès et signatures, puis mesurer la durée de reprise. Conserver séparément la phrase de récupération et les clés de signature Android, explicitement exclues de l’archive courante. Ne pas activer une destination fictive sans destination réellement disponible.

La réussite à 08:48 plutôt qu’à 03 h n’est pas classée comme panne du calendrier : un rattrapage après indisponibilité du serveur est possible et prévu. L’historique de disponibilité du poste n’a pas été reconstruit.

### A05 — P2 : le contrôle de fraîcheur Android échoue

**Reproduit.** La commande documentée `Prepare-Assets.py --check` sort avec le code 1 et le message `Android assets are missing or stale`. L’HTML embarqué porte l’empreinte `5c8b9c2b…`, tandis que la génération actuelle produit `f29987ff…`. Le manifeste des ressources ne correspond plus à `chat.html` et `ui.js`.

Le diff de 27 lignes porte sur les hooks de conversation vocale introduits dans le chat commun : collecte de `conversationRequest`, ajout des champs de requête, transmission du texte non-SSE et condition de récupération Hermes. Android ne livre actuellement que la dictée manuelle ; **ce décalage ne démontre donc pas une panne du chat Android publié**. Il rend néanmoins le contrôle de reconstruction incohérent et empêche de garantir que les sources et le paquet généré représentent le même état.

Le script `Build-Android.ps1` régénère les ressources avant de construire et les revérifie : la protection de build existe. La dette se situe dans la fraîcheur des ressources suivies et la gestion des changements de l’interface commune.

**Correction :** décider si ces hooks facultatifs doivent être générés tels quels pour Android ou neutralisés explicitement dans la transformation, régénérer, vérifier le diff, relancer les suites communes et les tests Android, puis mettre à jour le manifeste. Ne pas republier un APK uniquement pour cet écart sans comportement corrigé et validation.

Preuves : [android-assets.json](android-assets.json), [android-assets.diff](android-assets.diff), [assets-android.txt](assets-android.txt).

### A06 — P2 : EG2 ne bénéficie pas encore de la frontière HTTP bornée commune

**Confirmé par le code.** Dans `embedding_worker.py`, le serveur utilise directement `ThreadingHTTPServer`. Le timeout de 15 secondes est posé dans `do_POST`, **après** l’analyse des en-têtes et l’authentification. Le verrou `guard` limite les calculs simultanés, mais pas les connexions ni les threads créés avant cette étape.

Un processus local qui ouvre des connexions incomplètes peut immobiliser des threads sans détenir le jeton EG2. Le watchdog mémoire à 4 Gio peut finalement arrêter le worker ; il ne garantit pas la disponibilité de l’indexation. La console, le client Windows, la passerelle et le service privé Hermes disposent déjà du `BoundedHTTPServer` commun.

**Portée :** déni de service local ; aucune route publique directe vers le worker EG2 n’a été établie. Aucun test de saturation n’a été exécuté contre le worker de production.

**Correction :** appliquer un délai à l’acceptation de la socket et un plafond de workers avant la lecture des en-têtes, en réutilisant une frontière adaptée au déploiement du worker. Vérifier les requêtes incomplètes, le rejet à saturation et le retour au fonctionnement normal sans charger de modèle réel dans les tests de transport.

### A07 — P2 : le commit et les requirements ne suffisent pas à reconstruire l’état en service

Les dépendances directes sont épinglées, des manifestes de build existent, Go conserve ses sommes et Node possède un lockfile : ces points sont positifs. Il manque néanmoins un verrouillage complet et vérifié de l’ensemble déployé.

Exemples contrôlés : `cryptography==50.0.1` figure dans les requirements du lanceur/client, tandis que le runtime Strata installé contient **50.0.2**. `pip check` ne compare pas l’environnement à ces fichiers ; il peut donc réussir malgré ce décalage. Les manifests décrivent l’environnement de construction, pas nécessairement tous les modules réellement inclus dans le binaire. Le paquet Certifi, par exemple, ne doit pas être supposé embarqué sur la seule foi de l’inventaire du venv.

La production utilise le moteur **0.1.45.3** avec le serveur Python **0.1.43.1 corrigé** et l’encodeur P2200 spécifique. Son empreinte correspond à la preuve de déploiement. Mais les chemins de configuration modifiés, les références du nouveau paquet et les preuves du 19 octobre sont encore partiellement modifiés/non suivis dans le checkout initial. Restaurer uniquement `HEAD` ne reproduit donc pas cette production.

**Correction :** conserver une référence de livraison cohérente comprenant configuration non secrète, versions, empreintes des distributions et ordre des patchs ; intégrer les changements autorisés dans Git après revue. Produire des contraintes/locks des dépendances transitives par runtime, avec empreintes des paquets téléchargés lorsque le gestionnaire le permet. Comparer les environnements aux locks et inventorier les modules réellement empaquetés. Pour une livraison de sécurité, lier chaque binaire aux dépendances qu’il contient.

Le rapport ne demande pas de committer les secrets ou les paquets téléchargés. La procédure doit permettre de récupérer ces derniers depuis leurs références et de vérifier leurs empreintes.

### A08 — P3 : la documentation d’entrée indique encore un ancien état courant

`README.md` présente Strata **0.1.43.1** comme moteur actuel et parle de Windows/serveur **3.5.29**. `CONTEXTE-PROJET.md`, `RECONSTRUIRE-FRED.md` et les preuves de production indiquent le moteur **0.1.45.3**, avec le serveur Python 0.1.43.1 conservé, et la version **3.5.30**. La distinction moteur/serveur Python est essentielle : remplacer tout le dossier ancien supprimerait un composant encore utilisé.

**Correction :** une fiche d’état courant courte, datée, avec versions de chaque composant et lien vers la preuve de déploiement ; les interventions précédentes restent dans les archives. Relier le README à cette fiche et vérifier automatiquement les versions principales lors d’une livraison.

### A09 — P3 : alertes sur deux scripts d’archives — conclusion initiale rectifiée

**Erratum du 21 octobre, pendant l’application des correctifs :** les deux fichiers étaient acceptés par `ast.parse` de Python 3.12. L’affirmation initiale selon laquelle ils ne pouvaient pas s’exécuter était incorrecte. Ruff signalait l’affectation au mot-clé contextuel `match` placée après un point-virgule ; séparer les instructions sur deux lignes élimine son signalement sans changer le comportement Python.

L’analyse étendue avait signalé `invalid-syntax` dans :

- `preuves/conversation-windows-20261011/finalize.py:14` ;
- `recherche/strata-0.1.43.1-20261013/Comparer-Deux-Modeles.py:236`.

Le vérificateur `maintenance/check_sources.py` ne couvrait pas ces dossiers historiques ; son résultat réussi reste exact dans son périmètre. Les instructions ont été séparées pour rendre les sources compatibles avec cet analyseur. Aucun appel depuis le chemin de démarrage actuel n’a été identifié. Aucune panne Python n’est retenue pour ce constat.

## Protections vérifiées et limites de sécurité

**Accès et isolation.** Les jetons distants sont aléatoires, stockés sous forme de hashes et comparés avec `compare_digest`. Le refus des accès révoqués/suspendus/expirés est revérifié pendant de nombreux traitements longs ; un registre de révocation monotone survit aux restaurations. Les opérations sur projets et documents relient les objets au propriétaire. Les appels MCP et d’inférence Hermes portent une identité de tour contrôlée, ce qui corrige le défaut inter-tours de l’audit du 12 octobre. Les tests comprennent les propriétaires étrangers, l’annulation et les accès retirés.

**HTTP et navigateur.** Les principaux serveurs Python disposent de capacité et délais bornés, de limites de corps JSON et d’un rejet des tailles ambiguës/Transfer-Encoding. La console contrôle Host/Origin et un jeton pour les mutations. La passerelle refuse les requêtes de navigateur avec Origin et exige un Bearer. Le Markdown désactive le HTML brut, borne les liens à HTTP(S), empêche les chargements d’images distantes et ajoute `noopener noreferrer`. Les clients utilisent des CSP avec nonce ; la console bénéficie de protections Host/Origin et anti-encadrement. L’exception EG2 est détaillée dans A06.

**Secrets et stockage.** DPAPI protège les secrets Windows ; le client Android utilise AES-GCM avec Android Keystore, écriture atomique et AAD. Les répertoires sensibles contrôlés sont restreints. Le `.gitignore` exclut les fichiers privés courants. La recherche de signatures de clés privées et jetons GitHub/fournisseurs/Fred dans les textes suivis n’a trouvé aucun candidat. Elle ne couvre ni toutes les formes de secrets, ni l’historique Git complet, ni le texte présent dans les captures d’écran, ni tous les fichiers ignorés. Elle ne prouve pas l’absence absolue de secret.

**Documents, réseau et outils.** Les documents sont analysés hors processus principal, avec bornes sur tailles, décompression et temps. Les valeurs SQL des chemins examinés sont liées. La lecture web héritée fixe l’IP vérifiée, maintient SNI/certificat et refuse les adresses privées ; l’adaptateur web natif ajoute des contrôles de destination finale et désactive les caches personnels susceptibles de contenir des pages privées. Les outils Fred ont des périmètres propriétaire/projet/tour ; les outils hôte libres ne sont pas exposés. Les contenus de documents sont traités comme données. Cela réduit les effets d’une injection de prompt, sans garantir qu’un modèle ne produira jamais une réponse inappropriée ou qu’une recherche web ne divulguera aucun contenu de sa requête à son fournisseur.

**Sauvegardes et mises à jour.** Les sauvegardes utilisent Fernet et une dérivation PBKDF2-SHA256 à 600 000 itérations, publication atomique et vérification. Les restaurations disposent de retours après échec et de contrôles de schéma. Windows vérifie la signature Ed25519 du manifeste puis taille/empreinte du binaire et conserve un retour. Android vérifie le paquet, sa version, son empreinte et le certificat de signature avant l’installation confirmée par Android. Un secret de provisionnement initial reste un moyen d’accès personnel à transmettre de façon privée ; la signature des mises à jour ne dispense pas de protéger la première distribution.

## Maintenabilité, performances et exploitation

Les fonctions de transport concentrent encore beaucoup de responsabilités : `serve_gateway` **558 lignes**, son `do_POST` **378 lignes**, `app.serve` **259 lignes**. Extraire progressivement les handlers par domaine, en préservant l’ordre lecture → validation → autorisation → admission → exécution → révocation/annulation. Les tests existants sont indispensables à ces extractions ; une réécriture générale serait difficile à contrôler.

Les imports croisés et modifications de `sys.path` permettent de partager `fred_http`, les pièces jointes et l’interface, mais rendent les dépendances implicites. Un petit paquet commun explicite pour les contrats et le transport réduirait les ambiguïtés. L’assemblage Android par remplacements et expressions régulières est défensif grâce à `replace_once`, mais reste sensible aux changements du HTML ; A05 en montre la nécessité de vérification systématique.

L’indexation et les exports ont déjà une invalidation par propriétaire et des vérifications périodiques. Le stockage Hermes inclut des réservations, quotas et conservation : les anciens défauts ne sont pas simplement repris de l’audit antérieur. La reconstruction du schéma des bases individuelles utilise désormais l’initialisation partagée.

Le test de volume de la suite serveur restaure correctement **8 documents, 16 Mio au total**, avec concordance SHA-256. Dans cette exécution isolée : sauvegarde **1,781 s**, restauration **4,250 s**, verrou de snapshot **0,156 s**, pic RSS d’environ **286,6 Mio**, hausse de RSS d’environ **219,1 Mio**. Les transformations de sauvegarde conservent donc une amplification mémoire notable, malgré les optimisations précédentes. Ces mesures ne décrivent ni les données privées ni le pic global du serveur et ne permettent pas une extrapolation linéaire à de gros volumes.

Les bibliothèques et modèles lourds sont répartis en runtimes dédiés, ce qui est utile pour la stabilité et les performances, mais multiplie les mises à jour de sécurité à suivre. Aucun workflow `.github` suivi n’a été trouvé. Une commande locale/CI de validation regroupant syntaxe, tests, fraîcheur Android, locks et avis de sécurité éviterait des contrôles oubliés ; les builds GPU et la signature restent sur un environnement adapté.

Pendant la lecture de production, environ **65,3 Gio de RAM** et **26,4 Gio libres sur C:** ont été observés ; D: disposait d’environ **4 268 Gio libres**. C: héberge outils et caches : prévoir une alerte de capacité avant une reconstruction importante. Ces instantanés ne constituent ni un profil de charge ni une alerte de saturation avérée.

Le chargement du modèle et la reprise bénéficient de contrôles d’identité des processus et d’une protection RAM. Le pilote et le paquet Strata doivent rester une combinaison explicitement validée : le moteur 0.1.45.3 annonce un support SM60 expérimental et la documentation du 19 octobre conserve une réserve sur le pilote. Aucun benchmark GPU, test thermique, redémarrage Windows ni nouveau chargement à froid n’a été réalisé ici. L’audit n’a pas rétabli de seuil thermique que l’utilisateur avait explicitement demandé de retirer.

## Plan de correction proposé

| Ordre | Travail | Critère de clôture |
| --- | --- | --- |
| 1 | Restreindre les droits de l’exploitation et séparer le checkout | Un compte standard distinct ne peut modifier ni sources exécutées ni registre d’accès ; exploitation normale validée |
| 2 | Corriger Certifi dans les runtimes concernés | Magasin corrigé, tests fournisseurs/HTTPS/web réussis, artefacts réellement concernés identifiés |
| 3 | Mettre à jour pypdf et trier les autres avis | Extraction et corpus de documents passent ; chaque avis est associé à un chemin atteint, bloqué ou absent |
| 4 | Configurer une seconde copie indépendante | Copie chiffrée réussie et restauration isolée complète ; phrase et signatures récupérables |
| 5 | Résoudre la dérive Android | `Prepare-Assets.py --check`, suites UI et validations Android réussis |
| 6 | Borner le serveur EG2 avant les en-têtes | Tests de transport incomplet/saturation sans modèle lourd ; reprise normale vérifiée |
| 7 | Stabiliser une référence de livraison et les locks | Reconstitution dans un répertoire neuf depuis références/empreintes, sans copier les secrets dans Git |
| 8 | Actualiser l’état courant, indexer les archives et extraire les handlers | Documentation cohérente et suite de régression inchangée |

Les corrections 1 à 3 méritent une fenêtre de déploiement préparée et un retour arrière. Une mise à jour de bibliothèque dans un processus déjà démarré ne garantit pas le remplacement du code chargé ; prévoir un redémarrage ciblé et une vérification après activation, sans interrompre inutilement le moteur lourd.

## Ce que cet audit ne certifie pas

Le rapport ne constitue pas un pentest de l’exposition Internet Cloudflare/OVH, un audit des règles de routeur et pare-feu dans tous leurs états, une revue exhaustive du code C/CUDA/Go/JavaScript tiers, une analyse des poids de modèles, un test sur appareils Android physiques, une validation acoustique de la voix, une analyse complète de l’historique Git ou une reconstruction bit à bit des EXE/APK. La signature Android n’a pas été renouvelée et les binaires distribués n’ont pas été reconstruits.

Les résultats des tests décrivent la suite exécutée, pas une nouvelle mesure de couverture de branches. Les taux de couverture du rapport du 12 octobre ne sont pas présentés comme des mesures actuelles. Les avis OSV sont un instantané au 21 octobre : les alertes de paquets présents demandent une qualification fonctionnelle et ne prouvent pas toutes une exploitation possible dans Fred.

L’objectif de livraison de cet audit est un état vérifiable, des risques hiérarchisés et un plan de correction. Les sources applicatives et l’exploitation restent à corriger dans un travail distinct autorisé par l’utilisateur.
