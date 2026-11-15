# Reprise de l’intégration Agent — 13 novembre 2026

Le [plan d’intégration à jour](2026-11-12-plan-integration-agent.md) rassemble l’état courant. Ce journal retrace les étapes de reprise.

Les sources de Kiara restent dans `D:\Serveur IA`. La recette et ses journaux sont dans `D:\Kiara\integration-agent`. Le compte Windows Fred dispose maintenant du droit Modification avec héritage sur ces deux dossiers. Les environnements Python et les outils déjà installés dans `E:\Kiara-Integration` restent utilisables depuis les sources sur D:.

## Récupération

- `agent/app/services/backup.py` et `agent/tests/test_project_note_backup.py` étaient intégralement remplis d’octets nuls. Ils ont été remis en place depuis le commit Agent `0c2e08a`, base de l’import dans Kiara. Les deux caches compilés retrouvés étaient eux aussi corrompus. La révision locale exacte du 12 novembre n’est donc pas attestée ; l’inventaire des 16 tests de sauvegarde des notes correspond à celui de la recette du 12 novembre.
- Au début de la reprise, le plan du 12 novembre était illisible. Le [plan à jour](2026-11-12-plan-integration-agent.md) a été reconstitué à partir de l’[analyse du 11 novembre](2026-11-11-integration-agent.md) et des recettes.

## Vérification sur D:

Les journaux sont dans `D:\Kiara\integration-agent\verification-kiara\reprise-20261113`.

| Contrôle | Résultat |
| --- | --- |
| Sauvegarde et restauration Agent | 78 tests réussis |
| Passerelle, droits et service Agent dans Kiara | 17 tests réussis |
| Outils de restauration | 3 tests réussis |
| PDF multimodal | 5 tests réussis |
| Client Windows | 107 tests réussis |
| Suite backend Agent | 2 998 tests détectés sans erreur de chargement ; exécution intégrale non relancée |

La recette précédente a validé le parcours **Conversations → Agent → Conversations** dans Tauri via WireGuard. La qualification globale du lanceur reste à terminer. Son dernier journal complet après réinstallation signalait des échecs liés aux anciens chemins, au runtime Hermes et au client Windows installé. La configuration et les données de production n’ont pas été changées pendant cette reprise.

## Relais Windows lancé par Tauri

La recette Windows a validé le démarrage de `kiara-relay.exe` par Tauri avec un profil fictif au format des EXE Kiara, puis le parcours **Conversations → Agent → Conversations** via WireGuard. La navigation vers une autre origine locale a été refusée et le port du relais a cessé de répondre à la fermeture de la fenêtre. Le client Windows a passé ses 107 tests et le relais compilé a passé le contrôle natif, qui initialise désormais TLS.

Le prototype lit un profil fourni explicitement et utilise les réglages locaux existants du profil. L’installateur signé, la mise à niveau depuis le client déployé et les fonctions natives restent à qualifier. La recette a utilisé uniquement des données fictives.

La fermeture de Conversations a été testée avec un historique de plus de 64 Kio et un brouillon saisi juste avant de fermer. Tauri a attendu la réponse du relais, puis l’historique et le brouillon ont été relus dans les fichiers locaux chiffrés. La recette Agent a observé le signal de modifications en attente. Le parcours d’annulation dans la boîte de dialogue reste à confirmer.

## Reprise du profil Windows

La recette `tauri-profil-smoke.log` a importé un profil fictif au format historique et vérifié son stockage DPAPI. Après déplacement du fichier source, Tauri a démarré sans argument, retrouvé le brouillon et la donnée témoin WebView, puis ouvert Agent via WireGuard. La recette a utilisé l’option `--profile-exe` pour le premier lancement. La boîte de sélection interactive et la mise à niveau via installateur restent à qualifier.

## Installateur Windows de recette

`client-tauri/Build-Installer.ps1` assemble l’installateur NSIS x64 par utilisateur avec le relais Kiara. `tauri-installateur-verification-v2.log` confirme l’installation dans un dossier de recette, l’empreinte du relais, la navigation Agent via WireGuard, la conservation des données chiffrées après réinstallation et la désinstallation. Le paquet de recette est non signé. La réinstallation portait sur le même paquet, avec import d’un profil fictif au format historique. La mise à niveau depuis le client 3.5.62 déployé, la sélection interactive et la distribution signée restent à qualifier.

## Ouverture des liens de projet sur Windows

Le relais ouvre les dossiers et documents des liens réseau et des preuves de jalon sur le poste Windows. Le poste configure ses racines via `AGENT_OPEN_ROOTS`. La recette `agent-chemins-wireguard.log` vérifie l’accès au projet par WireGuard et le refus après retrait de cet accès. La suite complète du frontend Agent a passé 1 025 tests.

`agent-chemins-nsis-verification.log` confirme l’ouverture d’un dossier fictif en chemin UNC dans l’Explorateur Windows depuis l’onglet **Fichiers et dossiers** du client Tauri installé. La recette utilise SMB sur le même poste et vérifie le chemin de la fenêtre ouverte. Elle se termine par la fermeture du relais et la désinstallation du client. Les partages métier et leurs droits sur un deuxième poste restent à qualifier.

## Liaison Thunderbird

Le XPI de recette utilise une clé locale dédiée et le relais Windows. La passerelle réserve les opérations de l’extension à un appareil Kiara désigné, propriétaire sans restriction de projets. La recette initiale via WireGuard a testé les commandes de synchronisation et de brouillon, puis le refus après retrait des droits.

`tauri-thunderbird-real.log` confirme l’installation du XPI par politique dans une instance isolée de Thunderbird 153.7 ESR et son appairage avec `kiara-relay.exe`. Thunderbird a traité la commande Agent via WireGuard. Le test a vérifié le statut final et le contenu du brouillon dans le dossier local `Drafts`.

`tauri-thunderbird-import-v5.log` confirme le transfert d’un mail fictif depuis le dossier Thunderbird sélectionné. La pièce jointe a été relue dans l’EML stocké par Agent et comparée à l’original. Le mail du dossier exclu est resté dans Thunderbird. Une deuxième synchronisation a ignoré le mail déjà transféré. La recette a utilisé des dossiers locaux et un module de test distinct pour y préparer les messages. Les six tests serveur Thunderbird passent. Une boîte métier et la distribution de l’extension restent à qualifier.

## Accès web privé

Le lanceur active l’accès web lorsque `KIARA_AGENT_WEB_ORIGIN` définit son origine HTTPS. `KIARA_AGENT_WEB_PORT` fixe le port local, 8767 par défaut. Le proxy HTTPS de cette origine doit conserver l’en-tête `Host` et transmettre les requêtes au port d’écoute `127.0.0.1`. La session web est liée à l’accès Kiara et à son empreinte, expire après huit heures et peut être fermée depuis la page d’accueil de l’origine. Les écritures exigent l’origine HTTPS configurée. Les 22 tests ciblés du lanceur passent.

`agent-web-https.log` confirme la recette Chrome avec un véritable service Agent, deux accès fictifs et un certificat local autosigné. Le propriétaire voit les deux projets et peut en créer un. Le lecteur ne voit que son projet et sa tentative d’écriture est refusée. La déconnexion invalide la session et le navigateur ne peut pas prendre de commande dans la file Thunderbird. Le proxy et le certificat de production restent à qualifier.

## Helper WASAPI Windows

`client-tauri/Build-AgentCapture.ps1` compile le helper Agent avec PyAV, NumPy et PyAudioWPatch. `Build-Installer.ps1 -AgentCapture` l’installe aux côtés de Tauri et du relais. La recette a installé le paquet NSIS, comparé les empreintes, lancé le helper installé, capté un son de test sur la sortie système et vérifié le fragment Ogg/Opus et son empreinte. La désinstallation a abouti et les 44 tests audio ciblés passent. Le pilotage depuis une réunion Agent, le transfert des fragments et les essais microphone restent à qualifier.

`agent-wasapi-transfer.log` valide le transfert depuis le relais Windows recompilé. Le helper a enregistré un son de test pour une séance Agent fictive. Le relais a transmis le fragment via WireGuard et contrôlé le reçu, puis a rejoué l’envoi sans créer de doublon. L’audio téléchargé depuis la séance a la même empreinte que le fragment local. Cette recette lance la capture et la synchronisation en ligne de commande. L’écran de réunion et la reprise automatique après coupure restent à raccorder.

Le relais Tauri peut maintenant piloter le helper depuis les commandes Windows de l’écran de réunion. Un essai du contrôleur a démarré, mis en pause et repris la capture de la sortie Windows. Après une panne de transport simulée, l’arrêt a fermé le helper et conservé les fragments sur le poste. Un nouveau contrôleur a relu le journal, transmis les fragments via WireGuard et finalisé la séance. Le téléchargement Ogg et le nombre de fragments côté serveur ont été vérifiés. La consolidation a utilisé le runtime audio indiqué par `KIARA_AGENT_SPEECH_PYTHON` au lanceur. Les deux suites frontend ciblées totalisent 162 tests réussis. Le parcours depuis Tauri recompilé, le microphone et la reprise automatique restent à qualifier.

`tauri-audio-ui-smoke.log` valide le parcours dans Tauri avec le relais Windows recompilé. Depuis Réunions, l’opérateur a démarré la capture de la sortie Windows, l’a mise en pause, reprise, puis arrêtée. Agent a conservé deux fragments via WireGuard et renvoyé le téléchargement Ogg consolidé. Le lancement du helper utilise son propre environnement PyInstaller et laisse à l’exécutable le temps de charger les bibliothèques audio. L’essai utilise une séance et un profil fictifs. Le microphone et la reprise automatique restent à qualifier.

`tauri-audio-reprise-smoke.log` valide l’arrêt depuis Réunions pendant une coupure réelle de la passerelle de recette. Après réouverture de la passerelle, le relais recompilé a transmis le fragment et finalisé la séance sans nouvelle commande. WebView2 a téléchargé l’audio Ogg et Tauri a fermé le relais. `agent-wasapi-reprise-automatique.log` valide aussi la persistance de la demande après remplacement du contrôleur pendant la coupure. Les deux recettes utilisent la sortie Windows. Le microphone et le retrait d’un périphérique restent à qualifier.

`tauri-microphone-helper-smoke.log` confirme la capture avec le microphone Logi C525 depuis Réunions. Démarrage, pause, reprise, arrêt, transfert des deux fragments via WireGuard et téléchargement Ogg ont abouti avec le helper recompilé. La perte d’un périphérique a été simulée dans la boucle WASAPI. Le test vérifie que le dernier fragment est transmis au journal même si la fermeture du flux échoue. Les 50 tests audio ciblés et 15 sous-tests passent. Le débranchement physique reste à vérifier.

`tauri-audio-nsis-verification.log` confirme l’installation neuve de `Kiara-Agent-audio-recette-x64.exe`, les empreintes du relais et du helper installés, le même parcours microphone depuis l’application installée et la désinstallation. Le paquet de recette est non signé.

## Migration du client Windows 3.5.62

L’empreinte de `client-qwen/dist/Accès serveur Fred.exe` concorde avec le manifeste 3.5.62. `tauri-migration-3562-nsis.log` confirme la reprise de l’historique, du brouillon, du thème sombre, d’une donnée témoin WebView et du profil chiffré DPAPI à partir de ce binaire personnalisé avec un accès fictif. Le client Tauri installé via NSIS a retrouvé l’identité de l’appareil et ouvert Agent via WireGuard. La recette a vérifié les écritures dans l’ancien client après rechargement, puis a arrêté ses processus de test avant de lancer Tauri avec `--profile-exe`. La boîte de sélection interactive, les packs vocaux hérités, la migration via le canal de mise à jour et le deuxième poste restent à qualifier.

`tauri-profile-dialog-nsis-v3.log` valide le premier lancement interactif après installation. L’annulation quitte Kiara sans enregistrer de profil. La sélection de l’EXE 3.5.62 fictif retrouve les données locales et ouvre Agent. Après déplacement de l’EXE source, Kiara redémarre avec le profil DPAPI et le même accès. La désinstallation du paquet de recette a abouti.

## WireGuard en recette locale

Le serveur et le client WireGuard des recettes écoutent sur `127.0.0.1`. Le mode `loopback_only` conserve cette écoute quand le serveur redémarre sur le même port. Utiliser le paquet `Kiara-Agent-recette-x64.exe` pour les recettes NSIS et le dossier `relais-tauri-download` pour les essais du relais compilé. Les recettes de migration et de sélection interactive écrivent l’historique, les préférences et le stockage WebView avec le client classique lancé depuis les sources. Le client classique lancé depuis les sources utilise le même pont local que le serveur de recette. Les recettes importent ensuite un profil de test au format historique. Le résultat de la migration réalisée avec le binaire 3.5.62 d’origine est archivé ci-dessus.

Le 14 novembre, le test de résilience du tunnel et la migration NSIS ont abouti sans nouvel événement de demande WireGuard (2097) dans le journal du pare-feu Windows.

Le pont de développement a été reconstruit sur `D:`. Les recettes de conversation et de mise à jour Android utilisent désormais ce pont. Le test de résilience vérifie les adresses UDP du serveur et du client dans un tunnel réel. Ce test, le téléchargement Android via le tunnel et le test EG2 via l’API locale Windows ont réussi.

## Téléchargements dans Kiara

Le relais Windows, WireGuard et la passerelle transmettent les en-têtes de téléchargement par plage jusqu’à Agent. `tauri-download-smoke.log` confirme le téléchargement d’un original fictif de 32 Mio dans WebView2 via WireGuard. L’empreinte SHA-256 correspond au fichier serveur. La plage de 8 Mio renvoie les octets attendus, une plage hors fichier renvoie 416 et un ancien ETag déclenche le téléchargement complet. L’essai vérifie les requêtes HTTP depuis WebView2.

## Construction du paquet Windows

`Build-Installer.ps1` accepte un outil de signature Authenticode et l’empreinte du certificat de l’éditeur. Le mode signé construit en release, signe les auxiliaires et demande à Tauri de signer l’application et le paquet. Le script vérifie les signatures avant de fournir le SHA-256 du paquet. Un outil de recette qui retourne un succès sans signer le relais a été rejeté. Les magasins Windows examinés ne contiennent aucun certificat de signature avec clé privée. Le parcours signé reste à valider avec l’outil et le certificat de livraison.

`Kiara-Agent-recette-x64.exe` regroupe les derniers correctifs de WireGuard et du téléchargement. `tauri-livraison-verification.log` confirme l’installation, les empreintes des auxiliaires, le téléchargement de 32 Mio et le transfert par plage depuis Agent, le retour à Conversations, la fermeture du relais et la désinstallation. Ce paquet de recette est non signé.

## Originaux CDC à récupérer

La recherche a couvert 129 118 fichiers locaux et les entrées de 179 ZIP dans les dossiers Kiara, Agent et les archives accessibles. Aucun fichier lisible ne correspondait aux tailles attendues de 2 238 044 et 6 234 776 octets. Des emplacements restent inaccessibles, dont `E:\Kiara-Integration\AgentData`, et quatre ZIP sont illisibles. Le dossier `.minipilot\cdc` de l’ancien poste reste la source à vérifier.

