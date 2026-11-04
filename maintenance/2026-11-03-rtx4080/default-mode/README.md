# Profil RTX 4080 par défaut — 3 novembre 2026

Profil enregistré à la demande de l'utilisateur après les campagnes de mesure :
**RTX 4080 principale, deux P100 pour les experts distants, DFlash2 et cache
d'experts automatique.** Le résultat du test séparé avec une seule P100 est dans
`p100-comparison.json` ; il ne remplace pas le choix de fonctionnement par défaut.

## Réglages et fichiers

- Moteur officiel Strata 0.1.56 CUDA 12.9, copié et vérifié fichier par fichier
  dans `F:/Kiara/moteurs/strata-0.1.56-cuda12/`.
- DFlash2 Q4_0 / selector Q4_0, empreinte vérifiée, conservé dans
  `F:/Kiara/modeles/dflash2/qwen3.8-flash-next-dflash2.q4_0-selq4.pack`.
- RTX 4080 `GPU-7d35736d-3ef5-1304-0e9e-1d26021be1a0` comme CUDA0 ; les deux
  P100 `GPU-a39f1b57-5a26-b53d-e943-44ef8042a438` et
  `GPU-486d5352-582e-2880-78bf-3dec4688e142` comme caches d'experts distants.
- Cache principal et caches P100 en `auto`, sans layer split, experts distants
  activés, quinze workers CPU, aucun déplacement du calcul des experts RAM vers
  la RTX (`--pcie-frac 0`).
- DFlash2 : `--spec 6`, `--draft-conf 0.8`, `--draft-fallback none`, vocabulaire
  existant passé avec `--mtp-draft-vocab` ; aucune couche MTP chargée.
- Contexte maximal 262144, KV INT8, fenêtre résidente 20480, préfill 2048,
  réserve VRAM 1600 Mio. Poids et table PLE existants conservés.
- P2200 conservée pour la vision, exclue du calcul des experts texte.
- Huit sauvegardes de prompt et cache de conversations de 30720 Mio conservés.
  L'autochargement et la reprise automatique restent activés.

Les deux bases `strata-iq4-p100-hybride.json` et `lanceur/base-strata.json`,
les réglages courants et par défaut sont enregistrés. Les derniers réglages
valides sont promus après validation, puis régénérés par le superviseur.
`before/` sauvegarde les profils précédents et les options d'exploitation.
Les anciens moteurs et packs ne sont pas supprimés.

## Conservation de DFlash2 au relancement

Le constructeur de configuration du lanceur ramenait `--spec` à 1 lorsque la
couche MTP était désactivée. Il préserve désormais la fenêtre DFlash2 configurée.
Une sélection explicite de MTP retire les options DFlash2 afin de ne pas charger
deux drafters. Aucun écran ni texte visible de l'interface n'est modifié.

Dix tests du lanceur passent, dont le roundtrip DFlash2 sans MTP et le retour
au MTP. Les scripts de mesure acceptent désormais `--p100-count 1` pour exclure
la seconde P100 tout en gardant la RTX principale et son premier cache distant.
Ils ne passent pas à l'ancien partage des couches entre deux GPU.

## Validation

`validation/` utilise le profil avec vision et caches de production activés :
calculs, JSON, négation, image VISION 47/cercle rouge/carré bleu et restitution
des trois codes d'un document de **27702 tokens** passent. Des préfixes système
distincts empêchent la réutilisation des prompts ; tous les compteurs de cache
réutilisé sont à zéro.

Le contexte configuré de 262144 n'est pas une preuve de stress test à cette taille.
La validation de la vision et les réponses ciblées ne sont pas une évaluation
générale de qualité. La cohabitation avec un autre modèle utilisant la RTX ne fait
pas partie de cette activation ; les caches automatiques utilisent une grande
partie de sa VRAM.

La console doit être relue pour prendre les nouvelles bases en mémoire.
`status.json` donne l'état de cette activation : `active_verified` n'est enregistré
qu'après démarrage géré et contrôles calcul/image sur le service final.
`console-process.json`, `managed-start.json`, `managed-calculation.json` et
`managed-image.json` conservent ces preuves quand l'activation est terminée.

## Essai avec une seule P100

`two-p100/` et `one-p100/` utilisent les mêmes options de calcul et DFlash2,
mais désactivent les caches de prompt/conversation pour mesurer les débits.
Le premier voit trois GPU texte, le second uniquement la RTX 4080 et la première
P100. La seconde P100 est exclue ; les experts supplémentaires restent dans
le complément CPU en RAM verrouillée.

Le cache de la P100 conservée est recalculé suivant le classement automatique :
il ne conserve pas exactement le même sous-ensemble d'experts que lorsque les
rangs sont répartis entre deux P100. Cette comparaison mesure les deux
configurations utilisables, pas un retrait à placement des autres experts figé.
Trois générations de 256 tokens, deux préremplissages par longueur et un contrôle
de document long sont conservés dans chaque dossier.

| Mesure médiane | RTX 4080 + deux P100 | RTX 4080 + une P100 | Écart une/deux |
| --- | ---: | ---: | ---: |
| Génération | 61,5 tok/s | 55,4 tok/s | −9,9 % |
| Préfill de 1516 tokens | 558,05 tok/s | 583,95 tok/s | +4,6 % |
| Préfill de 5932 tokens | 728,85 tok/s | 745,45 tok/s | +2,3 % |

Le complément d'experts en RAM verrouillée passe d'environ 24,65 à 39,71 Gio.
La seconde P100 reste à 9 Mio de VRAM utilisée dans l'essai avec une seule P100.
Les deux passages réussissent les treize contrôles ciblés, y compris les trois
codes du document de 27683 tokens. Les caches restent désactivés et aucune
réutilisation de tokens n'est relevée. Les petites différences de préfill ne
démontrent pas un gain général ; le retrait de la seconde P100 coûte environ
10 % de génération sur cette demande d'explication en français.

Les deux bases et réglages par défaut restent sur **deux P100** pendant et après
la comparaison. Les empreintes surveillées ne changent pas durant les essais.
Les dix tests du lanceur et les contrôles de sources passent (515 Python,
94 JavaScript, 98 PowerShell dans chacun des deux interpréteurs).

## Revenir sur le changement

Arrêter le modèle depuis la console lorsqu'il est inactif. Restaurer les profils
et réglages depuis `before/`, puis recharger la console. Les profils sauvegardés
référencent l'ancienne RTX 3080 : pour les utiliser avec le matériel actuel,
remplacer cet UUID par celui de la 4080 avant un redémarrage. Ne pas restaurer
un ancien pointeur de session ou des PID.

`save_default.py`, `activate_default.py` et `compare_p100.py` dans le dossier parent
documentent l'enregistrement, l'activation et l'analyse. L'enregistrement refuse
d'écraser ce dossier de preuves ou une installation dont l'empreinte diffère.
