# Dictée locale — Windows et Android

Whisper.cpp **1.9.5**, modèle **Small multilingue complet**, français forcé. Le modèle optionnel pèse **487 601 967 octets** ; son URL, sa révision et son SHA-256 sont fixés dans [model.json](model.json). Les textes de licence MIT sont inclus dans `licenses/` et les paquets clients. Les sources amont sont intactes ; le wrapper Fred est dans ce dossier.

## Utilisation

Dans la conversation, choisir **Installer la dictée** une seule fois par appareil, puis **Dicter**. Sur ce PC, le modèle est déjà installé et vérifié. Android demande l’autorisation microphone à la première utilisation. Une permission refusée laisse le clavier disponible.

Le brouillon existant est conservé. Le texte provisoire apparaît progressivement et peut être révisé. Une pause de 1,5 seconde stabilise une phrase et laisse le microphone ouvert. **Terminer la dictée** ferme le microphone et attend la dernière transcription. Corriger le texte, puis **Envoyer** pour demander la réponse à Fred. Aucun silence, résultat de transcription ou fin de durée ne déclenche un envoi. **Annuler** restaure exactement le brouillon précédent.

Chaque dictée est limitée à **deux minutes**. Le passage en arrière-plan sur Android ferme le microphone et finalise le texte. Le bouton de fermeture attend la finalisation ; une destruction forcée annule la capture. Le texte du champ de saisie ne devient une conversation sauvegardée qu’après l’envoi habituel. Ce mode Dictée conserve les réponses écrites. Windows ajoute un mode distinct de [conversation vocale](CONVERSATION-WINDOWS.md), avec envoi automatique et lecture des réponses.

Les commandes **Installer / réparer** et **Désinstaller le modèle** sont sous **Dictée**, près des options du message. Un téléchargement interrompu conserve une partie reprenable. Le contrôle SHA-256 est obligatoire avant publication et avant chargement ; un fichier corrompu ne peut pas ouvrir le microphone.

## Ressources et limites

Le calcul utilise le CPU, au plus quatre threads. Aucune dépendance CUDA, aucun chargement sur les Tesla P100. Prévoir environ 1 Go de RAM disponible pour la dictée, en plus de l’application. Le contexte du modèle et les buffers audio sont libérés à la fin de chaque session ; les bibliothèques du moteur peuvent rester chargées.

Whisper est exécuté sur des fenêtres, avec des aperçus toutes les trois secondes lorsque le CPU les traite assez vite. Les aperçus utilisent un contexte audio réduit ; la passe finale conserve le contexte complet du modèle pour la qualité. Ce mécanisme ne garantit pas une latence de trois secondes. Un téléphone lent peut afficher le texte avec un retard important. Les mesures sur le PC et les émulateurs sont dans [la validation](../preuves/voix-small-20261011/VALIDATION.md) ; aucun téléphone physique n’a été mesuré.

La capture est en mémoire, PCM mono 16 kHz. Aucun audio n’est écrit sur disque ou transmis au serveur. L’accès Internet sert uniquement à l’installation publique du modèle. Une fois installé, la dictée fonctionne hors connexion. Le texte est envoyé par le transport de chat existant quand l’utilisateur appuie sur Envoyer, avec les mêmes droits et la même gestion de l’historique.

## Implantation et compilation

- Windows : `local_voice.py`, capture WinMM, DLL native et routes locales `/client/voice` soumises à la clé locale, à l’hôte et à l’origine existants. Cache public du modèle : `%LOCALAPPDATA%\QwenClient\voice`.
- Android : `LocalVoice.java`, capture AudioRecord, permission RECORD_AUDIO demandée à l’usage, JNI. Cache public dans le dossier privé de l’application. Les profils et clés d’accès ne sont pas dans le modèle.
- Interface commune : `client-qwen/voice.js`. Une session identifiée bloque l’envoi et les changements de conversation ; une commande tardive d’une autre session est refusée.
- Moteur : `fred_voice.cpp`, file bornée à huit phrases, buffers bornés, annulation coopérative, CPU uniquement. Windows et Android x86_64 choisissent à l’exécution un backend CPU compatible ; Android ARM64 utilise le backend NEON de base. Les bibliothèques Android sont alignées pour des pages de 16 Ko.

Les scripts `Build-Voice.cmd`, `Prepare-Windows.ps1` et `client-android/scripts/Build-Voice-Android.ps1` utilisent le compilateur MSVC portable, CMake/Ninja et le NDK 27.3 déjà installés dans `toolchain`. Ils sont appelés par les scripts de livraison. Les paquets debug Android ont l’identité séparée `net.karenax.fred.voiceqa` afin de conserver l’application signée et ses données.

Tests : `python -X utf8 client-voice/test_service.py`, `python -X utf8 client-voice/test_http.py`, `python -X utf8 preuves/voix-small-20261011/test_native_windows.py`, `node lanceur/web/tests/voice_ui.mjs`. La fixture audio française est une voix synthétique, pas un enregistrement humain ; elle vérifie le chemin réel d’inférence sans prétendre mesurer une précision générale.

Références primaires : [whisper.cpp 1.9.5](https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.5), [modèle Small épinglé](https://huggingface.co/ggerganov/whisper.cpp/tree/5359861c739e955e79d9a303bcbc70fb988958b1), [ABI Android et extensions CPU](https://developer.android.com/ndk/guides/abis).
