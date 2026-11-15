# Reconnaissance locale des PDF scannés

Livraison du 16 octobre 2026, sur le serveur Agent unique `8001`.

Dans **Sources → Détails du PDF → Reconnaître le texte du scan**, Agent utilise
l’OCR intégré à Windows. En grille, le bouton est directement dans la carte.
Il apparaît pour un PDF conservé, courant, dont le texte manque sur certaines
pages. Les pages possédant déjà du texte natif ne sont pas réinterprétées.
La reconnaissance française est préférée, sinon l’anglais installé. Aucun
téléchargement, moteur génératif, microphone ou GPU n’est nécessaire.

Le bouton et l’indicateur annoncent le travail en cours. Il n’y a pas de plafond
de RAM disponible, de nombre de pages ou de durée totale ajouté par ce parcours.
Les capacités documentaires existantes restent applicables : import de 50 Mio,
texte de 2 millions de caractères, rendu visuel RGB de 2048 pixels sur le grand
côté. Ce rendu n’est pas une garantie de lecture des petits caractères d’un
grand plan ; le PDF original reste la référence.

## Conservation et preuves

`POST /api/v1/workspace/sources/{source_id}/ocr` effectue le traitement sur un
thread de requête, puis crée une nouvelle interprétation `Source` et de nouveaux
`SourceArtifact`. L’original, la version de contenu `LibraryVersion`, les anciens
artefacts et leurs index restent conservés. Seul le lien courant de
`LibraryItem` bascule après reconnaissance et vérification de l’empreinte.
Le remplacement est conditionnel : un nouvel import concurrent ne peut pas être
remplacé par un résultat OCR commencé sur une ancienne version.

Les citations conservent la page physique, le profil Windows/langue/rendu, les
lignes et rectangles reconnus, et `text_is_OCR=true` avec
`visual_review_required=true`. **« Texte OCR · relecture nécessaire »** ne vaut
pas validation technique ou commerciale. Une page sans résultat reste signalée
comme telle ; elle n’est pas déclarée extraite. Le texte natif est conservé.

Le nouveau texte courant est ajouté aux preuves canoniques et sa projection EG2
est mise en attente dans le mécanisme habituel. L’ancienne interprétation est
écartée du rappel courant. L’action ne reconstruit pas l’index multimodal et ne
charge pas son encodeur ; celui-ci se complète explicitement depuis Indexation.

Chaque page reconnue possède un point de reprise sous `storage/raw/ocr/`, à
adapter si `PB_STORAGE_DIR` est personnalisé. Son identité comprend l’empreinte
du PDF, la page et le profil. L’intégrité du résultat est contrôlée avant
réutilisation. Une interruption avant la transaction finale laisse le lien
courant intact ; relancer le bouton réutilise les pages terminées. Un résultat
de cache corrompu est refusé et conservé. Il n’y a pas de reprise automatique au
démarrage, ni de suppression des tentatives. Un onglet fermé peut perdre son
indicateur alors que la requête serveur continue : actualiser les Sources avant
de relancer. Une reconnaissance simultanée de la même source est refusée ; la
vérification conditionnelle SQL protège aussi contre un autre processus.

## Configuration et contrôle

Services : `app/services/library_ocr.py`, `scripts/windows_ocr.ps1` et la route
Sources existante. Le rendu réutilise `scripts/render_multimodal_pdf.py` dans
le Python `PB_MULTIMODAL_PYTHON` ou `.venv-litert`, avec PDFium 5.14.0 et Pillow
12.1.1. Aucun encodeur multimodal n’est exécuté pour l’OCR. Windows doit disposer
de la reconnaissance française ou anglaise. L’absence de langue ou de rendu
retourne un échec explicite et préserve les preuves.

Les contrôles projet, source courante et opérateur en écriture sont vérifiés
côté serveur. Les lecteurs ne peuvent pas lancer l’action. Les imports CDC
hérités ne sont pas réécrits : le bouton concerne les PDF conservés dans la
bibliothèque Sources.

Preuve réelle : `.ui-preview/ocr-windows-20261016/actual-http-result.json`.
Un PDF fictif mixte a traversé la route HTTP produit avec le véritable OCR
Windows en **4,14 s**. La page scannée contient exactement `1250 W`, `230 V` et
`Réserve : ne pas valider.` ; la page native, les anciens artefacts et les octets
de l’original téléchargé sont inchangés. La projection a été mise en attente,
sans exécution d’embedding pendant cet essai privé.

Validation ciblée : 71 tests backend OCR/Sources, 28 tests d’interface Sources
et 16 tests de transport/indicateurs. Le premier passage contenait une erreur
dans le scénario de remplacement simulé, corrigée et rejouée ; son rapport est
conservé. TypeScript, compilation Vite et Ruff sont vérifiés séparément. Les
suites globales acquises ne sont pas présentées comme rejouées. Cette livraison
réduit le manque OCR du L09 ; elle ne clôt pas L09 ou L12.

Référence de l’API native : [Microsoft OcrEngine.RecognizeAsync](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine.recognizeasync).

### L09 qualifié sur ses corpus fixés — 16 octobre 2026

Recherche réelle du produit courant :11/11questions documentaires retrouvent la
source/version et page ou cellule exactes au rang1, avec4/4exclusions. PDF visuels,
scan OCR et tableurs sont couverts ; les preuves acquises de4images PNG et2requêtes
audio sont réutilisées après contrôle du code et du profil. L’index est rouvert,
l’encodeur CPU s’arrête naturellement et les anciens vecteurs restent conservés.
P95 chaud observé sur11questions :0,302s ; essai38,635s, sans génération ni mesure DOM.
Le graphe courant couvre976sources et3555liens connus sur5pages, sans doublon.
27contrôles ciblés index/profils/PDF/graphe/Word/disponibilité passent, Ruff aussi.

Le reçu de qualification attendu par le runtime est maintenant présent : moteur
installé et qualifié, résident arrêté. Aucun modèle n’est relancé pour corriger
cet état. Le mode réseau et les données métier restent inchangés. Pas de nouvelle
capture, transcription, GPU ou LLM génératif. Aucune réindexation globale lancée.
L09 est clos selon ses exigences de corpus fixé et de provenance ; ce n’est pas
une garantie de lecture native CAO, de tous les formats Office ou de toute donnée
industrielle future. Neuf lots sont clos ; L02/L03/L11/L12 restent ouverts.
Correspondance des exigences et preuves : `docs/49_FORESIGHT_L09_QUALIFICATION.md`.

