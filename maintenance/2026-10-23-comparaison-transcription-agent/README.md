# Comparaison de la transcription audio — Agent et Fred

Rapport du 23 octobre 2026. Périmètre : sources locales des projets Codex **Agent** (`D:\Agent`) et **Serveur IA / Fred** (`D:\Serveur IA`).

## Conclusion

**Agent possède une chaîne de réunion plus complète ; Fred possède une chaîne mieux adaptée au dialogue vocal.** Le principal apport d’Agent à Fred serait la conservation, la reprise, l’attribution des prises de parole et la validation du texte. L’examen ne justifie pas de remplacer Parakeet dans la conversation Windows par le Whisper Medium d’Agent.

Les deux applications font leur reconnaissance localement dans les chemins examinés. Elles poursuivent cependant des objectifs différents : Agent transforme un enregistrement en document métier vérifié ; Fred transforme la parole en message pour obtenir une réponse orale ou écrite.

**Aucun gagnant général en précision n’est démontré.** Les essais disponibles portent sur des corpus et des métriques différents. Aucun nouveau benchmark commun n’a été exécuté pour ce rapport.

## 1. Méthode et niveau de preuve

L’analyse couvre les guides courants, les sélecteurs de modèles, les workers de reconnaissance, la capture, la reprise, les contrôles de validation et les tests ciblés présents dans les sources.

- Agent : commit local `184eecb`, arbre de travail propre au moment du relevé.
- Fred : commit de base `aba4da8`, avec de nombreuses modifications locales, dont la migration Parakeet. Ce rapport analyse **les fichiers actuels**, pas uniquement le dernier commit.
- Le fichier de version Windows de Fred indique **3.5.37**. Les guides vocaux et la preuve de migration Parakeet portent encore la version **3.5.35**. Cela ne prouve pas la version effectivement ouverte chez chaque utilisateur.
- Les résultats Fred du 23 octobre ont été lus dans leurs JSON locaux. Les résultats Agent cités sont **rapportés par sa documentation** : les dossiers `logs/foresight-runtime`, les modèles et les environnements privés correspondants ne sont pas présents dans le checkout `D:\Agent` examiné. Leurs mesures n’ont donc pas été revérifiées dans les preuves brutes.
- Aucun microphone ouvert, aucune base métier consultée ou modifiée, aucun modèle chargé et aucun service redémarré. Les suites de tests n’ont pas été rejouées ; leur présence et certains contrats ont été examinés.

Les conclusions d’architecture reposent sur le code. Les performances publiées sont distinguées des observations réalisées pendant cette analyse. Les limites des deux produits restent explicites.

## 2. Ce que fait réellement Agent

### Capture et conservation

Agent propose le microphone, le son du PC ou les deux pistes. La capture Windows native s’appuie sur WASAPI ; un parcours navigateur existe également. Le guide précise que le son système est le mix de la sortie sélectionnée : d’autres applications peuvent donc y être présentes.

Le parcours natif conserve des fragments Ogg/Opus, avec empreintes, reçus et reprise. Le service contrôle le périmètre des chemins, la taille et le SHA-256 avant d’exploiter un fragment. Les erreurs de stockage et de périphérique sont traitées séparément de la transcription. Une saturation de la transcription peut laisser l’audio conservé pour un traitement explicite ultérieur.

Les limites centrales prévoient jusqu’à **12 heures et 512 Mio de capture**, avec un budget distinct pour le retard du direct. Ce sont des plafonds logiciels, pas une preuve d’endurance de douze heures ni une promesse que tous les parcours d’import acceptent cette durée.

### Reconnaissance directe

Le code courant préfère **Whisper Medium installé**, sur **faster-whisper 1.2.1 / CTranslate2**, **CPU int8**, quatre threads par défaut. Un autre dossier reste possible par configuration et un profil incomplet conserve le chemin antérieur. Une ancienne note de `docs/25_REALTIME_VOICE.md` décrit encore Small pour le direct ; le sélecteur actuel et ses tests privilégient bien Medium.

Le worker reste résident pendant le traitement et produit des segments horodatés à partir des fragments. Le décodage force le français, utilise un faisceau de cinq hypothèses (`beam_size=5`), les horodatages des mots et un filtre de parole. Il ne conditionne pas le décodage sur le texte précédent. Le service gère aussi du contexte audio entre fragments et la révision du texte provisoire, avec protection des corrections humaines.

Il s’agit d’un **traitement progressif de fragments**, pas d’un modèle de reconnaissance nativement streaming. Les étiquettes micro/système du direct ne constituent pas l’identification certaine d’une personne.

