# Complément : lecture des réponses et conversation vocale

Étude documentaire du **11 octobre 2026**, complément de [l’étude ASR dans les clients](ETUDE-ASR-CLIENTS.md). Aucun moteur installé, poids téléchargé, benchmark vocal exécuté ou service activé.

## Ressources constatées sur le serveur

Le relevé pendant l’étude montre un Threadripper PRO 3955WX, 16 cœurs physiques/32 logiques, environ 128 Gio de RAM dont 59 Gio disponibles à cet instant, Windows 10 Pro et deux P100 de 16 Go occupées par Qwen. Il reste environ 1,4 Gio de VRAM sur chaque P100. La Quadro P2200 de 5 Go a environ 4,2 Gio disponibles, mais sert également à l’affichage. Ces valeurs sont un instantané, pas une réservation de ressources.

Les P100 sont de génération Pascal, capacité CUDA 6.0. La table CTranslate2 consultée documente une conversion vers FP32 sur cette génération pour les types quantifiés et FP16 de ses binaires précompilés ; il ne faut donc pas promettre un avantage INT8/FP16 avec faster-whisper sur nos P100. Le CPU est le premier terrain d’essai de la voix serveur, avec concurrence et nombre de fils bornés. [Compatibilités NVIDIA](https://developer.nvidia.com/cuda/gpus/legacy), [table CTranslate2](https://opennmt.net/CTranslate2/quantization.html).

Une transcription dans les clients évite toute consommation ASR sur ce serveur. Si un repli serveur est ensuite voulu pour les appareils trop faibles, Whisper.cpp CPU et faster-whisper CPU constituent des candidats ; leur essai devra utiliser un environnement séparé et préserver Qwen, ses dépendances et les pilotes.

## Synthèse vocale française

La première comparaison proposée est **Pocket TTS français contre Piper SIWIS**, puis Kokoro. Il s’agit d’un choix de candidats CPU, sans classement auditif encore établi.

Les tailles ci-dessous représentent des fichiers sur disque, pas la mémoire d’exécution. Ajouter les codecs et dépendances lorsqu’ils sont requis.

| Candidat | Français et ressources publiées | Licence et limite | Place proposée |
|---|---|---|---|
| Pocket TTS, Kyutai | Variantes françaises 6 couches/219 Mo et 24 couches/672 Mo, codec supplémentaire ; CPU et génération par morceaux | Code MIT, poids CC BY 4.0 ; accès aux poids après acceptation. Variante 24 couches présentée comme aperçu | Premier essai CPU pour une lecture progressive |
| Piper, OHF | Voix française SIWIS medium, fichier de 63,2 Mo ; Windows x64 et CPU | Moteur GPL 3, notices propres à chaque voix ; fiche SIWIS mentionnant données CC BY 4.0 | Solution compacte à comparer |
| Kokoro 82M v1.0 | Poids de 327 Mo, CPU ; voix française officielle `ff_siwis` | Apache 2.0 ; fournisseur indiquant moins de 11 heures de données françaises | Troisième comparaison compacte |
| NeuTTS Nano French | GGUF Q4 de 195 Mo, codec supplémentaire ; CPU, streaming et clonage | NeuTTS Open License 1.0 et accès soumis à acceptation ; intégration plus complexe | Option à étudier si personnalisation de voix utile |
| Qwen3-TTS 0.6B/1.7B | Français, voix prédéfinies ou clonage selon variante ; plusieurs Go de fichiers | Apache 2.0 ; SDK et compatibilité GPU à examiner | Essai ultérieur, après les moteurs CPU compacts |

Pocket TTS a renouvelé ses modèles français en version 3.2.0 du 23 septembre 2026 ; 3.3.0 du 24 septembre corrige notamment les apostrophes et guillemets. L’API expose `generate_audio_stream` et l’annulation. Ses délais annoncés sur MacBook Air M4 ne constituent pas des mesures de notre serveur. [Modèles Kyutai](https://huggingface.co/kyutai/pocket-tts), [versions](https://github.com/kyutai-labs/pocket-tts/releases), [API Python](https://kyutai-labs.github.io/pocket-tts/API%20Reference/python-api/).

Les enregistrements de référence ont leurs propres droits. Le catalogue Kyutai identifie Estelle comme un enregistrement maison CC0, alors que d’autres voix ont des restrictions différentes. La licence du moteur Piper ne décrit pas toutes les voix : la fiche SIWIS mentionne CC BY 4.0 et celle de Tom AGPLv3. Conserver les notices du moteur, du modèle et de la voix sélectionnés. [Catalogue des voix Kyutai](https://huggingface.co/kyutai/tts-voices), [Piper maintenu par OHF](https://github.com/OHF-Voice/piper1-gpl), [distribution Windows](https://pypi.org/project/piper-tts/), [fiche SIWIS](https://huggingface.co/rhasspy/piper-voices/blob/main/fr/fr_FR/siwis/medium/MODEL_CARD).

Kokoro est intéressant, mais sa réputation anglaise ne démontre pas le rendu français. NeuTTS nécessite aussi ses composants de codec et ONNX/llama.cpp ; sa taille GGUF seule ne décrit pas toute l’installation. [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [NeuTTS](https://github.com/neuphonic/neutts).

Qwen3-TTS annonce une architecture streaming, mais le SDK consulté précise que `non_streaming_mode=False` simule une entrée texte progressive ; le wrapper renvoie l’audio complet. Les instructions de style sont ignorées pour 0.6B dans le code examiné. L’exemple BF16 avec FlashAttention 2 ne convient pas aux P100 ; une autre précision et un autre mécanisme d’attention seraient nécessaires, sans garantie de vitesse. [Dépôt Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS), [code d’inférence effectif](https://github.com/QwenLM/Qwen3-TTS/blob/main/qwen_tts/inference/qwen3_tts_model.py), [compatibilité FlashAttention](https://github.com/Dao-AILab/flash-attention).

Autres candidats examinés : Chatterbox Multilingual V3 propose le français et le clonage, mais les mesures de vitesse du fabricant sont sur H100 ; Supertonic 3 propose un moteur ONNX compact français, mais son dépôt a été archivé le 9 septembre 2026 avec arrêt du support. XTTS v2 a une licence Coqui réservant l’usage des poids et sorties au non-commercial. Aucun de ces trois n’est la première proposition pour Fred. [Bilan Chatterbox du fabricant](https://www.resemble.ai/resources/chatterbox-multilingual-v3-tts-with-embedded-watermarking-for-25-languages), [archive Supertonic](https://github.com/supertone-oss-archive/supertonic), [licence XTTS](https://huggingface.co/coqui/XTTS-v2).

## Conversation vocale continue

La dictée locale puis réponse Qwen permet de conserver le modèle, les conversations, les documents et les permissions de Fred. Ajouter ensuite détection de silence, texte provisoire, synthèse par phrases, arrêt de lecture et annulation du travail lié à la demande. Silero VAD détecte la parole mais ne la transcrit pas. Le duplex complet et l’écho demandent des essais de capture, casques et haut-parleurs. [Silero VAD](https://github.com/snakers4/silero-vad).

Moshi officiel est anglais, l’implémentation PyTorch recommande 24 Go de GPU et Windows n’est pas officiellement pris en charge. Ses délais annoncés ne sont pas des résultats de Fred. [Moshi](https://github.com/kyutai-labs/moshi), [FAQ](https://github.com/kyutai-labs/moshi/blob/main/FAQ.md).

Les services vocaux OpenAI constituent une autre voie, hébergée : l’architecture documentée permet de déléguer à un backend existant, donc à Qwen. Cela implique cependant un fournisseur, un compte et une facturation ; ce n’est pas de l’ASR exécutée dans les clients. Aucun compte ou service n’est configuré dans cette étude. [Architecture officielle des agents vocaux](https://developers.openai.com/api/docs/guides/voice-agents).

## Validation future

Comparer les voix sur les mêmes phrases françaises : dates, montants, noms propres, sigles et réponses longues. Mesurer premier audio, débit, pic RAM, annulation et débit Qwen pendant la lecture. La console devra exposer disponibilité réelle, ressources, file bornée et erreurs ; l’historique textuel reste la référence. Tester transports audio bornés en HTTPS/WireGuard, suppression des temporaires, reprise après interruption et appareils physiques.

Le lot 7 reste **planifié**. L’étude des moteurs embarqués précise une alternative à la transcription serveur du plan initial ; elle ne signifie pas que cette alternative est déjà implantée ou définitivement retenue.
