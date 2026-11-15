# Contexte et statut — Agent 0.4.0

État documentaire réconcilié le **21 octobre 2026**, après livraison du commit
`4b749c65f4ac47242c6312077adcbf0a9aedcea2` sur `origin/main`.
Ce document distingue le code livré, les qualifications historiques et les
contrôles de livraison. Il ne constitue pas une vérification en direct du serveur,
des modèles chargés ou du corpus actuel. Les comptes rendus datés restent
historiques ; les compléments les plus récents prévalent dans leur portée.

## Objet et gouvernance

Le projet canonique est `C:/Agent`. Un dépôt, un serveur Agent sur **8001**,
Brain et ERP avec leurs bases canoniques et leurs liaisons explicites.
XPilot sur **8000** reste externe et préservé ; aucun serveur sur 8002.
Les modules MiniPilot Projets, CDC, CDC & BE, Revues, Atelier et Import Sage
restent conservés. Les règles de `AGENTS.md` s'appliquent : suppression sur accord
explicite, sauvegarde avant suppression de lignes, commit et push sur demande.
Les décisions humaines et les données métier ne sont pas remplacées par les
propositions de l'assistant.

## Mémoire, recherche et modèles

SQLite conserve les connaissances, décisions et provenances canoniques.
L'index EG2 est une dérivation reconstructible. La génération LLM reste distincte
de l'indexation. La recherche unifiée combine rappel sémantique, termes normalisés
et références exactes, avec filtrage des droits et du périmètre projet.

La livraison comprend aussi la bibliothèque Sources, l'extraction de documents,
les pages PDF, l'OCR et les chemins d'indexation/recherche multimodale. Leurs
prérequis et preuves sont détaillés dans les documents de domaine ; leur présence
dans le code ne garantit pas leur disponibilité sur chaque poste.
L'indexation des projets dispose d'un suivi dédié.

Le routage propose le moteur réseau et le secours local configurés. La préparation
distingue capture, transcription, encodeur et génération. Un modèle téléchargé,
un modèle chargé et une génération réussie sont trois observations différentes.
Les adresses, modèles, compteurs et durées de la migration du 11 octobre sont des
mesures historiques, décrites dans `docs/20_EG2_ENGINE.md` et
`docs/36_EMBEDDING_CHANNEL.md` ; ils ne sont pas des inventaires actuels.
Le chargement des moteurs et l'état du corpus n'ont pas été revérifiés le 21 octobre.

## Fonctions présentes dans la livraison

- Réunions : Studio, séances persistantes, rattachement au projet, capture native
  ou navigateur, transcription, édition du transcript, notes, versions,
  publication, pièces jointes et exports. Le calendrier de séance et l'assistant
  contextualisé disposent de leurs routes et interfaces.
- Assistant : réponses avec preuves, discussion et questions en direct,
  retours humains, suivi de fraîcheur, statistiques et tokens réellement fournis
  par le moteur. Les absences de mesure ne sont pas converties en estimations.
- Mails : classement assisté, décisions humaines conservées, liaison Thunderbird
  et affichage du HTML MIME original avec images CID ; les images distantes
  demandent une action explicite.
- Navigation : accès aux projets, Sources, réunions, notes et réglages ; suivi
  des activités et téléchargements asynchrones.
- Exploitation : superviseur persistant, sauvegardes, reprises et diagnostics.
  Un processus vivant ne prouve pas le service rendu : santé HTTP, moteurs et
  résultats métier se vérifient séparément.

