# Conversation vocale Windows — version 3.5.52

La version actuelle ajoute les commandes de mémoire, notes, tâches et rappels,
les bilans de projet, une image choisie pour le tour oral et la sélection d’une
région du bureau. Le [guide commun de l’assistant](../GUIDE-ASSISTANT-KIARA.md)
décrit ces parcours. L’attente de **« Bonjour Kiara »** reste un essai local
facultatif, application visible, à valider avec un microphone humain. Le
[rapport d’intégration](../maintenance/2026-10-25-assistant-integration/README.md)
conserve les tests, la publication et les limites matérielles.

## Version 3.5.51

Max utilise désormais Whisper Turbo Q5 sur le GPU Vulkan choisi et Phonon français
Q8 sur CPU. Le complément reste optionnel et sa taille est affichée avant installation.
Le test conseille un lieu de traitement sans interdire Max. Les moteurs Low et la
dictée sont conservés. Voir les [mesures et limites](../maintenance/2026-10-25-vocal-realtime/README.md).
Les descriptions des anciens moteurs ci-dessous restent historiques.

## Utilisation

### Page Vocal (sources du 24 octobre 2026)

La conversation orale possède désormais son entrée **Vocal** dans la navigation Windows.
Dans le chat, choisir Qwen local et le projet, puis ouvrir **Vocal** et sélectionner
**Démarrer la conversation**. Un brouillon doit être envoyé ou laissé dans une autre
conversation avant le démarrage. **Dicter** reste dans le chat, avec envoi manuel.

La page rassemble le microphone, l’autorisation d’interrompre Kiara en parlant
(désactivée par défaut), le volume de lecture et l’animation. Volume, animation et
interruptions sont conservés dans les réglages chiffrés du client. Les périphériques
se choisissent dans Windows ; la voix se configure côté serveur. L’orbe distingue
l’écoute, la parole détectée, la préparation, la lecture et le microphone coupé.
Pendant la lecture, ses déformations suivent le niveau de sortie audio. Les
mouvements réduits de l’appareil et l’option **Animer l’orbe** sont respectés.

**Échanges écrits** permet de consulter les textes et leurs sources. **Ouvrir le
chat** conserve l’appel ; **Vocal en cours** permet d’y revenir. **Raccrocher**
ferme le microphone. Android propose aussi la conversation Low et conserve la
dictée manuelle ; voir le [guide Android](../client-android/README.md).
Installer la mise à jour du client pour retrouver les fonctions publiées.

Les paragraphes de versions ci-dessous décrivent aussi les libellés historiques.

La page propose également **Qualité : Low / Max**. Low utilise Parakeet sur
Windows et la voix Phonon du serveur. Le complément Max utilise Whisper
large-v3-turbo Q5 sur le GPU Vulkan choisi et Phonon français Q8 sur CPU.
Le test conseille un lieu de traitement ; un choix manuel reste possible.
Profil et lieu se
choisissent avant l’appel et restent mémorisés par PC. Le son du micro rejoint le
serveur uniquement lorsque ce dernier est choisi pour Max. La dictée du chat
reste indépendante. Sur les PC AMD ou NVIDIA, Vocal propose un téléchargement
séparé avec sa taille, l’espace disque nécessaire et une confirmation avant
installation. Aucun modèle Max ni runtime GPU n’est ajouté à l’EXE de base.
L’installation peut être arrêtée et relancée ; un test réel vérifie ensuite la
fluidité. Intel reste hors du périmètre local pour ce complément.
Les [mesures du 25 octobre](../maintenance/2026-10-25-vocal-realtime/README.md)
décrivent les moteurs actuellement livrés et leurs limites. Les essais du
[24 octobre](../maintenance/2026-10-24-vocal-low-max/IMPLEMENTATION.md) et du
[premier complément optionnel](../maintenance/2026-10-24-max-optionnel/README.md)
restent des références historiques, avec d’autres moteurs.

Mettre à jour le client Windows personnel avec la mise à jour intégrée. Choisir **Installer la conversation** une fois : environ **680 Mo** téléchargés publiquement puis vérifiés par SHA-256. Le même modèle sert à **Dicter**. Une réparation conserve les fichiers valides et remplace uniquement ceux manquants ou corrompus. L'installation peut être arrêtée. Une corruption détectée propose **Réparer la conversation**.

