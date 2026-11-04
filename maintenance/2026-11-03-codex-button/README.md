# Ajout à Codex dans le client Kiara — 3 novembre 2026

**Windows 3.5.56 est publié**, avec quatre EXE personnels reconditionnés et vérifiés.
Dans Réglages → API locale → Intégrations, « Ajouter à Codex » télécharge les
ressources signées depuis Kiara et configure Qwen avec l’accès personnel du client.
Le guide repliable est intégré au même écran. Aucun paquet séparé n’est demandé.

Le téléchargement passe par `GET /v1/client/codex`, en HTTPS ou dans le tunnel
WireGuard. Le client vérifie la signature épinglée, la taille, le SHA-256 et les
noms des fichiers avant d’exécuter l’installation. Les ressources ne contiennent
aucune clé ; la clé personnelle vient de l’accès client et reste chiffrée avec
DPAPI sur le poste. Un échec restaure les configurations précédentes.

## Vérifications

- 14 tests des intégrations Hermes/OpenCode et de leur préservation.
- 6 tests Codex : véritable trajet HTTP du bouton, téléchargement authentifié,
  signature obligatoire, installation PowerShell dans un dossier temporaire,
  chiffrement de la clé personnelle et restauration après échec.
- 20 contrôles API distante/tunnels existants exécutés avec le nouveau gestionnaire.
- Tests navigateur du bouton et du guide, de l’attente, du résultat, des erreurs,
  de la sauvegarde, du choix de modèle et des largeurs 1280/390 pixels.
- Régression de l’interface Hermes et du sélecteur de modèles Windows/Android.
- Contrôle des sources réussi. `ux:check` conserve trois avertissements de textes
  longs préexistants dans la console serveur ; aucun contenu supprimé.
- EXE compilé : interface identique aux sources, nouveau bridge embarqué et
  exécution du vérificateur de téléchargement depuis le code Python gelé.
- Production : téléchargement signé de la mise à jour, EXE personnels préservés,
  ressources Codex récupérées par HTTPS avec un accès existant, signature vérifiée.

Les captures utilisent uniquement des données fictives. Les tests d’installation
écrivent dans des dossiers temporaires, sans modifier le Codex réel de l’utilisateur.
La connexion réelle vérifie et décompresse les ressources sans les installer.

## Mise en service

Sauvegarde chiffrée créée et vérifiée avant publication. Le modèle Qwen est resté
chargé pendant le redémarrage de la console. Les empreintes des données, des clés,
des réglages et de la politique de sauvegarde ont été conservées. Le paquet vocal
et l’APK Android publiés restent identiques.

Preuves : `frozen-validation.json`, `publication.json`, `production.json`,
`codex-download.json`, `avant-livraison.json`, `sauvegarde-avant.json` et les captures
sous `toolchain/test-results/ui/*/codex-integration/`. Les fichiers précédents sont
conservés dans `previous/` pour un retour.
