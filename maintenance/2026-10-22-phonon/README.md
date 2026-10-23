# Remplacement du serveur de synthèse par Phonon

Demandé et **activé le 22 octobre 2026**. Phonon remplace Pocket TTS pour la
synthèse française du serveur. Fred a été redémarré ; les processus Qwen sont
restés chargés. Données, clés, réglages et programmation des sauvegardes vérifiés
identiques avant/après. `production.json` conserve la preuve de la bascule.

Phonon `ptts==0.4.1` est installé dans `toolchain/phonon-server-python`, séparé
des runtimes Qwen, EG2 et Pocket TTS. Import natif et normalisation française
exécutés sur ce CPU ; le runtime expose uniquement le périphérique CPU.
`pip check` réussit. Dépendances directes dans `lanceur/requirements-phonon.txt`.

Le checkpoint français est `gradium/phonon-40m-fr`, révision
`b0e916ef8d2a9034902c449d113c3b2d4f081651`, poids q8 et voix fournie `default`.
Ses tailles et empreintes officielles sont fixées dans `lanceur/phonon-model.json`.
Les poids sont sous CC BY-NC 4.0. Le téléchargement authentifié a réussi et
`checkpoint.json` conserve les empreintes SHA-256 des cinq fichiers locaux.
Le jeton communiqué dans le chat doit être révoqué sur Hugging Face ; la synthèse
de production n’en a plus besoin. Aucun jeton n’est enregistré dans ces rapports.

## Reconstruire le checkpoint sur une nouvelle installation

Accepter les conditions sur [la page du modèle](https://huggingface.co/gradium/phonon-40m-fr),
puis ouvrir PowerShell dans `D:\Serveur IA` et lancer :

```powershell
& '.\toolchain\phonon-server-python\Scripts\hf.exe' auth login
```

Utiliser un jeton Hugging Face de lecture autorisé sur ce modèle. Le stocker
avec la commande native, hors dépôt. Inutile de l’ajouter aux identifiants Git.

## Préparation et validation avant activation

```powershell
& '.\toolchain\phonon-server-python\Scripts\python.exe' -X utf8 maintenance/2026-10-22-phonon/prepare.py --download
& '.\toolchain\phonon-server-python\Scripts\python.exe' -X utf8 -m unittest discover -s lanceur -p test_phonon_worker.py -v
& '.\toolchain\phonon-server-python\Scripts\python.exe' -X utf8 maintenance/2026-10-22-phonon/validate.py
```

Le nouveau worker conserve le protocole de Fred : JSON, PCM mono 24 kHz signé
16 bits little endian, fragments bornés, une synthèse à la fois, textes de
600 caractères maximum et durée maximale de 90 secondes. Quatre threads CPU,
aucun PyTorch et aucun appel Hub pendant une synthèse : chemin local et empreintes
vérifiées avant chargement, voix fournie avec le checkpoint.

Les sept tests simulés passent : format, bornes, annulation avant/pendant une
phrase, fermeture du flux natif, reprise, échantillons invalides, durée excessive
et corruption de poids. Les douze tests de passerelle et de conversation passent
aussi après la bascule (`tests-gateway-final.txt`).

`native-validation.json` valide le vrai moteur français : chargement 329 ms,
premier fragment 93 ms pour une phrase produisant 4,24 s d’audio en 562 ms,
annulation acquittée en 46 ms, puis nouvelle phrase avec premier fragment en
32 ms. Mémoire résidente de l’arbre du worker : environ 202 à 244 Mio durant
ces trois essais, sans mesure de pic. Ces délais excluent Qwen et le chargement.

`live-http.json` valide Qwen réellement chargé, puis sa réponse « trois cent
vingt-trois » synthétisée par Phonon via une passerelle HTTP authentifiée
temporaire : génération Qwen 3,47 s, premier fragment TTS 109 ms pour cette
autre phrase. Une annulation HTTP et une reprise passent aussi. Les comptes et
la base de test sont temporaires ; aucune conversation personnelle ajoutée,
aucun appel Hermes ou cloud. Aucun test d’écoute humaine, d’acoustique dans la
pièce ni de microphone humain n’est revendiqué.

## Bascule exécutée

La commande suivante a été exécutée après les validations ; ne pas la relancer
sur cette production déjà migrée :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' -X utf8 maintenance/2026-10-22-phonon/activate.py
```

Ce script exige une preuve native correspondant aux empreintes des sources
actuelles. Il remplace le moteur déclaré, le worker lancé, le runtime, les
dépendances et le verrou de la voix, puis redémarre uniquement Fred avec la
procédure existante préservant les processus Qwen. Il vérifie la disponibilité
Phonon, les données, clés et sauvegardes, puis conserve `production.json`.
Les sources précédentes sont sauvegardées dans
`toolchain/releases-staging/phonon-20261022/previous` ; en cas d’échec de la bascule,
elles sont restaurées et Fred est relancé avec Pocket TTS.

Le protocole des clients est conservé : aucune nouvelle version du client
Windows n’est nécessaire pour changer le moteur serveur. La reconnaissance
vocale, le microphone et la détection de fin de tour conservent leur moteur actuel.
Les notices des sources des futurs paquets clients et le guide de conversation
ont été actualisés. Les EXE déjà distribués conservent leurs notices historiques,
mais utilisent immédiatement le nouveau serveur avec leur protocole existant.
L’ancien point d’entrée `lanceur/voice_worker.py` redirige aussi vers Phonon.
L’ancien runtime Pocket TTS et ses sources sont conservés uniquement pour retour
arrière ; la production ne les charge plus.

Références : [runtime et API](https://github.com/gradium-ai/xn-ptts),
[paquet 0.4.1](https://pypi.org/project/ptts/0.4.1/),
[modèle français](https://huggingface.co/gradium/phonon-40m-fr).
