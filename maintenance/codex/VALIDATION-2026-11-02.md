# Livraison Codex / Qwen — 2 novembre 2026

L'intégration est en service sur `https://ia.karenax.net/v1`, modèle `fred-qwen`.
La console Kiara et son bridge WireGuard ont été rechargés ; les processus Qwen,
les clés, les réglages et les contenus des utilisateurs ont été conservés. Une
sauvegarde chiffrée a été créée et vérifiée avant la mise en service.

## Vérifications réalisées

| Vérification | Résultat |
| --- | --- |
| Transport Responses et proxy client | 13 tests réussis, dont flux progressif, outil et résultat repris, arrêt après révocation, erreurs, accès refusés et véritable tunnel WireGuard |
| API externe existante | 7 tests réussis |
| API distante et clients existants | 20 tests réussis, dont tunnels, révocation, profils et clés préservés |
| File et exploitation existantes | 7 tests réussis |
| Installation Windows et stockage DPAPI | 3 tests réussis : fusion répétable, réglages préservés, aucune clé en clair dans les fichiers |
| Tests Go du bridge | Réussis |
| Contrôle des sources | Réussi : Python, JavaScript et les deux interpréteurs PowerShell |
| UX du dépôt | Contrôle réussi avec trois avertissements de texte long préexistants dans la console ; aucun contenu supprimé |

Les 50 tests Python ci-dessus sont proportionnés aux composants modifiés. Il ne
s'agit pas d'une exécution de toutes les suites Android, voix ou interface du dépôt.

## Qualifications avec le véritable Qwen chargé

Codex **0.166.0-alpha.5.1**, sans appel à un modèle OpenAI pour ces scénarios :

- Lecture d'un fichier temporaire dont le contenu aléatoire n'est pas donné dans
  le prompt : outil exécuté par Codex, résultat renvoyé à Qwen, réponse correcte.
- Création d'un fichier temporaire avec l'outil libre `apply_patch` : contenu
  conforme au fichier source lu par Codex.
- Deux sous-agents Qwen indépendants : lecture du fichier fictif et calcul de
  `17 × 19`, attente des deux résultats et réponse finale correcte. Neuf requêtes
  Responses réussies, toutes routées vers `fred-qwen`.
- App-server : deux tours, rappel du code fictif, compaction locale, puis rappel
  correct après compaction.
- Même scénario app-server avec helper PowerShell lisant une clé DPAPI temporaire,
  sans variable `KIARA_API_KEY` dans le processus Codex.
- Profil installé : véritable session Codex via l'adresse HTTPS publique, outil
  de lecture exécuté sur le PC et réponse finale exacte.
- Production : SSE terminé normalement via loopback et HTTPS ; le modèle exposé
  reste `fred-qwen`. Empreintes des données, clés et réglages conservées.

Les scénarios isolés créent leurs propres accès temporaires et utilisent des
données fictives. La vérification HTTPS lit un accès personnel existant en mémoire,
sans enregistrer sa clé, et ne stocke pas de conversation sur Kiara.

## Limites

La validation couvre les transports et le protocole app-server, pas l'affichage
de l'application d'un PC client distant. Elle ne garantit pas la qualité de Qwen
sur toutes les tâches. Les WebSockets, les outils hébergés OpenAI, l'historique
stocké côté API et la compaction distante ne sont pas exposés. La vision n'a pas
été requalifiée dans cette livraison.

Les sous-agents natifs héritent du fournisseur du parent. Pour déléguer à Qwen
depuis une session OpenAI, employer une session Codex séparée avec le profil Kiara.

Les rapports détaillés, les empreintes avant/après et la preuve de sauvegarde
sont dans `toolchain/test-results/codex-20261102/`. Le paquet client est créé par
`maintenance/codex/package_client.py`, avec un manifeste d'empreintes et sans clé.
