# Test RTX 4080 — 3 novembre 2026

**Profil désormais enregistré par défaut :** [RTX 4080 + deux P100, DFlash2,
cache automatique et comparaison avec une seule P100](default-mode/README.md).

[Comparaison complète sans P100 / une P100 / deux P100](no-p100/README.md) :
47,2 / 55,4 / 61,5 tokens/s sur la même demande de génération.

Suite de la campagne : [moteur 0.1.56, cache agrandi, DFlash2 et tentative de
portage du nouveau partage multi-GPU sous Windows](ESSAIS-0156.md).

[Diagnostic CPU/PCIe et estimation de capacité d'une V100](diagnostic-cpu/README.md) :
cinq essais supplémentaires, profilage des attentes et simulation 16/32 Go.

Le benchmark texte termine sans erreur en 253,36 secondes, chargement compris.
Les treize contrôles ciblés passent, sans réutilisation de tokens de cache.
Les empreintes des sept fichiers de configuration/session surveillés sont
identiques avant et après. Les processus du benchmark sont arrêtés et la VRAM
des deux P100 est revenue à 9 Mio par carte.

## Résultats

Comparaison avec la référence historique du 31 octobre,
`../2026-10-30-rtx3080/rtx3080-ctx262144-opt3-int8-p2048-cache1/`.
Les empreintes du moteur sont identiques ; les options de calcul sont les mêmes,
indépendamment de leur ordre. La vision était activée dans la référence et
est désactivée pour cet essai texte.

| Mesure médiane | RTX 3080 | RTX 4080 | Écart |
| --- | ---: | ---: | ---: |
| Génération, trois réponses plafonnées à 256 tokens | 52,4 tok/s | 57,7 tok/s | +10,1 % |
| Préremplissage de 1 516 tokens, deux répétitions | 502,25 tok/s | 522,7 tok/s | +4,1 % |
| Préremplissage de 5 932 tokens, deux répétitions | 622,25 tok/s | 667,7 tok/s | +7,3 % |

Le document long comporte 27 683 tokens. Son préremplissage prend 41,473 s,
soit 667,5 tok/s ; la réponse complète arrive en 42,14 s. Les trois codes placés
au début, au milieu et à la fin sont correctement restitués en JSON. Ce test
dépasse la fenêtre KV résidente de 20 480 cellules ; il ne remplit pas le contexte
maximal de 262 144 tokens.

La RTX atteint au maximum échantillonné 50 °C, 8 405 Mio de VRAM utilisée
au total et 99 % d'utilisation. Aucun signal de bridage thermique n'est relevé
pendant les requêtes. La télémétrie espacée de deux secondes ne capture pas
nécessairement tous les pics instantanés.

## Configuration et limites

- RTX 4080 16 Go : `GPU-7d35736d-3ef5-1304-0e9e-1d26021be1a0`, calcul dense et MTP.
- Deux P100 de 16 Go : caches d'experts distants ; P2200 exclue du test texte.
- Pilote NVIDIA 581.80 ; Strata officiel 0.1.54 CUDA 12.9.
- Flash-Next IQ4_XS, contexte 262144, KV INT8, KV résident 20480,
  préfill 2048, réserve 1600 Mio, 15 workers, MTP 3/seuil 0,5.
- Cache primaire limité à une entrée, comme sur la 3080 ; caches P100 en auto.
  Cette campagne ne cherche pas à optimiser l'usage des 16 Go de la nouvelle carte.
- Experts CPU : 30,81 Gio verrouillés par VirtualLock après refus du verrouillage
  CUDA, comme dans le profil précédent ; aucune lecture de blobs depuis les fichiers
  n'est rapportée pendant les requêtes.
- Caches de prompt et de conversation désactivés pour la mesure.
- Les gains concernent cette petite campagne et une référence historique,
  sans comparaison simultanée ni démonstration statistique générale.
- Les contrôles calcul/JSON/négation/restitution ne constituent pas une évaluation
  générale de qualité. La vision n'est pas validée par cette campagne.

Les profils persistants gardent la référence matérielle de l'ancienne 3080.
Le nouvel UUID a été appliqué uniquement à la configuration isolée du benchmark.
L'adaptation du profil de service à la 4080 reste une opération distincte.

## Reproduire et examiner

Depuis la racine, sans moteur texte concurrent, avec suffisamment de RAM libre :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' -u maintenance/2026-10-30-rtx3080/benchmark.py rtx4080 --primary-gpu-uuid GPU-7d35736d-3ef5-1304-0e9e-1d26021be1a0 --context 262144 --quality-suite --long-prefill --output-dir maintenance/2026-11-03-rtx4080/int8-cache1
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/2026-11-03-rtx4080/analyze.py
```

Choisir un autre dossier de sortie pour un nouvel essai : le pilote refuse
d'écraser un dossier existant. Le port local de test est 18080.

`comparison.json` contient le calcul des écarts et les résumés des deux cartes.
`hardware.csv` consigne les GPU et le pilote. `int8-cache1/` conserve la
configuration, les requêtes, réponses, métriques, journaux, télémétrie et
empreintes avant/après.

Le pilote historique accepte désormais un UUID primaire explicite, le nom
`rtx4080` et un dossier de sortie externe. Les contrôles de sources du projet
passent : 506 Python, 94 JavaScript, 98 PowerShell dans chaque interpréteur.
Le script d'analyse ajouté ensuite passe aussi la vérification de syntaxe.
