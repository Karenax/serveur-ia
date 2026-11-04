# Qwen via Kiara dans Codex

Modèle public : **`fred-qwen`**. API client : **`https://ia.karenax.net/v1`**.
Utiliser la clé personnelle Kiara du destinataire, jamais une clé d'administration.

La passerelle expose l'API Responses native de Strata : texte, streaming,
réflexion, outils fonction et outils libres, espaces de noms, reprise des appels
d'outils et conversations dont Codex renvoie l'historique. Les outils du PC sont
exécutés par Codex sur le PC client. Cette route ne lance aucun outil Hermes ou
MCP sur le serveur Kiara et n'ajoute pas de documents privés aux requêtes.

## Ajouter Codex depuis Kiara

Mettre à jour Accès serveur Kiara vers **3.5.57** ou une version ultérieure.
Dans **Réglages → API locale → Intégrations**, sélectionner Qwen local puis cliquer
sur **Ajouter à Codex**. Codex doit déjà être installé sur le PC.

Kiara télécharge les ressources depuis le serveur, vérifie la signature avec la
clé publique de l’accès personnel, puis configure Codex. Aucun paquet séparé,
aucun script à lancer et aucune clé à recopier. Le guide court se trouve sous
le bouton, dans **Utiliser Qwen dans Codex**.

L’ajout enregistre uniquement le fournisseur optionnel Kiara et le profil `kiara`.
Le modèle, le fournisseur, le catalogue, les sous-agents et les autorisations
par défaut de la configuration principale sont conservés. La configuration est
sauvegardée avant l’ajout du fournisseur. Pour une session Qwen :
`codex --profile kiara`. Les modèles ChatGPT restent les modèles habituels.

La version Codex qualifiée ne propose pas de sélecteur commun à plusieurs
fournisseurs. Enregistrer Kiara ne rend pas Qwen sélectionnable dans le menu
ChatGPT d’une conversation liée à OpenAI. Le profil explicite choisit Qwen et
son catalogue pour la session ; les autres sessions gardent leur fournisseur.
En cas d’échec de l’installation, Kiara restaure les fichiers précédents.

La clé personnelle est chiffrée avec DPAPI pour le compte Windows courant, dans
`~/.codex/kiara-api-key.dpapi`. Elle n’apparaît ni dans le TOML, ni dans la ligne de
commande du programme d’installation, ni dans la requête du navigateur local.
Un helper d’authentification la fournit à Codex à la demande.

Codex utilise directement l’API HTTPS via Cloudflare, même si le client Kiara est
en WireGuard. Cette différence est indiquée dans le guide ; Cloudflare peut
techniquement lire les données en transit. Kiara peut être fermé après l’ajout.
L’installation automatique est disponible sous Windows. Le protocole Responses
reste utilisable sur les autres systèmes avec une configuration Codex adaptée.

Les fichiers sont servis sur `GET /v1/client/codex`, avec l’authentification Kiara
habituelle. Les deux filtres WireGuard autorisent cette route. La réponse contient
une archive limitée et son manifeste Ed25519 signé par la clé de publication
existante. Le client vérifie la signature épinglée, la taille, le SHA-256 et la
liste exacte des fichiers avant toute exécution. Les scripts et le catalogue
restent sur le serveur et ne sont pas embarqués dans l’EXE du client.

Le catalogue a été testé avec Codex **0.166.0-alpha.5.1**. Les configurations TOML
multilignes sont conservées lors du premier ajout. Un fournisseur `kiara` créé
par un autre outil nécessite une fusion manuelle ; ses réglages sont conservés
en cas de refus. Cette version n’effectue aucune restauration de configuration
ancienne, conformément à la demande de ne pas ajouter de réparation.

## Sous-agents et délégation depuis un autre fournisseur

Exemple dans une session Qwen : « Lance deux sous-agents sans historique hérité :
le premier examine les tests et le second examine la documentation. Attends leurs
résultats avant de répondre. » Les deux sous-agents partagent les autorisations
Codex de leur parent ; changer de modèle n'accorde pas d'accès supplémentaire.

La file accepte quatre demandes Responses par accès, parent compris, et conserve
une exécution FIFO sur le modèle local. Le chat Kiara garde son exclusion actuelle.
Un cinquième appel reçoit une erreur 429. Une déconnexion ou une révocation
interrompt la requête en cours et libère la file.