| Source | SHA-256 attendu | État de reprise |
| --- | --- | --- |
| `694184-STB-A3.pdf` (`4a0b3de6-1420-472f-bd2c-bc6929304f5b`) | `3f978ec9f59924c8bdbbc1bd0bbaf9e1e111bd60c448568c07b6953820f7f79a` | Original manquant, 35 pages enregistrées. |
| `CDC-671134-Allègement_des_planchers_règleurs-ind01.pdf` (`69c1c1ee-41fa-43d1-9997-44572a85e01e`) | `cbf53fb91b7ab4bcedff9e46601af72f38ae9d487fa889be313bbe855fc65779` | Original rétabli depuis une pièce jointe de l’archive mail. Les 35 pages et les 130 ancrages sont conservés. |
| `694184-STB-A3.pdf` (`45c6c8cd-089d-4a9d-a77d-d38af165ad06`) | Absente | Fiche historique sans empreinte ni chemin. Aucun rattachement automatique. |

Réimporter un original depuis la liste des documents CDC du projet. Si l’empreinte correspond et que le fichier géré manque, Agent rattache le fichier à la fiche existante. Le test API vérifie la conservation des pages, des éléments et de leurs preuves, le refus d’écraser un fichier différent et l’idempotence de la réimportation. Le décodage MIME des 1 198 mails restaurés a retrouvé un des PDF par SHA-256. Le journal `agent-cdc-original-retabli.log` confirme son rattachement à la fiche existante. L’original `694184-STB-A3.pdf` reste à retrouver.

La recherche a ensuite couvert 4 254 entrées dans 71 archives ZIP jointes aux mails, sans correspondance avec l’empreinte de `694184-STB-A3.pdf`. Le PDF joint `97100D57133414202-SO1-STB-A3.pdf` contient le même texte normalisé sur les 35 pages enregistrées. Il fait 2 237 621 octets au lieu des 2 238 044 attendus et son empreinte diffère. La fiche historique continue donc de référencer l’original attendu.

## Configuration serveur persistante

Le lanceur lit `agent-service.json` depuis `KIARA_DATA_DIR`. Une configuration erronée laisse le catalogue Agent indisponible et affiche la cause dans **Accès Agent**. `agent-configuration-persistante.log` confirme deux démarrages du service réel par deux instances successives du contrôleur, à partir du même fichier et de bases fictives. Le test vérifie aussi le diagnostic authentifié quand le chemin Python manque. Les 16 tests du lanceur, des accès administrateur et de la passerelle passent. Le fichier de production reste à établir sur le dossier de données retenu pour la bascule.

## Catalogue et index de la restauration

`agent-catalogue-index-bascule.log` confirme 11 projets ERP, 11 projets Brain et 10 liens dont les codes concordent. Chaque base conserve un projet autonome. Les 37 546 passages EG2 se rattachent à 1 148 sources résolues du bon projet. Les index EG2 et multimodal passent le contrôle SQLite. L’index EG2 conserve le profil de l’ancien relais. Aucun passage ne porte le profil de la passerelle Kiara. Les 4 997 entrées multimodales sont marquées obsolètes dans la restauration contrôlée.

La sauvegarde utilise désormais SQLite pour les index imbriqués sous `storage/eg2` et `storage/multimodal`. La restauration reloge le chemin EG2 sous son nouveau dossier de stockage. Le diagnostic de connexion signale un profil incompatible. Avant activation des recherches sur les données métier, reconstruire les index et vérifier les résultats sur le moteur cible. La restauration existante a été inspectée en lecture seule.

`agent-eg2-reconstruction.log` confirme la reconstruction de deux sources fictives par Agent via la passerelle Kiara avec EmbeddingGemma 2 réel sur CPU. La recherche a placé la preuve attendue en tête et le diagnostic a confirmé deux projections au profil courant. Une reconstruction en échec conserve désormais les passages incompatibles encore présents et laisse la date du dernier succès inchangée. Le test de reprise vérifie la suppression des anciens passages après succès pour le seul projet traité. Les 22 tests EG2 et diagnostics ciblés passent. La reconstruction des index métier et la qualification sur le GPU de production restent à effectuer.

`agent-multimodal-gateway.log` confirme cinq entrées fictives indexées par le moteur multimodal CPU via Kiara. Les quatre recherches texte, image et audio ont classé la source attendue en tête et l’original téléchargé via sa citation correspond octet pour octet au fichier indexé. Le propriétaire a pu reconstruire l’index, le lecteur a reçu un refus et la répétition a réutilisé les cinq entrées. Le lanceur configure désormais le runtime, le dossier du modèle et le dossier FFmpeg. Le rapport `multimodal-qualification.json` réside à côté du modèle vérifié. Les 38 tests ciblés multimodaux, PDF, lanceur et passerelle passent. Cette recette locale a utilisé HTTP sur `127.0.0.1`. La reconstruction multimodale des données métier reste à effectuer sur le stockage retenu pour la bascule.

La reconstruction métier a démarré dans la restauration privée existante `D:\Kiara\integration-agent\restauration-parcours-20261112`. Elle écrit l’index dérivé et lit les bases canoniques en lecture seule. Les empreintes des 1 147 originaux EML concordent avec les sources résolues. Le premier projet a fourni 23 passages et une citation au premier rang. Les 37 540 passages des dix autres projets ont été mis en file. Le quota global passe à 1 Gio pour accueillir cette génération. La recherche limite maintenant la lecture de l’index aux sources autorisées. Agent retrouve aussi l’index EG2 géré sous le dossier de stockage courant quand l’ancien chemin absolu a disparu. Les 28 tests ciblés passent. La console Kiara confirme que son moteur EG2 est prêt sur la Quadro P2200. Le journal `agent-multimodal-reconstruction.log` suit la reconstruction multimodale. La reconstruction EG2 du corpus avec ce moteur et la validation de la bascule restent à faire.

La reconstruction multimodale a repris le même travail avec réutilisation des vecteurs de texte à profil et texte identiques. La provenance reste attachée à chaque entrée. Les 12 tests multimodaux ciblés passent. `agent-eg2-metier.log` confirme une inférence de 768 dimensions sur la Quadro P2200 via la passerelle active et le démarrage de la reconstruction EG2 de 1 148 sources. Le processus Kiara est passé sur CPU après une saturation de mémoire CUDA. Le code essaie maintenant un lot unitaire sur GPU avant ce repli. Les 17 tests du moteur EG2 et de son API passent. Cette modification sera chargée au prochain redémarrage du moteur. `agent-inventaire-bascule.log` confirme que le catalogue actif Kiara compte zéro projet et zéro document. La console active indique que le service Agent n’est pas encore configuré.

`agent-relogement-metier.log` confirme que 1 147 mails et 98 fragments audio ont été vérifiés par SHA-256 et rattachés à leur chemin sur D: dans la restauration existante. Le chemin EG2 configuré a été relogé. Les deux originaux CDC sont toujours absents. `agent-bascule-preparation.log` confirme le démarrage d’Agent par un lanceur isolé avec sa configuration persistante et les traitements automatiques suspendus. Les 11 projets ERP et les 11 projets Brain sont accessibles dans leurs catalogues respectifs, avec 10 liaisons. Le refus avant habilitation, l’accès accordé et la révocation ont été vérifiés. Les 16 tests de service, administration et passerelle passent. La configuration testée est sous `verification-kiara/reprise-20261113/configuration-bascule`. Le traitement EG2 a repris avec des requêtes de quatre textes, après un lot de seize bloqué sur le premier projet. Le moteur actif est encore en mode CPU après le repli CUDA.

La configuration vérifiée a été installée dans `D:\Serveur IA\lanceur\agent-service.json`, avec les traitements automatiques suspendus. Windows a refusé l’arrêt du lanceur actif, exécuté avec les droits élevés de la tâche d’ouverture de session. Le serveur de modèles et la passerelle répondent toujours. `Start-Interface-Qwen.ps1 -Redemarrer -SansNavigateur` vérifie le PID, l’heure de création et l’absence de requête distante active avant de relancer le lanceur avec l’état du modèle conservé. Le script a passé l’analyse PowerShell. La relance effective reste à effectuer depuis une session élevée. Le découpage EG2 borne désormais les passages contenant de longues suites sans espaces à 4 096 caractères en conservant le contenu. Les 20 tests de mémoire et de connexion passent. Le processus de reconstruction a repris avec ce découpage et un délai de requête borné.

Les lots EG2 de quatre textes ont dépassé le délai sur le premier projet. Avec des lots unitaires et des passages de 1 536 caractères au maximum, en privilégiant les espaces pour les coupures, le premier projet a été reconstruit en 17,6 secondes après réutilisation des vecteurs déjà calculés. La recherche a placé la citation métier au premier rang. Le moteur actif reste sur CPU. Les 30 tests ciblés de mémoire, de connexion et du canal d’embeddings passent. `agent-bascule-droits-originaux.log` vérifie sur les données restaurées qu’un lecteur limité à un projet télécharge l’EML de ce projet avec la bonne empreinte, reçoit un refus pour une source hors projet et perd l’accès après révocation. La commande de redémarrage vérifie désormais qu’Agent répond après relance. Le lanceur de production n’a toujours pas chargé le fichier.

Les vérifications en lecture seule de la restauration métier confirment l’intégrité SQLite des deux bases, l’absence de violations de clés étrangères et la validité des 98 fragments audio pour la sauvegarde. Les nouvelles sauvegardes Kiara lient l’archive Agent par sa taille et son SHA-256 dans l’enveloppe chiffrée. La recette vérifie la redécouverte de la paire après perte du catalogue et le refus d’une archive Agent modifiée. Au dernier relevé, deux projets EG2 étaient reconstruits avec 303 passages pour sept sources et le multimodal comptait 2 619 passages terminés. Les deux processus étaient actifs.

Après arrêt du moteur EG2 et expiration de la reconstruction, le moteur a été relancé via la console Kiara. Le contrôle par la passerelle et les projets suivants ont utilisé la Quadro P2200. Quatre projets ont été reconstruits. La reprise a réutilisé les projets terminés et diffère les sources temporairement en échec. Le superviseur distingue désormais un délai de démarrage d’un contrôle de santé manqué par un moteur déjà prêt. L’index SQLite EG2 utilise une clé de recherche par projet et source pour éviter de parcourir tous les passages d’un projet à chaque remplacement. Les 35 tests ciblés du moteur, de l’API et de la mémoire passent. La reconstruction multimodale reste active. Le lanceur de production attend toujours son redémarrage pour charger Agent.

Le web privé lit maintenant l’origine HTTPS et le port local dans `agent-service.json`, avec les variables d’environnement prioritaires. `agent-web-proxy-https.log` confirme le parcours Chrome via un proxy TLS local qui transmet le `Host` d’origine. Les droits de deux comptes fictifs, la création par le propriétaire, la déconnexion et le refus des commandes Thunderbird depuis le navigateur sont vérifiés. Les 18 tests ciblés du lanceur passent. L’origine publique, son proxy et son certificat restent à configurer et à qualifier. Au dernier relevé, 70 sources EG2 et 3 243 passages multimodaux étaient reconstruits.

`agent-recherche-metier.log` confirme que la route HTTP de recherche Agent a utilisé le moteur EG2 de Kiara sur le corpus restauré, a classé la citation attendue au premier rang et a refusé un projet hors du périmètre du lecteur. La recette exécute la route FastAPI localement avec l’identité signée de Kiara. Le chargement de l’index se fait hors de la boucle HTTP et la sélection de sources limite la lecture SQLite. Les 33 tests de recherche et de mémoire passent. Au dernier relevé, les deux travaux étaient actifs, avec 74 sources EG2 et 3 545 passages multimodaux reconstruits.

La désignation du poste Thunderbird peut être enregistrée dans `agent-service.json`. `agent-thunderbird-configuration.log` confirme sur le service Agent réel que la passerelle accepte le poste désigné après redémarrage, refuse un autre poste propriétaire et retire l’accès à la révocation. Les 18 tests du lanceur réussissent. La recette utilise des accès fictifs et une passerelle sur la boucle locale. La désignation du poste métier et l’appairage de sa boîte restent à effectuer. Au dernier relevé, le multimodal avait terminé 3 704 passages. EG2 avait publié les passages de 74 sources et continuait à alimenter son cache sur la P2200.

`agent-restauration-archive.log` valide la sauvegarde chiffrée native et sa restauration isolée par la console Kiara sur un projet fictif. Les deux bases restaurées passent le contrôle d’intégrité. La console refuse une requête sans jeton et une phrase incorrecte. Une archive invalide ne laisse aucun dossier de récupération partiel. L’arrêt d’Agent ferme aussi les descendants du Python de l’environnement virtuel, qui pouvaient garder une base ouverte pendant la sauvegarde. Les 17 tests ciblés du service et de la passerelle passent. Au dernier relevé, EG2 avait publié les passages de 101 sources et le multimodal avait terminé 4 008 passages.

`agent-rupture-lanceur.log` confirme que l’arrêt brutal d’un lanceur de recette entraîne la fermeture des trois processus Agent et libère la base SQLite. Agent surveille la fin du flux que le lanceur tient ouvert pendant sa durée de vie. La recette d’archive passe avec cette supervision et les 13 tests de service et de passerelle réussissent. Au dernier relevé, EG2 comptait 125 sources au profil Kiara et le multimodal 4 125 passages terminés. Le lanceur actif attend toujours son redémarrage administrateur.

Pendant la reconstruction EG2, le rappel du chat peut citer les preuves déjà au profil Kiara et signale que le projet est partiellement indexé. `agent-recherche-migration-partielle.log` confirme sur le corpus restauré que la route de rappel renvoie 18 sources, toutes au profil courant, et l’avertissement de reconstruction. Les 34 tests de recherche et de mémoire passent. Les travaux restent actifs avec 142 sources EG2 et 4 301 passages multimodaux terminés.

`agent-eg2-reconciliation.log` confirme que les 142 projections SQL déjà reconstruites sur sept projets ont été rattachées à leurs nouvelles références EG2. Le rapprochement vérifie la provenance et le contenu canonique avant d’écrire dans la restauration sur D:. Le contrôle suivant retrouve les 142 références concordantes. La reconstruction continue avec 4 384 passages multimodaux terminés. La console de production confirme qu’Agent reste à démarrer après son redémarrage administrateur.

Le runtime de transcription audio et Whisper medium sont installés sur D:. `agent-transcription-locale.log` confirme deux transcriptions locales d’un WAV français fictif avec les cinq mots attendus. `agent-audio-configuration.log` confirme que le service lancé par Kiara lit le profil et la qualification depuis le dossier configuré. Le fichier de production référence maintenant ces chemins. Les 51 tests ciblés passent, avec un test ignoré. Cette recette ne qualifie ni une séance longue ni deux pistes simultanées. Au dernier relevé, le multimodal comptait 4 643 passages et EG2 142 sources publiées. Le lanceur actif attend son redémarrage administrateur.

`agent-transcription-deux-pistes.log` confirme la transcription complète après clôture d’une séance courte fictive avec deux fragments simultanés, un par piste microphone et système. Whisper medium sur CPU a conservé trois segments avec les mots attendus sur chaque piste et des timecodes dans les limites des originaux. Les deux WAV restent identiques octet pour octet. Le direct à deux pistes et une séance longue restent à qualifier. Au dernier relevé, 148 sources EG2 et 4 882 passages multimodaux étaient terminés.

