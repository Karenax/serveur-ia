# Comparaison Flash-Next et Qwen 27B — 13 octobre 2026

Débits de génération mesurés par les moteurs, hors chargement et lecture du prompt. Ciel et code Fibonacci : médianes de trois requêtes après chauffe. Les préfixes distincts empêchent la reprise du prompt vivant ; les prompts restent comparables entre profils de cette campagne, mais diffèrent légèrement des essais du 3 octobre.

| Profil | Ciel tok/s | Code Fibonacci tok/s | Débit soutenu tok/s | Durée soutenue | Température max | Échantillons thermiques |
|---|---:|---:|---:|---:|---:|---:|
| flash-production | 29.00 | 33.70 | — | 0.00 s | 79.00 °C | 4 |

| Profil | Lecture ~1,5K | Lecture ~6K | Lecture ~23,6K | Vérifications exactes | JSON strict |
|---|---:|---:|---:|---:|---:|
| flash-production | 7.71 s | 17.93 s | 61.25 s | 8/8 | 8/8 |

Les durées du tableau documents sont celles de lecture du prompt remontées par le moteur, pas le délai client jusqu’au premier texte. Les comptes réels de tokens figurent dans chaque réponse ; ils peuvent différer entre tokenizers. Chaque dossier est mesuré deux fois.

Flash-Next : même IQ4_XS, deux P100 24/24, 15 workers CPU, prefill 2048, contexte 262144, KV FP16, MTP 3/0,5, PLE direct. Strata reference désactive explicitement le tail skip ; mtp-batch ajoute seulement le traitement groupé du brouillon sur la seconde carte.

27B : Huihui abliterated Q4_K_M, deux P100 en mode tensor, Café, MTP Q4_0 2 tokens lorsque indiqué. Le contexte 32768 permet les mêmes documents ; le contexte 4096 reprend les conditions de taille de contexte historiques. Comparer ces configurations séparément.

La charge soutenue enchaîne des réponses plafonnées à 512 tokens sans pauses de refroidissement, pendant au moins trois minutes si elle aboutit. Ce débit agrège les tokens et temps de génération de cette charge ; il dépend du texte. Il ne constitue pas un classement général de qualité des deux modèles. Les réponses explicatives et le code sont conservés pour inspection, mais leur présence seule ne valide pas leur qualité.

Température/fréquences/puissance/limitation thermique relevées toutes les deux secondes. Les échantillons du tableau couvrent uniquement les requêtes mesurées ; le journal complet inclut la chauffe et le chargement. Bits thermiques : masque 0x60. Une campagne est interrompue à 80 °C ; les résultats partiels restent visibles.

## Comparaison des versions Strata


## État et reprise

Phase : interrompu-thermique. Production restaurée et vérifiée par une réponse calculée : False. Aucun nouveau moteur déployé en production.
- Erreur de campagne : Limitation thermique observée à 79 C ; client de benchmark arrêté pendant la seconde lecture du grand dossier, production non arrêtée.

Les fichiers de production sont contrôlés par leurs empreintes. Les requêtes, réponses complètes, paramètres effectifs et journaux se trouvent dans ce dossier. Les profils non mesurés et les images/conversations concurrentes restent hors de cette campagne.
