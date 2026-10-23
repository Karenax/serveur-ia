# Tiphaine, voix française de Fred

Voix choisie par l'utilisateur après écoute des deux aperçus le 23 octobre 2026.
Phonon 0.4.1 et le checkpoint français restent identiques. La voix sélectionnée
est maintenant `Tiphaine`, déclarée `fr-FR` dans le catalogue Gradium.

L'embedding `0fvH6XAKvA748v2v` provient de `gradium/phonon-voices`, révision
`0ee17205f254b5abc43b266c8a0f215565c352f7`, sous Apache-2.0. Le fichier local
`voices/Tiphaine.safetensors` fait 256136 octets, SHA-256
`5646677e9cf4a517e8cc316f94a34e18fa987e224925d916d6fe13396579b95b`.
Le modèle conserve sa licence existante. Métadonnées et sources des six fichiers
sont dans `lanceur/phonon-model.json`. Le préparateur existant télécharge aussi
la voix épinglée depuis son dépôt, puis la copie à l'emplacement local attendu.
Le chargement et les synthèses utilisent exclusivement les fichiers vérifiés.

Le worker et l'état du service utilisent la voix de cette configuration. Les
clients n'envoient aucune voix ni aucun chemin arbitraire. La voix française
initiale est conservée comme ressource de base du checkpoint.

Les sept tests du worker passent. `validate.py` utilise le vrai moteur pour la
synthèse, l'annulation et la reprise ; `native-validation.json` contient les
résultats et les empreintes des sources. Premier fragment : environ 110 ms dans
cet essai ; annulation acquittée en environ 78 ms, hors réseau et lecture client.

`activate.py` recharge Fred en préservant Qwen, les clés, les données et les
réglages de sauvegarde ; voir `production.json`. Ne pas relancer une activation
déjà démarrée sans examiner ses preuves. Ce changement de voix serveur ne
nécessite aucune reconstruction ni mise à jour de l'EXE.

```powershell
& '.\toolchain\phonon-server-python\Scripts\python.exe' -X utf8 maintenance/2026-10-22-phonon/prepare.py --download
& '.\toolchain\phonon-server-python\Scripts\python.exe' -X utf8 maintenance/2026-10-23-tiphaine/validate.py
```
