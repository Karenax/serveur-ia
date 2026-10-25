# Qualité Low / Max — intégration du 24 octobre 2026

## Fonctionnement

La page Vocal propose **Low · Léger** et **Max · Voix avancée**. Low garde Parakeet
sur le PC et Phonon/Tiphaine sur le serveur. Max utilise les poids ouverts de
Voxtral Realtime 2602 pour transcrire et Qwen3-TTS 1.7B CustomVoice, voix Serena en
français, pour lire les réponses. Il ne s’agit pas de l’offre Voxtral 3.

Max propose **Automatique · PC ou serveur**, **Ce PC**, **Serveur Kiara**. En
automatique, seuls les moteurs ayant réussi le test et disponibles sont candidats.
Le choix minimise le temps de transcription et de préparation audio mesuré ; le
temps aller-retour observé pour joindre le serveur est ajouté. Qwen reste le même
modèle de dialogue : ces mesures ne prédisent pas son temps de génération.

Le profil et le lieu sont conservés dans les préférences chiffrées du PC. Ils se
choisissent avant l’appel, puis restent verrouillés jusqu’au raccrochage. Le lieu
effectif apparaît pendant l’appel. L’envoi du son au serveur est annoncé dans le
panneau Max. Aucun service audio extérieur n’est appelé. La dictée reste dans le
chat et continue d’utiliser son moteur existant.

Si Max est absent, non testé, trop lent ou occupé, une erreur visible permet de
choisir Low. Le moteur Low n’est jamais utilisé en prétendant que Max est actif.

## Architecture et limites de cette première intégration

- `client-qwen/advanced_voice.py` : contrôleur commun, processus séparés,
  deux files bornées (écoute et voix), annulation liée au propriétaire,
  test réel et réservation pendant un appel. Le serveur réutilise ce même module
  via `lanceur/voice_max.py`.
- `client-voice/max_worker.py` : Voxtral et Qwen3-TTS fonctionnent dans deux
  environnements distincts. Voxtral emploie Transformers 5.20.2 ; qwen-tts 0.1.1
  impose Transformers 4.57.3. Le microphone et le DSP restent dans le worker léger.
- `recognition.py` conserve Silero et Smart Turn. Les aperçus et phrases sont
  décodés par Voxtral via une fonction dédiée ; cette version n’exploite pas son
  cache natif de streaming continu entre fenêtres. Qwen3-TTS génère chaque morceau
  de texte avant de transmettre ses trames PCM 24 kHz. Ce n’est donc pas encore
  une implémentation audio token par token comparable au SDK Voxtral 3 complet.
- Le transport local utilise l’API loopback, son jeton éphémère et la session
  propriétaire. Le transport serveur utilise l’authentification Kiara existante.
  Les limites sont 28 secondes par segment entrant et 600 caractères par lecture.
  L’audio n’est pas écrit dans l’historique ni sur disque.
- L’écoute et la synthèse disposent de processus et de verrous séparés : une
  réponse en lecture ne monopolise pas la reconnaissance. Les annulations sont
  bornées et les processus bloqués sont arrêtés avant réutilisation du créneau.
- Un appel réserve Max. Un autre accès ne peut pas le retester au milieu de cet
  appel. Le raccrochage libère la réservation ; elle expire après vingt minutes
  si le client disparaît. La conversation est bornée à quinze minutes de temps
  écoulé, y compris pendant une coupure du microphone.

## Installation explicite

Les deux runtimes existants de reconnaissance et de synthèse légère, Strata et
Hermes ne sont pas modifiés. L’installateur Max ne reçoit aucun chemin depuis
l’API du client ou du serveur.

