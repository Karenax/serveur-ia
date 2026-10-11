# Accès serveur Fred — Android

Un même APK est fourni pour téléphone et tablette Android 8.0 ou plus récent
(API 26 minimum, cible API 36). Il inclut les moteurs ARM64 et x86_64.
Les appareils Android limités aux applications 32 bits ne sont pas pris en charge.

## Installer et ouvrir

Le fichier à installer est `dist/Acces-serveur-Fred-Android.apk`, version
**1.0.9** (`versionCode=10`). Installer le nouvel APK par-dessus l’application
existante pour conserver le profil et les conversations.
Transférer cet APK sur l’appareil puis l’ouvrir et autoriser son installation
depuis l’application utilisée pour ouvrir le fichier.

Au premier lancement, toucher **Importer mon profil**, sélectionner
le fichier `.fred-android` ou l’EXE personnel fourni pour cet appareil,
puis choisir **HTTPS** ou **WireGuard**. L’EXE est seulement lu : Android
n’exécute pas le programme Windows.

HTTPS utilise `https://ia.karenax.net`, avec vérification du certificat et
sans suivre les redirections. WireGuard utilise l’adresse personnelle incluse
dans le profil. Cette version affiche cette adresse sans la modifier.
Le moteur WireGuard est intégré à l’application : aucun VPN Android séparé
n’est nécessaire. La connexion dépend aussi de la disponibilité du serveur
et des autorisations de l’accès personnel.

## Sources et notifications

Dans un projet, ouvrir **Rechercher un passage dans les documents** puis
**Ouvrir le passage cité**. Fred affiche le texte utilisé, sa révision et
la page réelle lorsqu’elle existe. Une note n’affiche aucune page inventée.
Une citation ancienne conserve son extrait et signale un document modifié
ou supprimé. Les résultats des tâches conservent également leurs sources.
Le geste Retour ferme d’abord le passage consulté.

La rubrique **Notifications** retrouve les événements conservés sur le serveur,
y compris après une fermeture de l’application. **Marquer lu** et les
préférences par type sont synchronisés avec le serveur. Pour les alertes
Android, toucher **Activer les alertes Android** : la permission système est
demandée à cet instant, jamais au démarrage. Un refus laisse la boîte Fred
utilisable.

Le réglage serveur **Alertes discrètes** choisit le canal des prochaines
alertes Android : coché, il est silencieux ; décoché, il utilise le son de
notification Android, selon les réglages système de l’appareil. Changer ce
réglage ne renvoie pas une alerte déjà annoncée. Android permet de personnaliser
chacun des deux canaux ; ces choix système sont respectés.

Les alertes système utilisent toujours une phrase générique ; aucun titre
de document, extrait ou conversation privée n’y figure, même sur l’écran
verrouillé. Un rattrapage produit au maximum une alerte, ouvrant le résultat
le plus récent ; la boîte Fred conserve tous les événements. Le clic relit
la notification après authentification avant d’ouvrir sa destination.
La lecture, la révocation et la suppression d’un événement expiré retirent
les alertes correspondantes. Au maximum vingt alertes restent dans le tiroir
Android.

Cette livraison reçoit les événements pendant l’utilisation de Fred et à
sa prochaine ouverture. Une application complètement arrêtée ne reçoit pas
de nouveau push. Les essais physiques de veille et de gestion de batterie
restent distincts ; aucun fournisseur de push externe n’est configuré.

## Préparer l’accès d’un appareil

Dans la console serveur, ouvrir **Appareils → ＋ Ajouter un appareil**.
Saisir un nom distinct, par exemple « Téléphone de Paul », et éventuellement
un propriétaire. Choisir **Android · profil à importer** dans **Application**,
puis **Téléphone** ou **Tablette** dans **Type d’appareil**. Cliquer sur
**Créer l’accès personnel**, puis **Télécharger le profil Android** sur
la fiche de l’appareil. Le serveur crée directement le fichier
`.fred-android`, sans passer par un EXE Windows ; sa copie serveur est
conservée chiffrée avec DPAPI.

La console permet aussi de suspendre, réactiver ou révoquer l’appareil,
et d’en consulter la dernière activité. Un remplacement crée un nouvel
accès et archive l’ancien ; les données restent rattachées à leur accès.
Le propriétaire sert à identifier l’appareil dans la console.

Pour un accès Windows existant, l’EXE personnel reste importable directement
dans Android. Un fichier de profil peut aussi être extrait ainsi, depuis
`D:\Serveur IA` :

```powershell
.\client-android\Export-Profil-Android.ps1 `
  -Exe '.\lanceur\clients\IDENTIFIANT.exe' `
  -DossierSortie '.\client-android\exports-prives\telephone-paul'
```

