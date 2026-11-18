# Reconstruire et vérifier Kiara

La livraison de référence est Kiara 4.0.8 pour Windows et le portail privé.
La 4.0.7 constitue le point de retour Windows. Les clients Android et Linux
gardent leur propre calendrier de qualification. Chaque construction produit
`build-manifest.json` : empreintes des sources, empreinte du binaire, versions des
paquets Python, Go, CMake, JDK, SDK/NDK Android et commit Hermes réellement utilisés.
Les sources modifiées avant commit sont identifiées par leurs empreintes.
Le manifeste est propre à son composant ; `maintenance/deployment_manifest.py`
relie les livrables et les résultats de validation, puis vérifie leurs empreintes.
La [référence d’architecture](ARCHITECTURE-ACTUELLE.md) décrit les données, versions
et compatibilités courantes.

## Préparer le poste

1. Extraire le dépôt sur Windows, avec Git, PowerShell 7 ou Windows PowerShell 5.1,
   Node.js ≥ 20 et Chrome. Sur le poste Fred, placer sur D: le dépôt, les outils,
   les caches, les fichiers temporaires et les résultats de recette. E: est
   réservé aux archives et aux preuves conservées. Utiliser les chemins de la
   configuration locale du lanceur pour retrouver le moteur et les modèles.
   [dependances/moteurs.json](dependances/moteurs.json) conserve les références des
   dépôts historiques et de leurs patchs, décrites dans
   [dependances/README.md](dependances/README.md).
2. Préparer Python 3.12 dans `Strata-src/.venv`, sans héritage des bibliothèques
   d’outillage, puis installer le verrou `dependances/verrous/strata.requirements.txt`
   et le paquet local `shared` avec `--no-deps --no-build-isolation -e shared`.
   Préparer séparément `toolchain/build-python` avec
   `maintenance/prepare_build_environment.py` ; PyInstaller appartient à ce constructeur. Les
   modèles GPU, CUDA, compilateur et dépendances propres à Strata se préparent
   suivant le moteur épinglé ; leurs poids restent hors Git.
3. Préparer le runtime privé Hermes et ses dépendances publiques verrouillées.
   Le pointeur `toolchain/hermes-security-runtime/runtime.json` déclare ses sources,
   Python, dépendances et outils ; il est résolu avant le bootstrap personnel.
   Le commit utilisé par une livraison
   figure dans son manifeste et se vérifie avec `hermes_service.installation()`.
   Kiara réutilise ce runtime ; il ne télécharge pas de dépendances pendant une conversation.
4. Préparer les dépendances vocales selon [client-voice/README.md](client-voice/README.md)
   et [CONVERSATION-WINDOWS.md](client-voice/CONVERSATION-WINDOWS.md). Le build utilise
   Whisper.cpp 1.9.5, CMake 3.31.8, Ninja 1.12.1 et MSVC sous `toolchain` ; les
   dépendances du worker sont épinglées dans `client-voice/requirements-conversation.txt`.
   Windows utilise Parakeet v3 pour dictée et conversation avec le runtime ONNX
   existant ; Android conserve Whisper Small. Le catalogue Windows épinglé se
   vérifie avec `client-voice/prepare_conversation.py` (`--download` pour installer).
   L'[étude du 23 octobre](maintenance/2026-10-23-reconnaissance/README.md) décrit les
   mesures et les propositions Android non encore déployées.
5. Pour Android, disposer du SDK 36, build-tools 36.0.0, NDK 27.3.13750724,
   Gradle 8.13 et JDK 21 aux emplacements définis par
   `client-qwen/android-outils/Environnement-Android.ps1`. Lancer
   `Verifier-Android.ps1` pour vérifier ces outils avant compilation.
6. Installer le Go épinglé avec `maintenance/prepare_go.py` : version et empreinte
   publique dans `client-qwen/wireguard-toolchain.json`. Conserver les caches des modules vérifiés par
   `go.mod/go.sum`. Conserver les clés privées dans leurs dossiers exclus de Git :
   une nouvelle clé empêcherait les mises à jour des clients déjà installés.

Les emplacements sont explicités par les scripts et les manifestes. Un checkout
seul ne contient pas les SDK, moteurs, modèles et clés privées. Le manifeste décrit
la construction réalisée ; il ne promet pas un binaire bit à bit identique sur un
autre poste ou avec une autre clé.