Serveur :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' client-voice/prepare_max.py --server --device auto --download
```

Sur un PC disposant des sources et de Python 3.12 :

```powershell
python client-voice/prepare_max.py --device auto --download
```

Le dossier par défaut du PC est `%LOCALAPPDATA%/QwenClient/voice-max`. Pour le
serveur : `toolchain/voice-max-server`. `--home` permet de préparer un autre
dossier explicitement. L’environnement CUDA est choisi automatiquement uniquement
si une carte compatible possède au moins 20 Go de VRAM libre ; sinon le candidat
est CPU. La compatibilité pratique dépend ensuite du test, pas de ce seuil seul.

Il faut prévoir environ 13,4 Go de poids, les deux environnements Python et
l’espace de préparation. L’installateur demande 30 Go libres. Les poids BF16 sont
convertis en float32 en CPU, en float16 sur GPU. La voie WebGPU q4f16 de l’étude
reste une optimisation possible et n’est pas intégrée ici.

L’installateur épingle les révisions, vérifie les empreintes publiées par les
dépôts et crée un manifeste SHA-256 local. Les workers vérifient ensuite les
fichiers avant chargement. Les dépendances transitives sont épinglées avec leurs
empreintes dans `client-voice/requirements-max-asr.txt` et `requirements-max-tts.txt` ;
les quatre wheels officiels Torch/Torchaudio CPU/CUDA Windows Python 3.12 ont leurs
empreintes dans `max-torch-wheels.json`. L’installation finale avec
`--require-hashes` et les deux contrôles `pip check` ont réussi. Les rapports pip
et listes exactes des versions sont aussi enregistrés dans le runtime. Aucun
paquet n’est installé pendant un appel. Le cache est placé dans ce dossier lors d’une nouvelle
préparation avec le script final.

Révisions : Voxtral `2769294da9567371363522aac9bbcfdd19447add` ; Qwen3-TTS
`0c0e3051f131929182e2c023b9537f8b1c68adfe`. La copie `consolidated.safetensors`
de Voxtral n’est pas téléchargée : Transformers utilise `model.safetensors`.

## Qualification

**Tester le PC et le serveur** ne capte pas le microphone. Le moteur synthétise
une phrase fictive mentionnant Orion et quinze heures, puis la retranscrit.
La présence de ces deux éléments et les temps sont contrôlés. Cette vérification
fonctionnelle ciblée ne mesure pas la qualité de reconnaissance de tous les accents
ou du bruit. Une écoute comparative reste nécessaire avant de recommander la voix.

Les deux modèles sont chargés avant le test, afin que leurs mémoires soient
occupées simultanément. Les budgets produit initiaux sont RTF ASR et TTS <= 0,8
et somme du temps de transcription et du délai audio <= 3 s sur cet extrait.
RTF désigne le temps de calcul divisé par la durée du son. Ces budgets sont des
critères d’acceptation, pas des performances annoncées par le fabricant.

Le résultat `benchmark.json` est lié aux empreintes du worker et du manifeste.
Une modification de ces fichiers exige un nouveau test. Une indisponibilité du
runtime, un modèle corrompu ou une mesure échouée ne donnent pas un état prêt.

## Contrôles effectués

- Six suites UI partagées : réussies. Le contrôle UX conserve neuf avertissements
  de textes longs dans la console, hors des modifications de cette tâche.
- Variante conversation `--max --web-events` : réussie avec PCM et reconnaissance
  fictifs, dont les appels au second moteur, le lieu serveur choisi, le profil
  conservé après reload, l’interdiction de changement en cours d’appel, les sources,
  le raccrochage, la reconnexion et les interruptions.
- Tests Python : 57 tests du client Windows et 26 tests vocaux réussis ; 4 tests
  des routes Max de la passerelle et 11 tests des conversations Qwen réussis.
  Nouveaux tests de
  disponibilité, cache de benchmark, sélection automatique/manuelle, typage,
  propriétaire, session expirée, annulation, files indépendantes, contre-pression
  sur les phrases longues et transport HTTP réel PC/serveur.
- Routes de passerelle testées avec comptes et données fictifs ; aucune ouverture
  d’accès, redémarrage de Qwen ou écriture dans une conversation de production.
- Playwright MCP : captures bureau 1440×1000, téléphone 390×844 et tablette
  768×1024 ; clair/sombre. Sélecteur, lieu effectif et blocage en cours d’appel
  examinés. Aucun débordement horizontal observé. Pas d’audit WCAG complet.

## État de la mesure native

Les deux environnements CPU et les poids ont été installés et vérifiés dans le
dossier serveur indépendant. Le test complet a chargé les deux modèles ensemble
et exécuté la synthèse puis la transcription d’un extrait fictif de 5,04 s.

| Mesure CPU réelle | Résultat |
| --- | --- |
| Synthèse Qwen3-TTS | 37,73 s, RTF 7,49 |
| Transcription Voxtral du son produit | 56,61 s, RTF 11,23 |
| Temps vocal cumulé, hors Qwen et réseau | 94,34 s |
| Qualification pour le dialogue en direct | Échec : Low conseillé |

Un essai indépendant de Voxtral sur une phrase synthétique Phonon de 4,32 s a
retranscrit correctement « Bonjour. La réunion du projet Orion est prévue demain
à 15h. » en 49,88 s (RTF 11,55). Son chargement vérifié a pris 25,62 s. Ce test
ciblé montre un fonctionnement effectif, sans établir une qualité générale.

Le statut persistant est `installed: true`, `available: false`, et affiche
« Mode Max trop lent sur cet appareil. Low est conseillé. ». Aucun classement
favorable n’est déduit des seuls 128 Go de RAM. Les GPU P100/P2200 n’ont pas été
sollicités : leurs ressources sont déjà utilisées et ne permettent pas cette
configuration accélérée. La voie CUDA sur un autre PC reste à qualifier réellement.

L’essai a aussi permis de corriger l’ordre de démarrage du worker : les imports et
le chargement précèdent le lecteur de commandes sur stdin. Le premier lancement
simultané bloquait avant le chargement ; l’essai final fonctionne et publie les
mesures ci-dessus. Le contrôle du résultat utilise une écriture atomique avec
synchronisation Windows ; un retest échoué invalide un ancien succès.

Preuves : `asr-native.json`, `benchmark-native-status.json` et le `benchmark.json`
du runtime ; logs d’installation et des suites dans ce dossier. Les workers ont
été fermés après la mesure, aucune instance de test n’est restée active et la RAM
disponible est revenue à environ 68 Go. Aucun microphone réel ni écoute
comparative humaine n’a été utilisé. Max n’a pas été activé sur la passerelle de
production.

Les captures utilisent une fixture dont les deux cibles sont volontairement
déclarées prêtes ; elles ne prouvent pas la puissance du PC ou du serveur réel.
Les distributions installées et signées n’ont pas été remplacées par cette tâche.
La diffusion exige une reconstruction Windows et le chargement des nouvelles
routes de passerelle. Le programme d’installation Max est un outil administratif
distinct ; il n’est pas embarqué dans un EXE personnel.
