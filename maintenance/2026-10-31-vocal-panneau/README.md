# Échanges écrits en panneau dans Vocal

Le bouton « Ouvrir le chat » de l’en-tête est retiré. La navigation
« Conversations » reste disponible dans le menu principal, y compris pendant
un appel. Les échanges écrits sont déplacés à droite de l’animation dans un
panneau repliable, fermé au départ. Sous 900 pixels, ils prennent place sous
l’animation pour conserver une largeur de lecture suffisante.

Le composant natif `details/summary` conserve l’ouverture au clic, Entrée et
Espace. Échap referme le panneau et restaure le focus sur son résumé. Les échanges,
leur mise à jour pendant l’appel, le message vide et l’accès aux sources sont
conservés. Le panneau dispose d’un défilement indépendant pour les textes longs.

Sources partagées Windows/Android : `client-qwen/conversation.js` et `ui.css`.
Les assets Android ont été régénérés avec `Prepare-Assets.py` puis vérifiés.
Les tests qui utilisaient le bouton retiré passent désormais par la navigation.

## Vérification ciblée

Fixture isolée `test_conversation_ui.cjs --preview`, données fictives Orion,
sans microphone, historique personnel ou serveur de production. Inspection
avec Playwright MCP, captures ouvertes et examinées :

- `vocal-panneau-bureau.png` : 1440 × 900, thème clair, panneau vide à droite.
- `vocal-panneau-rempli.png` : 1440 × 900, thème sombre, quatre échanges écrits.
- `vocal-panneau-mobile.png` : 390 × 844, thème sombre, échanges sous l’animation.
- `vocal-panneau-tablette.png` : 768 × 1024, thème sombre, position sous l’animation.

Ouverture, fermeture par Échap et restauration du focus vérifiées avec MCP.
Largeur intermédiaire de 1024 pixels contrôlée : animation et panneau distincts,
sans débordement horizontal. Le compteur console de la fixture inclut une
requête favicon non authentifiée (401), sans erreur JavaScript de l’interface.

La suite `test_voice_workspace_ui.cjs` passe sur Windows et Android simulés :
absence du bouton retiré, panneau fermé au départ, ouverture au clavier,
état vide, position latérale ou empilée, focus après Échap, texte réel des
échanges, création/renommage/historique, appel et commandes vocales.

Le contrôle UX n’ajoute aucun avertissement sur cette modification ; les trois
avertissements existants concernent les textes longs de la console serveur.
La commande `npm --prefix client-qwen test` termine avec **16 suites UI réussies**.
Le contrôle de syntaxe des sources et la vérification des assets Android passent.
Cette vérification ne constitue pas une certification WCAG complète ni un
essai sur téléphone ou microphone physiques.

Les sources et assets sont modifiés ; aucun EXE ni APK installé n’est remplacé.
