# Audit du dossier et nettoyage — 17 octobre 2026

Audit de l'organisation, des volumes locaux, de la documentation de production et
de l'état Git. Il ne s'agit pas d'un nouvel audit fonctionnel du code.

## Nettoyage réalisé

Cinq archives téléchargées à la racine ont été supprimées : `cudart.zip`,
`llama-cpu.zip`, `llama-cuda.zip`, `unsloth-legacy.zip`, `unsloth-portable.zip`.
Chaque fichier contenu dans chaque archive a été comparé en taille et SHA-256
avec sa copie extraite conservée. Aucune référence à ces noms d'archives n'a été
trouvée dans les scripts et documents du périmètre recherché.

Cinq caches régénérables ont été supprimés : `__pycache__`, `.ruff_cache`,
`lanceur/__pycache__`, `client-qwen/__pycache__`, `client-voice/__pycache__`.
Le script vérifie qu'aucun fichier de ces caches n'est suivi par Git et refuse
les sous-éléments constituant des liens de système de fichiers.

Le bilan exact est dans `bilan.json`. Les empreintes des archives et la preuve
de comparaison de leurs 206 fichiers sont dans `archives.json` ; les caches
et leurs volumes sont dans `caches.json`. `nettoyer.ps1` conserve la procédure
exécutée et ses contrôles de confinement dans le projet.

## Éléments conservés

- Sources actives et modifications locales déjà présentes dans Git.
- Moteur officiel Strata, encodeur vision, modèles, environnements de production.
- Comptes, conversations, clés, configurations privées et sauvegardes.
- Moteurs historiques, patchs et résultats : la documentation
  `ARCHIVES-ET-PREUVES.md` et `dependances/README.md` les conserve comme références
  ou solutions de retour arrière.
- Journaux et preuves historiques, y compris ceux exclus de Git : leur absence
  du dépôt ne signifie pas qu'ils sont sans valeur.

## Volumes et pistes restantes

L'inventaire initial donne environ 67 Gio pour les dossiers visibles, dont
45,6 Gio dans `toolchain` et 5,8 Gio dans `strata-data`. Les archives à la racine
s'ajoutaient à ces volumes. Mesure logique des fichiers, hors dossier Git ; ce
n'est pas une mesure des blocs réellement occupés sur disque.

`volumes-toolchain.json` détaille les quinze principaux dossiers d'outillage.
Les plus gros sont l'émulateur Android (15 Gio), le SDK Android (8,1 Gio),
`android-studio-extraction` et `android-studio` (3,34 Gio chacun), les versions
en préparation (2,23 Gio) et les téléchargements Android (2 Gio).

Les deux dossiers Android Studio de taille voisine sont une piste de doublon
à vérifier fichier par fichier et contre les chemins de compilation avant
suppression. L'émulateur et le SDK servent potentiellement à reconstruire et
valider Android ; leur volume ne démontre pas leur inutilité. Les versions
en préparation peuvent contenir des livraisons ou du retour arrière.

## Vérification

La procédure s'est terminée avec succès. Aucun fichier suivi par Git n'a été
supprimé. L'état Git final est conservé dans `git-status-apres.txt` ; le contrôle
initial est dans la sortie de la session. L'état Git a évolué pendant l'audit :
les modifications initiales ne figurent plus dans l'état final, sans action Git
d'écriture de cette procédure. Aucun service n'a été redémarré et aucun test applicatif n'a été lancé,
car le nettoyage porte sur des archives identiques aux copies conservées et
des caches régénérables. Ces caches peuvent être recréés automatiquement.
