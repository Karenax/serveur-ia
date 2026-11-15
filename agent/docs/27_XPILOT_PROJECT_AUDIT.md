# Audit des fonctions projet XPilot → Agent

Date : **5 octobre 2026**. Statut : **audit et préparation, aucune reprise exécutée**.

## Conclusion

Agent dispose d'un socle utilisable, mais ses tâches, livrables, documents et revues
restent sensiblement plus simples que ceux d'XPilot. La reprise complète nécessite
des évolutions du modèle métier et des services, puis des écrans. Copier les menus
ne suffit pas. Les moteurs existants de CDC, de réunions, de mails et de mémoire
doivent être enrichis et raccordés, en conservant leurs données.

Le détail XPilot déclare **19 rubriques possibles**, dont **18 ordinaires** et
**Tubes** uniquement pour la famille `19 - T&P`. La navigation adaptative peut en
placer certaines dans **Plus** : elles font toutes partie de cet audit.

Le périmètre financier reste **volontairement exclu** : l'utilisateur a demandé
de supprimer le code financier dédié et de conserver toutes les données. Les
heures, charges, pointages, besoins techniques et informations fournisseurs
restent dans la reprise. Les écrans de prix, taux, marges, ventes et chiffrage ne
seront pas réintroduits sans nouvelle instruction explicite.

## Référentiel et méthode

- Source locale : `C:\Users\Frederic.LEFRANCOIS\Documents\ChatGPT\Xpilot`.
- XPilot : version **0.1.54**, commit `82d47dff8475d32ea18a99e9f81d6409b1c19643` ;
  arbre suivi propre lors de l'audit.
- Agent : commit `42eabda68ab277bdc8bbdfa2816fe36f20b0105f`, **arbre modifié** ;
  les empreintes des fichiers décrivent l'état réellement comparé, au-delà du commit.
- Lecture du code de navigation, composants, appels API, routes, services directs,
  règles métier et documentation. Pas de connexion à MariaDB, de modification
  d'XPilot, d'arrêt de service, de migration ou de copie de données.
- [Inventaire de preuves](27_XPILOT_PROJECT_INVENTORY.json) : **52 fichiers UI**,
  **29 fichiers de routes / 293 déclarations**, **34 services directement importés**,
  références de domaine et **22 fichiers Agent** ; chemins, lignes et SHA-256.
  Les fichiers de routes partagées incluent des opérations hors projet : 293
  n'est donc pas un nombre de fonctionnalités projet ni de fonctions manquantes.
- Audit **statique** : présence et raccordement dans les sources, sans recette
  complète de chaque parcours XPilot en production. Disponibilité des modèles,
  réseau, Office, moteurs IA et permissions à qualifier lors de chaque lot.

Les sources de vérité de l'audit sont les fichiers listés ci-dessous et dans
l'inventaire, pas une ancienne roadmap. Les suppressions exposées par XPilot
seront adaptées à la gouvernance d'Agent : sauvegarde, confirmation et préférence
pour l'archivage. Aucun nettoyage de données n'est inclus dans le plan.

## Lecture de la matrice

**Présent** = capacité métier déjà exposée par Agent, sans prétendre à une
équivalence intégrale. **Partiel** = base existante à enrichir. **Absent** = aucun
équivalent spécialisé trouvé. **Exclu** = décision financière conservée.
**À venir XPilot** = entrée annoncée mais désactivée dans le code source.
Les lots `L0` à `L9` sont détaillés dans le [plan de reprise](28_XPILOT_PROJECT_PLAN.md).

### 01 — Pilotage (`pilotage`)