`agent-transcription-direct-deux-pistes.log` confirme que le worker de transcription directe a produit trois segments durables alors que la séance fictive était encore en cours. Les deux fragments microphone et système ont été transcrits avec les mots attendus, les bons timecodes et les originaux intacts. Le dernier segment a été enregistré 19,16 secondes après le début du dépôt, pour deux pistes de moins de neuf secondes chacune. Ce parcours injecte des WAV fictifs et ne mesure pas la latence de bout en bout depuis les périphériques. Sept projets EG2 sont reconstruits, et 168 sources sur huit projets ont une référence SQL vérifiée et relogée.

Le rapprochement EG2 vérifie désormais le nombre, l’ordre et le texte intégral des passages avant de rattacher une projection SQL. Le journal de rapprochement confirme 18 références mises à jour et 186 projections concordantes lors de la vérification suivante. La base Brain passe `quick_check` et le contrôle des clés étrangères. Le multimodal a terminé 5 185 passages. Les deux processus de reconstruction restent actifs.

Le rapprochement EG2 suit la reconstruction active toutes les trois minutes dans la restauration existante. Le dernier contrôle a validé 406 références et huit projets ont fini leur reconstruction. À la sortie du processus, le contrôle final exige l’intégrité SQLite, un seul profil dans l’index et la concordance de toutes les sources canoniques, références et passages. Ce contrôle a refusé l’index en cours, comme attendu. Le multimodal a terminé 6 655 passages.

La suite backend complète a repris avec un dossier temporaire court sur D:, après des erreurs d’écriture de fragments dues à la longueur des chemins de recette. Les trois tests ciblés qui couvrent la libération d’une capture navigateur passent avec ce réglage. Les résultats de la suite complète sont suivis dans `agent-backend-complet-chemins-courts.log` et ceux du frontend dans `agent-web-complet.log`.

La suite web Agent complète passe avec 1 025 tests sur 97 fichiers. Le mode threads évite le délai d’arrêt des processus de test rencontré sous Windows. Le résultat complet est dans `agent-web-complet-threads.log`.

La passerelle et le relais transmettent les quatre en-têtes de vérification des copies documentaires. Le service lancé par Kiara lit les racines documentaires de lecture et d’écriture et les mappings depuis sa configuration persistante. `agent-recu-documents-wireguard.log` valide l’aperçu, la préparation d’un DOCX fictif, la correspondance des empreintes et l’intégrité de l’original via Agent, la passerelle, WireGuard et le relais exécuté depuis les sources. Le journal du pare-feu ne contient aucune nouvelle demande WireGuard. Les 25 tests ciblant le transport, le web privé, le service et l’administration passent. Les racines du partage métier restent à renseigner.

Le nouveau paquet non signé `Kiara-Agent-recu-documents-recette-x64.exe` a passé l’installation NSIS, la vérification des empreintes des auxiliaires, le téléchargement de 32 Mio intégral et par plage dans WebView2, le retour à Conversations, la fermeture du relais et la désinstallation. Le journal `agent-recu-documents-nsis-recette.log` confirme zéro nouvelle demande WireGuard pendant ce parcours.

Le lanceur accepte une sélection de groupes dans `worker_groups` pour reprendre les traitements progressivement. Le groupe documentaire active le même worker que le lanceur autonome Agent. `agent-lifespan-reprise.log` confirme la sélection, la suspension et l’arrêt des traitements déjà lancés en cas d’erreur au démarrage. `agent-worker-document-reel.log` confirme avec Agent et WireGuard que le worker documentaire accepte les lots et qu’une copie DOCX reste vérifiable. Aucun événement de demande WireGuard n’a été enregistré. Les 24 chemins documentaires restaurés sont inaccessibles depuis le poste, dont 23 sur le lecteur V: absent. Les racines de partage doivent être renseignées avec les accès métier.

Les quatre échecs de rendu PDF dans la suite backend lancée sans runtime multimodal correspondent à l’absence de l’exécutable de rendu par défaut. Les cinq tests PDF passent avec le runtime configuré pour la production, dans `agent-pdf-runtime-bascule.log`. D’autres résultats de la suite complète restent à examiner. Le rapprochement a vérifié 567 références EG2 et le multimodal a terminé 8 016 passages.

La fermeture des pistes WASAPI tente de libérer chaque périphérique. Quand une fermeture échoue, la capture rapporte la piste concernée et conserve les fragments déjà journalisés. La vidange de fin de capture exige une fermeture confirmée. Les 26 tests audio et PDF ciblés passent dans `agent-audio-fin-capture.log`. Le composant WASAPI corrigé a été recompilé et intégré dans `Kiara-Agent-fin-capture-recette-x64.exe`.

Après interruption des travaux, EG2 et le multimodal ont repris sur les index existants. Le rapprochement a vérifié 677 références EG2 et le multimodal comptait 8 529 passages terminés. La suite backend relancée utilise le runtime multimodal configuré pour la production. Le script de redémarrage utilise les contrôles de fichiers du service Agent avant l’arrêt du lanceur. La configuration de production passe ce contrôle et la recette refuse un runtime multimodal inexistant. Après redémarrage, le script vérifie aussi le catalogue et l’état de la passerelle WireGuard.

La consolidation audio se bloquait sous le lanceur Windows alors que les fragments étaient présents et que le même mix réussissait en ligne de commande. Le mix et le rendu PDF s’exécutent désormais avec une entrée standard fermée. `agent-audio-fin-capture-nsis-stdin.log` confirme, depuis le paquet de recette installé, l’enregistrement microphone, la pause, la reprise, la finalisation de deux fragments, le téléchargement Ogg et la désinstallation. Le journal Windows indique zéro nouvelle demande WireGuard. Les 26 tests ciblés audio et PDF passent aussi après la correction.

`agent-precontrole-bascule-live.log` confirme que le lanceur actif et le fichier PID concordent, que le service configuré dispose de ses runtimes et de ses bases, que la passerelle traite zéro requête et que le catalogue historique contient zéro projet et zéro document. Le contrôle est rejoué avant la première activation par le script de redémarrage. À ce relevé, le rapprochement EG2 a vérifié 743 références et l’index multimodal compte 9 328 passages terminés.

Une fois le catalogue Agent configuré, la restauration Kiara refuse les archives qui réintroduiraient d’anciens projets. Les archives historiques restent consultables et une sauvegarde d’espaces avec des conversations et sans projet reste restaurable. Cinq tests ciblés passent, dont la vérification d’une archive réelle de recette, le refus avant maintenance et la comparaison des octets de la base. À ce relevé, EG2 a vérifié 798 références et le multimodal a terminé 9 562 passages.

Le précontrôle de redémarrage tient désormais compte aussi des requêtes Agent qui passent par le relais Windows ou le web privé. La passerelle suit ces requêtes pendant les transferts et libère le compteur à leur fin. Les 16 tests de passerelle, de web privé et d’administration passent, dont le contrôle du compteur pendant un transfert. Le lanceur actif conserve son PID et n’a pas chargé Agent.

EG2 et la génération utilisent des réservations distinctes dans Agent, même avec la même adresse de passerelle. En cas de 429 ou 503, EG2 libère sa réservation avant d’attendre la prochaine tentative. Sous Windows, la découverte documentaire vérifie aussi les noms des entrées des dossiers entièrement parcourus, car l’horodatage seul peut rester identique après une modification. Les 69 tests ciblés passent, dont le cas qui échouait dans la suite complète et la recherche EG2 pendant l’attente d’une tentative. Le rapprochement a vérifié 881 références.

`agent-cdc-generation-kiara-preuves.log` confirme l’extraction d’un PDF fictif et la création de deux exigences candidates par le modèle `fred-qwen` via la passerelle de production. La recette vérifie la provenance, la page physique et la présence des citations dans le texte extrait. La génération a duré 10,7 secondes. Agent s’exécutait avec des bases isolées et un accès existant à la passerelle. Le lancement du service Agent dans le lanceur de production reste à effectuer.

`agent-eg2-vecteurs-valides.log` confirme en lecture seule que les 28 485 vecteurs des 891 sources déjà rapprochées comportent chacun 768 valeurs finies et une norme exploitable. Les passages concordent avec le texte canonique et aucune référence n’était à corriger à ce relevé. Le contrôle final inclut ces vérifications pour toutes les sources de la restauration.

La reconstruction EG2 s’est interrompue à la suite de l’arrêt du moteur. Le démarrage via la console Kiara a rétabli le moteur CUDA. La recette attend désormais le retour du moteur prêt lors d’une interruption temporaire et reprend sur les vecteurs présents. Le journal `agent-eg2-metier-reprise-apres-panne.log` confirme une inférence de contrôle sur CUDA et la reprise des lots. Le multimodal a atteint 10 661 passages.

L’audit multimodal relit les passages attendus à partir des sources canoniques et vérifie les citations, les chemins, les empreintes et les vecteurs normalisés de 768 dimensions. Le premier relevé de `agent-multimodal-audit.log` confirme que les 37 563 passages attendus pour 1 148 sources sont présents et que les 11 039 vecteurs alors terminés sont valides. Le contrôle final a refusé l’index encore en cours. Il sera rejoué en lecture seule à la sortie du processus actif.

Le script de bascule relève le catalogue ERP avant la première activation et compare les identifiants, codes et intitulés au catalogue servi par Agent après le redémarrage. Le précontrôle sur le lanceur actif confirme zéro projet et zéro document historiques, ainsi que 11 projets ERP attendus. Le comparateur refuse un projet absent, un doublon ou un champ divergent. Le contrôle après redémarrage reste à effectuer sur le lanceur de production.

Le pont WireGuard relaie les routes déjà authentifiées de la voix Max, dont le téléchargement du pack, la transcription et la synthèse. Le contrôle de l’état, l’annulation et la libération de session passent pendant les flux de synthèse. `tauri-voix-max-wireguard.log` vérifie les routes de bout en bout dans un tunnel local avec des réponses fictives et confirme zéro nouvelle demande du pare-feu Windows. Les cinq tests de la passerelle Max passent. La conservation d’un pack Max déjà installé sur un poste et son usage avec le moteur vocal réel restent à qualifier.

`tauri-voix-max-nsis.log` confirme l’installation du nouveau paquet NSIS, la concordance des empreintes des auxiliaires, la reprise du profil et le parcours Conversations → Agent → Conversations. Le relais installé a atteint les routes d’état et de test de la passerelle Max avec des réponses fictives. La désinstallation a abouti et le journal Windows indique zéro nouvelle demande WireGuard. Le pont vérifié est en place au chemin attendu par le serveur pour son prochain démarrage. Le paquet de recette est non signé.

Le descripteur du moteur Voix Max serveur pointait encore vers F:. Il référence désormais le pack déjà présent sur D:, après vérification des 147 empreintes du manifeste. `tauri-voix-max-moteur-reel.log` confirme que la passerelle de production a synthétisé puis reconnu la phrase française du test avec le moteur réel. Le résultat est fonctionnel à 6,12 s, au-dessus du seuil de 3 s, avec un facteur temps réel de reconnaissance de 1,34. La migration du pack sur un poste client reste à qualifier.

Les 11 projets restaurés ont répondu à une recherche EG2 via la passerelle de production. La première vérification, fondée sur les débuts de documents, a retrouvé la source attendue dans les cinq premiers résultats pour huit projets. Avec une phrase distinctive du corpus par projet, les 11 sources attendues sont revenues dans les cinq premiers résultats, dont 10 au premier rang. Les 312 citations renvoyées pointaient vers des preuves canoniques du bon projet et du profil courant. Les deux contrôles ont ouvert les index en lecture seule. Le rapprochement continue sur les dernières sources différées.

La vérification en lecture seule a confirmé les 38 004 vecteurs de 1 146 sources EG2 sur les 1 148 attendues. Les deux dernières sources conservent 1 034 passages à l’ancien profil jusqu’à la fin de leur reprise. L’audit multimodal a vérifié 13 511 vecteurs terminés et la présence des 37 563 passages attendus, sans entrée active étrangère au corpus ni anomalie SQLite.

La reconstruction EG2 est terminée sur la restauration métier de D:. `agent-eg2-metier-reprise-apres-panne.log` confirme l’intégrité SQLite et un seul profil Kiara pour les 39 038 passages. L’audit complet dans `agent-eg2-reconciliation.log` a validé les 39 038 vecteurs de 768 dimensions, les 1 148 sources et les projections des 11 projets. Les deux dernières références ont été relogées. La reconstruction multimodale continue séparément.

`agent-eg2-route-bascule.log` confirme que les routes mémoire d’Agent ouvrent l’index reconstruit de 39 038 passages avec les réglages Kiara. Sur la restauration, une recherche par un lecteur limité à un projet a renvoyé 24 citations, dont la source attendue. Le même lecteur a reçu un refus sur un autre projet. La recette a appelé l’application Agent sans exécuter son démarrage ni ses workers, et a utilisé la passerelle Kiara active pour calculer le vecteur de recherche. Le lancement supervisé de production reste à effectuer.

Le worker multimodal parcourt désormais les entrées du lot en avançant dans l’index SQLite des identifiants. La reprise repart des états enregistrés et le worker vérifie les entrées antérieures avant de terminer le lot. Sur l’index métier actif, la lecture de l’entrée suivante est passée d’environ 111 ms à moins de 0,1 ms une fois le parcours engagé. Les 17 tests d’indexation, de reprise, de changement de profil et de PDF passent. La reconstruction active continue avec le code chargé à son lancement. Le changement sera utilisé au prochain démarrage du worker.

La reconstruction a redémarré avec le correctif sur l’index existant. Elle a conservé les 14 173 passages déjà calculés et atteint 14 195 au premier relevé après reprise. `agent-multimodal-reprise-optimisee.log` suit ce processus et sa recette inclut l’audit final en lecture seule. Le lanceur de production est resté actif pendant l’opération.

Le redémarrage administrateur du 14 novembre a activé Agent dans le lanceur de production. `agent-bascule-production.log` confirme la concordance des identifiants, codes et intitulés des 11 projets avec la base ERP restaurée. La passerelle et WireGuard sont actifs, sans nouvelle demande du pare-feu Windows. EG2 est prêt sur CUDA. Les workers Agent restent suspendus par la configuration de bascule, tandis que la reconstruction multimodale externe continue sur D: avec 14 757 passages terminés. Les habilitations métier sont à attribuer par appareil.

L’accès Kiara « Fred » a reçu le rôle Propriétaire sur les 11 identifiants ERP restaurés. La passerelle de production, appelée avec le profil Fred, renvoie les 11 projets. L’inventaire préalable à la reprise a trouvé 10 scans de jalons en file et un marqué en cours. Le groupe planning reste suspendu avec les autres traitements automatiques.

Les groupes CDC et audio sont activés en production. L’inventaire précédant leur activation confirmait un job CDC terminé et aucune réunion en capture ou en transcription. `agent-bascule-traitements.log` confirme le redémarrage, les 11 projets servis et la passerelle WireGuard active. L’habilitation de Fred persiste. Les groupes mail, planning, documents, connaissances et multimodal restent suspendus dans le service. La reconstruction multimodale externe continue et a atteint 14 919 passages.

