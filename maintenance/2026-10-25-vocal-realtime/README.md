# Vocal : diagnostic et correction du 25 octobre 2026

Livraison ciblée : Windows/serveur **3.5.51**, Android **1.0.22 / code 23**,
complément signé **vocal-rt-f88da3269d16c833**, API 6.
Les fichiers `*-publication.json` et `production.json` confirment les publications
effectivement terminées ; leur absence ne doit pas être présentée comme une livraison.

## Ce qui n'allait pas

- Une demande orale ordinaire passait par une génération supplémentaire de
  classification web avant sa réponse. Les nouvelles versions utilisent une seule
  génération pour répondre ou sélectionner une recherche publique. Seule une
  recherche effectivement demandée conserve une validation supplémentaire de la
  requête à partir du dialogue sans les documents privés, avant appel au fournisseur.
  Les droits web et l'annulation restent appliqués.
- Qwen3-TTS 1.7B était un mauvais compromis pour cette conversation française locale.
  Son coût s'ajoutait aux fragments de texte trop courts et aux appels répétés.
- Le découpage Max pouvait lancer la synthèse au milieu d'un groupe de mots après
  80 caractères. La file pouvait aussi abandonner la fin d'une réponse longue.
- La reprise d'écoute conservait une fenêtre de 350 ms après la lecture : des mots
  pouvaient être ignorés alors que l'écran annonçait déjà l'écoute.
- Une continuation déjà capturée, mais dont le décodage était encore en attente,
  pouvait laisser partir la première moitié comme une demande indépendante.
- Une interruption du flux audio arrêtait aussi le son déjà reçu et programmé.
- Le calcul de taille des anciens dossiers Python Max parcourait chaque ascendant
  de chaque fichier et pouvait bloquer le verrou de progression de l'installation.

Les anciens tests séparés et les simulations d'interface ne suffisaient pas à
établir la qualité d'une conversation réelle. Les essais complets ci-dessous ont
également rejeté une première configuration Whisper qui répétait les questions
courtes : les horodatages de décodage ont été rétablis avant publication.

## Architecture retenue

Max reconnaît le français avec **Whisper large-v3-turbo Q5**, via whisper.cpp 1.9.5
et Vulkan, sur la carte AMD/NVIDIA choisie. Les identités PCI persistantes et la
préférence pour une carte dédiée sont conservées. Une erreur GPU ne provoque pas
un basculement silencieux vers l'iGPU ou le CPU.

La voix Max est **Phonon 40m français Q8, Tiphaine**, calculée sur CPU, en trames
PCM de 80 ms. Le moteur de voix cesse ainsi de concurrencer la reconnaissance GPU.
Le contexte d'encodage Whisper est borné selon la durée audio ; le décodage conserve
les horodatages internes et le français forcé. La transcription finale relit la
fenêtre complète, sans supprimer un préfixe sur la foi d'horodatages incertains.

Le complément représente **692 388 589 octets** pour une installation neuve,
**683 065 553 octets** si les deux petits modèles de détection sont réutilisables.
Le plan d'installation affiche le montant réel avant téléchargement. Les poids et
les dépendances Max restent hors de l'EXE de base, d'environ 94,5 Mo. La suppression
de tous les fichiers Max et l'ouverture de leur dossier sont conservées. Un test
lent ou non concluant conseille, sans interdire l'utilisation de Max.

Low conserve ses moteurs et seuils : Parakeet sur Windows, Whisper Small sur
Android, Phonon côté serveur. La dictée du chat reste indépendante. Les nouvelles
demandes orales bénéficient du transport de réponse simplifié ; les anciens clients
restent acceptés. La limite orale reste 16 384 tokens, avec une réserve de réponse
de 1 024 tokens pour les nouveaux clients, sans modifier l'historique enregistré.

Les réponses ordinaires sont diffusées dès leurs premiers mots. Le marqueur de
recherche reste interne et ne déclenche un outil qu'après validation complète.
Une réponse naturelle ou numérique sans marqueur reste lisible, sans nouvel appel
au modèle ; les objets de routage JSON ne sont pas lus à voix haute.

## Contexte du modèle et compromis de latence

La suppression de toutes les captures de contexte semblait gagner environ trois
secondes sur un préfixe déjà chaud. Mais elle empêchait ensuite la réutilisation
correcte d'un dialogue qui s'allonge. **Cette optimisation seule a été abandonnée.**
Les réponses conservent les captures de conversation et épinglent uniquement les
consignes stables avec `strata_prefix`, sans déplacer cette racine à chaque tour.
Les captures ordinaires du moteur réutilisent le dialogue ; le contexte courant
est toujours borné après réduction et ajout de sources web.
Seul l'ancien classificateur web, qui reste une requête ponctuelle, désactive sa
capture. Aucun réglage global ni redémarrage de Qwen n'est nécessaire.

Sur les cinq demandes synthétiques de `reply-pinned-checkpoints.log`, la première
réponse a commencé à 4,50 s, puis les réponses ordinaires à 1,62–1,66 s. Il s'agit
du premier texte du modèle, sans reconnaissance ni lecture audio.

## Vérifications et limites

