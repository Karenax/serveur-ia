# Pilotes retenus pour l'essai des quatre GPU sous Windows 10

## Résultat de la recherche

Version commune **581.80 WHQL** : deux paquets NVIDIA officiels, avec le même
pilote noyau et la même bibliothèque CUDA. C'est une combinaison matériellement
cohérente d'après les fichiers signés examinés ; son fonctionnement simultané
sur cette machine reste à valider après installation et redémarrage.

Cette sélection revient à une version publiée en novembre 2025. Ce document
ne certifie pas la sécurité ou la stabilité générale d'un ancien pilote, ni
une validation NVIDIA du montage mixte GeForce/Tesla/Quadro.

| Cartes | Paquet 581.80 | INF signé vérifié |
| --- | --- | --- |
| GeForce RTX 3080 Gigabyte, DEV_2216 / SUBSYS_403F1458 | GeForce Game Ready desktop Windows 10/11 x64 DCH | `nv_dispi.inf`, entrée générique `PCI\VEN_10DE&DEV_2216` |
| Deux Tesla P100 PCIe 16 Go, DEV_15F8 / SUBSYS_118F10DE | NVIDIA RTX/Quadro Enterprise Windows 10/11 x64 DCH | `nv_dispwi.inf`, entrée exacte `PCI\VEN_10DE&DEV_15F8&SUBSYS_118F10DE` |
| Quadro P2200, DEV_1C31 / SUBSYS_131B10DE | Même paquet RTX/Quadro | `nv_dispwi.inf`, entrée générique `PCI\VEN_10DE&DEV_1C31` ; entrée exacte aussi dans `nvlwwi.inf` |

Les deux paquets doivent être alignés sur cette même version ; le maintien des
P100/P2200 en 582.99 ne constitue pas l'essai de la combinaison ci-dessus.

## Téléchargements officiels, déjà présents sur F:

GeForce :
https://us.download.nvidia.com/Windows/581.80/581.80-desktop-win10-win11-64bit-international-dch-whql.exe

Fichier local :
`F:/Kiara-tests/pilotes-581.80/geforce/581.80-desktop-win10-win11-64bit-international-dch-whql.exe`

RTX/Quadro (comprend les INF Tesla nécessaires) :
https://us.download.nvidia.com/Windows/Quadro_Certified/581.80/581.80-quadro-rtx-desktop-notebook-win10-win11-64bit-international-dch-whql.exe

Fichier local :
`F:/Kiara-tests/pilotes-581.80/quadro/581.80-quadro-rtx-desktop-notebook-win10-win11-64bit-international-dch-whql.exe`

Le lien Tesla officiel de la même version répond aussi avec un fichier de taille
et ETag MD5 identiques au paquet professionnel ci-dessus :
https://us.download.nvidia.com/tesla/581.80/581.80-data-center-tesla-desktop-win10-win11-64bit-dch-international.exe
Ce troisième fichier n'a pas été téléchargé, le paquet professionnel inspecté
contient déjà les entrées matérielles des deux P100.

## Vérifications effectuées sans installation

- Les deux installateurs ont une signature Authenticode **Valid**, signataire
  NVIDIA Corporation.
- Les catalogues `nv_disp.cat` ont une signature **Valid**, signataire
  Microsoft Windows Hardware Compatibility Publisher.
- `DriverVer` dans les INF et version du fichier noyau : **32.0.15.8180**.
- Le fichier `nvlddmkm.sys` est identique dans les deux paquets : SHA-256
  `f2c2a13c47f4cae5dc91aa245b99a2a7794b5c77be1d12276adc3ae2e55cf9c3`.
- Le fichier `nvcuda64.dll` est identique dans les deux paquets : SHA-256
  `a3799e40e99acbe3d4b26fb9ca2e42955bcbf0dfa03e042d26f7ed0a485a1d47`.
- Installateur GeForce SHA-256 :
  `0a08462764f4d36eeecb8da6abfc01a6e32c94359b9e1e3287399f057c1d2839`.
- Installateur RTX/Quadro SHA-256 :
  `cfe62fb91fe2c258dd0fbe38b3b8941b1c039e4422bf2e08f9ea0e8a577bfa44`.
- Extraction faite avec 7-Zip, sans exécuter les installateurs et sans modifier
  les INF ou le magasin de pilotes Windows.

Paquets plus récents : les INF 582.99 actuellement installés ne couvrent pas la
3080. L'archive GeForce 582.78 officielle a aussi été téléchargée et inspectée :
aucune entrée DEV_2216 (ni DEV_15F8 ou DEV_1C31) dans ses INF. Le site NVIDIA
décrit les nouvelles éditions GeForce Security Update comme destinées aux
anciennes générations Maxwell/Volta/Pascal. Le seul numéro de branche 582 ne
suffit donc pas à couvrir la RTX 3080 Ampere. Ne pas utiliser le fichier GeForce
582.78 téléchargé pour ce montage.

Les résultats bruts sont dans `driver-geforce-58180.json`,
`driver-quadro-58180.json` et `driver-geforce-58278.json`.

## Sources primaires

- GeForce 581.80, liste NVIDIA incluant RTX 3080 :
  https://www.nvidia.com/pt-br/drivers/details/257589/
- RTX/Quadro 581.80, liste NVIDIA incluant P2200 :
  https://www.nvidia.com/ko-kr/drivers/details/257498/
- Data Center 581.80, liste NVIDIA incluant Tesla P100 :
  https://docs.nvidia.com/datacenter/tesla/tesla-release-notes-580-105-08/index.html
- Historique des branches professionnelles :
  https://www.nvidia.com/en-us/drivers/rtx-enterprise-and-quadro-driver-branch-history/
- Exemple de GeForce Security Update 582.53 limité aux anciennes générations :
  https://www.nvidia.com/en-us/geforce/drivers/details/271217/

## Étape suivante

Préparer une réinstallation contrôlée des quatre périphériques, avec sauvegarde
des paquets actuels et alignement effectif de leurs associations INF en 581.80.
Après redémarrage : quatre GPU dans `nvidia-smi`, zéro code d'erreur PnP, puis
encodage sur P2200 et reprise du benchmark RTX 3080 + deux P100 depuis F:.
Ne pas confondre la couverture des identifiants et l'identité des binaires,
déjà vérifiées, avec ce test réel restant à effectuer.
