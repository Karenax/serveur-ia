# EG2 sur Quadro P2200 — mise en service du 4 novembre 2026

**EG2 fonctionne sur la P2200 en production**, en float32, attention SDPA et
groupes de quatre textes. L’UUID de cette carte est épinglé dans
`lanceur/eg2-runtime.json` ; la RTX 4080 et les P100 ne sont pas des solutions
de remplacement automatiques. Qwen reste chargé avec ses processus existants.

**Aucune mise à jour des clients n’est nécessaire.** Les EXE personnels 3.5.60,
leur signature et leurs empreintes restent identiques. Modèle
`google/embeddinggemma-2`, route `/v1/embeddings`, 768 dimensions, float/base64,
lots de 32 et file de seize demandes conservent leurs contrats. Les index de
connaissances existants sont conservés ; la proximité numérique CPU/GPU a été
vérifiée pendant les [essais préalables](../2026-11-04-eg2-gpu/README.md).

## Runtime et repli

Le runtime CUDA validé pendant les essais a été promu comme runtime applicatif
et conserve le chemin `toolchain/eg2-gpu-benchmark-python-20261104`. Ce dossier
doit désormais être conservé. Son Python charge PyTorch 2.14.1+cu126 et
torchvision 0.29.1+cu126 ; les autres dépendances sont celles du runtime CPU
verrouillé, avec une référence explicite au paquet local `shared`.
`maintenance/prepare_eg2_gpu.py` prépare ou vérifie cet environnement. Les sept
profils de `maintenance/verrous_runtime.py check` passent, y compris le nouveau
verrou GPU et le profil CPU préservé.

Le budget de l’allocateur est de 2 200 Mio. Une marge minimale de 1 024 Mio est
contrôlée avec `nvidia-smi` ; le démarrage exige en outre la place du budget
complet. Une insuffisance initiale ou détectée avant une requête fait exécuter
le modèle sur CPU. Une saturation mémoire GPU pendant le calcul entraîne une
reprise de la même demande sur CPU. Un runtime GPU absent, arrêté ou trop long
à démarrer provoque le lancement du runtime CPU séparé. Les raisons sont
visibles dans l’état administratif ; le modèle ne change pas silencieusement.
Arrêter puis réactiver EG2 permet de retenter le GPU après un repli.

Le CPU peut encore dépasser le délai de 45 secondes sur les très gros lots :
l’Agent doit alors réduire leur taille. La vision partage la P2200 ; la marge
est surveillée, mais une qualification de toutes les tailles d’images et de
la charge simultanée reste distincte de cette mise en service.

## Vérifications

- Worker GPU réel avant activation : 32 textes longs, 768 dimensions,
  normalisation vérifiée, environ **5,5 secondes**.
- Worker réel avec marge mémoire volontairement impossible : repli CPU visible
  et calcul réussi, sans modifier la production.
- **19 tests** : politique GPU, UUID/périmètre du runtime, mémoire insuffisante,
  CUDA indisponible, reprise après saturation, autorisations et révocation,
  file FIFO, limites des lots et transport Windows/WireGuard.
- Console sur données fictives : affichage « GPU · Quadro P2200 », affichage du
  repli « CPU · 2 threads », recherche et isolation, arrêt et retour lexical.
  Les captures et résultats de ce test sont isolés dans `ui/`.
- Contrôle des sources et contrôle UX ; les cinq avertissements de textes longs
  préexistants de la console restent examinés et conservés.
- Sauvegarde chiffrée préalable vérifiée avec seconde copie NAS. Processus Qwen,
  données utilisateur, clés, accès, réglages et programmation des sauvegardes
  identiques avant/après. Aucun reconditionnement des EXE ou nouvel APK.
- Vérification du code embarqué dans l’EXE 3.5.60 à travers son API locale,
  avec le vrai EG2 : HTTPS et tunnel WireGuard local isolé, float/base64,
  lots de 1, 2 et 32 textes, dont les lots de 32 passages longs.

`production.json` atteste la carte réellement utilisée et la préservation de
l’état ; `eg2-client-verification.json` contient les résultats des requêtes du
client. `worker-validation.json`, `tests-final.log`, `tests-ui-isolated.log`,
`runtime-locks.json`, `check-sources.log`, `ux-check.log`, les empreintes sources
et la sauvegarde préalable conservent les autres preuves.

Une copie indépendante du runtime CUDA a d’abord été essayée sous
`toolchain/eg2-cuda-python`, mais son chargement natif n’a pas été validé. Elle
n’est pas utilisée par le service. Le runtime CUDA déjà validé a été conservé
et ses paquets sont verrouillés pour éviter de promouvoir cette copie non qualifiée.

Le premier lancement d’un ancien test UI utilisait son dossier de preuves
historique ; sa capture suivie par Git a été restaurée à l’identique et le test
a été relancé avec le dossier isolé `ui/`. Les fixtures API placées sur le disque
de données ont subi des délais d’écriture pendant la préparation du runtime ;
le runner final utilise un dossier temporaire séparé et réussit les 19 tests.

`activate.py` a déjà effectué la sauvegarde et l’activation : ne pas le rejouer
sans examiner les preuves existantes. Le retour CPU se règle en conservant le
fichier de configuration et en passant `device` à `cpu`, puis en redémarrant
la console par la procédure qui préserve Qwen. Aucun EXE client n’est concerné.
