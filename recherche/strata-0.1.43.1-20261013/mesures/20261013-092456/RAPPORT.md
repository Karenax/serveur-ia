# Comparaison Flash-Next et Qwen 27B — 13 octobre 2026

Cette campagne refroidit les P100 sous 55 °C entre les requêtes ordinaires. Les débits ordinaires ne sont donc pas des débits garantis en continu. Les seules séries soutenues sont explicitement séparées ci-dessous.

Débits de génération mesurés par les moteurs, hors chargement et lecture du prompt. Ciel et code Fibonacci : médianes de trois requêtes après chauffe. Les préfixes distincts empêchent la reprise du prompt vivant ; les prompts restent comparables entre profils de cette campagne, mais diffèrent légèrement des essais du 3 octobre.

| Profil | Ciel tok/s | Code Fibonacci tok/s | Série sans pauses tok/s | Durée de la série | Température max | Échantillons thermiques |
|---|---:|---:|---:|---:|---:|---:|
| Flash-Next / Strata 0.1.35 actuel | 30.10 | 33.70 | — | — | 79.00 °C | 1 |
| Flash-Next / Strata 0.1.43.1, MTP groupé demandé | 35.20 | 38.90 | — | — | 78.00 °C | 0 |
| 27B / Café MTP 2, contexte 4K | 30.76 | 35.79 | 27.73 | 77.27 s | 79.00 °C | 5 |
| 27B / Café sans MTP, contexte 4K | 18.54 | 18.54 | — | — | 64.00 °C | 0 |
| 27B / Café MTP 2, contexte 32K | 30.64 | 35.66 | — | — | 80.00 °C | 27 |

| Profil | Lecture ~1,5K | Lecture ~6K | Lecture ~23,6K | Vérifications exactes | JSON strict |
|---|---:|---:|---:|---:|---:|
| Flash-Next / Strata 0.1.35 actuel | 7.70 s | 17.95 s | 58.53 s | 9/9 | 9/9 |
| Flash-Next / Strata 0.1.43.1, MTP groupé demandé | 7.84 s | 17.80 s | 56.80 s | 9/9 | 9/9 |
| 27B / Café MTP 2, contexte 4K | — s | — s | — s | 3/3 | 3/3 |
| 27B / Café sans MTP, contexte 4K | — s | — s | — s | 3/3 | 3/3 |
| 27B / Café MTP 2, contexte 32K | 6.44 s | 24.89 s | 115.04 s | 8/8 | 8/8 |

Les durées du tableau documents sont celles de lecture du prompt remontées par le moteur, pas le délai client jusqu’au premier texte. Les comptes réels de tokens figurent dans chaque réponse ; ils peuvent différer entre tokenizers. Chaque dossier est mesuré deux fois.

Flash-Next : même IQ4_XS, deux P100 24/24, 15 workers CPU, prefill 2048, contexte 262144, KV FP16, MTP 3/0,5, PLE direct. Strata reference désactive explicitement le tail skip ; mtp-batch ajoute seulement le traitement groupé du brouillon sur la seconde carte.

27B : Huihui abliterated Q4_K_M, deux P100 en mode tensor, Café, MTP Q4_0 2 tokens lorsque indiqué. Le contexte 32768 permet les mêmes documents ; le contexte 4096 reprend les conditions de taille de contexte historiques. Comparer ces configurations séparément.

La charge soutenue enchaîne des réponses plafonnées à 512 tokens sans pauses de refroidissement, pendant au moins trois minutes si elle aboutit. Ce débit agrège les tokens et temps de génération de cette charge ; il dépend du texte. Il ne constitue pas un classement général de qualité des deux modèles. Les réponses explicatives et le code sont conservés pour inspection, mais leur présence seule ne valide pas leur qualité.

Température/fréquences/puissance/limitation thermique relevées toutes les deux secondes. Les échantillons du tableau couvrent uniquement les requêtes mesurées ; le journal complet inclut la chauffe et le chargement. Bits thermiques : masque 0x60. Une campagne est interrompue à 80 °C ; les résultats partiels restent visibles.

## Comparaison des versions Strata

- strata-mtp-batch : génération médiane +15.4%, pire rapport de lecture des dossiers 0.97. Seuils de vitesse et vérifications exactes atteints : True. Validation globale avec référence sans limitation thermique : False.
  La référence a un échantillon de limitation thermique sur le grand document ; cela empêche de présenter la comparaison thermique globale comme validée, même si les seuils de vitesse et les valeurs exactes sont bons.

## État et reprise

Phase : production-retablie. Production restaurée et vérifiée par une réponse calculée : True. Aucun nouveau moteur déployé en production.

Console reconnectée : True. Moteur conservé pendant cette reconnexion : PID 11084. Réglages conservés : chargement automatique True, relance automatique True.

La série MTP 4K sans pauses comprend 4 réponses, 77.3 secondes et 27.73 tokens/s agrégés. Débits individuels : 28.11 / 28.66 / 28.07 / 26.00. La série s’arrête sur une limitation thermique ; elle n’a pas atteint les trois minutes visées.

Complément MTP 4K : D:\Serveur IA\recherche\strata-0.1.43.1-20261013\mesures\20261013-110242, phase production-retablie. L'attente maximale de refroidissement passe de cinq à dix minutes, avec le même seuil de départ de 55 °C. Les données de la première tentative restent conservées séparément.
- Profil flash-production : Limitation thermique ou 80 C observés ; profil interrompu.
- Profil strata-reference : Le serveur de test a quitté pendant le chargement.
- Profil 27b-mtp2-32768 : Limitation thermique ou 80 C observés ; profil interrompu.
- Profil 27b-mtp2-4096 : Refroidissement sous 55 C non atteint en 5 minutes.
- Complément 27b-mtp2-4096 : Limitation thermique ou 80 C observés ; profil interrompu.

Le premier démarrage officiel a dépassé le délai interne de 900 secondes du serveur pendant la copie des experts, avant toute inférence. Une prélecture séquentielle de 60,94 Gio d’experts a été effectuée ; le pilote des mesures a attendu sa fin. Le démarrage suivant bénéficie du cache de fichiers chaud. Cette campagne ne mesure donc pas un temps de chargement froid comparable entre versions. Le lanceur de test a ensuite été préparé avec STRATA_ENGINE_READY_S=1800 pour les futurs démarrages froids ; ce réglage ne constitue pas une réparation du binaire.

Le moteur a annoncé un refus du MTP groupé sur la première requête courte : moins de 64 lignes disponibles pour un batch. Le diagnostic n’est écrit qu’une fois par processus, alors que le choix est refait pour chaque bloc. Il ne prouve donc pas que tous les documents ont suivi le repli. Faute de mesure complète du même binaire avec cette option désactivée, les gains observés ne peuvent pas être attribués isolément au MTP groupé.

Les fichiers de production sont contrôlés par leurs empreintes. Les requêtes, réponses complètes, paramètres effectifs et journaux se trouvent dans ce dossier. Les profils non mesurés et les images/conversations concurrentes restent hors de cette campagne.
