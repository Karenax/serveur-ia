# Inventaire des scripts suivis à la racine

Recherche du 16 novembre 2026 : références littérales insensibles à la casse au nom complet du script dans les fichiers suivis du dépôt. Le tableau ne couvre pas les raccourcis, tâches planifiées, chemins calculés, extensions omises et appels externes ; un complément local partiel figure ci-dessous. Une absence ne démontre donc jamais qu’un fichier est inutilisé. Aucun déplacement ni suppression n’a été effectué.

## Complément local du 17 novembre

Une recherche en lecture seule sur cette machine a examiné 196 tâches planifiées, 71 entrées de raccourcis dans les bureaux et menus Démarrer accessibles, et 278 processus. Certains répertoires de raccourcis se recoupent, donc ce nombre peut inclure des doublons. La tâche `\Kiara - ouverture de session` référence `Start-Interface-Qwen.ps1` dans ce dépôt : ce script et son chemin doivent rester disponibles tant que cette tâche existe. Aucun autre de ces éléments examinés ne mentionnait littéralement l’un des 81 noms de scripts racine ; aucun autre raccourci ou action de tâche ne mentionnait littéralement `D:\Serveur IA`. Les arguments de lancement n’ont pas été conservés dans le rapport. Résultat et périmètre détaillé : `D:\Kiara\essais\audit-corrections-20261116\inventaire-local.json`.

Cette recherche ne couvre pas les autres machines, comptes, raccourcis hors des emplacements examinés, références indirectes ou chemins calculés. Quelques dépendances calculées vérifiées dans le code illustrent le risque : `Start-Interface-Qwen.ps1` construit ses chemins depuis `$PSScriptRoot`, notamment vers `lanceur\app.py` et le Python local ; `Start-Qwen.ps1` invoque `Start-Qwen-GPU.ps1` depuis ce même dossier ; `Start-Strata-P100.ps1` calcule le chemin de `Warmup-Strata-P100.ps1` et de plusieurs configurations avant de lancer des processus. Déplacer ces fichiers séparément casserait ces chemins. L’inventaire ci-dessous ne justifie donc pas de suppression automatique.

