La seconde étape, avec modifications et publication, est décrite dans [VALIDATION-CORRECTIONS.md](VALIDATION-CORRECTIONS.md). Les paragraphes ci-dessous décrivent les preuves de l’audit initial, avant correction.

# Preuves de l’audit du 12 octobre 2026

Rapport principal : [RAPPORT-AUDIT.md](<D:/Serveur IA/audits/2026-10-12/RAPPORT-AUDIT.md>).

`inventory.json` décrit les sources suivies et leurs empreintes avant vérification. Une comparaison finale des 351 fichiers de cet inventaire ne relève aucun changement. `repo-results.json` décrit les volumes suivis, les références de moteurs et la recherche de candidats secrets sans enregistrer leurs valeurs.

`reproductions.json` contient sept scénarios synthétiques correspondant à six défauts applicatifs ; les deux scénarios d’historique portent sur le même défaut. Le septième problème du rapport concerne PowerShell et figure dans `powershell-syntax.json`. Le script d’installation EG2 n’a pas été exécuté. Sous PowerShell 7.6.5, sa source UTF-8 produit quatre erreurs de syntaxe ; sous Windows PowerShell 5.1.19041.6456, `ParseFile` produit zéro erreur.

`tests-server.log`, `tests-client.log`, `tests-voice.log` et `tests-android-python.log` conservent les sorties des 481 tests existants. Les journaux sont exclus par la règle Git générale `*.log` ; les principaux compteurs sont aussi consignés dans le rapport. `coverage-server.json` conserve les mesures de la suite serveur uniquement.

`ui-results.json` décrit les 58 vérifications syntaxiques et huit suites JavaScript. Les journaux séparés des suites et les captures sont dans ce dossier et `ui/`. Les cinq fichiers CJS ont exécuté les interfaces avec un navigateur sans fenêtre visible, dont les transformations Android en mémoire.

`android-lint.log` est la sortie de Gradle ; `android-lint-results.json` contient les cinq avertissements extraits du rapport XML. Le build de lint travaille sur les sources locales sans publication ni installation d’APK.

Les analyses statiques portent sur 99 fichiers Python suivis des composants applicatifs et de leurs utilitaires. `ruff.json`, `bandit.json` et `vulture.txt` sont les résultats bruts. Ils nécessitent la qualification du rapport : leur nombre ne représente pas un nombre de bugs confirmés.

Outils installés pour l’audit dans `toolchain/audit-python`, séparément des runtimes applicatifs : Ruff 0.17.0, Coverage 7.16.2, Bandit 1.9.4 et Vulture 2.16. Python applicatif : 3.12.14. Les commandes sont lancées depuis `D:\Serveur IA`.

Pour rejouer les reproductions et les contrôles qui ne nécessitent pas de modèles réels :

```powershell
& '.\Strata-src\.venv\Scripts\python.exe' -X utf8 'audits\2026-10-12\reproduce.py'
& '.\Strata-src\.venv\Scripts\python.exe' -X utf8 'audits\2026-10-12\ui_checks.py'
& '.\Strata-src\.venv\Scripts\python.exe' -X utf8 'client-android\scripts\Prepare-Assets.py' --check
```

`ui_checks.py` suppose le Playwright et le Chrome de ce poste, comme les tests existants. Les fixtures de `reproduce.py` ne contactent ni fournisseur externe ni modèle de production.

Pour la suite serveur mesurée avec Coverage :

```powershell
$env:PYTHONPATH = 'D:\Serveur IA\toolchain\audit-python\Lib\site-packages'
$env:COVERAGE_FILE = 'D:\Serveur IA\audits\2026-10-12\.coverage-server'
& '.\Strata-src\.venv\Scripts\python.exe' -X utf8 -m coverage run --branch --source=lanceur,client-qwen -m unittest discover -s lanceur -p 'test_*.py' -v
& '.\Strata-src\.venv\Scripts\python.exe' -m coverage json -o 'audits\2026-10-12\coverage-server.json'
```

Les autres suites Python se relancent avec `-m unittest discover -s client-qwen`, `-s client-voice` et `-s client-android/tests`, et le motif `test_*.py`. Les tests serveur comportent certains essais de moteurs et de runtimes natifs installés dans ce poste ; ils demandent plus de prérequis qu’un checkout vierge.

Pour Android lint :

```powershell
. '.\client-qwen\android-outils\Environnement-Android.ps1'
& '.\toolchain\gradle-8.13\bin\gradle.bat' --offline --no-daemon --console=plain -p 'client-android' lintDebug
```

Les scripts `inventory.py`, `static_checks.py`, `repo_checks.py` et `ui_checks.py` écrivent leurs résultats dans le dossier de cet audit. Les fichiers applicatifs sont lus sans être modifiés.
