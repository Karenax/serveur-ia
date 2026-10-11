# Correction de la conversation Windows — 11 octobre 2026

Windows **3.5.23** corrige l’arrêt de la lecture lors de la synchronisation automatique de l’historique après une réponse. Le modèle et les outils Hermes terminaient le calcul, puis le client affichait « Réponse interrompue avant la fin de sa première phrase » et raccrochait avant que la première phrase soit entièrement lue.

## Cause et changement

`chat.html` termine le tour avec `conversationOnReplyEnd`, puis synchronise l’historique. `conversation.js` assimilait `historySyncPending` à une rupture nécessitant l’arrêt de la conversation. Un poll pendant cette synchronisation appelait `stop`, annulait l’audio et remplaçait la réponse par le marqueur d’interruption lorsque `heard` était encore vide. La [reproduction sur la version précédente](reproduction.json) produit ce résultat sans nouvel événement de parole.

La synchronisation normale garde désormais le microphone et la lecture actifs. Les nouveaux tours attendent la fin de la synchronisation, des enregistrements et d’une récupération d’agent, puis sont soumis une seule fois. Les vraies interruptions par la voix, les erreurs de connexion/historique et le raccrochage conservent leur traitement.

## Vérifications

- Le nouveau test navigateur `client-qwen/test_conversation_ui.cjs` échoue avec `conversation.js` du commit `0354e91` et passe avec le correctif : sept scénarios, quatre tours et quatre accusés de réception uniques. Une synchronisation de 1,2 seconde ne coupe ni la session ni les trois fragments PCM programmés ; le texte complet est conservé. Le tour suivant reste en attente, puis part dans la même conversation avec un autre identifiant. Reprise de parole pendant le calcul, interruption de l’audio et raccrochage restent fonctionnels. ASR et chronologie PCM sont simulés, sans microphone physique ni modèle serveur. [Résultats](delayed-sync-validation.json).
- Les dix scénarios existants passent avec **WireGuard et Pocket TTS CPU réels**, ASR/LLM simulés : projet conservé, envoi automatique, lecture, interruption, raccrochage, erreur microphone et arrêt/redémarrage de la voix serveur. Le harness attend maintenant que le bouton soit prêt avant un redémarrage. [Résultats](legacy-validation.json).
- Les neuf tests Python de conversation et les sept tests d’historique/distribution Windows passent.

## Livraison

Le [contrôle de compilation](client-build-validation.json) vérifie la signature Ed25519 habituelle, la compatibilité avec l’ancien updater, la version PE, l’autotest et les assets embarqués. Le [contrôle de livraison](delivery-validation.json) contient l’empreinte de l’EXE signé, sa version publiée, la préparation du paquet personnel, l’état agent/voix et la préservation de Qwen, des accès, réglages et de l’APK Android. Les données réelles ne reçoivent aucun message synthétique. Les captures et journaux détaillés restent dans `toolchain/releases-staging/conversation-fix-20261011/`.

Mettre à jour depuis **Mises à jour → Vérifier les mises à jour → Mettre à jour le client**. L’accès, les modèles vocaux et l’historique sont conservés. L’installation sur le poste utilisateur reste à effectuer par ce parcours ; les essais ne constituent pas une mesure acoustique avec sa voix ou son matériel.