Le code livré centralise aussi des capacités élargies dans
`app/operational_limits.py` (imports, capture et délais d'inférence).
Ces plafonds logiciels ne prouvent ni une capture continue de douze heures,
ni la capacité réelle du matériel. Les essais antérieurs avec d'autres budgets
restent historiques.

## Qualification et limites connues

La consolidation documentaire du 16 octobre clôt **9 lots sur 13,
16 fonctions sur 25 et 12 recettes sur 17**. L02/L03/L11/L12 restent ouverts.
Les recettes T01/T02/T03/T04/T16 restent à clore dans cette consolidation.
Voir `docs/40_FORESIGHT_ACCEPTANCE.md` et `docs/52_FORESIGHT_RECIPES.md`.

T11 est documenté réussi sous coupure réseau observée pour la chaîne
transcription/recherche/génération sur fichiers fictifs, avec reprise et retour
réseau. Cette preuve ne qualifie ni microphone/casque réel, ni navigation pendant
capture, ni précision du direct industriel, ni latence DOM. Le CR complet medium
CPU est documenté actif avec relecture ; le direct medium CPU reste en essai.
Les preuves locales citées dans les documents ne sont pas toutes versionnées.
Aucune nouvelle recette matérielle ou hors ligne n'a été menée pour cette mise à jour.

Les qualifications backend antérieures (dont 2 680 réussites et 1 test ignoré)
et frontend antérieures restent attachées à leurs versions et périmètres.
Elles ne constituent pas une suite globale réussie sur le commit du 21 octobre.
Pour cette livraison :

- Ruff `app backend/app tests` : réussi avant les dernières modifications
  concurrentes ; aucune certification globale après celles-ci.
- TypeScript et Vite : compilation réussie, avec avertissement de taille du bundle.
- Vitest global : 968 tests réussis, 1 échec sur 969 ; l'attente du délai de reprise
  de transcription a ensuite été actualisée, puis les 19 tests du fichier
  `meetingSessions.test.ts` ont réussi. Pas de nouveau global après ce delta.
- Pytest global : première collecte bloquée par les permissions ; relance avec
  accès nécessaires, puis interruption après une progression affichée de 2 %.
  Aucun résultat global final validé pour cette livraison.

Une modification locale de `tests/test_relaxed_limits.py` restait hors du commit
livré lors du contrôle du 21 octobre. Cette mise à jour documentaire n'affirme pas
que l'arbre de travail est propre ou que les derniers changements sont poussés.

Les chemins SMB réels et les sorties documentaires restent à qualifier dans leur
environnement. CAO/3D, intégration XPilot2 complète, authentification individuelle
multi-utilisateur et déploiement réseau ne sont pas attestés opérationnels ici.
Les capacités décrites dans Foresight complètent le périmètre historique du
7 octobre ; ses exclusions anciennes de capture, OCR et calendrier ne décrivent
plus à elles seules le code livré.

## Frontières des garanties

`validated` désigne une information retenue dans la base canonique. Le champ
`validation_mode` distingue la décision humaine du mode `default` avec
`validated_by=auto-default` ; ce dernier ne vaut pas confirmation humaine.
Les passages `evidence` restent des preuves proposées, et le rappel EG2 ne valide
aucune connaissance. Le déclassement retire les vérités actives ; le filtre des
preuves portant leur valeur exacte ne garantit pas l'exclusion de toute paraphrase.

Les labels d'acteur ne sont pas une authentification individuelle. Un brouillon
de transfert BE n'est pas un livrable final. Deux commits SQLite ne constituent
pas une transaction distribuée. Les backups globaux se font hors ligne et leur
restauration se vérifie sur une copie. DPAPI dépend du compte Windows. Les données
historiques invalides ne sont pas purgées automatiquement. La licence du dépôt
reste une décision de son propriétaire.

## Ordre de lecture

1. [README](README.md) : vue d'ensemble et architecture mono-serveur.
2. [Exploitation backend](README_BACKEND.md) : réglages, lancement, reprise et tests.
3. [Architecture générale](docs/01_GLOBAL_ARCHITECTURE.md) et
   [moteur EG2](docs/20_EG2_ENGINE.md) : sources canoniques, index et génération.
4. [Analyse projet](docs/35_PROJECT_KNOWLEDGE_ANALYSIS.md) : preuves, lots et limites.
5. [Manifest](manifest.json) : inventaire des documents et services.