### Transcription complète et séparation des voix

Après l’arrêt, une passe complète peut reconnaître le texte et séparer les intervenants : segmentation de type pyannote via sherpa-onnx, extraction d’empreintes vocales, regroupement et association des mots aux plages de parole.

Pour les longs fichiers, le worker prévoit des fenêtres de quinze minutes, avec soixante secondes de recouvrement et regroupement global des empreintes. Cette capacité est distincte du traitement direct. La séparation des voix **ne démêle pas automatiquement toutes les paroles simultanées** et ne fournit pas les vrais noms des personnes : une relecture reste prévue.

### Production métier

La chaîne va jusqu’à la correction, la validation de la transcription, la préparation du compte rendu, sa validation et son enregistrement. Le code vérifie les révisions : un compte rendu ne doit pas être publié à partir d’une ancienne transcription devenue obsolète. Les révisions antérieures sont conservées et les actions restent explicites.

### Calcul et isolation

Un environnement vocal séparé contient les dépendances verrouillées. Une option CUDA existe pour Medium avec un profil précis et des contrôles d’identité du runtime. **Le CPU reste le choix conservé selon la documentation courante ; le GPU est en essai.** La présence de ce code ne prouve pas sa disponibilité sur le matériel de Fred.

Les tâches complètes et le direct partagent un arbitrage de ressources qui empêche certains traitements simultanés. Les sous-processus Windows disposent de mécanismes de fermeture et les délais sont bornés.

Sources principales : [sélection et profil ASR](D:/Agent/app/services/live_speech.py:35), [worker direct](D:/Agent/scripts/transcribe_live.py:17), [passe complète et diarisation](D:/Agent/scripts/transcribe_meeting.py:62), [contrôle des fragments](D:/Agent/app/services/audio_capture.py:32), [admission](D:/Agent/app/services/speech_admission.py), [arbitrage CPU](D:/Agent/app/services/audio_cpu_coordinator.py), [validation des révisions](D:/Agent/app/services/meeting_audio.py:118), [guide utilisateur](D:/Agent/docs/56_MEETING_START_GUIDE.md).

## 3. Ce que fait Fred aujourd’hui

### Windows

Le client instancie désormais `DictationService` et `ConversationService` avec **le même Parakeet TDT 0.6B v3 int8**, exécuté par sherpa-onnx sur CPU, quatre threads. Le catalogue partagé contient environ **680 Mo**, dont environ 670,5 Mo de fichiers ASR. Les empreintes sont vérifiées avant utilisation.

Le microphone produit du PCM mono 16 kHz en mémoire. Le DSP Windows gère annulation d’écho, réduction de bruit et contrôle du gain. Le code aligne les périphériques de capture et de lecture sur les périphériques Windows par défaut.

**Silero détecte la parole ; Smart Turn estime la fin de tour ; Parakeet reconnaît les mots.** Parakeet fonctionne ici par fenêtres recalculées. Les aperçus sont proposés à intervalles d’environ une seconde d’audio, sous réserve que le calcul suive ; cela ne garantit pas leur affichage chaque seconde.

Le décodage est séparé de la récupération du microphone. Les finales sont prioritaires sur les aperçus et les files sont bornées. En conversation, le moteur examine la fin de tour après au moins 850 ms de silence, puis termine au plus tard à 2,5 s de silence. Un segment est limité à 28 s.

- **Dictée :** deux minutes maximum, correction et envoi manuel, annulation avec restauration du brouillon.
- **Conversation :** quinze minutes maximum par session, envoi automatique du texte, Qwen local pour répondre, Phonon serveur pour parler, interruption de la réponse lors d’une reprise reconnue.

Le navigateur complète l’annulation acoustique par un filtre de texte ressemblant à la lecture récente. Ce filtre évite certains faux déclenchements, mais une répétition volontaire des mots de Fred peut rester ambiguë. Aucun résultat acoustique général en conditions humaines n’est établi.

Le microphone n’est ni archivé ni transmis au serveur dans ce parcours. Le texte envoyé rejoint le chat et son historique. Cette conception préserve la confidentialité audio, mais ne permet pas de rejouer l’original pour retranscrire un mot perdu.

### Android

Android conserve **Whisper.cpp 1.9.5 et Whisper Small multilingue**, français forcé, modèle d’environ 488 Mo. Le microphone utilise `AudioRecord`, en mode `VOICE_RECOGNITION` dans le code actuel. La conversation automatique Windows et son annulation d’écho ne doivent donc pas être attribuées au client Android.

Canary 180M Flash et l’éventuelle reconnaissance sur PC restent des pistes d’étude dans la documentation : ce ne sont pas des fonctions Android livrées par les sources examinées.