Pour la livraison Windows, construire le client Tauri et le paquet serveur avec
le portail compilé. Utiliser la validation de périmètre `windows` pour le
manifeste de déploiement. La 4.0.9 publiée utilise le manifeste Ed25519 du canal
avec un installateur sans Authenticode. Conserver l’installateur et le manifeste
4.0.8 ainsi que l’index du portail précédent. [Construction Windows](client-tauri/README.md)
[Procédure de bascule et preuves](audits/2026-11-15-fusion-kiara/BASCULE.md)

Construire le relais avec `Build-Client.ps1 -Relay -SkipManifest`. La recette
PyInstaller utilise `client-qwen/kiara-relay.spec` pour embarquer les ressources de
récupération et du portail. Extraire le NSIS de distribution et comparer les
empreintes de `Kiara.exe`, `kiara-relay.exe` et `kiara-agent-capture.exe` aux
binaires de construction. Vérifier WebView2 en 720p, 1080p et 1440p.

Pour activer le service Projets au démarrage du lanceur, créer `project-service.json` dans
`KIARA_DATA_DIR` (par défaut, le dossier `lanceur`). Renseigner `data` avec le
chemin absolu du dossier des données des projets qui contient `brain`, `erp` et `storage`,
et `python` avec celui de l’exécutable Python du service. Le champ facultatif
`speech_python` désigne le runtime audio.
Le champ `speech_models` désigne le dossier des modèles audio et de leur rapport
`audio-qualification.json`. `KIARA_PROJECT_SPEECH_MODELS_DIR` prime sur le fichier.
Installer `agent/requirements-pdf.txt` dans le Python du service pour le rendu PDF.
La recherche multimodale locale est obsolète. La recherche sémantique utilise
EmbeddingGemma 2 via EG2, y compris pour le texte extrait des images et de l’audio.
Les variables `KIARA_PROJECT_DATA_DIR`, `KIARA_PROJECT_PYTHON` et
`KIARA_PROJECT_SPEECH_PYTHON` priment sur les champs correspondants.
Les variables de démarrage `KIARA_AGENT_*` restent lues lorsque la variable
`KIARA_PROJECT_*` correspondante est absente. Pendant le pilote, conserver
les anciennes valeurs pour un retour vers le lanceur précédent.
Après modification du fichier, relancer le lanceur.
Sous Windows, pour relancer uniquement le lanceur depuis une session de même
niveau de droits, exécuter `& '.\Start-Interface-Qwen.ps1' -Redemarrer -SansNavigateur`.
L’option `-VerifierBascule` exécute les vérifications préalables sur le lanceur
en service. Lors de la première activation, elle vérifie aussi en lecture seule
que le catalogue Kiara historique ne contient aucun projet ni document, puis
relève les projets de la base ERP restaurée. À chaque redémarrage, le script
compare les identifiants, codes, intitulés et états relevés avant l’arrêt
au catalogue du service Projets.
Dans **Clients & accès**, ouvrir **Droits sur les projets** pour consulter les erreurs de configuration et de démarrage.
Les journaux du processus sont dans `logs/service.log` sous le dossier des données des projets.
Pour la recette d’une restauration, `start_workers: false` suspend le démarrage
automatique des traitements. La variable `KIARA_PROJECT_START_WORKERS` accepte `0`
ou `1` et prime sur le fichier. Les traitements démarrent par défaut.
Pour une reprise progressive, régler `start_workers` à `true` et renseigner
`worker_groups` avec les groupes à démarrer parmi `mail`, `cdc`, `audio`,
`documents`, `planning` et `knowledge`. Une liste vide les
suspend tous. Sans ce champ, le service applique le démarrage habituel.
Pour les documents de projet, `document_roots` et `document_write_roots`
sont deux listes distinctes de chemins absolus vus par le service Projets.
`document_drive_mappings` associe si nécessaire une lettre de lecteur
au chemin absolu du partage sur le serveur. Les variables JSON
`AGENT_DOCUMENT_ROOTS`, `AGENT_DOCUMENT_WRITE_ROOTS` et
`AGENT_DOCUMENT_DRIVE_MAPPINGS` priment sur le fichier. Sans racines
configurées, le service désactive l’accès correspondant.
Le champ `document_project_root` désigne le répertoire privé des dossiers
clients. Kiara crée un sous-dossier par projet lors de la création ou de
l’import. La configuration autorise le projet à lire et publier dans son
sous-dossier. Les racines partagées doivent être distinctes de ce répertoire.
`AGENT_DOCUMENT_PROJECT_ROOT` accepte un chemin absolu encodé en JSON.
La sauvegarde chiffrée inclut les dossiers clients. Une restauration isolée
place les fichiers sous `data/dossiers-clients` et reloge les liens correspondants.
Pour remettre une restauration en service, définir `data` sur son répertoire de
données et `document_project_root` sur le dossier client restauré.
Dans Kiara, le scan des jalons utilise les mêmes racines de lecture et les
mêmes correspondances de lecteurs pour ses sources réseau.
Pour activer le web privé, renseigner `web_origin` avec son origine HTTPS
dédiée et, si nécessaire, `web_port` avec le port local (8767 par défaut).
Le proxy HTTPS conserve l’en-tête `Host` et transmet au port d’écoute sur
`127.0.0.1`. Les variables `KIARA_PROJECT_WEB_ORIGIN` et `KIARA_PROJECT_WEB_PORT`
priment sur le fichier.
Pour les imports Thunderbird, renseigner `thunderbird_device` avec l’identifiant
de l’accès Kiara du poste prévu. Cet accès doit avoir le rôle Propriétaire sans
restriction de projets. `KIARA_PROJECT_THUNDERBIRD_DEVICE` prime sur le fichier.

