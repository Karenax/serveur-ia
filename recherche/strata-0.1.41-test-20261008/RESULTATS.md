# Essai Strata 0.1.41 sur les deux P100 — 8 octobre 2026

Décision : conserver notre moteur hybride 0.1.35. La 0.1.41 officielle et sa variante FP16 accélèrent la génération, mais régressent sur le document de 23 614 tokens. La reprise du moteur actuel est contrôlée séparément dans `validation/production-retablie.json`.

Même modèle IQ4_XS, deux P100 en partage 24/24, 15 workers CPU, prefill 2 048, experts CPU résidents, MTP 3 / 0,5, PLE direct sur SSD. Cache de prompt explicitement désactivé dans chaque requête et compteur de réutilisation vérifié à zéro. Le modèle natif reste sur D: (disque dur). Serveur Python et moteur officiel isolés sur 8081.

| Profil | Vérifications exactes | Réponses explicatives non vides | Gain médian de génération | Pire variation de lecture des documents |
|---|---:|---:|---:|---:|
| Actuel 0.1.35 | 7/7 | 2/2 | +0.0 % | +0.0 % |
| Officiel 0.1.41 | 7/7 | 2/2 | +14.0 % | -17.2 % |
| 0.1.41 avec FP16 | 7/7 | 2/2 | +14.9 % | -21.9 % |

Temps jusqu’au premier texte, mesurés côté client :

| Document | Actuel 0.1.35 | Officiel 0.1.41 | 0.1.41 FP16 |
|---|---:|---:|---:|
| 1,534 tokens | 7.63 s | 7.86 s | 7.87 s |
| 5,950 tokens | 17.86 s | 18.03 s | 17.93 s |
| 23,614 tokens | 69.54 s | 83.83 s | 88.94 s |

Adaptation testée : `STRATA_BF16_TC=2` force le chemin de conversion FP16 déjà présent dans le moteur officiel, et `STRATA_PREFILL_BF16X2=0` maintient le mode standard. Cette adaptation ne modifie pas les fichiers de production. Elle ne résout pas la régression du grand document.

Critère fixé pour retenir une variante : valeurs attendues correctes, débit médian de génération au moins égal à 97 % de la référence, et débit de lecture d’au moins 95 % de la référence pour **chacune** des trois tailles de document. Une médiane seule des documents masque la régression du plus grand.

Portée : neuf requêtes mesurées par profil, après une requête de chauffe. Calculs et Fibonacci répétés deux fois ; une extraction exacte par taille de document. Les deux réponses sur la couleur du ciel sont plafonnées à 192 tokens et servent à mesurer la génération : leur simple présence ne prouve pas la qualité générale. Les clôtures Markdown autour de JSON sont comptées séparément : les valeurs sont correctes, mais les consignes de JSON strict ne sont pas toujours respectées (voir `comparaison.json`). Aucun essai de contexte 262 144, d’image ou de conversations concurrentes.

Résidence : les métriques de la 0.1.41 indiquent zéro blob expert lu sur disque pendant les neuf requêtes. Son RSS après chargement est voisin de 53 Gio. Le mode officiel conserve le complément CPU en RAM, sans reprendre le verrouillage strict de notre patch. Le rechargement initial depuis D: peut prendre plusieurs minutes.

Les profils `trim` et `pipeline` sont préparés mais **n’ont pas été mesurés** dans cette campagne. Les mesures brutes, textes, requêtes, événements SSE et échantillons mémoire sont dans `mesures/production-complet`, `mesures/officiel-reference` et `mesures/officiel-fp16`. 51 tests Python du serveur ont également réussi (`validation/tests-serveur.txt`).

Un arrêt du serveur de test a rencontré une course : le parent Python était déjà sorti après l’arrêt de ses enfants. Le script gère désormais cet état comme un arrêt réussi. La reprise du moteur actuel a bien été déclenchée.