Sources principales : [raccord client](<D:/Serveur IA/client-qwen/client.py:343>), [moteur Parakeet et fins de tour](<D:/Serveur IA/client-voice/recognition.py:15>), [limites de session](<D:/Serveur IA/client-voice/conversation_worker.py:73>), [DSP Windows](<D:/Serveur IA/client-voice/fred_aec.cpp:107>), [gestion de l’écho et de l’interruption](<D:/Serveur IA/client-qwen/conversation.js:42>), [capture Android](<D:/Serveur IA/client-android/app/src/main/java/net/karenax/fred/LocalVoice.java:97>).

## 4. Comparaison fonctionnelle

| Critère | Agent | Fred |
| --- | --- | --- |
| Usage principal | Réunion, preuve, compte rendu | Dictée et dialogue avec l’assistant |
| Moteur courant sur PC | Whisper Medium préféré, faster-whisper CPU int8 | Parakeet v3 int8, sherpa-onnx CPU |
| Fonctionnement progressif | Fragments conservés, segments horodatés | Fenêtres en mémoire, aperçus puis finale |
| Microphone et son système | Deux sources possibles, séparées | Microphone ; sortie utilisée pour l’AEC |
| Conservation de l’audio | Oui dans le parcours réunion | Non dans le parcours vocal examiné |
| Reprise et nouvelle transcription | Depuis les fragments conservés | Refaire la dictée si l’original est perdu |
| Intervenants | Diarisation complète, noms à corriger | Pas de diarisation de réunion identifiée |
| Corrections | Révisions persistantes et validation | Brouillon de dictée et historique du chat |
| Protection avant compte rendu | Validation liée à la bonne révision | Pas de parcours équivalent dans le module vocal examiné |
| Réponse orale et interruption | Pas de boucle équivalente établie dans les modules examinés | Qwen + Phonon, fin de tour et interruption |
| Fonctionnement sans réseau | ASR local ; chaîne locale complète rapportée dans les recettes | ASR local ; réponse de l’assistant dépend du serveur Fred |
| Téléphone | Pas d’ASR Android natif identifié dans ce périmètre | Dictée Android Whisper Small |
| GPU | Option CUDA en essai | ASR CPU ; aucun besoin GPU ajouté par cette reconnaissance |

Le son système utile aux réunions et le son de référence utilisé pour annuler l’écho répondent à deux besoins différents. Reprendre la capture Agent ne constitue pas une amélioration automatique de l’AEC de Fred.

## 5. Performances : ce qu’on peut conclure

| Système et protocole | Résultat disponible | Portée |
| --- | --- | --- |
| Agent Medium CPU, 15 phrases fictives et 26 Opus | P50 chaud **6,82 s**, P95 chaud **7,74 s**, chargement froid **22,44 s** | Délai après fin de parole annotée jusqu’au texte visible, rapporté dans la documentation |
| Fred Parakeet, extrait français synthétique de 10,05 s | **0,64 s** de décodage en une passe | Calcul seul, JSON local consulté |
| Fred Parakeet, worker empaqueté, même extrait | **1,01 s** de calcul en conversation ; **1,54 s** en dictée | Chaîne VAD/fin de tour/aperçus/finale, alimentée sans attente temps réel |
| Fred worker empaqueté | Pic RSS d’environ **947 Mo** ; durée murale du scénario d’environ **3,86 s** en conversation | Scénario d’essai, pas délai humain après la parole |
| Fred ancien Whisper Small, protocole local de comparaison | **4,98 s** de calcul sur l’extrait de 10,05 s | Ne représente ni Whisper Medium d’Agent ni un téléphone physique |

**Diviser 7,74 par 0,64 pour annoncer un gain de vitesse serait incorrect.** Le premier chiffre inclut le parcours jusqu’à l’affichage ; le second mesure une passe de décodage. Le corpus et les conditions diffèrent également. La mémoire actuelle de Medium n’est pas établie ici par une mesure comparable.

Les résultats Fred soutiennent le maintien de Parakeet comme choix de travail pour le dialogue, mais ne démontrent pas sa supériorité générale en français. Les résultats Agent montrent une chaîne vérifiable et documentent un retard du direct supérieur à sa cible initiale de cinq secondes.

Sources : [mesures Agent publiées](D:/Agent/docs/23_MEETING_AUDIO.md:38), [comparaison Fred](<D:/Serveur IA/maintenance/2026-10-23-reconnaissance/README.md>), [mesures Parakeet brutes](<D:/Serveur IA/maintenance/2026-10-23-reconnaissance/parakeet-results.json>), [worker empaqueté](<D:/Serveur IA/maintenance/2026-10-23-reconnaissance/native-results.json>).

