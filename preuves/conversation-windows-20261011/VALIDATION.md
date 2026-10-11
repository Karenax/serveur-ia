# Conversation Windows — livraison 3.5.21

Implantée et activée après la fin du chat Codex intégrant EG2/mémoire. Android demeure en 1.0.3/code 4 ; son APK est identique. Aucun changement des processus Qwen ni des GPU.

## Contrôles

| Contrôle | Résultat | Preuve |
| --- | --- | --- |
| Régression globale serveur | 276 tests réussis en 538.208 s | [Journal](regression.log) |
| Capture réelle et fermeture | Moteur Windows empaqueté, DSP AEC actif, aucun audio/transcrit microphone enregistré | [Mesures](native-capture.json) |
| ASR français, vraie inférence CPU | Texte provisoire à 0,8 s d’audio ; fixture 10,05 s calculée en 1,43 s ; deux tours détectés | [Moteur empaqueté](helper-real.log), [sources](asr-real.log) |
| Smart Turn, préparation des caractéristiques | Écart maximal 4,27 × 10⁻⁶ par rapport à l’extracteur officiel normalisé, tolérance 10⁻⁵ | [Comparaison](smart-turn-features.json) |
| Pocket TTS français, vraie inférence CPU | Estelle ; premier fragment 0,172 s, 3,92 s d’audio calculées en 1,39 s ; environ 859 Mio | [Mesures](tts-real.json), [voix synthétique](fred-francais.wav) |
| Annulation de synthèse avant démarrage | Requête annulée sans PCM ; requête suivante produit 30 fragments et termine ; arrêt propre hors ligne | [Contrôle](tts-cancel.json) |
| Interface client et console | Dix scénarios réussis, aucune exception JavaScript ; transport WireGuard et TTS CPU réels, ASR/LLM contrôlés | [Résultats](browser/conversation-ui.json), [journal](browser-tests.log) |
| Service local | Neuf tests réussis : modèles absents/corrompus, refus de capture, sessions, réparation, champs inconnus, annulation par propriétaire | [Journal](unit-tests.log), [tests](../../client-voice/test_conversation.py) |
| Passerelle voix | Six tests réussis : accès/session, service désactivé, limites, refus de fichiers/voix arbitraires, flux borné, révocation | [Journal](http-tests.log), [tests](../../lanceur/test_voice.py) |
| Restauration | Onze tests réussis, dont sauvegarde/restauration de `voix.json` avec moteur arrêté | [Journal](restoration-tests.log) |
| Dictée Small conservée | Huit tests service, trois HTTP et six scénarios navigateur réussis | [Service](small-service-tests.log), [HTTP](small-http-tests.log), [interface](small-browser-tests.log) |
| Livraison Windows | Fichiers embarqués comparés aux sources ; exécutable testé avec chargement des deux moteurs et fermeture du microphone | [Empreintes](windows-release.json), [autotest](windows-exe-self-test.txt), [compilation](windows-release-build.log) |
| HTTPS public | Les trois routes voix et `/v1/models` répondent 401 sans autorisation, avec l’agent HTTP du client ; flux HTTPS authentifié non mesuré ici | [Routes](https-routes.json) |
| Production | Voix prête ; EG2 prêt, 36 passages sans attente ; Qwen chargé et PID/créations conservés ; données/accès/réglages et programmation identiques | [Validation réelle](production-validation.json), [empreintes avant](before.json), [après](after.json) |
| Sauvegarde réelle | Nouvelle archive serveur chiffrée, catalogue vérifié ; aucun secret ou texte de conversation copié dans les preuves | [Métadonnées](production-validation.json) |
| Licences et versions | Modèles publics Apache-2.0/BSD-2-Clause/CC-BY-4.0 ; versions figées et notices embarquées | [Métadonnées épinglées](model-licenses.json), [client](client-environment.txt), [serveur](server-environment.txt) |

## Parcours testé

La suite complète termine avec **276 tests réussis en 538,208 s**. Le journal contient un `ResourceWarning` sur un socket déjà fermé, sans échec de test. [Synthèse de livraison et conservation](delivery-final.json), [empreintes des sources](source-manifest.json).

Le navigateur conserve un brouillon, conserve le projet sélectionné, bloque les changements pendant la capture, envoie une transcription finale une seule fois par le chat existant, commence la lecture avant la fin de la réponse, puis coupe audio et génération à un événement de reprise de parole. Le raccrochage et une erreur microphone rendent le clavier disponible. La console désactive et réactive le vrai moteur Pocket TTS. Captures : [écoute](browser/01-ecoute.png), [réponse parlée](browser/02-reponse-vocale.png), [interruption](browser/03-interruption.png), [console](browser/04-console-voix.png).

La capture réelle et l’ASR réel sont éprouvés séparément du parcours navigateur contrôlé. La fixture d’inférence est une voix synthétique française ; elle contient les erreurs « AJOUTENT » et « RÉSUMENT ». Aucune mesure de précision générale n’est revendiquée. La qualité acoustique de l’annulation d’écho et de l’interruption avec une personne parlant réellement dans la pièce reste à mesurer. Les temps excluent le chargement initial et la génération Qwen ; ils ne donnent pas le délai global de réponse. La mémoire client mesurée concerne le moteur, en plus de l’application.

Un traitement TTS simultané ; texte limité à 600 caractères par segment, files et trames bornées. Les interruptions gardent dans l’historique les segments entièrement lus, sans estimation au mot près. Les tours ASR sont bornés à trente secondes et la session à quinze minutes. [Guide utilisateur et maintenance](../../client-voice/CONVERSATION-WINDOWS.md).

Une restauration n’a pas été effectuée sur les données de production. Les restaurations sont testées sur des instances isolées. Aucun téléphone physique ni mode conversation Android n’est testé ou livré dans cette étape.
