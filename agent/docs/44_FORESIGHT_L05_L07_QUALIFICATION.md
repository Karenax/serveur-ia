# Qualification L05 et L07 — Assistant et notes enrichies

L05 et L07 sont qualifiés selon leurs livrables et sorties : scopes/citations/file, puis ajouts sourcés et questions. La qualité du STT direct, la capture matérielle et les mesures P95 restent dans leurs lots/recettes ; L12 reste ouvert.

## L05

| Exigence | Preuve inspectée |
|---|---|
| Scopes séance/sources/projet/global contrôlés serveur et historique partitionné | Tests Session assistant/histoire dans le ciblé107 ; droits/identités/relecture21 ; sélections et clés de conversation distinctes |
| Contexte provisoire séparé du canon, citations et budget | Aucun Source avant attribution ; citations note/version/bloc, calendrier working, audio/segment ; budget borné avant transport ; corpus canonique courant contrôlé |
| File par moteur et priorité au geste utilisateur | Planificateur inchangé ; contrôle réseau réel avec trois demandeurs : question arrivée dernière mais servie avant les deux automatiques |
| Regroupement et annulation des sorties périmées | Réservation SQL d’une seule action par tick et par snapshot ; stabilité ; annulation de file ;47tests actuels ; propositions/answers obsolètes après changement |
| Aucune fuite ; sources périmées exclues ; sans réponse explicite | Cas de droits/révocation/scopes/historique et d’absence de citations ; fonctions answer/visibility inchangées ; relecture courante réelle avec LLM réseau |
| Placement réseau/local conforme | Lecture actuelle des catalogues LM Studio : modèle génératif primaire chargé, aucun génératif local chargé ; pas de load/unload/génération lancé par cette lecture |

## L07

| Exigence | Preuve inspectée |
|---|---|
| Stabilisation du texte, ajouts structurés par point et provenance | Module session_enhancements identique à l’essai réel utile ; JSON additions avec références/quotes vérifiées, nouvelles propositions après stabilité ; actuel47 |
| Acceptation/rejet sans réécriture automatique ou publication | Notes ajoutées seulement par commande humaine, avec version attendue et saga rejouable ; rejet distinct ; protection de saisie actuelle par92contrats Studio réutilisés |
| Respect réserves/négations/nombres/unités | Trois résultats réels utiles inspectés : Nora proposée, réserve fournisseur, absence de commande acceptée et1250W conservés ; citations vérifiées. Preuve sur ce corpus, pas garantie universelle |
| Questions dédupliquées et épinglables | Écho de texte normalisé avec intervalles audio chevauchants traité une fois, sans fusion de valeurs différentes ni répétitions ultérieures ; cas inter-séances ; contrats pin/rejeu/quota conservés |
| Saisie pendant génération, sorties obsolètes et sources consultables | Contrats Studio de brouillon riche/Markdown et réception de proposition ;92cas réussis et source Studio inchangée ; DOM réel des trois cartes et citations disponible |
| Automatismes désactivables en gardant chat et transcription | Opt-ins séparés ;47cas actuels de réservation/stabilité/arrêt/permissions ; chemins manuels et collecte texte indépendants des deux drapeaux automatiques |

## Échos de questions

La déduplication compare mots et signes après normalisation Unicode, casse et espaces ; la ponctuation significative est conservée. Elle exige un chevauchement réel des intervalles audio de deux segments de la même séance et une tentative déjà conservée pour la version du segment correspondant.
Les valeurs numériques restent des tokens distincts : 1250 et2250 ne sont pas fusionnés. Une répétition hors recouvrement ou une autre séance peut déclencher sa propre réponse. Aucune fenêtre arbitraire en secondes n’est introduite.
Les deux segments restent conservés. L’événement assistant.proactive-duplicate contient question_token et duplicate_of ; il évite une seconde génération et ne valide aucune information. Le SSE reste un signal sans contenu privé, selon son filtrage existant.
Le premier test complémentaire tentait deux captures simultanées et a été refusé par le produit. Il est conservé ; le cas corrigé utilise des séances successives et garde ce contrôle de propriété intact.

## Portée des preuves

Le correctif passe47cas affectés puis un cas complémentaire ; les quatre cas de chevauchement sont inclus dans47. Le ciblé107, le ciblé21 et les92contrats UI sont antérieurs, recouvrants et réutilisés après contrôle des sources/fonctions concernées. Aucun total global courant n’est inventé.
Les trois réponses utiles avec DOM réel et le contrôle réseau de priorité restent leurs essais datés. Le module de suggestions et les fonctions de réponse/visibilité sont identiques ; les évolutions de préparation/relecture disposent de leurs contrôles actuels séparés. Les anciens indicateurs de qualification limitée restent inchangés.
Les réserves et chiffres sont préservés dans le corpus réel observé ; cela ne démontre pas une absence universelle d’hallucination ni une qualité industrielle du STT. Les propositions demeurent soumises à lecture humaine et ne publient rien automatiquement.
La lecture actuelle des catalogues LM Studio constate le génératif réseau chargé et aucun génératif local chargé. Cette lecture ne lance ni chargement ni génération ; elle ne constitue pas un nouveau test de réponse.
Activation après sauvegardes/restaurations privées des trois bases et comparaison exacte des lignes non volatiles Brain/ERP. Aucun modèle, micro, GPU, téléchargement ou nouvelle génération dans ce correctif. Ruff passe.

[Audit et empreintes](../logs/foresight-runtime/L05-L07-assistant-qualification-ROOT-20261016.json).

### Précision de comparaison des questions — 16 octobre 2026

La déduplication ignore les espaces et la casse, avec normalisation Unicode,
mais conserve chaque signe de ponctuation. Elle distingue les références
AIRB…-A et AIRB…/A, ainsi que1,5 et1/5. Les deux cas échouaient avant précision ;
les sept cas de déduplication passent sur la version finale. Les autres43cas
du ciblé47 restent leurs preuves acquises, sans nouvelle exécution ni cumul.
La portée inter-séances et les répétitions ultérieures restent conservées.

Correction activée, sans nouvelle génération ni capture. Les sauvegardes SQL
récentes intactes et leurs restaurations déjà qualifiées sont réutilisées après
comparaison exacte des données non volatiles Brain/ERP avant et après redémarrage.
Ruff passe. L05/L07 restent qualifiés ; L12 reste ouvert.
