# Niveaux de connaissance

## État actuel — 11 octobre 2026

Depuis le 8 octobre, les informations issues d'une source résolue du même projet peuvent être retenues par défaut : `validated_by=auto-default`, `validation_mode=default`. Elles sont distinctes des confirmations humaines. `project_attach` reste exclu de cette acceptation automatique. Une contradiction ne remplace pas silencieusement une confirmation humaine ; les décisions et versions restent auditables. Le canon est commité avant toute projection mémoire.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Niveau A — Vérité validée
Information active dans le canon SQL, avec son mode de validation : confirmation humaine ou information retenue par défaut depuis une source résolue. Le statut `validated` indique son usage dans la connaissance ; il ne suffit pas à prouver une confirmation humaine.

Exemples :
- date de livraison confirmée ;
- exigence client validée ;
- décision technique actée ;
- budget de référence ;
- jalon officiel.

Règles :
- stockée canoniquement dans Project Brain ;
- versionnée ;
- jamais écrasée ;
- interrogeable par tous les agents autorisés ;
- changement = nouvelle version + lien `supersedes` ;
- déclassement/restauration auditables sans suppression de la source ;
- mode de validation visible dans les API et le contexte de l'assistant.

## Niveau B — Information proposée
Information non encore retenue ou nécessitant une décision particulière :
- extraction IA dont la source n'est pas résolue ou dont l'acceptation n'est pas admissible ;
- nouvelle demande client ;
- contradiction ;
- hypothèse ;
- rattachement projet incertain ;
- proposition d'action.

Règles :
- visible avec niveau de confiance ;
- toujours liée à la source ;
- peut être utilisée comme contexte secondaire ;
- ne doit jamais être présentée comme vérité sans qualification ;

## Niveau C — Sources brutes
Preuves :
- audio ;
- vidéo ;
- e-mail MIME ;
- pièce jointe ;
- PDF ;
- Word ;
- image ;
- fichier 3D ;
- transcription ;
- logs d'ingestion.

## Niveau D — Interprétations temporaires et mémoire dérivée
- résumés ;
- clusters ;
- embeddings ;
- passages et scores de recherche EG2 ;
- sorties d'analyse métier non encore retenues ;
- réponses d'agents ;
- caches ;
- mémoire de session.

## Séparation `evidence` / `truth`
- `evidence` recherche les passages des sources résolues dans l'index SQLite EG2 ;
- `truth` lit les connaissances actives du niveau A dans le canon SQL.

L'index est dérivé et reconstructible, sans copie vectorielle de la vérité. Le rappel revérifie l'appartenance des sources au projet et exclut les textes remplacés. En cas d'indisponibilité EG2, les faits SQL peuvent rester disponibles, avec un avertissement explicite sur les preuves non recherchées.

Cette séparation permet de demander explicitement :
- « donne-moi uniquement la vérité validée » ;
- « cherche également dans les éléments non validés et les sources ».

## Politique de réponse des agents
Chaque réponse doit pouvoir qualifier l'information :
- `validated`
- `proposed`
- `source_only`
- `derived`
- `unknown`

Les citations de vérité précisent « retenue par défaut » ou « confirmation humaine » ; les citations de preuves restent du contexte à vérifier. Une réponse ou un score de similarité ne valide pas une nouvelle information.

En cas de conflit, l'agent doit exposer le conflit plutôt que choisir silencieusement.
