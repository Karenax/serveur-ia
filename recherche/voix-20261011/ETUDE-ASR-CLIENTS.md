# Reconnaissance vocale directement dans les clients Fred

Recherche documentaire du **11 octobre 2026**, recentrée à la demande de l’utilisateur sur l’ASR exécutée dans les clients Windows et Android, téléphone et tablette. ASR signifie reconnaissance de la parole : transformer la voix en texte. La synthèse de la réponse est étudiée dans [l’annexe serveur](ANNEXE-VOIX-SERVEUR.md).

**Recommandation : comparer d’abord Whisper.cpp avec Whisper base multilingue pour la dictée et Sherpa-ONNX avec Zipformer français pour le texte progressif.** Canary 180M Flash fournit une troisième comparaison intéressante. Vosk constitue une option compacte. Ce choix est une proposition fondée sur la disponibilité des moteurs, leurs interfaces et leurs licences ; leur qualité et leur vitesse sur nos appareils ne sont pas encore mesurées.

Aucun moteur installé, aucun poids téléchargé et aucune modification des clients ou du serveur effectuée pendant cette étude. Le lot 7 reste planifié. Les bibliothèques Android décrites ci-dessous n’ont pas encore été intégrées à l’APK Fred.

## Comparatif des moteurs et modèles embarqués

Les tailles sont celles des fichiers publiés, avant ajout du moteur, de ses dépendances et des fichiers auxiliaires. **Elles ne représentent pas la RAM.** Les listings ONNX utilisent des tailles arrondies en unités binaires ; Vosk indique la taille du téléchargement compressé. Un moteur est le programme qui exécute un modèle : Sherpa-ONNX peut donc utiliser plusieurs modèles très différents.

| Moteur et modèle français | Windows / Android | Fonctionnement | Fichiers principaux | Licence du moteur / poids | Usage proposé |
|---|---|---|---|---|---|
| Whisper.cpp + Whisper tiny/base multilingue | Oui / oui, JNI | Dictée enregistrée ; texte progressif possible par réanalyse de fenêtres | tiny 75 Mio, base 142 Mio, small 466 Mio, avant quantification | MIT / MIT | Référence pour dicter un message puis le corriger |
| Sherpa-ONNX + Zipformer FR 2023-04-14 | Oui / oui, configuration Kotlin fournie | Véritable streaming avec résultats progressifs | Environ 123 Mio avec encodeur INT8 | Apache 2.0 / Apache 2.0 déclaré | Premier candidat pour voir le texte pendant qu’on parle |
| Sherpa-ONNX + Canary 180M Flash INT8 | Oui / configuration Kotlin disponible | Dictée par segments, non streaming ; ponctuation et capitalisation | Environ 198 Mio | Apache 2.0 / CC BY 4.0 | Autre candidat de taille intermédiaire pour la dictée |
| Vosk small FR 0.22 | Oui / oui, SDK Android | Véritable streaming, résultats partiels puis finals | Archive de 41 Mo ; installation plus volumineuse | Apache 2.0 / Apache 2.0 | Option compacte, notamment pour commandes limitées |
| Sherpa-ONNX + Parakeet TDT 0.6B v3 INT8 | Oui / démo Android publiée | Modèle non streaming ; microphone découpé par détection des silences | Environ 640 Mio | Apache 2.0 / CC BY 4.0 | Option pour appareil plus puissant |
| Sherpa-ONNX + Nemotron 3.5 ASR 0.6B INT8 | Oui / interfaces natives disponibles ; APK multilingue non vérifié | Véritable streaming avec cache ; français France et Canada | Environ 650 Mio | Apache 2.0 / OpenMDW 1.1 | Option récente pour PC, tablette ou téléphone puissant |
| Sherpa-ONNX + Qwen3-ASR 0.6B INT8 | Oui / oui, configuration et exemples officiels | Non streaming, par segments ; simulation progressive par VAD dans cette intégration | Environ 941 Mio, tokenizer compris | Apache 2.0 / Apache 2.0 | Essai secondaire si les ressources du client le permettent |

### Whisper.cpp