Les groupes connaissances et documents sont également actifs. `agent-bascule-connaissances-documents.log` confirme le redémarrage et les 11 projets servis. La file documentaire était vide et aucun élément canonique ne demandait une promotion automatique. Une analyse de connaissances est passée de l’attente du modèle à l’attente d’un créneau libre. Les opérations documentaires sur les partages métier attendent la configuration de leurs racines. La reconstruction multimodale externe continue avec 15 149 passages terminés. Le journal Windows ne contient aucune nouvelle demande WireGuard pendant cette reprise.

Le réglage mail restauré sélectionne Thunderbird et désactive le scan automatique. Les files de tri, d’enrichissement et de liaison Thunderbird ne contenaient aucun traitement en attente au contrôle. L’analyse de connaissances restante a atteint le modèle, puis a dépassé son délai de réponse de 45 secondes. Elle a enregistré une nouvelle tentative automatique. Le lancement du groupe mail reste à confirmer après validation administrateur.

Windows a signalé l’annulation de l’élévation pour le groupe mail. Le service et ses quatre groupes actifs sont restés en place. Le délai des analyses de connaissances passe à 110 secondes dans les sources, sous le délai amont Kiara de 120 secondes. Les 25 tests ciblés passent. Le service en cours utilise encore l’ancien délai et traitait une analyse lors du relevé.

Agent a ensuite été relancé seul depuis sa console d’administration lorsque la passerelle était libre. Le service charge le délai de 110 secondes. Les 11 projets répondent, le PID du lanceur est identique et WireGuard est actif. L’analyse en attente conserve son curseur au cinquième lot. Au relevé suivant, les analyses étaient réparties entre neuf terminées, une en attente d’un créneau et une en attente de reprise après échec. La reconstruction multimodale externe continue.

`agent-fred-wireguard-production.log` confirme que le profil Fred ouvre le catalogue des 11 projets et la page Agent via le tunnel WireGuard de production. Le client de vérification utilisait le relais depuis les sources et une liaison UDP sur 127.0.0.1. Zéro nouvelle demande WireGuard a été enregistrée.

`agent-catalogue-conversations-production.log` confirme, avec le profil Fred via WireGuard, que le contrat utilisé par Conversations et le catalogue ERP servi par Agent présentent les mêmes 11 identifiants, codes, intitulés et états d’archivage. Fred peut modifier ses projets. La création de nouveaux projets est hors de son périmètre de 11 identifiants. Le journal Windows indique zéro nouvelle demande WireGuard.

`agent-citation-production.log` valide, avec le profil Fred via WireGuard, la recherche Agent sur un projet restauré et l’ouverture d’un original cité. Les 10 sources renvoyées appartiennent au projet interrogé et le mail téléchargé a le SHA-256 enregistré dans Brain. Le journal Windows indique zéro nouvelle demande WireGuard. Ce contrôle vérifie la chaîne de recherche et d’accès à la preuve, sans lancer de conversation Hermes.

`agent-hermes-citations-production.log` valide un tour de recette séparé depuis l’API de Conversations. Le profil Fred a interrogé un projet restauré via WireGuard, Hermes a terminé la réponse et a renvoyé six citations Agent. Les six identifiants de source concordent avec le projet Brain lié au projet ERP demandé. Le journal Windows confirme zéro nouvelle demande WireGuard.

Le dossier privé `D:\Kiara\dossiers-clients` accueille les nouveaux fichiers clients. Chaque projet ERP restauré dispose d’un dossier et d’un lien « Dossier client Kiara ». Les 29 liens précédents sont conservés. La configuration du serveur autorise la lecture et l’écriture sous cette racine. Son chargement dans le service de production attend la validation du redémarrage administrateur. Les anciens fichiers du lecteur V: restent à retrouver.

La passerelle de production renvoie les 11 liens « Dossier client Kiara » au profil Fred via WireGuard. Chaque lien pointe vers le sous-dossier de son projet sur D:. Windows a signalé l’annulation de l’élévation pour le redémarrage. La vérification de la lecture et de l’écriture depuis le service attend le chargement de la nouvelle configuration.

Le réglage `document_project_root` limite les lectures, les publications et les scans de jalons au sous-dossier correspondant à l’identifiant du projet. Le précontrôle a validé les 11 dossiers existants et la configuration de bascule. Le groupe `planning` est ajouté à la configuration pour reprendre les 11 traitements en attente au prochain démarrage du lanceur. Les scans peuvent reprendre avec les sources restaurées dans Kiara. Les fichiers historiques de V: restent à retrouver.

La mise à jour des liens réseau conserve désormais l’identifiant des liens dont le code et le chemin sont identiques. Les brouillons documentaires gardent ainsi leur lien quand un autre chemin change. Les 78 tests ciblés sur les projets, les brouillons et la découverte documentaire passent. Le lanceur de production attend toujours le redémarrage administrateur. La reconstruction multimodale atteint 17 729 passages terminés sur 37 563 et continue sur la base active.

La création d’un projet depuis le catalogue Kiara provisionne désormais son sous-dossier et ajoute le lien « Dossier client Kiara ». Si la racine est inaccessible, la création échoue avant l’enregistrement du projet. La recette vérifie cet état puis la création réussie quand la racine est disponible. La configuration de production passe de nouveau le précontrôle de bascule.

Les imports de dossier et de projet utilisent le même provisionnement. Les archives avec un lien « Dossier client Kiara » associent ce lien au nouveau projet en conservant ses références remappées. Les fichiers déjà présents dans le dossier d’origine restent à leur emplacement. La recette vérifie deux importations successives d’une archive de revue, le dossier d’origine, les nouveaux liens et le refus d’un import quand la racine est indisponible.

La sauvegarde Agent déclenchée par Kiara inclut les fichiers de la racine des dossiers clients configurée. Elle vérifie les empreintes et rattache les liens aux dossiers de la restauration isolée. La recette sur données fictives valide la sauvegarde native, le relogement et l’extraction du fichier client depuis l’archive chiffrée. Les dossiers clients de production sont encore vides. Le redémarrage administrateur reste nécessaire avant la première sauvegarde planifiée avec cette configuration.

Deux analyses de connaissances avaient échoué lors du décodage JSON, aux curseurs 5 et 16. Le service demande désormais le format structuré à Kiara et conserve la validation des citations. Les 25 tests ciblés passent. Le redémarrage d’Agent seul a chargé le correctif avec les mêmes 11 projets et le tunnel WireGuard actif. Les deux analyses attendent leur créneau de reprise enregistré. Le lanceur reste en place et la reconstruction multimodale atteint 18 977 passages terminés.

La première analyse a repris et validé trois lots, jusqu’au curseur 8. Le script de redémarrage compare maintenant les groupes de traitements et la racine documentaire chargés par le lanceur à la configuration validée avant l’arrêt. Les 10 tests du service et de la console passent. Le précontrôle de bascule est réussi sur le lanceur actif.

Le groupe mail est préparé dans la configuration de redémarrage pour traiter les classements et enrichissements. Le contrôle des files retrouve neuf classements et 1 138 enrichissements terminés, sans traitement en attente. Le réglage Thunderbird conserve le scan automatique désactivé. Le poste et la boîte Thunderbird métier restent à appairer. La première analyse de connaissances a atteint le curseur 10.

Le précontrôle vérifie aussi que la racine des dossiers clients existe, qu’elle correspond à son chemin résolu et qu’elle reste distincte des racines partagées de lecture et d’écriture. Les 11 tests de la console et du service passent, ainsi que le contrôle de bascule avec la racine D:. Le lanceur actif attend toujours le redémarrage administrateur.

L’audit intermédiaire de l’index multimodal en production a retrouvé les 37 563 passages attendus pour les 1 148 sources. Les 20 300 vecteurs terminés ont été vérifiés avec leurs références. SQLite ne signale aucune anomalie. Il reste 17 262 passages en attente et un en cours. Le worker externe continue sur la même base. Les deux analyses de connaissances ont dépassé leurs lots en échec.

La recette de bout en bout du lanceur confirme qu’une sauvegarde Kiara avec Agent inclut un document client fictif. La restauration lancée depuis la console retrouve les mêmes octets, reloge le chemin du lien dans le dossier isolé et vérifie les deux bases. Une phrase incorrecte et une archive invalide sont refusées.

La configuration Foresight restaurée est en mode réseau, avec les nouvelles séances désactivées. Après le contrôle final de l’index et l’arrêt du processus externe, l’activation du groupe multimodal permet les commandes d’indexation. Le démarrage automatique du worker multimodal exige aussi le réglage Foresight activé en mode local. Ce réglage change les capacités des séances et le routage de la recherche. Il doit être vérifié séparément du redémarrage qui charge les dossiers clients, le planning et le traitement des mails.

Le contrôle du runtime audio avec les chemins de production confirme que la transcription différée est prête, y compris pour les séances. La transcription directe répond au contrôle d’installation, mais les seuils de latence et de qualité n’ont pas été validés. Foresight est désactivé, avec une séance restaurée terminée et une séance créée. Les réglages de production n’ont pas été modifiés pendant ce contrôle.

## Retrait du moteur multimodal local

La décision du 14 novembre rend le moteur LiteRT obsolète et remplace les
étapes précédentes de reconstruction multimodale. Le calcul a été arrêté,
l’index actif et le modèle avec ses caches ont été supprimés. Les commandes
d’indexation locale ont été retirées. L’ancienne recherche explicite image
ou audio retourne HTTP 410. La bibliothèque réutilise EG2 pour les documents,
le texte OCR et les transcriptions indexées. Les sauvegardes et restaurations
échappent désormais à la réintroduction de l’index dérivé retiré.

Le rendu PDF reste exécuté dans le runtime Python d’Agent avec PDFium.
La production a confirmé le catalogue des 11 projets, les résultats de la
recherche générale et de la bibliothèque, ainsi que le SHA-256 d’un original
cité. Après le redémarrage administrateur, les deux actions de recherche
Hermes ont renvoyé des sources du projet attendu et Conversations a transmis
une citation de ce projet. EG2 est prêt sur la Quadro P2200. Le fichier
de configuration historique vide a été supprimé.
Les commandes de suppression des anciens runtimes D: et E: ont été refusées
par la politique d’exécution. Ces répertoires ne font plus partie de la
configuration sur disque.

## Reprise des scans de jalons en production

Les six groupes Agent sont actifs et la racine `D:\Kiara\dossiers-clients`
est chargée. Au contrôle, dix scans attendaient et un scan était encore à
zéro. Le worker prépare maintenant un lot borné et réutilise le texte déjà
traité d’une pièce jointe lorsque tous ses passages ont abouti et que le
SHA-256 du mail est identique. Si l’original change ou si un passage doit être
repris, le document est relu. Les 11 tests de jalons passent.

Agent seul a été relancé. Les 11 projets et WireGuard répondent toujours.
La file de jalons a repris en production. Un scan de 30 passages est terminé,
le suivant en a traité 11 sur 30 et neuf scans sont en attente. Les anciens
fichiers du lecteur V: ne sont pas présents dans les dossiers clients.

## Paquet de distribution Windows

Le constructeur accepte une version Windows explicite et produit le paquet
NSIS sous le nom Kiara avec l’identifiant `fr.kiara.desktop`. Tauri transmet le
numéro du paquet au relais pour l’affichage et la déclaration de version à
la passerelle. L’ancien client 3.5.62 remplace un EXE personnel et son canal de
mise à jour ne peut pas exécuter un paquet NSIS. L’installation et l’import
du profil 3.5.62 constituent le parcours de migration déjà pris en charge.
Le magasin Windows ne contient aucun certificat de signature de code avec sa
clé privée. Aucun paquet n’a été publié sur le canal de production.

`tauri-distribution-3.5.63-finale.log` confirme l’installation puis la
désinstallation du paquet 3.5.63 non signé. Les empreintes du relais et du
helper correspondent aux binaires attendus. La version affichée correspond
à la version installée. La recette a repris un profil fictif au format
3.5.62, l’identité de l’appareil, l’historique, le brouillon et les réglages.
Le passage de Conversations à Agent et le retour, les routes Voix Max et la
fermeture du relais sont vérifiés. Windows a enregistré zéro demande de
pare-feu WireGuard. Les 28 tests ciblés du client passent.

## Préparation du web privé sur le tunnel de Kiara

Le connecteur `Karenax-Cloudflare-Tunnel` fonctionne et l’API HTTPS existante
renvoie 401 sans jeton. L’origine retenue pour Agent est
`https://agent.karenax.net`. Le fichier de configuration local définit le port
8767 sur la boucle locale. Le lancement valide l’origine et le script de
redémarrage vérifie l’état du listener et la réponse à une requête `HEAD` avec
le `Host` prévu. Les 24 tests ciblés passent. La recette HTTPS locale dans
Chrome a de nouveau vérifié deux comptes, le périmètre des projets et la
déconnexion.

Pour l’ouverture réseau, ajouter au tunnel existant le nom public
`agent.karenax.net` vers `http://127.0.0.1:8767` en conservant le `Host` public.
La règle de contournement du cache doit couvrir ce nom. Vérifier ensuite le
certificat public, la page de connexion, le refus sans session et le catalogue
de l’accès Fred. L’origine n’avait pas d’enregistrement A au contrôle.
Le précontrôle du lanceur en production est passé. Windows a signalé
l’annulation de l’élévation au redémarrage. Le port 8767 reste fermé jusqu’au
chargement de la configuration par le lanceur.

## Compatibilité Android avec les projets Agent

Le paquet Android de recette a été compilé avec l’interface partagée à jour.
Sur l’émulateur API 36, `android-agent-historique.log` vérifie qu’un identifiant
ERP Agent survit à l’écriture chiffrée, à la relecture et à la fusion d’un
historique, et qu’un tel identifiant est refusé comme identifiant de document
Workspace. L’autotest Android et les 17 tests de livraison passent. Les 16 tests
ciblés du relais bureau et de la passerelle passent également. Le canal Android
de production servait encore la version 1.0.26 au contrôle.

La version Android 1.0.27 (code 28) a été compilée en mode Release après
reconstruction du pont WireGuard pour arm64 et x86_64. Les quatre tests du
canal de mise à jour passent. Le paquet non signé est sous
`client-android/app/build/outputs/apk/release/app-release-unsigned.apk`.
Le compte Fred reçoit un refus d’accès au dossier `toolchain/android-signing`.
L’archive de récupération documentée sur `\\DS218\home` est inaccessible
depuis ce poste. La publication reste en 1.0.26 jusqu’à ce que le nouvel APK
puisse être signé avec la clé historique et installé par-dessus cette version.

## Validation des citations dans l’analyse des connaissances

Deux passages d’un même élément de connaissance peuvent figurer dans le même
lot. La validation compare maintenant la citation littérale à tous les
passages de l’élément dans ce lot et conserve les références à ses sources.
Le test couvre aussi les citations inventées et les identifiants étrangers.
Les suites ciblées d’analyse, de découverte documentaire et de Foresight
comptent 80 réussites et un test ignoré. Agent a été relancé avec le correctif.
Le catalogue des 11 projets et le tunnel WireGuard ont répondu après relance.

L’un des deux projets restants a progressé jusqu’au lot 42 sur 63. L’autre
attend sa nouvelle tentative au lot 153 sur 264 après un rejet de preuves
sur un lot de 55 éléments distincts. Le modèle reçoit désormais des codes
courts pour les passages et les cibles. Agent les résout avant de vérifier
les citations mot pour mot et conserve les identifiants métier dans les
résultats. Les 27 tests d’analyse passent. Agent a rechargé le correctif et
le catalogue des 11 projets et WireGuard ont répondu après redémarrage.