Remplacer `IDENTIFIANT.exe` par l’EXE téléchargé ou son chemin réel.
Le dossier de sortie doit être nouveau. Le résultat est
`exports-prives/telephone-paul/profil.fred-android` ; le dossier Windows
est protégé avant toute écriture du profil. L’export lit et vérifie le
format du profil, sans créer de client, modifier d’autorisation ni toucher
aux clés du serveur.

**Un accès distinct par appareil.** L’export conserve la clé API, la clé
WireGuard et l’adresse existantes. Utiliser le même profil sur un PC et un
téléphone, ou sur deux appareils Android, leur donne la même identité,
les mêmes données et les mêmes autorisations ; en WireGuard, les appareils
peuvent se couper mutuellement la connexion.

Le fichier `.fred-android`, comme l’EXE personnel, contient des secrets en
clair. Le remettre uniquement à son destinataire par un transfert privé.
Après import, l’application conserve sa propre copie chiffrée ; le fichier
source reste à l’emplacement choisi dans les fichiers de l’appareil.

## Fonctions adaptées

| Fonction | Comportement Android |
| --- | --- |
| Conversations | Réponses progressives, Markdown, choix du modèle et réflexion |
| Historique | Copie locale chiffrée, synchronisation avec le serveur, import/export |
| Restauration serveur | Confirmation explicite avant de reprendre la synchronisation ; copie chiffrée de l’ancien historique local conservée |
| Documents et pièces jointes | Sélecteur de fichiers Android et enregistrement dans un emplacement choisi |
| Espaces de travail | Projets, documents, correcteur et tâches côté serveur |
| Téléphone/tablette | Interface adaptative, tiroir latéral sur téléphone, clavier tactile |
| Copie | Presse-papiers Android |
| Connexion | Choix explicite HTTPS ou WireGuard, accès personnels existants |
| Appareil | Déclaration authentifiée du format téléphone/tablette, de la version et du transport ; activité consultable dans la console |
| Mise à jour | Détection et téléchargement automatiques ; installation confirmée dans Android |

Dans le champ de message, **Entrée** ajoute une ligne ; le bouton **↑**
envoie le message. Les intégrations spécifiques au PC et l’installation
des mises à jour Windows sont retirées de l’interface Android.
En WireGuard, chaque requête complète (messages et pièces jointes) est
limitée à 2 Mo : alléger les grosses images ou envoyer moins de pièces à la fois.

Les profils, historiques, brouillons et préférences sont chiffrés avec
AES-GCM et une clé Android Keystore, dans le stockage privé de l’application.
Les remplacements de fichiers sont atomiques. Les sauvegardes Android de
ces données sont désactivées. Aucun profil personnel n’est inclus dans
l’APK ; la clé API du serveur reste dans la partie native de l’application.
Les fichiers volontairement exportés via le sélecteur Android sont des
fichiers ordinaires, sans ce chiffrement local.
Après une restauration serveur, l’application détecte le changement de
génération de l’historique et demande une confirmation avant de reprendre
les échanges. Le type et la version déclarés par l’application sont des
informations d’inventaire ; les autorisations viennent de l’accès serveur.

## Construire l’APK

Depuis la racine du projet, dans PowerShell :

```powershell
.\client-android\Build-Android.ps1
```

Le script charge `client-qwen/android-outils/Environnement-Android.ps1`,
choisit le Python 3.12 existant du projet, compile le moteur WireGuard,
prépare et vérifie l’interface mobile, exécute les tests de profils, puis
lance `assembleRelease` avec Gradle 8.13 et Android Gradle Plugin 8.13.2.
Il aligne l’APK sur 16 Ko, le signe, vérifie la signature et l’alignement,
puis copie le résultat et son SHA-256 dans `dist/`.

La signature utilise une clé locale RSA 3072 persistante, alias
`fred-client`, conservée dans `toolchain/android-signing/fred-client.p12`.
Son mot de passe aléatoire est conservé dans `password.dpapi`, protégé
par le compte Windows. Ce dossier privé est exclu de Git. Le mot de passe
n’est jamais affiché ni transmis dans les arguments de commande.
**Conserver cette clé et son secret pour signer les prochaines mises à jour.**
Un [outil de récupération séparée](../lanceur/RECUPERATION-SIGNATURES.md)
permet d’exporter et de vérifier un paquet portable chiffré `.fredkeys`,
avec le mot de passe Android déprotégé uniquement en mémoire.
La signature est destinée à une distribution privée de l’APK ; aucune
publication dans Google Play n’est effectuée.

