# Corrections UX — 22 octobre 2026

Les corrections des 20 constats du [rapport initial](58_UX_AUDIT_20261022.md)
sont appliquées. Les modules métier, les versions de notes, les propositions,
les validations humaines et les données actives sont conservés. Aucune purge,
affectation, publication ou capture audio réelle n’a été effectuée pendant la
recette. Aucun commit ni push.

## Corrections et preuves

Les chemins de captures et journaux ci-dessous sont relatifs au dossier privé
`logs/ux-quality/fixes-20261022/`. Ces fichiers peuvent contenir des informations
professionnelles et ne doivent pas être publiés.

| Constat | Correction appliquée | Vérification |
|---|---|---|
| UX01 · P0 | Confirmation commune avant toute suppression d’un mail, y compris bouton direct, destination et dépôt. Nombre de mails, connaissances associées, original externe conservé, sauvegarde technique et absence d’annulation immédiate explicités. Alternative Divers conservée. | Tests des trois chemins avec annulation : aucun appel de suppression. Dialogue natif observé ; requête acceptée interceptée, aucune donnée supprimée. |
| UX02 · P1 | La navigation se charge même si le portefeuille échoue. Les vues dépendantes présentent l’erreur et Réessayer. Les mails restent lisibles avec les projets déjà connus et un avertissement d’actualisation. | Panne 503 simulée sur le portefeuille seul ; `mail-portfolio-unavailable.png`. |
| UX03 · P1 | Libellés associés aux champs de création projet, dossier réseau, exigence/citation/page CDC, pointage, référence et désignation. Recherche CDC nommée pour les technologies d’assistance. | Tests frontend, inspection des noms accessibles et revue des formulaires. Pas de soumission métier réelle. |
| UX04 · P1 | Informations du projet : date, version et consultation de la source dans l’inspecteur existant. Le backend fournit les citations autorisées ; les sources déplacées ou écartées restent exclues. Absence de preuve annoncée explicitement. | Test backend de provenance et d’isolation ; ouverture d’une source puis Échap ; `project-knowledge.png`. |
| UX05 · P2 | Séances et comptes rendus ont chacun leur titre et compteur ; une liste de comptes rendus vide n’annonce plus l’absence de toute réunion. | Tests frontend et bibliothèque des Réunions. |
| UX06 · P2 | Même navigation latérale et même seuil mobile pour les rubriques, y compris Sources et Réunions. Les exceptions qui réduisaient les libellés sont retirées. | Largeur de 228 px observée sur Accueil, Sources et Réunions à 1440 px. |
| UX07 · P2 | Requête, filtres et pagination des listes concernées sont synchronisés avec leur URL ; sous-vue des réglages conservée. Chaque vue ne modifie que ses propres paramètres. | Rechargement réel de Recherche, Sources et Apparence ; tests de reprise d’Informations et de pagination Réunions. |
| UX08 · P2 | Ctrl K et le clic sur Rechercher ouvrent tous deux la recherche complète. La palette est conservée sous une commande distincte « Accès rapide aux rubriques ». | Raccourci réel, tests de navigation et de clavier. |
| UX09 · P2 | La progression CDC représente le nombre d’éléments traités sur le total, avec un élément progress accessible et une piste neutre. | Valeur 1, maximum 157 observés ; `cdc-review.png`, `cdc-mobile-final.png`. |
| UX10 · P2 | Les points CDC sont une liste filtrable par texte/type, paginée par 20, avec accès à l’élément et à sa preuve. Le compteur utilise la même liste dédupliquée, sans retirer de point métier. | 20 lignes affichées sur 156 points distincts ; `cdc-points-final.png`. |
| UX11 · P2 | Vocabulaire « Compte rendu » harmonisé. Compte rendu et Transcription occupent le panneau principal, les brouillons de notes restent montés et conservés. « Choisir un projet » ouvre la préparation et donne le focus au choix, sans affectation automatique. | Tests de conservation/publication ; interaction réelle ; `report-1440.png`, `report-mobile-closed.png`. |
| UX12 · P2 | Anciennes analyses regroupées dans « Historique des analyses » fermé avec compteur et statuts français. Aucune version supprimée. | Tests frontend ; `history-closed.png`. |
| UX13 · P2 | Filtres CDC repliés sur petit écran. Studio : panneau demandé prioritaire, détails de l’audio terminé regroupés. Les commandes d’enregistrement/récupération actives et les avertissements nécessaires restent accessibles. | Captures 390 × 844 et repli 720 × 450 ; aucune largeur de page excessive observée sur les parcours contrôlés. |
| UX14 · P2 | État sans planning et charge non estimée explicités ; achats, pointage et nomenclature vides présentent une action ou une explication utile. Les tables vides concernées sont masquées. | Portefeuille et projet représentatif ; tests frontend. Les zéros réellement utiles dans d’autres écrans sont conservés. |
| UX15 · P2 | Types métier traduits, « Déclasser » pour une information conservée, « Supprimer d’Agent » pour une purge. Actions, confirmations et messages de résultat concordent. | Tests des libellés et revue des textes. |
| UX16 · P2 | Une proposition de classement inférieure à 75 % est présentée comme incertaine avec invitation à choisir une destination ou Divers. Le score reste une aide ; les validations humaines sont conservées. | Mail à faible score observé ; `mail-dark.png`. |
| UX17 · P2 | L’indexation devient un bouton distinct avec état ouvert/fermé et panneau associé ; Liste et Relations restent les deux onglets de consultation. | URL et état des relations repris après rechargement ; `sources.png`. |
| UX18 · P3 | Suppression des variantes à libellés minuscules et rehaussement des métadonnées utiles de la navigation, badges et CDC. | Lecture desktop/mobile et repli à 720 px. Le zoom natif navigateur à 200 % et un lecteur d’écran réel restent à qualifier. |
| UX19 · P3 | Images mail distantes bloquées remplacées par un emplacement neutre explicite. Action d’affichage au style existant ; HTML MIME et images CID conservés. Activation distante toujours explicite. | Six emplacements neutres observés dans le mail HTML ; thème sombre ; `mail-dark.png`. Images externes non activées. |
| UX20 · P3 | Pagination retirée lorsqu’inutile, table de livrables vide masquée, second message de sélection des notes supprimé quand aucune note n’existe. Filtres et création restent disponibles. | Tests de pagination et des documents ; états vides contrôlés. |

