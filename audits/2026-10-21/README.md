# Livrable de l’audit du 21 octobre 2026

Lire [RAPPORT-AUDIT.md](RAPPORT-AUDIT.md).

## Preuves

- `inventaire.json` : fichiers suivis, tailles, empreintes des composants retenus, fonctions longues et recherche de formes de secrets.
- `synthese.json` : compteurs des tests, versions et regroupement des alias de sécurité.
- `production-lecture-seule.json` : santé et ports locaux, état des sauvegardes, ressources disponibles.
- `acl.json`, `acl-detail.json` : permissions Windows des répertoires et fichiers contrôlés, sans contenu des fichiers privés.
- `dependances-installees.json` : versions des cinq runtimes ; `pip check` indisponible pour Hermes, qui n’inclut pas pip.
- `osv.json`, `osv-resume.txt` : réponses publiques aux requêtes paquet/version. Les plages affectées ne suffisent pas à établir l’exploitabilité dans Fred.
- `android-assets.json`, `android-assets.diff`, `assets-android.txt` : désynchronisation des ressources générées.
- `livraisons.json` : vérification des distributions disponibles.
- `syntaxe.txt`, `tests-*.txt`, `android-lint.txt` : contrôles exécutés.
- `ruff-applications.json`, `bandit-applications.json` : analyse de 81 fichiers actuels hors tests/fixtures/validateurs ; les variantes sans suffixe `-applications` couvrent aussi des scripts historiques.

## Rejouer les collectes

Depuis `D:\Serveur IA`, avec les runtimes du poste :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' audits/2026-10-21/inventorier.py
& '.\Strata-src\.venv\Scripts\python.exe' audits/2026-10-21/verifier.py
& '.\Strata-src\.venv\Scripts\python.exe' audits/2026-10-21/analyser_dependances.py
& '.\Strata-src\.venv\Scripts\python.exe' audits/2026-10-21/synthetiser.py
```

Ces scripts réécrivent leurs preuves dans ce dossier. Les consultations OSV nécessitent Internet ; elles transmettent seulement noms et versions des paquets. `verifier.py` lit la console locale et les artefacts, sans instancier de contrôleur de production. `synthetiser.py` résume les journaux existants ; il ne lance pas les tests. Les commandes des suites sont documentées dans `RECONSTRUIRE-FRED.md`.

Les collectes utilisent le dépôt et les distributions du poste ; elles ne sont pas une installation autonome. Conserver les preuves d’origine avant de les rejouer, puisque l’état du projet et les avis publics peuvent évoluer.
