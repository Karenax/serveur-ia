# Max : test indicatif et gestion des fichiers locaux

La RX 7800 XT possède 16 Go de VRAM. La précédente exclusion native reposait sur
une estimation de mémoire **libre** d’au moins 4 Go, et non sur la mémoire réelle
de cette carte. Ce seuil et le blocage lié au résultat du test sont retirés.

Max installé reste sélectionnable après un test lent, interrompu, non concluant
ou sans test. Le test conserve ses repères de fluidité (RTF jusqu’à 0,8, première
réponse jusqu’à 3 secondes et reconnaissance de la phrase de contrôle), comme
conseils. Ces mesures ne constituent plus une condition d’utilisation. Le choix
explicite « Ce PC » est respecté. Le choix automatique compare les délais mesurés
et privilégie un moteur sans erreur de chargement connue quand il est disponible.
Les mesures devenues périmées ne servent plus au classement.

Le moteur recherche une carte AMD ou NVIDIA accessible via Vulkan. Une absence
de carte accessible ou un échec de chargement du modèle produit un message de
compatibilité/chargement et des pistes de récupération. Aucun verdict de puissance
du PC n’en est déduit. Intel reste hors de la proposition d’installation.

Dans **Vocal → Max**, « Fichiers Max sur ce PC » affiche le chemin, l’espace occupé,
« Ouvrir le dossier » et « Supprimer Max de ce PC ». La suppression demande une
confirmation, arrête les workers Max inactifs et enlève tout le dossier propre à
Max : modèles, téléchargements partiels, moteur, anciennes versions et mesures.
Elle refuse un appel/test/installation actif et les liens ou jonctions vers
d’autres dossiers. Le dossier Low et les fichiers de dictée sont préservés.
Une erreur de verrouillage laisse une action de reprise. Le client ne relance
aucun téléchargement après suppression ; une réinstallation reste proposée.

## Vérifications

- 76 tests du client Python, 29 tests du moteur vocal et 5 tests de passerelle Max ; sélection GPU simulée
  avec RX 7800 XT 16 Go et estimations de mémoire libre à 0, 2 et 16 Go.
- Huit suites UI partagées Windows/Android. La suite Max couvre désormais un
  appel local après test lent, le dossier, la taille, la confirmation, la protection
  pendant un appel, une suppression ratée puis réussie et la réinstallation.
- Captures réelles du navigateur de test dans `ui/`, aux largeurs 1440 et 800.
  Aucun dépassement horizontal constaté pour le chemin ou les commandes ajoutées.
- Contrôles des sources et UX ; neuf avertissements de longueur déjà présents
  dans la console serveur, hors de ce changement.

Les résultats GPU utilisent des descriptions et mesures simulées. Aucun PC équipé
d’une RX 7800 XT n’est accessible ici : sa vitesse réelle et ses pilotes ne sont
pas validés par ces tests. Le contrôleur Low/Phonon et ses moteurs sont conservés.

## Livraison

Windows **3.5.45** et complément Max signé, API de runtime 3. Les poids restent
identiques ; leur réutilisation évite de les télécharger à nouveau lors de la
mise à jour du complément. Le client propose **Mettre à jour Max** quand le moteur
installé utilise encore l’ancien critère de mémoire. Le complément et ses modèles
restent extérieurs à l’exécutable de base. Android reste en 1.0.18/code 19,
avec Low ; seuls ses assets sources partagés sont synchronisés.

Construire le complément avec le Python de signature (le runtime de reconnaissance
ne contient pas cryptography) :

```powershell
& Strata-src/.venv/Scripts/python.exe client-voice/package_max.py --output 'D:/Serveur IA/toolchain/releases-staging/max-choice-pack' --sign-home 'D:/Serveur IA/lanceur'
```

Les scripts de publication utilisent les clés existantes et une sauvegarde
chiffrée vérifiée ; ils vérifient les téléchargements authentifiés et préservent
les processus Qwen, les profils, les données et le calendrier de sauvegarde.
Preuves de livraison : `max-publication.json`, `publication.json`, `production.json`.

Fiche constructeur : [AMD Radeon RX 7800 XT](https://www.amd.com/en/products/graphics/desktops/radeon/7000-series/amd-radeon-rx-7800-xt.html).
