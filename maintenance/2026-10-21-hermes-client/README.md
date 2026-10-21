# Ajout de modèles à Hermes depuis le client Windows

Livraison Windows/serveur **3.5.33**, le 21 octobre 2026. Android reste en 1.0.13/code 14.

La capture du poste client montrait les identifiants `fred-model-…` transformés en « Fred Model… », le modèle d’embeddings dans les conversations et tous les interrupteurs désactivés. Hermes Desktop construit le nom affiché à partir de l’identifiant, sans utiliser le champ `name` de `/models`. Le bouton Fred ne pouvait donc pas corriger ces noms en ajoutant seulement des libellés YAML.

Fred configure désormais une API locale dédiée à Hermes, `/hermes/v1`. Son catalogue propose uniquement les modèles de conversation disponibles. Les identifiants ont un préfixe stable distinct par modèle et un dernier composant lisible, que Hermes affiche. Les requêtes sont traduites vers l’identifiant serveur exact avant transmission ; les autres paramètres, outils et le streaming utilisent le transport existant. L’API générale `/v1`, notamment `/v1/embeddings`, garde son catalogue et ses identifiants.

Un nouvel ajout remplace la liste du fournisseur Fred pour enlever les anciens identifiants et EmbeddingGemma. La sauvegarde exacte du YAML, les autres fournisseurs et le modèle global personnel sont conservés. Les préférences de visibilité sont dans le stockage privé Electron de Hermes : elles ne sont pas écrasées par Fred. Le message après ajout indique explicitement d’activer l’interrupteur du modèle.

## Sur le PC client

1. Mettre Fred à jour vers **3.5.33**.
2. Dans Fred, sélectionner le modèle souhaité et cliquer sur **Ajouter à Hermes**.
3. Relancer Hermes, ouvrir **Modèles**, puis activer les modèles souhaités sous **Serveur Fred**. Les interrupteurs noirs de la capture correspondent à des modèles masqués.
4. Choisir le modèle dans la conversation et garder Fred ouvert.

## Vérifications et publication

- 22 tests Python du client et 12 tests d’intégration de configuration réussis ; cinq suites d’interface réussies.
- `validation-native.json` : catalogue et changement de modèle avec le runtime Hermes installé dans un profil temporaire, aller-retour avec son SDK OpenAI et formatage par le code TypeScript réel de son interface. Ces appels utilisent un serveur synthétique, sans inférence facturée.
- `artefacts.json` : nouveaux modules présents dans l’EXE, ressources et bridge identiques aux sources, autotest réel de l’EXE réussi.
- `publication.json` : manifeste Windows signé et clients personnels reconditionnés avec leurs profils existants. La distribution 3.5.32 est conservée sous `toolchain/releases-staging/hermes-client-20261021/previous/windows`.
- `production-apres.json` : mise à jour vérifiée, Qwen conservé avec les mêmes processus, Hermes et EG2 prêts, clés, données, réglages et politique de sauvegarde conservés.

Le PC client distant n’a pas été piloté. Sa mise à jour, le nouvel ajout et l’activation des interrupteurs restent à effectuer sur ce PC.
