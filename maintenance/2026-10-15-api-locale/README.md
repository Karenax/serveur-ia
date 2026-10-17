# API locale Hermes et OpenCode 2 — 15 octobre 2026

Correctif **serveur uniquement**, en service avec les clients Windows existants.
L’API locale démarre déjà automatiquement avec Fred sur `127.0.0.1:17841`
(ou le prochain port libre jusqu’à 17850). Elle reste disponible tant que le
client Fred reste ouvert. Aucun bouton d’activation supplémentaire n’est requis.

## Défauts reproduits et correction

Le catalogue de la passerelle de production répondait HTTP 200, puis une requête
OpenAI standard recevait HTTP 409 `client_update_required` : depuis l’intégration
Hermes, le serveur exigeait systématiquement un `conversation_id` propre au chat
Fred. Hermes et OpenCode n’en transmettent pas. OpenCode **2.0.29** envoie aussi
`store: false`, qui était rejeté HTTP 400 comme paramètre inconnu.

Les requêtes standard sans identité de conversation Fred utilisent maintenant
une route de complétion simple. Le client tiers conserve sa conversation et ses
outils ; Fred ne lance aucun outil hôte pour ces requêtes et n’ajoute pas son
contexte documentaire. Le choix et l’autorisation du modèle restent contrôlés
par le serveur. Qwen passe par la file d’inférence locale ; les fournisseurs
partagés utilisent les adaptateurs du runtime Hermes installé, dans un processus
isolé, sans exposer leurs identifiants aux clients. Les budgets de sortie des
applications tierces sont conservés. Le champ booléen `store` est accepté puis
retiré. Le chat Fred avec `conversation_id` garde sa route agent existante.

Le flux Qwen reste progressif. Pour les fournisseurs partagés, le résultat d’un
appel est assemblé avant son émission au format SSE ; des commentaires de
maintien de connexion sont émis pendant l’attente. Les appels et résultats
d’outils restent au format OpenAI. Il n’y a pas de repli sur un autre fournisseur.

## Vérifications

- Erreur 409 reproduite sur l’ancienne passerelle, moteur Qwen direct répondant OK.
- Sept tests de régression : API locale réelle avec outils et résultats, isolation
  de la route agent, fournisseur sélectionné, sérialisation SSE des outils,
  révocation et arrêt du processus de complétion lors d’une annulation.
- Suites comptes/API, modèles partagés et réflexion : 46 tests réussis lors de la
  correction ; suites intégration, vocal et réflexion : 30 tests réussis.
  Les sept régressions ont été repassées après l’ajout de `store`.
- [Requêtes réelles](live-local-api.json) par le client Fred et la passerelle de
  production : Qwen avec/sans flux en HTTPS et WireGuard ; GPT-6 Luna avec/sans
  flux en HTTPS ; appel `fred_probe(value=7)` puis message de résultat d’outil
  Qwen réussi, sans exécuter d’outil hôte.
- [Applications réelles](opencode-live.json) : CLI Hermes du runtime installé et
  OpenCode 2.0.29 donnent les réponses attendues en utilisant l’API locale Fred
  puis GPT-6 Luna via HTTPS. Configurations et données temporaires ; aucun
  changement dans les configurations personnelles des deux applications.
- [Mise en service](production-corrections.json) : sauvegarde chiffrée vérifiée,
  mêmes processus Qwen et encodeur visuel, mêmes clés, données et programmation
  des sauvegardes. Aucun nouveau binaire client nécessaire pour cette correction.

Les essais des deux applications et des transports ont été faits sur le serveur,
pas sur le poste distant de l’utilisateur. Les autres modèles partagés annoncés
n’ont pas chacun fait l’objet d’une génération réelle pendant cette intervention.

Sur le poste client : garder **Accès serveur Fred** ouvert, puis rouvrir une
discussion dans Hermes ou OpenCode avec le modèle ajouté sous **Serveur Fred**.
Si l’adresse locale a changé après plusieurs lancements simultanés, refaire
**Ajouter à Hermes** ou **Ajouter à OpenCode 2** depuis le client Fred actif.
