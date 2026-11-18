# Kiara pour Linux — client vocal

Cible : PC Ubuntu 24.04 / Debian 13, processeur x86_64,
session graphique et Python 3.12 ou 3.13. Le constructeur peut aussi produire un
paquet ARM64 ; cette cible n’a pas été validée sur un appareil.

Le chat, les modèles disponibles, les projets, les documents, le correcteur,
les images jointes, l’historique synchronisé et l’API locale reprennent les
sources du client de bureau. WireGuard est intégré, sans configuration réseau
système ni droits administrateur. L’accès HTTPS existant est conservé.

La dictée et la conversation vocale utilisent le microphone Linux via
PipeWire/PulseAudio. Low reconnaît le français sur le PC avec Parakeet v3 et
lit la voix française du serveur. Max peut utiliser le serveur Kiara pour la
reconnaissance et la synthèse avancées ; le complément Max local Windows n’est
pas installé sur Linux. Le mot d’appel expérimental « Bonjour Kiara » est inclus.

Sous Linux, le microphone se ferme pendant la réponse de Kiara puis se rouvre
automatiquement. L’interruption par la parole est désactivée pour éviter que
Kiara ne retranscrive le son de ses haut-parleurs. Couper le micro ou raccrocher
ferme le processus de capture. Dans le vocal, « Choisir une capture » ouvre le
portail de capture du bureau Linux. Selon le bureau, celui-ci propose une zone,
une fenêtre ou capture directement l’écran entier. Kiara permet ensuite de
choisir localement une zone, à la souris ou par coordonnées. Vérifiez l’aperçu et retirez-le si nécessaire :
l’image n’est jointe qu’à la prochaine question. Le portail peut conserver une
copie locale de la capture. Si le portail est absent, joignez une image enregistrée.
Cette fonction nécessite `xdg-desktop-portal` et un backend de capture adapté au
bureau graphique ; elle peut ne pas être proposée par tous les environnements.
Les mises à jour sont manuelles :
les EXE Windows proposés par le serveur ne sont jamais installés sous Linux.

## Installer

Installer les prérequis système (Ubuntu 24.04) :

```sh
sudo apt install python3 python3-venv python3-tk gnome-keyring pulseaudio-utils gstreamer1.0-pulseaudio libegl1 libopengl0 libxcb-cursor0 libnss3 libasound2t64 libgtk-3-0 libwebkit2gtk-4.1-0
```

Télécharger **l’archive complète Tauri** du client Linux. Le paquet de recette
se nomme `Kiara-linux-amd64-4.0.9-tauri.tar.gz`.
Le dossier `client-linux` du dépôt contient les sources de l’installateur :
le copier seul ne permet pas d’installer l’application.

Depuis le dossier contenant l’archive téléchargée, extraire le paquet dans un
emplacement que vous conserverez, puis ouvrir son dossier :

```sh
tar -xzf Kiara-linux-amd64-4.0.9-tauri.tar.gz
cd Kiara-linux-amd64
python3 installer.py
./start-tauri.sh
```

Le raccourci `./start.sh` ouvre aussi le client Tauri. Le profil, le trousseau
et les données locales restent séparés du dossier d’installation. Si des
données d’une ancienne interface sont détectées, la récupération expérimentale
s’arrête et les conserve ; elle ne les migre pas automatiquement.

Le client Tauri empêche l’ouverture simultanée du même profil Linux, avant le
chargement de ses données. Fermez les anciennes versions avant de le lancer.
Si un brouillon local ou un audio en attente semble absent
après relance, ne pas le remplacer : un changement de port du relais peut le
masquer. Conserver le profil et les anciennes versions en attendant une
procédure de récupération vérifiée.

Le candidat vérifie les origines Tauri avant de choisir le port d'un profil
existant. Il s'arrête sans modifier les données si plusieurs origines sont
utilisées ou si la vérification échoue ; leur fusion reste à qualifier.

Le fichier `build-manifest.json` et les dossiers `client` et `shared` doivent
être présents à côté de `installer.py`. Si le manifeste est absent, reprendre
l’extraction de l’archive complète ; ne pas créer un manifeste vide.

L’installateur télécharge les bibliothèques Python de reconnaissance depuis PyPI, crée un
environnement isolé dans le dossier extrait et ajoute Kiara au menu des
applications de votre session. Il ne demande pas sudo. Un bureau avec service
Secret Service et trousseau déverrouillé est nécessaire (GNOME Keyring ou service
compatible). Le paquet Tauri utilise WebKitGTK et requiert ses bibliothèques système.
Ne pas désactiver le bac à sable
du moteur web pour lancer l’application.

