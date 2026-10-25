# Max optionnel AMD / NVIDIA — 24 octobre 2026

## Résultat

La page Vocal propose l'installation locale de Max lorsque Windows identifie une
carte AMD ou NVIDIA. Intel ne reçoit pas cette proposition. Choisir Max ne lance
aucun téléchargement : **Installer Max sur ce PC** calcule d'abord la taille et
l'espace libre nécessaires. **Télécharger et installer** est ensuite une action
explicite. **Plus tard**, la progression, l'annulation, la relance et les erreurs
récupérables sont présents. Les préférences Low / Max et PC / serveur restent
indépendantes et conservées dans les préférences existantes.

Low conserve son moteur Parakeet / Phonon, son détecteur de fin de parole, sa
dictée, ses réglages, sa lecture et son cache. `recognition.py` n'a pas été modifié
par cette tâche. Max ajoute une sous-classe et des fichiers indépendants ; le
worker partagé n'emprunte cette voie que pour un appel Max qualifié. Le complément
peut lire et vérifier les modèles Low déjà présents pour les copier ; il ne les
modifie pas. Une installation Max neuve possède aussi ses propres Silero et
Smart Turn, sans devoir installer ou réparer Low.

Le client de base a d'abord été compilé en staging. Il a ensuite été publié en
**3.5.42** : voir le [rapport de diffusion](../2026-10-24-client-3.5.42/README.md).
Son archive ne contient aucun GGUF, `qwen.dll`, worker
Max, Torch ou Transformers ajouté pour Max. Elle contient uniquement le petit
contrôleur d'installation et les adaptations du parcours.

## Architecture et améliorations reprises

