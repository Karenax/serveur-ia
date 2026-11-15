# Pipelines d'ingestion

## Pièces jointes des mails — 4 novembre 2026

Une preuve issue d’une pièce jointe appartient à la **Source mail**, et donc
au projet auquel ce mail est classé. Aucun projet parallèle ni copie de
classement n’est créé. `projections.process` prépare ces preuves avant EG2,
pour les imports, classements, reprises et reconstructions. Les mails à
rattacher ou écartés sont exclus. Le projet et l’état courant sont revérifiés
sous verrou SQL après l’extraction, puis après le calcul des vecteurs.

L’original MIME est relu dans `storage/raw/<sha256>.eml` et son empreinte est
vérifiée. Les parties jointes et parties nommées, y compris inline, sont lues
avec les mêmes indices que le téléchargement des pièces jointes. Un nom
MIME ne devient jamais un chemin de destination. Les pièces restent dans le
mail original ; seuls textes dérivés et reçus d’extraction sont ajoutés.

Formats textuels : PDF, DOCX, XLSX/XLSM (feuille et plage), PPTX (diapositive),
TXT/MD/CSV, HTML, ICS, XML/JSON/LOG. Les ZIP sont ouverts en lecture, avec au
plus 200 fichiers, 100 Mio décompressés cumulés, 50 Mio par entrée et deux
niveaux d’archives. Les membres ne sont jamais extraits sous leur propre
chemin ni exécutés. Les formats anciens DOC/XLS/PPT, archives RAR/7z et médias
audio/vidéo n’ont pas de lecteur ajouté par cette évolution.
Les images incorporées dans DOCX/PPTX passent aussi par l’OCR et gardent
leur chemin de membre Office. Les HTML complets sont lus comme du texte,
sans script, style ni chargement de ressource. Les dimensions de mise en
forme Excel ne comptent pas comme des cellules de données ; lignes et
cellules effectivement lues restent bornées. Pour les PDF que pypdf ne
peut décoder, le lecteur PDFium du runtime local déjà installé est essayé
en sous-processus avec les mêmes limites ; il ne contourne aucun mot de passe.

Les lecteurs tournent dans le sous-processus existant limité à 90 secondes
et 1 Gio ; l’import est borné à 50 Mio, le texte à 2 millions de caractères
par fichier et 10 millions par mail. Les images et pages PDF sans texte sont
proposées à l’OCR Windows français/anglais avec le moteur déjà installé.
L’OCR conserve son moteur/langue dans les repères. Un OCR indisponible reste
`ocr_required`, y compris pour un membre d’archive ; du texte vide
après reconnaissance reste `empty`. Aucune lecture visuelle complète ni
interprétation de dessin technique n’est revendiquée.

Les textes sont conservés en `attachment_text` avec nom, indice MIME,
empreinte et repères. Les fichiers illisibles, chiffrés, trop volumineux ou
non pris en charge ont un `attachment_status`. Le récapitulatif par mail
est dans `source_metadata.attachment_extraction`. Les tentatives ne créent
pas de doublons ; un changement d’interprétation marque les anciens passages
hors usage sans supprimer les originaux. Les classements et informations
validées ne sont pas modifiés par la reprise.

La recherche et l’assistant consomment les textes canoniques du mail et leurs
repères. Les embeddings restent distincts de l’extraction et de la validation
humaine. L’échec d’un fichier n’empêche pas d’indexer le corps et les autres
pièces ; il reste déclaré dans les états d’extraction. Une panne du serveur
d’embeddings conserve la projection à reprendre.

Reprise des existants : `scripts/index_mail_attachments.py --backup <nouveau-dossier>`
effectue des sauvegardes SQLite vérifiées de Brain et de l’index actif,
parcourt les mails résolus, extrait les pièces et réveille leur projection
par l’état `pending`. Le worker mémoire déjà présent sur **8001** reprend
ces projections. `progress.json` et `errors.json` du dossier de sauvegarde
suivent la reprise ; la fin de ce script ne prouve pas la fin des embeddings.
La recette isolée couvre texte exclusif à une pièce jointe, OCR simulé,
tableur, ZIP et chemins piégés, formats illisibles, idempotence,
reclassement concurrent et réutilisation des vecteurs par profil.

## État actuel — 11 octobre 2026

Uploads EML/audio et CDC limités à 50 MiB ; texte complet conservé et original consultable.
Le parcours réunion des Revues comporte transcription automatique locale,
séparation des interlocuteurs, relecture puis synthèse LLM ; son fonctionnement réel dépend de l'état du moteur audio et doit être vérifié séparément : voir
[23_MEETING_AUDIO.md](23_MEETING_AUDIO.md). L’import audio avec transcript manuel
est conservé. L’OCR automatique reste un objectif. Les opérations bloquantes sont
hors event loop ; les travaux audio sont persistés et exécutés en arrière-plan.

Le Studio complète ce parcours par une capture directe durable, navigateur ou
Windows, avec pistes micro/système explicites. Les imports audio restent bornés
à 50 MiB ; une capture cumule au plus 512 MiB et 120 minutes. Fragments, empreintes,
acquittements et commandes permettent reprise et consolidation sans effacer
les originaux. Une séance sans projet peut conserver et traiter son staging ;
la projection de preuves dans un projet exige toujours le rattachement final
et une Source admissible. Ni staging ni brouillon de bibliothèque ne valide
une information de projet.

