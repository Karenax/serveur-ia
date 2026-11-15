# Moteur mémoire EG2

## Fraîcheur canonique et profil multimodal séparé — 11 octobre 2026

Le rappel/recherche vérifie désormais l'éligibilité de la Source et la version
canonique de toute note ERP avant et après le calcul d'embedding. Une édition
invalide immédiatement l'ancien contenu ; une projection terminée trop tard ne
réintroduit pas une version périmée. Une réponse de chat dont le contexte a
changé reçoit un état obsolète. Les citations gardent leurs localisateurs réels
et les versions de provenance validée ne sont pas remplacées par la tête courante.

L'encodeur local complet EmbeddingGemma 2 utilise un runtime LiteRT isolé et un
profil SHA-256 détaillé (modèle/révision/runtime/prétraitements/modalités).
`storage/multimodal/index.db` conserve ses travaux, entrées, vecteurs et locators.
Il ne remplace pas `storage/eg2/index.db`. Texte, images PNG/JPEG et fenêtres WAV
mono 16 kHz sont pris en charge ; les longs audios sont convertis en fenêtres
de 30 s, avec les temps originaux conservés. Les PDF texte/tableurs gardent leur
extraction ; aucun OCR ou interprétation CAO n'est promis.

Chaque résultat contrôle droits, Source, version, empreinte et profil après
encodage de la requête. Annulation/reprise sont persistées, avec quotas et erreurs
visibles, sans purge. Le mode local de l'assistant peut combiner SQL et cet index
sans serveur d'embeddings distant ; la dégradation vers SQL est annoncée.
Les statistiques comptent les seuls passages visibles et toujours actuels ;
une mesure indisponible n'est pas remplacée par une estimation.

Les preuves réelles et limites de pertinence sont tenues dans
[38_FORESIGHT_DELIVERY.md](38_FORESIGHT_DELIVERY.md). Une recherche réussie sur
quatre documents fictifs ne qualifie pas une bibliothèque industrielle complète.

## Recherche unifiée

La rubrique **Recherche**, la barre supérieure et `/app/search` utilisent
`GET /v1/search`. Le service `app/services/unified_search.py` réutilise la
configuration et l'index de production EG2. Il lit l'index SQLite sans création,
migration ni réindexation. Un vecteur est calculé pour toute la requête, avec
20 secondes de délai maximal. Les passages sont comparés au texte canonique
courant, après l'appel distant : sources classées seulement, projet identique,
profil identique, empreinte du contenu identique, artefacts remplacés et audio en
attente exclus. Les connaissances invalidées/remplacées ne sont pas recherchées.

Le classement associe correspondance lexicale normalisée (casse et accents),
bonus aux expressions et références exactes, puis similarité EG2. Un seuil de
similarité minimal de 0,25 et une fenêtre de 0,12 sous le meilleur résultat,
bornée à 100 candidats, écartent le bruit purement sémantique ; ces paramètres
sont heuristiques et doivent être qualifiés sur des recherches métier réelles.
Une référence structurée contenant un chiffre impose une correspondance exacte
avec cette référence, y compris le code projet, et exclut les voisins sémantiques
sans correspondance. Une référence présente dans le document est prioritaire
sur son seul classement projet ; ce dernier porte le badge « Code du projet de
classement ». Le calcul local s'effectue hors de la boucle principale du serveur.
Le score n'est pas une confiance
ni une probabilité. Un résultat est regroupé par source, avec le passage lexical
le mieux adapté ou le passage sémantique le plus proche. Les connaissances SQL
restent recherchées par mots, avec distinction validation humaine/acceptation
par défaut et provenance consultable lorsqu'elle existe.

Filtres : projet Brain autorisé, type de source, dates inclusives (réception de
la source ou création de la connaissance). Résultats triés avant pagination de
25 éléments par défaut, extraits de 700 caractères maximum ; la consultation
ouvre le texte complet et le téléchargement existant dans l'inspecteur de source.
Le compteur d'indexation concerne les sources du périmètre avec une projection
de texte courante dans le profil configuré. Un index indisponible, un profil
incompatible, un vecteur invalide ou du texte non indexé produit un avertissement.
La recherche textuelle de secours est annoncée explicitement.

Cette étape recherche le texte extrait, y compris pièces jointes déjà extraites
dans les artefacts. Elle ne fournit pas encore de recherche visuelle native,
d'indexation de dossiers supplémentaires, ni de navigation à une page ou un
horodatage précis. Aucun changement des classifications ou des connaissances,
aucun service supplémentaire. Tests : `tests/test_unified_search.py` et
`web/src/components/SearchView.test.tsx`, en complément des contrats EG2 et des
droits de projets.

