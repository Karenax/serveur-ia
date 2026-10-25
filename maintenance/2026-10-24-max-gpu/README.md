# Max : carte dédiée et sélection manuelle

L’ancienne sélection classait les cartes Vulkan selon leur mémoire libre, puis
leur mémoire totale. Une puce intégrée qui annonce beaucoup de RAM partagée
pouvait donc passer devant une RX 7800 XT avec 16 Go de VRAM.

Le runtime lit maintenant le type réel fourni par GGML/Vulkan : GPU dédié ou
GPU intégré. En automatique, une carte dédiée passe avant toute carte intégrée,
quelle que soit l’estimation de mémoire libre de cette dernière. Les cartes
dédiées sont ensuite classées par mémoire totale puis libre. Aucun seuil de
mémoire ou résultat de benchmark ne bloque une carte.

Dans **Vocal → Max → Ce PC**, le nouveau sélecteur **Carte graphique de ce PC**
permet de conserver l’automatique ou de choisir une carte AMD/NVIDIA détectée.
Les options distinguent mémoire partagée et mémoire dédiée. Le nom utilisé au
chargement de la synthèse est affiché, séparément de la simple recommandation.
Le sélecteur est verrouillé pendant un appel, une installation ou un test.
Le traitement sur le serveur conserve ses réglages propres.

## Identité et persistance

La sélection est stockée dans `voice-max/gpu.json`, indépendamment des préférences
d’animation, d’interruption et du profil Low/Max. Elle utilise une empreinte de
l’adresse PCI, ou du nom exact et du type si le pilote ne fournit pas l’adresse.
Un changement d’ordre Vulkan0/Vulkan1 ne modifie donc pas la carte choisie.
Si une identité manque ou est ambiguë, le démarrage échoue clairement ; il ne
rebascule pas silencieusement sur un autre GPU. L’utilisateur peut actualiser
la liste ou revenir explicitement à l’automatique.

Le changement de carte décharge uniquement la synthèse Max et invalide les mesures
de l’ancienne sélection. Un nouveau benchmark reste facultatif. Un appel suivant
reprend la carte choisie ; un autre client ayant changé le choix est également
pris en compte au prochain échauffement du moteur.

## Détection et intégrité

Le complément signé, API de runtime **4**, expose `--probe-gpus`. Cette commande
énumère les périphériques sans lire les poids ni charger de modèle vocal. Le
contrôleur vérifie les exécutables et bibliothèques avant de la lancer, puis
valide les identifiants et propriétés reçus. Les nouvelles commandes HTTP restent
sur le loopback authentifié, sans chemin de programme ou hôte fourni par l’UI.

Les structures ctypes correspondent à l’ABI de `ggml-backend.h` du GGML épinglé.
Son backend Vulkan distingue déjà `GGML_BACKEND_DEVICE_TYPE_GPU` et `IGPU` et
expose l’adresse PCI. Le moteur Qwen reçoit le nom natif résolu au moment du
chargement via `ggml_backend_init_by_name`, sans repli automatique sur le CPU.

## Vérifications

- 81 tests Python client, 32 tests moteur vocal ; 49 tests ciblés rejoués après
  les dernières corrections. Cas intégré 64 Go partagés / RX 7800 XT 16 Go,
  ordre inversé, identité disparue ou ambiguë, choix intégré volontaire, faible
  mémoire libre, persistance, intégrité, reprise après erreur et protection d’appel.
- 11 suites UI : carte recommandée, carte réellement chargée, sauvegarde/reprise,
  rechargement et ordre modifié, carte retirée, ancien complément et mise à jour.
  Les suites Low, interruptions, animations et Android restent présentes.
- Détection native réelle depuis le nouveau complément signé, dans un répertoire
  temporaire vérifié sous toolchain, avec **aucun poids présent**. La Quadro P2200
  de ce poste est identifiée comme dédiée avec son adresse PCI ; sélection sauvée
  puis relue. Résultat : `packaged-probe.json`.
- Captures Playwright MCP lues aux largeurs 1440 et 800, clair/sombre, fixture
  hybride AMD fictive : sélection, nom complet dans l’aide, focus visible et
  absence de débordement. Ce contrôle ciblé ne constitue pas un audit WCAG complet.

La RX 7800 XT n’est pas physiquement accessible ici. Sa sélection est testée avec
des périphériques simulés ; aucune mesure de vitesse réelle sur cette carte n’est
annoncée. La détection native réelle porte sur le matériel NVIDIA de ce poste.

## Livraison

Windows **3.5.48** et complément Max signé API 4. Dans le client mis à jour,
**Mettre à jour Max** remplace le runtime d’environ 46 Mo ; les poids identiques
sont réutilisés. Le modèle vocal lourd reste extérieur à l’EXE de base.
Les clients avec l’ancien complément reçoivent une indication de mise à jour.

Android reste en **1.0.20/code 21**, avec Low ; les assets sources communs sont
synchronisés mais le sélecteur GPU est masqué sur Android. Les interruptions et
les deux animations sont conservées. La publication préserve aussi la désactivation
de la voix serveur demandée précédemment et vérifie qu’elle reste déchargée.
Les processus Qwen, les clés, les profils et les données sont conservés.

Preuves finales : `max-publication.json`, `publication.json`, `production.json`.