La transcription directe reste provisoire, avec relecture ; les étiquettes de
piste ne prouvent pas l'identité des interlocuteurs. Le moteur batch hérité est
conservé et l'admission CPU évite sa concurrence avec la capture directe.
Qualité/latence industrielles et capture matérielle restent des qualifications
distinctes. Les Notes ERP sont sauvegardées avant leur projection par outbox
ERP11/reçu Brain, sans dépendance à une génération LLM. Voir
[audio et quotas](23_MEETING_AUDIO.md),
[Notes et projection](34_XPILOT_DOCUMENTS_NOTES_SIGNATURES.md) et
[recettes, activation et limites](38_FORESIGHT_DELIVERY.md).

La bibliothèque distingue le **type de source** (document, mail, note, réunion)
du **format du fichier** (PDF, PNG, TXT, DOCX, XLSX, CSV, audio…). Le MIME reconnu
fait autorité ; un suffixe compatible précise le format, et le nom du fichier
conservé sert de repli si le MIME est absent ou générique. Un MIME explicite non
reconnu reste sans format reconnu. Les Notes structurées et les transcriptions
sans fichier ne deviennent pas des PDF ou des fichiers texte par leur titre.
Cette indication de métadonnées ne prouve ni le décodage ni l'indexation.

Google Drive est **exclu du périmètre demandé par l'utilisateur** depuis le
11 octobre 2026. Le connecteur Foresight est masqué et refusé par défaut :
`foresight.drive_enabled` doit être strictement `true` pour l'admettre.
L'absence de cette clé ou un ancien jeton ne l'active pas. Les imports
fichier/dossier/URL et le calendrier ICS local restent disponibles ; code,
jetons, fichiers et versions historiques Drive sont conservés. Aucun réglage
canonique ni connexion Google n'est créé pour appliquer cette exclusion.
Voir [décision de périmètre](../logs/foresight-runtime/user-scope-decision-20261011-drive-visual.json)
et [contrat API](07_API_EVENTS_MCP.md).

Depuis Sources, **Nouvelle séance** ouvre le formulaire existant de Réunions
avec le projet accessible choisi, ou « À rattacher ». Cette préparation ne
crée aucune séance avant validation du formulaire et ne démarre aucun micro :
le lancement de l'enregistrement reste une action explicite dans le Studio.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Contrat commun d'entrée

`SourceEnvelope` décrit le contrat commun de conception des connecteurs ; les formats concrets d'entrée et champs effectivement acceptés sont définis par les schémas et routes d'Agent :
- `source_type`
- `captured_at`
- `sender`
- `recipients`
- `participants`
- `channel`
- `binary_uri`
- `raw_text`
- `external_message_id`
- `phone_call_id`
- `meeting_id`
- `metadata`
- `candidate_projects[]`

Puis le pipeline commun de résolution des Sources de projet, distinct du
staging de séance :
1. idempotence ;
2. stockage brut ;
3. hash ;
4. extraction texte/média ;
5. résolution identité ;
6. résolution projet ;
7. analyse IA ;
8. comparaison à la mémoire existante ;
9. création de propositions ;
10. conservation des informations admissibles par défaut ou demande de décision, selon leur provenance et leur statut.

L'indexation EG2 est une branche distincte après résolution du projet : texte canonique courant → passages → vecteurs distants → index SQLite. Elle ne nécessite pas de passer par l'analyse LLM. Les longs paragraphes sont découpés avec recouvrement ; aucun texte de fin n'est supprimé par une limite de caractères. Le texte complet et l'original restent consultables.

La file d'indexation persiste, reprend les échecs et remplace atomiquement les passages d'une source une fois les nouveaux vecteurs calculés. Une panne distante ne supprime pas le canon. La provenance et le rattachement sont contrôlés avant la projection puis après le calcul, ainsi qu'au rappel.

## Branche téléphone
Capturer :
- entrant/sortant ;
- numéro ;
- contact résolu ;
- heure début/fin ;
- fichier audio ;
- participants si conférence ;
- transcription par locuteur ;
- segments horodatés ;
- résumé ;
- éléments proposés.

Important : l'enregistrement dépend des capacités OS/appareil/politique d'entreprise et du cadre légal applicable. Le cœur doit accepter plusieurs méthodes de capture sans dépendre d'une seule implémentation mobile.

## Branche réunions
Réutiliser exactement le moteur audio :
- source = fichier audio/vidéo ;
- diarisation ;
- participants ;
- transcription ;
- analyse.

Ajouter :
- titre ;
- invitation/calendrier si disponible ;
- liste des participants ;
- documents présentés.

## Branche e-mail
Conserver :
- message original ;
- Message-ID ;
- thread ;
- expéditeur/destinataires/CC ;
- date serveur ;
- sujet ;
- corps texte/HTML normalisé ;
- pièces jointes ;
- liens ;
- signatures détectées.

Traiter :
- classification ;
- résolution projet ;
- demandes ;
- engagements ;
- dates ;
- actions ;
- contradictions avec la vérité existante ;
- opportunité de réponse.

## Branche documents
PDF/Word/Excel/PowerPoint/images :
- extraction native en priorité ;
- OCR si nécessaire ;
- conserver structure pages/tableaux ;
- vision pour schémas ;
- métadonnées ;
- version ;
- auteur/date si fiable.

## Branche CAO / 3D
V1 :
- indexer nom, type, taille, version, chemin, projet, auteur ;
- extraire métadonnées disponibles ;
- générer aperçu visuel si possible.

V2 :
- parser assemblages/nomenclatures ;
- propriétés pièces ;
- dimensions ;
- matériaux ;
- attributs ;
- relations avec exigences.

Ne pas faire dépendre le cœur d'un format CAO unique.

### Règle
Aucune source en `resolution_pending` ne doit être injectée dans l'index d'un projet. Seules les sources `resolved` sont admissibles ; les artefacts remplacés et `audio_pending` sont exclus. Une reconstruction repart de ce canon sans changer les classifications ni les décisions.
