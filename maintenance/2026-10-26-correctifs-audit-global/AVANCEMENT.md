# Application des correctifs de l’audit global

Demande : appliquer les corrections et améliorations des 17 constats. Le [rapport des corrections](README.md) décrit les changements, preuves et limites.

| Constats | Résultat |
|---|---|
| F01–F02 | Service mémoire canonique, révisions, récupération du brouillon ; annulation/oubli hors quota, journal borné et idempotence compatible. Régressions métier et UI validées. |
| F03–F05 | Six profils vérifiés ; 217 versions Python analysées sans avis OSV restant ; npm sans vulnérabilité signalée. Go 1.27.3 reconstruit ; aucun avis sur les fonctions appelées dans l’analyse source Windows. Constructeur isolé et Strata sans héritage des paquets Codex. |
| F06–F08 | Six domaines Workspace, adaptateurs HTTP séparés, paquet partagé explicite et contrôlé dans l’exécutable ; adaptations Android nommées et capacités de plateforme. |
| F09–F11 | Schéma 2 et sauvegardes connues ; historiques et caches conservés ; runtime privé prioritaire et prérequis explicites ; négations et citations filtrées. |
| F12–F13 | Requêtes par lots, index et mesures p50/p95 ; diagnostics bornés sans contenu privé. Tests de confidentialité et de croissance des requêtes validés. |
| F14–F15 | Manifestes par composant et d’ensemble ; reconstruction depuis le paquet serveur et restauration fictive réussies dans un environnement neuf. Validation agrégée avec échecs initiaux et reprises nominatives. |
| F16–F17 | Protocole vocal commun, alias Phonon, compatibilité documentée, index courant et deux outils ponctuels archivés. |

## Résultats de validation

- Suite serveur complète : 579 tests, un initialement ignoré et deux échecs initiaux. Le contrôle ignoré a ensuite été exécuté avec succès sur le nouvel exécutable. Les deux contrôles concernés passent après correction ; leurs journaux de reprise sont référencés dans le bilan.
- 25 contrôles supplémentaires des adaptateurs HTTP et deux contrôles natifs Hermes réussis.
- Windows : 89 tests Python ; voix : 41 ; Android : 17 ; maintenance : 4. Quinze suites UI partagées réussies.
- Exécutable Windows : paquet gelé, chiffrement, ressources et pont embarqué validés. Une version personnalisée est exécutée dans une distribution de test isolée.
- Pack vocal : signature, inventaire de tous les fichiers et démarrage du worker construit vérifiés. Aucun microphone ouvert.
- Reconstruction : installation depuis le verrou public dans un environnement neuf, imports sans répertoire client, sauvegarde/restauration fictive et contrôle du schéma 2.
- Neuf fichiers modifiés avant cette intervention conservés à l’identique par empreinte. Modifications concomitantes de résidence RAM des modèles conservées.

Preuve consolidée : `validation-final/validation.json`. La publication et l’état réellement activé sont consignés séparément dans `publication.json` et `production.json` lorsqu’ils sont disponibles. Les limites matérielles et de sécurité restent détaillées dans le rapport.