Qualification du 11 octobre 2026 : 58 tests Python ciblés finaux, 487 tests
React, Ruff et build conformes. La suite Python globale termine avec
1 786 réussites, 1 ignoré et un échec préexistant du classement des mails
(`test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`).
Elle a été lancée avant les derniers ajustements de pertinence et de calcul
local ; ces chemins finaux sont couverts par les tests ciblés. Sur 8001 : une
recherche réelle calcule le vecteur EG2, reconnaît les 897 sources indexées,
retrouve une référence exacte et permet la consultation de la source. Les
tests incluent panne réseau, profil incompatible, index absent, vecteurs
invalides, source changée durant l'appel, accents, classement documentaire
prioritaire sur le code projet, droits, dates et pagination. Les comptes et
classifications canoniques ont été comparés à la sauvegarde avant activation.
Preuves : `logs/search-activation-20261011-123128/qualification.json`,
`preservation.json`, `search-final.jpg` ; sorties de suites :
`logs/search-python-tests.txt`, `logs/search-final-targeted.txt`,
`logs/search-web-tests.txt`. Ces recettes ne constituent pas une mesure
comparative de qualité avec DigUp ni une qualification multimodale.

## Architecture

Agent fonctionne sur le serveur unique 8001. Sources et faits validés restent en base canonique. L’adaptateur `app/services/eg2_memory.py` indexe uniquement le texte des sources classées, sans extraction LLM ni graphe. EG2 distant (`http://192.9.110.115:1234`, modèle `text-embedding-embeddinggemma-2`) calcule les vecteurs. Le LLM déjà configuré rédige les réponses.

## Index et gouvernance

Index SQLite par défaut : `storage/eg2/index.db`. Filtre strict de projet, sources résolues, exclusion des artefacts remplacés et audio en attente. Aucun rappel ne valide une proposition. Les faits validés sont lus directement dans SQL et restent disponibles en cas de panne réseau, d’index indisponible ou de profil incompatible. Les preuves non recherchées sont alors signalées explicitement. Les changements de profil déclenchent une erreur explicite et exigent une reconstruction.

Paragraphes conservés intégralement ; paragraphes longs découpés en fenêtres de 160 mots avec recouvrement de 32 mots. Aucun caractère de fin n’est jeté. Le contexte utilise les passages pertinents avec leur provenance ; citations et passages sélectionnés sans troncature en caractères.

## Exploitation

Réglages → Mémoire : serveur EG2, modèle, chemin d’index, test réel sur index temporaire. `POST /v1/settings/memory/test` vérifie indexation, rappel et nettoyage. `GET /v1/settings/memory/engines` décrit l’état local, sans prétendre tester le serveur distant.

Les files d’indexation et de reprise persistent. La purge cible une référence du projet uniquement. La reconstruction repart des sources et faits canoniques sans les supprimer. Pour réindexer toutes les sources pendant un arrêt du backend : `python scripts/rebuild_eg2.py --backup C:/AgentBackups/eg2-nouvelle-reconstruction` ; le dossier doit être neuf. La base est sauvegardée avant toute modification des projections.

Tests : `tests/test_eg2_memory.py`, `tests/test_memory_recovery.py`, `tests/test_chat.py`, `tests/test_embedding_channel.py`.

La version du texte canonique est vérifiée au rappel : un index de texte remplacé est exclu avant sa réindexation. Les vérités déclassées et les extraits reprenant leur valeur exacte sont exclus du contexte. Une paraphrase différente reste une limite du filtre ; le déclassement ne garantit pas à lui seul l’absence de toute reformulation par le LLM.

## Migration du 11 octobre 2026

897 sources classées ont été réindexées en 16 180 passages, zéro échec et zéro attente.
Les 1 410 sources, 1 340 artefacts, 2 345 connaissances, 4 759 décisions de validation
et 2 374 liens de provenance sont identiques à la sauvegarde avant la remise en service.
11 projets et 11 mappings mémoire conservés. Les sources non classées restent hors index.
La sauvegarde et les historiques sont hors projet dans `C:/AgentBackups/eg2-migration-20261011-102725`.
Agent relancé par son superviseur persistant sur 8001 ; santé Agent/Brain/ERP et interface 200.

