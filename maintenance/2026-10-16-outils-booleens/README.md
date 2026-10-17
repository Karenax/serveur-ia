# Arguments booléens des outils Strata / OpenCode

Correctif du 16 octobre 2026 installé et vérifié sur le serveur de production. L'utilisateur a aussi demandé de passer de quatre à **20 emplacements de conversations sauvegardées**, en conservant le plafond global de **30 Gio (30 720 Mio)** et la réserve RAM de 6 Gio.

## Problème et correction

Deux appels OpenCode de `subagent` échouaient avec `background: "True"` : le schéma exige un booléen. Le parseur installé reproduisait cette sortie quand le modèle émettait `True` dans son format XML d'outil, et laissait également les chaînes booléennes dans la forme JSON. Le format brut des deux générations fautives n'a pas été enregistré : on ne peut pas distinguer rétrospectivement les deux formes dans cette session.

Le correctif dans `dependances/strata-0.1.43.1/source/serve/frontend.py` convertit uniquement les chaînes littérales `true` et `false` (casse et espaces périphériques tolérés) lorsque le schéma exige un booléen, éventuellement nullable. Il couvre les paramètres XML, les appels JSON, les objets/tableaux typés imbriqués et le flux progressif des arguments. Les champs texte, les champs non déclarés et les unions acceptant aussi du texte restent inchangés. `yes`, `no`, `0`, `1` et le texte arbitraire ne sont pas convertis en booléens.

Le correctif agit sur le serveur Python, sans modification du binaire CUDA, du modèle, de son template de prompt ou des configurations OpenCode. Aucun outil retourné par les essais n'a été exécuté sur l'hôte.

## Validation

- **355 tests réussis** : régressions booléennes, parseur et format frontend, appels trouvés dans la réflexion, noms d'outils et suite serveur. Cas XML `True`, `False`, `"True"`, `"False"`, format JSON, champs imbriqués, booléens nullable, unions booléen/texte et flux découpés jusqu'au caractère. Vérification HTTP OpenAI et Anthropic, avec et sans streaming. Sortie dans `tests.log`.
- **API réelle après redémarrage** : l'appel synthétique `bool_probe` renvoie `background: true` sans streaming puis `background: false` en streaming ; dans les deux cas, `marker: "True"` reste une chaîne. Ces essais vérifient l'intégration réelle ; la reproduction déterministe des graphies fautives est couverte par les tests à moteur simulé. Preuve : `validation-outils-live.json`.
- **Cache réel** : trois conversations synthétiques d'environ 3 k tokens sont alternées puis restaurées. Retours en 1,00–1,94 s, 7 ou 29 tokens relus, réponse A identique à la référence. Trois restaurations réussies. Preuve : `validation-cache/mesures.json`. Les 20 emplacements sont confirmés par les métriques ; cet essai ne les remplit pas tous.
- État final : modèle chargé et file vide, vision active, Hermes, passerelle et WireGuard disponibles. Empreintes des configurations d'accès, WireGuard, fournisseurs Hermes et exploitation identiques avant/après. Les valeurs finales de mémoire et les compteurs figurent dans `verification-finale.json`.

## Déploiement et conservation

Les deux profils persistants `lanceur/base-strata.json` et `strata-iq4-p100-hybride.json` contiennent `--conversation-cache-slots 20` et `--conversation-cache-mib 30720`. Le lanceur les conserve lors des prochains chargements. Les emplacements sont des conversations sauvegardées, en plus de la conversation active ; le budget mémoire peut imposer des évictions avant que tous soient utilisés.

Un seul redémarrage a appliqué les deux changements. Chargement et validation CUDA : **957,6 secondes**. La protection ponctuelle de RAM a cette fois détecté le moteur à travers le redirecteur Python Windows et a fonctionné automatiquement.

Deux prélectures ponctuelles, en lecture seule, ont accompagné le chargement à froid : le premier passage a lu environ 18 Gio puis s'est arrêté à son seuil de mémoire, et un second a parcouru les banques des couches 40–47. Les fichiers `prelecture.json` et `prelecture-40.json` détaillent ces passages. Ils ne sont pas intégrés au démarrage automatique et leur gain isolé n'a pas été mesuré.

`frontend-avant.py` conserve le parseur précédent. `strata-0.1.43.1-booleens.patch` contient le correctif et son test, et `source.json` les empreintes avant/après. Une mise à jour de la distribution tierce peut écraser le fichier modifié : vérifier la présence du correctif et rejouer les tests lors d'une mise à jour Strata.

Commande de vérification depuis le dossier source Strata :

```powershell
& 'D:/Serveur IA/Strata-src/.venv/Scripts/python.exe' -m unittest serve.test_tool_boolean_types serve.test_frontend serve.test_reasoning_tools serve.test_tool_name_space serve.test_server
```

Les scripts `deployer.py` et `verifier_live.py` conservent leurs preuves et refusent de les écraser ; ne pas relancer le déploiement pour simplement consulter l'état du serveur.
