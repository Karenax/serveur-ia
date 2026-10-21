# Comparaison réelle Strata 0.1.43.1 / paquet moteur 0.1.45.3

Essais du 19 octobre 2026 sur Flash-Next Uncensored IQ4_XS, deux P100 16 Gio, split 24, préfill 2048, 15 workers, MTP 3 / seuil 0,5, contexte configuré 262144. Le serveur Python corrigé et la vision P2200 sont conservés. Le nouveau moteur utilise les DLL CUDA de son paquet officiel ; ses sept réglages P100 sont confirmés actifs dans le journal.

## Génération : comparaison finale commune

Chaque moteur a été chargé, a lu un document de 23,6K tokens puis a enchaîné les mêmes six requêtes texte/code (trois paires), sans pause de refroidissement. Le seuil artificiel de 80 °C a été supprimé à la demande explicite de l’utilisateur. Les fréquences et le bridage matériel restent relevés. Les médianes portent sur trois requêtes par cas, dans un processus par moteur ; ce sont des séries courtes, pas une validation de débit continu sur plusieurs heures.

| Cas | 0.1.43.1 | 0.1.45.3 | Débit |
|---|---:|---:|---:|
| ciel | 34.10 tok/s | 35.10 tok/s | +2.9% |
| fibonacci-code | 39.00 tok/s | 39.70 tok/s | +1.8% |

Les premières mesures de génération, dont la chauffe différait, restent archivées mais ne servent pas à ce tableau.

## Lecture des documents

Médianes de deux requêtes identiques par moteur, sans réutilisation du prompt. Ces mesures ont été effectuées dans la phase initiale avec départ à 55 °C ou moins. La seconde lecture longue du nouveau moteur a atteint 80 °C sans bridage thermique déclaré : elle est conservée selon la consigne ultérieure de l’utilisateur, sans modifier les fichiers bruts où l’ancien critère avait marqué thermally_valid=false.

| Taille moteur | 0.1.43.1 | 0.1.45.3 | Débit de lecture |
|---|---:|---:|---:|
| 1545 tokens | 7.88 s | 7.67 s | +2.7% |
| 5962 tokens | 17.88 s | 16.79 s | +6.5% |
| 23627 tokens | 58.20 s | 54.29 s | +7.2% |

## Vérifications réelles

- Appel d’outil : booléen false et chaîne "True" conservés avec leur type attendu. Aucune fonction hôte exécutée.
- Image synthétique : texte VISION 47, cercle rouge et carré bleu reconnus dans le JSON demandé, via la P2200.
- Cache : trois conversations textuelles alternées ; retour à A en 1.08 s, réponse identique à la référence, 99.67% du prompt réutilisé (2134/2141 tokens).
- Cache configuré à 20 emplacements / 30720 Mio et réserve RAM 6144 Mio. L’essai porte sur environ 2,1K tokens par conversation ; ni les retours à 32K tokens, ni le remplissage complet du cache, ni les 262K tokens de contexte ne sont testés.
- Génération : 1/6 réponses finales identiques entre moteurs. Les réponses et le code sont conservés ; leur présence ne démontre pas une qualité générale équivalente. Les calculs et codes cachés des documents ont des contrôles de valeur exacts.
- reference-sans-seuil : maximum échantillonné 73 °C, 0 échantillon(s) de bridage thermique matériel. Aucun arrêt manuel à 80 °C dans la série finale.
- nouveau-sans-seuil : maximum échantillonné 77 °C, 0 échantillon(s) de bridage thermique matériel. Aucun arrêt manuel à 80 °C dans la série finale.

## État final et portée

Production remise sur 0.1.43.1, modèle chargé, calcul réel 43 × 7 = 301 vérifié, console conservée, port de test fermé. Empreintes des réglages persistants et configurations d’accès identiques. Le paquet nouveau reste isolé dans ce dossier ; aucun pilote ni poids de modèle n’a été remplacé.

Le paquet officiel annonce 0.1.45.3 / CUDA 12.9, build f6d65cb584c0 ; son --version affiche 0.1.45. SHA-256 de l’archive et des sept fichiers, plus signature Ed25519, vérifiés. Le manifeste annonce un pilote minimal 576.02 alors que le poste utilise 528.89 : les réussites observées ici ne changent pas cette exigence déclarée et ne valident pas tous les chemins CUDA.

Les tests concernent le moteur derrière notre serveur Python 0.1.43.1 corrigé, pas la nouvelle application ni son serveur non corrigé. Les chargements ont bénéficié de prélectures séquentielles et de la réduction ponctuelle des pages par le superviseur : aucun temps de démarrage froid comparable n’est revendiqué. La protection RAM reste active.

Les premières tentatives, l’erreur initiale du pilote d’attente et le premier arrêt à 80 °C sont conservés dans les journaux. La série finale commune a été rejouée après suppression du seuil. Requêtes, réponses, configurations, empreintes et télémétrie toutes les deux secondes : mesures/essai-01/.