## 6. Précision et risques métier

Agent documente des erreurs sur les termes techniques, les réserves et les négations en présence de bruit ou de paroles simultanées. Ses essais Qwen3-ASR 0.6B et Canary 1B v2 sur deux extraits difficiles n’ont pas résolu tous ces défauts et n’ont pas conduit à leur adoption. Ces résultats ne portent ni sur Parakeet ni sur le Canary 180M étudié pour Fred.

Fred a correctement traité les quelques extraits de son étude, y compris des variantes de volume et de bruit. Ce corpus réduit ne mesure pas suffisamment les noms propres, les montants, les négations métier, les accents ou les échanges spontanés. L’ouverture et la fermeture réelles du microphone ont été vérifiées ; cela ne vaut pas une qualification de reconnaissance de la voix de l’utilisateur ou de double parole acoustique.

Le point fort d’Agent est de traiter une transcription comme **un résultat à relire**, dont la source et la révision restent accessibles. Un mot perdu par Fred peut partir directement vers Qwen en conversation. Pour une décision ou une demande ambiguë, une confirmation reste utile ; changer uniquement le modèle ne règle pas ce risque.

Les tests présents couvrent notamment les corrections humaines concurrentes, les reçus après erreur disque et l’arbitrage CPU côté Agent ; les sessions obsolètes, les modèles corrompus, le cache partagé et l’annulation côté Fred. Ce rapport ne transforme pas ces tests en preuve d’une précision acoustique générale.

## 7. Recommandations pour Fred

### Priorité 1 — Comparer la précision sur un corpus commun

Conserver Parakeet Windows comme référence actuelle et comparer **Parakeet v3 contre le profil exact Whisper Medium d’Agent**, sur le même PC et les mêmes fichiers fictifs ou explicitement autorisés.

Prévoir des phrases spontanées, noms propres, dates, montants, unités, négations, bruit, faible volume et chevauchement de voix. Ne pas fournir les réponses attendues comme prompt. Mesurer séparément chargement froid, première transcription, finale après fin de parole, affichage, erreur de mots et conservation des faits critiques. Pour le dialogue, mesurer aussi premier texte Qwen et premier son Phonon. Rapporter P50/P95 chauds sur suffisamment de répétitions et la mémoire avec la même méthode.

La réussite doit porter sur l’usage : comprendre correctement les demandes et rester fluide. Le passage de tous les tests logiciels ne remplace pas cette comparaison.

### Priorité 2 — Reprendre les outils de qualification d’Agent

Adapter sa distinction entre moteur **installé**, **chargé**, **opérationnel sur le scénario testé** et **qualifié sur un corpus**. Relier les résultats à l’empreinte du modèle, au runtime et au protocole pour éviter de réutiliser un ancien score après changement de moteur.

Reprendre aussi ses critères métier : une bonne moyenne ne doit pas masquer une valeur incorrecte ou une négation disparue. Les diagnostics peuvent recevoir ces mesures sans alourdir l’interface de conversation.

### Priorité 3 — Si un mode Réunion est souhaité

Créer un parcours explicite de réunion avec conservation choisie, reprise, pistes micro/système, horodatage, correction, puis validation du compte rendu. Ce serait une fonction nouvelle de Fred, avec ses propres règles de durée, stockage, accès et suppression. La conservation audio modifierait le fonctionnement actuel et doit être clairement choisie.

La séparation des intervenants peut venir ensuite. Avant sa validation, les étiquettes proposées doivent rester corrigeables et ne pas être présentées comme des identités certaines. Garder distincts texte provisoire, transcription validée et document publié, comme dans Agent.

### Priorité 4 — Android et GPU

Ne pas importer automatiquement la pile Medium/CUDA d’Agent dans Android ou dans les runtimes serveur de Fred. Les contraintes et les plateformes diffèrent. Les pistes Android déjà identifiées demandent des essais sur téléphone physique. Une éventuelle accélération GPU doit être qualifiée séparément et ne pas reprendre les résultats obtenus sur un autre matériel.

## Décision proposée

**Pour parler à Fred : garder l’architecture Parakeet → Qwen → Phonon et renforcer sa qualification sur la voix et les usages réels. Pour enregistrer des réunions : s’inspirer de la chaîne documentaire d’Agent.**

Agent apporte surtout une meilleure maîtrise de ce qui se passe avant et après la reconnaissance. Son code ne démontre pas qu’un remplacement du moteur actuel de Fred améliorerait la précision ou la fluidité.