Les licences complètes du projet (MIT), de markdown-it (MIT), de Go (BSD)
et des modules du moteur WireGuard sont incluses dans l’APK sous
`assets/third-party/`. Le script vérifie que les licences des dépendances
présentes dans les deux moteurs compilés sont disponibles localement.

Pour le développement uniquement :

```powershell
.\client-android\Build-Android.ps1 -Configuration Debug
```

La sortie est alors `dist/Acces-serveur-Fred-Android-debug.apk`.
Cette variante utilise le certificat debug, autorise l’inspection WebView
et la démonstration de test ; la variante Release désactive ces fonctions.
Les certificats debug et Release étant différents, ils ne permettent pas
de remplacer directement une variante par l’autre avec `adb install -r`.

Pour préparer une livraison avant sa publication, l’option
`-OutputDirectory 'D:\Serveur IA\toolchain\releases-staging\android-1.0.2'`
place l’APK vérifié dans ce dossier sans remplacer le paquet de `dist/`.

## Tester

Les tests d’export utilisent uniquement des EXE synthétiques. Ils vérifient
la lecture bornée du footer `QWENPROFILE1`, les profils invalides,
l’absence de secrets dans les erreurs, le refus d’écraser une sortie
existante et les permissions Windows réelles du dossier exporté.

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover `
  -s '.\client-android\tests' -p 'test_*.py' -v
.\client-android\tests\Test-Signing.ps1
```

Le test de signature utilise l’APK de contrôle Android et une clé
temporaire isolée ; il vérifie signature v2/v3, alignement, permissions,
réutilisation de la clé et nettoyage du mot de passe de l’environnement.
Il ne modifie pas la clé de distribution.

Pour installer sur un appareil USB ou un émulateur démarré :

```powershell
. .\client-qwen\android-outils\Environnement-Android.ps1
adb devices
adb install -r '.\client-android\dist\Acces-serveur-Fred-Android.apk'
```

Les profils virtuels `Fred_Telephone_API36` et `Fred_Tablette_API36`
peuvent être démarrés avec les scripts du dossier `client-qwen/android-outils`.
Pour la version 1.0.2, les tests natifs ont réussi sur les deux émulateurs
Android 16, y compris le chiffrement, l’import, la synchronisation et la
confirmation d’une restauration avec une copie locale précédente déchiffrable.
Le tunnel WireGuard réel, les réponses progressives et la déclaration
d’appareil ont été vérifiés contre un serveur de test Windows isolé.
L’instrumentation utilise la variante Debug ; la mise à jour du Release signé
depuis 1.0.1 a conservé le profil, le choix de connexion et la conversation sur
les deux formats. Les sources et notifications ont été vérifiées dans la vraie
WebView et avec les dialogues et clics Android.
Les [preuves des lots 6 et 8](../preuves/lots-6-8/android/VALIDATION.md)
et [VALIDATION.md](VALIDATION.md) distinguent les vérifications actuelles
des essais historiques.
Les essais sur appareil physique ARM64 et une conversation HTTPS avec
un compte autorisé restent à effectuer.

## Dictée locale 1.0.3

Whisper Small français est disponible avec les boutons Installer la dictée, Dicter et Terminer la dictée. Télécharger le modèle une fois (environ 488 Mo), autoriser le microphone, dicter puis corriger et envoyer le texte. Aucun envoi automatique, aucun audio transmis au serveur. Small peut prendre du retard selon le CPU. [Guide commun](../client-voice/README.md) et [preuves téléphone/tablette](../preuves/voix-small-20261011/VALIDATION.md). Installer l’APK signé par-dessus l’application existante ; aucune désinstallation n’est nécessaire.

## Interface Android 1.0.4

Le bouton « Réessayer la réponse » et son menu Options sont supprimés sur
Android. L’action « Réessayer sans réflexion » reste disponible uniquement
si le modèle termine sa réflexion sans réponse finale. La préparation de
l’interface vérifie l’absence du bouton supprimé à chaque compilation.

Validation du 11 octobre 2026 : 13 tests Python réussis, vérification de la
syntaxe JavaScript, essais navigateur téléphone/tablette réussis, compilation
Release et signature v2/v3 vérifiées. La tablette physique doit recevoir le
nouvel APK pour appliquer cette modification.

## Mises à jour automatiques 1.0.5

Pendant l’utilisation de Fred, l’application recherche une nouvelle version
au démarrage après le choix de connexion, puis toutes les dix minutes.
Elle télécharge automatiquement l’APK dans son stockage privé, via HTTPS ou
WireGuard, avec l’accès personnel importé. Dans **Mon accès personnel →
Mises à jour Android**, **Rechercher une mise à jour** permet de relancer la
vérification ou un téléchargement interrompu. L’application arrêtée ne
recherche pas de mises à jour.

