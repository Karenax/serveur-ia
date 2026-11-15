# Pages PDF dans l’index multimodal

## Profil de rendu — 22 octobre 2026

Le correctif de sécurité utilise **Pillow 13.0.0** et un profil PDF distinct ;
les empreintes et profils précédents restent conservés. Le comptage des pages
s'exécute dans un processus limité à 90 secondes et 1 Gio. Aucun index canonique
PDF n'était présent lors du contrôle préalable ; les entrées texte sont
préservées. Voir [le suivi de sécurité](60_SECURITY_REMEDIATION.md).

La conversion visuelle comble l’absence d’image pour les pages PDF scannées.
Elle conserve l’original et les artefacts texte existants. Chaque entrée image cite
sa page physique et l’artefact correspondant ; elle porte le profil de rendu et
l’empreinte de la version source. Une modification de l’original exclut les anciens
vecteurs de la recherche sans les supprimer.

## Installation et fonctionnement

`requirements-multimodal.txt` ajoute pypdfium2==5.14.0 et Pillow==12.1.1 au seul
environnement `.venv-litert`. PDFium est exécuté via `scripts/render_multimodal_pdf.py`
dans un processus distinct, sans SDK de modèle, GPU ni réseau. Les appels PDFium ne
sont donc pas partagés entre les threads du serveur. Le rendu RGB vise2048pixels sur
le côté le plus long ; ce paramètre est inclus dans le profil de chaque page.
Toutes les pages sont préparées, sans plafond ajouté au nombre de pages ; les lots
et quotas de stockage de l’index existant continuent de s’appliquer.

Le rendu est différé jusqu’au traitement de l’entrée image. Son reçu conserve les
empreintes du PDF et du PNG, la page, les dimensions et le profil. Un cache modifié
est refusé et conservé. Un arrêt avant publication du reçu laisse une tentative
orpheline conservée et permet une nouvelle tentative. Les chemins longs Windows
sont pris en charge par le convertisseur. Les dépendances absentes font échouer
l’entrée explicitement ; aucun encodeur n’est lancé pour cette entrée.

## États et limites

Un nouvel import sans texte natif est `ocr_required`, un PDF mixte est
`partially_extracted`, une extraction réellement vide est `empty`. Les libellés sont
français dans Sources. Un rendu visuel ne transforme pas ces états en texte extrait.
Les anciens imports ne sont pas réinterprétés ni réécrits automatiquement.

Le profil du modèle multimodal reste identique ; le profil de rendu est lié à
l’empreinte des seules sources PDF. Leur prochaine reconstruction explicite ajoutera
les pages visuelles et conservera les anciennes entrées. Aucune reconstruction
canonique n’a été déclenchée par cette livraison.

La construction/reprise et la recherche explicitement Images/Audio sont maintenant indépendantes du mode de génération. En mode réseau, la recherche générale/texte conserve EG2 réseau ; sélectionner Images ou Audio pour le complément local.
La qualité générale sur scans industriels, l’OCR et la CAO native ne sont pas qualifiés
par ces cinq cas. L09 et L12 restent ouverts.

## Vérification

Les5cas nouveaux couvrent un PDF image de deux pages sans texte, un PDF mixte,
l’échec de rendu sans démarrage de modèle, la réutilisation/refus d’un cache altéré,
et la reprise après tentative orpheline. Rendu PDFium réel ; encodeur simulé. Les
couleurs, dimensions, pages, artefacts, conservation de l’original, recherche après
réouverture, rejeu sans doublon et exclusion après changement sont contrôlés.

Le premier ciblé a donné78réussites et4échecs nouveaux ; après correction, les5cas
nouveaux passent. Les77cas existants du ciblé restent leur preuve acquise, sans les
réexécuter. Les30cas frontend, TypeScript, Vite et Ruff passent. Le blocage initial
de création des bases temporaires dans le bac à sable est conservé comme tel.

Activation backend8001 et assets HTTP vérifiés ; sauvegardes récentes réutilisées
uniquement après vérification des empreintes et comparaison exacte des données
non volatiles Brain/ERP avant/après. Aucun modèle, microphone, GPU, XPilot8000,
réindexation métier, commit ni push dans cette livraison.

Reçu : `logs/foresight-runtime/L09-PDF-pages-delivery-ROOT-20261016.json`.
API PDFium officielle : https://pypdfium2.readthedocs.io/en/stable/python_api.html

### Images et audio avec le LLM réseau — 16 octobre 2026

La préparation multimodale locale et les recherches explicitement choisies Images/Audio
fonctionnent aussi en mode réseau. Le mode et le modèle de génération ne sont pas modifiés.
Dans Réglages > Mémoire > Recherche locale dans les images et l’audio, choisir le projet
et « Vérifier et compléter ce projet » ; dans Sources, choisir ensuite Images ou Audio.
La recherche générale/texte conserve EG2 réseau. Les démarrages réseau n’activent pas
automatiquement l’indexeur local ; la construction ou la reprise restent explicites.

10contrôles backend ciblés,26frontend, TypeScript, Vite et Ruff passent, avec moteurs
simulés dans ces contrôles. Backend8001 et assets activés, sauvegardes vérifiées et
données non volatiles Brain/ERP comparées exactes. Aucun modèle, GPU ni microphone
lancé dans ce raccordement. Les anciennes preuves réelles de l’encodeur restent acquises.
L09 et L12 restent ouverts ; voir domaine45.

### OCR des PDF conservés — 16 octobre 2026

Sources → Détails du PDF → « Reconnaître le texte du scan » ajoute le texte des
pages scannées avec son numéro de page et un état de relecture explicite. Le bouton
est aussi visible en grille. Indicateur de travail en cours, pages déjà traitées
réutilisées après interruption, aucune nouvelle limite de RAM/page/durée totale.
L’original, les anciennes extractions et les versions sont conservés ; le nouveau
texte est mis en attente d’indexation dans le mécanisme EG2 habituel. Les limites
documentaires existantes restent applicables. Aucun module CDC hérité n’est réécrit.

L’OCR Windows français/anglais fonctionne sur CPU, sans modèle génératif ni GPU.
Essai réel via HTTP sur un PDF fictif mixte : 4,14 s, valeurs 1250 W et 230 V et
réserve « ne pas valider » reconnues ; anciens artefacts et téléchargement original
inchangés. 71 tests backend et 44 tests frontend/transport ciblés passent, ainsi que
TypeScript, Vite et Ruff. Les suites globales ne sont pas rejouées.
Backend 8001 et fichiers compilés activés après sauvegardes et comparaison SQL.
Huit lots restent clos ; L02/L03/L09/L11/L12 restent ouverts. Détail :
`docs/48_FORESIGHT_SCAN_OCR.md`. Aucun microphone, téléchargement ou LLM lancé.

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

