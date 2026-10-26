# Bilan des vérifications — audit Kiara, 25–26 octobre 2026

## Suite corrective du 26 octobre 2026

Les constats ci-dessous décrivent l’état initial de l’audit. Les corrections du produit, validations et limites sont suivies dans [le rapport des correctifs](<D:/Serveur IA/maintenance/2026-10-26-correctifs-audit-global/README.md>) et [leur bilan](<D:/Serveur IA/maintenance/2026-10-26-correctifs-audit-global/AVANCEMENT.md>). Les preuves historiques restent conservées.

## Résultats

| Contrôle | Résultat | Preuve |
|---|---|---|
| Tests Python serveur | **568 réussis**, 1 294,226 s | [journal](<D:/Serveur IA/audits/2026-10-25-global/server-1.txt>) |
| Tests Python client Windows | **87 réussis** | [journal](<D:/Serveur IA/audits/2026-10-25-global/clients-1.txt>) |
| Tests Python voix | **38 réussis** | [journal](<D:/Serveur IA/audits/2026-10-25-global/clients-2.txt>) |
| Tests Python Android | **13 réussis** ; ne sont pas des tests sur téléphone | [journal](<D:/Serveur IA/audits/2026-10-25-global/clients-3.txt>) |
| Test du pont Go | **1 test réussi** : les commandes de contrôle passent pendant l’occupation des connexions de données | [journal](<D:/Serveur IA/audits/2026-10-25-global/go-tests.txt>) |
| Interface partagée | **15 suites réussies**, 173,89 s | [journal](<D:/Serveur IA/audits/2026-10-25-global/ui-1.txt>) |
| Syntaxe des sources | **Réussite** : 400 Python, 86 JavaScript/fragments HTML, 93 PowerShell sous chacune des deux versions de shell | [journal](<D:/Serveur IA/audits/2026-10-25-global/static-1.txt>) |
| Assets Android | **À jour**, `Prepare-Assets.py --check` | [journal](<D:/Serveur IA/audits/2026-10-25-global/static-2.txt>) |
| Android `lintDebug` | **0 erreur, 5 avertissements** | [exécution](<D:/Serveur IA/audits/2026-10-25-global/android-lint.txt>) |
| UX statique sur tous les fichiers | **56 fichiers, 9 avertissements de texte long** | [journal](<D:/Serveur IA/audits/2026-10-25-global/static-4.txt>) |
| UX sur les sources modifiées, exécuté par `posttest` | Réussite, aucun fichier UI produit modifié pendant l’audit | [journal UI](<D:/Serveur IA/audits/2026-10-25-global/ui-1.txt>) |
| Verrous runtime, outil officiel | **Échec** : cinq paquets de construction supplémentaires dans Strata | [journal](<D:/Serveur IA/audits/2026-10-25-global/static-3.txt>) |
| Vérification indépendante des cinq runtimes | Empreintes des verrous valides, versions verrouillées correspondantes ; extras seulement dans Strata | [données](<D:/Serveur IA/audits/2026-10-25-global/runtimes.json>) |
| `pip check` | Quatre réussites ; indisponible dans Hermes privé sans pip | [données](<D:/Serveur IA/audits/2026-10-25-global/runtimes.json>) |
| Avis Python OSV | 220 couples interrogés ; 7 couples concernés, 5 noms de paquets ; aucun échec de requête | [avis](<D:/Serveur IA/audits/2026-10-25-global/osv.json>) |
| Go `govulncheck` | 10 avis avec symboles atteignables statiquement dans la bibliothèque standard | [résumé](<D:/Serveur IA/audits/2026-10-25-global/go-summary.json>) |
| `npm audit` | Aucun avis remonté ; dépendances de développement uniquement | [résultat](<D:/Serveur IA/audits/2026-10-25-global/npm-audit.json>) |
| Reproductions ciblées | Conflit mémoire contournable par l’ancienne route ; annulation bloquée aux limites ; garde d’intention permissif | [résultats](<D:/Serveur IA/audits/2026-10-25-global/boundary-results.json>) |