- `stack-validation.json` : installation signée réelle, worker figé, vrai Vulkan
  sur **Quadro P2200**, détection de parole, transcription, Qwen de production déjà
  chargé, puis synthèse PCM. Les questions sont fictives, sans historique utilisateur.
  Premier échange : premier son après 5,65 s ; suivant : 3,00 s après la fin du son
  rejoué. Aucun trou de lecture mesuré sur ces deux réponses.
- `pause-validation.json` : enregistrement humain français FLEURS avec une pause
  de 800 ms ajoutée au milieu ; une seule demande complète, sans envoi prématuré.
- `short-asr.json` : deux questions courtes reconnues sans répétition, en 0,65 et
  0,33 s sur P2200. Le test automatique réel du serveur est fonctionnel, environ
  0,66 s pour sa transcription et 0,30 s pour le premier son de synthèse.
- `asr-vulkan-comparison.json`, `corpus.json` : huit extraits FLEURS français,
  environ 88 secondes, licence CC-BY-4.0. Ce petit corpus ne démontre pas une
  supériorité générale ; noms propres et écriture des nombres influencent les erreurs.
- `phonon-timings.json` et `qwen-timings.json` : mêmes trois textes sur CPU ; Phonon
  commence en environ 50–120 ms lors de cet essai, contre 0,5–3,4 s pour Qwen-TTS.
  Ces chiffres ne sont pas une mesure sur RX 7800 XT.
- 13 suites UI partagées Windows/Android, avec réponses longues, abréviations,
  décimales, reprise immédiate, erreur audio, interruptions et conservation de Low.
- Journaux des tests Python client, workers, passerelle et Android. La dernière
  suite serveur de 48 tests a rencontré un timeout HTTP isolé ; le test concerné
  passe lors de sa reprise individuelle, en 194 secondes avec sa préparation. Les
  six tests du nouveau transport et les cinq du décodeur passent séparément. Contrôle des
  sources et contrôle UX. Les neuf avertissements UX concernent des textes longs
  préexistants de la console serveur et ont été conservés.

Le micro physique, le casque du client, une RX 7800 XT et un téléphone Android
physique n'ont pas été testés ici. Les essais avec parole rejouée et les simulations
d'AudioContext ne remplacent pas cette vérification matérielle.

Le contrôle de cinq tours avec des consignes synthétiques nouvelles passe aussi
(`dialogue-fresh-five-turns.log`) : 37, puis 42, 84, 80 et 40, sans perte de contexte.
Le premier texte a cependant demandé **19,3 s au premier tour**, puis **2,6 à 4,9 s**.
Une autre série avec le préfixe déjà en cache était à 0,8–2,1 s. Ces mesures ne
permettent pas de présenter le serveur comme constamment réactif.

### Lenteurs du serveur encore observées

Une série supplémentaire, `dialogue-validation.log`, a rencontré un premier
préremplissage de **206,6 secondes**, puis environ **175 secondes** sur la demande
suivante. La seconde réponse numérique sans marqueur a aussi exposé le défaut de
validation désormais corrigé. Cette première série ne doit pas être comptée comme
réussie. Le fichier `dialogue-validation.json`, s'il existe, décrit une nouvelle
série terminée après correction, sans effacer cette première observation.

Pendant ces attentes, les deux P100 étaient à 0 % d'utilisation. Une mesure Windows
montrait huit requêtes en attente sur D: et aucun débit, alors que C: répondait.
D: est un disque SATA ST5000DM000 de 5 To ; Windows le déclarait sain et aucune
erreur 7/11/51/129/153/157 n'a été retournée dans la dernière heure inspectée.
Les journaux du moteur confirment toujours la table ngram sur C: et les experts
résidents en RAM, sans lecture de leurs fichiers pendant ces réponses.

Ces observations établissent une attente supplémentaire à examiner ; elles ne
prouvent ni une panne de disque, ni sa responsabilité exclusive. Il serait faux
de garantir une latence constante de trois secondes sur ce serveur.

## Reconstruction et publication

1. Construire `client-voice/Build-Max-ASR.cmd`. Les sources Whisper épinglées et le
   patch Windows des chemins Vulkan avec espaces sont vérifiés par le constructeur.
2. Préparer le runtime isolé `toolchain/max-realtime-python` à partir de
   `client-voice/requirements-max-realtime.txt`, puis exécuter `package_max.py` avec
   les clés existantes. Les notices et le modèle Phonon vérifié restent dans le pack.
3. Exécuter `validate_stack.py`, `validate_pause.py` et les contrôles partagés.
4. Construire Windows avec `Build-Client.ps1` et Android avec `Build-Android.ps1`,
   vers les dossiers de staging correspondant aux versions ci-dessus.
5. Effectuer une sauvegarde manuelle chiffrée vérifiée. `install_server.py` conserve
   les anciens poids et installe Max sur la P2200 disponible, puis décharge ses workers.
6. `publish_pack.py`, `publish_windows.py`, puis `publish_android.py` vérifient les
   signatures, les téléchargements servis et les identités de mise à jour. Les
   anciennes distributions sont conservées pour récupération.

L'état d'activation Phonon Low demandé précédemment est préservé : il reste désactivé
et déchargé sur ce serveur. Max est indépendant et charge ses moteurs lors de son
utilisation. Les identifiants personnels, historiques, clés et paramètres de
sauvegarde sont comparés avant/après ; Qwen conserve son processus déjà chargé.