| Script | Fichiers suivis qui citent son nom complet (4 exemples au plus) |
|---|---|
| `Activer-Historique-IQ4.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` |
| `Analyser-Comparatifs.py` | `Conserver-Comparatif-Strata.ps1`, `Finaliser-Analyse-P100.py`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` ; 8 fichiers au total |
| `Analyser-Strata-Hybride.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-02-strata-hybride-p100/Analyser-Strata-Hybride.py`, `comparatifs/2026-10-02-strata-hybride-p100/manifest-sha256.json` |
| `Auditer-IQ3-Reglages.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `audits/2026-10-21/ruff.json` |
| `Build-Cafe-Hybride-P100.cmd` | `RESULTATS-CAFE-IQ3-HYBRIDE.txt`, `audits/2026-10-12/inventory.json` |
| `Build-P100.cmd` | `RESULTATS-GPU.txt`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-cafe-q4-p100/RESULTATS-GPU.txt`, `comparatifs/2026-10-02-cafe-q4-p100/manifest.json` |
| `Build-Strata-Cache.cmd` | `Diagnostic-Cache-Hermes.md`, `audits/2026-10-12/inventory.json` |
| `Build-Strata-Contribution.cmd` | `audits/2026-10-12/inventory.json` |
| `Build-Strata-P100.cmd` | `Conserver-Comparatif-Strata.ps1`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-strata-hybride-p100/manifest-sha256.json`, `comparatifs/2026-10-02-strata-q4-p100/Conserver-Comparatif-Strata.ps1` ; 6 fichiers au total |
| `Check-Strata-Build-Dependencies.cmd` | `Conserver-Comparatif-Strata.ps1`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-strata-q4-p100/Conserver-Comparatif-Strata.ps1`, `comparatifs/2026-10-02-strata-q4-p100/manifest-final.json` |
| `Check-Strata-P100.cmd` | `Conserver-Comparatif-Strata.ps1`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-strata-q4-p100/Conserver-Comparatif-Strata.ps1`, `comparatifs/2026-10-02-strata-q4-p100/manifest-final.json` |
| `Comparer-Huihui-Final.ps1` | `audits/2026-10-12/inventory.json` |
| `Comparer-Huihui-Suite.ps1` | `audits/2026-10-12/inventory.json` |
| `Comparer-Huihui-Tensor.ps1` | `audits/2026-10-12/inventory.json` |
| `Comparer-Huihui.ps1` | `audits/2026-10-12/inventory.json` |
| `Comparer-Q4-IQ4.py` | `Executer-Comparatif-IQ4.py`, `Retablir-Strata-Cache-Q4.ps1`, `Tester-Strata-8coeurs.py`, `audits/2026-10-12/inventory.json` ; 12 fichiers au total |
| `Configurer-IQ4-Application.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` |
| `Conserver-Comparatif-Strata.ps1` | `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-strata-q4-p100/Conserver-Comparatif-Strata.ps1`, `comparatifs/2026-10-02-strata-q4-p100/manifest-final.json` |
| `Construire-Cache-Strata.py` | `Build-Strata-Cache.cmd`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` |
| `Continuer-Cache-Q4.ps1` | `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-03-q4-cpu8-vs16-p100/essai-075112/MANIFESTE-SHA256.json` |
| `Convert-MTP-Strata.py` | `Conserver-Comparatif-Strata.ps1`, `Prepare-Strata-Contribution.py`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` ; 8 fichiers au total |
| `Executer-Comparatif-IQ4.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-02-q4-iq4-xs-p100/essai-20261002-210119/manifest-sha256.json` |
| `Finaliser-Analyse-P100.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-02-strata-hybride-p100/Finaliser-Analyse-P100.py`, `comparatifs/2026-10-02-strata-hybride-p100/manifest-sha256.json` |
| `Fix-Strata-Build-Dependencies.ps1` | `Build-Strata-P100.cmd`, `Conserver-Comparatif-Strata.ps1`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-strata-hybride-p100/Build-Strata-P100.cmd` ; 8 fichiers au total |
| `Fix-Strata-Contribution-Dependencies.ps1` | `audits/2026-10-12/inventory.json` |
| `Garder-Strata-Debloque.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-03-q4-cpu8-vs16-p100/essai-075112/MANIFESTE-SHA256.json` |
| `Generer-CompteRendu-Strata.py` | `Conserver-Comparatif-Strata.ps1`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-02-strata-q4-p100/Conserver-Comparatif-Strata.ps1` ; 5 fichiers au total |
| `Inspect-Comparatif-IQ4.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-02-q4-iq4-xs-p100/essai-20261002-210119/manifest-sha256.json` |
| `Inspect-Gguf.ps1` | `audits/2026-10-12/inventory.json` |
| `Inspecter-GGUF.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` |
| `Install-EG2.ps1` | `RECONSTRUIRE-FRED.md`, `audits/2026-10-12/RAPPORT-AUDIT.md`, `audits/2026-10-12/inventory.json`, `audits/2026-10-12/powershell-syntax.json` ; 7 fichiers au total |
| `Liberer-Cache-Prelecture.ps1` | `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-03-q4-cpu8-vs16-p100/essai-075112/MANIFESTE-SHA256.json` |
| `Limiter-Strata-8coeurs.py` | `Retablir-Strata-Cache-Q4.ps1`, `Tester-Strata-8coeurs.py`, `Warmup-Strata-P100.ps1`, `audits/2026-10-12/inventory.json` ; 11 fichiers au total |
| `Link-Cafe-Hybride-P100.cmd` | `audits/2026-10-12/inventory.json` |
| `Mesurer-Chargement-Disques.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` |
| `Mesurer-Huihui-GPU.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `audits/2026-10-21/ruff.json` |
| `Mesurer-Huihui-RAM.ps1` | `audits/2026-10-12/inventory.json` |
| `Prelire-Experts-IQ4.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-02-q4-iq4-xs-p100/essai-20261002-210119/manifest-sha256.json` |
| `Prelire-Experts-Strata.py` | `Liberer-Cache-Prelecture.ps1`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-03-q4-cpu8-vs16-p100/essai-075112/Liberer-Cache-Prelecture.ps1` ; 5 fichiers au total |
| `Prelire-GPU2-IQ4.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-02-q4-iq4-xs-p100/essai-20261002-210119/manifest-sha256.json` |
| `Prepare-Strata-Contribution.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `audits/2026-10-21/ruff.json` |
| `Preparer-Cache-Q4.ps1` | `CHARGEMENT-Q4.txt`, `Start-Strata-P100.ps1`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-03-q4-cpu8-vs16-p100/essai-075112/MANIFESTE-SHA256.json` ; 6 fichiers au total |
| `Preparer-Cache-Q4.py` | `Continuer-Cache-Q4.ps1`, `Preparer-Cache-Q4.ps1`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` ; 7 fichiers au total |
| `Preparer-IQ4-Strata.py` | `Synthetiser-Comparatif-IQ4.py`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-02-q4-iq4-xs-p100/essai-20261002-210119/RAPPORT.txt` ; 6 fichiers au total |
| `Rapport-Strata-8coeurs.py` | `Retablir-Strata-Cache-Q4.ps1`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `audits/2026-10-21/ruff.json` ; 6 fichiers au total |
| `Resumer-Huihui.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` |
| `Retablir-Strata-Cache-Q4.ps1` | `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-03-q4-cpu8-vs16-p100/essai-075112/MANIFESTE-SHA256.json` |
| `Sauvegarder-Dependances.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `dependances/README.md` |
| `Serveur Qwen.cmd` | `README.md`, `SOURCES-WIREGUARD.txt`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit-applications.json` ; 8 fichiers au total |
| `Start-Cafe-IQ3-Hybride-P100.ps1` | `RESULTATS-CAFE-IQ3-HYBRIDE.txt`, `audits/2026-10-12/inventory.json` |
| `Start-Cafe-IQ3-P100.ps1` | `RESULTATS-CAFE-IQ3.txt`, `Start-Cafe-IQ3-Hybride-P100.ps1`, `Tester-Cafe-IQ3.py`, `audits/2026-10-12/inventory.json` |
| `Start-Huihui-P100.ps1` | `Comparer-Huihui-Final.ps1`, `Comparer-Huihui-Suite.ps1`, `Comparer-Huihui-Tensor.ps1`, `Comparer-Huihui.ps1` ; 7 fichiers au total |
| `Start-Huihui-Rapide-P100.ps1` | `RESULTATS-HUIHUI.txt`, `Resumer-Huihui.py`, `audits/2026-10-12/inventory.json` |
| `Start-Interface-Qwen.ps1` | `HISTORIQUE-PROJET-AVANT-AUDIT-20261012.md`, `README.md`, `RECONSTRUIRE-FRED.md`, `Serveur Qwen.cmd` ; 44 fichiers au total |
| `Start-Qwen-CPU-ancien.ps1` | `audits/2026-10-12/inventory.json` |
| `Start-Qwen-GPU.ps1` | `RESULTATS-GPU.txt`, `Start-Qwen.ps1`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-cafe-q4-p100/LISEZ-MOI.txt` ; 7 fichiers au total |
| `Start-Qwen.ps1` | `COMPARATIF-Q4-STRATA.txt`, `CONVERSATIONS-MULTIPLES.txt`, `Generer-CompteRendu-Strata.py`, `LISEZ-MOI-CPU-ancien.txt` ; 16 fichiers au total |
| `Start-Strata-IQ3-P100.ps1` | `audits/2026-10-12/inventory.json` |
| `Start-Strata-IQ4-P100.ps1` | `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-q4-iq4-xs-p100/essai-20261002-210119/manifest-sha256.json`, `maintenance/2026-10-13-strata-0.1.43.1/README.md`, `maintenance/2026-10-13-strata-0.1.43.1/deployer.py` |
| `Start-Strata-P100-Persistant.ps1` | `CHARGEMENT-Q4.txt`, `Mesurer-Chargement-Disques.py`, `Rapport-Strata-8coeurs.py`, `audits/2026-10-12/inventory.json` ; 10 fichiers au total |
| `Start-Strata-P100.ps1` | `Analyser-Strata-Hybride.py`, `CHARGEMENT-Q4.txt`, `COMPARATIF-Q4-STRATA.txt`, `Conserver-Comparatif-Strata.ps1` ; 25 fichiers au total |
| `Stop-Cafe-IQ3-P100.ps1` | `RESULTATS-CAFE-IQ3-HYBRIDE.txt`, `RESULTATS-CAFE-IQ3.txt`, `audits/2026-10-12/inventory.json` |
| `Stop-Huihui-P100.ps1` | `RESULTATS-HUIHUI.txt`, `Resumer-Huihui.py`, `audits/2026-10-12/inventory.json` |
| `Stop-Qwen-CPU-ancien.ps1` | `Stop-Qwen.ps1`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-cafe-q4-p100/Stop-Qwen.ps1` |
| `Stop-Qwen-GPU.ps1` | `RESULTATS-GPU.txt`, `Stop-Qwen.ps1`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-cafe-q4-p100/LISEZ-MOI.txt` ; 7 fichiers au total |
| `Stop-Qwen.ps1` | `COMPARATIF-Q4-STRATA.txt`, `Generer-CompteRendu-Strata.py`, `LISEZ-MOI-CPU-ancien.txt`, `LISEZ-MOI.txt` ; 14 fichiers au total |
| `Stop-Strata-IQ3-P100.ps1` | `audits/2026-10-12/inventory.json` |
| `Stop-Strata-IQ4-P100.ps1` | `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-q4-iq4-xs-p100/essai-20261002-210119/manifest-sha256.json` |
| `Stop-Strata-P100.ps1` | `Analyser-Strata-Hybride.py`, `CHARGEMENT-Q4.txt`, `COMPARATIF-Q4-STRATA.txt`, `Conserver-Comparatif-Strata.ps1` ; 18 fichiers au total |
| `Synthetiser-Comparatif-IQ4.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-02-q4-iq4-xs-p100/essai-20261002-210119/manifest-sha256.json` |
| `Test-Qwen-GPU.ps1` | `Conserver-Comparatif-Strata.ps1`, `RESULTATS-GPU.txt`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-cafe-q4-p100/LISEZ-MOI.txt` ; 8 fichiers au total |
| `Test-Qwen-Parallel.ps1` | `CONVERSATIONS-MULTIPLES.txt`, `audits/2026-10-12/inventory.json` |
| `Test-Strata-Hybride.ps1` | `Finaliser-Analyse-P100.py`, `LISEZ-MOI.txt`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-strata-hybride-p100/Finaliser-Analyse-P100.py` ; 6 fichiers au total |
| `Test-Strata-Hybride.py` | `Analyser-Strata-Hybride.py`, `Test-Strata-Hybride.ps1`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` ; 7 fichiers au total |
| `Test-Strata-P100.ps1` | `Conserver-Comparatif-Strata.ps1`, `LISEZ-MOI.txt`, `audits/2026-10-12/inventory.json`, `comparatifs/2026-10-02-strata-hybride-p100/LISEZ-MOI.txt` ; 8 fichiers au total |
| `Tester-Cafe-IQ3.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` |
| `Tester-Huihui.py` | `Comparer-Huihui-Final.ps1`, `Comparer-Huihui-Suite.ps1`, `Comparer-Huihui-Tensor.ps1`, `Comparer-Huihui.ps1` ; 6 fichiers au total |
| `Tester-Strata-8coeurs.py` | `Preparer-Cache-Q4.ps1`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json`, `comparatifs/2026-10-03-q4-cpu8-vs16-p100/essai-075112/MANIFESTE-SHA256.json` ; 5 fichiers au total |
| `Tester-Strata-IQ3.py` | `Start-Strata-IQ3-P100.ps1`, `Stop-Strata-IQ3-P100.ps1`, `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` |
| `Verify-Strata-Contribution.py` | `audits/2026-10-12/inventory.json`, `audits/2026-10-21/bandit.json` |
| `Warmup-Strata-P100.ps1` | `Conserver-Comparatif-Strata.ps1`, `Start-Strata-P100.ps1`, `Stop-Strata-P100.ps1`, `audits/2026-10-12/inventory.json` ; 14 fichiers au total |

Avant tout rangement, vérifier les appelants externes et effectuer un essai de lancement et de retour sur une copie. Les scripts de production, historiques P100 et de comparaison restent en place.
