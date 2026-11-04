# Codex : ajout sans remplacement des modèles — 3 novembre 2026

Windows **3.5.57** remplace l’installation globale Qwen de 3.5.56 par un ajout
de fournisseur optionnel. Le bouton enregistre `[model_providers.kiara]` et un
profil `kiara.config.toml`, sans réécrire les choix par défaut de `config.toml`.

Sont conservés : modèle et fournisseur habituels, catalogue global, niveaux de
réflexion, recherche web, réglages des sous-agents, autorisations, autres
fournisseurs, MCP, authentification et conversations. Le catalogue Qwen est
limité au profil Qwen ou à son endpoint de découverte propre.

La réparation automatique proposée pendant le diagnostic a été retirée à la
demande de l’utilisateur. Une configuration déjà basculée par une ancienne
installation n’est pas restaurée par cette version.

## Validation

- Cinq tests de l’installateur : conservation complète des réglages habituels,
  ajout répétable, configuration multiligne et authentification préservées,
  chiffrement DPAPI, absence de réparation de valeurs existantes.
- Six tests de l’intégration : clic HTTP réel, téléchargement authentifié,
  signature et intégrité avant exécution, clé chiffrée et restauration lors
  d’un échec d’installation.
- Test réel dans Codex 0.166.0-alpha.5.1 : huit modèles OpenAI restent listés,
  `gpt-6.1-sol` reste le défaut, une conversation explicitement liée au fournisseur
  Kiara reçoit `COEXISTENCE-OK` de Qwen et la liste OpenAI reste identique ensuite.
  Aucun appel d’inférence OpenAI n’est nécessaire pour ce contrôle.
- Test navigateur du bouton, du guide, du résultat, des erreurs, de l’état
  d’attente, du choix de modèle, du focus et de la largeur étroite.
- Contrôles de sources et UX ; les trois avertissements de textes longs dans
  la console serveur sont antérieurs à ce changement.

La version Codex installée ne propose pas de liste de modèles avec une identité
de fournisseur par entrée. Ce changement ne prétend donc pas ajouter Qwen au
menu ChatGPT d’une conversation OpenAI. Qwen reste utilisable avec
`codex --profile kiara` ou par une conversation explicitement liée à Kiara via
le protocole app-server. Les réglages ChatGPT demeurent ceux de l’utilisateur.

Le rapport de coexistence est dans
`toolchain/test-results/codex-20261103/coexistence.json`. La publication réutilise
les contrôles de sauvegarde, de signature et de préservation du modèle chargé.