Un sous-agent natif hérite du fournisseur du parent. Une session OpenAI ne peut
donc pas sélectionner directement le fournisseur Kiara pour un seul sous-agent.
Elle peut déléguer explicitement une tâche à un processus Codex séparé :

```powershell
codex exec --profile kiara --cd "C:\mon-projet" "Examine les tests sans modifier de fichier et rapporte tes conclusions."
```

Cette commande est une session séparée ; elle suit les autorisations configurées
sur ce PC. Le profil n'élargit pas les permissions de fichiers ou d'exécution.

## Portée et limites vérifiées

- HTTP Responses stateless, `store: false` imposé par Kiara. Les historiques
  normaux restent gérés par Codex sur le PC client.
- Pas de `previous_response_id`, conversation stockée côté serveur, background,
  WebSocket ni compaction distante. Codex renvoie les éléments de conversation
  et utilise sa compaction locale. Ces fonctionnalités ne sont pas simulées.
- Pas d'outils hébergés OpenAI (recherche web, code interpreter, MCP distant).
  Les outils fonction/custom fournis et exécutés par le client sont admis.
- Images intégrées PNG/JPEG/WebP, 2 Mo par image ; aucun chemin ou URL à charger
  depuis le serveur. La vision réelle n'a pas été requalifiée pour cette livraison.
- Les autres modèles partagés Hermes gardent leur API Chat Completions. La nouvelle
  route Responses est réservée à Qwen local.
- Le contexte annoncé est celui du profil actuel, 262144 tokens. Adapter le
  catalogue si l'administrateur réduit cette capacité.
- Les transports source Windows/Linux et les deux filtres WireGuard autorisent
  `/v1/responses`. Un ancien EXE client conserve son filtre embarqué ; utiliser
  directement HTTPS avec le paquet Codex, ou reconstruire ce client pour passer
  par sa passerelle locale. Aucun remplacement des EXE personnels n'est nécessaire
  pour l'intégration Codex par HTTPS.
- Le protocole app-server a été testé avec deux tours et rappel du premier message.
  Aucune validation visuelle de l'application installée sur un PC client distant
  n'est revendiquée. La qualité des réponses dépend du modèle Qwen et de la tâche.

## Reconstruire et qualifier

```powershell
& '.\client-qwen\Build-WireGuard.ps1' -OutputBinary "$PWD\toolchain\releases-staging\codex-20261102\wireguard-bridge.exe"
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s lanceur -p test_gateway_responses.py -v
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s maintenance/codex -p test_setup.py -v
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/codex/validate_live.py --output toolchain/test-results/codex-20261102/live-client.json
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/codex/validate_live.py --agents --output toolchain/test-results/codex-20261102/live-subagents.json
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/codex/validate_live.py --edit --output toolchain/test-results/codex-20261102/live-edit.json
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/codex/validate_app_server.py --output toolchain/test-results/codex-20261102/app-server.json
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/codex/validate_app_server.py --credential-helper --output toolchain/test-results/codex-20261102/app-server-dpapi.json
```

Les qualifications emploient des accès temporaires isolés et des données fictives,
avec le modèle déjà chargé. Le test d'outils utilise les permissions du lanceur
de qualification pour lire son fichier temporaire ; cela ne change aucun réglage
de permission dans les profils livrés. Les rapports sont dans `toolchain/test-results`.

La mise en service suit `activate_gateway.py prepare`, puis `activate`, puis
`verify` : sauvegarde chiffrée vérifiée, contrôles d'inactivité, remplacement du
bridge et redémarrage de la console en préservant les processus Qwen. La vérification
contrôle HTTPS, le modèle public et les empreintes des données, réglages et clés.

Références officielles consultées le 2 novembre 2026 :
[passerelles Codex](https://learn.chatgpt.com/docs/enterprise/gateway-compatibility),
[connexion et authentification](https://learn.chatgpt.com/docs/enterprise/connect-to-a-gateway),
[profils](https://learn.chatgpt.com/docs/config-file/config-advanced),
[sous-agents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[app-server](https://learn.chatgpt.com/docs/app-server).
