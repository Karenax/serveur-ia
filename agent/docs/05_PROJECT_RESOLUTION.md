# Suggestions et résolution humaine du projet

## État actuel — 30 septembre 2026, Agent 0.3.0

Politique actuelle : suggestions seulement, auto=false même avec un code explicite ou un indice IA. Le choix manuel de projet à l’import et la validation/reclassification sont des décisions humaines. Les codes proches sont délimités.

Références actuelles : [contexte](../PROJECT_CONTEXT.md), [exploitation](../README_BACKEND.md), [corrections et preuves](19_AUDIT_REMEDIATION.md). Les sections de conception ci-dessous doivent être lues avec cet état.

## Références explicites — correction du 5 octobre 2026

La suggestion d’import utilise désormais le projet et le score déjà détectés,
au lieu d’afficher systématiquement un projet indéfini à 30 %. Le code peut
être entouré de tirets/underscores de séparation, notamment
`PO-26-01872-AIRB25LTH0806-A-Votre colis` et `AIRB25LTH0806-A_CORRECTION`.
Les références incluses dans un mot ou prolongées par un suffixe compact
(une ou deux lettres) ou numérique restent exclues : `XAIRB25LTH0806-A`,
`AIRB25LTH0806-A-AB` et `AIRB25LTH0806-A-4` ne désignent pas le code de base.
La recherche ignore la casse et porte sur l’objet et le corps complet stocké.

Un alias déclaré contenant lettres et chiffres vaut référence explicite
(`explicit_alias`, score 0.9) ; un alias textuel demeure un indice contextuel
(`alias`, score 0.4). Les références explicites priment sur les indices IA
et sur l’accumulation de mots-clés. Les codes proches ne sont jamais fusionnés
par ressemblance : une référence alternative doit être déclarée.

La reprise `scripts.refresh_mail_references` sauvegarde avant écriture et ne
remplace que les propositions en attente vers un unique projet référencé.
Les décisions validées et les conflits de références sont préservés.

## Invariant
Aucune information durable n'est considérée traitée tant que `project_id` n'est pas résolu.

## Signaux de résolution
Ordre indicatif :
1. référence projet explicite ;
2. identifiant dans sujet/fichier ;
3. thread déjà lié ;
4. expéditeur + client + contacts projet ;
5. participants ;
6. pièces jointes ;
7. termes techniques spécifiques ;
8. proximité temporelle avec réunions/événements ;
9. similarité sémantique ;
10. historique récent du contact.

## Score
Le moteur produit :
- candidats ;
- score ;
- explications des signaux ;
- niveau de confiance.

Exemple :
```json
{
  "candidates": [
    {"project_id":"P26-0148","score":0.91,"reasons":["sender_customer","thread_history","technical_terms"]},
    {"project_id":"P26-0201","score":0.42,"reasons":["same_contact"]}
  ]
}
```

## Politique
- score élevé + règles déterministes cohérentes : suggestion à confirmer ;
- zone grise : proposition ;
- conflit : validation obligatoire ;
- aucun candidat : source resolution_pending sans projet, jamais injectée dans la mémoire projet.

## Apprentissage
Le classement utilise `app/services/mail_learning.py`. Les mails actuellement
classés par l’humain et les connaissances validées forment des profils de projet
recalculés à chaque import/lot. Aucune proposition non validée ne renforce ses
propres critères ; DIVERS et les sources écartées sont exclus.

Les expéditeurs et destinataires sont des adresses exactes normalisées. Leur
poids dépend du nombre d’exemples et de leur répartition entre les projets.
Un expéditeur exclusif vaut 0.42 après un mail validé, 0.62 après deux et 0.8
à partir de trois ; le poids d’un expéditeur partagé est plafonné à 0.5.
Les domaines restent faibles (0.12 maximum), les destinataires spécifiques
peuvent compléter le signal (0.25 maximum). Le fil MIME déjà validé, l’objet
normalisé, les thèmes distinctifs, contacts déclarés, nom du projet et noms
des pièces jointes enrichissent les candidats. Les mots génériques et l’historique
cité/signature repérable ne nourrissent pas le vocabulaire appris.

Les références explicites gardent la priorité, avec l’objet avant le corps.
Deux références au même niveau rendent le choix ambigu. Hors référence, le
meilleur candidat doit atteindre 0.75 avec au moins 0.12 d’avance ; les contacts
partagés nécessitent une information discriminante (thème, fil, destinataire
spécifique confirmé, etc.). Les scores contextuels sont plafonnés à 0.89 et
restent heuristiques. La validation est toujours humaine.

Un reclassement déplace l’exemple vers le projet actuellement choisi ; une
exclusion retire son apport. Aucun profil persistant ni entraînement des poids
du LLM : l’apprentissage concerne les associations et thèmes du projet.
Les profils sont exposés par `/v1/triage/learning`, et les contributions lisibles
par `/v1/triage/queue`. Tests : `tests/test_mail_learning.py`, `tests/test_triage.py`.