Sources : `web/src/components/project-advanced/ProjectPilotage.tsx:33`,
`PilotInspector.tsx`, `ProjectAdvancedPanel.tsx`, routes `projects.py:432`.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Cockpit reliant projet, jalons, tâches et livrables | Partiel : tableau de synthèse | Construire les relations et une vue interactive, sans dupliquer la vérité ERP | L2, L4 |
| Recherche dans le cockpit, couches tâches/livrables, ajustement de vue | Absent | Recherche contextualisée, filtres, inspection, vue compacte | L4 |
| Masquage des jalons passés et inspection responsive | Absent | Navigation du cycle de vie, panneau clavier et petite largeur | L4 |
| Créer une tâche depuis un jalon, modifier tâche/date depuis inspecteur | Partiel : formulaires séparés | Mutations partagées et rafraîchissement immédiat de toutes les vues | L2, L4 |
| Alertes, retards, blocages, sujets qualité et Kaizen | Partiel : retards et actions Brain | Consolider les alertes structurées et destinations utiles | L4, L9 |
| Projets similaires, état du traitement, nouvelle tentative, liens vers projets/BOM | Absent | Recherche asynchrone avec provenance et invalidation des résultats périmés | L9 |

### 02 — Documents (`document-filling`)

Sources : `ProjectDocumentFillingPanel.tsx:125`, service `document_filling.py:385`,
routes `document_filling.py`, `web/src/runtime/tauriRuntime.ts`.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Résolution du dossier local/réseau et correspondance des racines | Partiel : liens et ouverture Windows | Gestion de racines autorisées et diagnostic d'accès | L5 |
| Détection des documents existants, recherche, filtres et sélection par lot | Partiel : liste de liens | Règles configurables de recherche, états trouvé/absent/ambigu | L5 |
| Remplissage de modèles, champs manquants et liens vers leurs fiches | Absent | Exploiter identité, client, CAF et agence ; aperçu des changements | L1, L5 |
| Offre LT simplifiée, TDAO, TDSP | Absent : remplissage ; liens déjà présents | Reprendre les seuls champs d'identification/documentation ; calcul financier exclu | L5 |
| CDC fabrication simple, notice, demande CE | Absent | Mappings de cellules/signets et qualification des trames | L5 |
| Satisfaction client produit et forfait | Absent | Deux trames distinctes et référencement du résultat | L5 |
| Sélection manuelle d'un fichier, liaison/déliaison, ouverture | Partiel | Validation du format et de l'appartenance au dossier projet | L5 |
| Progression, annulation, résultat par document, traitement des fichiers existants | Absent | Job durable ; écrasement explicite, sauvegarde préalable | L5 |

**Dépendance décisive :** le panneau XPilot nécessite son runtime desktop ; le
navigateur affiche « Application XPilot requise ». Agent est servi localement par
FastAPI : porter les opérations dans un service local borné, ou un adaptateur
Windows, après qualification DOCX/DOCM/XLSX/XLSM. Le navigateur seul n'offre pas
les mêmes accès au réseau. Ne pas incorporer toute l'application Tauri.

### 03 — CDC & BE (`cdc-analysis`)

Sources : `ProjectCdcAnalysisPanel.tsx:580`, `ProjectCdcBeTransferPanel.tsx:157`,
routes `cdc_analysis.py`, `cdc_be_transfer.py`, domaine et services CDC.

| Sous-menu / fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Sources : registre, révisions, upload, texte par page, lisibilité, relance extraction | Partiel : sources et pages déjà là | Extraction asynchrone et gestion explicite du remplacement/réextraction | L7 |
| Synthèse : sélection d'une révision d'analyse, génération, filtres type/état | Partiel : éléments, runs, revue | Révisions métier indépendantes des simples exécutions techniques | L7 |
| Synthèse : correction, ajout manuel, preuves et consultation de la page source | Présent en base ; parité partielle | Vérifier localisateurs, preuves multiples et concurrence | L7 |
| Contrôles : anomalies, soumission, approbation, gel | Partiel : contrôles et revue | Machine d'états et impossibilité de modifier une analyse gelée | L7 |
| Progression des lots et récupération du traitement actif | Partiel : jobs durables Agent | Unifier états, progression et reprise sans remplacer le worker existant | L7 |
| Retrait d'une synthèse sans supprimer ses sources, restrictions de dépendance | Absent comme révision métier | Préférer archivage ; suppression éventuelle confirmée et sauvegardée | L7 |
| Transfert BE / Demande : besoin, inclus/exclus, scénarios, implantation, utilités, réception, livrables, lancement | Partiel : sortie de transfert | Dossier éditable versionné lié à une analyse approuvée | L7 |
| Transfert BE / Réponse : architecture, technologies, hypothèses, variantes, exclusions, risques, heures, planning, capacité | Partiel : heures/exigences | Matrice réponse par exigence et position BE | L7 |
| Transfert BE / Revue : arbitrages et réserves | Partiel | Arbitrages persistants ; base financière de chiffrage exclue | L7 |
| Contrôles, approbation, génération DOCX/PDF, QA, émission et téléchargement | Partiel : transfert et livraisons versionnées | Séparer révision, génération et émission ; QA bloquante | L7 |

