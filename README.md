# Serveur IA

Projet privé de serveur Qwen local, avec un lanceur web, un client Windows et des mesures d'inférence sur deux Tesla P100.

## Organisation

- `lanceur/` : pilotage du serveur, interface web, comptes, espaces de travail et accès distant.
- `client-qwen/` : client Windows, interface de conversation, historique et mises à jour.
- Les scripts `Start-*.ps1`, `Stop-*.ps1`, `Build-*.cmd` et les scripts Python à la racine servent au lancement, à la compilation et aux comparatifs.
- `analyses/`, `comparatifs/`, `recherche/` et les rapports à la racine conservent les protocoles et résultats.
- `contribution-strata-p100/` contient la proposition expérimentale soumise à Strata : https://github.com/Niko1221/Strata/pull/527.
- `dependances/` conserve les références des moteurs tiers et leurs adaptations locales sous forme de patchs.

## Utilisation locale

Le poste d'origine utilise Windows et le dossier `D:\Serveur IA`. Certains scripts et configurations contiennent les chemins de ce poste : les adapter avant une installation ailleurs.

`Serveur Qwen.cmd` lance `Start-Interface-Qwen.ps1`. Consulter `lanceur/LISEZ-MOI.txt`, `client-qwen/LISEZ-MOI.txt` et les rapports `RESULTATS-*.txt` pour les commandes et configurations mesurées. Les prérequis Python du lanceur et du client sont dans leurs fichiers `requirements*.txt`.

Les moteurs Strata et llama.cpp restent des dépôts distincts. Leurs sources, outils CUDA et environnements Python doivent être installés séparément. Les références et patchs enregistrés dans `dependances/` permettent de retrouver les versions et modifications locales.

## Périmètre de sauvegarde Git

Ce dépôt conserve les sources du projet, les scripts, configurations de modèle, protocoles et résultats textuels. Les poids des modèles, logiciels téléchargés, binaires compilés et journaux de fonctionnement sont exclus.

Les comptes, clés et paramètres d'accès WireGuard, fichiers chiffrés DPAPI, bases de données et historiques de conversations restent sur le poste. Leur sauvegarde doit être organisée séparément ; ils ne sont pas inclus dans ce dépôt privé.

Les performances consignées correspondent aux versions et au matériel indiqués dans chaque rapport. Elles ne constituent pas une garantie pour d'autres configurations.
