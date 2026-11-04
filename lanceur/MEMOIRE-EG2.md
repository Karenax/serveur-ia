# Mémoire et connaissances — EmbeddingGemma 2

Intégration du 11 octobre 2026, actualisée le 4 novembre. Le backend Kiara pilote deux moteurs indépendants : Qwen via Strata pour les réponses, EmbeddingGemma 2 via Sentence Transformers/PyTorch pour retrouver les passages utiles. EG2 utilise désormais la **Quadro P2200**, en float32, avec attention SDPA et groupes de quatre textes. Le runtime CPU à deux threads reste disponible en secours. Son activation ou sa désactivation conserve Qwen chargé.

```mermaid
flowchart LR
    C[Clients Windows et Android] --> B[Backend Kiara]
    B --> E[EG2 · GPU P2200]
    E --> K[Index de connaissances]
    K --> B
    B --> Q[Qwen / Strata · GPU]
    Q --> C
```

## Espaces de connaissances

Chaque accès personnel conserve ses propres données. Une question dans un projet recherche uniquement ses documents, souvenirs et conversations. Une question hors projet recherche uniquement les conversations hors projet et les souvenirs personnels de cet accès. Les projets archivés et discussions archivées, supprimées ou déplacées ne sont pas rappelés dans leur ancien espace. Une conversation liée à un projet inexistant ne devient pas une conversation personnelle.

Les conversations déjà synchronisées sont indexées automatiquement. Les pièces
jointes binaires, réflexions internes et réponses interrompues sont exclues.
Une ancienne réponse de l’assistant reste un échange passé, sans devenir un
souvenir confirmé. Depuis serveur/Windows 3.5.52 et Android 1.0.23/code 24,
les souvenirs se gèrent explicitement en conversation écrite ou orale et dans
**Mémoire et rappels**, dans l’espace Personnel ou un projet. La console conserve
ses outils d’administration. Voir le [guide commun](../GUIDE-ASSISTANT-KIARA.md).

Une préférence personnelle explicitement choisie pour tous les projets peut
s’appliquer dans leurs réponses ; elle ne donne pas accès aux autres conversations
ou documents personnels. Après correction ou oubli, les anciens passages
correspondants sont filtrés dans le contexte et la recherche. Les discussions
sources et archives conservées ne sont pas supprimées et toute paraphrase n’est
pas nécessairement masquée. Kiara porte la mémoire de référence ; la mémoire
native Hermes automatique est désactivée.

La séparation suit l’identité d’accès actuelle de Kiara. Deux accès distincts, même sur des appareils appartenant à la même personne, ont deux espaces distincts. Une copie du même profil partage son identité et son espace.

## Utilisation

