# Flash-Next et Strata — comparaison du 16 octobre 2026

## Conclusion pour notre serveur

La recherche porte exclusivement sur les variantes de Flash-Next. **GSQ-RCO IQ3_S est le premier candidat à comparer pour le compromis qualité/mémoire ; Swift 1.5 IQ3_S l'est pour diminuer l'attente lorsque la réflexion est activée.** UD-Q4_K_XL intéresse surtout la fidélité des poids, avec un coût mémoire supérieur. Aucune mesure locale ne permet encore de déclarer l'une de ces versions meilleure que notre Uncensored IQ4_XS.

Pour le moteur, le premier essai reste **Strata officiel 0.1.44.1 CUDA 12 avec les poids actuels**. Il permettrait de mesurer le changement de moteur indépendamment du changement de modèle. Aucun téléchargement de poids, remplacement de moteur, redémarrage ou benchmark d'inférence n'a été effectué pendant cette recherche.

## Référence et sens des « versions »

Notre serveur dispose de 128 Gio de RAM, de deux P100 de 16 Gio pour le texte et d'une P2200 de 5 Gio pour les images. Il utilise Strata 0.1.43.1, Flash-Next Uncensored IQ4_XS, les experts résidents en RAM depuis D: et la table ngram sur le SSD C: en lecture directe. Le démarrage à froid peut produire un pic de mémoire pendant la copie des experts. [Instantané local](serveur-avant.json).

Une quantification change la représentation des poids ; Swift est un réentraînement complémentaire ; Uncensored modifie le comportement de refus ; Coder et REAP retirent des experts. Ces transformations ne sont pas interchangeables. Un fichier plus récent ou plus gros ne garantit ni de meilleures réponses, ni plus de vitesse.

La provenance exacte de notre fichier Uncensored n'a pas été établie par une correspondance cryptographique avec un dépôt public. Les chiffres Unsloth ci-dessous ne constituent donc pas une mesure directe de notre fichier, malgré le même suffixe IQ4_XS.

## Variantes à comparer

Les tailles sont des **Go décimaux de fichiers**, pas la RAM utilisée. Pour les packs GSQ-RCO, elles comprennent la table ngram de 28,8 Go ; le projecteur vision d'environ 0,91 Go s'ajoute. Les caches et le moteur s'ajoutent également.

| Variante Flash-Next | Taille indicative | Intérêt pour nous | Limite déterminante |
| --- | ---: | --- | --- |
| Uncensored IQ4_XS actuel | Référence locale | Vision et outils déjà vérifiés | Ne pas lui attribuer les scores d'un autre producteur |
| GSQ-RCO IQ3_S, modèle complet | 83,6 Go | Réduction des fichiers sans retirer d'experts ; candidat équilibré | Comparaison française, outils et vitesse P100 à faire |
| GSQ-RCO Q2_0, modèle complet | 66,4 Go | Priorité à l'empreinte et au débit potentiel | Quantification plus agressive ; gain P100 non mesuré |
| Swift 1.5 GSQ-RCO IQ3_S | 83,7 Go | Réflexion plus courte, attente potentiellement réduite | Gain dépendant des tâches et du mode réflexion |
| Unsloth UD-Q4_K_XL | 111,3 Go | Meilleure fidélité que son IQ4_XS de référence | Plus d'experts en RAM, démarrage et trafic plus coûteux |
| GSQ-RCO Coder | 58,4 Go | Version allégée spécialisée dans le code | Moitié des experts retirés ; pertes généralistes |
| NVIDIA FP4-Local | Environ 96 Gio | Quantification avec réentraînement dédié | Conversion et compatibilité P100 à établir |

### GSQ-RCO : compression sans retirer d'experts

Ces packs conservent les 512 experts par couche. Ils proposent Q2_0, IQ2_XS, IQ3_XXS et IQ3_S, respectivement 66,4, 68,0, 75,8 et 83,6 Go, table ngram comprise. La calibration répartit la précision entre couches. Le producteur présente IQ3_S comme le choix privilégiant la qualité ; ses résultats proches du BF16 ne prouvent pas une supériorité sur notre Uncensored. Les accélérations publiées pour Q2_0 ont été obtenues sur un autre matériel. [Fiche et évaluations ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF).

L'intérêt attendu sur notre serveur est une diminution du volume des experts et de leur trafic mémoire. Cela reste une hypothèse à mesurer avec Strata et nos deux P100 ; le nombre de bits seul ne prédit pas le débit.

### Swift 1.5 : surtout moins de réflexion

