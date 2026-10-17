# Préfill excessif avec OpenCode — 16 octobre 2026

L'analyse établit un conflit entre l'alternance des agents OpenCode et la configuration du cache Strata. Elle ne montre pas une incompatibilité générale de l'API. La phase de diagnostic ci-dessous a été réalisée sans modifier les processus ou réglages actifs ni envoyer de génération de test. Après autorisation de l'utilisateur, le cache a ensuite été [activé avec un plafond de 30 Gio et mesuré](activation/README.md).

## Constats directs

- OpenCode utilise le fournisseur `qwen-local` à `http://127.0.0.1:8080/v1`. Cette analyse contourne donc Fred et Hermes : leur passerelle ne peut pas être responsable des transformations de cette requête.
- La base SQLite OpenCode contient un agent principal (« Analyse et améliorations projet »), un sous-agent frontend et un sous-agent backend, avec le même modèle local. Leurs appels s'entrelacent. La chronologie et les compteurs, sans contenu des messages, sont dans `preuves.json`.
- `/metrics` confirme Strata 0.1.43.1 et `conversation_cache.enabled=false`, budget 0 Mio, zéro sauvegarde et zéro restauration de conversation.
- Le cache de préfixe reste actif : plusieurs appels des sous-agents réutilisent exactement 2 639 tokens. Il ne faut pas confondre ce cache avec le cache des conversations complètes.
- Le réglage persistant `history_every=160000` correspond à `--prompt-cache-every 160000`. Les appels observés de 30–47 k tokens restent sous cet intervalle ; les lignes moteur annoncent généralement deux points de reprise.
- Sur les vingt appels mesurés lors du premier diagnostic : 757 400 tokens relus, 21 112 réutilisés, 3 499 487 ms de préfill contre 326 672 ms de génération. Soit 91,5 % du temps moteur en préfill et 2,7 % des tokens d'entrée réutilisés.
- Ces appels annoncent zéro lecture de blobs experts depuis le fichier. La relecture des experts sur HDD n'explique pas cette séquence.

## Mécanisme vérifié dans les sources installées

`dependances/strata-0.1.43.1/source/src/program/generate.cpp` :

- vers 7785 : les checkpoints forment une chaîne de préfixes de la session active, pas un arbre indépendant de toutes les conversations ;
- vers 7883 : `park_current_body` ne sauvegarde rien lorsque le cache des conversations est désactivé ;
- vers 10557 : avant de lire le nouvel appel, les checkpoints dépassant le point de reprise ou incompatibles avec son préfixe sont supprimés ;
- vers 10629 : le prochain checkpoint périodique est placé à `resume + prompt_cache_every`.

Donc A → B → A supprime les états propres à A lorsque B réécrit les K/V, sans sauvegarde permettant de les restaurer au retour. Le préfixe système commun peut survivre (les 2 639 tokens observés), mais le reste doit être recalculé. Un agent principal utilisant un autre préfixe peut repartir de zéro. L'intervalle à 160 k prive aussi les branches plus courtes de points de reprise intermédiaires.

La documentation installée `docs/DETAILS.md` (section « Multiple conversations ») décrit précisément la conservation des historiques contrôleur/travailleurs avec `--conversation-cache-mib` et `--conversation-cache-slots`, y compris avec `--layer-split`. Le problème est aussi documenté en amont : https://github.com/Niko1221/Strata/issues/1920 et https://github.com/Niko1221/Strata/issues/2099 . Les mesures d'autres machines ne constituent pas une prédiction de gain sur ce serveur.

## Correction à valider

La priorité est un essai A/B/A avec le cache de conversations activé, par exemple un plafond initial de 8 192 Mio / 4 conversations, après vérification de la RAM disponible. Il faut mesurer les sauvegardes/restaurations, la réutilisation, le temps total et la mémoire. Le budget est un plafond, pas une réservation ni une garantie qu'il suffira aux contextes futurs.

Un intervalle périodique plus court (8 192 ou 16 384) peut aider les branches qui divergent dans une même histoire, mais ne remplace pas la sauvegarde des conversations lors de leur alternance. Plus de checkpoints consomment aussi des ressources : le choix doit être mesuré.

Les options `--prompt-cache-tail` et `STRATA_CACHE_MESSAGE_BOUNDARY` ne sont pas une recette directement applicable ici : dans cette version installée, leur chemin documenté ou leur condition de code exclut le multi-GPU.

Changer ces options implique de relancer le moteur. Cette investigation n'a pas interrompu l'analyse ni rechargé le modèle. Le gain réel et l'absence d'autres invalidations de préfixe restent à vérifier par l'essai contrôlé ; la comparaison avec DeepSeek ne garantit pas des parcours d'outils identiques.
