# Client Windows Kiara 4

La version Windows publiée est indiquée par `DESKTOP_INSTALLER_VERSION` dans [le catalogue des versions](../lanceur/releases.py). Elle utilise le manifeste Ed25519 du canal
Kiara et un installateur sans Authenticode. [Publication et preuves](../audits/2026-11-16-architecture-interface/AVANCEMENT.md#publication-windows-et-portail-4012)

Dans le client classique 3.5.62, ouvrir **Mises à jour** et installer la
3.5.63. Dans cette dernière, cliquer sur **Passer à Kiara 4**. Le client
vérifie l’installateur, l’exécute pour le compte Windows courant et ouvre
Kiara 4 avec l’accès existant. Le relais conserve le profil chiffré par
DPAPI et retrouve les réglages, l’historique et les brouillons de l’appareil.

Dans Kiara sur Windows, ouvrir **Réglages → Mises à jour**. En 4.0.10,
le raccourci du portail ouvre les réglages de l’appareil. Y choisir l’onglet
**Mises à jour**. Une fois sur Kiara 4.0.2 ou ultérieure, choisir
**Vérifier les mises à jour** et **Mettre à jour le client**. Kiara vérifie le
paquet du serveur, enregistre les changements en cours et redémarre après
l’installation pour le compte Windows courant. Une 4.0.0 ou 4.0.1 déjà installée
doit recevoir ce premier paquet via le téléchargement ci-dessous.

Pour une installation manuelle, ouvrir **Clients & accès** dans la console Kiara et
choisir **Télécharger Kiara 4 pour Windows**. Au premier lancement,
coller le code fourni depuis **Clients & accès** dans la console serveur.
Le même installateur convient à tous les utilisateurs.

Le candidat Windows de recette verrouille le profil avant l’ouverture des
données. Il détecte aussi une ancienne fenêtre WebView2 déjà ouverte avec le
même profil. Fermer les anciennes versions avant de lancer Kiara : elles ne
participent pas au nouveau verrou et peuvent encore démarrer après sa vérification.
Le client et son relais doivent provenir du même installateur.

Les brouillons de réunion et fragments audio locaux du portail dépendent aussi
du port du relais local. Dans le candidat, Kiara vérifie les origines Tauri et
enregistre le port lorsqu'une seule contient des données. Si plusieurs origines
contiennent des données ou si une origine ne peut pas être vérifiée, le démarrage
s'arrête sans les effacer ; leur fusion automatique reste à qualifier. Conserver
les données et éviter de remplacer un brouillon qui semble absent.
Sous Linux, le paquet de recette utilise uniquement Tauri. Le verrou protège
le profil contre une autre instance Tauri ; fermer les anciennes versions,
qui ne prennent pas nécessairement ce verrou. Tauri et son relais doivent
provenir du même paquet complet.

La navigation de la fenêtre est limitée à l’origine locale fournie au démarrage.
Sous Linux, seule la commande native de zoom est exposée au contenu de cette
origine et à la fenêtre Kiara ; Windows utilise le zoom natif de WebView2.
Pour agrandir ou réduire le contenu, utiliser Ctrl avec + ou - ; Ctrl + 0
rétablit la taille normale. Les incréments dépendent du système.
Les caches Cargo et npm, les fichiers temporaires et les résultats de compilation
vont dans `toolchain/tauri-work` sur le disque de travail. `-WorkRoot` permet de
choisir un autre dossier de travail. Par défaut, `-ToolsRoot` pointe vers
`toolchain` dans le dépôt. Pour fournir une autre installation de MSVC et Rust,
indiquez le dossier d’outils du disque de travail.
Sur ce poste, Cargo et Rust 1.99.0 sont sous `toolchain/Rust/cargo/bin` et Tauri CLI
2.12.2 sous `toolchain/TauriCLI-2.12.2`. Le script met aussi le cache des outils NSIS
dans le répertoire de compilation. [Configuration du cache Tauri](https://v2.tauri.app/reference/config/#uselocaltoolsdir)

Depuis la racine du dépôt actif :

```powershell
. .\maintenance\tauri-dev-env.ps1
cargo test -j 2 --locked --manifest-path .\client-tauri\Cargo.toml
cargo build -j 2 --locked --manifest-path .\client-tauri\Cargo.toml
```

Le binaire de recette se trouve sous `toolchain/tauri-work/Build/tauri-prototype`.
Compiler le pont WireGuard et le relais avec les ressources vocales Windows déjà
préparées. Placer le prototype compilé à côté de `kiara-relay.exe`.

```powershell
$dist = 'D:\Kiara\integration-agent\relais-tauri'
New-Item -ItemType Directory -Path $dist -Force | Out-Null
$bridge = Join-Path $dist 'wireguard-bridge.exe'
.\client-qwen\Build-WireGuard.ps1 -OutputBinary $bridge
.\client-qwen\Build-Client.ps1 -Relay -SkipManifest -DistributionDirectory $dist -WireGuardBinary $bridge
Copy-Item -LiteralPath (Join-Path $env:CARGO_TARGET_DIR 'debug\kiara-tauri-prototype.exe') -Destination $dist
& (Join-Path $dist 'kiara-tauri-prototype.exe') --profile-exe 'D:\Kiara\integration-agent\profil-de-recette.exe'
```

Le mode `--local-url http://127.0.0.1:PORT/chat` utilise un serveur de recette
démarré séparément. L’option `--hidden` masque la fenêtre pour l’automatisation.
L’option `--profile-exe` permet de choisir le fichier sans ouvrir la boîte de
sélection. En mode avec relais, la fenêtre attend la sauvegarde des conversations
et des brouillons avant de l’arrêter. Si l’enregistrement échoue ou si Kiara
signale des modifications en attente, Kiara demande de confirmer la fermeture.
Les fonctions natives et la distribution signée restent à qualifier.

Pour ouvrir les liens réseau et les preuves de jalon dans l’Explorateur,
définir `AGENT_OPEN_ROOTS` dans l’environnement de l’utilisateur Windows, avec
les chemins absolus des dossiers autorisés, séparés par `;`. Le relais vérifie
l’accès au projet et limite l’ouverture à ces dossiers et aux types de
documents pris en charge.

## Installateur de recette

Le script assemble un installateur NSIS en français pour le compte Windows
courant. Il prend le relais compilé par `Build-Client.ps1` et utilise Tauri CLI
2.12.2. L’installateur se trouve sous
`toolchain/tauri-work/Build/tauri-prototype/x86_64-pc-windows-msvc/debug/bundle/nsis`
dans le dépôt sur D: avec les paramètres par défaut.

```powershell
.\client-tauri\Build-Installer.ps1 `
  -Relay (Join-Path $dist 'kiara-relay.exe') `
  -TauriCli '.\toolchain\TauriCLI-2.12.2\cargo-tauri.exe'
```

Pour construire un candidat en mode release, fournir `-Version` et
`-AgentCapture`. Le paquet utilise le nom **Kiara** et l’identifiant
`fr.kiara.desktop`, comme le client installé. Exemple avec un relais et un
composant WASAPI déjà compilés, depuis une copie de recette du dépôt :

```powershell
.\client-tauri\Build-Installer.ps1 `
  -Version 4.0.12 `
  -Relay (Join-Path $dist 'kiara-relay.exe') `
  -AgentCapture (Join-Path $captureDist 'kiara-agent-capture.exe') `
  -TauriCli (Join-Path $tools 'TauriCLI-2.12.2\cargo-tauri.exe') `
  -ToolsRoot $tools -WorkRoot $work
```

`$dist` et `$captureDist` désignent les dossiers des deux exécutables, `$tools`
le dossier `toolchain` du dépôt principal et `$work` un dossier de construction
de recette sur D:. Pour tester la mise à jour
de la 4.0.11 vers la 4.0.12, utiliser un environnement Windows isolé avec son
propre compte et un profil fictif. Le contrôle des exécutables extraits avec DPAPI natif
et les essais d’installateurs sous Wine sont consignés dans le
[suivi de l’audit](../audits/2026-11-16-architecture-interface/AVANCEMENT.md).

Pour signer le candidat avec Authenticode, fournir `-SigningTool`
avec le chemin de l’outil de signature, `-SigningArguments` avec ses arguments
et `-SignerThumbprint` avec l’empreinte du certificat de l’éditeur.
Le script ajoute le chemin de chaque binaire en dernier argument. Configurer les
identifiants du service de signature hors des arguments, car Tauri écrit la
configuration de construction sur disque. Le script vérifie la signature
Authenticode du relais, du helper, de l’application et du paquet NSIS, puis
affiche le SHA-256 du paquet. L’installateur `Kiara_<version>_x64-setup.exe` se trouve sous
`toolchain/tauri-work/Build/tauri-prototype/x86_64-pc-windows-msvc/release/bundle/nsis`
dans le dépôt sur D: avec les paramètres par défaut.

## Helper WASAPI

Compiler le composant de capture avec un environnement Windows Python 3.13 qui contient
PyInstaller 6.22.3 et les versions de PyAV, NumPy et PyAudioWPatch verrouillées
dans `agent/requirements-audio.txt`. Le script vérifie que le binaire peut
inventorier les périphériques WASAPI. Passer le binaire à `Build-Installer.ps1`
avec `-AgentCapture` pour le livrer aux côtés du relais. Dans l’exemple, `$PythonAudio`
désigne le chemin de l’interpréteur de cet environnement sur D:.

```powershell
.\client-tauri\Build-AgentCapture.ps1 `
  -Python $PythonAudio `
  -OutputDirectory 'D:\Kiara\integration-agent\wasapi'
```

Pour la recette de transfert, après avoir fermé Tauri, le relais peut renvoyer
les fragments journalisés d’une séance existante avec
`kiara-relay.exe --sync-agent-capture <UUID-séance> <dossier-des-fragments>`.
Cette commande utilise le profil Kiara importé sous le compte Windows courant.
Elle conserve les fichiers locaux et vérifie chaque reçu du serveur. Dans Kiara,
les commandes de la séance pilotent la capture Windows. Si la connexion se coupe
pendant l’arrêt, le relais reprend le transfert des fragments dès qu’il peut joindre
le serveur, y compris après un redémarrage de Kiara.
