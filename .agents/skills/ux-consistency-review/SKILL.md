---
name: ux-consistency-review
description: Vérifier la cohérence de plusieurs écrans ou d'un changement transversal Fred, y compris entre le client Windows, Android et les conventions de la console.
---

# Cohérence des écrans

Choisir un écran existant comparable comme référence. Lire les composants partagés,
les variables de style et les parcours voisins avant de proposer une variante.
Comparer seulement les surfaces touchées ; ne pas uniformiser des publics différents.

Vérifier terminologie métier, noms et comportement des boutons, navigation, modales,
notifications, icônes, dimensions, espacements, tableaux, formulaires (normal,
invalide, désactivé, chargement), raccourcis clavier et organisation des fonctions
avancées. Une action identique doit porter le même nom et produire un retour cohérent.

Pour Fred, contrôler l'effet d'une modification des sources `client-qwen` sur Android
et ses adaptations `client-android/mobile-ui`. Préférer un composant commun à deux
copies presque identiques. Ne pas éditer les assets Android générés directement :
suivre `client-android/scripts/Prepare-Assets.py` et les procédures du projet si une
génération est nécessaire dans la tâche. La présente installation n'en exige aucune.

Rendre les écarts avec emplacement, référence utilisée, impact et proposition.
Réutiliser l'existant quand il convient ; ne pas imposer une refonte pour une petite
différence. Tester les parcours partagés si la modification les affecte. Appliquer
`ux-writing-cleaner` aux termes modifiés et `ux-visual-audit` aux changements visuels
importants, sans lancer un audit global pour une retouche isolée.
