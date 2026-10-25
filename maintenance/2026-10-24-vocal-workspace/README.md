# Conversations vocales et ondes — 24 octobre 2026

Livraison Windows 3.5.49 ; Android 1.0.21, code 22.

La page Vocal permet de créer, retrouver, renommer, archiver, restaurer et
supprimer une conversation. Une suppression demande confirmation et peut être
annulée. L'historique partagé existant reste la source des conversations, sans
duplication ni modification du format enregistré. Choisir une conversation dans
l'historique depuis Vocal conserve cette page. Les brouillons du chat sont gardés.

Les réglages sont placés dans un panneau modal avec fermeture visible, retour du
focus et bouton Raccrocher pendant un appel. L'option « Interrompre Kiara en
parlant » reste directement accessible sous les commandes de conversation.
Low/Phonon, Max, le choix du GPU et les commandes de gestion des fichiers Max sont
conservés.

Deux surfaces d'ondes projetées en 3D remplacent le graphique par défaut : vert
pour le micro et bleu pour la voix de Kiara. Le niveau du micro vient du RMS des
trames natives ; sa date évite d'afficher un ancien signal. Le niveau de Kiara est
mesuré sur le son joué, après réglage du volume. Les oscillations sont une
visualisation de l'intensité, sans prétendre reproduire la forme PCM du micro.
Une réflexion ou un texte reçu ne produit pas de fausse activité sonore.
Les anciennes animations restent disponibles. Le choix ultérieur, la pause et les
mouvements réduits sont conservés. Le dessin est limité à environ 30 images/s,
avec une définition et un maillage réduits sur Android ; le silence évite les
redessins. Aucune bibliothèque graphique ou ressource lourde n'est ajoutée.

## Vérifications

- 12 suites UI partagées passent, avec conservation des scénarios Low, Max,
  interruptions, GPU, dictée, chat et correcteur : `ui-tests.log`.
- Nouvelle suite Windows et Android : `workspace-tests.log`. Elle couvre aussi
  les erreurs d'enregistrement, annuler une suppression, les brouillons, le
  focus du panneau et de l'historique mobile, le silence, un signal micro périmé,
  le micro coupé, les deux sources simultanées, le volume zéro, les mouvements
  réduits et la migration du choix d'animation.
- 82 tests Python du client et 32 tests du vocal passent. Le worker est vérifié
  sur ses trames et leurs dates, y compris à la coupure/reprise du micro.
- Construction Android signée : 13 tests de livraison et compilation Java.
- `maintenance/check_sources.py` passe ; `npm --prefix client-qwen run ux:check`
  retourne 9 avertissements préexistants sur de longs textes de la console serveur,
  relus et sans rapport avec cette page. Aucun contenu n'a été supprimé.

## Revue visuelle ciblée

Inspection avec Playwright MCP du panneau de réglages et du menu de conversation,
puis lecture des captures Windows 1440 × 1000 et 2551 × 1390 et Android simulé
390 × 844 et 768 × 1024, en clair et sombre. Preuves dans `ui/` :

- `audit-desktop-settings.png`, `audit-actions.png`, `audit-phone-settings.png` ;
- `windows-microphone.png`, `windows-kiara.png`, `windows-2551-dark.png` ;
- `android-microphone.png`, `android-kiara.png`, `android-settings.png`,
  `android-390-dark.png`, `android-768-dark.png`.

Aucun P0/P1 observé dans ce périmètre. Un P2 a été corrigé : le message de
suppression restait visible après restauration ou changement de conversation.
Les contrôles importants sont visibles, les colonnes ne débordent pas et le
panneau garde sa fermeture accessible. Les couleurs sont également identifiées
par des libellés ; les états de conversation restent écrits et annoncés.

Limites : signaux et serveur de test déterministes, sans microphone physique ni
téléphone connecté ; aucune validation acoustique en conditions réelles ni
déclaration de conformité WCAG complète. La revue visuelle est limitée au parcours
Vocal modifié ; les autres parcours sont couverts par leurs contrôles existants.

Les publications signées et les empreintes sont enregistrées dans
`publication.json`, `production.json` et `android-publication.json`. La livraison
préserve les identités des clients, les données, les processus Qwen et la voix
serveur désactivée à la demande précédente de l'utilisateur.