L’intégration de l’assistant ajoute des ressources de détection locale épinglées
(sherpa-onnx 1.13.8, modèle int8, AAR Android) : exécuter
`maintenance/2026-10-25-assistant-integration/prepare_wakeword.py --download` avec
le Python du projet si elles sont absentes. Les deux scripts de build vérifient
leurs empreintes sans téléchargement implicite. Le modèle reste expérimental
pour la phrase française ; voir le [rapport et ses limites](maintenance/2026-10-25-assistant-integration/README.md).

## Exécuter les vérifications

Les runtimes applicatifs, dont EG2 CPU et CUDA, et le constructeur Windows disposent de sept
[verrous avec empreintes](dependances/verrous/README.md). Vérifier leur conformité
avec `maintenance/verrous_runtime.py check`. Reconstruire dans des environnements
neufs à partir des verrous ; ne pas modifier le runtime personnel Hermes. Kiara
sélectionne son runtime privé validé par le pointeur
`toolchain/hermes-security-runtime/runtime.json`, préparé avec le script et le
patch de `maintenance/2026-10-21-correctifs-audit/`.

Sur ce poste, le projet actif est `D:\Serveur IA`. Préparer sur **D:** les outils,
caches, fichiers temporaires, builds, restaurations de recette et nouvelles preuves.
**E:** est réservé au stockage des archives et des preuves finalisées. Pendant la
suspension des accès à E:, conserver également les livrables et les preuves sur D:.

Depuis la racine, indiquer explicitement la sortie sur D:. `--output` est prioritaire
sur `KIARA_EVIDENCE_DIR`, qui peut contenir un ancien chemin.

```powershell
$Recette = Join-Path $PWD ('toolchain\test-results\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/verify_project.py --desktop-audit --output $Recette
```

Il agrège les échecs et produit `validation.json` dans un répertoire d’exécution
sous `toolchain/test-results`. `--output` permet un emplacement explicite et
`--checks` un sous-ensemble. Les vérifications OSV et Go consultent les avis publics.
Les captures UI restent dans ce répertoire et ne remplacent aucune preuve historique.

Pour la vérification ciblée Windows et Linux de l'audit, sans lancer Android ni
les anciens tests Qt, utiliser `--desktop-audit` et fournir au besoin
`--business-python` avec un environnement Python contenant les dépendances du
service Projets. Ce profil comprend un test serveur isolé, les contrôles statiques
et la compilation du portail, puis deux simulations Chromium de l'interface aux
tailles de bureau de 720p à WQHD. Le champ `coverage` du rapport énumère les
groupes non enregistrés ; la réussite concerne les seules commandes exécutées.
Ces simulations ne remplacent pas les recettes Tauri natives Windows et Linux,
ni la suite complète du service ou du portail.
Sans `--desktop-audit` ni sélection `--checks`, le contrôle historique lance un
ensemble plus large qui comprend Android et des scénarios mobiles.

