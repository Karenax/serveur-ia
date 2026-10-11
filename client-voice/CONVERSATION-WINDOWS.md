# Conversation vocale Windows — version 3.5.23

## Utilisation

Mettre à jour le client Windows personnel avec la mise à jour intégrée. Sur ce PC, les modèles sont déjà installés. Sur les autres PC, choisir **Installer la conversation** une fois : environ **138 Mo** téléchargés publiquement puis vérifiés par SHA-256. L’installation peut être arrêtée ; un nouvel essai recommence les fichiers. Une corruption détectée propose **Réparer la conversation**.

Dans un chat connecté, terminer ou conserver son brouillon, sélectionner le projet voulu, puis cliquer **Conversation**. Parler normalement : le texte provisoire apparaît et une fin de tour déclenche automatiquement l’envoi à Fred. Avec Hermes, Fred lit la réponse finale après la génération et les outils. Reprendre la parole coupe la lecture et annule la génération de cette demande ; le prochain tour part dès que l’annulation et l’enregistrement sont terminés. **Raccrocher** ferme le microphone et rend le clavier disponible. Le passage en arrière-plan arrête également le mode. Durée maximale : quinze minutes, puis il faut relancer Conversation.

La synchronisation automatique de l’historique après chaque réponse conserve le microphone et la lecture actifs. Un nouveau tour vocal reçu pendant cette synchronisation attend son achèvement, puis part une seule fois. La version 3.5.23 corrige l’arrêt intempestif qui affichait « Réponse interrompue avant la fin de sa première phrase » lors d’une synchronisation lente.

Le silence ne raccroche pas. Silero détecte la parole ; après environ 550 ms de silence, Smart Turn estime si le tour est terminé. S’il hésite, le moteur réévalue et termine après quatre secondes de silence au maximum. Un tour est borné à trente secondes. Il peut envoyer trop tôt ou attendre trop longtemps selon l’accent, le bruit et la manière de parler : ces seuils ne garantissent pas une compréhension parfaite de l’intention.

**Dicter** conserve le mode Whisper Small existant, avec correction et envoi manuel. Il ne peut pas utiliser le microphone en même temps que Conversation. Android conserve cette dictée ; la conversation automatique est activée uniquement dans Windows.

## Répartition des traitements

| Client Windows | Serveur Fred |
| --- | --- |
| Microphone ; DSP Windows d’annulation d’écho, réduction du bruit et contrôle du niveau | Accès personnel, session, droits et gestion des appareils |
| Sherpa-ONNX Zipformer français, texte progressif sur CPU | Chat Qwen/Strata existant, projets, documents et mémoire EG2 |
| Silero VAD et Smart Turn v3.2, décision de fin de tour | Pocket TTS 3.3.0 français, voix Estelle, CPU uniquement |
| Envoi du texte et des paramètres habituels du chat | Audio de réponse PCM mono 24 kHz, transmis progressivement |
| Lecture Web Audio, détection d’une reprise de parole, arrêt local immédiat | Annulation limitée à la demande et à l’accès concernés |

Le son du microphone reste en mémoire sur le PC. Aucun enregistrement de conversation n’est envoyé ni enregistré. Seul le texte transcrit rejoint le chat et son historique serveur. Les réponses audio ne sont pas archivées. Les conversations continuent à bénéficier des sauvegardes et de la mémoire existantes ; `voix.json` entre dans les sauvegardes serveur. Après interruption, l’historique garde uniquement les segments audio complètement lus, avec une marque d’interruption ; les mots déjà entendus dans une phrase coupée ne sont pas comptés précisément.

## Console et ressources

Dans **Démarrage et surveillance**, la carte **Conversation vocale Windows** permet d’activer/désactiver la synthèse et affiche son chargement, sa disponibilité ou une erreur. L’activation est persistante. Les modèles utilisent exclusivement les CPU ; Qwen et EG2 ont leurs processus distincts. La synthèse traite une demande à la fois ; un deuxième accès reçoit une réponse « occupé ». Il n’y a pas de file illimitée ni de bascule GPU.

Mesures sur ce poste : environ **249 Mio** de RAM pour le moteur Windows, en plus du client ; Pocket TTS environ **859 Mio** sur la fixture française. Les six modèles client totalisent environ 138 Mo. Le premier aperçu ASR apparaît après 0,8 s d’audio synthétique ; une phrase de 10,05 s est calculée en environ 1,4–1,5 s. La synthèse délivre son premier fragment en environ 0,17 s sur la courte fixture. Ces mesures excluent le chargement initial et la génération Qwen ; elles ne garantissent pas le délai complet ni la précision sur d’autres PC. La fixture ASR contient des erreurs grammaticales : un essai avec votre voix et vos périphériques reste nécessaire pour juger la qualité en situation.

La capture réelle avec le DSP Windows et sa fermeture sont vérifiées. L’interruption est vérifiée par événements contrôlés dans le navigateur ; la qualité acoustique de l’annulation d’écho et de l’interruption avec une voix humaine dans votre pièce n’a pas encore été mesurée. Utiliser les périphériques Windows par défaut ; un casque peut améliorer la séparation entre la voix de Fred et la vôtre.

## Maintenance

Une restauration ferme le moteur vocal avant de remplacer les données. Le réglage d’activation est restauré ; relancer la voix depuis la console, ou redémarrer la console, après la reprise.

Deux environnements isolés : `toolchain/conversation-client-python` pour la compilation du moteur embarqué, `toolchain/voice-server-python` pour Pocket TTS serveur. Les versions sont figées dans `requirements-conversation.txt` et `lanceur/requirements-voice.txt`. Le moteur serveur utilise son cache public `toolchain/voice-server-models` hors ligne ; la configuration française officielle fixe ses révisions. Aucun ajout à l’environnement Strata ni à celui d’EG2.

Le cache utilisateur Windows est `%LOCALAPPDATA%\QwenClient\conversation`. `conversation-models.json` fixe les fichiers, tailles, SHA-256 et révisions publiques. Le binaire contient les moteurs et les licences, sans les poids optionnels. Les notices d’attribution Kyutai/CC-BY-4.0 et des moteurs sont dans `licenses/CONVERSATION-NOTICES.txt`.

Tests et captures : [validation](../preuves/conversation-windows-20261011/VALIDATION.md). Références : [Zipformer français](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html#shaojieli-sherpa-onnx-streaming-zipformer-fr-2023-04-14-french), [Smart Turn](https://github.com/pipecat-ai/smart-turn), [Pocket TTS](https://kyutai-labs.github.io/pocket-tts/API%20Reference/python-api/), [DSP Windows](https://learn.microsoft.com/en-us/windows/win32/medfound/voicecapturedmo).
