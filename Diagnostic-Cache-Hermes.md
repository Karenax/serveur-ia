# Diagnostic du cache Hermes — 5 octobre 2026

Les mesures ont été relevées sur le serveur qui reçoit les requêtes du client distant. La nouvelle conversation a produit onze appels successifs : chacun a réutilisé le préfixe en cache. Hermes peut retransmettre l'historique complet à l'API sans que le moteur recalcule les tokens déjà présents.

| Appel | Tokens du contexte | Tokens réutilisés | Tokens relus | Lecture du contexte |
| --- | ---: | ---: | ---: | ---: |
| 1 | 23 362 | 23 283 | 79 | 2,39 s |
| 2 | 23 858 | 23 357 | 501 | 5,39 s |
| 3 | 24 065 | 23 853 | 212 | 3,47 s |
| 4 | 24 290 | 24 060 | 230 | 3,57 s |
| 5 | 24 639 | 24 285 | 354 | 4,31 s |
| 6 | 25 024 | 24 634 | 390 | 4,40 s |
| 7 | 25 232 | 25 019 | 213 | 3,49 s |
| 8 | 25 521 | 25 227 | 294 | 3,99 s |
| 9 | 26 319 | 25 516 | 803 | 10,56 s |
| 10 | 26 928 | 26 314 | 614 | 6,38 s |
| 11 | 27 410 | 26 923 | 487 | 5,74 s |

Les réponses sont générées à environ 30 tokens/s. La durée totale d'un appel comprend la lecture des nouveaux tokens et la génération de la réponse ; elle ne mesure pas seulement l'attente avant son premier token.

Les appels précédents montrent un autre scénario : un contexte de 81 100 tokens est suivi d'une requête différente de 59 tokens, puis d'un contexte de 81 685 tokens dont aucun token n'est réutilisé. La lecture de ce dernier prend 380,56 secondes. L'appel suivant réutilise ensuite 81 680 tokens. Cela correspond à un remplacement du contexte actif par une requête intermédiaire. La fonction de cette petite requête n'est pas identifiée.

Les métriques brutes, sans contenu des messages, sont conservées dans `analyses/cache-hermes-20261005/mesures.json`.

## Correctif préparé, sans remplacement du moteur actif

Le moteur actuel garde le contexte actif et ses points de reprise, mais son cache de conversations distinctes est désactivé (`conversation_cache_mib=0`). Le code initial refuse l'association du cache de conversations et de la répartition des couches sur plusieurs GPU.

L'extension locale sauvegarde et restaure les K/V, l'état récurrent, l'historique PLE et les données de l'indexeur de chaque GPU, ainsi que le cache du modèle de brouillon sur le dernier GPU. Les captures sont effectuées au changement de conversation, pas à chaque message. Une capture incompatible est rejetée avant toute restauration. Le budget RAM et la réserve minimale de mémoire restent contrôlés. Cette extension couvre les requêtes textuelles.

La compilation isolée s'effectue avec `Build-Strata-Cache.cmd`, en réutilisant les bibliothèques CUDA du build P100. Les exécutables sont écrits dans `strata-cache-build-bin`, sans écraser ceux de `strata-build-p100`.

Validation effectuée : 972 contrôles de validation sans GPU, 4 175 contrôles de gestion du cache et 1 957 contrôles de sauvegarde/restauration sur les P100. Ces derniers exercent explicitement A/B/A sur deux GPU dans quatre formats K/V et vérifient les états récurrents, PLE et indexeur, les K/V et le brouillon, ainsi que le refus d'une capture invalide avant écriture. La compilation du moteur et `git diff --check` passent.

Pour une validation complète, il reste à lancer le nouveau moteur avec un budget explicite, par exemple `--conversation-cache-mib 8192 --conversation-cache-slots 4`, puis à tester une conversation A, une requête B différente et un retour à A. Cette vérification nécessite de libérer les P100 actuellement utilisées par le moteur de production. Les tests sur les petites allocations GPU ne remplacent pas ce test avec le vrai modèle.

## Compression native dans Hermes, sur le PC client Fred

La version de Hermes inspectée possède déjà une compression automatique : elle remplace l'ancien historique par un résumé et conserve les messages récents. Pour la configurer sur le PC où tourne la conversation, exécuter dans son terminal :

```powershell
hermes config set model.context_length 262144
hermes config set compression.enabled true
hermes config set compression.threshold 0.80
hermes config set compression.micro_compact false
```

Relancer Hermes pour charger les réglages. Le seuil de 80 % vise environ 209 715 tokens sur la fenêtre de 262 144 tokens annoncée par ce serveur. Un éventuel `compression.threshold_tokens` déjà configuré peut déclencher une compression plus tôt. Vérifier la version et les réglages de Hermes sur Fred : ce PC distant n'a pas été modifié depuis le serveur.

La commande `/compress` dans une conversation permet également de demander une compression manuelle. Lors d'une compression, le préfixe envoyé au modèle change et doit être recalculé ; une telle opération doit rester occasionnelle pour conserver le bénéfice du cache entre les messages.

La durée maximale des requêtes de résumé peut devoir être augmentée pour ce modèle local : les lectures intégrales observées dépassent déjà plusieurs minutes. La compression réduit la taille de l'historique mais ne corrige pas, à elle seule, le remplacement du contexte actif par une autre requête.
