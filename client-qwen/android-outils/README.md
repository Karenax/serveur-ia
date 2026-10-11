# Outils Android du client Fred

Installation locale du 10 octobre 2026 dans `D:\Serveur IA\toolchain`.
Le raccourci **Android Studio - client Fred** est disponible sur le bureau.

| Outil | Version / emplacement |
| --- | --- |
| Android Studio | 2026.2.1.8, `toolchain/android-studio` |
| Java pour Gradle | Microsoft OpenJDK 21.0.12.1, `toolchain/android-jdk` |
| Gradle | 8.13, `toolchain/gradle-8.13` |
| SDK Android | API 36 (Android 16), `toolchain/android-sdk` |
| Outils de compilation | 36.0.0 |
| ADB / Platform Tools | 37.0.1 |
| Command Line Tools | 22.0 |
| Android Emulator | 37.2.12 |
| NDK | 27.3.13750724 |
| CMake Android | 3.22.1 |
| Go existant pour WireGuard | 1.27.1, `client-qwen/wireguard-tools/go` |

Les téléchargements Android Studio, Command Line Tools, Java et Gradle ont été
vérifiés par SHA-256 auprès de leur distribution officielle. Les autres paquets
sont installés par le gestionnaire du SDK Google. Les outils, caches Gradle,
réglages Android Studio et appareils virtuels sont conservés sur D:.

## Commandes

Depuis la racine du projet, dans PowerShell :

```powershell
. .\client-qwen\android-outils\Environnement-Android.ps1
.\client-qwen\android-outils\Verifier-Android.ps1
.\client-qwen\android-outils\Ouvrir-Android-Studio.ps1
```

Les variables et chemins des outils ont aussi été ajoutés à l'environnement
utilisateur. Une nouvelle session Windows les reprend ; le script d'environnement
les rend disponibles immédiatement dans un terminal déjà ouvert.
Dans Android Studio, utiliser le SDK `D:\Serveur IA\toolchain\android-sdk`
et sélectionner le JDK 21 dans les réglages Gradle du futur projet.
Android Studio utilise son propre JBR 25 pour l'éditeur.

Deux profils utilisent la même image Android 16 Google APIs x86_64 :

- `Fred_Telephone_API36` : Pixel 9.
- `Fred_Tablette_API36` : Pixel Tablet.

```powershell
.\client-qwen\android-outils\Lancer-Emulateur.ps1 -Appareil telephone
.\client-qwen\android-outils\Lancer-Emulateur.ps1 -Appareil tablette
adb devices
```

## Accélération de l'émulateur

La **Plateforme de l'hyperviseur Windows** a été activée par l'utilisateur.
Après redémarrage, le contrôle du 10 octobre 2026 confirme
`WHPX(10.0.19045) is installed and usable`, code 0, et un hyperviseur Windows actif.
L'accélération matérielle Android est disponible.

Pour une réinstallation sur un poste où cette fonction est désactivée, commande
à exécuter dans un PowerShell administrateur, puis redémarrer Windows :

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -All -NoRestart
```

Après un redémarrage, relancer `Verifier-Android.ps1`. Le paramètre
`-SansAcceleration` de `Lancer-Emulateur.ps1` permet de demander l'émulation
logicielle, nettement plus lente. Le démarrage des appareils virtuels n'a pas été
validé. La compilation et les tests sur un téléphone ou une tablette USB ne
dépendent pas de cet hyperviseur.

## Vérifications effectuées

- Compilation Gradle avec Android Gradle Plugin 8.13.2 : `BUILD SUCCESSFUL`.
- APK de contrôle : `toolchain/android-smoke/app/build/outputs/apk/debug/app-debug.apk`.
- Signature APK v2 vérifiée par `apksigner` ; cible API 36, minimum API 26.
- Compilation NDK d'une bibliothèque Android ARM64 ELF64, avec alignement 16 Ko.
- Exécution des outils Java, Gradle, ADB, Clang et CMake.
- Hyperviseur WHPX disponible après activation Windows et redémarrage.

Le projet de contrôle sert uniquement à vérifier l'installation. Il ne contient
ni profil personnel, ni clé d'accès, ni connexion au serveur Fred.
Les sources de contrôle et binaires restent dans `toolchain`, exclu de Git.

## Travail restant pour l'application

Ces installations préparent le développement Android. Le client Fred n'a pas
encore été porté ni publié sous forme d'APK. Son HTML/CSS/JavaScript peut servir
de base, mais le serveur local Python, Windows DPAPI, WebView2, le moteur
WireGuard Windows et les mises à jour EXE doivent être adaptés. Le stockage
Android, les accès personnels et le comportement téléphone/tablette devront
être implémentés puis testés dans le véritable client.

Sources des outils : [Android Studio](https://developer.android.com/studio),
[gestionnaire du SDK](https://developer.android.com/tools/sdkmanager),
[Microsoft OpenJDK](https://learn.microsoft.com/java/openjdk/download),
[Gradle 8.13](https://docs.gradle.org/8.13/release-notes.html).
