# EmbeddingGemma 2 dans l’API distante de Fred

Livraison : serveur/Windows **3.5.32**, Android **1.0.13, code 14**.

Dans le client Windows ou Android, ouvrir **Réglages → API locale**. Copier l’adresse de base et la clé affichées dans l’application utilisatrice. Garder Fred ouvert : il transmet les requêtes au serveur par la connexion HTTPS ou WireGuard choisie. Le modèle d’embeddings utilise le CPU du serveur ; aucun modèle supplémentaire n’est installé sur le client distant.

| Réglage dans l’application utilisatrice | Valeur |
| --- | --- |
| API | Compatible OpenAI |
| Adresse de base | Adresse affichée dans Fred, suffixée par `/v1` |
| Clé | Clé API **locale** affichée dans ce même client |
| Modèle embeddings | `google/embeddinggemma-2` |
| Dimensions | 768 |
| Requête | `POST /v1/embeddings` |

Exemple de corps JSON, à envoyer à l’adresse de base suivie de `/embeddings`, avec `Authorization: Bearer <clé locale>` et `Content-Type: application/json` :

```json
{"model":"google/embeddinggemma-2","input":["Premier document","Deuxième document"],"encoding_format":"float"}
```

La réponse contient une liste `data` avec `index` et `embedding`, le modèle et l’utilisation en tokens. `encoding_format` accepte `float` (défaut) ou `base64` (valeurs float32 little endian). Le paramètre facultatif `dimensions` doit valoir 768. Les tableaux d’identifiants de tokens ne sont pas acceptés.

L’extension facultative `input_type` accepte `document` (défaut, pour indexer les textes) et `query` (préfixe de recherche du modèle, pour une question). Les documents et les requêtes conservent les mêmes vecteurs normalisés de 768 dimensions. Les limites sont huit textes par requête, 4500 caractères par texte et 64 Kio pour le JSON. Le moteur tronque les entrées à sa limite existante de 2048 tokens ; l’utilisation rapporte les tokens effectivement tokenisés après préfixe et troncature, y compris les tokens spéciaux.

Le modèle apparaît dans `GET /v1/models` avec `capabilities.embedding=true`. Les sélecteurs de conversation Windows et Android le filtrent : il est destiné aux fonctions d’embeddings des autres applications. Une API d’embeddings reste utilisable même si aucun modèle de conversation n’est disponible, dès lors que le catalogue peut être obtenu et qu’EG2 est prêt.

## Accès et disponibilité

La passerelle applique l’authentification personnelle existante, la suspension, l’expiration, la maintenance et la révocation. L’identité est revérifiée après le calcul, avant de renvoyer les vecteurs. La clé privée du worker EG2 reste sur le serveur. Les routes d’administration du worker ne sont pas exposées.

Une seule requête d’embeddings externe est admise à la fois ; les requêtes concurrentes reçoivent 429. Le calcul partage le moteur existant avec la recherche documentaire. Un moteur arrêté ou occupé répond 503, une requête invalide 400, et un accès refusé 401/403. Les erreurs du moteur sont remplacées par un message public sans détails privés.

Sur Android, le nouveau panneau permet de copier l’adresse et la clé locales. Elles changent quand le service local redémarre ; recopier les deux si nécessaire. Il faut une application qui accepte une adresse HTTP locale et une clé personnalisée. Le service reste lié au cycle de vie de Fred : Android peut l’arrêter en arrière-plan. Le port est lié à `127.0.0.1` et n’est pas exposé au réseau Wi-Fi. Aucun service Android permanent n’est ajouté.

## Preuves

Validation finale : **47 cas Python ciblés réussis** (45 dans la suite de régression, puis deux cas supplémentaires de découverte sans modèle de chat), **cinq suites d’interface réussies**, syntaxe Python/JavaScript/PowerShell valide et aucune erreur Ruff de classe F dans les fichiers concernés. Android lint : zéro erreur et cinq avertissements préexistants. Les premiers journaux `tests-api.txt` conservent les échecs détectés avant reconstruction du bridge et publication du manifeste ; ils sont résolus par les contrôles finaux cités ci-dessous.

- `tests-eg2-final.txt` : tests de validation, formats float/base64, usage, authentification, saturation, révocation pendant calcul et trajet réel API Windows → WireGuard → passerelle.
- `tests-regressions.txt` : recherche documentaire, frontières HTTP, accès distants et catalogue Windows ; tests exécutés après publication du binaire et du manifeste correspondants.
- `tests-embedding-seul.txt` : disponibilité sans modèle de chat et découverte avec le catalogue Hermes.
- `tests-ui.txt` : cinq suites web, dont le filtre des modèles embeddings et les contrôles du panneau API sur Windows/Android (affichage et copie de la clé Android).
- `build-wireguard.txt`, `build-windows.txt`, `build-android.txt` : reconstruction des deux paquets avec le bridge WireGuard autorisant précisément la nouvelle route. `lint-android.txt` : contrôle Android.
- `artefacts.json`, `publication.json` : comparaison des ressources et du bridge embarqués, test de démarrage Windows, vérification de l’APK et conservation du certificat Android.
- `production-apres.json`, `inference-distante.json` : services prêts, données/clés/paramètres préservés, Qwen conservé et vraie inférence EG2 à travers les deux transports et l’API locale Windows.
- `android-api-package.json` : panneau API présent dans l’APK publié et comparaison des deux bridges Android embarqués aux binaires reconstruits.

Aucun appareil Android ni émulateur n’était connecté pendant cette intervention. La compilation et les tests web Android sont effectués ; aucun essai natif sur téléphone physique n’est revendiqué. Les versions antérieures des paquets sont conservées pour retour arrière sous `toolchain/releases-staging/eg2-20261021/previous`.
