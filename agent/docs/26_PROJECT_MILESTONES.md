# Jalons projet et recherche des dates

Chaque jalon conserve trois dates indépendantes, au format `AAAA-MM-JJ` :

| Champ | Sens |
|---|---|
| `contractual_date` | Engagement explicite d'un contrat, d'une commande ou d'un avenant |
| `forecast_date` | Dernière prévision validée, notamment après report |
| `actual_date` | Date d'un événement effectivement réalisé |

Un champ absent reste vide. L'écart en jours compare la date réelle, sinon la
prévision, à la date contractuelle. Une réalisation renseignée clôt le jalon pour
les alertes de retard et le prochain jalon du portefeuille. `due_date` reste
compatible avec les anciens consommateurs : prévision, sinon contrat. Une ancienne
échéance unique est migrée en prévision, sans inventer d'engagement contractuel.

## Interface et validation

Dans Projet → Planification → Jalons : tableau éditable des trois dates, état,
écart, sources et historique. Les nouveaux projets reçoivent huit jalons usuels
(lancement, validation CDC, revue de conception, fin des études, FAT, livraison,
SAT, réception définitive), sans dates. Au démarrage, cette trame est ajoutée
seulement aux projets qui n'ont aucun jalon ; les listes existantes sont conservées.
Les noms sont modifiables et des jalons spécifiques peuvent être ajoutés.

Les assertions extraites apparaissent dans « Dates proposées ». La preuve exacte,
la source, la qualification et la confiance sont affichées. L'utilisateur choisit
le jalon cible, valide ou écarte. Une valeur différente est signalée comme conflit
et le bouton annonce explicitement son remplacement. La date actuelle est relue
côté serveur ; une validation périmée retourne `409`. Une preuve modifiée,
inaccessible ou rattachée à un autre projet bloque également la validation.
Les écritures alimentent `milestone_changes` ; aucune ancienne date n'est effacée
de cet historique. Les dates validées restent opérationnelles même si leur source
devient ensuite inaccessible ; leur preuve et leur historique demeurent consultables.

## Sources et limites de recherche

Le worker local lit uniquement les données associées au projet :

- textes canoniques des mails classés, transcriptions, OCR et documents Brain ;
- pièces jointes lisibles des EML originaux conservés dans le stockage géré ;
- pages extraites des CDC et décisions des comptes rendus ERP ;
- documents accessibles depuis les liens réseau du projet.

Le réseau est lu, jamais modifié. Formats repris du lecteur CDC : PDF avec texte,
DOCX, XLSX/XLSM, CSV, TXT et Markdown. Pas d'OCR supplémentaire pour les scans,
ni lecture des anciens XLS, des plans CAO ou des documents chiffrés. Les chemins
inaccessibles, textes insuffisants et formats de liens directs non pris en charge
sont signalés dans le résultat. Les documents portant uniquement un autre numéro
d'affaire explicite sont ignorés et signalés.

L'exploration est bornée à cinq niveaux, 500 documents / 5000 entrées par lien,
20 Mio par fichier, 300 000 caractères par document, et 30 passages d'environ
10 000 caractères par traitement. Les textes se chevauchent sur 500 caractères ;
une citation doit rester intégralement dans un passage. Le compteur concerne les
passages du lot courant, pas le nombre total de fichiers réseau. Les limites et
sources restantes sont visibles ; les prochains lots reprennent les textes non
traités. Réduire le périmètre des liens lorsque la limite d'exploration est atteinte.

Le LLM configuré dans Brain est utilisé avec raisonnement désactivé, hors de toute
transaction SQLite. Les résultats sont vérifiés localement : citation littérale,
nom du jalon présent, date complète avec année explicite, une seule date et une
seule qualification par citation. Les formulations négatives et réalisations
futures sont refusées. Dates relatives ou ambiguës : aucune date n'est fabriquée.
Si l'IA est désactivée, une extraction conservatrice cherche les jalons usuels
dans les lignes avec dates explicites. Si le LLM ne répond pas, ce secours peut
produire des propositions, mais la source reste en échec et sera reprise.

## Exécution, stockage et assistant

Un seul worker dans Agent `:8001`, passage automatique toutes les cinq minutes
sur les projets actifs, réveil après classement humain d'un mail, lancement manuel
« Rechercher les dates ». Les projets inactifs restent analysables manuellement.
L'état et l'avancement sont visibles dans les Jalons et dans Traitements. La file
est persistante et les traitements interrompus sont repris au redémarrage.
Le dernier état est réutilisé par projet pour éviter une accumulation de jobs vides.

ERP conserve `milestones`, `milestone_candidates`, `milestone_changes`,
`milestone_inputs` et `milestone_scan_jobs`. Le journal incrémental identifie les
passages déjà analysés par empreinte du texte et configuration d'extraction.
Les documents réseau inchangés et complètement traités ne sont pas ré-extraits.
Les résultats sont contrôlés contre la source courante après l'appel IA.
Les sauvegardes et archives projet incluent les nouvelles tables ; les anciennes
archives conservent leur échéance comme prévision. Les journaux importés sont
marqués à reprendre pour relire les preuves.

Pour les questions sur les dates/jalons, l'assistant ajoute le tableau ERP courant
à son contexte validé, même si la mémoire externe est indisponible. Il distingue
explicitement les trois dates et les champs non renseignés. Le tableau ne dépend
donc pas d'un ancien embedding. La sélection du contexte reste bornée ; les sources
des dates individuelles sont accessibles dans le tableau des jalons.

## API et vérification

| Route | Usage |
|---|---|
| `POST /api/v1/projects/{pid}/milestones` | Ajouter un jalon et ses dates |
| `PATCH /api/v1/projects/{pid}/milestones/{mid}` | Modifier les dates / le nom, avec historique |
| `GET /api/v1/projects/{pid}` | Liste structurée et écarts |
| `GET /api/v1/projects/{pid}/milestones/review` | Propositions en attente et dernier traitement |
| `POST /api/v1/projects/{pid}/milestones/scan` | Recherche asynchrone, `202` |
| `POST /api/v1/projects/{pid}/milestones/candidates/{cid}/decision` | `accept` / `reject`, `expected_value`, `milestone_id` facultatif |
| `GET /api/v1/projects/{pid}/milestones/{mid}/history` | Historique des modifications |

Tests : `tests/test_milestones.py`, `web/src/components/MilestonesPanel.test.tsx`.
Ils couvrent migration additive, trois dates, clôture, preuve, contradictions,
source déplacée/modifiée, reprise IA, incréments au-delà d'un lot, réseau,
pièces jointes, CDC/CR, contexte assistant et interactions d'interface.
