# Qualification L10 — Publication métier, tâches et exports

L10 est qualifié selon ses livrables et sorties. Les contrats nécessaires de séance, notes, scopes et affichage sont exercés ; cela ne clôture pas les autres périmètres L02/L03/L05/L06 ou L12.
La publication de notes seules et d’audio conservé ne dépend pas de la qualification du direct industriel.

| Exigence du plan | Preuve inspectée |
|---|---|
| Séance finale, relecture et citations vérifiées | Contrôle ASR medium CPU + LLM réseau conservé ; fonctions ASR/synthèse/publication inchangées ; règles de relecture actuelles vérifiées séparément |
| CR/actions/informations publiés avec identités idempotentes | Reprise audio après commit ERP dans le JUnit courant ; notes seules après commit ERP dans le global sur service inchangé ; CR/actions/provenances uniques |
| Conversion explicite en Task | Nouveau parcours HTTP privé : aucune tâche après publication ; création uniquement par commande ; deuxième conversion rejetée 409, une seule tâche |
| Ouverture depuis projet et global | Nouveau parcours HTTP : même CR et session dans les deux listes ; liens PDF disponibles dans les deux interfaces |
| PDF et exports existants | Nouveau PDF direct via ReportLab/Vera existants ; Markdown conservé ; ZIP autonome notes/versions/audio ; RLP PDF existant inchangé |
| CR de notes seules sans audio fictif | Nouveau parcours HTTP : zéro MeetingRecording, CR/action/provenance réels sur notes fictives ; aucune tâche implicite |
| Citation note/version/bloc et rejeu après modification Documents | Contrats historiques sur service inchangé : version publiée figée après changement de note ; citations inventées et versions périmées refusées |
| Rectification et conservation du CR figé | Corps du CR conservé ; nouvelle commande de publication d’une même séance refusée ; aucun parcours d’amendement proposé ; actions de suivi existantes restent explicites |
| Pas de validation humaine créée par direct/indexation | La commande de publication explicite porte l’opérateur ; les chemins capture et evidence restent distincts ; tests notes-only et contrôle projet |

## Export PDF du CR

`GET /api/v1/projects/{project_id}/meetings/{meeting_id}/pdf` est une lecture autorisée du projet, sans fichier temporaire ni écriture SQL. ReportLab et les polices Vera déjà présents dans Agent produisent le PDF.
Le contenu conserve projet, date, participants, compte rendu et actions, responsables/échéances et état de transfert en tâche. Le texte HTML est échappé ; aucune image distante ni URL n’est chargée.
Le PDF a des pages A4, marges et pieds de page numérotés. Les paragraphes et actions longs passent sur plusieurs pages. Le téléchargement réutilise l’indicateur de préparation existant.
Le bouton Exporter en PDF se trouve sur les CR du projet et dans le détail global des réunions. L’export Markdown et le PDF des revues de lancement restent disponibles.

## Qualification et conservation

Trois tests backend couvrent publication/rejeu/tâche/PDF, droits/texte hostile et pagination longue. Les 48 tests frontend et les 23 contrôles d’accès ciblés passent. TypeScript, Vite et Ruff passent. Les ensembles historiques et actuels se recouvrent.
Les deux pages du PDF fictif ont été rendues avec Poppler puis inspectées visuellement. Les six valeurs techniques, les réserves, la dernière action et les pieds de page sont présents et lisibles.
Le parcours ASR medium CPU et LLM réseau déjà acquis est conservé : ses fonctions concernées sont identiques par AST. Aucune nouvelle transcription ou génération n’a été lancée pour cette qualification.
Activation après sauvegarde/restauration privée des trois bases et comparaison exacte des lignes non volatiles Brain/ERP. Backend et assets HTTP vérifiés ; anciens assets conservés pour les onglets existants.
Aucun CR métier réel n’est publié, aucune tâche métier réelle créée et aucun microphone ouvert. Les publications et tâches de qualification utilisent des bases SQLite privées.
L12 reste ouvert pour les critères restants. Aucun amendement lié n’est proposé dans cette livraison ; les CR publiés ne sont pas réécrits.

[Audit, empreintes et preuves](../logs/foresight-runtime/L10-publication-PDF-qualification-ROOT-20261016.json).
