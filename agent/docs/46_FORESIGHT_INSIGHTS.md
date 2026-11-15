# Relations et statistiques vérifiables

## Graphe

GET `/api/v1/workspace/source-graph` accepte `offset >= 0` et `limit` de1à500.
La taille limite une page HTTP, pas le nombre total de sources explorables. La vue
utilise des pages de200sources et propose Précédentes/Suivantes. Les sources sont
triées par projet et identifiant pour stabiliser les pages ; un changement de
périmètre ou de présentation revient au début. Chaque page inclut tous les liens
de provenance de ses sources, sans l’ancienne coupure au nombre de sources.

Le retour fournit offset, limit, total, has_next et page_provenance_complete.
Seuls l’appartenance au projet et les liens de citation réellement enregistrés
sont présentés. Une citation croisée entre projets ne suffit pas à élargir les
droits. Aucun lien sémantique n’est inventé.

## Compteurs

Sources indexées correspond à l’union des identifiants avec passages EG2 de profil
et contenu actuels ou entrées multimodales terminées de profil et empreinte actuels.
La même source présente dans les deux index n’est comptée qu’une fois. Les anciens
reçus `projection_receipts_indexed` restent disponibles séparément dans l’API.
Si une couverture est illisible, `indexed_sources` vaut null plutôt qu’un zéro
présenté comme certain. Aucun index absent n’est créé pour lire sa couverture.

Les pistes sont comptées en fragments. La durée de séance reste le maximum de
start_ms+duration_ms par séance, additionné sur les séances visibles : deux pistes
simultanées ne doublent pas cette durée. Le volume audio est la somme des tailles.

Audio direct en attente additionne les durées des fragments mic/system de0à10secondes
qui portent l’état pending/running dans une séance visible non annulée. Deux pistes
représentent deux travaux et sont additionnées pour cette charge. L’âge du fragment
est mesuré depuis sa conservation ; ce n’est pas une mesure de retard visible.
Les états de tous les fragments restent présents dans `transcription.by_status`.

Les percentiles de réponse utilisent uniquement des durées numériques finies
positives ou nulles ; booléens, valeurs négatives, NaN et chaînes sont exclus.
Le nombre de mesures est exposé. L’utilité des réponses n’est pas instrumentée :
`useful_answers=null`. Les tokens restent null sans instrumentation. Aucune
économie financière ou qualité utile n’est déduite du simple nombre de réponses.
Toutes les formules sont disponibles dans l’API et les compteurs restent bornés
par les droits de projet/séance existants.

## Vérification et état des lots

15contrôles backend ciblés passent, dont4nouveaux cas de pagination, index réel,
index illisible et mesures audio/réponse ; un cas HTTP additionnel vérifie la
pagination et les valeurs refusées. Ils utilisent des bases privées et aucun modèle.
Le frontend initial compte31réussites et1échec d’assertion dû au nouvel argument
offset. Ce cas est corrigé et rejoué seul :1réussite,25cas volontairement ignorés.
Les2nouveaux cas d’interface sont dans les31réussites. Pas de total global inventé.
TypeScript, Vite et Ruff passent.

Le serveur8001 activé est contrôlé par HTTP : tous les identifiants visibles du
graphe sont parcourus une seule fois jusqu’à has_next=false ; toutes les arêtes
aboutissent à des nœuds visibles. Les statistiques et assets servis sont vérifiés.
Les sauvegardes récentes sont réutilisées uniquement après validation de leur
empreinte et comparaison exacte des données non volatiles Brain/ERP avant/après.

L09 reste ouvert pour les capacités de recherche encore non qualifiées. L11 reste
ouvert pour la qualification complète de la chaîne hors ligne actuelle et de sa
préparation ; ces compteurs ne prouvent pas un fonctionnement sans réseau.
L12 reste ouvert. Aucun microphone, GPU, modèle, réindexation métier, commit ou push.

Preuve : `logs/foresight-runtime/L09-L11-insights-completeness-ROOT-20261016.json`.

Le parcours du graphe201–400/976 et les nouveaux compteurs ont aussi été inspectés dans le navigateur. Capture locale : .ui-preview/insights-completeness-20261016/statistiques-actuelles.jpg. Aucun changement de configuration ni de donnée métier.

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