Le moteur C/C++ fonctionne sur CPU et propose la quantification des poids. Les modèles multilingues reconnaissent le français ; les variantes portant le suffixe `.en` sont réservées à l’anglais. Le tableau du projet donne environ **388 Mo de RAM pour base** et **852 Mo pour small**, dans sa configuration de référence non quantifiée. Ces valeurs ne sont pas des mesures de notre APK. Q5 réduit la taille, mais son impact sur la transcription française doit être comparé au modèle d’origine. [Dépôt et tableau de référence](https://github.com/ggml-org/whisper.cpp), [code et poids Whisper sous MIT](https://github.com/openai/whisper).

L’exemple Android recommande tiny ou base. Son minimum SDK 26 correspond à Android 8, comme Fred. Il fournit la capture et le pont natif nécessaires ; cela ne démontre pas encore la compatibilité de notre compilation finale. [Exemple Android](https://github.com/ggml-org/whisper.cpp/blob/master/examples/whisper.android/README.md), [configuration de la bibliothèque Android](https://github.com/ggml-org/whisper.cpp/blob/master/examples/whisper.android/lib/build.gradle).

### Sherpa-ONNX et Zipformer français

Le moteur fournit C/C++, Java/Kotlin et Python, avec bibliothèques Android ARM64, ARM32, x86 et x86_64 ainsi que Windows. L’exemple Android VAD/ASR consulté fixe minSdk 21 ; notre minimum 26 dépasse ce minimum déclaré. Il faudra encore vérifier les bibliothèques effectivement embarquées et leur alignement pour les pages mémoire de 16 Ko. [Moteur officiel](https://github.com/k2-fsa/sherpa-onnx), [Gradle de l’exemple Android](https://github.com/k2-fsa/sherpa-onnx/blob/master/android/SherpaOnnxVadAsr/app/build.gradle).

Le modèle `shaojieli/sherpa-onnx-streaming-zipformer-fr-2023-04-14` est réellement français et streaming. Les fichiers sélectionnés représentent environ 123 Mio : encodeur INT8 121 Mio, petit décodeur et joiner. La configuration française est déjà exposée dans le code Kotlin officiel. Le modèle est ancien, mais reste une base concrète pour un premier essai ; les scores publiés ne permettent pas de le classer contre Whisper sur notre usage. [Modèle et fichiers](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html#shaojieli-sherpa-onnx-streaming-zipformer-fr-2023-04-14-french), [licence déclarée du modèle](https://huggingface.co/shaojieli/icefall-asr-commonvoice-fr-pruned-transducer-stateless7-streaming-2023-04-02), [configuration Kotlin](https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/kotlin-api/OnlineRecognizer.kt).

### Canary, Parakeet, Nemotron et Qwen dans Sherpa

**Canary 180M Flash** reconnaît le français, avec source et cible réglées toutes deux sur `fr` pour transcrire plutôt que traduire. La conversion contient 127 Mio d’encodeur et 71 Mio de décodeur. Kotlin expose `OfflineCanaryModelConfig`, mais aucun APK de démonstration Canary prêt à l’emploi n’a été identifié dans la liste examinée. Poids CC BY 4.0, avec attribution à conserver. [Conversion officielle](https://k2-fsa.github.io/sherpa/onnx/nemo/canary.html), [fiche NVIDIA](https://huggingface.co/nvidia/canary-180m-flash), [API Kotlin offline](https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/kotlin-api/OfflineRecognizer.kt).

**Parakeet TDT v3** couvre 25 langues dont le français. Sa conversion INT8 représente environ 640 Mio. Le projet donne une commande Windows et une démo Android explicitement classée dans le streaming simulé : les silences découpent l’audio avant reconnaissance. Les versions Parakeet anglophones ne doivent pas être confondues avec v3 multilingue. Poids CC BY 4.0. [Conversion et preuve Android](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/nemo-transducer-models.html), [fiche NVIDIA](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3).

**Nemotron 3.5 ASR** dispose d’un export multilingue Sherpa daté du 11 juin 2026. `fr-FR` et `fr-CA` sont utilisables directement. Les variantes traitent des blocs de 80, 160, 560 ou 1120 ms : il s’agit de tailles de blocs, pas de délais garantis jusqu’au texte à l’écran. Les poids INT8 font environ 650 Mio. L’option de langue se règle par flux ; Kotlin expose `setOption`. Aucun APK officiel multilingue correspondant n’a été vérifié. Poids OpenMDW 1.1, distincts de la licence Apache du moteur. [Export et paramètres](https://k2-fsa.github.io/sherpa/onnx/nemo/nemotron-streaming.html), [fiche NVIDIA et licence](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b), [API Kotlin du flux](https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/kotlin-api/OnlineStream.kt).

**Qwen3-ASR 0.6B** possède maintenant une voie ONNX pour Android et Windows. Elle ne nécessite pas vLLM dans le téléphone. Les fichiers INT8 représentent environ 941 Mio avec tokenizer. Dans Sherpa, ce modèle relève de `OfflineRecognizer` et les exemples progressifs utilisent un découpage VAD. Une capacité streaming de l’architecture d’origine ne transforme pas automatiquement cette intégration en moteur streaming natif. [Plateformes prises en charge](https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/index.html), [fichiers de la conversion](https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/pretrained.html), [poids Apache 2.0](https://huggingface.co/Qwen/Qwen3-ASR-0.6B-hf).

### Vosk

Le catalogue recommande `vosk-model-small-fr-0.22` pour les usages compacts. Son téléchargement fait 41 Mo, tandis que la mémoire annoncée pour les petits modèles Vosk en général est de l’ordre de 300 Mo. Le français large de 1,4 Go n’est pas le premier choix pour notre APK. Le fournisseur publie des erreurs de mots sur des corpus français ; sans corpus identique entre candidats, ces résultats ne constituent pas un classement de notre dictée. [Catalogue et licences](https://alphacephei.com/vosk/models).

La démo Android actuelle fixe minSdk 21 et `vosk-android:0.3.75`, avec JNA 5.18.1 et les quatre ABI. Ce sont les versions observées dans la démo, pas une promesse de compatibilité de toutes les versions. [Démo Android officielle](https://github.com/alphacep/vosk-android-demo/blob/master/app/build.gradle), [code du moteur](https://github.com/alphacep/vosk-api).

## Reconnaissance fournie par le système

**Android :** l’API explicitement locale existe depuis Android 12/API 31 : tester `isOnDeviceRecognitionAvailable()` avant `createOnDeviceSpeechRecognizer()`. API 33 ajoute la vérification des capacités, des langues installées et le déclenchement du téléchargement ; API 34 ajoute son suivi. La disponibilité d’un service ne suffit pas à prouver que son modèle français est installé. Fred prenant en charge Android 8, cette API ne peut pas être notre seul moteur. [SpeechRecognizer](https://developer.android.com/reference/android/speech/SpeechRecognizer), [état des langues](https://developer.android.com/reference/android/speech/RecognitionSupport).

Avec le service de reconnaissance ordinaire, `EXTRA_PREFER_OFFLINE` peut être ignoré. Il ne garantit donc pas que la voix reste sur l’appareil. Le clavier vocal de l’utilisateur peut servir à saisir du texte, mais ne remplace pas une fonction vocale Fred maîtrisée. [RecognizerIntent](https://developer.android.com/reference/android/speech/RecognizerIntent).

**Windows :** la dictée libre WinRT prédéfinie utilise un service web ; des grammaires locales permettent surtout les commandes. SAPI/System.Speech peut exploiter un moteur installé, dont il faut vérifier la culture française sur chaque PC. Voice Access sait dicter hors ligne après installation de sa langue sur Windows 11 22H2+, mais constitue une fonction d’accessibilité externe. [WinRT](https://learn.microsoft.com/en-us/windows/apps/develop/input/speech-recognition), [moteurs installés](https://learn.microsoft.com/fr-fr/dotnet/api/system.speech.recognition.speechrecognitionengine.installedrecognizers), [Voice Access](https://support.microsoft.com/fr-fr/accessibility/windows/voice-access/set-up-voice-access).

La nouvelle API Windows AI est locale sur CPU ou NPU. Sa documentation du 8 octobre 2026 la déclare toutefois expérimentale, hors production, avec Windows 11 24H2+, SDK expérimental et paquet MSIX côté client. Le français n’est pas établi dans cette page. Ce statut et ces exigences empêchent d’en faire notre base de production commune actuelle. [Documentation Microsoft](https://learn.microsoft.com/en-us/windows/ai/apis/speech-recognition).

**Azure Embedded Speech :** véritable SDK embarqué, français France/Canada, Android API 26 ARM64/ARM32 et Windows 11 x64/ARM64. Estimation mémoire publiée : taille du modèle plus environ 200 Mo. Accès restreint après demande, modèle avec licence ; prix et droit de distribution doivent être obtenus. Le SDK Azure cloud ordinaire n’a pas ces garanties locales. Cette offre Android ne couvre pas l’émulateur x86_64 utilisé pour Fred. [Documentation Embedded Speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/embedded-speech).

## Autres offres commerciales embarquées

**Picovoice Cheetah** transcrit en direct ; **Leopard** traite un enregistrement ou un fichier. Les deux reconnaissent le français sur Android et Windows x64/ARM64, avec calcul de l’audio local. Leurs modèles français font respectivement 31,2 Mo et 25,3 Mo, selon les fichiers affichés par GitHub ; ce ne sont pas des mesures de RAM. [Cheetah officiel](https://github.com/Picovoice/cheetah), [Leopard officiel](https://github.com/Picovoice/leopard), [poids français Cheetah](https://github.com/Picovoice/cheetah/blob/master/lib/common/cheetah_params_fr.pv), [poids français Leopard](https://github.com/Picovoice/leopard/blob/master/lib/common/leopard_params_fr.pv).

Les modules Android déclarent minSdk 21 et les bibliothèques sont disponibles pour ARM64, ARM32, x86 et x86_64. [Module Cheetah](https://github.com/Picovoice/cheetah/blob/master/binding/android/Cheetah/cheetah/build.gradle), [module Leopard](https://github.com/Picovoice/leopard/blob/master/binding/android/Leopard/leopard/build.gradle), [inventaire Cheetah](https://api.github.com/repos/Picovoice/cheetah/contents/lib/android), [inventaire Leopard](https://api.github.com/repos/Picovoice/leopard/contents/lib/android).

Leurs README exigent une **AccessKey validée par les serveurs de licence**, donc une connexion à Picovoice malgré l’audio local. Aucune garantie publique de fonctionnement permanent après une activation unique n’a été trouvée. Bindings et exemples ouverts ne rendent pas les moteurs et modèles propriétaires libres. La FAQ actuelle décrit une offre B2B, essai unique, sans forfait personnel dédié ; contrat et prix sur devis. Cheetah reste une option si le support fournisseur justifie cette dépendance. [Conditions commerciales et techniques](https://picovoice.ai/docs/faq/general/).

**Speechmatics On-device** annonce une bibliothèque C/C++, en direct et différé, sur Windows 11 avec GPU d’au moins 2 Go, et environ 800 Mo de RAM. L’article du 24 septembre 2026 indique Android/iOS à venir ; ce n’est donc pas encore notre moteur commun PC/téléphone/tablette. Le paquet français, son volume, son activation et ses conditions doivent être confirmés avec le fournisseur. [FAQ officielle On-device](https://www.speechmatics.com/company/articles-and-news/on-device-speech-to-text-in-10-questions).

## Candidats à écarter du premier essai français

**Moonshine Voice** propose bien Android, Windows et des modèles streaming, mais sa liste officielle actuelle ne comporte aucun modèle ASR français. Une voix TTS française ne signifie pas une reconnaissance française. [Liste des modèles](https://moonshine-voice.readthedocs.io/en/latest/models/available-models/).

Les services cloud Whisper API, Deepgram ou Azure Speech restent accessibles depuis un client, mais cela ne signifie pas qu’ils exécutent la reconnaissance dans le client. Les gros modèles serveur comme Voxtral ne deviennent pas des composants Android simplement parce qu’ils acceptent de l’audio. Ils ne répondent donc pas au besoin prioritaire de cette étude.

## Architecture proposée pour Fred

```text
Microphone du PC, téléphone ou tablette
             ↓
Capture native et moteur ASR local
             ↓
Texte provisoire, puis texte final modifiable
             ↓
Envoi authentifié du texte par le circuit Fred existant
             ↓
Qwen sur le serveur → réponse affichée
             ↓
Synthèse vocale facultative → lecture dans le client
```

Dans ce fonctionnement, l’audio de dictée reste dans le client. Le texte confirmé rejoint l’historique et les sauvegardes actuels. La dictée peut fonctionner sans Internet après installation du modèle ; **la réponse de Qwen exige toujours une connexion au serveur**.

Android utilise déjà Java, WebView et le pont `AndroidClient`, avec minimum 26 et ABI ARM64/x86_64. Il faut ajouter permission microphone à l’utilisation, capture native `AudioRecord`, worker ASR, annulation et événements de texte vers l’interface. Le manifeste actuel ne demande pas `RECORD_AUDIO`. Le client Windows utilise une interface web et un serveur local Python : un worker natif ou processus auxiliaire peut envoyer les mêmes événements par ce pont protégé. Le calcul ne doit bloquer aucun des fils d’interface.

Une interface commune d’ASR permettra d’essayer les modèles sans réécrire le chat. Elle distinguera chargement, écoute, texte provisoire, texte final, annulation et erreur. Commencer par bouton démarrer/arrêter, correction et envoi explicite. Pendant la dictée, suspendre la lecture de Fred pour éviter que le micro retranscrive sa propre réponse. Détection des silences, interruption naturelle et gestion d’écho viennent après validation de cette première étape.

Les modèles peuvent être proposés comme téléchargements optionnels depuis le serveur Fred, avec version, taille, notices de licence, manifeste signé et SHA-256. Ils restent installés pour les dictées suivantes et peuvent être supprimés. Cela évite d’alourdir systématiquement l’APK actuel avec tous les poids. Les fichiers publics du modèle ne contiennent pas les conversations ; les buffers audio privés seront temporaires et supprimés par défaut.

La console conserve activation, catalogue autorisé et limites administratives ; le client sélectionne une variante compatible avec ses ressources. Aucune substitution automatique par un moteur cloud ne doit avoir lieu dans un mode annoncé local. Une transcription locale ne remplace aucun contrôle des droits du serveur.

La passerelle WireGuard limite actuellement les corps à 2 Mio. Calcul : PCM mono 16 kHz, 16 bits = 32 000 octets/seconde, soit 1,92 Mo par minute ; base64 ajoute environ un tiers et dépasse alors 2 Mio. Envoyer le texte évite ce transfert de dictée. La lecture TTS et un éventuel repli serveur nécessiteront encore des routes audio bornées.

## Essais nécessaires avant choix final

1. Même corpus français de 30 à 50 phrases : questions courtes, noms propres, dates, montants, sigles, silence, bruit et accents. Conserver les transcriptions de référence et comparer erreurs de mots ainsi que nombres critiques.
2. Whisper base multilingue original contre Q5 ; Zipformer FR INT8 ; Vosk small FR. Ajouter Canary si la dictée demande une comparaison supplémentaire. Les modèles de 640–941 Mio viennent ensuite pour les appareils puissants.
3. Mesurer téléchargement/installé, chargement, premier texte et texte final, pic RAM, CPU, chauffe et batterie. Comparer les mêmes enregistrements ; un résultat sur PC n’est pas une mesure de téléphone.
4. Tester téléphone et tablette physiques, permissions refusées, micro occupé, casque/Bluetooth, arrière-plan, interruption, annulation et reprise. Contrôler ARM64/x86_64 et alignement 16 Ko dans les binaires finaux.
5. Après installation, couper le réseau et vérifier la transcription sans trafic audio externe. Puis reconnecter et vérifier l’envoi à Qwen par HTTPS et WireGuard, conservation du brouillon et droits existants.

Les benchmarks des fournisseurs utilisent différents corpus, appareils et réglages. Aucun vainqueur en qualité ou en rapidité sur nos appareils n’est établi ici. Le développement du lot 7 devra publier ses propres mesures et preuves.
