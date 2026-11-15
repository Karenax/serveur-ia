# Analyse IA et structuration

## Amélioration manuelle structurée et panne réseau — 15 octobre 2026

Une connexion TCP réussie ne garantit pas le succès de la requête suivante.
Le chemin `chat_text(response_format=...)` rejoint maintenant le transport
commun `_post_llm` utilisé par les CR JSON : sur panne de transport, le secours
local explicitement configuré peut reprendre une demande manuelle avant
réception d'un résultat. Il conserve le schéma strict et le contexte ; le
modèle est remplacé et la clé réseau est retirée de la requête locale.

Les refus de schéma ou d'authentification (400/401/404/422) ne déclenchent pas
ce changement de moteur. Aucun second résultat n'est appliqué. Les suggestions
automatiques gardent fallback_enabled/fallback_autostart à false ; une panne
invalide néanmoins une ancienne décision de déchargement. Les réglages de
secours désactivé restent respectés. La règle de déchargement LM Studio au
retour du principal reste en place et ses tests de concurrence passent.

Les trois cas connexion refusée/délai/503 reproduisent le défaut avant le
correctif, puis passent dans la sélection de 146 tests en 74,82 s. Ces tests
ne lancent aucun vrai modèle. Le backend supervisé 8001 est redémarré après
une nouvelle sauvegarde Brain/ERP/EG2 et restauration privée vérifiée ; le
correctif est actif. La grande suite Python historique n'a pas été relancée.
L'intermittence du serveur réseau lui-même reste un fait observé, pas un
défaut que ce correctif prétend résoudre.

[Audit et limites](../logs/foresight-runtime/GPU-product-and-fallback-delivery-ROOT-e0176bcfd58e41e7b6c9d02eb527f9b3.json).

## État actuel — 11 octobre 2026

Tous les chemins IA CDC lisent les réglages Brain. `reasoning_effort=none` et `enable_thinking=false` sont conservés ; Ollama reçoit `think=false` et le budget/options/schema. Les suggestions CDC suivent leur parcours de revue. Les informations de connaissance admissibles peuvent être retenues par défaut avec un mode de validation explicite, distinct d'une confirmation humaine.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Étapes
1. segmenter la source ;
2. identifier locuteurs/auteurs ;
3. extraire des candidats ;
4. normaliser unités/dates/noms ;
5. classifier ;
6. relier à la mémoire existante ;
7. détecter nouveauté, confirmation, modification ou contradiction ;
8. générer propositions ;
9. produire explications et provenance.

## Sortie structurée
Le modèle ne retourne pas seulement un résumé. Il doit produire un JSON validé par schéma.

Exemple :
```json
{
  "project_id":"P26-0148",
  "items":[
    {
      "kind":"milestone",
      "operation":"propose_update",
      "subject":"FAT",
      "value":"2026-12-18",
      "confidence":0.96,
      "source_locator":{"start_sec":421.2,"end_sec":435.8},
      "reason":"Le client demande explicitement le report."
    }
  ]
}
```

## Comparaison
Pour chaque candidat :
- `new`
- `confirms`
- `supersedes`
- `contradicts`
- `duplicates`
- `unclear`

## Validation et décision métier
Les informations extraites d'une source résolue du même projet peuvent être retenues automatiquement, avec provenance, `validated_by=auto-default` et décision auditée. Les rattachements projet incertains, refus et reports conservent leur parcours spécifique. Une contradiction ne remplace jamais silencieusement une confirmation humaine ; déclassement et restauration restent possibles.

Une information retenue automatiquement ne vaut pas autorisation d'une action engageante. La gouvernance métier doit prévoir une confirmation autorisée pour :
- engagement contractuel ;
- prix/budget ;
- planning de référence ;
- exigence ;
- décision qualité ;
- action externe engageante.

## Résumés
Les résumés sont des vues calculées et peuvent être régénérés. Ils ne remplacent pas les KnowledgeItems.

## Indexation et réponse avec EG2
La mémoire des preuves utilise uniquement EG2 : découpage du texte canonique, calcul distant des vecteurs de 768 dimensions et persistance des passages dans SQLite. Elle ne produit ni nouvelles connaissances ni décisions de validation.

Pour répondre, l'assistant combine les connaissances actives SQL et les passages recherchés par EG2, avec portée projet, provenance et références numérotées. Le LLM déjà configuré rédige ensuite la réponse et doit qualifier les informations retenues par défaut, les confirmations humaines et les preuves. Les textes sélectionnés et citations n'ont plus de troncature arbitraire en caractères ; les limites de contexte du modèle restent applicables.

Les métriques d'indexation, de rappel et de génération doivent rester séparées. Un test de connexion EG2 ou un rappel pertinent ne prouve pas à lui seul la qualité d'une réponse métier. Voir [20_EG2_ENGINE.md](20_EG2_ENGINE.md) et [36_EMBEDDING_CHANNEL.md](36_EMBEDDING_CHANNEL.md).
