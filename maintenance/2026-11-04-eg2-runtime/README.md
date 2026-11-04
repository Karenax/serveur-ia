# EG2 disponible dans Kiara — 4 novembre 2026

Le moteur était activé mais arrêté après ses tentatives de redémarrage : son
environnement isolé ne contenait pas `kiara-shared`. L’import de
`embedding_worker.py` échouait via `http_boundary.py` avec
`ModuleNotFoundError: No module named 'kiara_shared'`. L’API renvoyait alors
HTTP 503, indépendamment de la disponibilité du LLM Qwen.

Le paquet local a été installé dans `toolchain/eg2-python`, ainsi que sa
dépendance `cryptography==50.0.2`, avec les empreintes déjà vérifiées dans le
verrou Strata. Le verrou EG2 et son manifeste ont été complétés ; les autres
runtimes restent identiques. `Install-EG2.ps1` installe désormais le verrou,
le paquet local partagé, puis contrôle les dépendances et l’import du worker.
Les guides de reconstruction et d’exploitation EG2 décrivent la réparation.

EG2 a été réactivé par la console, sans redémarrer celle-ci ni Qwen, et sans
retélécharger les poids. Les requêtes synthétiques suivantes ont réussi :

- Passerelle authentifiée locale : lot de deux textes, HTTP 200.
- HTTPS public avec les en-têtes du client Kiara : requête de recherche et
  encodage base64, HTTP 200.
- API locale du client Windows, avec le vrai transport HTTPS et le vrai moteur :
  HTTP 200. Le test utilise le code client livré en 3.5.58, un port et des réglages
  temporaires, sans ouvrir une fenêtre ni modifier les réglages du destinataire.
- Dans chaque cas : 768 dimensions, valeurs finies, vecteurs normalisés et
  consommation de jetons renseignée.
- Sept tests API existants réussis, notamment le proxy Windows/WireGuard,
  les autorisations, la révocation, les limites et la libération du verrou.
- `pip check` EG2 et contrôle des six verrous de runtimes réussis.

`production.json` contient les résultats réels sans clés ni contenu utilisateur ;
les processus Qwen sont identiques à ceux de `before.json`. `runtime-locks.json`
et `tests-api.log` conservent les autres validations. `verify.py` permet de
rejouer les requêtes synthétiques. Le premier essai HTTPS avec l’agent HTTP
générique de Python a été refusé par Cloudflare (1010) ; les essais avec les
en-têtes du client Kiara passent, sans modification des règles Cloudflare.

Aucune nouvelle compilation de l’EXE n’est nécessaire : la correction concerne
l’environnement du moteur sur le serveur. L’application cliente peut réessayer
`POST /v1/embeddings` avec le modèle `google/embeddinggemma-2` et 768 dimensions.
