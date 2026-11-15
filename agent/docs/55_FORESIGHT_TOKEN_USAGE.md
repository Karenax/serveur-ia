# Mesure des tokens des réponses de réunion

Complément L11 du 16 octobre 2026, actif sur Agent 8001. Mesure des réponses
conservées de la Discussion et des Questions en direct, dans leurs périmètres
séance, projet, sources ou global. Ce compteur ne représente pas la consommation
de tous les modules d'Agent, ni une facture fournisseur.

## Mesures disponibles

Le client conserve les compteurs réellement reçus du moteur : `prompt_tokens`,
`completion_tokens` et `total_tokens` pour les réponses compatibles OpenAI ;
`prompt_eval_count` et `eval_count` pour Ollama. Un total fourni est conservé.
À défaut, le total peut être la somme des deux composantes **toutes deux fournies**,
avec cette formule explicitement enregistrée. Aucun calcul depuis le texte.

Les valeurs négatives, booléennes, décimales, chaînes ou absentes ne deviennent
pas des tokens mesurés. Un total contradictoire avec ses deux composantes est
marqué incohérent et exclu. Les modèles qui n'exposent pas ces données restent
sans mesure. Aucun prix, token économisé ou coût supposé.

Une réponse peut nécessiter plusieurs tentatives, par exemple après une réponse
vide ou lors du secours local. Chaque tentative garde sa mesure connue, ou son
absence de mesure. La consommation connue des tentatives est additionnée ; une
tentative sans compteur rend la couverture partielle. Une tentative échouée
n'est pas supposée gratuite. Aucun mot de passe, prompt, réponse ou message
d'erreur détaillé n'est conservé dans ce reçu de mesure.

Le reçu est attaché à l'événement de réponse existant sous `usage`. Le rejeu de
cette réponse conserve le même reçu et ne double pas le compteur. La collecte
utilise un contexte propre à la requête et au thread de génération. Les appels
extérieurs à cette collecte gardent leur comportement existant.

Les échecs qui ne produisent aucune réponse conservée ne font pas partie de ce
compteur des réponses ; ce n'est pas un journal exhaustif de facturation du
service. Les notes enrichies, CR, classements de mails et autres modules ne sont
pas incorporés silencieusement dans le compteur de l'assistant de séance.

## Lecture des statistiques

**Réglages → Autres réglages → Statistiques → Tokens mesurés** affiche la somme
connue des réponses accessibles, puis distingue :

- réponses avec mesure complète ;
- réponses avec mesure partielle ;
- réponses sans mesure, notamment l'historique antérieur à l'instrumentation.

S'il n'existe aucune mesure disponible, la valeur reste « Indisponible ».
Les droits actuels des citations sont vérifiés avant agrégation. Les quatre
réponses historiques de la base actuelle restent sans mesure ; elles ne sont
ni recalculées, ni modifiées. Les formules sont aussi exposées par l'API Stats.

## Vérification

201 contrôles ciblés passent : compteurs, types invalides, tentatives reprises,
échec et secours, isolation entre threads et contextes imbriqués, conservation
asynchrone/rejeu, CDC, routage et déchargement, assistant, enrichissements,
statistiques et avis humains. Un avertissement de dépréciation TestClient reste
conservé. Les deux contrôles frontend, TypeScript, Vite et Ruff réussissent.
Les cohortes ne sont pas additionnées aux suites globales historiques.

Un parcours réel sur notes fictives privées utilise le modèle réseau déjà chargé
`google/gemma-4-26b-a4b-qat`, sans repli ni chargement local. La réponse conserve
1250 W et 350 lux avec citation ; le fournisseur expose **176 tokens de contexte
+27 tokens de réponse =203 tokens au total**. Le reçu SQL et Stats retrouvent203,
avec couverture complète ; le rejeu garde la même réponse et la même mesure.
Les bases privées restent intègres. Gemma local est déchargé avant et après.
Ce résultat qualifie la mesure des tokens de ce moteur, pas une précision
industrielle générale ou une mesure de temps d'affichage.

L'observation ajoutée dans `_post_llm` est isolée : une comparaison AST après
retrait de ses seuls contextes d'observation retrouve exactement le transport,
les paramètres et le repli antérieurs. Les autres fonctions du client restent
identiques. Aucun protocole de capture, modèle ASR ou publication métier changé.

Activation après sauvegardes Brain/ERP/EG2 et restaurations privées. Les assets
servis correspondent à la compilation et les anciens sont conservés. Les données
historiques ne sont pas réécrites. Aucun microphone, téléchargement ou nouvelle
coupure réseau. Le fonctionnement entièrement hors ligne, la capture matérielle
et le direct industriel restent à qualifier ; L11/L12 ne sont pas clos.

Pièces : `.ui-preview/l11-token-usage-20261016/`,
`logs/foresight-runtime/L11-token-usage-ROOT-20261016.json` et matrice courante
`docs/40_FORESIGHT_ACCEPTANCE.md`.
