# Historique séparé du Correcteur — 23 octobre 2026

La liste de gauche contient uniquement les corrections et reformulations sur la
page Correcteur. Les conversations ordinaires restent dans leur propre liste,
y compris les discussions des projets. Les anciens résultats sont reconnus par
leur titre et leur instruction d'origine ; aucun enregistrement n'est supprimé
et le format d'historique reste compatible avec les clients installés.

Un clic sur un résultat recharge son texte d'origine et sa réponse dans le
Correcteur, avec un avertissement si elle est partielle. Les recherches et filtres
d'archives sont mémorisés séparément pour les deux listes pendant la session.
« Nouveau texte » ouvre un formulaire vide sans créer de conversation ;
« Nouvelle conversation » conserve son comportement habituel. Le retour au chat
retrouve une conversation ordinaire et son brouillon. La suppression d'un chat
sélectionne une autre conversation, même si une correction est plus récente.

## Vérification

- `test_direct_corrector_ui.cjs` : historique mélangé et ancien, listes de projets,
  réouverture au clavier, texte et résultat, brouillons, recherches et archives
  distincts, bouton de création, suppression du chat courant, rechargement,
  annulation et réponse partielle, sur les interfaces Windows et Android.
- `test_model_selector_ui.cjs` : navigation explicite vers Conversations avant de
  sélectionner un chat depuis le Correcteur, selon le nouveau parcours.
- `npm --prefix client-qwen test` : six suites partagées puis contrôle UX.
- `maintenance/check_sources.py` et `Prepare-Assets.py --check`.
- `verify.py` : démarrage de l'EXE construit, empreintes des sources embarquées et
  16 tests isolés de profil, installation, signature, mise à jour et retour arrière.

Les captures `windows-*.png` et `android-*.png` proviennent de données fictives
dans Chrome. Elles ne constituent pas un test sur téléphone physique.

## Livraison

Client Windows 3.5.39. `activate.py` publie le binaire vérifié et signé après
contrôle de la sauvegarde chiffrée et de l'absence de génération en cours.
`production.json` constate le résultat, les processus Qwen, les clés, les données,
la programmation des sauvegardes et la voix Tiphaine préservés. La distribution
précédente est conservée dans le dossier de préparation pour retour arrière.

Les ressources Android partagées sont régénérées et testées. Cette livraison ne
publie pas de nouvel APK ; le correctif sera inclus dans sa prochaine construction.
