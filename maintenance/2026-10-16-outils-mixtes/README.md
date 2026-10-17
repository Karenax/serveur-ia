# Appels d'outils XML/JSON mixtes — correction activée

Le 16 octobre 2026, l'utilisateur a d'abord demandé de corriger le parseur **sans redémarrer le moteur pour l'instant**. La préparation décrite ci-dessous a respecté cette demande. Il a ensuite demandé explicitement la relance : le correctif est désormais [activé et vérifié](../2026-10-16-activation-outils-mixtes/README.md). Les preuves de préparation sans interruption sont conservées séparément des preuves d'activation.

## Défaut reproduit

Le parseur transformait en `{}` un objet JSON placé directement dans une enveloppe XML de fonction, par exemple :

```text
<tool_call>
<function=subagent>
{"agent":"explore","description":"Frontend","prompt":"Lecture seule"}
</function>
</tool_call>
```

Le flux progressif pouvait également annoncer l'outil puis émettre `{}`, car son lecteur d'arguments attendait des balises `<parameter=...>`. Dans la session signalée, un appel vide et un appel frontend complet apparaissent dans le même message. La génération brute n'est pas conservée : le défaut mixte est reproduit, mais son implication dans cet appel précis reste non prouvée.

## Changement préparé

- Les objets JSON dans une enveloppe XML de fonction sont décodés, avec ou sans clôture Markdown `json`. Les variantes sans enveloppe externe ou avec plusieurs fonctions sont aussi prises en charge lorsque la récupération correspondante est activée.
- Les balises XML présentes dans les chaînes JSON restent du texte ; elles ne terminent pas prématurément l'appel. Aucun remplacement global de texte n'est effectué.
- Les arguments booléens continuent de bénéficier du correctif précédent selon leur schéma.
- Les champs obligatoires de premier niveau (`required`) sont vérifiés avant la transmission d'un appel. Un appel complet auquel il manque des champs provoque une erreur explicite listant les clés manquantes ; aucune valeur n'est inventée. Les outils autorisés à n'avoir aucun argument restent valides.
- Les outils qui déclarent des champs obligatoires sont assemblés avant leur émission comme appel, y compris en streaming. Les arguments n'apparaissent donc plus caractère par caractère pour ces outils ; le flux de réponse et les mécanismes de maintien de connexion du serveur restent disponibles. Les appels mixtes sont également assemblés. Les outils XML sans champs obligatoires gardent leur flux d'arguments progressif.
- Un appel tronqué avant sa fin ne devient pas un appel complet. Ce correctif n'ajoute pas de régénération automatique et ne constitue pas une validation exhaustive de toutes les contraintes JSON Schema.

## Vérifications

**367 tests de régression passent** : formats mixtes, champs obligatoires, booléens, frontend, réflexion, noms d'outils et suite serveur. Les 12 tests du nouveau module passent aussi isolément après fermeture explicite des réponses HTTP de test.

Les essais HTTP utilisent un moteur simulé sur des ports locaux temporaires, avec les vrais sérialiseurs OpenAI et Anthropic, avec et sans streaming. Les arguments mixtes sont conservés. Un appel incomplet en champs obligatoires retourne HTTP 400 sans streaming, ou un événement d'erreur après le début du flux, sans émettre d'invocation vide. Les en-têtes et corps ne sont pas ceux d'une requête de production.

Les identités PID + heure de création du serveur, du moteur texte et de l'encodeur visuel sont identiques avant/après. Le pointeur de session n'a pas changé. Les métriques de production confirment toujours **20 emplacements / 30 720 Mio**. Preuves : `validation.json`, `tests.log`, `tests-hybrides.log` et `processus-avant.json`.

`frontend-avant.py` contient la version avec le seul correctif booléen, chargée avant cette activation. `strata-0.1.43.1-outils-mixtes.patch` contient le nouveau correctif et son module de test. Il s'applique après le patch booléen du dossier `2026-10-16-outils-booleens`. `source.json` indique les empreintes et le rapport d'activation. Aucun binaire CUDA, réglage de modèle, cache ou fichier OpenCode n'a été modifié par ce correctif.

Le service Strata a été redémarré et sa vérification d'intégration est réussie ; voir le [rapport d'activation](../2026-10-16-activation-outils-mixtes/README.md).