La phase **Revue** propre à Agent reste conservée. Maintenir les réglages IA du
Brain et les paramètres désactivant le raisonnement prévus par `AGENTS.md`.
L'OCR des PDF scannés n'est pas une capacité universelle déjà garantie par XPilot.

### 04 — Synthèse (`overview`)

Sources : `ProjectDetailPage.tsx:746`, `ProjectMacroOverview.tsx`,
`ProjectFinancialOverview.tsx`, routes `project_financials.py`.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Identité, échéances, jalon courant et avancement | Partiel : synthèse Agent | Distinguer échéance projet et date du jalon ; rattacher les indicateurs | L1, L4 |
| Budgets, consommé et RAF en heures | Partiel : total global | Répartition par lots techniques, sans conversion monétaire | L8 |
| Achats en euros, prix de vente, coût final, résultats, marges et ratios financiers | Exclu | Recensé ; pas de réactivation du moteur financier | — |
| Rafraîchissement persistant des résultats financiers | Exclu | Conserver les données historiques sans cette commande | — |

### 05 — Jalons (`milestones`)

Sources : `ProjectMilestonesPanel.tsx:75`, `services/project_governance.py:56`,
`docs/business/projects.md`. Agent : `MilestonesPanel.tsx`, `services/milestones.py`.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Dates contractuelle, prévisionnelle et réelle | Présent | Conserver historique et preuves d'Agent | L2 |
| 14 jalons standards, code stable, ordre de workflow | Partiel : trame de 8 jalons et titre | Ajouter codes/ordre sans remplacer les jalons existants | L2 |
| État À venir / Ouvert / Validé, commentaire et jalon courant | Partiel : réalisation déduite de la date réelle | État explicite indépendant des dates et commentaire | L2 |
| Ajouter, retirer, réordonner ; autosave | Partiel : ajout/modification | Réordonner ; archivage non destructif pour les jalons liés | L2 |
| Modèle versionné de typologie, décalages en jours ouvrés, instanciation | Absent | Templates de jalons et tâches ; mémoriser la révision utilisée | L1, L2 |
| Complétion depuis mails, documents, réunions et réseau | Présent, apport spécifique Agent | Préserver validation humaine, conflit optimiste et provenance | L2, L7 |

Socle XPilot : Réception du besoin, Remise offre, Réception commande, RLP, KOM,
PDR, CDR, FDR, Go fabrication, Réception CISS, Livraison, Mise en service,
Validation client, Clôture. La reprise ne créera pas 14 doublons dans les projets
existants : rapprochement proposé et accepté explicitement.

### 06 — Tâches (`tasks`)

Sources : `ProjectTasksPanel.tsx:90`, `TaskEditorModal.tsx:17`, routes `tasks.py`.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Création, édition détaillée, états et priorités | Partiel : titre/échéance/statut | Description, priorité, états attribué/bloqué/annulé | L2 |
| Hiérarchie parent/enfants et rattachement au jalon | Absent | Relations structurées, contrôle des cycles et du projet cible | L2 |
| Responsable unique, recherche personne et affectation/désaffectation | Absent : propriétaire textuel des actions de CR | Personnes identifiées et synchronisation avec l'équipe | L1, L2 |
| Dates début/fin, charge prévue, indicateurs BE/fabrication | Partiel : échéance | Planification opérationnelle et capacité | L2, L8 |
| Recherche, filtres statut/jalon/personne/priorité, tri, pagination, mémorisation | Absent dans la liste spécialisée | Liste dense filtrable, chargement progressif | L2 |
| Retrait de tâche | Absent dans l'écran simple | Archivage/annulation, confirmation si suppression demandée | L2 |

### 07 — Livrables (`deliverables`)

