# EG2 : lots de 32 textes et file de 16 demandes — Windows 3.5.59

La livraison serveur/Windows **3.5.59** relève les limites EG2 jusque dans le
client EXE et ses deux ponts WireGuard. Le moteur reste sur CPU, avec deux
threads, un calcul actif et des groupes de quatre textes pour le calcul.

## Contrat de l’API

- `POST /v1/embeddings`, modèle `google/embeddinggemma-2` : 1 à **32 textes**,
  **4 500 caractères** au plus par texte, corps JSON de **2 Mio** maximum.
- 768 dimensions normalisées, encodage float ou base64 et consommation de jetons.
- **16 demandes en attente**, en plus de la demande active, en ordre FIFO.
- **HTTP 429** lorsque la file est pleine ou après 30 secondes d’attente.
  L’Agent doit réessayer avec un délai progressif.
- Jusqu’à cinq secondes pour accéder au moteur partagé avec la mémoire interne,
  puis 45 secondes pour le calcul. Le client Windows attend jusqu’à 90 secondes.
  Un échec du moteur reste signalé par **HTTP 503**.
- Les droits de l’accès personnel sont contrôlés à l’admission, après l’attente
  et après le calcul. Une demande révoquée en attente n’atteint pas le modèle.

Le worker et la lecture de sa réponse acceptent désormais 2 Mio ; 32 vecteurs
float réels dépassent l’ancienne limite interne de 512 Kio. Les limites de la
route de notifications restent à 64 Kio. Les autres routes conservent leurs
limites existantes.

Mettre le client EXE à jour dans **Réglages → Mises à jour**. Un ancien EXE garde
sa limite d’entrée de 64 Kio, même avec le serveur actualisé. La nouvelle file
s’applique déjà côté serveur à ses demandes valides. Android et Linux ne sont
pas reconstruits par cette livraison.

## Vérifications et preuves

- **104 tests client**, **13 tests ciblés serveur/API/mémoire** : succès.
- File réellement saturée : une demande active et seize en attente, dix-huitième
  admission refusée, ordre FIFO vérifié, expiration libérant sa place.
- Test HTTP concurrent : une demande attend le calcul précédent, et une
  révocation pendant son attente empêche son exécution.
- Test réel des deux ponts WireGuard et de l’API locale Windows : lot de 32 textes
  dépassant 64 Kio, avec un moteur synthétique isolé. Le runner utilise le
  binaire de staging avant de remplacer celui de production.
- Construction Windows, auto-tests natifs, version gelée, comparaison du
  bytecode client et des onze ressources UI aux sources, pont embarqué vérifié.
- Contrôle des sources et contrôle UX ; les cinq avertissements de textes longs
  de la console sont conservés et examinés lors de la livraison précédente.

`tests-api.log`, `tests-client.log`, `tests-go.log`, `check-sources.log`,
`ux-check.log` et `frozen-validation.json` conservent les contrôles.
`publication.json` et `production.json` attestent la livraison signée, les EXE
personnels et le téléchargement authentifié. `embedding-production.json`
contient les contrôles du vrai moteur : lots de 32 en float/base64, API locale
Windows via HTTPS et rafale de 17 requêtes simultanées, avec 768 dimensions et
vecteurs normalisés. Aucun contenu utilisateur ni clé n’est écrit dans ces preuves.

La première tentative de publication a attendu une requête Qwen en cours,
sans la couper. `initial-snapshot/` conserve le premier instantané ; après
retour au repos, `avant-livraison.json` et `sauvegarde-avant.json` sont renouvelés
avec une sauvegarde chiffrée vérifiée et sa copie NAS. Les contrôles comparent
les données, accès, clés, réglages et programmation des sauvegardes avant/après,
et préservent les processus Qwen chargés. La console et EG2 redémarrent par la
procédure existante. La distribution et le pont précédents sont dans `previous/`.

Une nouvelle requête Qwen est arrivée pendant les auto-tests personnels : la
procédure a suspendu le redémarrage après préparation des fichiers. La phase
`publish.py activate` a ensuite terminé la mise en service au retour au repos,
sans refaire les EXE personnels et sans couper la génération en cours.

## Limite de durée sur les longs lots

Le premier essai réel avec **32 textes de 4 200 caractères** a renvoyé HTTP 503 ;
sa trace est conservée dans `long-batch-probe.log`. Les 32 textes sont acceptés
par la validation et le transport, mais le budget de calcul reste de 45 secondes.
La vérification réussie de `embedding-production.json` utilise des textes courts.
Pour les gros passages, l’Agent doit réduire la taille du lot après un échec,
plutôt que réessayer sans fin le même lot. Cette limite CPU n’est pas masquée par
la hausse du nombre de textes admis.

Le comportement en cas de file pleine et d’expiration est vérifié sur données
synthétiques ; les requêtes du vrai moteur n’ont pas besoin de saturer la
production pendant 30 secondes pour répéter ces cas. Cette livraison ne mesure
pas l’impact d’une charge EG2 soutenue sur toutes les fonctions vocales ou les
générations Qwen ; elle conserve les deux threads CPU et le calcul unique.

`publish.py prepare` et `publish.py publish` ne doivent pas être rejoués sans
examiner les preuves existantes. `verify.py` refait les requêtes EG2 synthétiques,
avec des réglages client temporaires. `run_api_tests.py` vérifie le bridge de staging.
