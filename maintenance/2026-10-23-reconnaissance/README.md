# Reconnaissance et conversation Fred — étude du 23 octobre 2026

## Décision

**PC Windows : Parakeet TDT 0.6B v3 int8 pour la dictée et la conversation,
Qwen existant pour répondre, Phonon existant pour parler.** Un seul moteur de
reconnaissance est chargé pendant une session. Zipformer n'est plus utilisé dans
le nouveau client Windows ; Whisper reste le moteur Android actuellement livré.
Silero détecte la parole et Smart Turn estime les fins de tour : ils ne transcrivent
aucun mot. Aucun nouveau paquet Python n'a été installé dans les runtimes actifs.

**Smartphone : premier candidat local, Canary 180M Flash int8 en français.**
Il utilise le même runtime sherpa-onnx, mais des poids nettement plus petits.
L'A54 présumé avec 6 Go de RAM sert de repère ; aucun verdict de performance n'est
déduit de sa fiche technique. Une option de reconnaissance sur PC pourra alléger
le téléphone si les essais locaux ne sont pas assez fluides. Ces deux possibilités
Android sont une proposition, pas une fonction annoncée comme déjà livrée.

Phonon produit du son à partir du texte ; il ne reconnaît pas le microphone.
L'architecture choisie conserve la mémoire, les projets, les documents et les
droits Fred existants au lieu de changer l'assistant pour un modèle vocal complet.

## Recherche : candidats réellement pertinents

| Candidat | Français et fonctionnement | Conclusion pour Fred |
| --- | --- | --- |
| Ancien Zipformer français 2023 | Streaming local ; environ 128 Mo de poids ASR | Rapide, mais pertes de mots à faible volume dans nos essais. Remplacé sur Windows. |
| Whisper Small | Français forcé, local, 488 Mo ; fenêtres avec transcription finale | Bonne transcription des extraits, mais environ cinq secondes de calcul dans notre protocole court. Plus lent que les nouveaux candidats mesurés. |
| Whisper Large v3 Turbo | Multilingue, 809 M de paramètres, décodeur allégé | Candidat valable pour la précision ; non mesuré ici. Ne pas lui attribuer un résultat obtenu avec Small. |
| Parakeet TDT 0.6B v3 int8 | Français, ponctuation ; reconnaissance par fenêtres, 670,5 Mo de poids ASR | Retenu sur PC après essais locaux. Les aperçus sont recalculés ; ce n'est pas un modèle nativement streaming. |
| Nemotron 3.5 ASR 0.6B int8, 560 ms | Vrai streaming avec cache, français forcé `fr-FR`, environ 682 Mo | Testé avec le runtime existant. Intéressant pour la continuité du flux, mais moins convaincant que Parakeet dans notre petit essai de précision/calcul. |
| Canary 180M Flash int8 | Français forcé, ASR par fenêtres, environ 207 Mo de poids | Premier candidat pour les essais Android locaux, sans imposer un moteur obsolète pour économiser de la RAM. |
| Moonshine | Catalogue officiel consulté sans modèle français publié | Non retenu pour Fred français à cette date. Les scores anglais ne répondent pas à notre besoin. |
| Qwen3-ASR 0.6B / 1.7B | Français, reconnaissance et flux continu annoncés | À surveiller ; non mesuré, pas de nouveau runtime ajouté pour cette étude. |
| Voxtral Mini 4B Realtime | Français et flux continu ; modèle 4B, déploiement amont vLLM | Solution serveur intéressante, mais intégration et ressources plus importantes. Non mesurée, non installée. |