Les commandes individuelles restent disponibles :

Le runtime EG2 doit recevoir son verrou `dependances/verrous/eg2.requirements.txt`
puis le paquet local partagé, comme Strata :

```powershell
& '.\toolchain\eg2-python\Scripts\python.exe' -m pip install --require-hashes -r dependances/verrous/eg2.requirements.txt
& '.\toolchain\eg2-python\Scripts\python.exe' -m pip install --no-index --no-deps --no-build-isolation -e shared
& '.\toolchain\eg2-python\Scripts\python.exe' -m pip check
```

`Install-EG2.ps1` installe également ce paquet local. Après une réparation,
**Activer EG2** remet à zéro les essais de démarrage sans redémarrer Qwen.

Depuis le 4 novembre, `lanceur/eg2-runtime.json` sélectionne la P2200 pour EG2.
Préparer d’abord le runtime CPU de secours, puis le runtime CUDA verrouillé avec
`maintenance/prepare_eg2_gpu.py`. Le runtime CUDA validé conserve son chemin
historique `toolchain/eg2-gpu-benchmark-python-20261104` : ce dossier est désormais
un prérequis de production et ne doit pas être nettoyé comme un résultat de test.
Il partage les dépendances publiques verrouillées du runtime CPU et charge ses
propres roues PyTorch/torchvision CUDA 12.6. Les sources locales `shared` restent
référencées explicitement. Le verrou `eg2-gpu.requirements.txt` permet aussi une
reconstruction autonome avec toutes les dépendances.

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' -m pip check
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s lanceur -v
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s client-qwen -v
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s client-voice -v
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s client-android/tests -v
```

Les tests natifs Hermes utilisent des dossiers temporaires et des fournisseurs
HTTP synthétiques. Ils nécessitent le runtime installé. Des suites sans interface
testent directement les mêmes sources du chat Windows et de l’interface Android.
Leurs dépendances et versions sont désormais indépendantes d’un dossier Codex personnel :

```powershell
Push-Location client-qwen
npm ci --ignore-scripts
npm test
Pop-Location
```

`PLAYWRIGHT_MODULE` permet facultativement de réutiliser un module déjà installé.
`CHROME_PATH` permet un navigateur personnalisé ; sous Windows, Chrome est recherché
par son canal Playwright. Sous les autres systèmes, installer Chromium avec
`npx playwright install chromium`. Aucun chemin `C:/Users/karen` n’est imposé.

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' client-android/scripts/Prepare-Assets.py --check
. '.\client-qwen\android-outils\Environnement-Android.ps1'
& '.\toolchain\gradle-8.13\bin\gradle.bat' --offline --no-daemon --console=plain -p client-android lintDebug assembleDebugAndroidTest
```

Les tests d’instrumentation se lancent sur un émulateur/appareil de test avec l’APK
debug et son APK de tests. `SelfTestInstrumentation` et `-e fred_updates true`
vérifient notamment la politique des signatures et la conservation du cache.

## Construire avant publication