**Total : 706 tests Python réussis**, plus le test Go et les quinze suites UI. Cette réussite ne signifie pas que tous les chemins sont couverts : les cas F01 et F02 ajoutés par l’audit révèlent précisément des lacunes de couverture.

Le test serveur de sauvegarde/restauration avec volume a également réussi sur données isolées : huit documents, 16 Mio d’originaux, archive de 30 289 407 octets, sauvegarde en 1,938 s, restauration en 6,563 s et empreintes identiques. Ce résultat ne mesure ni le NAS réel ni un sinistre complet sur une nouvelle machine.

Les cinq avertissements Android concernent notamment les différences de niveau d’API pour le retour système, JavaScript dans WebView, une ressource redondante, une API d’estimation de l’espace libre et l’icône monochrome. JavaScript est nécessaire à l’application ; l’avertissement ne prouve pas que son activation constitue ici une faille. Le détail produit par lint est conservé dans le dossier d’audit.

## Parcours visuels

- Windows, 1 440 × 900 : conversations, vocal, projets, correcteur, tâches, notifications, mémoire/rappels ; réglages accès, connexion, mises à jour et API ; inspection du thème sombre.
- Console isolée : les seize rubriques de navigation, notamment clients, sauvegardes, mémoire, API, tâches et notifications ; contrôle ciblé en largeur de téléphone.
- Android, couche web : conversations, vocal et mémoire/rappels à 390 × 844 et 768 × 1024 ; menu, fermeture avec Échap et retour du focus.
- Captures conservées dans [le dossier UI](<D:/Serveur IA/audits/2026-10-25-global/ui>).

Les contrôles de géométrie n’ont pas relevé de débordement horizontal sur les états parcourus. Les captures ont été prises après stabilisation des animations. Les limites de l’inspection — matériel, états rares, longs contenus, lecteur d’écran — sont exposées dans le rapport.

## Reproduire les contrôles

Depuis `D:\Serveur IA`, les groupes de contrôles existants peuvent être relancés avec le Python du projet :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s lanceur -v
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s client-qwen -v
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s client-voice -v
& '.\Strata-src\.venv\Scripts\python.exe' -m unittest discover -s client-android/tests -v
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/check_sources.py
& '.\Strata-src\.venv\Scripts\python.exe' client-android/scripts/Prepare-Assets.py --check
& '.\Strata-src\.venv\Scripts\python.exe' maintenance/verrous_runtime.py check
npm --prefix client-qwen test
npm --prefix client-qwen run ux:check:all
```

Attention à l’effet de bord identifié F15 : certaines suites UI écrivent encore dans les preuves historiques. Le script [run_checks.py](<D:/Serveur IA/audits/2026-10-25-global/run_checks.py>) conserve les captures visées avant exécution et restaure leurs octets ensuite. Le script ponctuel `restore_test_screenshots.py` est une trace de la remise en état de cet audit, pas un outil à relancer sans vérifier l’état courant.

La reproduction des défauts est autonome et utilise des bases temporaires :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' audits/2026-10-25-global/reproduce_boundaries.py
```

Les scripts d’inventaire et de dépendances sont des outils d’audit, pas des commandes de mise à jour. Les consultations OSV et `govulncheck` utilisent le réseau pour lire les avis publics. Le contrôle Go a téléchargé ses outils d’analyse dans les caches de toolchain ; aucun binaire applicatif n’a été remplacé.

## Préservation du travail

Les fichiers applicatifs et les modifications préexistantes ont été préservés. Les captures historiques écrasées par certains tests ont été restaurées, leurs nouvelles versions étant conservées dans `ui-tests`. Les seuls nouveaux fichiers destinés à rester dans le dépôt sont les livrables et preuves de ce dossier d’audit. Les caches ordinaires d’outillage peuvent avoir été alimentés par les contrôles.

Les fixtures de navigateur ont utilisé les ports locaux 51872, 51873 et 8875. Elles sont distinctes du serveur réel. Leur fermeture et le contrôle final de l’état Git sont enregistrés dans `final-state.json`.