Mesures de cette migration réelle (897 sources, 16 180 passages) : réindexation avec reprise 21.6 minutes, dont dernier passage à quatre tâches 13.6 minutes ; index 280.87 Mio. Cela ne constitue pas une comparaison de modèles : le corpus et le découpage diffèrent des essais de laboratoire. RAM/VRAM du serveur distant non mesurées. Chat réel après remise en service : 13.985 secondes, réponse avec références numérotées toutes présentes dans le contexte.

Instantané après le chat réel : backend Agent entier à 211,73 Mio de RAM, pic processus observé 524,85 Mio (ERP et workers inclus). Ces chiffres ne mesurent pas EG2 isolément et ne sont pas comparables aux anciens essais de laboratoire. Le serveur distant d’embeddings et de génération reste hors mesure.

Validation de la migration : contrats EG2 finaux 6/6 ; suite React 481 tests
réussis et 2 tests du nouveau formulaire réussis ; build et Ruff conformes.
Suite Python globale : 1 777 réussis, 1 ignoré, 1 échec en 2 169,90 s.
L’échec préexistant `test_uneven_shared_sender_is_not_an_automatic_default_even_with_ai_hint`
concerne une règle de classement des mails non modifiée par cette migration.
Les tests ciblés du chat, de la mémoire, de la reprise et des archives passent.
La suite globale a démarré avant les dernières retouches ; les contrats EG2
et archives ont aussi été exécutés sur les fichiers finaux.
La livraison rassemble le moteur EG2, son interface et son exploitation documentée ; les données canoniques et les sauvegardes restent hors du dépôt Git.


### Indexation et navigation — 15 octobre 2026
Statistiques et préparation des réunions : Réglages → Autres réglages, dans deux rubriques distinctes. Sources → Indexation des projets affiche la couverture réelle du moteur EG2 configuré, vérifiée par profil et empreinte de contenu, dans le périmètre accessible.
Le classement des mails et les imports alimentent déjà automatiquement EG2 réseau ; les vecteurs restent stockés dans l’index SQLite local. Aucun dossier réseau n’est parcouru. En mode réseau, la recherche de contenu dans Sources réutilise la recherche EG2 habituelle et ne démarre aucun encodeur local. L’index multimodal local reste réservé au mode local explicite ; il n’est ni démarré ni repris en mode réseau. Sa maintenance avancée reste accessible dans les réglages de recherche. Les anciens signalements de quota restent consultables, sans altérer les sources ni les classements.
L’API GET /api/v1/workspace/indexing est en lecture seule et distingue indexées, en attente, en échec, manquantes et sans texte. Tests ciblés de navigation, recherche et indexation ; compilation frontend.


### Recherche et préparation qualifiées ; lexique non généralisé — 16 octobre 2026

La recherche unifiée est vérifiée sur trois sources fictives privées avec le vrai
encodeur réseau déjà chargé : « retard livraison » retrouve le décalage de trois
semaines par le seul sens ; les mots éclairage/350lux et la référence choisie
retrouvent la bonne fiche. La référence exacte exclut les voisins. L'index reste
identique par SHA pendant les trois recherches, les trois Sources restent
conservées et aucune connaissance validée n'est créée. Les15contrats applicables
du global backend restent acquis sur sources inchangées, sans nouvelle suite.

La préparation privée termine puis relit son état dans une nouvelle session SQL,
se réouvre et garde transcription/proactif/enrichissement désactivés. Le lecteur
ne peut pas la modifier. Les9contrôles UI acquis sont reliés à leurs sources
inchangées ; la sauvegarde et le bloc de préparation restent identiques au
préimage qualifié. Les diagnostics distinguent installation, chargement et
réponse réelle, y compris l'échec et la reprise, sans déduire une qualification
matérielle d'un modèle présent.

F16 et F20 sont clos selon leurs fonctions du plan.16fonctions sur25,9lots sur13
et11recettes sur17 sont clos. L02/L03/L11/L12 restent ouverts.

Le comparatif CPU de lexique dure28,94s sur trois WAV connus et un silence
fictif existant : consignation corrigée dans le bruit, témoin1250W/350lux exact
et silence sans texte ; dans le chevauchement, la réserve client reste omise et
« commande manuelle » disparaît aussi. Il s'agit d'un essai de développement,
pas d'une validation aveugle. Aucune promotion de profil : les défauts anciens
et le nouveau résultat défavorable restent conservés. Aucun microphone, LLM,
GPU, téléchargement ou donnée métier dans cet essai CPU ; il n'a modifié aucun
poids, réglage ou source produit. Aucun autre essai identique à relancer.
