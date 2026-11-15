# Avis explicites sur les réponses de réunion

Livraison du 16 octobre 2026 sur Agent 8001. Complément aux statistiques du lot
L11 ; L02/L03/L11/L12 et la recette hors ligne actuelle restent ouverts.

## Parcours

Dans **Réunions → séance → Assistant**, chaque réponse identifiée de la Discussion
et des Questions en direct propose **Utile** et **Pas utile**. Le bouton sélectionné
porte un état pressé accessible au clavier. Recliquez dessus pour retirer l'avis.
L'enregistrement affiche l'indicateur de travail commun. Un échec conserve l'avis
affiché et les saisies ; un ancien retour d'historique ne remplace pas l'avis reçu.

Un avis porte sur la réponse conservée. Il ne valide aucune information métier,
ne publie pas de compte rendu et ne modifie ni la note ni la transcription.
Une réponse historique obsolète garde son avertissement et peut être évaluée.
L'utilité est un avis humain, pas une garantie de précision du modèle.

La séance partage **le dernier avis explicite**, quel que soit l'opérateur ayant
émis l'avis. L'auteur et tous les changements restent enregistrés. Ce mécanisme
ne calcule ni une moyenne de votes, ni un taux automatique de qualité.

## API et conservation

```text
PUT /api/v1/meeting-sessions/{sid}/answers/{answer_kind}/{answer_id}/feedback
{"useful": true | false | null}
```

`answer_kind` vaut `ask` ou `live`. Le corps refuse les propriétés supplémentaires,
les chaînes et les nombres à la place d'un booléen. `null` retire l'avis.
Les droits d'écriture de la séance et les droits courants des sources citées sont
vérifiés. Une réponse inaccessible ou appartenant à une autre séance ne peut pas
être évaluée. L'identité de l'opérateur provient du serveur.

Le service `app/services/assistant_feedback.py` ajoute des événements
`assistant.answer-feedback` dans le journal de séance existant, avec la réponse,
son type, l'événement d'origine et l'opérateur. Aucun schéma SQL nouveau.
La réponse du modèle reste immuable, ainsi que la révision de contenu de la
séance. Les répétitions du même avis n'ajoutent pas de doublon. L'avis de discussion
et celui du direct restent distincts, même si leurs identifiants sont identiques.
L'historique et les réponses rejouées restaurent le dernier avis enregistré.
Les exports de séance du propriétaire conservent ces événements avec le journal.
L'export à périmètre restreint conserve l'enveloppe et expurge leur contenu selon
les règles existantes ; cet ajout n'élargit pas les droits d'export.

## Statistiques

Dans **Réglages → Autres réglages → Statistiques**, l'affichage distingue :

- réponses jugées utiles : dernier avis explicite `true` ;
- réponses jugées pas utiles : dernier avis explicite `false` ;
- réponses évaluées : somme des deux catégories, une fois par réponse ;
- avis retiré : absent de ces trois compteurs, historique toujours conservé.

Les réponses dont les citations ne sont plus accessibles sont exclues de ces
compteurs. Une absence d'avis donne zéro réponse évaluée, sans jugement implicite.
La source des formules est retournée par l'API des statistiques. Le complément55mesure maintenant les tokens réellement fournis, avec leur
couverture ; l'historique sans mesure reste indisponible, sans économie inventée.
Les latences enregistrées restent des temps serveur, distincts d'un P95 d'affichage.
F19 n'est pas déclaré entièrement clos par ce seul ajout.

## Qualification et activation

Le premier passage backend conserve 32 réussites et deux échecs de fixtures
d'index incomplètes ; les six cas du nouveau service passent après correction.
Les 28 autres cas réussis restent acquis sur code inchangé. Un avertissement de
dépréciation TestClient est conservé. Les cohortes se recouvrent.

Les 121 contrôles frontend passent, puis les deux contrôles Stats sont revérifiés
avec le compteur explicite. Les quatre nouveaux cas Studio passent après retrait
d'options de test non reconnues par TypeScript. L'échec TypeScript initial est
conservé ; le contrôle final, Vite et Ruff réussissent. Les refus sandbox d'esbuild
restent distincts de ces résultats ; aucune ACL ou protection Windows modifiée.

Dans le vrai navigateur sur deux bases privées, les boutons enregistrent un avis
utile et un avis pas utile. Le retrait du premier fait passer le compteur de
1 utile / 2 évaluées à 0 / 1 ; le brouillon riche demeure intact. Les trois avis
sont retrouvés en SQL, les deux réponses initiales et les notes de version 1 sont
conservées, sans tâche ou CR créé. Le navigateur ne permet pas la capture d'image
à cet instant ; preuve DOM et SQL conservée, aucune mesure visuelle fine déduite.
Les onglets temporaires et le serveur privé se ferment ; aucun modèle ou microphone.

Sauvegardes Brain/ERP/EG2, restaurations privées et intégrités vérifiées avant le
redémarrage supervisé. Les 23 tables Brain comparées restent exactes ; sur les
68 tables ERP comparées, seules deux tables de suivi présentent des changements
de progression ou de dates, sans retrait d'identifiant. Les écarts bruts sont
conservés. Les anciens assets restent disponibles et les nouveaux octets servis
sur 8001 correspondent à la compilation. Aucun onglet utilisateur rechargé.

Pièces : `.ui-preview/l11-feedback-20261016/`,
`logs/foresight-runtime/L11-answer-feedback-ROOT-20261016.json` et matrice courante
`docs/40_FORESIGHT_ACCEPTANCE.md`. La suite globale backend déjà acquise n'est pas
rejouée : le delta de trois fichiers modifiés et deux nouveaux fichiers est isolé
et les chemins ASR, génération, capture et publication existants restent inchangés.


### Tokens réellement fournis par le moteur — 16 octobre 2026

Les réponses conservées de la Discussion et des Questions en direct gardent les
compteurs du fournisseur. Les tentatives reprises sont conservées, y compris une
absence de mesure. Stats affiche la somme connue et sa couverture complète,
partielle ou absente. Aucun calcul depuis le texte, économie ou prix estimé.
Les quatre réponses historiques restent sans mesure. Ce compteur de réponses
ne devient pas une comptabilité de tous les modules ou des échecs non conservés.

201contrôles ciblés passent avec un avertissement TestClient ; frontend2,
TypeScript, Vite et Ruff réussissent. Le contrôle réel sur notes fictives privées
utilise le modèle réseau déjà chargé :176tokens de contexte+27de réponse=203,
même reçu après rejeu et Stats203. Bases privées intègres, Gemma local déchargé
avant/après, aucun microphone ou téléchargement. Comparaison AST : transport,
paramètres et repli identiques après retrait des seuls contextes d'observation ;
les sept autres fonctions du client sont identiques.

Activation8001 après sauvegardes/restaurations privées Brain/ERP/EG2. Les91tables
non volatiles comparées sont exactes à la vérification après redémarrage. Une
lecture ultérieure distingue les statuts/avertissements/dates de suivi qui
continuent d'évoluer, sans retrait d'identifiant. Assets servis conformes et
anciens conservés. Sceau hors ligne r5 rebasé sur462sources sans nouvelle coupure.

F19 est clos selon la fonction Stats/diagnostics du plan : sources/index, durée/
pistes/retard, avis humains, temps serveur, compteurs fournis et formules.
Il ne qualifie pas le P95 d'affichage ou le fonctionnement hors ligne complet.
9lots sur13,14fonctions sur25 et11recettes sur17 sont clos ; L02/L03/L11/L12
restent ouverts. Détail : `docs/55_FORESIGHT_TOKEN_USAGE.md`.