Le producteur rapporte une réduction médiane de 63,4 % des tokens de réflexion sur GPQA au niveau xhigh, avec des scores proches de la base. Les résultats varient : certaines évaluations baissent et TerminalBench ne réduit pas les tokens moyens. Swift ne signifie donc pas « génération toujours plus rapide ». Avec la réflexion déjà désactivée, notamment en vocal, ce bénéfice peut disparaître. [Fiche Swift et comparaisons détaillées](https://huggingface.co/ukisai/Swift1.5-Qwen3.8-Flash-Next), [pack GGUF GSQ-RCO](https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF).

### Quantifications Unsloth : fidélité contre mémoire

La documentation Strata rapporte, face à Q8_0, une concordance du token préféré de 93,09 % pour Q4_K_XL contre 88,91 % pour IQ4_XS. C'est une mesure de fidélité sur un corpus fixe, pas un score d'intelligence ou un test de notre Uncensored. Les experts routés passent d'environ 55,4 à 71,7 Gio entre ces deux packs.

Q5_K_XL, Q6_K_XL et Q8_0 augmentent encore fortement la mémoire ; leurs tables ngram sont également plus grandes. Avec nos autres services et les pics au chargement, ils ne sont pas prioritaires. Q4_K_XL constitue un essai de fidélité, pas une proposition d'accélération. [Tailles et protocole Strata](https://github.com/Niko1221/Strata/blob/v0.1.44.1/docs/QUANTS.md).

### Coder, REAP, Uncensored et déclinaisons matérielles

**Coder** conserve 256 experts sur 512. Son producteur annonce la conservation de 91,3 % du score SWE-bench Verified et 98,7 % de LiveCodeBench v6, mais reconnaît des pertes généralistes. Il convient mieux à un profil spécialisé qu'au remplacement général d'Hermes. [Fiche Coder](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF).

Les **REAP-288 et REAP-320** retirent aussi des experts. La première indique une vision non testée après élagage ; la seconde documente des pertes de connaissances et des hallucinations dans une petite sonde, insuffisante pour établir un taux global. Ces variantes ne sont pas mes premiers choix pour notre usage texte, outils et images. [REAP-288](https://huggingface.co/sh0wie/Qwen3.8-Flash-Next-REAP-288-GGUF), [REAP-320](https://huggingface.co/AnonimousA/Qwen3.8-Flash-Next-REAP-320-GGUF).

**Uncensored** correspond d'abord à un changement de comportement de refus, sans garantie de meilleure précision. Les packs **R9V** ciblent notamment RDNA4 ; **CED** est une approximation du préfill, distincte du projecteur de vision. Les résultats ROCm publiés ne démontrent pas un bénéfice sur nos P100. [R9V](https://huggingface.co/Dyluhn/Qwen3.8-Flash-Next-Uncensored-R9V-IQ4_XS), [CED](https://huggingface.co/Dyluhn/Qwen3.8-Flash-Next-Uncensored-CED-Projector).

### NVIDIA FP4-Local

FP4-Local ajoute un entraînement adapté à la quantification et utilise un stockage de facteurs d'échelle qui demande une prise en charge spécifique. Les P100 n'ont pas d'unités matérielles FP4 ; Strata possède néanmoins des chemins logiciels NVFP4. Il serait donc inexact de déclarer tout NVFP4 impossible sur Pascal, comme de supposer que le nouveau FP4-Local fonctionne directement.

Le réentraînement touche aussi les tables ngram : réutiliser automatiquement notre PLE actuel serait injustifié. La conversion des anciens packs NVIDIA documentée par Strata ne prouve pas la compatibilité de ce nouveau checkpoint. [Fiche NVIDIA](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-FP4-Local), [support NVFP4 Strata](https://github.com/Niko1221/Strata/blob/v0.1.44.1/docs/NVFP4.md).

## Strata et dérivés, pour Flash-Next uniquement

**Strata officiel 0.1.44.1**, publié le 14 octobre, apporte notamment des corrections de démarrage et de compilation CUDA, après les évolutions de quantification et de cache image de 0.1.44. Aucun résultat consulté ne mesure le gain sur notre configuration Windows/P100. Un essai doit conserver notre encodeur P2200 CUDA 12.4 fonctionnel et isoler les éventuels changements de réglages introduits par le nouveau setup. [0.1.44.1](https://github.com/Niko1221/Strata/releases/tag/v0.1.44.1), [0.1.44](https://github.com/Niko1221/Strata/releases/tag/v0.1.44).

**PXA 3.1** mérite une veille pour ses kernels Pascal/Volta et ses mesures Flash-Next sur P100. Toutefois, son environnement Linux, ses quantifications propres et ses résultats principalement sur une seule carte ne démontrent pas un gain applicable à notre déploiement Windows à deux P100. [Notes PXA 3.1](https://github.com/poisonxa16/pxa/blob/main/RELEASE-NOTES-v3.1.md).

Le fork strata-nvfp4 vise surtout des GPU RTX plus récents ; les branches V100, RDNA et Blackwell ne constituent pas des améliorations établies pour nos P100. Les éléments détaillés sur les moteurs restent dans [l'annexe de recherche](RAPPORT.md).

## Ordre des essais proposé

1. Mesurer Strata 0.1.44.1 avec notre Flash-Next actuel, à réglages comparables.
2. Comparer GSQ-RCO IQ3_S au même moteur : français, outils, code, images, grand contexte, mémoire au démarrage et latence.
3. Comparer Swift 1.5 IQ3_S lorsque la réflexion est activée, en mesurant aussi le nombre total de tokens et la qualité.
4. Réserver Q4_K_XL à la fidélité et Q2_0 à l'objectif mémoire/débit, selon les résultats précédents.

Chaque pack doit utiliser une configuration compatible avec ses poids, son MTP, sa table ngram et son projecteur. La présence de fichiers similaires ne suffit pas à justifier leur réutilisation. Cet ordre constitue une proposition d'évaluation, pas une bascule de production.