Ouvrir la [console Mémoire et connaissances](http://127.0.0.1:8765/#knowledge). Elle affiche le moteur, la progression et les limites d’indexation. **Activer EG2** et **Désactiver EG2** pilotent uniquement le moteur mémoire. **Reconstruire l’index** efface le cache et le recalcule depuis les données originales.

Choisir un accès pour ajouter, modifier ou supprimer un souvenir personnel. Le formulaire de recherche permet de comparer les passages retrouvés hors projet ou dans un projet sélectionné. Les autres clients conservent leur contrat de chat actuel : le serveur ajoute automatiquement les passages pertinents au contexte envoyé à Qwen et retourne les sources consultables.

La recherche combine mots-clés et proximité sémantique, avec filtrage par accès et projet avant le classement. Le serveur revérifie chaque passage dans les données originales avant de l’utiliser. Une source supprimée ou modifiée est donc refusée immédiatement, même avant la prochaine indexation. Si EG2 est arrêté, occupé ou indisponible, la recherche par mots-clés reste disponible et Qwen continue de répondre.

## Installation et exploitation

### API pour les applications clientes — 3.5.59

`POST /v1/embeddings` accepte **1 à 32 textes**, de **4 500 caractères maximum
chacun**, avec `model: "google/embeddinggemma-2"`. Les vecteurs ont 768 dimensions,
en float ou base64. Le corps JSON est limité à **2 Mio**. Les calculs restent sur
P2200, avec un seul calcul actif et des groupes de quatre textes. Le travail
CPU auxiliaire reste limité à deux threads.

La file commune aux clients accepte **16 demandes en attente**, en plus de la
demande active, dans leur ordre d’arrivée. Une file pleine ou une attente de
plus de 30 secondes renvoie **HTTP 429** : l’application doit réessayer avec un
délai progressif. L’accès personnel est revérifié après l’attente et après le
calcul. Le calcul attend au plus cinq secondes le moteur partagé avec la
recherche interne, puis dispose de 45 secondes pour répondre ; une
indisponibilité du moteur reste signalée par **HTTP 503**.

La limite de 32 textes ne garantit pas qu’un lot de 32 longs passages termine
en 45 secondes en mode CPU de secours. Avant la migration GPU, le test de
32 passages de 4 200 caractères avait renvoyé HTTP 503. Pour les longs documents,
réduire la taille des lots après un échec
plutôt que renvoyer continuellement le même gros lot. Les lots de textes courts
et les limites de transport sont vérifiés séparément.

Le client Windows **3.5.59** et son pont WireGuard relèvent aussi la taille
acceptée et attendent jusqu’à 90 secondes la réponse. Mettre l’EXE à jour pour
utiliser des lots qui dépassent l’ancienne limite de 64 Kio. Les anciens clients
conservent leur limite de transport même si le serveur accepte désormais 32 textes.

### Préparation et réparation

La configuration `eg2-runtime.json` épingle l’UUID de la P2200, le runtime CUDA,
un plafond d’allocateur de 2 200 Mio et une marge minimale de 1 024 Mio. Elle ne
sélectionne jamais automatiquement une P100 ou la RTX 4080. Le service utilise
le CPU si CUDA ne démarre pas, si la marge mémoire est insuffisante ou si le
calcul manque de mémoire GPU ; l’état réel et la raison du repli sont visibles
dans la console. Arrêter puis réactiver EG2 permet de retenter le GPU après un
repli. La vision partage la P2200 ; les entrées les plus lourdes restent à qualifier.

Après préparation du runtime CPU, préparer le runtime CUDA avec :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/prepare_eg2_gpu.py
```

Le chemin du runtime choisi est explicite dans `eg2-runtime.json`. Le dossier
initialement nommé `eg2-gpu-benchmark-python-20261104` a été promu comme runtime
CUDA validé et doit être conservé. Il utilise ses propres roues CUDA verrouillées
et les autres dépendances du runtime CPU, également verrouillées. Une reconstruction
autonome peut installer le verrou complet `eg2-gpu.requirements.txt`.
Cette migration est uniquement serveur : aucun nouvel EXE ni APK n’est nécessaire.
Voir la [mise en service et ses preuves](../maintenance/2026-11-04-eg2-p2200/README.md).

Sur cette installation, les poids sont déjà téléchargés et le moteur activé. Pour réinstaller les composants locaux :

```powershell
.\Install-EG2.ps1
```

Le runtime EG2 doit aussi contenir le paquet local `kiara-shared`, utilisé par
son serveur HTTP. `Install-EG2.ps1` l’installe après les dépendances publiques.
Pour réparer uniquement ce paquet sans retélécharger les poids :

```powershell
& '.\toolchain\eg2-python\Scripts\python.exe' -m pip install --no-index --no-deps --no-build-isolation -e shared
```

Puis cliquer **Activer EG2** dans la console, même si l’activation est déjà
cochée : cette action remet à zéro les tentatives de redémarrage après erreur.
Un état « erreur » avec un processus absent peut provoquer le HTTP 503 des
applications clientes alors que Qwen continue de répondre.

Le script crée `toolchain/eg2-python` sans modifier les dépendances Strata, puis télécharge `google/embeddinggemma-2`, révision `914f7f89142e33e77833254d9c9b90c3cef7303b`, dans `toolchain/eg2-model`. Le chargement et les calculs suivants sont hors ligne. Le service écoute seulement sur une adresse locale et exige un jeton interne éphémère ; les clients distants passent par les droits existants du backend.

Configuration : texte uniquement, float32, 768 dimensions normalisées, P2200 avec secours CPU, 2 048 jetons au plus par passage. Quatre passages sont indexés par lot ; les questions interactives ont priorité. Le processus s’arrête avec son parent et possède un garde-fou de RAM à 4 Gio. Un échec de lancement GPU déclenche le runtime CPU séparé ; après trois échecs de redémarrage du service, l’administrateur peut relancer depuis la console.

L’index est limité à 16 000 passages au total, 4 000 par accès et un budget logique de cache de 64 Mio. Le dépassement est affiché dans la console. L’indexation priorise les souvenirs, les documents actuels, puis les discussions. Les quotas de stockage des données originales restent applicables ; les souvenirs personnels sont limités à 50 par accès et 2 000 caractères chacun.

## Sauvegarde et mesures

La base originale `lanceur/espaces-prives/espaces.sqlite3` conserve les conversations, documents et souvenirs, y compris personnels, ainsi que le réglage d’activation EG2. Elle entre dans les sauvegardes chiffrées existantes. `connaissances-cache.sqlite3` est un cache privé reconstructible, exclu des archives ; il est vidé après restauration. Le moteur et ses poids se réinstallent séparément.

Sur les fixtures françaises : chargement d’environ 14 secondes, RAM du véritable processus autour de 1,63 Gio, huit courts passages indexés en 0,75 seconde. Les six questions reformulées retrouvent chacune la source attendue en premier. Les passages longs demandent davantage de temps ; ces mesures ne garantissent pas un débit sur tous les documents. L’impact pendant une génération Qwen simultanée n’a pas été mesuré.

Les preuves, contrôles d’isolation, parcours de console, sauvegardes avant/après et état réel du serveur sont dans [le rapport de validation](../preuves/eg2-20261011/VALIDATION.md).
