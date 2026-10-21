# Noms des modèles dans OpenCode 2

Windows/serveur **3.5.34**, le 21 octobre 2026. Android reste en 1.0.13/code 14.

Le bouton Ajouter à OpenCode 2 utilisait l’identifiant technique Fred comme nom affiché. Il utilise maintenant le libellé public du catalogue, par exemple GPT-6 Luna. L’identifiant de requête reste identique, et le mécanisme existant active le modèle sélectionné dans les préférences d’OpenCode Desktop.

Lors d’un ajout, les noms des autres modèles Fred déjà configurés et présents dans le catalogue sont aussi actualisés. Aucun autre modèle du catalogue n’est ajouté automatiquement. Les options des modèles, les autres fournisseurs, les préférences de visibilité des autres modèles, les commentaires JSONC et le modèle global sont conservés. Le fichier précédent bénéficie d’une sauvegarde exacte. Un modèle indisponible ou d’embeddings ne peut pas être ajouté comme modèle de conversation.

Sur le PC client : mettre Fred à jour en **3.5.34**, fermer complètement OpenCode 2, puis cliquer à nouveau sur **Ajouter à OpenCode 2**. Rouvrir OpenCode et choisir le modèle sous **Serveur Fred**. Garder Fred ouvert.

Vérifications : 14 tests de configuration, sept tests de visibilité et 22 tests Python du client réussis. Le test natif avec OpenCode **2.0.32** utilise une configuration, une base SQLite et une API temporaires ; il vérifie le nom exposé par OpenCode, l’activation du modèle, la priorité JSONC, la sauvegarde, la conservation des autres paramètres et une requête de conversation authentifiée envoyée avec l’identifiant exact. Aucune inférence facturée et aucune modification de la configuration personnelle OpenCode.

`verification-opencode.json` contrôle le code embarqué dans le nouvel EXE, `artefacts.json` son autotest et ses ressources, `publication.json` la signature et les clients personnels reconditionnés. `production-apres.json` confirme la disponibilité des services et la conservation des processus Qwen, données, clés, réglages et sauvegardes. La distribution précédente est conservée sous `toolchain/releases-staging/opencode-noms-20261021/previous/windows`.

Le poste client distant n’a pas été piloté : sa mise à jour et le nouvel ajout restent à effectuer sur ce poste.
