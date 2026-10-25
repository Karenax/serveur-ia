# Compréhension sémantique de la recherche vocale — 24 octobre 2026

Le premier raccordement exigeait des formulations reconnues par une expression
régulière. « cherche internet la dernière actualité sur l’IA » et une phrase
commençant par « sur Internet… » pouvaient donc arriver à Qwen sans recherche.
Les anciennes réponses affirmant une absence d’accès au web pouvaient aussi
orienter les réponses suivantes. Le test initial du 23 octobre vérifiait une
formulation explicite unique et n’avait pas couvert ces cas.

## Fonctionnement corrigé

Chaque tour vocal passe par une courte décision du Qwen local, sans réflexion :
répondre directement, rechercher une information publique, ou demander le sujet
manquant. Aucun test par mot-clé, expression régulière ou liste de formulations
ne sélectionne la recherche. La décision JSON est validée côté serveur ; seul un
choix `search` avec une requête bornée peut atteindre les outils web.

La décision est calculée sous la même file d’inférence et les mêmes droits que la
réponse. Elle reçoit la dernière demande et au plus deux messages récents, bornés,
pour comprendre le contexte ; ni les consignes système ni les documents rappelés
ne lui sont transmis. Ce calcul reste local. Seule la requête publique reformulée
est envoyée au moteur web. L’historique complet n’est pas transmis au fournisseur.

Les capacités web sont expliquées à Qwen et les résultats réellement obtenus sont
présentés comme disponibles pour la réponse actuelle. Les anciens refus du modèle
ne font plus autorité sur les capacités. Les erreurs et les recherches vides
restent signalées ; une page non lue reste identifiée comme extrait de recherche.

Les outils `web_search` et `web_extract` Hermes existants restent utilisés sans
agent Hermes. La réponse Qwen continue sa lecture progressive. Droits Web,
annulation, révocation, URLs publiques et contexte vocal 16k restent contrôlés.
Le correcteur et le chat écrit gardent leur parcours.

## Vérifications et coût

Le Qwen réel a réussi les 14 cas du corpus conservé dans
`semantic-validation.json` : formulation signalée, demande indirecte, actualité
sans mention d’Internet, météo, sujet manquant, capacité seule, explication
générale, refus du web, documents privés, calcul, salutation, texte à reformuler
et fin de conversation. Ce corpus ciblé n’est pas une garantie universelle de
compréhension. La décision a pris environ 4,6 à 5,2 secondes sur ces essais ; ce
coût s’ajoute aussi aux questions qui ne nécessitent aucune recherche.

L’essai intégré suivant a mesuré 1,407 s pour cette décision avant la recherche,
et 1,047 s pour une demande de précision sans recherche. Les temps varient selon
le contexte et le cache ; ils ne constituent pas une promesse de délai constant.
La formulation signalée a produit une réponse fondée sur trois sources publiques,
dont deux pages lues, malgré un ancien refus artificiel dans les échanges de test.
Le premier texte est arrivé en 43,5 s pour cette recherche complète. Sans sujet,
la réponse demande ce qu’il faut rechercher au lieu de nier l’accès au web.

`test_voice_web.py` couvre le contrat de décision, l’absence de mots-clés requis,
les appels effectifs, la clarification, l’annulation pendant la décision, les
sorties invalides, les droits et la révocation. Les suites de voix et de correcteur
sont également rejouées. `validate_native.py` teste de vrais tours sur un compte
temporaire, y compris un ancien refus artificiel du modèle, avec les vrais outils
web et Qwen. Les essais n’utilisent aucun microphone ni lecture audio utilisateur.

L’activation reste côté serveur, avec le client Windows 3.5.41 existant. Les sources
et données en cours, les processus Qwen, les clés, les historiques et les réglages
de sauvegarde sont préservés. Les changements de nom Kiara en cours sont conservés.

## Activation vérifiée

Le correctif est actif sur le serveur 3.5.41. Les 56 tests backend et les contrôles
syntaxiques ont réussi. Le contrôle UX signale neuf textes longs dans des sources
de console modifiées hors de ce correctif ; aucun changement d’interface n’a été
nécessaire ici.

L’essai sur la passerelle authentifiée active a rejoué la formulation signalée
avec un ancien refus artificiel dans le contexte. La recherche et la lecture ont
renvoyé trois sources, dont une page lue, puis une réponse sans refus d’accès.
Premier texte à 32,593 s sur cet essai ; la synthèse Phonon a ensuite été vérifiée
sur une phrase fictive distincte, avec un premier PCM en 0,094 s. Aucun run Hermes
n’a été créé. Les empreintes des données, clés, sources activées et réglages de
sauvegarde ainsi que les processus Qwen ont été contrôlés après activation.
