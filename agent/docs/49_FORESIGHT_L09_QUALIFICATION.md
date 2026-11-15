# L09 — Recherche multimodale et relations qualifiées

Clôture du lot L09 le 16 octobre 2026, selon ses exigences d’origine dans
`docs/37_FORESIGHT_FUSION_PLAN.md`. L12 reste ouvert.

## Parcours disponible

Dans **Sources**, importer les documents du projet. Pour un scan PDF, ouvrir ses
détails puis **Reconnaître le texte du scan**. Le texte reconnu est mis en attente
d’indexation EG2. Pour la recherche visuelle ou audio, ouvrir **Indexation des
projets**, puis la préparation locale et **Vérifier et compléter ce projet** ;
choisir ensuite **Images** ou **Audio** dans les filtres de recherche des Sources.
Le LLM peut rester sur le réseau. Les index et originaux métier déjà présents
ne sont pas reconstruits globalement par cette livraison.

## Exigences et preuves

| Exigence du lot | Preuve vérifiée |
|---|---|
| Extraction PDF, Office et tableurs avec localisateurs | PDF physique/page, Word DOCX/partie du document et Excel XLSX/XLSM/feuille/plage ; extraction native conservée. Un DOCX fictif vérifie texte, réserve, contenu barré et tableau sans inventer de page imprimée. |
| OCR des scans si nécessaire | Véritable OCR Windows français/anglais via le parcours HTTP ; nouvelle interprétation immuable, ancien texte et original inchangés. La recherche réelle retrouve la page OCR 2 avec le signal de relecture. Domaine48. |
| Images et schémas | Quatre rendus PNG de géométries distinctes retrouvés au rang1 dans la preuve acquise ; quatre pages de plans PDF retrouvées au rang1 avec le rendu produit actuel PDFium. |
| Fenêtres audio et encodeur correspondant | Preuve réelle R3 : quatre conversions FFmpeg, deux recherches audio au rang1, trois exclusions, persistance et rejeu ; SDK complet 740M sur CPU, 768dimensions. Il s’agit d’embeddings audio, distincts de la transcription ASR. |
| Index persistant et profil identifié | Index SQLite séparé, modèle/révision/runtime/prétraitements/modalité/dimension dans le profil ; réouverture et recherche réussies. Poids identiques aux essais audio et documentaires ; encodeur et script SDK audio byte-identiques. |
| Profils incompatibles et reconstruction parallèle | Trois contrats sur deux générations SQLite : ancienne recherche toujours disponible, index EG2 texte inchangé, nouvelle génération sélectionnée explicitement après construction ; mauvais profil ou vecteur512 refusé sans remplacer les anciens vecteurs768. Les encodeurs de ces contrats sont simulés. Un autre modèle réel n’est pas installé pour ces tests. |
| Contrôles projet et version | Corpus documentaire : projet étranger, ancien PDF, interprétation pré-OCR et tableur modifié exclus ; nouvelle lecture canonique après calcul de requête. Contrats de course et de droits conservés. |
| Graphe connu, navigable et traçable | Vue Sources/Relations déjà inspectée ; nouveau parcours HTTP en lecture seule des976sources sur5pages, sans doublon ;3555arêtes connues, toutes reliées à des nœuds visibles, `inferred=false`. Contrats vérifiant l’exclusion des liens croisés non autorisés. |
| Pas de nouvelle autorité métier | Résultats multimodaux de niveau proposé, OCR à relire, aucune création de validation humaine ou de fait métier par la recherche ou le graphe. |

« Office » couvre les formats documentaires pris en charge ici : DOCX et tableurs
XLSX/XLSM, complétés par CSV/TXT/MD/HTML. Les formats binaires DOC/XLS/PPT, PPTX,
la lecture native de CAO et l’analyse industrielle universelle ne sont pas
revendiqués. Les originaux non extractibles restent conservés avec leur état
explicite. Les modules CDC hérités ne sont pas réécrits.

## Corpus fixé et pertinence mesurée

Corpus et questions figés **avant** le chargement du modèle :
`.ui-preview/l09-document-retrieval-20261016/corpus.json`, SHA-256
`dba594342c04a10335677e511a0fb039873b7403b9cf609dc41a353876cd4d8d`.

Neuf fichiers fictifs : six PDF avec versions contradictoires et projet étranger,
un PDF mixte natif/scan et deux classeurs. Le critère fixe demande la source,
version, modalité et page ou plage exactes au **rang1** sur tout le projet autorisé.
Aucun filtrage préalable vers la seule bonne source pour les questions positives.

Le véritable encodeur produit courant a indexé25entrées, dont les anciennes
conservées pour vérifier leur exclusion. Résultats :

- quatre recherches visuelles de plans PDF : **4/4** au rang1 ;
- quatre instructions textuelles PDF : **4/4** au rang1 ;
- deux lignes de tableur avec feuille/plage exactes : **2/2** au rang1 ;
- une recherche de la réserve du scan OCR : **1/1** au rang1 ;
- quatre contrôles d’exclusion : **4/4**, aucun résultat interdit ;
- réouverture de l’index : même source correcte ; arrêt naturel de l’encodeur : code0.

Sur ces11questions : exactitude au rang1 et Recall@5 de **100%**. Le P95 observé
des recherches à chaud, services et contrôle canonique compris, est **0,302s** ;
le chargement du modèle est mesuré séparément à **2,012s**. L’essai entier dure
**38,635s**. Ce sont des mesures sur ce corpus, sans génération ni mesure DOM ;
elles ne valent pas une garantie sur tout document ou un P95 d’assistance directe.
Les questions et annotations n’ont pas été ajustées après les résultats.

Preuve actuelle :
`.ui-preview/l09-document-retrieval-20261016/run-6959e9d8f6114bb3b0fb5c2fb490852f/result.json`.
Les preuves PNG et audio antérieures sont réutilisées après vérification des
empreintes, du profil et des portions de code concernées ; elles ne sont pas
présentées comme des essais rejoués aujourd’hui.

## Disponibilité et exploitation

Le fichier attendu par `runtime_status`,
`logs/foresight-runtime/multimodal-qualification.json`, était absent. Il est créé
à partir de ces preuves réelles, du profil et de l’identité vérifiée des poids.
Agent peut ainsi indiquer **installé et qualifié** tout en indiquant le résident
**arrêté** après l’essai. Quatre contrats vérifient que le reçu absent, un profil
modifié ou un fichier de poids remplacé empêchent la disponibilité qualifiée.
Le champ historique de qualité générale reste faux : cette qualification est
explicitement celle des corpus fixés, sans généralisation industrielle.

Vérification logicielle de ce complément :22contrats index/PDF/profils/graphe,
un contrôle Word et quatre contrôles de disponibilité, soit **27réussites**.
Ruff passe. Les71contrôles backend et44contrôles frontend/transport de la livraison
OCR précédente sont acquis sur des sources produit inchangées. Les suites
globales ne sont pas annoncées comme rejouées.

Le lot exige une pertinence mesurée sur corpus fixé ; il n’ajoute pas un seuil
de RAM libre, un essai industriel illimité ou une nouvelle répétition de toutes
les modalités inchangées. Cette clôture respecte ce critère sans transformer
les mesures du pilote en une promesse générale. L02/L03/L11/L12 restent ouverts.
Mode réseau et règles de déchargement du LLM local inchangés ; aucun microphone,
GPU, transcription ou LLM génératif n’a été lancé pendant ce complément.

Audit : `logs/foresight-runtime/L09-requirements-qualification-ROOT-20261016.json`.