## Recette et limites

- Frontend : 1 000 tests réussis dans 95 fichiers après les corrections de
  reprise d’URL et de pagination de recherche (`frontend-release.log`). Un
  passage intermédiaire avait dépassé le délai d’attente du chargement d’une
  source sous forte concurrence ; le passage complet avec quatre workers est
  réussi. Dernier passage sur les sources livrées : 1 000 réussites,
  `frontend-final-qa.log`, commande `npm --prefix web test -- --maxWorkers=4`.
  Contrôles ciblés Recherche/CDC après revue sémantique : 15 tests réussis dans
  `ux-last-targeted.log`.
- Backend ciblé : 26 tests réussis (`test_workspace.py`,
  `test_knowledge_defaults.py`), notamment les citations autorisées du projet.
- Ruff : `ruff check app backend/app tests` réussi.
- Contrôle UX : 121 fichiers, 63 avertissements heuristiques à relire ; ils ne
  constituent pas 63 défauts établis et n’ont pas été supprimés automatiquement.
  Les alertes de longueur sur les précautions métier et les noms portés par
  des composants enfants sont conservées ; la quantité de nomenclature est
  nommée explicitement. Le contrôle ne certifie pas tous les écrans hérités.
- Build TypeScript/Vite réussi ; avertissement conservé sur la taille du bundle
  principal (environ 1,10 Mo non compressé).
- Suite backend globale : **2 934 réussites, 1 test ignoré et 54 sous-tests
  réussis**, code de sortie 0, en 57 min 12 s (`pytest-full-short.log`).
  Commande : `python -m pytest tests/ -q --basetemp C:/Agent/logs/uxtfull`,
  avec TEMP/TMP courts. Deux avertissements conservés : dépréciation de
  TestClient/httpx et clé source nulle dans un test de triage.
  Une première exécution avait été interrompue après reproduction d’un échec de
  chemin temporaire trop long sous Windows. Les 12 tests audio de ce premier
  fichier passent avec un chemin court. Cette tentative ne constitue pas une
  réussite globale ; le résultat ci-dessus est celui de la relance complète.

Les résultats structurés et les empreintes des sources vérifiées sont conservés
dans `verification.json` et `verified-source-hashes.json`.

Les vérifications Playwright utilisent une instance temporaire sur 8011 avec
copies SQLite, fichiers EML de recette, lifespan désactivé et écritures API
bloquées. Les actions sensibles sont testées par interception ou tests unitaires.
Les captures portent sur des parcours représentatifs, pas toutes les données,
habilitations ou combinaisons de formulaires. Pas de test utilisateur, de
certification WCAG, de cycle de suppression/restauration réel, de qualification
microphone, transcription ou IA nouvelle.

## Livraison locale

L’architecture reste mono-serveur Agent sur 8001. XPilot sur 8000 reste intact.
Le serveur normal était arrêté avant l’audit ; son arrêt est conservé. Le port
8011 a servi seulement à la recette temporaire. L’instance a été arrêtée et
le navigateur de recette fermé ; 8001 et 8011 sont vérifiés sans écoute à cette
clôture visuelle.

Les sources d’avant correction sont conservées sous `before/` avec empreintes.
Le bundle est construit dans un dossier de recette, puis copié dans `web/dist`
sans supprimer les anciens assets. L’index précédent et ses assets référencés
sont sauvegardés sous `deployment-before/`. Les empreintes de livraison sont
consignées dans `deployment.json`. Le prochain démarrage normal d’Agent utilisera
le bundle corrigé et le backend de provenance ; aucun changement de schéma.
