---
name: ux-visual-audit
description: Auditer une interface réelle avec Playwright MCP pour une nouvelle page, une refonte, une modification visuelle importante ou une demande explicite d'audit UX complet.
---

# Audit visuel et interactions

1. Lire `maintenance/ux-ui/README.md`, identifier les parcours concernés et utiliser
   le serveur de test ou les fixtures existantes. Vérifier l'URL et les données.
   Tester avec des données fictives ; aucune écriture réelle pour valider un parcours.
2. Ouvrir l'application avec les outils `playwright` MCP. S'ils ne sont pas exposés,
   vérifier `codex mcp get playwright` et le redémarrage nécessaire. Le test
   `node maintenance/ux-ui/playwright_smoke.cjs` vérifie séparément le transport et
   une fixture ; il ne prouve pas que l'application a été auditée.
3. Inspecter l'arbre accessible et réaliser les actions principales : navigation,
   formulaires, boutons et menus, clavier seul, ordre et restauration du focus,
   fermeture des modales et annonces des erreurs. Vérifier chargement, vide, succès
   et erreur avec les fixtures disponibles ; déclarer les états non reproduits.
4. Capturer les écrans pertinents : typiquement bureau 1440×900, téléphone 390×844,
   tablette 768×1024, et thèmes supportés. Adapter aux appareils cibles et au zoom.
   Lire réellement les captures ; l'arbre accessible ne remplace pas l'examen visuel.
5. Vérifier surcharge de texte, hiérarchie, lisibilité, alignements, débordements,
   contraste, accessibilité et retour des actions. Appliquer `ux-writing-cleaner`,
   `ux-consistency-review` et `web-design-guidelines` selon les constats.
6. Pour une modification de page autorisée, corriger les défauts de cette modification
   et rejouer les scénarios et captures concernés. Pour « audit UX complet », parcourir
   les écrans accessibles, proposer les corrections et réaliser celles demandées.

Rapport : parcours/URL, environnement/fixtures, résolutions, tests réellement joués,
capture ou fichier:ligne, symptôme, impact et correction proposée. Classer P0 (action
critique impossible/risque de perte de données), P1 (ergonomie/accessibilité majeure),
P2 (texte/cohérence/hiérarchie), P3 (finition). Distinguer constat et hypothèse.

Ne pas déclarer d'audit visuel sans accès réel à l'application et examen des captures.
Ne pas annoncer un état, écran ou appareil physique non testé. Si MCP est indisponible,
utiliser les tests Playwright existants quand possible et expliciter la différence.
Conserver les preuves sans secrets ni données privées ; ne pas publier les captures
d'un espace authentifié. Nettoyer uniquement les processus/fixtures de cet audit.