Quand l’APK est prêt, le bandeau **Installer la mise à jour** apparaît.
L’installation attend la fin de la conversation et un enregistrement confirmé.
Android peut demander d’autoriser Fred à installer des applications ; au retour,
l’installateur s’ouvre et demande la confirmation. Une annulation conserve
l’application et ses données ; le bouton permet de recommencer.

Le téléchargement est borné à 128 Mo. Le client vérifie sa taille et son SHA-256,
le nom du paquet, une version strictement plus récente et la même signature que
l’application installée. L’APK est partagé avec l’installateur par une URI
temporaire en lecture seule. Aucun accès personnel n’est inclus dans le paquet.

`Build-Android.ps1` publie l’APK signé et `dist/release.json`. Le serveur vérifie
leur concordance avant d’exposer les routes authentifiées
`/v1/client/android/release` et `/v1/client/android/download`. La publication d’une
nouvelle compilation Release suffit ensuite à la proposer aux appareils.

**Première installation :** les versions 1.0.4 et précédentes n’ont pas cette
fonction. Installer une fois manuellement l’APK 1.0.9 par-dessus l’application
existante ; les versions suivantes pourront être téléchargées depuis Fred.

## Conversations Hermes 1.0.6

Les conversations passent par Hermes sur
le serveur, avec un profil par accès Fred et une session par discussion.
La création d’un nouvel accès prépare son profil automatiquement.
La progression affiche les recherches et outils séparément de la réponse.
Quand une action exige un accord, Fred décrit son effet : **Autoriser cette
action** ne vaut que pour cette action ; **Refuser** empêche son exécution.

Chaque envoi possède un identifiant durable. Après une coupure, Fred retrouve
la réponse finalisée sur le serveur sans exécuter une seconde fois la demande.
Un accord encore en attente est retrouvé après la réouverture de Fred, dans
la même conversation et le même projet.
**Arrêter** attend la confirmation serveur. L’historique chiffré, les profils
importés et les mises à jour automatiques APK sont conservés.

Le transport annonce le protocole conversationnel 4 ; les profils existants
au format 3 restent importables. Hermes utilise le modèle choisi parmi ceux autorisés par le serveur. Aucun
agent ni secret de fournisseur n’est installé sur l’appareil. Une panne Hermes est signalée explicitement.

## Correcteur direct 1.0.7

Les trois actions **Corriger**, **Reformuler professionnel** et **Reformuler
amical** du correcteur utilisent directement le Qwen local sur le serveur.
Le serveur choisit la consigne d’après l’action ; le texte fourni est traité
comme un texte à transformer. Le résultat reste dans le correcteur, avec
les actions de copie et de reprise habituelles. Les conversations et les
tâches continuent d’utiliser Hermes et ses outils autorisés.

Le profil importé, l’historique chiffré, la dictée locale Whisper Small et
les mises à jour automatiques sont conservés. Installer cette version
par-dessus l’application existante.

## Choix du modèle 1.0.8

Le sélecteur près du champ de message affiche les modèles autorisés par le
serveur, avec leur fournisseur et leur disponibilité. Le choix est enregistré
avec chaque conversation et retrouvé après sa réouverture, son import ou la
synchronisation de l’historique. Une nouvelle conversation utilise le modèle
par défaut du serveur.

Le modèle choisi sert au chat, au contexte et à la réflexion. Les possibilités
d’image suivent ses capacités. Si ce modèle devient indisponible ou est retiré,
Fred conserve le choix et demande de sélectionner un modèle disponible avant
d’envoyer ; il ne remplace pas silencieusement le modèle. Un fournisseur distant
peut répondre lorsque le Qwen local est déchargé.

Les trois boutons du correcteur continuent d’utiliser directement le Qwen local.
Les tâches utilisent le modèle par défaut du serveur via Hermes.
La [validation Android 1.0.8](../preuves/model-selector-20261011/ANDROID.md)
consigne le transport natif, l’historique chiffré, le correcteur et les contrôles
de mise à jour exécutés sur le Release signé.

## Sélecteur stable 1.0.9

Le menu conserve son défilement et le modèle pointé pendant les actualisations
du serveur. Les nouveaux modèles apparaissent après la fermeture du menu.
Les modèles indisponibles sont masqués, sauf le choix déjà enregistré dans
une conversation : celui-ci reste signalé jusqu’à un nouveau choix explicite.
L’administrateur peut aussi choisir les modèles proposés dans la console.

La [validation Android 1.0.9](../preuves/model-picker-fix-20261011/ANDROID.md)
documente les huit contrôles du vrai menu Android, les 31 vérifications de
l’APK signé et la validation isolée des contrôles de partage dans la console.