Pour enregistrer une réunion dans le portail Tauri, accepter la demande d’accès
au microphone. Lorsque WebKitGTK ne propose pas WebM, Kiara utilise des fragments
WAV PCM pour conserver l’audio. Le paquet GStreamer ci-dessus permet l’accès à
PulseAudio ; sa présence ne remplace pas la vérification du microphone sur le poste.
Pour enregistrer aussi le son du PC, sélectionner l’option correspondante et
autoriser les deux sources audio. Kiara enregistre le microphone et tous les sons
de la sortie par défaut au démarrage sur deux pistes distinctes. Si la sortie
change, arrêter la capture puis démarrer une nouvelle séance. La boucle est
retirée à la fin de la capture ; le périphérique de sortie par défaut ne change
pas. Cette fonction exige `pactl` et un serveur PulseAudio ou compatible qui
accepte les sources de boucle. Vérifiez son fonctionnement sur votre poste.

Les bibliothèques natives sont installées depuis leurs paquets binaires.

Au premier lancement, choisir le client personnel `.exe` fourni par
l’administrateur. Il est lu sans être exécuté ; seul son accès est importé et
enregistré chiffré. Aucun Wine ni WebView2 n’est nécessaire. Demander un accès
distinct pour chaque appareil utilisé simultanément ; importer le même fichier
sur deux appareils peut interrompre leurs connexions WireGuard.

## Utiliser le vocal

Choisir le microphone et la sortie audio dans les réglages Linux. La session
graphique doit disposer de PipeWire avec `pipewire-pulse` (standard sur Ubuntu
24.04) ou de PulseAudio. Pour le son du PC en réunion, Kiara crée une source de
boucle temporaire dans la session audio sans changer la sortie par défaut.

Ouvrir **Vocal**, garder **Low**, puis cliquer **Installer le vocal** : environ
680 Mo de modèles publics sont téléchargés une seule fois et vérifiés par leurs
empreintes. Cliquer ensuite **Démarrer la conversation**. Parler, attendre la
réponse lue, puis parler de nouveau. Les boutons **Couper le micro** et
**Raccrocher** restent disponibles. Les modèles de dictée et du vocal sont partagés.

Pour **Max**, choisir cette qualité dans les réglages du vocal : le traitement
est fixé au **Serveur Kiara**. Le serveur doit avoir Max disponible. Si les modèles
Low ne sont pas installés, environ 9,3 Mo d’outils de détection de parole suffisent
sur le PC. Dans ce mode, le son du micro est transmis au serveur par l’accès
authentifié existant. En Low et en dictée, l’audio reconnu reste sur le PC ;
seul le texte est envoyé lors de la conversation ou de l’envoi du message.

Les données sont conservées dans `${XDG_DATA_HOME:-~/.local/share}/kiara`,
chiffrées avec une clé enregistrée dans le trousseau de la session. Sauvegarder
ce dossier **et le trousseau**. Une clé perdue n’est jamais remplacée quand des
données chiffrées existent. Les conversations synchronisées restent sur le serveur ;
l’import n’emporte pas les brouillons locaux du PC Windows.

Pour une mise à jour, fermer Kiara, extraire le nouveau paquet dans un autre
dossier puis relancer son installateur. Le raccourci pointera vers cette version ;
les données personnelles sont conservées séparément. Conserver l’ancien dossier
pour revenir à la version précédente. Pour désinstaller, supprimer le raccourci
`~/.local/share/applications/kiara.desktop` et le dossier de l’application ;
ne supprimer les données personnelles qu’après sauvegarde.

## Construire et vérifier

Depuis la racine du dépôt, avec le Python de construction :

```powershell
& '.\toolchain\build-python\Scripts\python.exe' maintenance/package_linux_client.py --tauri-binary '<binaire-Linux>' --tauri-version '<version>'
```

Le constructeur utilise le Go épinglé de `wireguard-toolchain.json`, vérifie les
modules et compile le bridge pour Linux avec CGO désactivé. `--architecture arm64`
sélectionne ARM64. `--output` choisit un dossier de livraison distinct.
Les fichiers sont sélectionnés explicitement : aucun profil, token, historique,
clé ou fichier de production n’entre dans le paquet. Seul le petit modèle public
du mot d’appel est inclus ; les modèles Parakeet restent téléchargeables depuis
le client. Le manifeste donne
la version et les empreintes SHA-256 des fichiers. Il permet de repérer une
altération, mais ne remplace pas une signature de publication.

Sur Linux, après installation :

```sh
./start.sh --self-test
./start.sh --audio-self-test
```

Le premier contrôle vérifie le chiffrement via le vrai trousseau, les ressources
et le bridge natif, sans contacter le serveur. Le second ouvre le microphone,
reçoit une seconde de PCM puis le ferme, sans enregistrer ni envoyer d’audio.
Après installation des modèles, `./start.sh --conversation-self-test --self-test`
teste aussi l’ouverture, la coupure et la réouverture du micro avec la reconnaissance.
Tester ensuite la fenêtre, le clavier,
une connexion avec un accès de test, un échange, une pièce jointe, les projets,
la synchronisation et la fermeture avec sauvegarde. La validation native Linux
reste nécessaire avant diffusion générale. Le paquet a été préparé depuis Windows ;
aucune validation graphique ou matérielle Linux n’est annoncée.

Référence : [trousseau Secret Service](https://keyring.readthedocs.io/en/stable/).
La capture utilise [parec de PulseAudio](https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/).