Sources : `ProjectDeliverableCards.tsx`, `DeliverableAssistancePanel.tsx`,
`domain/deliverables.py`, routes `deliverables.py` et vérifications spécialisées.

| Fonction / sous-espace XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Sélection par typologie, catalogue et livrable personnalisé | Partiel : ajout libre titre | Types, activation, catégories et administration | L1, L3 |
| AF, AR, conception 3D/2D, calcul, AMDEC, notice, V&V, formation, FDR, ACV | Partiel : liste générique | Catalogue métier, rattachement multi-jalons | L3 |
| Checklist editable, jalons, gates et progression | Absent | Validation structurée et distinction génération/vérification humaine | L3 |
| États brouillon/à vérifier/validé/à réviser/archivé | Partiel : statuts simples | Transitions et conditions de préparation | L3 |
| Versions fichier, référence, commentaire et manifeste | Absent hors livraisons CDC | Versions immuables, empreintes et provenance | L3 |
| Aide AF : génération depuis CDC, aperçu et choix des domaines/exigences | Absent | Prévisualisation puis génération traçable | L6 |
| Aide AR / notice / ACV : récupération de modèles | Absent | Copie locale contrôlée et référencement au livrable | L5, L6 |
| Aide calcul : note d'hypothèses | Absent | Formulaire métier et génération de document | L6 |
| Vérification AF ↔ synthèse CDC ou PDF CDC | Absent | Traitement durable, constats, décisions humaines et validation | L6 |
| Vérification AR ↔ AF ↔ CDC, rattachement d'une AR existante | Absent | Choix de versions, constats critiques et preuves | L6 |
| ACV : fichier existant, mesures, analyse et historique de runs | Absent | Analyse environnementale séparée des finances | L6 |
| Soudure / EXC depuis AF, AR ou 3D | Absent : destination transverse XPilot | Questionnaires, évaluation et explication locale ; qualification métier | L6 |
| Préparation d'une demande au vérificateur | Absent | Brouillon sans envoi automatique ; XPilot utilise le client et Outlook | L6 |
| Normes KDrive / Cobaz | Absent ; liens optionnels XPilot | Liens configurables ; disponibilité dépend de la configuration | L6 |
| Tutoriel AppKD | À venir XPilot : indisponible | Recensé, pas présenté comme fonction active à porter | — |

### 08 — BOM / Nomenclature (`bom`)

Sources : `ProjectBomPanel.tsx:51`, `BomClassificationReview.tsx`,
`BomSupplierProposalReview.tsx`, `BomClassificationMemoryPanel.tsx`, routes `bom.py`.

| Sous-menu / fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Documents/révisions de BOM et import XLSX immuable, dédoublonnage par empreinte | Partiel : lignes manuelles | Ajouter import versionné en conservant la saisie manuelle | L8 |
| Lignes : sections, hiérarchie, anomalies, pagination | Partiel : tableau plat | Parseur borné et anomalies consultables | L8 |
| Classification : famille de fabrication, matière, statut d'achat | Absent | Règles déterministes puis IA explicite pour cas restants | L8 |
| Acceptation/correction humaine de chaque proposition | Absent | Proposition et décision distinctes | L8 |
| Mémoire : promotion/rejet/restauration/annulation, règles et métriques | Absent | Capitalisation contrôlée ; administration partagée Supply | L8 |
| Fournisseurs : propositions depuis familles confirmées et capacités | Partiel : fournisseur textuel | Annuaire, preuves et sélection humaine | L8 |
| Recherche d'un fournisseur hors propositions ; choix manuel tracé | Partiel : saisie libre | Provenance `manual`, sans fausse recommandation | L8 |

Prix et valorisation ne sont pas inclus. Un fichier de BOM et ses révisions
doivent être sauvegardés avec l'ERP, pas uniquement indexés dans les embeddings.

### 09 — Revues (`reviews`)

Sources : `domain/project_reviews.py:23`, `ProjectReviewsPanel.tsx:340`,
`ProjectReviewAudioRecorder.tsx`, routes `project_reviews.py`, `audio_transcriptions.py`.

