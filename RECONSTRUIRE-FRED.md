# Reconstruire et vérifier Kiara

Les constructions Windows/serveur 3.5.54 et Android 1.0.25/code 26 utilisent les
sources locales et les clés de signature existantes. Chaque construction produit
`build-manifest.json` : empreintes des sources, empreinte du binaire, versions des
paquets Python, Go, CMake, JDK, SDK/NDK Android et commit Hermes réellement utilisés.
Les sources modifiées avant commit sont identifiées par leurs empreintes.
Le manifeste est propre à son composant ; `maintenance/deployment_manifest.py`
relie les livrables et les résultats de validation, puis vérifie leurs empreintes.
La [référence d’architecture](ARCHITECTURE-ACTUELLE.md) décrit les données, versions
et compatibilités courantes.

## Préparer le poste

1. Extraire le dépôt sur Windows, avec Git, PowerShell 7 ou Windows PowerShell 5.1,
   Node.js ≥ 20 et Chrome. Le moteur de production Flash-Next est Strata officiel
   **0.1.45.3**, sous `dependances/strata-0.1.45.3/engine-cuda12`, avec le serveur
   Python corrigé conservé sous `dependances/strata-0.1.43.1/source` : suivre
   [sa configuration de production](maintenance/2026-10-19-strata-0.1.45.3/README.md).
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

L’intégration de l’assistant ajoute des ressources de détection locale épinglées
(sherpa-onnx 1.13.8, modèle int8, AAR Android) : exécuter
`maintenance/2026-10-25-assistant-integration/prepare_wakeword.py --download` avec
le Python du projet si elles sont absentes. Les deux scripts de build vérifient
leurs empreintes sans téléchargement implicite. Le modèle reste expérimental
pour la phrase française ; voir le [rapport et ses limites](maintenance/2026-10-25-assistant-integration/README.md).

## Exécuter les vérifications

Les cinq runtimes applicatifs et le constructeur Windows disposent de six
[verrous avec empreintes](dependances/verrous/README.md). Vérifier leur conformité
avec `maintenance/verrous_runtime.py check`. Reconstruire dans des environnements
neufs à partir des verrous ; ne pas modifier le runtime personnel Hermes. Kiara
sélectionne son runtime privé validé par le pointeur
`toolchain/hermes-security-runtime/runtime.json`, préparé avec le script et le
patch de `maintenance/2026-10-21-correctifs-audit/`.

Le point d’entrée complet, depuis la racine, est :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/verify_project.py
```

Il agrège les échecs et produit `validation.json` dans un répertoire d’exécution
sous `toolchain/test-results`. `--output` permet un emplacement explicite et
`--checks` un sous-ensemble. Les vérifications OSV et Go consultent les avis publics.
Les captures UI restent dans ce répertoire et ne remplacent aucune preuve historique.

Les commandes individuelles restent disponibles :

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