Au contrôle suivant, une analyse avait atteint le lot 44 sur 63. La reprise
de l’autre au lot 153 restait programmée. La file de jalons a été corrigée
pour trier les scans selon leur mise en file, même lorsqu’une relance
périodique réutilise une ancienne ligne. Les 12 tests de jalons passent.
Après relance d’Agent, un projet qui attendait a pris la main sur la file
de production. Les 11 projets et le tunnel WireGuard ont répondu.

L’import des exports historiques exclut désormais `storage/multimodal`,
même si la casse du nom diffère. Les sauvegardes et restaurations appliquent
la même exclusion. La recette préserve EG2, l’original mail et les octets de
l’archive source. La restauration a aussi été vérifiée avec une ancienne
archive qui déclare encore le dossier dans son manifeste. L’index actif est
absent. Trois copies hors production conservent environ 83 Mio d’anciens
index, dont une copie référencée par un manifeste de sauvegarde.

Le processus isolé d’extraction documentaire reçoit désormais une entrée
standard fermée, comme le mixage audio. Il ne reprend plus le flux ouvert
utilisé par le lanceur pour superviser Agent. Les deux tests ciblés couvrent
le délai du processus et l’extraction depuis un parent dont l’entrée reste
ouverte. Après redémarrage d’Agent seul, le premier scan de production a
traité 10 passages sur 30. Les 11 projets et WireGuard ont répondu.

Le premier scan a ensuite terminé ses 30 passages et cédé la place au
projet suivant. La recette de sauvegarde de Kiara rejouée après le retrait
de LiteRT restaure le document client fictif et reloge son lien. Les deux
bases restaurées passent le contrôle d’intégrité et les restaurations
invalides sont refusées. En production, les deux bases Agent et l’index
EG2 passent `quick_check` sans violation de clé étrangère. Le catalogue
des sauvegardes de production ne contenait encore aucune archive Agent
associée. La prochaine sauvegarde est planifiée à 03 h.

Les habilitations Agent sont dans la base Workspace que Kiara sauvegarde
avec ses accès personnels. La validation de l’archive vérifie désormais
qu’un droit Agent correspond à un accès connu et que le rôle, le périmètre
et l’identité déléguée sont valides. La recette restaure le rôle et le
périmètre d’un propriétaire et refuse un rôle invalide ou un accès absent.
La base de production contient le rôle Propriétaire de Fred sur les 11
projets Agent, une seule habilitation et zéro projet Workspace historique.
Les 67 tests d’accès, Workspace, sauvegarde et restauration passent. Le
contrôle ajouté à la passerelle de sauvegarde sera chargé au prochain
redémarrage du lanceur.

Le paquet serveur inclut désormais le service Agent, son frontend compilé,
les sources de reconstruction et leurs dépendances déclarées. La recette
du ZIP compte 754 fichiers dont 606 pour Agent. Les actifs référencés par
la page et les empreintes du manifeste concordent. Les bases, les clés et
la configuration locale de production sont exclues. Le paquet est prêt
pour une recette de réinstallation indépendante.

La réinstallation de recette a révélé que le fichier de base Strata manquait
à l’archive. Il est désormais inclus. Le script PowerShell respecte aussi
`KIARA_RUNTIME_PYTHON` pour un environnement déjà installé hors du paquet.
Depuis une extraction neuve sur D:, Kiara a démarré Agent sur des bases
fictives, créé un projet, relu son catalogue via la passerelle authentifiée
et servi les trois fichiers référencés par la page Agent. La recette a
réutilisé les runtimes Python déjà installés sur ce poste.

Les scans de jalons appellent le modèle en arrière-plan. Ils restent suivis
par le planificateur et ne remettent plus à zéro le délai d’inactivité
interactif qui autorise l’analyse des connaissances. Les demandes
interactives gardent la priorité. Les 40 tests ciblés passent. Après relance
d’Agent, le catalogue des 11 projets et WireGuard ont répondu, et un scan
de jalons avait repris. L’avancement des deux analyses reste à vérifier.

Le suivi en production a montré que des scans quasi continus pouvaient
encore empêcher la réservation d’un créneau par l’analyse. Celle-ci peut
maintenant prendre place dans la file du moteur pendant un scan. Le moteur
continue de traiter un appel à la fois et privilégie les demandes
interactives dans la file. Les 63 tests ciblés passent. Agent a rechargé
la correction et le catalogue des 11 projets répond. Le contrôle de
recherche avec Fred a confirmé les deux outils, la bibliothèque EG2 et le
SHA-256 d’un original cité. EmbeddingGemma 2 est prêt sur la Quadro P2200.

L’analyse bloquée a validé les lots 153 et 154 en production. Le curseur
est à 155 et l’erreur précédente est levée. L’autre projet attend au lot
51 sur 63. En parallèle, un scan de jalons avait traité 29 passages sur 30.
Le paquet serveur a été reconstruit avec les corrections et la recette de
réinstallation a de nouveau servi le catalogue et les trois actifs web.

## Web Agent sur le tunnel HTTPS existant

L’origine retenue est maintenant `https://ia.karenax.net/agent/`. Le mode
`web_port: 0` monte Agent sous `/agent/` dans la passerelle 8766, déjà
desservie par le tunnel. La recette Chrome sur une passerelle HTTPS isolée
valide deux comptes, les droits par projet, la navigation et son rechargement,
la déconnexion et le refus sans jeton sur `/v1/models`. Le nouveau réglage
est écrit sur D:. La route publique répond encore 404 depuis le lanceur
actif. La vérification préalable a rencontré une requête en cours et la
politique d’exécution a bloqué la commande de redémarrage administrateur.

La recette de la passerelle partagée couvre aussi le téléchargement d’une
plage d’octets sous `/agent/`. Elle confirme le contenu HTTP 206, le nom du
fichier et l’interdiction de mise en cache. Une demande sans session ou hors
du périmètre du projet est refusée. Les 14 tests de la passerelle passent.

Le redémarrage explicite attend jusqu’à une minute que les requêtes Kiara
et Agent se terminent. Il revérifie le PID à l’écoute et l’activité avant
l’arrêt. Le précontrôle seul reste immédiat et refuse si une requête est
en cours. L’analyse qui bloquait au lot 153 a atteint le lot 176 sur 264.


Le redémarrage administrateur a réussi après correction du précontrôle
Python sous Windows PowerShell 5.1 et PowerShell 7. La passerelle de
production sert la page de connexion sur `https://ia.karenax.net/agent/`
avec HTTP 200 et `Cache-Control: no-store`. Sans session, `/agent/app`
redirige vers la connexion et `/agent/v1/models` répond 401. Les droits
chargés pour Fred couvrent les 11 projets du catalogue au rôle
Propriétaire. Le diagnostic du lanceur indique EmbeddingGemma 2 prêt sur
la Quadro P2200. La vérification publique a porté sur les routes sans session.


## Réunions dans l’EXE Kiara

La recette du paquet Windows 3.5.63 installé sur D: a couvert la capture du
son système par WASAPI, la pause et la reprise, la conservation de six fragments
via WireGuard et la récupération de l’audio Ogg. Le projet et la réunion
étaient fictifs. La première transcription différée restait bloquée avant
le décodage. Le processus Whisper reçoit désormais une entrée standard
fermée, comme les sous-processus de consolidation audio et de rendu PDF.

Après ce correctif, Whisper medium a transcrit le son réellement capturé.
La transcription a été relue et validée dans Kiara. Qwen a généré le compte
rendu depuis cette transcription et le bouton d’enregistrement l’a publié
dans les Revues du projet fictif. Le relais s’est fermé proprement, la
désinstallation de recette a abouti et le journal du pare-feu ne montre
aucune nouvelle demande WireGuard. Le dernier essai complet utilise la
sortie Windows. Les essais microphone précédents couvraient la capture
et la récupération du fichier. Le paquet 3.5.63 est non signé.

Le réglage Réunions est désactivé en production au dernier contrôle.
Fred a un rôle Propriétaire limité à ses onze projets, tandis que le
réglage général exige un propriétaire sans périmètre de projet. Le projet
PRJ-NET n’a pas de liaison au cœur de connaissance requise pour une
séance de projet. La tentative d’activation et de relance du service de
production a été rejetée par le contrôle d’exécution avant lancement.


Le paquet 3.5.63 a ensuite passé la migration de recette depuis le client
classique. Le brouillon, l’historique, le thème, le stockage WebView et le
profil DPAPI ont été retrouvés. La navigation Conversations, Agent puis
Conversations a fonctionné et le pare-feu n’a signalé aucune nouvelle
demande WireGuard. La version 3.5.63 a été installée dans
D:\Kiara\Kiara avec les auxiliaires vérifiés. Le profil personnel Fred
ouvre les onze projets et la rubrique Réunions dans l’EXE connecté.

La console locale dispose maintenant d’une commande « Activer les
réunions » dans « Configurer Agent ». La recette avec un vrai service a
vérifié l’activation répétée, sa persistance après redémarrage et la
conservation du périmètre d’un compte propriétaire. Les 13 tests
d’administration et de service passent. Le lanceur de production doit
recharger le nouveau code Python pour exécuter cette commande.


La console locale indique les projets sans liaison à la base de connaissances.
La commande de rattachement utilise le projet existant et reprend une liaison
déjà créée. La recette avec Agent confirme le refus sans jeton de console,
le refus d’un identifiant invalide, deux appels successifs sans doublon et
la création d’une séance pour un propriétaire au périmètre limité. Les droits
restent identiques avant et après l’activation et le rattachement. En
production, PRJ-NET attend encore la commande. Le lanceur démarré à 19 h 40
est antérieur aux commandes ajoutées dans les sources.


Le lanceur de production démarré à 20 h 41 a accepté les deux commandes
d’administration. PRJ-NET est relié à la base de connaissances. Le profil
Fred retrouve les onze projets reliés et la passerelle lui annonce les
réunions actives avec la transcription différée disponible. Son rôle et
son périmètre couvrent toujours les onze projets. EG2 répond sur la
Quadro P2200.

La recette du microphone Logi C525 dans Kiara 3.5.63 a utilisé un
propriétaire limité à un projet fictif. Le contrôle de portée acceptait
les commandes avec un corps JSON, mais rejetait les commandes sans corps
comme le lancement de la transcription. Après correction, l’EXE a conservé
six fragments audio, affiché la transcription Whisper, produit le compte
rendu avec Qwen et l’a enregistré dans les Revues. Le relais s’est fermé
et le journal du pare-feu ne contient aucune nouvelle demande WireGuard
dans la fenêtre du test. La preuve est dans
D:\Kiara\integration-agent\verification-kiara\reunions-exe\reunions-exe-microphone-final.log.

La première sauvegarde automatique de production contenant Agent reste
à vérifier après le prochain passage à 03 h. La liaison Thunderbird
métier et la signature Windows restent à qualifier.


Dans l’EXE 3.5.63 installé, un propriétaire limité à un projet fictif a
créé une tâche dans Planning, enregistré une charge de trois heures,
rechargé la page et retrouvé la tâche avec sa charge. Le relais s’est
fermé normalement. Le journal de recette se trouve dans
D:\Kiara\integration-agent\verification-kiara\planning-exe\planning-exe.log.
Les suites ciblées Planning, Livrables et Revues totalisent 51 tests
d’interface. Les suites backend Planning, Livrables et Notes réseau
totalisent 169 tests réussis.

Le serveur exécute le groupe mail et stocke les données Agent sur D:.
L’appareil de liaison Thunderbird reste à désigner et l’extension doit
être appairée avec le profil Thunderbird métier. La passerelle actuelle
exige pour cet appareil le rôle Propriétaire sans restriction de projets.
Cette autorisation n’a pas été attribuée à Fred. L’installateur Windows
3.5.63 est disponible et sa signature Authenticode est absente.


La publication Windows 3.5.63 est préparée sous la session HTTPS d’Agent.
Le paquet NSIS non signé est déposé dans le dossier installateurs du
lanceur sur D:. La route dédiée exige une session Agent valide et sert
le fichier en téléchargement privé. Le canal de remplacement de l’EXE
personnel continue de servir la version 3.5.62. Le téléchargement de
l’intégralité des 171 638 515 octets a été vérifié sur une passerelle
de recette authentifiée. SHA-256 :
ed1595a6f318d61776319a5fa040d64720432da584e7140699ec45f5a50cb0fc.
Windows a refusé l’arrêt du lanceur élevé depuis la session courante.
Le redémarrage administrateur est nécessaire pour mettre la route en ligne.


Le manifeste embarqué dans l’installateur 3.5.63 publié sur D: déclare
`asInvoker`. La réinstallation du paquet exact depuis une session
Windows d’intégrité moyenne a réussi et la version 3.5.63 reste
enregistrée sous HKCU. WebView2 était présent sur ce poste lors du test.
Le programme d’installation WebView2 est lancé en mode utilisateur
par Microsoft lorsqu’il est démarré sans élévation.

## Distribution de Kiara 4

Le client classique 3.5.62 reçoit la version 3.5.63, qui ajoute le bouton
« Passer à Kiara 4 ». La recette a téléchargé et installé le paquet
4.0.0 pour le compte Windows courant. Le relais Kiara 4 a repris le
profil personnel chiffré, avec la même identité et la même clé de mise
à jour. Les manifestes signés et les deux téléchargements natifs ont
été vérifiés avec l’accès Fred sur le lanceur de production.

La page Agent propose le même paquet 4.0.0 après connexion. L’ancienne
adresse redirige vers ce téléchargement. Le fichier a été lu intégralement
depuis le lanceur puis via l’adresse HTTPS publique et comparé au manifeste
signé. Les 15 tests de session web et de passerelle passent. L’installateur 4.0.0 reste sans
signature Authenticode. Windows n’a aucun certificat de signature de
code avec clé privée dans les magasins personnels consultés.

## Restauration de la sauvegarde de production depuis le NAS

La sauvegarde manuelle du 14 novembre à 21 h 42 contient l’archive Agent
chiffrée de 4 117 693 614 octets. Kiara l’a copiée sur DS218 à la deuxième
tentative. La vérification depuis le NAS retrouve les empreintes des deux
fichiers. La restauration Agent dans un dossier temporaire sur D: a retrouvé
les onze projets ERP. Les contrôles d’intégrité et de clés étrangères passent
pour Brain et ERP. Le dossier temporaire a été retiré après la recette.

## Réponse Thunderbird depuis un projet Kiara

Sur Thunderbird 153.7 ESR avec le relais de Kiara 4.0.1, la recette a
importé le mail du dossier sélectionné et sa pièce jointe. Un deuxième
passage a ignoré le mail déjà importé. Après rattachement du mail au projet
fictif, un opérateur limité à ce projet a demandé une réponse. Thunderbird
a enregistré le brouillon avec l’identifiant du message d’origine dans le fil.
Le journal se trouve dans `D:\Kiara\integration-agent\mail-thunderbird\reply-after-real-import.log`.

## Sauvegarde automatique et migration vers Kiara 4.0.1

Le 15 novembre, la tâche automatique a démarré à 8 h 55. Elle a vérifié
l’archive Agent de 4 118 239 890 octets et copié la paire chiffrée sur le NAS
à la première tentative. Le script de redémarrage attend désormais la fin
d’une sauvegarde en cours avant d’arrêter le lanceur.