| Sous-menu / fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| RLP : participants, date, lieu, vigilance, fonctions, contraintes, décisions | Partiel : CR libre et actions | Revue structurée avec catalogue de sections | L4 |
| Sélection des livrables et checklists pendant la revue | Absent | Relier revue, jalons et documents métier | L3, L4 |
| Sauvegarde, publication, PDF, révision figée et nouvelle révision | Partiel : export CR simple | Versionnement et publication formelle | L4 |
| Demande de signatures aux participants | Absent | Workflow de signature tracé | L4, L5 |
| Audio : enregistrement, transcription éditable, synthèse IA et publication | Présent côté Agent | Raccorder les résultats aux sections RLP ; conserver la pile locale | L4 |
| RLC, RLF, RCD, Go/No-Go, Offre commerciale, Offre technique | À venir XPilot : 6 entrées désactivées | Prévoir extension du catalogue, après définition des trames ; pas une parité livrée | L4, ultérieur |

Seule la RLP est activée dans le référentiel de revues examiné. L'absence de
parcours opérationnel des six autres types ne doit pas être masquée par leurs menus.

### 10 — Écarts (`baselines`)

Sources : `ProjectBaselinesPanel.tsx:39`, routes `project_governance.py:81`,
service `project_governance.py:293`.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Capturer plusieurs références initiale/contractuelle/revue/avenant | Absent | Snapshot immuable de projet, jalons et tâches | L2 |
| Comparer courant/référence : ajout, retrait, modification, avant/après | Absent | Service de comparaison et tableau lisible | L2 |
| Sévérités, delta de charge, filtres et compteurs | Absent | Dates et heures uniquement ; finances exclues | L2 |
| Modifier nom/commentaire et archiver une référence | Absent : commande backend XPilot | Métadonnées modifiables, snapshot protégé | L2 |

### 11 — Tubes (`tube-costing`, conditionnel)

Sources : `TubeCostingPanel.tsx:29`, routes `tube_costing.py`.

Les cinq calculateurs sont **Boîte à coupe**, **Boîte de traçage**, **Tracé grandeur**,
**COM** et **Pointage soudure**. Ce dernier guide les étapes Exemple, Plateau,
Extrémités, Supports, Coude et Pièces supplémentaires. S'y ajoutent paramètres,
sauvegarde des résultats/offre et exports TDAO, offre et offre technique.

**Agent : absent. Reprise financière exclue.** Les données géométriques, choix
techniques, livrables et calculs d'heures pourraient être isolés dans un lot
ultérieur spécialisé ; ils ne justifient pas de réintroduire le chiffrage complet.
Le plan de parité opérationnelle laisse ce découpage après L9.

### 12 — Discussion (`chat`)

Sources : `ProjectDetailPage.tsx:990`, routes `projects.py:741` et notifications chat.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Messages entre collaborateurs avec auteur et portrait | Absent : assistant IA présent | Conversation humaine distincte de l'assistant | L9 |
| Notifications et marquage lu | Absent pour discussion humaine | Messages persistants, compteurs et permissions projet | L9 |

### 13 — Pointage (`time`)

Sources : `project-advanced/TimePanel.tsx:20`, routes `project_time_tracking.py`.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Totaux par personne et détails Sage | Partiel ; saisie manuelle Agent en plus | Filtrage de période, pagination et données source inspectables | L8 |
| Heures prévues, réalisées et RAF par lot métier | Partiel : RAF total réestimable | Décomposer les lots, conserver le RAF global existant | L8 |
| Enregistrement des réestimations et analyse des écarts en heures | Partiel | Historique et contrôle de concurrence par lot | L8 |
| Valorisation au taux horaire | Exclu | Les heures restent exploitables sans taux | — |

### 14 — Achats (`purchases`)

Sources : `project-advanced/PurchasesPanel.tsx:10`, routes `project_purchases.py`.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Détail des lignes Sage, statut, fournisseur et désignation | Présent sous forme simple | Filtres, colonnes configurables, pagination | L8 |
| Synthèse par fournisseur et besoins restant à acheter | Partiel | Liste opérationnelle liée à la BOM et dates, sans montants | L8 |
| Budget achats, réalisé/RAF en euros, résultat et marge | Exclu | Données historiques conservées, moteur non repris | — |

