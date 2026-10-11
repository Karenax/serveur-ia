# Gestion des clients — 6 octobre 2026

La console serveur, rubrique **Clients**, propose maintenant **Renommer** et **Supprimer** pour chaque client, y compris les accès déjà révoqués.

## Renommer

Cliquez Renommer, saisissez un nom de 1 à 80 caractères, puis Enregistrer le nom. Le prochain téléchargement prend la forme **Accès serveur Fred v3.5.3 - NOM DU CLIENT.exe**, avec la version réelle du profil. Les caractères incompatibles avec un nom de fichier Windows sont remplacés. L’identité du client, ses clés, son accès et ses conversations sont conservés. Retéléchargez l’EXE pour obtenir un fichier portant le nouveau nom.

## Supprimer

Cliquez Supprimer, puis Confirmer la suppression. Le client disparaît de la liste ; son jeton API est invalidé, ses requêtes et sessions sont annulées et son pair WireGuard est retiré. L’EXE n’est plus téléchargeable depuis la console et ne permet plus de se connecter, y compris par Cloudflare.

Les conversations et fichiers restent sur le serveur. Une fiche révoquée est conservée dans l’archive interne du registre pour permettre la sauvegarde et la restauration de ces données. Les anciennes copies de l’EXE ne retrouvent pas d’autorisation après restauration de cette archive.

## Vérifications

- 9 tests Python réussis : renommage, suppression et refus d’accès, maintien des autres clients, sauvegarde/restauration des données conservées, erreur d’écriture, protection des actions HTTP et nom du téléchargement.
- Syntaxe JavaScript et vérification du diff réussies.
- Interface vérifiée dans le navigateur : formulaire de renommage, boutons sur les clients autorisés et révoqués, confirmation de suppression et annulation.
- La console a été rechargée après vérification de l’absence de requêtes et tâches en cours. Le processus du modèle chargé a été conservé ; WireGuard et la version signée 3.5.3 restent disponibles.

Aucun client existant n’a été renommé ou supprimé pendant les vérifications de l’interface.