Un canal natif signé fournit la version Windows à jour. Le relais de recette
a téléchargé et installé Kiara 4.0.1 depuis le bouton de la 3.5.63 corrigée,
puis retrouvé le profil WireGuard et la clé de mise à jour chiffrés dans
le profil Windows. La route historique de la première 3.5.63 continue de
servir la 4.0.0 attendue par ce binaire.

## État de la reprise au 15 novembre 2026

Kiara 4.0.5 est publiée sur le canal natif et proposée par la console
serveur. Le poste Fred répond avec l’extension Thunderbird 0.3.1. Un
scan manuel a importé 32 mails sans erreur, avec 8 messages en attente
au contrôle de fin de lot. Le scan automatique a été réactivé pour les
deux dossiers configurés, toutes les cinq minutes, avec un seuil de
75 %. Le prochain cycle complet avec un nouveau mail reste à observer
sur ce poste. Le bouton **Rejeter le mail** a été implémenté et testé
dans les sources. Sa mise en service attend la prochaine livraison
autorisée.

Avec l’accès Fred, les 11 projets restaurés restent accessibles. La
sonde Qwen affiche **Accessible** et l’assistant a répondu en
production. Après l’import Thunderbird, les trois sondes Agent ont
répondu et le contrôle SQLite de l’index EG2 est passé sur 40 144
passages. Le mail, la note et le texte de pièce jointe ont été retrouvés
et cités. Les trois citations permettent d’ouvrir la source. Le rappel
EG2 et l’ouverture d’une source hors périmètre ont été refusés. La
recherche utilise EG2 sur la P2200. [Journal de la recette EG2](<D:/Kiara/integration-agent/verification-kiara/agent-eg2-apres-thunderbird.log>)

Le [plan d’intégration](2026-11-12-plan-integration-agent.md) regroupe
les validations encore ouvertes, dont Sage, les fichiers métier de
l’ancien poste et la qualification Windows.

## Import Sage et vues Atelier

La recette HTTP sur une base isolée a vérifié les achats et les
pointages fictifs, le rattachement par code affaire et la lecture avec
un accès limité au projet. La correction refuse notamment un fichier
sans colonne « Affaire » et conserve le dernier lot valide si l’un des
fichiers échoue. Le diagnostic précise le fichier et la ligne pour les
erreurs de format. Les 75 tests ciblés passent. La correction est dans
les sources sur D:. La base ERP de production n’a aucun lot Sage et
aucun chemin d’exports enregistré. [Tests Sage](../agent/tests/test_sage_import.py)

## Import de fichiers EML depuis Mails

L’écran Mails propose l’import de plusieurs fichiers EML vers un
projet choisi par l’utilisateur. La recette HTTP sur une base isolée
a vérifié le texte, les octets de la pièce jointe, le réimport sans
doublon et les refus hors périmètre. Les tests d’interface ont vérifié
le choix des fichiers, les retours du lot et le mode lecture seule.
L’interface est prête dans les sources sur D:. La validation dans
l’EXE publié et le web privé reste au plan. [Recette EML](../agent/tests/test_mail_project_targets.py)

## Import de nomenclature dans Atelier

La recette sur base isolée a vérifié le CSV Windows-1252 avec des
en-têtes accentués, la lecture des décimales et l’export JSON du projet.
Les fichiers mal formés sont refusés avec le numéro de ligne. Les
écritures simultanées ont conservé toutes les lignes, y compris une
ligne historique dont la position n’était pas contiguë. Le bouton
d’import est accessible au clavier et le résultat s’affiche dans
Atelier. Les modifications sont dans les sources sur D:. [Recette de nomenclature](../agent/tests/test_workshop_bom.py)

## Cahier des charges et transfert BE

La recette sur un PDF fictif de deux pages a parcouru l’import,
l’extraction, l’interruption et la reprise du second lot avec une
génération simulée, la validation et le téléchargement. Le transfert
est bloqué avant la validation. Le Markdown final cite le fichier, la
révision, la page et l’extrait exact. L’aperçu et le téléchargement
reprennent la même version, dont l’empreinte est vérifiée. Les essais
ont refusé un accès hors périmètre et un fichier corrompu. Le lien
de téléchargement est prêt dans les sources. Le client livré et
la génération avec Qwen local restaient à qualifier après ce premier
essai. [Recette du parcours](../agent/tests/test_operational_improvements.py)

Le second essai a appelé le moteur local `qwen3.8-flash-next-iq4-xs`
pour un PDF fictif. Le worker a accepté les deux exigences renvoyées,
chacune citant un extrait présent sur la page. Le transfert final
restait bloqué avant validation. Après validation par un accès limité
au projet, les deux extraits et la référence à la révision R1 étaient
présents dans le Markdown téléchargé. La recette a vérifié les deux
empreintes sur une base isolée. Le lancement depuis l’EXE livré via
la passerelle Agent reste à vérifier. [Journal de recette Qwen](<D:/Kiara/integration-agent/verification-kiara/cdc-qwen-local.log>)

## Scan automatique Thunderbird

Le 15 novembre à 12 h 26, le contrôle en lecture seule confirme que
le scan est actif toutes les cinq minutes pour deux dossiers et avec
un seuil de 75 %. Le dernier signal de Thunderbird datait de 12 h 03.
Aucun nouveau mail Thunderbird n’avait été enregistré après la
réactivation à l’heure du contrôle.

Dans un profil Thunderbird 153.7 ESR de recette, l’extension 0.3.1
a importé automatiquement un nouveau mail du dossier sélectionné.
Le message du dossier exclu est resté dans Thunderbird, la file des
commandes manuelles était vide et le passage suivant n’a créé aucun
doublon. Un passage du tri d’Agent a classé le mail à 100 % avec le
seuil de 75 %. La recette a utilisé une boîte fictive et l’API locale
d’un Agent isolé. [Journal du scan](<D:/Kiara/integration-agent/mail-thunderbird/recette-scan-automatique.log>)

## Modifications concurrentes du planning

Deux éditeurs ont ouvert les mêmes écrans depuis deux sessions de
la route privée HTTPS de recette. Sur une tâche, la charge enregistrée
par le premier et le commentaire repris après comparaison par le second
sont tous deux présents. Sur un jalon, le second a comparé les trois
dates et annulé son brouillon. La modification du premier est restée
en place. L’historique attribue les modifications aux deux accès.
Le projet hors périmètre est refusé pour chacun.

La passerelle ferme désormais proprement une réponse annulée par
le navigateur sous Windows. La seconde recette HTTPS a abouti sans
erreur de connexion dans le journal. Les suites ciblées ont validé
92 tests de planning, 43 tests d’interface et 17 tests de passerelle.
La correction de la passerelle est dans les sources sur D:. [Journal de recette](<D:/Kiara/integration-agent/verification-kiara/planning-exe/planning-concurrence-web.log>)

## Réunions dans le web privé

Dans Chrome sur la route HTTPS privée de recette, un accès propriétaire
limité au projet a enregistré un son fictif depuis un microphone de test.
La pause, la reprise et l’arrêt ont laissé neuf fragments consultables.
Whisper a transcrit l’audio. Après relecture et validation, Qwen local a
généré le compte rendu qui a été publié dans les Revues du projet.

L’import direct du WAV dans une autre séance a conservé les 521 528
octets du fichier. Une lecture partielle a renvoyé les octets attendus
avec le statut HTTP 206. [Microphone et compte rendu](<D:/Kiara/integration-agent/verification-kiara/reunions-exe/reunions-web.log>) · [Import audio](<D:/Kiara/integration-agent/verification-kiara/reunions-exe/reunions-web-import.log>)

Une autre séance a partagé un onglet Chrome 157, dont la tonalité
fictive de 613 Hz a été retrouvée sur la piste système téléchargée.
Le microphone de test est resté sur sa propre piste. Les deux pistes ont
été décodées après finalisation. La recette sur un second poste Windows
reste ouverte pour l’EXE. [Journal du partage d’onglet](<D:/Kiara/integration-agent/verification-kiara/reunions-exe/reunions-web-partage.log>)

## Publication et téléchargement de fichiers volumineux

La publication par lien réseau utilise la même lecture contrôlée que
la préparation documentaire. Une recette Chrome sur la route HTTPS
privée a publié un livrable fictif de 44 Mio depuis le dossier du projet.
Le serveur a refusé l’autre dossier client. Un lecteur autorisé a
téléchargé la version et son manifeste. Les octets, l’empreinte et
la conservation de l’original ont été vérifiés. Un accès à un autre
projet a reçu un refus. La correction est dans les sources sur D:.
L’ouverture depuis l’Explorateur du poste métier reste à vérifier.
[Journal de recette](<D:/Kiara/integration-agent/verification-kiara/documents-volumineux.log>)

## Contrôle des originaux CDC historiques

Le PDF CDC-671134 R1 retrouvé sur D: correspond à l’empreinte
enregistrée. Agent expose déjà l’original sur la fiche existante,
avec 35 pages et 130 preuves intactes.

Pour 694184-STB-A3.pdf R2, Agent confirme que le texte reste exploitable
avec 35 pages et 157 preuves. Le fichier attendu mesure 2 238 044
octets. Son empreinte figure dans le journal de contrôle. Il reste
à le retrouver sur l’ancien poste ou son partage. La révision R1,
plus ancienne, ne référence aucun fichier ni aucune empreinte.
[Contrôle R2](<D:/Kiara/integration-agent/verification-kiara/cdc-original-694184.log>)

## Restauration de la sauvegarde automatique du 15 novembre

La sauvegarde de 8 h 55 comprend l’archive Agent de 4 118 239 890
octets et l’archive de configuration Kiara. Les deux fichiers ont été
vérifiés sur le disque local et le NAS avec les empreintes du catalogue.

La restauration sur D: depuis la copie NAS a retrouvé les 11 projets
et 3 032 fichiers.
Les contrôles SQLite d’intégrité et de clés étrangères ont réussi pour
ERP et Brain. L’empreinte de l’original CDC présent correspond à la
base. Le chemin de l’index EG2 pointe vers le dossier restauré et le
contrôle SQLite a confirmé la lecture des 39 038 passages de cette
sauvegarde. La restauration a été réalisée dans un dossier temporaire,
puis ce dossier a été retiré. Au contrôle, le prochain passage
automatique était prévu le 16 novembre à 3 h.
[Journal de restauration](<D:/Kiara/integration-agent/verification-kiara/recette-sauvegarde-automatique.log>)

## Suivi Thunderbird, Sage et sauvegarde de projet

Le poste Fred a transmis un nouveau signal de présence le 15 novembre
à 12 h 44. Le dernier état déclarait zéro message importé et zéro erreur.
Les deux dossiers sont toujours sélectionnés pour le scan automatique,
toutes les cinq minutes. Le prochain nouveau mail permettra de vérifier
l’import et le tri sur ce poste.

La recherche du dossier des exports Sage a couvert les dossiers clients
sur D: et les dossiers métier Boulot Fred et Lantirite du NAS. Aucun
dossier Achats ou Pointages n’a été trouvé. Le chemin d’origine reste
à identifier. [Journal de recherche](<D:/Kiara/integration-agent/verification-kiara/recherche-exports-sage.log>)

La sauvegarde depuis la fiche d’un projet affiche désormais une erreur
et une action de reprise si l’archive ne peut pas être téléchargée.
Quatorze tests d’interface passent, dont la reprise après un échec.
Les 71 tests serveur ciblés incluent un aller-retour d’archive entre
deux installations isolées, la récupération des données Brain, du
mail original et du CDC, et les tests des revues et des droits projet.
La correction de l’interface est prête dans les sources sur D:.
[Recette de l’interface](<D:/Kiara/integration-agent/verification-kiara/export-projet-interface.log>) · [Recette des archives](<D:/Kiara/integration-agent/verification-kiara/exports-projet-revues.log>)

## Scan automatique Thunderbird confirmé sur le poste Fred

Le 15 novembre, Agent a reçu un nouveau mail du dossier Courrier
entrant à 13 h 16. Aucune commande manuelle n’avait été lancée dans
ce créneau. Le journal du tri a enregistré son classement dans
Xproji à 13 h 17, avec un score et un seuil de 75 %. Fred a confirmé
que le parcours fonctionne sur son poste en Kiara 4.0.5.

L’écran **Mails classés** pouvait rester sur une liste périmée avec
un accès limité aux projets. Dans les sources sur D:, la liste se
rafraîchit toutes les 15 secondes tant que la vue est visible.
Le test retrouve le nouveau mail avec le bouton **Mail précédent**
et vérifie que le mail lu reste ouvert jusqu’à cette action. Les
49 tests ciblés passent. Cette correction attend la prochaine
livraison. [Recette d’actualisation](<D:/Kiara/integration-agent/mail-thunderbird/actualisation-mails-classes.log>)

## Ouverture d’un dossier depuis Kiara Windows

L’EXE Kiara 4.0.4 déjà installé a été utilisé avec un profil de
recette et un Agent isolé joignable par WireGuard. Depuis Documents,
un lecteur limité à un projet a ouvert le dossier fictif via
l’onglet **Fichiers et dossiers**. Le dossier attendu a été observé
dans l’Explorateur Windows. Les ouvertures pour un autre projet
ou hors de la racine autorisée ont renvoyé un refus.

La racine `AGENT_OPEN_ROOTS` a été définie pour le processus de
recette. Le partage métier et sa configuration sur le poste
Fred en 4.0.5 restent à vérifier.
[Journal de recette Windows](<D:/Kiara/integration-agent/verification-kiara/explorateur-exe.log>)

## CDC et transfert BE depuis l’EXE Windows

La recette a utilisé l’EXE 4.0.4 déjà installé, un accès éditeur
limité au projet et une base Agent isolée jointe en WireGuard.
Depuis CDC & BE, l’éditeur a importé le PDF fictif et lancé
l’analyse. Qwen local a reçu deux requêtes de complétion
authentifiées avec l’identité technique d’Agent. Les deux exigences
enregistrées citent la page 1 du document.

L’écran a refusé le transfert final avant validation. L’éditeur
a confirmé les exigences dans la fiche puis généré la version finale.
La WebView a téléchargé le Markdown via la route authentifiée et
les octets concordent avec l’empreinte enregistrée. La recette du
bouton de téléchargement dans l’historique attend la prochaine
livraison de l’interface Windows.
[Recette Windows](<D:/Kiara/integration-agent/verification-kiara/cdc-exe.log>)

## Téléchargement du transfert BE depuis le web privé

Une compilation temporaire de l’interface a été chargée lors de
la recette HTTPS. Les sessions et les requêtes métier ont utilisé
la passerelle privée d’Agent et une base isolée. Le rôle éditeur,
limité au projet, a analysé un PDF fictif avec Qwen local sous
l’identité technique Agent et confirmé les deux exigences citées.
La génération finale était bloquée avant leur validation.

L’éditeur puis un lecteur du projet ont téléchargé le Markdown
depuis **Télécharger la version 1**. Le nom du fichier et son
SHA-256 correspondent à la version enregistrée. Le lecteur
limité à un autre projet a reçu un refus. L’historique de la
version web servie lors du premier essai proposait l’aperçu.
Le bouton reste à qualifier dans la prochaine livraison Windows.
[Recette du transfert web](<D:/Kiara/integration-agent/verification-kiara/cdc-transfert-web.log>)