### 15 — Ventes (`sales`)

Sources : `project-advanced/SalesPanel.tsx:6`, routes `project_sales.py`.

**Exclu.** L'écran présente les lignes Sage, commandé/livré/facturé/avoir en
euros et leur répartition. Aucun écran financier Ventes ne sera ajouté dans
la reprise actuelle. Les références de commande nécessaires au projet peuvent
être conservées dans son identité et ses sources, sans ce moteur.

### 16 — Notes (`notes`)

Sources : `ProjectDocumentsPanels.tsx:128`, `notes/clientProjectNotes.ts`,
routes `projects.py:778` et adaptateurs runtime.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Liste/recherche, créer, ouvrir, renommer et éditer une note | Absent comme bloc-notes projet | Notes structurées, brouillons et fichiers référencés | L5 |
| Texte riche, listes/checkboxes, tableaux, images et pièces jointes | Absent | Éditeur borné et assainissement HTML | L5 |
| Autosave, reprise des brouillons, état d'enregistrement | Absent | Sauvegarde durable indépendante de l'affichage | L5 |
| Versions/restauration et notes historiques côté API | Absent | Journal et migration explicite ; distinguer le mode client utilisé par la fiche | L5 |
| Ouverture/téléchargement de fichiers Office locaux ou réseau | Partiel : ouverture de liens | Adaptateur local ; fichiers conservés et sauvegardés | L5 |

La fiche XPilot choisit `storageMode="client"` : la présence d'API de notes
serveur ne signifie pas que toutes les notes affichées y sont stockées. Décider
du stockage canonique Agent et d'un import séparé, sans aspirer automatiquement
les dossiers utilisateurs ni déplacer leurs documents.

### 17 — Import (`tdao`)

Sources : `ProjectTdaoPanel.tsx:1`, routes `projects.py:708`.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Import depuis chemin TDAO du projet | Partiel : import dossier et lecture d'heures TDAO | Commande projet explicite, aperçu et erreurs de lecture | L1, L8 |
| Répartition d'heures par disciplines et édition manuelle | Partiel : total importé | Chiffrage/AVP, management, qualité, études 3D/2D, calcul, supply, automatismes, électricité, chantier, montage, câblage, essais ; rester en heures | L8 |
| Confirmation de remplacement des valeurs existantes | Partiel | Aperçu avant/après, historique, maintien des données absentes du fichier | L8 |
| Prix de vente, budget achats et marge | Exclu | Pas de reprise du formulaire financier | — |

### 18 — Équipe (`team`)

Sources : `ProjectCollaborationPanels.tsx:36`, routes `projects.py:555`, service
`projects.py:221`. Agent dispose de rôles d'accès Brain, mais pas de cette équipe ERP.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Ajouter/modifier/retirer un membre, rechercher une personne | Absent | Référentiel personnes et rattachement projet | L1 |
| Responsable projet, pilote étude, BE 3D/2D, vérificateur, qualité, calcul, fabrication, collaborateur, lecteur | Absent comme rôles métier ERP | Distinguer rôle métier et permission d'accès | L1 |
| Synchronisation du CAF et de l'équipe ; coordonnées utilisées dans les documents | Absent | Identité unique, contrôle de cohérence | L1, L5 |

### 19 — Clôture (`closure`)

Sources : `ProjectCollaborationPanels.tsx:1279`, service `projects.py:342`, routes
`projects.py:602`. Un simple changement de statut Agent ne fournit pas ce workflow.

| Fonction XPilot | Agent actuel | Écart et reprise | Lot |
|---|---|---|---|
| Commentaire projet et REX de fin distincts | Partiel : connaissance/CR | Bilan de fin structuré, sans effacer les faits existants | L9 |
| Revue de fin terminée et dossier déclaré archivé | Absent | Checklist de clôture explicite et vérifiable | L9 |
| Contrôle d'accès au dossier réseau principal | Absent | Adapter la règle à Agent : réseau inaccessible ne prouve pas un archivage | L9 |
| Contrôle des tâches ouvertes et décision explicite de traitement | Absent | Aucune annulation/suppression de planning en cascade silencieuse | L9 |
| Date réelle distincte de l'échéance, statut fermé et retrait des vues actives | Partiel : statut brut | Commande métier et conservation de l'historique | L1, L9 |
| Réouverture dédiée avec motif audité | Absent | Commande dédiée, pas simple édition libre du statut | L9 |

