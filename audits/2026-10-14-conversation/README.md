# Audit et correction de la conversation vocale Windows — 14 octobre 2026

La capture de référence montre Fred Windows 3.5.28, une transcription envoyée,
des réponses interrompues avant leur première phrase et l’arrêt du mode vocal
avec un message de connexion/synchronisation. La photo Android précédente a
été écartée à la demande de l’utilisateur ; elle ne sert pas au diagnostic.

## Défauts établis et corrections

| Défaut | Preuve et conséquence | Correction |
| --- | --- | --- |
| Erreur Hermes terminale confondue avec une rupture réseau | L’ancien proxy ajoute `connection_error` après une erreur SSE sans `[DONE]`, désactive la connexion et fait raccrocher la voix. Reproduit par `transport-before.log`. | L’erreur métier est transmise une seule fois ; une véritable rupture sans événement terminal reste signalée. |
| Annulation volontaire confondue avec une rupture réseau | Même traitement d’un flux arrêté par l’utilisateur ; l’ancienne source échoue au test d’annulation. | Reçus bornés par identifiant de demande ; une annulation ne déconnecte pas Fred et n’annule pas un autre tour. |
| Capture AEC dépendante d’une sortie audio active | Le moteur source a réellement échoué pendant la lecture microphone, avant toute trame. L’ancien worker pouvait annoncer l’écoute avant l’ouverture du micro. | Flux WASAPI partagé silencieux pendant l’écoute, source mode explicite, erreurs HRESULT lisibles. État « listening » seulement après réception de PCM ; délai de cinq secondes sans trame. |
| Parcours oral dépendant des runs Hermes | Attente de la réponse finale et traitement d’outils avant la lecture. | Voix directement vers Qwen local via la passerelle personnelle, streaming par phrases, sans réflexion ni outils, limite de sortie de 512 tokens. Le chat écrit garde Hermes. |
| Réponses courtes et phrases longues mal découpées | Une première ponctuation avant douze caractères bloquait les phrases suivantes ; un segment long pouvait être tronqué à 600 caractères. | Les courtes phrases comme « Oui. » sont lues immédiatement ; segmentation bornée des longues phrases. |
| Raccrochage impossible à réessayer après une erreur | `active=false` avec verrou vocal conservé désactivait le bouton. | Bouton de reprise du raccrochage ; conservation de la réponse terminée après erreur/fermeture. |
| Horloge audio conservée entre deux sessions | Après raccrochage, la nouvelle `AudioContext` repartait à zéro mais la file gardait le temps de l’ancienne session ; le premier son pouvait attendre plusieurs secondes. Reproduit par le test de reprise. | Réinitialisation de l’horloge à la fermeture et à l’ouverture ; reprise testée avec lecture d’une première phrase avant la fin du LLM. |
| Réponse JSON de secours non lue | La réponse texte hors SSE n’alimentait pas la file vocale. | Même alimentation de la lecture que pour le streaming. |
| Descripteurs du worker non fermés | Les tubes stdin/stdout n’étaient pas explicitement libérés à la fin d’une session. | Fermeture des tubes après arrêt du worker. |

Microsoft précise que le DSP AEC en mode source ne produit pas de sortie si
le périphérique de rendu n’a aucun flux actif :
[MFPKEY_WMAAECMA_DEVICE_INDEXES](https://learn.microsoft.com/en-us/windows/win32/medfound/mfpkey-wmaaecma-device-indexesproperty).
Le maintien du flux silencieux a permis de recevoir plus de 16 000 échantillons
réels du micro puis de fermer proprement le moteur, en source et dans le worker
empaqueté. Aucun son ni texte issu du microphone n’a été enregistré.

## Validation

- `transport-before.log` reproduit les deux défauts réseau sur la source HEAD ;
  `test_voice_transport.py` valide leurs corrections et garde la détection d’une
  vraie rupture.
- `test_voice_conversation.py` vérifie le contournement d’un Hermes indisponible,
  le modèle local imposé, l’absence d’outils, l’identité des tours, les droits du
  projet, la révocation et l’annulation avant envoi ou pendant un flux silencieux.
- `ui-conversation.log` et `ui-conversation-automatic.log` vérifient les tours
  automatiques, la synchronisation différée, le premier son avant la fin du LLM,
  l’interruption, le raccrochage et sa reprise après erreur, sans effacer une
  réponse terminée. ASR et PCM contrôlés dans ces tests navigateur.
- `native-source.json` et `native-packaged.json` vérifient le vrai ASR local sur
  une fixture synthétique et la réception réelle de trames microphone.
- `live-model-tts.json` vérifie le vrai Qwen chargé et la vraie synthèse CPU hors
  ligne avec des comptes jetables : deux réponses, premier texte vers 2,9 s,
  premier fragment TTS 0,13–0,16 s après la demande de synthèse. Cette vérification
  appelle la synthèse après la réponse texte ; ces mesures séparées ne sont pas
  une mesure de conversation humaine complète.
- `artifact.json` contrôle les fichiers embarqués, le profil personnel de test
  en version 3.5.30 et le démarrage/arrêt du microphone dans le nouvel EXE.
- Les suites serveur/client/voix et les cinq suites d’interface commune sont
  recoupées dans les journaux et le bilan `validation.json`.

Une fenêtre « Version du profil incompatible avec le binaire » a été déclenchée
par le premier test de mise à jour : la source 3.5.30 utilisait encore le binaire
de distribution 3.5.29. Le test peut désormais recevoir `FRED_TEST_CLIENT_EXE`
pour utiliser le binaire de staging avant publication. Les dix tests de mise à
jour/authentification repassent avec le nouvel EXE. Aucun profil de production
n’a été modifié par cette erreur de test.

## Limites et utilisation

Zipformer conserve deux erreurs grammaticales sur la fixture synthétique de
10,05 s. La capture utilisateur montre aussi une transcription incorrecte ;
aucune qualité générale ni précision sur la voix de l’utilisateur n’est donc
revendiquée. La suppression acoustique de l’écho et le barge-in humain dans sa
pièce restent à évaluer. Les tests automatiques ne peuvent pas fournir cette
mesure distante. Le mode reste limité à un traitement de synthèse simultané,
des tours de trente secondes et des sessions de quinze minutes.

Sur le PC client : installer **3.5.30**, choisir **Qwen local**, ouvrir une
conversation courte et cliquer **Conversation**. Une sortie audio Windows
fonctionnelle et le microphone par défaut sont nécessaires. Le chat écrit,
les projets et la mémoire locale restent disponibles ; les outils Hermes et
la recherche web ne sont pas exécutés par les tours vocaux directs.

La livraison et les contrôles de conservation sont enregistrés séparément
dans `production-corrections.json`. Les deux P100 et l’encodeur visuel P2200
doivent rester chargés ; les comptes, clés et sauvegardes sont conservés.