Dans un chat connecté, terminer ou conserver son brouillon, sélectionner **Qwen local** et le projet voulu, puis cliquer **Conversation**. Parler normalement : le texte provisoire apparaît et une fin de tour déclenche automatiquement l’envoi à Kiara. Qwen local produit directement les réponses, sans conversation pilotée par l’agent Hermes. Les phrases sont synthétisées pendant la génération. Les réponses orales disposent de 100 000 tokens de sortie et du contexte du modèle chargé (262 144 tokens sur ce serveur), sans réflexion ; le réglage du chat écrit reste conservé. L’historique, les sources du projet et la recherche locale de mémoire gardent leur périmètre personnel.

Kiara interprète le sens de la demande pour décider si une recherche Internet est utile. Aucune formule précise n’est nécessaire : **« Quoi de neuf aujourd’hui dans l’IA ? »**, **« Va voir les dernières nouvelles »** ou **« Quel temps fera-t-il demain à Paris ? »** peuvent déclencher une recherche. Si le sujet manque, Kiara demande une précision. Une explication générale ou une recherche dans vos documents reste locale. Le droit **Web** du compte est nécessaire. Qwen prend cette décision localement ; seule la requête publique reformulée est envoyée aux outils web Hermes, sans transmettre les documents ni l’historique complet. Les étapes et les liens apparaissent dans le chat. L’interprétation ajoute quelques secondes ; une recherche complète peut prendre plusieurs dizaines de secondes. Annuler, Raccrocher ou une interruption autorisée l’arrêtent. Voir [la correction et ses limites](../maintenance/2026-10-24-web-vocal/README.md).

Lorsque l’option d’interruption vocale est activée, reprendre la parole coupe la lecture et annule uniquement la demande vocale concernée ; le prochain tour part dès que l’annulation et l’enregistrement sont terminés. **Raccrocher** ferme le microphone et rend le clavier disponible. Si cette commande échoue, **Réessayer le raccrochage** reste accessible. Une réponse entièrement générée n’est pas effacée par une erreur de lecture ou une fermeture. Le passage en arrière-plan arrête également le mode. Durée maximale : quinze minutes, puis il faut relancer Conversation.

La synchronisation automatique de l’historique après chaque réponse conserve le microphone et la lecture actifs. Un nouveau tour vocal reçu pendant cette synchronisation attend son achèvement, puis part une seule fois. La version 3.5.23 corrige l’arrêt intempestif qui affichait « Réponse interrompue avant la fin de sa première phrase » lors d’une synchronisation lente.

Le silence ne raccroche pas. Silero détecte la parole ; après au moins 850 ms de silence, Smart Turn estime si le tour est terminé. S’il hésite, le moteur réévalue et termine après 2,5 secondes de silence au maximum. Un segment audio est borné à 28 secondes, silence et préambule compris. Ces seuils ne garantissent pas une compréhension parfaite de l’intention.

**Dicter** utilise le même Parakeet v3, avec correction et envoi manuel. Il ne
peut pas utiliser le microphone en même temps que Conversation. Android conserve
Whisper Small pour la dictée et la conversation Low.

## Répartition des traitements

| Client Windows | Serveur Kiara |
| --- | --- |
| Microphone ; DSP Windows d’annulation d’écho, réduction du bruit et contrôle du niveau ; flux de sortie silencieux maintenu pendant l’écoute | Accès personnel, session, droits et gestion des appareils |
| Sherpa-ONNX Parakeet v3 int8, aperçus par fenêtres et transcription finale sur CPU | Qwen/Strata direct, projets, documents et mémoire EG2 locale |
| Silero VAD et Smart Turn v3.2, décision de fin de tour | Phonon 0.4.1, modèle français 40m q8, voix fournie default, CPU uniquement |
| Envoi du texte et des paramètres habituels du chat | Audio de réponse PCM mono 24 kHz, transmis progressivement |
| Lecture Web Audio, détection d’une reprise de parole, arrêt local immédiat | Annulation limitée à la demande et à l’accès concernés |

Le son du microphone reste en mémoire sur le PC. Aucun enregistrement de conversation n’est envoyé ni enregistré. Seul le texte transcrit rejoint le chat et son historique serveur. Les réponses audio ne sont pas archivées. Les conversations continuent à bénéficier des sauvegardes et de la mémoire existantes ; `voix.json` entre dans les sauvegardes serveur. Après interruption, l’historique garde uniquement les segments audio complètement lus, avec une marque d’interruption ; les mots déjà entendus dans une phrase coupée ne sont pas comptés précisément.

## Console et ressources

Dans **Démarrage et surveillance**, la carte **Conversation vocale Windows** permet d’activer/désactiver la synthèse et affiche son chargement, sa disponibilité ou une erreur. L’activation est persistante. Les modèles utilisent exclusivement les CPU ; Qwen et EG2 ont leurs processus distincts. La synthèse traite une demande à la fois ; un deuxième accès reçoit une réponse « occupé ». Il n’y a pas de file illimitée ni de bascule GPU.