## Dépendances transversales indispensables

| Dépendance XPilot | État Agent et décision proposée | Lot |
|---|---|---|
| Identité : agence, BU, famille, typologie, CAF, dates, références client/outillage, standby | Champs projet insuffisants ; migrations additives et référentiels légers | L1 |
| Modèles de typologies et catalogue de livrables | Ajouter administration dans Réglages, sans nouvelle application séparée | L1–L3 |
| Portefeuille : mes projets, équipe, états, anomalies et navigation ciblée | Filtrage Agent existant ; enrichir après identité/permissions | L1, L4 |
| Droits métier et visibilité documentaire | Agent possède une session locale et des ACL Brain ; aligner la portée ERP/Brain avant fonctions multi-utilisateurs | L0, L1 |
| Signatures : éligibilité, demande, document final, signer/refuser/rappeler/annuler | Absent ; provenance, gel et identité nécessaires ; ne pas promettre une signature qualifiée | L5 |
| Agenda / charge / capacité / personnes / absences | Planning Agent simple ; modèle de ressources nécessaire pour les fonctions projet qui en dépendent | L8 |
| Abonnements iCalendar : tâches, jalons, revues, absences, révocation | Absent ; dépendance partagée, pas sous-menu caché de la fiche projet | L9 |
| Qualité / Kaizen : tickets, actions, preuves, mesures, discussion, alertes | Risques/actions Brain ne remplacent pas leurs workflows ; reprendre le raccordement projet | L9 |
| Référentiel Supply et capacité fournisseurs | Nécessaire au sourcing BOM ; reprendre la partie opérationnelle requise | L8 |
| Jobs durables, annulation, nouvelle tentative, progression, invalidation | Déjà présents pour plusieurs moteurs Agent ; mutualiser leurs conventions | Tous |
| Versions, sauvegardes et archive JSON | Archive projet Agent existante ; inclure chaque nouvelle table et chaque fichier | Tous |
| Notifications et collaboration | Ne pas confondre assistant IA, discussion d'équipe et décisions validées | L4, L9 |

## Ce qui peut être repris et ce qui doit être adapté

**Réutiliser comme base** : définitions de jalons/livrables, trames de revue,
règles de contrôle et comparaison, parseurs bornés, schémas métier, scénarios de
tests, algorithmes de classification et mappings documentaires. Valider les
droits de réutilisation des assets/trames nécessaires lors du lot concerné.

**Adapter** : services utilisant repositories XPilot/MariaDB, schémas de
permissions, stockage de fichiers, jobs, client API et composants liés au
runtime Tauri. Agent conserve SQLite ERP + SQLite Brain et FastAPI sur **8001**.
L'adaptation doit étendre les modules hérités, sans les réécrire ou les retirer.

**Éviter la duplication** : ne pas lancer un troisième backend, copier la base
XPilot, remplacer le moteur mémoire par Qdrant uniquement pour la similarité,
ou recopier les services financiers. Les embeddings restent des projections ;
les dates, décisions, états et versions restent en base métier.

**Préserver les apports Agent** : classement mail, création depuis dossier avec
code correct, rafraîchissement des sélecteurs, témoins d'indexation, réunions
locales, propositions datées sourcées, historique et assistant contextualisé.

## Qualification de cet audit

Les 19 identifiants sont relevés dans `ProjectDetailPage.tsx:603–684` et les
actions rattachées dans les composants/routes inventoriés. Les entrées inactives
ont été distinguées des fonctions opérationnelles. Les écarts Agent ont été
vérifiés dans ses modèles, routes et écrans actuels. L'inventaire permet de
détecter une évolution du référentiel avant une reprise.

Les suites de tests XPilot constituent des exemples de recette à adapter ; elles
n'ont pas été lancées ni déclarées passantes pour Agent. Cette livraison modifie
uniquement la documentation et l'inventaire d'audit. Aucun commit, push,
redémarrage de service ou changement de données n'est effectué.
