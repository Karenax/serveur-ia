# Installation NVIDIA 581.80 — 30 octobre 2026

Installation explicitement demandée par l'utilisateur, effectuée avec élévation
administrateur Windows. Les installateurs NVIDIA et catalogues Microsoft ont
été revérifiés, et les paquets précédents `oem114.inf`, `oem119.inf`, `oem122.inf`
ont été exportés avant toute modification. Le modèle était inactif au moment
de son arrêt via la console locale.

Les fichiers INF signés officiels ont été installés via l'API Microsoft
`UpdateDriverForPlugAndPlayDevicesW`, avec le drapeau FORCE nécessaire au retour
de 582.99 vers 581.80, en ciblant uniquement les identifiants matériels vérifiés.
Les trois appels (RTX 3080, deux P100, P2200) ont réussi. Aucune modification
des INF, suppression des anciens paquets ou modification des réglages CUDA/TCC.

Contrôle après installation : **quatre GPU présents dans `nvidia-smi`, tous en
581.80**, et quatre périphériques Display sans problème PnP (code 0).
L'API n'a signalé aucun besoin de redémarrage obligatoire.

À la demande de prudence exprimée par l'utilisateur, les mesures sont néanmoins
différées jusqu'à un redémarrage propre. Le chargement de benchmark entamé sous
le tag `pilote58180` a été arrêté ; son interruption ne constitue pas une erreur
CUDA. Aucun redémarrage automatique n'a été lancé.

Journaux et sauvegardes :
`F:/Kiara-tests/installation-58180-20261030-autorisee/`.

Après redémarrage, vérifier les quatre GPU et reprendre le protocole de
`REPRISE.md`. La validation de calcul avec les quatre cartes reste à faire.
