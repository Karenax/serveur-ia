# Moteurs tiers

Depuis le 13 octobre 2026, le moteur de production Flash-Next est la distribution officielle CUDA 12 de Strata **0.1.43.1**, installée dans `strata-0.1.43.1/` avec sa source serveur, ses bibliothèques CUDA 12.9, son tokenizer et le profil experts testé. Les modèles restent dans `strata-data/`. La preuve de déploiement et la sauvegarde précédente sont dans `maintenance/2026-10-13-strata-0.1.43.1/`. L'ancien moteur P100 personnalisé reste disponible.

`moteurs.json` référence les six dépôts historiques et leurs modifications ; il ne décrit pas la distribution officielle actuellement chargée. Pour celle-ci, suivre [le guide de mise en service](../maintenance/2026-10-13-strata-0.1.43.1/README.md) et l’empreinte de `production.json`. La vérification du contexte du 13 octobre confirme que le processus actif exécute ce binaire.

Pour chaque entrée de `moteurs.json`, cloner `remote` dans `directory`, extraire le commit `patch_base`, puis appliquer le patch depuis ce dossier avec `git apply --binary <chemin-du-projet>/dependances/<patch>`. Copier ensuite les éventuels fichiers indiqués par `additional_directory` dans le moteur.

Les patchs contiennent les modifications locales, y compris les changements committés depuis la base. Les outils CUDA, modèles et environnements Python ne sont pas sauvegardés ici. Relancer `Sauvegarder-Dependances.py` avant un commit pour actualiser cet instantané.