Avant les tests locaux de transport WireGuard, lancer
`& '.\client-qwen\Build-WireGuard.ps1'` depuis la racine. Les fixtures Windows
et Android utilisent le pont reconstruit et son écoute UDP sur `127.0.0.1`.
Avant de créer l’archive serveur, installer les dépendances verrouillées du
portail Kiara avec `pnpm --dir agent/web install --frozen-lockfile`, puis
compiler avec `pnpm --dir agent/web run build`. L’archive serveur contient
l’interface compilée et les sources du service Projets. Les données et le fichier
`lanceur/project-service.json` se préparent sur le serveur cible. `agent-service.json` reste lu si le nouveau fichier est absent.

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/prepare_go.py
& '.\client-qwen\Build-WireGuard.ps1' -OutputBinary "$PWD\toolchain\releases-staging\wireguard-bridge.exe"
& '.\client-qwen\Build-Client.ps1' -DistributionDirectory "$PWD\toolchain\releases-staging\windows" -SkipManifest -WireGuardBinary "$PWD\toolchain\releases-staging\wireguard-bridge.exe"
& '.\client-android\Build-Android.ps1' -OutputDirectory "$PWD\toolchain\releases-staging\android"
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/package_server.py --output toolchain/releases-staging/server
```

Vérifier les manifestes, les ressources incluses et les tests des exécutables avant
de remplacer les dossiers `dist`. Le serveur doit disposer d’une sauvegarde chiffrée
vérifiée. Le manifeste Windows est signé avec `lanceur/releases.py` et les EXE
personnels sont reconditionnés avec `client-qwen/Mettre-A-Jour-Clients.py`, en
préservant leurs profils et clés. Conserver les distributions précédentes pour
le retour. La preuve de chaque mise en service doit confirmer les empreintes des
données et des clés, les processus Qwen et la programmation des sauvegardes.

Pour constituer le manifeste d’ensemble, fournir les trois `build-manifest.json`
et le `validation.json` réussi à `maintenance/deployment_manifest.py`. Le script
refuse une validation incomplète, un fichier remplacé ou des sources changées
depuis la construction. Le paquet serveur contient les sources et les verrous,
pas les modèles, clés ni données privées.

`KIARA_DATA_DIR` permet de séparer les données de la version exécutable ; le chemin
historique reste la valeur par défaut. Toute migration utilise une sauvegarde
vérifiée et la restauration existante. `KIARA_RUNTIME_PYTHON` désigne le Python
d’exécution lorsqu’il se trouve ailleurs que dans le chemin historique.

## Synthèse française Phonon (22 octobre 2026)

Le runtime actif est `toolchain/phonon-server-python` (Python 3.12), isolé de Strata. Reconstruire avec le verrou `dependances/verrous/voix-serveur.requirements.txt`. Télécharger ensuite le checkpoint épinglé avec `maintenance/2026-10-22-phonon/prepare.py --download` dans cet environnement, après acceptation des conditions Hugging Face et connexion. Ses empreintes sont dans `lanceur/phonon-model.json`. La synthèse exige uniquement les fichiers locaux. La procédure et les tests natifs/HTTP sont dans [le rapport de migration](maintenance/2026-10-22-phonon/README.md). Ne pas relancer `activate.py` sur une production déjà migrée.


Depuis le 23 octobre 2026, la voix serveur est Tiphaine (français de France). Le moteur Phonon et son checkpoint restent identiques ; l’embedding de voix est vérifié et épinglé dans `lanceur/phonon-model.json`. Voir [la sélection et les preuves](maintenance/2026-10-23-tiphaine/README.md).

## Client Linux avec vocal

Le [guide Linux](client-linux/README.md) décrit l’installation Ubuntu/Debian,
l’import d’un accès personnel, le trousseau, la dictée et la conversation vocale.
Construire une archive sans données privées avec :

```powershell
& '.\toolchain\build-python\Scripts\python.exe' maintenance/package_linux_client.py
```

Le moteur WireGuard est compilé nativement pour Linux avec le Go épinglé ;
le paquet utilise les sources partagées du client et un environnement Python/Qt
installé sur le poste Linux. Le manifeste Linux est indépendant des manifestes
de publication Windows/Android/serveur. Ne pas l’ajouter à leur publication comme
un livrable natif déjà validé : le premier lancement, le trousseau et les échanges
avec un accès de test doivent encore être vérifiés sur une machine Linux.
La révision Linux 2 produit une archive `*-vocal.tar.gz` avec le worker Python
de reconnaissance et le modèle public du mot d’appel. Le microphone utilise
`parec` (PipeWire/PulseAudio) ; installer `pulseaudio-utils`. Les modèles Low
sont téléchargés et vérifiés par le client. Max utilise le serveur Kiara ; les
compléments Windows ne sont pas exécutés sous Linux. L’écoute se suspend pendant
la réponse puis reprend automatiquement. Voir le [rapport vocal Linux](maintenance/2026-11-01-client-linux/VOCAL.md).

## Codex avec Qwen via Kiara

Le [guide Codex](maintenance/codex/README.md) décrit le profil client, le stockage
Windows chiffré de la clé, les sous-agents et les qualifications Responses.
Les scripts de mise en service conservent le modèle chargé, les accès et les
historiques ; les EXE personnels restent utilisables sans reconstruction pour
les connexions Codex directes en HTTPS.
