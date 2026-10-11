# Preuves de la console — lots 0 à 4

Validation réalisée le 10 octobre 2026 avec Chrome sans interface, à partir de la console HTML/CSS/JavaScript réellement rendue. Les captures ont été relues. Aucun compte, document ou réglage de production n’a été utilisé ou modifié par ces tests.

| Cycle | Résultat | Rapport |
|---|---:|---|
| API synthétique, interactions réelles du navigateur | 16 scénarios réussis, aucune exception JavaScript | [maintenance-ui.json](maintenance-ui.json) |
| Vrai Controller, stockage et identités jetables | 16 scénarios réussis, aucune exception JavaScript | [maintenance-backend-ui.json](maintenance-backend-ui.json) |

Le second cycle utilise les vraies routes d’administration, le chiffrement des sauvegardes, Windows DPAPI, les profils Android, le catalogue, la copie secondaire et la restauration. Seules les métriques matérielles sont fictives. Le Controller est créé avec `include_legacy=False`, dans un dossier temporaire propre, avec une configuration de modèle entièrement synthétique préparée avant son initialisation. Aucun modèle, service WireGuard ni serveur de production n’est lancé ou arrêté. La copie secondaire est un second dossier de test ; elle ne valide pas un NAS physique.

La preuve de restauration compare les empreintes des réglages, de l’historique et de l’original UTF-8 avant et après restauration. Les réglages et l’historique ont été réellement modifiés entre les deux étapes ; un document supplémentaire a été ajouté, puis retiré par la restauration. Les trois empreintes finales sont identiques aux originales, la génération de synchronisation a changé et l’accès distant reste désactivé. Voir `checksumProof` dans le rapport réel.

## Scénarios avec le vrai backend

1. Programmation, rétention et protection de la phrase par DPAPI.
2. Création d’une archive chiffrée et copie secondaire vérifiée.
3. Refus d’une phrase incorrecte avant toute restauration.
4. Aperçu déchiffré, contenu, empreinte et effets de la restauration.
5. Restauration guidée complète et comparaison des données.
6. Création directe d’un profil Android, sans préparation d’EXE.
7. Téléchargement privé du profil Android avec autorisation dans l’en-tête.
8. Modification du propriétaire et de la date d’expiration.
9. Suspension et réactivation ; profil suspendu indisponible.
10. Révocation conservant les autorisations et documents de l’autre appareil.
11. Archivage et consultation de la fiche archivée.
12. Remplacement par une nouvelle identité ; historique et original de l’ancien accès conservés.
13. Ouverture directe de la rubrique Appareils après rechargement.
14. Affichage sur téléphone sans débordement horizontal.
15. Panne de stockage simulée dans le processus de test : retour refusé, accès bloqués, réparation puis nouvel essai de retour réussi.
16. Absence d’exception JavaScript.

Le défaut de stockage du scénario 15 est injecté uniquement dans le processus Python jetable, par son entrée standard. Aucune route de débogage n’est ajoutée au serveur livré.

## Scénarios complémentaires avec API synthétique

Navigation et catalogue ; conservation du brouillon pendant une actualisation ; programmation hebdomadaire ; suivi du travail asynchrone ; phrase incorrecte ; aperçu et effets ; confirmation périmée et nouvelle vérification ; inventaire ; création d’accès Android ; téléchargement avec token hors URL ; métadonnées et recherche par propriétaire ; suspension/réactivation ; remplacement ; révocation/archivage avec conservation ; rendu téléphone ; absence d’exception JavaScript.

## Captures du backend réel

- [Sauvegardes](01-backend-sauvegardes.png).
- [Aperçu de restauration](02-backend-restauration-apercu.png).
- [Restauration terminée](03-backend-restauration-terminee.png).
- [Appareil archivé](04-backend-appareil-archive.png).
- [Appareils sur ordinateur](05-backend-appareils-desktop.png).
- [Appareils sur téléphone](06-backend-appareils-telephone.png).
- [Sauvegardes sur téléphone](07-backend-sauvegardes-telephone.png).
- [Retour refusé tant que le stockage est défaillant](08-backend-retour-echec.png).
- [Retour réussi après réparation](09-backend-retour-reussi.png).

Les six autres PNG documentent le cycle synthétique, notamment le dialogue de restauration sur téléphone. [empreintes.json](empreintes.json) contient les empreintes SHA-256 des deux rapports et des quinze captures. Aucun fichier de profil personnel ou secret n’est copié dans ce dossier de preuves.

## Reproduction

Depuis `D:\Serveur IA`, avec Node et Python déjà installés :

```powershell
& 'C:\Users\karen\AppData\Local\hermes\node\node.exe' lanceur/web/tests/maintenance_ui.mjs
& 'C:\Users\karen\AppData\Local\hermes\node\node.exe' lanceur/web/tests/maintenance_backend_ui.mjs
```

Le second runner démarre `maintenance_backend_fixture.py`, crée son stockage jetable, pilote Chrome et ferme ses propres processus à la fin. Les résultats bruts vont dans `toolchain/maintenance-ui-evidence` et `toolchain/maintenance-backend-evidence` ; les fichiers de ce dossier sont une sélection des derniers cycles réussis.
