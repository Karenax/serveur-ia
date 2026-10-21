# Diagnostic des modèles partagés dans Hermes

Le 21 octobre 2026, l’utilisateur signalait que seul Qwen fonctionnait dans Hermes sur le PC client. Après diagnostic, il a confirmé que le problème venait du niveau de réflexion choisi et que les modèles fonctionnent avec un niveau compatible. Aucun nouveau correctif ni changement de niveau imposé n’a été publié pour ce diagnostic ; la livraison reste Windows/serveur 3.5.34.

`sondage-avant.txt` vérifie les quatre modèles distants avec des requêtes simples. `capturer.py` relève les requêtes d’un agent Hermes dans un profil temporaire et sur une API synthétique. `rejeu-avant.txt` reproduit le rejet de Low sur Nemotron, dont le catalogue annonce none, medium et high ; les trois GPT répondent avec low.

`natif-reel.json` et `verifier_natif_reel.py` vérifient des tours réels avec l’agent Hermes installé, un client Fred local temporaire, son API dédiée `/hermes/v1` et la connexion HTTPS authentifiée vers les fournisseurs partagés : Nemotron en medium, GPT-6.1 Sol, GPT-6 Astra et GPT-6 Luna en low. Les quatre tours se terminent avec la réponse synthétique OK. Aucun outil client n’est autorisé pendant ces essais. Les clés sont résolues à l’exécution depuis le profil existant et ne sont pas enregistrées dans les preuves.

Le poste client distant n’a pas été piloté. Sa résolution est confirmée par l’utilisateur.