Mesures historiques avec Zipformer et Pocket TTS, avant Parakeet du 23 octobre et Phonon du 22 octobre : environ **249 Mio** de RAM pour l'ancien moteur Windows ; Pocket TTS environ **859 Mio**. Les anciens modèles client totalisaient 138 Mo et l'ancien premier aperçu apparaissait après 0,8 s d'audio synthétique. Ces valeurs ne décrivent pas le moteur actuel. Les [mesures Parakeet et leurs limites](../maintenance/2026-10-23-reconnaissance/README.md) portent sur des extraits publics ou fictifs : un essai avec votre voix et vos périphériques reste nécessaire.

La capture réelle avec le DSP Windows et sa fermeture sont vérifiées avec réception de trames microphone avant d’annoncer l’écoute. Le DSP nécessite un flux actif sur le périphérique de sortie : le moteur conserve donc un flux partagé silencieux, y compris avant la première réponse. Une absence de trames pendant cinq secondes ou une erreur Windows est signalée au client. L’interruption est vérifiée par événements contrôlés dans le navigateur ; la qualité acoustique de l’annulation d’écho et de l’interruption avec une voix humaine dans votre pièce n’a pas encore été mesurée. Utiliser les périphériques Windows par défaut ; un casque peut améliorer la séparation entre la voix de Kiara et la vôtre.

L’audit 3.5.30 a également validé le vrai Qwen et Pocket TTS sur deux questions de test, sans redémarrer le modèle : premier texte vers 2,9 s et premier fragment TTS en 0,13–0,16 s après la demande de synthèse. Ces délais séparés ne représentent pas le délai complet après votre parole. Zipformer conserve deux erreurs grammaticales sur la fixture française ; sa qualité avec votre voix reste à évaluer. Voir [l’audit et ses preuves](../audits/2026-10-14-conversation/README.md).

## Maintenance

Une restauration ferme le moteur vocal avant de remplacer les données. Le réglage d’activation est restauré ; relancer la voix depuis la console, ou redémarrer la console, après la reprise.

Deux environnements isolés : `toolchain/conversation-client-python` pour la compilation du moteur embarqué, `toolchain/phonon-server-python` pour Phonon serveur. Les versions sont figées dans `requirements-conversation.txt` et `lanceur/requirements-voice.txt`. Le moteur serveur charge le checkpoint local vérifié sous `toolchain/phonon-models`, dont la révision et les empreintes figurent dans `lanceur/phonon-model.json`. Le téléchargement préparatoire requiert les conditions Hugging Face acceptées et un jeton de lecture ; la synthèse fonctionne ensuite hors ligne. Aucun ajout à l’environnement Strata ni à celui d’EG2.

Le cache Windows partagé est `%LOCALAPPDATA%\QwenClient\asr`. `conversation-models.json` fixe les fichiers, tailles, SHA-256 et révisions publiques. Le binaire contient le runtime et les licences, sans les poids optionnels. Les notices d'attribution NVIDIA/CC-BY-4.0 et des moteurs sont dans `licenses/CONVERSATION-NOTICES.txt`.

Tests et captures : [validation](../preuves/conversation-windows-20261011/VALIDATION.md). Références : [Zipformer français](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html#shaojieli-sherpa-onnx-streaming-zipformer-fr-2023-04-14-french), [Smart Turn](https://github.com/pipecat-ai/smart-turn), [Pocket TTS](https://kyutai-labs.github.io/pocket-tts/API%20Reference/python-api/), [DSP Windows](https://learn.microsoft.com/en-us/windows/win32/medfound/voicecapturedmo).

## Synthèse serveur remplacée le 22 octobre 2026

Le moteur actif est désormais Phonon 0.4.1, modèle phonon-40m-fr q8, voix fournie default, quatre threads CPU. Le runtime est `toolchain/phonon-server-python` et le checkpoint local épinglé est sous `toolchain/phonon-models`. Les références Pocket TTS et ses mesures ci-dessus décrivent les validations historiques. Reconnaissance et protocole client conservés. Voir [la migration et les mesures natives](../maintenance/2026-10-22-phonon/README.md).


Depuis le 23 octobre 2026, la voix serveur est Tiphaine (français de France). Le moteur Phonon et son checkpoint restent identiques ; l’embedding de voix est vérifié et épinglé dans `lanceur/phonon-model.json`. Voir [la sélection et les preuves](../maintenance/2026-10-23-tiphaine/README.md).
