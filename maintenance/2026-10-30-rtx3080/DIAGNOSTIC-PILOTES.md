# RTX 3080 après mise à jour et redémarrage

Windows a redémarré le 30 octobre 2026 à 23:05:06 (heure locale).
L'utilisateur demande une analyse de la disparition apparente de la 3080.
Aucune installation, suppression ou réaffectation de pilote n'a été effectuée
pendant ce diagnostic.

## Constat

La RTX 3080 est présente sur le bus PCIe, identifiant matériel
`PCI\VEN_10DE&DEV_2216&SUBSYS_403F1458`. Son contrôleur audio HDMI est également
présent et sans erreur. Le périphérique Display est en code 31, avec le statut
`0xC0000182`, et reste associé au pilote **560.94**, `oem114.inf`.
Elle ne figure donc pas parmi les GPU utilisables dans `nvidia-smi`.

Les deux P100 et la P2200 sont sans erreur et utilisent maintenant **582.99** :
`oem119.inf` pour les P100 et `oem122.inf` pour la P2200. Le code matériel de la
3080 (`DEV_2216`) ainsi que les libellés RTX 3080 sont absents de ces deux nouveaux
INF, alors qu'ils figurent bien dans l'ancien `oem114.inf`.

Ces faits montrent une migration partielle des pilotes : le nouveau pilote est
actif sur trois cartes, tandis que la GeForce reste sur l'ancien paquet et échoue
à démarrer. Le mélange de paquets et l'absence de prise en charge de la 3080 par
les nouveaux INF constituent la cause logicielle probable. Le code 31 ne prouve
pas à lui seul le mécanisme interne exact de l'échec.

Le journal `C:/Windows/INF/setupapi.dev.log` confirme l'installation de 582.99
vers 22:47–22:48 et la demande de redémarrage parce que l'ancien pilote ne se
déchargeait pas. Le redémarrage a bien activé 582.99 pour les trois cartes
compatibles ; il n'a pas affecté un nouveau paquet compatible à la 3080.

## Correction à préparer

Vérifier la prise en charge explicite des quatre modèles par les paquets retenus
et leur compatibilité de coexistence sous Windows, en particulier GeForce +
Tesla + Quadro. Le seul numéro de branche 580 ne garantit pas cette couverture.
Ne pas forcer les INF professionnels actuels sur la 3080 : son identifiant
matériel n'y figure pas. Aucune version précise ni procédure de réinstallation
des quatre cartes n'a encore été validée par cette analyse.

Preuves machine : `diagnostic-pilotes-apres-redemarrage.json`.
Définition Microsoft du code 31 :
https://learn.microsoft.com/en-us/windows-hardware/drivers/install/cm-prob-failed-add

Les tests du modèle avec la 3080 restent en attente de résolution de ce problème.
Les profils de stockage sur F: et les autres modifications précédentes restent
en place. L'ancienne copie PLE sur C: n'a pas encore été supprimée.
