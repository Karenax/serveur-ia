# Reconstruire et vérifier Fred

Les constructions Windows/serveur 3.5.30 et Android 1.0.11/code 12 utilisent les
sources locales et les clés de signature existantes. Chaque construction produit
`build-manifest.json` : empreintes des sources, empreinte du binaire, versions des
paquets Python, Go, CMake, JDK, SDK/NDK Android et commit Hermes réellement utilisés.
Les sources modifiées avant commit sont identifiées par leurs empreintes.

## Préparer le poste

1. Extraire le dépôt sur Windows, avec Git, PowerShell 7 ou Windows PowerShell 5.1,
   Node.js ≥ 20 et Chrome. Le moteur de production Flash-Next est Strata officiel
   **0.1.43.1**, avec sa source serveur, sous `dependances/strata-0.1.43.1` : suivre
   [sa configuration de production](maintenance/2026-10-13-strata-0.1.43.1/README.md).
   [dependances/moteurs.json](dependances/moteurs.json) conserve les références des
   dépôts historiques et de leurs patchs, décrites dans
   [dependances/README.md](dependances/README.md).
2. Préparer Python 3.12 dans `Strata-src/.venv`, puis installer les versions épinglées
   de `lanceur/requirements.txt` et `client-qwen/requirements-build.txt`. Les
   modèles GPU, CUDA, compilateur et dépendances propres à Strata se préparent
   suivant le moteur épinglé ; leurs poids restent hors Git.
3. Installer Hermes avec son runtime Windows. Le commit utilisé par une livraison
   figure dans son manifeste et se vérifie avec `hermes_service.installation()`.
   Fred réutilise ce runtime ; il ne télécharge pas de dépendances pendant une conversation.
4. Préparer les dépendances vocales selon [client-voice/README.md](client-voice/README.md)
   et [CONVERSATION-WINDOWS.md](client-voice/CONVERSATION-WINDOWS.md). Le build utilise
   Whisper.cpp 1.9.5, CMake 3.31.8, Ninja 1.12.1 et MSVC sous `toolchain` ; les
   dépendances du worker sont épinglées dans `client-voice/requirements-conversation.txt`.
5. Pour Android, disposer du SDK 36, build-tools 36.0.0, NDK 27.3.13750724,
   Gradle 8.13 et JDK 21 aux emplacements définis par
   `client-qwen/android-outils/Environnement-Android.ps1`. Lancer
   `Verifier-Android.ps1` pour vérifier ces outils avant compilation.
6. Installer Go pour le bridge et conserver les caches des modules vérifiés par
   `go.mod/go.sum`. Conserver les clés privées dans leurs dossiers exclus de Git :
   une nouvelle clé empêcherait les mises à jour des clients déjà installés.

Les emplacements sont explicités par les scripts et les manifestes. Un checkout
seul ne contient pas les SDK, moteurs, modèles et clés privées. Le manifeste décrit
la construction réalisée ; il ne promet pas un binaire bit à bit identique sur un
autre poste ou avec une autre clé.

## Exécuter les vérifications

Depuis la racine du projet :

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
& '.\client-qwen\Build-WireGuard.ps1'
& '.\client-qwen\Build-Client.ps1' -DistributionDirectory "$PWD\toolchain\releases-staging\windows" -SkipManifest
& '.\client-android\Build-Android.ps1' -OutputDirectory "$PWD\toolchain\releases-staging\android"
```

Vérifier les manifestes, les ressources incluses et les tests des exécutables avant
de remplacer les dossiers `dist`. Le serveur doit disposer d’une sauvegarde chiffrée
vérifiée. Le manifeste Windows est signé avec `lanceur/releases.py` et les EXE
personnels sont reconditionnés avec `client-qwen/Mettre-A-Jour-Clients.py`, en
préservant leurs profils et clés. Conserver les distributions précédentes pour
le retour. La preuve de chaque mise en service doit confirmer les empreintes des
données et des clés, les processus Qwen et la programmation des sauvegardes.
