# Résultats du 31 octobre 2026 après redémarrage

Les quatre GPU sont reconnus sous NVIDIA 581.80, sans erreur PnP après le
redémarrage de 09:35. Les essais RTX qui échouaient au premier produit cuBLAS
avant la mise à jour réussissent désormais. Cela ne permet pas de séparer
l'effet de l'installation propre et celui du redémarrage.

## Comparaison mesurée

Même moteur officiel Strata 0.1.54 CUDA 12.9, même modèle IQ4_XS depuis F:,
PLE/Ngram directement sur F:, contexte 8192, préfill 2048, 15 workers, MTP 3.
Cache de prompt et cache de conversation désactivés. Médianes de trois générations
de 256 tokens et deux préremplissages par longueur, avec zéro token de cache réutilisé.

| Mesure | Deux P100 | RTX 3080 + deux P100 | Gain de débit |
| --- | ---: | ---: | ---: |
| Génération | 34,9 tok/s | 54,5 tok/s | +56,2 % |
| Préfill 1516 tokens | 248,7 tok/s | 482,8 tok/s | +94,1 % |
| Préfill 5932 tokens | 298,1 tok/s | 580,7 tok/s | +94,8 % |

Les contrôles de calcul et restitution du code sont corrects. Le contrôle des
textes générés vérifie une réponse non vide ; ce n'est pas une évaluation générale
de qualité. Les différences de sortie sont attendues entre chemins de calcul GPU.

Sur l'essai RTX, CUDA0 est la 3080 : projections natives, états et MTP sur cette
carte. Les deux P100 reçoivent chacun 6077 experts supplémentaires (15,07 Gio) ;
leurs compteurs de requêtes confirment leur participation effective. Le complément
CPU verrouillé est de 30,63 Gio, contre 45,04 Gio avec les deux P100 seuls.

VRAM maximale échantillonnée : 7854 Mio sur la 3080 et 15912 Mio sur chaque P100.
Températures maximales pendant les requêtes : 62 °C pour la 3080, 39 °C pour les
P100 dans le montage RTX ; 58/60 °C pour les P100 seuls. Aucun échantillon ne
signale de bridage thermique. Les sondes sont espacées de deux secondes.

Le chemin dense BF16 du préfill sur Ampere est éligible aux Tensor Cores ; aucun
profilage matériel Nsight n'a été effectué, donc aucun taux d'utilisation des
Tensor Cores n'est revendiqué. Les gains mesurent toute la configuration, y
compris le placement des experts, les transferts et le MTP.

Ces résultats concernent le contexte 8192. Le profil habituel à 262144 tokens
reste à valider sur la 3080 de 10 Gio avant tout déploiement permanent. Les
temps de chargement ne sont pas comparés, car le cache disque diffère.
L'ancienne mesure à 398,95 tok/s sur 5932 tokens utilisait un autre moteur et un
autre pilote ; elle n'est pas utilisée pour calculer les gains ci-dessus. Le
nouveau moteur ne constitue donc pas un gain garanti pour tous les montages.

## Vision et stockage

La P2200 réussit l'encodage de l'image synthétique sous 581.80 : 240 tokens
visuels en 0,578 s, environ 1156 Mio de VRAM. Le modèle du test est sur F:.
Le rapport `vision-pilote58180-apres-redemarrage.json` conserve la mesure.
Cet encodage est mesuré séparément des requêtes de performance textuelle ;
les débits ci-dessus n'incluent pas le temps de lecture d'une image.

Les trois shards IQ4_XS et la table PLE sont présents sur F:. Le SHA-256 complet
de la copie PLE a été vérifié lors de la migration. L'ancien fichier sur C: est
déjà absent au début de cette reprise ; aucune suppression n'a été faite ici.
Les chemins D: restants servent au pack auxiliaire, au profil d'experts et au MTP.

## Preuves

- `comparison.json` : synthèse, médianes, températures et intégrité des profils.
- `rtx3080-ctx8192-pilote58180-apres-redemarrage/` : requêtes, réponses, journaux,
  configuration et télémétrie du montage à trois GPU.
- `p100-ctx8192-pilote58180-apres-redemarrage/` : référence avec le même moteur.
- `after-reboot-inventory.json` : démarrage, pilotes et erreurs PnP.
- Les deux benchmarks ont conservé tous les profils persistants à l'identique.
- 16 tests résidence/admission et 8 tests du lanceur réussissent ; contrôles de
  syntaxe : 474 Python, 88 JavaScript, 94 PowerShell dans chaque interpréteur.

Le service habituel est rechargé et prêt avec son profil deux P100, vision P2200 et
moteur 0.1.45.3, contexte 262144. La requête image complète réussit en 6,656 s :
« Le code est VISION 47. La forme rouge est un cercle et la forme bleue est un
carré. » La validation est consignée dans `production-after-58180.json` ; la
configuration de session confirme les chemins F: pour le modèle et la PLE.

À la demande suivante de l'utilisateur, le profil RTX 3080 + deux P100 + P2200
est devenu le défaut actif avec Strata 0.1.54 et contexte 262144 en FP16, KV
partiellement en VRAM. La validation finale et le retour arrière sont décrits
dans `default-architecture/README.md`. Le service deux P100 ci-dessus correspond
à la remise en route immédiatement après les mesures comparatives.