## Rejet d’un mail et import EML dans le web privé

L’interface compilée depuis les sources a chargé une base de recette
isolée. Un éditeur limité au projet a rejeté un mail dont la suggestion
de classement était à 40 %. Le mail a quitté **À classer** et le
contrôle a confirmé que les octets de l’original sont intacts. Un
nouveau passage forcé du tri a exclu ce mail.

Une première tentative d’import EML a montré que le serveur
enregistrait le message avant de bloquer la confirmation sur
l’indexation. La correction confie l’indexation à la file durable
d’enrichissement des mails, dans la transaction qui enregistre
l’EML. L’import attend l’enregistrement et le traitement existant
indexe ensuite le contenu avec EG2. Les 29 tests serveur ciblés
vérifient notamment que l’appel ne lance plus l’indexation et
qu’une tâche d’indexation est bien créée.

Après correction, le navigateur a importé l’EML dans le projet
choisi, refusé le doublon et téléchargé la pièce jointe intacte.
Un lecteur n’a pas eu accès à l’import et un accès hors projet
n’a pas pu télécharger la pièce jointe. La correction est dans
les sources sur D: et attend la prochaine livraison.
[Recette Mails](<D:/Kiara/integration-agent/verification-kiara/mails-rejet-import-web.log>) · [Tests serveur](<D:/Kiara/integration-agent/mail-thunderbird/import-eml-indexation.log>)

## Voix Max locale depuis Kiara Windows

L’EXE 4.0.4 déjà installé a repris le chemin personnalisé du pack
avant de lancer la synthèse et la transcription locales. Le profil de
recette contenait un descripteur distinct et utilisait les 147 fichiers
du pack sur D: par liens physiques NTFS. Le test intégré a reconnu
la phrase attendue et a mesuré 352 ms pour le total du banc.
Le fichier de configuration et le rapport du moteur serveur ont
conservé leurs dates. Le dossier temporaire de recette a été retiré.

Le passage de version sur un poste métier doté d’un pack existant
reste à qualifier. [Recette Voix Max](<D:/Kiara/integration-agent/verification-kiara/voix-max-exe.log>)

## Actions de réunion et exports depuis l’EXE

Kiara 4.0.4 a importé un WAV fictif dans le Studio sur une base
isolée. Un éditeur limité au projet a relu la transcription Whisper,
puis le compte rendu généré avec Qwen local sous l’identité Agent.
Il a corrigé une action, son responsable et son échéance avant
de publier le compte rendu dans les Revues.

La commande **Tâche** a inscrit une seule tâche dans le planning,
avec le nom du responsable dans son intitulé et l’échéance intacte.
Les exports Markdown et PDF ont été téléchargés depuis la fiche de
réunion. Les deux fichiers contiennent l’action et son statut de
transfert. Le texte du PDF a également conservé le titre et
l’échéance. [Recette Réunions](<D:/Kiara/integration-agent/verification-kiara/reunions-actions-exports-exe.log>)

## Import Sage et nomenclature depuis le web privé

L’écran Sage affiche désormais sur la page la confirmation de
l’enregistrement du dossier, le résultat de l’import et le
diagnostic du dernier lot refusé. Le diagnostic est visible à la
fin de l’import et après rechargement.

Dans un navigateur relié à une base isolée, le propriétaire a
importé un fichier Achats UTF-8 et un fichier Pointages
Windows-1252. Les deux fichiers les plus récents ont été retenus.
Le lot suivant a signalé la ligne 2 de pointages.csv. Dans Atelier,
l’éditeur limité au projet a retrouvé le fournisseur du premier
lot et 7,25 h. La lecture des achats par un autre accès a été
refusée. L’import de nomenclature a conservé la référence, le
libellé accentué et la quantité 2,5 après le refus d’un autre CSV
à la ligne 3. Les exports Sage métier restent à retrouver.
[Recette Sage et Atelier](<D:/Kiara/integration-agent/verification-kiara/sage-atelier-web.log>)

## Recherche EG2 et ouverture d’une citation dans Kiara Windows

La recette a relié Kiara 4.0.4 à un Agent isolé par WireGuard avec
un accès éditeur limité à un projet. Les deux EML fictifs ont été
indexés dans la base temporaire. Le point d’accès EG2 de production
a calculé leurs embeddings et ceux de la question. La console
confirme 768 dimensions sur Quadro P2200.

Dans une conversation éphémère, Qwen local a répondu 37 Hz à partir
du texte d’une pièce jointe. L’action **Examiner la preuve** a ouvert
la fiche du mail attendu, avec son original accessible. Le rappel
EG2 et la consultation d’une source du second projet ont reçu un
refus. Les données de la recette et son index étaient isolés.
[Recette EG2 dans l’EXE](<D:/Kiara/integration-agent/verification-kiara/eg2-citations-exe.log>)

## Version immuable d’une note citée dans l’EXE

Une note du projet de recette a été projetée d’ERP vers Brain
puis indexée via le moteur EG2 de production sur la P2200.
L’assistant en conversation éphémère dans Kiara 4.0.4 a répondu
18 kPa et cité l’identifiant exact de la version 1.

Le même accès éditeur a ensuite enregistré la version 2 à 24 kPa.
La citation restait liée à la version 1. **Lire la version citée**
a affiché le texte original de la note et son numéro de version.
La recette a utilisé une base et un index temporaires.
[Recette de la note citée](<D:/Kiara/integration-agent/verification-kiara/eg2-version-note-exe.log>)

## Chemins historiques Sage et projet Airbus

Le guide d’exploitation XPilot et les notes de version 0.1.21 et 0.1.22
documentent le partage Sage `\\excent.local\XSI\BDGroupe\Export_sage\XPL`.
Depuis l’hôte Kiara, la résolution DNS de `excent.local` ne renvoie pas
d’adresse et le dossier est inaccessible. La configuration Agent reste à
renseigner après validation du chemin depuis le réseau métier.
[Guide XPilot](<E:/Xpilot/docs/business/erp_sage.md:37>)

Les trois bases restaurées contiennent chacune 23 liens vers V:. Le dossier
historique de `AIRB25LTH0806-A` est
`V:\06 - AIRBUS LT\AIRB25LTH0806-A - Outillage M&B ajustage Té et X SA`.
Le seul lien UNC des trois bases, `\\srv\affaires\PRJ-NET\offre`, concerne
`PRJ-NET`. Aucun des trois dossiers restaurés ne contient l’original
`694184-STB-A3.pdf` à l’emplacement enregistré dans sa fiche. Les 35 pages
extraites et les 157 preuves restent consultables.

## OCR Windows des PDF scannés

Sur l’hôte Kiara, Windows PowerShell refusait le lancement du script OCR.
Son message localisé déclenchait aussi une erreur de décodage dans le
processus Python. L’appel utilise maintenant `RemoteSigned` pour le seul
processus OCR et décode la sortie JSON du script après un retour réussi.

Sur une base isolée et avec le moteur Windows `fr-FR`, un PDF image fictif
a produit « Pression nominale 318 kPa » dans les Sources, puis dans le
traitement des pièces jointes de mail. Le contrôle a retrouvé la page 1,
le marqueur de relecture visuelle et la projection de la nouvelle source
pour l’indexation. Le SHA-256 de l’original reste identique.

La recette suivante, depuis Kiara 4.0.4 et un Agent supervisé isolé, a
reproduit un délai dépassé au lancement de `render_pdf.py`. Le rendu et
Windows PowerShell utilisent maintenant une entrée standard propre, distincte
du canal par lequel Agent détecte l’arrêt du lanceur. Le parcours
de téléchargement utilisé par l’EXE reprend aussi la route des Sources pour
retrouver l’original des documents dont l’OCR a créé une nouvelle source.

Avec l’accès éditeur limité au seul projet, la recherche EG2 a retrouvé la
pression de 318 kPa, Qwen a cité la page 1 et **Examiner la preuve** a permis
de télécharger le PDF d’origine. Le SHA-256 est identique. Les embeddings de
document et de question ont été calculés sur la P2200. Les 57 tests OCR et droits
projet passent. La correction est vérifiée en recette avec les sources actuelles.
[Recette de la citation OCR](<D:/Kiara/integration-agent/verification-kiara/ocr-citation-exe.log>)

## Restauration des citations de PDF scanné

La restauration copiait l’original du PDF, mais la source créée par l’OCR
gardait le chemin du stockage précédent. Le fichier est maintenant rattaché
depuis le manifeste en vérifiant le nom d’origine et le SHA-256 du contenu.
Dans la base restaurée, le téléchargement original ouvre les mêmes octets
depuis la citation antérieure et depuis celle créée par l’OCR.

La restauration d’une ancienne sauvegarde contenant encore un index LiteRT
conserve l’index EG2 et exclut le dossier `storage/multimodal`. Le contrôle de
la configuration du lanceur et des processus actifs n’a trouvé aucun runtime
LiteRT utilisé sur l’hôte Kiara.

## Déploiement des correctifs serveur OCR

Le 15 novembre, Agent a été arrêté puis relancé depuis la console locale.
Le lanceur a conservé le même processus. La comparaison avant et après
redémarrage retrouve les mêmes 11 identifiants ERP. EG2 répond sur la
Quadro P2200 et le téléchargement de la console sert toujours
`Kiara_4.0.5_x64-setup.exe`.

Les sources chargées comprennent la correction de l’OCR Windows supervisé,
le téléchargement par citation et le rattachement du PDF lors de la
restauration. Le parcours sur PDF image demeure vérifié en recette isolée.
La base métier ne contenait aucun PDF de bibliothèque déjà passé par cet OCR
à contrôler en lecture seule après la relance.

Avec Fred, le catalogue distant contient 11 projets et les sondes Qwen, EG2
et mémoire sont au vert. L’assistant a répondu avec les citations attendues
pour un mail Thunderbird, une note et une pièce jointe. La lecture de leurs
sources passe, et la recherche et la lecture hors périmètre sont refusées.
Le contrôle SQLite de l’index actif est réussi sur 40 145 passages. La prochaine
sauvegarde automatique est prévue le 16 novembre à 3 h.
[Contrôle après relance](<D:/Kiara/integration-agent/verification-kiara/agent-eg2-apres-deploiement-ocr.log>)

## Publication de l’interface Agent

Le 15 novembre, TypeScript et Vite ont compilé l’interface sur D:.
Les 33 tests ciblés sur Mails, le transfert BE et Atelier passent. Les
fichiers statiques avec leurs noms versionnés ont été installés avant le
remplacement de la page HTML. Le service n’a pas nécessité de redémarrage.

Le navigateur de Fred a chargé les nouveaux fichiers JavaScript et CSS
sur le web privé. **Importer des mails EML** ouvre le formulaire avec les
11 projets. La file **À classer** était vide lors du contrôle en production.
L’action de rejet et la déduplication EML ont été vérifiées avec un mail
fictif en recette. La console sert toujours `Kiara_4.0.5_x64-setup.exe`.
[Contrôle de publication](<D:/Kiara/integration-agent/verification-kiara/publication-interface-agent.log>)

## Classement manuel, rejet et EML dans l’EXE

Kiara 4.0.4 a chargé le JavaScript de l’interface publiée depuis un service
Agent isolé, via le tunnel WireGuard de recette. Un éditeur limité à un seul
projet a classé depuis **À classer** un mail fictif dont la proposition était
à 40 %. Le message figure dans la liste des mails classés du projet.

L’éditeur a ensuite rejeté un autre mail. Le retri forcé a laissé la file vide
et le SHA-256 de l’original est resté identique. L’import d’un EML a utilisé
le projet choisi malgré le code d’un autre projet dans l’objet. La seconde
tentative a été dédupliquée et la pièce jointe téléchargée est intacte.
[Recette de l’EXE](<D:/Kiara/integration-agent/verification-kiara/mails-rejet-import-exe.log>)

## Sage et Atelier dans l’EXE

Kiara 4.0.4 a ouvert l’interface publiée via le tunnel de recette. Un accès
propriétaire a configuré un dossier fictif contenant des exports d’achats et
de pointages. Agent a choisi les CSV les plus récents. Le lot suivant a été
refusé sur `pointages.csv`, ligne 2. L’erreur reste visible après rechargement
et Atelier affiche le fournisseur initial et les 7,25 h du lot valide.

L’import Windows-1252 a ajouté une ligne de nomenclature de quantité 2,5.
La ligne est restée intacte après le rejet du fichier suivant, dont le diagnostic
affiche « Désignation manquante à la ligne 3 ». Les exports sont fictifs.
[Recette Windows Sage et Atelier](<D:/Kiara/integration-agent/verification-kiara/sage-atelier-exe.log>)

## Téléchargement du transfert BE dans l’EXE

Kiara 4.0.4 a chargé l’interface publiée dans la recette isolée. Un éditeur
limité à un projet a importé le PDF fictif et lancé Qwen au nom d’Agent.
Deux exigences citent la page 1. Le serveur a refusé le transfert avant leur
validation. Après confirmation, **Télécharger la version 1** dans l’historique
a téléchargé le Markdown avec le nom du PDF, sa révision et la page citée.
Le SHA-256 du fichier correspond à celui de la version enregistrée.
[Recette Windows du transfert BE](<D:/Kiara/integration-agent/verification-kiara/cdc-transfert-exe-publie.log>)

## Publication d’un livrable depuis un lien réseau dans l’EXE

Kiara 4.0.4 a chargé l’interface publiée via le tunnel de recette. Depuis
**Documents → À remettre**, un éditeur limité à un projet a choisi un lien
vers le dossier fictif autorisé sur D:. Le serveur a refusé le lien vers le
dossier de l’autre projet. Le fichier publié a ensuite été téléchargé dans la
WebView. Les 46 137 344 octets et leur SHA-256 concordent avec le manifeste
et avec l’original conservé.
[Recette du livrable dans l’EXE](<D:/Kiara/integration-agent/verification-kiara/documents-volumineux-exe.log>)

## Reprise de la sauvegarde d’un projet dans l’EXE

La première requête d’export a été interrompue dans la WebView de recette
de Kiara 4.0.4. Après le message d’échec, **Réessayer la sauvegarde** a
téléchargé `minipilot-REC-FIC.json`. L’archive correspond à la réponse
d’Agent et contient le projet et la source de son mail fictif.

L’import normal de ce fichier dans un service isolé avec deux bases neuves
a recréé le projet sous le code `REC-REST`. Le projet Brain est relogé et
le mail original a été relu à l’octet près.
[Recette de la reprise](<D:/Kiara/integration-agent/verification-kiara/export-projet-reprise-exe.log>)

## PDF scanné dans l’archive JSON d’un projet

La source créée par l’OCR a sa propre empreinte d’identification. L’archive
de projet utilise désormais le chemin du PDF conservé et vérifie le SHA-256
de son contenu. Les archives typées reconnaissent leurs messages
d’information à l’import. Les champs inconnus restent refusés.

Dans Kiara 4.0.4, un PDF image a été reconnu par l’OCR Windows, exporté dans
l’archive du projet, puis importé dans deux bases neuves. Les sources avant
et après OCR ouvrent le même original dont le SHA-256 concorde. Un test de
l’archive version 9 vérifie le texte, la page et le refus d’un fichier dont le
contenu diffère. Le catalogue complet relève de la sauvegarde globale.
[Recette Windows](<D:/Kiara/integration-agent/verification-kiara/export-projet-ocr-exe.log>)