Référence étudiée : [Hugging Face speech-to-speech,
0835002](https://github.com/huggingface/speech-to-speech/tree/0835002ad1c73cf1cc408ac10ebd2a19f777ae12).
Le moteur GPU commun utilise [qwentts.cpp,
5916bf7](https://github.com/ServeurpersoCom/qwentts.cpp/tree/5916bf7c79dbb4e66fc059cdc507a79a23a28bb4),
GGML `cc5df49a6b878db2b68b9a7b45976e279594627d`, et Vulkan. Les modèles
Qwen3-TTS 1.7B CustomVoice Q4_K_M et codec F32 sont épinglés dans
`client-voice/max-models.json`, à la révision GGUF
`b7ee2e8c7459c3bea99da23e3d178125a7d1713c`.

| Amélioration | Intégration |
| --- | --- |
| Vraie synthèse progressive | Callback natif pendant la génération ; les premiers échantillons sont transmis avant la fin de la phrase. Voix Serena, français. |
| Quantification | Poids du générateur en Q4_K_M ; le codec conserve sa précision F32. Aucun environnement Torch à installer sur le client. |
| Transcription progressive | Parakeet int8 sur CPU ; envoi des seuls nouveaux échantillons avec curseur, finalisation et identité de tour liée au propriétaire. |
| Réutilisation du travail | Les phrases stables observées deux fois peuvent être figées avec leurs timestamps ; seule la suite reste à décoder. |
| Chevauchement | La synthèse de la phrase suivante commence pendant la lecture de la précédente, avec files bornées et contre-pression. |
| Pauses et reprises | Smart Turn reste actif ; Max retient brièvement une transcription finale pour réunir une reprise avant l'envoi. La préparation anticipée reste limitée à l'ASR : aucun outil ni écriture d'historique spéculatif. |
| Interruptions | Annulation du calcul, des trames et de la lecture programmée. L'historique interrompu ne considère comme entendues que les phrases dont la lecture est terminée, même après une synchronisation d'historique. |
| Mesures | Temps ASR final, premier texte, première trame TTS et fin de parole → début de lecture estimé dans les informations vocales. Les étapes se chevauchent et ne s'additionnent pas. |
| PC / serveur | Le contrôleur commun sait charger ce complément sur l'une ou l'autre cible ; Auto conserve le choix parmi les cibles testées et disponibles. |

Parakeet TDT reste ici un modèle hors ligne : la réutilisation de phrases n'est
pas un cache d'encodeur natif continu. La borne « lecture » est une estimation de
programmation Web Audio, avec latence de sortie lorsqu'elle est fournie par le
navigateur ; elle ne mesure pas physiquement le haut-parleur. Le transport Kiara
authentifié HTTP/SSE est conservé : ce complément n'annonce pas une implémentation
complète de l'API OpenAI Realtime/WebRTC. L'orbe existant continue de suivre les
états et l'amplitude audio ; aucun alignement de lèvres n'est inventé.

## Taille et distribution

Le paquet signé courant est dans `toolchain/voice-max-release/`. Sa révision est
`vulkan-q4-62db5a83ab69c6c7`. La signature Ed25519 réutilise la clé de mise à jour
serveur existante, sans créer ou remplacer de clé. Les profils clients vérifient
avec leur clé publique déjà épinglée.

| Situation | Téléchargement calculé |
| --- | ---: |
| Installation neuve, aucun modèle local | 2 555 847 223 octets, environ **2,6 Go** |
| Modèles Low déjà installés et vérifiés | 1 876 045 415 octets, environ **1,9 Go** |
| Moteur seul, modèles Max déjà présents | 46 151 015 octets, environ **46 Mo** |
| Runtime installé, hors modèles | 130 196 067 octets |

L'espace libre annoncé inclut les fichiers temporaires et une copie de secours
si le système de fichiers ne permet pas les liens physiques : environ 5,5 Go
sur une installation neuve et 4,8 Go avec Low présent. Ces montants sont calculés
à partir de l'inventaire signé, pas déduits de la seule marque de carte.
Les captures utilisent un montant de disque fictif pour tester le parcours.

Les modèles sont téléchargés publiquement à une révision épinglée puis vérifiés
par SHA-256. Le code vient exclusivement de la passerelle Kiara authentifiée :
`/v1/voice/max/package` et `/v1/voice/max/package/download`. L'archive est
contrôlée avant exécution : inventaire signé, tailles, empreintes, chemins,
doublons et refus des liens/jonctions de redirection. L'activation du nouveau
runtime est atomique ; une interruption avant activation ne remplace pas le
runtime précédent. Les poids Max peuvent être réutilisés lors d'une mise à jour.

Le Vulkan loader est privé au complément ; aucun SDK, pilote ou environnement
Python de développement n'est installé chez l'utilisateur. Les licences du
moteur, de GGML, du loader Vulkan, de la reconnaissance et des poids sont incluses.

Le garde-fou initial exige **4 Go de mémoire graphique libre**, puis un test réel
ASR + synthèse doit réussir. Ce seuil n'est pas une garantie de rapidité. La
mémoire libre NVIDIA est recoupée avec `nvidia-smi` lorsque disponible : le budget
Vulkan peut être plus optimiste que la mémoire réellement libre. Intel et la
bascule CPU silencieuse ne sont pas sélectionnés par le complément local.

## Vérifications réalisées

- Client Windows construit dans
  `toolchain/releases-staging/voice-max-optional/Accès serveur Fred.exe` :
  **94 476 005 octets**. Manifeste de construction présent ; les huit sources
  principales de cette fonctionnalité correspondent à leurs empreintes dans le
  manifeste. `base-package-check.json` confirme l'absence des dépendances lourdes
  Max dans l'EXE de base.
- Huit tests de l'installation : consentement, intégrité/signature, chemins,
  archives altérées/liens, conservation de Low, annulation et relance, réutilisation
  des modèles, refus pendant un appel et exclusion d'Intel.
- Dix tests du contrôleur Max ; onze tests HTTP client et cinq tests de passerelle,
  incluant l'authentification du téléchargement optionnel et le propriétaire des
  trames progressives.
- Vingt-six tests vocaux existants et six suites UI partagées réussis.
- Variantes UI Max + recherche web, installation et chevauchement : réussies.
  Le chevauchement est observé avant la fin de la lecture précédente ; une
  interruption annule la prélecture et conserve seulement ce qui a été entendu.
- Contrôle des sources Python/JS/PowerShell et contrôle UX : réussis ; les neuf
  avertissements UX de textes longs dans la console existaient avant ce parcours.
- Installation réelle du paquet signé dans `toolchain/voice-max-optional-qa`,
  séparément de la production : téléchargement, empreintes, extraction,
  réutilisation des modèles et lancement du test réellement exécutés.

### Mesures natives sur extrait fictif

`native-cpu-streaming.json` : génération Qwen3-TTS quantifiée sur CPU uniquement,
première trame vers **0,38 s**, **41 trames** sur **6,4 s** de son, environ **6,7 s**
de génération et RTF temps de calcul/durée audio de **1,04**. Parakeet reconnaît
« Bonjour, la réunion du projet Orion est prévue demain à 15h. » en environ
**0,55 s**. Il s'agit d'une preuve fonctionnelle sur CPU, pas d'une qualification
GPU ni d'une évaluation perceptuelle générale de la voix française.

`native-progressive.json` utilise le vrai worker EXE : **102 400 échantillons**
envoyés en deux requêtes progressives, exactement autant que l'extrait complet ;
transcription partielle puis finale correctes. `native-recognizer.json` vérifie
aussi Silero, Smart Turn et le nouveau reconnaisseur Max avec les vrais modèles.

Un blocage Windows observé lors du premier essai a été corrigé : NumPy doit être
initialisé avant le thread qui attend les commandes sur stdin. La compilation
finale du complément intègre cette correction et le test du worker empaqueté
est passé ensuite.

Sur ce serveur, le test GPU refuse normalement Max : les P100 sont déjà occupées
et seule la P2200 est exposée par Vulkan, avec moins de 4 Go réellement libres.
Le statut reste `installed: true`, `available: false`, avec un message permettant
de choisir une autre cible ou Low. Aucune inférence GPU ni modification du modèle
Qwen en production n'a été effectuée. Aucun matériel AMD physique n'était
disponible : sa validation repose sur le backend Vulkan compilé et devra être
confirmée par le test réel sur la machine concernée.

### Vérification visuelle

Skill `ux-visual-audit`, Playwright MCP sur une fixture locale avec données
fictives, sans compte de production : bureau 1440×1000, tablette 768×1024,
fenêtre étroite 390×844, clair et sombre. Captures ouvertes et examinées :
`desktop-installation.png`, `tablet-installation.png`, `narrow-installation.png`
et `dark-progress.png`. Taille, confirmation, « Plus tard », progression,
annulation et restauration du focus ont été vérifiés. Aucun débordement horizontal
observé. Une finition P3 du bouton principal a été corrigée en réutilisant les
classes partagées `secondary primary`. Pas d'audit WCAG complet ni de test Android
sur appareil ; la conversation automatique reste réservée au client Windows.

## Reconstruction et mise en service

Le build de base `Build-Client.ps1` ne construit et n'embarque jamais le complément.
La compilation optionnelle utilise CMake 3.31.8, Ninja 1.12.1, MSVC du projet et
Vulkan SDK **1.4.363.0**, préparé dans `toolchain` en mode copie sans installation
de pilote. Empreinte de l'installateur officiel :
`94a82d378f7a5e3e54c9db7d2fb7016af136e14ac0a18dbf0f2f67a36352d141`.
Le loader officiel provient du zip VulkanRT 1.4.363.0, empreinte
`a25a927aa8b9f0371048f1861cf88ac3b9bc9b1fb332c42d897c8ab32695769a`.

Après checkout des deux commits ci-dessus, appliquer
`client-voice/qwentts-windows-spaces.patch` au sous-module GGML : il corrige
l'échappement des chemins Windows dans le générateur de shaders, sans modifier
les calculs du moteur. Lancer ensuite :

```powershell
& client-voice/Build-Max-Native.cmd
& 'Strata-src/.venv/Scripts/python.exe' client-voice/package_max.py --sign-home lanceur
```

Le script de packaging réutilise l'environnement de compilation de conversation,
mais place le worker, les DLL et les notices dans une archive séparée. Pour un
serveur où l'administrateur souhaite installer ce nouveau moteur, après examen
du plan de téléchargement :

```powershell
& 'Strata-src/.venv/Scripts/python.exe' client-voice/prepare_max_pack.py --server
& 'Strata-src/.venv/Scripts/python.exe' client-voice/prepare_max_pack.py --server --download
```

L'ancien `prepare_max.py` conserve l'installation historique Voxtral/Torch ; ce
n'est pas le nouveau complément proposé aux clients.

La diffusion ultérieure en **3.5.42** charge les nouvelles routes et prépare les
EXE personnels suivant `RECONSTRUIRE-FRED.md`, avec sauvegarde vérifiée,
signature des versions et contrôle des profils existants. Les preuves de cette
mise en service figurent dans `maintenance/2026-10-24-client-3.5.42/`.