Sources primaires : [Whisper Turbo](https://huggingface.co/openai/whisper-large-v3-turbo),
[Parakeet](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3),
[conversion Parakeet maintenue par sherpa](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/nemo-transducer-models.html),
[Nemotron 3.5](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b),
[streaming Nemotron avec sherpa](https://k2-fsa.github.io/sherpa/onnx/nemo/nemotron-streaming.html),
[Canary](https://huggingface.co/nvidia/canary-180m-flash),
[catalogue Moonshine](https://moonshine-voice.readthedocs.io/en/latest/models/available-models/),
[Qwen3-ASR](https://huggingface.co/Qwen/Qwen3-ASR-0.6B),
[Voxtral](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602).

Les classements ne doivent pas mélanger langues, corpus, quantifications et matériel.
Les débits NVIDIA sur H100 ne sont pas des mesures sur notre PC ou le téléphone.

## Vérification des trois projets suggérés

**NemotronLabs VoiceChat 11B** est bien un modèle vocal intégré capable de dialogue
simultané et d'appels d'outils. Son annonce de prise de parole vers 450 ms vient de
son environnement de référence, testé sur H100. La fiche est orientée anglais et
demande notamment des instructions/résultats d'outils ASCII. Ce n'est donc pas un
remplacement français prêt à brancher à Fred. Il remplacerait aussi Qwen et sa voix,
pas seulement le STT. [Fiche NVIDIA](https://huggingface.co/nvidia/NVIDIA-NemotronLabs-VoiceChat-11B).

**Realtime-Venus** prend en charge l'audio/vidéo et l'interaction simultanée. Les
langues déclarées sont l'anglais et le chinois. Son dépôt demande au moins une
A100 pour la démonstration Duplex. L'APK Android bêta ne prouve pas une inférence
complète sur téléphone. Non retenu pour résoudre immédiatement notre français.
[Dépôt](https://github.com/inclusionAI/Realtime-Venus),
[fiche du modèle](https://huggingface.co/inclusionAI/Realtime-Venus).

**VoxEdge** est un démonstrateur Android en cascade ASR → LLM → TTS, et non un
modèle unique de conversation. Ses mesures de 0,55–0,66 s commencent après le
texte reconnu ; elles excluent la fin de parole et l'ASR. Les essais publiés portent
sur anglais/coréen, sur Galaxy Z Fold7 / SM8750, avec des backends spécifiques.
L'interruption reste expérimentale, désactivée par défaut à cause des auto-coupures
par écho. Ses idées de lecture par propositions et de mesures sont utiles ; copier
ses chiffres ou ses modèles ne résoudrait pas notre cas français.
[Dépôt et limites des auteurs](https://github.com/GT-KIM/voxedge).

## Mesures locales, CPU quatre threads

Les scripts `compare.py`, `baselines.py`, `nemotron.py` et `canary.py` sont
rejouables avec `toolchain/conversation-client-python/Scripts/python.exe`.
Les téléchargements sont épinglés par révision et vérifiés par empreinte.
Les poids de recherche restent sous `toolchain/asr-research-20261023`, hors Git.

| Moteur | Calcul sur l'extrait synthétique français de 10,05 s | À faible volume |
| --- | ---: | --- |
| Zipformer, décodage de l'extrait complet | 0,72 s | Perd « Bonjour Fred » ; erreur « résument » |
| Whisper Small installé | 4,98 s | Mots conservés |
| Parakeet v3 int8, une passe | 0,64 s | Mots conservés |
| Nemotron 3.5 int8, trames de 100 ms | 1,88 s | Mots conservés, mais « résument » |
| Canary 180M Flash int8, une passe | 0,93 s | Mots conservés ; ponctuation différente |

Ces durées sont du calcul, pas le délai entre la fin de parole et le premier son.
Les protocoles par fenêtres et streaming sont différents. Les mesures incluent
six essais par moteur sur deux extraits, chacun en original, volume ×0,15 et bruit
gaussien reproductible. Parakeet a aussi été essayé sur un troisième extrait.
Le deuxième extrait est public, mais l'origine humaine ou synthétique de son
locuteur n'a pas été vérifiée. Aucun taux d'erreur représentatif du français,
aucune précision sur la voix de l'utilisateur et aucune performance Android ne
sont déduits de ce petit échantillon.

Les résultats bruts sont dans `baseline-results.json`, `parakeet-results.json`,
`nemotron-results.json` et `canary-results.json`.

Le worker Windows empaqueté transcrit la phrase attendue dans les deux modes.
La chaîne intégrée VAD/fin de tour/aperçus/finale consomme environ 1,01 s de calcul
en conversation et 1,54 s en dictée sur cet extrait lu sans attente temps réel.
Le RSS maximum observé est proche de 947 Mo. Ces chiffres incluent davantage de
travail que la passe Parakeet seule. `native-results.json` contient les mesures et
la preuve réelle d'ouverture, réception et fermeture du micro avec le DSP Windows.

## Architecture proposée sur smartphone

Premier essai : microphone Android natif → AEC → Silero → Canary français local →
texte par le transport Fred existant → Qwen et contexte existants → Phonon serveur
en streaming → lecture Android. Le téléphone continue de capturer pendant la
lecture. La reconnaissance locale évite de transmettre le microphone au serveur.
Un seul STT est chargé sur le téléphone.

L'AEC doit être attaché à la session `AudioRecord`, vérifié disponible et activé,
avec un routage audio cohérent entre capture et lecture. `VOICE_COMMUNICATION`
et l'effet système sont à vérifier sur le téléphone ; la présence de l'API ne
garantit pas la séparation acoustique. Aucun test d'émulateur ne prouve cela.
[API Android AEC](https://developer.android.com/reference/android/media/audiofx/AcousticEchoCanceler).

Alternative plus légère : le téléphone conserve capture/AEC/VAD/lecture, tandis
que le PC effectue Parakeet, Qwen et Phonon. Il faudrait ajouter un transport audio
authentifié, chiffré, borné et annulable. À 16 kHz mono PCM16, le microphone représente
32 ko/s hors protocole. Cette option transmettrait l'audio au PC, contrairement au
fonctionnement actuellement livré ; elle doit être clairement indiquée dans le
réglage. Elle n'est ni activée ni implémentée par ces correctifs.

Phonon CPU sur Android peut également être étudié ultérieurement pour rapprocher
la lecture du téléphone, en utilisant le même modèle de synthèse. Il n'est pas
nécessaire d'ajouter Piper ou Kokoro. Le téléphone ne chargerait pas un LLM 4B pour
ce premier essai : Qwen et les données de Fred sont déjà sur le serveur.

## Écho, interruptions et erreurs corrigés dans les sources Windows

- Le décodage ASR a son propre thread : les aperçus/finales ne bloquent plus la
  récupération des trames du microphone. Files et audio sont bornés.
- La fin de tour attend au moins 850 ms de silence et une décision Smart Turn
  plus prudente. La queue de silence utile au détecteur est retirée de la finale
  ASR pour éviter de dégrader un premier mot. La capture reste active.
- Les périphériques AEC sont explicitement alignés sur les périphériques Windows
  par défaut utilisés pour la lecture ; réduction de bruit et gain automatique
  sont activés. Ce sont des protections, pas une mesure de l'écho dans la pièce.
- Le navigateur attend des mots reconnus, filtre les mots correspondant à la
  lecture récente, conserve « Stop » et les reprises distinctes, puis annule la
  demande concernée. La détection seule ne coupe plus toutes les réponses.
  Une citation littérale de la voix de Fred peut rester ambiguë pendant la lecture.
- Dictée et conversation partagent le modèle et son cache vérifié ; une réparation
  ne retélécharge que les fichiers nécessaires. Les téléchargements concurrents
  sont sérialisés. La dictée garde envoi manuel, annulation et brouillon initial.
- La passerelle conserve désormais le motif des refus dans `inference-errors.json`
  et l'affiche dans les logs de la console. Auparavant, le corps du refus était
  perdu derrière « Le moteur a refusé la demande (503) ». Un refus 503 avec
  `Retry-After` court peut être réessayé avant toute sortie du modèle. Une erreur
  inconnue ou une réponse commencée n'est pas rejouée.

La capture utilisateur est recadrée et les logs antérieurs ne conservent pas le
motif de chaque 503. La cause exacte de ces occurrences historiques ne peut donc
pas être affirmée. L'état réel consulté pendant l'étude indique Qwen prêt,
Phonon prêt, aucune demande active/en attente, et huit annulations comptabilisées.
Cela confirme des interruptions fréquentes, sans prouver qu'elles sont toutes dues
à l'écho. Les tests reproduisent un refus temporaire de slots, pas un incident GPU
historique de production.

## Validation et limites de livraison

Six suites UI partagées passent, dont bruit seul, écho partiel/final ignoré,
reprise réelle, lecture progressive, synchronisation lente et raccrochage.
Les 23 tests vocaux, 24 tests client, 9 tests de conversation serveur et
16 tests de transformations directes passent. Les contrôles de syntaxe et UX
sont exécutés séparément. Le paquet Windows 3.5.35 a été testé dans son exécutable
complet, signé et mis à disposition. La console a été rechargée ; Qwen, les clés,
les données et la programmation des sauvegardes ont été conservés. Phonon est
prêt. `production.json` conserve la preuve. Le client ouvert doit appliquer sa
mise à jour pour utiliser Parakeet ; Android n'a pas été remplacé pendant l'étude.

À tester avec l'utilisateur : phrases françaises spontanées, début de phrase
à voix faible, pauses de réflexion, bruit, haut-parleur/casque, « stop », reprise
pendant un mot de Fred, longues conversations et récupération après coupure.
Mesurer séparément capture, première transcription, fin de tour, premier texte
Qwen et premier son. Le préremplissage Qwen reste une composante du délai total.
Le smartphone physique et son acoustique n'ont pas été testés. Aucun nouveau
modèle vocal intégré, aucune API cloud ni aucun flux microphone vers le serveur
n'ont été activés pendant l'étude.