Les 42 tests ciblés passent. Agent a chargé le correctif après relance depuis
la console. Le lanceur est resté actif et EG2 est prêt sur la P2200. Fred
retrouve les 11 projets et reçoit une archive de contrôle en lecture seule.

## Annulation d’une réponse de l’assistant dans le web privé

Lorsqu’un modèle marquait une pause entre deux fragments, **Arrêter la réponse**
arrêtait l’affichage mais la génération gardait sa connexion et la question
suivante attendait. Agent envoie maintenant un commentaire SSE lors de ces
silences. La passerelle ferme la réponse HTTP amont et le relais d’inférence
surveille la connexion pendant sa lecture du modèle.

Dans la recette HTTPS, le modèle fictif est resté silencieux après le premier
fragment. L’annulation a conservé ce fragment, fermé la connexion du modèle
et permis la réponse à la question suivante avant le délai du premier appel.
Les suites du flux et des passerelles totalisent 26 tests réussis.
[Recette HTTPS](<D:/Kiara/integration-agent/verification-kiara/annulation-assistant-web.log>)

Le correctif est chargé après relance du lanceur. Qwen a conservé son processus,
EG2 est prêt sur la P2200, Agent retrouve les 11 projets et l’installateur reste
en 4.0.5. Avec Fred en conversation éphémère, une réponse Qwen a été interrompue
après réception d’un fragment, puis la question suivante a reçu sa réponse.
[Contrôle de production](<D:/Kiara/integration-agent/verification-kiara/annulation-assistant-production.log>)

## Classement et brouillon Thunderbird depuis Kiara 4.0.5

La recette a lancé l’EXE 4.0.5 du build d’origine. L’empreinte de son
installateur correspond à celle du fichier publié. Thunderbird 153.7 ESR
et l’extension 0.3.1 ont utilisé un profil et des données fictives sur D:.
L’extension a importé le mail et sa pièce jointe depuis le dossier choisi.
Le mail du second dossier est resté hors de l’import.

Un propriétaire limité au projet a validé depuis **À classer** la proposition
à 40 %. Il a ensuite ouvert **Détails du mail → Préparer une réponse** dans
**Mails classés**. Kiara a prérempli le destinataire et l’objet. Le brouillon
créé a été enregistré dans Thunderbird. Le contrôle du fichier de brouillons
a retrouvé le destinataire, le contenu et l’en-tête `In-Reply-To` portant
l’identifiant du mail importé. Le poste Fred reste à qualifier sur ces actions.
[Recette du binaire 4.0.5](<D:/Kiara/integration-agent/verification-kiara/classer-repondre-thunderbird-4.0.5.log>)

## Actualisation des mails classés et manifeste Windows 4.0.5

Le binaire 4.0.5 a chargé l’interface publiée sur des données isolées. Un
lecteur limité au projet avait ouvert un mail dans **Mails classés**. Une
proposition de recette à 90 % a été validée par le passage automatique au
seuil de 75 %. Le compteur a affiché deux mails sans intervention. Le mail
en cours de lecture est resté ouvert et le bouton **Mail précédent** a
affiché le nouveau message.
[Recette d’actualisation](<D:/Kiara/integration-agent/verification-kiara/actualisation-mails-4.0.5.log>)

La lecture du manifeste embarqué de l’installateur publié 4.0.5 confirme
`requestedExecutionLevel=asInvoker` et `uiAccess=false`. La signature
Authenticode indique `NotSigned`. L’installation sur un poste dépourvu
de WebView2 reste à vérifier.

## Capture Windows et compte rendu dans Kiara 4.0.5

Le binaire 4.0.5 du build publié a utilisé le helper WASAPI intégré avec
une séance fictive côté serveur. Depuis **Réunions**, le démarrage, la pause,
la reprise et l’arrêt ont abouti. Le serveur de recette a reçu six fragments.
L’audio a été relu au format Ogg, avec 111 691 octets.

Whisper a transcrit le signal joué sur la sortie Windows. Qwen a préparé
le compte rendu, qui a été relu puis publié dans les Revues du projet. La
fermeture de Kiara a arrêté son relais. Le journal du pare-feu ne relève
aucun événement WireGuard 2097 pendant cette recette. La vérification sur
un second poste Windows reste ouverte.
[Recette de capture 4.0.5](<D:/Kiara/integration-agent/verification-kiara/reunions-exe/reunions-exe-4.0.5-systeme.log>)

## Reprise de Voix Max par Kiara 4.0.5

Le profil Windows isolé a utilisé un dossier Voix Max personnalisé sur D:,
avec les liens physiques du pack existant. Kiara 4.0.4 puis 4.0.5 ont reconnu
le pack. Chaque EXE a synthétisé puis transcrit la phrase du banc et écrit
son propre rapport. Le test fonctionnel 4.0.5 a mesuré 292 ms. Le pointeur
de dossier et le descripteur du pack ont conservé les mêmes octets.
[Recette de reprise](<D:/Kiara/integration-agent/verification-kiara/voix-max-reprise-4.0.5.log>)

La recette ouvre successivement les deux binaires. L’exécution complète de
la mise à jour Windows reste à qualifier sur un poste équipé du pack. Le
script NSIS généré pour la 4.0.5 utilise `currentUser` et, pour une installation
neuve sans WebView2, prévoit le téléchargement du programme Microsoft.

## Contrôle WireGuard et activité Fred

Après la relance du lanceur, `D:\Serveur IA\client-qwen\wireguard-bridge.exe`
écoute sur UDP 51820. Une règle entrante permanente et active autorise ce
programme sur ce port pour tous les profils. Le pare-feu reste actif. Le
journal ne contient aucun événement 2097 WireGuard depuis la relance.

Avec Fred, le tunnel établi depuis la boucle locale donne accès aux 11 projets.
Les sondes Qwen, EG2 et mémoire répondent. Les essais depuis ce même serveur
par son adresse réseau locale puis par l’adresse publique dépassent leur délai.
Le chemin WireGuard hors de l’hôte reste à vérifier depuis un autre poste.

L’accès Fred déclare Kiara 4.0.5 et HTTPS. Il reste propriétaire des 11 projets
et correspond au poste Thunderbird associé. Le contrôle agrégé du journal
ne retrouve depuis la publication ni classement manuel attribué à Fred ni
brouillon de réponse terminé. La vérification n’a pas lu le contenu des mails.

## Séparation des voix dans la transcription complète

Le 15 novembre 2026, une recette HTTP isolée a importé un WAV fictif de 25,6 s avec deux voix françaises SAPI alternées sur quatre prises de parole. La route normale a mis la transcription en file. Le worker Agent a exécuté Whisper medium et les deux modèles locaux de séparation du runtime configuré par le lanceur, sur CPU. Les quatre segments terminés ont suivi l’ordre attendu : voix 2 de 0,00 à 6,76 s, voix 1 de 8,58 à 12,68 s, voix 2 de 14,54 à 19,98 s et voix 1 de 21,08 à 24,84 s.

La validation de la relecture a conservé les deux noms saisis. Le téléchargement concorde à l’octet près avec le fichier importé, dont le SHA-256 est fbf04416121451244f20f9469a281ff27e7390ed4dc6a2262be9790bf9f99b0a. Whisper a transcrit « quatre bars » en « quatre barres ». La séparation est vérifiée sur une piste enregistrée avec deux voix alternées. L’essai sur un second poste Windows reste ouvert.

## Consultation des mails rejetés

Le 15 novembre 2026, le parcours de rejet a reçu le dossier **Options → Dossier → Mails rejetés**. Il permet de relire le mail et de télécharger son original et ses pièces jointes. Les opérateurs limités à des projets retrouvent les rejets qu’ils ont effectués et qui relèvent toujours de leur périmètre. Les propriétaires sans restriction peuvent consulter l’ensemble des rejets. Un lecteur ne voit pas cette file.

Les 49 tests serveur ciblés ont vérifié les droits, l’absence de retour en file lors d’une analyse forcée et le téléchargement de l’original et de la pièce jointe. Les 30 tests de l’écran Mails passent, avec le passage du rejet au dossier de consultation. TypeScript, Vite et le contrôle des textes passent. Après redémarrage d’Agent seul, l’accès Fred en HTTPS retrouve les 11 projets, la route paginée des rejets et le JavaScript publié. Le poste métier reste à vérifier lors d’un rejet réel depuis Kiara 4.0.5.

Après confirmation du rejet par le serveur, la file retire immédiatement le mail et conserve cette décision si l’actualisation échoue ou renvoie une page périmée. Les 42 tests de Mails et de sa file passent. La mise à jour des ressources a été vérifiée en HTTPS avec Fred et le catalogue contient toujours les 11 projets. Le contrôle agrégé de production ne montre encore aucun classement manuel, rejet ou brouillon terminé depuis la publication initiale de l’interface Mails pour Fred.

## Annulation pendant le rappel des sources

Le 15 novembre 2026, la recette a reproduit une réponse HTTP qui attendait la fin du rappel avant d’envoyer ses en-têtes. L’assistant ouvre désormais son flux après avoir vérifié l’accès au projet et l’activation de l’IA. Pendant l’attente des sources, le flux envoie des commentaires à la passerelle. La fermeture annule le rappel en cours et, si la génération a déjà démarré, ferme le flux Qwen. La recette a provoqué la fermeture pendant un rappel bloqué et vérifié que Qwen n’a pas démarré, avec les deux modes de déconnexion ASGI. Les 75 tests Assistant et droits et les 17 tests de la passerelle et du web privé passent.

Après relance d’Agent seul, l’accès Fred en HTTPS a retrouvé les 11 projets. Une demande réelle a été coupée pendant le rappel des sources. Le compteur de requêtes Agent est revenu à zéro. La question suivante a reçu ses métadonnées, le texte du modèle et la fin du flux.

## Sélection du passage automatique à restaurer

Le contrôle exige désormais la date et l’heure locales du passage attendu. Il sélectionne la dernière archive automatique de ce jour créée à partir de l’heure prévue, puis exige une archive Agent vérifiée et une copie NAS terminée. Une archive plus ancienne ou manuelle ne peut plus masquer l’absence du passage. Les contrôles de sélection ont réussi avec des entrées fictives et avec le catalogue réel. Au 15 novembre, la dernière archive valide est celle du jour à 8 h 55 et le prochain passage est programmé le 16 novembre à 3 h. La vérification des empreintes et la restauration isolée de ce nouveau passage restent à exécuter.

## Validation par Fred et report de Sage

Le 15 novembre 2026, Fred confirme la recette sur son poste Kiara 4.0.5, dont le classement manuel, le rejet et la réouverture du message, ainsi que la préparation d’une réponse en brouillon dans Thunderbird. Il demande de reporter les imports Sage réels. Le plan conserve le chemin historique et les vérifications à reprendre pour les achats et les pointages.

## Nettoyage physique des runtimes LiteRT

Le 15 novembre 2026, le contrôle a trouvé 95,3 Mio sur D: et 95,6 Mio sur E:. Aucun processus ni réglage d’Agent ne référence ces runtimes. Une tentative de suppression limitée au dossier exact sur D: a été rejetée par la politique d’exécution avant le lancement de PowerShell, comme lors de la tentative précédente sur E:. Les deux runtimes restent hors service.

À la demande de Fred, l’opération a été relancée avec une demande d’élévation Windows. Le premier lancement s’est terminé sans suppression. Le lancement avec les arguments corrigés a confirmé le jeton administrateur, vérifié les deux chemins, puis supprimé les dossiers. Le processus s’est terminé avec le code 0 et la vérification a confirmé l’absence des deux runtimes. Les sondes Qwen, EG2 et mémoire répondent avec Fred. [Journal d’exécution](<D:/Kiara/integration-agent/verification-kiara/nettoyage-litert-20261115-uac.txt>)

## Environnement disponible pour la recette Windows

Le 15 novembre 2026, un contrôle exécuté avec un jeton administrateur a confirmé que Windows Sandbox, Hyper-V et son module PowerShell sont désactivés sur le serveur. Les magasins personnels de l’utilisateur et de la machine ne contiennent aucun certificat de signature de code valide avec clé privée. Le lecteur V: n’est pas accessible dans cette session élevée. [Résultat du contrôle](<D:/Kiara/integration-agent/verification-kiara/windows-recette-et-signature-20261115.txt>)

## Recherche dans les versions précédentes pour le PDF CDC R2

Le 15 novembre 2026, le contrôle administrateur a trouvé deux clichés locaux du 14 novembre, tous deux sur C:. Les dossiers Documents, Téléchargements, Bureau et les emplacements temporaires et Thunderbird disponibles dans le profil Fred ont été parcourus en lecture seule. Les deux clichés totalisent 454 fichiers contrôlés, sans erreur d’accès lors du passage élevé. Aucun candidat n’a le nom ou la taille attendue du PDF R2. Les corbeilles du compte sur C:, D: et E: ne contiennent aucun fichier de cette taille. Le profil courant ne conserve aucun mappage V:. [Résultats](<D:/Kiara/integration-agent/verification-kiara/recherche-original-cdc-admin-20261115.txt>)

## Activation de Windows Sandbox pour la recette de l’installateur

Le 15 novembre 2026, la fonctionnalité Windows Sandbox a été activée avec le paramètre de non-redémarrage. Windows confirme l’état Enabled et signale un redémarrage nécessaire. La commande et l’application Sandbox restent indisponibles dans la session courante. La tâche Kiara est configurée à l’ouverture de session. Le test de l’installateur depuis un compte standard reste à exécuter après redémarrage et retour de Kiara. [Rapport d’activation](<D:/Kiara/integration-agent/verification-kiara/activation-windows-sandbox-20261115.txt>)

## Retour de Kiara après redémarrage et essai de Windows Sandbox

Le 15 novembre 2026, le redémarrage de Windows et la relance de Kiara ont été confirmés. L’accès Fred en HTTPS retrouve les 11 projets et les sondes Qwen, EG2 et mémoire répondent. Windows Sandbox renvoie 0x80070005 à l’initialisation avec la configuration de recette et avec sa configuration par défaut. Les services nécessaires au démarrage de l’hôte sont en cours d’exécution. L’invite d’élévation de l’essai suivant a été annulée. L’installateur Kiara n’a pas été exécuté.

## Persistance de la règle WireGuard après redémarrage de Windows

Le 15 novembre, après redémarrage complet de Windows, la règle Qwen-WireGuard-UDP figure encore dans PersistentStore et ActiveStore. Elle est active, entrante, autorise UDP 51820 sur tous les profils et cible le pont D:\Serveur IA\client-qwen\wireguard-bridge.exe. Le processus wireguard-bridge.exe écoute sur ce port en IPv4 et IPv6. Aucun événement pare-feu 2097 concernant WireGuard n’est présent depuis le démarrage. Le contrôle hors de l’hôte reste à faire.

## Validation de l’installation sans droits administrateur par Fred

Le 15 novembre 2026, Fred confirme avoir testé l’installation de Kiara 4.0.5 sans droits administrateur et demande de considérer ce point comme validé. La présence de WebView2 avant son essai n’a pas été précisée.
