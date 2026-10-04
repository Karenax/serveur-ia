# Moteurs tiers

Pour chaque entrée de `moteurs.json`, cloner `remote` dans `directory`, extraire le commit `patch_base`, puis appliquer le patch depuis ce dossier avec `git apply --binary <chemin-du-projet>/dependances/<patch>`. Copier ensuite les éventuels fichiers indiqués par `additional_directory` dans le moteur.

Les patchs contiennent les modifications locales, y compris les changements committés depuis la base. Les outils CUDA, modèles et environnements Python ne sont pas sauvegardés ici. Relancer `Sauvegarder-Dependances.py` avant un commit pour actualiser cet instantané.
